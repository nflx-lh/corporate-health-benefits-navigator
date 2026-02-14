# Local Runbook (MVP)

## Start
docker compose up --build

## Stop
docker compose down

## API
http://localhost:8000/v1/health

## Swagger
http://localhost:8000/docs

---

## Phase 5 — Eval Harness & Verification

### Prerequisites

```bash
# Install Python dependencies (from repo root)
pip install -r requirements.txt
```

### Start Backend (local, no Docker)

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

### Run Backend Test Suite

```bash
# All tests (from repo root)
python -m pytest tests/ -v

# Phase 1 regression only
python -m pytest tests/test_rule_engine.py tests/test_query_endpoint.py -v

# Phase 3 orchestration only
python -m pytest tests/test_orchestration_graph.py tests/test_query_endpoint_orchestrated.py -v
```

### Run Eval Harness

Requires backend running on port 8000.

```bash
# Default (20s timeout per case)
python scripts/run_eval.py

# With higher timeout for cold-start model loading
python scripts/run_eval.py --timeout 60

# Custom cases file
python scripts/run_eval.py --cases eval/eval_cases.json --timeout 60
```

### Verify Artifacts

```bash
# List generated artifacts
ls -la eval/artifacts/

# View latest summary
ls -1t eval/artifacts/eval_summary_*.md | head -n 1 | xargs cat

# View latest JSON results
python -c "import json,glob; f=sorted(glob.glob('eval/artifacts/eval_results_*.json'))[-1]; d=json.load(open(f)); print(json.dumps(d['summary'], indent=2))"
```

### Start Frontend (local dev)

```bash
cd frontend && npm install && npm run dev
```

Frontend dev server runs at http://localhost:5173.
Vite proxy forwards `/v1` requests to http://127.0.0.1:8000.

### Generate MVP Readiness Report

```bash
python scripts/generate_readiness_report.py
```

---

## Phase 6 — Database Setup

### Start with PostgreSQL

```bash
# Start all services including PostgreSQL
docker compose up --build -d

# Verify db service is healthy
docker compose ps
docker compose logs db --tail=20
```

### Migration Safety Checks

```bash
cd backend

# Check current migration state
alembic current

# Verify single migration head (fail if multiple heads)
alembic heads
# Expected: single head "002"

# Run migrations
alembic upgrade head

cd ..
```

### Seed Data

```bash
# Idempotent — safe to re-run
python scripts/seed_employees.py
python scripts/seed_rules.py
```

### REPO_MODE Toggle

Set `REPO_MODE` env var to control data source:
- `db_first` (default when `DATABASE_URL` set): query Postgres first, CSV fallback on error
- `csv_only`: bypass DB entirely (safe rollback path)

```bash
# Force CSV-only mode (rollback path)
REPO_MODE=csv_only python -m pytest tests/ -v

# DB-first mode (default)
DATABASE_URL=postgresql://chbn:chbn_dev@localhost:5432/chbn python -m pytest tests/ -v
```

### Run DB Parity & No-Drift Tests

```bash
# No-drift gate (works without DB — pure CSV path)
python -m pytest tests/test_query_endpoint_nodrift.py -v

# DB parity + fallback tests
python -m pytest tests/test_rule_engine_db_parity.py -v

# Full suite
python -m pytest tests/ -v
```

### Verify Fallback (DB stopped)

```bash
docker compose stop db
DATABASE_URL=postgresql://chbn:chbn_dev@localhost:5432/chbn python -m pytest tests/ -v
docker compose start db
```
