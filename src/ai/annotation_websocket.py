"""
AI Annotation WebSocket Handler.

Provides real-time WebSocket communication for AI annotation collaboration,
including live suggestions, conflict resolution, and progress updates.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Message Types
# =============================================================================

class AnnotationMessageType(str, Enum):
    """Annotation WebSocket message types."""
    # Client to server
    AUTH = "auth"
    SUBSCRIBE_PROJECT = "subscribe_project"
    UNSUBSCRIBE_PROJECT = "unsubscribe_project"
    REQUEST_SUGGESTION = "request_suggestion"
    SUBMIT_ANNOTATION = "submit_annotation"
    SUBMIT_FEEDBACK = "submit_feedback"
    START_TASK = "start_task"
    COMPLETE_TASK = "complete_task"
    RESOLVE_CONFLICT = "resolve_conflict"
    REQUEST_PROGRESS = "request_progress"
    PING = "ping"

    # Server to client
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    SUGGESTION = "suggestion"
    SUGGESTION_BATCH = "suggestion_batch"
    ANNOTATION_UPDATE = "annotation_update"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    PROGRESS_UPDATE = "progress_update"
    QUALITY_ALERT = "quality_alert"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    ERROR = "error"
    PONG = "pong"


class ConflictType(str, Enum):
    """Types of annotation conflicts."""
    LABEL_MISMATCH = "label_mismatch"
    BOUNDARY_OVERLAP = "boundary_overlap"
    MISSING_ANNOTATION = "missing_annotation"
    DUPLICATE_ANNOTATION = "duplicate_annotation"


# =============================================================================
# Message Models
# =============================================================================

class AnnotationMessage(BaseModel):
    """WebSocket message for annotation collaboration."""
    type: AnnotationMessageType
    payload: Dict[str, Any] = Field(default_factory=dict)
    message_id: str = Field(default_factory=lambda: f"ann_{uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None

    class Config:
        use_enum_values = True


class SuggestionPayload(BaseModel):
    """Payload for annotation suggestions."""
    document_id: str
    text: str
    context: Optional[str] = None
    annotation_type: str = "ner"
    position: Optional[Dict[str, int]] = None  # start, end positions


class AnnotationPayload(BaseModel):
    """Payload for annotation submission."""
    document_id: str
    task_id: str
    annotation_data: Dict[str, Any]
    confidence: Optional[float] = None


class FeedbackPayload(BaseModel):
    """Payload for suggestion feedback."""
    suggestion_id: str
    accepted: bool
    modified_annotation: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class ConflictResolutionPayload(BaseModel):
    """Payload for conflict resolution."""
    conflict_id: str
    resolution: str  # accepted, rejected, modified
    resolved_annotation: Optional[Dict[str, Any]] = None
    resolution_notes: Optional[str] = None


# =============================================================================
# Connection Info
# =============================================================================

@dataclass
class AnnotationConnectionInfo:
    """WebSocket connection information for annotation."""
    connection_id: str
    websocket: WebSocket
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    role: Optional[str] = None
    subscribed_projects: Set[str] = field(default_factory=set)
    subscribed_documents: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_authenticated: bool = False

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()


# =============================================================================
# Annotation WebSocket Manager
# =============================================================================

class AnnotationWebSocketManager:
    """
    Manages WebSocket connections for AI annotation collaboration.

    Features:
    - Real-time suggestion delivery (<100ms latency target)
    - Live annotation updates
    - Conflict detection and resolution
    - Progress tracking and updates
    - User presence awareness
    """

    def __init__(
        self,
        suggestion_handler: Optional[Callable] = None,
        feedback_handler: Optional[Callable] = None,
        conflict_resolver: Optional[Callable] = None,
        max_connections_per_project: int = 50,
        suggestion_timeout: float = 5.0,
    ):
        """
        Initialize annotation WebSocket manager.

        Args:
            suggestion_handler: Handler for generating suggestions
            feedback_handler: Handler for processing feedback
            conflict_resolver: Handler for resolving conflicts
            max_connections_per_project: Max connections per project
            suggestion_timeout: Timeout for suggestion generation
        """
        self._connections: Dict[str, AnnotationConnectionInfo] = {}
        self._project_connections: Dict[str, Set[str]] = {}
        self._document_connections: Dict[str, Set[str]] = {}
        self._user_connections: Dict[str, str] = {}  # user_id -> connection_id

        self._suggestion_handler = suggestion_handler
        self._feedback_handler = feedback_handler
        self._conflict_resolver = conflict_resolver

        self._max_connections_per_project = max_connections_per_project
        self._suggestion_timeout = suggestion_timeout

        self._lock = asyncio.Lock()
        self._running = False

        # Metrics
        self._suggestion_count = 0
        self._feedback_count = 0
        self._conflict_count = 0
        self._avg_suggestion_latency_ms = 0.0

    async def start(self) -> None:
        """Start the WebSocket manager."""
        self._running = True
        logger.info("Annotation WebSocket manager started")

    async def stop(self) -> None:
        """Stop the WebSocket manager and close all connections."""
        self._running = False

        for conn_id in list(self._connections.keys()):
            await self.disconnect(conn_id, reason="Server shutdown")

        logger.info("Annotation WebSocket manager stopped")

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: Optional[str] = None,
    ) -> AnnotationConnectionInfo:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            connection_id: Optional custom connection ID

        Returns:
            Connection info for the new connection
        """
        await websocket.accept()

        conn_id = connection_id or f"ann_{uuid4().hex[:12]}"

        connection = AnnotationConnectionInfo(
            connection_id=conn_id,
            websocket=websocket,
        )

        async with self._lock:
            self._connections[conn_id] = connection

        logger.info(f"Annotation WebSocket connected: {conn_id}")

        # Send welcome message
        await self._send_message(connection, AnnotationMessage(
            type=AnnotationMessageType.AUTH_SUCCESS,  # Temporarily use this
            payload={
                "status": "connected",
                "connection_id": conn_id,
                "message": "Please authenticate to continue"
            }
        ))

        return connection

    async def disconnect(
        self,
        connection_id: str,
        reason: str = "Normal closure",
    ) -> None:
        """
        Disconnect and cleanup a WebSocket connection.

        Args:
            connection_id: ID of connection to disconnect
            reason: Reason for disconnection
        """
        async with self._lock:
            connection = self._connections.pop(connection_id, None)

        if not connection:
            return

        # Remove from project tracking
        for project_id in connection.subscribed_projects:
            project_conns = self._project_connections.get(project_id, set())
            project_conns.discard(connection_id)

            # Notify others
            await self._broadcast_to_project(
                project_id,
                AnnotationMessage(
                    type=AnnotationMessageType.USER_LEFT,
                    payload={
                        "user_id": connection.user_id,
                        "user_name": connection.user_name,
                        "project_id": project_id,
                    }
                ),
                exclude_connection=connection_id,
            )

        # Remove from document tracking
        for doc_id in connection.subscribed_documents:
            doc_conns = self._document_connections.get(doc_id, set())
            doc_conns.discard(connection_id)

        # Remove from user tracking
        if connection.user_id:
            self._user_connections.pop(connection.user_id, None)

        # Close websocket
        try:
            await connection.websocket.close()
        except Exception as e:
            logger.debug(f"Error closing websocket: {e}")

        logger.info(f"Annotation WebSocket disconnected: {connection_id}, reason: {reason}")

    async def authenticate(
        self,
        connection_id: str,
        token: str,
        tenant_id: str,
        user_id: str,
        user_name: str,
        role: str = "annotator",
    ) -> bool:
        """
        Authenticate a WebSocket connection.

        Args:
            connection_id: Connection to authenticate
            token: Authentication token
            tenant_id: Tenant ID
            user_id: User ID
            user_name: User display name
            role: User role

        Returns:
            True if authentication successful
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return False

        # TODO: Add actual token validation
        # For now, accept all tokens

        connection.tenant_id = tenant_id
        connection.user_id = user_id
        connection.user_name = user_name
        connection.role = role
        connection.is_authenticated = True

        # Track user connection
        self._user_connections[user_id] = connection_id

        await self._send_message(connection, AnnotationMessage(
            type=AnnotationMessageType.AUTH_SUCCESS,
            payload={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "user_name": user_name,
                "role": role,
            }
        ))

        logger.info(f"Connection authenticated: {connection_id}, user: {user_id}")
        return True

    # =========================================================================
    # Subscription Management
    # =========================================================================

    async def subscribe_project(
        self,
        connection_id: str,
        project_id: str,
    ) -> bool:
        """
        Subscribe a connection to a project's updates.

        Args:
            connection_id: Connection to subscribe
            project_id: Project to subscribe to

        Returns:
            True if subscription successful
        """
        connection = self._connections.get(connection_id)
        if not connection or not connection.is_authenticated:
            return False

        # Check project connection limit
        project_conns = self._project_connections.get(project_id, set())
        if len(project_conns) >= self._max_connections_per_project:
            await self._send_message(connection, AnnotationMessage(
                type=AnnotationMessageType.ERROR,
                payload={
                    "error": "project_connection_limit",
                    "message": f"Project has reached maximum connections ({self._max_connections_per_project})"
                }
            ))
            return False

        # Add subscription
        connection.subscribed_projects.add(project_id)

        if project_id not in self._project_connections:
            self._project_connections[project_id] = set()
        self._project_connections[project_id].add(connection_id)

        # Get current users in project
        current_users = []
        for conn_id in self._project_connections[project_id]:
            conn = self._connections.get(conn_id)
            if conn and conn.user_id and conn_id != connection_id:
                current_users.append({
                    "user_id": conn.user_id,
                    "user_name": conn.user_name,
                    "role": conn.role,
                })

        await self._send_message(connection, AnnotationMessage(
            type=AnnotationMessageType.SUBSCRIBED,
            payload={
                "project_id": project_id,
                "current_users": current_users,
            }
        ))

        # Notify others
        await self._broadcast_to_project(
            project_id,
            AnnotationMessage(
                type=AnnotationMessageType.USER_JOINED,
                payload={
                    "user_id": connection.user_id,
                    "user_name": connection.user_name,
                    "role": connection.role,
                    "project_id": project_id,
                }
            ),
            exclude_connection=connection_id,
        )

        logger.debug(f"Connection {connection_id} subscribed to project {project_id}")
        return True

    async def unsubscribe_project(
        self,
        connection_id: str,
        project_id: str,
    ) -> bool:
        """
        Unsubscribe a connection from a project.

        Args:
            connection_id: Connection to unsubscribe
            project_id: Project to unsubscribe from

        Returns:
            True if unsubscription successful
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return False

        connection.subscribed_projects.discard(project_id)

        if project_id in self._project_connections:
            self._project_connections[project_id].discard(connection_id)

        # Notify others
        await self._broadcast_to_project(
            project_id,
            AnnotationMessage(
                type=AnnotationMessageType.USER_LEFT,
                payload={
                    "user_id": connection.user_id,
                    "user_name": connection.user_name,
                    "project_id": project_id,
                }
            ),
            exclude_connection=connection_id,
        )

        await self._send_message(connection, AnnotationMessage(
            type=AnnotationMessageType.UNSUBSCRIBED,
            payload={"project_id": project_id}
        ))

        return True

    # =========================================================================
    # Message Handling
    # =========================================================================

    async def handle_message(
        self,
        connection_id: str,
        message_data: Dict[str, Any],
    ) -> None:
        """
        Handle an incoming WebSocket message.

        Args:
            connection_id: Source connection
            message_data: Message data
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return

        connection.update_activity()

        try:
            message = AnnotationMessage(**message_data)

            # Route message to handler
            handlers = {
                AnnotationMessageType.AUTH: self._handle_auth,
                AnnotationMessageType.SUBSCRIBE_PROJECT: self._handle_subscribe,
                AnnotationMessageType.UNSUBSCRIBE_PROJECT: self._handle_unsubscribe,
                AnnotationMessageType.REQUEST_SUGGESTION: self._handle_suggestion_request,
                AnnotationMessageType.SUBMIT_ANNOTATION: self._handle_annotation_submit,
                AnnotationMessageType.SUBMIT_FEEDBACK: self._handle_feedback,
                AnnotationMessageType.START_TASK: self._handle_task_start,
                AnnotationMessageType.COMPLETE_TASK: self._handle_task_complete,
                AnnotationMessageType.RESOLVE_CONFLICT: self._handle_conflict_resolution,
                AnnotationMessageType.REQUEST_PROGRESS: self._handle_progress_request,
                AnnotationMessageType.PING: self._handle_ping,
            }

            handler = handlers.get(message.type)
            if handler:
                await handler(connection, message)
            else:
                logger.warning(f"No handler for message type: {message.type}")
                await self._send_message(connection, AnnotationMessage(
                    type=AnnotationMessageType.ERROR,
                    payload={
                        "error": "unknown_message_type",
                        "type": str(message.type),
                    }
                ))

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_message(connection, AnnotationMessage(
                type=AnnotationMessageType.ERROR,
                payload={
                    "error": "message_processing_error",
                    "message": str(e),
                }
            ))

    async def _handle_auth(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Handle authentication message."""
        payload = message.payload
        await self.authenticate(
            connection.connection_id,
            payload.get("token", ""),
            payload.get("tenant_id", ""),
            payload.get("user_id", ""),
            payload.get("user_name", ""),
            payload.get("role", "annotator"),
        )

    async def _handle_subscribe(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Handle project subscription."""
        project_id = message.payload.get("project_id")
        if project_id:
            await self.subscribe_project(connection.connection_id, project_id)

    async def _handle_unsubscribe(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Handle project unsubscription."""
        project_id = message.payload.get("project_id")
        if project_id:
            await self.unsubscribe_project(connection.connection_id, project_id)

    async def _handle_suggestion_request(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Handle suggestion request with low latency target."""
        if not connection.is_authenticated:
            await self._send_message(connection, AnnotationMessage(
                type=AnnotationMessageType.ERROR,
                payload={"error": "not_authenticated"}
            ))
            return

        start_time = datetime.utcnow()

        try:
            payload = SuggestionPayload(**message.payload)

            # Generate suggestion
            if self._suggestion_handler:
                try:
                    suggestion = await asyncio.wait_for(
                        self._suggestion_handler(
                            document_id=payload.document_id,
                            text=payload.text,
                            context=payload.context,
                            annotation_type=payload.annotation_type,
                            position=payload.position,
                            user_id=connection.user_id,
                            tenant_id=connection.tenant_id,
                        ),
                        timeout=self._suggestion_timeout,
                    )
                except asyncio.TimeoutError:
                    suggestion = {
                        "suggestion_id": f"sug_{uuid4().hex[:12]}",
                        "status": "timeout",
                        "message": "Suggestion generation timed out",
                    }
            else:
                # Mock suggestion for testing
                suggestion = {
                    "suggestion_id": f"sug_{uuid4().hex[:12]}",
                    "document_id": payload.document_id,
                    "annotations": [
                        {
                            "label": "ENTITY",
                            "start": 0,
                            "end": len(payload.text),
                            "text": payload.text,
                            "confidence": 0.85,
                        }
                    ],
                    "confidence": 0.85,
                }

            # Calculate latency
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_suggestion_metrics(latency_ms)

            suggestion["latency_ms"] = latency_ms

            await self._send_message(connection, AnnotationMessage(
                type=AnnotationMessageType.SUGGESTION,
                payload=suggestion,
                correlation_id=message.message_id,
            ))

        except Exception as e:
            logger.error(f"Suggestion request failed: {e}")
            await self._send_message(connection, AnnotationMessage(
                type=AnnotationMessageType.ERROR,
                payload={
                    "error": "suggestion_failed",
                    "message": str(e),
                },
                correlation_id=message.message_id,
            ))

    async def _handle_annotation_submit(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Handle annotation submission."""
        if not connection.is_authenticated:
            return

        try:
            payload = AnnotationPayload(**message.payload)

            # Check for conflicts with other users
            conflict = await self._check_annotation_conflict(
                payload.document_id,
                payload.annotation_data,
                connection.user_id,
            )

            if conflict:
                # Notify about conflict
                await self._broadcast_to_document(
                    payload.document_id,
                    AnnotationMessage(
                        type=AnnotationMessageType.CONFLICT_DETECTED,
                        payload={
                            "conflict_id": conflict["conflict_id"],
                            "document_id": payload.document_id,
                            "conflict_type": conflict["type"],
                            "annotations": conflict["annotations"],
                            "users": conflict["users"],
                        }
                    ),
                )
                self._conflict_count += 1
            else:
                # Broadcast annotation update
                await self._broadcast_to_document(
                    payload.document_id,
                    AnnotationMessage(
                        type=AnnotationMessageType.ANNOTATION_UPDATE,
                        payload={
                            "document_id": payload.document_id,
                            "task_id": payload.task_id,
                            "user_id": connection.user_id,
                            "user_name": connection.user_name,
                            "annotation_data": payload.annotation_data,
                            "confidence": payload.confidence,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ),
                    exclude_connection=connection.connection_id,
                )

        except Exception as e:
            logger.error(f"Annotation submit failed: {e}")
            await self._send_message(connection, AnnotationMessage(
                type=AnnotationMessageType.ERROR,
                payload={"error": "annotation_submit_failed", "message": str(e)}
            ))

    async def _handle_feedback(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Handle suggestion feedback."""
        if not connection.is_authenticated:
            return

        try:
            payload = FeedbackPayload(**message.payload)

            if self._feedback_handler:
                await self._feedback_handler(
                    suggestion_id=payload.suggestion_id,
                    accepted=payload.accepted,
                    modified_annotation=payload.modified_annotation,
                    reason=payload.reason,
                    user_id=connection.user_id,
                    tenant_id=connection.tenant_id,
                )

            self._feedback_count += 1

        except Exception as e:
            logger.error(f"Feedback processing failed: {e}")

    async def _handle_task_start(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Handle task start notification."""
        if not connection.is_authenticated:
            return

        task_id = message.payload.get("task_id")
        project_id = message.payload.get("project_id")

        if project_id:
            await self._broadcast_to_project(
                project_id,
                AnnotationMessage(
                    type=AnnotationMessageType.TASK_STARTED,
                    payload={
                        "task_id": task_id,
                        "user_id": connection.user_id,
                        "user_name": connection.user_name,
                        "started_at": datetime.utcnow().isoformat(),
                    }
                ),
                exclude_connection=connection.connection_id,
            )

    async def _handle_task_complete(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Handle task completion notification."""
        if not connection.is_authenticated:
            return

        task_id = message.payload.get("task_id")
        project_id = message.payload.get("project_id")
        result = message.payload.get("result", {})

        if project_id:
            await self._broadcast_to_project(
                project_id,
                AnnotationMessage(
                    type=AnnotationMessageType.TASK_COMPLETED,
                    payload={
                        "task_id": task_id,
                        "user_id": connection.user_id,
                        "user_name": connection.user_name,
                        "result": result,
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                ),
                exclude_connection=connection.connection_id,
            )

    async def _handle_conflict_resolution(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Handle conflict resolution."""
        if not connection.is_authenticated:
            return

        try:
            payload = ConflictResolutionPayload(**message.payload)

            if self._conflict_resolver:
                await self._conflict_resolver(
                    conflict_id=payload.conflict_id,
                    resolution=payload.resolution,
                    resolved_annotation=payload.resolved_annotation,
                    resolution_notes=payload.resolution_notes,
                    resolver_id=connection.user_id,
                    tenant_id=connection.tenant_id,
                )

            # Broadcast resolution
            # TODO: Get document_id from conflict
            document_id = message.payload.get("document_id", "")
            if document_id:
                await self._broadcast_to_document(
                    document_id,
                    AnnotationMessage(
                        type=AnnotationMessageType.CONFLICT_RESOLVED,
                        payload={
                            "conflict_id": payload.conflict_id,
                            "resolution": payload.resolution,
                            "resolved_by": connection.user_id,
                            "resolved_by_name": connection.user_name,
                            "resolved_annotation": payload.resolved_annotation,
                            "resolved_at": datetime.utcnow().isoformat(),
                        }
                    ),
                )

        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            await self._send_message(connection, AnnotationMessage(
                type=AnnotationMessageType.ERROR,
                payload={"error": "conflict_resolution_failed", "message": str(e)}
            ))

    async def _handle_progress_request(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Handle progress request."""
        if not connection.is_authenticated:
            return

        project_id = message.payload.get("project_id")

        # TODO: Integrate with CollaborationManager for real progress
        progress = {
            "project_id": project_id,
            "total_tasks": 100,
            "completed_tasks": 45,
            "in_progress_tasks": 10,
            "pending_tasks": 45,
            "completion_rate": 0.45,
            "active_annotators": len(self._project_connections.get(project_id, set())),
            "avg_time_per_task_minutes": 5.2,
        }

        await self._send_message(connection, AnnotationMessage(
            type=AnnotationMessageType.PROGRESS_UPDATE,
            payload=progress,
            correlation_id=message.message_id,
        ))

    async def _handle_ping(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Handle ping message."""
        await self._send_message(connection, AnnotationMessage(
            type=AnnotationMessageType.PONG,
            payload={"timestamp": datetime.utcnow().isoformat()},
            correlation_id=message.message_id,
        ))

    # =========================================================================
    # Broadcasting
    # =========================================================================

    async def _broadcast_to_project(
        self,
        project_id: str,
        message: AnnotationMessage,
        exclude_connection: Optional[str] = None,
    ) -> int:
        """Broadcast message to all project subscribers."""
        connection_ids = self._project_connections.get(project_id, set())
        sent_count = 0

        for conn_id in list(connection_ids):
            if conn_id == exclude_connection:
                continue

            connection = self._connections.get(conn_id)
            if connection:
                try:
                    await self._send_message(connection, message)
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send to {conn_id}: {e}")

        return sent_count

    async def _broadcast_to_document(
        self,
        document_id: str,
        message: AnnotationMessage,
        exclude_connection: Optional[str] = None,
    ) -> int:
        """Broadcast message to all document viewers."""
        connection_ids = self._document_connections.get(document_id, set())
        sent_count = 0

        for conn_id in list(connection_ids):
            if conn_id == exclude_connection:
                continue

            connection = self._connections.get(conn_id)
            if connection:
                try:
                    await self._send_message(connection, message)
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send to {conn_id}: {e}")

        return sent_count

    async def broadcast_quality_alert(
        self,
        project_id: str,
        alert_type: str,
        alert_data: Dict[str, Any],
    ) -> int:
        """
        Broadcast quality alert to project subscribers.

        Args:
            project_id: Target project
            alert_type: Type of alert (quality_drop, high_rejection, etc.)
            alert_data: Alert details

        Returns:
            Number of connections notified
        """
        return await self._broadcast_to_project(
            project_id,
            AnnotationMessage(
                type=AnnotationMessageType.QUALITY_ALERT,
                payload={
                    "alert_type": alert_type,
                    "project_id": project_id,
                    **alert_data,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
        )

    async def send_suggestion_batch(
        self,
        user_id: str,
        suggestions: List[Dict[str, Any]],
    ) -> bool:
        """
        Send batch of suggestions to a specific user.

        Args:
            user_id: Target user
            suggestions: List of suggestion data

        Returns:
            True if sent successfully
        """
        conn_id = self._user_connections.get(user_id)
        if not conn_id:
            return False

        connection = self._connections.get(conn_id)
        if not connection:
            return False

        try:
            await self._send_message(connection, AnnotationMessage(
                type=AnnotationMessageType.SUGGESTION_BATCH,
                payload={
                    "suggestions": suggestions,
                    "count": len(suggestions),
                }
            ))
            return True
        except Exception as e:
            logger.warning(f"Failed to send suggestion batch to {user_id}: {e}")
            return False

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _send_message(
        self,
        connection: AnnotationConnectionInfo,
        message: AnnotationMessage,
    ) -> None:
        """Send a message to a connection."""
        try:
            await connection.websocket.send_json(message.model_dump(mode="json"))
        except Exception as e:
            logger.error(f"Error sending message to {connection.connection_id}: {e}")
            raise

    async def _check_annotation_conflict(
        self,
        document_id: str,
        annotation_data: Dict[str, Any],
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check for conflicts with other users' annotations.

        This is a simplified implementation. In production, this would
        check against recent annotations from other users in the same
        document region.
        """
        # TODO: Implement actual conflict detection
        # For now, return None (no conflict)
        return None

    def _update_suggestion_metrics(self, latency_ms: float) -> None:
        """Update suggestion metrics."""
        self._suggestion_count += 1
        # Rolling average
        self._avg_suggestion_latency_ms = (
            (self._avg_suggestion_latency_ms * (self._suggestion_count - 1) + latency_ms)
            / self._suggestion_count
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            "total_connections": len(self._connections),
            "projects": len(self._project_connections),
            "documents": len(self._document_connections),
            "suggestion_count": self._suggestion_count,
            "feedback_count": self._feedback_count,
            "conflict_count": self._conflict_count,
            "avg_suggestion_latency_ms": round(self._avg_suggestion_latency_ms, 2),
            "connections_by_project": {
                proj: len(conns)
                for proj, conns in self._project_connections.items()
            },
        }


# =============================================================================
# Global Instance
# =============================================================================

_annotation_ws_manager: Optional[AnnotationWebSocketManager] = None


def get_annotation_ws_manager() -> AnnotationWebSocketManager:
    """Get the global annotation WebSocket manager instance."""
    global _annotation_ws_manager
    if _annotation_ws_manager is None:
        _annotation_ws_manager = AnnotationWebSocketManager()
    return _annotation_ws_manager


def set_annotation_ws_manager(manager: AnnotationWebSocketManager) -> None:
    """Set the global annotation WebSocket manager instance."""
    global _annotation_ws_manager
    _annotation_ws_manager = manager


__all__ = [
    "AnnotationWebSocketManager",
    "AnnotationConnectionInfo",
    "AnnotationMessage",
    "AnnotationMessageType",
    "ConflictType",
    "SuggestionPayload",
    "AnnotationPayload",
    "FeedbackPayload",
    "ConflictResolutionPayload",
    "get_annotation_ws_manager",
    "set_annotation_ws_manager",
]
