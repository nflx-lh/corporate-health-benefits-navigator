"""Deterministic rules engine – evaluates employee eligibility against benefit rules.

Precedence order:
1. Missing critical info -> insufficient_info
2. Inactive employee -> not_covered
3. Exclusions
4. Tenure / age / employment gates
5. Service-specific rules
6. Fallback general rule
7. Output docs / preauth / financial terms
"""

from __future__ import annotations

import uuid
from typing import Optional

from app.models.decision import QueryResponse
from app.services.employee_repo import EmployeeRecord
from app.services.query_parser import ParsedQuery
from app.services.rule_repo import BenefitRule, get_rules


def _insufficient(
    employee_id: str,
    parsed: ParsedQuery,
    reason: str,
    reason_codes: list[str],
    path: list[str],
) -> QueryResponse:
    return QueryResponse(
        query_id=str(uuid.uuid4()),
        employee_id=employee_id,
        decision="insufficient_info",
        benefit_type=parsed.benefit_type,
        service_category=parsed.service_category,
        reason_summary=reason,
        reason_codes=reason_codes,
        matched_rule_ids=[],
        required_docs=[],
        preauth_required=None,
        coverage_percent=None,
        annual_limit_sgd=None,
        co_pay_sgd=None,
        decision_path=path,
    )


def _not_covered(
    employee_id: str,
    parsed: ParsedQuery,
    reason: str,
    reason_codes: list[str],
    matched_rule_ids: list[str],
    path: list[str],
) -> QueryResponse:
    return QueryResponse(
        query_id=str(uuid.uuid4()),
        employee_id=employee_id,
        decision="not_covered",
        benefit_type=parsed.benefit_type,
        service_category=parsed.service_category,
        reason_summary=reason,
        reason_codes=reason_codes,
        matched_rule_ids=matched_rule_ids,
        required_docs=[],
        preauth_required=None,
        coverage_percent=None,
        annual_limit_sgd=None,
        co_pay_sgd=None,
        decision_path=path,
    )


