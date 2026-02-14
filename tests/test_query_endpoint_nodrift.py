"""No-drift gate: /v1/query and /v1/query-orchestrated responses must match
golden outputs exactly.

Normalization method: both actual and expected query_id are set to
QUERY_ID_STATIC before comparison. All other fields are exact match
with canonical numeric casting and ordered list equality.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.parity_helpers import (
    CORE_DECISION_FIELDS,
    normalize_response_for_parity,
)

client = TestClient(app)

FIXTURES_PATH = pathlib.Path(__file__).parent / "fixtures" / "query_golden_outputs.json"


def _load_golden() -> list[dict]:
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        return json.load(f)


GOLDEN_CASES = _load_golden()


# ------------------------------------------------------------------
# /v1/query no-drift tests
# ------------------------------------------------------------------


class TestQueryEndpointNoDrift:
    """Full-payload no-drift gate for POST /v1/query."""

    @pytest.mark.parametrize(
        "golden_case",
        GOLDEN_CASES,
        ids=[c["label"] for c in GOLDEN_CASES],
    )
    def test_nodrift(self, golden_case: dict) -> None:
        resp = client.post("/v1/query", json=golden_case["input"])
        assert resp.status_code == 200

        actual = normalize_response_for_parity(resp.json())
        expected = normalize_response_for_parity(golden_case["expected"])

        assert actual == expected, (
            f"Drift detected for {golden_case['label']}:\n"
            f"  expected: {expected}\n"
            f"  actual:   {actual}"
        )


# ------------------------------------------------------------------
# /v1/query-orchestrated no-drift guard (core decision fields only)
# ------------------------------------------------------------------


class TestOrchestratedEndpointNoDrift:
    """Core decision field no-drift gate for POST /v1/query-orchestrated.

    Compares only the shared decision fields (not Phase 3 additive fields
    like policy_citations / explanation which may vary).
    """

    @pytest.mark.parametrize(
        "golden_case",
        GOLDEN_CASES,
        ids=[c["label"] for c in GOLDEN_CASES],
    )
    def test_orchestrated_core_fields_nodrift(self, golden_case: dict) -> None:
        resp = client.post("/v1/query-orchestrated", json=golden_case["input"])
        assert resp.status_code == 200

        actual_full = normalize_response_for_parity(resp.json())
        expected_full = normalize_response_for_parity(golden_case["expected"])

        for field in CORE_DECISION_FIELDS:
            assert actual_full.get(field) == expected_full.get(field), (
                f"Drift in orchestrated endpoint for {golden_case['label']}, "
                f"field '{field}': expected={expected_full.get(field)!r}, "
                f"actual={actual_full.get(field)!r}"
            )
