"""
Unit tests for Permission Manager.
"""

import pytest
import ipaddress
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, time

from src.security.permission_manager import (
    PermissionManager, AccessContext, PolicyResult,
    get_permission_manager
)
from src.security.rbac_engine import AccessDecision, Permission
from src.models.security import DynamicPolicyModel, PolicyType, IPWhitelistModel


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = MagicMock()
    db.query = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.rollback = MagicMock()
    db.refresh = MagicMock()
    return db


@pytest.fixture
def mock_rbac_engine():
    """Create mock RBAC engine."""
    engine = MagicMock()
    engine.check_permission = MagicMock()
    return engine


@pytest.fixture
def permission_manager(mock_rbac_engine):
    """Create permission manager instance."""
    return PermissionManager(rbac_engine=mock_rbac_engine)


@pytest.fixture
def access_context():
    """Create test access context."""
    return AccessContext(
        ip_address="192.168.1.100",
        timestamp=datetime(2024, 1, 15, 10, 30),
        user_agent="TestAgent/1.0",
        session_id="session123",
        request_id="req456",
        attributes={"department": "engineering", "clearance_level": 3}
    )


class TestAccessContext:
    """Tests for AccessContext dataclass."""

    def test_access_context_creation(self):
        """Test creating access context."""
        context = AccessContext(
            ip_address="10.0.0.1",
            user_agent="Browser/1.0"
        )
        assert context.ip_address == "10.0.0.1"
        assert context.user_agent == "Browser/1.0"
        assert isinstance(context.timestamp, datetime)
        assert context.attributes == {}

    def test_access_context_with_attributes(self):
        """Test access context with attributes."""
        attrs = {"role": "admin", "level": 5}
        context = AccessContext(attributes=attrs)
        assert context.attributes == attrs


class TestPolicyResult:
    """Tests for PolicyResult dataclass."""

    def test_policy_result_allowed(self):
        """Test allowed policy result."""
        result = PolicyResult(allowed=True)
        assert result.allowed is True
        assert result.policy_name is None
        assert result.details == {}

    def test_policy_result_denied(self):
        """Test denied policy result."""
        result = PolicyResult(
            allowed=False,
            policy_name="time_policy",
            policy_type=PolicyType.TIME_RANGE,
            reason="Outside business hours",
            details={"current_hour": 22}
        )
        assert result.allowed is False
        assert result.policy_name == "time_policy"
        assert result.policy_type == PolicyType.TIME_RANGE
        assert result.reason == "Outside business hours"
        assert result.details["current_hour"] == 22


