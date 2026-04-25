"""
JWT + bcrypt authentication utilities.

Design:
  - Passwords stored as bcrypt hashes in PostgreSQL `users` table.
  - JWT access tokens signed with HS256 (SECRET_KEY from env).
  - `get_current_user` is a FastAPI dependency — inject it to protect any route.
  - First registered user gets `admin` role automatically.

21 CFR Part 11 note:
  When `get_current_user` is used on the ELN sign endpoint, the verified
  JWT identity replaces the typed-acknowledgment re-authentication proxy.
  This provides a proper §11.200(a) compliant re-authentication check.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from api.postgres import User, get_db

# ── Config ────────────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "change-me-in-production-use-a-long-random-string"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 hours

# ── Password hashing ──────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ── Dependencies ──────────────────────────────────────────────────────────────


def get_token(
    request: Request, bearer_token: str = Depends(oauth2_scheme)
) -> Optional[str]:
    """Extract token from lab_jwt cookie or fallback to Authorization header."""
    return request.cookies.get("lab_jwt") or bearer_token


async def get_current_user(
    token: str = Depends(get_token),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency.  Validates JWT and returns the authenticated User.
    Raises 401 if token is missing, invalid, or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = (
        db.query(User)
        .filter(User.username == username, User.is_active.is_(True))
        .first()
    )
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_optional(
    token: str = Depends(get_token),
) -> Optional[dict]:
    """
    Soft dependency — returns decoded payload or None.
    Use this on routes that work for both authenticated and anonymous users.
    """
    if token is None:
        return None
    try:
        return decode_token(token)
    except JWTError:
        return None


def require_role(*roles: str):
    """
    Dependency factory for role-based access control.
    Usage: Depends(require_role('admin', 'scientist'))
    """

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not authorized. Required: {roles}",
            )
        return current_user

    return _check
