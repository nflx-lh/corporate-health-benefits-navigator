# Changelog

All notable changes to this project are documented in this file.

---

## [0.18.1] `v0.18.1-phase17-freeze` - 24-Mar-2026 — Analytics & UI Fixes

### Fixed
- **Analytics logging**: `log_query()` was defined but never called — wired into `/v1/query-orchestrated` route so queries are now actually recorded.
- **Required documents formatting**: Displayed in Title Case without underscores (e.g. `Invoice, Treatment Summary` instead of `invoice, treatment_summary`).
- **Sidebar width**: Increased from 22% to 26% to prevent guide button text from wrapping.

### Added
- **Policy Gaps breakdown**: New "Policy Gaps" table in Analytics tab — for `insufficient_info` queries, the LLM extracts an anonymous 2–4 word benefit topic (e.g. "Yoga Classes", "Weight Management") and logs it, so HR can see exactly what benefit areas employees are asking about that the system cannot answer.
- **LLM topic extraction**: When a query returns `insufficient_info` and has no parsed service category, a lightweight LLM call extracts the benefit topic anonymously before logging. Silent on failure — falls back gracefully if LLM is unavailable.
- **Analytics dashboard redesign**: Stat cards with teal accent border and shadow; table sections styled as cards; Policy Gaps table shows top 3 by count (highest first) with a "Show all" toggle.

---

## [0.18.0] - 24-Mar-2026 — HR Analytics Dashboard (Phase 17)

### Added
- **Anonymous query logging**: Every `/v1/query-orchestrated` call logs benefit_type, service_category, and decision to a new `query_logs` DB table — no employee PII stored.
- **`QueryLogDB` model**: New SQLAlchemy model auto-created on startup via `Base.metadata.create_all()`.
- **`GET /v1/admin/analytics`**: New HR admin-only endpoint returning total queries, last-7-days count, and breakdowns by decision and benefit type.
- **Analytics tab**: New tab in the admin dashboard with stat cards (Total Queries, Last 7 Days) and breakdown tables (By Decision, By Benefit Type).
- **Graceful degradation**: Analytics logging and retrieval are silent on failure — `csv_only` mode returns empty stats without error.

---

## [0.17.0] - 24-Mar-2026 — Evaluation Suite (Phase 16)

### Added
- **Golden eval dataset expanded**: `eval/eval_cases.json` grown from 15 → 30 cases (EVAL016–EVAL030), covering cosmetic procedure exclusions (all plan tiers), day surgery with preauth, mental health tenure gates, diagnostic imaging, restorative dental, cosmetic dental, orthodontic exclusions, intensive therapy, and contract employee edge cases.
- **CI golden eval step**: `.github/workflows/ci.yml` now starts the backend in `REPO_MODE=csv_only` / `LLM_ENABLED=false` after the smoke import and runs `scripts/run_eval.py` against it. CI fails if any golden case regresses.
- **Human eval scorecard**: `eval/human_eval_scorecard.md` — structured 10-case scoring template (Accuracy, Clarity, Tone, Completeness, 1–5 scale) with pass threshold mean ≥ 3.5 and overall pass rate guidance.
- **Human eval review 1**: `eval/human_eval_review_1.md` — first completed review run (10 cases, 9/10 passed, 90% pass rate). One failure identified: contract employee dental exclusion reason incorrectly explained as "no coverage rules" (P0 finding for future fix).

### Fixed
- **`test_seed_rules.py` row count**: Updated assertions from 46 → 51 to match the current `benefit_rules.csv` (R048–R052 added in Phase 15).

### Deferred
- **Layer 2 (DeepEval LLM quality metrics)**: Requires live LLM API calls — cannot run in CI. Deferred post-submission.
- **Layer 3 (CloudWatch alarms)**: Pure Terraform/infra work, no user-visible output. Deferred post-submission.

### Architecture Notes
- Layer 1 (golden eval + CI gate) and Layer 4 (human eval scorecard) are complete. Layer 2 and Layer 3 deferred.
- Eval cases run deterministically — LLM disabled in CI. Human eval scorecard used for periodic LLM quality spot-checks with LLM enabled.

---

## [0.16.0] - 24-Mar-2026 — Cloud RAG & Production Hardening (Phase 15)

### Fixed

**Cloud RAG Pipeline**
- **Policy index not found in Docker**: `_DEFAULT_INDEX_DIR` in `nodes.py` used `parents[3]` which resolves to `/` inside the container (missing `backend/` directory level). Fixed via `DATA_ROOT` env var (`ENV DATA_ROOT=/app/data` in `Dockerfile.prod`) with local fallback.
- **Index not bundled in Docker image**: `Dockerfile.prod` only created an empty `data/index/` directory. Changed to `COPY data/index ./data/index` — pre-built index (chunks.jsonl, embeddings.npy, meta.json) now baked into the image. LLM now receives policy citations in cloud.

