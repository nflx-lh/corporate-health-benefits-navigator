"""Database initialisation for cloud/demo mode.

Called once on startup when DATABASE_URL is configured and REPO_MODE != csv_only.
Creates tables (idempotent) and seeds from CSV if tables are empty.
"""

from __future__ import annotations

import csv
import logging
import os
import pathlib

from app.db.session import engine, SessionLocal, Base
from app.models.employee_db import EmployeeDB
from app.models.rule_db import BenefitRuleDB
from app.models.password_reset_db import PasswordResetRequestDB  # noqa: F401 — register model
from app.models.query_log_db import QueryLogDB  # noqa: F401 — register model (Phase 17 analytics)

logger = logging.getLogger(__name__)

_DATA_ROOT = pathlib.Path(os.environ["DATA_ROOT"]) if "DATA_ROOT" in os.environ else pathlib.Path(__file__).resolve().parents[3] / "data"


def _safe_int(val: str | None) -> int | None:
    if val is None or val.strip() == "":
        return None
    return int(val)


def _parse_bool(val: str) -> bool:
    return val.strip().lower() == "true"


def _seed_employees(session) -> int:
    """Seed employees table from CSV. Returns count inserted."""
    if session.query(EmployeeDB).first() is not None:
        return 0

    csv_path = _DATA_ROOT / "fixtures" / "employees.csv"
    if not csv_path.exists():
        logger.warning("employees.csv not found at %s — skipping seed", csv_path)
        return 0

    count = 0
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            session.add(EmployeeDB(
                employee_id=row["employee_id"],
                name=row.get("name") or None,
                age=_safe_int(row.get("age")),
                employment_type=row.get("employment_type") or None,
                plan_tier=row.get("plan_tier") or None,
                tenure_months=_safe_int(row.get("tenure_months")),
                dependents_count=_safe_int(row.get("dependents_count")) or 0,
                is_active=row.get("is_active", "").strip().lower() == "true",
            ))
            count += 1
    session.commit()
    return count


def _seed_rules(session) -> int:
    """Seed benefit_rules table from CSV. Returns count inserted."""
    if session.query(BenefitRuleDB).first() is not None:
        return 0

    csv_path = _DATA_ROOT / "rules" / "benefit_rules.csv"
    if not csv_path.exists():
        logger.warning("benefit_rules.csv not found at %s — skipping seed", csv_path)
        return 0

    count = 0
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            session.add(BenefitRuleDB(
                rule_id=row["rule_id"],
                benefit_type=row["benefit_type"],
                plan_tier=row["plan_tier"],
                employment_type=row["employment_type"],
                tenure_min_months=int(row["tenure_min_months"]),
                age_min=int(row["age_min"]),
                age_max=int(row["age_max"]),
                preauth_required=_parse_bool(row["preauth_required"]),
                coverage_percent=float(row["coverage_percent"]),
                annual_limit_sgd=float(row["annual_limit_sgd"]),
                co_pay_sgd=float(row["co_pay_sgd"]),
                is_excluded=_parse_bool(row["is_excluded"]),
                exclusion_reason=row.get("exclusion_reason", ""),
                required_docs=row.get("required_docs", ""),
                effective_from=row.get("effective_from", ""),
                effective_to=row.get("effective_to", ""),
                service_category=row.get("service_category", ""),
            ))
            count += 1
    session.commit()
    return count


def init_db() -> None:
    """Create tables and seed data. Safe to call multiple times."""
    if engine is None or SessionLocal is None:
        return

    logger.info("Initialising database tables …")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        emp_count = _seed_employees(session)
        rule_count = _seed_rules(session)

    if emp_count or rule_count:
        logger.info("Seeded DB: %d employees, %d rules", emp_count, rule_count)
    else:
        logger.info("DB tables already populated — skipping seed")
