"""
Multi-Tenant Workspace Module

This module provides comprehensive multi-tenant workspace management including:
- Tenant lifecycle management
- Workspace hierarchy management
- Member and role management
- Resource quota management
- Data isolation
- Cross-tenant collaboration

Components:
- TenantManager: Manages tenant creation, configuration, and lifecycle
- WorkspaceManager: Manages workspace hierarchy and configuration
- MemberManager: Manages workspace members and roles
- QuotaManager: Manages resource quotas and usage tracking
- IsolationEngine: Ensures tenant data isolation
- CrossTenantCollaborator: Enables controlled cross-tenant collaboration
"""

from src.multi_tenant.workspace.schemas import (
    # Enums
    TenantStatus,
    WorkspaceStatus,
    MemberRole,
    SharePermission,
    EntityType,
    ResourceType,
    
    # Tenant schemas
    TenantConfig,
    TenantCreateConfig,
    TenantUpdateConfig,
    TenantQuotaConfig,
    
    # Workspace schemas
    WorkspaceCreateConfig,
    WorkspaceUpdateConfig,
    WorkspaceNode,
    WorkspaceTemplate,
    
    # Member schemas
    MemberAddRequest,
    CustomRoleConfig,
    InvitationConfig,
    
    # Quota schemas
    QuotaConfig,
    QuotaUsageData,
    QuotaCheckResult,
    TemporaryQuotaConfig,
    
    # Share schemas
    ShareConfig,
    SharedResourceAccess,
)

__all__ = [
    # Enums
    "TenantStatus",
    "WorkspaceStatus", 
    "MemberRole",
    "SharePermission",
    "EntityType",
    "ResourceType",
    
    # Tenant schemas
    "TenantConfig",
    "TenantCreateConfig",
    "TenantUpdateConfig",
    "TenantQuotaConfig",
    
    # Workspace schemas
    "WorkspaceCreateConfig",
    "WorkspaceUpdateConfig",
    "WorkspaceNode",
    "WorkspaceTemplate",
    
    # Member schemas
    "MemberAddRequest",
    "CustomRoleConfig",
    "InvitationConfig",
    
    # Quota schemas
    "QuotaConfig",
    "QuotaUsageData",
    "QuotaCheckResult",
    "TemporaryQuotaConfig",
    
    # Share schemas
    "ShareConfig",
    "SharedResourceAccess",
]
