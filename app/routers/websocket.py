"""WebSocket Router for real-time layer-by-layer scan progress streaming."""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket_manager import ws_manager

logger = logging.getLogger("phishguard.websocket_router")
router = APIRouter(tags=["Real-time"])


@router.websocket("/ws/scan/{scan_id}")
async def websocket_scan_progress(websocket: WebSocket, scan_id: str):
    """
    Live streaming WebSocket endpoint.
    Emits real-time progress events as the 5 pipeline layers execute:
    - Layer 0: Ingestion & URL unshortening
    - Layer 1: Deterministic rules (typosquatting, TLDs, subdomains)
    - Layer 2: Behavioral NLP intent triggers & token spans
    - Layer 3: Scorer aggregation & severity calculation
    - Layer 4: LLM explanation synthesis & SOAR artifact generation
    """
    await ws_manager.connect(scan_id, websocket)
    try:
        while True:
            # Keep socket alive and respond to client heartbeats / ping
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(scan_id, websocket)
    except Exception as exc:
        logger.debug(f"WebSocket closed with exception: {exc}")
        await ws_manager.disconnect(scan_id, websocket)