**DB Seeding**
- **employees.csv / benefit_rules.csv not found in Docker**: `init_db.py` used `parents[3]` (same bug) resolving to `/data/fixtures/` instead of `/app/data/fixtures/`. Fixed via `DATA_ROOT` env var.
- **seed_rules.py same path bug**: `_DEFAULT_CSV` used `parents[3]` — same fix applied.

**Rules Engine**
- **Cosmetic surgery incorrectly returned Covered**: `cosmetic_procedure` exclusion rule (R024) only existed for `plus/full_time`. For Premium and Basic plan employees, the rules engine fell back to `general_consult` (covered at 90%). Added R048–R052 covering all missing plan/employment combinations. Rules table now has 52 rows (up from 46).

**LLM Response Quality**
- **Rigid template-style responses**: System prompt used "Format example (follow this style exactly)" which caused slot-filling behaviour. Replaced with conversational guidance — LLM now leads with a direct yes/no and uses natural language.

**Frontend**
- **Copy button silent fail on HTTP**: `navigator.clipboard.writeText()` requires HTTPS. On the HTTP ALB endpoint, the call silently failed. Added `document.execCommand('copy')` fallback in `TempPasswordModal`.

### Added
- `backend/app/scripts/seed_rules.py` — one-off ECS task to upsert benefit rules from CSV into RDS. Idempotent (upsert by rule_id). Referenced in `docs/DEPLOYMENT.md`.
- `tests/test_seed_rules.py` — tests for the seed_rules script.

### Changed
- `docs/DEPLOYMENT.md`: added seed rules one-off ECS task runbook section.

### Architecture Notes
- `DATA_ROOT=/app/data` is the canonical path inside Docker for all data file lookups (fixtures, rules, index). Local dev uses `parents[N]` fallback.
- Rules count: 46 → 52 (added cosmetic_procedure exclusions for all plan/employment tiers).
- Version follows `phase + 1` convention: Phase 13 = v0.14.0, Phase 14 = v0.15.0, Phase 15 = v0.16.0.

---

## [0.15.0] - 24-Feb-2026 — Deterministic Deploy & DB-Only Production (Phase 14)

### Changed
- **SHA-tagged images enforced**: ECS task definitions pinned to exact Git SHA — `:latest` never used for deployment
- **db_only enforcement**: When `enable_rds=true`, `REPO_MODE` forced to `db_only` — no CSV fallback in production
- **DATABASE_URL via SSM**: Wired as ECS secret from SSM SecureString (`/chbn/dev/database-url`) — never in plaintext env vars
- **IAM hardening**: Added EC2 networking permissions (`ec2:Describe*`, route table, subnet, IGW ops) to GitHub Actions role for Terraform VPC management

### Infrastructure
- `terraform/modules/ecs/main.tf`: `REPO_MODE=db_only` injected when RDS enabled; `DATABASE_URL` injected via `secrets` from SSM ARN
- `terraform/modules/iam/main.tf`: Extended EC2 permissions for full Terraform VPC lifecycle management
- `.github/workflows/deploy.yml`: `TF_INPUT=false`, `-lock-timeout=5m`, `TF_LOG=INFO` with artifact upload, 20-minute job timeout

---

## [0.14.0] - 24-Feb-2026 — CI/CD Fix & ECS Runtime Hardening (Phase 13)

### Fixed
- **Deploy workflow secrets**: `TF_VAR_*` secrets now passed as environment variables to Terraform apply step
- **Terraform prompts disabled**: `TF_INPUT=false` prevents workflow from hanging on interactive prompts
- **Deploy timeout**: Added 20-minute job timeout to prevent runaway workflows

### Changed
- **Terraform logging**: `TF_LOG=INFO` + `TF_LOG_PATH=terraform.log` with artifact upload on every run for debugging
- **Lock timeout**: `-lock-timeout=5m` added to `terraform apply` to handle state lock contention

---

## [0.13.0] - 23-Feb-2026 — AWS Cloud Deployment & RDS Persistence (Phase 12)

### Added

**Infrastructure — Terraform**
- **Terraform persistent stack** (`terraform/persistent/`): ECR repos (chbn-api, chbn-web), IAM roles (ECS exec + GitHub Actions OIDC), SSM params (JWT secret + OpenAI API key)
- **Terraform demo stack** (`terraform/demo/`): VPC, ALB, ECS Fargate, CloudWatch logs — fully destroyable ephemeral resources
- **7 Terraform modules** (`terraform/modules/`): `ecr`, `iam`, `ssm`, `vpc`, `alb`, `ecs`, `rds` — 21 files total
- **RDS Postgres module** (`terraform/modules/rds/`): `aws_db_instance` (db.t3.micro, PostgreSQL 16.4), `aws_db_subnet_group`, `aws_security_group` (5432 from ECS only), `random_password` for credentials
- **Private subnets** in VPC module: 2 private subnets (one per AZ) with isolated route table, gated by `enable_private_subnets` — no NAT gateway