class TestPermissionManager:
    """Tests for PermissionManager class."""

    def test_permission_manager_creation(self, permission_manager):
        """Test creating permission manager."""
        assert permission_manager is not None
        assert permission_manager.rbac_engine is not None
        assert len(permission_manager.policy_priority) > 0

    def test_get_permission_manager_singleton(self):
        """Test singleton pattern for permission manager."""
        pm1 = get_permission_manager()
        pm2 = get_permission_manager()
        assert pm1 is pm2

    def test_check_access_rbac_denied(self, permission_manager, mock_db, access_context):
        """Test access check when RBAC denies access."""
        user_id = uuid4()
        
        # Mock RBAC to deny access
        permission_manager.rbac_engine.check_permission.return_value = AccessDecision(
            allowed=False,
            reason="No permission"
        )
        
        # Mock logging
        with patch.object(permission_manager, '_log_decision') as mock_log:
            decision = permission_manager.check_access(
                user_id=user_id,
                resource="projects/123",
                action="read",
                tenant_id="tenant1",
                context=access_context,
                db=mock_db
            )
        
        assert decision.allowed is False
        assert decision.reason == "No permission"
        mock_log.assert_called_once()

    def test_check_access_rbac_allowed_no_policies(self, permission_manager, mock_db, access_context):
        """Test access check when RBAC allows and no policies block."""
        user_id = uuid4()
        
        # Mock RBAC to allow access
        permission_manager.rbac_engine.check_permission.return_value = AccessDecision(
            allowed=True,
            reason="Permission granted"
        )
        
        # Mock no applicable policies
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        # Mock logging
        with patch.object(permission_manager, '_log_decision') as mock_log:
            decision = permission_manager.check_access(
                user_id=user_id,
                resource="projects/123",
                action="read",
                tenant_id="tenant1",
                context=access_context,
                db=mock_db
            )
        
        assert decision.allowed is True
        assert decision.reason == "Access granted"
        mock_log.assert_called_once()

    def test_check_access_policy_blocks(self, permission_manager, mock_db, access_context):
        """Test access check when policy blocks access."""
        user_id = uuid4()
        
        # Mock RBAC to allow access
        permission_manager.rbac_engine.check_permission.return_value = AccessDecision(
            allowed=True,
            reason="Permission granted"
        )
        
        # Mock policy that blocks access
        mock_policy = MagicMock()
        mock_policy.resource_pattern = "projects/*"
        mock_policy.policy_type = PolicyType.TIME_RANGE
        mock_policy.name = "business_hours"
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_policy]
        
        # Mock policy evaluation to deny
        with patch.object(permission_manager, '_evaluate_policy') as mock_eval:
            mock_eval.return_value = PolicyResult(
                allowed=False,
                policy_name="business_hours",
                reason="Outside business hours"
            )
            
            with patch.object(permission_manager, '_log_decision') as mock_log:
                decision = permission_manager.check_access(
                    user_id=user_id,
                    resource="projects/123",
                    action="read",
                    tenant_id="tenant1",
                    context=access_context,
                    db=mock_db
                )
        
        assert decision.allowed is False
        assert decision.reason == "Outside business hours"
        assert decision.policy_applied == "business_hours"
        mock_log.assert_called_once()


class TestTimeRangePolicy:
    """Tests for time range policy evaluation."""

    def test_time_range_policy_allowed(self, permission_manager):
        """Test time range policy allows access during business hours."""
        policy = MagicMock()
        policy.name = "business_hours"
        policy.policy_type = PolicyType.TIME_RANGE
        policy.config = {
            "start_hour": 9,
            "end_hour": 18,
            "allowed_days": [0, 1, 2, 3, 4]  # Monday-Friday
        }
        
        # Monday 10:30 AM
        context = AccessContext(timestamp=datetime(2024, 1, 15, 10, 30))
        
        result = permission_manager._check_time_range(policy, context)
        
        assert result.allowed is True

    def test_time_range_policy_denied_hour(self, permission_manager):
        """Test time range policy denies access outside hours."""
        policy = MagicMock()
        policy.name = "business_hours"
        policy.policy_type = PolicyType.TIME_RANGE
        policy.config = {
            "start_hour": 9,
            "end_hour": 18,
            "allowed_days": [0, 1, 2, 3, 4]
        }
        
        # Monday 8:30 AM (before start)
        context = AccessContext(timestamp=datetime(2024, 1, 15, 8, 30))
        
        result = permission_manager._check_time_range(policy, context)
        
        assert result.allowed is False
        assert "hour 8" in result.reason
        assert result.details["current_hour"] == 8

    def test_time_range_policy_denied_day(self, permission_manager):
        """Test time range policy denies access on weekend."""
        policy = MagicMock()
        policy.name = "business_hours"
        policy.policy_type = PolicyType.TIME_RANGE
        policy.config = {
            "start_hour": 9,
            "end_hour": 18,
            "allowed_days": [0, 1, 2, 3, 4]  # Monday-Friday
        }
        
        # Saturday 10:30 AM
        context = AccessContext(timestamp=datetime(2024, 1, 13, 10, 30))  # Saturday
        
        result = permission_manager._check_time_range(policy, context)
        
        assert result.allowed is False
        assert "day 5" in result.reason  # Saturday is day 5
        assert result.details["current_day"] == 5