def evaluate(employee: EmployeeRecord, parsed: ParsedQuery) -> QueryResponse:
    """Run the deterministic decision pipeline and return a QueryResponse."""
    path: list[str] = []

    # ------------------------------------------------------------------
    # 1. Missing critical profile info
    # ------------------------------------------------------------------
    missing_codes: list[str] = []
    if employee.plan_tier is None:
        missing_codes.append("MISSING_PLAN_TIER")
    if employee.employment_type is None:
        missing_codes.append("MISSING_EMPLOYMENT_TYPE")
    if employee.age is None:
        missing_codes.append("MISSING_AGE")
    if employee.tenure_months is None:
        missing_codes.append("MISSING_TENURE_MONTHS")
    if employee.name is None:
        missing_codes.append("MISSING_NAME")

    if missing_codes:
        path.append("check_profile_completeness: FAIL")
        return _insufficient(
            employee.employee_id,
            parsed,
            f"Employee profile has missing fields: {', '.join(missing_codes)}",
            missing_codes,
            path,
        )
    path.append("check_profile_completeness: PASS")

    # ------------------------------------------------------------------
    # 1b. Ambiguous benefit type
    # ------------------------------------------------------------------
    if parsed.benefit_type is None:
        path.append("parse_benefit_type: FAIL")
        return _insufficient(
            employee.employee_id,
            parsed,
            "Could not determine benefit type from query",
            ["AMBIGUOUS_BENEFIT_TYPE"],
            path,
        )
    path.append(f"parse_benefit_type: {parsed.benefit_type}")

    # ------------------------------------------------------------------
    # 2. Inactive employee
    # ------------------------------------------------------------------
    if not employee.is_active:
        path.append("check_active_status: INACTIVE")
        return _not_covered(
            employee.employee_id,
            parsed,
            "Employee is inactive",
            ["EMPLOYEE_INACTIVE"],
            [],
            path,
        )
    path.append("check_active_status: ACTIVE")

    # ------------------------------------------------------------------
    # Filter rules for this benefit_type, plan_tier, employment_type
    # ------------------------------------------------------------------
    all_rules = get_rules()
    candidate_rules = [
        r
        for r in all_rules
        if r.benefit_type == parsed.benefit_type
        and r.plan_tier == employee.plan_tier
        and r.employment_type == employee.employment_type
    ]
    path.append(f"candidate_rules_count: {len(candidate_rules)}")

    if not candidate_rules:
        path.append("no_matching_rules")
        return _not_covered(
            employee.employee_id,
            parsed,
            f"No rules found for benefit_type={parsed.benefit_type}, "
            f"plan_tier={employee.plan_tier}, employment_type={employee.employment_type}",
            ["NO_MATCHING_RULE"],
            [],
            path,
        )

    # ------------------------------------------------------------------
    # Narrow by service_category if we have one
    # ------------------------------------------------------------------
    if parsed.service_category:
        service_rules = [
            r for r in candidate_rules if r.service_category == parsed.service_category
        ]
        if service_rules:
            candidate_rules = service_rules
            path.append(f"service_category_match: {parsed.service_category}")
        else:
            # Fall back to general_consult / general category
            general = [
                r for r in candidate_rules if r.service_category == "general_consult"
            ]
            if general:
                candidate_rules = general
                path.append("service_category_fallback: general_consult")
            else:
                # Explicit service category with no matching rules and no
                # general fallback — must NOT award unrelated coverage.
                path.append(f"service_category_not_covered: {parsed.service_category}")
                return _not_covered(
                    employee.employee_id,
                    parsed,
                    f"No coverage rules found for service category '{parsed.service_category}'",
                    ["SERVICE_CATEGORY_NOT_COVERED"],
                    [],
                    path,
                )

    # ------------------------------------------------------------------
    # 3-4. Evaluate exclusions and eligibility gates together.
    #
    # Strategy: first try to find non-excluded rules the employee
    # qualifies for.  If any exist, the employee is eligible (exclusion
    # rules that co-exist are "conditional" and don't apply).  Only when
    # zero non-excluded rules qualify do we check whether an exclusion
    # rule explains why.
    # ------------------------------------------------------------------
    non_excluded = [r for r in candidate_rules if not r.is_excluded]
    exclusion_rules = [r for r in candidate_rules if r.is_excluded]

    # 4. Apply tenure / age gates to non-excluded rules
    eligible_rules: list[BenefitRule] = []
    for r in non_excluded:
        if employee.tenure_months is not None and employee.tenure_months < r.tenure_min_months:
            path.append(f"rule_{r.rule_id}_tenure_gate: FAIL (need {r.tenure_min_months}, have {employee.tenure_months})")
            continue
        if employee.age is not None and (employee.age < r.age_min or employee.age > r.age_max):
            path.append(f"rule_{r.rule_id}_age_gate: FAIL (need {r.age_min}-{r.age_max}, have {employee.age})")
            continue
        eligible_rules.append(r)

    # 3. If no non-excluded rule qualifies, check exclusion rules
    if not eligible_rules:
        if exclusion_rules:
            rule = exclusion_rules[0]
            path.append(f"exclusion_matched: {rule.rule_id}")
            return _not_covered(
                employee.employee_id,
                parsed,
                rule.exclusion_reason or "Excluded by plan rules",
                ["EXCLUSION"],
                [rule.rule_id],
                path,
            )
        path.append("all_rules_gated_out")
        return _not_covered(
            employee.employee_id,
            parsed,
            "Employee does not meet tenure or age requirements for this benefit",
            ["ELIGIBILITY_GATE_FAILED"],
            [],
            path,
        )

    # ------------------------------------------------------------------
    # 5-6. Pick best rule: prefer service-specific over general, then
    #       highest coverage_percent, then lowest co_pay
    # ------------------------------------------------------------------
    def _rule_sort_key(r: BenefitRule) -> tuple:
        is_specific = r.service_category != "general_consult"
        return (is_specific, r.coverage_percent, -r.co_pay_sgd)

    eligible_rules.sort(key=_rule_sort_key, reverse=True)
    winning = eligible_rules[0]
    path.append(f"winning_rule: {winning.rule_id}")

    # ------------------------------------------------------------------
    # 7. Build covered response
    # ------------------------------------------------------------------
    return QueryResponse(
        query_id=str(uuid.uuid4()),
        employee_id=employee.employee_id,
        decision="covered",
        benefit_type=parsed.benefit_type,
        service_category=winning.service_category or parsed.service_category,
        reason_summary=f"Covered under rule {winning.rule_id}",
        reason_codes=["COVERED"],
        matched_rule_ids=[winning.rule_id],
        required_docs=winning.required_docs,
        preauth_required=winning.preauth_required,
        coverage_percent=winning.coverage_percent,
        annual_limit_sgd=winning.annual_limit_sgd,
        co_pay_sgd=winning.co_pay_sgd,
        decision_path=path,
    )
