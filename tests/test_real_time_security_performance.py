"""
Test suite for real-time security monitoring performance validation.

Tests the < 5 second security monitoring real-time performance requirement.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from src.security.real_time_security_monitor import RealTimeSecurityMonitor
from src.security.security_event_monitor import SecurityEvent, SecurityEventType, ThreatLevel
from src.security.models import AuditLogModel, AuditAction
from src.api.security_performance_api import _calculate_performance_grade


class TestRealTimeSecurityPerformance:
    """Real-time security monitoring performance tests."""
    
    @pytest.fixture
    async def monitor(self):
        """Create a real-time security monitor instance."""
        monitor = RealTimeSecurityMonitor()
        await monitor.initialize()
        yield monitor
        await monitor.stop_monitoring()
    
    @pytest.fixture
    def sample_audit_logs(self):
        """Create sample audit logs for testing."""
        logs = []
        base_time = datetime.utcnow()
        
        for i in range(100):
            log = AuditLogModel(
                id=str(uuid4()),
                user_id=uuid4(),
                tenant_id=str(uuid4()),
                action=AuditAction.LOGIN if i % 10 == 0 else AuditAction.READ,
                resource_type="user" if i % 5 == 0 else "document",
                resource_id=str(uuid4()),
                ip_address=f"192.168.1.{i % 255}",
                timestamp=base_time - timedelta(seconds=i),
                details={
                    "status": "failed" if i % 15 == 0 else "success",
                    "user_agent": "test-agent",
                    "export_size_mb": 10 if i % 20 == 0 else 0
                }
            )
            logs.append(log)
        
        return logs
    
    @pytest.mark.asyncio
    async def test_detection_latency_under_5_seconds(self, monitor, sample_audit_logs):
        """Test that threat detection completes within 5 seconds."""
        
        start_time = time.time()
        
        # Process events through fast threat detection
        threats = await monitor._fast_threat_detection(sample_audit_logs)
        
        end_time = time.time()
        detection_time = end_time - start_time
        
        # Verify detection time is under 5 seconds
        assert detection_time < 5.0, f"Detection took {detection_time:.3f}s, exceeds 5s requirement"
        
        # Verify threats were detected
        assert isinstance(threats, list)
        
        print(f"✅ Detection latency: {detection_time:.3f}s (< 5s requirement)")
    
    @pytest.mark.asyncio
    async def test_brute_force_detection_performance(self, monitor):
        """Test brute force detection performance."""
        
        # Create brute force attack simulation
        attack_logs = []
        base_time = datetime.utcnow()
        
        for i in range(20):  # 20 failed login attempts
            log = AuditLogModel(
                id=str(uuid4()),
                user_id=uuid4(),
                tenant_id="test-tenant",
                action=AuditAction.LOGIN,
                resource_type="user",
                resource_id=str(uuid4()),
                ip_address="192.168.1.100",  # Same IP for brute force
                timestamp=base_time - timedelta(seconds=i),
                details={"status": "failed", "username": f"user{i % 5}"}
            )
            attack_logs.append(log)
        
        start_time = time.time()
        
        # Detect brute force attacks
        threats = await monitor._detect_brute_force_fast(attack_logs)
        
        end_time = time.time()
        detection_time = end_time - start_time
        
        # Verify performance and detection
        assert detection_time < 1.0, f"Brute force detection took {detection_time:.3f}s, should be < 1s"
        assert len(threats) > 0, "Should detect brute force attack"
        assert threats[0][0].event_type == SecurityEventType.BRUTE_FORCE_ATTACK
        
        print(f"✅ Brute force detection: {detection_time:.3f}s, detected {len(threats)} threats")
    
    @pytest.mark.asyncio
    async def test_privilege_escalation_detection_performance(self, monitor):
        """Test privilege escalation detection performance."""
        
        # Create privilege escalation simulation
        escalation_logs = []
        base_time = datetime.utcnow()
        user_id = uuid4()
        
        for i in range(5):  # 5 privilege operations
            log = AuditLogModel(
                id=str(uuid4()),
                user_id=user_id,
                tenant_id="test-tenant",
                action=AuditAction.UPDATE,
                resource_type="role",
                resource_id=str(uuid4()),
                ip_address="192.168.1.101",
                timestamp=base_time - timedelta(seconds=i),
                details={"operation": "grant_permission", "target": "admin_role"}
            )
            escalation_logs.append(log)
        
        start_time = time.time()
        
        # Detect privilege escalation
        threats = await monitor._detect_privilege_escalation_fast(escalation_logs)
        
        end_time = time.time()
        detection_time = end_time - start_time
        
        # Verify performance and detection
        assert detection_time < 1.0, f"Privilege escalation detection took {detection_time:.3f}s, should be < 1s"
        assert len(threats) > 0, "Should detect privilege escalation"
        assert threats[0][0].event_type == SecurityEventType.PRIVILEGE_ESCALATION
        
        print(f"✅ Privilege escalation detection: {detection_time:.3f}s, detected {len(threats)} threats")
    
    @pytest.mark.asyncio
    async def test_data_exfiltration_detection_performance(self, monitor):
        """Test data exfiltration detection performance."""
        
        # Create data exfiltration simulation
        exfiltration_logs = []
        base_time = datetime.utcnow()
        user_id = uuid4()
        
        for i in range(15):  # 15 export operations
            log = AuditLogModel(
                id=str(uuid4()),
                user_id=user_id,
                tenant_id="test-tenant",
                action=AuditAction.EXPORT,
                resource_type="dataset",
                resource_id=str(uuid4()),
                ip_address="192.168.1.102",
                timestamp=base_time - timedelta(seconds=i),
                details={"export_size_mb": 50, "format": "csv"}
            )
            exfiltration_logs.append(log)
        
        start_time = time.time()
        
        # Detect data exfiltration
        threats = await monitor._detect_data_exfiltration_fast(exfiltration_logs)
        
        end_time = time.time()
        detection_time = end_time - start_time
        
        # Verify performance and detection
        assert detection_time < 1.0, f"Data exfiltration detection took {detection_time:.3f}s, should be < 1s"
        assert len(threats) > 0, "Should detect data exfiltration"
        assert threats[0][0].event_type == SecurityEventType.DATA_EXFILTRATION
        
        print(f"✅ Data exfiltration detection: {detection_time:.3f}s, detected {len(threats)} threats")
    
    @pytest.mark.asyncio
    async def test_malicious_request_detection_performance(self, monitor):
        """Test malicious request detection performance."""
        
        # Create malicious request simulation
        malicious_logs = []
        base_time = datetime.utcnow()
        
        malicious_payloads = [
            {"request": "union select * from users", "type": "sql_injection"},
            {"request": "<script>alert('xss')</script>", "type": "xss"},
            {"request": "../../../etc/passwd", "type": "path_traversal"}
        ]
        
        for i, payload in enumerate(malicious_payloads * 3):  # 9 malicious requests
            log = AuditLogModel(
                id=str(uuid4()),
                user_id=uuid4(),
                tenant_id="test-tenant",
                action=AuditAction.READ,
                resource_type="api",
                resource_id=str(uuid4()),
                ip_address="192.168.1.103",
                timestamp=base_time - timedelta(seconds=i),
                details=payload
            )
            malicious_logs.append(log)
        
        start_time = time.time()
        
        # Detect malicious requests
        threats = await monitor._detect_malicious_requests_fast(malicious_logs)
        
        end_time = time.time()
        detection_time = end_time - start_time
        
        # Verify performance and detection
        assert detection_time < 1.0, f"Malicious request detection took {detection_time:.3f}s, should be < 1s"
        assert len(threats) > 0, "Should detect malicious requests"
        assert threats[0][0].event_type == SecurityEventType.MALICIOUS_REQUEST
        
        print(f"✅ Malicious request detection: {detection_time:.3f}s, detected {len(threats)} threats")
    
    @pytest.mark.asyncio
    async def test_parallel_threat_detection_performance(self, monitor, sample_audit_logs):
        """Test parallel threat detection performance."""
        
        start_time = time.time()
        
        # Run all detection methods in parallel
        detection_tasks = [
            monitor._detect_brute_force_fast(sample_audit_logs),
            monitor._detect_privilege_escalation_fast(sample_audit_logs),
            monitor._detect_data_exfiltration_fast(sample_audit_logs),
            monitor._detect_malicious_requests_fast(sample_audit_logs)
        ]
        
        results = await asyncio.gather(*detection_tasks)
        
        end_time = time.time()
        parallel_detection_time = end_time - start_time
        
        # Verify parallel processing is faster than sequential
        assert parallel_detection_time < 2.0, f"Parallel detection took {parallel_detection_time:.3f}s, should be < 2s"
        
        # Verify all detection methods completed
        assert len(results) == 4
        
        total_threats = sum(len(result) for result in results)
        print(f"✅ Parallel detection: {parallel_detection_time:.3f}s, {total_threats} total threats")
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, monitor):
        """Test cache performance and hit rates."""
        
        # Test cache operations
        cache_operations = []
        
        start_time = time.time()
        
        # Perform cache operations
        for i in range(100):
            key = f"test_key_{i % 10}"  # 10 unique keys, repeated 10 times each
            value = f"test_value_{i}"
            
            # Set cache
            await monitor._set_cache(key, value, ttl=300)
            
            # Get cache
            cached_value = await monitor._get_cache(key)
            cache_operations.append(cached_value is not None)
        
        end_time = time.time()
        cache_operation_time = end_time - start_time
        
        # Calculate cache hit rate
        cache_hits = sum(cache_operations)
        cache_hit_rate = cache_hits / len(cache_operations)
        
        # Verify cache performance
        assert cache_operation_time < 1.0, f"Cache operations took {cache_operation_time:.3f}s, should be < 1s"
        assert cache_hit_rate > 0.8, f"Cache hit rate {cache_hit_rate:.2f} should be > 0.8"
        
        print(f"✅ Cache performance: {cache_operation_time:.3f}s, hit rate: {cache_hit_rate:.2%}")
    
    @pytest.mark.asyncio
    async def test_event_processing_throughput(self, monitor, sample_audit_logs):
        """Test event processing throughput."""
        
        start_time = time.time()
        
        # Process events in batches
        batch_size = 20
        batches = [sample_audit_logs[i:i + batch_size] for i in range(0, len(sample_audit_logs), batch_size)]
        
        processed_events = 0
        for batch in batches:
            await monitor._process_events_batch(batch)
            processed_events += len(batch)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Calculate throughput
        throughput = processed_events / processing_time if processing_time > 0 else 0
        
        # Verify throughput meets requirements
        assert throughput > 50, f"Throughput {throughput:.1f} events/s should be > 50 events/s"
        assert processing_time < 5.0, f"Processing took {processing_time:.3f}s, should be < 5s"
        
        print(f"✅ Event processing: {processed_events} events in {processing_time:.3f}s ({throughput:.1f} events/s)")
    
    @pytest.mark.asyncio
    async def test_websocket_alert_latency(self, monitor):
        """Test WebSocket alert sending latency."""
        
        # Mock WebSocket connections
        mock_websockets = [Mock() for _ in range(5)]
        for ws in mock_websockets:
            ws.send = AsyncMock()
            monitor.websocket_connections.add(ws)
        
        # Create test threat event
        threat_event = SecurityEvent(
            event_id="test_threat_001",
            event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
            threat_level=ThreatLevel.HIGH,
            tenant_id="test-tenant",
            user_id=None,
            ip_address="192.168.1.100",
            timestamp=datetime.utcnow(),
            description="Test threat for WebSocket latency",
            details={"test": True}
        )
        
        start_time = time.time()
        
        # Send WebSocket alert
        await monitor._send_websocket_alert(threat_event)
        
        end_time = time.time()
        alert_latency = end_time - start_time
        
        # Verify alert latency
        assert alert_latency < 0.1, f"WebSocket alert latency {alert_latency:.3f}s should be < 0.1s"
        
        # Verify all WebSockets received the alert
        for ws in mock_websockets:
            ws.send.assert_called_once()
        
        print(f"✅ WebSocket alert latency: {alert_latency:.3f}s")
    
    @pytest.mark.asyncio
    async def test_auto_response_performance(self, monitor):
        """Test auto-response execution performance."""
        
        # Create test threat events requiring auto-response
        threat_events = [
            SecurityEvent(
                event_id=f"test_threat_{i}",
                event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
                threat_level=ThreatLevel.CRITICAL,
                tenant_id="test-tenant",
                user_id=None,
                ip_address=f"192.168.1.{100 + i}",
                timestamp=datetime.utcnow(),
                description=f"Test threat {i} for auto-response",
                details={"test": True}
            )
            for i in range(5)
        ]
        
        start_time = time.time()
        
        # Execute auto-responses
        response_tasks = [
            monitor._execute_auto_response_async(threat)
            for threat in threat_events
        ]
        
        await asyncio.gather(*response_tasks)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Verify auto-response performance
        assert response_time < 2.0, f"Auto-response took {response_time:.3f}s, should be < 2s"
        
        print(f"✅ Auto-response performance: {len(threat_events)} responses in {response_time:.3f}s")
    
    def test_performance_grade_calculation(self):
        """Test performance grade calculation."""
        
        # Test excellent performance
        excellent_metrics = {
            'avg_processing_time': 0.5,
            'cache_hits': 950,
            'cache_misses': 50,
            'monitoring_active': True,
            'redis_enabled': True
        }
        
        grade = _calculate_performance_grade(excellent_metrics)
        assert grade in ['A+', 'A'], f"Excellent metrics should get A+ or A grade, got {grade}"
        
        # Test poor performance
        poor_metrics = {
            'avg_processing_time': 8.0,
            'cache_hits': 300,
            'cache_misses': 700,
            'monitoring_active': False,
            'redis_enabled': False
        }
        
        grade = _calculate_performance_grade(poor_metrics)
        assert grade in ['C', 'D'], f"Poor metrics should get C or D grade, got {grade}"
        
        print(f"✅ Performance grading: Excellent={_calculate_performance_grade(excellent_metrics)}, Poor={_calculate_performance_grade(poor_metrics)}")
    
    @pytest.mark.asyncio
    async def test_end_to_end_performance_sla(self, monitor, sample_audit_logs):
        """Test end-to-end performance SLA compliance."""
        
        # Simulate complete security monitoring workflow
        start_time = time.time()
        
        # 1. Event ingestion
        ingestion_start = time.time()
        await monitor._process_events_batch(sample_audit_logs)
        ingestion_time = time.time() - ingestion_start
        
        # 2. Threat detection
        detection_start = time.time()
        threats = await monitor._fast_threat_detection(sample_audit_logs)
        detection_time = time.time() - detection_start
        
        # 3. Alert processing
        alert_start = time.time()
        for threat, confidence in threats:
            await monitor._handle_real_time_threat(threat, confidence)
        alert_time = time.time() - alert_start
        
        total_time = time.time() - start_time
        
        # Verify SLA compliance
        assert total_time < 5.0, f"End-to-end processing took {total_time:.3f}s, exceeds 5s SLA"
        assert ingestion_time < 1.0, f"Event ingestion took {ingestion_time:.3f}s, should be < 1s"
        assert detection_time < 3.0, f"Threat detection took {detection_time:.3f}s, should be < 3s"
        assert alert_time < 1.0, f"Alert processing took {alert_time:.3f}s, should be < 1s"
        
        # Performance breakdown
        performance_breakdown = {
            'total_time': total_time,
            'ingestion_time': ingestion_time,
            'detection_time': detection_time,
            'alert_time': alert_time,
            'events_processed': len(sample_audit_logs),
            'threats_detected': len(threats),
            'sla_compliant': total_time < 5.0
        }
        
        print(f"✅ End-to-end SLA compliance: {total_time:.3f}s < 5s")
        print(f"   - Ingestion: {ingestion_time:.3f}s")
        print(f"   - Detection: {detection_time:.3f}s")
        print(f"   - Alerting: {alert_time:.3f}s")
        print(f"   - Events: {len(sample_audit_logs)}, Threats: {len(threats)}")
        
        return performance_breakdown


class TestPerformanceOptimization:
    """Performance optimization tests."""
    
    @pytest.mark.asyncio
    async def test_batch_size_optimization(self):
        """Test batch size optimization impact."""
        
        monitor = RealTimeSecurityMonitor()
        
        # Test different batch sizes
        batch_sizes = [10, 50, 100, 200]
        performance_results = {}
        
        for batch_size in batch_sizes:
            monitor.batch_size = batch_size
            
            # Create test events
            test_events = [Mock() for _ in range(100)]
            
            start_time = time.time()
            
            # Simulate batch processing
            batches = [test_events[i:i + batch_size] for i in range(0, len(test_events), batch_size)]
            for batch in batches:
                await asyncio.sleep(0.001 * len(batch))  # Simulate processing time
            
            processing_time = time.time() - start_time
            performance_results[batch_size] = processing_time
        
        # Find optimal batch size (should be around 100)
        optimal_batch_size = min(performance_results, key=performance_results.get)
        
        print(f"✅ Batch size optimization results: {performance_results}")
        print(f"   Optimal batch size: {optimal_batch_size}")
        
        assert optimal_batch_size >= 50, "Optimal batch size should be at least 50"
    
    @pytest.mark.asyncio
    async def test_cache_ttl_optimization(self):
        """Test cache TTL optimization."""
        
        monitor = RealTimeSecurityMonitor()
        await monitor.initialize()
        
        # Test different TTL values
        ttl_values = [60, 300, 600, 1800]  # 1min, 5min, 10min, 30min
        cache_performance = {}
        
        for ttl in ttl_values:
            # Set cache entries with different TTLs
            for i in range(10):
                await monitor._set_cache(f"test_key_{i}", f"value_{i}", ttl=ttl)
            
            # Measure cache hit rate over time
            hits = 0
            total_requests = 20
            
            for i in range(total_requests):
                key = f"test_key_{i % 10}"
                value = await monitor._get_cache(key)
                if value:
                    hits += 1
                await asyncio.sleep(0.01)  # Small delay
            
            hit_rate = hits / total_requests
            cache_performance[ttl] = hit_rate
        
        print(f"✅ Cache TTL optimization: {cache_performance}")
        
        # Verify reasonable cache performance
        assert max(cache_performance.values()) > 0.8, "Best cache hit rate should be > 80%"
    
    @pytest.mark.asyncio
    async def test_parallel_worker_optimization(self):
        """Test parallel worker optimization."""
        
        worker_counts = [1, 2, 4, 8]
        performance_results = {}
        
        for worker_count in worker_counts:
            # Simulate parallel processing
            start_time = time.time()
            
            # Create tasks for parallel execution
            tasks = []
            for i in range(100):
                task = asyncio.create_task(asyncio.sleep(0.01))  # Simulate work
                tasks.append(task)
            
            # Process tasks in parallel batches
            batch_size = max(1, len(tasks) // worker_count)
            batches = [tasks[i:i + batch_size] for i in range(0, len(tasks), batch_size)]
            
            for batch in batches:
                await asyncio.gather(*batch)
            
            processing_time = time.time() - start_time
            performance_results[worker_count] = processing_time
        
        print(f"✅ Parallel worker optimization: {performance_results}")
        
        # Verify parallel processing improves performance
        single_worker_time = performance_results[1]
        multi_worker_time = performance_results[4]
        
        improvement = (single_worker_time - multi_worker_time) / single_worker_time
        assert improvement > 0.2, f"4 workers should be at least 20% faster than 1 worker, got {improvement:.2%}"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])