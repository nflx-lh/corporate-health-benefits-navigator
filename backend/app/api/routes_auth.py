"""Auth endpoints – login, change-password, request-password-reset."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.auth.jwt_handler import create_token
from app.auth.dependencies import get_current_user
from app.auth.password import verify_password, hash_password
from app.models.employee_db import EmployeeDB
from app.models.password_reset_db import PasswordResetRequestDB

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    employee_id: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    must_reset_password: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class RequestPasswordResetBody(BaseModel):
    employee_id: str


# ---------------------------------------------------------------------------
# Demo credentials (backward compat for HR001 and test employees)
# ---------------------------------------------------------------------------

_DEMO_CREDENTIALS: dict[str, dict] = {
    "EMP001": {"password": "password123", "role": "employee"},
    "EMP002": {"password": "password123", "role": "employee"},
    "EMP003": {"password": "password123", "role": "employee"},
    "HR001": {"password": "hradmin123", "role": "hr_admin"},
}


# ---------------------------------------------------------------------------
# DB session dependency (reuse pattern from routes_employee_crud)
# ---------------------------------------------------------------------------

def _get_db_optional():
    """Yield a DB session if available, else yield None."""
    from app.db.session import SessionLocal
    if SessionLocal is None:
        yield None
        return
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# POST /v1/auth/login
# ---------------------------------------------------------------------------

@router.post("/auth/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    settings: Settings = Depends(get_settings),
    db: Session | None = Depends(_get_db_optional),
):
    # 1. Try DB lookup first
    if db is not None:
        emp = db.get(EmployeeDB, body.employee_id)
        if emp is not None and emp.password_hash:
            if not verify_password(body.password, emp.password_hash):
                raise HTTPException(
                    status_code=401,
                    detail={"code": "INVALID_CREDENTIALS", "message": "Invalid employee_id or password"},
                )
            role = "hr_admin" if body.employee_id.startswith("HR") else "employee"
            token = create_token(body.employee_id, role, settings)
            return LoginResponse(
                access_token=token,
                role=role,
                must_reset_password=bool(emp.must_reset_password),
            )
        elif emp is not None and not emp.password_hash:
            # Employee exists in DB but has no password set — reject
            # (unless they match a demo credential below for backward compat)
            pass

    # 2. Fall back to demo credentials
    user = _DEMO_CREDENTIALS.get(body.employee_id)
    if not user or user["password"] != body.password:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid employee_id or password"},
        )

    token = create_token(body.employee_id, user["role"], settings)
    return LoginResponse(access_token=token, role=user["role"])


# ---------------------------------------------------------------------------
# POST /v1/auth/employee/change-password
# ---------------------------------------------------------------------------

@router.post("/auth/employee/change-password")
def change_password(
    body: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
    db: Session | None = Depends(_get_db_optional),
):
    if db is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "DB_UNAVAILABLE", "message": "Database is not configured"},
        )

    emp = db.get(EmployeeDB, user["sub"])
    if emp is None or not emp.password_hash:
        raise HTTPException(
            status_code=404,
            detail={"code": "EMPLOYEE_NOT_FOUND", "message": "Employee not found"},
        )

    if not verify_password(body.current_password, emp.password_hash):
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Current password is incorrect"},
        )

    emp.password_hash = hash_password(body.new_password)
    emp.must_reset_password = False
    db.commit()

    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /v1/auth/employee/request-password-reset
# ---------------------------------------------------------------------------

@router.post("/auth/employee/request-password-reset")
def request_password_reset(
    body: RequestPasswordResetBody,
    db: Session | None = Depends(_get_db_optional),
):
    # Always return ok to avoid info leak
    if db is None:
        return {"ok": True}

    emp = db.get(EmployeeDB, body.employee_id)
    if emp is None:
        return {"ok": True}

    # Check for existing pending request
    existing = (
        db.query(PasswordResetRequestDB)
        .filter_by(employee_id=body.employee_id, status="pending")
        .first()
    )
    if existing is None:
        req = PasswordResetRequestDB(employee_id=body.employee_id)
        db.add(req)
        db.commit()

    return {"ok": True}
