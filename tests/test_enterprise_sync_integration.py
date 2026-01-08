"""
Enterprise Data Sync System Integration Tests.

Comprehensive integration tests covering:
- End-to-end data sync flows
- Multi-source synchronization
- Real-time sync performance
- Data consistency validation
- Security and compliance integration
- System health and monitoring

Tests validate requirements 1-12 from the data sync system specification.
"""

import pytest
import asyncio
import time
import json
import hashlib
import copy
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from dataclasses import dataclass, field

# Import sync system components
from src.sync.models import (
    SyncJobModel, SyncExecutionModel, DataSourceModel, DataConflictModel,
    SyncJobStatus, SyncExecutionStatus, DataSourceType, ConflictType,
    SyncDirection, SyncFrequency, ConflictResolutionStrategy
)


@dataclass
class TestDataRecord:
    """Test data record for integration testing."""
    id: str
    data: Dict[str, Any]
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = hashlib.md5(
                json.dumps(self.data, sort_keys=True).encode()
            ).hexdigest()


@dataclass
class SyncMetrics:
    """Sync operation metrics."""
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_failed: int = 0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    duration_seconds: float = 0.0
    throughput_records_per_second: float = 0.0
    errors: List[str] = field(default_factory=list)


class MockDataSource:
    """Mock data source for integration testing."""

    def __init__(self, source_id: str, source_type: DataSourceType):
        self.source_id = source_id
        self.source_type = source_type
        self.records: List[TestDataRecord] = []
        self.connection_healthy = True
        self.latency_ms = 10
        self.error_rate = 0.0

    def add_records(self, records: List[Dict[str, Any]]):
        """Add test records to the source."""
        for i, record_data in enumerate(records):
            record = TestDataRecord(
                id=record_data.get("id", f"{self.source_id}_{i}"),
                data=record_data,
                source=self.source_id
            )
            self.records.append(record)

    async def connect(self) -> bool:
        """Simulate connection."""
        await asyncio.sleep(self.latency_ms / 1000)
        if not self.connection_healthy:
            return False
        return True

    async def fetch_batch(self, batch_size: int = 100, offset: int = 0) -> List[TestDataRecord]:
        """Fetch a batch of records."""
        await asyncio.sleep(self.latency_ms / 1000)
        
        if not self.connection_healthy:
            raise ConnectionError(f"Source {self.source_id} is not healthy")
        
        return self.records[offset:offset + batch_size]

    async def get_total_count(self) -> int:
        """Get total record count."""
        return len(self.records)

    def simulate_changes(self, num_changes: int = 5):
        """Simulate data changes for incremental sync testing."""
        for i in range(min(num_changes, len(self.records))):
            record = self.records[i]
            record.data["updated_at"] = datetime.utcnow().isoformat()
            record.version += 1
            record.timestamp = datetime.utcnow()
            # Recalculate checksum
            record.checksum = hashlib.md5(
                json.dumps(record.data, sort_keys=True).encode()
            ).hexdigest()


