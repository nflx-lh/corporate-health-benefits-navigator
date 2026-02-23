"""Benefit-rules repository — lazy CSV loading, REPO_MODE-aware lookups.

REPO_MODE semantics:
  - "csv_only": DB never touched; CSV loaded lazily on first call.
  - "dual" (default): DB-first with CSV fallback on error/empty.
  - "db_only": DB only; raises on DB misconfigured or error.
"""

from __future__ import annotations

import csv
import logging
import pathlib
from dataclasses import dataclass, field
from typing import Optional

from app.db.session import SessionLocal, REPO_MODE
from app.models.rule_db import BenefitRuleDB

logger = logging.getLogger(__name__)

FALLBACK_EVENT = "repo_fallback_csv"

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


def _db_to_rule(row: BenefitRuleDB) -> BenefitRule:
    """Convert a DB row to a BenefitRule dataclass, matching CSV semantics exactly."""
    docs_raw = row.required_docs or ""
    docs = [d.strip() for d in docs_raw.split(";") if d.strip()] if docs_raw else []
    return BenefitRule(
        rule_id=row.rule_id,
        benefit_type=row.benefit_type,
        plan_tier=row.plan_tier,
        employment_type=row.employment_type,
        tenure_min_months=int(row.tenure_min_months),
        age_min=int(row.age_min),
        age_max=int(row.age_max),
        preauth_required=bool(row.preauth_required),
        coverage_percent=float(row.coverage_percent),
        annual_limit_sgd=float(row.annual_limit_sgd),
        co_pay_sgd=float(row.co_pay_sgd),
        is_excluded=bool(row.is_excluded),
        exclusion_reason=row.exclusion_reason or "",
        required_docs=docs,
        effective_from=row.effective_from or "",
        effective_to=row.effective_to or "",
        service_category=row.service_category or "",
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


# --- Lazy CSV cache (loaded on first access, not at import time) ---

_csv_cache: list[BenefitRule] | None = None


def _get_csv() -> list[BenefitRule]:
    """Return cached CSV data, loading lazily on first call."""
    global _csv_cache
    if _csv_cache is None:
        _csv_cache = _load(_DATA_PATH)
    return _csv_cache


# --- Public API ---


def get_rules() -> list[BenefitRule]:
    """Return all rules, respecting REPO_MODE.

    DB ordering: ORDER BY rule_id ASC — preserves CSV iteration order
    (R001..R043 zero-padded) for deterministic precedence behaviour.
    """

    if REPO_MODE == "csv_only":
        return _get_csv()

    if REPO_MODE == "db_only":
        if SessionLocal is None:
            raise RuntimeError(
                "REPO_MODE=db_only but database is not configured "
                "(DATABASE_URL missing or empty)"
            )
        with SessionLocal() as session:
            rows = (
                session.query(BenefitRuleDB)
                .order_by(BenefitRuleDB.rule_id)
                .all()
            )
            return [_db_to_rule(r) for r in rows]

    # --- dual mode (default) ---

    if SessionLocal is None:
        # DB not configured — silent CSV fallback (expected in dev/test)
        return _get_csv()

    try:
        with SessionLocal() as session:
            rows = (
                session.query(BenefitRuleDB)
                .order_by(BenefitRuleDB.rule_id)
                .all()
            )
            if rows:
                return [_db_to_rule(r) for r in rows]
            # DB connected but table empty -> fallback
            logger.warning(
                {
                    "event": FALLBACK_EVENT,
                    "repo": "rule_repo",
                    "reason": "db_empty",
                }
            )
    except Exception as exc:
        logger.warning(
            {
                "event": FALLBACK_EVENT,
                "repo": "rule_repo",
                "reason": "db_error",
                "exception_type": type(exc).__name__,
            }
        )

    return _get_csv()


def reload(path: Optional[pathlib.Path] = None) -> None:
    """Re-read CSV (useful for tests)."""
    global _csv_cache
    _csv_cache = _load(path or _DATA_PATH)
