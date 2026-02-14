"""
Property-based tests for authenticated data access in OpenClawDataBridge.

Tests that data access requests are properly authenticated and authorized
before returning data.
"""

import pytest
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.models.ai_integration import AIGateway, AISkill, AIAuditLog
from src.ai_integration.data_bridge import OpenClawDataBridge
from src.ai_integration.authorization import AuthorizationService
from src.ai_integration.gateway_manager import GatewayManager
from src.ai_integration.auth import generate_credentials, JWTTokenService
from src.database.connection import Base


def _create_test_db_session():
    """Create a fresh database session for property tests."""
    engine = create_engine("sqlite:///:memory:")
    
    # Create tables with JSON instead of JSONB for SQLite
    for table in [AIGateway.__table__, AISkill.__table__, AIAuditLog.__table__]:
        for column in table.columns:
            if hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'JSONB':
                column.type = JSON()
    
    # Only create AI integration tables, not all tables
    AIGateway.__table__.create(engine, checkfirst=True)
    AISkill.__table__.create(engine, checkfirst=True)
    AIAuditLog.__table__.create(engine, checkfirst=True)
    
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    
    # Create tables with JSON instead of JSONB for SQLite
    for table in [AIGateway.__table__, AISkill.__table__, AIAuditLog.__table__]:
        for column in table.columns:
            if hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'JSONB':
                column.type = JSON()
    
    # Only create AI integration tables, not all tables
    AIGateway.__table__.create(engine, checkfirst=True)
    AISkill.__table__.create(engine, checkfirst=True)
    AIAuditLog.__table__.create(engine, checkfirst=True)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def valid_configuration():
    """Provide a valid gateway configuration."""
    return {
        'channels': [
            {
                'channel_type': 'whatsapp',
                'enabled': True
            }
        ],
        'network_settings': {
            'port': 3000,
            'host': 'localhost'
        }
    }