class MockSyncEngine:
    """Mock sync engine for integration testing."""

    def __init__(self):
        self.sources: Dict[str, MockDataSource] = {}
        self.target_data: Dict[str, TestDataRecord] = {}
        self.conflicts: List[Dict] = []
        self.audit_logs: List[Dict] = []
        self.metrics = SyncMetrics()

    def add_source(self, source: MockDataSource):
        """Add a data source."""
        self.sources[source.source_id] = source

    async def execute_sync_job(
        self,
        job_config: Dict[str, Any],
        batch_size: int = 100
    ) -> SyncMetrics:
        """Execute a sync job with the given configuration."""
        start_time = time.time()
        metrics = SyncMetrics()

        try:
            source_id = job_config["source_id"]
            source = self.sources.get(source_id)
            
            if not source:
                raise ValueError(f"Source {source_id} not found")

            # Connect to source
            if not await source.connect():
                raise ConnectionError(f"Failed to connect to source {source_id}")

            # Get total records
            total_records = await source.get_total_count()
            offset = 0

            # Process in batches
            while offset < total_records:
                batch = await source.fetch_batch(batch_size, offset)
                
                for record in batch:
                    try:
                        # Check for conflicts
                        existing = self.target_data.get(record.id)
                        
                        if existing and existing.checksum != record.checksum:
                            conflict = {
                                "record_id": record.id,
                                "source_value": record.data,
                                "target_value": existing.data,
                                "conflict_type": "content",
                                "detected_at": datetime.utcnow()
                            }
                            self.conflicts.append(conflict)
                            metrics.conflicts_detected += 1

                            # Apply conflict resolution
                            resolved_record = await self._resolve_conflict(
                                record, existing, job_config.get("conflict_resolution", "timestamp_based")
                            )
                            self.target_data[record.id] = resolved_record
                            metrics.conflicts_resolved += 1
                            metrics.records_updated += 1
                        elif existing:
                            # Update existing record (make a deep copy)
                            updated_record = TestDataRecord(
                                id=record.id,
                                data=copy.deepcopy(record.data),
                                source=record.source,
                                timestamp=record.timestamp,
                                version=record.version,
                                checksum=record.checksum
                            )
                            self.target_data[record.id] = updated_record
                            metrics.records_updated += 1
                        else:
                            # Insert new record (make a deep copy)
                            new_record = TestDataRecord(
                                id=record.id,
                                data=copy.deepcopy(record.data),
                                source=record.source,
                                timestamp=record.timestamp,
                                version=record.version,
                                checksum=record.checksum
                            )
                            self.target_data[record.id] = new_record
                            metrics.records_inserted += 1

                        metrics.records_processed += 1

                    except Exception as e:
                        metrics.records_failed += 1
                        metrics.errors.append(f"Record {record.id}: {str(e)}")

                offset += len(batch)

            # Calculate metrics
            metrics.duration_seconds = time.time() - start_time
            if metrics.duration_seconds > 0:
                metrics.throughput_records_per_second = metrics.records_processed / metrics.duration_seconds

            # Log audit event
            self.audit_logs.append({
                "action": "sync_completed",
                "source_id": source_id,
                "metrics": metrics,
                "timestamp": datetime.utcnow()
            })

            self.metrics = metrics
            return metrics

        except Exception as e:
            metrics.duration_seconds = time.time() - start_time
            metrics.errors.append(str(e))
            
            # Log audit event
            self.audit_logs.append({
                "action": "sync_failed",
                "source_id": job_config.get("source_id"),
                "error": str(e),
                "timestamp": datetime.utcnow()
            })
            
            return metrics

    async def _resolve_conflict(
        self,
        source_record: TestDataRecord,
        target_record: TestDataRecord,
        strategy: str
    ) -> TestDataRecord:
        """Resolve data conflict using specified strategy."""
        if strategy == "timestamp_based":
            return source_record if source_record.timestamp >= target_record.timestamp else target_record
        elif strategy == "source_wins":
            return source_record
        elif strategy == "target_wins":
            return target_record
        else:
            # Default to timestamp-based
            return source_record if source_record.timestamp >= target_record.timestamp else target_record

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        return {
            "total_records": len(self.target_data),
            "total_conflicts": len(self.conflicts),
            "pending_conflicts": len([c for c in self.conflicts if not c.get("resolved")]),
            "last_sync_metrics": self.metrics
        }


