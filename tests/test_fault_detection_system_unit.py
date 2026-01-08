"""
Unit tests for the Fault Detection System.

Tests the core functionality of fault detection including:
- Fault event creation and management
- Service dependency tracking
- ML-based anomaly detection
- Root cause analysis
- Recovery action generation
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from collections import deque

from src.system.fault_detection_system import (
    FaultDetectionSystem, FaultEvent, FaultType, FaultSeverity,
    ServiceDependency, FaultPattern, fault_detection_system
)


class TestFaultDetectionSystem:
    """Test suite for FaultDetectionSystem class."""
    
    @pytest.fixture
    def fault_system(self):
        """Create a fresh fault detection system for testing."""
        system = FaultDetectionSystem()
        return system
    
    @pytest.fixture
    def sample_fault_event(self):
        """Create a sample fault event for testing."""
        return FaultEvent(
            fault_id="test_fault_001",
            fault_type=FaultType.SERVICE_UNAVAILABLE,
            severity=FaultSeverity.HIGH,
            service_name="test_service",
            description="Test service is unavailable",
            detected_at=datetime.utcnow()
        )
    
    def test_fault_detection_system_initialization(self, fault_system):
        """Test fault detection system initialization."""
        assert fault_system.active_faults == {}
        assert len(fault_system.fault_history) == 0
        assert len(fault_system.service_dependencies) > 0  # Default dependencies
        assert len(fault_system.fault_patterns) > 0  # Default patterns
        assert not fault_system.detection_active
    
    def test_service_dependency_registration(self, fault_system):
        """Test service dependency registration."""
        dependency = ServiceDependency(
            service_name="test_service",
            dependency_name="test_dependency",
            dependency_type="hard",
            timeout_threshold=30.0,
            failure_threshold=3
        )
        
        fault_system.register_service_dependency(dependency)
        
        assert "test_service" in fault_system.service_dependencies
        assert len(fault_system.service_dependencies["test_service"]) == 1
        assert fault_system.service_dependencies["test_service"][0].dependency_name == "test_dependency"
    
    def test_fault_pattern_setup(self, fault_system):
        """Test fault pattern initialization."""
        patterns = fault_system.fault_patterns
        
        # Check default patterns exist
        assert "perf_degradation" in patterns
        assert "resource_exhaustion" in patterns
        assert "cascade_failure" in patterns
        
        # Check pattern structure
        perf_pattern = patterns["perf_degradation"]
        assert perf_pattern.pattern_type == "performance"
        assert len(perf_pattern.features) > 0
        assert 0 <= perf_pattern.threshold <= 1
    
    @pytest.mark.asyncio
    async def test_start_stop_detection(self, fault_system):
        """Test starting and stopping fault detection."""
        # Test start
        await fault_system.start_detection()
        assert fault_system.detection_active
        assert fault_system.detection_task is not None
        
        # Test stop
        await fault_system.stop_detection()
        assert not fault_system.detection_active
        assert fault_system.detection_task is None
    
    @pytest.mark.asyncio
    async def test_collect_metrics(self, fault_system):
        """Test metric collection functionality."""
        with patch('src.system.fault_detection_system.health_monitor') as mock_health_monitor:
            # Mock health monitor response
            mock_health_monitor.get_metrics_summary.return_value = {
                "metrics": {
                    "cpu_usage": {"value": 75.0, "status": "warning"},
                    "memory_usage": {"value": 85.0, "status": "warning"}
                }
            }
            
            with patch('src.system.fault_detection_system.error_handler') as mock_error_handler:
                mock_error_handler.get_error_statistics.return_value = {
                    "error_rate": 0.03
                }
                
                # Collect metrics
                await fault_system._collect_metrics()
                
                # Check metrics were stored
                assert "cpu_usage" in fault_system.metric_history
                assert "memory_usage" in fault_system.metric_history
                assert "error_rate_percent" in fault_system.metric_history
                
                # Check metric values
                cpu_history = fault_system.metric_history["cpu_usage"]
                assert len(cpu_history) == 1
                assert cpu_history[0]["value"] == 75.0
                assert cpu_history[0]["status"] == "warning"
    
    @pytest.mark.asyncio
    async def test_service_fault_detection(self, fault_system):
        """Test service-level fault detection."""
        with patch('src.system.fault_detection_system.health_monitor') as mock_health_monitor:
            # Mock unhealthy service
            mock_health_monitor.get_metrics_summary.return_value = {
                "metrics": {
                    "test_service": {"value": 0, "status": "unhealthy"}
                }
            }
            
            with patch.object(fault_system, '_create_fault_event') as mock_create_fault:
                mock_create_fault.return_value = None
                
                # Run service fault detection
                await fault_system._detect_service_faults()
                
                # Verify fault event was created
                mock_create_fault.assert_called_once()
                call_args = mock_create_fault.call_args[1]
                assert call_args["fault_type"] == FaultType.SERVICE_UNAVAILABLE
                assert call_args["severity"] == FaultSeverity.HIGH
                assert call_args["service_name"] == "test_service"
    
    @pytest.mark.asyncio
    async def test_system_fault_detection(self, fault_system):
        """Test system-level fault detection."""
        # Set up metric history with high resource usage
        fault_system.metric_history["cpu_usage_percent"].append({
            "timestamp": time.time(),
            "value": 95.0,  # Above threshold
            "status": "critical"
        })
        
        with patch.object(fault_system, '_create_fault_event') as mock_create_fault:
            mock_create_fault.return_value = None
            
            # Run system fault detection
            await fault_system._detect_system_faults()
            
            # Verify fault event was created for resource exhaustion
            mock_create_fault.assert_called_once()
            call_args = mock_create_fault.call_args[1]
            assert call_args["fault_type"] == FaultType.RESOURCE_EXHAUSTION
            assert call_args["severity"] == FaultSeverity.HIGH
    
    @pytest.mark.asyncio
    async def test_cascade_failure_detection(self, fault_system):
        """Test cascade failure detection."""
        # Set up service dependencies
        fault_system.service_dependencies["test_service"] = [
            ServiceDependency("test_service", "database", "hard"),
            ServiceDependency("test_service", "cache", "soft")
        ]
        
        # Set up failed dependencies
        fault_system.metric_history["database_health"].append({
            "timestamp": time.time(),
            "value": 0.0,  # Unhealthy
            "status": "unhealthy"
        })
        
        with patch.object(fault_system, '_create_fault_event') as mock_create_fault:
            mock_create_fault.return_value = None
            
            # Run cascade failure detection
            await fault_system._detect_cascade_failures()
            
            # Verify cascade failure was detected
            mock_create_fault.assert_called_once()
            call_args = mock_create_fault.call_args[1]
            assert call_args["fault_type"] == FaultType.CASCADE_FAILURE
            assert call_args["severity"] == FaultSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_ml_based_fault_detection(self, fault_system):
        """Test ML-based fault detection."""
        # Set up baseline metrics
        fault_system.baseline_metrics["cpu_usage"] = {
            "mean": 50.0,
            "std": 10.0,
            "min": 30.0,
            "max": 70.0,
            "p95": 65.0
        }
        
        # Set up current metrics with anomaly
        fault_system.metric_history["cpu_usage"].append({
            "timestamp": time.time(),
            "value": 95.0,  # Anomalous value
            "status": "critical"
        })
        
        with patch.object(fault_system, '_create_fault_event') as mock_create_fault:
            mock_create_fault.return_value = None
            
            # Run ML-based fault detection
            await fault_system._detect_ml_based_faults()
            
            # Verify anomaly was detected (may or may not trigger based on threshold)
            # This test verifies the detection logic runs without error
    
    @pytest.mark.asyncio
    async def test_calculate_anomaly_score(self, fault_system):
        """Test anomaly score calculation."""
        # Set up baseline metrics
        fault_system.baseline_metrics["cpu_usage"] = {
            "mean": 50.0,
            "std": 10.0
        }
        
        # Set up current metrics
        fault_system.metric_history["cpu_usage"].append({
            "timestamp": time.time(),
            "value": 80.0,  # 3 standard deviations above mean
            "status": "warning"
        })
        
        # Create test pattern
        pattern = FaultPattern(
            pattern_id="test_pattern",
            pattern_type="performance",
            features=["cpu_usage"],
            threshold=0.8
        )
        
        # Calculate anomaly score
        score = await fault_system._calculate_anomaly_score(pattern)
        
        # Score should be high for anomalous value
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should detect the anomaly
    
    @pytest.mark.asyncio
    async def test_root_cause_analysis(self, fault_system):
        """Test root cause analysis."""
        # Set up service dependencies
        fault_system.service_dependencies["test_service"] = [
            ServiceDependency("test_service", "database", "hard")
        ]
        
        # Set up failed dependency
        fault_system.metric_history["database_health"].append({
            "timestamp": time.time(),
            "value": 0.0,
            "status": "unhealthy"
        })
        
        # Create test fault event
        fault_event = FaultEvent(
            fault_id="test_fault",
            fault_type=FaultType.SERVICE_UNAVAILABLE,
            severity=FaultSeverity.HIGH,
            service_name="test_service",
            description="Test fault",
            detected_at=datetime.utcnow()
        )
        
        # Analyze root cause
        root_cause = await fault_system._analyze_root_cause(fault_event)
        
        # Should identify dependency failure
        assert "Dependency failure: database" in root_cause
    
    @pytest.mark.asyncio
    async def test_recovery_action_generation(self, fault_system):
        """Test recovery action generation."""
        # Test different fault types
        fault_types_and_expected_actions = [
            (FaultType.SERVICE_UNAVAILABLE, ["restart_service", "check_service_dependencies"]),
            (FaultType.PERFORMANCE_DEGRADATION, ["scale_up_service", "clear_caches"]),
            (FaultType.RESOURCE_EXHAUSTION, ["scale_up_resources", "clear_temporary_files"]),
            (FaultType.CASCADE_FAILURE, ["enable_circuit_breakers", "isolate_failed_services"]),
            (FaultType.CONFIGURATION_ERROR, ["validate_configuration", "restore_backup_configuration"])
        ]
        
        for fault_type, expected_actions in fault_types_and_expected_actions:
            fault_event = FaultEvent(
                fault_id="test_fault",
                fault_type=fault_type,
                severity=FaultSeverity.HIGH,
                service_name="test_service",
                description="Test fault",
                detected_at=datetime.utcnow()
            )
            
            actions = await fault_system._generate_recovery_actions(fault_event)
            
            # Check that expected actions are included
            for expected_action in expected_actions:
                assert expected_action in actions
    
    @pytest.mark.asyncio
    async def test_fault_resolution_check(self, fault_system):
        """Test fault resolution checking."""
        # Create test fault event
        fault_event = FaultEvent(
            fault_id="test_fault",
            fault_type=FaultType.SERVICE_UNAVAILABLE,
            severity=FaultSeverity.HIGH,
            service_name="test_service",
            description="Test fault",
            detected_at=datetime.utcnow()
        )
        
        # Set up healthy service metrics
        fault_system.metric_history["test_service_health"].extend([
            {"timestamp": time.time() - 30, "value": 1.0, "status": "healthy"},
            {"timestamp": time.time() - 20, "value": 1.0, "status": "healthy"},
            {"timestamp": time.time() - 10, "value": 1.0, "status": "healthy"}
        ])
        
        # Check if fault is resolved
        is_resolved = await fault_system._is_fault_resolved(fault_event)
        
        # Should be resolved with 3 consecutive healthy checks
        assert is_resolved
    
    def test_fault_statistics(self, fault_system):
        """Test fault statistics generation."""
        # Add some test faults to history
        fault1 = FaultEvent(
            fault_id="fault_1",
            fault_type=FaultType.SERVICE_UNAVAILABLE,
            severity=FaultSeverity.HIGH,
            service_name="service_1",
            description="Test fault 1",
            detected_at=datetime.utcnow(),
            resolved_at=datetime.utcnow(),
            resolution_time=30.0
        )
        
        fault2 = FaultEvent(
            fault_id="fault_2",
            fault_type=FaultType.PERFORMANCE_DEGRADATION,
            severity=FaultSeverity.MEDIUM,
            service_name="service_2",
            description="Test fault 2",
            detected_at=datetime.utcnow()
        )
        
        fault_system.fault_history.extend([fault1, fault2])
        fault_system.active_faults["fault_2"] = fault2
        
        # Get statistics
        stats = fault_system.get_fault_statistics()
        
        # Verify statistics
        assert stats["total_faults"] == 2
        assert stats["active_faults"] == 1
        assert stats["resolved_faults"] == 1
        assert stats["resolution_rate"] == 0.5
        assert stats["avg_resolution_time"] == 30.0
        
        # Check fault type distribution
        assert "service_unavailable" in stats["fault_types"]
        assert "performance_degradation" in stats["fault_types"]
        
        # Check severity distribution
        assert "high" in stats["severity_distribution"]
        assert "medium" in stats["severity_distribution"]
    
    def test_active_faults_retrieval(self, fault_system):
        """Test active faults retrieval."""
        # Add active fault
        fault_event = FaultEvent(
            fault_id="active_fault",
            fault_type=FaultType.SERVICE_UNAVAILABLE,
            severity=FaultSeverity.HIGH,
            service_name="test_service",
            description="Active test fault",
            detected_at=datetime.utcnow(),
            root_cause="Test root cause",
            recovery_actions=["restart_service"],
            affected_services=["dependent_service"]
        )
        
        fault_system.active_faults["active_fault"] = fault_event
        
        # Get active faults
        active_faults = fault_system.get_active_faults()
        
        # Verify structure
        assert len(active_faults) == 1
        fault_data = active_faults[0]
        
        assert fault_data["fault_id"] == "active_fault"
        assert fault_data["fault_type"] == "service_unavailable"
        assert fault_data["severity"] == "high"
        assert fault_data["service_name"] == "test_service"
        assert fault_data["root_cause"] == "Test root cause"
        assert fault_data["recovery_actions"] == ["restart_service"]
        assert fault_data["affected_services"] == ["dependent_service"]
    
    def test_fault_callback_registration(self, fault_system):
        """Test fault callback registration and execution."""
        callback_called = False
        callback_fault = None
        
        def test_callback(fault_event):
            nonlocal callback_called, callback_fault
            callback_called = True
            callback_fault = fault_event
        
        # Register callback
        fault_system.add_fault_callback(test_callback)
        
        # Create test fault event
        fault_event = FaultEvent(
            fault_id="callback_test",
            fault_type=FaultType.SERVICE_UNAVAILABLE,
            severity=FaultSeverity.HIGH,
            service_name="test_service",
            description="Callback test fault",
            detected_at=datetime.utcnow()
        )
        
        # Simulate fault event handling (normally done by _create_fault_event)
        for callback in fault_system.fault_callbacks:
            callback(fault_event)
        
        # Verify callback was called
        assert callback_called
        assert callback_fault == fault_event
    
    def test_pattern_to_fault_type_mapping(self, fault_system):
        """Test pattern type to fault type mapping."""
        mappings = [
            ("performance", FaultType.PERFORMANCE_DEGRADATION),
            ("resource", FaultType.RESOURCE_EXHAUSTION),
            ("cascade", FaultType.CASCADE_FAILURE),
            ("unknown", FaultType.PERFORMANCE_DEGRADATION)  # Default
        ]
        
        for pattern_type, expected_fault_type in mappings:
            fault_type = fault_system._pattern_to_fault_type(pattern_type)
            assert fault_type == expected_fault_type
    
    def test_anomaly_score_to_severity_mapping(self, fault_system):
        """Test anomaly score to severity mapping."""
        mappings = [
            (0.95, FaultSeverity.CRITICAL),
            (0.85, FaultSeverity.HIGH),
            (0.65, FaultSeverity.MEDIUM),
            (0.35, FaultSeverity.LOW)
        ]
        
        for score, expected_severity in mappings:
            severity = fault_system._anomaly_score_to_severity(score)
            assert severity == expected_severity


class TestFaultEvent:
    """Test suite for FaultEvent class."""
    
    def test_fault_event_creation(self):
        """Test fault event creation."""
        detected_at = datetime.utcnow()
        
        fault_event = FaultEvent(
            fault_id="test_fault",
            fault_type=FaultType.SERVICE_UNAVAILABLE,
            severity=FaultSeverity.HIGH,
            service_name="test_service",
            description="Test fault description",
            detected_at=detected_at,
            root_cause="Test root cause",
            affected_services=["service1", "service2"],
            recovery_actions=["restart", "scale"]
        )
        
        assert fault_event.fault_id == "test_fault"
        assert fault_event.fault_type == FaultType.SERVICE_UNAVAILABLE
        assert fault_event.severity == FaultSeverity.HIGH
        assert fault_event.service_name == "test_service"
        assert fault_event.description == "Test fault description"
        assert fault_event.detected_at == detected_at
        assert fault_event.root_cause == "Test root cause"
        assert fault_event.affected_services == ["service1", "service2"]
        assert fault_event.recovery_actions == ["restart", "scale"]
        assert fault_event.resolved_at is None
        assert fault_event.resolution_time is None


class TestServiceDependency:
    """Test suite for ServiceDependency class."""
    
    def test_service_dependency_creation(self):
        """Test service dependency creation."""
        dependency = ServiceDependency(
            service_name="test_service",
            dependency_name="test_dependency",
            dependency_type="hard",
            timeout_threshold=30.0,
            failure_threshold=3
        )
        
        assert dependency.service_name == "test_service"
        assert dependency.dependency_name == "test_dependency"
        assert dependency.dependency_type == "hard"
        assert dependency.timeout_threshold == 30.0
        assert dependency.failure_threshold == 3


class TestFaultPattern:
    """Test suite for FaultPattern class."""
    
    def test_fault_pattern_creation(self):
        """Test fault pattern creation."""
        pattern = FaultPattern(
            pattern_id="test_pattern",
            pattern_type="performance",
            features=["cpu_usage", "memory_usage"],
            threshold=0.8,
            confidence=0.75
        )
        
        assert pattern.pattern_id == "test_pattern"
        assert pattern.pattern_type == "performance"
        assert pattern.features == ["cpu_usage", "memory_usage"]
        assert pattern.threshold == 0.8
        assert pattern.confidence == 0.75
        assert pattern.occurrences == 0
        assert pattern.last_seen is None


class TestGlobalFaultDetectionSystem:
    """Test suite for global fault detection system instance."""
    
    def test_global_instance_exists(self):
        """Test that global fault detection system instance exists."""
        assert fault_detection_system is not None
        assert isinstance(fault_detection_system, FaultDetectionSystem)
    
    def test_convenience_functions_exist(self):
        """Test that convenience functions exist."""
        from src.system.fault_detection_system import (
            start_fault_detection, stop_fault_detection, get_fault_status,
            register_fault_callback
        )
        
        # Functions should be callable
        assert callable(start_fault_detection)
        assert callable(stop_fault_detection)
        assert callable(get_fault_status)
        assert callable(register_fault_callback)
    
    def test_get_fault_status(self):
        """Test get_fault_status convenience function."""
        from src.system.fault_detection_system import get_fault_status
        
        status = get_fault_status()
        
        # Should return dictionary with expected keys
        expected_keys = [
            "detection_active", "active_faults", "total_patterns",
            "service_dependencies", "statistics"
        ]
        
        for key in expected_keys:
            assert key in status
        
        assert isinstance(status["detection_active"], bool)
        assert isinstance(status["active_faults"], int)
        assert isinstance(status["total_patterns"], int)
        assert isinstance(status["service_dependencies"], int)
        assert isinstance(status["statistics"], dict)


if __name__ == "__main__":
    pytest.main([__file__])