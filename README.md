# Corporate Health Benefits Navigator (MVP)

Multi-agent, policy-grounded assistant that helps employees understand health benefit eligibility, coverage, required documents, and claim steps.

## MVP Scope
- Benefits: Outpatient, Dental, Mental Health
- Users: Employee, HR Admin
- Stack: FastAPI, React/Vite, LangGraph, SQLite (MVP), Docker Compose

## Project Status
In active development (MVP sprint).

## Quick Start
1. Copy `.env.example` to `.env`
2. Start services:
```bash
   docker compose up --build
```
3. Access:
    - Frontend: `http://localhost:5173` (or your configured port)
    - Backend: `http://localhost:8000/docs`

## Repository Structure
- `backend/` — API + agent orchestration  
- `frontend/` — UI  
- `data/` — policy corpus + fixtures  
- `docs/` — architecture and project docs  
- `tests/` — test suites  

## Notes
- Synthetic data only for MVP.  
- Cloud deployment intentionally deferred post-MVP.
