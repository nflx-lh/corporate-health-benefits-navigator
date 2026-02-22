"""Tests for password reset flow: request reset, admin approve/reject,
change password, and login with DB credentials."""

import os

os.environ.setdefault("APP_ENV", "development")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.session import Base
from app.models.employee_db import EmployeeDB  # noqa: F401
from app.models.password_reset_db import PasswordResetRequestDB  # noqa: F401
from app.api.routes_employee_crud import get_db
from app.api.routes_auth import _get_db_optional
from app.auth.dependencies import get_current_user
from app.auth.password import hash_password
from app.main import app

# In-memory SQLite with StaticPool
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(_engine)
_TestSession = sessionmaker(bind=_engine)


def _override_get_db():
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


_HR_USER = {"sub": "HR001", "role": "hr_admin"}
_EMP_USER = {"sub": "TST001", "role": "employee"}


@pytest.fixture(autouse=True)
def _setup_and_cleanup():
    """Set up dependency overrides, clean up after each test."""
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[_get_db_optional] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _HR_USER
    yield
    # Clean up test data
    with _TestSession() as s:
        s.query(PasswordResetRequestDB).delete()
        s.query(EmployeeDB).delete()
        s.commit()
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(_get_db_optional, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def emp_in_db():
    """Create a test employee with a known password in the DB."""
    with _TestSession() as s:
        emp = EmployeeDB(
            employee_id="TST001",
            name="Test User",
            password_hash=hash_password("oldpassword123"),
            must_reset_password=False,
        )
        s.add(emp)
        s.commit()
    return "TST001"


@pytest.fixture()
def emp_must_reset():
    """Create a test employee with must_reset_password=True."""
    with _TestSession() as s:
        emp = EmployeeDB(
            employee_id="TST002",
            name="Reset User",
            password_hash=hash_password("temppass12345"),
            must_reset_password=True,
        )
        s.add(emp)
        s.commit()
    return "TST002"


# ---------------------------------------------------------------------------
# Request Password Reset
# ---------------------------------------------------------------------------

class TestRequestPasswordReset:
    def test_request_reset_employee_exists(self, client, emp_in_db):
        resp = client.post(
            "/v1/auth/employee/request-password-reset",
            json={"employee_id": emp_in_db},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Verify request was created
        with _TestSession() as s:
            req = s.query(PasswordResetRequestDB).filter_by(employee_id=emp_in_db).first()
            assert req is not None
            assert req.status == "pending"

    def test_request_reset_employee_not_found(self, client):
        resp = client.post(
            "/v1/auth/employee/request-password-reset",
            json={"employee_id": "NOPE001"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True  # No info leak

    def test_duplicate_pending_request_blocked(self, client, emp_in_db):
        client.post(
            "/v1/auth/employee/request-password-reset",
            json={"employee_id": emp_in_db},
        )
        client.post(
            "/v1/auth/employee/request-password-reset",
            json={"employee_id": emp_in_db},
        )
        # Should still be only one pending request
        with _TestSession() as s:
            count = (
                s.query(PasswordResetRequestDB)
                .filter_by(employee_id=emp_in_db, status="pending")
                .count()
            )
            assert count == 1


# ---------------------------------------------------------------------------
# Admin: List Pending Requests
# ---------------------------------------------------------------------------

class TestAdminListResetRequests:
    def test_list_pending_requests(self, client, emp_in_db):
        # Create a pending request
        client.post(
            "/v1/auth/employee/request-password-reset",
            json={"employee_id": emp_in_db},
        )
        resp = client.get("/v1/admin/password-reset-requests?status=pending")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["employee_id"] == emp_in_db
        assert data[0]["status"] == "pending"


# ---------------------------------------------------------------------------
# Admin: Approve Reset
# ---------------------------------------------------------------------------

class TestAdminApproveReset:
    def test_approve_returns_temp_password(self, client, emp_in_db):
        # Create a pending request
        client.post(
            "/v1/auth/employee/request-password-reset",
            json={"employee_id": emp_in_db},
        )
        # Get the request ID
        list_resp = client.get("/v1/admin/password-reset-requests?status=pending")
        request_id = list_resp.json()[0]["id"]

        # Approve
        resp = client.post(f"/v1/admin/password-reset-requests/{request_id}/reset")
        assert resp.status_code == 200
        assert "temp_password" in resp.json()
        assert len(resp.json()["temp_password"]) >= 8

        # Employee should now have must_reset_password=True
        with _TestSession() as s:
            emp = s.get(EmployeeDB, emp_in_db)
            assert emp.must_reset_password is True

        # Request should be completed
        with _TestSession() as s:
            req = s.get(PasswordResetRequestDB, request_id)
            assert req.status == "completed"


# ---------------------------------------------------------------------------
# Admin: Reject Reset
# ---------------------------------------------------------------------------

class TestAdminRejectReset:
    def test_reject_marks_request_rejected(self, client, emp_in_db):
        client.post(
            "/v1/auth/employee/request-password-reset",
            json={"employee_id": emp_in_db},
        )
        list_resp = client.get("/v1/admin/password-reset-requests?status=pending")
        request_id = list_resp.json()[0]["id"]

        resp = client.post(
            f"/v1/admin/password-reset-requests/{request_id}/reject",
            json={"notes": "Not verified"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        with _TestSession() as s:
            req = s.get(PasswordResetRequestDB, request_id)
            assert req.status == "rejected"
            assert req.notes == "Not verified"


# ---------------------------------------------------------------------------
# Login with DB credentials
# ---------------------------------------------------------------------------

class TestLoginWithDbCredentials:
    def test_login_with_db_password(self, client, emp_in_db):
        resp = client.post(
            "/v1/auth/login",
            json={"employee_id": emp_in_db, "password": "oldpassword123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "employee"
        assert data["must_reset_password"] is False

    def test_login_with_wrong_db_password(self, client, emp_in_db):
        resp = client.post(
            "/v1/auth/login",
            json={"employee_id": emp_in_db, "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_must_reset_password_flag(self, client, emp_must_reset):
        resp = client.post(
            "/v1/auth/login",
            json={"employee_id": emp_must_reset, "password": "temppass12345"},
        )
        assert resp.status_code == 200
        assert resp.json()["must_reset_password"] is True


# ---------------------------------------------------------------------------
# Change Password
# ---------------------------------------------------------------------------

class TestChangePassword:
    def test_change_password_success(self, client, emp_in_db):
        app.dependency_overrides[get_current_user] = lambda: _EMP_USER
        resp = client.post(
            "/v1/auth/employee/change-password",
            json={"current_password": "oldpassword123", "new_password": "newpassword456"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # must_reset_password should be False
        with _TestSession() as s:
            emp = s.get(EmployeeDB, emp_in_db)
            assert emp.must_reset_password is False

    def test_change_password_wrong_current(self, client, emp_in_db):
        app.dependency_overrides[get_current_user] = lambda: _EMP_USER
        resp = client.post(
            "/v1/auth/employee/change-password",
            json={"current_password": "wrongpassword", "new_password": "newpassword456"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_change_password_too_short(self, client, emp_in_db):
        app.dependency_overrides[get_current_user] = lambda: _EMP_USER
        resp = client.post(
            "/v1/auth/employee/change-password",
            json={"current_password": "oldpassword123", "new_password": "short"},
        )
        assert resp.status_code == 422

    def test_change_password_clears_must_reset(self, client, emp_must_reset):
        app.dependency_overrides[get_current_user] = lambda: {"sub": "TST002", "role": "employee"}
        resp = client.post(
            "/v1/auth/employee/change-password",
            json={"current_password": "temppass12345", "new_password": "mynewpassword1"},
        )
        assert resp.status_code == 200
        with _TestSession() as s:
            emp = s.get(EmployeeDB, "TST002")
            assert emp.must_reset_password is False


# ---------------------------------------------------------------------------
# Employee Create with temp password
# ---------------------------------------------------------------------------

class TestEmployeeCreateWithTempPassword:
    def test_create_employee_returns_temp_password(self, client):
        resp = client.post("/v1/admin/employees", json={
            "employee_id": "NEW001",
            "name": "New User",
            "age": 25,
            "employment_type": "full_time",
            "plan_tier": "basic",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "temp_password" in data
        assert len(data["temp_password"]) >= 8
        assert data["employee_id"] == "NEW001"

        # Employee should have must_reset_password=True
        with _TestSession() as s:
            emp = s.get(EmployeeDB, "NEW001")
            assert emp.must_reset_password is True
            assert emp.password_hash is not None
