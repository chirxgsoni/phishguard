"""WebSocket Connection and Event Broadcasting Manager."""

import asyncio
import logging
from typing import Any, Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger("phishguard.websocket")


class WebSocketManager:
    """Manages active WebSockets and broadcasts live scan progress events."""

    def __init__(self):
        # Map scan_id -> Set of active WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Event replay buffer per scan_id so late-joining clients catch up
        self._event_history: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, scan_id: str, websocket: WebSocket):
        """Accept connection and replay any historical progress events."""
        await websocket.accept()
        async with self._lock:
            if scan_id not in self._connections:
                self._connections[scan_id] = set()
            self._connections[scan_id].add(websocket)

            # Replay any prior events for this scan
            history = self._event_history.get(scan_id, [])
            for event in history:
                try:
                    await websocket.send_json(event)
                except Exception as exc:
                    logger.debug(f"Failed to replay event to websocket: {exc}")

    async def disconnect(self, scan_id: str, websocket: WebSocket):
        """Remove disconnected websocket."""
        async with self._lock:
            if scan_id in self._connections:
                self._connections[scan_id].discard(websocket)
                if not self._connections[scan_id]:
                    del self._connections[scan_id]

    async def broadcast_step(self, scan_id: str, event_data: Dict[str, Any]):
        """Append to history and broadcast event to all connected clients for this scan."""
        async with self._lock:
            if scan_id not in self._event_history:
                self._event_history[scan_id] = []
            self._event_history[scan_id].append(event_data)

            websockets = list(self._connections.get(scan_id, []))

        # Send outside lock to prevent blocking
        dead_sockets = []
        for ws in websockets:
            try:
                await ws.send_json(event_data)
            except Exception as exc:
                logger.debug(f"Error broadcasting to socket for {scan_id}: {exc}")
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for ws in dead_sockets:
                    if scan_id in self._connections:
                        self._connections[scan_id].discard(ws)

    def clear_scan(self, scan_id: str):
        """Cleanup historical cache for completed scans to manage memory."""
        self._event_history.pop(scan_id, None)


ws_manager = WebSocketManager()
