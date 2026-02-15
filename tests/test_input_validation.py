"""B-703 – Input Validation Guardrails tests."""

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
    return s


def _get_client(settings: Settings | None = None) -> TestClient:
    if settings is None:
        settings = _make_settings()
    from app.config import get_settings
    from app.main import app
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


# ---------------------------------------------------------------------------
# employee_id validation
# ---------------------------------------------------------------------------

class TestEmptyEmployeeId:
    def test_empty_employee_id_returns_422(self):
        client = _get_client()
        resp = client.post("/v1/query", json={"employee_id": "", "question": "dental"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"


class TestInvalidEmployeeIdFormat:
    def test_lowercase_rejected(self):
        client = _get_client()
        resp = client.post("/v1/query", json={"employee_id": "emp001", "question": "dental"})
        assert resp.status_code == 422

    def test_no_digits_rejected(self):
        client = _get_client()
        resp = client.post("/v1/query", json={"employee_id": "EMPLOYEE", "question": "dental"})
        assert resp.status_code == 422

    def test_too_long_rejected(self):
        client = _get_client()
        resp = client.post("/v1/query", json={"employee_id": "A" * 21, "question": "dental"})
        assert resp.status_code == 422

    def test_special_chars_rejected(self):
        client = _get_client()
        resp = client.post("/v1/query", json={"employee_id": "EMP@01", "question": "dental"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# question validation
# ---------------------------------------------------------------------------

class TestOversizedQuestion:
    def test_oversized_question_returns_422(self):
        client = _get_client()
        resp = client.post("/v1/query", json={"employee_id": "EMP001", "question": "x" * 501})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_empty_question_returns_422(self):
        client = _get_client()
        resp = client.post("/v1/query", json={"employee_id": "EMP001", "question": ""})
        assert resp.status_code == 422

    def test_whitespace_only_question_returns_422(self):
        client = _get_client()
        resp = client.post("/v1/query", json={"employee_id": "EMP001", "question": "   "})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Extra fields rejected
# ---------------------------------------------------------------------------

class TestExtraFieldsRejected:
    def test_extra_fields_422(self):
        client = _get_client()
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "dental", "hacker": "payload"},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# Valid input passes
# ---------------------------------------------------------------------------

class TestValidInputPasses:
    def test_valid_input_accepted(self):
        client = _get_client()
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "Am I covered for dental?"},
        )
        # Should not be a validation error (200 or 404 depending on employee)
        assert resp.status_code != 422
        assert resp.status_code != 401
        assert resp.status_code != 403

    def test_whitespace_stripped(self):
        client = _get_client()
        resp = client.post(
            "/v1/query",
            json={"employee_id": "EMP001", "question": "  dental cleaning  "},
        )
        assert resp.status_code != 422
