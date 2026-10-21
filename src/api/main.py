"""Aplicação local editorial com confirmação humana obrigatória."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlencode
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from src.api.schemas import ClassifyRequest, DeleteArticleRequest, SaveArticleRequest, UpdateArticleRequest
from src.db.database import create_database
from src.db.models import Article, Prediction
from src.ml.inference import NewsClassifier
from src.web.feed import FeedSource, article_view, demo_stories, get_feed

ROOT = Path(__file__).resolve().parents[2]


def create_app(model_dir: str | None = None, database_url: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine, app.state.sessions = create_database(database_url or os.getenv("DATABASE_URL", "sqlite:///./editorial.db"))
        app.state.classifier = None
        try:
            app.state.classifier = NewsClassifier(model_dir or os.getenv("MODEL_DIR", str(ROOT / "models/production")))
        except Exception:
            logging.getLogger(__name__).exception("Modelo indisponível; consulte o README para treinar ou iniciar a demonstração.")
        yield
        app.state.engine.dispose()

    app = FastAPI(title="Pauta · Assistente editorial", lifespan=lifespan)
    templates = Jinja2Templates(directory=str(ROOT / "src/web/templates"))
    app.mount("/static", StaticFiles(directory=str(ROOT / "src/web/static")), name="static")
    high, medium = float(os.getenv("CONFIDENCE_HIGH", ".85")), float(os.getenv("CONFIDENCE_MEDIUM", ".65"))
    if not 0 <= medium <= high <= 1:
        raise ValueError("Limiares de confiança devem satisfazer 0 <= medium <= high <= 1.")

    @app.get("/health")
    def health():
        classifier = app.state.classifier
        return {"status": "ok" if classifier else "degraded", "model_loaded": classifier is not None,
                "model_version": classifier.metadata["version"] if classifier else None,
                "demo": classifier.metadata.get("demo", False) if classifier else False}

    @app.get("/api/categories")
    def categories():
        classifier = app.state.classifier
        return {"categories": classifier.categories if classifier else [], "thresholds": {"high": high, "medium": medium}}

    @app.post("/api/classify")
    def classify(payload: ClassifyRequest):
        classifier = app.state.classifier
        if classifier is None:
            raise HTTPException(503, "Modelo não carregado. Configure MODEL_DIR e reinicie a aplicação.")
        result = classifier.predict(payload.title, payload.content)
        prediction_id = str(uuid4())
        with app.state.sessions() as session:
            session.add(Prediction(id=prediction_id, title=payload.title, content=payload.content, **result,
                                   categories=classifier.categories, demo=classifier.metadata.get("demo", False)))
            session.commit()
        return {**result, "prediction_id": prediction_id}

    @app.post("/api/articles", status_code=201)
    def save_article(payload: SaveArticleRequest):
        if not payload.confirmed:
            raise HTTPException(422, "Confirme a decisão editorial antes de salvar.")
        with app.state.sessions() as session:
            prediction = session.get(Prediction, payload.prediction_id)
            if prediction is None:
                raise HTTPException(404, "Previsão não encontrada. Analise a notícia novamente.")
            if payload.final_category not in prediction.categories:
                raise HTTPException(422, "Categoria final desconhecida.")
            article = Article(prediction_id=prediction.id, title=prediction.title, content=prediction.content,
                              predicted_category=prediction.predicted_category, predicted_confidence=prediction.confidence,
                              final_category=payload.final_category, was_corrected=prediction.predicted_category != payload.final_category,
                              model_version=prediction.model_version, demo=prediction.demo)
            session.add(article)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(409, "Esta previsão já foi salva.") from None
            return serialize_article(article)

    @app.get("/api/articles")
    def articles(category: str | None = None, was_corrected: bool | None = None,
                 offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
        filters = []
        if category:
            filters.append(Article.final_category == category)
        if was_corrected is not None:
            filters.append(Article.was_corrected == was_corrected)
        with app.state.sessions() as session:
            total = session.scalar(select(func.count()).select_from(Article).where(*filters))
            items = session.scalars(select(Article).where(*filters).order_by(Article.id.desc()).offset(offset).limit(limit)).all()
            return {"items": [serialize_article(a) for a in items], "total": total, "offset": offset, "limit": limit}

    @app.get("/api/feedback")
    def feedback():
        with app.state.sessions() as session:
            groups = session.execute(select(Article.predicted_category, Article.final_category, func.count()).group_by(Article.predicted_category, Article.final_category)).all()
            total = sum(n for _, _, n in groups)
            corrections = sum(n for a, b, n in groups if a != b)
            return {"total": total, "corrections": corrections, "acceptance_rate": (total - corrections) / total if total else None,
                    "pairs": [{"predicted": a, "final": b, "count": n} for a, b, n in groups]}

    @app.get("/api/articles/{article_id}")
    def article_detail(article_id: int):
        with app.state.sessions() as session:
            article = session.get(Article, article_id)
            if article is None:
                raise HTTPException(404, "Notícia não encontrada. Atualize o histórico.")
            prediction = session.get(Prediction, article.prediction_id)
            return {**serialize_article(article), "categories": prediction.categories,
                    "analysis": {"prediction_id": prediction.id,
                                 "predicted_category": prediction.predicted_category,
                                 "confidence": prediction.confidence, "top_k": prediction.top_k,
                                 "model_version": prediction.model_version}}

    @app.put("/api/articles/{article_id}")
    def update_article(article_id: int, payload: UpdateArticleRequest):
        if not payload.confirmed:
            raise HTTPException(422, "Confirme a decisão editorial antes de salvar.")
        with app.state.sessions() as session:
            article = session.get(Article, article_id)
            if article is None:
                raise HTTPException(404, "Notícia não encontrada. Atualize o histórico.")
            if serialize_article(article)["revision"] != payload.expected_revision:
                raise HTTPException(409, "Esta notícia foi alterada. Reabra a edição pelo histórico.")
            prediction = session.get(Prediction, payload.prediction_id)
            if prediction is None:
                raise HTTPException(404, "Previsão não encontrada. Analise a notícia novamente.")
            if payload.final_category not in prediction.categories:
                raise HTTPException(422, "Categoria final desconhecida.")
            # Texto e metadados vêm da mesma análise persistida, nunca do cliente.
            values = dict(prediction_id=prediction.id, title=prediction.title, content=prediction.content,
                          predicted_category=prediction.predicted_category, predicted_confidence=prediction.confidence,
                          final_category=payload.final_category,
                          was_corrected=prediction.predicted_category != payload.final_category,
                          model_version=prediction.model_version, demo=prediction.demo)
            try:
                result = session.execute(update(Article).where(
                    Article.id == article_id, Article.prediction_id == article.prediction_id,
                    Article.final_category == article.final_category).values(**values))
                if result.rowcount != 1:
                    raise HTTPException(409, "Esta notícia foi alterada. Reabra a edição pelo histórico.")
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(409, "Esta análise já está vinculada a outra notícia.") from None
            session.refresh(article)
            return serialize_article(article)

    @app.delete("/api/articles/{article_id}")
    def delete_article(article_id: int, payload: DeleteArticleRequest):
        if not payload.confirmed:
            raise HTTPException(422, "Confirme a remoção da notícia.")
        with app.state.sessions() as session:
            article = session.get(Article, article_id)
            if article is None:
                raise HTTPException(404, "Notícia não encontrada. Atualize o histórico.")
            if serialize_article(article)["revision"] != payload.expected_revision:
                raise HTTPException(409, "Esta notícia foi alterada. Atualize o histórico antes de remover.")
            result = session.execute(delete(Article).where(
                Article.id == article_id, Article.prediction_id == article.prediction_id,
                Article.final_category == article.final_category))
            if result.rowcount != 1:
                raise HTTPException(409, "Esta notícia foi alterada. Atualize o histórico antes de remover.")
            session.commit()
            return {"deleted": True, "id": article_id}

    @app.get("/")
    def index(request: Request, category: str = Query("", max_length=100),
              q: str = Query("", max_length=200), source: FeedSource = "all", p: int = Query(1, ge=1)):
        q = q.strip()
        with app.state.sessions() as session:
            feed = get_feed(session, category=category, q=q, source=source, page=p)

        def feed_url(**changes):
            params = {"category": category, "q": q, "source": source, **changes}
            return "/?" + urlencode({key: value for key, value in params.items() if value != ""})

        return templates.TemplateResponse(request=request, name="feed.html", context={
            "page": "feed", **feed, "category": category, "q": q, "source": source, "feed_url": feed_url})

    @app.get("/news/{key}")
    def read_article(request: Request, key: str):
        story = next((item for item in demo_stories() if item["key"] == key), None)
        if key.startswith("local-") and key[6:].isascii() and key[6:].isdigit() and len(key[6:]) <= 18:
            with app.state.sessions() as session:
                article = session.get(Article, int(key[6:]))
                if article:
                    story = article_view(article)
        if story is None:
            return templates.TemplateResponse(request=request, name="news_missing.html",
                                              context={"page": "feed"}, status_code=404)
        return templates.TemplateResponse(request=request, name="news.html", context={
            "page": "feed", "story": story, "category_url": "/?" + urlencode({"category": story["category"]})})

    @app.get("/editor")
    def editor(request: Request, article: int | None = Query(None, ge=1)):
        return templates.TemplateResponse(request=request, name="index.html", context={"page": "editor", "editing": article})

    @app.get("/history")
    def history(request: Request):
        return templates.TemplateResponse(request=request, name="history.html", context={"page": "history"})

    return app


def serialize_article(article: Article) -> dict:
    data = {c.name: getattr(article, c.name) for c in Article.__table__.columns}
    data = {key: (value.replace(tzinfo=value.tzinfo or timezone.utc)
                  if isinstance(value, datetime) else value) for key, value in data.items()}
    canonical = {key: (value.isoformat() if isinstance(value, datetime) else value) for key, value in data.items()}
    data["revision"] = hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return data


app = create_app()
