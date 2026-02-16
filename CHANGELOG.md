# Changelog

All notable changes to this project are documented in this file.

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