class TestIPWhitelistPolicy:
    """Tests for IP whitelist policy evaluation."""

    def test_ip_whitelist_no_ip_deny_default(self, permission_manager, mock_db):
        """Test IP whitelist denies when no IP and deny_by_default."""
        policy = MagicMock()
        policy.name = "ip_whitelist"
        policy.policy_type = PolicyType.IP_WHITELIST
        policy.deny_by_default = True
        policy.config = {"whitelist": ["192.168.1.0/24"]}
        
        context = AccessContext()  # No IP address
        
        result = permission_manager._check_ip_whitelist(policy, context, mock_db)
        
        assert result.allowed is False
        assert "No IP address" in result.reason

    def test_ip_whitelist_private_ip_allowed(self, permission_manager, mock_db):
        """Test IP whitelist allows private IPs when configured."""
        policy = MagicMock()
        policy.name = "ip_whitelist"
        policy.policy_type = PolicyType.IP_WHITELIST
        policy.config = {
            "whitelist": [],
            "allow_private": True
        }
        
        context = AccessContext(ip_address="192.168.1.100")
        
        result = permission_manager._check_ip_whitelist(policy, context, mock_db)
        
        assert result.allowed is True

    def test_ip_whitelist_config_whitelist_match(self, permission_manager, mock_db):
        """Test IP whitelist matches config whitelist."""
        policy = MagicMock()
        policy.name = "ip_whitelist"
        policy.policy_type = PolicyType.IP_WHITELIST
        policy.config = {
            "whitelist": ["192.168.1.0/24", "10.0.0.0/8"],
            "allow_private": False
        }
        
        context = AccessContext(ip_address="192.168.1.50")
        
        result = permission_manager._check_ip_whitelist(policy, context, mock_db)
        
        assert result.allowed is True

    def test_ip_whitelist_database_whitelist_match(self, permission_manager, mock_db):
        """Test IP whitelist matches database whitelist."""
        policy = MagicMock()
        policy.name = "ip_whitelist"
        policy.policy_type = PolicyType.IP_WHITELIST
        policy.tenant_id = "tenant1"
        policy.config = {
            "whitelist": [],
            "use_database_whitelist": True,
            "allow_private": False
        }
        
        # Mock database whitelist entry
        whitelist_entry = MagicMock()
        whitelist_entry.ip_range = "203.0.113.0/24"
        whitelist_entry.ip_address = None
        mock_db.query.return_value.filter.return_value.all.return_value = [whitelist_entry]
        
        context = AccessContext(ip_address="203.0.113.10")
        
        result = permission_manager._check_ip_whitelist(policy, context, mock_db)
        
        assert result.allowed is True

    def test_ip_whitelist_denied(self, permission_manager, mock_db):
        """Test IP whitelist denies unlisted IP."""
        policy = MagicMock()
        policy.name = "ip_whitelist"
        policy.policy_type = PolicyType.IP_WHITELIST
        policy.tenant_id = "tenant1"
        policy.config = {
            "whitelist": ["192.168.1.0/24"],
            "use_database_whitelist": True,
            "allow_private": False
        }
        
        # Mock empty database whitelist
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        context = AccessContext(ip_address="203.0.113.10")
        
        result = permission_manager._check_ip_whitelist(policy, context, mock_db)
        
        assert result.allowed is False
        assert "not in whitelist" in result.reason


