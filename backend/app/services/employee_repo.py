"""Employee repository – loads and validates employees.csv at import time."""

from __future__ import annotations

import csv
import pathlib
from typing import Optional

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
    return _EMPLOYEES.get(employee_id)


def reload(path: Optional[pathlib.Path] = None) -> None:
    """Re-read CSV (useful for tests)."""
    global _EMPLOYEES
    _EMPLOYEES = _load(path or _DATA_PATH)
