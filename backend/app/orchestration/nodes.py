"""LangGraph node functions for the benefits query orchestration pipeline.

Each node receives the full ``OrchestratorState`` dict and returns a
partial dict of keys to merge back into state.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.models.decision import QueryResponse
from app.orchestration.state import OrchestratorState
from app.services.employee_repo import get_employee
from app.services.query_parser import parse_query
from app.services.rules_engine import evaluate

logger = logging.getLogger(__name__)

# Default index directory — resolved relative to repo root.
_DEFAULT_INDEX_DIR = Path(__file__).resolve().parents[3] / "data" / "index"


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
    response: QueryResponse = evaluate(employee, parsed)
    decision_dict = response.model_dump()
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

    final = dict(rule_decision)
    final["policy_citations"] = citations
    final["explanation"] = explanation
    return {"final_response": final}