**Infrastructure — Docker & Deploy-on-Demand**
- **Production Dockerfiles**: multi-stage builds for backend (`backend/Dockerfile.prod`) and frontend (`frontend/Dockerfile.prod`)
  - Backend: Python 3.11-slim, non-root `appuser`, healthcheck, graceful `data/index/` handling
  - Frontend: Node 20 builder → nginx:alpine runtime with SPA fallback
- **nginx config** (`frontend/nginx.conf`): SPA fallback, guide markdown serving as `text/plain`, security headers, gzip
- **docker-compose.prod.yml**: local test of production images (no DB, no volumes)
- **Deploy-on-demand workflow** (`.github/workflows/deploy.yml`): manual trigger (`workflow_dispatch`), OIDC auth, build + push to ECR, optional ECS deploy with service stability wait

**Backend**
- **DB auto-initialisation** (`backend/app/db/init_db.py`): on startup, creates tables via `Base.metadata.create_all()` and seeds employees + benefit rules from CSV if tables are empty
- **Startup hook** in `main.py`: `@app.on_event("startup")` calls `init_db()` — safe no-op when `REPO_MODE=csv_only`
- **Deployment runbook** (`docs/DEPLOYMENT.md`): first-time setup, demo day spin-up (CSV-only and RDS modes), persistence test steps, teardown checklist, cost guardrails

### Changed

**Terraform**
- `terraform/demo/main.tf`: conditionally creates RDS module and VPC private subnets when `enable_rds=true`; added `random` provider
- `terraform/modules/ecs/main.tf`: API task image uses `var.api_image` directly (no `:latest` suffix); environment uses `concat()` to conditionally inject `DATABASE_URL`; `REPO_MODE` switches to `dual` when RDS enabled
- `terraform/modules/alb/main.tf`: ALB listener rule forwards `/docs*`, `/openapi.json`, `/redoc*` to API target group (Swagger UI accessible via ALB)

**Backend — Repository hardening**
- `backend/app/db/session.py`: `REPO_MODE` standardised to three values (`csv_only`, `dual`, `db_only`; default `dual`); exported as public constant
- `backend/app/services/employee_repo.py`: removed import-time CSV loading; CSV now loaded lazily on first access; `get_employee()` respects `REPO_MODE` (`csv_only` → CSV only, `db_only` → DB only with RuntimeError on missing DB, `dual` → DB-first with CSV fallback)
- `backend/app/services/rule_repo.py`: same lazy-loading and `REPO_MODE`-aware refactor as employee_repo
- `backend/app/orchestration/nodes.py`: explainer node returns `None` gracefully when LLM returns empty/non-string result

**Config & Docs**
- `.gitignore`: added Terraform entries (`.terraform/`, `*.tfstate*`, `*.tfvars`, `.terraform.lock.hcl`)
- `README.md`: updated project status to v0.13.0, added cloud deployment section
- `docs/DEPLOYMENT.md`: full rewrite with dual-mode architecture (CSV-only and RDS), cost tables, persistence test steps, RDS technical details

**Tests**
- `tests/conftest.py`: added `REPO_MODE=csv_only` default for test environment
- `tests/test_rule_engine_db_parity.py`: fallback tests now patch `REPO_MODE` to `dual`; employee db_empty test expects CSV fallback (not None); added `TestEmployeeRepoFallbackDbEmptyNotInCsv` for unknown-ID case
- 327 tests pass (up from 325)

### Architecture
- **Deploy-on-demand**: ~$0.90/day CSV-only, ~$1.25/day with RDS; ~$0.50/month when off (ECR storage only)
- **No NAT Gateway**: ECS in public subnets, RDS in private subnets (reachable only from ECS)
- **Separate Terraform states**: persistent (ECR/IAM/SSM) and demo (VPC/ALB/ECS/RDS) with independent lifecycles — `terraform destroy` in demo/ does NOT touch persistent resources
- **RDS cleanup**: `skip_final_snapshot=true`, `deletion_protection=false`, `backup_retention_period=0` — `terraform destroy` removes RDS cleanly
- **Lazy CSV repos**: importing `employee_repo` or `rule_repo` no longer reads CSV at import time — production-safe for containers where fixtures may not exist

### Notes
- `rules_engine.py` is NOT modified
- `docker-compose.yml` (dev workflow) unchanged
- CloudWatch log retention: 7 days
- Checkpoint tag planned: `v0.13.0-phase12-freeze`

---

## [0.12.1] - 23-Feb-2026 — Admin UX & Guide Styling

