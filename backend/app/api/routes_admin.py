from fastapi import APIRouter

router = APIRouter()

@router.post("/admin/reindex")
def reindex():
    return {"status": "accepted", "message": "Stub reindex triggered"}
