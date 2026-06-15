from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


def make_engine():
    settings = get_settings()
    database_url = normalize_sync_database_url(settings.database_url)
    return create_engine(database_url, future=True, pool_pre_ping=True, **_engine_kwargs(database_url))


def normalize_sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return database_url


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def reset_engine() -> None:
    global engine, SessionLocal
    engine.dispose()
    engine = make_engine()
    SessionLocal.configure(bind=engine)


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    import app.models  # noqa: F401

    if engine.dialect.name != "sqlite":
        return
    Base.metadata.create_all(bind=engine)
