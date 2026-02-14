"""Integration tests for POST /v1/query-orchestrated endpoint.

Mirrors the Phase 1 /v1/query tests to confirm decision field
preservation, plus validates the additive Phase 3 fields.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Phase 1 decision keys that MUST be present in every response.
BASE_RESPONSE_KEYS = {
    "query_id",
    "employee_id",
    "decision",
    "benefit_type",
    "service_category",
    "reason_summary",
    "reason_codes",
    "matched_rule_ids",
    "required_docs",
    "preauth_required",
    "coverage_percent",
    "annual_limit_sgd",
    "co_pay_sgd",
    "decision_path",
}

# Phase 3 additive keys.
PHASE3_KEYS = {"policy_citations", "explanation"}


# ------------------------------------------------------------------
# Employee not found
# ------------------------------------------------------------------

class TestUnknownEmployee:

    def test_404_structure(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "UNKNOWN", "question": "dental"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "EMPLOYEE_NOT_FOUND"


# ------------------------------------------------------------------
# Decision field regression
# ------------------------------------------------------------------

class TestDecisionFieldPreservation:
    """Deterministic decision fields must match /v1/query output."""

    def _query_both(self, payload: dict) -> tuple[dict, dict]:
        """Query both endpoints and return (original, orchestrated) bodies."""
        r1 = client.post("/v1/query", json=payload)
        r2 = client.post("/v1/query-orchestrated", json=payload)
        assert r1.status_code == 200
        assert r2.status_code == 200
        return r1.json(), r2.json()

    def test_covered_decision_fields(self) -> None:
        payload = {"employee_id": "EMP001", "question": "dental cleaning"}
        orig, orch = self._query_both(payload)
        assert orch["decision"] == orig["decision"] == "covered"
        # Financial fields must match exactly.
        for key in ("coverage_percent", "annual_limit_sgd", "co_pay_sgd", "preauth_required"):
            assert orch[key] == orig[key], f"Mismatch for {key}"
        assert orch["matched_rule_ids"] == orig["matched_rule_ids"]

    def test_not_covered_decision_fields(self) -> None:
        payload = {"employee_id": "EMP026", "question": "dental cleaning"}
        orig, orch = self._query_both(payload)
        assert orch["decision"] == orig["decision"] == "not_covered"
        assert orch["reason_codes"] == orig["reason_codes"]
        assert orch["coverage_percent"] is None
        assert orch["annual_limit_sgd"] is None

    def test_insufficient_info_decision_fields(self) -> None:
        payload = {"employee_id": "EMP025", "question": "dental cleaning"}
        orig, orch = self._query_both(payload)
        assert orch["decision"] == orig["decision"] == "insufficient_info"
        assert orch["reason_codes"] == orig["reason_codes"]


# ------------------------------------------------------------------
# Response schema
# ------------------------------------------------------------------

class TestResponseSchema:

    def test_covered_has_all_keys(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "dental cleaning"},
        )
        keys = set(resp.json().keys())
        assert BASE_RESPONSE_KEYS.issubset(keys)
        assert PHASE3_KEYS.issubset(keys)

    def test_not_covered_has_all_keys(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP026", "question": "dental cleaning"},
        )
        keys = set(resp.json().keys())
        assert BASE_RESPONSE_KEYS.issubset(keys)
        assert PHASE3_KEYS.issubset(keys)

    def test_insufficient_has_all_keys(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "random gibberish"},
        )
        keys = set(resp.json().keys())
        assert BASE_RESPONSE_KEYS.issubset(keys)
        assert PHASE3_KEYS.issubset(keys)


# ------------------------------------------------------------------
# Phase 3 additive fields
# ------------------------------------------------------------------

class TestPolicyCitations:

    def test_citations_is_list(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "dental cleaning"},
        )
        body = resp.json()
        assert isinstance(body["policy_citations"], list)

    def test_insufficient_has_empty_citations(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "random gibberish"},
        )
        body = resp.json()
        assert body["policy_citations"] == []
        assert body["explanation"] is None


# ------------------------------------------------------------------
# Retrieval failure fallback
# ------------------------------------------------------------------

class TestRetrievalFallback:

    def test_retrieval_error_still_returns_200(self) -> None:
        with patch(
            "app.services.retriever.PolicyRetriever",
            side_effect=Exception("boom"),
        ):
            resp = client.post(
                "/v1/query-orchestrated",
                json={"employee_id": "EMP001", "question": "dental cleaning"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "covered"
        assert body["policy_citations"] == []
        assert body["explanation"] is None

    def test_missing_index_still_returns_200(self) -> None:
        with patch(
            "app.orchestration.nodes._DEFAULT_INDEX_DIR",
            __class__=type("FakePath", (), {
                "is_dir": lambda self: False,
            }),
        ):
            resp = client.post(
                "/v1/query-orchestrated",
                json={"employee_id": "EMP001", "question": "dental cleaning"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "covered"


# ------------------------------------------------------------------
# Original /v1/query endpoint untouched
# ------------------------------------------------------------------

class TestOriginalEndpointUnchanged:

    def test_original_query_still_works(self) -> None:
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental cleaning"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "covered"
        # Original endpoint should NOT have Phase 3 fields.
        assert "policy_citations" not in body
        assert "explanation" not in body
