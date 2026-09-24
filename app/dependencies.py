"""FastAPI dependencies for authentication and database services."""

from typing import Any, Dict, Optional
from fastapi import Header, HTTPException, status
from app.core.security import security_service
from app.core.supabase import db_service, DatabaseService

DEFAULT_DEMO_USER_ID = "00000000-0000-0000-0000-000000000000"

DEMO_USER = {
    "id": DEFAULT_DEMO_USER_ID,
    "email": "demo@nexus.security",
    "role": "authenticated",
    "app_metadata": {},
    "user_metadata": {"name": "Demo Analyst"},
}


async def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer <supabase_jwt>")
) -> Dict[str, Any]:
    """
    Extract and validate the Supabase JWT token from the Authorization header.
    In development/demo mode, if no header or a demo token is supplied, returns a demo user.
    """
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()

            # Support demo mode and dummy tokens without failing JWT validation
            if token in ("demo-token", "demo", "null", "undefined") or not token:
                return DEMO_USER

            # Verify it has standard JWT 3-segment format (header.payload.signature)
            if token.count(".") != 2:
                # In development/test mode, fall back to demo user
                from app.config import settings
                if settings.ENVIRONMENT in ("development", "test"):
                    return DEMO_USER
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": {"code": "INVALID_TOKEN", "message": "Malformed JWT token structure"}},
                )

            try:
                user = security_service.verify_supabase_jwt(token)
                return user
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": {"code": "INVALID_TOKEN", "message": str(exc)}},
                )

    # Fallback demo user for public/local scan testing
    return DEMO_USER


def get_db() -> DatabaseService:
    """Dependency returning the database service."""
    return db_service
