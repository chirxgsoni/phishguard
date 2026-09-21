"""Authentication and session validation endpoint."""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/session")
async def validate_session(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Validate the Supabase JWT provided in the Authorization Bearer header
    and return the user profile metadata.
    """
    return {
        "authenticated": True,
        "user": {
            "id": current_user["id"],
            "email": current_user.get("email"),
            "role": current_user.get("role", "authenticated"),
            "user_metadata": current_user.get("user_metadata", {}),
            "app_metadata": current_user.get("app_metadata", {}),
        },
    }
