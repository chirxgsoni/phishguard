"""Connections Router for OAuth account integrations (Gmail, Slack, etc.)."""

import secrets
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.config import settings
from app.connectors.gmail import gmail_connector
from app.core.security import security_service
from app.core.supabase import db_service
from app.dependencies import get_current_user
from app.models.connection import (
    ConnectionProvider,
    ConnectionResponse,
    ConnectionStartRequest,
    ConnectionStartResponse,
)
from app.models.scan import ScanStatus, Severity, SourceType
from app.pipeline.orchestrator import run_pipeline_orchestrator

router = APIRouter(prefix="/api/connections", tags=["Connections"])


@router.post("", response_model=ConnectionStartResponse)
async def start_connection(
    body: ConnectionStartRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Initialize OAuth flow for an external provider.
    Returns the authorization redirect URL and state token.
    """
    if body.provider == ConnectionProvider.GMAIL:
        state = f"{current_user['id']}:{secrets.token_urlsafe(16)}"
        redirect_url = gmail_connector.get_authorization_url(state)
        return ConnectionStartResponse(
            provider=body.provider,
            redirect_url=redirect_url,
            state=state,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "PROVIDER_NOT_SUPPORTED",
                    "message": f"Provider '{body.provider}' is coming soon.",
                }
            },
        )


@router.get("/callback")
async def oauth_callback(
    code: str = Query(..., description="OAuth authorization code"),
    state: Optional[str] = Query(None, description="CSRF state parameter"),
):
    """
    OAuth authorization code callback.
    Exchanges code for tokens, encrypts tokens with Fernet, and saves the connection.
    """
    try:
        user_id = "00000000-0000-0000-0000-000000000000"
        if state and ":" in state:
            user_id = state.split(":")[0]

        # Exchange code for tokens
        token_data = await gmail_connector.exchange_code_for_tokens(code)

        # Encrypt tokens before storing in database
        encrypted_str = security_service.encrypt_json(token_data)

        connection_id = str(uuid.uuid4())
        record = {
            "id": connection_id,
            "user_id": user_id,
            "provider": "gmail",
            "encrypted_tokens": encrypted_str,
            "status": "active",
            "metadata": {
                "email": token_data.get("email", "connected_account@gmail.com"),
                "scopes": ["gmail.readonly"],
            },
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        }

        await db_service.save_connection(record)

        # Redirect user back to frontend connections page
        redirect_target = f"{settings.FRONTEND_URL}/connections?connected=gmail"
        return RedirectResponse(url=redirect_target, status_code=status.HTTP_302_FOUND)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "OAUTH_FAILED", "message": str(exc)}},
        )


@router.get("", response_model=List[ConnectionResponse])
async def list_user_connections(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List all connected accounts and their status for the authenticated user."""
    connections = await db_service.list_connections(current_user["id"])
    return [
        ConnectionResponse(
            id=c["id"],
            provider=c["provider"],
            status=c.get("status", "active"),
            metadata=c.get("metadata", {}),
            last_synced_at=c.get("last_synced_at"),
            created_at=c.get("created_at", ""),
        )
        for c in connections
    ]


@router.delete("/{connection_id}")
async def revoke_connection(
    connection_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Revoke and delete a connected provider account."""
    success = await db_service.delete_connection(connection_id, current_user["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Connection not found"}},
        )
    return {"revoked": True, "connection_id": connection_id}


@router.post("/{connection_id}/sync")
async def sync_and_scan_connection(
    connection_id: str,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Pull recent messages from the connected account and run them through
    the identical 5-layer threat detection pipeline.
    """
    conn = await db_service.get_connection(connection_id, current_user["id"])
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Connection not found"}},
        )

    # Decrypt stored credentials
    tokens = {}
    if conn.get("encrypted_tokens"):
        try:
            tokens = security_service.decrypt_json(conn["encrypted_tokens"])
        except Exception:
            pass

    # Fetch recent messages
    messages = await gmail_connector.fetch_recent_messages(tokens, limit=5)
    scans_initiated = []

    for msg in messages:
        scan_id = str(uuid.uuid4())
        scan_content = msg.to_scan_content()

        scan_record = {
            "id": scan_id,
            "user_id": current_user["id"],
            "source_type": SourceType.EMAIL.value,
            "raw_input_ref": f"Inbox Sync: {msg.subject[:60]}",
            "risk_score": 0,
            "severity": Severity.LOW.value,
            "status": ScanStatus.PROCESSING.value,
            "metadata": {"message_id": msg.message_id, "connection_id": connection_id},
        }
        await db_service.create_scan(scan_record)

        background_tasks.add_task(
            run_pipeline_orchestrator,
            scan_id=scan_id,
            user_id=current_user["id"],
            source_type=SourceType.EMAIL,
            content=scan_content,
        )
        scans_initiated.append({"scan_id": scan_id, "subject": msg.subject})

    # Update last_synced_at
    await db_service.save_connection(
        {
            **conn,
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    return {
        "status": "syncing",
        "messages_pulled": len(messages),
        "scans_initiated": scans_initiated,
    }
