from fastapi import APIRouter, Depends

from app.auth.rbac import require_role
from app.services.analytics_service import get_analytics

router = APIRouter()


@router.post("/admin/reindex")
def reindex(_user: dict = Depends(require_role("hr_admin"))):
    return {"status": "accepted", "message": "Stub reindex triggered"}


@router.get("/admin/analytics")
def analytics(_user: dict = Depends(require_role("hr_admin"))):
    """Return anonymous query analytics for the HR admin dashboard."""
    return get_analytics()
