"""
Comprehensive test suite for the Complete Event Capture System.

Tests the 100% security event capture functionality including:
- Multi-source event capture
- Redundant capture mechanisms
- Event validation and integrity
- Automatic retry and recovery
- Performance and reliability
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4, UUID
import json

from prometheus_client import CollectorRegistry, REGISTRY

from src.security.complete_event_capture_system import (
    CompleteEventCaptureSystem, EventSource, CaptureStatus,
    EventCaptureRecord, CaptureMetrics, initialize_complete_capture_system
)
from src.security.security_event_monitor import SecurityEventMonitor, SecurityEvent, SecurityEventType, ThreatLevel
from src.security.threat_detector import AdvancedThreatDetector
from src.security.models import AuditLogModel, AuditAction


@pytest.fixture(autouse=True)
def setup_prometheus_registry():
    """Setup separate Prometheus registry for each test to avoid conflicts."""
    # Create a new registry for each test
    test_registry = CollectorRegistry()
    
    # Patch the prometheus_client to use our test registry
    with patch('prometheus_client.Counter') as mock_counter, \
         patch('prometheus_client.Gauge') as mock_gauge, \
         patch('prometheus_client.Histogram') as mock_histogram:
        
        # Create mock metrics that don't actually register
        mock_counter.return_value = Mock()
        mock_gauge.return_value = Mock()
        mock_histogram.return_value = Mock()
        
        yield test_registry


class TestCompleteEventCaptureSystem:
    """Test complete event capture system functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.mock_security_monitor = Mock(spec=SecurityEventMonitor)
        self.mock_threat_detector = Mock(spec=AdvancedThreatDetector)
        
        # Mock Prometheus metrics and asyncio components to avoid conflicts
        with patch('src.security.complete_event_capture_system.PrometheusCounter') as mock_counter, \
             patch('src.security.complete_event_capture_system.Gauge') as mock_gauge, \
             patch('src.security.complete_event_capture_system.Histogram') as mock_histogram, \
             patch('asyncio.Queue') as mock_queue:
            
            mock_counter.return_value = Mock()
            mock_gauge.return_value = Mock()
            mock_histogram.return_value = Mock()
            
            # Mock asyncio.Queue to avoid event loop issues
            mock_queue_instance = Mock()
            mock_queue_instance.maxsize = 10000
            mock_queue_instance.qsize.return_value = 0
            mock_queue_instance.empty.return_value = True
            mock_queue_instance.put = AsyncMock()  # Make put method async
            mock_queue_instance.get = AsyncMock()  # Make get method async
            mock_queue.return_value = mock_queue_instance
            
            self.capture_system = CompleteEventCaptureSystem(
                self.mock_security_monitor,
                self.mock_threat_detector
            )
        
        self.tenant_id = "test_tenant_capture"
        self.user_id = uuid4()
    
    def test_system_initialization(self):
        """Test capture system initialization."""
        assert self.capture_system is not None
        assert self.capture_system.capture_enabled is True
        assert self.capture_system.max_retry_attempts == 3
        assert self.capture_system.validation_enabled is True
        assert len(self.capture_system.source_metrics) == len(EventSource)
        assert self.capture_system.event_queue.maxsize == 10000
    
    def test_capture_metrics_initialization(self):
        """Test capture metrics are properly initialized."""
        metrics = self.capture_system.prometheus_metrics
        
        # Check required metrics exist
        assert 'security_events_captured_total' in metrics
        assert 'security_event_capture_rate' in metrics
        assert 'security_event_validation_failures' in metrics
        assert 'security_event_retry_attempts' in metrics
        assert 'security_event_processing_latency' in metrics
        assert 'security_event_queue_size' in metrics
        assert 'security_event_capture_coverage' in metrics
    
    @pytest.mark.asyncio
    async def test_event_enqueuing(self):
        """Test event enqueuing functionality."""
        # Create test event data
        event_data = {
            'event_id': 'TEST_EVENT_001',
            'source': EventSource.AUDIT_LOG.value,
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': self.tenant_id,
            'user_id': str(self.user_id),
            'action': 'read',
            'resource_type': 'dataset'
        }
        
        # Test enqueuing
        await self.capture_system._enqueue_event(event_data)
        
        # Verify event was attempted to be queued (check put was called)
        self.capture_system.event_queue.put.assert_called_once_with(event_data)
        
        # Verify capture record was created
        assert event_data['event_id'] in self.capture_system.capture_records
        
        # Verify capture record
        record = self.capture_system.capture_records[event_data['event_id']]
        assert record.event_id == event_data['event_id']
        assert record.source == EventSource.AUDIT_LOG
        assert record.status == CaptureStatus.PENDING
        assert record.metadata == event_data
    
    @pytest.mark.asyncio
    async def test_audit_log_capture(self):
        """Test audit log event capture."""
        # Create mock audit log
        audit_log = Mock(spec=AuditLogModel)
        audit_log.id = "audit_001"
        audit_log.tenant_id = self.tenant_id
        audit_log.user_id = self.user_id
        audit_log.action = AuditAction.READ
        audit_log.resource_type = "dataset"
        audit_log.resource_id = "dataset_123"
        audit_log.ip_address = "192.168.1.100"
        audit_log.timestamp = datetime.utcnow()
        audit_log.details = {"operation": "data_access"}
        
        # Test capture
        await self.capture_system._capture_event_from_audit_log(audit_log)
        
        # Verify event was attempted to be queued (check put was called)
        self.capture_system.event_queue.put.assert_called_once()
        
        # Get the queued event data from the call
        queued_event = self.capture_system.event_queue.put.call_args[0][0]
        
        assert queued_event['event_id'] == f"AUDIT_{audit_log.id}"
        assert queued_event['source'] == EventSource.AUDIT_LOG.value
        assert queued_event['tenant_id'] == self.tenant_id
        assert queued_event['action'] == AuditAction.READ.value
        assert queued_event['raw_log_id'] == audit_log.id
    
    @pytest.mark.asyncio
    async def test_security_event_capture(self):
        """Test security event capture."""
        # Create mock security event
        security_event = SecurityEvent(
            event_id="SEC_TEST_001",
            event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
            threat_level=ThreatLevel.HIGH,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            ip_address="192.168.1.100",
            timestamp=datetime.utcnow(),
            description="Test brute force attack",
            details={"failed_attempts": 10}
        )
        
        # Test capture
        await self.capture_system._capture_security_event(security_event)
        
        # Verify event was attempted to be queued (check put was called)
        self.capture_system.event_queue.put.assert_called_once()
        
        # Get the queued event data from the call
        queued_event = self.capture_system.event_queue.put.call_args[0][0]
        
        assert queued_event['event_id'] == f"SEC_{security_event.event_id}"
        assert queued_event['source'] == EventSource.REAL_TIME_MONITOR.value
        assert queued_event['event_type'] == SecurityEventType.BRUTE_FORCE_ATTACK.value
        assert queued_event['threat_level'] == ThreatLevel.HIGH.value
    
    @pytest.mark.asyncio
    async def test_event_processing(self):
        """Test event processing functionality."""
        # Create test event
        event_data = {
            'event_id': 'PROCESS_TEST_001',
            'source': EventSource.AUDIT_LOG.value,
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': self.tenant_id,
            'user_id': str(self.user_id)
        }
        
        # Create capture record
        record = EventCaptureRecord(
            event_id=event_data['event_id'],
            source=EventSource.AUDIT_LOG,
            timestamp=datetime.utcnow(),
            status=CaptureStatus.PENDING,
            metadata=event_data
        )
        
        self.capture_system.capture_records[record.event_id] = record
        
        # Register a test handler
        handler_called = False
        async def test_handler(data):
            nonlocal handler_called
            handler_called = True
            assert data['event_id'] == event_data['event_id']
        
        self.capture_system.register_event_handler(EventSource.AUDIT_LOG, test_handler)
        
        # Process event
        await self.capture_system._process_captured_event(event_data)
        
        # Verify processing
        assert record.status == CaptureStatus.CAPTURED
        assert record.attempts == 1
        assert record.last_attempt is not None
        assert handler_called is True
        
        # Verify metrics updated
        assert self.capture_system.capture_metrics.captured_events == 1
        assert self.capture_system.source_metrics[EventSource.AUDIT_LOG].captured_events == 1
    
    @pytest.mark.asyncio
    async def test_event_validation(self):
        """Test event validation functionality."""
        
        # Register validation rules for testing
        self.capture_system.validation_rules = [
            self.capture_system._validate_required_fields,
            self.capture_system._validate_timestamp,
            self.capture_system._validate_data_integrity
        ]
        
        # Create test event with valid data
        valid_event_data = {
            'event_id': 'VALID_TEST_001',
            'source': EventSource.AUDIT_LOG.value,
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': self.tenant_id
        }
        
        record = EventCaptureRecord(
            event_id=valid_event_data['event_id'],
            source=EventSource.AUDIT_LOG,
            timestamp=datetime.utcnow(),
            status=CaptureStatus.CAPTURED,
            metadata=valid_event_data
        )
        
        # Test validation
        await self.capture_system._validate_captured_event(record)
        
        # Verify validation passed
        assert record.status == CaptureStatus.VALIDATED
        assert record.validation_hash is not None
        
        # Test with invalid data (missing required fields)
        invalid_event_data = {
            'source': EventSource.AUDIT_LOG.value,
            # Missing event_id and timestamp
        }
        
        invalid_record = EventCaptureRecord(
            event_id='INVALID_TEST_001',
            source=EventSource.AUDIT_LOG,
            timestamp=datetime.utcnow(),
            status=CaptureStatus.CAPTURED,
            metadata=invalid_event_data
        )
        
        # Test validation failure
        await self.capture_system._validate_captured_event(invalid_record)
        
        # Verify validation failed
        assert invalid_record.status == CaptureStatus.FAILED
        assert "Validation failed" in invalid_record.error_message
    
    @pytest.mark.asyncio
    async def test_event_retry_mechanism(self):
        """Test event retry mechanism."""
        # Create failed event record
        event_data = {
            'event_id': 'RETRY_TEST_001',
            'source': EventSource.AUDIT_LOG.value,
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': self.tenant_id
        }
        
        record = EventCaptureRecord(
            event_id=event_data['event_id'],
            source=EventSource.AUDIT_LOG,
            timestamp=datetime.utcnow(),
            status=CaptureStatus.FAILED,
            attempts=1,
            error_message="Initial processing failed",
            metadata=event_data
        )
        
        self.capture_system.capture_records[record.event_id] = record
        
        # Mock successful retry
        with patch.object(self.capture_system, '_process_captured_event', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = None  # Successful processing
            
            # Test retry
            await self.capture_system._retry_event_capture(record)
            
            # Verify retry was attempted
            assert record.status == CaptureStatus.RETRY
            assert record.attempts == 2
            assert record.last_attempt is not None
            mock_process.assert_called_once_with(event_data)
    
    @pytest.mark.asyncio
    async def test_capture_rate_calculation(self):
        """Test capture rate calculation."""
        # Set up test metrics
        self.capture_system.capture_metrics.total_events = 100
        self.capture_system.capture_metrics.captured_events = 95
        
        # Set up source metrics
        self.capture_system.source_metrics[EventSource.AUDIT_LOG].total_events = 50
        self.capture_system.source_metrics[EventSource.AUDIT_LOG].captured_events = 48
        
        # Calculate rates
        await self.capture_system._calculate_capture_rates()
        
        # Verify overall rate
        assert self.capture_system.capture_metrics.capture_rate == 0.95
        
        # Verify source rate
        assert self.capture_system.source_metrics[EventSource.AUDIT_LOG].capture_rate == 0.96
    
    @pytest.mark.asyncio
    async def test_capture_rate_alerts(self):
        """Test capture rate alerting."""
        # Set low capture rate
        self.capture_system.capture_metrics.capture_rate = 0.85  # Below threshold
        self.capture_system.source_metrics[EventSource.AUDIT_LOG].capture_rate = 0.80
        self.capture_system.source_metrics[EventSource.AUDIT_LOG].total_events = 20  # Above minimum
        
        # Capture log messages
        with patch.object(self.capture_system.logger, 'warning') as mock_warning:
            await self.capture_system._check_capture_rate_alerts()
            
            # Verify alerts were triggered
            assert mock_warning.call_count >= 1
            
            # Check alert messages
            warning_calls = [call.args[0] for call in mock_warning.call_args_list]
            assert any("Low capture rate detected" in msg for msg in warning_calls)
    
    @pytest.mark.asyncio
    async def test_health_checks(self):
        """Test system health checks."""
        # Set up healthy system state
        self.capture_system.capture_metrics.capture_rate = 0.98
        
        # Mock active listeners
        for source in EventSource:
            self.capture_system.source_listeners[source] = True
        
        # Perform health check
        health_status = await self.capture_system._perform_health_checks()
        
        # Verify health status
        assert health_status['event_queue'] == 'healthy'
        assert health_status['event_listeners'] == 'healthy'
        assert health_status['capture_rate'] == 'healthy'
        assert health_status['processing_tasks'] in ['healthy', 'degraded']  # May vary based on task state
    
    def test_event_hash_calculation(self):
        """Test event hash calculation."""
        event_data = {
            'event_id': 'HASH_TEST_001',
            'source': EventSource.AUDIT_LOG.value,
            'timestamp': '2024-01-01T12:00:00',
            'tenant_id': self.tenant_id,
            'user_id': str(self.user_id),
            'extra_field': 'should_be_ignored'
        }
        
        # Calculate hash
        hash1 = self.capture_system._calculate_event_hash(event_data)
        
        # Calculate hash again with same data
        hash2 = self.capture_system._calculate_event_hash(event_data)
        
        # Hashes should be identical
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
        
        # Modify data and verify hash changes
        event_data['event_id'] = 'HASH_TEST_002'
        hash3 = self.capture_system._calculate_event_hash(event_data)
        
        assert hash1 != hash3
    
    def test_validation_rules(self):
        """Test validation rules."""
        
        # Register validation rules for testing
        self.capture_system.validation_rules = [
            self.capture_system._validate_required_fields,
            self.capture_system._validate_timestamp,
            self.capture_system._validate_data_integrity
        ]
        
        # Test required fields validation
        valid_data = {
            'event_id': 'VALID_001',
            'source': EventSource.AUDIT_LOG.value,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        invalid_data = {
            'source': EventSource.AUDIT_LOG.value
            # Missing event_id and timestamp
        }
        
        # Test validation
        assert asyncio.run(self.capture_system._validate_required_fields(valid_data)) is True
        assert asyncio.run(self.capture_system._validate_required_fields(invalid_data)) is False
        
        # Test timestamp validation
        future_data = {
            'event_id': 'FUTURE_001',
            'source': EventSource.AUDIT_LOG.value,
            'timestamp': (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        old_data = {
            'event_id': 'OLD_001',
            'source': EventSource.AUDIT_LOG.value,
            'timestamp': (datetime.utcnow() - timedelta(days=60)).isoformat()
        }
        
        assert asyncio.run(self.capture_system._validate_timestamp(valid_data)) is True
        assert asyncio.run(self.capture_system._validate_timestamp(future_data)) is False
        assert asyncio.run(self.capture_system._validate_timestamp(old_data)) is False
    
    def test_statistics_collection(self):
        """Test statistics collection."""
        # Set up test data
        self.capture_system.capture_metrics.total_events = 1000
        self.capture_system.capture_metrics.captured_events = 950
        self.capture_system.capture_metrics.failed_events = 30
        self.capture_system.capture_metrics.retry_events = 20
        self.capture_system.capture_metrics.capture_rate = 0.95
        
        # Add some source metrics
        self.capture_system.source_metrics[EventSource.AUDIT_LOG].total_events = 500
        self.capture_system.source_metrics[EventSource.AUDIT_LOG].captured_events = 480
        
        # Get statistics
        stats = self.capture_system.get_capture_statistics()
        
        # Verify structure
        assert 'overall_metrics' in stats
        assert 'source_metrics' in stats
        assert 'system_status' in stats
        
        # Verify overall metrics
        overall = stats['overall_metrics']
        assert overall['total_events'] == 1000
        assert overall['captured_events'] == 950
        assert overall['capture_rate'] == 0.95
        
        # Verify source metrics
        audit_metrics = stats['source_metrics'][EventSource.AUDIT_LOG.value]
        assert audit_metrics['total_events'] == 500
        assert audit_metrics['captured_events'] == 480
    
    def test_failed_events_retrieval(self):
        """Test failed events retrieval."""
        # Add some failed events
        for i in range(5):
            record = EventCaptureRecord(
                event_id=f'FAILED_{i}',
                source=EventSource.AUDIT_LOG,
                timestamp=datetime.utcnow(),
                status=CaptureStatus.FAILED,
                error_message=f"Error {i}",
                metadata={'tenant_id': self.tenant_id}
            )
            self.capture_system.failed_events.append(record)
        
        # Get failed events
        failed_events = self.capture_system.get_failed_events(limit=3)
        
        # Verify results
        assert len(failed_events) == 3
        assert all(event['status'] == 'failed' for event in failed_events)
        assert all('error_message' in event for event in failed_events)
    
    @pytest.mark.asyncio
    async def test_force_event_capture(self):
        """Test force event capture functionality."""
        event_data = {
            'event_id': 'FORCE_TEST_001',
            'source': EventSource.AUDIT_LOG.value,
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': self.tenant_id,
            'forced': True
        }
        
        # Test force capture
        success = await self.capture_system.force_event_capture(event_data)
        
        # Verify success
        assert success is True
        
        # Verify event was attempted to be queued (check put was called)
        self.capture_system.event_queue.put.assert_called_once_with(event_data)
        
        # Verify capture record was created
        assert event_data['event_id'] in self.capture_system.capture_records


class TestEventSourceListeners:
    """Test event source listeners functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.mock_security_monitor = Mock(spec=SecurityEventMonitor)
        self.mock_threat_detector = Mock(spec=AdvancedThreatDetector)
        
        # Mock Prometheus metrics and asyncio components to avoid conflicts
        with patch('src.security.complete_event_capture_system.PrometheusCounter') as mock_counter, \
             patch('src.security.complete_event_capture_system.Gauge') as mock_gauge, \
             patch('src.security.complete_event_capture_system.Histogram') as mock_histogram, \
             patch('asyncio.Queue') as mock_queue:
            
            mock_counter.return_value = Mock()
            mock_gauge.return_value = Mock()
            mock_histogram.return_value = Mock()
            
            # Mock asyncio.Queue to avoid event loop issues
            mock_queue_instance = Mock()
            mock_queue_instance.maxsize = 10000
            mock_queue_instance.qsize.return_value = 0
            mock_queue_instance.empty.return_value = True
            mock_queue_instance.put = AsyncMock()  # Make put method async
            mock_queue_instance.get = AsyncMock()  # Make get method async
            mock_queue.return_value = mock_queue_instance
            
            self.capture_system = CompleteEventCaptureSystem(
                self.mock_security_monitor,
                self.mock_threat_detector
            )
    
    @pytest.mark.asyncio
    async def test_audit_log_listener(self):
        """Test audit log listener functionality."""
        # Mock database session and query results
        mock_logs = [
            Mock(
                id="log_1",
                tenant_id="test_tenant",
                user_id=uuid4(),
                action=AuditAction.READ,
                resource_type="dataset",
                timestamp=datetime.utcnow(),
                details={"test": "data"}
            )
        ]
        
        with patch('src.security.complete_event_capture_system.get_db_session') as mock_get_db:
            mock_db = Mock()
            mock_db.__enter__ = Mock(return_value=mock_db)
            mock_db.__exit__ = Mock(return_value=None)
            mock_db.execute.return_value.scalars.return_value.all.return_value = mock_logs
            mock_get_db.return_value = mock_db
            
            # Start listener for a short time
            self.capture_system.capture_enabled = True
            
            # Create listener task
            listener_task = asyncio.create_task(self.capture_system._audit_log_listener())
            
            # Let it run briefly
            await asyncio.sleep(0.1)
            
            # Stop listener
            self.capture_system.capture_enabled = False
            
            # Wait for task to complete
            try:
                await asyncio.wait_for(listener_task, timeout=1.0)
            except asyncio.TimeoutError:
                listener_task.cancel()
            
            # Verify listener was active
            assert EventSource.AUDIT_LOG in self.capture_system.source_listeners
    
    @pytest.mark.asyncio
    async def test_real_time_monitor_listener(self):
        """Test real-time monitor listener functionality."""
        # Mock security events
        mock_events = [
            SecurityEvent(
                event_id="test_event_1",
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                threat_level=ThreatLevel.MEDIUM,
                tenant_id="test_tenant",
                user_id=uuid4(),
                ip_address="192.168.1.100",
                timestamp=datetime.utcnow(),
                description="Test suspicious activity",
                details={}
            )
        ]
        
        self.mock_security_monitor.get_active_events.return_value = mock_events
        
        # Start listener for a short time
        self.capture_system.capture_enabled = True
        
        # Create listener task
        listener_task = asyncio.create_task(self.capture_system._real_time_monitor_listener())
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Stop listener
        self.capture_system.capture_enabled = False
        
        # Wait for task to complete
        try:
            await asyncio.wait_for(listener_task, timeout=1.0)
        except asyncio.TimeoutError:
            listener_task.cancel()
        
        # Verify monitor was called
        self.mock_security_monitor.get_active_events.assert_called()


class TestCaptureSystemIntegration:
    """Test integration scenarios and end-to-end workflows."""
    
    def setup_method(self):
        """Setup test environment."""
        self.mock_security_monitor = Mock(spec=SecurityEventMonitor)
        self.mock_threat_detector = Mock(spec=AdvancedThreatDetector)
        
        # Mock Prometheus metrics and asyncio components to avoid conflicts
        with patch('src.security.complete_event_capture_system.PrometheusCounter') as mock_counter, \
             patch('src.security.complete_event_capture_system.Gauge') as mock_gauge, \
             patch('src.security.complete_event_capture_system.Histogram') as mock_histogram, \
             patch('asyncio.Queue') as mock_queue:
            
            mock_counter.return_value = Mock()
            mock_gauge.return_value = Mock()
            mock_histogram.return_value = Mock()
            
            # Mock asyncio.Queue to avoid event loop issues
            mock_queue_instance = Mock()
            mock_queue_instance.maxsize = 10000
            mock_queue_instance.qsize.return_value = 0
            mock_queue_instance.empty.return_value = True
            mock_queue_instance.put = AsyncMock()  # Make put method async
            mock_queue_instance.get = AsyncMock()  # Make get method async
            mock_queue.return_value = mock_queue_instance
            
            self.capture_system = CompleteEventCaptureSystem(
                self.mock_security_monitor,
                self.mock_threat_detector
            )
        
        self.tenant_id = "integration_test_tenant"
    
    @pytest.mark.asyncio
    async def test_end_to_end_event_capture_workflow(self):
        """Test complete end-to-end event capture workflow."""
        # Create multiple events from different sources
        events = [
            {
                'event_id': 'E2E_AUDIT_001',
                'source': EventSource.AUDIT_LOG.value,
                'timestamp': datetime.utcnow().isoformat(),
                'tenant_id': self.tenant_id,
                'action': 'read'
            },
            {
                'event_id': 'E2E_SEC_001',
                'source': EventSource.REAL_TIME_MONITOR.value,
                'timestamp': datetime.utcnow().isoformat(),
                'tenant_id': self.tenant_id,
                'event_type': 'brute_force_attack'
            },
            {
                'event_id': 'E2E_SYS_001',
                'source': EventSource.SYSTEM_LOG.value,
                'timestamp': datetime.utcnow().isoformat(),
                'tenant_id': self.tenant_id,
                'severity': 'warning'
            }
        ]
        
        # Enqueue all events
        for event in events:
            await self.capture_system._enqueue_event(event)
        
        # Verify all events were attempted to be queued
        assert self.capture_system.event_queue.put.call_count == 3
        
        # Verify capture records were created
        for event in events:
            assert event['event_id'] in self.capture_system.capture_records
            record = self.capture_system.capture_records[event['event_id']]
            assert record.status == CaptureStatus.PENDING
        
        # Process events (simulate processing)
        for event in events:
            await self.capture_system._process_captured_event(event)
        
        # Verify all events were processed
        for event in events:
            record = self.capture_system.capture_records[event['event_id']]
            assert record.status == CaptureStatus.CAPTURED
        
        # Verify metrics
        assert self.capture_system.capture_metrics.captured_events == 3
    
    @pytest.mark.asyncio
    async def test_high_volume_event_processing(self):
        """Test system performance under high event volume."""
        # Generate large number of events
        event_count = 1000
        events = []
        
        for i in range(event_count):
            event = {
                'event_id': f'VOLUME_TEST_{i}',
                'source': EventSource.AUDIT_LOG.value,
                'timestamp': datetime.utcnow().isoformat(),
                'tenant_id': self.tenant_id,
                'sequence': i
            }
            events.append(event)
        
        # Measure enqueuing time
        start_time = datetime.utcnow()
        
        for event in events:
            await self.capture_system._enqueue_event(event)
        
        enqueue_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Verify all events were attempted to be queued
        assert self.capture_system.event_queue.put.call_count == event_count
        
        # Measure processing time
        start_time = datetime.utcnow()
        
        # Process events in batches to simulate real-world scenario
        batch_size = 50
        for i in range(0, event_count, batch_size):
            batch_tasks = []
            for j in range(min(batch_size, event_count - i)):
                event_idx = i + j
                if event_idx < len(events):
                    task = asyncio.create_task(
                        self.capture_system._process_captured_event(events[event_idx])
                    )
                    batch_tasks.append(task)
            
            # Wait for batch to complete
            if batch_tasks:
                await asyncio.gather(*batch_tasks)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Performance assertions
        assert enqueue_time < 5.0  # Should enqueue 1000 events in under 5 seconds
        assert processing_time < 10.0  # Should process 1000 events in under 10 seconds
        
        # Verify all events were processed
        assert self.capture_system.capture_metrics.captured_events == event_count
    
    @pytest.mark.asyncio
    async def test_failure_recovery_scenarios(self):
        """Test system recovery from various failure scenarios."""
        
        # Register validation rules for testing
        self.capture_system.validation_rules = [
            self.capture_system._validate_required_fields,
            self.capture_system._validate_timestamp,
            self.capture_system._validate_data_integrity
        ]
        
        # Scenario 1: Processing failures with retry
        failing_event = {
            'event_id': 'FAIL_TEST_001',
            'source': EventSource.AUDIT_LOG.value,
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': self.tenant_id
        }
        
        # Create record and simulate failure
        record = EventCaptureRecord(
            event_id=failing_event['event_id'],
            source=EventSource.AUDIT_LOG,
            timestamp=datetime.utcnow(),
            status=CaptureStatus.FAILED,
            attempts=1,
            error_message="Simulated failure",
            metadata=failing_event
        )
        
        self.capture_system.capture_records[record.event_id] = record
        
        # Mock successful retry
        with patch.object(self.capture_system, '_process_captured_event', new_callable=AsyncMock):
            await self.capture_system._retry_event_capture(record)
            
            # Verify retry was attempted
            assert record.status == CaptureStatus.RETRY
            assert record.attempts == 2
        
        # Scenario 2: Validation failures
        invalid_event = {
            'event_id': 'INVALID_TEST_001',
            'source': EventSource.AUDIT_LOG.value,
            # Missing required timestamp
            'tenant_id': self.tenant_id
        }
        
        invalid_record = EventCaptureRecord(
            event_id=invalid_event['event_id'],
            source=EventSource.AUDIT_LOG,
            timestamp=datetime.utcnow(),
            status=CaptureStatus.CAPTURED,
            metadata=invalid_event
        )
        
        await self.capture_system._validate_captured_event(invalid_record)
        
        # Verify validation failure was handled
        assert invalid_record.status == CaptureStatus.FAILED
        assert "Validation failed" in invalid_record.error_message
        assert self.capture_system.capture_metrics.validation_failures == 1
    
    @pytest.mark.asyncio
    async def test_capture_rate_monitoring(self):
        """Test capture rate monitoring and alerting."""
        # Set up scenario with mixed success/failure rates
        total_events = 100
        successful_events = 85  # 85% success rate
        
        # Simulate events
        for i in range(total_events):
            event_data = {
                'event_id': f'MONITOR_TEST_{i}',
                'source': EventSource.AUDIT_LOG.value,
                'timestamp': datetime.utcnow().isoformat(),
                'tenant_id': self.tenant_id
            }
            
            await self.capture_system._enqueue_event(event_data)
            
            # Simulate processing success/failure
            if i < successful_events:
                # Successful processing
                await self.capture_system._process_captured_event(event_data)
            else:
                # Failed processing - manually update metrics since we're mocking
                record = self.capture_system.capture_records[event_data['event_id']]
                record.status = CaptureStatus.FAILED
                record.error_message = "Simulated failure"
                self.capture_system.capture_metrics.failed_events += 1
        
        # Manually set total events since we're mocking the queue
        self.capture_system.capture_metrics.total_events = total_events
        
        # Calculate capture rates
        await self.capture_system._calculate_capture_rates()
        
        # Verify metrics
        assert self.capture_system.capture_metrics.total_events == total_events
        assert self.capture_system.capture_metrics.captured_events == successful_events
        assert self.capture_system.capture_metrics.capture_rate == 0.85
        
        # Test alerting for low capture rate
        with patch.object(self.capture_system.logger, 'warning') as mock_warning:
            await self.capture_system._check_capture_rate_alerts()
            
            # Should trigger alert since 85% < 95% threshold
            mock_warning.assert_called()
            alert_message = mock_warning.call_args[0][0]
            assert "Low capture rate" in alert_message


class TestCaptureSystemAPI:
    """Test capture system API integration."""
    
    def setup_method(self):
        """Setup test environment."""
        self.tenant_id = "api_test_tenant"
    
    @pytest.mark.asyncio
    async def test_initialization_function(self):
        """Test capture system initialization function."""
        mock_security_monitor = Mock(spec=SecurityEventMonitor)
        mock_threat_detector = Mock(spec=AdvancedThreatDetector)
        
        # Test initialization with mocked Prometheus metrics
        with patch('src.security.complete_event_capture_system.PrometheusCounter') as mock_counter, \
             patch('src.security.complete_event_capture_system.Gauge') as mock_gauge, \
             patch('src.security.complete_event_capture_system.Histogram') as mock_histogram, \
             patch('src.security.complete_event_capture_system.CompleteEventCaptureSystem') as mock_class:
            
            mock_counter.return_value = Mock()
            mock_gauge.return_value = Mock()
            mock_histogram.return_value = Mock()
            
            mock_instance = Mock()
            mock_instance.start_capture_system = AsyncMock()
            mock_class.return_value = mock_instance
            
            result = await initialize_complete_capture_system(
                mock_security_monitor,
                mock_threat_detector
            )
            
            # Verify initialization
            mock_class.assert_called_once_with(mock_security_monitor, mock_threat_detector)
            mock_instance.start_capture_system.assert_called_once()
            assert result == mock_instance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])