"""LangGraph node functions for the benefits query orchestration pipeline.

Each node receives the full ``OrchestratorState`` dict and returns a
partial dict of keys to merge back into state.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.models.decision import QueryResponse
from app.orchestration.state import OrchestratorState
from app.services.employee_repo import get_employee
from app.services.query_parser import parse_query
from app.services.rules_engine import evaluate
from app.services.llm_client import chat_completion

logger = logging.getLogger(__name__)

# Default index directory — use DATA_ROOT env var in Docker, fallback to repo root for local dev.
_DATA_ROOT = Path(os.environ["DATA_ROOT"]) if "DATA_ROOT" in os.environ else Path(__file__).resolve().parents[3] / "data"
_DEFAULT_INDEX_DIR = _DATA_ROOT / "index"


# ------------------------------------------------------------------
# Node: parse_input
# ------------------------------------------------------------------

def parse_input_node(state: OrchestratorState) -> dict[str, Any]:
    """Validate that required input keys are present.

    This is a pass-through sanity check; actual parsing happens in the
    rules engine node.
    """
    errors: list[str] = list(state.get("errors") or [])
    if not state.get("query_text"):
        errors.append("missing query_text")
    if not state.get("employee_id"):
        errors.append("missing employee_id")
    return {"errors": errors}


# ------------------------------------------------------------------
# Node: run_rules_engine
# ------------------------------------------------------------------

def run_rules_engine_node(state: OrchestratorState) -> dict[str, Any]:
    """Execute the deterministic rules engine and store the decision."""
    employee_id: str = state["employee_id"]
    question: str = state["query_text"]

    employee = get_employee(employee_id)
    if employee is None:
        return {
            "rule_decision": None,
            "needs_explanation": False,
            "errors": list(state.get("errors") or []) + [f"EMPLOYEE_NOT_FOUND:{employee_id}"],
        }

    parsed = parse_query(question)
    logger.debug(
        "run_rules_engine_node | employee=%s question=%r | parsed=(%s, %s)",
        employee_id, question, parsed.benefit_type, parsed.service_category,
    )
    response: QueryResponse = evaluate(employee, parsed)
    decision_dict = response.model_dump()
    raw_plan = getattr(employee, "plan_tier", None) or "your plan"
    decision_dict["plan_tier"] = raw_plan.title()
    logger.debug(
        "run_rules_engine_node | decision=%s service_category=%s matched_rules=%s",
        decision_dict.get("decision"), decision_dict.get("service_category"),
        decision_dict.get("matched_rule_ids"),
    )
    needs = decision_dict.get("decision") in ("covered", "not_covered")
    return {
        "rule_decision": decision_dict,
        "needs_explanation": needs,
    }


# ------------------------------------------------------------------
# Router: should_retrieve
# ------------------------------------------------------------------

def should_retrieve_router(state: OrchestratorState) -> str:
    """Conditional edge: route to retrieval or straight to compose.

    Returns:
        ``"retrieve"`` or ``"compose"``.
    """
    if state.get("needs_explanation", False):
        return "retrieve"
    return "compose"


# ------------------------------------------------------------------
# Node: retrieve_policy_hits
# ------------------------------------------------------------------

def retrieve_policy_hits_node(state: OrchestratorState) -> dict[str, Any]:
    """Retrieve citation-ready policy hits. Degrades gracefully on failure."""
    query_text: str = state.get("query_text", "")
    try:
        from app.services.retriever import PolicyRetriever

        index_dir = _DEFAULT_INDEX_DIR
        if not index_dir.is_dir():
            logger.warning("Retrieval index directory not found: %s", index_dir)
            return {"retrieval_hits": [], "errors": list(state.get("errors") or []) + ["RETRIEVAL_INDEX_MISSING"]}

        retriever = PolicyRetriever(index_dir)
        hits = retriever.retrieve(query_text, top_k=3)
        return {
            "retrieval_hits": [
                {
                    "clause_id": h.clause_id,
                    "source_file": h.source_file,
                    "section": h.section,
                    "text": h.text,
                    "score": h.score,
                }
                for h in hits
            ],
        }
    except Exception as exc:
        logger.warning("Retrieval failed (graceful fallback): %s", exc)
        return {
            "retrieval_hits": [],
            "errors": list(state.get("errors") or []) + [f"RETRIEVAL_ERROR:{exc}"],
        }


# ------------------------------------------------------------------
# Helper: normalize required_docs vs preauth_required
# ------------------------------------------------------------------

def _normalize_docs(
    required_docs: list[str] | None,
    preauth_required: bool | None,
) -> list[str]:
    """Ensure required_docs and preauth_required are semantically aligned.

    Rules:
    - Deduplicate while preserving original order.
    - If preauth_required is True: ensure ``preauth_form`` is present.
    - If preauth_required is False: remove ``preauth_form``.
    - If preauth_required is None: dedupe only (no add/remove).
    """
    docs = list(required_docs or [])

    # Deduplicate, preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for d in docs:
        if d not in seen:
            seen.add(d)
            deduped.append(d)

    if preauth_required is True:
        if "preauth_form" not in seen:
            deduped.append("preauth_form")
    elif preauth_required is False:
        deduped = [d for d in deduped if d != "preauth_form"]

    return deduped


# ------------------------------------------------------------------
# Node: compose_response
# ------------------------------------------------------------------

def compose_response_node(state: OrchestratorState) -> dict[str, Any]:
    """Assemble the final response from rules decision + optional citations."""
    rule_decision: dict[str, Any] | None = state.get("rule_decision")
    retrieval_hits: list[dict[str, Any]] = state.get("retrieval_hits") or []

    # If rules engine didn't produce a decision (employee not found),
    # return an error response dict for the route handler to interpret.
    if rule_decision is None:
        return {
            "final_response": {
                "error": True,
                "code": "EMPLOYEE_NOT_FOUND",
                "employee_id": state.get("employee_id", ""),
            },
        }

    # Build citations list from retrieval hits.
    citations = [
        {
            "clause_id": h["clause_id"],
            "source_file": h["source_file"],
            "section": h["section"],
            "text": h["text"],
            "score": h["score"],
        }
        for h in retrieval_hits
    ]

    # Build explanation string from top citation.
    explanation: str | None = None
    if citations:
        top = citations[0]
        explanation = (
            f"Per {top['clause_id']} ({top['source_file']}, "
            f"{top['section']}): {top['text'][:200]}"
        )

    # --- Phase 8: Safety gate for ai_summary ---
    ai_summary = state.get("explanation_text")
    ai_summary_source = "fallback"

    if ai_summary and rule_decision:
        if _validate_ai_summary(ai_summary, rule_decision):
            ai_summary_source = "llm"
        else:
            logger.warning("Safety gate: ai_summary rejected (mismatch with deterministic decision)")
            ai_summary = None
            ai_summary_source = "fallback"

    final = dict(rule_decision)
    final["required_docs"] = _normalize_docs(
        final.get("required_docs"), final.get("preauth_required"),
    )
    final["policy_citations"] = citations
    final["explanation"] = explanation
    final["ai_summary"] = ai_summary
    final["ai_summary_source"] = ai_summary_source

    # Pass through critic result if present
    critic = state.get("critic_result")
    if critic:
        final["critic_result"] = critic

    return {"final_response": final}


# ------------------------------------------------------------------
# Safety gate helper
# ------------------------------------------------------------------

_DECISION_KEYWORDS = {
    "covered": ["covered"],
    "not_covered": ["not covered", "not_covered", "denied", "excluded"],
    "insufficient_info": ["insufficient", "more information", "unable to determine"],
}


def _validate_ai_summary(ai_summary: str, rule_decision: dict[str, Any]) -> bool:
    """Validate that ai_summary is consistent with deterministic decision.

    Checks:
    1. Decision word appears correctly
    2. Financial fields mentioned if present
    3. Required docs / preauth mentioned if applicable
    """
    decision = rule_decision.get("decision", "")
    summary_lower = ai_summary.lower()

    # Check 1: Decision keyword present
    keywords = _DECISION_KEYWORDS.get(decision, [])
    if not any(kw in summary_lower for kw in keywords):
        return False

    # Check 2: If decision is 'covered' and there's a preauth requirement, it should be mentioned
    if rule_decision.get("preauth_required") is True:
        if "pre-auth" not in summary_lower and "preauth" not in summary_lower and "pre auth" not in summary_lower and "authorization" not in summary_lower:
            return False

    # Check 3: If there are required docs, at least one should be referenced
    required_docs = rule_decision.get("required_docs") or []
    if required_docs and decision == "covered":
        # At least mention "document" or one of the doc names
        doc_mentioned = "document" in summary_lower or "doc" in summary_lower
        if not doc_mentioned:
            doc_mentioned = any(d.lower() in summary_lower for d in required_docs)
        if not doc_mentioned:
            return False

    return True


# ------------------------------------------------------------------
# Node: explainer
# ------------------------------------------------------------------

def explainer_node(state: OrchestratorState) -> dict[str, Any]:
    """Build prompt from rule_decision + citations + critic feedback, call LLM."""

    rule_decision = state.get("rule_decision") or {}
    retrieval_hits = state.get("retrieval_hits") or []
    retry_count = state.get("retry_count", 0)
    critic_result = state.get("critic_result")

    # Build citation context
    citation_text = ""
    for h in retrieval_hits[:3]:
        citation_text += f"\n- {h.get('clause_id', '')}: {h.get('text', '')[:200]}"

    # Build system prompt
    plan_name = rule_decision.get("plan_tier") or "your plan"
    system_prompt = (
        "You are a friendly but concise benefits assistant helping an employee understand their coverage. "
        f"The deterministic decision is: {rule_decision.get('decision', 'unknown')}. "
        "You MUST accurately reflect this decision — never contradict it. "
        "Write in plain, conversational English as if speaking directly to the employee. "
        "Lead with a direct yes/no answer to whether they are covered, then give the key details naturally. "
        f"Always open with 'Current Plan: {plan_name}' on its own line. "
        "Keep it brief — 3 to 5 sentences max. "
        "Rules:\n"
        "- Never mention internal rule IDs (e.g. R008) or field names.\n"
        "- Never list required document names — just say they need to keep their documents.\n"
        "- Do not use bullet points, headers, or markdown.\n"
        "- Do not add greetings, sign-offs, or filler phrases like 'Great news!' or 'Let me know'.\n"
        "- If policy citations are provided, reference them naturally (e.g. 'per your plan policy').\n"
        "- This is a search result panel, not a chat — keep it factual and direct."
    )

    # Build user message
    user_message = f"Decision: {json.dumps(rule_decision, default=str)}"
    if citation_text:
        user_message += f"\n\nPolicy citations:{citation_text}"
    if critic_result and not critic_result.get("critic_pass", True):
        user_message += f"\n\nPrevious attempt was rejected: {critic_result.get('critic_feedback', '')}. Please fix."

    result = chat_completion(system_prompt, user_message)
    if not isinstance(result, str) or not result.strip():
        return {"explanation_text": None, "retry_count": retry_count + 1}

    # Post-process: ensure line breaks before key fact patterns
    result = re.sub(r'(?<!\n)((?:Current Plan:|Annual limit:|Co-pay:|Please refer|Please note))', r'\n\1', result)
    result = result.strip()

    return {
        "explanation_text": result,
        "retry_count": retry_count + 1,
    }


# ------------------------------------------------------------------
# Node: critic
# ------------------------------------------------------------------

_CRITIC_FAILURE_REASONS = frozenset({
    "decision_mismatch",
    "financial_mismatch",
    "missing_required_actions",
    "low_confidence",
    "llm_error",
})


def critic_node(state: OrchestratorState) -> dict[str, Any]:
    """Validate explanation against deterministic decision. Returns critic schema."""

    settings = get_settings()
    explanation_text = state.get("explanation_text")
    rule_decision = state.get("rule_decision") or {}

    start_ms = time.time()

    # If explainer produced nothing, auto-pass with llm_error
    if not explanation_text:
        latency = int((time.time() - start_ms) * 1000)
        return {
            "critic_result": {
                "critic_pass": False,
                "critic_failure_reason": "llm_error",
                "critic_feedback": "Explainer produced no output",
                "critic_latency_ms": latency,
                "critic_model": settings.LLM_MODEL_NAME,
            }
        }

    system_prompt = (
        "You are a critic that validates AI-generated benefit explanations against "
        "deterministic decisions. Check:\n"
        "1. Decision word matches (covered/not_covered/insufficient_info)\n"
        "2. Financial fields (coverage_percent, annual_limit_sgd, co_pay_sgd) are accurate\n"
        "3. Required docs and preauth are mentioned if applicable\n"
        "Respond ONLY with a JSON object: "
        '{"pass": true/false, "reason": "decision_mismatch|financial_mismatch|missing_required_actions|low_confidence|llm_error", "feedback": "..."}'
    )

    user_message = (
        f"Decision: {json.dumps(rule_decision, default=str)}\n\n"
        f"Explanation to validate:\n{explanation_text}"
    )

    raw = chat_completion(system_prompt, user_message)
    latency = int((time.time() - start_ms) * 1000)

    # If critic LLM call failed, auto-pass (don't block on critic failure)
    if not raw:
        return {
            "critic_result": {
                "critic_pass": True,
                "critic_failure_reason": None,
                "critic_feedback": "Critic LLM unavailable, auto-pass",
                "critic_latency_ms": latency,
                "critic_model": settings.LLM_MODEL_NAME,
            }
        }

    # Parse critic response
    try:
        parsed = json.loads(raw)
        critic_pass = bool(parsed.get("pass", False))
        reason = parsed.get("reason")
        if reason not in _CRITIC_FAILURE_REASONS:
            reason = None
        feedback = str(parsed.get("feedback", ""))
    except (json.JSONDecodeError, KeyError):
        # Can't parse critic response, auto-pass
        critic_pass = True
        reason = None
        feedback = "Critic response unparseable, auto-pass"

    return {
        "critic_result": {
            "critic_pass": critic_pass,
            "critic_failure_reason": reason if not critic_pass else None,
            "critic_feedback": feedback,
            "critic_latency_ms": latency,
            "critic_model": settings.LLM_MODEL_NAME,
        }
    }


# ------------------------------------------------------------------
# Router: should_run_explainer
# ------------------------------------------------------------------

def should_run_explainer_router(state: OrchestratorState) -> str:
    """Route to explainer if LLM is enabled + has API key + provider != none + needs_explanation."""
    settings = get_settings()

    if not settings.LLM_ENABLED:
        return "compose"
    if settings.LLM_PROVIDER.lower() == "none":
        return "compose"
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return "compose"
    if not state.get("needs_explanation", False):
        return "compose"
    return "explainer"


# ------------------------------------------------------------------
# Router: critic_decision
# ------------------------------------------------------------------

def critic_decision_router(state: OrchestratorState) -> str:
    """Route to retry explainer if critic fails and retries remain, else compose."""
    settings = get_settings()
    critic = state.get("critic_result") or {}
    retry_count = state.get("retry_count", 0)

    if critic.get("critic_pass", True):
        return "compose"

    if retry_count < settings.MAX_EXPLAINER_RETRIES + 1:
        return "explainer"

    return "compose"
