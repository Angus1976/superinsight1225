"""
Ontology Expert Collaboration WebSocket API (本体专家协作 WebSocket API)

WebSocket handlers for real-time collaboration features including:
- Real-time presence indicators
- Element locking/unlocking
- Change broadcasting
- Conflict detection

Uses Redis pub/sub for multi-instance support.
All async code uses asyncio.Lock (NOT threading.Lock) to prevent deadlocks.

Requirements: Task 16 - Implement WebSocket handlers for real-time collaboration
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from pydantic import BaseModel, Field

# Import collaboration service
from src.collaboration.collaboration_service import (
    CollaborationService,
    ConflictResolution,
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/ontology-collaboration",
    tags=["ontology-collaboration-websocket"]
)


# =============================================================================
# Enums and Constants
# =============================================================================

class MessageType(str, Enum):
    """WebSocket message types."""
    # Connection messages
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    
    # Presence messages
    PRESENCE_UPDATE = "presence_update"
    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"
    
    # Lock messages
    LOCK_ELEMENT = "lock_element"
    UNLOCK_ELEMENT = "unlock_element"
    LOCK_ACQUIRED = "lock_acquired"
    LOCK_RELEASED = "lock_released"
    LOCK_DENIED = "lock_denied"
    
    # Edit messages
    EDIT_ELEMENT = "edit_element"
    ELEMENT_UPDATED = "element_updated"
    
    # Conflict messages
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    
    # Error messages
    ERROR = "error"


# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = 30

# Lock timeout in seconds
LOCK_TIMEOUT = 300  # 5 minutes


# =============================================================================
# Data Models
# =============================================================================

class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: MessageType
    session_id: Optional[str] = None
    expert_id: Optional[str] = None
    element_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_id: str = Field(default_factory=lambda: str(uuid4()))


class ConnectionInfo(BaseModel):
    """Information about a WebSocket connection."""
    connection_id: str
    session_id: str
    expert_id: str
    connected_at: datetime
    last_heartbeat: datetime


# =============================================================================
# Connection Manager
# =============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections for collaboration sessions.
    
    Uses asyncio.Lock for thread-safe operations in async context.
    Supports Redis pub/sub for multi-instance broadcasting.
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        # Active connections: {session_id: {expert_id: WebSocket}}
        self._connections: Dict[str, Dict[str, WebSocket]] = {}
        
        # Connection info: {connection_id: ConnectionInfo}
        self._connection_info: Dict[str, ConnectionInfo] = {}
        
        # Async lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Redis client for pub/sub (optional)
        self._redis_client = None
        self._pubsub_task: Optional[asyncio.Task] = None
        
        # Collaboration service
        self._collaboration_service = CollaborationService()
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        expert_id: str
    ) -> str:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            session_id: The collaboration session ID
            expert_id: The expert's ID
            
        Returns:
            The connection ID
        """
        await websocket.accept()
        
        connection_id = str(uuid4())
        now = datetime.utcnow()
        
        async with self._lock:
            # Initialize session dict if needed
            if session_id not in self._connections:
                self._connections[session_id] = {}
            
            # Store connection
            self._connections[session_id][expert_id] = websocket
            
            # Store connection info
            self._connection_info[connection_id] = ConnectionInfo(
                connection_id=connection_id,
                session_id=session_id,
                expert_id=expert_id,
                connected_at=now,
                last_heartbeat=now,
            )
        
        # Join the collaboration session
        await self._collaboration_service.join_session(session_id, expert_id)
        
        # Broadcast participant joined
        await self.broadcast_to_session(
            session_id,
            WebSocketMessage(
                type=MessageType.PARTICIPANT_JOINED,
                session_id=session_id,
                expert_id=expert_id,
                data={"joined_at": now.isoformat()},
            ),
            exclude_expert=expert_id,
        )
        
        logger.info(f"Expert {expert_id} connected to session {session_id}")
        
        return connection_id
    
    async def disconnect(
        self,
        session_id: str,
        expert_id: str
    ):
        """
        Handle WebSocket disconnection.
        
        Args:
            session_id: The collaboration session ID
            expert_id: The expert's ID
        """
        async with self._lock:
            # Remove connection
            if session_id in self._connections:
                if expert_id in self._connections[session_id]:
                    del self._connections[session_id][expert_id]
                
                # Clean up empty session
                if not self._connections[session_id]:
                    del self._connections[session_id]
            
            # Remove connection info
            to_remove = [
                cid for cid, info in self._connection_info.items()
                if info.session_id == session_id and info.expert_id == expert_id
            ]
            for cid in to_remove:
                del self._connection_info[cid]
        
        # Leave the collaboration session (releases locks)
        await self._collaboration_service.leave_session(session_id, expert_id)
        
        # Broadcast participant left
        await self.broadcast_to_session(
            session_id,
            WebSocketMessage(
                type=MessageType.PARTICIPANT_LEFT,
                session_id=session_id,
                expert_id=expert_id,
                data={"left_at": datetime.utcnow().isoformat()},
            ),
        )
        
        logger.info(f"Expert {expert_id} disconnected from session {session_id}")
    
    async def broadcast_to_session(
        self,
        session_id: str,
        message: WebSocketMessage,
        exclude_expert: Optional[str] = None
    ):
        """
        Broadcast a message to all participants in a session.
        
        Args:
            session_id: The collaboration session ID
            message: The message to broadcast
            exclude_expert: Optional expert ID to exclude from broadcast
        """
        async with self._lock:
            connections = self._connections.get(session_id, {})
        
        message_json = message.model_dump_json()
        
        # Send to all connections in the session
        for expert_id, websocket in connections.items():
            if exclude_expert and expert_id == exclude_expert:
                continue
            
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to send message to {expert_id}: {e}")
        
        # Also publish to Redis for multi-instance support
        if self._redis_client:
            try:
                await self._redis_client.publish(
                    f"ontology:session:{session_id}",
                    message_json
                )
            except Exception as e:
                logger.error(f"Failed to publish to Redis: {e}")
    
    async def send_to_expert(
        self,
        session_id: str,
        expert_id: str,
        message: WebSocketMessage
    ):
        """
        Send a message to a specific expert.
        
        Args:
            session_id: The collaboration session ID
            expert_id: The expert's ID
            message: The message to send
        """
        async with self._lock:
            websocket = self._connections.get(session_id, {}).get(expert_id)
        
        if websocket:
            try:
                await websocket.send_text(message.model_dump_json())
            except Exception as e:
                logger.error(f"Failed to send message to {expert_id}: {e}")
    
    async def get_session_participants(self, session_id: str) -> List[str]:
        """
        Get list of participants in a session.
        
        Args:
            session_id: The collaboration session ID
            
        Returns:
            List of expert IDs
        """
        async with self._lock:
            return list(self._connections.get(session_id, {}).keys())
    
    async def update_heartbeat(self, connection_id: str):
        """
        Update the last heartbeat time for a connection.
        
        Args:
            connection_id: The connection ID
        """
        async with self._lock:
            if connection_id in self._connection_info:
                self._connection_info[connection_id].last_heartbeat = datetime.utcnow()
    
    async def handle_lock_element(
        self,
        session_id: str,
        expert_id: str,
        element_id: str
    ) -> bool:
        """
        Handle element lock request.
        
        Args:
            session_id: The collaboration session ID
            expert_id: The expert's ID
            element_id: The element to lock
            
        Returns:
            True if lock acquired, False otherwise
        """
        lock = await self._collaboration_service.lock_element(
            session_id=session_id,
            element_id=element_id,
            expert_id=expert_id,
        )
        
        if lock:
            # Broadcast lock acquired
            await self.broadcast_to_session(
                session_id,
                WebSocketMessage(
                    type=MessageType.LOCK_ACQUIRED,
                    session_id=session_id,
                    expert_id=expert_id,
                    element_id=element_id,
                    data={
                        "locked_at": lock.locked_at.isoformat() if lock.locked_at else None,
                        "expires_at": lock.expires_at.isoformat() if lock.expires_at else None,
                    },
                ),
            )
            return True
        else:
            # Send lock denied to requester
            await self.send_to_expert(
                session_id,
                expert_id,
                WebSocketMessage(
                    type=MessageType.LOCK_DENIED,
                    session_id=session_id,
                    expert_id=expert_id,
                    element_id=element_id,
                    data={"reason": "Element is already locked by another user"},
                ),
            )
            return False
    
    async def handle_unlock_element(
        self,
        session_id: str,
        expert_id: str,
        element_id: str
    ) -> bool:
        """
        Handle element unlock request.
        
        Args:
            session_id: The collaboration session ID
            expert_id: The expert's ID
            element_id: The element to unlock
            
        Returns:
            True if unlocked, False otherwise
        """
        result = await self._collaboration_service.unlock_element(
            session_id=session_id,
            element_id=element_id,
            expert_id=expert_id,
        )
        
        if result:
            # Broadcast lock released
            await self.broadcast_to_session(
                session_id,
                WebSocketMessage(
                    type=MessageType.LOCK_RELEASED,
                    session_id=session_id,
                    expert_id=expert_id,
                    element_id=element_id,
                ),
            )
        
        return result
    
    async def handle_edit_element(
        self,
        session_id: str,
        expert_id: str,
        element_id: str,
        changes: Dict[str, Any]
    ):
        """
        Handle element edit and broadcast to session.
        
        Args:
            session_id: The collaboration session ID
            expert_id: The expert's ID
            element_id: The element being edited
            changes: The changes made
        """
        # Record the change
        await self._collaboration_service.record_change(
            session_id=session_id,
            element_id=element_id,
            expert_id=expert_id,
            changes=changes,
        )
        
        # Broadcast the update (within 2 seconds requirement)
        await self.broadcast_to_session(
            session_id,
            WebSocketMessage(
                type=MessageType.ELEMENT_UPDATED,
                session_id=session_id,
                expert_id=expert_id,
                element_id=element_id,
                data={"changes": changes},
            ),
            exclude_expert=expert_id,
        )
    
    def set_redis_client(self, redis_client):
        """
        Set the Redis client for pub/sub support.
        
        Args:
            redis_client: The Redis client instance
        """
        self._redis_client = redis_client
    
    async def start_redis_subscriber(self):
        """Start the Redis pub/sub subscriber for multi-instance support."""
        if not self._redis_client:
            return
        
        async def subscriber():
            pubsub = self._redis_client.pubsub()
            await pubsub.psubscribe("ontology:session:*")
            
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        # Extract session_id from channel
                        channel = message["channel"].decode()
                        session_id = channel.split(":")[-1]
                        
                        # Parse and broadcast message
                        data = json.loads(message["data"])
                        ws_message = WebSocketMessage(**data)
                        
                        # Broadcast to local connections
                        await self.broadcast_to_session(
                            session_id,
                            ws_message,
                        )
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
        
        self._pubsub_task = asyncio.create_task(subscriber())
    
    async def stop_redis_subscriber(self):
        """Stop the Redis pub/sub subscriber."""
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass


