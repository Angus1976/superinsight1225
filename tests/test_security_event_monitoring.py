"""
Comprehensive test suite for security event monitoring system.

Tests the security event monitor, threat detector, and monitoring API endpoints.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4, UUID

from src.security.security_event_monitor import (
    SecurityEventMonitor, SecurityEvent, SecurityEventType, ThreatLevel,
    ThreatPattern, PrometheusConfig
)
from src.security.threat_detector import (
    AdvancedThreatDetector, ThreatSignature, ThreatCategory, DetectionMethod,
    BehaviorProfile
)
from src.security.models import AuditLogModel, AuditAction
from src.api.security_monitoring_api import router


class TestSecurityEventMonitor:
    """Test security event monitoring functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = PrometheusConfig(
            metrics_port=9091,  # Different port for testing
            collection_interval=1.0,  # Faster for testing
            enable_system_metrics=False,  # Disable for testing
            enable_business_metrics=False,
            enable_performance_metrics=False
        )
        self.monitor = SecurityEventMonitor(self.config)
        self.tenant_id = "test_tenant_123"
        self.user_id = uuid4()
    
    def test_monitor_initialization(self):
        """Test security monitor initialization."""
        assert self.monitor is not None
        assert self.monitor.monitoring_enabled is True
        assert len(self.monitor.threat_patterns) > 0
        assert len(self.monitor.active_events) == 0
        assert self.monitor.config.metrics_port == 9091
    
    def test_threat_patterns_initialization(self):
        """Test threat patterns are properly initialized."""
        patterns = self.monitor.threat_patterns
        
        # Check required patterns exist
        assert 'brute_force_login' in patterns
        assert 'privilege_escalation' in patterns
        assert 'data_exfiltration' in patterns
        assert 'anomalous_behavior' in patterns
        assert 'malicious_requests' in patterns
        
        # Verify pattern structure
        brute_force = patterns['brute_force_login']
        assert brute_force.pattern_id == 'brute_force_login'
        assert brute_force.threat_level == ThreatLevel.HIGH
        assert brute_force.auto_response is True
        assert len(brute_force.response_actions) > 0
    
    def test_security_metrics_initialization(self):
        """Test security metrics are properly initialized."""
        metrics = self.monitor.security_metrics
        
        # Check required metrics exist
        assert 'security_events_total' in metrics
        assert 'threat_detections_total' in metrics
        assert 'security_alerts_total' in metrics
        assert 'active_security_events' in metrics
        assert 'security_score' in metrics
    
    @pytest.mark.asyncio
    async def test_brute_force_detection(self):
        """Test brute force attack detection."""
        # Create mock audit logs for brute force attack
        failed_logs = []
        ip_address = "192.168.1.100"
        
        for i in range(12):  # More than threshold
            log = Mock(spec=AuditLogModel)
            log.id = f"log_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = None
            log.action = AuditAction.LOGIN
            log.resource_type = "user"
            log.ip_address = ip_address
            log.timestamp = datetime.utcnow() - timedelta(minutes=i)
            log.details = {"status": "failed", "username": f"user_{i % 3}"}
            failed_logs.append(log)
        
        # Test detection
        pattern = self.monitor.threat_patterns['brute_force_login']
        events = await self.monitor._detect_brute_force_attacks(pattern, failed_logs)
        
        assert len(events) == 1
        event = events[0]
        assert event.event_type == SecurityEventType.BRUTE_FORCE_ATTACK
        assert event.threat_level == ThreatLevel.HIGH
        assert event.ip_address == ip_address
        assert "暴力破解攻击" in event.description
        assert event.details['failed_attempts'] == 12
    
    @pytest.mark.asyncio
    async def test_privilege_escalation_detection(self):
        """Test privilege escalation detection."""
        # Create mock audit logs for privilege escalation
        privilege_logs = []
        
        for i in range(5):  # Above threshold
            log = Mock(spec=AuditLogModel)
            log.id = f"priv_log_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = self.user_id
            log.action = AuditAction.UPDATE
            log.resource_type = "role"
            log.ip_address = "192.168.1.101"
            log.timestamp = datetime.utcnow() - timedelta(minutes=i)
            log.details = {"role_name": "admin", "permissions": ["read", "write", "admin"]}
            privilege_logs.append(log)
        
        # Test detection
        pattern = self.monitor.threat_patterns['privilege_escalation']
        events = await self.monitor._detect_privilege_escalation(pattern, privilege_logs)
        
        assert len(events) == 1
        event = events[0]
        assert event.event_type == SecurityEventType.PRIVILEGE_ESCALATION
        assert event.threat_level == ThreatLevel.CRITICAL
        assert event.user_id == self.user_id
        assert "权限提升攻击" in event.description
    
    @pytest.mark.asyncio
    async def test_data_exfiltration_detection(self):
        """Test data exfiltration detection."""
        # Create mock audit logs for data export
        export_logs = []
        
        for i in range(3):
            log = Mock(spec=AuditLogModel)
            log.id = f"export_log_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = self.user_id
            log.action = AuditAction.EXPORT
            log.resource_type = "dataset"
            log.ip_address = "192.168.1.102"
            log.timestamp = datetime.utcnow() - timedelta(minutes=i * 10)
            log.details = {"export_size_mb": 500, "format": "csv"}  # Large export
            export_logs.append(log)
        
        # Test detection
        pattern = self.monitor.threat_patterns['data_exfiltration']
        events = await self.monitor._detect_data_exfiltration(pattern, export_logs)
        
        assert len(events) == 1
        event = events[0]
        assert event.event_type == SecurityEventType.DATA_EXFILTRATION
        assert event.threat_level == ThreatLevel.HIGH
        assert event.user_id == self.user_id
        assert event.details['total_export_size_mb'] == 1500
    
    @pytest.mark.asyncio
    async def test_malicious_request_detection(self):
        """Test malicious request detection."""
        # Create mock audit logs with malicious patterns
        malicious_logs = []
        
        for i in range(6):  # Above threshold
            log = Mock(spec=AuditLogModel)
            log.id = f"mal_log_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = self.user_id
            log.action = AuditAction.READ
            log.resource_type = "data"
            log.ip_address = "192.168.1.103"
            log.timestamp = datetime.utcnow() - timedelta(seconds=i * 5)
            log.details = {
                "query": "SELECT * FROM users WHERE 1=1 UNION SELECT password FROM admin",
                "user_input": "<script>alert('xss')</script>"
            }
            malicious_logs.append(log)
        
        # Test detection
        pattern = self.monitor.threat_patterns['malicious_requests']
        events = await self.monitor._detect_malicious_requests(pattern, malicious_logs)
        
        assert len(events) == 1
        event = events[0]
        assert event.event_type == SecurityEventType.MALICIOUS_REQUEST
        assert event.threat_level == ThreatLevel.CRITICAL
        assert len(event.details['detected_patterns']) > 0
        assert 'sql_injection' in event.details['attack_types']
    
    @pytest.mark.asyncio
    async def test_security_event_handling(self):
        """Test security event handling and storage."""
        # Create a test security event
        event = SecurityEvent(
            event_id="TEST_EVENT_001",
            event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
            threat_level=ThreatLevel.HIGH,
            tenant_id=self.tenant_id,
            user_id=None,
            ip_address="192.168.1.100",
            timestamp=datetime.utcnow(),
            description="Test brute force attack",
            details={"test": "data"}
        )
        
        # Mock database session
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        # Test event handling
        await self.monitor._handle_security_event(event, mock_db)
        
        # Verify event is stored
        assert event.event_id in self.monitor.active_events
        stored_event = self.monitor.active_events[event.event_id]
        assert stored_event.event_type == SecurityEventType.BRUTE_FORCE_ATTACK
        assert stored_event.threat_level == ThreatLevel.HIGH
        
        # Verify audit log creation
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_security_score_calculation(self):
        """Test security score calculation."""
        # Test with no threats
        threat_counts = {}
        score = self.monitor._calculate_security_score(threat_counts)
        assert score == 100.0  # Perfect score with no threats
        
        # Test with various threat levels
        threat_counts = {
            ThreatLevel.LOW.value: 2,
            ThreatLevel.MEDIUM.value: 1,
            ThreatLevel.HIGH.value: 1,
            ThreatLevel.CRITICAL.value: 0
        }
        score = self.monitor._calculate_security_score(threat_counts)
        assert 0 <= score <= 100
        assert score < 100  # Should be reduced due to threats
    
    def test_event_resolution(self):
        """Test security event resolution."""
        # Create and store a test event
        event = SecurityEvent(
            event_id="RESOLVE_TEST_001",
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            threat_level=ThreatLevel.MEDIUM,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            ip_address="192.168.1.104",
            timestamp=datetime.utcnow(),
            description="Test suspicious activity",
            details={}
        )
        
        self.monitor.active_events[event.event_id] = event
        
        # Test resolution
        success = self.monitor.resolve_event(event.event_id, "False positive - user verified")
        
        assert success is True
        assert event.event_id not in self.monitor.active_events
        assert len(self.monitor.resolved_events) == 1
        
        resolved_event = self.monitor.resolved_events[0]
        assert resolved_event.resolved is True
        assert resolved_event.resolution_notes == "False positive - user verified"
    
    def test_get_security_summary(self):
        """Test security summary generation."""
        # Add some test events
        events = [
            SecurityEvent(
                event_id=f"SUMMARY_TEST_{i}",
                event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
                threat_level=ThreatLevel.HIGH if i % 2 == 0 else ThreatLevel.MEDIUM,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                ip_address=f"192.168.1.{100 + i}",
                timestamp=datetime.utcnow(),
                description=f"Test event {i}",
                details={}
            )
            for i in range(5)
        ]
        
        for event in events:
            self.monitor.active_events[event.event_id] = event
        
        # Get summary
        summary = self.monitor.get_security_summary(self.tenant_id)
        
        assert summary["tenant_id"] == self.tenant_id
        assert summary["active_events_count"] == 5
        assert summary["threat_level_distribution"][ThreatLevel.HIGH.value] == 3
        assert summary["threat_level_distribution"][ThreatLevel.MEDIUM.value] == 2
        assert summary["event_type_distribution"][SecurityEventType.BRUTE_FORCE_ATTACK.value] == 5
        assert 0 <= summary["security_score"] <= 100


