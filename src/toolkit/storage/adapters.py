"""
Concrete in-memory storage adapter implementations.

Each adapter simulates a specific storage backend using in-memory
dictionaries, suitable for testing and development.
"""

from typing import Any, Dict, List

from src.toolkit.models.processing_plan import StorageType

from .base import QueryResult, StorageAdapter, StorageResult


class PostgreSQLAdapter(StorageAdapter):
    """In-memory adapter simulating PostgreSQL for structured tabular data."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
        self._available = True

    @property
    def storage_type(self) -> StorageType:
        return StorageType.POSTGRESQL

    def store(self, data_id: str, data: Any, **kwargs: Any) -> StorageResult:
        self._store[data_id] = data
        return StorageResult(
            success=True, data_id=data_id, storage_type=self.storage_type,
        )

    def retrieve(self, data_id: str, **kwargs: Any) -> QueryResult:
        if data_id not in self._store:
            return QueryResult(success=False)
        data = self._store[data_id]
        count = len(data) if isinstance(data, (list, dict)) else 1
        return QueryResult(success=True, data=data, record_count=count)

    def query(self, query_params: Dict[str, Any]) -> QueryResult:
        table = query_params.get("table", "")
        results = {k: v for k, v in self._store.items() if k.startswith(table)}
        return QueryResult(
            success=True, data=results, record_count=len(results),
        )

    def delete(self, data_id: str) -> bool:
        return self._store.pop(data_id, None) is not None

    def is_available(self) -> bool:
        return self._available


class VectorDBAdapter(StorageAdapter):
    """In-memory adapter simulating a vector database for embeddings."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._available = True

    @property
    def storage_type(self) -> StorageType:
        return StorageType.VECTOR_DB

    def store(self, data_id: str, data: Any, **kwargs: Any) -> StorageResult:
        metadata = kwargs.get("metadata", {})
        self._store[data_id] = {"embedding": data, "metadata": metadata}
        return StorageResult(
            success=True, data_id=data_id, storage_type=self.storage_type,
        )

    def retrieve(self, data_id: str, **kwargs: Any) -> QueryResult:
        if data_id not in self._store:
            return QueryResult(success=False)
        entry = self._store[data_id]
        return QueryResult(success=True, data=entry, record_count=1)

    def query(self, query_params: Dict[str, Any]) -> QueryResult:
        """Simulate similarity search — returns all stored entries."""
        top_k = query_params.get("top_k", 10)
        items = list(self._store.values())[:top_k]
        return QueryResult(success=True, data=items, record_count=len(items))

    def delete(self, data_id: str) -> bool:
        return self._store.pop(data_id, None) is not None

    def is_available(self) -> bool:
        return self._available


class GraphDBAdapter(StorageAdapter):
    """In-memory adapter simulating a graph database for relationships."""

    def __init__(self) -> None:
        self._nodes: Dict[str, Any] = {}
        self._edges: List[Dict[str, str]] = []
        self._available = True

    @property
    def storage_type(self) -> StorageType:
        return StorageType.GRAPH_DB

    def store(self, data_id: str, data: Any, **kwargs: Any) -> StorageResult:
        self._nodes[data_id] = data
        edges = kwargs.get("edges", [])
        self._edges.extend(edges)
        return StorageResult(
            success=True, data_id=data_id, storage_type=self.storage_type,
        )

    def retrieve(self, data_id: str, **kwargs: Any) -> QueryResult:
        if data_id not in self._nodes:
            return QueryResult(success=False)
        related = [e for e in self._edges if e.get("source") == data_id]
        data = {"node": self._nodes[data_id], "edges": related}
        return QueryResult(success=True, data=data, record_count=1)

    def query(self, query_params: Dict[str, Any]) -> QueryResult:
        start = query_params.get("start_node", "")
        if start not in self._nodes:
            return QueryResult(success=False)
        connected = [
            e for e in self._edges
            if e.get("source") == start or e.get("target") == start
        ]
        return QueryResult(
            success=True, data=connected, record_count=len(connected),
        )

    def delete(self, data_id: str) -> bool:
        if data_id not in self._nodes:
            return False
        del self._nodes[data_id]
        self._edges = [
            e for e in self._edges
            if e.get("source") != data_id and e.get("target") != data_id
        ]
        return True

    def is_available(self) -> bool:
        return self._available


class DocumentDBAdapter(StorageAdapter):
    """In-memory adapter simulating a document database (MongoDB-like)."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
        self._available = True

    @property
    def storage_type(self) -> StorageType:
        return StorageType.DOCUMENT_DB

    def store(self, data_id: str, data: Any, **kwargs: Any) -> StorageResult:
        self._store[data_id] = data
        return StorageResult(
            success=True, data_id=data_id, storage_type=self.storage_type,
        )

    def retrieve(self, data_id: str, **kwargs: Any) -> QueryResult:
        if data_id not in self._store:
            return QueryResult(success=False)
        return QueryResult(success=True, data=self._store[data_id], record_count=1)

    def query(self, query_params: Dict[str, Any]) -> QueryResult:
        """Simple field-match filter across stored documents."""
        field = query_params.get("field")
        value = query_params.get("value")
        if not field:
            items = list(self._store.values())
            return QueryResult(success=True, data=items, record_count=len(items))
        matches = [
            doc for doc in self._store.values()
            if isinstance(doc, dict) and doc.get(field) == value
        ]
        return QueryResult(success=True, data=matches, record_count=len(matches))

    def delete(self, data_id: str) -> bool:
        return self._store.pop(data_id, None) is not None

    def is_available(self) -> bool:
        return self._available


class TimeSeriesAdapter(StorageAdapter):
    """In-memory adapter simulating a time-series database."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
        self._available = True

    @property
    def storage_type(self) -> StorageType:
        return StorageType.TIME_SERIES_DB

    def store(self, data_id: str, data: Any, **kwargs: Any) -> StorageResult:
        self._store[data_id] = data
        return StorageResult(
            success=True, data_id=data_id, storage_type=self.storage_type,
        )

    def retrieve(self, data_id: str, **kwargs: Any) -> QueryResult:
        if data_id not in self._store:
            return QueryResult(success=False)
        data = self._store[data_id]
        count = len(data) if isinstance(data, list) else 1
        return QueryResult(success=True, data=data, record_count=count)

    def query(self, query_params: Dict[str, Any]) -> QueryResult:
        series_id = query_params.get("series_id", "")
        if series_id not in self._store:
            return QueryResult(success=False)
        return QueryResult(
            success=True, data=self._store[series_id], record_count=1,
        )

    def delete(self, data_id: str) -> bool:
        return self._store.pop(data_id, None) is not None

    def is_available(self) -> bool:
        return self._available
