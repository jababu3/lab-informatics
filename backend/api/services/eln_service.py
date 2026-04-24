"""
ELN (Electronic Lab Notebook) Service Layer.

This module contains the business logic for creating and managing ELN records,
independent of the HTTP layer (FastAPI).

By separating this into a service, we:
  1. Solve Deadlocks: Internal agents (like the Scientist Agent) can save 
     records directly without making a loopback HTTP call to `localhost`.
  2. Reusability: Multiple routes or CLI scripts can use the same logic.
  3. Compliance: Ensures 21 CFR Part 11 logic (hashing, audit logs) is 
     consistently applied regardless of the entry point.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from models.schemas import ELNEntry
from api.database import MONGO_AVAILABLE, db
from api.postgres import User

# ── Mongo collection initialization ──────────────────────────────────────────

eln_collection = None
if MONGO_AVAILABLE and db is not None:
    try:
        eln_collection = db["eln_entries"]
    except Exception:
        eln_collection = None


# ── Internal Helpers ─────────────────────────────────────────────────────────

def _content_hash(data: dict) -> str:
    """SHA-256 of the record content, used for integrity verification (§11.10(a))."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def _audit_event(action: str, actor: str, detail: str = "") -> dict:
    return {
        "action": action,
        "actor": actor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "detail": detail,
    }


# ── Service Methods ──────────────────────────────────────────────────────────

def create_entry(entry_data: ELNEntry, current_user: User) -> Dict[str, Any]:
    """
    Creates a new ELN entry record with full audit trail and content hashing.
    
    Args:
        entry_data: The notebook entry content (title, sections, etc.)
        current_user: The authenticated User object (PostgreSQL) creating the record.
        
    Returns:
        The fully assembled and saved entry dictionary.
    """
    data = entry_data.dict()
    data["entry_id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    data["status"] = "draft"        # draft → in_review → signed
    data["documents"] = []
    data["signature"] = None
    data["created_by"] = current_user.username  # verified identity
    
    # Audit trail: §11.10(e)
    data["audit_log"] = [
        _audit_event("created", current_user.username, f'Entry titled "{entry_data.title}" created')
    ]
    
    # Integrity hash: §11.10(a)
    # We hash the content BEFORE appending the audit log and hash itself
    data["content_hash"] = _content_hash({
        k: v for k, v in data.items() if k not in ("audit_log", "content_hash")
    })

    if MONGO_AVAILABLE and eln_collection is not None:
        result = eln_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
    else:
        # Graceful fallback for demo environments without MongoDB
        data["_id"] = data["entry_id"]

    return data


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    if not MONGO_AVAILABLE or eln_collection is None:
        return None
    
    entry = eln_collection.find_one({"entry_id": entry_id})
    if entry:
        entry["_id"] = str(entry["_id"])
    return entry