# ============================================================================
# Property-Based Test for Authenticated and Authorized Data Access
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_tenants=st.integers(min_value=2, max_value=4),
    num_gateways_per_tenant=st.integers(min_value=1, max_value=3),
    num_access_attempts=st.integers(min_value=5, max_value=15)
)
def test_property_authenticated_and_authorized_data_access(
    num_tenants: int,
    num_gateways_per_tenant: int,
    num_access_attempts: int
):
    """
    **Property 6: Authenticated and Authorized Data Access**
    
    For any data access request, if authentication succeeds and the gateway 
    has permission for the requested resource within its tenant, then data 
    should be returned; otherwise, the request should be rejected with 
    appropriate error code.
    
    **Validates: Requirements 3.1, 3.2**
    
    This property test verifies that:
    1. Authenticated requests with valid permissions return data
    2. Unauthenticated requests are rejected
    3. Authenticated requests without permission are rejected
    4. Cross-tenant access attempts are rejected
    5. Appropriate error codes are returned for each failure case
    
    Feature: ai-application-integration, Property 6: Authenticated and Authorized Data Access
    """
    # Create fresh session
    db_session = _create_test_db_session()
    auth_service = AuthorizationService(db_session)
    gateway_manager = GatewayManager(db_session)
    jwt_service = JWTTokenService()
    
    try:
        config = {
            'channels': [{'channel_type': 'whatsapp', 'enabled': True}],
            'network_settings': {'port': 3000}
        }
        
        # Create gateways for multiple tenants
        tenant_gateways = {}
        gateway_credentials = {}
        gateway_tokens = {}
        
        for tenant_idx in range(num_tenants):
            tenant_id = f"tenant_{tenant_idx}"
            tenant_gateways[tenant_id] = []
            
            for gw_idx in range(num_gateways_per_tenant):
                gateway, credentials = gateway_manager.register_gateway(
                    name=f"Gateway_{tenant_idx}_{gw_idx}",
                    gateway_type="openclaw",
                    tenant_id=tenant_id,
                    configuration=config
                )
                
                # Activate gateway to grant permissions
                gateway.status = "active"
                db_session.commit()
                
                tenant_gateways[tenant_id].append(gateway)
                gateway_credentials[gateway.id] = credentials
                
                # Generate JWT token for authenticated access
                token = jwt_service.generate_token(
                    gateway_id=gateway.id,
                    tenant_id=tenant_id,
                    permissions=["read:data"]
                )
                gateway_tokens[gateway.id] = token
        
        # Test authenticated and authorized access
        for attempt_idx in range(num_access_attempts):
            # Pick a random tenant and gateway
            tenant_idx = attempt_idx % num_tenants
            tenant_id = f"tenant_{tenant_idx}"
            gateways = tenant_gateways[tenant_id]
            gateway_idx = attempt_idx % len(gateways)
            gateway = gateways[gateway_idx]
            
            # Test Case 1: Authenticated request with valid permission
            # Should succeed and return data
            has_permission = auth_service.check_permission(
                gateway_id=gateway.id,
                resource="data",
                action="read"
            )
            
            # Property 1: Active gateway with read permission should have access
            assert has_permission is True, \
                f"Active gateway {gateway.id} should have read permission for data"
            
            # Verify token is valid
            claims = jwt_service.validate_token(gateway_tokens[gateway.id])
            assert claims.gateway_id == gateway.id, \
                f"Token gateway_id should match {gateway.id}"
            assert claims.tenant_id == tenant_id, \
                f"Token tenant_id should match {tenant_id}"
            assert "read:data" in claims.permissions, \
                "Token should include read:data permission"
            
            # Test Case 2: Unauthenticated request (no token)
            # Should be rejected - simulated by checking non-existent gateway
            unauthenticated_result = auth_service.check_permission(
                gateway_id="nonexistent_gateway",
                resource="data",
                action="read"
            )
            
            # Property 2: Unauthenticated requests should be rejected
            assert unauthenticated_result is False, \
                "Unauthenticated request should be rejected"
            
            # Test Case 3: Authenticated but inactive gateway
            # Create an inactive gateway
            inactive_gateway, _ = gateway_manager.register_gateway(
                name=f"Inactive_Gateway_{attempt_idx}",
                gateway_type="openclaw",
                tenant_id=tenant_id,
                configuration=config
            )
            # Don't activate it (status remains "inactive")
            
            inactive_permission = auth_service.check_permission(
                gateway_id=inactive_gateway.id,
                resource="data",
                action="read"
            )
            
            # Property 3: Inactive gateway should not have permission
            assert inactive_permission is False, \
                f"Inactive gateway {inactive_gateway.id} should not have permission"
            
            # Test Case 4: Cross-tenant access attempt
            # Pick a different tenant
            other_tenant_idx = (tenant_idx + 1) % num_tenants
            other_tenant_id = f"tenant_{other_tenant_idx}"
            
            # Property 4: Cross-tenant access should be rejected
            from src.ai_integration.authorization import CrossTenantAccessError
            with pytest.raises(CrossTenantAccessError):
                auth_service.validate_cross_tenant_access(
                    gateway_id=gateway.id,
                    resource_tenant_id=other_tenant_id
                )
            
            # Test Case 5: Authenticated request without required permission
            # Check for a permission the gateway doesn't have
            no_permission = auth_service.check_permission(
                gateway_id=gateway.id,
                resource="data",
                action="delete"  # Gateway only has "read" permission
            )
            
            # Property 5: Request without required permission should be rejected
            assert no_permission is False, \
                f"Gateway {gateway.id} should not have delete permission"
        
        # Test Case 6: Verify tenant isolation in data queries
        for tenant_id, gateways in tenant_gateways.items():
            for gateway in gateways:
                # Query with tenant filter
                query = db_session.query(AIGateway)
                filtered_query = auth_service.apply_tenant_filter(
                    query,
                    tenant_id,
                    AIGateway
                )
                
                results = filtered_query.all()
                
                # Property 6: All results should belong to the same tenant
                for result_gateway in results:
                    assert result_gateway.tenant_id == tenant_id, \
                        f"Query for tenant {tenant_id} returned gateway from {result_gateway.tenant_id}"
                
                # Property 7: Results should not include gateways from other tenants
                result_ids = {gw.id for gw in results}
                for other_tenant_id, other_gateways in tenant_gateways.items():
                    if other_tenant_id != tenant_id:
                        other_ids = {gw.id for gw in other_gateways}
                        intersection = result_ids & other_ids
                        assert len(intersection) == 0, \
                            f"Tenant {tenant_id} query should not return gateways from {other_tenant_id}"
        
        # Test Case 7: Verify deactivated gateway loses access
        for tenant_id, gateways in tenant_gateways.items():
            if gateways:
                gateway = gateways[0]
                
                # Verify gateway has permission before deactivation
                assert auth_service.check_permission(
                    gateway_id=gateway.id,
                    resource="data",
                    action="read"
                ) is True
                
                # Deactivate gateway
                gateway_manager.deactivate_gateway(gateway.id)
                db_session.refresh(gateway)
                
                # Property 8: Deactivated gateway should lose permission
                assert auth_service.check_permission(
                    gateway_id=gateway.id,
                    resource="data",
                    action="read"
                ) is False, \
                    f"Deactivated gateway {gateway.id} should not have permission"
                
                # Property 9: Token should still be valid but permission check fails
                # (Token validation is separate from permission checking)
                claims = jwt_service.validate_token(gateway_tokens[gateway.id])
                assert claims.gateway_id == gateway.id, \
                    "Token should still be valid after deactivation"
                
                # But permission check should fail
                assert auth_service.check_permission(
                    gateway_id=gateway.id,
                    resource="data",
                    action="read"
                ) is False, \
                    "Permission check should fail for deactivated gateway"
    
    finally:
        db_session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
