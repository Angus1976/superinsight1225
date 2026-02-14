"""
Authorization service for AI Application Integration.

This module provides the AuthorizationService class for enforcing multi-tenant
isolation and permission checks for AI gateways.
"""

from typing import Optional, List, Any
from sqlalchemy.orm import Session, Query
from sqlalchemy import and_

from src.models.ai_integration import AIGateway


class PermissionDeniedError(Exception):
    """Raised when permission check fails."""
    pass


class CrossTenantAccessError(Exception):
    """Raised when cross-tenant access is attempted."""
    pass


class AuthorizationService:
    """
    Enforces authorization and tenant isolation for AI gateways.
    
    Provides methods for:
    - Permission checking
    - Tenant filter injection into queries
    - Cross-tenant access validation
    """
    
    def __init__(self, db: Session):
        """
        Initialize AuthorizationService.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def check_permission(
        self,
        gateway_id: str,
        resource: str,
        action: str
    ) -> bool:
        """
        Check if gateway has permission for resource and action.
        
        Args:
            gateway_id: Gateway ID to check
            resource: Resource type (e.g., 'data', 'skill', 'config')
            action: Action type (e.g., 'read', 'write', 'delete')
            
        Returns:
            True if gateway has permission, False otherwise
            
        Validates: Requirements 4.2
        """
        # Fetch gateway
        gateway = self.db.query(AIGateway).filter(
            AIGateway.id == gateway_id
        ).first()
        
        if not gateway:
            return False
        
        # Check if gateway is active
        if gateway.status != "active":
            return False
        
        # For now, all active gateways have basic permissions
        # In future, this can be extended with role-based access control
        basic_permissions = {
            'data': ['read'],
            'skill': ['read'],
            'config': ['read']
        }
        
        if resource in basic_permissions:
            return action in basic_permissions[resource]
        
        return False
    
    def apply_tenant_filter(
        self,
        query: Query,
        tenant_id: str,
        model_class: Any
    ) -> Query:
        """
        Apply tenant filter to database query.
        
        Injects tenant_id filter into the query to ensure multi-tenant isolation.
        This ensures that queries only return data belonging to the specified tenant.
        
        Args:
            query: SQLAlchemy query object
            tenant_id: Tenant ID to filter by
            model_class: Model class being queried (must have tenant_id column)
            
        Returns:
            Query with tenant filter applied
            
        Raises:
            ValueError: If model_class doesn't have tenant_id attribute
            
        Validates: Requirements 4.4
        """
        # Verify model has tenant_id attribute
        if not hasattr(model_class, 'tenant_id'):
            raise ValueError(
                f"Model {model_class.__name__} does not have tenant_id attribute"
            )
        
        # Apply tenant filter
        return query.filter(model_class.tenant_id == tenant_id)
    
    def validate_cross_tenant_access(
        self,
        gateway_id: str,
        resource_tenant_id: str
    ) -> None:
        """
        Validate that gateway is not attempting cross-tenant access.
        
        Checks if the gateway's tenant matches the resource's tenant.
        Raises CrossTenantAccessError if they don't match.
        
        Args:
            gateway_id: Gateway ID attempting access
            resource_tenant_id: Tenant ID of the resource being accessed
            
        Raises:
            CrossTenantAccessError: If gateway tenant doesn't match resource tenant
            PermissionDeniedError: If gateway not found
            
        Validates: Requirements 4.3
        """
        # Fetch gateway
        gateway = self.db.query(AIGateway).filter(
            AIGateway.id == gateway_id
        ).first()
        
        if not gateway:
            raise PermissionDeniedError(f"Gateway {gateway_id} not found")
        
        # Check tenant match
        if gateway.tenant_id != resource_tenant_id:
            raise CrossTenantAccessError(
                f"Gateway {gateway_id} (tenant {gateway.tenant_id}) "
                f"attempted to access resource from tenant {resource_tenant_id}"
            )
    
    def get_gateway_tenant(self, gateway_id: str) -> Optional[str]:
        """
        Get the tenant ID for a gateway.
        
        Args:
            gateway_id: Gateway ID to look up
            
        Returns:
            Tenant ID if gateway exists, None otherwise
        """
        gateway = self.db.query(AIGateway).filter(
            AIGateway.id == gateway_id
        ).first()
        
        return gateway.tenant_id if gateway else None
    
    def filter_by_tenant(
        self,
        items: List[Any],
        tenant_id: str,
        tenant_attr: str = 'tenant_id'
    ) -> List[Any]:
        """
        Filter a list of items by tenant ID.
        
        Useful for filtering in-memory collections by tenant.
        
        Args:
            items: List of items to filter
            tenant_id: Tenant ID to filter by
            tenant_attr: Attribute name for tenant ID (default: 'tenant_id')
            
        Returns:
            Filtered list containing only items from specified tenant
        """
        return [
            item for item in items
            if hasattr(item, tenant_attr) and getattr(item, tenant_attr) == tenant_id
        ]
