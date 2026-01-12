"""
Permission Performance Optimizer for SuperInsight Platform.

Implements advanced performance optimizations to achieve <10ms permission check response times.
Includes micro-optimizations, query optimization, and performance monitoring.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from uuid import UUID
import threading
from concurrent.futures import ThreadPoolExecutor
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import text, select, and_

from src.security.rbac_models import (
    RoleModel, PermissionModel, UserRoleModel, RolePermissionModel,
    PermissionScope, ResourceType
)

logger = logging.getLogger(__name__)


@dataclass
class PermissionCheckMetrics:
    """Metrics for individual permission checks."""
    user_id: UUID
    permission_name: str
    response_time_ms: float
    cache_hit: bool
    timestamp: datetime
    tenant_id: Optional[str] = None
    resource_id: Optional[str] = None


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    total_checks: int = 0
    cache_hits: int = 0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    checks_under_10ms: int = 0
    checks_over_10ms: int = 0
    target_compliance_rate: float = 0.0  # Percentage under 10ms
    
    def update_compliance_rate(self):
        """Update the target compliance rate."""
        if self.total_checks > 0:
            self.target_compliance_rate = (self.checks_under_10ms / self.total_checks) * 100


@dataclass
class OptimizationConfig:
    """Configuration for performance optimizations."""
    target_response_time_ms: float = 10.0
    cache_preload_enabled: bool = True
    query_optimization_enabled: bool = True
    batch_processing_enabled: bool = True
    async_logging_enabled: bool = True
    connection_pooling_enabled: bool = True
    memory_optimization_enabled: bool = True
    
    # Cache settings
    memory_cache_size: int = 5000
    redis_cache_ttl: int = 600  # 10 minutes
    preload_common_permissions: bool = True
    
    # Query optimization settings
    use_prepared_statements: bool = True
    enable_query_hints: bool = True
    batch_size: int = 100
    
    # Performance monitoring
    metrics_collection_enabled: bool = True
    performance_alerts_enabled: bool = True
    slow_query_threshold_ms: float = 5.0


class PermissionQueryOptimizer:
    """Optimizes database queries for permission checking."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self._prepared_statements = {}
        self._query_cache = {}
        self._lock = threading.Lock()
    
    def get_optimized_user_permissions_query(self, user_id: UUID, tenant_id: str) -> str:
        """Get optimized query for user permissions."""
        cache_key = f"user_perms_{tenant_id}"
        
        if cache_key not in self._prepared_statements:
            with self._lock:
                if cache_key not in self._prepared_statements:
                    # Optimized query with proper indexes and hints
                    query = """
                    SELECT DISTINCT p.name, p.scope, p.resource_type
                    FROM permissions p
                    INNER JOIN role_permissions rp ON p.id = rp.permission_id
                    INNER JOIN user_roles ur ON rp.role_id = ur.role_id
                    INNER JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id 
                    AND r.tenant_id = :tenant_id 
                    AND r.is_active = true
                    """
                    
                    if self.config.enable_query_hints:
                        # Add PostgreSQL-specific hints for better performance
                        query = f"/*+ USE_INDEX(ur, idx_user_roles_user_id) */ {query}"
                    
                    self._prepared_statements[cache_key] = query
        
        return self._prepared_statements[cache_key]
    
    def get_batch_permission_check_query(self, permissions: List[str]) -> str:
        """Get optimized batch permission check query."""
        permission_count = len(permissions)
        cache_key = f"batch_perms_{permission_count}"
        
        if cache_key not in self._prepared_statements:
            with self._lock:
                if cache_key not in self._prepared_statements:
                    placeholders = ",".join([f":perm_{i}" for i in range(permission_count)])
                    query = f"""
                    SELECT p.name, COUNT(*) as has_permission
                    FROM permissions p
                    INNER JOIN role_permissions rp ON p.id = rp.permission_id
                    INNER JOIN user_roles ur ON rp.role_id = ur.role_id
                    INNER JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = :user_id 
                    AND r.tenant_id = :tenant_id 
                    AND r.is_active = true
                    AND p.name IN ({placeholders})
                    GROUP BY p.name
                    """
                    self._prepared_statements[cache_key] = query
        
        return self._prepared_statements[cache_key]


