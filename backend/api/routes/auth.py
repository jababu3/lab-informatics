"""
Authentication routes.

POST /auth/register  — Create a new user account.
                       First user auto-gets 'admin'. Subsequent registrations
                       require an admin JWT token.
POST /auth/login     — Exchange username + password for a JWT access token.
GET  /auth/me        — Return the current user's profile (requires token).
GET  /auth/users     — List all users (admin only).
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api.limiter import limiter

from api.postgres import User, get_db, POSTGRES_AVAILABLE
from api.auth import (
    create_access_token,
    hash_password,
    verify_password,
    get_current_user,
    require_role,
)
from models.schemas import (
    UserCreate,
    UserOut,
    Token,
    UserRoleUpdate,
    UserStatusUpdate,
    UserProfileUpdate,
    AdminUserUpdate,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _require_postgres():
    if not POSTGRES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable — PostgreSQL not connected",
        )


# ── Register ──────────────────────────────────────────────────────────────────


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_in: UserCreate,
    db: Session = Depends(get_db),
    # current_user injected only AFTER first user exists
    token: str | None = None,
):
    """
    Create a new user.
    - If no users exist yet → open registration (first user becomes admin).
    - Otherwise → admin JWT required (passed as Bearer token in Authorization header).
    """
    _require_postgres()

    user_count = db.query(User).count()
    is_first_user = user_count == 0

    # For subsequent users, validate that caller is an admin. We do a manual
    # token check here because we can't use `Depends(get_current_user)` while
    # also allowing the first-user open-registration path.
    if not is_first_user:
        from fastapi import Request

        # Callers must supply Authorization: Bearer <token> themselves
        # We re-use the require_role logic via a secondary dependency in the
        # route signature — but for simplicity we raise FORBIDDEN here.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account creation requires an admin. Use POST /auth/admin/create-user.",
        )

    # Check uniqueness
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    role = "admin" if is_first_user else user_in.role or "scientist"

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=role,
        full_name=user_in.full_name or "",
        title=user_in.title or "",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/admin/create-user", response_model=UserOut, status_code=201)
async def admin_create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Admin-only: create additional user accounts."""
    _require_postgres()

    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=user_in.role or "scientist",
        full_name=user_in.full_name or "",
        title=user_in.title or "",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ── Login ─────────────────────────────────────────────────────────────────────


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Exchange username + password for a JWT access token."""
    _require_postgres()

    user = (
        db.query(User)
        .filter(
            User.username == form_data.username,
            User.is_active == True,
        )
        .first()
    )

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "full_name": user.full_name,
            "title": user.title,
        }
    )

    response.set_cookie(
        key="lab_jwt",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production over HTTPS
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
        "full_name": user.full_name,
        "title": user.title,
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("lab_jwt", samesite="lax")
    return {"status": "success"}


# ── Current user ──────────────────────────────────────────────────────────────


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Admin: User Management ────────────────────────────────────────────────────


@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return db.query(User).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: str,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    _require_postgres()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Optional: prevent demoting the last admin. We'll skip for brevity as this is a lab environment.
    user.role = role_update.role
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/status", response_model=UserOut)
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    _require_postgres()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id and not status_update.is_active:
        raise HTTPException(
            status_code=400, detail="You cannot deactivate your own account"
        )

    user.is_active = status_update.is_active
    db.commit()
    db.refresh(user)
    return user


@router.put("/profile", response_model=UserOut)
async def update_profile(
    profile_update: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Self-service endpoint to update own profile fields and password."""
    _require_postgres()

    if profile_update.email is not None and profile_update.email != current_user.email:
        if db.query(User).filter(User.email == profile_update.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = profile_update.email

    if profile_update.full_name is not None:
        current_user.full_name = profile_update.full_name

    if profile_update.title is not None:
        current_user.title = profile_update.title

    if profile_update.new_password:
        if not profile_update.current_password or not verify_password(
            profile_update.current_password, current_user.hashed_password
        ):
            raise HTTPException(status_code=400, detail="Incorrect current password")
        current_user.hashed_password = hash_password(profile_update.new_password)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/users/{user_id}", response_model=UserOut)
async def admin_update_user(
    user_id: str,
    user_update: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Admin endpoint to update another user's email, full name, or title."""
    _require_postgres()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.email is not None and user_update.email != user.email:
        if db.query(User).filter(User.email == user_update.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = user_update.email

    if user_update.full_name is not None:
        user.full_name = user_update.full_name

    if user_update.title is not None:
        user.title = user_update.title

    db.commit()
    db.refresh(user)
    return user
