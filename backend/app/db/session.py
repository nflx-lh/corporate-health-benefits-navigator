"""SQLAlchemy engine and session factory.

REPO_MODE controls data access strategy:
  - "csv_only": engine and SessionLocal are None — pure CSV, no DB.
  - "dual" (default): DB-first with CSV fallback.
      Engine created only when DATABASE_URL is set.
  - "db_only": DB required.
      Engine created only when DATABASE_URL is set; repos raise at
      runtime if SessionLocal is None.
"""

from __future__ import annotations

import logging
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

logger = logging.getLogger(__name__)

DATABASE_URL: str = os.getenv("DATABASE_URL", "")
REPO_MODE: str = os.getenv("REPO_MODE", "dual")

# Fail fast: db_only mode requires a valid DATABASE_URL
if REPO_MODE == "db_only" and not DATABASE_URL:
    logger.critical("REPO_MODE=db_only but DATABASE_URL is not set — cannot start")
    sys.exit(1)

_db_enabled = bool(DATABASE_URL) and REPO_MODE != "csv_only"

engine = create_engine(DATABASE_URL, pool_pre_ping=True) if _db_enabled else None

SessionLocal = sessionmaker(bind=engine) if engine is not None else None


class Base(DeclarativeBase):
    pass
