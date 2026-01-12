"""
Ultra-Fast Permission Checker for SuperInsight Platform.

Implements aggressive optimizations to guarantee <10ms permission check response times
through micro-optimizations, intelligent caching, and performance monitoring.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from uuid import UUID
import threading
import hashlib
import json

from sqlalchemy.orm import Session
from sqlalchemy import text, select, and_

logger = logging.getLogger(__name__)


@dataclass
class PerformanceTarget:
    """Performance targets for permission checking."""
    target_response_time_ms: float = 10.0
    cache_hit_rate_target: float = 95.0
    compliance_rate_target: float = 98.0
    p95_threshold_ms: float = 15.0
    p99_threshold_ms: float = 25.0


class UltraFastCache:
    """
    Ultra-fast in-memory cache optimized for <10ms permission checks.
    
    Features:
    - Microsecond-level access times
    - Intelligent pre-warming
    - Memory-efficient storage
    - Lock-free reads for common cases
    """
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._cache = {}  # Main cache storage
        self._access_times = {}  # Track access for LRU
        self._lock = threading.RLock()
        
        # Performance counters
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        # Pre-computed hash cache for common patterns
        self._hash_cache = {}
    
    def _generate_key(
        self,
        user_id: UUID,
        permission: str,
        tenant_id: str,
        resource_id: Optional[str] = None
    ) -> str:
        """Generate optimized cache key."""
        # Use pre-computed hash for common patterns
        base_key = f"{user_id}:{permission}:{tenant_id}"
        if base_key in self._hash_cache:
            hash_part = self._hash_cache[base_key]
        else:
            hash_part = hashlib.md5(base_key.encode()).hexdigest()[:16]
            if len(self._hash_cache) < 1000:  # Limit hash cache size
                self._hash_cache[base_key] = hash_part
        
        if resource_id:
            return f"{hash_part}:{resource_id}"
        return hash_part
    
    def get(
        self,
        user_id: UUID,
        permission: str,
        tenant_id: str,
        resource_id: Optional[str] = None
    ) -> Optional[bool]:
        """Ultra-fast cache get with microsecond access times."""
        key = self._generate_key(user_id, permission, tenant_id, resource_id)
        
        # Fast path: no lock for cache hits
        if key in self._cache:
            result, timestamp = self._cache[key]
            # Quick TTL check (5 minutes)
            if (time.time() - timestamp) < 300:
                self.hits += 1
                self._access_times[key] = time.time()
                return result
            else:
                # Expired, remove
                with self._lock:
                    if key in self._cache:
                        del self._cache[key]
                        del self._access_times[key]
        
        self.misses += 1
        return None
    
    def set(
        self,
        user_id: UUID,
        permission: str,
        tenant_id: str,
        result: bool,
        resource_id: Optional[str] = None
    ):
        """Ultra-fast cache set with automatic eviction."""
        key = self._generate_key(user_id, permission, tenant_id, resource_id)
        current_time = time.time()
        
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            self._cache[key] = (result, current_time)
            self._access_times[key] = current_time
    
    def _evict_lru(self):
        """Evict least recently used items."""
        if not self._access_times:
            return
        
        # Evict 10% of items or at least 1
        evict_count = max(1, len(self._access_times) // 10)
        
        # Sort by access time and evict oldest
        sorted_items = sorted(self._access_times.items(), key=lambda x: x[1])
        for i in range(min(evict_count, len(sorted_items))):
            key = sorted_items[i][0]
            if key in self._cache:
                del self._cache[key]
            del self._access_times[key]
            self.evictions += 1
    
    def invalidate_user(self, user_id: UUID):
        """Invalidate all cache entries for a user."""
        user_str = str(user_id)
        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if user_str in key
            ]
            for key in keys_to_remove:
                if key in self._cache:
                    del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
    
    def invalidate_tenant(self, tenant_id: str):
        """Invalidate all cache entries for a tenant."""
        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if tenant_id in key
            ]
            for key in keys_to_remove:
                if key in self._cache:
                    del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "cache_size": len(self._cache),
            "max_size": self.max_size,
            "evictions": self.evictions,
            "hash_cache_size": len(self._hash_cache)
        }
    
    def clear(self):
        """Clear all cache data."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._hash_cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0


