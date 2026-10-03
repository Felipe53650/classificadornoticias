from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.db.database import Base


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    predicted_category: Mapped[str] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(100))
    top_k: Mapped[list] = mapped_column(JSON)
    categories: Mapped[list] = mapped_column(JSON)
    demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[str] = mapped_column(ForeignKey("predictions.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    predicted_category: Mapped[str] = mapped_column(String(100))
    predicted_confidence: Mapped[float] = mapped_column(Float)
    final_category: Mapped[str] = mapped_column(String(100))
    was_corrected: Mapped[bool] = mapped_column(Boolean)
    model_version: Mapped[str] = mapped_column(String(100))
    demo: Mapped[bool] = mapped_column(Boolean, default=False)
