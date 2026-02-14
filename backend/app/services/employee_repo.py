"""Employee repository – loads employees.csv at import time, with optional
DB-first lookup when DATABASE_URL is configured and REPO_MODE != csv_only.

Dual-read contract:
  - DB-first: query Postgres by employee_id.
  - CSV fallback: if DB unavailable, empty, or errored.
  - Structured warning on fallback (see FALLBACK_EVENT).
"""

from __future__ import annotations

import csv
import logging
import pathlib
from typing import Optional

from app.db.session import SessionLocal
from app.models.employee_db import EmployeeDB

logger = logging.getLogger(__name__)

FALLBACK_EVENT = "repo_fallback_csv"

REQUIRED_COLUMNS = {
    "employee_id",
    "name",
    "age",
    "employment_type",
    "plan_tier",
    "tenure_months",
    "dependents_count",
    "is_active",
}

_DATA_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "data"
    / "fixtures"
    / "employees.csv"
)


class EmployeeRecord:
    __slots__ = (
        "employee_id",
        "name",
        "age",
        "employment_type",
        "plan_tier",
        "tenure_months",
        "dependents_count",
        "is_active",
    )

    def __init__(self, row: dict[str, str]) -> None:
        self.employee_id: str = row["employee_id"]
        self.name: Optional[str] = row.get("name") or None
        self.age: Optional[int] = _safe_int(row.get("age"))
        self.employment_type: Optional[str] = row.get("employment_type") or None
        self.plan_tier: Optional[str] = row.get("plan_tier") or None
        self.tenure_months: Optional[int] = _safe_int(row.get("tenure_months"))
        self.dependents_count: int = _safe_int(row.get("dependents_count")) or 0
        self.is_active: bool = row.get("is_active", "").strip().lower() == "true"


def _safe_int(val: Optional[str]) -> Optional[int]:
    if val is None or val.strip() == "":
        return None
    return int(val)


def _db_to_record(row: EmployeeDB) -> EmployeeRecord:
    """Convert a DB row to an EmployeeRecord, matching CSV semantics exactly."""
    rec = object.__new__(EmployeeRecord)
    rec.employee_id = row.employee_id
    rec.name = row.name if row.name else None
    rec.age = row.age  # already Optional[int]
    rec.employment_type = row.employment_type if row.employment_type else None
    rec.plan_tier = row.plan_tier if row.plan_tier else None
    rec.tenure_months = row.tenure_months  # already Optional[int]
    rec.dependents_count = row.dependents_count if row.dependents_count is not None else 0
    rec.is_active = bool(row.is_active)
    return rec


def _load(path: pathlib.Path) -> dict[str, EmployeeRecord]:
    if not path.exists():
        raise FileNotFoundError(f"Employee data file not found: {path}")

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        actual = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - actual
        if missing:
            raise ValueError(
                f"employees.csv schema validation failed – missing columns: {sorted(missing)}"
            )
        records: dict[str, EmployeeRecord] = {}
        for row in reader:
            rec = EmployeeRecord(row)
            records[rec.employee_id] = rec
    return records


_EMPLOYEES: dict[str, EmployeeRecord] = _load(_DATA_PATH)


def get_employee(employee_id: str) -> Optional[EmployeeRecord]:
    """Lookup employee by ID. DB-first with CSV fallback."""
    if SessionLocal is not None:
        try:
            with SessionLocal() as session:
                row = session.get(EmployeeDB, employee_id)
                if row is not None:
                    return _db_to_record(row)
                # Employee not in DB — return None (not a fallback scenario)
                return None
        except Exception as exc:
            logger.warning(
                {
                    "event": FALLBACK_EVENT,
                    "repo": "employee_repo",
                    "reason": "db_error",
                    "exception_type": type(exc).__name__,
                }
            )
    # CSV fallback
    return _EMPLOYEES.get(employee_id)


def reload(path: Optional[pathlib.Path] = None) -> None:
    """Re-read CSV (useful for tests)."""
    global _EMPLOYEES
    _EMPLOYEES = _load(path or _DATA_PATH)
