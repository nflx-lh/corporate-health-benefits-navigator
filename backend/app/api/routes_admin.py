from fastapi import APIRouter, Depends

from app.auth.rbac import require_role

router = APIRouter()

@router.post("/admin/reindex")
def reindex(_user: dict = Depends(require_role("hr_admin"))):
    return {"status": "accepted", "message": "Stub reindex triggered"}
