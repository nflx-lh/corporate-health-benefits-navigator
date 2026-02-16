"""Integration tests for POST /v1/query-orchestrated endpoint.

Mirrors the Phase 1 /v1/query tests to confirm decision field
preservation, plus validates the additive Phase 3 and Phase 8 fields.
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

# Phase 8 additive keys.
PHASE8_KEYS = {"ai_summary", "ai_summary_source"}


# ------------------------------------------------------------------
# Employee not found
# ------------------------------------------------------------------

class TestUnknownEmployee:

    def test_404_structure(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "UNK001", "question": "dental"},
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
        assert PHASE8_KEYS.issubset(keys)

    def test_not_covered_has_all_keys(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP026", "question": "dental cleaning"},
        )
        keys = set(resp.json().keys())
        assert BASE_RESPONSE_KEYS.issubset(keys)
        assert PHASE3_KEYS.issubset(keys)
        assert PHASE8_KEYS.issubset(keys)

    def test_insufficient_has_all_keys(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "random gibberish"},
        )
        keys = set(resp.json().keys())
        assert BASE_RESPONSE_KEYS.issubset(keys)
        assert PHASE3_KEYS.issubset(keys)
        assert PHASE8_KEYS.issubset(keys)


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
# Phase 8 fields
# ------------------------------------------------------------------

class TestPhase8Fields:

    def test_ai_summary_defaults_to_fallback(self) -> None:
        """Without LLM configured, ai_summary should be null and source fallback."""
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "dental cleaning"},
        )
        body = resp.json()
        assert body["ai_summary"] is None
        assert body["ai_summary_source"] == "fallback"

    def test_insufficient_info_also_has_phase8_fields(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "random gibberish"},
        )
        body = resp.json()
        assert "ai_summary" in body
        assert "ai_summary_source" in body
        assert body["ai_summary_source"] == "fallback"


class TestOrthodonticsExclusionOrchestrated:
    """QC4: Orthodontics/braces must route to exclusion, not preventive_dental."""

    def test_orthodontic_treatment_premium_excluded(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "Is orthodontic treatment covered for me?"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "not_covered"
        assert body["service_category"] == "orthodontics"
        assert body["service_category"] != "preventive_dental"
        assert "EXCLUSION" in body["reason_codes"]
        assert "R008" not in body["matched_rule_ids"]

    def test_braces_premium_excluded(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "Is braces covered for me?"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "not_covered"
        assert body["service_category"] == "orthodontics"
        assert "EXCLUSION" in body["reason_codes"]

    def test_orthodontics_decision_path(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "orthodontic treatment"},
        )
        body = resp.json()
        path_str = " ".join(body.get("decision_path", []))
        assert "service_category_match: orthodontics" in path_str


class TestMajorDentalPreauthCoherence:
    """Major dental queries must have coherent preauth + required_docs (CL-031, CL-044, CL-075)."""

    def test_bridges_premium_covered_with_preauth(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP011", "question": "bridges"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "covered"
        assert body["service_category"] == "major_dental"
        assert body["matched_rule_ids"] == ["R012"]
        assert body["coverage_percent"] == 50.0
        assert body["annual_limit_sgd"] == 2000.0
        assert body["co_pay_sgd"] == 15.0
        assert body["preauth_required"] is True
        assert "preauth_form" in body["required_docs"]

    def test_crown_premium_covered_with_preauth(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP011", "question": "crown treatment"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "covered"
        assert body["service_category"] == "major_dental"
        assert body["matched_rule_ids"] == ["R012"]
        assert body["coverage_percent"] == 50.0
        assert body["preauth_required"] is True
        assert "preauth_form" in body["required_docs"]

    def test_root_canal_premium_covered_with_preauth(self) -> None:
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP011", "question": "root canal"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "covered"
        assert body["service_category"] == "root_canal"
        assert body["matched_rule_ids"] == ["R038"]
        assert body["coverage_percent"] == 50.0
        assert body["preauth_required"] is True
        assert "preauth_form" in body["required_docs"]

    def test_no_preauth_contradiction_in_response(self) -> None:
        """If preauth_required is False, required_docs must NOT contain preauth_form."""
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "dental cleaning"},
        )
        body = resp.json()
        assert body["preauth_required"] is False
        assert "preauth_form" not in body["required_docs"]


class TestNoAPIKeyEquivalence:
    """With LLM_ENABLED=true but no API key, response should match deterministic path."""

    def test_no_key_matches_deterministic(self) -> None:
        # Default test environment has no OPENAI_API_KEY set
        r_det = client.post("/v1/query", json={"employee_id": "EMP001", "question": "dental cleaning"})
        r_orch = client.post("/v1/query-orchestrated", json={"employee_id": "EMP001", "question": "dental cleaning"})
        assert r_det.status_code == 200
        assert r_orch.status_code == 200
        det = r_det.json()
        orch = r_orch.json()
        # Core decision fields must match
        assert orch["decision"] == det["decision"]
        assert orch["coverage_percent"] == det["coverage_percent"]
        assert orch["annual_limit_sgd"] == det["annual_limit_sgd"]
        assert orch["co_pay_sgd"] == det["co_pay_sgd"]
        # Phase 8 fallback assertions
        assert orch["ai_summary"] is None
        assert orch["ai_summary_source"] == "fallback"


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
        # Original endpoint should NOT have Phase 3 or Phase 8 fields.
        assert "policy_citations" not in body
        assert "explanation" not in body
        assert "ai_summary" not in body
        assert "ai_summary_source" not in body
