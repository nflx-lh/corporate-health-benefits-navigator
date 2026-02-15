"""Query endpoint – deterministic rules engine (Phase 1)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.models.decision import QueryRequest, QueryResponse
from app.services.employee_repo import get_employee
from app.services.query_parser import parse_query
from app.services.rules_engine import evaluate
from app.services.input_sanitizer import sanitize_question
from app.auth.rbac import require_role
from app.config import get_settings
from app.rate_limit import limiter

router = APIRouter()

_settings = get_settings()


@router.post("/query", response_model=QueryResponse)
@limiter.limit(_settings.RATE_LIMIT)
def query(request: Request, req: QueryRequest, _user: dict = Depends(require_role("employee", "hr_admin"))):
    employee = get_employee(req.employee_id)
    if employee is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "EMPLOYEE_NOT_FOUND",
                    "message": f"employee_id {req.employee_id} not found",
                }
            },
        )

    cleaned_question = sanitize_question(req.question)
    parsed = parse_query(cleaned_question)
    return evaluate(employee, parsed)
