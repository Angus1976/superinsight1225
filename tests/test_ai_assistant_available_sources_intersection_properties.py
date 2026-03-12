"""
Property-based tests for AI Assistant Available Data Sources Intersection.

Tests validate that available data sources equal the intersection of enabled
sources and role-authorized sources using hypothesis for comprehensive coverage.

Feature: ai-assistant-config-redesign, Property 4: 可用数据源等于已启用与角色授权的交集
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.ai.data_source_config import AIDataSourceService, AIDataSourceConfigModel, DATA_SOURCE_REGISTRY
from src.ai.role_permission_service import RolePermissionService
from src.models.ai_data_source_role_permission import AIDataSourceRolePermission


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Create an in-memory SQLite database session for property tests.
    
    This fixture creates the necessary tables for testing data source
    configuration and role permissions.
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create tables
    AIDataSourceConfigModel.__table__.create(bind=engine, checkfirst=True)
    AIDataSourceRolePermission.__table__.create(bind=engine, checkfirst=True)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating valid role names
role_strategy = st.sampled_from([
    "admin",
    "business_expert",
    "annotator",
    "viewer"
])

# Get all available source IDs from the registry
AVAILABLE_SOURCE_IDS = [source["id"] for source in DATA_SOURCE_REGISTRY]

# Strategy for generating source IDs from the registry
source_id_strategy = st.sampled_from(AVAILABLE_SOURCE_IDS)

# Strategy for generating enabled/disabled status
enabled_strategy = st.booleans()

# Strategy for generating data source configuration
# Maps source_id -> enabled status
def data_source_config_strategy():
    """Generate a random configuration of enabled/disabled data sources."""
    return st.dictionaries(
        keys=source_id_strategy,
        values=enabled_strategy,
        min_size=0,
        max_size=len(AVAILABLE_SOURCE_IDS)
    )

# Strategy for generating role permissions
# List of (role, source_id, allowed) tuples
def role_permissions_strategy():
    """Generate random role permission mappings."""
    return st.lists(
        st.tuples(role_strategy, source_id_strategy, st.booleans()),
        min_size=0,
        max_size=30
    ).map(lambda perms: _deduplicate_role_permissions(perms))


def _deduplicate_role_permissions(permissions: list[tuple]) -> list[dict]:
    """
    Remove duplicate (role, source_id) combinations, keeping the last occurrence.
    Convert to list of dicts for service consumption.
    """
    seen = {}
    for role, source_id, allowed in permissions:
        key = (role, source_id)
        seen[key] = {"role": role, "source_id": source_id, "allowed": allowed}
    return list(seen.values())


# ============================================================================
# Property 4: Available Data Sources = Enabled ∩ Role-Authorized
# ============================================================================

class TestProperty4_AvailableSourcesIntersection:
    """
    Feature: ai-assistant-config-redesign, Property 4: 可用数据源等于已启用与角色授权的交集
    
    **Validates: Requirements 5.2, 6.3**
    
    For any user role and any data source configuration state,
    GET /data-sources/available should return exactly the intersection
    of enabled data sources and role-authorized data sources.
    """
    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=role_strategy,
        config=data_source_config_strategy(),
        permissions=role_permissions_strategy()
    )
    def test_available_sources_equals_enabled_intersect_authorized(
        self,
        db_session: Session,
        role: str,
        config: dict,
        permissions: list[dict]
    ):
        """
        Property: Available sources = Enabled sources ∩ Authorized sources.
        
        For any role and any configuration of enabled/disabled sources and
        role permissions, the available sources should be exactly those that
        are both enabled AND authorized for the role.
        """
        # Clear database
        db_session.query(AIDataSourceConfigModel).delete()
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Setup services
        ds_service = AIDataSourceService(db_session)
        perm_service = RolePermissionService(db_session)
        
        # Configure data sources (enabled/disabled)
        config_updates = []
        for source in DATA_SOURCE_REGISTRY:
            source_id = source["id"]
            enabled = config.get(source_id, True)  # Default to enabled if not specified
            config_updates.append({
                "id": source_id,
                "label": source["label"],
                "enabled": enabled,
                "access_mode": "read"
            })
        ds_service.update_config(config_updates)
        
        # Configure role permissions
        if permissions:
            perm_service.update_permissions(permissions)
        
        # Act - Get available sources for the role
        available = ds_service.get_available_sources(role)
        available_ids = {s["id"] for s in available}
        
        # Assert - Build expected intersection
        # Step 1: Get enabled source IDs
        all_config = ds_service.get_config()
        enabled_ids = {s["id"] for s in all_config if s.get("enabled")}
        
        # Step 2: Get authorized source IDs for the role
        authorized_ids = set(perm_service.get_permissions_by_role(role))
        
        # Step 3: Calculate expected intersection
        # Special case: if no permissions configured for role, fallback to all enabled
        if not authorized_ids:
            expected_ids = enabled_ids
        else:
            expected_ids = enabled_ids & authorized_ids
        
        # Assert - Available sources match expected intersection
        assert available_ids == expected_ids, (
            f"Available sources for role '{role}' do not match expected intersection.\n"
            f"Enabled sources: {enabled_ids}\n"
            f"Authorized sources: {authorized_ids}\n"
            f"Expected (intersection): {expected_ids}\n"
            f"Actual available: {available_ids}\n"
            f"Missing: {expected_ids - available_ids}\n"
            f"Extra: {available_ids - expected_ids}"
        )

    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=role_strategy,
        config=data_source_config_strategy(),
        permissions=role_permissions_strategy()
    )
    def test_disabled_sources_never_available(
        self,
        db_session: Session,
        role: str,
        config: dict,
        permissions: list[dict]
    ):
        """
        Property: Disabled sources are never available, regardless of permissions.
        
        Even if a role has permission to access a data source, if that source
        is disabled, it should not appear in the available sources list.
        """
        # Clear database
        db_session.query(AIDataSourceConfigModel).delete()
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Setup services
        ds_service = AIDataSourceService(db_session)
        perm_service = RolePermissionService(db_session)
        
        # Configure data sources
        config_updates = []
        for source in DATA_SOURCE_REGISTRY:
            source_id = source["id"]
            enabled = config.get(source_id, True)
            config_updates.append({
                "id": source_id,
                "label": source["label"],
                "enabled": enabled,
                "access_mode": "read"
            })
        ds_service.update_config(config_updates)
        
        # Configure permissions
        if permissions:
            perm_service.update_permissions(permissions)
        
        # Act - Get available sources
        available = ds_service.get_available_sources(role)
        available_ids = {s["id"] for s in available}
        
        # Assert - No disabled sources in available list
        all_config = ds_service.get_config()
        disabled_ids = {s["id"] for s in all_config if not s.get("enabled")}
        
        overlap = available_ids & disabled_ids
        assert len(overlap) == 0, (
            f"Disabled sources should never be available, but found: {overlap}"
        )

    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=role_strategy,
        config=data_source_config_strategy(),
        permissions=role_permissions_strategy()
    )
    def test_unauthorized_sources_never_available(
        self,
        db_session: Session,
        role: str,
        config: dict,
        permissions: list[dict]
    ):
        """
        Property: Unauthorized sources are never available (when permissions exist).
        
        If permissions are configured and a role is not authorized for a source,
        that source should not appear in available sources even if enabled.
        """
        # Clear database
        db_session.query(AIDataSourceConfigModel).delete()
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Setup services
        ds_service = AIDataSourceService(db_session)
        perm_service = RolePermissionService(db_session)
        
        # Configure data sources
        config_updates = []
        for source in DATA_SOURCE_REGISTRY:
            source_id = source["id"]
            enabled = config.get(source_id, True)
            config_updates.append({
                "id": source_id,
                "label": source["label"],
                "enabled": enabled,
                "access_mode": "read"
            })
        ds_service.update_config(config_updates)
        
        # Configure permissions
        if permissions:
            perm_service.update_permissions(permissions)
        
        # Act - Get available sources
        available = ds_service.get_available_sources(role)
        available_ids = {s["id"] for s in available}
        
        # Assert - Check unauthorized sources
        authorized_ids = set(perm_service.get_permissions_by_role(role))
        
        # Only check if permissions are configured for this role
        if authorized_ids:
            # All available sources must be in authorized list
            unauthorized_in_available = available_ids - authorized_ids
            assert len(unauthorized_in_available) == 0, (
                f"Unauthorized sources should not be available when permissions exist, "
                f"but found: {unauthorized_in_available}"
            )

    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=role_strategy,
        permissions=role_permissions_strategy()
    )
    def test_all_enabled_when_no_permissions_configured(
        self,
        db_session: Session,
        role: str,
        permissions: list[dict]
    ):
        """
        Property: All enabled sources available when no permissions configured for role.
        
        If no permissions are configured for a specific role (fallback behavior),
        all enabled sources should be available to that role.
        """
        # Clear database
        db_session.query(AIDataSourceConfigModel).delete()
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Setup services
        ds_service = AIDataSourceService(db_session)
        perm_service = RolePermissionService(db_session)
        
        # Enable all sources
        config_updates = []
        for source in DATA_SOURCE_REGISTRY:
            config_updates.append({
                "id": source["id"],
                "label": source["label"],
                "enabled": True,
                "access_mode": "read"
            })
        ds_service.update_config(config_updates)
        
        # Configure permissions for OTHER roles only (not the target role)
        filtered_permissions = [p for p in permissions if p["role"] != role]
        if filtered_permissions:
            perm_service.update_permissions(filtered_permissions)
        
        # Act - Get available sources for role with no permissions
        available = ds_service.get_available_sources(role)
        available_ids = {s["id"] for s in available}
        
        # Assert - Should get all enabled sources (fallback behavior)
        all_config = ds_service.get_config()
        enabled_ids = {s["id"] for s in all_config if s.get("enabled")}
        
        # Verify no permissions configured for this role
        authorized_ids = set(perm_service.get_permissions_by_role(role))
        assert len(authorized_ids) == 0, "Test setup error: role should have no permissions"
        
        # All enabled sources should be available
        assert available_ids == enabled_ids, (
            f"When no permissions configured for role '{role}', "
            f"all enabled sources should be available.\n"
            f"Expected: {enabled_ids}\n"
            f"Actual: {available_ids}"
        )

    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=role_strategy,
        config=data_source_config_strategy(),
        permissions=role_permissions_strategy()
    )
    def test_intersection_is_subset_of_enabled(
        self,
        db_session: Session,
        role: str,
        config: dict,
        permissions: list[dict]
    ):
        """
        Property: Available sources are always a subset of enabled sources.
        
        The intersection of enabled and authorized sources must be a subset
        of the enabled sources.
        """
        # Clear database
        db_session.query(AIDataSourceConfigModel).delete()
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Setup services
        ds_service = AIDataSourceService(db_session)
        perm_service = RolePermissionService(db_session)
        
        # Configure data sources
        config_updates = []
        for source in DATA_SOURCE_REGISTRY:
            source_id = source["id"]
            enabled = config.get(source_id, True)
            config_updates.append({
                "id": source_id,
                "label": source["label"],
                "enabled": enabled,
                "access_mode": "read"
            })
        ds_service.update_config(config_updates)
        
        # Configure permissions
        if permissions:
            perm_service.update_permissions(permissions)
        
        # Act - Get available sources
        available = ds_service.get_available_sources(role)
        available_ids = {s["id"] for s in available}
        
        # Assert - Available is subset of enabled
        all_config = ds_service.get_config()
        enabled_ids = {s["id"] for s in all_config if s.get("enabled")}
        
        assert available_ids.issubset(enabled_ids), (
            f"Available sources must be a subset of enabled sources.\n"
            f"Enabled: {enabled_ids}\n"
            f"Available: {available_ids}\n"
            f"Not enabled but available: {available_ids - enabled_ids}"
        )

    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=role_strategy,
        config=data_source_config_strategy(),
        permissions=role_permissions_strategy()
    )
    def test_intersection_is_subset_of_authorized(
        self,
        db_session: Session,
        role: str,
        config: dict,
        permissions: list[dict]
    ):
        """
        Property: Available sources are subset of authorized (when permissions exist).
        
        When permissions are configured for a role, available sources must be
        a subset of the authorized sources.
        """
        # Clear database
        db_session.query(AIDataSourceConfigModel).delete()
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Setup services
        ds_service = AIDataSourceService(db_session)
        perm_service = RolePermissionService(db_session)
        
        # Configure data sources
        config_updates = []
        for source in DATA_SOURCE_REGISTRY:
            source_id = source["id"]
            enabled = config.get(source_id, True)
            config_updates.append({
                "id": source_id,
                "label": source["label"],
                "enabled": enabled,
                "access_mode": "read"
            })
        ds_service.update_config(config_updates)
        
        # Configure permissions
        if permissions:
            perm_service.update_permissions(permissions)
        
        # Act - Get available sources
        available = ds_service.get_available_sources(role)
        available_ids = {s["id"] for s in available}
        
        # Assert - Available is subset of authorized (if permissions configured)
        authorized_ids = set(perm_service.get_permissions_by_role(role))
        
        if authorized_ids:  # Only check if permissions are configured
            assert available_ids.issubset(authorized_ids), (
                f"Available sources must be a subset of authorized sources "
                f"when permissions are configured.\n"
                f"Authorized: {authorized_ids}\n"
                f"Available: {available_ids}\n"
                f"Not authorized but available: {available_ids - authorized_ids}"
            )

    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role1=role_strategy,
        role2=role_strategy,
        config=data_source_config_strategy(),
        permissions=role_permissions_strategy()
    )
    def test_different_roles_get_different_sources(
        self,
        db_session: Session,
        role1: str,
        role2: str,
        config: dict,
        permissions: list[dict]
    ):
        """
        Property: Different roles may get different available sources.
        
        When permissions differ between roles, their available sources
        should reflect their respective permissions.
        """
        # Skip if roles are the same
        if role1 == role2:
            return
        
        # Clear database
        db_session.query(AIDataSourceConfigModel).delete()
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Setup services
        ds_service = AIDataSourceService(db_session)
        perm_service = RolePermissionService(db_session)
        
        # Configure data sources
        config_updates = []
        for source in DATA_SOURCE_REGISTRY:
            source_id = source["id"]
            enabled = config.get(source_id, True)
            config_updates.append({
                "id": source_id,
                "label": source["label"],
                "enabled": enabled,
                "access_mode": "read"
            })
        ds_service.update_config(config_updates)
        
        # Configure permissions
        if permissions:
            perm_service.update_permissions(permissions)
        
        # Act - Get available sources for both roles
        available1 = ds_service.get_available_sources(role1)
        available1_ids = {s["id"] for s in available1}
        
        available2 = ds_service.get_available_sources(role2)
        available2_ids = {s["id"] for s in available2}
        
        # Assert - Each role gets correct intersection
        all_config = ds_service.get_config()
        enabled_ids = {s["id"] for s in all_config if s.get("enabled")}
        
        auth1_ids = set(perm_service.get_permissions_by_role(role1))
        auth2_ids = set(perm_service.get_permissions_by_role(role2))
        
        # Calculate expected for each role
        expected1 = enabled_ids if not auth1_ids else (enabled_ids & auth1_ids)
        expected2 = enabled_ids if not auth2_ids else (enabled_ids & auth2_ids)
        
        assert available1_ids == expected1, (
            f"Role '{role1}' available sources incorrect"
        )
        assert available2_ids == expected2, (
            f"Role '{role2}' available sources incorrect"
        )

    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=role_strategy,
        config=data_source_config_strategy(),
        permissions=role_permissions_strategy()
    )
    def test_available_sources_have_valid_structure(
        self,
        db_session: Session,
        role: str,
        config: dict,
        permissions: list[dict]
    ):
        """
        Property: Available sources have valid structure with required fields.
        
        Each available source should be a dict with id, label, description,
        enabled, and access_mode fields.
        """
        # Clear database
        db_session.query(AIDataSourceConfigModel).delete()
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Setup services
        ds_service = AIDataSourceService(db_session)
        perm_service = RolePermissionService(db_session)
        
        # Configure data sources
        config_updates = []
        for source in DATA_SOURCE_REGISTRY:
            source_id = source["id"]
            enabled = config.get(source_id, True)
            config_updates.append({
                "id": source_id,
                "label": source["label"],
                "enabled": enabled,
                "access_mode": "read"
            })
        ds_service.update_config(config_updates)
        
        # Configure permissions
        if permissions:
            perm_service.update_permissions(permissions)
        
        # Act - Get available sources
        available = ds_service.get_available_sources(role)
        
        # Assert - Each source has valid structure
        required_fields = ["id", "label", "enabled"]
        for source in available:
            assert isinstance(source, dict), f"Source should be dict, got {type(source)}"
            
            for field in required_fields:
                assert field in source, f"Source missing required field '{field}': {source}"
            
            assert isinstance(source["id"], str), "Source id should be string"
            assert isinstance(source["label"], str), "Source label should be string"
            assert isinstance(source["enabled"], bool), "Source enabled should be boolean"
            assert source["enabled"] is True, "Available sources should all be enabled"
