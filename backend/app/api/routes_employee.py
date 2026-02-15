"""Employee verification endpoint."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field, constr
from app.services.employee_repo import get_employee
from app.config import get_settings
from app.rate_limit import limiter

router = APIRouter()
_settings = get_settings()


@router.get("/employees/{employee_id}/verify")
@limiter.limit(_settings.RATE_LIMIT)
def verify_employee(request: Request, employee_id: str):
    """Check whether an employee ID exists. Returns 200 or 404."""
    import re

    if not re.match(r"^[A-Z]{2,5}\d{1,6}$", employee_id):
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "Invalid employee ID format"},
        )

    employee = get_employee(employee_id)
    if employee is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "EMPLOYEE_NOT_FOUND", "message": f"Employee {employee_id} not found"},
        )

    return {"employee_id": employee_id, "status": "active" if employee.is_active else "inactive"}