class TestAdvancedThreatDetector:
    """Test advanced threat detection functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.detector = AdvancedThreatDetector()
        self.tenant_id = "test_tenant_456"
        self.user_id = str(uuid4())
    
    def test_detector_initialization(self):
        """Test threat detector initialization."""
        assert self.detector is not None
        assert len(self.detector.threat_signatures) > 0
        assert len(self.detector.behavior_profiles) == 0
        assert self.detector.detection_stats['total_detections'] == 0
    
    def test_threat_signatures_initialization(self):
        """Test threat signatures are properly initialized."""
        signatures = self.detector.threat_signatures
        
        # Check required signatures
        assert 'sql_injection' in signatures
        assert 'xss_attack' in signatures
        assert 'path_traversal' in signatures
        assert 'brute_force' in signatures
        assert 'privilege_escalation' in signatures
        
        # Verify signature structure
        sql_sig = signatures['sql_injection']
        assert sql_sig.category == ThreatCategory.APPLICATION_SECURITY
        assert sql_sig.detection_method == DetectionMethod.RULE_BASED
        assert len(sql_sig.patterns) > 0
        assert sql_sig.confidence_threshold > 0
    
    @pytest.mark.asyncio
    async def test_rule_based_detection(self):
        """Test rule-based threat detection."""
        # Create mock audit log with SQL injection
        log = Mock(spec=AuditLogModel)
        log.id = "rule_test_001"
        log.tenant_id = self.tenant_id
        log.user_id = UUID(self.user_id)
        log.action = AuditAction.READ
        log.resource_type = "data"
        log.ip_address = "192.168.1.200"
        log.timestamp = datetime.utcnow()
        log.user_agent = "Mozilla/5.0"
        log.details = {
            "query": "SELECT * FROM users WHERE id = 1 UNION SELECT password FROM admin",
            "input": "test' OR '1'='1"
        }
        
        signature = self.detector.threat_signatures['sql_injection']
        threats = await self.detector._rule_based_detection(signature, [log])
        
        assert len(threats) == 1
        event, confidence = threats[0]
        assert event.event_type == SecurityEventType.MALICIOUS_REQUEST
        assert confidence >= signature.confidence_threshold
        assert 'sql_injection' in event.details['signature_id']
    
    @pytest.mark.asyncio
    async def test_statistical_detection(self):
        """Test statistical threat detection."""
        # Create multiple failed login logs
        logs = []
        for i in range(15):  # Above threshold
            log = Mock(spec=AuditLogModel)
            log.id = f"stat_test_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = None
            log.action = AuditAction.LOGIN
            log.resource_type = "user"
            log.ip_address = "192.168.1.201"
            log.timestamp = datetime.utcnow() - timedelta(seconds=i * 10)
            log.details = {"status": "failed", "username": f"user_{i % 5}"}
            logs.append(log)
        
        signature = self.detector.threat_signatures['brute_force']
        mock_db = Mock()
        
        threats = await self.detector._statistical_detection(signature, logs, mock_db)
        
        assert len(threats) == 1
        event, confidence = threats[0]
        assert event.event_type == SecurityEventType.BRUTE_FORCE_ATTACK
        assert confidence >= signature.confidence_threshold
    
    @pytest.mark.asyncio
    async def test_behavior_profile_creation(self):
        """Test user behavior profile creation and updates."""
        # Create mock audit logs for a user
        logs = []
        for i in range(10):
            log = Mock(spec=AuditLogModel)
            log.id = f"behavior_test_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = UUID(self.user_id)
            log.action = AuditAction.READ if i % 2 == 0 else AuditAction.UPDATE
            log.resource_type = "dataset" if i % 3 == 0 else "annotation"
            log.ip_address = "192.168.1.202"
            log.timestamp = datetime.utcnow() - timedelta(hours=i)
            log.details = {"operation": f"test_op_{i}"}
            logs.append(log)
        
        mock_db = Mock()
        mock_db.execute = Mock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        
        # Update behavior profiles
        await self.detector._update_behavior_profiles(logs, mock_db)
        
        # Verify profile creation
        assert self.user_id in self.detector.behavior_profiles
        profile = self.detector.behavior_profiles[self.user_id]
        
        assert profile.user_id == self.user_id
        assert profile.tenant_id == self.tenant_id
        assert len(profile.action_patterns) > 0
        assert len(profile.resource_access_patterns) > 0
        assert len(profile.time_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_behavioral_detection(self):
        """Test behavioral threat detection."""
        # Create behavior profile first
        profile = BehaviorProfile(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            profile_created=datetime.utcnow() - timedelta(days=30),
            last_updated=datetime.utcnow()
        )
        
        # Set baseline patterns
        profile.action_frequency_baseline = {
            'privilege_ops': (2.0, 1.0)  # mean=2, std=1
        }
        
        self.detector.behavior_profiles[self.user_id] = profile
        
        # Create logs showing privilege escalation behavior
        logs = []
        for i in range(8):  # Well above baseline
            log = Mock(spec=AuditLogModel)
            log.id = f"behavioral_test_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = UUID(self.user_id)
            log.action = AuditAction.UPDATE
            log.resource_type = "role"
            log.ip_address = "192.168.1.203"
            log.timestamp = datetime.utcnow() - timedelta(minutes=i * 5)
            log.details = {"role": "admin", "permissions": ["superuser"]}
            logs.append(log)
        
        signature = self.detector.threat_signatures['privilege_escalation']
        mock_db = Mock()
        
        threats = await self.detector._behavioral_detection(signature, logs, mock_db)
        
        assert len(threats) == 1
        event, confidence = threats[0]
        assert event.event_type == SecurityEventType.PRIVILEGE_ESCALATION
        assert confidence >= signature.confidence_threshold
    
    def test_behavioral_feature_extraction(self):
        """Test behavioral feature extraction."""
        # Create mock logs
        logs = []
        for i in range(5):
            log = Mock(spec=AuditLogModel)
            log.action = AuditAction.READ if i % 2 == 0 else AuditAction.UPDATE
            log.resource_type = "dataset"
            log.ip_address = f"192.168.1.{200 + i}"
            log.timestamp = datetime.utcnow() - timedelta(hours=i)
            logs.append(log)
        
        # Create mock profile
        profile = BehaviorProfile(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            profile_created=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            peak_activity_hours=[9, 10, 11, 14, 15, 16]
        )
        
        # Extract features
        features = self.detector._extract_behavioral_features(logs, profile)
        
        assert 'total_actions' in features
        assert 'unique_actions' in features
        assert 'action_diversity' in features
        assert 'unique_resources' in features
        assert 'unique_ips' in features
        assert features['total_actions'] == 5
        assert features['unique_actions'] == 2  # READ and UPDATE
    
    def test_anomaly_score_calculation(self):
        """Test anomaly score calculation."""
        features = {
            'total_actions': 100,  # High activity
            'time_deviation': 8,   # Outside normal hours
            'resource_diversity': 0.9,  # Very diverse access
            'unique_ips': 5        # Multiple IPs
        }
        
        profile = BehaviorProfile(
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            profile_created=datetime.utcnow(),
            last_updated=datetime.utcnow()
        )
        
        profile.action_frequency_baseline = {
            'total_actions': (20.0, 5.0)  # mean=20, std=5
        }
        
        score = self.detector._calculate_anomaly_score(features, profile)
        
        assert 0 <= score <= 1.0
        assert score > 0.5  # Should be high due to anomalies
    
    def test_detection_statistics(self):
        """Test detection statistics tracking."""
        # Update statistics
        self.detector.detection_stats['total_detections'] = 100
        self.detector.detection_stats['confirmed_threats'] = 85
        self.detector.detection_stats['false_positives'] = 15
        
        stats = self.detector.get_detection_statistics()
        
        assert stats['total_detections'] == 100
        assert stats['confirmed_threats'] == 85
        assert stats['false_positives'] == 15
        assert stats['detection_accuracy'] == 0.85
        assert stats['active_signatures'] == len(self.detector.threat_signatures)


class TestSecurityMonitoringAPI:
    """Test security monitoring API endpoints."""
    
    def setup_method(self):
        """Setup test environment."""
        self.tenant_id = "api_test_tenant"
        self.user_id = str(uuid4())
    
    @pytest.mark.asyncio
    async def test_get_security_events_endpoint(self):
        """Test get security events API endpoint."""
        from src.api.security_monitoring_api import get_security_events
        
        # Mock security monitor
        mock_events = [
            SecurityEvent(
                event_id="API_TEST_001",
                event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
                threat_level=ThreatLevel.HIGH,
                tenant_id=self.tenant_id,
                user_id=UUID(self.user_id),
                ip_address="192.168.1.100",
                timestamp=datetime.utcnow(),
                description="Test brute force attack",
                details={"test": "data"}
            )
        ]
        
        with patch('src.api.security_monitoring_api.security_event_monitor') as mock_monitor:
            mock_monitor.get_active_events.return_value = mock_events
            
            mock_db = Mock()
            result = await get_security_events(
                tenant_id=self.tenant_id,
                threat_level="high",
                limit=50,
                db=mock_db
            )
            
            assert result["tenant_id"] == self.tenant_id
            assert result["total_events"] == 1
            assert len(result["events"]) == 1
            assert result["events"][0]["event_type"] == "brute_force_attack"
    
    @pytest.mark.asyncio
    async def test_get_security_summary_endpoint(self):
        """Test get security summary API endpoint."""
        from src.api.security_monitoring_api import get_security_summary
        
        mock_summary = {
            "tenant_id": self.tenant_id,
            "active_events_count": 5,
            "threat_level_distribution": {"high": 2, "medium": 3},
            "event_type_distribution": {"brute_force_attack": 3, "suspicious_activity": 2},
            "security_score": 75.5,
            "last_scan_time": datetime.utcnow().isoformat(),
            "monitoring_status": "active"
        }
        
        with patch('src.api.security_monitoring_api.security_event_monitor') as mock_monitor:
            mock_monitor.get_security_summary.return_value = mock_summary
            
            mock_db = Mock()
            result = await get_security_summary(tenant_id=self.tenant_id, db=mock_db)
            
            assert result.tenant_id == self.tenant_id
            assert result.active_events_count == 5
            assert result.security_score == 75.5
    
    @pytest.mark.asyncio
    async def test_detect_threats_endpoint(self):
        """Test detect threats API endpoint."""
        from src.api.security_monitoring_api import detect_threats, ThreatDetectionRequest
        
        request = ThreatDetectionRequest(
            tenant_id=self.tenant_id,
            time_window_hours=1,
            confidence_threshold=0.7
        )
        
        # Mock audit logs
        mock_logs = [
            Mock(spec=AuditLogModel, tenant_id=self.tenant_id, timestamp=datetime.utcnow())
        ]
        
        # Mock detected threats
        mock_event = SecurityEvent(
            event_id="DETECT_TEST_001",
            event_type=SecurityEventType.MALICIOUS_REQUEST,
            threat_level=ThreatLevel.HIGH,
            tenant_id=self.tenant_id,
            user_id=UUID(self.user_id),
            ip_address="192.168.1.100",
            timestamp=datetime.utcnow(),
            description="Test malicious request",
            details={"signature_id": "sql_injection"}
        )
        
        mock_threats = [(mock_event, 0.85)]
        
        with patch('src.api.security_monitoring_api.threat_detector') as mock_detector:
            mock_detector.detect_threats = AsyncMock(return_value=mock_threats)
            
            mock_db = Mock()
            mock_db.execute.return_value.scalars.return_value.all.return_value = mock_logs
            
            result = await detect_threats(request=request, db=mock_db)
            
            assert result["tenant_id"] == self.tenant_id
            assert result["total_threats_detected"] == 1
            assert len(result["threats"]) == 1
            assert result["threats"][0]["confidence_score"] == 0.85
    
    @pytest.mark.asyncio
    async def test_resolve_security_event_endpoint(self):
        """Test resolve security event API endpoint."""
        from src.api.security_monitoring_api import resolve_security_event, EventResolutionRequest
        
        event_id = "RESOLVE_API_TEST_001"
        resolution_data = EventResolutionRequest(
            resolution_notes="False positive - verified legitimate activity",
            resolved_by="security_analyst_001"
        )
        
        with patch('src.api.security_monitoring_api.security_event_monitor') as mock_monitor:
            mock_monitor.resolve_event.return_value = True
            
            with patch('src.api.security_monitoring_api.AuditService') as mock_audit_service:
                mock_audit_instance = Mock()
                mock_audit_service.return_value = mock_audit_instance
                
                mock_db = Mock()
                result = await resolve_security_event(
                    tenant_id=self.tenant_id,
                    event_id=event_id,
                    resolution_data=resolution_data,
                    db=mock_db
                )
                
                assert result["event_id"] == event_id
                assert result["status"] == "resolved"
                assert result["resolved_by"] == "security_analyst_001"
                
                # Verify audit logging
                mock_audit_instance.log_system_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_behavior_profile_endpoint(self):
        """Test get user behavior profile API endpoint."""
        from src.api.security_monitoring_api import get_user_behavior_profile
        
        mock_profile = {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "profile_created": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "action_patterns": {"read": 0.6, "update": 0.4},
            "resource_access_patterns": {"dataset": 0.7, "annotation": 0.3},
            "time_patterns": {9: 0.3, 14: 0.4, 16: 0.3},
            "peak_activity_hours": [9, 14, 16],
            "risk_score": 0.2,
            "anomaly_count": 1
        }
        
        with patch('src.api.security_monitoring_api.threat_detector') as mock_detector:
            mock_detector.get_user_behavior_profile.return_value = mock_profile
            
            mock_db = Mock()
            result = await get_user_behavior_profile(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                db=mock_db
            )
            
            assert result.user_id == self.user_id
            assert result.tenant_id == self.tenant_id
            assert result.risk_score == 0.2
            assert result.anomaly_count == 1
    
    @pytest.mark.asyncio
    async def test_monitoring_health_check_endpoint(self):
        """Test security monitoring health check API endpoint."""
        from src.api.security_monitoring_api import security_monitoring_health_check
        
        with patch('src.api.security_monitoring_api.security_event_monitor') as mock_monitor:
            mock_monitor.monitoring_enabled = True
            mock_monitor.last_scan_time = datetime.utcnow()
            mock_monitor.active_events = {}
            
            mock_db = Mock()
            result = await security_monitoring_health_check(db=mock_db)
            
            assert result["status"] == "healthy"
            assert result["monitoring_enabled"] is True
            assert "components" in result
            assert result["components"]["event_monitor"] == "healthy"


class TestIntegrationScenarios:
    """Test integration scenarios and end-to-end workflows."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = PrometheusConfig(
            metrics_port=9092,
            collection_interval=1.0,
            enable_system_metrics=False,
            enable_business_metrics=False,
            enable_performance_metrics=False
        )
        self.monitor = SecurityEventMonitor(self.config)
        self.detector = AdvancedThreatDetector()
        self.tenant_id = "integration_test_tenant"
        self.user_id = uuid4()
    
    @pytest.mark.asyncio
    async def test_complete_threat_detection_workflow(self):
        """Test complete threat detection workflow from audit logs to alerts."""
        # Create comprehensive audit logs simulating an attack
        audit_logs = []
        
        # Phase 1: Reconnaissance (multiple failed logins)
        for i in range(8):
            log = Mock(spec=AuditLogModel)
            log.id = f"recon_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = None
            log.action = AuditAction.LOGIN
            log.resource_type = "user"
            log.ip_address = "192.168.1.100"
            log.timestamp = datetime.utcnow() - timedelta(minutes=30 - i)
            log.details = {"status": "failed", "username": f"admin_{i}"}
            audit_logs.append(log)
        
        # Phase 2: Successful login and privilege escalation
        login_log = Mock(spec=AuditLogModel)
        login_log.id = "successful_login"
        login_log.tenant_id = self.tenant_id
        login_log.user_id = self.user_id
        login_log.action = AuditAction.LOGIN
        login_log.resource_type = "user"
        login_log.ip_address = "192.168.1.100"
        login_log.timestamp = datetime.utcnow() - timedelta(minutes=20)
        login_log.details = {"status": "success", "username": "compromised_user"}
        audit_logs.append(login_log)
        
        # Phase 3: Privilege escalation attempts
        for i in range(4):
            log = Mock(spec=AuditLogModel)
            log.id = f"priv_esc_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = self.user_id
            log.action = AuditAction.UPDATE
            log.resource_type = "role"
            log.ip_address = "192.168.1.100"
            log.timestamp = datetime.utcnow() - timedelta(minutes=15 - i)
            log.details = {"role": "admin", "permissions": ["superuser", "delete_all"]}
            audit_logs.append(log)
        
        # Phase 4: Data exfiltration
        for i in range(3):
            log = Mock(spec=AuditLogModel)
            log.id = f"exfil_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = self.user_id
            log.action = AuditAction.EXPORT
            log.resource_type = "dataset"
            log.ip_address = "192.168.1.100"
            log.timestamp = datetime.utcnow() - timedelta(minutes=5 - i)
            log.details = {"export_size_mb": 800, "format": "json"}
            audit_logs.append(log)
        
        # Mock database session
        mock_db = Mock()
        mock_db.execute = Mock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        # Run threat detection
        detected_threats = await self.detector.detect_threats(audit_logs, mock_db)
        
        # Verify multiple threat types detected
        threat_types = set(event.event_type for event, _ in detected_threats)
        assert SecurityEventType.BRUTE_FORCE_ATTACK in threat_types
        assert SecurityEventType.PRIVILEGE_ESCALATION in threat_types
        assert SecurityEventType.DATA_EXFILTRATION in threat_types
        
        # Process events through monitor
        for event, confidence in detected_threats:
            await self.monitor._handle_security_event(event, mock_db)
        
        # Verify events are stored and metrics updated
        assert len(self.monitor.active_events) > 0
        
        # Verify security score is impacted
        summary = self.monitor.get_security_summary(self.tenant_id)
        assert summary["security_score"] < 100  # Should be reduced due to threats
        assert summary["active_events_count"] > 0
    
    @pytest.mark.asyncio
    async def test_false_positive_handling(self):
        """Test handling of false positive detections."""
        # Create logs that might trigger false positives
        normal_logs = []
        
        # Legitimate admin activities that might look suspicious
        for i in range(3):
            log = Mock(spec=AuditLogModel)
            log.id = f"admin_work_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = self.user_id
            log.action = AuditAction.UPDATE
            log.resource_type = "user"
            log.ip_address = "192.168.1.200"  # Known admin IP
            log.timestamp = datetime.utcnow() - timedelta(hours=i)
            log.details = {"operation": "password_reset", "target_user": f"user_{i}"}
            normal_logs.append(log)
        
        mock_db = Mock()
        mock_db.execute = Mock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        # Run detection
        detected_threats = await self.detector.detect_threats(normal_logs, mock_db)
        
        # Should have low or no detections for normal activity
        high_confidence_threats = [
            (event, conf) for event, conf in detected_threats if conf > 0.8
        ]
        
        # Normal admin activity should not trigger high-confidence alerts
        assert len(high_confidence_threats) == 0
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test system performance under high load."""
        # Generate large number of audit logs
        large_log_set = []
        
        for i in range(1000):  # Large dataset
            log = Mock(spec=AuditLogModel)
            log.id = f"load_test_{i}"
            log.tenant_id = self.tenant_id
            log.user_id = self.user_id if i % 10 == 0 else uuid4()
            log.action = AuditAction.READ if i % 3 == 0 else AuditAction.UPDATE
            log.resource_type = "dataset" if i % 2 == 0 else "annotation"
            log.ip_address = f"192.168.1.{100 + (i % 50)}"
            log.timestamp = datetime.utcnow() - timedelta(seconds=i)
            log.details = {"operation": f"test_op_{i}"}
            large_log_set.append(log)
        
        mock_db = Mock()
        mock_db.execute = Mock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        # Measure detection time
        start_time = datetime.utcnow()
        detected_threats = await self.detector.detect_threats(large_log_set, mock_db)
        detection_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Performance assertions
        assert detection_time < 10.0  # Should complete within 10 seconds
        assert isinstance(detected_threats, list)
        
        # Process events through monitor
        start_time = datetime.utcnow()
        for event, confidence in detected_threats[:10]:  # Process first 10 events
            await self.monitor._handle_security_event(event, mock_db)
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        assert processing_time < 5.0  # Should process quickly


if __name__ == "__main__":
    pytest.main([__file__, "-v"])