"""
Incremental Updater for Knowledge Graph.

Integrates data listening, entity extraction, and version management
to keep the knowledge graph synchronized with source data.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from ..core.models import Entity, Relation, EntityType, RelationType
from ..core.graph_db import GraphDatabase, get_graph_database
from .data_listener import (
    DataListener,
    DataChangeEvent,
    ChangeType,
    DataSource,
)
from .version_manager import (
    VersionManager,
    ChangeOperationType,
    ChangeRecord,
    get_version_manager,
)

logger = logging.getLogger(__name__)


class UpdateStrategy(str, Enum):
    """Strategies for handling incremental updates."""
    IMMEDIATE = "immediate"  # Process changes immediately
    BATCHED = "batched"  # Batch changes and process periodically
    SCHEDULED = "scheduled"  # Process at scheduled times
    MANUAL = "manual"  # Only process on explicit trigger


class ExtractionMode(str, Enum):
    """Modes for entity/relation extraction."""
    FULL = "full"  # Full extraction from content
    INCREMENTAL = "incremental"  # Only extract changes
    DIFFERENTIAL = "differential"  # Extract and compare with existing


@dataclass
class UpdateResult:
    """
    Result of an incremental update operation.

    Contains statistics and details about the update.
    """
    id: UUID = field(default_factory=uuid4)
    success: bool = True
    events_processed: int = 0
    entities_created: int = 0
    entities_updated: int = 0
    entities_deleted: int = 0
    relations_created: int = 0
    relations_updated: int = 0
    relations_deleted: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    version_id: Optional[UUID] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_completed(self) -> None:
        """Mark the update as completed."""
        self.completed_at = datetime.now()
        self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    @property
    def total_changes(self) -> int:
        """Get total number of changes."""
        return (
            self.entities_created +
            self.entities_updated +
            self.entities_deleted +
            self.relations_created +
            self.relations_updated +
            self.relations_deleted
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "success": self.success,
            "events_processed": self.events_processed,
            "entities_created": self.entities_created,
            "entities_updated": self.entities_updated,
            "entities_deleted": self.entities_deleted,
            "relations_created": self.relations_created,
            "relations_updated": self.relations_updated,
            "relations_deleted": self.relations_deleted,
            "total_changes": self.total_changes,
            "errors": self.errors,
            "warnings": self.warnings,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "version_id": str(self.version_id) if self.version_id else None,
            "metadata": self.metadata,
        }


class IncrementalUpdater:
    """
    Main class for incremental knowledge graph updates.

    Coordinates data listening, extraction, and graph updates
    with version control.
    """

    def __init__(
        self,
        graph_db: Optional[GraphDatabase] = None,
        data_listener: Optional[DataListener] = None,
        version_manager: Optional[VersionManager] = None,
        strategy: UpdateStrategy = UpdateStrategy.BATCHED,
        batch_size: int = 50,
        batch_timeout: float = 30.0,
        extraction_mode: ExtractionMode = ExtractionMode.INCREMENTAL,
        min_confidence: float = 0.5,
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize IncrementalUpdater.

        Args:
            graph_db: Graph database instance
            data_listener: Data listener instance
            version_manager: Version manager instance
            strategy: Update strategy
            batch_size: Maximum events per batch
            batch_timeout: Maximum batch wait time (seconds)
            extraction_mode: Entity extraction mode
            min_confidence: Minimum confidence for extractions
            tenant_id: Tenant ID filter
        """
        self.graph_db = graph_db
        self.data_listener = data_listener
        self.version_manager = version_manager
        self.strategy = strategy
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.extraction_mode = extraction_mode
        self.min_confidence = min_confidence
        self.tenant_id = tenant_id

        self._running = False
        self._event_buffer: List[DataChangeEvent] = []
        self._last_batch_time = datetime.now()
        self._batch_task: Optional[asyncio.Task] = None
        self._entity_extractor = None
        self._relation_extractor = None

        # Statistics
        self._stats = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "total_events": 0,
            "total_entities_created": 0,
            "total_relations_created": 0,
            "start_time": None,
            "last_update_time": None,
        }

    async def initialize(self) -> None:
        """Initialize all components."""
        # Initialize graph database
        if not self.graph_db:
            self.graph_db = get_graph_database()
            await self.graph_db.initialize()

        # Initialize version manager
        if not self.version_manager:
            self.version_manager = get_version_manager()

        # Initialize data listener
        if not self.data_listener:
            self.data_listener = DataListener(
                batch_size=self.batch_size,
                batch_timeout=self.batch_timeout,
                tenant_id=self.tenant_id,
            )

        # Initialize extractors
        await self._initialize_extractors()

        # Register event handler
        self.data_listener.register_handler(self._handle_event)

        logger.info("IncrementalUpdater initialized")

    async def _initialize_extractors(self) -> None:
        """Initialize entity and relation extractors."""
        try:
            from ..nlp.entity_extractor import EntityExtractor
            from ..nlp.relation_extractor import RelationExtractor

            self._entity_extractor = EntityExtractor()
            self._relation_extractor = RelationExtractor()
            logger.info("NLP extractors initialized")
        except ImportError as e:
            logger.warning(f"Could not initialize NLP extractors: {e}")

    async def start(self) -> None:
        """Start the incremental updater."""
        if self._running:
            logger.warning("IncrementalUpdater is already running")
            return

        await self.initialize()

        self._running = True
        self._stats["start_time"] = datetime.now()

        # Start data listener
        await self.data_listener.start()

        # Start batch processing if using batched strategy
        if self.strategy == UpdateStrategy.BATCHED:
            self._batch_task = asyncio.create_task(self._batch_process_loop())

        logger.info(f"IncrementalUpdater started with strategy: {self.strategy.value}")

    async def stop(self) -> None:
        """Stop the incremental updater."""
        if not self._running:
            return

        self._running = False

        # Stop data listener
        if self.data_listener:
            await self.data_listener.stop()

        # Stop batch processing
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass

        # Process remaining events
        if self._event_buffer:
            await self._process_batch(self._event_buffer)
            self._event_buffer.clear()

        logger.info("IncrementalUpdater stopped")

    async def _handle_event(self, event: DataChangeEvent) -> None:
        """
        Handle a data change event.

        Args:
            event: The data change event
        """
        self._stats["total_events"] += 1

        if self.strategy == UpdateStrategy.IMMEDIATE:
            # Process immediately
            await self._process_event(event)
        elif self.strategy == UpdateStrategy.BATCHED:
            # Add to buffer
            self._event_buffer.append(event)

            # Check if we should flush
            if len(self._event_buffer) >= self.batch_size:
                batch = self._event_buffer.copy()
                self._event_buffer.clear()
                await self._process_batch(batch)
        elif self.strategy == UpdateStrategy.MANUAL:
            # Just buffer for later
            self._event_buffer.append(event)

    async def _batch_process_loop(self) -> None:
        """Background task for periodic batch processing."""
        while self._running:
            try:
                await asyncio.sleep(self.batch_timeout)

                if self._event_buffer:
                    batch = self._event_buffer.copy()
                    self._event_buffer.clear()
                    await self._process_batch(batch)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch process loop: {e}")

    async def _process_batch(self, events: List[DataChangeEvent]) -> UpdateResult:
        """
        Process a batch of events.

        Args:
            events: List of events to process

        Returns:
            Update result
        """
        result = UpdateResult()
        result.metadata["batch_size"] = len(events)

        try:
            for event in events:
                try:
                    event_result = await self._process_event(event)
                    result.events_processed += 1
                    result.entities_created += event_result.get("entities_created", 0)
                    result.entities_updated += event_result.get("entities_updated", 0)
                    result.entities_deleted += event_result.get("entities_deleted", 0)
                    result.relations_created += event_result.get("relations_created", 0)
                    result.relations_updated += event_result.get("relations_updated", 0)
                    result.relations_deleted += event_result.get("relations_deleted", 0)
                except Exception as e:
                    result.add_error(f"Error processing event {event.id}: {str(e)}")

            # Create version if there were changes
            if result.total_changes > 0 and self.version_manager:
                version = await self.version_manager.create_version(
                    name=f"Batch update ({result.total_changes} changes)",
                    description=f"Processed {result.events_processed} events",
                )
                result.version_id = version.id

            self._stats["total_updates"] += 1
            if result.success:
                self._stats["successful_updates"] += 1
            else:
                self._stats["failed_updates"] += 1
            self._stats["last_update_time"] = datetime.now()

        except Exception as e:
            result.add_error(f"Batch processing error: {str(e)}")
            logger.error(f"Batch processing error: {e}")

        result.mark_completed()
        logger.info(f"Batch processed: {result.events_processed} events, {result.total_changes} changes")
        return result

    async def _process_event(self, event: DataChangeEvent) -> Dict[str, int]:
        """
        Process a single data change event.

        Args:
            event: The event to process

        Returns:
            Dictionary with change counts
        """
        result = {
            "entities_created": 0,
            "entities_updated": 0,
            "entities_deleted": 0,
            "relations_created": 0,
            "relations_updated": 0,
            "relations_deleted": 0,
        }

        if event.change_type == ChangeType.DELETE:
            # Handle deletion
            await self._handle_deletion(event, result)
        elif event.change_type in (ChangeType.CREATE, ChangeType.UPDATE):
            # Handle creation or update
            await self._handle_upsert(event, result)
        elif event.change_type in (ChangeType.BULK_CREATE, ChangeType.BULK_UPDATE):
            # Handle bulk operations
            for entity_id in event.entity_ids:
                sub_event = DataChangeEvent(
                    source=event.source,
                    change_type=ChangeType.CREATE if "CREATE" in event.change_type.value else ChangeType.UPDATE,
                    entity_id=entity_id,
                    new_data=event.new_data,
                    tenant_id=event.tenant_id,
                )
                sub_result = await self._process_event(sub_event)
                for key in result:
                    result[key] += sub_result.get(key, 0)

        return result

    async def _handle_deletion(
        self,
        event: DataChangeEvent,
        result: Dict[str, int],
    ) -> None:
        """Handle a deletion event."""
        if not self.graph_db:
            return

        # Find entities related to this data
        entities_to_delete = await self._find_related_entities(event)

        for entity in entities_to_delete:
            try:
                # Delete entity
                deleted = await self.graph_db.delete_entity(entity.id, hard_delete=False)
                if deleted:
                    result["entities_deleted"] += 1

                    # Record change
                    if self.version_manager:
                        await self.version_manager.record_change(
                            operation=ChangeOperationType.DELETE_ENTITY,
                            entity_id=entity.id,
                            old_data=entity.to_neo4j_properties(),
                            source=event.source.value,
                            tenant_id=event.tenant_id,
                        )
            except Exception as e:
                logger.error(f"Error deleting entity {entity.id}: {e}")

    async def _handle_upsert(
        self,
        event: DataChangeEvent,
        result: Dict[str, int],
    ) -> None:
        """Handle a create or update event."""
        if not self.graph_db:
            return

        # Extract text content from event data
        text_content = self._extract_text_content(event)
        if not text_content:
            return

        # Extract entities and relations
        extracted_entities, extracted_relations = await self._extract_from_text(text_content)

        # Process extracted entities
        for ext_entity in extracted_entities:
            try:
                # Check if entity already exists
                existing = await self._find_existing_entity(ext_entity)

                if existing:
                    # Update existing entity
                    updates = {
                        "updated_at": datetime.now().isoformat(),
                        "source": event.source.value,
                    }
                    if ext_entity.confidence > existing.confidence:
                        updates["confidence"] = ext_entity.confidence

                    updated = await self.graph_db.update_entity(existing.id, updates)
                    if updated:
                        result["entities_updated"] += 1

                        # Record change
                        if self.version_manager:
                            await self.version_manager.record_change(
                                operation=ChangeOperationType.UPDATE_ENTITY,
                                entity_id=existing.id,
                                old_data=existing.to_neo4j_properties(),
                                new_data=updated.to_neo4j_properties(),
                                source=event.source.value,
                                tenant_id=event.tenant_id,
                            )
                else:
                    # Create new entity
                    entity = ext_entity.to_entity(source=event.source.value)
                    entity.tenant_id = event.tenant_id

                    created = await self.graph_db.create_entity(entity)
                    if created:
                        result["entities_created"] += 1
                        self._stats["total_entities_created"] += 1

                        # Record change
                        if self.version_manager:
                            await self.version_manager.record_change(
                                operation=ChangeOperationType.CREATE_ENTITY,
                                entity_id=entity.id,
                                new_data=entity.to_neo4j_properties(),
                                source=event.source.value,
                                tenant_id=event.tenant_id,
                            )
            except Exception as e:
                logger.error(f"Error processing entity {ext_entity.text}: {e}")

        # Process extracted relations
        for ext_relation in extracted_relations:
            try:
                # Find source and target entities
                source_entity = await self._find_existing_entity(ext_relation.source_entity)
                target_entity = await self._find_existing_entity(ext_relation.target_entity)

                if source_entity and target_entity:
                    # Create relation
                    relation = ext_relation.to_relation(
                        source_id=source_entity.id,
                        target_id=target_entity.id,
                        source=event.source.value,
                    )
                    relation.tenant_id = event.tenant_id

                    created = await self.graph_db.create_relation(relation)
                    if created:
                        result["relations_created"] += 1
                        self._stats["total_relations_created"] += 1

                        # Record change
                        if self.version_manager:
                            await self.version_manager.record_change(
                                operation=ChangeOperationType.CREATE_RELATION,
                                relation_id=relation.id,
                                new_data=relation.to_neo4j_properties(),
                                source=event.source.value,
                                tenant_id=event.tenant_id,
                            )
            except Exception as e:
                logger.error(f"Error processing relation: {e}")

    async def _find_related_entities(self, event: DataChangeEvent) -> List[Entity]:
        """Find entities related to a data change event."""
        if not self.graph_db:
            return []

        entities = []

        # Search by source ID
        if event.entity_id:
            results = await self.graph_db.search_entities(
                query_text=event.entity_id,
                tenant_id=event.tenant_id,
                limit=100,
            )
            entities.extend(results)

        return entities

    async def _find_existing_entity(self, ext_entity) -> Optional[Entity]:
        """Find an existing entity matching an extracted entity."""
        if not self.graph_db:
            return None

        # Search by name
        results = await self.graph_db.search_entities(
            query_text=ext_entity.normalized_name or ext_entity.text,
            entity_type=ext_entity.entity_type,
            tenant_id=self.tenant_id,
            limit=10,
        )

        # Find best match
        for entity in results:
            if self._is_entity_match(entity, ext_entity):
                return entity

        return None

    def _is_entity_match(self, entity: Entity, ext_entity) -> bool:
        """Check if an entity matches an extracted entity."""
        # Check name match
        name = ext_entity.normalized_name or ext_entity.text
        if entity.name.lower() == name.lower():
            return True

        # Check aliases
        if name.lower() in [a.lower() for a in entity.aliases]:
            return True

        return False

    def _extract_text_content(self, event: DataChangeEvent) -> Optional[str]:
        """Extract text content from event data."""
        if not event.new_data:
            return None

        # Try various content fields
        content_fields = ["content", "text", "annotation_data", "body", "description"]

        for field in content_fields:
            if field in event.new_data:
                value = event.new_data[field]
                if isinstance(value, str):
                    return value
                elif isinstance(value, dict):
                    # Try to extract text from nested structure
                    return self._extract_nested_text(value)

        return None

    def _extract_nested_text(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract text from nested data structure."""
        texts = []

        for key, value in data.items():
            if isinstance(value, str) and len(value) > 10:
                texts.append(value)
            elif isinstance(value, dict):
                nested = self._extract_nested_text(value)
                if nested:
                    texts.append(nested)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        texts.append(item)
                    elif isinstance(item, dict):
                        nested = self._extract_nested_text(item)
                        if nested:
                            texts.append(nested)

        return " ".join(texts) if texts else None

    async def _extract_from_text(self, text: str) -> Tuple[List, List]:
        """Extract entities and relations from text."""
        entities = []
        relations = []

        if self._entity_extractor:
            try:
                entities = await asyncio.to_thread(
                    self._entity_extractor.extract,
                    text,
                    min_confidence=self.min_confidence,
                )
            except Exception as e:
                logger.error(f"Entity extraction error: {e}")

        if self._relation_extractor and entities:
            try:
                relations = await asyncio.to_thread(
                    self._relation_extractor.extract,
                    text,
                    entities=entities,
                    min_confidence=self.min_confidence,
                )
            except Exception as e:
                logger.error(f"Relation extraction error: {e}")

        return entities, relations

    async def trigger_update(
        self,
        source: Optional[DataSource] = None,
        entity_ids: Optional[List[str]] = None,
    ) -> UpdateResult:
        """
        Manually trigger an update.

        Args:
            source: Filter by data source
            entity_ids: Specific entity IDs to update

        Returns:
            Update result
        """
        # Get pending events
        if self.strategy == UpdateStrategy.MANUAL and self._event_buffer:
            events = self._event_buffer.copy()
            self._event_buffer.clear()
        else:
            events = []

        # Filter by source if specified
        if source:
            events = [e for e in events if e.source == source]

        # Filter by entity IDs if specified
        if entity_ids:
            events = [e for e in events if e.entity_id in entity_ids]

        return await self._process_batch(events)

    async def full_resync(
        self,
        source: Optional[DataSource] = None,
        tenant_id: Optional[str] = None,
    ) -> UpdateResult:
        """
        Perform a full resynchronization.

        This rebuilds the knowledge graph from source data.

        Args:
            source: Filter by data source
            tenant_id: Filter by tenant

        Returns:
            Update result
        """
        result = UpdateResult()
        result.metadata["operation"] = "full_resync"
        result.metadata["source"] = source.value if source else "all"

        # This would need to be implemented based on specific data sources
        # For now, just process all buffered events
        if self._event_buffer:
            batch_result = await self._process_batch(self._event_buffer.copy())
            self._event_buffer.clear()

            result.events_processed = batch_result.events_processed
            result.entities_created = batch_result.entities_created
            result.entities_updated = batch_result.entities_updated
            result.relations_created = batch_result.relations_created
            result.errors.extend(batch_result.errors)

        result.mark_completed()
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get updater statistics."""
        listener_stats = self.data_listener.get_stats() if self.data_listener else {}
        version_stats = self.version_manager.get_stats() if self.version_manager else {}

        return {
            **self._stats,
            "strategy": self.strategy.value,
            "extraction_mode": self.extraction_mode.value,
            "buffer_size": len(self._event_buffer),
            "is_running": self._running,
            "listener": listener_stats,
            "version_manager": version_stats,
        }


# Global instance
_incremental_updater: Optional[IncrementalUpdater] = None


async def get_incremental_updater() -> IncrementalUpdater:
    """Get or create global IncrementalUpdater instance."""
    global _incremental_updater
    if _incremental_updater is None:
        _incremental_updater = IncrementalUpdater()
        await _incremental_updater.initialize()
    return _incremental_updater
