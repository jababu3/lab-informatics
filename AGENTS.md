# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Development commands

### Primary workflow (Docker Compose + Make)
- `make setup` — copy `.env.example` to `.env` and make scripts executable.
- `make start` — start MongoDB, PostgreSQL, backend, and frontend in detached mode.
- `make rebuild` — rebuild images and start the stack.
- `make stop` — stop services.
- `make logs` — stream container logs.
- `make seed` — seed sample compound data via backend script.
- `make clean` — remove containers and volumes (destructive).

### Direct Docker Compose commands
- `docker-compose up --build` — full startup with image build.
- `docker-compose exec backend pip install -e /lab-data-simulator` — optional install for AI Scientist simulator integration.

### Backend (FastAPI) commands
- Local dev entrypoint from `backend/pixi.toml`: `pixi run start`
  - Runs: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- Seed from backend task: `pixi run seed`
- In running container, ad hoc script execution pattern:
  - `docker-compose exec backend python /app/scripts/<script>.py`

### Frontend (Next.js) commands
- `npm run dev` — Next.js development server.
- `npm run build` — production build.
- `npm run start` — run built app.

### Tests and linting
- No dedicated lint script or automated test suite is currently defined in top-level Make targets, `frontend/package.json`, or backend pixi tasks.
- Existing analysis script often used as a verification utility:
  - `docker-compose exec backend python /app/scripts/msr_test.py`
- If adding tests, place them outside dependency/build folders and document the exact command in this file.

## Architecture overview

## Runtime topology
- The system is a local multi-service stack:
  - `frontend` (Next.js UI)
  - `backend` (FastAPI API)
  - `mongodb` (domain data: compounds, experiments, ELN entries)
  - `postgres` (identity/auth data: users, roles, password hashes)
- Service wiring is defined in `docker-compose.yml`.
- Frontend talks to backend via `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## Backend structure (FastAPI)
- Entry point: `backend/main.py`
  - Registers CORS, security headers middleware, and rate-limiting handler (`slowapi`).
  - Mounts route modules from `api/routes/*`.
  - Health endpoint reports RDKit, MongoDB, and PostgreSQL availability.
- Data access split:
  - `api/database.py`: Mongo client + collections (`compounds`, `experiments`, ELN collection accessed in route/service layer).
  - `api/postgres.py`: SQLAlchemy `User` model + DB session dependency.
- Core route domains:
  - `api/routes/auth.py` — JWT login, first-user bootstrap admin registration, admin user management, profile updates.
  - `api/routes/compounds.py` — compound CRUD + RDKit descriptor computation + similarity search.
  - `api/routes/experiments.py` — experiment CRUD.
  - `api/routes/analytics.py` — QSAR and dose-response computation endpoints.
  - `api/routes/eln.py` — ELN CRUD, file attachments, signatures with 21 CFR Part 11-oriented controls.
  - `api/routes/agent.py` — AI Scientist orchestration endpoints (`/run`, `/status`, `/health`).
- Service layer:
  - `api/services/eln_service.py` holds ELN business logic (hashing, audit trail, record creation) and is reused by both HTTP routes and agent code to avoid loopback deadlocks.
- Computational modules:
  - `services/chemistry.py`, `services/analytics.py`, and related service modules isolate domain calculations from API handlers.

## AI Scientist pipeline
- Main agent implementation: `backend/agents/scientist_agent.py`.
- Pipeline stages:
  1. Simulate experiment data (via optional `lab-data-simulator` package).
  2. Analyze outputs (IC50/KD/purity/flow metrics).
  3. Generate ELN narrative with Ollama (`OLLAMA_HOST`, `OLLAMA_MODEL`).
  4. Assemble structured ELN entry sections.
  5. Persist entry using in-process ELN service (preferred) or HTTP fallback.
- Agent routes in `api/routes/agent.py` expose trigger/status/health and can associate author identity with logged-in user context.

## Frontend structure (Next.js Pages Router)
- App-wide auth context lives in `frontend/src/pages/_app.tsx`.
  - JWT stored in `localStorage` (`lab_jwt`), parsed client-side for user context.
  - Provides `authHeader` helper used by protected API calls.
- Pages in `frontend/src/pages/*` correspond directly to major backend domains:
  - `compounds`, `experiments`, `eln`, `analytics`, `agent`, `admin/users`, `login`, `register`, `profile`.
- Frontend performs direct fetch calls to backend REST endpoints; there is no separate frontend API proxy layer.

## Data and compliance model (important for changes)
- MongoDB stores operational lab records (compounds, experiments, ELN documents/audit artifacts).
- PostgreSQL is the source of truth for users/roles/authentication.
- ELN signing flow enforces identity match and immutability semantics in route/service logic; signed records are treated as locked.
- Many endpoints degrade gracefully when backing services are unavailable (returning empty payloads or 503 depending on route).

## Repository operating constraints
- From `CLAUDE.md`, preserve these constraints during analysis/editing:
  - Do not read or index `chembl_36.dmp`.
  - Avoid reading large `.dmp`, `.sql`, `.csv` files over 1 MB.
  - Ignore `frontend/node_modules/`, `backend/.venv/`, `**/dist/`, and `INSTALL_postgresql/`.
  - Prefer reading dependency manifests (`pyproject.toml`, `package.json`) rather than lockfiles for dependency questions.
