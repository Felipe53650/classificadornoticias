from fastapi.testclient import TestClient
import pytest
from src.api.main import create_app


@pytest.fixture
def client(trained_dir, tmp_path):
    with TestClient(create_app(str(trained_dir), f"sqlite:///{(tmp_path / 'test.db').as_posix()}")) as instance:
        yield instance


def test_health_and_pages(client):
    assert client.get("/health").json()["model_loaded"] is True
    for path in ("/", "/editor", "/history", "/static/css/app.css", "/static/css/feed.css", "/static/js/app.js"):
        assert client.get(path).status_code == 200


@pytest.mark.parametrize("payload", [{}, {"title": " ", "content": "<p></p>"}, {"title": "x" * 501}, {"content": "x" * 100001}])
def test_invalid_classification(client, payload):
    assert client.post("/api/classify", json=payload).status_code == 422


def test_editorial_flow_and_no_automatic_article(client):
    response = client.post("/api/classify", json={"title": "Banco e juros", "content": "Mercado e inflação"})
    assert response.status_code == 200
    prediction = response.json()
    assert client.get("/api/articles").json()["total"] == 0
    alternative = next(c for c in client.get("/api/categories").json()["categories"] if c != prediction["predicted_category"])
    payload = {"prediction_id": prediction["prediction_id"], "final_category": alternative, "confirmed": True}
    assert client.post("/api/articles", json={**payload, "confirmed": False}).status_code == 422
    assert client.post("/api/articles", json={**payload, "predicted_confidence": .99}).status_code == 422
    assert client.post("/api/articles", json={**payload, "final_category": "inexistente"}).status_code == 422
    saved = client.post("/api/articles", json=payload)
    assert saved.status_code == 201
    assert saved.json()["was_corrected"] is True
    assert saved.json()["predicted_confidence"] == prediction["confidence"]
    assert client.post("/api/articles", json=payload).status_code == 409
    assert client.get("/api/articles?was_corrected=true").json()["total"] == 1
    assert client.get("/api/articles?was_corrected=false").json()["total"] == 0
    assert client.get("/api/articles?offset=1").json()["items"] == []
    assert client.get("/api/feedback").json()["corrections"] == 1


def test_unavailable_model(tmp_path):
    with TestClient(create_app(str(tmp_path / "missing"), "sqlite://")) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").json()["status"] == "degraded"
        assert client.post("/api/classify", json={"title": "notícia"}).status_code == 503
        assert client.get("/").status_code == 200
        assert client.get("/news/demo-cidade-mais-verde").status_code == 200


def test_feed_examples_filters_and_reading(client):
    home = client.get("/")
    assert len(home.context["stories"]) == 7
    assert home.context["total"] == 8
    assert 'src="/static/js/app.js"' not in home.text
    second = client.get("/?p=2")
    assert len(second.context["stories"]) == 1
    assert {s["key"] for s in home.context["stories"]}.isdisjoint(s["key"] for s in second.context["stories"])
    assert client.get("/?p=999").context["current_page"] == 2
    assert client.get("/?category=Tecnologia").context["total"] == 1
    assert client.get("/", params={"q": "BIBLIOTECA", "source": "demo"}).context["total"] == 1
    assert client.get("/?q=zzzinexistente").context["total"] == 0
    assert "Nenhuma matéria" in client.get("/?source=editorial").text
    assert client.get("/api/articles").json()["total"] == 0
    assert client.get("/api/feedback").json()["total"] == 0
    for path in ("/news/inexistente", "/news/local-999", "/news/local-9999999999999999999999"):
        assert client.get(path).status_code == 404
    story = client.get("/news/demo-cidade-mais-verde")
    assert "Conteúdo fictício" in story.text
    assert "jardins de chuva" in story.text
    assert client.get("/?p=0").status_code == 422
    assert client.get("/?source=invalid").status_code == 422


