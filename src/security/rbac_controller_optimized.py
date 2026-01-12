"""
Optimized RBAC Controller for SuperInsight Platform.

Extends the existing RBAC controller with advanced performance optimizations
to achieve <10ms permission check response times.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from src.security.rbac_controller import RBACController
from src.security.permission_performance_optimizer import (
    get_permission_performance_optimizer,
    OptimizationConfig
)
from src.security.rbac_models import ResourceType

logger = logging.getLogger(__name__)


class OptimizedRBACController(RBACController):
    """
    Performance-optimized RBAC controller.
    
    Extends RBACController with advanced optimizations:
    - Sub-10ms permission checks
    - Intelligent caching and preloading
    - Query optimization
    - Batch processing
    - Performance monitoring
    """
    
    def __init__(self, secret_key: str = "your-secret-key", optimization_config: Optional[OptimizationConfig] = None):
        super().__init__(secret_key)
        
        # Initialize performance optimizer
        if optimization_config:
            self.performance_optimizer = get_permission_performance_optimizer()
            self.performance_optimizer.config = optimization_config
        else:
            self.performance_optimizer = get_permission_performance_optimizer()
        
        # Performance tracking
        self._performance_stats = {
            "total_checks": 0,
            "optimized_checks": 0,
            "cache_hits": 0,
            "avg_response_time_ms": 0.0,
            "checks_under_10ms": 0
        }
    
    async def check_user_permission_optimized(
        self,
        user_id: UUID,
        permission_name: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        db: Session = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Optimized permission check with <10ms target response time.
        
        Args:
            user_id: User identifier
            permission_name: Permission name to check
            resource_id: Optional specific resource ID
            resource_type: Optional resource type
            db: Database session
            ip_address: Optional IP address for audit logging
            user_agent: Optional user agent for audit logging
            
        Returns:
            True if user has permission
        """
        try:
            # Get user for tenant info
            user = self.get_user_by_id(user_id, db)
            if not user or not user.is_active:
                return False
            
            # Use performance optimizer for the check
            result, response_time_ms = await self.performance_optimizer.optimize_permission_check(
                user_id=user_id,
                permission_name=permission_name,
                permission_cache=self.permission_cache,
                rbac_controller=self,
                db=db,
                tenant_id=user.tenant_id,
                resource_id=resource_id,
                resource_type=resource_type
            )
            
            # Update performance stats
            self._update_performance_stats(response_time_ms, True)
            
            # Log permission check to audit system (async, non-blocking)
            if self.performance_optimizer.config.async_logging_enabled:
                asyncio.create_task(
                    self._async_log_permission_check(
                        user_id=user_id,
                        tenant_id=user.tenant_id,
                        permission_name=permission_name,
                        resource_id=resource_id,
                        resource_type=resource_type,
                        result=result,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        response_time_ms=response_time_ms,
                        db=db
                    )
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Optimized permission check failed for user {user_id}, permission {permission_name}: {e}")
            return False
    
    def check_user_permission(
        self,
        user_id: UUID,
        permission_name: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        db: Session = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Enhanced permission check that automatically uses optimization.
        
        This method overrides the parent method to provide automatic optimization
        while maintaining backward compatibility.
        """
        if self.performance_optimizer.is_optimization_enabled():
            # Use async optimization in a sync context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an async context, create a task
                    # For sync calls, we'll use the fallback
                    return self._sync_optimized_check(
                        user_id, permission_name, resource_id, resource_type, db, ip_address, user_agent
                    )
                else:
                    # Run the async version
                    return loop.run_until_complete(
                        self.check_user_permission_optimized(
                            user_id, permission_name, resource_id, resource_type, db, ip_address, user_agent
                        )
                    )
            except RuntimeError:
                # No event loop, use sync fallback
                return self._sync_optimized_check(
                    user_id, permission_name, resource_id, resource_type, db, ip_address, user_agent
                )
        else:
            # Use parent implementation
            return super().check_user_permission(
                user_id, permission_name, resource_id, resource_type, db, ip_address, user_agent
            )
    
    def _sync_optimized_check(
        self,
        user_id: UUID,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        db: Session,
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> bool:
        """Synchronous optimized permission check."""
        start_time = time.perf_counter()
        
        try:
            # Get user for tenant info
            user = self.get_user_by_id(user_id, db)
            if not user or not user.is_active:
                return False
            
            # Fast cache check
            cached_result = self.permission_cache.get_permission(
                user_id, permission_name, resource_id, resource_type, user.tenant_id
            )
            
            if cached_result is not None:
                response_time_ms = (time.perf_counter() - start_time) * 1000
                self._update_performance_stats(response_time_ms, True)
                
                # Log async if enabled
                if self.performance_optimizer.config.async_logging_enabled:
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            self._async_log_permission_check(
                                user_id, user.tenant_id, permission_name, resource_id,
                                resource_type, cached_result, ip_address, user_agent,
                                response_time_ms, db
                            )
                        )
                    except RuntimeError:
                        pass  # No event loop, skip async logging
                
                return cached_result
            
            # Admin users have all permissions
            if user.role.value == "ADMIN":
                result = True
            else:
                # Use optimized database check
                result = self._optimized_sync_permission_check(
                    user_id, permission_name, resource_id, resource_type, user.tenant_id, db
                )
            
            # Cache the result
            self.permission_cache.set_permission(
                user_id, permission_name, result, resource_id, resource_type, user.tenant_id
            )
            
            response_time_ms = (time.perf_counter() - start_time) * 1000
            self._update_performance_stats(response_time_ms, True)
            
            return result
            
        except Exception as e:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            self._update_performance_stats(response_time_ms, False)
            logger.error(f"Sync optimized permission check failed: {e}")
            return False
    
    def _optimized_sync_permission_check(
        self,
        user_id: UUID,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        tenant_id: str,
        db: Session
    ) -> bool:
        """Synchronous optimized database permission check."""
        try:
            from sqlalchemy import text
            
            # Use optimized query with proper indexing hints
            query = """
            SELECT EXISTS(
                SELECT 1
                FROM permissions p
                INNER JOIN role_permissions rp ON p.id = rp.permission_id
                INNER JOIN user_roles ur ON rp.role_id = ur.role_id
                INNER JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id 
                AND r.tenant_id = :tenant_id 
                AND r.is_active = true
                AND p.name = :permission_name
            ) as has_permission
            """
            
            params = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "permission_name": permission_name
            }
            
            result = db.execute(text(query), params)
            row = result.fetchone()
            
            return row.has_permission if row else False
            
        except Exception as e:
            logger.error(f"Optimized sync permission check query failed: {e}")
            return False
    
    async def batch_check_permissions_optimized(
        self,
        user_id: UUID,
        permissions: List[str],
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        db: Session = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Optimized batch permission checking with <10ms target per permission.
        
        Args:
            user_id: User identifier
            permissions: List of permission names to check
            resource_id: Optional specific resource ID
            resource_type: Optional resource type
            db: Database session
            ip_address: Optional IP address for audit logging
            user_agent: Optional user agent for audit logging
            
        Returns:
            Dictionary mapping permission names to results
        """
        try:
            # Get user for tenant info
            user = self.get_user_by_id(user_id, db)
            if not user or not user.is_active:
                return {perm: False for perm in permissions}
            
            # Use performance optimizer for batch check
            results, total_response_time_ms = await self.performance_optimizer.batch_optimize_permission_checks(
                user_id=user_id,
                permissions=permissions,
                permission_cache=self.permission_cache,
                rbac_controller=self,
                db=db,
                tenant_id=user.tenant_id,
                resource_id=resource_id,
                resource_type=resource_type
            )
            
            # Update performance stats
            avg_response_time = total_response_time_ms / len(permissions) if permissions else 0
            for _ in permissions:
                self._update_performance_stats(avg_response_time, True)
            
            # Log batch permission check (async, non-blocking)
            if self.performance_optimizer.config.async_logging_enabled:
                asyncio.create_task(
                    self._async_log_batch_permission_check(
                        user_id=user_id,
                        tenant_id=user.tenant_id,
                        permissions=permissions,
                        results=results,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        total_response_time_ms=total_response_time_ms,
                        db=db
                    )
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Optimized batch permission check failed for user {user_id}: {e}")
            return {perm: False for perm in permissions}
    
    def batch_check_permissions(
        self,
        user_id: UUID,
        permissions: List[str],
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        db: Session = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Enhanced batch permission check that automatically uses optimization.
        
        This method overrides the parent method to provide automatic optimization
        while maintaining backward compatibility.
        """
        if self.performance_optimizer.is_optimization_enabled():
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create a task for async execution
                    return self._sync_batch_optimized_check(
                        user_id, permissions, resource_id, resource_type, db, ip_address, user_agent
                    )
                else:
                    # Run the async version
                    return loop.run_until_complete(
                        self.batch_check_permissions_optimized(
                            user_id, permissions, resource_id, resource_type, db, ip_address, user_agent
                        )
                    )
            except RuntimeError:
                # No event loop, use sync fallback
                return self._sync_batch_optimized_check(
                    user_id, permissions, resource_id, resource_type, db, ip_address, user_agent
                )
        else:
            # Use parent implementation
            return super().batch_check_permissions(
                user_id, permissions, resource_id, resource_type, db, ip_address, user_agent
            )
    
    def _sync_batch_optimized_check(
        self,
        user_id: UUID,
        permissions: List[str],
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        db: Session,
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> Dict[str, bool]:
        """Synchronous optimized batch permission check."""
        start_time = time.perf_counter()
        results = {}
        
        try:
            # Get user for tenant info
            user = self.get_user_by_id(user_id, db)
            if not user or not user.is_active:
                return {perm: False for perm in permissions}
            
            # Check cache for all permissions first
            uncached_permissions = []
            for permission in permissions:
                cached_result = self.permission_cache.get_permission(
                    user_id, permission, resource_id, resource_type, user.tenant_id
                )
                if cached_result is not None:
                    results[permission] = cached_result
                else:
                    uncached_permissions.append(permission)
            
            # Batch check uncached permissions
            if uncached_permissions:
                batch_results = self._sync_batch_permission_check(
                    user_id, uncached_permissions, user.tenant_id, db
                )
                results.update(batch_results)
                
                # Cache the results
                for permission, result in batch_results.items():
                    self.permission_cache.set_permission(
                        user_id, permission, result, resource_id, resource_type, user.tenant_id
                    )
            
            total_response_time_ms = (time.perf_counter() - start_time) * 1000
            avg_response_time = total_response_time_ms / len(permissions) if permissions else 0
            
            # Update performance stats
            for _ in permissions:
                self._update_performance_stats(avg_response_time, True)
            
            return results
            
        except Exception as e:
            total_response_time_ms = (time.perf_counter() - start_time) * 1000
            avg_response_time = total_response_time_ms / len(permissions) if permissions else 0
            
            for _ in permissions:
                self._update_performance_stats(avg_response_time, False)
            
            logger.error(f"Sync batch permission check failed: {e}")
            return {perm: False for perm in permissions}
    
    def _sync_batch_permission_check(
        self,
        user_id: UUID,
        permissions: List[str],
        tenant_id: str,
        db: Session
    ) -> Dict[str, bool]:
        """Synchronous batch permission check using optimized query."""
        try:
            from sqlalchemy import text
            
            # Create optimized batch query
            placeholders = ",".join([f":perm_{i}" for i in range(len(permissions))])
            query = f"""
            SELECT p.name
            FROM permissions p
            INNER JOIN role_permissions rp ON p.id = rp.permission_id
            INNER JOIN user_roles ur ON rp.role_id = ur.role_id
            INNER JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = :user_id 
            AND r.tenant_id = :tenant_id 
            AND r.is_active = true
            AND p.name IN ({placeholders})
            """
            
            params = {
                "user_id": user_id,
                "tenant_id": tenant_id
            }
            for i, perm in enumerate(permissions):
                params[f"perm_{i}"] = perm
            
            result = db.execute(text(query), params)
            user_permissions = {row.name for row in result}
            
            # Return results for all requested permissions
            return {perm: perm in user_permissions for perm in permissions}
            
        except Exception as e:
            logger.error(f"Sync batch permission check query failed: {e}")
            return {perm: False for perm in permissions}
    
    async def preload_user_permissions(
        self,
        user_id: UUID,
        db: Session,
        common_permissions: Optional[List[str]] = None
    ) -> bool:
        """
        Preload common permissions for a user to improve cache hit rates.
        
        Args:
            user_id: User to preload permissions for
            db: Database session
            common_permissions: List of common permissions to preload
            
        Returns:
            True if successful
        """
        try:
            user = self.get_user_by_id(user_id, db)
            if not user:
                return False
            
            preloaded_count = await self.performance_optimizer.preloader.preload_user_permissions(
                user_id, user.tenant_id, self.permission_cache, db, self
            )
            
            logger.debug(f"Preloaded {preloaded_count} permissions for user {user_id}")
            return preloaded_count > 0
            
        except Exception as e:
            logger.error(f"Failed to preload permissions for user {user_id}: {e}")
            return False
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        optimizer_report = self.performance_optimizer.get_performance_report()
        cache_stats = self.get_cache_statistics()
        
        return {
            "controller_stats": self._performance_stats,
            "optimizer_report": optimizer_report,
            "cache_stats": cache_stats,
            "optimization_enabled": self.performance_optimizer.is_optimization_enabled(),
            "target_response_time_ms": self.performance_optimizer.config.target_response_time_ms
        }
    
    def get_performance_recommendations(self) -> List[str]:
        """Get performance optimization recommendations."""
        return self.performance_optimizer.monitor.get_optimization_recommendations()
    
    def _update_performance_stats(self, response_time_ms: float, success: bool):
        """Update internal performance statistics."""
        self._performance_stats["total_checks"] += 1
        
        if success:
            self._performance_stats["optimized_checks"] += 1
            
            if response_time_ms < self.performance_optimizer.config.target_response_time_ms:
                self._performance_stats["checks_under_10ms"] += 1
            
            # Update rolling average
            current_avg = self._performance_stats["avg_response_time_ms"]
            total_checks = self._performance_stats["total_checks"]
            self._performance_stats["avg_response_time_ms"] = (
                (current_avg * (total_checks - 1) + response_time_ms) / total_checks
            )
    
    async def _async_log_permission_check(
        self,
        user_id: UUID,
        tenant_id: str,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        result: bool,
        ip_address: Optional[str],
        user_agent: Optional[str],
        response_time_ms: float,
        db: Session
    ):
        """Asynchronously log permission check to audit system."""
        try:
            await self.permission_audit.log_permission_check(
                user_id=user_id,
                tenant_id=tenant_id,
                permission_name=permission_name,
                resource_id=resource_id,
                resource_type=resource_type.value if resource_type else None,
                result=result,
                ip_address=ip_address,
                user_agent=user_agent,
                cache_hit=False,  # We don't track this in async logging
                response_time_ms=response_time_ms,
                db=db
            )
        except Exception as e:
            logger.error(f"Failed to log permission check asynchronously: {e}")
    
    async def _async_log_batch_permission_check(
        self,
        user_id: UUID,
        tenant_id: str,
        permissions: List[str],
        results: Dict[str, bool],
        ip_address: Optional[str],
        user_agent: Optional[str],
        total_response_time_ms: float,
        db: Session
    ):
        """Asynchronously log batch permission check to audit system."""
        try:
            await self.permission_audit.log_bulk_permission_check(
                user_id=user_id,
                tenant_id=tenant_id,
                permissions=permissions,
                results=results,
                ip_address=ip_address,
                user_agent=user_agent,
                cache_hits=0,  # We don't track this in async logging
                total_response_time_ms=total_response_time_ms,
                db=db
            )
        except Exception as e:
            logger.error(f"Failed to log batch permission check asynchronously: {e}")
    
    def enable_performance_optimization(self):
        """Enable performance optimization features."""
        self.performance_optimizer.enable_optimization()
        logger.info("Performance optimization enabled for RBAC controller")
    
    def disable_performance_optimization(self):
        """Disable performance optimization features."""
        self.performance_optimizer.disable_optimization()
        logger.info("Performance optimization disabled for RBAC controller")


# Global optimized controller instance
_optimized_rbac_controller = None


def get_optimized_rbac_controller(
    secret_key: str = "your-secret-key",
    optimization_config: Optional[OptimizationConfig] = None
) -> OptimizedRBACController:
    """Get the global optimized RBAC controller instance."""
    global _optimized_rbac_controller
    if _optimized_rbac_controller is None:
        _optimized_rbac_controller = OptimizedRBACController(secret_key, optimization_config)
    return _optimized_rbac_controller