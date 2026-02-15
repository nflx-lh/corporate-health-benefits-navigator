"""B-704 – CORS Strict Allowlist tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    s = Settings()
    s.APP_ENV = overrides.get("APP_ENV", "development")
    s.JWT_SECRET = overrides.get("JWT_SECRET", "test-secret-32chars-minimum-here")
    s.JWT_ALGORITHM = overrides.get("JWT_ALGORITHM", "HS256")
    s.JWT_EXPIRE_MINUTES = overrides.get("JWT_EXPIRE_MINUTES", 60)
    s.JWT_AUDIENCE = overrides.get("JWT_AUDIENCE", "chbn-api")
    s.CORS_ORIGINS = overrides.get("CORS_ORIGINS", [])
    return s


def _build_app(settings: Settings):
    """Build a fresh FastAPI app with the given settings to ensure
    CORSMiddleware picks up the overridden origins."""
    from fastapi import FastAPI, Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse

    from app.api.routes_health import router as health_router
    from app.api.routes_auth import router as auth_router
    from app.api.routes_query import router as query_router
    from app.api.routes_query_orchestrated import router as orchestrated_router
    from app.api.routes_admin import router as admin_router
    from app.config import get_settings

    test_app = FastAPI()

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @test_app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        messages = []
        for err in errors:
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            messages.append(f"{loc}: {err.get('msg', '')}")
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": "; ".join(messages)}},
        )

    test_app.include_router(health_router, prefix="/v1", tags=["health"])
    test_app.include_router(auth_router, prefix="/v1", tags=["auth"])
    test_app.include_router(query_router, prefix="/v1", tags=["query"])
    test_app.include_router(orchestrated_router, prefix="/v1", tags=["query-orchestrated"])
    test_app.include_router(admin_router, prefix="/v1", tags=["admin"])

    test_app.dependency_overrides[get_settings] = lambda: settings
    return test_app


# ---------------------------------------------------------------------------
# Dev mode: wildcard origins allowed
# ---------------------------------------------------------------------------

class TestDevAllowsAnyOrigin:
    def test_dev_allows_any_origin(self):
        settings = _make_settings(APP_ENV="development")
        app = _build_app(settings)
        client = TestClient(app)
        resp = client.get(
            "/v1/health",
            headers={"Origin": "http://evil.example.com"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "*"


# ---------------------------------------------------------------------------
# Prod: unknown origin blocked
# ---------------------------------------------------------------------------

class TestProdBlocksUnknownOrigin:
    def test_prod_blocks_unknown_origin(self):
        settings = _make_settings(
            APP_ENV="production",
            CORS_ORIGINS=["https://app.example.com"],
        )
        app = _build_app(settings)
        client = TestClient(app)
        resp = client.get(
            "/v1/health",
            headers={"Origin": "http://evil.example.com"},
        )
        assert resp.status_code == 200
        # Unknown origin should NOT get an access-control-allow-origin header
        assert resp.headers.get("access-control-allow-origin") is None

    def test_prod_allows_listed_origin(self):
        settings = _make_settings(
            APP_ENV="production",
            CORS_ORIGINS=["https://app.example.com"],
        )
        app = _build_app(settings)
        client = TestClient(app)
        resp = client.get(
            "/v1/health",
            headers={"Origin": "https://app.example.com"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "https://app.example.com"


# ---------------------------------------------------------------------------
# Preflight OPTIONS handled
# ---------------------------------------------------------------------------

class TestPreflightOptionsHandled:
    def test_preflight_options_handled(self):
        settings = _make_settings(APP_ENV="development")
        app = _build_app(settings)
        client = TestClient(app)
        resp = client.options(
            "/v1/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-methods" in resp.headers
