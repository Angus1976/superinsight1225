"""
Tests for audit log storage optimization functionality.

Tests batch storage, partitioning, and archival features.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from src.security.audit_storage import (
    OptimizedAuditStorage,
    AuditLogBatchStorage,
    AuditLogPartitionManager,
    AuditLogArchivalService,
    StorageConfig,
    StorageStats
)
from src.security.models import AuditLogModel, AuditAction
from src.database.connection import db_manager


class TestAuditLogBatchStorage:
    """Test batch storage functionality."""
    
    @pytest.fixture
    def storage_config(self):
        """Create test storage configuration."""
        return StorageConfig(
            batch_size=100,
            max_memory_mb=128,
            compression_enabled=True,
            retention_days=365
        )
    
    @pytest.fixture
    def batch_storage(self, storage_config):
        """Create batch storage instance."""
        return AuditLogBatchStorage(storage_config)
    
    @pytest.fixture
    def sample_audit_logs(self):
        """Create sample audit logs for testing."""
        logs = []
        for i in range(50):
            log = AuditLogModel(
                tenant_id="test_tenant",
                action=AuditAction.CREATE,
                resource_type="test_resource",
                resource_id=f"resource_{i}",
                details={"test_data": f"value_{i}", "index": i},
                timestamp=datetime.utcnow() - timedelta(minutes=i)
            )
            logs.append(log)
        return logs
    
    @pytest.mark.asyncio
    async def test_batch_storage_initialization(self, batch_storage):
        """Test batch storage initialization."""
        assert batch_storage.config.batch_size == 100
        assert batch_storage.config.compression_enabled is True
        assert len(batch_storage.pending_logs) == 0
        assert batch_storage.stats.total_logs_stored == 0
    
    @pytest.mark.asyncio
    async def test_prepare_batch_data(self, batch_storage, sample_audit_logs):
        """Test batch data preparation."""
        batch_data = await batch_storage._prepare_batch_data(sample_audit_logs[:5])
        
        assert len(batch_data) == 5
        assert all('id' in item for item in batch_data)
        assert all('tenant_id' in item for item in batch_data)
        assert all('timestamp' in item for item in batch_data)
        
        # Check that details are properly handled
        for item in batch_data:
            assert 'details' in item
            assert isinstance(item['details'], dict)
    
    @pytest.mark.asyncio
    async def test_compress_details(self, batch_storage):
        """Test details compression."""
        # Small details should not be compressed
        small_details = {"key": "value"}
        result = await batch_storage._compress_details(small_details)
        assert result == small_details
        
        # Large details should be compressed
        large_details = {"data": "x" * 2000}  # 2KB of data
        result = await batch_storage._compress_details(large_details)
        
        # Should be compressed if compression provides savings
        if '_compressed' in result:
            assert result['_compressed'] is True
            assert '_data' in result
    
    @pytest.mark.asyncio
    async def test_add_to_pending(self, batch_storage, sample_audit_logs):
        """Test adding logs to pending batch."""
        log = sample_audit_logs[0]
        batch_storage.add_to_pending(log)
        
        assert len(batch_storage.pending_logs) == 1
        assert batch_storage.pending_logs[0] == log
    
    @pytest.mark.asyncio
    @patch('src.security.audit_storage.db_manager.get_session')
    async def test_store_audit_logs_batch(self, mock_session, batch_storage, sample_audit_logs):
        """Test batch storage of audit logs."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_session.return_value.__enter__.return_value = mock_db
        
        # Test batch storage
        stats = await batch_storage.store_audit_logs_batch(sample_audit_logs[:10])
        
        assert isinstance(stats, StorageStats)
        assert stats.total_logs_stored == 10
        assert stats.batch_operations >= 1
        assert stats.storage_time_seconds >= 0


class TestAuditLogPartitionManager:
    """Test partition management functionality."""
    
    @pytest.fixture
    def partition_manager(self):
        """Create partition manager instance."""
        config = StorageConfig(partition_by_month=True)
        return AuditLogPartitionManager(config)
    
    @pytest.mark.asyncio
    async def test_partition_manager_initialization(self, partition_manager):
        """Test partition manager initialization."""
        assert partition_manager.config.partition_by_month is True
    
    @pytest.mark.asyncio
    @patch('src.security.audit_storage.db_manager.get_session')
    async def test_partition_exists_check(self, mock_session, partition_manager):
        """Test partition existence check."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_session.return_value.__enter__.return_value = mock_db
        
        # Mock query result
        mock_result = Mock()
        mock_result.scalar.return_value = True
        mock_db.execute.return_value = mock_result
        
        exists = await partition_manager._partition_exists("test_partition", mock_db)
        assert exists is True
    
    @pytest.mark.asyncio
    @patch('src.security.audit_storage.db_manager.get_session')
    async def test_create_monthly_partitions(self, mock_session, partition_manager):
        """Test monthly partition creation."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_session.return_value.__enter__.return_value = mock_db
        
        # Mock partition existence check to return False (partition doesn't exist)
        mock_result = Mock()
        mock_result.scalar.return_value = False
        mock_db.execute.return_value = mock_result
        
        start_date = datetime(2024, 1, 1)
        partitions = await partition_manager.create_monthly_partitions(
            start_date, months_ahead=3
        )
        
        # Should attempt to create partitions
        assert isinstance(partitions, list)


