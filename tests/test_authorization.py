"""
Tests for AuthorizationService class.

Tests permission checking, tenant filtering, and cross-tenant access validation
using both unit tests and property-based tests.
"""

import pytest
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker, Session
from hypothesis import given, strategies as st, settings, HealthCheck

from src.models.ai_integration import AIGateway, AISkill
from src.ai_integration.authorization import (
    AuthorizationService,
    PermissionDeniedError,
    CrossTenantAccessError
)
from src.ai_integration.gateway_manager import GatewayManager
from src.database.connection import Base


def _create_test_db_session():
    """Create a fresh database session for property tests."""
    engine = create_engine("sqlite:///:memory:")
    
    # Create tables with JSON instead of JSONB for SQLite
    from src.models.ai_integration import AIGateway, AISkill, AIAuditLog
    for table in [AIGateway.__table__, AISkill.__table__, AIAuditLog.__table__]:
        for column in table.columns:
            if hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'JSONB':
                column.type = JSON()
    
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    
    # Create tables with JSON instead of JSONB for SQLite
    from src.models.ai_integration import AIGateway, AISkill, AIAuditLog
    for table in [AIGateway.__table__, AISkill.__table__, AIAuditLog.__table__]:
        for column in table.columns:
            if hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'JSONB':
                column.type = JSON()
    
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def auth_service(db_session):
    """Create an AuthorizationService instance for testing."""
    return AuthorizationService(db_session)


@pytest.fixture
def gateway_manager(db_session):
    """Create a GatewayManager instance for testing."""
    return GatewayManager(db_session)


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
# Unit Tests
# ============================================================================

class TestPermissionChecking:
    """Test permission checking functionality."""
    
    def test_check_permission_gateway_not_found(self, auth_service):
        """Test permission check fails for non-existent gateway."""
        result = auth_service.check_permission(
            gateway_id="nonexistent",
            resource="data",
            action="read"
        )
        assert result is False
    
    def test_check_permission_inactive_gateway(
        self,
        auth_service,
        gateway_manager,
        valid_configuration
    ):
        """Test permission check fails for inactive gateway."""
        # Register gateway (starts as inactive)
        gateway, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        result = auth_service.check_permission(
            gateway_id=gateway.id,
            resource="data",
            action="read"
        )
        assert result is False
    
    def test_check_permission_active_gateway(
        self,
        auth_service,
        gateway_manager,
        valid_configuration,
        db_session
    ):
        """Test permission check succeeds for active gateway."""
        # Register and activate gateway
        gateway, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        gateway.status = "active"
        db_session.commit()
        
        result = auth_service.check_permission(
            gateway_id=gateway.id,
            resource="data",
            action="read"
        )
        assert result is True


class TestTenantFiltering:
    """Test tenant filtering functionality."""
    
    def test_apply_tenant_filter(
        self,
        auth_service,
        gateway_manager,
        valid_configuration,
        db_session
    ):
        """Test tenant filter is applied correctly."""
        # Create gateways for different tenants
        gw1, _ = gateway_manager.register_gateway(
            name="Gateway 1",
            gateway_type="openclaw",
            tenant_id="tenant_1",
            configuration=valid_configuration
        )
        
        gw2, _ = gateway_manager.register_gateway(
            name="Gateway 2",
            gateway_type="openclaw",
            tenant_id="tenant_2",
            configuration=valid_configuration
        )
        
        # Query with tenant filter
        query = db_session.query(AIGateway)
        filtered_query = auth_service.apply_tenant_filter(
            query,
            "tenant_1",
            AIGateway
        )
        
        results = filtered_query.all()
        
        # Should only return tenant_1 gateway
        assert len(results) == 1
        assert results[0].id == gw1.id
        assert results[0].tenant_id == "tenant_1"
    
    def test_apply_tenant_filter_invalid_model(self, auth_service, db_session):
        """Test tenant filter raises error for model without tenant_id."""
        class InvalidModel:
            pass
        
        query = db_session.query(AIGateway)
        
        with pytest.raises(ValueError, match="does not have tenant_id"):
            auth_service.apply_tenant_filter(query, "tenant_1", InvalidModel)