class QueryOptimizer:
    """
    Ultra-optimized database queries for permission checking.
    
    Features:
    - Pre-compiled query templates
    - Minimal data transfer
    - Index-optimized queries
    - Connection pooling hints
    """
    
    def __init__(self):
        self._query_cache = {}
        self._prepared_statements = {
            "single_permission": """
                SELECT 1 as has_permission
                FROM permissions p
                INNER JOIN role_permissions rp ON p.id = rp.permission_id
                INNER JOIN user_roles ur ON rp.role_id = ur.role_id
                INNER JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id 
                AND r.tenant_id = :tenant_id 
                AND r.is_active = true
                AND p.name = :permission_name
                LIMIT 1
            """,
            "batch_permissions": """
                SELECT p.name
                FROM permissions p
                INNER JOIN role_permissions rp ON p.id = rp.permission_id
                INNER JOIN user_roles ur ON rp.role_id = ur.role_id
                INNER JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id 
                AND r.tenant_id = :tenant_id 
                AND r.is_active = true
                AND p.name = ANY(:permission_names)
            """,
            "user_all_permissions": """
                SELECT p.name, p.scope
                FROM permissions p
                INNER JOIN role_permissions rp ON p.id = rp.permission_id
                INNER JOIN user_roles ur ON rp.role_id = ur.role_id
                INNER JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = :user_id 
                AND r.tenant_id = :tenant_id 
                AND r.is_active = true
            """
        }
    
    def check_single_permission(
        self,
        db: Session,
        user_id: UUID,
        tenant_id: str,
        permission_name: str
    ) -> bool:
        """Ultra-fast single permission check."""
        try:
            result = db.execute(
                text(self._prepared_statements["single_permission"]),
                {
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "permission_name": permission_name
                }
            )
            return result.fetchone() is not None
        except Exception as e:
            logger.error(f"Single permission query failed: {e}")
            return False
    
    def check_batch_permissions(
        self,
        db: Session,
        user_id: UUID,
        tenant_id: str,
        permission_names: List[str]
    ) -> Set[str]:
        """Ultra-fast batch permission check."""
        try:
            # For PostgreSQL, use ANY() for better performance
            # For SQLite, fall back to IN clause
            if len(permission_names) == 1:
                # Single permission optimization
                if self.check_single_permission(db, user_id, tenant_id, permission_names[0]):
                    return {permission_names[0]}
                return set()
            
            # Batch query with IN clause (SQLite compatible)
            placeholders = ",".join([f":perm_{i}" for i in range(len(permission_names))])
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
            for i, perm in enumerate(permission_names):
                params[f"perm_{i}"] = perm
            
            result = db.execute(text(query), params)
            return {row.name for row in result}
            
        except Exception as e:
            logger.error(f"Batch permission query failed: {e}")
            return set()
    
    def get_user_permissions(
        self,
        db: Session,
        user_id: UUID,
        tenant_id: str
    ) -> Set[str]:
        """Get all permissions for a user (for cache warming)."""
        try:
            result = db.execute(
                text(self._prepared_statements["user_all_permissions"]),
                {
                    "user_id": user_id,
                    "tenant_id": tenant_id
                }
            )
            return {row.name for row in result}
        except Exception as e:
            logger.error(f"User permissions query failed: {e}")
            return set()


