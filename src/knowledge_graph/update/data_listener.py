"""
Data Listener for Knowledge Graph Incremental Updates.

Monitors annotation data changes and triggers incremental extraction
to keep the knowledge graph synchronized with source data.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Coroutine,
    Union,
)
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Types of data changes."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"


class DataSource(str, Enum):
    """Data source types."""
    ANNOTATION = "annotation"
    DOCUMENT = "document"
    TASK = "task"
    PROJECT = "project"
    USER = "user"
    LABEL = "label"
    QUALITY_ISSUE = "quality_issue"
    EXTERNAL = "external"


@dataclass
class DataChangeEvent:
    """
    Represents a data change event.

    Captures information about changes to source data that may
    require knowledge graph updates.
    """
    id: UUID = field(default_factory=uuid4)
    source: DataSource = DataSource.ANNOTATION
    change_type: ChangeType = ChangeType.UPDATE
    entity_id: Optional[str] = None
    entity_ids: List[str] = field(default_factory=list)
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tenant_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    processed: bool = False
    processed_at: Optional[datetime] = None
    error: Optional[str] = None

    def __post_init__(self):
        """Ensure entity_ids includes entity_id if provided."""
        if self.entity_id and self.entity_id not in self.entity_ids:
            self.entity_ids = [self.entity_id] + self.entity_ids

    def mark_processed(self, error: Optional[str] = None) -> None:
        """Mark the event as processed."""
        self.processed = True
        self.processed_at = datetime.now()
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "source": self.source.value,
            "change_type": self.change_type.value,
            "entity_id": self.entity_id,
            "entity_ids": self.entity_ids,
            "old_data": self.old_data,
            "new_data": self.new_data,
            "metadata": self.metadata,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "processed": self.processed,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error": self.error,
        }


# Type alias for event handlers
EventHandler = Callable[[DataChangeEvent], Coroutine[Any, Any, None]]


class BaseDataListener(ABC):
    """
    Abstract base class for data listeners.

    Provides the interface for listening to data changes
    from various sources.
    """

    @abstractmethod
    async def start(self) -> None:
        """Start listening for changes."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening for changes."""
        pass

    @abstractmethod
    def register_handler(self, handler: EventHandler) -> None:
        """Register an event handler."""
        pass

    @abstractmethod
    def unregister_handler(self, handler: EventHandler) -> None:
        """Unregister an event handler."""
        pass


