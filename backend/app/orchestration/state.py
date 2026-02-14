"""Typed orchestration state for the LangGraph benefits query pipeline."""

from __future__ import annotations

from typing import Any, Optional

from typing_extensions import TypedDict


class OrchestratorState(TypedDict, total=False):
    """State passed through the LangGraph orchestration graph.

    Required keys are set by ``parse_input_node``; optional keys are
    populated by downstream nodes.
    """

    # --- inputs (set once) ---
    query_text: str
    employee_id: str

    # --- deterministic rules output ---
    rule_decision: Optional[dict[str, Any]]

    # --- retrieval control ---
    needs_explanation: bool

    # --- retrieval output ---
    retrieval_hits: list[dict[str, Any]]

    # --- final assembled response ---
    final_response: dict[str, Any]

    # --- error accumulator (non-fatal) ---
    errors: list[str]
