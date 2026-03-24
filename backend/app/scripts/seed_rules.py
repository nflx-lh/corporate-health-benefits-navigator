"""Seed benefit_rules table from CSV into Postgres.

Usage:
    python -m app.scripts.seed_rules
    python -m app.scripts.seed_rules --csv /app/data/rules/benefit_rules.csv

Requires DATABASE_URL env var. Idempotent: upserts by rule_id.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import pathlib
import sys

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("seed_rules")

_DEFAULT_CSV = pathlib.Path(__file__).resolve().parents[3] / "data" / "rules" / "benefit_rules.csv"


def _parse_bool(val: str) -> bool:
    return val.strip().lower() == "true"


def parse_csv(csv_path: pathlib.Path) -> list[dict]:
    """Parse benefit_rules.csv into a list of dicts with typed values."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append({
                "rule_id": row["rule_id"],
                "benefit_type": row["benefit_type"],
                "plan_tier": row["plan_tier"],
                "employment_type": row["employment_type"],
                "tenure_min_months": int(row["tenure_min_months"]),
                "age_min": int(row["age_min"]),
                "age_max": int(row["age_max"]),
                "preauth_required": _parse_bool(row["preauth_required"]),
                "coverage_percent": float(row["coverage_percent"]),
                "annual_limit_sgd": float(row["annual_limit_sgd"]),
                "co_pay_sgd": float(row["co_pay_sgd"]),
                "is_excluded": _parse_bool(row["is_excluded"]),
                "exclusion_reason": row.get("exclusion_reason", ""),
                "required_docs": row.get("required_docs", ""),
                "effective_from": row.get("effective_from", ""),
                "effective_to": row.get("effective_to", ""),
                "service_category": row.get("service_category", ""),
            })
    return rows


def seed(database_url: str, csv_path: pathlib.Path) -> dict:
    """Upsert benefit rules from CSV into Postgres.

    Returns dict with before_count, upserted_count, after_count.
    """
    from app.db.session import Base
    from app.models.rule_db import BenefitRuleDB
    # Register all models so create_all picks them up
    from app.models.employee_db import EmployeeDB  # noqa: F401
    from app.models.password_reset_db import PasswordResetRequestDB  # noqa: F401

    engine = create_engine(database_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if "benefit_rules" not in inspector.get_table_names():
        raise RuntimeError("benefit_rules table does not exist after create_all")

    rows = parse_csv(csv_path)

    with Session() as session:
        before_count = session.query(BenefitRuleDB).count()

        upserted = 0
        for row in rows:
            existing = session.get(BenefitRuleDB, row["rule_id"])
            if existing is None:
                session.add(BenefitRuleDB(**row))
                upserted += 1
            else:
                for key, val in row.items():
                    if key != "rule_id":
                        setattr(existing, key, val)
                upserted += 1

        session.commit()
        after_count = session.query(BenefitRuleDB).count()

    return {
        "before_count": before_count,
        "upserted_count": upserted,
        "after_count": after_count,
    }


def main():
    parser = argparse.ArgumentParser(description="Seed benefit_rules from CSV into Postgres")
    parser.add_argument("--csv", type=str, default=str(_DEFAULT_CSV), help="Path to benefit_rules.csv")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        logger.critical("DATABASE_URL env var is required")
        sys.exit(1)

    csv_path = pathlib.Path(args.csv)
    logger.info("Seeding benefit_rules from %s", csv_path)

    result = seed(database_url, csv_path)
    logger.info(
        "Done: before=%d, upserted=%d, after=%d",
        result["before_count"],
        result["upserted_count"],
        result["after_count"],
    )


if __name__ == "__main__":
    main()
