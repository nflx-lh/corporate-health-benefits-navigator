"""Analytics service for HR dashboard (B-1703).

Logs anonymous query events and aggregates stats for the admin analytics tab.
Degrades gracefully when running in csv_only mode (no DB).
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def log_query(
    benefit_type: str | None,
    service_category: str | None,
    decision: str | None,
    response_language: str | None = "en",
) -> None:
    """Persist an anonymous query log entry. Silent on failure."""
    try:
        from app.db.session import SessionLocal
        from app.models.query_log_db import QueryLogDB  # noqa: F401 — ensure model registered

        if SessionLocal is None:
            return

        with SessionLocal() as session:
            session.add(QueryLogDB(
                benefit_type=benefit_type,
                service_category=service_category,
                decision=decision,
                response_language=response_language or "en",
            ))
            session.commit()
    except Exception as exc:
        logger.debug("log_query failed (non-fatal): %s", exc)


def get_analytics() -> dict[str, Any]:
    """Return aggregated analytics. Returns empty stats on failure."""
    empty: dict[str, Any] = {
        "total_queries": 0,
        "by_decision": {},
        "by_benefit_type": {},
        "by_service_category": {},
        "by_language": {},
        "recent_7_days": 0,
    }

    try:
        from app.db.session import SessionLocal
        from app.models.query_log_db import QueryLogDB

        if SessionLocal is None:
            return empty

        with SessionLocal() as session:
            rows = session.query(QueryLogDB).all()

        if not rows:
            return empty

        cutoff = datetime.utcnow() - timedelta(days=7)

        by_decision: Counter = Counter()
        by_benefit: Counter = Counter()
        by_category: Counter = Counter()
        by_language: Counter = Counter()
        recent = 0

        for row in rows:
            if row.decision:
                by_decision[row.decision] += 1
            if row.benefit_type:
                by_benefit[row.benefit_type] += 1
            if row.service_category:
                by_category[row.service_category] += 1
            lang = row.response_language or "en"
            by_language[lang] += 1
            if row.logged_at and row.logged_at >= cutoff:
                recent += 1

        return {
            "total_queries": len(rows),
            "by_decision": dict(by_decision),
            "by_benefit_type": dict(by_benefit),
            "by_service_category": dict(by_category),
            "by_language": dict(by_language),
            "recent_7_days": recent,
        }

    except Exception as exc:
        logger.warning("get_analytics failed: %s", exc)
        return empty
