from fastapi.testclient import TestClient
import pytest
from src.api.main import create_app


@pytest.fixture
def client(trained_dir, tmp_path):
    with TestClient(create_app(str(trained_dir), f"sqlite:///{(tmp_path / 'test.db').as_posix()}")) as instance:
        yield instance


def test_health_and_pages(client):
    assert client.get("/health").json()["model_loaded"] is True
    for path in ("/", "/history", "/static/css/app.css", "/static/js/app.js"):
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
