"""Idempotent seed: load benefit_rules.csv into the benefit_rules table.

Usage:
    DATABASE_URL=postgresql://... python scripts/seed_rules.py

Behaviour:
    - Upserts by rule_id (insert or update).
    - Fully transactional — rolls back on any failure.
    - Prints inserted / updated / skipped counts.
    - Exits non-zero on parse/schema errors.
"""

from __future__ import annotations

import csv
import os
import pathlib
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Add backend to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.models.rule_db import BenefitRuleDB  # noqa: E402
from app.db.session import Base  # noqa: E402

CSV_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "rules" / "benefit_rules.csv"

REQUIRED_COLUMNS = {
    "rule_id", "benefit_type", "plan_tier", "employment_type",
    "tenure_min_months", "age_min", "age_max", "preauth_required",
    "coverage_percent", "annual_limit_sgd", "co_pay_sgd", "is_excluded",
    "exclusion_reason", "required_docs", "effective_from", "effective_to",
    "service_category",
}


def _parse_bool(val: str) -> bool:
    return val.strip().lower() == "true"


def seed(database_url: str) -> None:
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    # Read and validate CSV
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        actual = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - actual
        if missing:
            print(f"ERROR: CSV schema validation failed — missing columns: {sorted(missing)}", file=sys.stderr)
            sys.exit(1)
        rows = list(reader)

    inserted = 0
    updated = 0
    skipped = 0

    with Session(engine) as session:
        try:
            for row in rows:
                rid = row.get("rule_id", "").strip()
                if not rid:
                    skipped += 1
                    continue

                vals = {
                    "rule_id": rid,
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
                    "required_docs": row.get("required_docs", "").strip(),
                    "effective_from": row.get("effective_from", ""),
                    "effective_to": row.get("effective_to", ""),
                    "service_category": row.get("service_category", ""),
                }

                existing = session.get(BenefitRuleDB, rid)
                if existing is None:
                    session.add(BenefitRuleDB(**vals))
                    inserted += 1
                else:
                    changed = False
                    for k, v in vals.items():
                        if getattr(existing, k) != v:
                            setattr(existing, k, v)
                            changed = True
                    if changed:
                        updated += 1
                    else:
                        skipped += 1

            session.commit()
        except Exception as exc:
            session.rollback()
            print(f"ERROR: Seed failed, rolled back — {exc}", file=sys.stderr)
            sys.exit(1)

    print(f"Seed complete: {inserted} inserted, {updated} updated, {skipped} skipped.")


if __name__ == "__main__":
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    seed(url)
