"""SQLAlchemy model for anonymous query logging (B-1703 HR Analytics)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.db.session import Base


class QueryLogDB(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    benefit_type = Column(String, nullable=True)
    service_category = Column(String, nullable=True)
    decision = Column(String, nullable=True)
    response_language = Column(String, nullable=True, default="en")
    logged_at = Column(DateTime, default=datetime.utcnow, nullable=False)
