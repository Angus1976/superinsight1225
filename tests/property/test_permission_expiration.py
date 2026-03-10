"""
Property-Based Tests for Permission Expiration

**Validates: Requirements 9.6**

Property 22: Permission Expiration
For any permission with an expiration date, the permission should not be 
honored after the expiration date.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from unittest.mock import patch

from src.models.data_lifecycle import (
    ResourceType,
    Action,
    PermissionModel
)
from src.services.permission_manager import PermissionManager, Resource


# ============================================================================
# Test Strategies
# ============================================================================

@st.composite
def user_id_strategy(draw):
    """Generate valid user IDs"""
    return f"user_{draw(st.integers(min_value=1, max_value=1000))}"


@st.composite
def resource_strategy(draw):
    """Generate valid resources"""
    resource_type = draw(st.sampled_from(list(ResourceType)))
    resource_id = str(uuid4())
    return Resource(type=resource_type, id=resource_id)


@st.composite
def action_strategy(draw):
    """Generate valid actions"""
    return draw(st.sampled_from(list(Action)))


@st.composite
def expiring_permission_strategy(draw):
    """Generate permission with expiration date"""
    user_id = draw(user_id_strategy())
    resource = draw(resource_strategy())
    actions = draw(st.lists(action_strategy(), min_size=1, max_size=3, unique=True))
    granted_by = draw(user_id_strategy())
    
    # Generate expiration date (1 to 30 days in the future)
    days_until_expiry = draw(st.integers(min_value=1, max_value=30))
    expires_at = datetime.utcnow() + timedelta(days=days_until_expiry)
    
    return {
        'user_id': user_id,
        'resource': resource,
        'actions': actions,
        'granted_by': granted_by,
        'expires_at': expires_at,
        'days_until_expiry': days_until_expiry
    }


# ============================================================================
# Property Tests
# ============================================================================

@pytest.mark.property
@given(
    grant_data=expiring_permission_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_expiration_before_expiry(
    db_session: Session,
    grant_data: dict
):
    """
    Property: Before expiration date, permission should be granted.
    
    **Validates: Requirements 9.6**
    """
    permission_manager = PermissionManager(db_session)
    
    # Grant permission with expiration
    permission = permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Check permission before expiration
    for action in grant_data['actions']:
        has_permission = permission_manager.check_permission(
            user_id=grant_data['user_id'],
            resource=grant_data['resource'],
            action=action
        )
        
        # Property: Permission should be granted before expiration
        assert has_permission, \
            f"Permission should be granted before expiration date for action {action.value}"


@pytest.mark.property
@given(
    grant_data=expiring_permission_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_expiration_after_expiry(
    db_session: Session,
    grant_data: dict
):
    """
    Property: After expiration date, permission should be denied.
    
    **Validates: Requirements 9.6**
    """
    permission_manager = PermissionManager(db_session)
    
    # Grant permission with expiration
    permission = permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Mock current time to be after expiration
    future_time = grant_data['expires_at'] + timedelta(days=1)
    
    with patch('src.services.permission_manager.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = future_time
        
        # Check permission after expiration
        for action in grant_data['actions']:
            has_permission = permission_manager.check_permission(
                user_id=grant_data['user_id'],
                resource=grant_data['resource'],
                action=action
            )
            
            # Property: Permission should be denied after expiration
            assert not has_permission, \
                f"Permission should be denied after expiration date for action {action.value}"


@pytest.mark.property
@given(
    grant_data=expiring_permission_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_expiration_at_exact_expiry(
    db_session: Session,
    grant_data: dict
):
    """
    Property: At exact expiration time, permission should be denied.
    
    **Validates: Requirements 9.6**
    """
    permission_manager = PermissionManager(db_session)
    
    # Grant permission with expiration
    permission = permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Mock current time to be exactly at expiration
    with patch('src.services.permission_manager.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = grant_data['expires_at']
        
        # Check permission at exact expiration time
        for action in grant_data['actions']:
            has_permission = permission_manager.check_permission(
                user_id=grant_data['user_id'],
                resource=grant_data['resource'],
                action=action
            )
            
            # Property: Permission should be denied at exact expiration time
            assert not has_permission, \
                f"Permission should be denied at exact expiration time for action {action.value}"


@pytest.mark.property
@given(
    grant_data=expiring_permission_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_expiration_one_second_before(
    db_session: Session,
    grant_data: dict
):
    """
    Property: One second before expiration, permission should still be granted.
    
    **Validates: Requirements 9.6**
    """
    permission_manager = PermissionManager(db_session)
    
    # Grant permission with expiration
    permission = permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Mock current time to be one second before expiration
    one_second_before = grant_data['expires_at'] - timedelta(seconds=1)
    
    with patch('src.services.permission_manager.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = one_second_before
        
        # Check permission one second before expiration
        for action in grant_data['actions']:
            has_permission = permission_manager.check_permission(
                user_id=grant_data['user_id'],
                resource=grant_data['resource'],
                action=action
            )
            
            # Property: Permission should still be granted one second before expiration
            assert has_permission, \
                f"Permission should be granted one second before expiration for action {action.value}"


@pytest.mark.property
@given(
    grant_data=expiring_permission_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_expiration_cleanup(
    db_session: Session,
    grant_data: dict
):
    """
    Property: Cleanup should remove expired permissions.
    
    **Validates: Requirements 9.6**
    """
    permission_manager = PermissionManager(db_session)
    
    # Grant permission with expiration
    permission = permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Mock current time to be after expiration
    future_time = grant_data['expires_at'] + timedelta(days=1)
    
    with patch('src.services.permission_manager.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = future_time
        
        # Run cleanup
        removed_count = permission_manager.cleanup_expired_permissions()
        
        # Property: At least one permission should be removed
        assert removed_count >= 1, \
            "Cleanup should remove at least one expired permission"
        
        # Verify permission is actually removed from database
        db_permission = db_session.query(PermissionModel).filter(
            PermissionModel.id == permission.id
        ).first()
        
        assert db_permission is None, \
            "Expired permission should be removed from database after cleanup"


@pytest.mark.property
@given(
    grant_data=expiring_permission_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_expiration_get_user_permissions(
    db_session: Session,
    grant_data: dict
):
    """
    Property: get_user_permissions should not return expired permissions by default.
    
    **Validates: Requirements 9.6**
    """
    permission_manager = PermissionManager(db_session)
    
    # Grant permission with expiration
    permission = permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Get permissions before expiration
    permissions_before = permission_manager.get_user_permissions(
        user_id=grant_data['user_id'],
        include_expired=False
    )
    
    # Property: Permission should be included before expiration
    assert len(permissions_before) >= 1, \
        "User permissions should include non-expired permission"
    assert any(p.id == permission.id for p in permissions_before), \
        "Specific permission should be in user permissions before expiration"
    
    # Mock current time to be after expiration
    future_time = grant_data['expires_at'] + timedelta(days=1)
    
    with patch('src.services.permission_manager.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = future_time
        
        # Get permissions after expiration (without include_expired)
        permissions_after = permission_manager.get_user_permissions(
            user_id=grant_data['user_id'],
            include_expired=False
        )
        
        # Property: Expired permission should not be included
        assert not any(p.id == permission.id for p in permissions_after), \
            "Expired permission should not be in user permissions by default"
        
        # Get permissions with include_expired=True
        permissions_with_expired = permission_manager.get_user_permissions(
            user_id=grant_data['user_id'],
            include_expired=True
        )
        
        # Property: Expired permission should be included when explicitly requested
        assert any(p.id == permission.id for p in permissions_with_expired), \
            "Expired permission should be included when include_expired=True"


@pytest.mark.property
@given(
    grant_data=expiring_permission_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_expiration_get_resource_permissions(
    db_session: Session,
    grant_data: dict
):
    """
    Property: get_resource_permissions should not return expired permissions by default.
    
    **Validates: Requirements 9.6**
    """
    permission_manager = PermissionManager(db_session)
    
    # Grant permission with expiration
    permission = permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Get permissions before expiration
    permissions_before = permission_manager.get_resource_permissions(
        resource=grant_data['resource'],
        include_expired=False
    )
    
    # Property: Permission should be included before expiration
    assert len(permissions_before) >= 1, \
        "Resource permissions should include non-expired permission"
    assert any(p.id == permission.id for p in permissions_before), \
        "Specific permission should be in resource permissions before expiration"
    
    # Mock current time to be after expiration
    future_time = grant_data['expires_at'] + timedelta(days=1)
    
    with patch('src.services.permission_manager.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = future_time
        
        # Get permissions after expiration (without include_expired)
        permissions_after = permission_manager.get_resource_permissions(
            resource=grant_data['resource'],
            include_expired=False
        )
        
        # Property: Expired permission should not be included
        assert not any(p.id == permission.id for p in permissions_after), \
            "Expired permission should not be in resource permissions by default"
        
        # Get permissions with include_expired=True
        permissions_with_expired = permission_manager.get_resource_permissions(
            resource=grant_data['resource'],
            include_expired=True
        )
        
        # Property: Expired permission should be included when explicitly requested
        assert any(p.id == permission.id for p in permissions_with_expired), \
            "Expired permission should be included when include_expired=True"


@pytest.mark.property
@given(
    user_id=user_id_strategy(),
    resource=resource_strategy(),
    actions=st.lists(action_strategy(), min_size=1, max_size=3, unique=True),
    granted_by=user_id_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_no_expiration_always_valid(
    db_session: Session,
    user_id: str,
    resource: Resource,
    actions: list,
    granted_by: str
):
    """
    Property: Permissions without expiration date should always be valid.
    
    **Validates: Requirements 9.6**
    """
    permission_manager = PermissionManager(db_session)
    
    # Grant permission without expiration
    permission = permission_manager.grant_permission(
        user_id=user_id,
        resource=resource,
        actions=actions,
        granted_by=granted_by,
        expires_at=None  # No expiration
    )
    
    # Check permission now
    for action in actions:
        has_permission_now = permission_manager.check_permission(
            user_id=user_id,
            resource=resource,
            action=action
        )
        assert has_permission_now, \
            f"Permission without expiration should be valid now for action {action.value}"
    
    # Mock current time to be far in the future (1 year)
    future_time = datetime.utcnow() + timedelta(days=365)
    
    with patch('src.services.permission_manager.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = future_time
        
        # Check permission in the future
        for action in actions:
            has_permission_future = permission_manager.check_permission(
                user_id=user_id,
                resource=resource,
                action=action
            )
            
            # Property: Permission without expiration should still be valid
            assert has_permission_future, \
                f"Permission without expiration should be valid in the future for action {action.value}"
