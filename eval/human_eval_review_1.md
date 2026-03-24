# Human Eval Review — Review 1

**Review date:** 24-Mar-2026
**Reviewer:** Jane Doe (Project Lead)
**App version:** v0.17.0
**LLM model:** gpt-4o-mini
**Environment:** Cloud (AWS ECS Fargate, ALB endpoint)

---

## Scorecard

| # | Case | Employee | Question Summary | Decision | Accuracy (1–5) | Clarity (1–5) | Tone (1–5) | Completeness (1–5) | Mean | Pass? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | EMP014 | Premium / full_time / 84 mths | Root canal — docs and coverage | covered | 5 | 4 | 4 | 4 | **4.25** | ✅ |
| 2 | EMP014 | Premium / full_time / 84 mths | MRI scan recommended by doctor | covered | 5 | 5 | 4 | 5 | **4.75** | ✅ |
| 3 | EMP003 | Plus / full_time / 24 mths | Specialist consult for stomach pain | covered | 5 | 5 | 5 | 4 | **4.75** | ✅ |
| 4 | EMP003 | Plus / full_time / 24 mths | Mental health therapy sessions | covered | 5 | 5 | 5 | 4 | **4.75** | ✅ |
| 5 | EMP017 | Basic / full_time / 1 mth | Mental health counseling sessions | not_covered | 5 | 5 | 4 | 5 | **4.75** | ✅ |
| 6 | EMP017 | Basic / full_time / 1 mth | Cosmetic surgery (nose job) | not_covered | 4 | 5 | 4 | 4 | **4.25** | ✅ |
| 7 | EMP015 | Contract / Premium / 10 mths | Counseling — tenure eligibility | not_covered | 5 | 5 | 4 | 5 | **4.75** | ✅ |
| 8 | EMP015 | Contract / Premium / 10 mths | Root canal — docs and coverage | not_covered | 2 | 3 | 2 | 2 | **2.25** | ❌ |
| 9 | EMP001 | Premium / full_time / 48 mths | Intensive psychiatric counseling | covered | 5 | 5 | 4 | 4 | **4.50** | ✅ |
| 10 | EMP001 | Premium / full_time / 48 mths | Cosmetic surgery (nose job) | not_covered | 4 | 5 | 4 | 4 | **4.25** | ✅ |

---

## Summary

| Metric | Value |
|---|---|
| Total cases reviewed | 10 |
| Cases passed (mean ≥ 3.5) | 9 / 10 |
| Overall pass rate | **90%** |
| Verdict | ✅ Ship — LLM responses are production quality |

---

## Case-by-Case Observations

**Case 1 — EMP014 Root Canal (Pass, 4.25)**
Accurately states covered at 50%, SGD 2,000 limit, and that pre-authorization is required. Documents described generically ("treatment summary and pre-authorization form") rather than listing all required items (invoice, xray, dentist_justification). Minor completeness gap but not misleading.

**Case 2 — EMP014 MRI Scan (Pass, 4.75)**
Strongest covered response in this review. All financial figures correct (90%, SGD 5,000, co-pay SGD 10). Pre-authorization clearly stated. Documents mentioned generically but all key action points are present.

**Case 3 — EMP003 Specialist Consult (Pass, 4.75)**
Natural, warm tone. Correctly states 80%, SGD 3,000, co-pay SGD 15. Mentions "referrals and receipts" which covers the key docs. MC not explicitly named but not a significant gap.

**Case 4 — EMP003 Mental Health Therapy (Pass, 4.75)**
Correct figures (70%, SGD 1,800, co-pay SGD 30 per session). Documents mentioned generically. "co-pay of $30 per session" phrasing is a nice touch — more specific than just stating the figure.

**Case 5 — EMP017 Mental Health Not Covered (Pass, 4.75)**
Best not_covered response. Correctly explains the Basic plan EAP alternative (3 free sessions) — this goes beyond just saying "not covered" and gives the employee a meaningful next step. Empathetic tone with "Unfortunately".

**Case 6 — EMP017 Cosmetic Surgery Not Covered (Pass, 4.25)**
Correct decision. However the LLM adds "unless they are deemed medically necessary with proper certification from a specialist" — this nuance is not directly stated in the rules for the Basic plan. Directionally not wrong but slightly embellishes beyond what the rules engine returned.

**Case 7 — EMP015 Counseling Tenure Gate (Pass, 4.75)**
Outstanding response. Specifically states "12 months of tenure required" and "you currently have only 10 months." This level of specificity is exactly what an employee needs to understand when they will become eligible. Best use of deterministic data in a not_covered explanation.

**Case 8 — EMP015 Root Canal Not Covered (FAIL, 2.25)**
Critical issue identified. Decision is correct (not_covered) but the explanation is wrong: the LLM states "There are no coverage rules for this specific service category." The actual reason is that contract employees are categorically excluded from dental benefits regardless of plan tier. The incorrect reason could mislead the employee into thinking this is a gap in the rules rather than a deliberate exclusion. The closing line "keep your documents handy in case you need them for any future inquiries" is also inappropriate for a definitive not_covered case.
**Root cause:** The rules engine likely returned not_covered with a reason_code related to contract dental exclusion, but the LLM did not accurately convey this in the explanation.

**Case 9 — EMP001 Intensive Therapy (Pass, 4.50)**
Correct figures (85%, SGD 3,500, co-pay SGD 30, preauth required). Actionable and clear. Documents mentioned generically rather than specifically named.

**Case 10 — EMP001 Cosmetic Surgery Not Covered (Pass, 4.25)**
Same pattern as Case 6 — adds "medically necessary with proper certification" caveat not explicitly in the rules. Consistent across employees which suggests the LLM has learned this nuance from the policy corpus, but it is not directly grounded in the deterministic output.

---

## Issues & Recommendations

| Priority | Issue | Recommendation |
|---|---|---|
| P0 | Case 8: Wrong exclusion reason for contract employee dental denial | Investigate rules engine reason_code for contract dental exclusion — ensure it is passed clearly to the LLM prompt so the correct reason is explained |
| P1 | Cases 6, 10: "Medically necessary" caveat added without rules grounding | Review explainer prompt — add instruction to only state reasons present in the deterministic decision payload, not inferred from policy corpus |
| P2 | Cases 1, 3, 4, 9: Required docs listed generically | Consider whether to instruct LLM to reference specific document types by category (e.g. "dental documents" vs listing each) — current behaviour avoids overwhelming employees |

---

## Next Review

Recommended trigger: after any change to the explainer system prompt, or after upgrading the LLM model.
Focus areas: re-test Case 8 scenario after P0 fix; verify Cases 6/10 if prompt is updated.