### Changed
- **Employee form validation**: Name, Age, Employment Type, and Plan Tier are now required fields (HTML + JS-level validation with inline error messages)
- **Edit form → modal popup**: clicking Edit on a table row now opens the form in a centered overlay instead of inline above the table
- **Delete confirmation → modal popup**: delete prompt now appears as a centered overlay with "This action cannot be undone" warning
- **Table display formatting**: `full_time` → "Full Time", `part_time` → "Part Time", `basic` → "Basic", `premium` → "Premium", etc. via `formatLabel` helper
- **Guide drawer background**: soft peach (`#fef0e8`) with subtle wave pattern for all 3 policy guides
- **Guide popup window**: same peach + wave background retained when opening a guide in a new window
- **Modal animations**: fade-in backdrop + slide-up content for edit and delete modals

### Notes
- EMP025 seed data intentionally left unchanged (blank name/tenure) — used by `insufficient_info` test cases
- `rules_engine.py` is NOT modified

---

## [0.12.0] - 22-Feb-2026 — UI Polish & Content Refinement

### Changed
- **LLM explainer prompt** restructured with format example, one-fact-per-line style, and added "Please note to retain a copy of the required documents stated below" line
- **`plan_tier` capitalization**: `raw_plan.title()` applied in `run_rules_engine_node` so plan names display as "Premium" instead of "premium"
- **LLM output post-processing**: regex inserts newlines before key patterns (Current Plan, Annual limit, Co-pay, Please refer, Please note) for proper line-by-line rendering
- **`import re` moved** to top-level imports in `nodes.py`
- **Navigator page scroll fix**: removed `overflow: hidden` lockdown on desktop layout; page now scrolls naturally so Technical Details section is fully accessible
- **Policy guide rewrite**: all 3 guides (`coverage_eligibility_guide.md`, `claims_preauth_guide.md`, `exclusions_clarifications_guide.md`) restructured from clause-per-line format to flowing paragraphs with policy reference codes grouped at the end of each section
- **Sidebar background**: changed to `grassfield.png`
- **Guide card backgrounds**: removed image backgrounds, replaced with semi-transparent dark overlay
- **Helper text**: "Guides for manual references" color changed to white, trailing period removed
- **Insufficient info message**: updated to "Your query cannot be found in database."

### Notes
- `rules_engine.py` is NOT modified
- Checkpoint tag planned: `v0.12.0-phase11-freeze`

---

## [0.11.0] - 22-Feb-2026 — Password Reset & Real Auth

### Added
- Password-based authentication with bcrypt-hashed DB credentials
  - DB-first login with demo credential fallback (backward compat for HR001, EMP001-EMP003)
  - `must_reset_password` flag in login response for forced password change flow
- Password reset flow (HR-managed, no email/SMS):
  - `POST /v1/auth/employee/request-password-reset` — public endpoint, no info leak
  - `GET /v1/admin/password-reset-requests?status=pending` — HR admin list
  - `POST /v1/admin/password-reset-requests/{id}/reset` — approve, generate temp password
  - `POST /v1/admin/password-reset-requests/{id}/reject` — reject with optional notes
- Change password endpoint: `POST /v1/auth/employee/change-password` (authenticated, min 8 chars)
- Temp password generation on employee creation (returned once in create response)
- Alembic migration `003_add_password_fields`: `password_hash` + `must_reset_password` on employees, new `password_reset_requests` table
- `PasswordResetRequestDB` model (`backend/app/models/password_reset_db.py`)
- Password utility module (`backend/app/auth/password.py`): `hash_password`, `verify_password`, `generate_temp_password`
- Frontend: password field on employee login page with "Forgot password?" reset request flow
- Frontend: `ChangePasswordPage` — forced password change before app access
- Frontend: `PasswordInput` component with eye icon toggle for password visibility
- Frontend: Admin dashboard tabs (Employee Management / Reset Requests) with notification badge
- Frontend: Reset Requests management table with Reset/Reject actions
- Frontend: Temp password modal with copy-to-clipboard after employee creation or reset approval
- 14 new tests in `tests/test_password_reset.py` (326 total, up from 312)

### Changed
- `requirements.txt`: added `bcrypt==4.2.1`
- `routes_auth.py`: rewritten — DB-first login, change-password, request-password-reset endpoints
- `routes_employee_crud.py`: employee create now returns `temp_password`, added admin reset management endpoints
- `employee_db.py`: added `password_hash` and `must_reset_password` columns
- `alembic/env.py`: registered `PasswordResetRequestDB` model
- `App.jsx`: routes through `ChangePasswordPage` when `mustResetPassword` is true
- `LoginPage.jsx`: password input field, forgot password inline flow
- `AdminPage.jsx`: tabbed layout, reset requests section, temp password modal, alert badge
- `login.css`: styles for password toggle, forgot link, change password page
- `admin.css`: styles for tabs, notification badge, temp password modal
- `test_auth_jwt.py`: added `must_reset_password` assertion on login response
- `test_employee_crud.py`: added `temp_password` assertion on create response

