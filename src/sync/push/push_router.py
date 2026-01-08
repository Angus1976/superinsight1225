"""
Push Router.

Handles intelligent routing and load balancing for push operations:
- Route selection based on conditions
- Load balancing across multiple targets
- Failover and circuit breaker patterns
- Performance optimization
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

from .target_manager import PushTargetConfig, PushTargetManager, LoadBalancingStrategy
from .incremental_push import ChangeRecord, PushResult

logger = logging.getLogger(__name__)


class RouteMetrics(BaseModel):
    """Metrics for a specific route."""
    route_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time_ms: float = 0.0
    average_response_time_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    error_rate: float = 0.0


class TargetMetrics(BaseModel):
    """Metrics for a specific target."""
    target_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time_ms: float = 0.0
    average_response_time_ms: float = 0.0
    active_connections: int = 0
    last_request_time: Optional[datetime] = None
    error_rate: float = 0.0


class PushContext(BaseModel):
    """Context information for push routing decisions."""
    tenant_id: str
    table_name: Optional[str] = None
    operation: Optional[str] = None  # INSERT, UPDATE, DELETE
    record_count: int = 0
    data_size_bytes: int = 0
    priority: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RoutingDecision(BaseModel):
    """Result of routing decision."""
    selected_targets: List[PushTargetConfig]
    route_id: Optional[str] = None
    strategy: str
    reason: str
    fallback_used: bool = False
    estimated_completion_time: Optional[datetime] = None


class PushRouter:
    """
    Intelligent push router with load balancing and failover.
    
    Provides advanced routing capabilities including:
    - Condition-based route selection
    - Multiple load balancing strategies
    - Circuit breaker pattern
    - Performance-based routing
    - Automatic failover
    """
    
    def __init__(self, target_manager: PushTargetManager):
        self.target_manager = target_manager
        self._route_metrics: Dict[str, RouteMetrics] = {}
        self._target_metrics: Dict[str, TargetMetrics] = {}
        self._routing_cache: Dict[str, RoutingDecision] = {}
        self._cache_ttl_seconds = 300  # 5 minutes
        
    async def route_push(
        self,
        context: PushContext,
        changes: List[ChangeRecord]
    ) -> RoutingDecision:
        """
        Route a push operation to appropriate targets.
        
        Args:
            context: Push context information
            changes: List of change records to push
            
        Returns:
            Routing decision with selected targets
        """
        try:
            # Check cache first
            cache_key = self._generate_cache_key(context)
            cached_decision = self._routing_cache.get(cache_key)
            
            if cached_decision and self._is_cache_valid(cached_decision):
                logger.debug(f"Using cached routing decision for {cache_key}")
                return cached_decision
            
            # Select targets based on context
            selected_targets = await self.target_manager.select_targets(
                context.tenant_id, 
                {
                    "table_name": context.table_name,
                    "operation": context.operation,
                    "data_size": context.data_size_bytes,
                    "record_count": context.record_count,
                    "priority": context.priority
                }
            )
            
            if not selected_targets:
                # No targets available, try fallback
                selected_targets = await self._select_fallback_targets(context)
                fallback_used = True
            else:
                fallback_used = False
            
            # Apply intelligent routing optimizations
            optimized_targets = await self._optimize_target_selection(
                selected_targets, context, changes
            )
            
            # Determine routing strategy
            strategy = self._determine_routing_strategy(optimized_targets, context)
            
            # Create routing decision
            decision = RoutingDecision(
                selected_targets=optimized_targets,
                strategy=strategy,
                reason=self._generate_routing_reason(optimized_targets, context, fallback_used),
                fallback_used=fallback_used,
                estimated_completion_time=self._estimate_completion_time(optimized_targets, changes)
            )
            
            # Cache the decision
            self._routing_cache[cache_key] = decision
            
            logger.info(
                f"Routed push to {len(optimized_targets)} targets using {strategy} strategy"
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error routing push: {e}")
            # Return empty decision as fallback
            return RoutingDecision(
                selected_targets=[],
                strategy="error",
                reason=f"Routing failed: {str(e)}"
            )
    
    async def _optimize_target_selection(
        self,
        targets: List[PushTargetConfig],
        context: PushContext,
        changes: List[ChangeRecord]
    ) -> List[PushTargetConfig]:
        """
        Optimize target selection based on performance metrics and load.
        
        Args:
            targets: Initial target selection
            context: Push context
            changes: Change records
            
        Returns:
            Optimized list of targets
        """
        if not targets:
            return targets
        
        optimized_targets = []
        
        for target in targets:
            # Check if target is healthy and available
            if not await self._is_target_available(target):
                logger.warning(f"Target {target.target_id} is not available, skipping")
                continue
            
            # Check capacity and load
            if not await self._has_sufficient_capacity(target, context, changes):
                logger.warning(f"Target {target.target_id} at capacity, skipping")
                continue
            
            # Check performance criteria
            if not await self._meets_performance_criteria(target, context):
                logger.warning(f"Target {target.target_id} doesn't meet performance criteria")
                continue
            
            optimized_targets.append(target)
        
        # Sort by performance score
        optimized_targets.sort(
            key=lambda t: self._calculate_target_score(t),
            reverse=True
        )
        
        return optimized_targets
    
    async def _is_target_available(self, target: PushTargetConfig) -> bool:
        """Check if target is available for push operations."""
        if not target.enabled:
            return False
        
        # Check health status
        if target.health_status == "unhealthy":
            return False
        
        # Check circuit breaker
        circuit_breaker = self.target_manager._circuit_breakers.get(target.target_id, {})
        if circuit_breaker.get("state") == "open":
            # Check if we should try half-open
            next_attempt = circuit_breaker.get("next_attempt_time")
            if next_attempt and datetime.utcnow() < next_attempt:
                return False
        
        return True
    
    async def _has_sufficient_capacity(
        self,
        target: PushTargetConfig,
        context: PushContext,
        changes: List[ChangeRecord]
    ) -> bool:
        """Check if target has sufficient capacity for the push operation."""
        metrics = self._target_metrics.get(target.target_id)
        if not metrics:
            return True  # No metrics available, assume capacity
        
        # Check active connections
        max_connections = target.routing_config.get("max_connections", 100)
        if metrics.active_connections >= max_connections:
            return False
        
        # Check request rate
        max_requests_per_minute = target.routing_config.get("max_requests_per_minute", 1000)
        recent_requests = self._count_recent_requests(target.target_id, minutes=1)
        if recent_requests >= max_requests_per_minute:
            return False
        
        # Check data size limits
        max_data_size = target.routing_config.get("max_data_size_mb", 100) * 1024 * 1024
        if context.data_size_bytes > max_data_size:
            return False
        
        return True
    
    async def _meets_performance_criteria(
        self,
        target: PushTargetConfig,
        context: PushContext
    ) -> bool:
        """Check if target meets performance criteria."""
        metrics = self._target_metrics.get(target.target_id)
        if not metrics:
            return True  # No metrics available, assume it meets criteria
        
        # Check error rate
        max_error_rate = target.routing_config.get("max_error_rate", 0.1)  # 10%
        if metrics.error_rate > max_error_rate:
            return False
        
        # Check average response time
        max_response_time = target.routing_config.get("max_response_time_ms", 5000)
        if metrics.average_response_time_ms > max_response_time:
            return False
        
        return True
    
    def _calculate_target_score(self, target: PushTargetConfig) -> float:
        """Calculate a performance score for target selection."""
        metrics = self._target_metrics.get(target.target_id)
        if not metrics:
            return target.priority  # Use priority as base score
        
        # Base score from priority and weight
        score = target.priority * 10 + target.weight / 10
        
        # Adjust based on performance metrics
        if metrics.total_requests > 0:
            # Lower error rate is better
            error_penalty = metrics.error_rate * 50
            score -= error_penalty
            
            # Lower response time is better
            response_time_penalty = metrics.average_response_time_ms / 100
            score -= response_time_penalty
            
            # Higher success rate is better
            success_rate = metrics.successful_requests / metrics.total_requests
            success_bonus = success_rate * 20
            score += success_bonus
        
        # Adjust based on current load
        load_factor = metrics.active_connections / max(target.routing_config.get("max_connections", 100), 1)
        load_penalty = load_factor * 30
        score -= load_penalty
        
        return max(score, 0)  # Ensure non-negative score
    
    def _determine_routing_strategy(
        self,
        targets: List[PushTargetConfig],
        context: PushContext
    ) -> str:
        """Determine the best routing strategy for the given context."""
        if len(targets) == 0:
            return "no_targets"
        elif len(targets) == 1:
            return "single_target"
        elif context.priority > 5:  # High priority
            return "parallel_push"
        elif context.data_size_bytes > 10 * 1024 * 1024:  # Large data
            return "sequential_push"
        else:
            return "load_balanced"
    
    async def _select_fallback_targets(
        self,
        context: PushContext
    ) -> List[PushTargetConfig]:
        """Select fallback targets when primary selection fails."""
        # Get all available targets for the tenant
        all_targets = await self.target_manager.list_targets(
            context.tenant_id, enabled_only=True
        )
        
        # Filter by basic availability
        fallback_targets = []
        for target in all_targets:
            if await self._is_target_available(target):
                fallback_targets.append(target)
        
        # Sort by priority and return top targets
        fallback_targets.sort(key=lambda t: -t.priority)
        return fallback_targets[:3]  # Limit to top 3 fallback targets
    
    def _generate_cache_key(self, context: PushContext) -> str:
        """Generate cache key for routing decision."""
        key_parts = [
            context.tenant_id,
            context.table_name or "any",
            context.operation or "any",
            str(context.priority),
            str(context.data_size_bytes // 1024)  # KB granularity
        ]
        return ":".join(key_parts)
    
    def _is_cache_valid(self, decision: RoutingDecision) -> bool:
        """Check if cached routing decision is still valid."""
        # For now, implement simple time-based cache invalidation
        # In production, consider target health changes, load changes, etc.
        return True  # Simplified for demo
    
    def _generate_routing_reason(
        self,
        targets: List[PushTargetConfig],
        context: PushContext,
        fallback_used: bool
    ) -> str:
        """Generate human-readable reason for routing decision."""
        if not targets:
            return "No available targets found"
        
        if fallback_used:
            return f"Using {len(targets)} fallback targets due to primary target unavailability"
        
        if len(targets) == 1:
            return f"Single target selected: {targets[0].name} (priority: {targets[0].priority})"
        
        return f"Selected {len(targets)} targets based on load balancing and performance criteria"
    
    def _estimate_completion_time(
        self,
        targets: List[PushTargetConfig],
        changes: List[ChangeRecord]
    ) -> Optional[datetime]:
        """Estimate completion time for the push operation."""
        if not targets or not changes:
            return None
        
        # Calculate estimated time based on target performance and data size
        total_records = len(changes)
        
        # Use the fastest target for estimation
        fastest_target = min(
            targets,
            key=lambda t: self._target_metrics.get(t.target_id, TargetMetrics(target_id=t.target_id)).average_response_time_ms
        )
        
        metrics = self._target_metrics.get(fastest_target.target_id)
        if metrics and metrics.average_response_time_ms > 0:
            estimated_ms = metrics.average_response_time_ms * (total_records / 100)  # Assume 100 records per batch
        else:
            # Default estimation: 1ms per record
            estimated_ms = total_records
        
        return datetime.utcnow() + timedelta(milliseconds=estimated_ms)
    
    def _count_recent_requests(self, target_id: str, minutes: int) -> int:
        """Count recent requests to a target within the specified time window."""
        # In production, maintain a sliding window of request timestamps
        # For now, return a placeholder
        return 0
    
    async def execute_routed_push(
        self,
        decision: RoutingDecision,
        changes: List[ChangeRecord],
        context: PushContext
    ) -> List[PushResult]:
        """
        Execute push operation using the routing decision.
        
        Args:
            decision: Routing decision
            changes: Change records to push
            context: Push context
            
        Returns:
            List of push results from all targets
        """
        if not decision.selected_targets:
            logger.warning("No targets selected for push operation")
            return []
        
        results = []
        
        try:
            if decision.strategy == "parallel_push":
                results = await self._execute_parallel_push(decision.selected_targets, changes, context)
            elif decision.strategy == "sequential_push":
                results = await self._execute_sequential_push(decision.selected_targets, changes, context)
            elif decision.strategy == "load_balanced":
                results = await self._execute_load_balanced_push(decision.selected_targets, changes, context)
            else:
                # Default to single target push
                results = await self._execute_single_push(decision.selected_targets[0], changes, context)
            
            # Update metrics
            for result in results:
                await self._update_target_metrics(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error executing routed push: {e}")
            return []
    
    async def _execute_parallel_push(
        self,
        targets: List[PushTargetConfig],
        changes: List[ChangeRecord],
        context: PushContext
    ) -> List[PushResult]:
        """Execute push to multiple targets in parallel."""
        tasks = []
        
        for target in targets:
            task = self._push_to_target(target, changes, context)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to PushResult
        push_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Parallel push to {targets[i].target_id} failed: {result}")
                # Create failed result
                push_results.append(PushResult(
                    push_id=str(uuid4()),
                    target_id=targets[i].target_id,
                    status="failed",
                    records_failed=len(changes),
                    error_message=str(result)
                ))
            else:
                push_results.append(result)
        
        return push_results
    
    async def _execute_sequential_push(
        self,
        targets: List[PushTargetConfig],
        changes: List[ChangeRecord],
        context: PushContext
    ) -> List[PushResult]:
        """Execute push to targets sequentially."""
        results = []
        
        for target in targets:
            try:
                result = await self._push_to_target(target, changes, context)
                results.append(result)
                
                # If push was successful, we might not need to push to remaining targets
                # depending on the use case
                if result.status == "success":
                    logger.info(f"Sequential push successful to {target.target_id}, skipping remaining targets")
                    break
                    
            except Exception as e:
                logger.error(f"Sequential push to {target.target_id} failed: {e}")
                results.append(PushResult(
                    push_id=str(uuid4()),
                    target_id=target.target_id,
                    status="failed",
                    records_failed=len(changes),
                    error_message=str(e)
                ))
        
        return results
    
    async def _execute_load_balanced_push(
        self,
        targets: List[PushTargetConfig],
        changes: List[ChangeRecord],
        context: PushContext
    ) -> List[PushResult]:
        """Execute push using load balancing across targets."""
        # Distribute changes across targets based on their capacity and performance
        target_assignments = self._distribute_changes_across_targets(targets, changes)
        
        tasks = []
        for target, target_changes in target_assignments.items():
            if target_changes:
                task = self._push_to_target(target, target_changes, context)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        push_results = []
        target_list = list(target_assignments.keys())
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Load balanced push to {target_list[i].target_id} failed: {result}")
                push_results.append(PushResult(
                    push_id=str(uuid4()),
                    target_id=target_list[i].target_id,
                    status="failed",
                    records_failed=len(target_assignments[target_list[i]]),
                    error_message=str(result)
                ))
            else:
                push_results.append(result)
        
        return push_results
    
    async def _execute_single_push(
        self,
        target: PushTargetConfig,
        changes: List[ChangeRecord],
        context: PushContext
    ) -> List[PushResult]:
        """Execute push to a single target."""
        try:
            result = await self._push_to_target(target, changes, context)
            return [result]
        except Exception as e:
            logger.error(f"Single push to {target.target_id} failed: {e}")
            return [PushResult(
                push_id=str(uuid4()),
                target_id=target.target_id,
                status="failed",
                records_failed=len(changes),
                error_message=str(e)
            )]
    
    def _distribute_changes_across_targets(
        self,
        targets: List[PushTargetConfig],
        changes: List[ChangeRecord]
    ) -> Dict[PushTargetConfig, List[ChangeRecord]]:
        """Distribute changes across targets based on their weights and capacity."""
        if not targets or not changes:
            return {}
        
        # Calculate total weight
        total_weight = sum(target.weight for target in targets)
        if total_weight == 0:
            # Equal distribution if no weights
            total_weight = len(targets)
            for target in targets:
                target.weight = 1
        
        # Distribute changes
        assignments = {}
        total_changes = len(changes)
        start_idx = 0
        
        for i, target in enumerate(targets):
            # Calculate number of changes for this target
            if i == len(targets) - 1:
                # Last target gets remaining changes
                target_changes = changes[start_idx:]
            else:
                target_ratio = target.weight / total_weight
                target_count = int(total_changes * target_ratio)
                target_changes = changes[start_idx:start_idx + target_count]
                start_idx += target_count
            
            assignments[target] = target_changes
        
        return assignments
    
    async def _push_to_target(
        self,
        target: PushTargetConfig,
        changes: List[ChangeRecord],
        context: PushContext
    ) -> PushResult:
        """Push changes to a specific target."""
        start_time = time.time()
        push_id = str(uuid4())
        
        # Update active connections
        metrics = self._target_metrics.get(target.target_id)
        if not metrics:
            metrics = TargetMetrics(target_id=target.target_id)
            self._target_metrics[target.target_id] = metrics
        
        metrics.active_connections += 1
        
        try:
            # Simulate push operation
            # In production, this would use the actual push service
            await asyncio.sleep(0.1)  # Simulate processing time
            
            execution_time = (time.time() - start_time) * 1000
            
            result = PushResult(
                push_id=push_id,
                target_id=target.target_id,
                status="success",
                records_pushed=len(changes),
                records_failed=0,
                bytes_transferred=sum(len(str(change.new_data or {})) for change in changes),
                execution_time_ms=execution_time
            )
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            return PushResult(
                push_id=push_id,
                target_id=target.target_id,
                status="failed",
                records_pushed=0,
                records_failed=len(changes),
                execution_time_ms=execution_time,
                error_message=str(e)
            )
        
        finally:
            metrics.active_connections = max(0, metrics.active_connections - 1)
    
    async def _update_target_metrics(self, result: PushResult) -> None:
        """Update target metrics based on push result."""
        metrics = self._target_metrics.get(result.target_id)
        if not metrics:
            metrics = TargetMetrics(target_id=result.target_id)
            self._target_metrics[result.target_id] = metrics
        
        # Update counters
        metrics.total_requests += 1
        metrics.last_request_time = result.timestamp
        
        if result.status == "success":
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1
        
        # Update response time
        metrics.total_response_time_ms += result.execution_time_ms
        metrics.average_response_time_ms = metrics.total_response_time_ms / metrics.total_requests
        
        # Update error rate
        metrics.error_rate = metrics.failed_requests / metrics.total_requests
        
        # Update circuit breaker
        self.target_manager._update_circuit_breaker(
            result.target_id, 
            result.status == "success"
        )
    
    def get_routing_statistics(self, tenant_id: str) -> Dict[str, Any]:
        """Get routing statistics for a tenant."""
        # Filter metrics for tenant targets
        tenant_targets = [
            t.target_id for t in self.target_manager._targets.values() 
            if t.tenant_id == tenant_id
        ]
        
        tenant_metrics = {
            target_id: metrics for target_id, metrics in self._target_metrics.items()
            if target_id in tenant_targets
        }
        
        stats = {
            "total_targets": len(tenant_targets),
            "active_connections": sum(m.active_connections for m in tenant_metrics.values()),
            "total_requests": sum(m.total_requests for m in tenant_metrics.values()),
            "successful_requests": sum(m.successful_requests for m in tenant_metrics.values()),
            "failed_requests": sum(m.failed_requests for m in tenant_metrics.values()),
            "average_response_time_ms": 0.0,
            "overall_error_rate": 0.0,
            "cache_size": len(self._routing_cache),
            "target_metrics": {
                target_id: {
                    "total_requests": metrics.total_requests,
                    "success_rate": metrics.successful_requests / max(metrics.total_requests, 1),
                    "error_rate": metrics.error_rate,
                    "average_response_time_ms": metrics.average_response_time_ms,
                    "active_connections": metrics.active_connections
                }
                for target_id, metrics in tenant_metrics.items()
            }
        }
        
        # Calculate overall metrics
        if stats["total_requests"] > 0:
            stats["overall_error_rate"] = stats["failed_requests"] / stats["total_requests"]
            
            total_response_time = sum(
                m.total_response_time_ms for m in tenant_metrics.values()
            )
            stats["average_response_time_ms"] = total_response_time / stats["total_requests"]
        
        return stats
    
    def clear_cache(self) -> None:
        """Clear routing cache."""
        self._routing_cache.clear()
        logger.info("Routing cache cleared")
    
    def clear_metrics(self, target_id: Optional[str] = None) -> None:
        """Clear metrics for a specific target or all targets."""
        if target_id:
            self._target_metrics.pop(target_id, None)
            logger.info(f"Cleared metrics for target {target_id}")
        else:
            self._target_metrics.clear()
            logger.info("Cleared all target metrics")