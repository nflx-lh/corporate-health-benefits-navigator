# Phase 4 Frontend Smoke Test Checklist

## Scope
Phase 4 frontend integration for orchestrated flow (`POST /v1/query-orchestrated`) with MVP-only hardening:
- Base decision fields must render consistently
- Optional explanation/citations must be resilient when missing/null/empty
- Error and edge states must be graceful

## Prerequisites
```bash
# Terminal 1 — backend (from repo root)
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (from repo root)
cd frontend && npm run dev

```
Open http://localhost:5173 in a browser.

---

## API Sanity Check (direct backend)

- [ ] Known employee returns `200`:

```bash
curl -i -X POST 'http://127.0.0.1:8000/v1/query-orchestrated' \
  -H 'Content-Type: application/json' \
  -d '{"employee_id":"EMP003","question":"Am I covered for dental cleaning?"}'
```
- [ ] Unknown employee returns `404` + `EMPLOYEE_NOT_FOUND`:

```bash
curl -i -X POST 'http://127.0.0.1:8000/v1/query-orchestrated' \
  -H 'Content-Type: application/json' \
  -d '{"employee_id":"EMP999","question":"Am I covered for dental cleaning?"}'
```

## Test Cases

### 1) Login page renders
- [ ] Page shows title **"Corporate Health Benefits Navigator"**
- [ ] Employee ID input and Continue button are visible
- [ ] Continue button is disabled when input is empty

### 2) Login with valid employee ID
- **Input:** `EMP001` → click Continue
- [ ] Navigates to Navigator page
- [ ] Header shows **"Benefits Navigator"** and employee ID
- [ ] Logout button visible

### 3) Covered decision — dental cleaning
- **Input:** `Am I covered for dental cleaning?` → click Ask
- [ ] Loading state shows **"Checking..."** and submit button is disabled
- [ ] Decision badge shown (e.g., covered)
- [ ] `reason_summary` displayed (fallback `—` if absent)
- [ ] Base sections render:
  - [ ] Reason Codes (or `None`)
  - [ ] Required Documents (or `None`)
- [ ] Pre-auth Required renders as Yes/No/—
- [ ] Required financial rows render safely:
  - [ ] Coverage %
  - [ ] Annual Limit (SGD)
  - [ ] Remaining Limit (SGD, fallback `—` if absent)
  - [ ] Estimated Payout (SGD, fallback `—` if absent)
- [ ] Enrichment behavior:
  - [ ] If present, explanation/citations appear in separated purple section
  - [ ] If absent, enrichment section is omitted without crash

### 4) Not-covered decision — exclusion-style query
- **Input:** `Am I covered for cosmetic teeth whitening?`
- [ ] Red **not covered** badge shown
- [ ] Reason summary/reason codes shown
- [ ] Base required financial rows still render safely with fallbacks (`—` when unavailable)
- [ ] UI remains stable (no null/undefined artifacts)

### 5) Insufficient info handling
- **Input:** `Am I covered for an treatment?` (or other ambiguous query)
- [ ] Yellow **insufficient info** badge shown
- [ ] Reason summary/reason codes shown when provided
- [ ] Helper hint displayed:  
  **"More details may be required (e.g., treatment type/date/provider)."**
- [ ] No crash when enrichment is missing

### 6) 404 — unknown employee
- **Action:** Logout, login as `EMP999`, ask any query
- [ ] Error message shown for unknown employee
- [ ] No crash, no broken page state

### 7) Duplicate submit prevention
- **Action:** Enter a query and click Ask rapidly
- [ ] Ask button disabled during loading
- [ ] Only one request is fired (check DevTools Network)

### 8) Logout flow
- **Action:** Click Logout
- [ ] Returns to login page
- [ ] Prior result state is cleared

### 9) Empty arrays / null safety
- [ ] Empty `required_docs` renders `None`
- [ ] Empty `reason_codes` renders `None`
- [ ] Missing/null optional enrichment (`explanation`, `policy_citations`) does not crash UI
- [ ] Missing financial values render `—` in required rows (stable layout)

### 10) Visual separation of deterministic vs enrichment
- [ ] Deterministic/base decision content is clearly separate from enrichment block
- [ ] Enrichment block appears only when explanation and/or citations exist

---

## Pass/Fail Rule

**PASS** only if all items below are true:

- [ ] Frontend successfully calls `POST /v1/query-orchestrated`
- [ ] Base decision fields render consistently for all tested outcomes
- [ ] Optional enrichment fields are resilient to missing/null/empty
- [ ] Unknown employee flow is graceful
- [ ] Insufficient-info helper is visible when applicable
- [ ] No runtime crash observed in tested flows