### Notes
- Demo credentials (HR001, EMP001-EMP003) remain functional for backward compatibility
- `rules_engine.py` is NOT modified
- Checkpoint tag planned: `v0.11.0-phase10-freeze`

---

## [0.10.0] - 17-Feb-2026

### Added
- Dedicated Admin Page with two-phase flow (login form → employee dashboard)
  - Admin login form authenticates via `POST /v1/auth/login` with JWT token
  - Validates `hr_admin` role before granting dashboard access
  - Employee management table with Create, Edit, Delete operations
  - Inline employee form with validation (ID pattern, age, employment type, plan tier, tenure, dependents, active status)
  - Delete confirmation dialog
  - "Back to Employee Login" navigation from admin login
- Employee CRUD API endpoints (`/v1/admin/employees`):
  - `GET` — list all employees (hr_admin only)
  - `POST` — create employee (409 on duplicate)
  - `GET /{id}` — read single employee
  - `PUT /{id}` — update employee fields
  - `DELETE /{id}` — delete employee
- Admin icon FAB on login page now opens in-app admin login
- Admin page styles (`admin.css`) with BEM naming, matching green/dark palette, responsive layout
- CORS extended to allow PUT and DELETE methods
- 312 tests across 23 files (up from 301 across 22)

### Changed
- `App.jsx`: added `adminMode` state; routes to `AdminPage` when active
- `LoginPage.jsx`: admin FAB wired to `onAdminLogin` prop
- `main.py`: registered employee CRUD router, added PUT/DELETE to CORS allow_methods

### Notes
- Checkpoint tag planned: `v0.10.0-phase9-freeze`
---

## [0.9.1] - 17-Feb-2026

### Added
- Branded login page with split-panel layout, AnovaGreen header, and dedicated CSS modules
- Navigator page redesign: search-first UX replacing chatbot-style interface
- Policy Library sidebar with image-backed guide cards
- Guide drawer with markdown rendering, anchor navigation, and open-in-new-window support
- Policy guide files (Coverage & Eligibility, Claims & Pre-authorization, Clarifications & Exclusions)

### Changed
- Replaced `react-markdown` with lightweight built-in markdown converter (~43% bundle reduction)
- Vite config: added plugin to serve guide `.md` files in dev server

### Notes
- Checkpoint tag planned: `v0.9.0-phase8-freeze`
---

## [0.9.0] - 16-Feb-2026

### Added
- Phase 8 Part A (Multi-Agent Pipeline) + B-804 (Response UI Redesign):
  - Provider-agnostic LLM and embedding clients with graceful degradation (returns `null` on failure/disabled)
  - Explainer node: generates plain-language AI summary from rule decision + policy citations
  - Critic node: validates LLM output consistency with deterministic decision, with retry loop
  - Safety gate: validates AI summary against rule keywords before response, falls back on mismatch
  - New response fields on `POST /v1/query-orchestrated`: `ai_summary` (nullable) and `ai_summary_source` (`"llm"` | `"fallback"`)
  - Orchestration graph rewired with explainer → critic → conditional retry/compose flow
  - New benefit rules R044–R047 (orthodontics exclusion)
  - Query parser: refined keyword mapping for dental service categories
  - Frontend result panel redesign: AI summary primary zone, action alerts, collapsible detail panel
  - `pytest.ini` and `Makefile` for build/test convenience
  - 301 tests across 22 files (up from ~219 across 21)

### Changed
- Embedding pipeline migrated from local sentence-transformers to OpenAI API
- `benefit_rules.csv`: R012 preauth corrected, duplicate R041 removed, R044–R047 added (47 rules total)
- `requirements.txt`: added `openai>=1.58.0`, removed `sentence-transformers`
- `.env.example`: added LLM/embedding provider settings, removed unused keys
- `tests/conftest.py`: overhauled with env loading, shared fixtures, limiter reset

### Notes
- `rules_engine.py` is NOT modified — deterministic decisions remain authoritative
- AI summary is always validated against deterministic decision before display
- LLM failures degrade gracefully: `ai_summary=null`, `ai_summary_source="fallback"`
- Embedding pipeline migrated from local sentence-transformers to OpenAI API; retriever returns empty list on embedding failure
- 301 tests across 22 test files (up from ~219 across 21)
- Checkpoint tag planned: `v0.9.0-phase8-freeze` only after Phase 8 Part B concludes.

---

## [0.8.1] - 15-Feb-2026

### Added
- Employee verification endpoint (`GET /v1/employees/{id}/verify`)
  - Returns 200 if employee exists, 404 if not found, 422 if invalid format
- Server-side employee validation on login page before granting access

### Fixed
- Rate limiting enforcement: added missing `SlowAPIMiddleware` registration
- Vite proxy target updated to use Docker service name (`http://api:8000`)

### Changed
- Default rate limit reduced from 60/minute to 30/minute

---

## [0.8.0] - 15-Feb-2026

