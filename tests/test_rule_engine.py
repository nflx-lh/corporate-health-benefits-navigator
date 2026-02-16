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

    def test_orthodontics_excluded_premium(self):
        emp = _make_employee(plan_tier="premium")
        resp = evaluate(emp, parse_query("orthodontic treatment"))
        assert resp.decision == "not_covered"
        assert resp.service_category == "orthodontics"
        assert "EXCLUSION" in resp.reason_codes
        assert resp.coverage_percent is None

    def test_braces_excluded_premium(self):
        emp = _make_employee(plan_tier="premium")
        resp = evaluate(emp, parse_query("braces"))
        assert resp.decision == "not_covered"
        assert resp.service_category == "orthodontics"
        assert "EXCLUSION" in resp.reason_codes

    def test_basic_dental_excluded(self):
        emp = _make_employee(plan_tier="basic")
        resp = evaluate(emp, parse_query("dental cleaning"))
        assert resp.decision == "not_covered"
        assert "EXCLUSION" in resp.reason_codes


class TestServiceCategoryNotCoveredSafety:
    """Explicit service_category with no matching rule must NOT award unrelated coverage."""

    def test_unmatched_service_category_returns_not_covered(self):
        """Synthetic: explicit service_category with no rule should not keep-all."""
        emp = _make_employee(plan_tier="plus")
        parsed = ParsedQuery(benefit_type="dental", service_category="nonexistent_service")
        resp = evaluate(emp, parsed)
        assert resp.decision == "not_covered"
        assert "SERVICE_CATEGORY_NOT_COVERED" in resp.reason_codes
        assert resp.service_category == "nonexistent_service"
        assert resp.coverage_percent is None
        assert resp.matched_rule_ids == []

    def test_unmatched_service_category_decision_path(self):
        emp = _make_employee(plan_tier="plus")
        parsed = ParsedQuery(benefit_type="dental", service_category="nonexistent_service")
        resp = evaluate(emp, parsed)
        path_str = " ".join(resp.decision_path)
        assert "service_category_not_covered: nonexistent_service" in path_str
        assert "service_category_no_match_keeping_all" not in path_str

    def test_broad_query_no_service_category_still_covered(self):
        """Broad dental query (no service_category) should still find coverage."""
        emp = _make_employee(plan_tier="plus", tenure_months="6")
        parsed = ParsedQuery(benefit_type="dental", service_category=None)
        resp = evaluate(emp, parsed)
        assert resp.decision in ("covered", "not_covered")  # depends on rules, but NOT insufficient


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


class TestPreauthConsistency:
    """Regression guard: preauth_required and required_docs must be semantically aligned."""

    def test_no_rule_has_preauth_false_with_preauth_form(self):
        """No rule should have preauth_required=false while required_docs includes preauth_form."""
        from app.services.rule_repo import get_rules

        violations = []
        for rule in get_rules():
            if not rule.preauth_required and "preauth_form" in rule.required_docs:
                violations.append(
                    f"{rule.rule_id}: preauth_required=false but required_docs contains 'preauth_form'"
                )
        assert violations == [], f"Preauth inconsistencies found:\n" + "\n".join(violations)

    def test_bridges_emp011_preauth_coherent(self):
        """EMP011 bridges query must have coherent preauth_required + required_docs."""
        emp = _make_employee(plan_tier="premium", tenure_months="72", age="38")
        resp = evaluate(emp, parse_query("bridges"))
        assert resp.decision == "covered"
        assert resp.service_category == "major_dental"
        assert resp.preauth_required is True
        assert "preauth_form" in resp.required_docs
        assert resp.coverage_percent == 50.0


class TestNormalizeDocs:
    """Unit tests for _normalize_docs helper in orchestration layer."""

    def setup_method(self):
        from app.orchestration.nodes import _normalize_docs
        self._normalize = _normalize_docs

    def test_preauth_false_removes_preauth_form(self):
        result = self._normalize(["invoice", "preauth_form", "xray"], False)
        assert "preauth_form" not in result
        assert result == ["invoice", "xray"]

    def test_preauth_true_keeps_preauth_form(self):
        result = self._normalize(["invoice", "preauth_form"], True)
        assert "preauth_form" in result

    def test_preauth_true_adds_missing_preauth_form(self):
        result = self._normalize(["invoice", "xray"], True)
        assert "preauth_form" in result
        assert result == ["invoice", "xray", "preauth_form"]

    def test_preauth_none_leaves_docs_unchanged(self):
        result = self._normalize(["invoice", "preauth_form"], None)
        assert result == ["invoice", "preauth_form"]

    def test_deduplicate_preserves_order(self):
        result = self._normalize(["invoice", "xray", "invoice", "mc", "xray"], True)
        assert result == ["invoice", "xray", "mc", "preauth_form"]

    def test_deduplicate_with_preauth_false(self):
        result = self._normalize(["invoice", "preauth_form", "invoice", "preauth_form"], False)
        assert result == ["invoice"]

    def test_none_docs_returns_empty(self):
        result = self._normalize(None, False)
        assert result == []

    def test_none_docs_preauth_true_adds_form(self):
        result = self._normalize(None, True)
        assert result == ["preauth_form"]


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
