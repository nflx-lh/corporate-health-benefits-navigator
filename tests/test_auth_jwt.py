"""B-701 – JWT Hardening & Claims Validation tests."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.auth.jwt_handler import create_token, decode_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    """Return a Settings instance with test-friendly defaults."""
    s = Settings()
    s.APP_ENV = overrides.get("APP_ENV", "staging")
    s.JWT_SECRET = overrides.get("JWT_SECRET", "test-secret-32chars-minimum-here")
    s.JWT_ALGORITHM = overrides.get("JWT_ALGORITHM", "HS256")
    s.JWT_EXPIRE_MINUTES = overrides.get("JWT_EXPIRE_MINUTES", 60)
    s.JWT_AUDIENCE = overrides.get("JWT_AUDIENCE", "chbn-api")
    return s


def _get_client(settings: Settings | None = None) -> TestClient:
    """Build a fresh TestClient with overridden settings."""
    if settings is None:
        settings = _make_settings()

    from app.config import get_settings
    from app.main import app

    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    return client


# ---------------------------------------------------------------------------
# Unit: create / decode round-trip
# ---------------------------------------------------------------------------

class TestCreateAndDecodeToken:
    def test_round_trip(self):
        settings = _make_settings()
        token = create_token("EMP001", "employee", settings)
        claims = decode_token(token, settings)
        assert claims["sub"] == "EMP001"
        assert claims["role"] == "employee"
        assert claims["aud"] == "chbn-api"
        assert "exp" in claims
        assert "iat" in claims

    def test_all_required_claims_present(self):
        settings = _make_settings()
        token = create_token("HR001", "hr_admin", settings)
        claims = decode_token(token, settings)
        for claim in ("sub", "role", "exp", "iat", "aud"):
            assert claim in claims, f"Missing required claim: {claim}"


# ---------------------------------------------------------------------------
# Unit: decode error cases
# ---------------------------------------------------------------------------

class TestExpiredToken:
    def test_expired_token_raises(self):
        settings = _make_settings(JWT_EXPIRE_MINUTES=0)
        # Create a token that is already expired
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "EMP001",
            "role": "employee",
            "iat": now - timedelta(minutes=5),
            "exp": now - timedelta(seconds=1),
            "aud": settings.JWT_AUDIENCE,
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token, settings)


class TestInvalidToken:
    def test_garbage_token_raises(self):
        settings = _make_settings()
        with pytest.raises(jwt.DecodeError):
            decode_token("not.a.jwt", settings)

    def test_empty_string_raises(self):
        settings = _make_settings()
        with pytest.raises(jwt.DecodeError):
            decode_token("", settings)


class TestInvalidSignature:
    def test_wrong_secret_raises(self):
        settings = _make_settings()
        token = create_token("EMP001", "employee", settings)
        tampered_settings = _make_settings(JWT_SECRET="wrong-secret-definitely-not-correct")
        with pytest.raises(jwt.InvalidSignatureError):
            decode_token(token, tampered_settings)


class TestMissingAudClaim:
    def test_missing_aud_raises(self):
        settings = _make_settings()
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "EMP001",
            "role": "employee",
            "iat": now,
            "exp": now + timedelta(minutes=60),
            # aud intentionally omitted
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises((jwt.MissingRequiredClaimError, jwt.InvalidAudienceError)):
            decode_token(token, settings)

    def test_wrong_aud_raises(self):
        settings = _make_settings()
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "EMP001",
            "role": "employee",
            "iat": now,
            "exp": now + timedelta(minutes=60),
            "aud": "wrong-audience",
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(jwt.InvalidAudienceError):
            decode_token(token, settings)


# ---------------------------------------------------------------------------
# Integration: /v1/auth/login endpoint
# ---------------------------------------------------------------------------

class TestLoginEndpoint:
    def test_valid_login_returns_jwt(self):
        settings = _make_settings()
        client = _get_client(settings)
        resp = client.post("/v1/auth/login", json={"employee_id": "EMP001", "password": "password123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "employee"
        assert data["must_reset_password"] is False
        # Verify the returned token is valid
        claims = decode_token(data["access_token"], settings)
        assert claims["sub"] == "EMP001"

    def test_invalid_password_returns_401(self):
        client = _get_client()
        resp = client.post("/v1/auth/login", json={"employee_id": "EMP001", "password": "wrong"})
        assert resp.status_code == 401

    def test_unknown_employee_returns_401(self):
        client = _get_client()
        resp = client.post("/v1/auth/login", json={"employee_id": "UNKNOWN", "password": "password123"})
        assert resp.status_code == 401

    def test_hr_admin_login(self):
        settings = _make_settings()
        client = _get_client(settings)
        resp = client.post("/v1/auth/login", json={"employee_id": "HR001", "password": "hradmin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "hr_admin"
        claims = decode_token(data["access_token"], settings)
        assert claims["role"] == "hr_admin"


# ---------------------------------------------------------------------------
# Integration: HTTP error responses for protected endpoints
# ---------------------------------------------------------------------------

class TestProtectedEndpointErrors:
    """Verify the HTTP error contract for auth failures in non-dev mode."""

    def _auth_settings(self):
        return _make_settings(APP_ENV="staging")

    def test_expired_token_returns_401(self):
        settings = self._auth_settings()
        client = _get_client(settings)
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "EMP001", "role": "employee",
            "iat": now - timedelta(minutes=5),
            "exp": now - timedelta(seconds=1),
            "aud": settings.JWT_AUDIENCE,
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_EXPIRED"

    def test_invalid_token_returns_401(self):
        settings = self._auth_settings()
        client = _get_client(settings)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": "Bearer garbage.token.here"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_TOKEN"

    def test_invalid_signature_returns_403(self):
        settings = self._auth_settings()
        client = _get_client(settings)
        # Create token with different secret
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "EMP001", "role": "employee",
            "iat": now,
            "exp": now + timedelta(minutes=60),
            "aud": settings.JWT_AUDIENCE,
        }
        token = jwt.encode(payload, "completely-different-secret-key!!", algorithm="HS256")
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "INVALID_SIGNATURE"

    def test_missing_aud_claim_returns_401(self):
        settings = self._auth_settings()
        client = _get_client(settings)
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "EMP001", "role": "employee",
            "iat": now,
            "exp": now + timedelta(minutes=60),
            # no aud
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    def test_no_auth_header_returns_401(self):
        settings = self._auth_settings()
        client = _get_client(settings)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_TOKEN"


# ---------------------------------------------------------------------------
# Integration: dev mode bypasses auth
# ---------------------------------------------------------------------------

class TestDevModeBypassesAuth:
    """Verify APP_ENV=development skips JWT validation."""

    def test_dev_mode_no_token_succeeds(self):
        settings = _make_settings(APP_ENV="development")
        client = _get_client(settings)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "Am I covered for dental?"},
        )
        # Should succeed (not 401); the actual status depends on employee lookup
        assert resp.status_code != 401
        assert resp.status_code != 403

    def test_dev_mode_with_valid_token_also_works(self):
        settings = _make_settings(APP_ENV="development")
        client = _get_client(settings)
        token = create_token("EMP001", "employee", settings)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "Am I covered for dental?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code != 401
        assert resp.status_code != 403
