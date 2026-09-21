"""Pydantic models for SOAR artifacts and Incident Reports."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ReportType(str, Enum):
    CERT = "cert"
    DNS_SINKHOLE = "dns_sinkhole"
    SURICATA = "suricata"


class ReportRecord(BaseModel):
    id: Optional[str] = None
    scan_id: str
    report_type: ReportType
    content: str
    submitted: bool = False
    created_at: Optional[str] = None


class SOARReportsResponse(BaseModel):
    """Container for SOAR artifacts returned by GET /api/reports/{scan_id}."""

    scan_id: str
    cert_report: Optional[str] = Field(None, description="CERT-In/APWG/CISA style incident report text")
    dns_sinkhole: Optional[str] = Field(None, description="DNS sinkhole line format: 0.0.0.0 <domain>")
    suricata_rule: Optional[str] = Field(None, description="Suricata / Snort network IDS signature")
