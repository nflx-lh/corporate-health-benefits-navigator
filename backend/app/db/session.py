"""SQLAlchemy engine and session factory.

When DATABASE_URL is empty or REPO_MODE is csv_only, engine and SessionLocal
are None — the app runs in pure-CSV mode without any DB dependency.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_DATABASE_URL: str = os.getenv("DATABASE_URL", "")
_REPO_MODE: str = os.getenv("REPO_MODE", "db_first")

_db_enabled = bool(_DATABASE_URL) and _REPO_MODE != "csv_only"

engine = create_engine(_DATABASE_URL, pool_pre_ping=True) if _db_enabled else None

SessionLocal = sessionmaker(bind=engine) if engine is not None else None


class Base(DeclarativeBase):
    pass
