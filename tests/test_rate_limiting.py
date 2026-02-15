"""B-705 – Rate Limiting tests."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi.testclient import TestClient

from app.config import Settings, get_settings


# ---------------------------------------------------------------------------
# Helpers – build a minimal app with a tight rate limit for testing
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    s = Settings()
    s.APP_ENV = overrides.get("APP_ENV", "development")
    s.JWT_SECRET = overrides.get("JWT_SECRET", "test-secret-32chars-minimum-here")
    s.JWT_ALGORITHM = overrides.get("JWT_ALGORITHM", "HS256")
    s.JWT_EXPIRE_MINUTES = overrides.get("JWT_EXPIRE_MINUTES", 60)
    s.JWT_AUDIENCE = overrides.get("JWT_AUDIENCE", "chbn-api")
    s.RATE_LIMIT = overrides.get("RATE_LIMIT", "2/minute")
    s.CORS_ORIGINS = []
    return s


def _build_rate_limited_app(settings: Settings) -> FastAPI:
    """Build a fresh app with a very tight rate limit for testing."""
    test_limiter = Limiter(key_func=get_remote_address, default_limits=[])

    test_app = FastAPI()
    test_app.state.limiter = test_limiter

    @test_app.exception_handler(RateLimitExceeded)
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

    @test_app.post("/v1/test-limited")
    @test_limiter.limit(settings.RATE_LIMIT)
    def limited_endpoint(request: Request):
        return {"status": "ok"}

    @test_app.get("/v1/test-unlimited")
    def unlimited_endpoint():
        return {"status": "ok"}

    return test_app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWithinLimitSucceeds:
    def test_within_limit_succeeds(self):
        settings = _make_settings(RATE_LIMIT="5/minute")
        app = _build_rate_limited_app(settings)
        client = TestClient(app)
        resp = client.post("/v1/test-limited")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestExceedingLimitReturns429:
    def test_exceeding_limit_returns_429(self):
        settings = _make_settings(RATE_LIMIT="2/minute")
        app = _build_rate_limited_app(settings)
        client = TestClient(app)

        # First 2 requests should succeed
        for _ in range(2):
            resp = client.post("/v1/test-limited")
            assert resp.status_code == 200

        # 3rd request should be rate-limited
        resp = client.post("/v1/test-limited")
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    def test_unlimited_endpoint_not_affected(self):
        settings = _make_settings(RATE_LIMIT="1/minute")
        app = _build_rate_limited_app(settings)
        client = TestClient(app)

        # Exhaust the limited endpoint
        client.post("/v1/test-limited")
        resp = client.post("/v1/test-limited")
        assert resp.status_code == 429

        # Unlimited endpoint still works
        resp = client.get("/v1/test-unlimited")
        assert resp.status_code == 200
