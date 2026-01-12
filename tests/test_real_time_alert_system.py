"""
Comprehensive test suite for real-time alert system.

Tests the real-time alerting functionality, notification channels,
alert rules, and API endpoints.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from src.security.real_time_alert_system import (
    RealTimeAlertSystem, AlertRule, AlertChannel, AlertPriority,
    AlertStatus, AlertNotification, EmailAlertHandler, SlackAlertHandler,
    WebhookAlertHandler, SystemLogAlertHandler
)
from src.security.security_event_monitor import (
    SecurityEvent, SecurityEventType, ThreatLevel
)


class TestRealTimeAlertSystem:
    """Test real-time alert system functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = {
            'email': {
                'enabled': True,
                'smtp_server': 'localhost',
                'smtp_port': 587,
                'username': 'test@example.com',
                'password': 'test_password',
                'sender_email': 'alerts@example.com'
            },
            'slack': {
                'enabled': True,
                'webhook_url': 'https://hooks.slack.com/test'
            },
            'webhook': {
                'enabled': True
            },
            'critical_alert_recipients': ['admin@example.com'],
            'security_alert_recipients': ['security@example.com'],
            'auth_alert_recipients': ['auth@example.com']
        }
        self.alert_system = RealTimeAlertSystem(self.config)
        self.tenant_id = "test_tenant_123"
        self.user_id = uuid4()
    
    def test_alert_system_initialization(self):
        """Test alert system initialization."""
        assert self.alert_system is not None
        assert len(self.alert_system.alert_rules) > 0  # Default rules loaded
        assert len(self.alert_system.channel_handlers) > 0
        assert not self.alert_system.running
        assert len(self.alert_system.pending_notifications) == 0
    
    def test_default_alert_rules(self):
        """Test default alert rules are properly initialized."""
        rules = self.alert_system.alert_rules
        
        # Check required default rules
        assert 'critical_threats' in rules
        assert 'anomalous_behavior' in rules
        assert 'authentication_failures' in rules
        
        # Verify critical threats rule
        critical_rule = rules['critical_threats']
        assert critical_rule.name == "关键威胁告警"
        assert critical_rule.priority == AlertPriority.CRITICAL
        assert critical_rule.enabled is True
        assert SecurityEventType.BRUTE_FORCE_ATTACK in critical_rule.event_types
        assert ThreatLevel.CRITICAL in critical_rule.threat_levels
        assert AlertChannel.EMAIL in critical_rule.channels
    
    def test_channel_handlers_initialization(self):
        """Test channel handlers are properly initialized."""
        handlers = self.alert_system.channel_handlers
        
        # Check that enabled channels have handlers
        assert AlertChannel.EMAIL in handlers
        assert AlertChannel.SLACK in handlers
        assert AlertChannel.WEBHOOK in handlers
        assert AlertChannel.SYSTEM_LOG in handlers  # Always enabled
        
        # Verify handler types
        assert isinstance(handlers[AlertChannel.EMAIL], EmailAlertHandler)
        assert isinstance(handlers[AlertChannel.SLACK], SlackAlertHandler)
        assert isinstance(handlers[AlertChannel.WEBHOOK], WebhookAlertHandler)
        assert isinstance(handlers[AlertChannel.SYSTEM_LOG], SystemLogAlertHandler)
    
    def test_add_alert_rule(self):
        """Test adding custom alert rules."""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test alert rule",
            event_types=[SecurityEventType.SUSPICIOUS_ACTIVITY],
            threat_levels=[ThreatLevel.MEDIUM],
            channels=[AlertChannel.EMAIL],
            priority=AlertPriority.MEDIUM,
            recipients=['test@example.com']
        )
        
        initial_count = len(self.alert_system.alert_rules)
        self.alert_system.add_alert_rule(rule)
        
        assert len(self.alert_system.alert_rules) == initial_count + 1
        assert 'test_rule' in self.alert_system.alert_rules
        assert self.alert_system.alert_rules['test_rule'] == rule
    
    def test_remove_alert_rule(self):
        """Test removing alert rules."""
        # Add a test rule first
        rule = AlertRule(
            rule_id="temp_rule",
            name="Temporary Rule",
            description="Temporary test rule",
            event_types=[SecurityEventType.SUSPICIOUS_ACTIVITY],
            threat_levels=[ThreatLevel.LOW],
            channels=[AlertChannel.SYSTEM_LOG],
            priority=AlertPriority.LOW,
            recipients=['test@example.com']
        )
        
        self.alert_system.add_alert_rule(rule)
        initial_count = len(self.alert_system.alert_rules)
        
        self.alert_system.remove_alert_rule("temp_rule")
        
        assert len(self.alert_system.alert_rules) == initial_count - 1
        assert 'temp_rule' not in self.alert_system.alert_rules
    
    def test_enable_disable_alert_rule(self):
        """Test enabling and disabling alert rules."""
        rule_id = "critical_threats"
        
        # Test disable
        self.alert_system.disable_alert_rule(rule_id)
        assert not self.alert_system.alert_rules[rule_id].enabled
        
        # Test enable
        self.alert_system.enable_alert_rule(rule_id)
        assert self.alert_system.alert_rules[rule_id].enabled
    
    @pytest.mark.asyncio
    async def test_process_security_event_matching_rule(self):
        """Test processing security event with matching rule."""
        # Create a security event that matches critical_threats rule
        event = SecurityEvent(
            event_id="test_event_001",
            event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
            threat_level=ThreatLevel.CRITICAL,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            ip_address="192.168.1.100",
            timestamp=datetime.now(),
            description="Test brute force attack detected",
            details={"pattern_id": "brute_force_login", "attempts": 15}
        )
        
        initial_pending = len(self.alert_system.pending_notifications)
        
        await self.alert_system.process_security_event(event)
        
        # Should generate notifications for matching rule
        assert len(self.alert_system.pending_notifications) > initial_pending
        
        # Check that notifications were created for the right channels
        notifications = list(self.alert_system.pending_notifications)
        channels_used = {notif.channel for notif in notifications}
        
        # Critical threats rule uses EMAIL, SLACK, SYSTEM_LOG
        expected_channels = {AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SYSTEM_LOG}
        assert channels_used == expected_channels
    
    @pytest.mark.asyncio
    async def test_process_security_event_no_matching_rule(self):
        """Test processing security event with no matching rule."""
        # Create a security event that doesn't match any rule
        event = SecurityEvent(
            event_id="test_event_002",
            event_type=SecurityEventType.POLICY_VIOLATION,  # Not in default rules
            threat_level=ThreatLevel.LOW,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            ip_address="192.168.1.100",
            timestamp=datetime.now(),
            description="Test policy violation",
            details={}
        )
        
        initial_pending = len(self.alert_system.pending_notifications)
        
        await self.alert_system.process_security_event(event)
        
        # Should not generate any notifications
        assert len(self.alert_system.pending_notifications) == initial_pending
    
    @pytest.mark.asyncio
    async def test_cooldown_mechanism(self):
        """Test alert cooldown mechanism."""
        # Create a security event
        event = SecurityEvent(
            event_id="test_event_003",
            event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
            threat_level=ThreatLevel.CRITICAL,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            ip_address="192.168.1.100",
            timestamp=datetime.now(),
            description="Test brute force attack",
            details={"pattern_id": "brute_force_login"}
        )
        
        # Process event first time
        await self.alert_system.process_security_event(event)
        first_count = len(self.alert_system.pending_notifications)
        
        # Process same event immediately (should be in cooldown)
        event.event_id = "test_event_004"  # Different event ID
        await self.alert_system.process_security_event(event)
        second_count = len(self.alert_system.pending_notifications)
        
        # Should not generate new notifications due to cooldown
        assert second_count == first_count
    
    def test_find_matching_rules(self):
        """Test finding matching alert rules for events."""
        event = SecurityEvent(
            event_id="test_event_005",
            event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
            threat_level=ThreatLevel.HIGH,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            ip_address="192.168.1.100",
            timestamp=datetime.now(),
            description="Test event",
            details={}
        )
        
        matching_rules = self.alert_system._find_matching_rules(event)
        
        # Should match critical_threats rule
        assert len(matching_rules) > 0
        rule_ids = [rule.rule_id for rule in matching_rules]
        assert 'critical_threats' in rule_ids
    
    def test_check_rule_conditions(self):
        """Test rule condition checking."""
        # Create rule with specific conditions
        rule = AlertRule(
            rule_id="conditional_rule",
            name="Conditional Rule",
            description="Rule with conditions",
            event_types=[SecurityEventType.SUSPICIOUS_ACTIVITY],
            threat_levels=[ThreatLevel.MEDIUM],
            channels=[AlertChannel.SYSTEM_LOG],
            priority=AlertPriority.MEDIUM,
            recipients=['test@example.com'],
            conditions={
                'tenant_ids': [self.tenant_id],
                'ip_patterns': [r'192\.168\..*']
            }
        )
        
        # Event that matches conditions
        matching_event = SecurityEvent(
            event_id="test_event_006",
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            threat_level=ThreatLevel.MEDIUM,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            ip_address="192.168.1.100",
            timestamp=datetime.now(),
            description="Test event",
            details={}
        )
        
        # Event that doesn't match conditions
        non_matching_event = SecurityEvent(
            event_id="test_event_007",
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            threat_level=ThreatLevel.MEDIUM,
            tenant_id="different_tenant",
            user_id=self.user_id,
            ip_address="10.0.0.1",
            timestamp=datetime.now(),
            description="Test event",
            details={}
        )
        
        assert self.alert_system._check_rule_conditions(matching_event, rule) is True
        assert self.alert_system._check_rule_conditions(non_matching_event, rule) is False
    
    def test_generate_alert_id(self):
        """Test alert ID generation."""
        event = SecurityEvent(
            event_id="test_event_008",
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            threat_level=ThreatLevel.MEDIUM,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            ip_address="192.168.1.100",
            timestamp=datetime.now(),
            description="Test event",
            details={}
        )
        
        rule = self.alert_system.alert_rules['critical_threats']
        
        alert_id1 = self.alert_system._generate_alert_id(event, rule)
        alert_id2 = self.alert_system._generate_alert_id(event, rule)
        
        # Should generate different IDs each time
        assert alert_id1 != alert_id2
        assert alert_id1.startswith('ALERT_')
        assert len(alert_id1) == 18  # ALERT_ + 12 char hash
    
    def test_build_alert_message(self):
        """Test alert message building."""
        event = SecurityEvent(
            event_id="test_event_009",
            event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
            threat_level=ThreatLevel.CRITICAL,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            ip_address="192.168.1.100",
            timestamp=datetime.now(),
            description="Brute force attack detected",
            details={"attempts": 20, "target_user": "admin"}
        )
        
        rule = self.alert_system.alert_rules['critical_threats']
        
        message = self.alert_system._build_alert_message(event, rule)
        
        # Check message contains key information
        assert event.event_id in message
        assert event.event_type.value in message
        assert event.threat_level.value in message
        assert event.description in message
        assert str(event.user_id) in message
        assert event.ip_address in message
        assert rule.name in message
        assert "attempts: 20" in message
        assert "target_user: admin" in message
    
    def test_get_alert_statistics(self):
        """Test alert statistics generation."""
        # Add some test notifications
        notification1 = AlertNotification(
            notification_id="notif_001",
            alert_id="alert_001",
            rule_id="critical_threats",
            channel=AlertChannel.EMAIL,
            recipient="test@example.com",
            subject="Test Alert",
            message="Test message",
            priority=AlertPriority.CRITICAL,
            created_at=datetime.now(),
            status=AlertStatus.SENT
        )
        
        notification2 = AlertNotification(
            notification_id="notif_002",
            alert_id="alert_002",
            rule_id="anomalous_behavior",
            channel=AlertChannel.SLACK,
            recipient="#security",
            subject="Test Alert 2",
            message="Test message 2",
            priority=AlertPriority.MEDIUM,
            created_at=datetime.now(),
            status=AlertStatus.FAILED
        )
        
        self.alert_system.sent_notifications.extend([notification1, notification2])
        
        stats = self.alert_system.get_alert_statistics()
        
        assert stats['total_notifications'] == 2
        assert stats['successful_notifications'] == 1
        assert stats['failed_notifications'] == 1
        assert stats['success_rate'] == 0.5
        assert stats['priority_distribution']['critical'] == 1
        assert stats['priority_distribution']['medium'] == 1
        assert stats['channel_distribution']['email'] == 1
        assert stats['channel_distribution']['slack'] == 1


