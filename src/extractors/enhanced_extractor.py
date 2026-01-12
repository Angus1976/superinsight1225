"""
Enhanced Data Extractor for SuperInsight Platform.

Provides multi-source parallel data extraction with advanced features:
- Parallel extraction from multiple sources
- Connection pooling and retry mechanisms
- Schema discovery and mapping
- Data standardization and merging
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Union
import hashlib
import json

from src.extractors.base import (
    BaseExtractor,
    ExtractionResult,
    DatabaseConfig,
    APIConfig,
    FileConfig,
    SourceType,
)
from src.models.document import Document

logger = logging.getLogger(__name__)


class ExtractorType(str, Enum):
    """Supported extractor types."""
    DATABASE = "database"
    API = "api"
    FILE = "file"
    STREAM = "stream"
    CLOUD_STORAGE = "cloud_storage"
    MESSAGE_QUEUE = "message_queue"


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""
    id: str
    name: str
    type: ExtractorType
    enabled: bool = True
    priority: int = 0
    
    # Connection settings
    connection_config: Dict[str, Any] = field(default_factory=dict)
    
    # Extraction settings
    batch_size: int = 1000
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout_seconds: int = 300
    
    # Schema settings
    schema_mapping: Optional[Dict[str, str]] = None
    include_fields: Optional[List[str]] = None
    exclude_fields: Optional[List[str]] = None
    
    # Incremental settings
    incremental_field: Optional[str] = None
    incremental_value: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionBatch:
    """A batch of extracted data."""
    batch_id: str
    source_id: str
    records: List[Dict[str, Any]]
    schema: Optional[Dict[str, Any]] = None
    total_count: int = 0
    offset: int = 0
    has_more: bool = False
    checkpoint: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not self.batch_id:
            import uuid
            self.batch_id = str(uuid.uuid4())
        if self.total_count == 0:
            self.total_count = len(self.records)


@dataclass
class MultiSourceExtractionResult:
    """Result of multi-source extraction."""
    success: bool
    sources_processed: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    total_records: int = 0
    batches: List[ExtractionBatch] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedDataExtractor:
    """
    Enhanced data extractor with multi-source parallel extraction.
    
    Features:
    - Parallel extraction from multiple sources
    - Connection pooling and retry mechanisms
    - Schema discovery and automatic mapping
    - Data standardization and merging
    - Incremental extraction support
    """
    
    def __init__(self, max_parallel: int = 5):
        """
        Initialize enhanced extractor.
        
        Args:
            max_parallel: Maximum parallel extractions
        """
        self.max_parallel = max_parallel
        self._sources: Dict[str, DataSourceConfig] = {}
        self._extractors: Dict[str, BaseExtractor] = {}
        self._semaphore = asyncio.Semaphore(max_parallel)
        self._stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_records": 0,
            "total_bytes": 0
        }
    
    def register_source(self, config: DataSourceConfig) -> None:
        """Register a data source."""
        self._sources[config.id] = config
        logger.info(f"Registered data source: {config.id} ({config.type.value})")
    
    def unregister_source(self, source_id: str) -> bool:
        """Unregister a data source."""
        if source_id in self._sources:
            del self._sources[source_id]
            if source_id in self._extractors:
                del self._extractors[source_id]
            return True
        return False
    
    def get_source(self, source_id: str) -> Optional[DataSourceConfig]:
        """Get source configuration."""
        return self._sources.get(source_id)
    
    def list_sources(self) -> List[DataSourceConfig]:
        """List all registered sources."""
        return list(self._sources.values())
    
    async def extract_from_source(
        self,
        source_id: str,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> ExtractionBatch:
        """
        Extract data from a single source.
        
        Args:
            source_id: Source identifier
            query: Optional query string
            filters: Optional filters
            limit: Maximum records
            offset: Offset for pagination
            
        Returns:
            ExtractionBatch with extracted data
        """
        source = self._sources.get(source_id)
        if not source:
            raise ValueError(f"Source not found: {source_id}")
        
        if not source.enabled:
            raise ValueError(f"Source is disabled: {source_id}")
        
        async with self._semaphore:
            return await self._extract_with_retry(
                source, query, filters, limit, offset
            )
    
    async def extract_from_multiple_sources(
        self,
        source_ids: Optional[List[str]] = None,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        merge_results: bool = True
    ) -> MultiSourceExtractionResult:
        """
        Extract data from multiple sources in parallel.
        
        Args:
            source_ids: List of source IDs (None = all enabled sources)
            query: Optional query string
            filters: Optional filters
            limit: Maximum records per source
            merge_results: Whether to merge results
            
        Returns:
            MultiSourceExtractionResult with all extracted data
        """
        import time
        start_time = time.time()
        
        # Get sources to extract from
        if source_ids:
            sources = [
                self._sources[sid] for sid in source_ids
                if sid in self._sources and self._sources[sid].enabled
            ]
        else:
            sources = [s for s in self._sources.values() if s.enabled]
        
        # Sort by priority
        sources.sort(key=lambda s: s.priority, reverse=True)
        
        result = MultiSourceExtractionResult(
            success=True,
            sources_processed=len(sources)
        )
        
        # Create extraction tasks
        tasks = []
        for source in sources:
            task = asyncio.create_task(
                self._safe_extract(source, query, filters, limit)
            )
            tasks.append((source.id, task))
        
        # Wait for all tasks
        for source_id, task in tasks:
            try:
                batch = await task
                result.batches.append(batch)
                result.sources_succeeded += 1
                result.total_records += len(batch.records)
            except Exception as e:
                result.sources_failed += 1
                result.errors.append({
                    "source_id": source_id,
                    "error": str(e),
                    "type": type(e).__name__
                })
                logger.error(f"Extraction failed for {source_id}: {e}")
        
        # Merge results if requested
        if merge_results and len(result.batches) > 1:
            result.batches = [self._merge_batches(result.batches)]
        
        result.success = result.sources_failed == 0
        result.duration_seconds = time.time() - start_time
        
        # Update stats
        self._stats["total_extractions"] += result.sources_processed
        self._stats["successful_extractions"] += result.sources_succeeded
        self._stats["failed_extractions"] += result.sources_failed
        self._stats["total_records"] += result.total_records
        
        return result
    
    async def stream_from_source(
        self,
        source_id: str,
        batch_size: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[ExtractionBatch]:
        """
        Stream data from a source in batches.
        
        Args:
            source_id: Source identifier
            batch_size: Records per batch
            filters: Optional filters
            
        Yields:
            ExtractionBatch objects
        """
        source = self._sources.get(source_id)
        if not source:
            raise ValueError(f"Source not found: {source_id}")
        
        batch_size = batch_size or source.batch_size
        offset = 0
        has_more = True
        
        while has_more:
            batch = await self.extract_from_source(
                source_id,
                filters=filters,
                limit=batch_size,
                offset=offset
            )
            
            yield batch
            
            has_more = batch.has_more
            offset += len(batch.records)
            
            # Small delay to prevent overwhelming the source
            await asyncio.sleep(0.01)
    
    async def discover_schema(self, source_id: str) -> Dict[str, Any]:
        """
        Discover schema from a data source.
        
        Args:
            source_id: Source identifier
            
        Returns:
            Schema information dictionary
        """
        source = self._sources.get(source_id)
        if not source:
            raise ValueError(f"Source not found: {source_id}")
        
        # Extract sample data
        batch = await self.extract_from_source(source_id, limit=100)
        
        if not batch.records:
            return {"fields": [], "sample_count": 0}
        
        # Analyze schema from records
        schema = self._analyze_schema(batch.records)
        schema["source_id"] = source_id
        schema["sample_count"] = len(batch.records)
        schema["discovered_at"] = datetime.utcnow().isoformat()
        
        return schema
    
    async def test_source_connection(self, source_id: str) -> Dict[str, Any]:
        """
        Test connection to a data source.
        
        Args:
            source_id: Source identifier
            
        Returns:
            Connection test results
        """
        import time
        start_time = time.time()
        
        result = {
            "source_id": source_id,
            "success": False,
            "latency_ms": 0,
            "error": None,
            "details": {}
        }
        
        try:
            source = self._sources.get(source_id)
            if not source:
                result["error"] = f"Source not found: {source_id}"
                return result
            
            # Try to extract a small sample
            batch = await self.extract_from_source(source_id, limit=1)
            
            result["success"] = True
            result["details"] = {
                "type": source.type.value,
                "records_available": batch.total_count,
                "schema_discovered": batch.schema is not None
            }
            
        except Exception as e:
            result["error"] = str(e)
        
        result["latency_ms"] = (time.time() - start_time) * 1000
        return result
    
    async def _safe_extract(
        self,
        source: DataSourceConfig,
        query: Optional[str],
        filters: Optional[Dict[str, Any]],
        limit: Optional[int]
    ) -> ExtractionBatch:
        """Safely extract with error handling."""
        async with self._semaphore:
            return await self._extract_with_retry(
                source, query, filters, limit, 0
            )
    
    async def _extract_with_retry(
        self,
        source: DataSourceConfig,
        query: Optional[str],
        filters: Optional[Dict[str, Any]],
        limit: Optional[int],
        offset: int
    ) -> ExtractionBatch:
        """Extract with retry logic."""
        last_error = None
        
        for attempt in range(source.max_retries + 1):
            try:
                return await self._do_extract(
                    source, query, filters, limit, offset
                )
            except Exception as e:
                last_error = e
                if attempt < source.max_retries:
                    delay = source.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Extraction attempt {attempt + 1} failed for {source.id}, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
        
        raise last_error
    
    async def _do_extract(
        self,
        source: DataSourceConfig,
        query: Optional[str],
        filters: Optional[Dict[str, Any]],
        limit: Optional[int],
        offset: int
    ) -> ExtractionBatch:
        """Perform actual extraction."""
        import uuid
        
        batch_size = limit or source.batch_size
        
        # Simulate extraction based on source type
        # In production, this would use actual connectors
        records = []
        
        if source.type == ExtractorType.DATABASE:
            records = await self._extract_from_database(source, query, filters, batch_size, offset)
        elif source.type == ExtractorType.API:
            records = await self._extract_from_api(source, query, filters, batch_size, offset)
        elif source.type == ExtractorType.FILE:
            records = await self._extract_from_file(source, filters, batch_size, offset)
        elif source.type == ExtractorType.CLOUD_STORAGE:
            records = await self._extract_from_cloud_storage(source, filters, batch_size, offset)
        elif source.type == ExtractorType.MESSAGE_QUEUE:
            records = await self._extract_from_message_queue(source, batch_size)
        else:
            raise ValueError(f"Unsupported source type: {source.type}")
        
        # Apply field filtering
        if source.include_fields or source.exclude_fields:
            records = self._filter_fields(records, source.include_fields, source.exclude_fields)
        
        # Apply schema mapping
        if source.schema_mapping:
            records = self._apply_schema_mapping(records, source.schema_mapping)
        
        # Discover schema from records
        schema = self._analyze_schema(records) if records else None
        
        return ExtractionBatch(
            batch_id=str(uuid.uuid4()),
            source_id=source.id,
            records=records,
            schema=schema,
            total_count=len(records) + offset,  # Simplified
            offset=offset,
            has_more=len(records) >= batch_size,
            checkpoint={
                "offset": offset + len(records),
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata={
                "source_type": source.type.value,
                "query": query,
                "filters": filters
            }
        )
    
    async def _extract_from_database(
        self,
        source: DataSourceConfig,
        query: Optional[str],
        filters: Optional[Dict[str, Any]],
        limit: int,
        offset: int
    ) -> List[Dict[str, Any]]:
        """Extract from database source."""
        # In production, use actual database connector
        # This is a simulation
        records = []
        for i in range(min(limit, 100)):
            records.append({
                "id": f"db_{source.id}_{offset + i}",
                "content": f"Database record {offset + i}",
                "source": source.id,
                "extracted_at": datetime.utcnow().isoformat()
            })
        return records
    
    async def _extract_from_api(
        self,
        source: DataSourceConfig,
        query: Optional[str],
        filters: Optional[Dict[str, Any]],
        limit: int,
        offset: int
    ) -> List[Dict[str, Any]]:
        """Extract from API source."""
        # In production, use actual API connector
        records = []
        for i in range(min(limit, 100)):
            records.append({
                "id": f"api_{source.id}_{offset + i}",
                "data": f"API response {offset + i}",
                "source": source.id,
                "extracted_at": datetime.utcnow().isoformat()
            })
        return records
    
    async def _extract_from_file(
        self,
        source: DataSourceConfig,
        filters: Optional[Dict[str, Any]],
        limit: int,
        offset: int
    ) -> List[Dict[str, Any]]:
        """Extract from file source."""
        records = []
        for i in range(min(limit, 100)):
            records.append({
                "id": f"file_{source.id}_{offset + i}",
                "content": f"File content {offset + i}",
                "source": source.id,
                "extracted_at": datetime.utcnow().isoformat()
            })
        return records
    
    async def _extract_from_cloud_storage(
        self,
        source: DataSourceConfig,
        filters: Optional[Dict[str, Any]],
        limit: int,
        offset: int
    ) -> List[Dict[str, Any]]:
        """Extract from cloud storage source."""
        records = []
        for i in range(min(limit, 100)):
            records.append({
                "id": f"cloud_{source.id}_{offset + i}",
                "object_key": f"objects/{offset + i}.json",
                "source": source.id,
                "extracted_at": datetime.utcnow().isoformat()
            })
        return records
    
    async def _extract_from_message_queue(
        self,
        source: DataSourceConfig,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Extract from message queue source."""
        records = []
        for i in range(min(limit, 100)):
            records.append({
                "id": f"mq_{source.id}_{i}",
                "message": f"Queue message {i}",
                "source": source.id,
                "extracted_at": datetime.utcnow().isoformat()
            })
        return records
    
    def _filter_fields(
        self,
        records: List[Dict[str, Any]],
        include_fields: Optional[List[str]],
        exclude_fields: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Filter record fields."""
        filtered = []
        for record in records:
            if include_fields:
                new_record = {k: v for k, v in record.items() if k in include_fields}
            elif exclude_fields:
                new_record = {k: v for k, v in record.items() if k not in exclude_fields}
            else:
                new_record = record
            filtered.append(new_record)
        return filtered
    
    def _apply_schema_mapping(
        self,
        records: List[Dict[str, Any]],
        mapping: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Apply schema mapping to records."""
        mapped = []
        for record in records:
            new_record = {}
            for old_key, new_key in mapping.items():
                if old_key in record:
                    new_record[new_key] = record[old_key]
            # Keep unmapped fields
            for key, value in record.items():
                if key not in mapping:
                    new_record[key] = value
            mapped.append(new_record)
        return mapped
    
    def _analyze_schema(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze schema from records."""
        if not records:
            return {"fields": []}
        
        field_info = {}
        
        for record in records:
            for key, value in record.items():
                if key not in field_info:
                    field_info[key] = {
                        "name": key,
                        "types": set(),
                        "nullable": False,
                        "sample_values": []
                    }
                
                if value is None:
                    field_info[key]["nullable"] = True
                else:
                    field_info[key]["types"].add(type(value).__name__)
                    if len(field_info[key]["sample_values"]) < 3:
                        field_info[key]["sample_values"].append(str(value)[:100])
        
        # Convert to list format
        fields = []
        for name, info in field_info.items():
            fields.append({
                "name": name,
                "type": list(info["types"])[0] if len(info["types"]) == 1 else "mixed",
                "nullable": info["nullable"],
                "sample_values": info["sample_values"]
            })
        
        return {"fields": fields}
    
    def _merge_batches(self, batches: List[ExtractionBatch]) -> ExtractionBatch:
        """Merge multiple batches into one."""
        import uuid
        
        all_records = []
        all_sources = []
        
        for batch in batches:
            all_records.extend(batch.records)
            all_sources.append(batch.source_id)
        
        # Merge schemas
        merged_schema = {"fields": []}
        seen_fields = set()
        for batch in batches:
            if batch.schema and "fields" in batch.schema:
                for field in batch.schema["fields"]:
                    if field["name"] not in seen_fields:
                        merged_schema["fields"].append(field)
                        seen_fields.add(field["name"])
        
        return ExtractionBatch(
            batch_id=str(uuid.uuid4()),
            source_id=",".join(all_sources),
            records=all_records,
            schema=merged_schema,
            total_count=len(all_records),
            metadata={
                "merged_from": all_sources,
                "batch_count": len(batches)
            }
        )
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        return {
            **self._stats,
            "registered_sources": len(self._sources),
            "enabled_sources": len([s for s in self._sources.values() if s.enabled])
        }


# Global enhanced extractor instance
enhanced_extractor = EnhancedDataExtractor()


__all__ = [
    "EnhancedDataExtractor",
    "DataSourceConfig",
    "ExtractionBatch",
    "MultiSourceExtractionResult",
    "ExtractorType",
    "enhanced_extractor",
]
