"""
Tenant Isolation Service for multi-tenant data access control.

Provides comprehensive tenant-level data isolation with automatic filtering,
cross-tenant access prevention, and tenant-aware query modification.
"""

import logging
from typing import Dict, List, Optional, Any, Type, Union
from uuid import UUID
from sqlalchemy.orm import Session, Query
from sqlalchemy import and_, or_, text
from sqlalchemy.sql import Select
from sqlalchemy.inspection import inspect
from contextlib import contextmanager

from src.database.connection import get_db_session, Base
from .models import DataAccessAuditModel, AuditEventType

logger = logging.getLogger(__name__)


class TenantContext:
    """Thread-local tenant context for automatic filtering."""
    
    def __init__(self):
        self._tenant_id: Optional[str] = None
        self._user_id: Optional[UUID] = None
        self._bypass_isolation: bool = False
    
    @property
    def tenant_id(self) -> Optional[str]:
        return self._tenant_id
    
    @property
    def user_id(self) -> Optional[UUID]:
        return self._user_id
    
    @property
    def bypass_isolation(self) -> bool:
        return self._bypass_isolation
    
    def set_context(self, tenant_id: str, user_id: Optional[UUID] = None):
        """Set tenant context."""
        self._tenant_id = tenant_id
        self._user_id = user_id
        self._bypass_isolation = False
    
    def clear_context(self):
        """Clear tenant context."""
        self._tenant_id = None
        self._user_id = None
        self._bypass_isolation = False
    
    def set_bypass(self, bypass: bool = True):
        """Set bypass isolation flag (for system operations)."""
        self._bypass_isolation = bypass


# Global tenant context instance
tenant_context = TenantContext()


