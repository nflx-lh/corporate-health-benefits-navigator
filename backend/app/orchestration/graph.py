"""LangGraph orchestration graph for the benefits query pipeline.

Flow:
    START -> parse_input -> detect_language -> run_rules_engine -> conditional(should_retrieve)
      if "retrieve" -> retrieve_policy_hits -> conditional(should_run_explainer)
        if "explainer" -> explainer -> critic -> conditional(critic_decision)
          if "explainer" (retry) -> explainer -> critic -> ...
          if "compose" -> compose_response -> END
        if "compose" -> compose_response -> END
      if "compose"  -> compose_response -> END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.orchestration.nodes import (
    compose_response_node,
    critic_decision_router,
    critic_node,
    detect_language_node,
    explainer_node,
    parse_input_node,
    retrieve_policy_hits_node,
    run_rules_engine_node,
    should_retrieve_router,
    should_run_explainer_router,
)
from app.orchestration.state import OrchestratorState


def build_graph() -> StateGraph:
    """Construct and compile the orchestration graph."""
    builder = StateGraph(OrchestratorState)

    builder.add_node("parse_input", parse_input_node)
    builder.add_node("detect_language", detect_language_node)
    builder.add_node("run_rules_engine", run_rules_engine_node)
    builder.add_node("retrieve_policy_hits", retrieve_policy_hits_node)
    builder.add_node("explainer", explainer_node)
    builder.add_node("critic", critic_node)
    builder.add_node("compose_response", compose_response_node)

    builder.add_edge(START, "parse_input")
    builder.add_edge("parse_input", "detect_language")
    builder.add_edge("detect_language", "run_rules_engine")
    builder.add_conditional_edges(
        "run_rules_engine",
        should_retrieve_router,
        {"retrieve": "retrieve_policy_hits", "compose": "compose_response"},
    )
    builder.add_conditional_edges(
        "retrieve_policy_hits",
        should_run_explainer_router,
        {"explainer": "explainer", "compose": "compose_response"},
    )
    builder.add_edge("explainer", "critic")
    builder.add_conditional_edges(
        "critic",
        critic_decision_router,
        {"explainer": "explainer", "compose": "compose_response"},
    )
    builder.add_edge("compose_response", END)

    return builder.compile()


# Module-level compiled graph (singleton).
orchestration_graph = build_graph()
