# Testing Strategy

## Test Layers

### 1. Unit Tests (Phase 1–2)

Deterministic tests for rules engine, query parser, and chunker.

```bash
# Run all unit tests
python -m pytest tests/test_rule_engine.py tests/test_chunker.py -v
```

### 2. Integration Tests (Phase 1–3)

Endpoint tests for `/v1/query` and `/v1/query-orchestrated`.

```bash
# Phase 1 endpoint tests
python -m pytest tests/test_query_endpoint.py -v

# Phase 3 orchestration + orchestrated endpoint tests
python -m pytest tests/test_orchestration_graph.py tests/test_query_endpoint_orchestrated.py -v
```

### 3. Retriever Smoke Tests (Phase 2)

Requires sentence-transformers model (downloads on first run).

```bash
python -m pytest tests/test_retriever_smoke.py -v
```

### 4. Eval Harness (Phase 5)

End-to-end evaluation against the live orchestrated endpoint.
Requires backend running on port 8000.

```bash
# Terminal 1 — start backend
cd backend && python -m uvicorn app.main:app --port 8000

# Terminal 2 — run eval
python scripts/run_eval.py --timeout 60
```

**Note:** First run after cold start may need `--timeout 60` for model loading.
Subsequent runs with warm model can use the default `--timeout 20`.

### 5. Frontend Smoke Tests (Phase 4)

Manual checklist at `frontend/SMOKE_TEST.md`. No automated frontend test framework.

## Running the Full Suite

```bash
# All backend tests (from repo root)
python -m pytest tests/ -v

# Eval harness (requires live backend)
python scripts/run_eval.py --timeout 60
```

## Exit Code Policy

- `pytest`: exits 0 only if all collected tests pass
- `scripts/run_eval.py`: exits 0 only if all eval cases pass; exits 1 on any failure or runtime error

## Artifact Outputs

Eval artifacts are written to `eval/artifacts/` with UTC timestamps:
- `eval_results_<ts>.json` — full per-case results
- `eval_summary_<ts>.md` — human-readable summary

### 6. DB Parity & No-Drift Tests (Phase 6)

Ensures DB-backed repositories produce identical outputs to CSV.

```bash
# Golden output no-drift gate (works without DB)
python -m pytest tests/test_query_endpoint_nodrift.py -v

# CSV vs DB parity + fallback observability
python -m pytest tests/test_rule_engine_db_parity.py -v
```

**No-drift normalization:** Both actual and expected `query_id` are set to
`QUERY_ID_STATIC` before comparison. All other fields are exact match
with canonical numeric casting and ordered list equality.

**Fallback tests:** Explicitly named `test_employee_repo_fallback_*` and
`test_rule_repo_fallback_*` to validate structured warning schema:
- `event = "repo_fallback_csv"`
- `repo` in `{"employee_repo", "rule_repo"}`
- `reason` in `{"db_unavailable", "db_empty", "db_error"}`
- `exception_type` present ONLY when `reason == "db_error"`

**REPO_MODE rollback:** Set `REPO_MODE=csv_only` to bypass DB entirely.

## Contract Safety

- `POST /v1/query` semantics are locked and must not change
- `POST /v1/query-orchestrated` is the additive endpoint for orchestrated flow
- All tests validate that deterministic decision fields are preserved
- `rules_engine.py` is frozen — zero drift guaranteed by repo conversion layer