class TestAlertChannelHandlers:
    """Test alert channel handlers."""
    
    def setup_method(self):
        """Setup test environment."""
        self.email_config = {
            'smtp_server': 'localhost',
            'smtp_port': 587,
            'username': 'test@example.com',
            'password': 'test_password',
            'sender_email': 'alerts@example.com'
        }
        self.slack_config = {
            'webhook_url': 'https://hooks.slack.com/test'
        }
        self.webhook_config = {}
    
    @pytest.mark.asyncio
    async def test_system_log_handler(self):
        """Test system log alert handler."""
        handler = SystemLogAlertHandler({})
        
        with patch.object(handler.logger, 'critical') as mock_log:
            success = await handler.send_notification(
                recipient="system",
                subject="Test Alert",
                message="Test message",
                priority=AlertPriority.EMERGENCY
            )
            
            assert success is True
            mock_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_email_handler_success(self):
        """Test email handler successful sending."""
        handler = EmailAlertHandler(self.email_config)
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            success = await handler.send_notification(
                recipient="test@example.com",
                subject="Test Alert",
                message="Test message",
                priority=AlertPriority.HIGH
            )
            
            assert success is True
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_email_handler_failure(self):
        """Test email handler failure handling."""
        handler = EmailAlertHandler(self.email_config)
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP connection failed")
            
            success = await handler.send_notification(
                recipient="test@example.com",
                subject="Test Alert",
                message="Test message",
                priority=AlertPriority.HIGH
            )
            
            assert success is False
    
    @pytest.mark.asyncio
    async def test_slack_handler_success(self):
        """Test Slack handler successful sending."""
        handler = SlackAlertHandler(self.slack_config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            success = await handler.send_notification(
                recipient="#security",
                subject="Test Alert",
                message="Test message",
                priority=AlertPriority.CRITICAL
            )
            
            assert success is True
    
    @pytest.mark.asyncio
    async def test_slack_handler_failure(self):
        """Test Slack handler failure handling."""
        handler = SlackAlertHandler(self.slack_config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_post.return_value.__aenter__.return_value = mock_response
            
            success = await handler.send_notification(
                recipient="#security",
                subject="Test Alert",
                message="Test message",
                priority=AlertPriority.CRITICAL
            )
            
            assert success is False
    
    @pytest.mark.asyncio
    async def test_webhook_handler_success(self):
        """Test webhook handler successful sending."""
        handler = WebhookAlertHandler(self.webhook_config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            success = await handler.send_notification(
                recipient="https://example.com/webhook",
                subject="Test Alert",
                message="Test message",
                priority=AlertPriority.MEDIUM
            )
            
            assert success is True
    
    @pytest.mark.asyncio
    async def test_webhook_handler_failure(self):
        """Test webhook handler failure handling."""
        handler = WebhookAlertHandler(self.webhook_config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = Exception("Connection timeout")
            
            success = await handler.send_notification(
                recipient="https://example.com/webhook",
                subject="Test Alert",
                message="Test message",
                priority=AlertPriority.MEDIUM
            )
            
            assert success is False


class TestAlertSystemIntegration:
    """Test alert system integration scenarios."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = {
            'email': {'enabled': True, 'smtp_server': 'localhost'},
            'slack': {'enabled': True, 'webhook_url': 'https://hooks.slack.com/test'},
            'webhook': {'enabled': True}
        }
        self.alert_system = RealTimeAlertSystem(self.config)
    
    @pytest.mark.asyncio
    async def test_start_stop_notification_processing(self):
        """Test starting and stopping notification processing."""
        assert not self.alert_system.running
        
        # Start processing
        await self.alert_system.start_notification_processing()
        assert self.alert_system.running
        assert self.alert_system.notification_task is not None
        
        # Stop processing
        await self.alert_system.stop_notification_processing()
        assert not self.alert_system.running
    
    @pytest.mark.asyncio
    async def test_notification_processing_loop(self):
        """Test notification processing loop functionality."""
        # Add a test notification
        notification = AlertNotification(
            notification_id="test_notif_001",
            alert_id="test_alert_001",
            rule_id="critical_threats",
            channel=AlertChannel.SYSTEM_LOG,
            recipient="system",
            subject="Test Alert",
            message="Test message",
            priority=AlertPriority.HIGH,
            created_at=datetime.now()
        )
        
        self.alert_system.pending_notifications.append(notification)
        
        # Process notifications
        await self.alert_system._process_pending_notifications()
        
        # Check that notification was processed
        assert len(self.alert_system.pending_notifications) == 0
        assert len(self.alert_system.sent_notifications) == 1
        assert self.alert_system.sent_notifications[0].status == AlertStatus.SENT
    
    @pytest.mark.asyncio
    async def test_end_to_end_alert_flow(self):
        """Test complete end-to-end alert flow."""
        # Create a security event
        event = SecurityEvent(
            event_id="e2e_test_001",
            event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
            threat_level=ThreatLevel.CRITICAL,
            tenant_id="test_tenant",
            user_id=uuid4(),
            ip_address="192.168.1.100",
            timestamp=datetime.now(),
            description="End-to-end test brute force attack",
            details={"pattern_id": "brute_force_login", "attempts": 25}
        )
        
        # Process the event
        await self.alert_system.process_security_event(event)
        
        # Verify notifications were generated
        assert len(self.alert_system.pending_notifications) > 0
        
        # Process notifications
        await self.alert_system._process_pending_notifications()
        
        # Verify notifications were sent
        assert len(self.alert_system.sent_notifications) > 0
        
        # Check that at least one notification was successful
        successful_notifications = [
            n for n in self.alert_system.sent_notifications
            if n.status == AlertStatus.SENT
        ]
        assert len(successful_notifications) > 0
        
        # Verify alert statistics
        stats = self.alert_system.get_alert_statistics()
        assert stats['total_notifications'] > 0
        assert stats['successful_notifications'] > 0