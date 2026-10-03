"""Aplicação local editorial com confirmação humana obrigatória."""
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from src.api.schemas import ClassifyRequest, SaveArticleRequest
from src.db.database import create_database
from src.db.models import Article, Prediction
from src.ml.inference import NewsClassifier

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

    @app.get("/")
    def index(request: Request):
        return templates.TemplateResponse(request=request, name="index.html", context={"page": "editor"})

    @app.get("/history")
    def history(request: Request):
        return templates.TemplateResponse(request=request, name="history.html", context={"page": "history"})

    return app


def serialize_article(article: Article) -> dict:
    return {c.name: getattr(article, c.name) for c in Article.__table__.columns}


app = create_app()
