"""SQLAlchemy model for the employees table."""

from __future__ import annotations

from sqlalchemy import Column, String, Integer, Boolean

from app.db.session import Base


class EmployeeDB(Base):
    __tablename__ = "employees"

    employee_id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    employment_type = Column(String, nullable=True)
    plan_tier = Column(String, nullable=True)
    tenure_months = Column(Integer, nullable=True)
    dependents_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    password_hash = Column(String, nullable=True)
    must_reset_password = Column(Boolean, nullable=False, default=False)
