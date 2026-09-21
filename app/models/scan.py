"""Pydantic models for Scan submission, analysis results, and evidence items."""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    EMAIL = "email"
    URL = "url"
    QR = "qr"
    SCREENSHOT = "screenshot"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ScanStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EvidenceItem(BaseModel):
    """Discrete, rule-based evidence extracted by Layer 1 or Layer 2."""

    id: Optional[str] = None
    scan_id: Optional[str] = None
    layer: int = Field(..., description="1 = deterministic rules, 2 = behavioral NLP")
    type: str = Field(..., description="Evidence category, e.g. typosquatting, urgency")
    severity: Severity = Field(..., description="LOW, MEDIUM, or HIGH")
    human_label: str = Field(..., description="Human-readable explanation of the finding")
    raw_match: str = Field(..., description="The matched domain, token, or expression")
    span_start: Optional[int] = Field(None, description="Start offset in original text")
    span_end: Optional[int] = Field(None, description="End offset in original text")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class ScanCreateRequest(BaseModel):
    """Payload for submitting a scan via JSON."""

    source_type: SourceType = Field(..., description="Type of input: email, url, qr, screenshot")
    content: Optional[str] = Field(None, description="Raw text, URL, or base64 encoded image")
    agent_profile_id: Optional[str] = Field(None, description="Optional custom agent profile ID")


class ScanResponse(BaseModel):
    """Full scan result returned to frontend."""

    scan_id: str
    user_id: str
    source_type: SourceType
    risk_score: int = Field(..., ge=0, le=100)
    severity: Severity
    status: ScanStatus
    evidence: List[EvidenceItem] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    explanation: Optional[str] = None
    created_at: Optional[str] = None
    raw_input_ref: Optional[str] = None


class ScanListItem(BaseModel):
    """Summary item for past scan listings."""

    id: str
    source_type: SourceType
    risk_score: int
    severity: Severity
    status: ScanStatus
    raw_input_ref: Optional[str] = None
    created_at: str


class ScanListResponse(BaseModel):
    """Paginated scan history response."""

    items: List[ScanListItem]
    total: int
    page: int = 1
    page_size: int = 20
