"""Role-based access control dependency for FastAPI routes."""

from __future__ import annotations

from fastapi import Depends, HTTPException

from app.auth.dependencies import get_current_user


def require_role(*allowed_roles: str):
    """Return a FastAPI dependency that enforces role membership.

    Usage::

        @router.post("/admin/reindex")
        def reindex(user=Depends(require_role("hr_admin"))):
            ...
    """

    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Insufficient role"},
            )
        return current_user

    return _check