def test_feed_requires_confirmation_and_uses_final_category(client):
    title = "Banco e juros <script>alert(1)</script>"
    content = 'Texto do mercado <img src=x onerror="alert(1)">\nSegundo parágrafo.'
    prediction = client.post("/api/classify", json={"title": title, "content": content}).json()
    assert client.get("/?source=editorial").context["total"] == 0
    category = next(c for c in client.get("/api/categories").json()["categories"] if c != prediction["predicted_category"])
    saved = client.post("/api/articles", json={"prediction_id": prediction["prediction_id"], "final_category": category, "confirmed": True}).json()
    home = client.get("/")
    assert home.context["stories"][0]["key"] == f"local-{saved['id']}"
    assert home.context["stories"][0]["category"] == category
    assert home.context["total"] == 9
    assert len(client.get("/?p=2").context["stories"]) == 2
    assert client.get("/", params={"source": "editorial", "category": category, "q": "BANCO"}).context["total"] == 1
    assert client.get("/", params={"source": "editorial", "q": "%"}).context["total"] == 0
    assert client.get("/?source=demo").context["total"] == 8
    reading = client.get(f"/news/local-{saved['id']}")
    assert reading.status_code == 200
    assert "Segundo parágrafo." in reading.text
    assert "<script>alert(1)</script>" not in reading.text
    assert "<img src=x" not in reading.text
    assert "&lt;script&gt;" in home.text


def test_feed_pagination_across_local_and_example_stories(client):
    for index in range(8):
        prediction = client.post("/api/classify", json={"title": f"Banco e juros {index}"}).json()
        assert client.post("/api/articles", json={"prediction_id": prediction["prediction_id"],
            "final_category": prediction["predicted_category"], "confirmed": True}).status_code == 201
    pages = [client.get(f"/?p={number}").context["stories"] for number in (1, 2, 3)]
    keys = [story["key"] for page in pages for story in page]
    assert len(keys) == len(set(keys)) == 16
    assert keys[:8] == [f"local-{number}" for number in range(8, 0, -1)]
    assert all(key.startswith("demo-") for key in keys[8:])


def test_persistence_after_restart(trained_dir, tmp_path):
    database = f"sqlite:///{(tmp_path / 'persistent.db').as_posix()}"
    with TestClient(create_app(str(trained_dir), database)) as client:
        result = client.post("/api/classify", json={"title": "Juros e inflação"}).json()
        saved = client.post("/api/articles", json={"prediction_id": result["prediction_id"], "final_category": result["predicted_category"], "confirmed": True})
        assert saved.status_code == 201
    with TestClient(create_app(str(trained_dir), database)) as client:
        article = client.get("/api/articles").json()["items"][0]
        assert article["was_corrected"] is False
        assert article["title"] == "Juros e inflação"


def create_article(client, title="Banco e juros", content="Mercado e inflação"):
    prediction = client.post("/api/classify", json={"title": title, "content": content}).json()
    response = client.post("/api/articles", json={"prediction_id": prediction["prediction_id"],
        "final_category": prediction["predicted_category"], "confirmed": True})
    assert response.status_code == 201
    return response.json()


def test_edit_article_replaces_analysis_and_updates_feed(client):
    article = create_article(client)
    detail = client.get(f"/api/articles/{article['id']}").json()
    assert detail["revision"] == article["revision"]
    assert detail["analysis"]["prediction_id"] == article["prediction_id"]
    new_title = "Futebol e campeonato <script>alert(1)</script>"
    analysis = client.post("/api/classify", json={"title": new_title, "content": "O time venceu o jogo."}).json()
    payload = {"prediction_id": analysis["prediction_id"], "final_category": analysis["predicted_category"],
               "confirmed": True, "expected_revision": article["revision"]}
    assert client.put(f"/api/articles/{article['id']}", json={**payload, "confirmed": False}).status_code == 422
    assert client.put(f"/api/articles/{article['id']}", json={**payload, "title": "Texto adulterado"}).status_code == 422
    assert client.put(f"/api/articles/{article['id']}", json={**payload, "final_category": "Inválida"}).status_code == 422
    assert client.put(f"/api/articles/{article['id']}", json={**payload, "prediction_id": "ausente"}).status_code == 404
    updated = client.put(f"/api/articles/{article['id']}", json=payload)
    assert updated.status_code == 200
    data = updated.json()
    assert data["id"] == article["id"]
    assert data["title"] == new_title
    assert data["created_at"].rstrip("Z") == article["created_at"].rstrip("Z")
    assert data["predicted_confidence"] == analysis["confidence"]
    assert data["was_corrected"] is False
    assert data["revision"] != article["revision"]
    assert client.get("/api/articles").json()["total"] == 1
    assert client.get("/?source=editorial").context["stories"][0]["title"] == new_title
    reading = client.get(f"/news/local-{article['id']}")
    assert "O time venceu o jogo." in reading.text
    assert "<script>alert(1)</script>" not in reading.text
    assert client.get("/api/feedback").json()["corrections"] == 0
    assert client.put(f"/api/articles/{article['id']}", json=payload).status_code == 409
    assert client.request("DELETE", f"/api/articles/{article['id']}", json={
        "confirmed": True, "expected_revision": article["revision"]}).status_code == 409


