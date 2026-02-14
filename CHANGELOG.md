# Changelog

All notable changes to this project are documented in this file.

---

## [Unreleased]

### Planned
- Phase 2: Clause-aware chunking + local vector index (FAISS)
- Phase 3: LangGraph orchestration (rules-first, retrieval-backed explanations)
- Phase 4: Frontend integration and end-to-end demo flow hardening
- Phase 5: Evaluation harness execution + MVP readiness report

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
