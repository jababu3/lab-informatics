"""
Agent API routes.

POST /agent/run     — Trigger the AI scientist to run a simulation and write an ELN entry.
GET  /agent/status  — Return status of the last agent run.
GET  /agent/health  — Check simulator and Ollama availability.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from api.auth import get_current_user_optional
from api.postgres import User, get_db

from agents.scientist_agent import LabScientistAgent, ExperimentType

router = APIRouter(prefix="/agent", tags=["agent"])

# Singleton agent instance (initializes once, check availability on startup)
_agent = LabScientistAgent()


class AgentRunRequest(BaseModel):
    experiment_type: ExperimentType = "dose_response"
    author_name: str = "agent_scientist"
    author_title: str = "AI Research Scientist"
    token: Optional[str] = (
        None  # JWT token to post ELN entry; if None, entry is returned but not posted
    )


class AgentRunResponse(BaseModel):
    status: str
    experiment_type: str
    simulator_available: bool
    ollama_available: bool
    posted: bool = False
    entry_id: Optional[str] = None
    analysis: Optional[dict] = None
    error: Optional[str] = None


# ── Run ───────────────────────────────────────────────────────────────────────


@router.post("/run")
async def run_agent(
    request: Request,
    req: AgentRunRequest,
    token_payload: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Trigger the AI scientist agent synchronously.
    Returns the full run result including generated ELN content.

    Pass a valid JWT `token` (from /auth/login) to auto-post the entry to the ELN.
    Without a token, the assembled entry is returned but not persisted.
    """

    # Determine author based on logged-in user unless explicitly set to AI Scientist
    author_name = req.author_name
    author_title = req.author_title
    if token_payload is not None:
        # token_payload contains "sub" as username
        username = token_payload.get("sub")
        if author_name == "agent_scientist":
            author_name = username
        # Fetch user title from DB if needed
        user_obj = db.query(User).filter(User.username == username).first()
        if user_obj and author_title == "AI Research Scientist":
            author_title = user_obj.title or author_title

    # Extract token from cookie, fallback to request body
    cookie_token = request.cookies.get("lab_jwt") or req.token or ""

    result = _agent.run(
        experiment_type=req.experiment_type,
        author_name=author_name,
        author_title=author_title,
        token=cookie_token,
    )
    return result


# ── Status ────────────────────────────────────────────────────────────────────


@router.get("/status")
async def agent_status():
    """Return the result of the last agent run (or None if never run)."""
    if _agent.last_run is None:
        return {
            "status": "never_run",
            "message": "Agent has not been run yet in this session.",
        }
    return _agent.last_run


# ── Health ────────────────────────────────────────────────────────────────────


@router.get("/health")
async def agent_health():
    """Check whether the simulator and Ollama are reachable."""
    import os

    return {
        "simulator_available": _agent._simulator_available,
        "ollama_available": _agent._ollama_available,
        "ollama_host": os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "mistral:7b"),
        "eln_api_url": os.getenv("ELN_API_URL", "http://localhost:8000"),
    }
