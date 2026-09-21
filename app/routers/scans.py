"""Scans API Router for submitting and retrieving threat scans."""

import base64
import uuid
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)

from app.core.supabase import db_service
from app.dependencies import get_current_user
from app.models.scan import (
    EvidenceItem,
    ScanCreateRequest,
    ScanListItem,
    ScanListResponse,
    ScanResponse,
    ScanStatus,
    Severity,
    SourceType,
)
from app.pipeline.orchestrator import run_pipeline_orchestrator

router = APIRouter(prefix="/api/scans", tags=["Scans"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit_scan(
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Submit content for phishing threat analysis.
    Supports JSON body ({source_type, content, agent_profile_id})
    OR multipart/form-data for file uploads (QR codes, screenshots).
    """
    scan_id = str(uuid.uuid4())
    user_id = current_user["id"]
    source_type: SourceType = SourceType.EMAIL
    content: Optional[str] = None
    file_bytes: Optional[bytes] = None
    agent_profile_id: Optional[str] = None

    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            source_type = SourceType(body.get("source_type", "email"))
            content = body.get("content")
            agent_profile_id = body.get("agent_profile_id")
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": {"code": "INVALID_JSON", "message": str(exc)}},
            )
    elif "multipart/form-data" in content_type:
        form = await request.form()
        st_raw = form.get("source_type", "email")
        try:
            source_type = SourceType(st_raw)
        except ValueError:
            source_type = SourceType.EMAIL
        content = form.get("content")
        agent_profile_id = form.get("agent_profile_id")

        upload_file: Optional[UploadFile] = form.get("file")
        if upload_file:
            file_bytes = await upload_file.read()
    else:
        # Fallback to empty body or default email
        pass

    # Create initial scan record in DB
    scan_record = {
        "id": scan_id,
        "user_id": user_id,
        "source_type": source_type.value,
        "raw_input_ref": (content[:150] + "...") if content else "[File upload]",
        "risk_score": 0,
        "severity": Severity.LOW.value,
        "status": ScanStatus.PROCESSING.value,
        "agent_profile_id": agent_profile_id,
    }
    await db_service.create_scan(scan_record)

    # Launch pipeline orchestrator in background task
    background_tasks.add_task(
        run_pipeline_orchestrator,
        scan_id=scan_id,
        user_id=user_id,
        source_type=source_type,
        content=content,
        file_bytes=file_bytes,
        agent_profile_id=agent_profile_id,
    )

    return {
        "scan_id": scan_id,
        "status": ScanStatus.PROCESSING.value,
        "websocket_url": f"/ws/scan/{scan_id}",
    }


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan_details(
    scan_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Fetch full scan analysis result including evidence cards, risk score, and explanation."""
    scan = await db_service.get_scan(scan_id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"Scan '{scan_id}' not found"}},
        )

    # Fetch evidence items
    evidence_dicts = await db_service.get_scan_evidence(scan_id)
    evidence_items = [EvidenceItem(**e) for e in evidence_dicts]

    return ScanResponse(
        scan_id=scan["id"],
        user_id=scan["user_id"],
        source_type=SourceType(scan["source_type"]),
        risk_score=scan.get("risk_score", 0),
        severity=Severity(scan.get("severity", "LOW")),
        status=ScanStatus(scan.get("status", "completed")),
        evidence=evidence_items,
        recommended_action=scan.get("recommended_action"),
        explanation=scan.get("explanation"),
        created_at=scan.get("created_at"),
        raw_input_ref=scan.get("raw_input_ref"),
    )


@router.get("", response_model=ScanListResponse)
async def list_scans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Retrieve paginated scan history for the authenticated user."""
    res = await db_service.list_scans(current_user["id"], page=page, page_size=page_size)
    items = [
        ScanListItem(
            id=s["id"],
            source_type=SourceType(s["source_type"]),
            risk_score=s.get("risk_score", 0),
            severity=Severity(s.get("severity", "LOW")),
            status=ScanStatus(s.get("status", "completed")),
            raw_input_ref=s.get("raw_input_ref"),
            created_at=s.get("created_at", ""),
        )
        for s in res["items"]
    ]
    return ScanListResponse(
        items=items,
        total=res["total"],
        page=page,
        page_size=page_size,
    )
