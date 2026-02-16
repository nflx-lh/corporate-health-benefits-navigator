"""Focused audit: deterministic query → category → rule mapping.

Traces EMP011 (premium, full_time, age 38, tenure 72) and
EMP005 (plus, contract, age 31, tenure 8) through the full pipeline.
"""

import pytest

from app.services.employee_repo import EmployeeRecord
from app.services.query_parser import parse_query
from app.services.rules_engine import evaluate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _emp011() -> EmployeeRecord:
    """EMP011: James Lee, premium, full_time, age 38, tenure 72."""
    return EmployeeRecord({
        "employee_id": "EMP011",
        "name": "James Lee",
        "age": "38",
        "employment_type": "full_time",
        "plan_tier": "premium",
        "tenure_months": "72",
        "dependents_count": "2",
        "is_active": "true",
    })


def _emp005() -> EmployeeRecord:
    """EMP005: David Wong, plus, contract, age 31, tenure 8."""
    return EmployeeRecord({
        "employee_id": "EMP005",
        "name": "David Wong",
        "age": "31",
        "employment_type": "contract",
        "plan_tier": "plus",
        "tenure_months": "8",
        "dependents_count": "0",
        "is_active": "true",
    })


# ===================================================================
# EMP011 — premium / full_time
# ===================================================================

class TestEMP011Premium:
    """EMP011 (premium, full_time): 7 query scenarios."""

    def test_braces(self):
        emp = _emp011()
        parsed = parse_query("braces")
        assert parsed.benefit_type == "dental"
        assert parsed.service_category == "orthodontics"
        resp = evaluate(emp, parsed)
        assert resp.decision == "not_covered"
        assert "EXCLUSION" in resp.reason_codes
        assert resp.coverage_percent is None

    def test_orthodontic_treatment(self):
        emp = _emp011()
        parsed = parse_query("orthodontic treatment")
        assert parsed.benefit_type == "dental"
        assert parsed.service_category == "orthodontics"
        resp = evaluate(emp, parsed)
        assert resp.decision == "not_covered"
        assert "EXCLUSION" in resp.reason_codes
        assert "R044" in resp.matched_rule_ids

    def test_root_canal(self):
        emp = _emp011()
        parsed = parse_query("root canal")
        assert parsed.benefit_type == "dental"
        assert parsed.service_category == "root_canal"
        resp = evaluate(emp, parsed)
        assert resp.decision == "covered"
        assert "R038" in resp.matched_rule_ids
        assert resp.coverage_percent == 50.0
        assert resp.preauth_required is True

    def test_crown_treatment(self):
        """Per CL-031: crowns are Major dental (50%), per CL-044: preauth required."""
        emp = _emp011()
        parsed = parse_query("crown treatment")
        assert parsed.benefit_type == "dental"
        assert parsed.service_category == "major_dental"
        resp = evaluate(emp, parsed)
        assert resp.decision == "covered"
        assert "R012" in resp.matched_rule_ids
        assert resp.coverage_percent == 50.0
        assert resp.preauth_required is True
        assert "preauth_form" in resp.required_docs

    def test_bridge(self):
        """Per CL-031: bridges are Major dental (50%), per CL-044: preauth required."""
        emp = _emp011()
        parsed = parse_query("bridge")
        assert parsed.benefit_type == "dental"
        assert parsed.service_category == "major_dental"
        resp = evaluate(emp, parsed)
        assert resp.decision == "covered"
        assert "R012" in resp.matched_rule_ids
        assert resp.coverage_percent == 50.0
        assert resp.preauth_required is True
        assert "preauth_form" in resp.required_docs

    def test_dental_cleaning(self):
        emp = _emp011()
        parsed = parse_query("dental cleaning")
        assert parsed.benefit_type == "dental"
        assert parsed.service_category == "preventive_dental"
        resp = evaluate(emp, parsed)
        assert resp.decision == "covered"
        assert "R008" in resp.matched_rule_ids
        assert resp.coverage_percent == 100.0
        assert resp.co_pay_sgd == 15.0

    def test_specialist_consult(self):
        emp = _emp011()
        parsed = parse_query("specialist consult")
        assert parsed.benefit_type == "outpatient"
        assert parsed.service_category == "specialist_consult"
        resp = evaluate(emp, parsed)
        assert resp.decision == "covered"
        assert "R018" in resp.matched_rule_ids
        assert resp.coverage_percent == 90.0
        assert resp.co_pay_sgd == 10.0


# ===================================================================
# EMP005 — plus / contract
# ===================================================================

class TestEMP005PlusContract:
    """EMP005 (plus, contract): 3 query scenarios."""

    def test_dental_cleaning(self):
        """Plus/contract dental → R010 exclusion (contract not eligible)."""
        emp = _emp005()
        parsed = parse_query("dental cleaning")
        assert parsed.benefit_type == "dental"
        assert parsed.service_category == "preventive_dental"
        resp = evaluate(emp, parsed)
        assert resp.decision == "not_covered"
        # R010 is the exclusion for plus/contract/preventive_dental
        assert "EXCLUSION" in resp.reason_codes
        assert resp.coverage_percent is None

    def test_root_canal(self):
        """Plus/contract root_canal → no dental+plus+contract root_canal rule → SERVICE_CATEGORY_NOT_COVERED."""
        emp = _emp005()
        parsed = parse_query("root canal")
        assert parsed.benefit_type == "dental"
        assert parsed.service_category == "root_canal"
        resp = evaluate(emp, parsed)
        assert resp.decision == "not_covered"
        # No root_canal rule for plus/contract; only preventive_dental and orthodontics
        # After service_category narrowing: no match → fallback to general_consult → no general_consult
        # → SERVICE_CATEGORY_NOT_COVERED
        assert resp.coverage_percent is None

    def test_specialist_consult(self):
        """Plus/contract specialist → no specialist_consult rule → fallback to R004 general_consult."""
        emp = _emp005()
        parsed = parse_query("specialist consult")
        assert parsed.benefit_type == "outpatient"
        assert parsed.service_category == "specialist_consult"
        resp = evaluate(emp, parsed)
        # No outpatient+plus+contract+specialist_consult rule exists
        # Fallback to general_consult → R004 (plus/contract, tenure_min=3, EMP005 tenure=8 ≥ 3)
        # But R004 is NOT excluded, tenure passes → covered
        assert resp.decision == "covered"
        assert "R004" in resp.matched_rule_ids
        assert resp.coverage_percent == 80.0


# ===================================================================
# Ambiguous query
# ===================================================================

class TestAmbiguousQuery:
    """Ambiguous query: no keyword match → insufficient_info."""

    def test_can_i_claim_this(self):
        emp = _emp011()
        parsed = parse_query("can i claim this")
        assert parsed.benefit_type is None
        assert parsed.service_category is None
        resp = evaluate(emp, parsed)
        assert resp.decision == "insufficient_info"
        assert "AMBIGUOUS_BENEFIT_TYPE" in resp.reason_codes
