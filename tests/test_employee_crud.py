"""Tests for Employee CRUD endpoints (HR Admin only).

Uses in-memory SQLite via FastAPI dependency override with StaticPool
to ensure all connections share the same in-memory database.
"""

import os

os.environ.setdefault("APP_ENV", "development")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.session import Base
from app.models.employee_db import EmployeeDB  # noqa: F401 — register model
from app.models.password_reset_db import PasswordResetRequestDB  # noqa: F401
from app.api.routes_employee_crud import get_db
from app.auth.dependencies import get_current_user
from app.main import app

# In-memory SQLite with StaticPool — single shared connection
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


_TEST_ID = "TST001"


@pytest.fixture(autouse=True)
def _setup_and_cleanup():
    """Set up dependency overrides before each test, clean up after."""
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"sub": "HR001", "role": "hr_admin"}
    yield
    # Clean up test data
    with _TestSession() as s:
        row = s.get(EmployeeDB, _TEST_ID)
        if row:
            s.delete(row)
            s.commit()
    # Remove overrides so they don't leak to other test files
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def client():
    return TestClient(app)


class TestCreateEmployee:
    def test_create_success(self, client):
        resp = client.post("/v1/admin/employees", json={
            "employee_id": _TEST_ID,
            "name": "Test User",
            "age": 30,
            "employment_type": "full_time",
            "plan_tier": "basic",
            "tenure_months": 12,
            "dependents_count": 1,
            "is_active": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["employee_id"] == _TEST_ID
        assert data["name"] == "Test User"
        assert data["age"] == 30
        assert data["is_active"] is True
        assert "temp_password" in data
        assert len(data["temp_password"]) >= 8

    def test_create_duplicate_returns_409(self, client):
        client.post("/v1/admin/employees", json={
            "employee_id": _TEST_ID,
            "name": "First",
        })
        resp = client.post("/v1/admin/employees", json={
            "employee_id": _TEST_ID,
            "name": "Duplicate",
        })
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "EMPLOYEE_EXISTS"

    def test_create_invalid_id_format(self, client):
        resp = client.post("/v1/admin/employees", json={
            "employee_id": "bad-id",
            "name": "Bad",
        })
        assert resp.status_code == 422


class TestReadEmployee:
    def test_read_success(self, client):
        client.post("/v1/admin/employees", json={
            "employee_id": _TEST_ID,
            "name": "Read Test",
        })
        resp = client.get(f"/v1/admin/employees/{_TEST_ID}")
        assert resp.status_code == 200
        assert resp.json()["employee_id"] == _TEST_ID
        assert resp.json()["name"] == "Read Test"

    def test_read_not_found(self, client):
        resp = client.get("/v1/admin/employees/ZZZ999")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "EMPLOYEE_NOT_FOUND"

    def test_read_invalid_id(self, client):
        resp = client.get("/v1/admin/employees/bad-id")
        assert resp.status_code == 422


class TestUpdateEmployee:
    def test_update_success(self, client):
        client.post("/v1/admin/employees", json={
            "employee_id": _TEST_ID,
            "name": "Original",
            "age": 25,
        })
        resp = client.put(f"/v1/admin/employees/{_TEST_ID}", json={
            "name": "Updated",
            "age": 26,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated"
        assert data["age"] == 26

    def test_update_partial(self, client):
        client.post("/v1/admin/employees", json={
            "employee_id": _TEST_ID,
            "name": "Original",
            "age": 25,
        })
        resp = client.put(f"/v1/admin/employees/{_TEST_ID}", json={
            "name": "Only Name Changed",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Only Name Changed"
        assert data["age"] == 25  # unchanged

    def test_update_not_found(self, client):
        resp = client.put("/v1/admin/employees/ZZZ999", json={"name": "Nope"})
        assert resp.status_code == 404


class TestDeleteEmployee:
    def test_delete_success(self, client):
        client.post("/v1/admin/employees", json={
            "employee_id": _TEST_ID,
            "name": "To Delete",
        })
        resp = client.delete(f"/v1/admin/employees/{_TEST_ID}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

        # Confirm gone
        resp = client.get(f"/v1/admin/employees/{_TEST_ID}")
        assert resp.status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/v1/admin/employees/ZZZ999")
        assert resp.status_code == 404
