# Corporate Health Benefits Navigator (MVP)

Corporate health benefit policies are often lengthy and complex, making it difficult for employees to understand coverage eligibility, required documentation, and claim procedures. This platform addresses that gap by allowing users to ask plain-language questions about benefits (e.g., outpatient, dental, and mental health) and receive immediate, reliable answers.

Coverage decisions are grounded in a deterministic rules engine, while a multi-agent orchestration pipeline (explainer, critic, and safety gate) generates AI-powered explanations with policy citations to improve clarity and transparency.

This solution was developed as an MVP demonstration for a corporate health benefits program using fully synthetic data.

## MVP Scope
- **Benefits:** Outpatient, Dental, Mental Health
- **Users:** Employee, HR Admin
- **Stack:** FastAPI, React 19 / Vite 5, LangGraph, PostgreSQL, Docker Compose, AWS ECS Fargate, Terraform
- **AI:** OpenAI LLM (explainer/critic agents) + embeddings (policy retrieval)

## Project Status
- **v0.13.0** — AWS cloud deployment with RDS persistence (ECS Fargate, RDS PostgreSQL, Terraform IaC, GitHub Actions CI/CD)
- Phases 1–12 complete (rules engine, retrieval, orchestration, frontend, security, admin CRUD, password auth, UI polish, cloud deployment with RDS)

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
- **Admin dashboard** — HR admin login, employee CRUD with modal popups and field validation, password reset queue management
- **Password authentication** — DB-backed bcrypt login, forced password change flow, HR-managed reset queue
- **Security hardening** — JWT auth, RBAC, CORS allowlist, rate limiting, input validation, prompt injection guards, and safe error handling
- **Cloud deployment** — AWS ECS Fargate + RDS PostgreSQL, Terraform IaC (persistent/demo split), GitHub Actions CI/CD with OIDC, deploy-on-demand (~$0 when off)
- **Production-safe data layer** — PostgreSQL persistence with auto-init on startup (CSV seed → DB), `REPO_MODE` safety switch for graceful degradation and test isolation
- **Evaluation harness** — ~326 tests across 24 files, deterministic eval cases, no-drift golden output gates

## Repository Structure
- `backend/app/` — FastAPI backend (routes, auth, services, orchestration)
- `frontend/src/` — React SPA (pages, styles)
- `frontend/public/guides/` — Policy guide markdown files
- `data/` — policy corpus, rules CSV, employee fixtures, embedding index
- `tests/` — automated test suites
- `eval/` — evaluation cases and timestamped artifacts
- `scripts/` — seed, eval, build-index, readiness report
- `terraform/` — IaC (persistent stack + demo stack)
- `.github/workflows/` — CI/CD pipeline
- `docs/DEPLOYMENT.md` — cloud deployment runbook

## Cloud Deployment

Deploy-on-demand to AWS ECS Fargate. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the full runbook.

```bash
# Spin up for demo
cd terraform/demo && terraform apply

# Tear down after
cd terraform/demo && terraform destroy
```

## Attribution
- Images sourced from [Freepik](https://www.freepik.com)