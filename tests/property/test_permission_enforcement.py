"""
Property-Based Tests for Permission Enforcement

**Validates: Requirements 9.1, 9.3**

Property 20: Permission Enforcement
For all operations, execution should only proceed if the user has the required 
permissions, otherwise a 403 Forbidden error should be returned.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session

from src.models.data_lifecycle import (
    ResourceType,
    Action,
    PermissionModel
)
from src.services.permission_manager import PermissionManager, Resource
from src.middleware.permission_middleware import (
    PermissionDeniedError,
    check_permission_sync
)


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
def permission_grant_strategy(draw):
    """Generate permission grant data"""
    user_id = draw(user_id_strategy())
    resource = draw(resource_strategy())
    actions = draw(st.lists(action_strategy(), min_size=1, max_size=3, unique=True))
    granted_by = draw(user_id_strategy())
    
    # Optional expiration (50% chance)
    has_expiration = draw(st.booleans())
    expires_at = None
    if has_expiration:
        # Generate future expiration date
        days_until_expiry = draw(st.integers(min_value=1, max_value=365))
        expires_at = datetime.utcnow() + timedelta(days=days_until_expiry)
    
    return {
        'user_id': user_id,
        'resource': resource,
        'actions': actions,
        'granted_by': granted_by,
        'expires_at': expires_at
    }


# ============================================================================
# Property Tests
# ============================================================================

@pytest.mark.property
@given(
    grant_data=permission_grant_strategy(),
    action_to_check=action_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_enforcement_granted_actions(
    db_session: Session,
    grant_data: dict,
    action_to_check: Action
):
    """
    Property: If a user has been granted an action on a resource,
    permission check should succeed for that action.
    
    **Validates: Requirements 9.1, 9.3**
    """
    permission_manager = PermissionManager(db_session)
    
    # Grant permissions
    permission = permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Check permission
    has_permission = permission_manager.check_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        action=action_to_check
    )
    
    # Property: Permission check should succeed if and only if the action was granted
    if action_to_check in grant_data['actions']:
        assert has_permission, \
            f"User should have permission for granted action {action_to_check.value}"
    else:
        assert not has_permission, \
            f"User should not have permission for non-granted action {action_to_check.value}"


@pytest.mark.property
@given(
    user_id=user_id_strategy(),
    resource=resource_strategy(),
    action=action_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_enforcement_no_grant(
    db_session: Session,
    user_id: str,
    resource: Resource,
    action: Action
):
    """
    Property: If no permission has been granted, permission check should fail.
    
    **Validates: Requirements 9.1, 9.3**
    """
    permission_manager = PermissionManager(db_session)
    
    # Check permission without granting it
    has_permission = permission_manager.check_permission(
        user_id=user_id,
        resource=resource,
        action=action
    )
    
    # Property: Permission should be denied
    assert not has_permission, \
        "User should not have permission without explicit grant"


@pytest.mark.property
@given(
    grant_data=permission_grant_strategy(),
    action_to_check=action_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_enforcement_403_error(
    db_session: Session,
    grant_data: dict,
    action_to_check: Action
):
    """
    Property: When permission is denied, a 403 Forbidden error should be raised.
    
    **Validates: Requirements 9.3**
    """
    permission_manager = PermissionManager(db_session)
    
    # Grant permissions (but not the action we'll check)
    assume(action_to_check not in grant_data['actions'])
    
    permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Try to check permission for non-granted action
    with pytest.raises(PermissionDeniedError) as exc_info:
        check_permission_sync(
            db=db_session,
            user_id=grant_data['user_id'],
            resource_type=grant_data['resource'].type,
            resource_id=grant_data['resource'].id,
            action=action_to_check
        )
    
    # Property: Error should be 403 Forbidden
    assert exc_info.value.status_code == 403, \
        "Permission denied should return 403 Forbidden"
    
    # Property: Error should include required permissions
    assert 'required_permissions' in exc_info.value.detail, \
        "Error should include required permissions"
    assert action_to_check.value in exc_info.value.detail['required_permissions'], \
        "Error should specify the required action"


@pytest.mark.property
@given(
    grant_data=permission_grant_strategy(),
    other_user_id=user_id_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_enforcement_user_isolation(
    db_session: Session,
    grant_data: dict,
    other_user_id: str
):
    """
    Property: Permissions granted to one user should not affect other users.
    
    **Validates: Requirements 9.1**
    """
    assume(other_user_id != grant_data['user_id'])
    
    permission_manager = PermissionManager(db_session)
    
    # Grant permissions to first user
    permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Check that other user doesn't have permission
    for action in grant_data['actions']:
        has_permission = permission_manager.check_permission(
            user_id=other_user_id,
            resource=grant_data['resource'],
            action=action
        )
        
        # Property: Other user should not have permission
        assert not has_permission, \
            f"User {other_user_id} should not have permission granted to {grant_data['user_id']}"


@pytest.mark.property
@given(
    grant_data=permission_grant_strategy(),
    other_resource=resource_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_enforcement_resource_isolation(
    db_session: Session,
    grant_data: dict,
    other_resource: Resource
):
    """
    Property: Permissions granted for one resource should not affect other resources.
    
    **Validates: Requirements 9.1**
    """
    assume(other_resource.id != grant_data['resource'].id)
    assume(other_resource.type == grant_data['resource'].type)
    
    permission_manager = PermissionManager(db_session)
    
    # Grant permissions for first resource
    permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Check that user doesn't have permission for other resource
    for action in grant_data['actions']:
        has_permission = permission_manager.check_permission(
            user_id=grant_data['user_id'],
            resource=other_resource,
            action=action
        )
        
        # Property: User should not have permission for other resource
        assert not has_permission, \
            f"Permission for resource {grant_data['resource'].id} should not apply to {other_resource.id}"


@pytest.mark.property
@given(
    grant_data=permission_grant_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_enforcement_revoke(
    db_session: Session,
    grant_data: dict
):
    """
    Property: After revoking permission, permission check should fail.
    
    **Validates: Requirements 9.1, 9.4**
    """
    permission_manager = PermissionManager(db_session)
    
    # Grant permissions
    permission_manager.grant_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        actions=grant_data['actions'],
        granted_by=grant_data['granted_by'],
        expires_at=grant_data['expires_at']
    )
    
    # Verify permission exists
    for action in grant_data['actions']:
        has_permission = permission_manager.check_permission(
            user_id=grant_data['user_id'],
            resource=grant_data['resource'],
            action=action
        )
        assert has_permission, "Permission should exist before revoke"
    
    # Revoke permissions
    revoked = permission_manager.revoke_permission(
        user_id=grant_data['user_id'],
        resource=grant_data['resource'],
        revoked_by=grant_data['granted_by']
    )
    
    assert revoked, "Revoke should succeed"
    
    # Property: Permission check should now fail
    for action in grant_data['actions']:
        has_permission = permission_manager.check_permission(
            user_id=grant_data['user_id'],
            resource=grant_data['resource'],
            action=action
        )
        assert not has_permission, \
            f"Permission should not exist after revoke for action {action.value}"


@pytest.mark.property
@given(
    role=st.sampled_from(['admin', 'reviewer', 'annotator', 'viewer']),
    resource_type=st.sampled_from(list(ResourceType)),
    action=action_strategy()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_permission_enforcement_rbac(
    db_session: Session,
    role: str,
    resource_type: ResourceType,
    action: Action
):
    """
    Property: Role-based permissions should be enforced according to role definitions.
    
    **Validates: Requirements 9.2**
    """
    permission_manager = PermissionManager(db_session)
    
    # Create a resource
    resource = Resource(type=resource_type, id=str(uuid4()))
    user_id = f"user_with_role_{role}"
    
    # Check permission with role
    has_permission = permission_manager.check_permission(
        user_id=user_id,
        resource=resource,
        action=action,
        user_roles=[role]
    )
    
    # Get expected permissions for this role and resource type
    expected_actions = permission_manager.ROLE_PERMISSIONS.get(role, {}).get(resource_type, [])
    
    # Property: Permission should match role definition
    if action in expected_actions:
        assert has_permission, \
            f"Role {role} should have permission for {action.value} on {resource_type.value}"
    else:
        assert not has_permission, \
            f"Role {role} should not have permission for {action.value} on {resource_type.value}"
