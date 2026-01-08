"""
Change Detection and Comparison Engine.

Provides intelligent change detection, data comparison, and conflict resolution
for incremental synchronization with support for various comparison strategies.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from src.sync.connectors.base import DataRecord, OperationType

logger = logging.getLogger(__name__)


class ComparisonStrategy(str, Enum):
    """Data comparison strategies."""
    FULL_RECORD = "full_record"
    FIELD_LEVEL = "field_level"
    HASH_BASED = "hash_based"
    TIMESTAMP_BASED = "timestamp_based"
    VERSION_BASED = "version_based"
    CHECKSUM = "checksum"


class ChangeType(str, Enum):
    """Types of detected changes."""
    NEW_RECORD = "new_record"
    UPDATED_RECORD = "updated_record"
    DELETED_RECORD = "deleted_record"
    FIELD_CHANGE = "field_change"
    NO_CHANGE = "no_change"
    CONFLICT = "conflict"


class ConflictType(str, Enum):
    """Types of data conflicts."""
    CONCURRENT_UPDATE = "concurrent_update"
    DELETE_UPDATE = "delete_update"
    VERSION_MISMATCH = "version_mismatch"
    TIMESTAMP_CONFLICT = "timestamp_conflict"
    SCHEMA_MISMATCH = "schema_mismatch"


@dataclass
class FieldChange:
    """Represents a change to a specific field."""
    field_name: str
    old_value: Any
    new_value: Any
    change_type: str = "update"
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeDetectionResult:
    """Result of change detection analysis."""
    record_id: str
    change_type: ChangeType
    confidence: float
    field_changes: List[FieldChange] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComparisonResult:
    """Result of record comparison."""
    are_equal: bool
    similarity_score: float
    differences: List[FieldChange] = field(default_factory=list)
    hash_match: bool = False
    timestamp_comparison: Optional[str] = None  # "newer", "older", "same"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChangeDetectionConfig(BaseModel):
    """Configuration for change detection."""
    strategy: ComparisonStrategy = ComparisonStrategy.HASH_BASED
    
    # Field-level settings
    ignore_fields: List[str] = Field(default_factory=list)
    timestamp_fields: List[str] = Field(default_factory=lambda: ["updated_at", "modified_at"])
    version_fields: List[str] = Field(default_factory=lambda: ["version", "revision"])
    
    # Hash settings
    hash_algorithm: str = "sha256"
    hash_fields: List[str] = Field(default_factory=list)  # Empty = all fields
    
    # Comparison thresholds
    similarity_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    timestamp_tolerance_seconds: int = Field(default=1, ge=0)
    
    # Conflict detection
    enable_conflict_detection: bool = True
    conflict_resolution_strategy: str = "timestamp_priority"
    
    # Performance settings
    enable_caching: bool = True
    cache_size: int = Field(default=10000, ge=1)
    parallel_processing: bool = False
    max_workers: int = Field(default=4, ge=1)


class ChangeDetectionEngine:
    """
    Intelligent change detection and comparison engine.
    
    Features:
    - Multiple comparison strategies
    - Field-level change tracking
    - Conflict detection and resolution
    - Performance optimization with caching
    - Parallel processing support
    """

    def __init__(self, config: ChangeDetectionConfig):
        self.config = config
        self.engine_id = str(uuid4())
        
        # Caching
        self._hash_cache: Dict[str, str] = {}
        self._comparison_cache: Dict[str, ComparisonResult] = {}
        
        # Statistics
        self.stats = {
            "comparisons_performed": 0,
            "changes_detected": 0,
            "conflicts_detected": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }

    async def detect_changes(
        self,
        current_records: List[DataRecord],
        previous_records: Optional[List[DataRecord]] = None,
        baseline_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[ChangeDetectionResult]:
        """
        Detect changes in a set of records.
        
        Args:
            current_records: Current state of records
            previous_records: Previous state of records (optional)
            baseline_data: Baseline data for comparison (optional)
            
        Returns:
            List of change detection results
        """
        results = []
        
        # Create lookup for previous records
        previous_lookup = {}
        if previous_records:
            previous_lookup = {record.id: record for record in previous_records}
        
        # Process records
        if self.config.parallel_processing and len(current_records) > 100:
            results = await self._detect_changes_parallel(
                current_records, previous_lookup, baseline_data
            )
        else:
            results = await self._detect_changes_sequential(
                current_records, previous_lookup, baseline_data
            )
        
        # Update statistics
        self.stats["comparisons_performed"] += len(current_records)
        self.stats["changes_detected"] += len([r for r in results if r.change_type != ChangeType.NO_CHANGE])
        self.stats["conflicts_detected"] += len([r for r in results if r.conflicts])
        
        return results

    async def _detect_changes_sequential(
        self,
        current_records: List[DataRecord],
        previous_lookup: Dict[str, DataRecord],
        baseline_data: Optional[Dict[str, Dict[str, Any]]]
    ) -> List[ChangeDetectionResult]:
        """Detect changes sequentially."""
        results = []
        
        for record in current_records:
            result = await self._analyze_record_changes(
                record, previous_lookup.get(record.id), baseline_data
            )
            results.append(result)
        
        return results

    async def _detect_changes_parallel(
        self,
        current_records: List[DataRecord],
        previous_lookup: Dict[str, DataRecord],
        baseline_data: Optional[Dict[str, Dict[str, Any]]]
    ) -> List[ChangeDetectionResult]:
        """Detect changes in parallel."""
        semaphore = asyncio.Semaphore(self.config.max_workers)
        
        async def analyze_with_semaphore(record: DataRecord) -> ChangeDetectionResult:
            async with semaphore:
                return await self._analyze_record_changes(
                    record, previous_lookup.get(record.id), baseline_data
                )
        
        tasks = [analyze_with_semaphore(record) for record in current_records]
        results = await asyncio.gather(*tasks)
        
        return results

    async def _analyze_record_changes(
        self,
        current_record: DataRecord,
        previous_record: Optional[DataRecord],
        baseline_data: Optional[Dict[str, Dict[str, Any]]]
    ) -> ChangeDetectionResult:
        """Analyze changes for a single record."""
        if not previous_record:
            # New record
            return ChangeDetectionResult(
                record_id=current_record.id,
                change_type=ChangeType.NEW_RECORD,
                confidence=1.0,
                metadata={"operation": current_record.operation.value}
            )
        
        # Compare records
        comparison = await self.compare_records(current_record, previous_record)
        
        if comparison.are_equal:
            return ChangeDetectionResult(
                record_id=current_record.id,
                change_type=ChangeType.NO_CHANGE,
                confidence=comparison.similarity_score,
                metadata={"hash_match": comparison.hash_match}
            )
        
        # Detect conflicts
        conflicts = []
        if self.config.enable_conflict_detection:
            conflicts = await self._detect_conflicts(current_record, previous_record)
        
        # Determine change type
        change_type = ChangeType.UPDATED_RECORD
        if conflicts:
            change_type = ChangeType.CONFLICT
        
        return ChangeDetectionResult(
            record_id=current_record.id,
            change_type=change_type,
            confidence=comparison.similarity_score,
            field_changes=comparison.differences,
            conflicts=conflicts,
            metadata={
                "similarity_score": comparison.similarity_score,
                "hash_match": comparison.hash_match,
                "timestamp_comparison": comparison.timestamp_comparison
            }
        )

    async def compare_records(
        self,
        record1: DataRecord,
        record2: DataRecord
    ) -> ComparisonResult:
        """
        Compare two records and return detailed comparison result.
        
        Args:
            record1: First record
            record2: Second record
            
        Returns:
            ComparisonResult with detailed comparison information
        """
        # Check cache first
        cache_key = f"{record1.id}_{record2.id}_{record1.hash}_{record2.hash}"
        if self.config.enable_caching and cache_key in self._comparison_cache:
            self.stats["cache_hits"] += 1
            return self._comparison_cache[cache_key]
        
        self.stats["cache_misses"] += 1
        
        # Perform comparison based on strategy
        if self.config.strategy == ComparisonStrategy.HASH_BASED:
            result = await self._compare_hash_based(record1, record2)
        elif self.config.strategy == ComparisonStrategy.FIELD_LEVEL:
            result = await self._compare_field_level(record1, record2)
        elif self.config.strategy == ComparisonStrategy.TIMESTAMP_BASED:
            result = await self._compare_timestamp_based(record1, record2)
        elif self.config.strategy == ComparisonStrategy.VERSION_BASED:
            result = await self._compare_version_based(record1, record2)
        elif self.config.strategy == ComparisonStrategy.CHECKSUM:
            result = await self._compare_checksum_based(record1, record2)
        else:
            result = await self._compare_full_record(record1, record2)
        
        # Cache result
        if self.config.enable_caching:
            self._manage_cache()
            self._comparison_cache[cache_key] = result
        
        return result

    async def _compare_hash_based(
        self,
        record1: DataRecord,
        record2: DataRecord
    ) -> ComparisonResult:
        """Compare records using hash-based strategy."""
        hash1 = await self._compute_record_hash(record1.data)
        hash2 = await self._compute_record_hash(record2.data)
        
        are_equal = hash1 == hash2
        similarity_score = 1.0 if are_equal else 0.0
        
        differences = []
        if not are_equal:
            # Perform field-level comparison to identify differences
            field_comparison = await self._compare_field_level(record1, record2)
            differences = field_comparison.differences
            similarity_score = field_comparison.similarity_score
        
        return ComparisonResult(
            are_equal=are_equal,
            similarity_score=similarity_score,
            differences=differences,
            hash_match=are_equal,
            timestamp_comparison=self._compare_timestamps(record1, record2),
            metadata={"hash1": hash1, "hash2": hash2}
        )

    async def _compare_field_level(
        self,
        record1: DataRecord,
        record2: DataRecord
    ) -> ComparisonResult:
        """Compare records at field level."""
        data1 = record1.data
        data2 = record2.data
        
        # Get all fields
        all_fields = set(data1.keys()) | set(data2.keys())
        ignore_fields = set(self.config.ignore_fields)
        fields_to_compare = all_fields - ignore_fields
        
        differences = []
        matching_fields = 0
        total_fields = len(fields_to_compare)
        
        for field in fields_to_compare:
            value1 = data1.get(field)
            value2 = data2.get(field)
            
            if value1 != value2:
                differences.append(FieldChange(
                    field_name=field,
                    old_value=value2,
                    new_value=value1,
                    confidence=1.0
                ))
            else:
                matching_fields += 1
        
        are_equal = len(differences) == 0
        similarity_score = matching_fields / total_fields if total_fields > 0 else 1.0
        
        return ComparisonResult(
            are_equal=are_equal,
            similarity_score=similarity_score,
            differences=differences,
            timestamp_comparison=self._compare_timestamps(record1, record2),
            metadata={
                "total_fields": total_fields,
                "matching_fields": matching_fields,
                "different_fields": len(differences)
            }
        )

    async def _compare_timestamp_based(
        self,
        record1: DataRecord,
        record2: DataRecord
    ) -> ComparisonResult:
        """Compare records using timestamp-based strategy."""
        timestamp_comparison = self._compare_timestamps(record1, record2)
        
        # If timestamps are the same (within tolerance), consider equal
        are_equal = timestamp_comparison == "same"
        
        # If not equal, perform field-level comparison
        differences = []
        similarity_score = 1.0
        
        if not are_equal:
            field_comparison = await self._compare_field_level(record1, record2)
            differences = field_comparison.differences
            similarity_score = field_comparison.similarity_score
        
        return ComparisonResult(
            are_equal=are_equal,
            similarity_score=similarity_score,
            differences=differences,
            timestamp_comparison=timestamp_comparison,
            metadata={"strategy": "timestamp_based"}
        )

    async def _compare_version_based(
        self,
        record1: DataRecord,
        record2: DataRecord
    ) -> ComparisonResult:
        """Compare records using version-based strategy."""
        version1 = self._extract_version(record1.data)
        version2 = self._extract_version(record2.data)
        
        are_equal = version1 == version2
        
        differences = []
        similarity_score = 1.0
        
        if not are_equal:
            field_comparison = await self._compare_field_level(record1, record2)
            differences = field_comparison.differences
            similarity_score = field_comparison.similarity_score
        
        return ComparisonResult(
            are_equal=are_equal,
            similarity_score=similarity_score,
            differences=differences,
            timestamp_comparison=self._compare_timestamps(record1, record2),
            metadata={
                "version1": version1,
                "version2": version2,
                "strategy": "version_based"
            }
        )

    async def _compare_checksum_based(
        self,
        record1: DataRecord,
        record2: DataRecord
    ) -> ComparisonResult:
        """Compare records using checksum-based strategy."""
        checksum1 = await self._compute_checksum(record1.data)
        checksum2 = await self._compute_checksum(record2.data)
        
        are_equal = checksum1 == checksum2
        similarity_score = 1.0 if are_equal else 0.0
        
        differences = []
        if not are_equal:
            field_comparison = await self._compare_field_level(record1, record2)
            differences = field_comparison.differences
            similarity_score = field_comparison.similarity_score
        
        return ComparisonResult(
            are_equal=are_equal,
            similarity_score=similarity_score,
            differences=differences,
            hash_match=are_equal,
            timestamp_comparison=self._compare_timestamps(record1, record2),
            metadata={"checksum1": checksum1, "checksum2": checksum2}
        )

    async def _compare_full_record(
        self,
        record1: DataRecord,
        record2: DataRecord
    ) -> ComparisonResult:
        """Compare full records (default strategy)."""
        return await self._compare_field_level(record1, record2)

    async def _detect_conflicts(
        self,
        current_record: DataRecord,
        previous_record: DataRecord
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between records."""
        conflicts = []
        
        # Check for concurrent updates
        if self._is_concurrent_update(current_record, previous_record):
            conflicts.append({
                "type": ConflictType.CONCURRENT_UPDATE.value,
                "description": "Records were updated concurrently",
                "current_timestamp": current_record.timestamp,
                "previous_timestamp": previous_record.timestamp
            })
        
        # Check for version conflicts
        version_conflict = self._check_version_conflict(current_record, previous_record)
        if version_conflict:
            conflicts.append(version_conflict)
        
        # Check for schema mismatches
        schema_conflict = self._check_schema_mismatch(current_record, previous_record)
        if schema_conflict:
            conflicts.append(schema_conflict)
        
        return conflicts

    def _is_concurrent_update(
        self,
        record1: DataRecord,
        record2: DataRecord
    ) -> bool:
        """Check if records represent concurrent updates."""
        if not record1.timestamp or not record2.timestamp:
            return False
        
        time_diff = abs((record1.timestamp - record2.timestamp).total_seconds())
        return time_diff <= self.config.timestamp_tolerance_seconds

    def _check_version_conflict(
        self,
        record1: DataRecord,
        record2: DataRecord
    ) -> Optional[Dict[str, Any]]:
        """Check for version conflicts."""
        version1 = self._extract_version(record1.data)
        version2 = self._extract_version(record2.data)
        
        if version1 and version2 and version1 != version2:
            return {
                "type": ConflictType.VERSION_MISMATCH.value,
                "description": f"Version mismatch: {version1} vs {version2}",
                "version1": version1,
                "version2": version2
            }
        
        return None

    def _check_schema_mismatch(
        self,
        record1: DataRecord,
        record2: DataRecord
    ) -> Optional[Dict[str, Any]]:
        """Check for schema mismatches."""
        fields1 = set(record1.data.keys())
        fields2 = set(record2.data.keys())
        
        if fields1 != fields2:
            missing_in_1 = fields2 - fields1
            missing_in_2 = fields1 - fields2
            
            return {
                "type": ConflictType.SCHEMA_MISMATCH.value,
                "description": "Schema mismatch detected",
                "missing_in_current": list(missing_in_1),
                "missing_in_previous": list(missing_in_2)
            }
        
        return None

    def _compare_timestamps(
        self,
        record1: DataRecord,
        record2: DataRecord
    ) -> Optional[str]:
        """Compare timestamps between records."""
        timestamp1 = self._extract_timestamp(record1)
        timestamp2 = self._extract_timestamp(record2)
        
        if not timestamp1 or not timestamp2:
            return None
        
        time_diff = (timestamp1 - timestamp2).total_seconds()
        
        if abs(time_diff) <= self.config.timestamp_tolerance_seconds:
            return "same"
        elif time_diff > 0:
            return "newer"
        else:
            return "older"

    def _extract_timestamp(self, record: DataRecord) -> Optional[datetime]:
        """Extract timestamp from record."""
        if record.timestamp:
            return record.timestamp
        
        # Try to find timestamp in data
        for field in self.config.timestamp_fields:
            value = record.data.get(field)
            if value:
                if isinstance(value, datetime):
                    return value
                elif isinstance(value, str):
                    try:
                        return datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        continue
        
        return None

    def _extract_version(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract version from record data."""
        for field in self.config.version_fields:
            value = data.get(field)
            if value is not None:
                return str(value)
        
        return None

    async def _compute_record_hash(self, data: Dict[str, Any]) -> str:
        """Compute hash for record data."""
        # Use specified fields or all fields
        fields_to_hash = self.config.hash_fields or list(data.keys())
        ignore_fields = set(self.config.ignore_fields)
        fields_to_hash = [f for f in fields_to_hash if f not in ignore_fields]
        
        # Create deterministic hash
        hash_data = {k: data.get(k) for k in sorted(fields_to_hash)}
        hash_str = json.dumps(hash_data, sort_keys=True, default=str)
        
        # Check cache
        if self.config.enable_caching and hash_str in self._hash_cache:
            return self._hash_cache[hash_str]
        
        # Compute hash
        if self.config.hash_algorithm == "sha256":
            hash_value = hashlib.sha256(hash_str.encode()).hexdigest()
        elif self.config.hash_algorithm == "md5":
            hash_value = hashlib.md5(hash_str.encode()).hexdigest()
        else:
            hash_value = hashlib.sha1(hash_str.encode()).hexdigest()
        
        # Cache result
        if self.config.enable_caching:
            self._hash_cache[hash_str] = hash_value
        
        return hash_value

    async def _compute_checksum(self, data: Dict[str, Any]) -> str:
        """Compute checksum for record data."""
        # Simple checksum implementation
        data_str = json.dumps(data, sort_keys=True, default=str)
        return str(sum(ord(c) for c in data_str))

    def _manage_cache(self) -> None:
        """Manage cache size to prevent memory issues."""
        if len(self._comparison_cache) > self.config.cache_size:
            # Remove oldest entries (simple LRU approximation)
            items_to_remove = len(self._comparison_cache) - self.config.cache_size // 2
            keys_to_remove = list(self._comparison_cache.keys())[:items_to_remove]
            
            for key in keys_to_remove:
                del self._comparison_cache[key]
        
        if len(self._hash_cache) > self.config.cache_size:
            items_to_remove = len(self._hash_cache) - self.config.cache_size // 2
            keys_to_remove = list(self._hash_cache.keys())[:items_to_remove]
            
            for key in keys_to_remove:
                del self._hash_cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get change detection statistics."""
        return {
            "engine_id": self.engine_id,
            "cache_size": {
                "comparison_cache": len(self._comparison_cache),
                "hash_cache": len(self._hash_cache)
            },
            **self.stats
        }

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._comparison_cache.clear()
        self._hash_cache.clear()
        logger.info("Cleared change detection caches")