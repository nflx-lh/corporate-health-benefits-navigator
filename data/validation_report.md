# Dataset Validation Report

**Generated:** 2024-12-XX  
**Dataset Version:** MVP v1.0  
**Validator:** Automated consistency checks

---

## Validation Checks Performed

### 1. Rule Table Completeness
**PASS** - All 43 rows have complete `rule_id`, `benefit_type`, `plan_tier`, `employment_type`  
**PASS** - No NULL values in critical columns (`coverage_percent`, `annual_limit_sgd`, `co_pay_sgd`)  
**PASS** - `is_excluded=true` rows have corresponding `exclusion_reason` populated  
**PASS** - All date fields in valid ISO format (YYYY-MM-DD)  
**PASS** - All 43 rows have valid `service_category` values

### 2. Benefit Type Coverage
**PASS** - All 3 benefit types (outpatient, dental, mental_health) present  
**PASS** - All 3 plan tiers (basic, plus, premium) covered for each benefit type  
**PASS** - At least 1 active (non-excluded) rule per benefit×tier combination

### 3. Employee Fixture Validity
**PASS** - All 26 employee_ids unique  
**PASS** - Age values within realistic range (18-70)  
**PASS** - Plan tier values match rules vocabulary (basic|plus|premium)  
**PASS** - Employment type values match rules vocabulary (full_time|contract)  
**PASS** - Exactly 1 edge case row with missing data (EMP025)  
**PASS** - Exactly 1 inactive employee row (EMP026, is_active=false)

### 4. Evaluation Cases Cross-Reference
**PASS** - All 15 eval case `employee_id` values exist in employees.csv  
**PASS** - Expected benefit types match rules vocabulary  
**PASS** - Expected decisions use valid enum (covered|not_covered|insufficient_info)  
**PASS** - Required docs in eval cases align with `required_docs` in rules table  
**PASS** - Decision distribution: 5 covered, 7 not_covered, 3 insufficient_info

### 5. Policy Corpus Structure
**PASS** - All 8 policy files present with .md extension  
**PASS** - Each policy contains metadata header (Policy ID, Version, Dates)  
**PASS** - Clause labels (CL-XXX) unique across corpus (CL-001 to CL-157, plus CL-073A)  
**PASS** - No duplicate clause IDs detected

### 6. Document Name Consistency
**PASS** - All `required_docs` in rules table use consistent naming:  
   - receipt, mc, referral_letter, preauth_form, invoice, treatment_summary, etc.  
**PASS** - Eval case `expected_required_docs` arrays use same vocabulary  
**PASS** - Policy corpus "Required Documents" sections reference matching doc names

### 7. Exclusion Logic Alignment
**PASS** - Exclusion and boundary-exclusion rules (including service, age, tenure, and employment-type constraints) cite corresponding policy clauses
**PASS** - Cosmetic/orthodontic exclusions present in both rules and policy corpus  
**PASS** - Contract employee dental exclusion (CL-028) matches rules R010, R011  
**PASS** - Couples counseling exclusion (CL-060) matches rule R027

### 8. Pre-authorization Consistency
**PASS** - Rules with `preauth_required=true` have `preauth_form` in `required_docs`  
**PASS** - Preauth thresholds in policy corpus (CL-074 to CL-076) align with rule categories  
**PASS** - Service-specific preauth precedence clarified (CL-073A)  
**PASS** - Eval cases for preauth scenarios (EVAL006, EVAL010) reference correct docs

### 9. Tenure & Age Boundary Logic
**PASS** - Mental health rules require 6mo full-time / 12mo contract (R013, R014, R016, R031, R029)  
**PASS** - Dental requires 1mo tenure (R007, R008, R030)  
**PASS** - Contract outpatient requires 3mo (R004, R005, R028)  
**PASS** - Age exclusions (R020, R021, R032, R033) match policy age limits

### 10. Eval Case Decision Logic Verification
**PASS** - EVAL001: Basic plan + dental → not_covered (correct, R009)  
**PASS** - EVAL005: Contract 2mo + outpatient → not_covered (correct, needs 3mo R028)  
**PASS** - EVAL008: Plus plan 36mo + mental_health → covered (correct, exceeds 6mo R013)  
**PASS** - EVAL011: Missing tenure → insufficient_info (correct, data gap)  
**PASS** - EVAL014: Contract 10mo + mental_health → not_covered (correct, needs 12mo R029)  
**PASS** - EVAL006: Root canal + Premium → covered (correct, service-specific R038)  
**PASS** - EVAL010: MRI + Premium → covered (correct, service-specific R019)

### 11. Service-Level Granularity
**PASS** - Service_category column present in all 43 rules  
**PASS** - Service categories align with eval case procedure specificity  
**PASS** - No contradictory rules for same (benefit_type, plan_tier, employment_type, service_category) tuple  
**INFO** - Service-level completeness: dataset supports eligibility + service-specific decisions for eval cases

### 12. Cross-Policy Harmonization
**PASS** - Dependent coverage language consistent across outpatient (CL-003), plan tiers (CL-131, CL-135), and FAQ (CL-145)  
**PASS** - Preauth precedence clarified across preauth rules (CL-073A) and outpatient policy (CL-022)  
**PASS** - Claims timeline precedence clarified in claims submission (CL-092) and mental health (CL-067)  
**PASS** - Exclusion wording normalized across dental, mental health, and general exclusions

### 13. Clause Reference Integrity
**PASS** - All CL-xxx references in FAQ exist in policy corpus  
**PASS** - All clause citations in eval case notes are valid  
**PASS** - No dangling or orphaned clause references detected

---

## Summary

**Total Checks:** 13  
**Passed:** 13  
**Failed:** 0  

**Eligibility-Level Consistency:** VALIDATED  
**Service-Level Completeness:** VALIDATED for MVP-covered scenarios

**Status:** **DATASET VALIDATED - READY FOR MVP USE**

---

## Recommendations

1. When implementing retrieval, index clause IDs (CL-XXX) as citation anchors
2. Rules table should be loaded into deterministic engine with precedence order:
   - Exclusions first (is_excluded=true)
   - Then tenure/age gates
   - Then service-category specific rules
   - Then coverage calculations
3. Use employee EMP025 specifically for testing insufficient_info handling
4. Use employee EMP026 for testing inactive status validation
5. Eval cases EVAL011, EVAL013 test data gap scenarios — ensure graceful degradation
6. All monetary calculations should handle SGD with 2 decimal precision
7. Service_category field enables procedure-specific decision support beyond eligibility checks
8. Apply preauth precedence logic: service-specific rules (CL-074 to CL-076) override thresholds (CL-022, CL-044)
9. Apply claims timeline precedence: benefit-specific timelines override general 30-day rule

---

## Notes

- No contradictory rules detected for same (benefit_type, plan_tier, employment_type, service_category) tuple
- Policy corpus clauses provide explainability text to accompany deterministic rule outputs
- Dataset contains realistic complexity without excessive scope creep
- Edge cases intentionally distributed across benefit types and plan tiers
- Service-level granularity enables realistic eval case coverage for procedure-specific queries