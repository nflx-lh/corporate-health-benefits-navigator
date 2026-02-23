"""Employee CRUD endpoints — HR Admin only."""

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from app.auth.rbac import require_role
from app.auth.password import hash_password, generate_temp_password
from app.db.session import SessionLocal
from app.models.employee_db import EmployeeDB
from app.models.password_reset_db import PasswordResetRequestDB

router = APIRouter()

_ID_PATTERN = re.compile(r"^[A-Z]{2,5}\d{1,6}$")


class EmployeeCreate(BaseModel):
    employee_id: str = Field(..., pattern=r"^[A-Z]{2,5}\d{1,6}$", max_length=20)
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=16, le=100)
    employment_type: Optional[str] = None
    plan_tier: Optional[str] = None
    tenure_months: Optional[int] = Field(None, ge=0)
    dependents_count: int = Field(0, ge=0)
    is_active: bool = True


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=16, le=100)
    employment_type: Optional[str] = None
    plan_tier: Optional[str] = None
    tenure_months: Optional[int] = Field(None, ge=0)
    dependents_count: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class EmployeeResponse(BaseModel):
    employee_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    employment_type: Optional[str] = None
    plan_tier: Optional[str] = None
    tenure_months: Optional[int] = None
    dependents_count: int = 0
    is_active: bool = True


class EmployeeCreateResponse(EmployeeResponse):
    temp_password: Optional[str] = None


class PasswordResetRequestResponse(BaseModel):
    id: int
    employee_id: str
    status: str
    requested_at: str
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    notes: Optional[str] = None


class RejectBody(BaseModel):
    notes: Optional[str] = None


def get_db():
    """Yield a DB session. Raises 503 if DB is not configured."""
    if SessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "DB_UNAVAILABLE", "message": "Database is not configured"},
        )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _validate_id(employee_id: str):
    if not _ID_PATTERN.match(employee_id):
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "Invalid employee ID format"},
        )


def _row_to_response(row: EmployeeDB) -> EmployeeResponse:
    return EmployeeResponse(
        employee_id=row.employee_id,
        name=row.name,
        age=row.age,
        employment_type=row.employment_type,
        plan_tier=row.plan_tier,
        tenure_months=row.tenure_months,
        dependents_count=row.dependents_count if row.dependents_count is not None else 0,
        is_active=bool(row.is_active),
    )


# ---------------------------------------------------------------------------
# Employee CRUD
# ---------------------------------------------------------------------------

@router.get("/admin/employees", response_model=list[EmployeeResponse])
def list_employees(
    user: dict = Depends(require_role("hr_admin")),
    db: Session = Depends(get_db),
):
    """List all employee records."""
    rows = db.query(EmployeeDB).order_by(EmployeeDB.employee_id).all()
    return [_row_to_response(r) for r in rows]


@router.post("/admin/employees", response_model=EmployeeCreateResponse, status_code=201)
def create_employee(
    body: EmployeeCreate,
    user: dict = Depends(require_role("hr_admin")),
    db: Session = Depends(get_db),
):
    """Create a new employee record with a temporary password."""
    existing = db.get(EmployeeDB, body.employee_id)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": "EMPLOYEE_EXISTS", "message": f"Employee {body.employee_id} already exists"},
        )
    temp_pw = generate_temp_password()
    row = EmployeeDB(
        employee_id=body.employee_id,
        name=body.name,
        age=body.age,
        employment_type=body.employment_type,
        plan_tier=body.plan_tier,
        tenure_months=body.tenure_months,
        dependents_count=body.dependents_count,
        is_active=body.is_active,
        password_hash=hash_password(temp_pw),
        must_reset_password=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    resp = _row_to_response(row)
    return EmployeeCreateResponse(**resp.model_dump(), temp_password=temp_pw)


@router.get("/admin/employees/{employee_id}", response_model=EmployeeResponse)
def read_employee(
    employee_id: str,
    user: dict = Depends(require_role("hr_admin")),
    db: Session = Depends(get_db),
):
    """Read a single employee by ID."""
    _validate_id(employee_id)
    row = db.get(EmployeeDB, employee_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "EMPLOYEE_NOT_FOUND", "message": f"Employee {employee_id} not found"},
        )
    return _row_to_response(row)


