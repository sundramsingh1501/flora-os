"""
Flora OS — Database Setup
SQLAlchemy engine, session factory, and base model.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import os
from app.config import settings

logger = logging.getLogger(__name__)

# Ensure parent directory exists (important for /data/flora_os.db on HF Spaces)
if settings.database_url.startswith("sqlite:///"):
    _db_path = settings.database_url.replace("sqlite:///", "").replace("sqlite://", "")
    if _db_path and not _db_path.startswith(":"):
        os.makedirs(os.path.dirname(os.path.abspath(_db_path)), exist_ok=True)

# SQLite needs WAL mode for concurrent reads
_connect_args = {}
if settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    pool_timeout=30,
    echo=settings.is_development,
)

# Enable WAL for SQLite
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=10000")   # wait up to 10s instead of failing
        cursor.execute("PRAGMA synchronous=NORMAL")   # faster writes, still safe with WAL
        cursor.close()

# expire_on_commit=False keeps attributes accessible after the session closes,
# which is required when objects are used outside the with-get_db() block.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for database sessions with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called once at startup."""
    from app import models  # noqa: F401 — registers models with Base
    Base.metadata.create_all(bind=engine)
    logger.info("Flora OS database initialized.")