class TestCrossTenantAccess:
    """Test cross-tenant access validation."""
    
    def test_validate_cross_tenant_access_same_tenant(
        self,
        auth_service,
        gateway_manager,
        valid_configuration
    ):
        """Test validation succeeds for same tenant."""
        gateway, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        # Should not raise exception
        auth_service.validate_cross_tenant_access(
            gateway_id=gateway.id,
            resource_tenant_id="tenant_123"
        )
    
    def test_validate_cross_tenant_access_different_tenant(
        self,
        auth_service,
        gateway_manager,
        valid_configuration
    ):
        """Test validation fails for different tenant."""
        gateway, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        with pytest.raises(CrossTenantAccessError, match="attempted to access"):
            auth_service.validate_cross_tenant_access(
                gateway_id=gateway.id,
                resource_tenant_id="tenant_456"
            )
    
    def test_validate_cross_tenant_access_gateway_not_found(self, auth_service):
        """Test validation fails for non-existent gateway."""
        with pytest.raises(PermissionDeniedError, match="not found"):
            auth_service.validate_cross_tenant_access(
                gateway_id="nonexistent",
                resource_tenant_id="tenant_123"
            )


# ============================================================================
# Property-Based Tests
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_tenants=st.integers(min_value=2, max_value=5),
    gateways_per_tenant=st.integers(min_value=1, max_value=3)
)
def test_property_multi_tenant_data_isolation(
    num_tenants: int,
    gateways_per_tenant: int
):
    """
    **Property 12: Multi-Tenant Data Isolation**
    
    For any data access request from a gateway, all returned data should 
    belong exclusively to the gateway's assigned tenant, with no cross-tenant 
    data leakage.
    
    **Validates: Requirements 4.2, 4.4**
    
    This property test verifies that:
    1. Queries filtered by tenant only return data from that tenant
    2. No data from other tenants is included in results
    3. Tenant isolation holds across multiple tenants
    4. Tenant isolation holds for any number of gateways per tenant
    5. Empty results when no data exists for tenant
    
    Feature: ai-application-integration, Property 12: Multi-Tenant Data Isolation
    """
    # Create fresh session
    db_session = _create_test_db_session()
    auth_service = AuthorizationService(db_session)
    gateway_manager = GatewayManager(db_session)
    
    try:
        config = {
            'channels': [{'channel_type': 'whatsapp', 'enabled': True}],
            'network_settings': {'port': 3000}
        }
        
        # Create gateways for multiple tenants
        tenant_gateways = {}
        for tenant_idx in range(num_tenants):
            tenant_id = f"tenant_{tenant_idx}"
            tenant_gateways[tenant_id] = []
            
            for gw_idx in range(gateways_per_tenant):
                gateway, _ = gateway_manager.register_gateway(
                    name=f"Gateway_{tenant_idx}_{gw_idx}",
                    gateway_type="openclaw",
                    tenant_id=tenant_id,
                    configuration=config
                )
                tenant_gateways[tenant_id].append(gateway)
        
        # Test isolation for each tenant
        for tenant_id, expected_gateways in tenant_gateways.items():
            # Query with tenant filter
            query = db_session.query(AIGateway)
            filtered_query = auth_service.apply_tenant_filter(
                query,
                tenant_id,
                AIGateway
            )
            
            results = filtered_query.all()
            
            # Property 1: Number of results should match expected
            assert len(results) == len(expected_gateways), \
                f"Expected {len(expected_gateways)} gateways for {tenant_id}, got {len(results)}"
            
            # Property 2: All results should belong to the tenant
            for gateway in results:
                assert gateway.tenant_id == tenant_id, \
                    f"Gateway {gateway.id} has tenant {gateway.tenant_id}, expected {tenant_id}"
            
            # Property 3: All expected gateways should be in results
            result_ids = {gw.id for gw in results}
            expected_ids = {gw.id for gw in expected_gateways}
            assert result_ids == expected_ids, \
                f"Result IDs {result_ids} don't match expected {expected_ids}"
            
            # Property 4: No gateways from other tenants should be in results
            for other_tenant_id, other_gateways in tenant_gateways.items():
                if other_tenant_id != tenant_id:
                    other_ids = {gw.id for gw in other_gateways}
                    intersection = result_ids & other_ids
                    assert len(intersection) == 0, \
                        f"Found {len(intersection)} gateways from {other_tenant_id} in {tenant_id} results"
        
        # Property 5: Query for non-existent tenant returns empty
        query = db_session.query(AIGateway)
        filtered_query = auth_service.apply_tenant_filter(
            query,
            "nonexistent_tenant",
            AIGateway
        )
        results = filtered_query.all()
        assert len(results) == 0, "Query for non-existent tenant should return empty"
    
    finally:
        db_session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_tenants=st.integers(min_value=2, max_value=5),
    num_attempts=st.integers(min_value=1, max_value=10)
)
def test_property_cross_tenant_access_rejection(
    num_tenants: int,
    num_attempts: int
):
    """
    **Property 13: Cross-Tenant Access Rejection**
    
    For any attempt to access data from a different tenant, the request should 
    be rejected with a security error, and a security event should be logged 
    in the Audit_Log.
    
    **Validates: Requirements 4.3**
    
    This property test verifies that:
    1. Cross-tenant access attempts are detected
    2. CrossTenantAccessError is raised for different tenants
    3. Same-tenant access is allowed
    4. Rejection works for any combination of tenants
    5. All cross-tenant attempts are rejected consistently
    
    Feature: ai-application-integration, Property 13: Cross-Tenant Access Rejection
    """
    # Create fresh session
    db_session = _create_test_db_session()
    auth_service = AuthorizationService(db_session)
    gateway_manager = GatewayManager(db_session)
    
    try:
        config = {
            'channels': [{'channel_type': 'whatsapp', 'enabled': True}],
            'network_settings': {'port': 3000}
        }
        
        # Create gateways for multiple tenants
        gateways = []
        for tenant_idx in range(num_tenants):
            tenant_id = f"tenant_{tenant_idx}"
            gateway, _ = gateway_manager.register_gateway(
                name=f"Gateway_{tenant_idx}",
                gateway_type="openclaw",
                tenant_id=tenant_id,
                configuration=config
            )
            gateways.append((gateway, tenant_id))
        
        # Test cross-tenant access rejection
        for attempt_idx in range(num_attempts):
            # Pick a gateway and a different tenant
            gateway_idx = attempt_idx % len(gateways)
            target_tenant_idx = (attempt_idx + 1) % len(gateways)
            
            gateway, gateway_tenant = gateways[gateway_idx]
            _, target_tenant = gateways[target_tenant_idx]
            
            if gateway_tenant == target_tenant:
                # Property 1: Same-tenant access should succeed
                try:
                    auth_service.validate_cross_tenant_access(
                        gateway_id=gateway.id,
                        resource_tenant_id=target_tenant
                    )
                    # Should not raise exception
                except CrossTenantAccessError:
                    pytest.fail(
                        f"Same-tenant access should not raise CrossTenantAccessError: "
                        f"gateway {gateway.id} tenant {gateway_tenant} accessing {target_tenant}"
                    )
            else:
                # Property 2: Cross-tenant access should be rejected
                with pytest.raises(CrossTenantAccessError) as exc_info:
                    auth_service.validate_cross_tenant_access(
                        gateway_id=gateway.id,
                        resource_tenant_id=target_tenant
                    )
                
                # Property 3: Error message should contain relevant information
                error_msg = str(exc_info.value)
                assert gateway.id in error_msg, \
                    f"Error message should contain gateway ID {gateway.id}"
                assert gateway_tenant in error_msg, \
                    f"Error message should contain gateway tenant {gateway_tenant}"
                assert target_tenant in error_msg, \
                    f"Error message should contain target tenant {target_tenant}"
        
        # Property 4: Test all possible cross-tenant combinations
        for i, (gw1, tenant1) in enumerate(gateways):
            for j, (gw2, tenant2) in enumerate(gateways):
                if i != j:
                    # Different tenants should be rejected
                    with pytest.raises(CrossTenantAccessError):
                        auth_service.validate_cross_tenant_access(
                            gateway_id=gw1.id,
                            resource_tenant_id=tenant2
                        )
                else:
                    # Same tenant should succeed
                    auth_service.validate_cross_tenant_access(
                        gateway_id=gw1.id,
                        resource_tenant_id=tenant2
                    )
        
        # Property 5: Non-existent gateway should raise PermissionDeniedError
        with pytest.raises(PermissionDeniedError):
            auth_service.validate_cross_tenant_access(
                gateway_id="nonexistent_gateway",
                resource_tenant_id="tenant_0"
            )
    
    finally:
        db_session.close()
