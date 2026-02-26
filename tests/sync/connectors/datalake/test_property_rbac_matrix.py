"""
Property-based tests for RBAC Permission Matrix.

Tests Property 11: RBAC permission matrix
**Validates: Requirements 7.1, 7.2, 7.3, 7.4**

For any combination of user role (ADMIN, TECHNICAL_EXPERT, BUSINESS_EXPERT,
VIEWER) and API endpoint, access should be granted if and only if the role
has the required permission level. Unauthorized access should return 403.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

import pytest
from hypothesis import given, settings, strategies as st

from src.sync.gateway.auth import (
    AuthMethod,
    AuthToken,
    Permission,
    PermissionLevel,
    ResourceType,
)


# ============================================================================
# Role Definitions — each role maps to a fixed set of permissions
# ============================================================================

@dataclass(frozen=True)
class RoleDef:
    """Immutable role definition with its granted permissions."""
    name: str
    permissions: tuple  # tuple of (ResourceType, PermissionLevel)


ADMIN = RoleDef(
    name="ADMIN",
    permissions=(
        (ResourceType.DATALAKE_SOURCE, PermissionLevel.WRITE),
        (ResourceType.DATALAKE_DASHBOARD, PermissionLevel.READ),
    ),
)

TECHNICAL_EXPERT = RoleDef(
    name="TECHNICAL_EXPERT",
    permissions=(
        (ResourceType.DATALAKE_SOURCE, PermissionLevel.WRITE),
        (ResourceType.DATALAKE_DASHBOARD, PermissionLevel.READ),
    ),
)

BUSINESS_EXPERT = RoleDef(
    name="BUSINESS_EXPERT",
    permissions=(
        (ResourceType.DATALAKE_SOURCE, PermissionLevel.READ),
        (ResourceType.DATALAKE_DASHBOARD, PermissionLevel.READ),
    ),
)

VIEWER = RoleDef(
    name="VIEWER",
    permissions=(
        (ResourceType.DATALAKE_DASHBOARD, PermissionLevel.READ),
    ),
)

ALL_ROLES = [ADMIN, TECHNICAL_EXPERT, BUSINESS_EXPERT, VIEWER]


# ============================================================================
# Endpoint permission requirements (mirrors router auth dependencies)
# ============================================================================

@dataclass(frozen=True)
class EndpointDef:
    """An API endpoint with its required permission."""
    name: str
    resource_type: ResourceType
    level: PermissionLevel


# WRITE on DATALAKE_SOURCE — create, update, delete, test connection
WRITE_ENDPOINTS = [
    EndpointDef("POST /sources", ResourceType.DATALAKE_SOURCE, PermissionLevel.WRITE),
    EndpointDef("PUT /sources/{id}", ResourceType.DATALAKE_SOURCE, PermissionLevel.WRITE),
    EndpointDef("DELETE /sources/{id}", ResourceType.DATALAKE_SOURCE, PermissionLevel.WRITE),
    EndpointDef("POST /sources/{id}/test", ResourceType.DATALAKE_SOURCE, PermissionLevel.WRITE),
]

# READ on DATALAKE_SOURCE — list, get, databases, tables, schema, preview
READ_SOURCE_ENDPOINTS = [
    EndpointDef("GET /sources", ResourceType.DATALAKE_SOURCE, PermissionLevel.READ),
    EndpointDef("GET /sources/{id}", ResourceType.DATALAKE_SOURCE, PermissionLevel.READ),
    EndpointDef("GET /sources/{id}/databases", ResourceType.DATALAKE_SOURCE, PermissionLevel.READ),
    EndpointDef("GET /sources/{id}/tables", ResourceType.DATALAKE_SOURCE, PermissionLevel.READ),
    EndpointDef("GET /sources/{id}/schema", ResourceType.DATALAKE_SOURCE, PermissionLevel.READ),
    EndpointDef("GET /sources/{id}/preview", ResourceType.DATALAKE_SOURCE, PermissionLevel.READ),
]

# READ on DATALAKE_DASHBOARD — all dashboard endpoints
DASHBOARD_ENDPOINTS = [
    EndpointDef("GET /dashboard/overview", ResourceType.DATALAKE_DASHBOARD, PermissionLevel.READ),
    EndpointDef("GET /dashboard/health", ResourceType.DATALAKE_DASHBOARD, PermissionLevel.READ),
    EndpointDef("GET /dashboard/volume-trends", ResourceType.DATALAKE_DASHBOARD, PermissionLevel.READ),
    EndpointDef("GET /dashboard/query-performance", ResourceType.DATALAKE_DASHBOARD, PermissionLevel.READ),
    EndpointDef("GET /dashboard/data-flow", ResourceType.DATALAKE_DASHBOARD, PermissionLevel.READ),
]

ALL_ENDPOINTS = WRITE_ENDPOINTS + READ_SOURCE_ENDPOINTS + DASHBOARD_ENDPOINTS


# ============================================================================
# Expected permission matrix
# ============================================================================

# True = access granted, False = 403
EXPECTED_MATRIX = {
    # ADMIN: full access
    "ADMIN": {
        ResourceType.DATALAKE_SOURCE: {PermissionLevel.WRITE: True, PermissionLevel.READ: True},
        ResourceType.DATALAKE_DASHBOARD: {PermissionLevel.READ: True},
    },
    # TECHNICAL_EXPERT: full access (same as ADMIN for datalake)
    "TECHNICAL_EXPERT": {
        ResourceType.DATALAKE_SOURCE: {PermissionLevel.WRITE: True, PermissionLevel.READ: True},
        ResourceType.DATALAKE_DASHBOARD: {PermissionLevel.READ: True},
    },
    # BUSINESS_EXPERT: read-only source + dashboard
    "BUSINESS_EXPERT": {
        ResourceType.DATALAKE_SOURCE: {PermissionLevel.WRITE: False, PermissionLevel.READ: True},
        ResourceType.DATALAKE_DASHBOARD: {PermissionLevel.READ: True},
    },
    # VIEWER: dashboard only
    "VIEWER": {
        ResourceType.DATALAKE_SOURCE: {PermissionLevel.WRITE: False, PermissionLevel.READ: False},
        ResourceType.DATALAKE_DASHBOARD: {PermissionLevel.READ: True},
    },
}


# ============================================================================
# Helpers
# ============================================================================

def _build_auth_token(role: RoleDef, tenant_id: str) -> AuthToken:
    """Create an AuthToken with the given role's permissions."""
    now = datetime.utcnow()
    return AuthToken(
        token_id=f"tok-{role.name}",
        user_id=f"user-{role.name}",
        tenant_id=tenant_id,
        auth_method=AuthMethod.JWT,
        permissions=[
            Permission(resource_type=rt, level=lvl)
            for rt, lvl in role.permissions
        ],
        issued_at=now,
        expires_at=now + timedelta(hours=1),
    )


