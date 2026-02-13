# Dataset Documentation

## Overview
This dataset provides synthetic health benefits policy data for a corporate benefits navigator MVP. All data is fictitious and designed for demonstration purposes only.

---

## Entities

### 1. Policy Corpus (`data/raw/policies/`)
**Purpose:** Source documents for policy-grounded retrieval

**Files:**
- `outpatient_policy.md` - GP/specialist consultation coverage
- `dental_policy.md` - Preventive, restorative, and major dental work
- `mental_health_policy.md` - Counseling and therapy benefits
- `preauth_rules.md` - Pre-authorization requirements and thresholds
- `claims_submission.md` - Claims process and timelines
- `exclusions_general.md` - Comprehensive exclusions list
- `plan_tiers_overview.md` - Basic/Plus/Premium plan structure
- `faq_policy_clarifications.md` - Common Q&A

**Structure:**
- Each file contains metadata header (Policy ID, Version, Dates, Owner)
- Clauses labeled with unique IDs (CL-001 to CL-157, including extension CL-073A)
- Sections: Eligibility, Coverage Rules, Limits, Exclusions, Required Docs, Timelines

---

### 2. Benefit Rules Table (`data/rules/benefit_rules.csv`)

**Purpose:** Deterministic decision engine inputs

**Columns:**
- `rule_id` - Unique identifier (R001-R043)
- `benefit_type` - outpatient | dental | mental_health
- `plan_tier` - basic | plus | premium
- `employment_type` - full_time | contract
- `tenure_min_months` - Minimum service months required
- `age_min` / `age_max` - Age eligibility range
- `preauth_required` - true/false flag
- `coverage_percent` - Co-insurance percentage (0-100)
- `annual_limit_sgd` - Maximum annual benefit in SGD
- `co_pay_sgd` - Per-visit/session co-payment
- `is_excluded` - true if this rule represents an exclusion
- `exclusion_reason` - Text explanation if excluded
- `required_docs` - Semicolon-separated document list
- `effective_from` / `effective_to` - Date range (YYYY-MM-DD)
- `service_category` - Service-level granularity (general_consult, specialist_consult, diagnostic_imaging, day_surgery, preventive_dental, restorative_dental, major_dental, root_canal, orthodontics, therapy_session, cosmetic_procedure, etc.)

**Row Count:** 43 rules

**Key Coverage:**
- All 3 benefit types × 3 plan tiers = 9 base coverage rules
- 8 exclusion rules (cosmetic, orthodontics, age/tenure boundaries, employment type)
- 8 preauth rules (high-value services, diagnostic imaging, major dental)
- 6 contract employee variations
- 6 boundary/edge cases (tenure gates, age limits, tenure-enhanced benefits)
- Service-level granularity for procedure-specific decisions

---

### 3. Employee Fixtures (`data/fixtures/employees.csv`)

**Purpose:** Test profiles for evaluation queries

**Columns:**
- `employee_id` - Unique identifier (EMP001-EMP026)
- `name` - Full name (fictitious)
- `age` - Years
- `employment_type` - full_time | contract
- `plan_tier` - basic | plus | premium
- `tenure_months` - Months of service
- `dependents_count` - Number of covered dependents
- `is_active` - Employment status

**Row Count:** 26 employees

**Distribution:**
- Plan tiers: ~8 Basic, ~9 Plus, ~9 Premium
- Employment types: ~21 full-time, ~5 contract
- Age range: 22-55 years
- Tenure range: 1-156 months
- 25 active, 1 inactive

**Edge Cases:**
- EMP017: Very new employee (1 month tenure)
- EMP018: Senior age (55) + long tenure (144 months)
- EMP019: Contract employee with 2 months (below 3-month gate)
- EMP024: Plus plan with 5 months (below 6-month mental health gate)
- EMP025: Intentionally missing name and tenure_months (insufficient_info test case)
- EMP026: Inactive employee (is_active=false)

---

### 4. Evaluation Cases (`eval/eval_cases.json`)

**Purpose:** Ground truth for system quality assessment

**Fields per case:**
- `case_id` - Unique identifier (EVAL001-EVAL015)
- `employee_id` - References employee fixture
- `question` - Natural language query
- `expected_decision` - covered | not_covered | insufficient_info
- `expected_benefit_type` - outpatient | dental | mental_health
- `expected_required_docs` - Array of document names
- `expected_min_citations` - Minimum policy citations required
- `notes` - Explanation and relevant clause references

**Case Count:** 15

**Decision Distribution:**
- 5 covered
- 7 not_covered
- 3 insufficient_info

**Coverage:**
- Exclusions: orthodontics, cosmetic procedures, couples counseling
- Tenure gates: contract employees, mental health waiting period
- Pre-auth scenarios: MRI, root canal
- Emergency exemptions: A&E visit
- Data gaps: missing employee data, claims history unavailable
- Plan limitations: Basic plan dental/mental health restrictions

---

## Known Edge Cases

1. **EMP025** - Missing tenure_months and name (tests insufficient_info handling)
2. **EMP026** - Inactive employee (tests active status validation)
3. **Contract employees** - Dental always excluded (R010, R011)
4. **Mental health tenure gate** - Full-time needs 6mo, contract needs 12mo
5. **Age boundaries** - Basic max 65, Plus max 70 for certain benefits
6. **Pre-auth precedence** - Service-specific preauth rules override threshold rules
7. **Orthodontics** - Excluded across all plans (R023)
8. **Emergency services** - Preauth exempt but need retrospective notification
9. **Dependent coverage** - Varies significantly by plan tier
10. **Claims timeline precedence** - Benefit-specific timelines override general 30-day rule

---

## Currency & Context
- All monetary amounts in **Singapore Dollars (SGD)**
- Date format: **YYYY-MM-DD (ISO 8601)**
- Policy effective date: **2024-01-01**
- Cultural context: Singapore corporate benefits structure

---

## Usage Notes
- Rules table is the authoritative source for deterministic decisions
- Policy corpus provides citation evidence and edge case clarifications
- When rules and policy conflict, rules take precedence for computation
- Eval cases assume no prior claims history (fresh annual limits)
- Service_category field enables procedure-specific decision logic