class TestAuditLogArchivalService:
    """Test archival service functionality."""
    
    @pytest.fixture
    def archival_service(self):
        """Create archival service instance."""
        config = StorageConfig(
            archive_threshold_days=30,
            retention_days=365,
            cleanup_batch_size=1000
        )
        return AuditLogArchivalService(config)
    
    @pytest.fixture
    def old_audit_logs(self):
        """Create old audit logs for archival testing."""
        logs = []
        old_date = datetime.utcnow() - timedelta(days=40)  # Older than threshold
        
        for i in range(10):
            log = AuditLogModel(
                tenant_id="test_tenant",
                action=AuditAction.READ,
                resource_type="archived_resource",
                resource_id=f"old_resource_{i}",
                details={"archived": True, "index": i},
                timestamp=old_date - timedelta(hours=i)
            )
            logs.append(log)
        return logs
    
    @pytest.mark.asyncio
    async def test_archival_service_initialization(self, archival_service):
        """Test archival service initialization."""
        assert archival_service.config.archive_threshold_days == 30
        assert archival_service.config.retention_days == 365
        assert archival_service.executor is not None
    
    @pytest.mark.asyncio
    async def test_group_logs_for_archival(self, archival_service, old_audit_logs):
        """Test grouping logs for archival."""
        grouped = archival_service._group_logs_for_archival(old_audit_logs)
        
        assert isinstance(grouped, dict)
        assert len(grouped) >= 1  # Should have at least one group
        
        # Check group key format
        for group_key in grouped.keys():
            assert "test_tenant_" in group_key
            assert len(group_key.split('_')) >= 3  # tenant_year_month
    
    @pytest.mark.asyncio
    async def test_create_archive_file(self, archival_service, old_audit_logs):
        """Test archive file creation."""
        group_key = "test_tenant_2024_01"
        archive_filename = archival_service._create_archive_file(
            group_key, old_audit_logs[:5]
        )
        
        assert archive_filename is not None
        assert "audit_logs_" in archive_filename
        assert ".json.gz" in archive_filename
    
    @pytest.mark.asyncio
    @patch('src.security.audit_storage.db_manager.get_session')
    async def test_cleanup_expired_logs(self, mock_session, archival_service):
        """Test cleanup of expired logs."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_session.return_value.__enter__.return_value = mock_db
        
        # Mock select result (first call returns IDs, second call returns empty)
        mock_select_result = Mock()
        mock_select_result.fetchall.side_effect = [
            [(1,), (2,), (3,), (4,), (5,)],  # First batch of IDs
            []  # No more IDs (end loop)
        ]
        
        # Mock delete result
        mock_delete_result = Mock()
        mock_delete_result.rowcount = 5
        
        # Configure mock to return different results for select vs delete
        mock_db.execute.side_effect = [mock_select_result, mock_delete_result, mock_select_result]
        
        cleanup_stats = await archival_service.cleanup_expired_logs(
            tenant_id="test_tenant",
            retention_days=365
        )
        
        assert isinstance(cleanup_stats, dict)
        assert "logs_deleted" in cleanup_stats
        assert "processing_time_seconds" in cleanup_stats
        assert cleanup_stats["logs_deleted"] == 5


class TestOptimizedAuditStorage:
    """Test the main optimized audit storage class."""
    
    @pytest.fixture
    def optimized_storage(self):
        """Create optimized storage instance."""
        config = StorageConfig(
            batch_size=500,
            compression_enabled=True,
            partition_by_month=True,
            retention_days=2555  # 7 years
        )
        return OptimizedAuditStorage(config)
    
    @pytest.mark.asyncio
    async def test_optimized_storage_initialization(self, optimized_storage):
        """Test optimized storage initialization."""
        assert optimized_storage.config.batch_size == 500
        assert optimized_storage.batch_storage is not None
        assert optimized_storage.partition_manager is not None
        assert optimized_storage.archival_service is not None
    
    @pytest.mark.asyncio
    async def test_get_storage_statistics(self, optimized_storage):
        """Test storage statistics retrieval."""
        stats = optimized_storage.get_storage_statistics()
        
        assert isinstance(stats, dict)
        assert "batch_storage" in stats
        assert "configuration" in stats
        
        # Check batch storage stats
        batch_stats = stats["batch_storage"]
        assert "total_logs_stored" in batch_stats
        assert "batch_operations" in batch_stats
        assert "throughput_logs_per_second" in batch_stats
        
        # Check configuration
        config = stats["configuration"]
        assert "batch_size" in config
        assert "compression_enabled" in config
        assert "retention_days" in config
    
    @pytest.mark.asyncio
    @patch('src.security.audit_storage.db_manager.get_session')
    async def test_run_maintenance_tasks(self, mock_session, optimized_storage):
        """Test maintenance tasks execution."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_session.return_value.__enter__.return_value = mock_db
        
        # Mock various database operations
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_result.scalar.return_value = False
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result
        
        maintenance_stats = await optimized_storage.run_maintenance_tasks(
            tenant_id="test_tenant"
        )
        
        assert isinstance(maintenance_stats, dict)
        assert "archival_stats" in maintenance_stats
        assert "cleanup_stats" in maintenance_stats
        assert "optimization_stats" in maintenance_stats
        assert "total_time_seconds" in maintenance_stats


