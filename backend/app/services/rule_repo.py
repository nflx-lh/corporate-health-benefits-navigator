"""Benefit-rules repository – loads and validates benefit_rules.csv at import time."""

from __future__ import annotations

import csv
import pathlib
from dataclasses import dataclass, field
from typing import Optional

REQUIRED_COLUMNS = {
    "rule_id",
    "benefit_type",
    "plan_tier",
    "employment_type",
    "tenure_min_months",
    "age_min",
    "age_max",
    "preauth_required",
    "coverage_percent",
    "annual_limit_sgd",
    "co_pay_sgd",
    "is_excluded",
    "exclusion_reason",
    "required_docs",
    "effective_from",
    "effective_to",
    "service_category",
}

_DATA_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "data"
    / "rules"
    / "benefit_rules.csv"
)


@dataclass
class BenefitRule:
    rule_id: str
    benefit_type: str
    plan_tier: str
    employment_type: str
    tenure_min_months: int
    age_min: int
    age_max: int
    preauth_required: bool
    coverage_percent: float
    annual_limit_sgd: float
    co_pay_sgd: float
    is_excluded: bool
    exclusion_reason: str
    required_docs: list[str] = field(default_factory=list)
    effective_from: str = ""
    effective_to: str = ""
    service_category: str = ""


def _parse_bool(val: str) -> bool:
    return val.strip().lower() == "true"


def _parse_rule(row: dict[str, str]) -> BenefitRule:
    docs_raw = row.get("required_docs", "").strip()
    docs = [d.strip() for d in docs_raw.split(";") if d.strip()] if docs_raw else []
    return BenefitRule(
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
        required_docs=docs,
        effective_from=row.get("effective_from", ""),
        effective_to=row.get("effective_to", ""),
        service_category=row.get("service_category", ""),
    )


def _load(path: pathlib.Path) -> list[BenefitRule]:
    if not path.exists():
        raise FileNotFoundError(f"Benefit rules file not found: {path}")

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        actual = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - actual
        if missing:
            raise ValueError(
                f"benefit_rules.csv schema validation failed – missing columns: {sorted(missing)}"
            )
        return [_parse_rule(row) for row in reader]


_RULES: list[BenefitRule] = _load(_DATA_PATH)


def get_rules() -> list[BenefitRule]:
    return _RULES


def reload(path: Optional[pathlib.Path] = None) -> None:
    """Re-read CSV (useful for tests)."""
    global _RULES
    _RULES = _load(path or _DATA_PATH)
