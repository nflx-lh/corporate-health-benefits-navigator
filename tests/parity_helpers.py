"""Shared normalization helpers for no-drift and parity tests.

All no-drift tests MUST use normalize_response_for_parity() to ensure
consistent comparison semantics across the test suite.
"""

from __future__ import annotations

from typing import Any

QUERY_ID_STATIC = "QUERY_ID_STATIC"

# Fields that must be compared with exact ordered equality (lists).
ORDERED_LIST_FIELDS = {"reason_codes", "matched_rule_ids", "required_docs", "decision_path"}

# Numeric fields that should be canonically cast.
NUMERIC_FIELDS = {"coverage_percent", "annual_limit_sgd", "co_pay_sgd"}

# Core decision fields shared between /v1/query and /v1/query-orchestrated.
CORE_DECISION_FIELDS = {
    "decision",
    "reason_codes",
    "matched_rule_ids",
    "required_docs",
    "service_category",
    "preauth_required",
    "coverage_percent",
    "annual_limit_sgd",
    "co_pay_sgd",
}


def normalize_response_for_parity(response: dict[str, Any]) -> dict[str, Any]:
    """Normalize a query response for exact parity comparison.

    - Replace query_id with QUERY_ID_STATIC
    - Canonical numeric casting (float for numeric fields, preserve None)
    - Normalize empty/whitespace strings to None where applicable
    - Strict list order checking (lists are preserved as-is for ordered equality)
    """
    out: dict[str, Any] = {}
    for key, val in response.items():
        # 1) Replace query_id with static placeholder
        if key == "query_id":
            out[key] = QUERY_ID_STATIC
            continue

        # 2) Canonical numeric casting
        if key in NUMERIC_FIELDS:
            if val is not None:
                out[key] = float(val)
            else:
                out[key] = None
            continue

        # 3) Normalize empty/whitespace strings to None for nullable string fields
        if isinstance(val, str) and val.strip() == "":
            out[key] = None
            continue

        # 4) Lists are preserved as-is (ordered equality enforced by callers)
        out[key] = val

    return out
