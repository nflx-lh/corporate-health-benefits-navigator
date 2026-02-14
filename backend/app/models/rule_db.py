"""SQLAlchemy model for the benefit_rules table."""

from __future__ import annotations

from sqlalchemy import Column, String, Integer, Float, Boolean, Text

from app.db.session import Base


class BenefitRuleDB(Base):
    __tablename__ = "benefit_rules"

    rule_id = Column(String, primary_key=True)
    benefit_type = Column(String, nullable=False)
    plan_tier = Column(String, nullable=False)
    employment_type = Column(String, nullable=False)
    tenure_min_months = Column(Integer, nullable=False)
    age_min = Column(Integer, nullable=False)
    age_max = Column(Integer, nullable=False)
    preauth_required = Column(Boolean, nullable=False)
    coverage_percent = Column(Float, nullable=False)
    annual_limit_sgd = Column(Float, nullable=False)
    co_pay_sgd = Column(Float, nullable=False)
    is_excluded = Column(Boolean, nullable=False)
    exclusion_reason = Column(Text, nullable=False, server_default="")
    # Stored as semicolon-delimited string, parsed in repo layer
    required_docs = Column(Text, nullable=False, server_default="")
    effective_from = Column(String, nullable=False, server_default="")
    effective_to = Column(String, nullable=False, server_default="")
    service_category = Column(String, nullable=False, server_default="")
