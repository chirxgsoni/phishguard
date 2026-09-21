"""
PhishGuard Backend — Main FastAPI Application Entry Point.

Layered, explainable phishing-detection engine with real-time trainable LLM triage agent.
Exposed via REST + WebSockets for the React frontend and n8n automations.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import (
    agent_profiles,
    auth,
    connections,
    health,
    reports,
    scans,
    websocket,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("phishguard.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    logger.info("Starting PhishGuard Detection Engine...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Supabase configured: {'Live Cloud' if 'your-project' not in settings.SUPABASE_URL else 'In-Memory Fallback'}")
    yield
    logger.info("Shutting down PhishGuard Backend.")


app = FastAPI(
    title="PhishGuard — Explainable & Autonomous Phishing Threat Detection API",
    description=(
        "5-Layer deterministic detection pipeline + trainable LLM triage agent. "
        "Every risk score is traceable to concrete, rule-based evidence."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ------------------------------------------------------------------------------
# CORS MIDDLEWARE
# ------------------------------------------------------------------------------
# Allow requests from the React frontend (localhost and deployed Vercel apps)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        settings.FRONTEND_URL,
        "*",  # Permissive in dev/hackathon; frontend deploys separately to Vercel
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# GLOBAL ERROR ENVELOPE HANDLERS
# Required Contract: {"error": {"code": "...", "message": "..."}}
# ------------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Format HTTP exceptions into standard error contract."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        payload = exc.detail
    else:
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            422: "VALIDATION_ERROR",
            500: "INTERNAL_SERVER_ERROR",
        }
        err_code = code_map.get(exc.status_code, "ERROR")
        payload = {
            "error": {
                "code": err_code,
                "message": str(exc.detail),
            }
        }
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format request validation errors into standard error contract."""
    errors_summary = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Invalid field")
        errors_summary.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "; ".join(errors_summary),
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during threat processing.",
            }
        },
    )


# ------------------------------------------------------------------------------
# ROUTER REGISTRATIONS
# ------------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(scans.router)
app.include_router(websocket.router)
app.include_router(reports.router)
app.include_router(connections.router)
app.include_router(agent_profiles.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
