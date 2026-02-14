"""Idempotent seed: load employees.csv into the employees table.

Usage:
    DATABASE_URL=postgresql://... python scripts/seed_employees.py

Behaviour:
    - Upserts by employee_id (insert or update).
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

from app.models.employee_db import EmployeeDB  # noqa: E402
from app.db.session import Base  # noqa: E402

CSV_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "fixtures" / "employees.csv"

REQUIRED_COLUMNS = {
    "employee_id", "name", "age", "employment_type",
    "plan_tier", "tenure_months", "dependents_count", "is_active",
}


def _safe_int(val: str | None) -> int | None:
    if val is None or val.strip() == "":
        return None
    return int(val)


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
                eid = row.get("employee_id", "").strip()
                if not eid:
                    skipped += 1
                    continue

                vals = {
                    "employee_id": eid,
                    "name": row.get("name") or None,
                    "age": _safe_int(row.get("age")),
                    "employment_type": row.get("employment_type") or None,
                    "plan_tier": row.get("plan_tier") or None,
                    "tenure_months": _safe_int(row.get("tenure_months")),
                    "dependents_count": _safe_int(row.get("dependents_count")) or 0,
                    "is_active": row.get("is_active", "").strip().lower() == "true",
                }

                existing = session.get(EmployeeDB, eid)
                if existing is None:
                    session.add(EmployeeDB(**vals))
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
