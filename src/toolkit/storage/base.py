"""
Base storage adapter interface.

Defines the abstract StorageAdapter and result types used by all
concrete storage backend implementations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.toolkit.models.processing_plan import StorageType


class StorageResult(BaseModel):
    """Result of a store operation."""

    success: bool = Field(..., description="Whether the store succeeded")
    data_id: str = Field(..., description="Unique ID for the stored data")
    storage_type: StorageType = Field(..., description="Backend that stored the data")
    stored_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryResult(BaseModel):
    """Result of a query/retrieve operation."""

    success: bool = Field(..., description="Whether the query succeeded")
    data: Any = Field(default=None, description="Retrieved data")
    record_count: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StorageAdapter(ABC):
    """Abstract base class for all storage backend adapters."""

    @property
    @abstractmethod
    def storage_type(self) -> StorageType:
        """Return the storage type this adapter handles."""

    @abstractmethod
    def store(self, data_id: str, data: Any, **kwargs: Any) -> StorageResult:
        """Store data and return a StorageResult."""

    @abstractmethod
    def retrieve(self, data_id: str, **kwargs: Any) -> QueryResult:
        """Retrieve data by its ID."""

    @abstractmethod
    def query(self, query_params: Dict[str, Any]) -> QueryResult:
        """Execute a query against the storage backend."""

    @abstractmethod
    def delete(self, data_id: str) -> bool:
        """Delete data by its ID. Return True if deleted."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the storage backend is reachable."""
