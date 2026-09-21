"""Pydantic models for Agent Profiles (Versioned System Prompts)."""

from typing import Optional
from pydantic import BaseModel, Field


class AgentProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Descriptive name of the prompt profile")
    system_prompt: str = Field(..., min_length=10, description="Custom instructions for the Layer 4 triage agent")
    is_default: bool = Field(False, description="Set this profile as default for the user")


class AgentProfileResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    system_prompt: str
    is_default: bool = False
    created_at: str
    updated_at: str