class TestSensitivityLevelPolicy:
    """Tests for sensitivity level policy evaluation."""

    def test_sensitivity_level_allowed(self, permission_manager, mock_db):
        """Test sensitivity level policy allows sufficient clearance."""
        policy = MagicMock()
        policy.name = "clearance_check"
        policy.policy_type = PolicyType.SENSITIVITY_LEVEL
        policy.config = {
            "required_level": 3,
            "user_level_attribute": "clearance_level"
        }
        
        context = AccessContext(attributes={"clearance_level": 5})
        
        result = permission_manager._check_sensitivity_level(policy, uuid4(), context, mock_db)
        
        assert result.allowed is True

    def test_sensitivity_level_denied(self, permission_manager, mock_db):
        """Test sensitivity level policy denies insufficient clearance."""
        policy = MagicMock()
        policy.name = "clearance_check"
        policy.policy_type = PolicyType.SENSITIVITY_LEVEL
        policy.config = {
            "required_level": 5,
            "user_level_attribute": "clearance_level"
        }
        
        context = AccessContext(attributes={"clearance_level": 3})
        
        result = permission_manager._check_sensitivity_level(policy, uuid4(), context, mock_db)
        
        assert result.allowed is False
        assert "Insufficient clearance level" in result.reason
        assert result.details["user_level"] == 3
        assert result.details["required_level"] == 5

    def test_sensitivity_level_no_attribute(self, permission_manager, mock_db):
        """Test sensitivity level policy with missing attribute."""
        policy = MagicMock()
        policy.name = "clearance_check"
        policy.policy_type = PolicyType.SENSITIVITY_LEVEL
        policy.config = {
            "required_level": 3,
            "user_level_attribute": "clearance_level"
        }
        
        context = AccessContext(attributes={})  # No clearance level
        
        result = permission_manager._check_sensitivity_level(policy, uuid4(), context, mock_db)
        
        assert result.allowed is False  # Default level 0 < required 3


class TestAttributePolicy:
    """Tests for attribute-based policy evaluation."""

    def test_attribute_policy_match_all_success(self, permission_manager, mock_db):
        """Test attribute policy with match_all=True succeeds."""
        policy = MagicMock()
        policy.name = "attr_policy"
        policy.policy_type = PolicyType.ATTRIBUTE
        policy.config = {
            "conditions": [
                {"attribute": "department", "operator": "eq", "value": "engineering"},
                {"attribute": "role", "operator": "in", "value": ["admin", "manager"]}
            ],
            "match_all": True
        }
        
        context = AccessContext(attributes={
            "department": "engineering",
            "role": "admin"
        })
        
        result = permission_manager._check_attribute_policy(policy, uuid4(), context, mock_db)
        
        assert result.allowed is True

    def test_attribute_policy_match_all_failure(self, permission_manager, mock_db):
        """Test attribute policy with match_all=True fails."""
        policy = MagicMock()
        policy.name = "attr_policy"
        policy.policy_type = PolicyType.ATTRIBUTE
        policy.config = {
            "conditions": [
                {"attribute": "department", "operator": "eq", "value": "engineering"},
                {"attribute": "role", "operator": "eq", "value": "admin"}
            ],
            "match_all": True
        }
        
        context = AccessContext(attributes={
            "department": "engineering",
            "role": "user"  # Doesn't match admin
        })
        
        result = permission_manager._check_attribute_policy(policy, uuid4(), context, mock_db)
        
        assert result.allowed is False
        assert "Attribute conditions not met" in result.reason

    def test_attribute_policy_match_any_success(self, permission_manager, mock_db):
        """Test attribute policy with match_all=False succeeds."""
        policy = MagicMock()
        policy.name = "attr_policy"
        policy.policy_type = PolicyType.ATTRIBUTE
        policy.config = {
            "conditions": [
                {"attribute": "department", "operator": "eq", "value": "sales"},
                {"attribute": "role", "operator": "eq", "value": "admin"}
            ],
            "match_all": False
        }
        
        context = AccessContext(attributes={
            "department": "engineering",  # Doesn't match
            "role": "admin"  # Matches
        })
        
        result = permission_manager._check_attribute_policy(policy, uuid4(), context, mock_db)
        
        assert result.allowed is True


