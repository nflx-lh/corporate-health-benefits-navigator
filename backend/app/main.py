from fastapi import FastAPI
from app.api.routes_health import router as health_router
from app.api.routes_auth import router as auth_router
from app.api.routes_query import router as query_router
from app.api.routes_query_orchestrated import router as orchestrated_router
from app.api.routes_admin import router as admin_router

app = FastAPI(title="Corporate Health Benefits Navigator API", version="0.1.0")

app.include_router(health_router, prefix="/v1", tags=["health"])
app.include_router(auth_router, prefix="/v1", tags=["auth"])
app.include_router(query_router, prefix="/v1", tags=["query"])
app.include_router(orchestrated_router, prefix="/v1", tags=["query-orchestrated"])
app.include_router(admin_router, prefix="/v1", tags=["admin"])
