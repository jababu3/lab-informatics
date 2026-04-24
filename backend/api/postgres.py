"""
PostgreSQL connection + Users table via SQLAlchemy.

The `users` table is the authoritative identity store for JWT authentication.
Passwords are never stored in plain-text — only bcrypt hashes.
"""

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, String, Boolean, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker

POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql://labuser:labuser@localhost:5433/lab_db",
)

POSTGRES_AVAILABLE = False
engine = None
SessionLocal = None
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="scientist")  # admin | scientist | reviewer
    full_name = Column(String, default="")
    title = Column(String, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


try:
    engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
    # Quick connectivity check
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    # Create all tables (users) if they don't exist
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    POSTGRES_AVAILABLE = True
    print("✅ PostgreSQL connected — users table ready")
except Exception as exc:
    POSTGRES_AVAILABLE = False
    print(f"⚠️  PostgreSQL: {exc}")


def get_db():
    """FastAPI dependency that yields a DB session."""
    if not POSTGRES_AVAILABLE or SessionLocal is None:
        raise RuntimeError("PostgreSQL is not available")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
