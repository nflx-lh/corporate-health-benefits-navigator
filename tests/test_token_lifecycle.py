"""B-710 – Token Lifecycle / Auth Error Contract Tests.

Comprehensive integration tests covering the full token lifecycle:
  Login → get token → use token → token expires → 401
  Invalid token format → 401
  Tampered token (wrong signature) → 403
  Token with wrong audience → 401
  Token with missing claims → 401
  Expired then re-login → new token works
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.auth.jwt_handler import create_token, decode_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    s = Settings()
    s.APP_ENV = overrides.get("APP_ENV", "staging")
    s.JWT_SECRET = overrides.get("JWT_SECRET", "test-secret-32chars-minimum-here")
    s.JWT_ALGORITHM = overrides.get("JWT_ALGORITHM", "HS256")
    s.JWT_EXPIRE_MINUTES = overrides.get("JWT_EXPIRE_MINUTES", 60)
    s.JWT_AUDIENCE = overrides.get("JWT_AUDIENCE", "chbn-api")
    s.RATE_LIMIT = overrides.get("RATE_LIMIT", "1000/minute")
    s.CORS_ORIGINS = []
    return s


def _get_client(settings: Settings) -> TestClient:
    from app.main import app
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


# ---------------------------------------------------------------------------
# Full lifecycle: login → use → expire → 401
# ---------------------------------------------------------------------------

class TestFullTokenLifecycle:
    def test_login_get_token_use_token(self):
        """Login → get a valid JWT → use it to query → success."""
        settings = _make_settings()
        client = _get_client(settings)

        # Login
        login_resp = client.post(
            "/v1/auth/login",
            json={"employee_id": "EMP001", "password": "password123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        # Use token to query
        query_resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "Am I covered for dental?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert query_resp.status_code == 200
        assert query_resp.json()["employee_id"] == "EMP001"

    def test_expired_token_returns_401(self):
        """An expired token produces a 401 with TOKEN_EXPIRED code."""
        settings = _make_settings()
        client = _get_client(settings)
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "EMP001", "role": "employee",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(seconds=1),
            "aud": settings.JWT_AUDIENCE,
        }
        expired_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_EXPIRED"


# ---------------------------------------------------------------------------
# Invalid token format → 401
# ---------------------------------------------------------------------------

class TestInvalidTokenFormat:
    def test_garbage_string_returns_401(self):
        settings = _make_settings()
        client = _get_client(settings)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": "Bearer not-a-real-jwt"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_TOKEN"

    def test_empty_bearer_returns_401(self):
        settings = _make_settings()
        client = _get_client(settings)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401

    def test_no_bearer_prefix_returns_401(self):
        settings = _make_settings()
        client = _get_client(settings)
        token = create_token("EMP001", "employee", settings)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": token},  # Missing "Bearer " prefix
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tampered token (wrong signature) → 403
# ---------------------------------------------------------------------------

class TestTamperedToken:
    def test_wrong_signature_returns_403(self):
        settings = _make_settings()
        client = _get_client(settings)
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "EMP001", "role": "employee",
            "iat": now,
            "exp": now + timedelta(minutes=60),
            "aud": settings.JWT_AUDIENCE,
        }
        tampered = jwt.encode(payload, "totally-wrong-secret-key-here!!", algorithm="HS256")
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "INVALID_SIGNATURE"


# ---------------------------------------------------------------------------
# Token with wrong audience → 401
# ---------------------------------------------------------------------------

class TestWrongAudience:
    def test_wrong_audience_returns_401(self):
        settings = _make_settings()
        client = _get_client(settings)
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "EMP001", "role": "employee",
            "iat": now,
            "exp": now + timedelta(minutes=60),
            "aud": "wrong-audience",
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_TOKEN"


# ---------------------------------------------------------------------------
# Token with missing claims → 401
# ---------------------------------------------------------------------------

class TestMissingClaims:
    def test_missing_sub_returns_401(self):
        settings = _make_settings()
        client = _get_client(settings)
        now = datetime.now(timezone.utc)
        payload = {
            "role": "employee",
            "iat": now,
            "exp": now + timedelta(minutes=60),
            "aud": settings.JWT_AUDIENCE,
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    def test_missing_role_returns_401(self):
        settings = _make_settings()
        client = _get_client(settings)
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "EMP001",
            "iat": now,
            "exp": now + timedelta(minutes=60),
            "aud": settings.JWT_AUDIENCE,
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Expired then re-login → new token works
# ---------------------------------------------------------------------------

class TestExpiredThenReLogin:
    def test_expired_then_relogin_works(self):
        """After token expires, a new login produces a working token."""
        settings = _make_settings()
        client = _get_client(settings)

        # Create an expired token
        now = datetime.now(timezone.utc)
        expired_payload = {
            "sub": "EMP001", "role": "employee",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(seconds=1),
            "aud": settings.JWT_AUDIENCE,
        }
        expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        # Verify it's rejected
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

        # Re-login
        login_resp = client.post(
            "/v1/auth/login",
            json={"employee_id": "EMP001", "password": "password123"},
        )
        assert login_resp.status_code == 200
        new_token = login_resp.json()["access_token"]

        # New token works
        query_resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "Am I covered for dental?"},
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert query_resp.status_code == 200
        assert query_resp.json()["decision"] in ("covered", "not_covered", "insufficient_info")