class TestConditionEvaluation:
    """Tests for condition evaluation methods."""

    def test_evaluate_condition_eq(self, permission_manager):
        """Test equality condition."""
        assert permission_manager._evaluate_condition("admin", "eq", "admin") is True
        assert permission_manager._evaluate_condition("user", "eq", "admin") is False

    def test_evaluate_condition_in(self, permission_manager):
        """Test in condition."""
        assert permission_manager._evaluate_condition("admin", "in", ["admin", "manager"]) is True
        assert permission_manager._evaluate_condition("user", "in", ["admin", "manager"]) is False

    def test_evaluate_condition_gt(self, permission_manager):
        """Test greater than condition."""
        assert permission_manager._evaluate_condition(5, "gt", 3) is True
        assert permission_manager._evaluate_condition(2, "gt", 3) is False

    def test_evaluate_condition_contains(self, permission_manager):
        """Test contains condition."""
        assert permission_manager._evaluate_condition("hello world", "contains", "world") is True
        assert permission_manager._evaluate_condition("hello", "contains", "world") is False

    def test_evaluate_condition_null(self, permission_manager):
        """Test null conditions."""
        assert permission_manager._evaluate_condition(None, "is_null", None) is True
        assert permission_manager._evaluate_condition("value", "is_null", None) is False
        assert permission_manager._evaluate_condition(None, "is_not_null", None) is False
        assert permission_manager._evaluate_condition("value", "is_not_null", None) is True

    def test_evaluate_condition_unknown_operator(self, permission_manager):
        """Test unknown operator returns False."""
        with patch.object(permission_manager.logger, 'warning') as mock_warn:
            result = permission_manager._evaluate_condition("value", "unknown_op", "test")
            assert result is False
            mock_warn.assert_called_once()


class TestPolicyManagement:
    """Tests for policy management operations."""

    def test_create_policy_success(self, permission_manager, mock_db):
        """Test creating a policy successfully."""
        policy_data = {
            "name": "test_policy",
            "description": "Test policy",
            "tenant_id": "tenant1",
            "policy_type": PolicyType.TIME_RANGE,
            "resource_pattern": "projects/*",
            "config": {"start_hour": 9, "end_hour": 17},
            "priority": 10
        }
        
        policy = permission_manager.create_policy(db=mock_db, **policy_data)
        
        assert policy is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_policy_failure(self, permission_manager, mock_db):
        """Test policy creation failure."""
        mock_db.add.side_effect = Exception("Database error")
        
        policy = permission_manager.create_policy(
            name="test_policy",
            description="Test policy",
            tenant_id="tenant1",
            policy_type=PolicyType.TIME_RANGE,
            resource_pattern="projects/*",
            config={},
            db=mock_db
        )
        
        assert policy is None
        mock_db.rollback.assert_called_once()

    def test_list_policies(self, permission_manager, mock_db):
        """Test listing policies."""
        mock_policies = [MagicMock(), MagicMock()]
        
        # Set up the mock chain properly
        query_mock = MagicMock()
        filter_mock = MagicMock()
        order_mock = MagicMock()
        
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.filter.return_value = filter_mock  # For include_disabled filter
        filter_mock.order_by.return_value = order_mock
        order_mock.all.return_value = mock_policies
        
        policies = permission_manager.list_policies(
            tenant_id="tenant1",
            db=mock_db
        )
        
        assert policies == mock_policies

    def test_list_policies_with_type_filter(self, permission_manager, mock_db):
        """Test listing policies with type filter."""
        mock_policies = [MagicMock()]
        
        # Set up the mock chain properly
        query_mock = MagicMock()
        filter_mock = MagicMock()
        order_mock = MagicMock()
        
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.filter.return_value = filter_mock  # For policy_type filter
        filter_mock.filter.return_value = filter_mock  # For include_disabled filter
        filter_mock.order_by.return_value = order_mock
        order_mock.all.return_value = mock_policies
        
        policies = permission_manager.list_policies(
            tenant_id="tenant1",
            policy_type=PolicyType.TIME_RANGE,
            db=mock_db
        )
        
        assert policies == mock_policies
        # Verify filter was called multiple times (tenant_id, policy_type, include_disabled)
        assert query_mock.filter.call_count >= 1

    def test_update_policy_success(self, permission_manager, mock_db):
        """Test updating a policy successfully."""
        policy_id = uuid4()
        mock_policy = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_policy
        
        updates = {"name": "updated_policy", "enabled": False}
        result = permission_manager.update_policy(policy_id, updates, mock_db)
        
        assert result is True
        assert mock_policy.name == "updated_policy"
        assert mock_policy.enabled is False
        mock_db.commit.assert_called_once()

    def test_update_policy_not_found(self, permission_manager, mock_db):
        """Test updating non-existent policy."""
        policy_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = permission_manager.update_policy(policy_id, {"name": "test"}, mock_db)
        
        assert result is False
        mock_db.commit.assert_not_called()

    def test_delete_policy_success(self, permission_manager, mock_db):
        """Test deleting a policy successfully."""
        policy_id = uuid4()
        mock_policy = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_policy
        
        result = permission_manager.delete_policy(policy_id, mock_db)
        
        assert result is True
        mock_db.delete.assert_called_once_with(mock_policy)
        mock_db.commit.assert_called_once()

    def test_delete_policy_not_found(self, permission_manager, mock_db):
        """Test deleting non-existent policy."""
        policy_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = permission_manager.delete_policy(policy_id, mock_db)
        
        assert result is False
        mock_db.delete.assert_not_called()


