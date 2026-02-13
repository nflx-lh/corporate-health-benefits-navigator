from fastapi import APIRouter

router = APIRouter()

@router.post("/query")
def query():
    return {
        "decision": "insufficient_info",
        "summary": "Stub response. Implement orchestration next.",
        "citations": [],
        "confidence": 0.0
    }