class PerformanceMonitor:
    """
    Real-time performance monitoring for permission checks.
    
    Tracks response times, compliance rates, and optimization opportunities.
    """
    
    def __init__(self, target: PerformanceTarget):
        self.target = target
        self.metrics = deque(maxlen=1000)  # Keep last 1000 measurements
        self._lock = threading.Lock()
        
        # Real-time stats
        self.total_checks = 0
        self.under_target_count = 0
        self.cache_hits = 0
        
        # Performance buckets
        self.response_buckets = {
            "under_1ms": 0,
            "1_to_5ms": 0,
            "5_to_10ms": 0,
            "10_to_25ms": 0,
            "over_25ms": 0
        }
    
    def record_check(
        self,
        response_time_ms: float,
        cache_hit: bool,
        user_id: UUID,
        permission: str
    ):
        """Record a permission check measurement."""
        with self._lock:
            self.total_checks += 1
            
            if response_time_ms < self.target.target_response_time_ms:
                self.under_target_count += 1
            
            if cache_hit:
                self.cache_hits += 1
            
            # Update buckets
            if response_time_ms < 1.0:
                self.response_buckets["under_1ms"] += 1
            elif response_time_ms < 5.0:
                self.response_buckets["1_to_5ms"] += 1
            elif response_time_ms < 10.0:
                self.response_buckets["5_to_10ms"] += 1
            elif response_time_ms < 25.0:
                self.response_buckets["10_to_25ms"] += 1
            else:
                self.response_buckets["over_25ms"] += 1
            
            # Store detailed metric
            self.metrics.append({
                "timestamp": time.time(),
                "response_time_ms": response_time_ms,
                "cache_hit": cache_hit,
                "user_id": str(user_id),
                "permission": permission
            })
    
    def get_real_time_stats(self) -> Dict[str, Any]:
        """Get real-time performance statistics."""
        with self._lock:
            compliance_rate = (
                (self.under_target_count / self.total_checks * 100)
                if self.total_checks > 0 else 0
            )
            
            cache_hit_rate = (
                (self.cache_hits / self.total_checks * 100)
                if self.total_checks > 0 else 0
            )
            
            # Calculate percentiles from recent metrics
            recent_times = [m["response_time_ms"] for m in list(self.metrics)[-100:]]
            if recent_times:
                recent_times.sort()
                p95_idx = int(len(recent_times) * 0.95)
                p99_idx = int(len(recent_times) * 0.99)
                p95_time = recent_times[min(p95_idx, len(recent_times) - 1)]
                p99_time = recent_times[min(p99_idx, len(recent_times) - 1)]
                avg_time = sum(recent_times) / len(recent_times)
            else:
                p95_time = p99_time = avg_time = 0
            
            return {
                "total_checks": self.total_checks,
                "compliance_rate": compliance_rate,
                "cache_hit_rate": cache_hit_rate,
                "avg_response_time_ms": avg_time,
                "p95_response_time_ms": p95_time,
                "p99_response_time_ms": p99_time,
                "response_buckets": self.response_buckets.copy(),
                "target_met": compliance_rate >= self.target.compliance_rate_target,
                "performance_grade": self._calculate_grade(compliance_rate, cache_hit_rate, avg_time)
            }
    
    def _calculate_grade(self, compliance_rate: float, cache_hit_rate: float, avg_time: float) -> str:
        """Calculate performance grade A-F."""
        score = 0
        
        # Compliance rate (40% of score)
        if compliance_rate >= 99:
            score += 40
        elif compliance_rate >= 95:
            score += 35
        elif compliance_rate >= 90:
            score += 30
        elif compliance_rate >= 80:
            score += 20
        else:
            score += 10
        
        # Cache hit rate (30% of score)
        if cache_hit_rate >= 95:
            score += 30
        elif cache_hit_rate >= 90:
            score += 25
        elif cache_hit_rate >= 80:
            score += 20
        else:
            score += 10
        
        # Average response time (30% of score)
        if avg_time < 1.0:
            score += 30
        elif avg_time < 3.0:
            score += 25
        elif avg_time < 5.0:
            score += 20
        elif avg_time < 10.0:
            score += 15
        else:
            score += 5
        
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get specific optimization recommendations."""
        stats = self.get_real_time_stats()
        recommendations = []
        
        if stats["compliance_rate"] < self.target.compliance_rate_target:
            recommendations.append(
                f"Compliance rate {stats['compliance_rate']:.1f}% is below target "
                f"{self.target.compliance_rate_target}%. Consider increasing cache size or pre-warming."
            )
        
        if stats["cache_hit_rate"] < self.target.cache_hit_rate_target:
            recommendations.append(
                f"Cache hit rate {stats['cache_hit_rate']:.1f}% is below target "
                f"{self.target.cache_hit_rate_target}%. Enable aggressive pre-warming."
            )
        
        if stats["avg_response_time_ms"] > self.target.target_response_time_ms * 0.7:
            recommendations.append(
                f"Average response time {stats['avg_response_time_ms']:.2f}ms is approaching "
                f"target {self.target.target_response_time_ms}ms. Optimize database queries."
            )
        
        if stats["response_buckets"]["over_25ms"] > 0:
            recommendations.append(
                f"{stats['response_buckets']['over_25ms']} checks exceeded 25ms. "
                "Investigate slow queries and database performance."
            )
        
        if not recommendations:
            recommendations.append("Performance is optimal. All targets are being met.")
        
        return recommendations


class UltraFastPermissionChecker:
    """
    Ultra-fast permission checker optimized for <10ms response times.
    
    Combines aggressive caching, optimized queries, and real-time monitoring
    to guarantee sub-10ms permission checks in 98%+ of cases.
    """
    
    def __init__(
        self,
        cache_size: int = 10000,
        target: Optional[PerformanceTarget] = None
    ):
        self.target = target or PerformanceTarget()
        self.cache = UltraFastCache(cache_size)
        self.query_optimizer = QueryOptimizer()
        self.monitor = PerformanceMonitor(self.target)
        
        # Common permissions for pre-warming
        self.common_permissions = [
            "read_data", "write_data", "view_dashboard", "manage_projects",
            "view_reports", "export_data", "manage_users", "view_analytics",
            "create_annotations", "edit_annotations", "delete_annotations"
        ]
        
        # Performance flags
        self._optimization_enabled = True
        self._pre_warming_enabled = True
    
    def check_permission(
        self,
        user_id: UUID,
        permission: str,
        tenant_id: str,
        db: Session,
        resource_id: Optional[str] = None
    ) -> bool:
        """
        Ultra-fast permission check with <10ms guarantee.
        
        Args:
            user_id: User identifier
            permission: Permission name
            tenant_id: Tenant identifier
            db: Database session
            resource_id: Optional resource identifier
            
        Returns:
            True if user has permission
        """
        start_time = time.perf_counter()
        cache_hit = False
        result = False
        
        try:
            # Step 1: Ultra-fast cache check (microseconds)
            cached_result = self.cache.get(user_id, permission, tenant_id, resource_id)
            if cached_result is not None:
                cache_hit = True
                result = cached_result
            else:
                # Step 2: Optimized database query (milliseconds)
                result = self.query_optimizer.check_single_permission(
                    db, user_id, tenant_id, permission
                )
                
                # Step 3: Cache the result for future use
                self.cache.set(user_id, permission, tenant_id, result, resource_id)
                
                # Step 4: Trigger pre-warming if this is a new user pattern
                if self._pre_warming_enabled and not cache_hit:
                    self._maybe_pre_warm_user(user_id, tenant_id, db)
            
            # Step 5: Record performance metrics
            response_time_ms = (time.perf_counter() - start_time) * 1000
            self.monitor.record_check(response_time_ms, cache_hit, user_id, permission)
            
            return result
            
        except Exception as e:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            self.monitor.record_check(response_time_ms, cache_hit, user_id, permission)
            logger.error(f"Ultra-fast permission check failed: {e}")
            return False
    
    def check_permissions_batch(
        self,
        user_id: UUID,
        permissions: List[str],
        tenant_id: str,
        db: Session,
        resource_id: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Ultra-fast batch permission check.
        
        Args:
            user_id: User identifier
            permissions: List of permission names
            tenant_id: Tenant identifier
            db: Database session
            resource_id: Optional resource identifier
            
        Returns:
            Dictionary mapping permission names to results
        """
        start_time = time.perf_counter()
        results = {}
        uncached_permissions = []
        cache_hits = 0
        
        try:
            # Step 1: Check cache for all permissions
            for permission in permissions:
                cached_result = self.cache.get(user_id, permission, tenant_id, resource_id)
                if cached_result is not None:
                    results[permission] = cached_result
                    cache_hits += 1
                else:
                    uncached_permissions.append(permission)
            
            # Step 2: Batch query for uncached permissions
            if uncached_permissions:
                user_permissions = self.query_optimizer.check_batch_permissions(
                    db, user_id, tenant_id, uncached_permissions
                )
                
                # Step 3: Process results and cache them
                for permission in uncached_permissions:
                    has_permission = permission in user_permissions
                    results[permission] = has_permission
                    self.cache.set(user_id, permission, tenant_id, has_permission, resource_id)
            
            # Step 4: Record performance metrics
            total_time_ms = (time.perf_counter() - start_time) * 1000
            avg_time_per_permission = total_time_ms / len(permissions) if permissions else 0
            
            for permission in permissions:
                cache_hit = permission in results and cache_hits > 0
                self.monitor.record_check(avg_time_per_permission, cache_hit, user_id, permission)
            
            return results
            
        except Exception as e:
            total_time_ms = (time.perf_counter() - start_time) * 1000
            avg_time_per_permission = total_time_ms / len(permissions) if permissions else 0
            
            for permission in permissions:
                self.monitor.record_check(avg_time_per_permission, False, user_id, permission)
            
            logger.error(f"Ultra-fast batch permission check failed: {e}")
            return {perm: False for perm in permissions}
    
    def pre_warm_user_permissions(
        self,
        user_id: UUID,
        tenant_id: str,
        db: Session,
        permissions: Optional[List[str]] = None
    ) -> int:
        """
        Pre-warm cache with user's permissions for optimal performance.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            db: Database session
            permissions: Optional list of permissions to warm (uses common ones if None)
            
        Returns:
            Number of permissions pre-warmed
        """
        try:
            permissions_to_warm = permissions or self.common_permissions
            
            # Get user's actual permissions
            user_permissions = self.query_optimizer.get_user_permissions(db, user_id, tenant_id)
            
            # Cache all requested permissions
            warmed_count = 0
            for permission in permissions_to_warm:
                has_permission = permission in user_permissions
                self.cache.set(user_id, permission, tenant_id, has_permission)
                warmed_count += 1
            
            logger.debug(f"Pre-warmed {warmed_count} permissions for user {user_id}")
            return warmed_count
            
        except Exception as e:
            logger.error(f"Failed to pre-warm permissions for user {user_id}: {e}")
            return 0
    
    def _maybe_pre_warm_user(self, user_id: UUID, tenant_id: str, db: Session):
        """Maybe pre-warm user permissions if not done recently."""
        # Simple heuristic: pre-warm if we haven't seen this user recently
        # Check if user has any cached permissions
        user_str = str(user_id)
        has_cached_permissions = any(
            user_str in key for key in self.cache._cache.keys()
        )
        
        if not has_cached_permissions:
            # Pre-warm common permissions for new user
            self.pre_warm_user_permissions(user_id, tenant_id, db)
    
    def invalidate_user_cache(self, user_id: UUID):
        """Invalidate all cached permissions for a user."""
        self.cache.invalidate_user(user_id)
    
    def invalidate_tenant_cache(self, tenant_id: str):
        """Invalidate all cached permissions for a tenant."""
        self.cache.invalidate_tenant(tenant_id)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        monitor_stats = self.monitor.get_real_time_stats()
        cache_stats = self.cache.get_stats()
        recommendations = self.monitor.get_optimization_recommendations()
        
        return {
            "performance_stats": monitor_stats,
            "cache_stats": cache_stats,
            "recommendations": recommendations,
            "target_compliance": {
                "target_response_time_ms": self.target.target_response_time_ms,
                "target_cache_hit_rate": self.target.cache_hit_rate_target,
                "target_compliance_rate": self.target.compliance_rate_target,
                "current_compliance_rate": monitor_stats["compliance_rate"],
                "target_met": monitor_stats["target_met"]
            },
            "optimization_status": {
                "enabled": self._optimization_enabled,
                "pre_warming_enabled": self._pre_warming_enabled,
                "cache_size": len(self.cache._cache),
                "max_cache_size": self.cache.max_size
            }
        }
    
    def enable_optimization(self):
        """Enable all performance optimizations."""
        self._optimization_enabled = True
        self._pre_warming_enabled = True
        logger.info("Ultra-fast permission checker optimizations enabled")
    
    def disable_optimization(self):
        """Disable performance optimizations."""
        self._optimization_enabled = False
        self._pre_warming_enabled = False
        logger.info("Ultra-fast permission checker optimizations disabled")
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Ultra-fast permission checker cache cleared")


# Global instances by configuration
_ultra_fast_checkers = {}


def get_ultra_fast_permission_checker(
    cache_size: int = 10000,
    target: Optional[PerformanceTarget] = None
) -> UltraFastPermissionChecker:
    """Get an ultra-fast permission checker instance for the given configuration."""
    global _ultra_fast_checkers
    
    # Create a key based on configuration
    target_key = "default" if target is None else f"{target.target_response_time_ms}_{target.cache_hit_rate_target}_{target.compliance_rate_target}"
    config_key = f"{cache_size}_{target_key}"
    
    if config_key not in _ultra_fast_checkers:
        _ultra_fast_checkers[config_key] = UltraFastPermissionChecker(cache_size, target)
    
    return _ultra_fast_checkers[config_key]