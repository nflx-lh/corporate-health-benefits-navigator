"""Orchestrated query endpoint – LangGraph pipeline (Phase 3).

Safe rollout route that preserves the existing /v1/query contract
and adds optional ``policy_citations`` and ``explanation`` fields.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.models.decision import QueryRequest
from app.orchestration.graph import orchestration_graph
from app.auth.rbac import require_role
from app.services.input_sanitizer import sanitize_question
from app.services.analytics_service import log_query
from app.config import get_settings
from app.rate_limit import limiter

router = APIRouter()

_settings = get_settings()


class OrchestratedQueryResponse(BaseModel):
    """Extends the base QueryResponse with optional retrieval fields."""

    # --- existing decision fields (unchanged) ---
    query_id: str
    employee_id: str
    decision: str = Field(description="covered | not_covered | insufficient_info")
    benefit_type: Optional[str] = None
    service_category: Optional[str] = None
    reason_summary: str
    reason_codes: list[str] = Field(default_factory=list)
    matched_rule_ids: list[str] = Field(default_factory=list)
    required_docs: list[str] = Field(default_factory=list)
    preauth_required: Optional[bool] = None
    coverage_percent: Optional[float] = None
    annual_limit_sgd: Optional[float] = None
    co_pay_sgd: Optional[float] = None
    decision_path: list[str] = Field(default_factory=list)

    # --- additive Phase 3 fields ---
    policy_citations: list[dict[str, Any]] = Field(default_factory=list)
    explanation: Optional[str] = None

    # --- Phase 8 explainability fields ---
    ai_summary: Optional[str] = None
    ai_summary_source: str = Field(default="fallback")


@router.post("/query-orchestrated", response_model=OrchestratedQueryResponse)
@limiter.limit(_settings.RATE_LIMIT)
def query_orchestrated(request: Request, req: QueryRequest, _user: dict = Depends(require_role("employee", "hr_admin"))) -> Any:
    """Run the full LangGraph orchestration pipeline."""
    cleaned_question = sanitize_question(req.question)
    result = orchestration_graph.invoke({
        "query_text": cleaned_question,
        "employee_id": req.employee_id,
    })

    final: dict[str, Any] = result.get("final_response", {})

    # Handle employee-not-found error from the pipeline.
    if final.get("error"):
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": final.get("code", "UNKNOWN"),
                    "message": f"employee_id {final.get('employee_id', '')} not found",
                }
            },
        )

    log_query(
        benefit_type=final.get("benefit_type"),
        service_category=final.get("service_category"),
        decision=final.get("decision"),
    )

    return final