def _role_can_access(role: RoleDef, endpoint: EndpointDef) -> bool:
    """Look up the expected matrix to determine if role should have access."""
    rt_map = EXPECTED_MATRIX[role.name]
    level_map = rt_map.get(endpoint.resource_type, {})
    return level_map.get(endpoint.level, False)


# ============================================================================
# Hypothesis strategies
# ============================================================================

role_strategy = st.sampled_from(ALL_ROLES)
endpoint_strategy = st.sampled_from(ALL_ENDPOINTS)
tenant_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=30,
)


# ============================================================================
# Property Tests
# ============================================================================


class TestRBACPermissionMatrix:
    """**Validates: Requirements 7.1, 7.2, 7.3, 7.4**"""

    @settings(max_examples=200)
    @given(role=role_strategy, endpoint=endpoint_strategy, tenant_id=tenant_id_strategy)
    def test_permission_matrix_holds_for_all_combinations(
        self, role, endpoint, tenant_id
    ):
        """For any role-endpoint pair, has_permission matches the expected matrix.

        **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
        """
        token = _build_auth_token(role, tenant_id)
        actual = token.has_permission(endpoint.resource_type, endpoint.level)
        expected = _role_can_access(role, endpoint)

        assert actual == expected, (
            f"Role {role.name} accessing {endpoint.name} "
            f"(requires {endpoint.resource_type.value}/{endpoint.level.value}): "
            f"expected={expected}, actual={actual}"
        )

    @settings(max_examples=50)
    @given(role=role_strategy, tenant_id=tenant_id_strategy)
    def test_write_implies_read_for_same_resource(self, role, tenant_id):
        """If a role has WRITE on a resource, it must also have READ.

        Higher permission levels include lower ones in has_permission.

        **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
        """
        token = _build_auth_token(role, tenant_id)

        for rt in [ResourceType.DATALAKE_SOURCE, ResourceType.DATALAKE_DASHBOARD]:
            has_write = token.has_permission(rt, PermissionLevel.WRITE)
            has_read = token.has_permission(rt, PermissionLevel.READ)
            if has_write:
                assert has_read, (
                    f"Role {role.name}: has WRITE on {rt.value} but not READ"
                )

    @settings(max_examples=50)
    @given(
        role=st.sampled_from([BUSINESS_EXPERT, VIEWER]),
        write_ep=st.sampled_from(WRITE_ENDPOINTS),
        tenant_id=tenant_id_strategy,
    )
    def test_non_privileged_roles_denied_write_access(
        self, role, write_ep, tenant_id
    ):
        """BUSINESS_EXPERT and VIEWER must be denied WRITE on DATALAKE_SOURCE.

        **Validates: Requirements 7.2, 7.3, 7.4**
        """
        token = _build_auth_token(role, tenant_id)
        assert not token.has_permission(write_ep.resource_type, write_ep.level), (
            f"Role {role.name} should NOT have access to {write_ep.name}"
        )

    @settings(max_examples=50)
    @given(
        role=st.sampled_from([VIEWER]),
        read_ep=st.sampled_from(READ_SOURCE_ENDPOINTS),
        tenant_id=tenant_id_strategy,
    )
    def test_viewer_denied_source_read_access(self, role, read_ep, tenant_id):
        """VIEWER must be denied READ on DATALAKE_SOURCE endpoints.

        **Validates: Requirements 7.3, 7.4**
        """
        token = _build_auth_token(role, tenant_id)
        assert not token.has_permission(read_ep.resource_type, read_ep.level), (
            f"VIEWER should NOT have access to {read_ep.name}"
        )

    @settings(max_examples=50)
    @given(role=role_strategy, dash_ep=st.sampled_from(DASHBOARD_ENDPOINTS), tenant_id=tenant_id_strategy)
    def test_all_roles_can_access_dashboard(self, role, dash_ep, tenant_id):
        """All four roles must have READ access to dashboard endpoints.

        **Validates: Requirements 7.1, 7.2, 7.3**
        """
        token = _build_auth_token(role, tenant_id)
        assert token.has_permission(dash_ep.resource_type, dash_ep.level), (
            f"Role {role.name} should have access to {dash_ep.name}"
        )
