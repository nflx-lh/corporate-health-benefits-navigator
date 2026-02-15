"""Auth endpoint – login with JWT issuance."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.auth.jwt_handler import create_token

router = APIRouter()


class LoginRequest(BaseModel):
    employee_id: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


# MVP: simple credential map. Not production-grade; will be replaced by
# a proper user store / bcrypt in a future phase.
_DEMO_CREDENTIALS: dict[str, dict] = {
    "EMP001": {"password": "password123", "role": "employee"},
    "EMP002": {"password": "password123", "role": "employee"},
    "EMP003": {"password": "password123", "role": "employee"},
    "HR001": {"password": "hradmin123", "role": "hr_admin"},
}


@router.post("/auth/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    settings: Settings = Depends(get_settings),
):
    user = _DEMO_CREDENTIALS.get(body.employee_id)
    if not user or user["password"] != body.password:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid employee_id or password"},
        )

    token = create_token(body.employee_id, user["role"], settings)
    return LoginResponse(access_token=token, role=user["role"])
