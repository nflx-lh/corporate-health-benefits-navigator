"""Integration tests for POST /v1/query endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

RESPONSE_KEYS = {
    "query_id",
    "employee_id",
    "decision",
    "benefit_type",
    "service_category",
    "reason_summary",
    "reason_codes",
    "matched_rule_ids",
    "required_docs",
    "preauth_required",
    "coverage_percent",
    "annual_limit_sgd",
    "co_pay_sgd",
    "decision_path",
}


class TestUnknownEmployee:
    """Unknown employee_id => 404 + EMPLOYEE_NOT_FOUND."""

    def test_404_structure(self):
        resp = client.post("/v1/query", json={"employee_id": "UNK001", "question": "dental"})
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "EMPLOYEE_NOT_FOUND"
        assert "UNK001" in body["error"]["message"]


class TestInsufficientInfo:
    """EMP025 has missing name and tenure_months => insufficient_info."""

    def test_emp025_insufficient(self):
        resp = client.post("/v1/query", json={"employee_id": "EMP025", "question": "dental cleaning"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "insufficient_info"
        assert "MISSING_TENURE_MONTHS" in body["reason_codes"]
        assert isinstance(body["required_docs"], list)
        assert body["required_docs"] == []
        assert body["coverage_percent"] is None
        assert body["annual_limit_sgd"] is None
        assert body["co_pay_sgd"] is None
        assert body["preauth_required"] is None

    def test_ambiguous_query(self):
        resp = client.post("/v1/query", json={"employee_id": "EMP001", "question": "something random"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "insufficient_info"
        assert "AMBIGUOUS_BENEFIT_TYPE" in body["reason_codes"]


class TestInactiveEmployee:
    """EMP026 is inactive => not_covered with financial nulls."""

    def test_emp026_inactive(self):
        resp = client.post("/v1/query", json={"employee_id": "EMP026", "question": "dental cleaning"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "not_covered"
        assert "EMPLOYEE_INACTIVE" in body["reason_codes"]
        assert body["required_docs"] == []
        assert body["coverage_percent"] is None
        assert body["annual_limit_sgd"] is None
        assert body["co_pay_sgd"] is None
        assert body["preauth_required"] is None


class TestOrthodonticsExclusion:
    """Orthodontics excluded => not_covered with financial nulls."""

    def test_orthodontics(self):
        resp = client.post("/v1/query", json={"employee_id": "EMP002", "question": "orthodontics braces"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "not_covered"
        assert "EXCLUSION" in body["reason_codes"]
        assert body["required_docs"] == []
        assert body["coverage_percent"] is None


class TestServiceSpecificPrecedence:
    """Service-specific rule beats general rule."""

    def test_mri_diagnostic_imaging(self):
        resp = client.post("/v1/query", json={"employee_id": "EMP001", "question": "I need an MRI"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "covered"
        assert body["service_category"] == "diagnostic_imaging"
        assert "R019" in body["matched_rule_ids"]

    def test_root_canal(self):
        resp = client.post("/v1/query", json={"employee_id": "EMP001", "question": "root canal"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "covered"
        assert "R038" in body["matched_rule_ids"]


class TestResponseSchemaConsistency:
    """All response keys present in every outcome."""

    def test_covered_keys(self):
        resp = client.post("/v1/query", json={"employee_id": "EMP001", "question": "dental cleaning"})
        assert resp.status_code == 200
        assert set(resp.json().keys()) == RESPONSE_KEYS

    def test_not_covered_keys(self):
        resp = client.post("/v1/query", json={"employee_id": "EMP026", "question": "dental cleaning"})
        assert resp.status_code == 200
        assert set(resp.json().keys()) == RESPONSE_KEYS

    def test_insufficient_keys(self):
        resp = client.post("/v1/query", json={"employee_id": "EMP025", "question": "dental cleaning"})
        assert resp.status_code == 200
        assert set(resp.json().keys()) == RESPONSE_KEYS


class TestRequiredDocsAlwaysList:
    """required_docs is always a list, never null/string."""

    def test_covered(self):
        body = client.post("/v1/query", json={"employee_id": "EMP001", "question": "dental cleaning"}).json()
        assert isinstance(body["required_docs"], list)

    def test_not_covered(self):
        body = client.post("/v1/query", json={"employee_id": "EMP026", "question": "dental"}).json()
        assert isinstance(body["required_docs"], list)

    def test_insufficient(self):
        body = client.post("/v1/query", json={"employee_id": "EMP025", "question": "dental"}).json()
        assert isinstance(body["required_docs"], list)