class TestDecisionLogging:
    """Tests for decision logging functionality."""

    def test_log_decision_success(self, permission_manager, mock_db, access_context):
        """Test successful decision logging."""
        user_id = uuid4()
        decision = AccessDecision(allowed=True, reason="Access granted")
        
        # Mock previous log for hash chain
        mock_prev_log = MagicMock()
        mock_prev_log.hash = "prev_hash_123"
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_prev_log
        
        permission_manager._log_decision(
            user_id=user_id,
            resource="projects/123",
            action="read",
            tenant_id="tenant1",
            decision=decision,
            context=access_context,
            db=mock_db
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_log_decision_failure(self, permission_manager, mock_db, access_context):
        """Test decision logging failure doesn't break access check."""
        user_id = uuid4()
        decision = AccessDecision(allowed=True, reason="Access granted")
        
        # Mock database error
        mock_db.add.side_effect = Exception("Database error")
        
        # Should not raise exception
        permission_manager._log_decision(
            user_id=user_id,
            resource="projects/123",
            action="read",
            tenant_id="tenant1",
            decision=decision,
            context=access_context,
            db=mock_db
        )
        
        mock_db.rollback.assert_called_once()


class TestPolicyPatternMatching:
    """Tests for policy pattern matching."""

    def test_policy_applies_to_resource_exact_match(self, permission_manager):
        """Test exact resource pattern match."""
        assert permission_manager._policy_applies_to_resource("projects/123", "projects/123") is True
        assert permission_manager._policy_applies_to_resource("projects/123", "projects/456") is False

    def test_policy_applies_to_resource_wildcard(self, permission_manager):
        """Test wildcard resource pattern match."""
        assert permission_manager._policy_applies_to_resource("projects/*", "projects/123") is True
        assert permission_manager._policy_applies_to_resource("projects/*", "projects/456") is True
        assert permission_manager._policy_applies_to_resource("projects/*", "datasets/123") is False

    def test_policy_applies_to_resource_complex_pattern(self, permission_manager):
        """Test complex resource pattern match."""
        assert permission_manager._policy_applies_to_resource("*/sensitive/*", "projects/sensitive/data") is True
        assert permission_manager._policy_applies_to_resource("*/sensitive/*", "projects/public/data") is False