"""
Collaboration WebSocket API endpoints.

Provides WebSocket endpoints for real-time collaboration features:
- User presence tracking
- Conflict notifications
- Live collaborator updates
"""

import logging
from typing import Dict, List, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

logger = logging.getLogger(__name__)

# Import local modules with fallback
try:
    from ai.collaboration_manager import (
        CollaborationManager,
        get_collaboration_manager,
    )
except ImportError:
    from src.ai.collaboration_manager import (
        CollaborationManager,
        get_collaboration_manager,
    )


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/api/v1/collaboration", tags=["Collaboration"])


# =============================================================================
# WebSocket Connection Management
# =============================================================================

class CollaborationWebSocketManager:
    """Manager for collaboration WebSocket connections."""

    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.project_subscribers: Dict[str, List[str]] = {}  # project_id -> [connection_ids]
        self.user_presence: Dict[str, Dict[str, Any]] = {}  # connection_id -> user_info

    async def connect(self, websocket: WebSocket, project_id: str, user_id: str) -> str:
        """
        Accept WebSocket connection and register user presence.

        Args:
            websocket: WebSocket connection
            project_id: Project ID to subscribe to
            user_id: User ID

        Returns:
            connection_id: Unique connection identifier
        """
        await websocket.accept()

        connection_id = f"collab_{user_id}_{project_id}_{id(websocket)}"
        self.active_connections[connection_id] = websocket

        # Subscribe to project
        if project_id not in self.project_subscribers:
            self.project_subscribers[project_id] = []
        self.project_subscribers[project_id].append(connection_id)

        # Register presence
        self.user_presence[connection_id] = {
            "user_id": user_id,
            "project_id": project_id,
            "status": "online",
            "current_task": None,
        }

        logger.info(f"User {user_id} connected to project {project_id}")

        # Notify other users
        await self.broadcast_to_project(
            project_id,
            {
                "type": "user_joined",
                "user_id": user_id,
                "username": f"User {user_id}",  # TODO: Get actual username
                "status": "online",
                "color": "#1890ff",  # TODO: Generate unique color
            },
            exclude_connection=connection_id,
        )

        # Send current collaborators to new user
        collaborators = await self.get_project_collaborators(project_id)
        await websocket.send_json({
            "type": "collaborators_update",
            "collaborators": collaborators,
        })

        return connection_id

    async def disconnect(self, connection_id: str):
        """Disconnect WebSocket and clean up presence."""
        if connection_id not in self.active_connections:
            return

        # Get user info before removing
        user_info = self.user_presence.get(connection_id, {})
        user_id = user_info.get("user_id")
        project_id = user_info.get("project_id")

        # Remove connection
        del self.active_connections[connection_id]

        # Remove from project subscribers
        if project_id and project_id in self.project_subscribers:
            self.project_subscribers[project_id].remove(connection_id)
            if not self.project_subscribers[project_id]:
                del self.project_subscribers[project_id]

        # Remove presence
        if connection_id in self.user_presence:
            del self.user_presence[connection_id]

        logger.info(f"User {user_id} disconnected from project {project_id}")

        # Notify other users
        if project_id:
            await self.broadcast_to_project(
                project_id,
                {
                    "type": "user_left",
                    "user_id": user_id,
                },
            )

    async def handle_message(self, connection_id: str, data: Dict[str, Any]):
        """
        Handle incoming WebSocket message.

        Args:
            connection_id: Connection ID
            data: Message data
        """
        message_type = data.get("type")

        if message_type == "update_status":
            await self.handle_status_update(connection_id, data)
        elif message_type == "conflict_warning":
            await self.handle_conflict_warning(connection_id, data)
        elif message_type == "conflict_resolved":
            await self.handle_conflict_resolved(connection_id, data)
        else:
            logger.warning(f"Unknown message type: {message_type}")

    async def handle_status_update(self, connection_id: str, data: Dict[str, Any]):
        """Handle user status update."""
        if connection_id not in self.user_presence:
            return

        status = data.get("status")  # editing, viewing, idle
        current_task = data.get("current_task")

        # Update presence
        self.user_presence[connection_id]["status"] = status
        if current_task is not None:
            self.user_presence[connection_id]["current_task"] = current_task

        # Broadcast to project
        user_info = self.user_presence[connection_id]
        project_id = user_info.get("project_id")

        if project_id:
            await self.broadcast_to_project(
                project_id,
                {
                    "type": "user_status_changed",
                    "user_id": user_info.get("user_id"),
                    "status": status,
                },
            )

    async def handle_conflict_warning(self, connection_id: str, data: Dict[str, Any]):
        """Handle conflict warning."""
        user_info = self.user_presence.get(connection_id, {})
        project_id = user_info.get("project_id")

        if project_id:
            await self.broadcast_to_project(
                project_id,
                {
                    "type": "conflict_warning",
                    "warning_id": data.get("warning_id"),
                    "conflict_type": data.get("type", "concurrent_edit"),
                    "message": data.get("message"),
                    "conflicting_user": user_info.get("user_id"),
                    "timestamp": data.get("timestamp"),
                },
            )

    async def handle_conflict_resolved(self, connection_id: str, data: Dict[str, Any]):
        """Handle conflict resolution."""
        user_info = self.user_presence.get(connection_id, {})
        project_id = user_info.get("project_id")

        if project_id:
            await self.broadcast_to_project(
                project_id,
                {
                    "type": "conflict_resolved",
                    "warning_id": data.get("warning_id"),
                },
            )

    async def broadcast_to_project(
        self,
        project_id: str,
        message: Dict[str, Any],
        exclude_connection: str = None,
    ):
        """Broadcast message to all subscribers of a project."""
        if project_id not in self.project_subscribers:
            return

        for conn_id in self.project_subscribers[project_id]:
            if conn_id == exclude_connection:
                continue

            if conn_id in self.active_connections:
                try:
                    await self.active_connections[conn_id].send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to {conn_id}: {e}")

    async def get_project_collaborators(self, project_id: str) -> List[Dict[str, Any]]:
        """Get list of collaborators for a project."""
        if project_id not in self.project_subscribers:
            return []

        collaborators = []
        for conn_id in self.project_subscribers[project_id]:
            user_info = self.user_presence.get(conn_id, {})
            collaborators.append({
                "user_id": user_info.get("user_id"),
                "username": f"User {user_info.get('user_id')}",  # TODO: Get actual username
                "status": user_info.get("status", "idle"),
                "current_task": user_info.get("current_task"),
                "last_activity": "2026-01-24T10:00:00Z",  # TODO: Track actual activity
                "color": "#1890ff",  # TODO: Generate unique color
            })

        return collaborators

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket statistics."""
        return {
            "total_connections": len(self.active_connections),
            "active_projects": len(self.project_subscribers),
            "online_users": len(self.user_presence),
        }


# Singleton instance
_collaboration_ws_manager: CollaborationWebSocketManager = None


def get_collab_ws_manager() -> CollaborationWebSocketManager:
    """Get collaboration WebSocket manager instance."""
    global _collaboration_ws_manager
    if _collaboration_ws_manager is None:
        _collaboration_ws_manager = CollaborationWebSocketManager()
    return _collaboration_ws_manager


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@router.websocket("/ws")
async def collaboration_websocket(
    websocket: WebSocket,
    project_id: str,
    task_id: int = None,
):
    """
    WebSocket endpoint for real-time collaboration.

    Query parameters:
    - project_id: Required project ID
    - task_id: Optional task ID for task-specific collaboration

    Supports:
    - User presence tracking (online/offline/status)
    - Real-time collaborator list
    - Conflict detection and notifications
    - Status updates (editing/viewing/idle)
    """
    ws_manager = get_collab_ws_manager()

    # TODO: Get actual user ID from authentication
    user_id = "user_123"

    connection_id = await ws_manager.connect(websocket, project_id, user_id)

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()

            # Handle message
            await ws_manager.handle_message(connection_id, data)

    except WebSocketDisconnect:
        await ws_manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws_manager.disconnect(connection_id)


@router.get("/ws/stats")
async def get_collaboration_ws_stats():
    """Get collaboration WebSocket statistics."""
    ws_manager = get_collab_ws_manager()
    return ws_manager.get_stats()
