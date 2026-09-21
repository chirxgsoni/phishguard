"""Agent Profiles Router for managing and training custom LLM prompt profiles."""

import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.supabase import db_service
from app.dependencies import get_current_user
from app.models.agent_profile import AgentProfileCreateRequest, AgentProfileResponse

router = APIRouter(prefix="/api/agent-profiles", tags=["Agent Profiles"])


@router.get("", response_model=List[AgentProfileResponse])
async def list_agent_profiles(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List all available agent profiles (global defaults + user's customized profiles).
    This enables users to train and iterate on the Layer 4 explainability instructions.
    """
    profiles = await db_service.get_agent_profiles(current_user["id"])
    return [
        AgentProfileResponse(
            id=p["id"],
            user_id=p.get("user_id"),
            name=p["name"],
            system_prompt=p["system_prompt"],
            is_default=p.get("is_default", False),
            created_at=p.get("created_at", ""),
            updated_at=p.get("updated_at", ""),
        )
        for p in profiles
    ]


@router.post("", response_model=AgentProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_agent_profile(
    body: AgentProfileCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create or customize a system prompt profile for the Layer 4 LLM agent.
    Users can specify specialized SOC policies, financial compliance guidelines,
    or concise executive reporting tones.
    """
    profile_id = str(uuid.uuid4())
    record = {
        "id": profile_id,
        "user_id": current_user["id"],
        "name": body.name,
        "system_prompt": body.system_prompt,
        "is_default": body.is_default,
    }
    saved = await db_service.save_agent_profile(record)
    return AgentProfileResponse(
        id=saved["id"],
        user_id=saved["user_id"],
        name=saved["name"],
        system_prompt=saved["system_prompt"],
        is_default=saved["is_default"],
        created_at=saved.get("created_at", ""),
        updated_at=saved.get("updated_at", ""),
    )
