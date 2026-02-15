"""JWT token creation and validation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.config import Settings


def create_token(employee_id: str, role: str, settings: Settings) -> str:
    """Create a signed JWT with sub, role, exp, iat, and aud claims."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": employee_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
        "aud": settings.JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, settings: Settings) -> dict:
    """Decode and validate a JWT. Raises specific exceptions on failure.

    Raises:
        jwt.ExpiredSignatureError  – token has expired
        jwt.InvalidAudienceError   – aud claim mismatch
        jwt.InvalidSignatureError  – signature verification failed
        jwt.DecodeError            – malformed / unparseable token
        jwt.MissingRequiredClaimError – required claim absent
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        options={"require": ["sub", "role", "exp", "iat", "aud"]},
    )
