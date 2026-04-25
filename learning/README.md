# Lab Informatics — Learning Modules

## Overview

This repository implements a **local laboratory informatics environment** modeled on the software infrastructure common in pharmaceutical research. It includes an Electronic Lab Notebook (ELN), a compound registry, analytical data pipelines, and an LLM-driven automation agent.

Each module maps to a real industry concept, though every implementation is scoped for instruction rather than production deployment. The system runs entirely on Docker Compose and requires no external accounts or cloud services.

**Trade-offs:** This is an educational sandbox. It does not include the formal validation protocols (IQ/OQ/PQ), high-availability infrastructure, or third-party security audits required for genuine GxP compliance. Where the architecture makes simplifying choices, the relevant module calls them out.

---

## Module Index

| # | Module | Topics |
|---|---|---|
| 01 | [SQL & Data Modeling](./01_sql_and_data/README.md) | Relational schemas, the ChEMBL database, `JOIN` operations |
| 02 | [Authentication & Identity](./02_auth_and_identity/README.md) | Password hashing, JSON Web Tokens, polyglot persistence, RBAC |
| 03 | [Agentic AI](./03_agentic_ai/README.md) | Local LLM orchestration, instrument data simulation, automated ELN generation |
| 04 | [ELN & 21 CFR Part 11](./04_eln_compliance/README.md) | Cryptographic hashing, electronic signatures, audit trails, regulatory scope |
| 05 | [The Services Layer](./05_architecture_services.md) | Separating business logic from HTTP handlers, resolving deadlocks |
| 06 | [RBAC & Administration](./06_rbac_administration.md) | Role enforcement, the admin dashboard, account lifecycle |

---

## Suggested Path

1. **Module 01** — Start with relational data. Understanding how scientific data is structured in normalized tables is foundational to everything else.
2. **Module 02** — Move to authentication. This covers how the system establishes and verifies user identity via JWTs and password hashing.
3. **Module 03** — Explore the AI agent pipeline: simulated instrument data, curve fitting, local LLM narrative generation, and automated ELN entry creation.
4. **Module 04** — Study the regulatory concepts behind 21 CFR Part 11 and how the ELN models (in simplified form) electronic signatures, audit trails, and tamper detection.
5. **Modules 05–06** — These are supplementary. They cover the service-layer refactoring that resolved an architectural deadlock, and the RBAC enforcement model.

---

## Running the System

```bash
# Start all containerized services
docker-compose up --build

# Register the first admin account
open http://localhost:3000/register

# View the backend API documentation
open http://localhost:8000/docs
```

---

## Architecture

```
lab-data-simulator (sibling repository)
        │
        │ pip install -e (editable mount via Docker volume)
        ▼
Scientist Agent Pipeline  ───────────────────────────────────┐
        │                                                     │
        │ Calls local Ollama LLM (mistral:7b)                │
        │                                                     │
        ▼                                                     │
   ELN Service Layer (FastAPI)  ◄── JWT Auth ◄── Frontend (Next.js)
        │                          (PostgreSQL)
        ▼
   MongoDB (ELN entries, content hashes, audit logs)
```