### Added
- Phase 7 Security Hardening (B-701 through B-710):
  - JWT authentication with full claims validation (`backend/app/auth/jwt_handler.py`)
    - Token creation with sub, role, exp, iat, aud claims
    - Decode with signature, expiry, audience, and required-claim checks
  - Auth dependency with APP_ENV gate (`backend/app/auth/dependencies.py`)
    - Dev mode returns default `hr_admin` user without requiring a token
    - Non-dev mode enforces full JWT validation
  - RBAC enforcement matrix (`backend/app/auth/rbac.py`)
    - `/v1/query`, `/v1/query-orchestrated`: employee + hr_admin
    - `/v1/admin/reindex`: hr_admin only
    - `/v1/health`, `/v1/auth/login`: public (no auth)
  - Real login endpoint with JWT issuance (`backend/app/api/routes_auth.py`)
    - MVP demo credential map (EMP001–EMP003, HR001)
  - Centralised Settings class (`backend/app/config.py`)
    - APP_ENV, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_AUDIENCE
    - RATE_LIMIT, CORS_ORIGINS with env-aware defaults
    - Startup secret validation (rejects `change_me` in non-dev)
  - Input validation guardrails on `QueryRequest`:
    - `employee_id`: pattern `^[A-Z]{2,5}\d{1,6}$`, max 20 chars
    - `question`: max 500 chars, whitespace stripped, `extra="forbid"`
  - Custom 422 exception handler with structured `VALIDATION_ERROR` response
  - CORS strict allowlist via `CORSMiddleware`
    - Dev: defaults to `["*"]`; staging/prod: explicit origins only
  - Rate limiting via `slowapi` on query endpoints (default 60/minute)
    - Custom 429 response: `RATE_LIMIT_EXCEEDED`
  - Safe error handling (`backend/app/middleware/error_handler.py`)
    - Global catch-all returns safe 500 with `INTERNAL_ERROR` (no stack traces)
    - HTTPException pass-through with structured `{"error": {...}}` wrapping
  - Sensitive logging hygiene (`backend/app/middleware/log_sanitizer.py`)
    - Scrubs JWT tokens, passwords, API keys from log records
  - Prompt injection & output leakage guardrails (`backend/app/services/input_sanitizer.py`)
    - Strips known injection patterns (ignore instructions, system prompt markers, etc.)
    - File path sanitization for decision_path outputs
  - 8 new test files (88 new tests, 190 total):
    - `tests/test_auth_jwt.py` (19 tests)
    - `tests/test_auth_rbac.py` (11 tests)
    - `tests/test_input_validation.py` (11 tests)
    - `tests/test_cors.py` (4 tests)
    - `tests/test_rate_limiting.py` (3 tests)
    - `tests/test_error_handling.py` (5 tests)
    - `tests/test_logging_hygiene.py` (8 tests)
    - `tests/test_secrets_hygiene.py` (5 tests)
    - `tests/test_prompt_injection.py` (12 tests)
    - `tests/test_token_lifecycle.py` (10 tests)

### Changed
- `requirements.txt`: added `slowapi==0.1.9`
- `.env.example`: added `JWT_AUDIENCE`, `RATE_LIMIT`, `CORS_ORIGINS`
- `backend/app/main.py`: added CORSMiddleware, rate limiter, exception handlers, logging setup
- `backend/app/api/routes_query.py`: added RBAC + rate limit + input sanitization
- `backend/app/api/routes_query_orchestrated.py`: added RBAC + rate limit + input sanitization
- `backend/app/api/routes_admin.py`: added hr_admin-only RBAC
- `backend/app/models/decision.py`: hardened `QueryRequest` with field validators
- `tests/test_query_endpoint.py`: updated `UNKNOWN` → `UNK001` for validation compliance
- `tests/test_query_endpoint_orchestrated.py`: updated `UNKNOWN` → `UNK001`

### Notes
- `rules_engine.py` is NOT modified — zero drift guaranteed
- `POST /v1/query` and `POST /v1/query-orchestrated` response schemas remain unchanged
- All 102 existing tests pass unchanged in dev mode (APP_ENV=development)
- Auth error responses follow unified `{"error": {"code": "...", "message": "..."}}` format
- Checkpoint tag planned: `v0.8.0-phase7-freeze`

---

## [0.7.0] - 14-Feb-2026

