import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from api.database import RDKIT_AVAILABLE, MONGO_AVAILABLE
from api.postgres import POSTGRES_AVAILABLE
from api.limiter import limiter
from api.routes import compounds, experiments, analytics, ingestion, units, eln
from api.routes import auth as auth_router
from api.routes import agent as agent_router

app = FastAPI(title="Lab Informatics API", version="1.0.0")

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(compounds.router)
app.include_router(experiments.router)
app.include_router(analytics.router)
app.include_router(ingestion.router)
app.include_router(units.router)
app.include_router(eln.router)
app.include_router(auth_router.router)
app.include_router(agent_router.router)

@app.get("/")
async def root():
    return {"message": "Lab Informatics API", "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "rdkit": RDKIT_AVAILABLE,
        "mongodb": MONGO_AVAILABLE,
        "postgres": POSTGRES_AVAILABLE,
    }