class PermissionPreloader:
    """Preloads common permissions into cache for faster access."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.common_permissions = [
            "read_data", "write_data", "view_dashboard", "manage_projects",
            "view_reports", "export_data", "manage_users", "view_analytics",
            "create_annotations", "edit_annotations", "delete_annotations",
            "manage_datasets", "view_billing", "manage_billing"
        ]
        self._preload_stats = defaultdict(int)
    
    async def preload_user_permissions(
        self,
        user_id: UUID,
        tenant_id: str,
        permission_cache,
        db: Session,
        rbac_controller
    ) -> int:
        """Preload common permissions for a user."""
        preloaded_count = 0
        
        try:
            # Use batch query for better performance
            query_optimizer = PermissionQueryOptimizer(self.config)
            query = query_optimizer.get_batch_permission_check_query(self.common_permissions)
            
            # Prepare parameters
            params = {
                "user_id": user_id,
                "tenant_id": tenant_id
            }
            for i, perm in enumerate(self.common_permissions):
                params[f"perm_{i}"] = perm
            
            # Execute optimized query
            result = db.execute(text(query), params)
            user_permissions = {row.name: True for row in result}
            
            # Cache results
            for permission in self.common_permissions:
                has_permission = permission in user_permissions
                permission_cache.set_permission(
                    user_id, permission, has_permission, tenant_id=tenant_id
                )
                preloaded_count += 1
            
            self._preload_stats[str(user_id)] = preloaded_count
            logger.debug(f"Preloaded {preloaded_count} permissions for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to preload permissions for user {user_id}: {e}")
        
        return preloaded_count
    
    def get_preload_statistics(self) -> Dict[str, Any]:
        """Get preload statistics."""
        return {
            "total_users_preloaded": len(self._preload_stats),
            "total_permissions_preloaded": sum(self._preload_stats.values()),
            "average_permissions_per_user": (
                sum(self._preload_stats.values()) / len(self._preload_stats)
                if self._preload_stats else 0
            ),
            "common_permissions_count": len(self.common_permissions)
        }


class PerformanceMonitor:
    """Monitors permission check performance and provides optimization insights."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.metrics_buffer = deque(maxlen=10000)  # Keep last 10k metrics
        self._lock = threading.Lock()
        self._stats_cache = None
        self._stats_cache_time = None
        self._cache_ttl = 30  # 30 seconds cache for stats
    
    def record_permission_check(
        self,
        user_id: UUID,
        permission_name: str,
        response_time_ms: float,
        cache_hit: bool,
        tenant_id: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        """Record a permission check metric."""
        if not self.config.metrics_collection_enabled:
            return
        
        metric = PermissionCheckMetrics(
            user_id=user_id,
            permission_name=permission_name,
            response_time_ms=response_time_ms,
            cache_hit=cache_hit,
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            resource_id=resource_id
        )
        
        with self._lock:
            self.metrics_buffer.append(metric)
            
        # Check for performance alerts
        if (self.config.performance_alerts_enabled and 
            response_time_ms > self.config.target_response_time_ms):
            self._trigger_performance_alert(metric)
    
    def get_performance_stats(self, time_window_minutes: int = 60) -> PerformanceStats:
        """Get performance statistics for the specified time window."""
        current_time = datetime.utcnow()
        
        # Check cache first
        if (self._stats_cache and self._stats_cache_time and
            (current_time - self._stats_cache_time).seconds < self._cache_ttl):
            return self._stats_cache
        
        cutoff_time = current_time - timedelta(minutes=time_window_minutes)
        
        with self._lock:
            # Filter metrics within time window
            recent_metrics = [
                m for m in self.metrics_buffer
                if m.timestamp >= cutoff_time
            ]
        
        if not recent_metrics:
            return PerformanceStats()
        
        # Calculate statistics
        response_times = [m.response_time_ms for m in recent_metrics]
        cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
        checks_under_10ms = sum(1 for t in response_times if t < self.config.target_response_time_ms)
        checks_over_10ms = len(response_times) - checks_under_10ms
        
        stats = PerformanceStats(
            total_checks=len(recent_metrics),
            cache_hits=cache_hits,
            avg_response_time_ms=statistics.mean(response_times),
            p95_response_time_ms=statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0],
            p99_response_time_ms=statistics.quantiles(response_times, n=100)[98] if len(response_times) > 1 else response_times[0],
            checks_under_10ms=checks_under_10ms,
            checks_over_10ms=checks_over_10ms
        )
        stats.update_compliance_rate()
        
        # Cache the results
        self._stats_cache = stats
        self._stats_cache_time = current_time
        
        return stats
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations."""
        stats = self.get_performance_stats()
        recommendations = []
        
        # Check target compliance
        if stats.target_compliance_rate < 95.0:
            recommendations.append(
                f"Target compliance rate is {stats.target_compliance_rate:.1f}%. "
                f"Consider enabling more aggressive caching or query optimization."
            )
        
        # Check cache hit rate
        cache_hit_rate = (stats.cache_hits / stats.total_checks * 100) if stats.total_checks > 0 else 0
        if cache_hit_rate < 90.0:
            recommendations.append(
                f"Cache hit rate is {cache_hit_rate:.1f}%. "
                f"Consider preloading more common permissions or increasing cache TTL."
            )
        
        # Check average response time
        if stats.avg_response_time_ms > self.config.target_response_time_ms * 0.8:
            recommendations.append(
                f"Average response time is {stats.avg_response_time_ms:.2f}ms. "
                f"Consider enabling query optimization or increasing memory cache size."
            )
        
        # Check P95 response time
        if stats.p95_response_time_ms > self.config.target_response_time_ms:
            recommendations.append(
                f"P95 response time is {stats.p95_response_time_ms:.2f}ms. "
                f"Consider database index optimization or connection pooling."
            )
        
        if not recommendations:
            recommendations.append("Performance is meeting all targets. No optimizations needed.")
        
        return recommendations
    
    def _trigger_performance_alert(self, metric: PermissionCheckMetrics):
        """Trigger performance alert for slow permission check."""
        logger.warning(
            f"Slow permission check detected: {metric.response_time_ms:.2f}ms "
            f"for user {metric.user_id}, permission {metric.permission_name}"
        )


class PermissionPerformanceOptimizer:
    """Main performance optimizer for permission checking system."""
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        self.config = config or OptimizationConfig()
        self.query_optimizer = PermissionQueryOptimizer(self.config)
        self.preloader = PermissionPreloader(self.config)
        self.monitor = PerformanceMonitor(self.config)
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="perm_opt")
        self._optimization_enabled = True
    
    async def optimize_permission_check(
        self,
        user_id: UUID,
        permission_name: str,
        permission_cache,
        rbac_controller,
        db: Session,
        tenant_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None
    ) -> Tuple[bool, float]:
        """
        Perform optimized permission check with performance monitoring.
        
        Returns:
            Tuple of (permission_result, response_time_ms)
        """
        start_time = time.perf_counter()
        cache_hit = False
        result = False
        
        try:
            # 1. Fast path: Check memory cache first
            if tenant_id:
                cached_result = permission_cache.get_permission(
                    user_id, permission_name, resource_id, resource_type, tenant_id
                )
                if cached_result is not None:
                    cache_hit = True
                    result = cached_result
                    response_time_ms = (time.perf_counter() - start_time) * 1000
                    
                    # Record metrics
                    self.monitor.record_permission_check(
                        user_id, permission_name, response_time_ms, cache_hit, tenant_id, resource_id
                    )
                    
                    return result, response_time_ms
            
            # 2. Optimized database check
            if self.config.query_optimization_enabled:
                result = await self._optimized_permission_check(
                    user_id, permission_name, resource_id, resource_type, tenant_id, db
                )
            else:
                # Fallback to standard check
                result = rbac_controller._check_permission_through_roles(
                    user_id, permission_name, resource_id, resource_type, db
                )
            
            # 3. Cache the result
            if tenant_id:
                permission_cache.set_permission(
                    user_id, permission_name, result, resource_id, resource_type, tenant_id
                )
            
            response_time_ms = (time.perf_counter() - start_time) * 1000
            
            # 4. Record metrics
            self.monitor.record_permission_check(
                user_id, permission_name, response_time_ms, cache_hit, tenant_id, resource_id
            )
            
            # 5. Trigger preloading if this is a new user
            if not cache_hit and self.config.cache_preload_enabled:
                asyncio.create_task(
                    self._maybe_preload_user_permissions(
                        user_id, tenant_id, permission_cache, db, rbac_controller
                    )
                )
            
            return result, response_time_ms
            
        except Exception as e:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Optimized permission check failed: {e}")
            
            # Record failed check
            self.monitor.record_permission_check(
                user_id, permission_name, response_time_ms, cache_hit, tenant_id, resource_id
            )
            
            return False, response_time_ms
    
    async def _optimized_permission_check(
        self,
        user_id: UUID,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        tenant_id: str,
        db: Session
    ) -> bool:
        """Perform optimized database permission check."""
        try:
            # Use optimized query
            query = """
            SELECT COUNT(*) as has_permission
            FROM permissions p
            INNER JOIN role_permissions rp ON p.id = rp.permission_id
            INNER JOIN user_roles ur ON rp.role_id = ur.role_id
            INNER JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = :user_id 
            AND r.tenant_id = :tenant_id 
            AND r.is_active = true
            AND p.name = :permission_name
            LIMIT 1
            """
            
            params = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "permission_name": permission_name
            }
            
            result = db.execute(text(query), params)
            row = result.fetchone()
            
            return row.has_permission > 0 if row else False
            
        except Exception as e:
            logger.error(f"Optimized permission check query failed: {e}")
            return False
    
    async def _maybe_preload_user_permissions(
        self,
        user_id: UUID,
        tenant_id: str,
        permission_cache,
        db: Session,
        rbac_controller
    ):
        """Maybe preload user permissions if not already done recently."""
        try:
            # Check if we've preloaded for this user recently
            cache_key = f"preload_{user_id}_{tenant_id}"
            if hasattr(permission_cache, 'get_permission'):
                recent_preload = permission_cache.get_permission(
                    user_id, "__preload_marker__", tenant_id=tenant_id
                )
                if recent_preload is not None:
                    return  # Already preloaded recently
            
            # Preload common permissions
            await self.preloader.preload_user_permissions(
                user_id, tenant_id, permission_cache, db, rbac_controller
            )
            
            # Mark as preloaded
            permission_cache.set_permission(
                user_id, "__preload_marker__", True, tenant_id=tenant_id, ttl=300  # 5 minutes
            )
            
        except Exception as e:
            logger.error(f"Failed to preload permissions for user {user_id}: {e}")
    
    async def batch_optimize_permission_checks(
        self,
        user_id: UUID,
        permissions: List[str],
        permission_cache,
        rbac_controller,
        db: Session,
        tenant_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None
    ) -> Tuple[Dict[str, bool], float]:
        """
        Perform batch optimized permission checks.
        
        Returns:
            Tuple of (results_dict, total_response_time_ms)
        """
        start_time = time.perf_counter()
        results = {}
        cache_hits = 0
        
        try:
            # 1. Check cache for all permissions first
            uncached_permissions = []
            for permission in permissions:
                if tenant_id:
                    cached_result = permission_cache.get_permission(
                        user_id, permission, resource_id, resource_type, tenant_id
                    )
                    if cached_result is not None:
                        results[permission] = cached_result
                        cache_hits += 1
                    else:
                        uncached_permissions.append(permission)
                else:
                    uncached_permissions.append(permission)
            
            # 2. Batch check uncached permissions
            if uncached_permissions and self.config.batch_processing_enabled:
                batch_results = await self._batch_permission_check(
                    user_id, uncached_permissions, tenant_id, db
                )
                results.update(batch_results)
                
                # Cache the results
                if tenant_id:
                    for permission, result in batch_results.items():
                        permission_cache.set_permission(
                            user_id, permission, result, resource_id, resource_type, tenant_id
                        )
            
            total_response_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Record batch metrics
            for permission in permissions:
                self.monitor.record_permission_check(
                    user_id, permission, total_response_time_ms / len(permissions),
                    permission in results and cache_hits > 0, tenant_id, resource_id
                )
            
            return results, total_response_time_ms
            
        except Exception as e:
            total_response_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Batch permission check failed: {e}")
            
            # Return False for all permissions on error
            return {perm: False for perm in permissions}, total_response_time_ms
    
    async def _batch_permission_check(
        self,
        user_id: UUID,
        permissions: List[str],
        tenant_id: str,
        db: Session
    ) -> Dict[str, bool]:
        """Perform batch permission check using optimized query."""
        try:
            query = self.query_optimizer.get_batch_permission_check_query(permissions)
            
            params = {
                "user_id": user_id,
                "tenant_id": tenant_id
            }
            for i, perm in enumerate(permissions):
                params[f"perm_{i}"] = perm
            
            result = db.execute(text(query), params)
            user_permissions = {row.name: True for row in result}
            
            # Return results for all requested permissions
            return {perm: perm in user_permissions for perm in permissions}
            
        except Exception as e:
            logger.error(f"Batch permission check query failed: {e}")
            return {perm: False for perm in permissions}
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        stats = self.monitor.get_performance_stats()
        preload_stats = self.preloader.get_preload_statistics()
        recommendations = self.monitor.get_optimization_recommendations()
        
        return {
            "performance_stats": {
                "total_checks": stats.total_checks,
                "cache_hit_rate": (stats.cache_hits / stats.total_checks * 100) if stats.total_checks > 0 else 0,
                "avg_response_time_ms": stats.avg_response_time_ms,
                "p95_response_time_ms": stats.p95_response_time_ms,
                "p99_response_time_ms": stats.p99_response_time_ms,
                "target_compliance_rate": stats.target_compliance_rate,
                "checks_under_10ms": stats.checks_under_10ms,
                "checks_over_10ms": stats.checks_over_10ms
            },
            "preload_stats": preload_stats,
            "optimization_config": {
                "target_response_time_ms": self.config.target_response_time_ms,
                "cache_preload_enabled": self.config.cache_preload_enabled,
                "query_optimization_enabled": self.config.query_optimization_enabled,
                "batch_processing_enabled": self.config.batch_processing_enabled
            },
            "recommendations": recommendations,
            "status": "optimal" if stats.target_compliance_rate >= 95.0 else "needs_optimization"
        }
    
    def enable_optimization(self):
        """Enable performance optimization."""
        self._optimization_enabled = True
        logger.info("Permission performance optimization enabled")
    
    def disable_optimization(self):
        """Disable performance optimization."""
        self._optimization_enabled = False
        logger.info("Permission performance optimization disabled")
    
    def is_optimization_enabled(self) -> bool:
        """Check if optimization is enabled."""
        return self._optimization_enabled


# Global optimizer instance
_performance_optimizer = None


def get_permission_performance_optimizer() -> PermissionPerformanceOptimizer:
    """Get the global permission performance optimizer instance."""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PermissionPerformanceOptimizer()
    return _performance_optimizer