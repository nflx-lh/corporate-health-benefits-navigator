from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes_health import router as health_router
from app.api.routes_auth import router as auth_router
from app.api.routes_query import router as query_router
from app.api.routes_query_orchestrated import router as orchestrated_router
from app.api.routes_admin import router as admin_router
from app.api.routes_employee import router as employee_router
from app.api.routes_employee_crud import router as employee_crud_router
from app.config import get_settings
from app.rate_limit import limiter
from app.middleware.error_handler import (
    global_exception_handler,
    http_exception_handler,
)

import logging

from app.middleware.log_sanitizer import SensitiveDataFilter

_settings = get_settings()

# --- Logging hygiene ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
for handler in logging.root.handlers:
    handler.addFilter(SensitiveDataFilter())

app = FastAPI(title="Corporate Health Benefits Navigator API", version="0.1.0")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# --- Exception handlers (order: most specific first) ---

# Rate limit
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
            }
        },
    )


# Validation (422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    messages = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        messages.append(f"{loc}: {err.get('msg', '')}")
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "; ".join(messages),
            }
        },
    )


# HTTPException (structured pass-through)
app.add_exception_handler(HTTPException, http_exception_handler)

# Catch-all (safe 500)
app.add_exception_handler(Exception, global_exception_handler)

# --- Middleware ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# --- Routers ---

app.include_router(health_router, prefix="/v1", tags=["health"])
app.include_router(auth_router, prefix="/v1", tags=["auth"])
app.include_router(query_router, prefix="/v1", tags=["query"])
app.include_router(orchestrated_router, prefix="/v1", tags=["query-orchestrated"])
app.include_router(admin_router, prefix="/v1", tags=["admin"])
app.include_router(employee_router, prefix="/v1", tags=["employee"])
app.include_router(employee_crud_router, prefix="/v1", tags=["employee-crud"])
