# Lab Informatics

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![CI](https://github.com/jababu3/lab-informatics/actions/workflows/ci.yml/badge.svg)](https://github.com/jababu3/lab-informatics/actions)

A hands-on lab informatics learning environment for drug discovery. Run it entirely on your laptop. Learn by building and breaking things.  Please let me know if you have issues or questions.

This system simulates the core software infrastructure used in real pharmaceutical research:
- **Electronic Lab Notebook (ELN)** with 21 CFR Part 11 compliance
- **Compound registry** with RDKit-computed properties
- **Experiment tracking** and dose-response analytics
- **JWT authentication** backed by PostgreSQL
- **AI Scientist Agent** that generates instrument data and writes ELN entries using a local LLM

Pairs with [lab-data-simulator](https://github.com/jababu3/lab-data-simulator) — a companion repo that generates realistic instrument data (plate readers, liquid handlers, SPR, flow cytometry).

---

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/jababu3/lab-informatics.git
cd lab-informatics
cp .env.example .env
# Edit .env — change JWT_SECRET_KEY to something long and random!

# 2. Start the stack
docker-compose up --build

# 3. Install lab-data-simulator (optional, needed for AI agent)
docker-compose exec backend pip install -e /lab-data-simulator

# 4. Create your first account
open http://localhost:3000/register
```

**Access points:**
| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5433 (labuser / labpassword) |
| MongoDB | localhost:27017 |

---

## AI Scientist Agent

The agent uses `lab-data-simulator` to generate realistic instrument data, analyzes the results, calls a local **Ollama** LLM to write scientific narrative, and posts the result as a signed ELN entry.

```bash
# 1. Install Ollama: https://ollama.com
ollama pull mistral:7b

# 2. Go to the AI Scientist dashboard
open http://localhost:3000/agent
```

**Recommended LLM**: `mistral:7b` (4.5 GB, fast, great at structured scientific writing). Change via `OLLAMA_MODEL` in `.env`.

---

## Authentication

> [!NOTE]
> **Local Development & Cookies:** This application uses `httpOnly` cookies to store JWTs securely against XSS attacks. By default, the `secure` flag on these cookies is set to `False` to allow local development without HTTPS (`http://localhost`). Before deploying to production, you must set `secure=True` in `backend/api/routes/auth.py` and ensure the application is served over HTTPS.

All ELN write operations (create, sign) require login. The first registered user automatically becomes an administrator.

| Route | Who can access |
|---|---|
| `POST /eln/` | Authenticated users |
| `POST /eln/{id}/sign` | Authenticated user whose username matches signer_name |
| `POST /auth/register` | Anyone (first user only) |
| `POST /auth/admin/create-user` | Admin only |
| `GET /auth/users` | Admin only |

---

## Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | FastAPI (Python) | REST API |
| Chemistry | RDKit | Molecular properties, similarity |
| Analytics | scikit-learn + scipy | QSAR models, curve fitting |
| Document DB | MongoDB | ELN entries, experiments, compounds |
| Relational DB | PostgreSQL | User accounts + passwords (bcrypt) |
| Auth | JWT (python-jose) | Stateless authentication |
| LLM | Ollama + mistral:7b | ELN narrative generation |
| Simulator | lab-data-simulator | Instrument data generation |
| Frontend | Next.js | React dashboard |
| Infrastructure | Docker Compose | Local deployment |

---

## Features

- 🔐 **Authentication** — JWT login, bcrypt passwords in PostgreSQL, role-based access (admin/scientist/reviewer)
- 📓 **Electronic Lab Notebook** — 21 CFR Part 11 compliant (audit trail, content hashing, locked signed records)
- ✍️ **Electronic Signatures** — verified against JWT identity per §11.200(a)
- 🤖 **AI Scientist Agent** — autonomous simulation → analysis → LLM narrative → ELN post pipeline
- 🧬 **Compound Management** — SMILES input, RDKit descriptors, Lipinski compliance, similarity search
- 🔬 **Experiment Tracking** — link compounds to assays, track status, store results
- 📊 **Analytics** — QSAR modeling, dose-response curve fitting (4PL)
- 📁 **File Attachments** — uploadable documents on ELN entries
- 🔗 **Data Ingestion** — CSV import pipeline for instrument data

---

## Learning Modules

| Module | Topics |
|---|---|
| [01 — SQL & Data](./learning/01_sql_and_data/) | Relational databases, ChEMBL schema, JOINs |
| [02 — Auth & Identity](./learning/02_auth_and_identity/) | bcrypt, JWT, roles, PostgreSQL users |
| [03 — Agentic AI](./learning/03_agentic_ai/) | LLM agents, Ollama, prompt engineering, simulators |
| [04 — ELN Compliance](./learning/04_eln_compliance/) | 21 CFR Part 11, audit trails, electronic signatures |
| [05 — Service Layer Pattern](./learning/05_architecture_services.md) | Architectural design, deadlock resolution, abstraction |
| [06 — RBAC & Admin](./learning/06_rbac_administration.md) | AuthZ vs AuthN, user management, 21 CFR Part 11 roles |

---

## Make Commands

```bash
make start         # Start all services
make stop          # Stop all services
make logs          # Tail container logs
make seed          # Load sample compound data
make clean         # Stop and remove volumes (destroys data)
make setup-chembl  # Import ChEMBL database (requires .dmp file)
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MONGO_USERNAME` | `labuser` | MongoDB username |
| `MONGO_PASSWORD` | `labuser` | MongoDB password |
| `POSTGRES_PASSWORD` | `labuser` | PostgreSQL password |
| `JWT_SECRET_KEY` | `change-me-...` | **Change this!** Secret for signing JWTs |
| `JWT_EXPIRE_MINUTES` | `480` | Token lifetime (8 hours) |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `mistral:7b` | LLM model for ELN narrative generation |
| `AGENT_JWT_TOKEN` | _(empty)_ | Service account token for agent auto-posting |

---

## License

MIT
