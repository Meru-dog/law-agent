"""Database engine and session factory.

Provides helpers to build a SQLAlchemy engine and session factory from settings.
"""

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings


def build_engine(settings: Settings) -> Engine:
    """Create a SQLAlchemy engine from application settings.

    Adds ``check_same_thread=False`` for SQLite URLs so that FastAPI's
    threaded request handling works correctly.
    """
    connect_args: dict = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(settings.database_url, connect_args=connect_args)


def init_pgvector(engine: Engine) -> None:
    """Initialize pgvector extension for PostgreSQL.

    This should be called after engine creation but before creating tables.
    Safe to call on SQLite (no-op).

    Args:
        engine: SQLAlchemy engine instance.
    """
    if not engine.url.drivername.startswith("postgresql"):
        return

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a session factory bound to *engine*.

    Sessions created by this factory use ``expire_on_commit=False`` so that
    attributes remain accessible after commit without triggering lazy loads.
    """
    return sessionmaker(bind=engine, expire_on_commit=False)
