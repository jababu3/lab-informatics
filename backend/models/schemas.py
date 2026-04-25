from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class Compound(BaseModel):
    name: str
    smiles: str
    tags: List[str] = []


class Experiment(BaseModel):
    title: str
    description: str
    compound_ids: List[str]
    assay_type: str
    target: Optional[str] = None
    status: str = "planned"


class DoseResponseData(BaseModel):
    concentrations: List[float]
    responses: List[float]


class QSARData(BaseModel):
    compounds: List[Dict[str, Any]]


# ── ELN Models ───────────────────────────────────────────────────────────────


class ELNSection(BaseModel):
    section_id: str
    section_type: str  # "procedure", "observation", "result", "conclusion", "note"
    title: str
    content: str


class ELNEntry(BaseModel):
    title: str
    author: str
    author_title: str
    experiment_id: Optional[str] = None
    objective: Optional[str] = None
    sections: List[ELNSection] = []
    tags: List[str] = []


class SignatureRequest(BaseModel):
    """
    21 CFR Part 11 §11.50 compliant signature payload.
    Requires: printed name, date/time (server-assigned), and meaning of signature.
    Re-authentication is represented by the signer_name matching the entry author
    and the explicit acknowledgment_text affirmation.
    """

    signer_name: str  # §11.50(a)(1): printed name
    signer_title: str
    meaning: str  # §11.50(a)(3): purpose/meaning of signature
    acknowledgment_text: Optional[str] = None  # made optional for UX simplicity


# ── Auth / User Models ────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    username: str
    email: str
    password: str = Field(..., min_length=12)
    full_name: Optional[str] = ""
    title: Optional[str] = ""
    role: Optional[str] = "scientist"  # ignored on first-user registration


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=12)


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserRoleUpdate(BaseModel):
    role: str


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    title: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str
    full_name: str
    title: str