def test_category_only_edit_without_loaded_model(client):
    article = create_article(client)
    detail = client.get(f"/api/articles/{article['id']}").json()
    alternative = next(c for c in detail["categories"] if c != article["predicted_category"])
    client.app.state.classifier = None
    updated = client.put(f"/api/articles/{article['id']}", json={
        "prediction_id": article["prediction_id"], "final_category": alternative,
        "confirmed": True, "expected_revision": article["revision"]})
    assert updated.status_code == 200
    assert updated.json()["was_corrected"] is True
    assert updated.json()["title"] == article["title"]
    assert client.get("/api/feedback").json()["corrections"] == 1
    assert client.get("/?source=editorial").context["stories"][0]["category"] == alternative


def test_edit_rejects_analysis_used_by_other_article(client):
    first, second = create_article(client), create_article(client, "Time e futebol")
    result = client.put(f"/api/articles/{first['id']}", json={
        "prediction_id": second["prediction_id"], "final_category": second["final_category"],
        "confirmed": True, "expected_revision": first["revision"]})
    assert result.status_code == 409
    assert client.get(f"/api/articles/{first['id']}").json()["title"] == first["title"]


def test_delete_requires_confirmation_and_removes_article_everywhere(client):
    article = create_article(client)
    path = f"/api/articles/{article['id']}"
    payload = {"confirmed": True, "expected_revision": article["revision"]}
    assert client.request("DELETE", path, json={**payload, "confirmed": False}).status_code == 422
    assert client.request("DELETE", path, json={"confirmed": True}).status_code == 422
    assert client.get(path).status_code == 200
    client.app.state.classifier = None
    assert client.request("DELETE", path, json=payload).status_code == 200
    assert client.get(path).status_code == 404
    assert client.get(f"/news/local-{article['id']}").status_code == 404
    assert client.get("/api/articles").json()["total"] == 0
    assert client.get("/api/feedback").json()["total"] == 0
    assert client.get("/?source=editorial").context["total"] == 0
    assert client.get("/?source=demo").context["total"] == 8
    assert client.request("DELETE", path, json=payload).status_code == 404
    assert client.put(path, json={**payload, "prediction_id": article["prediction_id"],
                                 "final_category": article["final_category"]}).status_code == 404


def test_edits_and_removal_survive_restart(trained_dir, tmp_path):
    database = f"sqlite:///{(tmp_path / 'edits.db').as_posix()}"
    with TestClient(create_app(str(trained_dir), database)) as instance:
        article = create_article(instance)
        analysis = instance.post("/api/classify", json={"title": "Futebol e jogo"}).json()
        response = instance.put(f"/api/articles/{article['id']}", json={
            "prediction_id": analysis["prediction_id"], "final_category": analysis["predicted_category"],
            "confirmed": True, "expected_revision": article["revision"]})
        assert response.status_code == 200
    with TestClient(create_app(str(trained_dir), database)) as instance:
        detail = instance.get(f"/api/articles/{article['id']}").json()
        assert detail["title"] == "Futebol e jogo"
        assert instance.request("DELETE", f"/api/articles/{article['id']}", json={
            "confirmed": True, "expected_revision": detail["revision"]}).status_code == 200
    with TestClient(create_app(str(trained_dir), database)) as instance:
        assert instance.get("/api/articles").json()["total"] == 0
