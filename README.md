# Corporate Health Benefits Navigator (MVP)

Corporate health benefit policies are often lengthy and complex, making it difficult for employees to understand coverage eligibility, required documentation, and claim procedures. This platform addresses that gap by allowing users to ask plain-language questions about benefits (e.g., outpatient, dental, and mental health) and receive immediate, reliable answers.

Coverage decisions are grounded in a deterministic rules engine, while a multi-agent orchestration pipeline (explainer, critic, and safety gate) generates AI-powered explanations with policy citations to improve clarity and transparency.

This solution was developed as an MVP demonstration for a corporate health benefits program using fully synthetic data.

## MVP Scope
- **Benefits:** Outpatient, Dental, Mental Health
- **Users:** Employee, HR Admin
- **Stack:** FastAPI, React 19 / Vite 5, LangGraph, PostgreSQL, Docker Compose
- **AI:** OpenAI LLM (explainer/critic agents) + embeddings (policy retrieval)

## Project Status
- Admin page with employee CRUD management completed (Phase 9 Part A).
- Cloud deployment pending (Phase 10).

## Quick Start
1. Copy `.env.example` to `.env`
2. Start services:
```bash
docker compose up --build
```
3. Access:
   - Frontend: `http://localhost:5173`
   - Backend API docs: `http://localhost:8000/docs`

## Key Features
- **Rules-first decisions** — deterministic engine is the single source of truth; AI enriches but never overrides
- **LLM explainability** — plain-language summaries with critic validation and safety gate
- **Policy Library** — sidebar with guide cards and slide-in markdown viewer
- **Admin dashboard** — HR admin login with employee CRUD management (create, edit, delete)
- **Security hardening** — JWT auth, RBAC, CORS allowlist, rate limiting, input validation, prompt injection guards, and safe error handling
- **Evaluation harness** — automated test suite with deterministic eval cases and no-drift golden output gates

## Repository Structure
- `backend/app/` — FastAPI backend (routes, auth, services, orchestration)
- `frontend/src/` — React SPA (pages, styles)
- `frontend/public/guides/` — Policy guide markdown files
- `data/` — policy corpus, rules CSV, employee fixtures, embedding index
- `tests/` — automated test suites
- `eval/` — evaluation cases and timestamped artifacts
- `scripts/` — seed, eval, build-index, readiness report

## Attribution
- Background images sourced from [Freepik](https://www.freepik.com)
