"""Reports API Router for accessing SOAR incident containment artifacts."""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.supabase import db_service
from app.dependencies import get_current_user
from app.models.report import SOARReportsResponse

router = APIRouter(prefix="/api/reports", tags=["Reports & SOAR"])


@router.get("/{scan_id}", response_model=SOARReportsResponse)
async def get_scan_reports(
    scan_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Retrieve auto-generated SOAR artifacts for high-risk threats:
    - CERT-In / APWG / CISA formal incident report text
    - DNS sinkhole host file rule (0.0.0.0 <domain>)
    - Suricata / Snort network IDS inspection rule skeleton
    """
    scan = await db_service.get_scan(scan_id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"Scan '{scan_id}' not found"}},
        )

    reports = await db_service.get_scan_reports(scan_id)

    cert_report = None
    dns_sinkhole = None
    suricata_rule = None

    for r in reports:
        rtype = r.get("report_type")
        if rtype == "cert":
            cert_report = r.get("content")
        elif rtype == "dns_sinkhole":
            dns_sinkhole = r.get("content")
        elif rtype == "suricata":
            suricata_rule = r.get("content")

    return SOARReportsResponse(
        scan_id=scan_id,
        cert_report=cert_report,
        dns_sinkhole=dns_sinkhole,
        suricata_rule=suricata_rule,
    )
