"""Query endpoint – deterministic rules engine (Phase 1)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.decision import QueryRequest, QueryResponse
from app.services.employee_repo import get_employee
from app.services.query_parser import parse_query
from app.services.rules_engine import evaluate

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
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

    parsed = parse_query(req.question)
    return evaluate(employee, parsed)