### Added
- Phase 6 DB Foundation:
  - PostgreSQL service (`db`) in `docker-compose.yml` with healthcheck and `depends_on`
  - SQLAlchemy engine/session factory (`backend/app/db/session.py`) with `REPO_MODE` toggle
  - Alembic migration scaffold (`backend/alembic/`)
  - Employee DB model + migration `001_create_employees`
  - BenefitRule DB model + migration `002_create_benefit_rules`
  - Idempotent, transactional seed scripts (`scripts/seed_employees.py`, `scripts/seed_rules.py`)
    - Upsert by key, rollback on failure, prints inserted/updated/skipped counts
  - Dual-read repos: DB-first with CSV fallback and structured warning logging
  - Deterministic rule ordering (`ORDER BY rule_id ASC`)
  - Shared `normalize_response_for_parity()` helper (`tests/parity_helpers.py`)
  - No-drift golden output test gate (`tests/test_query_endpoint_nodrift.py`)
    - Covers `/v1/query` (full payload) and `/v1/query-orchestrated` (core decision fields)
  - DB parity test (`tests/test_rule_engine_db_parity.py`)
  - Explicit fallback tests: `test_employee_repo_fallback_*`, `test_rule_repo_fallback_*`
  - Golden output fixture (`tests/fixtures/query_golden_outputs.json`)

### Changed
- `requirements.txt`: added `sqlalchemy==2.0.36`, `psycopg2-binary==2.9.10`, `alembic==1.14.1`
- `.env.example`: updated `DATABASE_URL` for PostgreSQL, added `POSTGRES_*` vars and `REPO_MODE` toggle
  - Documents both `localhost` (host-run API) and `db` (compose network) variants
- `employee_repo.py`: DB-first lookup with CSV fallback, structured warning logging
- `rule_repo.py`: DB-first lookup with CSV fallback, deterministic ordering, structured warning logging
- `docs/runbook_local.md`: added Phase 6 database setup, migration safety checks, REPO_MODE docs
- `docs/testing_strategy.md`: added DB parity & no-drift test layer

### Notes
- `rules_engine.py` is NOT modified — zero drift guaranteed by repo conversion layer
- `POST /v1/query` and `POST /v1/query-orchestrated` contracts remain unchanged
- Fallback warnings follow exact schema: `{event, repo, reason[, exception_type]}`
- `REPO_MODE=csv_only` provides a safe rollback path to bypass DB entirely
- Checkpoint tag planned: `v0.7.0-phase6-freeze`

---

## [0.6.0] - 14-Feb-2026

### Added
- Phase 5 deterministic eval harness (`scripts/run_eval.py`):
  - Executes `eval/eval_cases.json` against `POST /v1/query-orchestrated`
  - Per-case PASS/FAIL with explicit failure reasons
  - Malformed eval case handling includes standalone token `INVALID_CASE_SCHEMA` and continues processing remaining cases
  - Timestamped JSON + markdown artifacts in `eval/artifacts/`
  - Emits run-level fatal artifacts on pre-run failures (e.g., missing/invalid cases file) with `fatal_error` traceability
  - Strict exit code policy: 0 only if all cases pass
  - CLI args: `--base-url`, `--cases`, `--timeout`
- MVP readiness report generator (`scripts/generate_readiness_report.py`):
  - Reads latest eval artifacts (or `--eval-results` override)
  - Accepts optional `--pytest-summary` JSON input for Test Status reporting
  - Produces GO / CONDITIONAL GO / NO-GO verdict with demo checklist

### Changed
- `docs/testing_strategy.md`: full testing strategy covering Phases 1–5
- `docs/runbook_local.md`: added Phase 5 command blocks (eval, artifacts, report)
- `.gitignore`: added `!eval/artifacts/.gitkeep` exception

### Notes
- `POST /v1/query` semantics remain unchanged.
- Eval harness is observation-only; no route or decision logic modifications.
- Checkpoint tag planned: `v0.6.0-phase5-freeze`.
---

## [0.5.0] - 14-Feb-2026
### Added
- Phase 4 Frontend integration with `POST /v1/query-orchestrated` for orchestrated benefits queries.
- Deterministic smoke checklist for Phase 4 validation (`frontend/SMOKE_TEST.md`).

### Changed
- Navigator result rendering hardened for optional enrichment fields:
  - `explanation` and `policy_citations` may be missing/null/empty without UI failure.
- Financial display normalized with safe fallbacks:
  - `annual_limit` / `annual_limit_sgd` mapping
  - `remaining_limit` and `estimated_payout` fallback rendering
- Improved base result resilience:
  - `reason_summary` fallback
  - `insufficient_info` helper hint in UI
- Frontend runnability fixes:
  - Added/validated build scripts and local `/v1` proxy configuration for dev flow.

### Fixed
- Graceful unknown employee handling (`404`, `EMPLOYEE_NOT_FOUND`) in frontend UX.
- Defensive rendering for empty arrays and absent optional fields (no crash/no undefined artifacts).

### Validation
- Backend API sanity checks:
  - Known employee (`EMP003`) returns `200`
  - Unknown employee (`EMP999`) returns `404` with `EMPLOYEE_NOT_FOUND`
- Frontend smoke checks passed per `frontend/SMOKE_TEST.md`.

### Notes
- Rules-first decision authority remains unchanged.
- No semantic changes to locked `POST /v1/query` contract.
- Phase 4 checkpoint tag planned: `v0.5.0-phase4-freeze`.

