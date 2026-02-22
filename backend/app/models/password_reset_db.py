"""SQLAlchemy model for the password_reset_requests table."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime

from app.db.session import Base


class PasswordResetRequestDB(Base):
    __tablename__ = "password_reset_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    requested_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
    notes = Column(String, nullable=True)