class TestStorageIntegration:
    """Integration tests for storage optimization."""
    
    @pytest.mark.asyncio
    @patch('src.security.audit_storage.db_manager.get_session')
    async def test_end_to_end_storage_workflow(self, mock_session):
        """Test complete storage workflow."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_session.return_value.__enter__.return_value = mock_db
        
        # Mock database operations
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_result.scalar.return_value = False
        mock_result.fetchall.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Create storage instance
        config = StorageConfig(
            batch_size=100,
            compression_enabled=True,
            partition_by_month=True
        )
        storage = OptimizedAuditStorage(config)
        
        # Create sample logs
        logs = []
        for i in range(150):  # More than batch size
            log = AuditLogModel(
                tenant_id="integration_test",
                action=AuditAction.UPDATE,
                resource_type="integration_resource",
                resource_id=f"resource_{i}",
                details={"integration_test": True, "batch": i // 100},
                timestamp=datetime.utcnow() - timedelta(minutes=i)
            )
            logs.append(log)
        
        # Test batch storage
        storage_stats = await storage.store_audit_logs_optimized(logs)
        assert isinstance(storage_stats, StorageStats)
        assert storage_stats.total_logs_stored == 150
        
        # Test maintenance tasks
        maintenance_stats = await storage.run_maintenance_tasks(
            tenant_id="integration_test"
        )
        assert isinstance(maintenance_stats, dict)
        
        # Test statistics
        stats = storage.get_storage_statistics()
        assert isinstance(stats, dict)
        assert stats["configuration"]["batch_size"] == 100


class TestStoragePerformance:
    """Performance tests for storage optimization."""
    
    @pytest.mark.asyncio
    @patch('src.security.audit_storage.db_manager.get_session')
    async def test_batch_storage_performance(self, mock_session):
        """Test batch storage performance with large datasets."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_session.return_value.__enter__.return_value = mock_db
        
        # Create large dataset
        large_dataset = []
        for i in range(5000):  # 5K logs
            log = AuditLogModel(
                tenant_id="performance_test",
                action=AuditAction.READ,
                resource_type="performance_resource",
                resource_id=f"perf_resource_{i}",
                details={"performance_test": True, "data": "x" * 100},  # 100 chars
                timestamp=datetime.utcnow() - timedelta(seconds=i)
            )
            large_dataset.append(log)
        
        # Test with optimized configuration
        config = StorageConfig(
            batch_size=1000,
            max_memory_mb=256,
            compression_enabled=True
        )
        batch_storage = AuditLogBatchStorage(config)
        
        # Measure performance
        start_time = datetime.now()
        stats = await batch_storage.store_audit_logs_batch(large_dataset)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Performance assertions
        assert stats.total_logs_stored == 5000
        assert processing_time < 10.0  # Should complete within 10 seconds
        assert stats.throughput_logs_per_second > 100  # At least 100 logs/second
        assert stats.peak_memory_mb < 512  # Should stay within memory limits


# Utility functions for testing

def create_test_audit_log(
    tenant_id: str = "test_tenant",
    action: AuditAction = AuditAction.CREATE,
    resource_type: str = "test_resource",
    timestamp: datetime = None
) -> AuditLogModel:
    """Create a test audit log."""
    return AuditLogModel(
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id="test_resource_id",
        details={"test": True},
        timestamp=timestamp or datetime.utcnow()
    )


@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    mock_session = Mock(spec=Session)
    mock_result = Mock()
    mock_result.rowcount = 0
    mock_result.scalar.return_value = None
    mock_result.fetchall.return_value = []
    mock_session.execute.return_value = mock_result
    return mock_session


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])