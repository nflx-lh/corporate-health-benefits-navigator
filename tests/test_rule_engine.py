"""Unit tests for the deterministic rules engine."""

import pytest

from app.services.employee_repo import EmployeeRecord
from app.services.query_parser import parse_query, ParsedQuery
from app.services.rules_engine import evaluate

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


def _make_employee(**overrides) -> EmployeeRecord:
    defaults = {
        "employee_id": "TEST001",
        "name": "Test User",
        "age": "30",
        "employment_type": "full_time",
        "plan_tier": "plus",
        "tenure_months": "24",
        "dependents_count": "0",
        "is_active": "true",
    }
    defaults.update(overrides)
    return EmployeeRecord(defaults)


class TestResponseSchemaKeys:
    """All response keys must always be present regardless of decision."""

    def test_covered_has_all_keys(self):
        emp = _make_employee()
        parsed = parse_query("dental cleaning")
        resp = evaluate(emp, parsed)
        assert set(resp.model_dump().keys()) == RESPONSE_KEYS

    def test_not_covered_has_all_keys(self):
        emp = _make_employee(is_active="false")
        parsed = parse_query("dental cleaning")
        resp = evaluate(emp, parsed)
        assert set(resp.model_dump().keys()) == RESPONSE_KEYS

    def test_insufficient_has_all_keys(self):
        emp = _make_employee(tenure_months="")
        parsed = parse_query("dental cleaning")
        resp = evaluate(emp, parsed)
        assert set(resp.model_dump().keys()) == RESPONSE_KEYS


class TestRequiredDocsAlwaysList:
    """required_docs must always be a list across all outcomes."""

    def test_covered_docs_is_list(self):
        emp = _make_employee()
        resp = evaluate(emp, parse_query("dental cleaning"))
        assert isinstance(resp.required_docs, list)

    def test_not_covered_docs_is_list(self):
        emp = _make_employee(is_active="false")
        resp = evaluate(emp, parse_query("dental"))
        assert isinstance(resp.required_docs, list)
        assert resp.required_docs == []

    def test_insufficient_docs_is_list(self):
        emp = _make_employee(tenure_months="")
        resp = evaluate(emp, parse_query("dental"))
        assert isinstance(resp.required_docs, list)
        assert resp.required_docs == []


class TestMissingProfileFields:
    """Missing employee data -> insufficient_info with reason_codes."""

    def test_missing_tenure(self):
        emp = _make_employee(tenure_months="")
        resp = evaluate(emp, parse_query("dental cleaning"))
        assert resp.decision == "insufficient_info"
        assert "MISSING_TENURE_MONTHS" in resp.reason_codes

    def test_missing_plan_tier(self):
        emp = _make_employee(plan_tier="")
        resp = evaluate(emp, parse_query("dental cleaning"))
        assert resp.decision == "insufficient_info"
        assert "MISSING_PLAN_TIER" in resp.reason_codes

    def test_financial_fields_null_for_insufficient(self):
        emp = _make_employee(tenure_months="")
        resp = evaluate(emp, parse_query("dental cleaning"))
        assert resp.coverage_percent is None
        assert resp.annual_limit_sgd is None
        assert resp.co_pay_sgd is None
        assert resp.preauth_required is None


class TestAmbiguousBenefitType:
    """When query text cannot be mapped -> AMBIGUOUS_BENEFIT_TYPE."""

    def test_gibberish_query(self):
        emp = _make_employee()
        resp = evaluate(emp, parse_query("xyzzy foobar"))
        assert resp.decision == "insufficient_info"
        assert "AMBIGUOUS_BENEFIT_TYPE" in resp.reason_codes


class TestInactiveEmployee:
    """Inactive employee -> not_covered with financial nulls."""

    def test_inactive_not_covered(self):
        emp = _make_employee(is_active="false")
        resp = evaluate(emp, parse_query("dental cleaning"))
        assert resp.decision == "not_covered"
        assert "EMPLOYEE_INACTIVE" in resp.reason_codes
        assert resp.required_docs == []
        assert resp.coverage_percent is None
        assert resp.annual_limit_sgd is None
        assert resp.co_pay_sgd is None
        assert resp.preauth_required is None


class TestExclusions:
    """Exclusion rules -> not_covered with financial nulls."""

    def test_orthodontics_excluded(self):
        emp = _make_employee(plan_tier="plus")
        resp = evaluate(emp, parse_query("orthodontics"))
        assert resp.decision == "not_covered"
        assert "EXCLUSION" in resp.reason_codes
        assert resp.required_docs == []
        assert resp.coverage_percent is None
        assert resp.annual_limit_sgd is None
        assert resp.co_pay_sgd is None
        assert resp.preauth_required is None

    def test_basic_dental_excluded(self):
        emp = _make_employee(plan_tier="basic")
        resp = evaluate(emp, parse_query("dental cleaning"))
        assert resp.decision == "not_covered"
        assert "EXCLUSION" in resp.reason_codes


class TestServiceSpecificPrecedence:
    """Service-specific rule should beat general_consult rule."""

    def test_mri_gets_diagnostic_imaging_rule(self):
        emp = _make_employee(plan_tier="premium")
        resp = evaluate(emp, parse_query("I need an MRI scan"))
        assert resp.decision == "covered"
        assert resp.service_category == "diagnostic_imaging"
        # R019 is the diagnostic_imaging rule for premium full_time
        assert "R019" in resp.matched_rule_ids

    def test_root_canal_gets_specific_rule(self):
        emp = _make_employee(plan_tier="premium")
        resp = evaluate(emp, parse_query("root canal treatment"))
        assert resp.decision == "covered"
        assert resp.service_category == "root_canal"
        assert "R038" in resp.matched_rule_ids


class TestCoveredResponse:
    """Covered responses must populate financial + docs fields."""

    def test_covered_dental_cleaning_plus(self):
        emp = _make_employee(plan_tier="plus", tenure_months="6")
        resp = evaluate(emp, parse_query("dental cleaning"))
        assert resp.decision == "covered"
        assert resp.benefit_type == "dental"
        assert resp.coverage_percent is not None
        assert resp.annual_limit_sgd is not None
        assert resp.co_pay_sgd is not None
        assert resp.preauth_required is not None
        assert len(resp.required_docs) > 0
        assert len(resp.matched_rule_ids) > 0

    def test_outpatient_general_consult(self):
        emp = _make_employee(plan_tier="plus", tenure_months="6")
        resp = evaluate(emp, parse_query("I need to see a doctor"))
        assert resp.decision == "covered"
        assert resp.benefit_type == "outpatient"
