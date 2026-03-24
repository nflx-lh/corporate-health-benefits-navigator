# Human Eval Scorecard — Benefits Navigator LLM Responses

**Purpose:** Periodic spot-check of LLM-generated explanations (`ai_summary`) for quality, accuracy, and tone.
**Pass threshold:** Mean score ≥ 3.5 across all four dimensions per case.
**Recommended cadence:** After each major prompt change, or monthly in production.

---

## How to Use This Scorecard

1. Run the app locally or against the cloud endpoint with LLM enabled (`LLM_ENABLED=true`).
2. Submit each query below using the specified Employee ID.
3. Score the `ai_summary` field in the response against the four dimensions.
4. Record scores in the table. Calculate the mean and mark Pass/Fail.
5. If more than 2 cases fail, investigate the explainer prompt before deploying.

---

## Scoring Dimensions

| Dimension | What it measures | Score 1 (Poor) | Score 5 (Excellent) |
|---|---|---|---|
| **Accuracy** | Does the summary correctly reflect the deterministic decision, financial figures, and preauth requirement? | Contradicts the decision or states wrong figures | Perfectly reflects decision, coverage %, limit, co-pay, and preauth |
| **Clarity** | Is the language plain and easy for a non-expert employee to understand? | Jargon-heavy, confusing, or hard to follow | Clear, simple language any employee can act on immediately |
| **Tone** | Is the tone professional, neutral, and empathetic — not robotic or overly formal? | Reads like a form letter or is cold/blunt | Warm, conversational, and direct without being chatty |
| **Completeness** | Does the summary cover all key actionable points — decision, next steps, any conditions? | Missing critical information (e.g. no mention of preauth or required docs) | All key points covered concisely with clear next steps |

---

## Scorecard Table

> Fill in scores 1–5 for each dimension. Mean = average of all four scores.

| # | Employee | Question Summary | Expected Decision | Accuracy (1–5) | Clarity (1–5) | Tone (1–5) | Completeness (1–5) | Mean | Pass? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | EMP014 / Premium / 84 mths | Root canal — docs and coverage | covered | | | | | | |
| 2 | EMP014 / Premium / 84 mths | MRI scan recommended by doctor | covered | | | | | | |
| 3 | EMP003 / Plus / 24 mths | Specialist consult for stomach pain | covered | | | | | | |
| 4 | EMP003 / Plus / 24 mths | Mental health therapy sessions | covered | | | | | | |
| 5 | EMP017 / Basic / 1 mth | Mental health counseling sessions | not_covered | | | | | | |
| 6 | EMP017 / Basic / 1 mth | Cosmetic surgery (nose job) | not_covered | | | | | | |
| 7 | EMP015 / Contract-Premium / 10 mths | Counseling — tenure eligibility | not_covered | | | | | | |
| 8 | EMP015 / Contract-Premium / 10 mths | Root canal — docs and coverage | not_covered | | | | | | |
| 9 | EMP001 / Premium / 48 mths | Intensive psychiatric counseling | covered | | | | | | |
| 10 | EMP001 / Premium / 48 mths | Cosmetic surgery (nose job) | not_covered | | | | | | |

---

## Summary

| Metric | Value |
|---|---|
| Total cases reviewed | 10 |
| Cases passed (mean ≥ 3.5) | ___ / 10 |
| Overall pass rate | ___% |
| Run date | |
| Reviewer | |
| App version | |
| LLM model used | |

---

## Notes & Observations

> Record any patterns, recurring issues, or improvement suggestions here after each review.

-
-
-

---

## Pass/Fail Criteria Reference

| Overall Pass Rate | Recommendation |
|---|---|
| ≥ 80% (8–10 cases pass) | Ship — LLM responses are production quality |
| 60–79% (6–7 cases pass) | Review failing cases — targeted prompt fix likely needed |
| < 60% (< 6 cases pass) | Do not ship — revisit explainer system prompt before deployment |