@router.put("/admin/employees/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: str,
    body: EmployeeUpdate,
    user: dict = Depends(require_role("hr_admin")),
    db: Session = Depends(get_db),
):
    """Update an existing employee record."""
    _validate_id(employee_id)
    row = db.get(EmployeeDB, employee_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "EMPLOYEE_NOT_FOUND", "message": f"Employee {employee_id} not found"},
        )
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return _row_to_response(row)


@router.delete("/admin/employees/{employee_id}", status_code=200)
def delete_employee(
    employee_id: str,
    user: dict = Depends(require_role("hr_admin")),
    db: Session = Depends(get_db),
):
    """Delete an employee record."""
    _validate_id(employee_id)
    row = db.get(EmployeeDB, employee_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "EMPLOYEE_NOT_FOUND", "message": f"Employee {employee_id} not found"},
        )
    db.delete(row)
    db.commit()
    return {"message": f"Employee {employee_id} deleted"}


# ---------------------------------------------------------------------------
# Password Reset Request Management (HR Admin)
# ---------------------------------------------------------------------------

def _reset_to_response(row: PasswordResetRequestDB) -> dict:
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "status": row.status,
        "requested_at": row.requested_at.isoformat() if row.requested_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "resolved_by": row.resolved_by,
        "notes": row.notes,
    }


@router.get("/admin/password-reset-requests")
def list_password_reset_requests(
    status: str = "pending",
    user: dict = Depends(require_role("hr_admin")),
    db: Session = Depends(get_db),
):
    """List password reset requests filtered by status."""
    rows = (
        db.query(PasswordResetRequestDB)
        .filter_by(status=status)
        .order_by(PasswordResetRequestDB.id)
        .all()
    )
    return [_reset_to_response(r) for r in rows]


@router.post("/admin/password-reset-requests/{request_id}/reset")
def approve_password_reset(
    request_id: int,
    user: dict = Depends(require_role("hr_admin")),
    db: Session = Depends(get_db),
):
    """Approve a password reset: generate temp password, update employee."""
    req = db.get(PasswordResetRequestDB, request_id)
    if req is None or req.status != "pending":
        raise HTTPException(
            status_code=404,
            detail={"code": "REQUEST_NOT_FOUND", "message": "Reset request not found or already resolved"},
        )

    emp = db.get(EmployeeDB, req.employee_id)
    if emp is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "EMPLOYEE_NOT_FOUND", "message": f"Employee {req.employee_id} not found"},
        )

    temp_pw = generate_temp_password()
    emp.password_hash = hash_password(temp_pw)
    emp.must_reset_password = True

    req.status = "completed"
    req.resolved_at = datetime.now(timezone.utc)
    req.resolved_by = user.get("sub", "unknown")

    db.commit()

    return {"temp_password": temp_pw}


@router.post("/admin/password-reset-requests/{request_id}/reject")
def reject_password_reset(
    request_id: int,
    body: RejectBody = None,
    user: dict = Depends(require_role("hr_admin")),
    db: Session = Depends(get_db),
):
    """Reject a password reset request."""
    req = db.get(PasswordResetRequestDB, request_id)
    if req is None or req.status != "pending":
        raise HTTPException(
            status_code=404,
            detail={"code": "REQUEST_NOT_FOUND", "message": "Reset request not found or already resolved"},
        )

    req.status = "rejected"
    req.resolved_at = datetime.now(timezone.utc)
    req.resolved_by = user.get("sub", "unknown")
    if body and body.notes:
        req.notes = body.notes

    db.commit()

    return {"ok": True}
