"""
Property-based tests for AI Assistant Role Permission Mapping Persistence.

Tests validate role-permission mapping round-trip consistency using hypothesis
for comprehensive coverage.

Feature: ai-assistant-config-redesign
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.ai.role_permission_service import RolePermissionService
from src.models.ai_data_source_role_permission import AIDataSourceRolePermission


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Create an in-memory SQLite database session for property tests.
    
    This fixture creates only the ai_data_source_role_permission table
    needed for testing role permission service.
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create the role permission table
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

# Strategy for generating data source IDs
source_id_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="_-"
    ),
    min_size=3,
    max_size=50
).filter(lambda s: s and not s.startswith("-") and not s.startswith("_"))

# Strategy for generating allowed boolean values
allowed_strategy = st.booleans()

# Strategy for generating a single permission mapping
permission_mapping_strategy = st.builds(
    dict,
    role=role_strategy,
    source_id=source_id_strategy,
    allowed=allowed_strategy
)

# Strategy for generating a list of unique permission mappings
# Ensures no duplicate (role, source_id) combinations
def unique_permissions_strategy(min_size=1, max_size=20):
    """Generate a list of unique permission mappings."""
    return st.lists(
        permission_mapping_strategy,
        min_size=min_size,
        max_size=max_size
    ).map(lambda perms: _deduplicate_permissions(perms))


def _deduplicate_permissions(permissions: list[dict]) -> list[dict]:
    """
    Remove duplicate (role, source_id) combinations, keeping the last occurrence.
    
    This ensures the permission list respects the unique constraint on (role, source_id).
    """
    seen = {}
    for perm in permissions:
        key = (perm["role"], perm["source_id"])
        seen[key] = perm
    return list(seen.values())


# ============================================================================
# Property 3: Role Permission Mapping Persistence Round-Trip
# ============================================================================

class TestProperty3_RolePermissionRoundTrip:
    """
    Feature: ai-assistant-config-redesign, Property 3: 角色权限映射持久化往返
    
    **Validates: Requirements 4.4**
    
    For any valid role-permission mapping configuration, saving via POST
    and then reading via GET should return the same permission mapping.
    """
    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(permissions=unique_permissions_strategy(min_size=1, max_size=20))
    def test_save_and_get_returns_same_permissions(
        self,
        db_session: Session,
        permissions: list[dict]
    ):
        """
        Property: Saving permissions and then retrieving them returns identical data.
        
        For any valid list of permission mappings, the round-trip operation
        (save → get) should preserve all permission data exactly.
        """
        # Clear any existing data from previous hypothesis examples
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Create service
        service = RolePermissionService(db_session)
        
        # Act - Save permissions
        service.update_permissions(permissions)
        
        # Retrieve all permissions
        retrieved = service.get_all_permissions()
        
        # Assert - Retrieved permissions match saved permissions
        # Convert both to sets of tuples for comparison (order-independent)
        expected_set = {
            (p["role"], p["source_id"], p["allowed"])
            for p in permissions
        }
        retrieved_set = {
            (p["role"], p["source_id"], p["allowed"])
            for p in retrieved
        }
        
        assert retrieved_set == expected_set, (
            f"Retrieved permissions do not match saved permissions.\n"
            f"Expected: {expected_set}\n"
            f"Retrieved: {retrieved_set}\n"
            f"Missing: {expected_set - retrieved_set}\n"
            f"Extra: {retrieved_set - expected_set}"
        )
    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        initial_permissions=unique_permissions_strategy(min_size=1, max_size=15),
        updated_permissions=unique_permissions_strategy(min_size=1, max_size=15)
    )
    def test_update_overwrites_existing_permissions(
        self,
        db_session: Session,
        initial_permissions: list[dict],
        updated_permissions: list[dict]
    ):
        """
        Property: Updating permissions overwrites existing values correctly.
        
        When permissions are saved twice, the second save should update
        existing entries and add new ones, with the final state matching
        the combined result.
        """
        # Clear any existing data from previous hypothesis examples
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Create service
        service = RolePermissionService(db_session)
        
        # Act - Save initial permissions
        service.update_permissions(initial_permissions)
        
        # Save updated permissions (may overlap with initial)
        service.update_permissions(updated_permissions)
        
        # Retrieve all permissions
        retrieved = service.get_all_permissions()
        
        # Assert - Build expected final state
        # Start with initial permissions
        expected_map = {
            (p["role"], p["source_id"]): p["allowed"]
            for p in initial_permissions
        }
        # Update with new permissions (overwrites existing)
        for p in updated_permissions:
            expected_map[(p["role"], p["source_id"])] = p["allowed"]
        
        # Convert retrieved to same format
        retrieved_map = {
            (p["role"], p["source_id"]): p["allowed"]
            for p in retrieved
        }
        
        assert retrieved_map == expected_map, (
            f"Retrieved permissions do not match expected state after update.\n"
            f"Expected: {expected_map}\n"
            f"Retrieved: {retrieved_map}"
        )
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        role=role_strategy,
        permissions=unique_permissions_strategy(min_size=5, max_size=20)
    )
    def test_get_permissions_by_role_filters_correctly(
        self,
        db_session: Session,
        role: str,
        permissions: list[dict]
    ):
        """
        Property: Getting permissions by role returns only allowed sources for that role.
        
        After saving permissions, querying by a specific role should return
        only the source_ids where that role has allowed=True.
        """
        # Clear any existing data from previous hypothesis examples
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Create service
        service = RolePermissionService(db_session)
        
        # Act - Save permissions
        service.update_permissions(permissions)
        
        # Get permissions for specific role
        allowed_sources = service.get_permissions_by_role(role)
        
        # Assert - Build expected list of allowed sources for this role
        expected_sources = {
            p["source_id"]
            for p in permissions
            if p["role"] == role and p["allowed"]
        }
        
        retrieved_sources = set(allowed_sources)
        
        assert retrieved_sources == expected_sources, (
            f"Retrieved sources for role '{role}' do not match expected.\n"
            f"Expected: {expected_sources}\n"
            f"Retrieved: {retrieved_sources}\n"
            f"Missing: {expected_sources - retrieved_sources}\n"
            f"Extra: {retrieved_sources - expected_sources}"
        )
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(permissions=unique_permissions_strategy(min_size=1, max_size=20))
    def test_permission_count_matches_unique_combinations(
        self,
        db_session: Session,
        permissions: list[dict]
    ):
        """
        Property: Number of stored permissions equals number of unique (role, source_id) pairs.
        
        The database should store exactly one entry per unique (role, source_id)
        combination, enforced by the unique constraint.
        """
        # Clear any existing data from previous hypothesis examples
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Create service
        service = RolePermissionService(db_session)
        
        # Act - Save permissions
        service.update_permissions(permissions)
        
        # Count unique (role, source_id) combinations in input
        unique_combinations = {
            (p["role"], p["source_id"])
            for p in permissions
        }
        expected_count = len(unique_combinations)
        
        # Count stored permissions
        retrieved = service.get_all_permissions()
        actual_count = len(retrieved)
        
        # Assert - Counts match
        assert actual_count == expected_count, (
            f"Number of stored permissions ({actual_count}) does not match "
            f"number of unique combinations ({expected_count})"
        )
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        permissions=unique_permissions_strategy(min_size=1, max_size=20),
        role=role_strategy
    )
    def test_empty_result_when_role_has_no_allowed_permissions(
        self,
        db_session: Session,
        permissions: list[dict],
        role: str
    ):
        """
        Property: Querying a role with no allowed permissions returns empty list.
        
        If a role has no permissions with allowed=True, or has no permissions at all,
        get_permissions_by_role should return an empty list.
        """
        # Clear any existing data from previous hypothesis examples
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Create service and modify permissions to ensure role has no allowed access
        service = RolePermissionService(db_session)
        
        # Set all permissions for the target role to allowed=False
        modified_permissions = []
        for p in permissions:
            if p["role"] == role:
                modified_permissions.append({
                    "role": p["role"],
                    "source_id": p["source_id"],
                    "allowed": False
                })
            else:
                modified_permissions.append(p)
        
        # Act - Save modified permissions
        service.update_permissions(modified_permissions)
        
        # Get permissions for role
        allowed_sources = service.get_permissions_by_role(role)
        
        # Assert - Should be empty
        assert len(allowed_sources) == 0, (
            f"Expected empty list for role '{role}' with no allowed permissions, "
            f"but got: {allowed_sources}"
        )
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        permissions=unique_permissions_strategy(min_size=10, max_size=20)
    )
    def test_all_roles_can_be_queried_independently(
        self,
        db_session: Session,
        permissions: list[dict]
    ):
        """
        Property: Each role's permissions can be queried independently without interference.
        
        After saving permissions for multiple roles, querying each role should
        return only its own allowed sources, with no cross-contamination.
        """
        # Clear any existing data from previous hypothesis examples
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Create service
        service = RolePermissionService(db_session)
        
        # Act - Save permissions
        service.update_permissions(permissions)
        
        # Build expected results for each role
        all_roles = ["admin", "business_expert", "annotator", "viewer"]
        expected_by_role = {}
        for role in all_roles:
            expected_by_role[role] = {
                p["source_id"]
                for p in permissions
                if p["role"] == role and p["allowed"]
            }
        
        # Query each role and verify
        for role in all_roles:
            allowed_sources = service.get_permissions_by_role(role)
            retrieved_sources = set(allowed_sources)
            expected_sources = expected_by_role[role]
            
            assert retrieved_sources == expected_sources, (
                f"Role '{role}' permissions do not match expected.\n"
                f"Expected: {expected_sources}\n"
                f"Retrieved: {retrieved_sources}"
            )
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        permissions=unique_permissions_strategy(min_size=1, max_size=20)
    )
    def test_permission_data_types_preserved(
        self,
        db_session: Session,
        permissions: list[dict]
    ):
        """
        Property: Data types of permission fields are preserved through round-trip.
        
        Role and source_id should remain strings, and allowed should remain boolean.
        """
        # Clear any existing data from previous hypothesis examples
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Create service
        service = RolePermissionService(db_session)
        
        # Act - Save and retrieve
        service.update_permissions(permissions)
        retrieved = service.get_all_permissions()
        
        # Assert - Check data types
        for perm in retrieved:
            assert isinstance(perm["role"], str), (
                f"Role should be string, got {type(perm['role'])}"
            )
            assert isinstance(perm["source_id"], str), (
                f"Source ID should be string, got {type(perm['source_id'])}"
            )
            assert isinstance(perm["allowed"], bool), (
                f"Allowed should be boolean, got {type(perm['allowed'])}"
            )
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        permissions=unique_permissions_strategy(min_size=1, max_size=20)
    )
    def test_idempotent_save_operation(
        self,
        db_session: Session,
        permissions: list[dict]
    ):
        """
        Property: Saving the same permissions multiple times produces the same result.
        
        The save operation should be idempotent - saving identical permissions
        twice should result in the same final state as saving once.
        """
        # Clear any existing data from previous hypothesis examples
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        # Arrange - Create service
        service = RolePermissionService(db_session)
        
        # Act - Save permissions twice
        service.update_permissions(permissions)
        service.update_permissions(permissions)
        
        # Retrieve permissions
        retrieved = service.get_all_permissions()
        
        # Assert - Result matches original permissions
        expected_set = {
            (p["role"], p["source_id"], p["allowed"])
            for p in permissions
        }
        retrieved_set = {
            (p["role"], p["source_id"], p["allowed"])
            for p in retrieved
        }
        
        assert retrieved_set == expected_set, (
            f"Idempotent save failed - retrieved permissions differ from expected.\n"
            f"Expected: {expected_set}\n"
            f"Retrieved: {retrieved_set}"
        )
