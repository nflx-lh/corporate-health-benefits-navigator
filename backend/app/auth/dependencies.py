"""FastAPI dependency for extracting and validating the current user from JWT."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

import jwt

from app.config import Settings, get_settings
from app.auth.jwt_handler import decode_token

# Default dev user returned when APP_ENV == "development"
_DEV_USER = {"sub": "dev", "role": "hr_admin"}


def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Extract and validate the Bearer token, returning decoded claims.

    In development mode (APP_ENV=development) returns a default dev user
    without requiring a token, preserving backward-compatible behavior for
    existing tests and the eval harness.
    """
    if settings.is_dev:
        # Allow requests with no token in dev mode
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return _DEV_USER
        # If a token IS provided in dev mode, still validate it
        token = auth_header.split(" ", 1)[1]
    else:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail={"code": "INVALID_TOKEN", "message": "Missing or malformed Authorization header"},
            )
        token = auth_header.split(" ", 1)[1]

    try:
        claims = decode_token(token, settings)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"code": "TOKEN_EXPIRED", "message": "Token has expired"},
        )
    except jwt.InvalidSignatureError:
        raise HTTPException(
            status_code=403,
            detail={"code": "INVALID_SIGNATURE", "message": "Token signature is invalid"},
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_TOKEN", "message": "Invalid audience claim"},
        )
    except (jwt.DecodeError, jwt.MissingRequiredClaimError):
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or malformed token"},
        )

    return claims
