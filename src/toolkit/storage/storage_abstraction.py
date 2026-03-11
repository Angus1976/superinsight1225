"""
StorageAbstraction — unified interface for intelligent storage selection,
data storage/retrieval, lineage tracking, and local cache fallback.
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.toolkit.models.data_profile import DataProfile
from src.toolkit.models.enums import DataStructure
from src.toolkit.models.processing_plan import Requirements, StorageType

from .adapters import (
    DocumentDBAdapter,
    GraphDBAdapter,
    PostgreSQLAdapter,
    TimeSeriesAdapter,
    VectorDBAdapter,
)
from .base import QueryResult, StorageAdapter, StorageResult
from .lineage import LineageTracker


# Mapping from StorageType to adapter factory
_ADAPTER_FACTORIES = {
    StorageType.POSTGRESQL: PostgreSQLAdapter,
    StorageType.VECTOR_DB: VectorDBAdapter,
    StorageType.GRAPH_DB: GraphDBAdapter,
    StorageType.DOCUMENT_DB: DocumentDBAdapter,
    StorageType.TIME_SERIES_DB: TimeSeriesAdapter,
}


class StorageAbstraction:
    """
    Unified storage layer with intelligent backend selection,
    lineage tracking, and local cache fallback on failure.
    """

    def __init__(self) -> None:
        self._adapters: Dict[StorageType, StorageAdapter] = {}
        self._lineage = LineageTracker()
        self._local_cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Adapter management
    # ------------------------------------------------------------------

    def get_adapter(self, storage_type: StorageType) -> StorageAdapter:
        """Return (or lazily create) the adapter for *storage_type*."""
        if storage_type not in self._adapters:
            factory = _ADAPTER_FACTORIES.get(storage_type)
            if factory is None:
                raise ValueError(f"Unsupported storage type: {storage_type}")
            self._adapters[storage_type] = factory()
        return self._adapters[storage_type]

    # ------------------------------------------------------------------
    # Intelligent storage selection  (Req 4.1, 4.2, 4.3)
    # ------------------------------------------------------------------

    def select_storage(
        self,
        profile: DataProfile,
        requirements: Optional[Requirements] = None,
    ) -> StorageAdapter:
        """
        Score each backend and return the adapter with the highest score.

        Deterministic: same profile + requirements → same selection.
        """
        reqs = requirements or Requirements()
        scores = self._score_backends(profile, reqs)

        if not scores:
            return self.get_adapter(StorageType.POSTGRESQL)

        best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
        return self.get_adapter(best_type)

    def _score_backends(
        self, profile: DataProfile, reqs: Requirements,
    ) -> Dict[StorageType, float]:
        """Return a score map for each applicable backend."""
        scores: Dict[StorageType, float] = {}
        structure = profile.structure_info.data_structure
        has_schema = bool(profile.structure_info.column_schema)

        if structure == DataStructure.TABULAR and has_schema:
            scores[StorageType.POSTGRESQL] = 0.9

        if reqs.needs_semantic_search:
            scores[StorageType.VECTOR_DB] = 0.95

        has_relationships = bool(profile.structure_info.relationships)
        if structure == DataStructure.GRAPH or has_relationships or reqs.needs_graph_traversal:
            scores[StorageType.GRAPH_DB] = 0.9

        if structure == DataStructure.HIERARCHICAL or reqs.needs_flexible_schema:
            scores[StorageType.DOCUMENT_DB] = 0.85

        if structure == DataStructure.TIME_SERIES or reqs.needs_time_range_queries:
            scores[StorageType.TIME_SERIES_DB] = 0.95

        return scores

    # ------------------------------------------------------------------
    # Store / Retrieve  (Req 4.4, 4.6)
    # ------------------------------------------------------------------

    def store_data(
        self,
        data: Any,
        adapter: StorageAdapter,
        data_id: Optional[str] = None,
        source_label: str = "unknown",
        **kwargs: Any,
    ) -> StorageResult:
        """
        Store *data* via *adapter*. On failure, cache locally (Req 4.6).
        Also records lineage source + storage events.
        """
        did = data_id or str(uuid4())
        self._lineage.record_source(did, source_label)

        if not adapter.is_available():
            return self._cache_locally(did, data, adapter.storage_type)

        try:
            result = adapter.store(did, data, **kwargs)
        except Exception:
            return self._cache_locally(did, data, adapter.storage_type)

        self._lineage.record_storage(did, adapter.storage_type.value)
        return result

    def retrieve_data(
        self, data_id: str, adapter: StorageAdapter, **kwargs: Any,
    ) -> QueryResult:
        """Retrieve data by ID, falling back to local cache if needed."""
        if adapter.is_available():
            result = adapter.retrieve(data_id, **kwargs)
            if result.success:
                return result

        cached = self._local_cache.get(data_id)
        if cached is not None:
            return QueryResult(
                success=True,
                data=cached["data"],
                record_count=1,
                metadata={"from_cache": True},
            )
        return QueryResult(success=False)

    # ------------------------------------------------------------------
    # Lineage  (Req 4.5)
    # ------------------------------------------------------------------

    def record_transformation(
        self, data_id: str, stage_name: str, **meta: Any,
    ) -> None:
        """Record a transformation stage in the lineage chain."""
        self._lineage.record_transformation(data_id, stage_name, **meta)

    def track_lineage(self, data_id: str):
        """Return the full lineage graph for *data_id*."""
        return self._lineage.get_lineage(data_id)

    # ------------------------------------------------------------------
    # Local cache fallback  (Req 4.6)
    # ------------------------------------------------------------------

    def _cache_locally(
        self, data_id: str, data: Any, storage_type: StorageType,
    ) -> StorageResult:
        """Cache data locally when the primary storage is unavailable."""
        self._local_cache[data_id] = {
            "data": data,
            "target_storage": storage_type,
        }
        return StorageResult(
            success=True,
            data_id=data_id,
            storage_type=storage_type,
            metadata={"cached_locally": True},
        )

    def sync_cached_data(self) -> List[str]:
        """
        Attempt to flush locally cached items to their target storage.
        Returns list of data IDs that were successfully synced.
        """
        synced: List[str] = []
        for data_id, entry in list(self._local_cache.items()):
            adapter = self.get_adapter(entry["target_storage"])
            if not adapter.is_available():
                continue
            try:
                adapter.store(data_id, entry["data"])
                self._lineage.record_storage(data_id, adapter.storage_type.value)
                del self._local_cache[data_id]
                synced.append(data_id)
            except Exception:
                continue
        return synced

    @property
    def cached_count(self) -> int:
        return len(self._local_cache)
