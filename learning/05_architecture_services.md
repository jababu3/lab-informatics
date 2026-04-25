# Module 05: The Services Layer Pattern

## The Problem: Logic in Route Handlers

In simple web applications, business logic is often placed directly inside the HTTP route handlers. As the application grows, this "fat controller" pattern creates two problems: the logic cannot be reused outside of an HTTP context, and it cannot be unit-tested without simulating HTTP requests.

The standard architectural response is to extract business logic into a dedicated **service layer** — a set of plain Python functions that can be called from any context (HTTP handlers, background workers, CLI scripts, tests).

## Why This Project Needed One

### 1. Resolving a Deadlock

The AI Scientist Agent runs as a background thread inside the FastAPI process. When the agent finished generating an ELN entry, it originally tried to save it by making an HTTP POST request back to `localhost:8000/eln/`. But the Uvicorn worker thread was already occupied — it was waiting for the agent's execution to finish. The result was a deadlock: the server could not process the incoming request because the only available worker was blocked waiting for the agent that sent it.

Extracting the persistence logic into `api/services/eln_service.py` allowed the agent to call a Python function directly, bypassing the HTTP layer entirely and eliminating the deadlock.

### 2. Code Reuse (DRY)

Multiple paths create ELN entries in this system:
- A user submitting through the web UI (HTTP POST)
- The AI Agent saving its results (in-process Python call)
- Potentially, a CLI script for bulk data import

Without a service layer, each path would need to independently implement timestamp generation, audit logging, and SHA-256 hashing. Centralizing this logic in a single `create_entry()` function ensures that all code paths apply the same integrity controls.

### 3. Compliance Consistency

The hashing and audit-trail steps are regulatory requirements (§11.10). Isolating them in the service layer makes it structurally difficult for a new code path to skip them — the function either runs the full sequence or it is not the function being called.

**Trade-off:** A service layer adds an extra layer of indirection. For very simple CRUD applications with a single entry point, it can feel like unnecessary abstraction. The value scales with the number of distinct callers.

---

## Implementation

The service module encapsulates the domain logic:

```python
# api/services/eln_service.py
def create_entry(entry_data: ELNEntry, current_user: User) -> dict:
    # 1. Generate UUID and UTC timestamps
    # 2. Append a "created" event to the audit log
    # 3. Compute SHA-256 content hash
    # 4. Insert into MongoDB
    return data
```

The route handler becomes a thin adapter that handles HTTP concerns and delegates:

```python
@router.post("/")
async def create_eln_entry(entry: ELNEntry, user: User = Depends(get_current_user)):
    return eln_service.create_entry(entry, user)
```

---

## Exercise

Run the AI Scientist agent from the UI (`http://localhost:3000/agent`). It should complete successfully without timing out. In the backend logs, look for the message `Agent: Saving entry via in-process service` — this confirms the agent is calling the service function directly rather than making an HTTP request.
