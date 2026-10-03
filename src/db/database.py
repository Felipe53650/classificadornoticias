from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def create_database(url: str):
    options = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    if url in ("sqlite://", "sqlite:///:memory:"):
        options["poolclass"] = StaticPool
    engine = create_engine(url, **options)
    from src.db import models  # Registra tabelas antes de create_all.
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)