# Global connection manager instance
connection_manager = ConnectionManager()


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@router.websocket("/collaboration/sessions/{session_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    expert_id: str = Query(..., description="专家ID"),
    token: Optional[str] = Query(None, description="认证令牌")
):
    """
    WebSocket endpoint for real-time collaboration.
    
    Handles:
    - Connection/disconnection
    - Heartbeat for presence detection
    - Element locking/unlocking
    - Change broadcasting
    - Conflict detection
    
    Requirements: 7.1, 7.2, 7.4
    """
    # TODO: Validate token for authentication
    # For now, accept all connections
    
    connection_id = await connection_manager.connect(
        websocket,
        session_id,
        expert_id
    )
    
    try:
        # Send initial presence update
        participants = await connection_manager.get_session_participants(session_id)
        await websocket.send_text(
            WebSocketMessage(
                type=MessageType.PRESENCE_UPDATE,
                session_id=session_id,
                data={"participants": participants},
            ).model_dump_json()
        )
        
        # Message handling loop
        while True:
            try:
                # Receive message with timeout for heartbeat
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=HEARTBEAT_INTERVAL * 2
                )
                
                # Parse message
                try:
                    message_data = json.loads(data)
                    message = WebSocketMessage(**message_data)
                except Exception as e:
                    logger.error(f"Invalid message format: {e}")
                    await websocket.send_text(
                        WebSocketMessage(
                            type=MessageType.ERROR,
                            data={"error": "Invalid message format"},
                        ).model_dump_json()
                    )
                    continue
                
                # Handle message based on type
                await handle_message(
                    websocket,
                    session_id,
                    expert_id,
                    message
                )
                
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text(
                    WebSocketMessage(
                        type=MessageType.HEARTBEAT,
                    ).model_dump_json()
                )
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {expert_id} from {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await connection_manager.disconnect(session_id, expert_id)


async def handle_message(
    websocket: WebSocket,
    session_id: str,
    expert_id: str,
    message: WebSocketMessage
):
    """
    Handle incoming WebSocket message.
    
    Args:
        websocket: The WebSocket connection
        session_id: The collaboration session ID
        expert_id: The expert's ID
        message: The received message
    """
    try:
        if message.type == MessageType.HEARTBEAT:
            # Respond to heartbeat
            await websocket.send_text(
                WebSocketMessage(
                    type=MessageType.HEARTBEAT_ACK,
                ).model_dump_json()
            )
        
        elif message.type == MessageType.HEARTBEAT_ACK:
            # Update heartbeat timestamp
            pass
        
        elif message.type == MessageType.LOCK_ELEMENT:
            # Handle lock request
            element_id = message.element_id
            if element_id:
                await connection_manager.handle_lock_element(
                    session_id,
                    expert_id,
                    element_id
                )
        
        elif message.type == MessageType.UNLOCK_ELEMENT:
            # Handle unlock request
            element_id = message.element_id
            if element_id:
                await connection_manager.handle_unlock_element(
                    session_id,
                    expert_id,
                    element_id
                )
        
        elif message.type == MessageType.EDIT_ELEMENT:
            # Handle edit
            element_id = message.element_id
            changes = message.data.get("changes", {}) if message.data else {}
            if element_id:
                await connection_manager.handle_edit_element(
                    session_id,
                    expert_id,
                    element_id,
                    changes
                )
        
        else:
            logger.warning(f"Unknown message type: {message.type}")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await websocket.send_text(
            WebSocketMessage(
                type=MessageType.ERROR,
                data={"error": str(e)},
            ).model_dump_json()
        )


# =============================================================================
# REST Endpoints for WebSocket Management
# =============================================================================

@router.get("/collaboration/sessions/{session_id}/participants")
async def get_session_participants(session_id: str):
    """
    Get list of participants in a collaboration session.
    
    Requirements: 7.1
    """
    participants = await connection_manager.get_session_participants(session_id)
    return {
        "session_id": session_id,
        "participants": participants,
        "count": len(participants),
    }


@router.get("/collaboration/sessions/{session_id}/presence")
async def get_session_presence(session_id: str):
    """
    Get presence information for a collaboration session.
    
    Requirements: 7.1
    """
    participants = await connection_manager.get_session_participants(session_id)
    
    # Get collaboration service for lock info
    service = connection_manager._collaboration_service
    session = await service.get_session(session_id)
    
    return {
        "session_id": session_id,
        "participants": participants,
        "active_locks": session.active_locks if session else {},
        "last_activity": session.last_activity.isoformat() if session and session.last_activity else None,
    }