class TenantIsolationService:
    """
    Tenant isolation service for multi-tenant data access control.
    
    Provides automatic tenant filtering, cross-tenant access prevention,
    and comprehensive audit logging.
    """
    
    def __init__(self):
        self.tenant_aware_models = self._discover_tenant_aware_models()
    
    def _discover_tenant_aware_models(self) -> Dict[str, Type[Base]]:
        """Discover models that have tenant_id field."""
        tenant_models = {}
        
        for model_class in Base.registry._class_registry.values():
            if hasattr(model_class, '__table__'):
                # Check if model has tenant_id column
                if hasattr(model_class, 'tenant_id'):
                    table_name = model_class.__tablename__
                    tenant_models[table_name] = model_class
                    logger.debug(f"Discovered tenant-aware model: {table_name}")
        
        return tenant_models
    
    @contextmanager
    def tenant_context_manager(self, tenant_id: str, user_id: Optional[UUID] = None):
        """Context manager for tenant isolation."""
        old_tenant = tenant_context.tenant_id
        old_user = tenant_context.user_id
        old_bypass = tenant_context.bypass_isolation
        
        try:
            tenant_context.set_context(tenant_id, user_id)
            yield
        finally:
            if old_tenant:
                tenant_context.set_context(old_tenant, old_user)
                tenant_context.set_bypass(old_bypass)
            else:
                tenant_context.clear_context()
    
    @contextmanager
    def bypass_isolation(self):
        """Context manager to bypass tenant isolation (for system operations)."""
        old_bypass = tenant_context.bypass_isolation
        try:
            tenant_context.set_bypass(True)
            yield
        finally:
            tenant_context.set_bypass(old_bypass)
    
    def apply_tenant_filter(self, query: Query, model_class: Type[Base]) -> Query:
        """
        Apply tenant filter to SQLAlchemy query.
        
        Args:
            query: SQLAlchemy query object
            model_class: Model class being queried
            
        Returns:
            Query with tenant filter applied
        """
        # Skip if bypassing isolation
        if tenant_context.bypass_isolation:
            return query
        
        # Skip if no tenant context
        if not tenant_context.tenant_id:
            logger.warning("No tenant context set for query")
            return query
        
        # Skip if model doesn't have tenant_id
        if not hasattr(model_class, 'tenant_id'):
            return query
        
        # Apply tenant filter
        filtered_query = query.filter(model_class.tenant_id == tenant_context.tenant_id)
        
        logger.debug(f"Applied tenant filter for {model_class.__name__}: {tenant_context.tenant_id}")
        return filtered_query
    
    def validate_tenant_access(
        self,
        model_instance: Base,
        operation: str = "access",
        db: Optional[Session] = None
    ) -> bool:
        """
        Validate that current tenant can access the model instance.
        
        Args:
            model_instance: Model instance to validate
            operation: Operation being performed
            db: Database session
            
        Returns:
            True if access is allowed
        """
        # Skip if bypassing isolation
        if tenant_context.bypass_isolation:
            return True
        
        # Skip if no tenant context
        if not tenant_context.tenant_id:
            logger.warning("No tenant context set for validation")
            return False
        
        # Skip if model doesn't have tenant_id
        if not hasattr(model_instance, 'tenant_id'):
            return True
        
        # Check tenant match
        instance_tenant = getattr(model_instance, 'tenant_id')
        if instance_tenant != tenant_context.tenant_id:
            logger.warning(
                f"Tenant isolation violation: {tenant_context.tenant_id} "
                f"attempted to access {model_instance.__class__.__name__} "
                f"belonging to {instance_tenant}"
            )
            
            # Log security event
            self._log_isolation_violation(
                model_instance.__class__.__name__,
                str(getattr(model_instance, 'id', 'unknown')),
                operation,
                db
            )
            
            return False
        
        return True
    
    def ensure_tenant_isolation(self, model_instance: Base) -> None:
        """
        Ensure model instance has correct tenant_id.
        
        Args:
            model_instance: Model instance to validate
            
        Raises:
            ValueError: If tenant isolation is violated
        """
        if not self.validate_tenant_access(model_instance, "create"):
            raise ValueError(
                f"Tenant isolation violation: Cannot create {model_instance.__class__.__name__} "
                f"for different tenant"
            )
        
        # Set tenant_id if not already set
        if hasattr(model_instance, 'tenant_id') and not getattr(model_instance, 'tenant_id'):
            if tenant_context.tenant_id:
                setattr(model_instance, 'tenant_id', tenant_context.tenant_id)
                logger.debug(f"Set tenant_id for {model_instance.__class__.__name__}")
    
    def filter_tenant_data(
        self,
        data_list: List[Base],
        strict: bool = True
    ) -> List[Base]:
        """
        Filter list of model instances by tenant.
        
        Args:
            data_list: List of model instances
            strict: If True, raise error on violation; if False, filter silently
            
        Returns:
            Filtered list containing only current tenant's data
        """
        if tenant_context.bypass_isolation:
            return data_list
        
        if not tenant_context.tenant_id:
            if strict:
                raise ValueError("No tenant context set")
            return []
        
        filtered_data = []
        
        for item in data_list:
            if not hasattr(item, 'tenant_id'):
                filtered_data.append(item)
                continue
            
            item_tenant = getattr(item, 'tenant_id')
            if item_tenant == tenant_context.tenant_id:
                filtered_data.append(item)
            elif strict:
                raise ValueError(
                    f"Tenant isolation violation: {item.__class__.__name__} "
                    f"belongs to different tenant"
                )
        
        return filtered_data
    
    def get_tenant_stats(self, tenant_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Get statistics for tenant data across all models.
        
        Args:
            tenant_id: Tenant ID
            db: Database session
            
        Returns:
            Dictionary with tenant statistics
        """
        if db is None:
            db = next(get_db_session())
        
        stats = {
            "tenant_id": tenant_id,
            "model_counts": {},
            "total_records": 0
        }
        
        with self.bypass_isolation():
            for table_name, model_class in self.tenant_aware_models.items():
                try:
                    count = db.query(model_class).filter(
                        model_class.tenant_id == tenant_id
                    ).count()
                    
                    stats["model_counts"][table_name] = count
                    stats["total_records"] += count
                    
                except Exception as e:
                    logger.error(f"Error counting {table_name} for tenant {tenant_id}: {e}")
                    stats["model_counts"][table_name] = -1
        
        return stats
    
    def cleanup_tenant_data(
        self,
        tenant_id: str,
        dry_run: bool = True,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Clean up all data for a tenant (for tenant deletion).
        
        Args:
            tenant_id: Tenant ID to clean up
            dry_run: If True, only count records without deleting
            db: Database session
            
        Returns:
            Dictionary with cleanup results
        """
        if db is None:
            db = next(get_db_session())
        
        results = {
            "tenant_id": tenant_id,
            "dry_run": dry_run,
            "deleted_counts": {},
            "total_deleted": 0,
            "errors": []
        }
        
        with self.bypass_isolation():
            for table_name, model_class in self.tenant_aware_models.items():
                try:
                    # Count records
                    count = db.query(model_class).filter(
                        model_class.tenant_id == tenant_id
                    ).count()
                    
                    if not dry_run and count > 0:
                        # Delete records
                        deleted = db.query(model_class).filter(
                            model_class.tenant_id == tenant_id
                        ).delete()
                        
                        results["deleted_counts"][table_name] = deleted
                        results["total_deleted"] += deleted
                        
                        logger.info(f"Deleted {deleted} records from {table_name} for tenant {tenant_id}")
                    else:
                        results["deleted_counts"][table_name] = count
                        results["total_deleted"] += count
                    
                except Exception as e:
                    error_msg = f"Error cleaning {table_name} for tenant {tenant_id}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            if not dry_run:
                try:
                    db.commit()
                    logger.info(f"Tenant cleanup completed for {tenant_id}")
                except Exception as e:
                    db.rollback()
                    error_msg = f"Error committing tenant cleanup: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
        
        return results
    
    def validate_cross_tenant_references(
        self,
        model_instance: Base,
        db: Optional[Session] = None
    ) -> List[str]:
        """
        Validate that model instance doesn't reference data from other tenants.
        
        Args:
            model_instance: Model instance to validate
            db: Database session
            
        Returns:
            List of validation errors
        """
        if db is None:
            db = next(get_db_session())
        
        errors = []
        
        # Skip if bypassing isolation
        if tenant_context.bypass_isolation:
            return errors
        
        # Get model's foreign key relationships
        mapper = inspect(model_instance.__class__)
        
        for relationship in mapper.relationships:
            # Get related model class
            related_class = relationship.mapper.class_
            
            # Skip if related model doesn't have tenant_id
            if not hasattr(related_class, 'tenant_id'):
                continue
            
            # Get foreign key value
            foreign_key = relationship.local_columns
            if not foreign_key:
                continue
            
            fk_column = list(foreign_key)[0]
            fk_value = getattr(model_instance, fk_column.name)
            
            if fk_value is None:
                continue
            
            # Check if referenced record belongs to same tenant
            with self.bypass_isolation():
                referenced_record = db.query(related_class).filter(
                    getattr(related_class, relationship.mapper.primary_key[0].name) == fk_value
                ).first()
                
                if referenced_record:
                    referenced_tenant = getattr(referenced_record, 'tenant_id')
                    current_tenant = getattr(model_instance, 'tenant_id', tenant_context.tenant_id)
                    
                    if referenced_tenant != current_tenant:
                        errors.append(
                            f"Cross-tenant reference: {relationship.key} references "
                            f"{related_class.__name__} from tenant {referenced_tenant}"
                        )
        
        return errors
    
    def _log_isolation_violation(
        self,
        model_name: str,
        resource_id: str,
        operation: str,
        db: Optional[Session] = None
    ) -> None:
        """Log tenant isolation violation for security monitoring."""
        if db is None:
            db = next(get_db_session())
        
        try:
            audit_log = DataAccessAuditModel(
                tenant_id=tenant_context.tenant_id or "unknown",
                user_id=tenant_context.user_id,
                event_type=AuditEventType.PERMISSION_DENIED,
                resource_id=resource_id,
                permission_granted=False,
                request_context={
                    "operation": operation,
                    "model_name": model_name,
                    "violation_type": "tenant_isolation"
                },
                response_context={
                    "reason": "Tenant isolation violation",
                    "attempted_tenant": tenant_context.tenant_id,
                },
                risk_score=0.8,  # High risk score for isolation violations
                anomaly_flags=["tenant_isolation_violation"]
            )
            
            db.add(audit_log)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging isolation violation: {e}")
            db.rollback()


# Convenience functions for common operations
def set_tenant_context(tenant_id: str, user_id: Optional[UUID] = None):
    """Set global tenant context."""
    tenant_context.set_context(tenant_id, user_id)


def clear_tenant_context():
    """Clear global tenant context."""
    tenant_context.clear_context()


def get_current_tenant() -> Optional[str]:
    """Get current tenant ID from context."""
    return tenant_context.tenant_id


def with_tenant_context(tenant_id: str, user_id: Optional[UUID] = None):
    """Decorator for functions that need tenant context."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with TenantIsolationService().tenant_context_manager(tenant_id, user_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator