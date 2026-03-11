"""WebSocket endpoint for real-time pipeline progress updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json

ws_router = APIRouter()

# Connected clients per execution_id
_connections: Dict[str, Set[WebSocket]] = {}


@ws_router.websocket("/ws/toolkit/progress/{execution_id}")
async def progress_websocket(websocket: WebSocket, execution_id: str):
    """WebSocket endpoint for real-time progress updates."""
    await websocket.accept()

    if execution_id not in _connections:
        _connections[execution_id] = set()
    _connections[execution_id].add(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections[execution_id].discard(websocket)
        if not _connections[execution_id]:
            del _connections[execution_id]


async def broadcast_progress(
    execution_id: str, progress: int, stage: str, status: str,
):
    """Broadcast progress update to all connected clients."""
    if execution_id not in _connections:
        return

    message = json.dumps({
        "execution_id": execution_id,
        "progress": progress,
        "stage": stage,
        "status": status,
    })

    disconnected: Set[WebSocket] = set()
    for ws in _connections[execution_id]:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)

    _connections[execution_id] -= disconnected