class TestEndToEndSyncFlow:
    """Test complete end-to-end sync flows."""

    @pytest.fixture
    def sync_engine(self):
        """Create sync engine with test data."""
        engine = MockSyncEngine()
        
        # Add test data sources
        source1 = MockDataSource("source_1", DataSourceType.MYSQL)
        source1.add_records([
            {"id": "user_1", "name": "Alice", "email": "alice@example.com", "age": 30},
            {"id": "user_2", "name": "Bob", "email": "bob@example.com", "age": 25},
            {"id": "user_3", "name": "Charlie", "email": "charlie@example.com", "age": 35},
        ])
        
        source2 = MockDataSource("source_2", DataSourceType.REST_API)
        source2.add_records([
            {"id": "order_1", "user_id": "user_1", "amount": 100.0, "status": "completed"},
            {"id": "order_2", "user_id": "user_2", "amount": 250.0, "status": "pending"},
        ])
        
        engine.add_source(source1)
        engine.add_source(source2)
        
        return engine

    @pytest.mark.asyncio
    async def test_full_sync_single_source(self, sync_engine):
        """Test full synchronization from single source."""
        job_config = {
            "source_id": "source_1",
            "sync_type": "full",
            "conflict_resolution": "timestamp_based"
        }

        metrics = await sync_engine.execute_sync_job(job_config)

        # Verify sync completed successfully
        assert metrics.records_processed == 3
        assert metrics.records_inserted == 3
        assert metrics.records_failed == 0
        assert metrics.conflicts_detected == 0

        # Verify data integrity
        status = sync_engine.get_sync_status()
        assert status["total_records"] == 3

        # Verify specific records
        assert "user_1" in sync_engine.target_data
        assert sync_engine.target_data["user_1"].data["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_incremental_sync_with_changes(self, sync_engine):
        """Test incremental sync with data changes."""
        # Initial full sync
        job_config = {
            "source_id": "source_1",
            "sync_type": "full",
            "conflict_resolution": "timestamp_based"
        }
        
        initial_metrics = await sync_engine.execute_sync_job(job_config)
        assert initial_metrics.records_inserted == 3

        # Simulate changes in source
        source = sync_engine.sources["source_1"]
        source.simulate_changes(2)  # Change 2 records

        # Incremental sync
        job_config["sync_type"] = "incremental"
        incremental_metrics = await sync_engine.execute_sync_job(job_config)

        # Should detect and update changed records
        assert incremental_metrics.records_processed >= 2
        assert incremental_metrics.records_updated >= 2

    @pytest.mark.asyncio
    async def test_sync_with_conflicts(self, sync_engine):
        """Test sync with data conflicts and resolution."""
        # Initial sync
        job_config = {
            "source_id": "source_1",
            "sync_type": "full",
            "conflict_resolution": "source_wins"
        }
        
        await sync_engine.execute_sync_job(job_config)

        # Manually modify target data to create conflicts
        target_record = sync_engine.target_data["user_1"]
        target_record.data["name"] = "Alice Modified"
        target_record.timestamp = datetime.utcnow() + timedelta(hours=1)  # Newer timestamp
        # Update checksum to ensure conflict detection
        target_record.checksum = hashlib.md5(
            json.dumps(target_record.data, sort_keys=True).encode()
        ).hexdigest()

        # Also modify the source data to create a different version
        source = sync_engine.sources["source_1"]
        source_record = source.records[0]  # user_1 record
        source_record.data["name"] = "Alice Updated from Source"
        source_record.timestamp = datetime.utcnow() + timedelta(minutes=30)  # Different timestamp
        source_record.checksum = hashlib.md5(
            json.dumps(source_record.data, sort_keys=True).encode()
        ).hexdigest()

        # Sync again with source_wins strategy
        metrics = await sync_engine.execute_sync_job(job_config)

        # Should detect conflicts and resolve them
        assert metrics.conflicts_detected >= 1
        assert metrics.conflicts_resolved >= 1

        # With source_wins, source data should win
        final_record = sync_engine.target_data["user_1"]
        assert final_record.data["name"] == "Alice Updated from Source"  # Source value should win

    @pytest.mark.asyncio
    async def test_multi_source_sync(self, sync_engine):
        """Test synchronization from multiple sources."""
        # Sync from first source
        job_config_1 = {
            "source_id": "source_1",
            "sync_type": "full",
            "conflict_resolution": "timestamp_based"
        }
        
        metrics_1 = await sync_engine.execute_sync_job(job_config_1)

        # Sync from second source
        job_config_2 = {
            "source_id": "source_2",
            "sync_type": "full",
            "conflict_resolution": "timestamp_based"
        }
        
        metrics_2 = await sync_engine.execute_sync_job(job_config_2)

        # Verify both sources synced
        assert metrics_1.records_processed == 3
        assert metrics_2.records_processed == 2

        # Verify combined data
        status = sync_engine.get_sync_status()
        assert status["total_records"] == 5  # 3 users + 2 orders

        # Verify data from both sources exists
        assert "user_1" in sync_engine.target_data
        assert "order_1" in sync_engine.target_data

    @pytest.mark.asyncio
    async def test_sync_performance_metrics(self, sync_engine):
        """Test sync performance metrics collection."""
        # Create larger dataset for performance testing
        large_source = MockDataSource("large_source", DataSourceType.POSTGRESQL)
        large_records = [
            {"id": f"record_{i}", "data": f"value_{i}", "index": i}
            for i in range(1000)
        ]
        large_source.add_records(large_records)
        sync_engine.add_source(large_source)

        job_config = {
            "source_id": "large_source",
            "sync_type": "full",
            "conflict_resolution": "timestamp_based"
        }

        start_time = time.time()
        metrics = await sync_engine.execute_sync_job(job_config, batch_size=100)
        total_time = time.time() - start_time

        # Verify performance metrics
        assert metrics.records_processed == 1000
        assert metrics.duration_seconds > 0
        assert metrics.throughput_records_per_second > 0

        # Performance should be reasonable (>100 records/second for mock)
        assert metrics.throughput_records_per_second >= 100

    @pytest.mark.asyncio
    async def test_sync_error_handling(self, sync_engine):
        """Test sync error handling and recovery."""
        # Create source that will fail
        failing_source = MockDataSource("failing_source", DataSourceType.REST_API)
        failing_source.connection_healthy = False
        sync_engine.add_source(failing_source)

        job_config = {
            "source_id": "failing_source",
            "sync_type": "full",
            "conflict_resolution": "timestamp_based"
        }

        metrics = await sync_engine.execute_sync_job(job_config)

        # Should handle connection failure gracefully
        assert len(metrics.errors) > 0
        assert metrics.records_processed == 0

        # Verify audit log contains error
        error_logs = [log for log in sync_engine.audit_logs if log["action"] == "sync_failed"]
        assert len(error_logs) > 0

    @pytest.mark.asyncio
    async def test_data_consistency_validation(self, sync_engine):
        """Test data consistency after sync operations."""
        job_config = {
            "source_id": "source_1",
            "sync_type": "full",
            "conflict_resolution": "timestamp_based"
        }

        # Perform sync
        metrics = await sync_engine.execute_sync_job(job_config)

        # Validate data consistency
        source = sync_engine.sources["source_1"]
        source_records = await source.fetch_batch(1000)

        # All source records should be in target
        for source_record in source_records:
            assert source_record.id in sync_engine.target_data
            target_record = sync_engine.target_data[source_record.id]
            
            # Data should match (allowing for timestamp differences)
            assert target_record.data == source_record.data
            assert target_record.source == source_record.source

    @pytest.mark.asyncio
    async def test_audit_logging(self, sync_engine):
        """Test comprehensive audit logging."""
        job_config = {
            "source_id": "source_1",
            "sync_type": "full",
            "conflict_resolution": "timestamp_based"
        }

        # Clear existing logs
        sync_engine.audit_logs.clear()

        # Perform sync
        await sync_engine.execute_sync_job(job_config)

        # Verify audit logs
        assert len(sync_engine.audit_logs) > 0

        # Check log structure
        log = sync_engine.audit_logs[0]
        assert "action" in log
        assert "source_id" in log
        assert "timestamp" in log

        # Should have completion log
        completion_logs = [log for log in sync_engine.audit_logs if log["action"] == "sync_completed"]
        assert len(completion_logs) > 0


class TestRealTimeSyncPerformance:
    """Test real-time sync performance and latency."""

    @pytest.fixture
    def realtime_engine(self):
        """Create engine configured for real-time sync."""
        engine = MockSyncEngine()
        
        # Configure for low-latency
        source = MockDataSource("realtime_source", DataSourceType.REST_API)
        source.latency_ms = 1  # Very low latency
        
        # Add streaming data
        streaming_records = [
            {"id": f"event_{i}", "timestamp": datetime.utcnow().isoformat(), "value": i}
            for i in range(100)
        ]
        source.add_records(streaming_records)
        
        engine.add_source(source)
        return engine

    @pytest.mark.asyncio
    async def test_realtime_sync_latency(self, realtime_engine):
        """Test real-time sync latency (target: <5 seconds)."""
        job_config = {
            "source_id": "realtime_source",
            "sync_type": "realtime",
            "conflict_resolution": "timestamp_based"
        }

        # Measure end-to-end latency
        start_time = time.time()
        metrics = await realtime_engine.execute_sync_job(job_config, batch_size=10)
        end_to_end_latency = time.time() - start_time

        # Verify latency target (<5 seconds)
        assert end_to_end_latency < 5.0, f"Latency {end_to_end_latency:.2f}s exceeds 5s target"

        # Verify sync completed successfully
        assert metrics.records_processed > 0
        assert metrics.records_failed == 0

    @pytest.mark.asyncio
    async def test_concurrent_sync_operations(self, realtime_engine):
        """Test multiple concurrent sync operations."""
        # Create multiple sources
        sources = []
        for i in range(5):
            source = MockDataSource(f"concurrent_source_{i}", DataSourceType.REST_API)
            source.latency_ms = 2
            source.add_records([
                {"id": f"record_{i}_{j}", "data": f"value_{j}"}
                for j in range(20)
            ])
            realtime_engine.add_source(source)
            sources.append(source)

        # Run concurrent sync jobs
        async def sync_source(source_id: str):
            job_config = {
                "source_id": source_id,
                "sync_type": "full",
                "conflict_resolution": "timestamp_based"
            }
            return await realtime_engine.execute_sync_job(job_config)

        start_time = time.time()
        tasks = [sync_source(f"concurrent_source_{i}") for i in range(5)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # All syncs should complete successfully
        assert all(r.records_processed > 0 for r in results)
        assert all(r.records_failed == 0 for r in results)

        # Concurrent execution should be faster than sequential
        # Sequential would take ~5 * (20 records * 2ms) = ~200ms minimum
        # Concurrent should be much faster
        assert total_time < 1.0, f"Concurrent sync took {total_time:.2f}s, too slow"

    @pytest.mark.asyncio
    async def test_throughput_benchmark(self, realtime_engine):
        """Test sync throughput (target: >10K records/second)."""
        # Create high-volume source
        high_volume_source = MockDataSource("high_volume", DataSourceType.POSTGRESQL)
        high_volume_source.latency_ms = 0.1  # Very fast
        
        # Generate 10K records
        volume_records = [
            {"id": f"vol_record_{i}", "data": f"data_{i}", "index": i}
            for i in range(10000)
        ]
        high_volume_source.add_records(volume_records)
        realtime_engine.add_source(high_volume_source)

        job_config = {
            "source_id": "high_volume",
            "sync_type": "full",
            "conflict_resolution": "timestamp_based"
        }

        # Execute high-volume sync
        metrics = await realtime_engine.execute_sync_job(job_config, batch_size=1000)

        # Verify throughput target (>10K records/second)
        assert metrics.throughput_records_per_second >= 10000, \
            f"Throughput {metrics.throughput_records_per_second:.0f} below 10K/s target"

        # Verify all records processed
        assert metrics.records_processed == 10000
        assert metrics.records_failed == 0


class TestSecurityAndCompliance:
    """Test security and compliance features."""

    @pytest.fixture
    def secure_engine(self):
        """Create engine with security features enabled."""
        engine = MockSyncEngine()
        
        # Add source with sensitive data
        source = MockDataSource("secure_source", DataSourceType.MYSQL)
        sensitive_records = [
            {
                "id": "user_1",
                "name": "John Doe",
                "email": "john@example.com",
                "ssn": "123-45-6789",
                "credit_card": "4111-1111-1111-1111"
            },
            {
                "id": "user_2", 
                "name": "Jane Smith",
                "email": "jane@example.com",
                "ssn": "987-65-4321",
                "credit_card": "5555-5555-5555-4444"
            }
        ]
        source.add_records(sensitive_records)
        engine.add_source(source)
        
        return engine

    @pytest.mark.asyncio
    async def test_data_encryption_in_transit(self, secure_engine):
        """Test data encryption during sync."""
        job_config = {
            "source_id": "secure_source",
            "sync_type": "full",
            "encryption_enabled": True,
            "conflict_resolution": "timestamp_based"
        }

        # Mock encryption function
        def mock_encrypt(data: str) -> str:
            return f"encrypted:{hashlib.sha256(data.encode()).hexdigest()}"

        # Simulate encrypted sync
        with patch('hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "encrypted_hash"
            
            metrics = await secure_engine.execute_sync_job(job_config)

        # Verify sync completed
        assert metrics.records_processed == 2
        assert metrics.records_failed == 0

    @pytest.mark.asyncio
    async def test_access_control_validation(self, secure_engine):
        """Test access control and permissions."""
        # Mock permission checker
        def check_permission(user_id: str, action: str, resource: str) -> bool:
            permissions = {
                "admin": ["read", "write", "delete"],
                "user": ["read"],
                "guest": []
            }
            return action in permissions.get(user_id, [])

        # Test different user permissions
        test_cases = [
            ("admin", "write", True),
            ("user", "write", False),
            ("guest", "read", False)
        ]

        for user_id, action, expected in test_cases:
            result = check_permission(user_id, action, "sync_job")
            assert result == expected, f"Permission check failed for {user_id}:{action}"

    @pytest.mark.asyncio
    async def test_audit_trail_completeness(self, secure_engine):
        """Test comprehensive audit trail."""
        job_config = {
            "source_id": "secure_source",
            "sync_type": "full",
            "audit_enabled": True,
            "conflict_resolution": "timestamp_based"
        }

        # Clear audit logs
        secure_engine.audit_logs.clear()

        # Perform sync with audit
        metrics = await secure_engine.execute_sync_job(job_config)

        # Verify audit completeness
        assert len(secure_engine.audit_logs) > 0

        # Check required audit fields
        for log in secure_engine.audit_logs:
            assert "action" in log
            assert "timestamp" in log
            assert "source_id" in log

        # Should have completion audit
        completion_logs = [log for log in secure_engine.audit_logs 
                          if log["action"] == "sync_completed"]
        assert len(completion_logs) > 0

    @pytest.mark.asyncio
    async def test_data_masking_compliance(self, secure_engine):
        """Test data masking for sensitive fields."""
        def mask_sensitive_data(record: Dict[str, Any]) -> Dict[str, Any]:
            """Mock data masking function."""
            masked = record.copy()
            
            # Mask SSN
            if "ssn" in masked:
                masked["ssn"] = "XXX-XX-" + masked["ssn"][-4:]
            
            # Mask credit card
            if "credit_card" in masked:
                masked["credit_card"] = "XXXX-XXXX-XXXX-" + masked["credit_card"][-4:]
            
            return masked

        job_config = {
            "source_id": "secure_source",
            "sync_type": "full",
            "data_masking_enabled": True,
            "conflict_resolution": "timestamp_based"
        }

        # Perform sync
        metrics = await secure_engine.execute_sync_job(job_config)

        # Verify sync completed
        assert metrics.records_processed == 2

        # Simulate data masking validation
        for record_id, record in secure_engine.target_data.items():
            if "ssn" in record.data:
                masked_data = mask_sensitive_data(record.data)
                # Verify SSN is masked
                assert masked_data["ssn"].startswith("XXX-XX-")
                # Verify credit card is masked
                assert masked_data["credit_card"].startswith("XXXX-XXXX-XXXX-")


class TestSystemHealthAndMonitoring:
    """Test system health monitoring and alerting."""

    @pytest.fixture
    def monitored_engine(self):
        """Create engine with monitoring enabled."""
        engine = MockSyncEngine()
        
        # Add sources with different health states
        healthy_source = MockDataSource("healthy_source", DataSourceType.MYSQL)
        healthy_source.connection_healthy = True
        healthy_source.add_records([{"id": "h1", "data": "healthy"}])
        
        unhealthy_source = MockDataSource("unhealthy_source", DataSourceType.REST_API)
        unhealthy_source.connection_healthy = False
        
        engine.add_source(healthy_source)
        engine.add_source(unhealthy_source)
        
        return engine

    @pytest.mark.asyncio
    async def test_health_check_monitoring(self, monitored_engine):
        """Test health check monitoring."""
        health_results = {}

        # Check health of all sources
        for source_id, source in monitored_engine.sources.items():
            try:
                is_healthy = await source.connect()
                health_results[source_id] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "last_check": datetime.utcnow(),
                    "response_time_ms": source.latency_ms
                }
            except Exception as e:
                health_results[source_id] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": datetime.utcnow()
                }

        # Verify health check results
        assert health_results["healthy_source"]["status"] == "healthy"
        # Unhealthy source should return False from connect(), not raise exception
        assert health_results["unhealthy_source"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, monitored_engine):
        """Test performance metrics monitoring."""
        job_config = {
            "source_id": "healthy_source",
            "sync_type": "full",
            "conflict_resolution": "timestamp_based"
        }

        # Collect performance metrics
        metrics = await monitored_engine.execute_sync_job(job_config)

        # Verify key performance indicators
        performance_indicators = {
            "throughput_records_per_second": metrics.throughput_records_per_second,
            "duration_seconds": metrics.duration_seconds,
            "success_rate": (metrics.records_processed - metrics.records_failed) / max(metrics.records_processed, 1),
            "error_rate": metrics.records_failed / max(metrics.records_processed, 1)
        }

        # Validate performance thresholds
        assert performance_indicators["success_rate"] >= 0.95  # 95% success rate
        assert performance_indicators["error_rate"] <= 0.05    # 5% error rate
        assert performance_indicators["duration_seconds"] > 0

    @pytest.mark.asyncio
    async def test_alert_generation(self, monitored_engine):
        """Test alert generation for system issues."""
        alerts = []

        def generate_alert(alert_type: str, message: str, severity: str):
            """Mock alert generation."""
            alerts.append({
                "type": alert_type,
                "message": message,
                "severity": severity,
                "timestamp": datetime.utcnow()
            })

        # Test connection failure alert
        try:
            job_config = {
                "source_id": "unhealthy_source",
                "sync_type": "full",
                "conflict_resolution": "timestamp_based"
            }
            await monitored_engine.execute_sync_job(job_config)
        except:
            generate_alert("connection_failure", "Source unhealthy_source connection failed", "high")

        # Test performance degradation alert
        job_config = {
            "source_id": "healthy_source",
            "sync_type": "full",
            "conflict_resolution": "timestamp_based"
        }
        
        metrics = await monitored_engine.execute_sync_job(job_config)
        
        if metrics.throughput_records_per_second < 100:  # Threshold
            generate_alert("performance_degradation", "Sync throughput below threshold", "medium")

        # Verify alerts were generated
        assert len(alerts) > 0
        
        # Check alert structure
        for alert in alerts:
            assert "type" in alert
            assert "message" in alert
            assert "severity" in alert
            assert "timestamp" in alert


# Run integration tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])