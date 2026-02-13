from fastapi import APIRouter

router = APIRouter()

@router.post("/auth/login")
def login():
    return {"access_token": "dev-token", "token_type": "bearer", "role": "employee"}