class DataListener(BaseDataListener):
    """
    Main data listener for monitoring annotation data changes.

    Supports multiple data sources and provides event batching,
    filtering, and handler management.
    """

    def __init__(
        self,
        poll_interval: float = 5.0,
        batch_size: int = 100,
        batch_timeout: float = 10.0,
        sources: Optional[List[DataSource]] = None,
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize DataListener.

        Args:
            poll_interval: Interval between polling checks (seconds)
            batch_size: Maximum events per batch
            batch_timeout: Maximum wait time for batch (seconds)
            sources: Data sources to listen to
            tenant_id: Filter events by tenant
        """
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.sources = sources or list(DataSource)
        self.tenant_id = tenant_id

        self._handlers: List[EventHandler] = []
        self._running = False
        self._event_queue: asyncio.Queue[DataChangeEvent] = asyncio.Queue()
        self._batch_buffer: List[DataChangeEvent] = []
        self._last_batch_time = datetime.now()
        self._poll_task: Optional[asyncio.Task] = None
        self._process_task: Optional[asyncio.Task] = None
        self._last_check_time: Dict[DataSource, datetime] = {}
        self._processed_events: Set[UUID] = set()
        self._max_processed_cache = 10000

        # Statistics
        self._stats = {
            "events_received": 0,
            "events_processed": 0,
            "events_failed": 0,
            "batches_processed": 0,
            "start_time": None,
            "last_event_time": None,
        }

        logger.info(f"DataListener initialized with sources: {[s.value for s in self.sources]}")

    async def start(self) -> None:
        """Start listening for data changes."""
        if self._running:
            logger.warning("DataListener is already running")
            return

        self._running = True
        self._stats["start_time"] = datetime.now()

        # Initialize last check times
        for source in self.sources:
            self._last_check_time[source] = datetime.now()

        # Start background tasks
        self._poll_task = asyncio.create_task(self._poll_loop())
        self._process_task = asyncio.create_task(self._process_loop())

        logger.info("DataListener started")

    async def stop(self) -> None:
        """Stop listening for data changes."""
        if not self._running:
            return

        self._running = False

        # Cancel background tasks
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass

        # Process remaining events
        await self._flush_batch()

        logger.info("DataListener stopped")

    def register_handler(self, handler: EventHandler) -> None:
        """Register an event handler."""
        if handler not in self._handlers:
            self._handlers.append(handler)
            logger.info(f"Registered handler: {handler.__name__}")

    def unregister_handler(self, handler: EventHandler) -> None:
        """Unregister an event handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)
            logger.info(f"Unregistered handler: {handler.__name__}")

    async def emit_event(self, event: DataChangeEvent) -> None:
        """
        Emit a data change event.

        This can be called directly by external code to trigger
        knowledge graph updates.

        Args:
            event: The data change event
        """
        # Filter by source
        if event.source not in self.sources:
            return

        # Filter by tenant
        if self.tenant_id and event.tenant_id != self.tenant_id:
            return

        # Deduplicate
        if event.id in self._processed_events:
            return

        await self._event_queue.put(event)
        self._stats["events_received"] += 1
        self._stats["last_event_time"] = datetime.now()

        logger.debug(f"Event emitted: {event.source.value}/{event.change_type.value}")

    async def _poll_loop(self) -> None:
        """Background task to poll for data changes."""
        while self._running:
            try:
                await self._check_for_changes()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in poll loop: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _process_loop(self) -> None:
        """Background task to process events."""
        while self._running:
            try:
                # Get event from queue with timeout
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=1.0
                    )
                    self._batch_buffer.append(event)
                except asyncio.TimeoutError:
                    pass

                # Check if we should flush the batch
                should_flush = (
                    len(self._batch_buffer) >= self.batch_size or
                    (self._batch_buffer and
                     (datetime.now() - self._last_batch_time).total_seconds() >= self.batch_timeout)
                )

                if should_flush:
                    await self._flush_batch()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in process loop: {e}")

    async def _check_for_changes(self) -> None:
        """Check data sources for changes."""
        for source in self.sources:
            try:
                events = await self._poll_source(source)
                for event in events:
                    await self.emit_event(event)
            except Exception as e:
                logger.error(f"Error polling {source.value}: {e}")

    async def _poll_source(self, source: DataSource) -> List[DataChangeEvent]:
        """
        Poll a specific data source for changes.

        This method should be overridden or extended to integrate
        with actual data sources.

        Args:
            source: The data source to poll

        Returns:
            List of change events
        """
        events = []
        last_check = self._last_check_time.get(source, datetime.now())

        # Check annotation changes
        if source == DataSource.ANNOTATION:
            events = await self._poll_annotation_changes(last_check)
        elif source == DataSource.DOCUMENT:
            events = await self._poll_document_changes(last_check)
        elif source == DataSource.TASK:
            events = await self._poll_task_changes(last_check)
        elif source == DataSource.PROJECT:
            events = await self._poll_project_changes(last_check)

        self._last_check_time[source] = datetime.now()
        return events

    async def _poll_annotation_changes(self, since: datetime) -> List[DataChangeEvent]:
        """Poll for annotation changes."""
        events = []

        try:
            # Import here to avoid circular imports
            from src.database.models import TaskModel
            from src.database.connection import get_async_session
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            async with get_async_session() as session:
                # Query for recently updated tasks (which contain annotations)
                query = select(TaskModel).where(
                    TaskModel.updated_at > since
                )
                if self.tenant_id:
                    query = query.where(TaskModel.tenant_id == self.tenant_id)

                result = await session.execute(query)
                tasks = result.scalars().all()

                for task in tasks:
                    # Determine change type based on timestamps
                    if task.created_at > since:
                        change_type = ChangeType.CREATE
                    else:
                        change_type = ChangeType.UPDATE

                    event = DataChangeEvent(
                        source=DataSource.ANNOTATION,
                        change_type=change_type,
                        entity_id=str(task.id),
                        new_data={
                            "task_id": str(task.id),
                            "document_id": str(task.document_id) if task.document_id else None,
                            "status": task.status.value if task.status else None,
                            "annotation_data": task.annotation_data,
                            "quality_score": task.quality_score,
                        },
                        tenant_id=task.tenant_id,
                        timestamp=task.updated_at,
                    )
                    events.append(event)

        except ImportError:
            logger.debug("Database models not available for polling")
        except Exception as e:
            logger.error(f"Error polling annotation changes: {e}")

        return events

    async def _poll_document_changes(self, since: datetime) -> List[DataChangeEvent]:
        """Poll for document changes."""
        events = []

        try:
            from src.database.models import DocumentModel
            from src.database.connection import get_async_session
            from sqlalchemy import select

            async with get_async_session() as session:
                query = select(DocumentModel).where(
                    DocumentModel.updated_at > since
                )
                if self.tenant_id:
                    query = query.where(DocumentModel.tenant_id == self.tenant_id)

                result = await session.execute(query)
                documents = result.scalars().all()

                for doc in documents:
                    change_type = ChangeType.CREATE if doc.created_at > since else ChangeType.UPDATE

                    event = DataChangeEvent(
                        source=DataSource.DOCUMENT,
                        change_type=change_type,
                        entity_id=str(doc.id),
                        new_data={
                            "document_id": str(doc.id),
                            "content": doc.content,
                            "metadata": doc.metadata,
                            "source_type": doc.source_type,
                        },
                        tenant_id=doc.tenant_id,
                        timestamp=doc.updated_at,
                    )
                    events.append(event)

        except ImportError:
            logger.debug("Database models not available for polling")
        except Exception as e:
            logger.error(f"Error polling document changes: {e}")

        return events

    async def _poll_task_changes(self, since: datetime) -> List[DataChangeEvent]:
        """Poll for task changes."""
        # Similar implementation to annotation changes
        return []

    async def _poll_project_changes(self, since: datetime) -> List[DataChangeEvent]:
        """Poll for project changes."""
        # Similar implementation
        return []

    async def _flush_batch(self) -> None:
        """Flush the current batch of events to handlers."""
        if not self._batch_buffer:
            return

        batch = self._batch_buffer.copy()
        self._batch_buffer.clear()
        self._last_batch_time = datetime.now()

        # Process batch through handlers
        for handler in self._handlers:
            for event in batch:
                try:
                    await handler(event)
                    event.mark_processed()
                    self._stats["events_processed"] += 1

                    # Track processed events for deduplication
                    self._processed_events.add(event.id)

                    # Limit cache size
                    if len(self._processed_events) > self._max_processed_cache:
                        # Remove oldest entries (approximate)
                        to_remove = len(self._processed_events) - self._max_processed_cache
                        for _ in range(to_remove):
                            self._processed_events.pop()

                except Exception as e:
                    event.mark_processed(error=str(e))
                    self._stats["events_failed"] += 1
                    logger.error(f"Handler error for event {event.id}: {e}")

        self._stats["batches_processed"] += 1
        logger.debug(f"Processed batch of {len(batch)} events")

    def get_stats(self) -> Dict[str, Any]:
        """Get listener statistics."""
        return {
            **self._stats,
            "handlers_count": len(self._handlers),
            "queue_size": self._event_queue.qsize(),
            "buffer_size": len(self._batch_buffer),
            "is_running": self._running,
        }


