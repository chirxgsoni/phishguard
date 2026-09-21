"""Pydantic models for Connected Accounts (OAuth, Gmail, etc.)."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ConnectionProvider(str, Enum):
    GMAIL = "gmail"
    SLACK = "slack"
    TEAMS = "teams"


class ConnectionStartRequest(BaseModel):
    provider: ConnectionProvider = Field(..., description="Provider to connect, e.g. gmail")


class ConnectionStartResponse(BaseModel):
    provider: ConnectionProvider
    redirect_url: str
    state: str


class ConnectionResponse(BaseModel):
    id: str
    provider: str
    status: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_synced_at: Optional[str] = None
    created_at: str
