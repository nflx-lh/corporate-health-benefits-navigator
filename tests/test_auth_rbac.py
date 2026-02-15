"""B-702 – RBAC Enforcement Matrix tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.config import Settings
from app.auth.jwt_handler import create_token


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
    return s


def _get_client(settings: Settings | None = None) -> TestClient:
    if settings is None:
        settings = _make_settings()
    from app.config import get_settings
    from app.main import app
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _auth_header(employee_id: str, role: str, settings: Settings) -> dict:
    token = create_token(employee_id, role, settings)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Permission matrix: employee role
# ---------------------------------------------------------------------------

class TestEmployeeCanAccessQuery:
    def test_employee_can_access_query(self):
        settings = _make_settings()
        client = _get_client(settings)
        headers = _auth_header("EMP001", "employee", settings)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "Am I covered for dental?"},
            headers=headers,
        )
        assert resp.status_code != 401
        assert resp.status_code != 403

    def test_employee_can_access_query_orchestrated(self):
        settings = _make_settings()
        client = _get_client(settings)
        headers = _auth_header("EMP001", "employee", settings)
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "Am I covered for dental?"},
            headers=headers,
        )
        assert resp.status_code != 401
        assert resp.status_code != 403


class TestEmployeeCannotAccessAdmin:
    def test_employee_blocked_from_admin(self):
        settings = _make_settings()
        client = _get_client(settings)
        headers = _auth_header("EMP001", "employee", settings)
        resp = client.post("/v1/admin/reindex", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# Permission matrix: hr_admin role
# ---------------------------------------------------------------------------

class TestHrAdminCanAccessAdmin:
    def test_hr_admin_can_access_admin(self):
        settings = _make_settings()
        client = _get_client(settings)
        headers = _auth_header("HR001", "hr_admin", settings)
        resp = client.post("/v1/admin/reindex", headers=headers)
        assert resp.status_code == 200

    def test_hr_admin_can_access_query(self):
        settings = _make_settings()
        client = _get_client(settings)
        headers = _auth_header("HR001", "hr_admin", settings)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "Am I covered for dental?"},
            headers=headers,
        )
        assert resp.status_code != 401
        assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Unknown / invalid roles
# ---------------------------------------------------------------------------

class TestUnknownRoleForbidden:
    def test_unknown_role_blocked(self):
        settings = _make_settings()
        client = _get_client(settings)
        headers = _auth_header("EMP001", "viewer", settings)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental"},
            headers=headers,
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# Dev mode: all routes accessible without tokens
# ---------------------------------------------------------------------------

class TestDevModeAllowsAll:
    """In dev mode, get_current_user returns role=hr_admin, so all routes pass."""

    def test_dev_query_no_token(self):
        settings = _make_settings(APP_ENV="development")
        client = _get_client(settings)
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "Am I covered for dental?"},
        )
        assert resp.status_code != 401
        assert resp.status_code != 403

    def test_dev_admin_no_token(self):
        settings = _make_settings(APP_ENV="development")
        client = _get_client(settings)
        resp = client.post("/v1/admin/reindex")
        assert resp.status_code == 200

    def test_dev_query_orchestrated_no_token(self):
        settings = _make_settings(APP_ENV="development")
        client = _get_client(settings)
        resp = client.post(
            "/v1/query-orchestrated",
            json={"employee_id": "EMP001", "question": "Am I covered for dental?"},
        )
        assert resp.status_code != 401
        assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Public endpoints (no auth required)
# ---------------------------------------------------------------------------

class TestPublicEndpoints:
    """Health and login endpoints remain public regardless of APP_ENV."""

    def test_health_no_auth_staging(self):
        settings = _make_settings(APP_ENV="staging")
        client = _get_client(settings)
        resp = client.get("/v1/health")
        assert resp.status_code == 200

    def test_login_no_auth_staging(self):
        settings = _make_settings(APP_ENV="staging")
        client = _get_client(settings)
        resp = client.post(
            "/v1/auth/login",
            json={"employee_id": "EMP001", "password": "password123"},
        )
        assert resp.status_code == 200