class WebhookDataListener(BaseDataListener):
    """
    Data listener that receives events via webhooks.

    Can be integrated with Label Studio webhooks or other
    external systems that push change notifications.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        allowed_sources: Optional[List[str]] = None,
    ):
        """
        Initialize WebhookDataListener.

        Args:
            secret_key: Secret key for webhook signature verification
            allowed_sources: List of allowed source identifiers
        """
        self.secret_key = secret_key
        self.allowed_sources = allowed_sources or []
        self._handlers: List[EventHandler] = []
        self._running = False

    async def start(self) -> None:
        """Start the webhook listener."""
        self._running = True
        logger.info("WebhookDataListener started")

    async def stop(self) -> None:
        """Stop the webhook listener."""
        self._running = False
        logger.info("WebhookDataListener stopped")

    def register_handler(self, handler: EventHandler) -> None:
        """Register an event handler."""
        if handler not in self._handlers:
            self._handlers.append(handler)

    def unregister_handler(self, handler: EventHandler) -> None:
        """Unregister an event handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> bool:
        """
        Handle an incoming webhook event.

        Args:
            payload: Webhook payload data
            signature: Optional HMAC signature for verification
            source_id: Identifier of the webhook source

        Returns:
            True if event was processed successfully
        """
        if not self._running:
            logger.warning("WebhookDataListener is not running")
            return False

        # Verify signature if secret key is configured
        if self.secret_key and signature:
            if not self._verify_signature(payload, signature):
                logger.warning("Invalid webhook signature")
                return False

        # Check allowed sources
        if self.allowed_sources and source_id not in self.allowed_sources:
            logger.warning(f"Webhook from unauthorized source: {source_id}")
            return False

        # Convert webhook payload to event
        event = self._parse_webhook_payload(payload, source_id)
        if not event:
            logger.warning("Failed to parse webhook payload")
            return False

        # Process through handlers
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Handler error for webhook event: {e}")

        return True

    def _verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """Verify webhook signature using HMAC."""
        import hashlib
        import hmac
        import json

        if not self.secret_key:
            return True

        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        expected_signature = hmac.new(
            self.secret_key.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def _parse_webhook_payload(
        self,
        payload: Dict[str, Any],
        source_id: Optional[str] = None,
    ) -> Optional[DataChangeEvent]:
        """Parse webhook payload into a DataChangeEvent."""
        try:
            # Detect webhook type and parse accordingly
            if "action" in payload:
                # Label Studio webhook format
                return self._parse_label_studio_webhook(payload)
            elif "event_type" in payload:
                # Generic webhook format
                return self._parse_generic_webhook(payload)
            else:
                # Try to create event from raw payload
                return DataChangeEvent(
                    source=DataSource.EXTERNAL,
                    change_type=ChangeType.UPDATE,
                    new_data=payload,
                    metadata={"source_id": source_id},
                )
        except Exception as e:
            logger.error(f"Error parsing webhook payload: {e}")
            return None

    def _parse_label_studio_webhook(self, payload: Dict[str, Any]) -> Optional[DataChangeEvent]:
        """Parse Label Studio webhook payload."""
        action = payload.get("action", "")

        # Map Label Studio actions to change types
        action_map = {
            "ANNOTATION_CREATED": ChangeType.CREATE,
            "ANNOTATION_UPDATED": ChangeType.UPDATE,
            "ANNOTATION_DELETED": ChangeType.DELETE,
            "TASK_CREATED": ChangeType.CREATE,
            "TASK_UPDATED": ChangeType.UPDATE,
            "TASK_DELETED": ChangeType.DELETE,
        }

        change_type = action_map.get(action, ChangeType.UPDATE)

        # Determine source type
        if "ANNOTATION" in action:
            source = DataSource.ANNOTATION
        elif "TASK" in action:
            source = DataSource.TASK
        else:
            source = DataSource.EXTERNAL

        # Extract entity ID
        entity_id = None
        if "annotation" in payload:
            entity_id = str(payload["annotation"].get("id", ""))
        elif "task" in payload:
            entity_id = str(payload["task"].get("id", ""))

        return DataChangeEvent(
            source=source,
            change_type=change_type,
            entity_id=entity_id,
            new_data=payload,
            metadata={
                "webhook_type": "label_studio",
                "action": action,
            },
        )

    def _parse_generic_webhook(self, payload: Dict[str, Any]) -> Optional[DataChangeEvent]:
        """Parse generic webhook payload."""
        event_type = payload.get("event_type", "update")

        # Map event types
        type_map = {
            "create": ChangeType.CREATE,
            "created": ChangeType.CREATE,
            "update": ChangeType.UPDATE,
            "updated": ChangeType.UPDATE,
            "delete": ChangeType.DELETE,
            "deleted": ChangeType.DELETE,
        }

        change_type = type_map.get(event_type.lower(), ChangeType.UPDATE)

        return DataChangeEvent(
            source=DataSource.EXTERNAL,
            change_type=change_type,
            entity_id=payload.get("entity_id") or payload.get("id"),
            new_data=payload.get("data", payload),
            metadata=payload.get("metadata", {}),
        )


class CompositeDataListener(BaseDataListener):
    """
    Composite listener that aggregates multiple data listeners.

    Allows combining polling and webhook listeners for
    comprehensive change detection.
    """

    def __init__(self, listeners: Optional[List[BaseDataListener]] = None):
        """
        Initialize CompositeDataListener.

        Args:
            listeners: List of data listeners to aggregate
        """
        self.listeners = listeners or []
        self._handlers: List[EventHandler] = []

    def add_listener(self, listener: BaseDataListener) -> None:
        """Add a listener to the composite."""
        self.listeners.append(listener)
        # Propagate existing handlers
        for handler in self._handlers:
            listener.register_handler(handler)

    def remove_listener(self, listener: BaseDataListener) -> None:
        """Remove a listener from the composite."""
        if listener in self.listeners:
            self.listeners.remove(listener)

    async def start(self) -> None:
        """Start all listeners."""
        for listener in self.listeners:
            await listener.start()

    async def stop(self) -> None:
        """Stop all listeners."""
        for listener in self.listeners:
            await listener.stop()

    def register_handler(self, handler: EventHandler) -> None:
        """Register handler with all listeners."""
        self._handlers.append(handler)
        for listener in self.listeners:
            listener.register_handler(handler)

    def unregister_handler(self, handler: EventHandler) -> None:
        """Unregister handler from all listeners."""
        if handler in self._handlers:
            self._handlers.remove(handler)
        for listener in self.listeners:
            listener.unregister_handler(handler)
