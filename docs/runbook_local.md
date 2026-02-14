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
