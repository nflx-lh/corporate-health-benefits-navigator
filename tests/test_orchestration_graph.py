"""Unit tests for the LangGraph orchestration graph.

Tests the graph nodes and routing logic in isolation, covering:
- Rules-only path (no retrieval needed)
- Rules + retrieval path
- Retrieval failure fallback
- Decision field preservation
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.orchestration.graph import build_graph
from app.orchestration.nodes import (
    compose_response_node,
    parse_input_node,
    run_rules_engine_node,
    should_retrieve_router,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_state(**overrides: Any) -> dict[str, Any]:
    """Build a minimal valid OrchestratorState dict."""
    base: dict[str, Any] = {
        "query_text": "dental cleaning",
        "employee_id": "EMP001",
        "rule_decision": None,
        "needs_explanation": False,
        "retrieval_hits": [],
        "final_response": {},
        "errors": [],
    }
    base.update(overrides)
    return base


# ------------------------------------------------------------------
# parse_input_node
# ------------------------------------------------------------------

class TestParseInputNode:

    def test_valid_input_no_errors(self) -> None:
        result = parse_input_node(_make_state())
        assert result["errors"] == []

    def test_missing_query_text(self) -> None:
        result = parse_input_node(_make_state(query_text=""))
        assert any("missing query_text" in e for e in result["errors"])

    def test_missing_employee_id(self) -> None:
        result = parse_input_node(_make_state(employee_id=""))
        assert any("missing employee_id" in e for e in result["errors"])


# ------------------------------------------------------------------
# run_rules_engine_node
# ------------------------------------------------------------------

class TestRunRulesEngineNode:

    def test_known_employee_produces_decision(self) -> None:
        state = _make_state(employee_id="EMP001", query_text="dental cleaning")
        result = run_rules_engine_node(state)
        assert result["rule_decision"] is not None
        assert result["rule_decision"]["decision"] in ("covered", "not_covered", "insufficient_info")

    def test_unknown_employee_returns_none(self) -> None:
        state = _make_state(employee_id="NONEXISTENT")
        result = run_rules_engine_node(state)
        assert result["rule_decision"] is None
        assert result["needs_explanation"] is False
        assert any("EMPLOYEE_NOT_FOUND" in e for e in result["errors"])

    def test_covered_sets_needs_explanation_true(self) -> None:
        state = _make_state(employee_id="EMP001", query_text="dental cleaning")
        result = run_rules_engine_node(state)
        assert result["rule_decision"]["decision"] == "covered"
        assert result["needs_explanation"] is True

    def test_insufficient_sets_needs_explanation_false(self) -> None:
        state = _make_state(employee_id="EMP001", query_text="something random gibberish")
        result = run_rules_engine_node(state)
        assert result["rule_decision"]["decision"] == "insufficient_info"
        assert result["needs_explanation"] is False


# ------------------------------------------------------------------
# should_retrieve_router
# ------------------------------------------------------------------

class TestShouldRetrieveRouter:

    def test_needs_explanation_true(self) -> None:
        assert should_retrieve_router(_make_state(needs_explanation=True)) == "retrieve"

    def test_needs_explanation_false(self) -> None:
        assert should_retrieve_router(_make_state(needs_explanation=False)) == "compose"

    def test_default_false(self) -> None:
        state = _make_state()
        del state["needs_explanation"]
        assert should_retrieve_router(state) == "compose"


# ------------------------------------------------------------------
# compose_response_node
# ------------------------------------------------------------------

class TestComposeResponseNode:

    def test_rules_only_response(self) -> None:
        decision = {
            "query_id": "test-id",
            "employee_id": "EMP001",
            "decision": "covered",
            "reason_summary": "Covered under rule R001",
            "decision_path": ["step1"],
        }
        state = _make_state(rule_decision=decision, retrieval_hits=[])
        result = compose_response_node(state)
        final = result["final_response"]
        assert final["decision"] == "covered"
        assert final["policy_citations"] == []
        assert final["explanation"] is None

    def test_rules_plus_retrieval(self) -> None:
        decision = {
            "query_id": "test-id",
            "employee_id": "EMP001",
            "decision": "covered",
            "reason_summary": "Covered under rule R001",
        }
        hits = [
            {
                "clause_id": "CL-001",
                "source_file": "outpatient_policy.md",
                "section": "## 1. Eligibility",
                "text": "All active employees are eligible.",
                "score": 0.85,
            },
        ]
        state = _make_state(rule_decision=decision, retrieval_hits=hits)
        result = compose_response_node(state)
        final = result["final_response"]
        assert len(final["policy_citations"]) == 1
        assert final["policy_citations"][0]["clause_id"] == "CL-001"
        assert final["explanation"] is not None
        assert "CL-001" in final["explanation"]

    def test_employee_not_found_error_response(self) -> None:
        state = _make_state(rule_decision=None)
        result = compose_response_node(state)
        final = result["final_response"]
        assert final["error"] is True
        assert final["code"] == "EMPLOYEE_NOT_FOUND"

    def test_decision_fields_preserved(self) -> None:
        """All original decision fields must pass through unchanged."""
        decision = {
            "query_id": "qid-123",
            "employee_id": "EMP001",
            "decision": "covered",
            "benefit_type": "dental",
            "service_category": "preventive_dental",
            "reason_summary": "Covered",
            "reason_codes": ["COVERED"],
            "matched_rule_ids": ["R001"],
            "required_docs": ["receipt"],
            "preauth_required": False,
            "coverage_percent": 80.0,
            "annual_limit_sgd": 800.0,
            "co_pay_sgd": 25.0,
            "decision_path": ["step1", "step2"],
        }
        state = _make_state(rule_decision=decision, retrieval_hits=[])
        result = compose_response_node(state)
        final = result["final_response"]
        for key in decision:
            assert final[key] == decision[key], f"Mismatch for {key}"


# ------------------------------------------------------------------
# Full graph integration (mocked retrieval)
# ------------------------------------------------------------------

class TestFullGraphRulesOnly:
    """Test full graph execution for the rules-only path."""

    def test_insufficient_info_skips_retrieval(self) -> None:
        graph = build_graph()
        result = graph.invoke({
            "query_text": "something random gibberish",
            "employee_id": "EMP001",
        })
        final = result["final_response"]
        assert final["decision"] == "insufficient_info"
        assert final["policy_citations"] == []
        assert final["explanation"] is None


class TestFullGraphRetrievalFallback:
    """Test that retrieval failure degrades gracefully."""

    def test_retrieval_error_produces_rules_only_response(self) -> None:
        with patch(
            "app.services.retriever.PolicyRetriever",
            side_effect=Exception("index missing"),
        ):
            graph = build_graph()
            result = graph.invoke({
                "query_text": "dental cleaning",
                "employee_id": "EMP001",
            })
        final = result["final_response"]
        assert final["decision"] == "covered"
        assert final["policy_citations"] == []
        assert final["explanation"] is None
        assert any("RETRIEVAL_ERROR" in e for e in result.get("errors", []))
