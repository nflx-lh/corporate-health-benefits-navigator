"""Employee repository — lazy CSV loading, REPO_MODE-aware lookups.

REPO_MODE semantics:
  - "csv_only": DB never touched; CSV loaded lazily on first call.
  - "dual" (default): DB-first with CSV fallback on error/empty.
  - "db_only": DB only; raises on DB misconfigured or error.
"""

from __future__ import annotations

import csv
import logging
import os
import pathlib
from typing import Optional

from app.db.session import SessionLocal, REPO_MODE
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
    pathlib.Path(os.getenv("DATA_ROOT", pathlib.Path(__file__).resolve().parents[3] / "data"))
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


# --- Lazy CSV cache (loaded on first access, not at import time) ---

_csv_cache: dict[str, EmployeeRecord] | None = None


def _get_csv() -> dict[str, EmployeeRecord]:
    """Return cached CSV data, loading lazily on first call."""
    global _csv_cache
    if _csv_cache is None:
        _csv_cache = _load(_DATA_PATH)
    return _csv_cache


# --- Public API ---


def get_employee(employee_id: str) -> Optional[EmployeeRecord]:
    """Lookup employee by ID, respecting REPO_MODE."""

    if REPO_MODE == "csv_only":
        return _get_csv().get(employee_id)

    if REPO_MODE == "db_only":
        if SessionLocal is None:
            raise RuntimeError(
                "REPO_MODE=db_only but database is not configured "
                "(DATABASE_URL missing or empty)"
            )
        with SessionLocal() as session:
            row = session.get(EmployeeDB, employee_id)
            return _db_to_record(row) if row is not None else None

    # --- dual mode (default) ---

    if SessionLocal is None:
        # DB not configured — silent CSV fallback (expected in dev/test)
        return _get_csv().get(employee_id)

    try:
        with SessionLocal() as session:
            row = session.get(EmployeeDB, employee_id)
            if row is not None:
                return _db_to_record(row)

            # DB returned nothing — check CSV for fallback
            csv_data = _get_csv()
            if employee_id in csv_data:
                logger.warning(
                    {
                        "event": FALLBACK_EVENT,
                        "repo": "employee_repo",
                        "reason": "db_empty",
                    }
                )
                return csv_data[employee_id]
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
        return _get_csv().get(employee_id)


def reload(path: Optional[pathlib.Path] = None) -> None:
    """Re-read CSV (useful for tests)."""
    global _csv_cache
    _csv_cache = _load(path or _DATA_PATH)
