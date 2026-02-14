# Changelog

All notable changes to this project are documented in this file.

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