---

## [0.4.0] - 14-Feb-2026

### Added
- Phase 3 LangGraph orchestration (rules-first, retrieval-optional explanation path):
  - Orchestration graph with typed state:
    - `backend/app/orchestration/state.py`
    - `backend/app/orchestration/nodes.py`
    - `backend/app/orchestration/graph.py`
  - Safe rollout endpoint:
    - `POST /v1/query-orchestrated`
    - implemented in `backend/app/api/routes_query_orchestrated.py`
  - App router wiring for orchestrated endpoint in `backend/app/main.py`
- Phase 3 tests:
  - `tests/test_orchestration_graph.py`
  - `tests/test_query_endpoint_orchestrated.py`

### Changed
- Added pinned orchestration dependency:
  - `langgraph==1.0.8` in root `requirements.txt`

### Notes
- Existing `POST /v1/query` contract remains unchanged.
- Orchestration is rules-first; retrieval is for explanation enrichment only.
- Phase 3 checkpoint tag planned: `v0.4.0-phase3-freeze`.

---

## [0.3.0] - 14-Feb-2026

### Added
- Phase 2 retrieval foundation (explanation support only; rules-first decisions unchanged):
  - Clause-aware markdown chunking (one chunk per clause) with clause ID preservation for citation traceability.
  - Optional bullet-prefixed clause-start support in policy docs.
  - Strict clause-start candidate validation for malformed clause IDs.
  - Local embedding index pipeline (local numpy/json artifacts; no FAISS in Phase 2):
    - `data/index/chunks.jsonl`
    - `data/index/embeddings.npy`
    - `data/index/meta.json`
  - Retrieval service returning citation-ready top-k hits with deterministic ranking tie-break:
    1. score DESC
    2. source_file ASC
    3. clause_id ASC
    4. chunk_id ASC
  - Build script:
    - `scripts/build_index.py`
  - New Phase 2 tests:
    - `tests/test_chunker.py`
    - `tests/test_retriever_smoke.py`

### Changed
- Dependency layout canonicalized to root `requirements.txt`; removed `backend/requirements.txt`.
- Pinned `httpx==0.27.2` to preserve Starlette `TestClient` compatibility for endpoint tests.

### Notes
- No `/v1/query` contract changes in Phase 2
- Checkpoint tag: `v0.3.0-phase2-freeze`.

---

## [0.2.0] - 14-Feb-2026

### Added
- Phase 1 deterministic rules engine integrated into `/v1/query`.
- Employee/rule repositories with fail-fast CSV schema validation.
- Centralized deterministic query parser for benefit/service mapping.
- Stable decision response schema and reason code output.
- Test coverage for engine and endpoint behavior:
  - `tests/test_rule_engine.py`
  - `tests/test_query_endpoint.py`

### Changed
- `/v1/query` behavior finalized for Phase 1:
  - unknown `employee_id` -> HTTP 404 structured error payload
  - known employee + ambiguous/missing info -> HTTP 200 `insufficient_info`
  - inactive/exclusion outcomes -> financial fields null
  - `required_docs` always returned as list

### Notes
- Checkpoint tag: `v0.2.0-phase1-freeze`.

---

## [0.1.0] - 13-Feb-2026

### Added
- Initialized MVP repository scaffold:
  - `backend/`, `frontend/`, `data/`, `docs/`, `eval/`, `tests/`
- Added local development infrastructure:
  - `docker-compose.yml`
  - `backend/Dockerfile`
  - `frontend/Dockerfile`
  - `.dockerignore`
  - CI scaffold under `.github/workflows/ci.yml`
- Added initial backend/API skeleton:
  - FastAPI app wiring and route stubs for health/auth/query/admin
- Added frontend skeleton:
  - Vite-based setup with initial entry files
- Added core technical docs:
  - `docs/api_contract.yaml`
  - `docs/architecture.md`
  - `docs/db_schema.md`
  - `docs/runbook_local.md`
  - `docs/testing_strategy.md`
  - `docs/security_baseline.md`
- Added synthetic MVP dataset pack:
  - Policy corpus in `data/raw/policies/` (8 policy docs + dataset README)
  - Rules table `data/rules/benefit_rules.csv` (43 rows with `service_category`)
  - Employee fixtures `data/fixtures/employees.csv` (26 rows; includes missing-data and inactive edge cases)
  - Evaluation set `eval/eval_cases.json` (15 cases; 5 covered / 7 not_covered / 3 insufficient_info)
  - Dataset validation artifact `data/validation_report.md`

### Changed
- Standardized policy cross-references and wording consistency across:
  - FAQ clarifications
  - pre-authorization precedence references
  - claims timeline references

### Notes
- All dataset content is synthetic/fictitious for MVP demo use only.
- Cloud deployment intentionally deferred post-MVP.
- Checkpoint tag: `v1.0-dataset-freeze`.
