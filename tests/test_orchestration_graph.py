"""Unit tests for the LangGraph orchestration graph.

Tests the graph nodes and routing logic in isolation, covering:
- Rules-only path (no retrieval needed)
- Rules + retrieval path
- Retrieval failure fallback
- Decision field preservation
- Phase 8: Explainer, critic, safety gate, routers
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.orchestration.graph import build_graph
from app.orchestration.nodes import (
    _validate_ai_summary,
    compose_response_node,
    critic_decision_router,
    critic_node,
    explainer_node,
    parse_input_node,
    run_rules_engine_node,
    should_retrieve_router,
    should_run_explainer_router,
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
        "explanation_text": None,
        "critic_result": None,
        "retry_count": 0,
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
        assert final["ai_summary"] is None
        assert final["ai_summary_source"] == "fallback"

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

    def test_ai_summary_passed_through_on_valid(self) -> None:
        decision = {
            "query_id": "test-id",
            "employee_id": "EMP001",
            "decision": "covered",
            "reason_summary": "Covered",
        }
        state = _make_state(
            rule_decision=decision,
            explanation_text="Your dental cleaning is covered under your plan.",
        )
        result = compose_response_node(state)
        final = result["final_response"]
        assert final["ai_summary"] == "Your dental cleaning is covered under your plan."
        assert final["ai_summary_source"] == "llm"

    def test_safety_gate_rejects_mismatched_summary(self) -> None:
        """Inject ai_summary that says 'covered' when decision is 'not_covered'."""
        decision = {
            "query_id": "test-id",
            "employee_id": "EMP001",
            "decision": "not_covered",
            "reason_summary": "Not covered",
        }
        state = _make_state(
            rule_decision=decision,
            explanation_text="Great news! Your dental cleaning is covered at 80%.",
        )
        result = compose_response_node(state)
        final = result["final_response"]
        assert final["ai_summary"] is None
        assert final["ai_summary_source"] == "fallback"

    def test_safety_gate_passes_correct_not_covered(self) -> None:
        decision = {
            "query_id": "test-id",
            "employee_id": "EMP001",
            "decision": "not_covered",
            "reason_summary": "Not covered",
        }
        state = _make_state(
            rule_decision=decision,
            explanation_text="Unfortunately, dental cleaning is not covered under your plan.",
        )
        result = compose_response_node(state)
        final = result["final_response"]
        assert final["ai_summary"] is not None
        assert final["ai_summary_source"] == "llm"

    def test_critic_result_passed_through(self) -> None:
        decision = {
            "query_id": "test-id",
            "employee_id": "EMP001",
            "decision": "covered",
            "reason_summary": "Covered",
        }
        critic = {
            "critic_pass": True,
            "critic_failure_reason": None,
            "critic_feedback": "OK",
            "critic_latency_ms": 100,
            "critic_model": "gpt-4o-mini",
        }
        state = _make_state(
            rule_decision=decision,
            explanation_text="This is covered.",
            critic_result=critic,
        )
        result = compose_response_node(state)
        assert result["final_response"]["critic_result"] == critic


# ------------------------------------------------------------------
# Safety gate validation
# ------------------------------------------------------------------

class TestValidateAISummary:

    def test_covered_keyword_present(self) -> None:
        decision = {"decision": "covered"}
        assert _validate_ai_summary("Your treatment is covered.", decision) is True

    def test_covered_keyword_missing(self) -> None:
        decision = {"decision": "covered"}
        assert _validate_ai_summary("Your treatment is great.", decision) is False

    def test_not_covered_keyword_present(self) -> None:
        decision = {"decision": "not_covered"}
        assert _validate_ai_summary("This is not covered by your plan.", decision) is True

    def test_preauth_required_mentioned(self) -> None:
        decision = {"decision": "covered", "preauth_required": True}
        assert _validate_ai_summary("This is covered, but pre-authorization is required.", decision) is True

    def test_preauth_required_missing(self) -> None:
        decision = {"decision": "covered", "preauth_required": True}
        assert _validate_ai_summary("This is covered. Enjoy!", decision) is False

    def test_required_docs_mentioned(self) -> None:
        decision = {"decision": "covered", "required_docs": ["receipt"]}
        assert _validate_ai_summary("This is covered. Please submit the required documents.", decision) is True

    def test_required_docs_not_mentioned(self) -> None:
        decision = {"decision": "covered", "required_docs": ["receipt"]}
        assert _validate_ai_summary("This is covered. All good!", decision) is False


# ------------------------------------------------------------------
# Explainer node
# ------------------------------------------------------------------

class TestExplainerNode:

    @patch("app.orchestration.nodes.chat_completion", return_value="This is covered at 80%.")
    def test_happy_path(self, mock_llm) -> None:
        decision = {"decision": "covered", "coverage_percent": 80}
        state = _make_state(rule_decision=decision, retry_count=0)
        result = explainer_node(state)
        assert result["explanation_text"] == "This is covered at 80%."
        assert result["retry_count"] == 1
        mock_llm.assert_called_once()

    @patch("app.orchestration.nodes.chat_completion", return_value=None)
    def test_llm_failure_returns_none(self, mock_llm) -> None:
        decision = {"decision": "covered"}
        state = _make_state(rule_decision=decision, retry_count=0)
        result = explainer_node(state)
        assert result["explanation_text"] is None
        assert result["retry_count"] == 1

    @patch("app.orchestration.nodes.chat_completion", return_value="Revised explanation, this is covered.")
    def test_critic_feedback_on_retry(self, mock_llm) -> None:
        decision = {"decision": "covered"}
        critic = {
            "critic_pass": False,
            "critic_failure_reason": "decision_mismatch",
            "critic_feedback": "Decision keyword missing",
        }
        state = _make_state(rule_decision=decision, retry_count=1, critic_result=critic)
        result = explainer_node(state)
        assert result["explanation_text"] == "Revised explanation, this is covered."
        assert result["retry_count"] == 2
        # Verify critic feedback was included in the prompt
        call_args = mock_llm.call_args
        assert "rejected" in call_args[0][1].lower() or "rejected" in str(call_args)


# ------------------------------------------------------------------
# Critic node
# ------------------------------------------------------------------

class TestCriticNode:

    @patch("app.orchestration.nodes.get_settings")
    @patch("app.orchestration.nodes.chat_completion")
    def test_critic_pass(self, mock_llm, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_MODEL_NAME="gpt-4o-mini")
        mock_llm.return_value = json.dumps({"pass": True, "reason": None, "feedback": "All good"})
        state = _make_state(
            rule_decision={"decision": "covered"},
            explanation_text="This is covered.",
        )
        result = critic_node(state)
        critic = result["critic_result"]
        assert critic["critic_pass"] is True
        assert critic["critic_failure_reason"] is None
        assert critic["critic_model"] == "gpt-4o-mini"
        assert isinstance(critic["critic_latency_ms"], int)

    @patch("app.orchestration.nodes.get_settings")
    @patch("app.orchestration.nodes.chat_completion")
    def test_critic_fail_decision_mismatch(self, mock_llm, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_MODEL_NAME="gpt-4o-mini")
        mock_llm.return_value = json.dumps({
            "pass": False,
            "reason": "decision_mismatch",
            "feedback": "Says covered but decision is not_covered",
        })
        state = _make_state(
            rule_decision={"decision": "not_covered"},
            explanation_text="This is covered.",
        )
        result = critic_node(state)
        critic = result["critic_result"]
        assert critic["critic_pass"] is False
        assert critic["critic_failure_reason"] == "decision_mismatch"

    @patch("app.orchestration.nodes.get_settings")
    @patch("app.orchestration.nodes.chat_completion")
    def test_critic_fail_financial_mismatch(self, mock_llm, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_MODEL_NAME="gpt-4o-mini")
        mock_llm.return_value = json.dumps({
            "pass": False,
            "reason": "financial_mismatch",
            "feedback": "Coverage percent wrong",
        })
        state = _make_state(
            rule_decision={"decision": "covered", "coverage_percent": 80},
            explanation_text="Covered at 50%.",
        )
        result = critic_node(state)
        assert result["critic_result"]["critic_failure_reason"] == "financial_mismatch"

    @patch("app.orchestration.nodes.get_settings")
    @patch("app.orchestration.nodes.chat_completion")
    def test_critic_fail_missing_required_actions(self, mock_llm, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_MODEL_NAME="gpt-4o-mini")
        mock_llm.return_value = json.dumps({
            "pass": False,
            "reason": "missing_required_actions",
            "feedback": "Didn't mention preauth",
        })
        state = _make_state(
            rule_decision={"decision": "covered", "preauth_required": True},
            explanation_text="Covered.",
        )
        result = critic_node(state)
        assert result["critic_result"]["critic_failure_reason"] == "missing_required_actions"

    @patch("app.orchestration.nodes.get_settings")
    @patch("app.orchestration.nodes.chat_completion")
    def test_critic_fail_low_confidence(self, mock_llm, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_MODEL_NAME="gpt-4o-mini")
        mock_llm.return_value = json.dumps({
            "pass": False,
            "reason": "low_confidence",
            "feedback": "Explanation is vague",
        })
        state = _make_state(
            rule_decision={"decision": "covered"},
            explanation_text="Maybe covered.",
        )
        result = critic_node(state)
        assert result["critic_result"]["critic_failure_reason"] == "low_confidence"

    @patch("app.orchestration.nodes.get_settings")
    @patch("app.orchestration.nodes.chat_completion", return_value=None)
    def test_critic_llm_unavailable_auto_passes(self, mock_llm, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_MODEL_NAME="gpt-4o-mini")
        state = _make_state(
            rule_decision={"decision": "covered"},
            explanation_text="This is covered.",
        )
        result = critic_node(state)
        assert result["critic_result"]["critic_pass"] is True

    @patch("app.orchestration.nodes.get_settings")
    def test_critic_no_explanation_returns_llm_error(self, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_MODEL_NAME="gpt-4o-mini")
        state = _make_state(
            rule_decision={"decision": "covered"},
            explanation_text=None,
        )
        result = critic_node(state)
        critic = result["critic_result"]
        assert critic["critic_pass"] is False
        assert critic["critic_failure_reason"] == "llm_error"

    @patch("app.orchestration.nodes.get_settings")
    @patch("app.orchestration.nodes.chat_completion", return_value="not valid json")
    def test_critic_unparseable_response_auto_passes(self, mock_llm, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_MODEL_NAME="gpt-4o-mini")
        state = _make_state(
            rule_decision={"decision": "covered"},
            explanation_text="This is covered.",
        )
        result = critic_node(state)
        assert result["critic_result"]["critic_pass"] is True


# ------------------------------------------------------------------
# Router: should_run_explainer
# ------------------------------------------------------------------

class TestShouldRunExplainerRouter:

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.orchestration.nodes.get_settings")
    def test_all_conditions_met_routes_to_explainer(self, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_ENABLED=True, LLM_PROVIDER="openai")
        state = _make_state(needs_explanation=True)
        assert should_run_explainer_router(state) == "explainer"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.orchestration.nodes.get_settings")
    def test_llm_disabled_routes_to_compose(self, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_ENABLED=False, LLM_PROVIDER="openai")
        state = _make_state(needs_explanation=True)
        assert should_run_explainer_router(state) == "compose"

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    @patch("app.orchestration.nodes.get_settings")
    def test_no_api_key_routes_to_compose(self, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_ENABLED=True, LLM_PROVIDER="openai")
        state = _make_state(needs_explanation=True)
        assert should_run_explainer_router(state) == "compose"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.orchestration.nodes.get_settings")
    def test_provider_none_routes_to_compose(self, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_ENABLED=True, LLM_PROVIDER="none")
        state = _make_state(needs_explanation=True)
        assert should_run_explainer_router(state) == "compose"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("app.orchestration.nodes.get_settings")
    def test_no_explanation_needed_routes_to_compose(self, mock_settings) -> None:
        mock_settings.return_value = MagicMock(LLM_ENABLED=True, LLM_PROVIDER="openai")
        state = _make_state(needs_explanation=False)
        assert should_run_explainer_router(state) == "compose"


# ------------------------------------------------------------------
# Router: critic_decision
# ------------------------------------------------------------------

class TestCriticDecisionRouter:

    @patch("app.orchestration.nodes.get_settings")
    def test_critic_pass_routes_to_compose(self, mock_settings) -> None:
        mock_settings.return_value = MagicMock(MAX_EXPLAINER_RETRIES=1)
        state = _make_state(
            critic_result={"critic_pass": True},
            retry_count=1,
        )
        assert critic_decision_router(state) == "compose"

    @patch("app.orchestration.nodes.get_settings")
    def test_critic_fail_retries_available_routes_to_explainer(self, mock_settings) -> None:
        mock_settings.return_value = MagicMock(MAX_EXPLAINER_RETRIES=1)
        state = _make_state(
            critic_result={"critic_pass": False},
            retry_count=1,
        )
        assert critic_decision_router(state) == "explainer"

    @patch("app.orchestration.nodes.get_settings")
    def test_critic_fail_no_retries_routes_to_compose(self, mock_settings) -> None:
        mock_settings.return_value = MagicMock(MAX_EXPLAINER_RETRIES=1)
        state = _make_state(
            critic_result={"critic_pass": False},
            retry_count=2,
        )
        assert critic_decision_router(state) == "compose"

    @patch("app.orchestration.nodes.get_settings")
    def test_uses_max_explainer_retries_setting(self, mock_settings) -> None:
        """Verify that MAX_EXPLAINER_RETRIES constant is used, not hardcoded."""
        mock_settings.return_value = MagicMock(MAX_EXPLAINER_RETRIES=3)
        state = _make_state(
            critic_result={"critic_pass": False},
            retry_count=3,
        )
        # With MAX_EXPLAINER_RETRIES=3, retry_count=3 < 3+1=4, so should retry
        assert critic_decision_router(state) == "explainer"


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
        assert final["ai_summary"] is None
        assert final["ai_summary_source"] == "fallback"


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


class TestFullGraphLLMDisabled:
    """Test full graph with LLM disabled follows deterministic path."""

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    @patch("app.orchestration.nodes.get_settings")
    def test_no_api_key_deterministic_path(self, mock_settings) -> None:
        mock_settings.return_value = MagicMock(
            LLM_ENABLED=True, LLM_PROVIDER="openai",
            MAX_EXPLAINER_RETRIES=1,
        )
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
        assert final["ai_summary"] is None
        assert final["ai_summary_source"] == "fallback"
