"""
Push Target Manager.

Manages push targets including:
- Multiple push target types (database, API, file)
- Push target configuration management
- Push routing and load balancing
- Push result verification and confirmation
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete

from src.database.connection import db_manager
from src.sync.models import (
    DataSourceModel,
    SyncAuditLogModel,
    AuditAction
)
from src.utils.encryption import encrypt_sensitive_data, decrypt_sensitive_data

logger = logging.getLogger(__name__)


class PushTargetConfig(BaseModel):
    """Push target configuration model."""
    target_id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    target_type: str  # database, api, file, webhook, queue
    
    # Connection configuration (encrypted in storage)
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Format and transformation settings
    format_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Retry and reliability settings
    retry_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Load balancing and routing
    routing_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Health check settings
    health_check_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Status and metrics
    enabled: bool = True
    priority: int = 1  # Higher priority targets are preferred
    weight: int = 100  # For load balancing
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_health_check: Optional[datetime] = None
    
    # Health status
    health_status: str = "unknown"  # healthy, unhealthy, unknown
    consecutive_failures: int = 0
    last_error: Optional[str] = None


class LoadBalancingStrategy(BaseModel):
    """Load balancing strategy configuration."""
    strategy: str  # round_robin, weighted, least_connections, random, priority
    targets: List[str]  # Target IDs in the group
    health_check_enabled: bool = True
    failover_enabled: bool = True
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5  # Failures before opening circuit


class PushRoute(BaseModel):
    """Push routing configuration."""
    route_id: str
    tenant_id: str
    name: str
    
    # Routing conditions
    conditions: Dict[str, Any] = Field(default_factory=dict)  # table_name, operation, etc.
    
    # Target configuration
    target_groups: List[LoadBalancingStrategy] = Field(default_factory=list)
    
    # Routing behavior
    enabled: bool = True
    priority: int = 1
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PushResult(BaseModel):
    """Result of a push operation."""
    push_id: str
    target_id: str
    route_id: Optional[str] = None
    status: str  # success, failed, partial, timeout
    records_pushed: int = 0
    records_failed: int = 0
    bytes_transferred: int = 0
    execution_time_ms: float = 0.0
    retry_count: int = 0
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthCheckResult(BaseModel):
    """Health check result."""
    target_id: str
    status: str  # healthy, unhealthy, timeout
    response_time_ms: float
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PushTargetManager:
    """
    Enterprise push target manager.
    
    Manages multiple push targets with load balancing, health checking,
    and automatic failover capabilities.
    """
    
    def __init__(self):
        self._targets: Dict[str, PushTargetConfig] = {}
        self._routes: Dict[str, PushRoute] = {}
        self._health_status: Dict[str, HealthCheckResult] = {}
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._connection_pools: Dict[str, Any] = {}
        
    async def create_target(
        self,
        tenant_id: str,
        target_config: Dict[str, Any]
    ) -> PushTargetConfig:
        """
        Create a new push target.
        
        Args:
            tenant_id: Tenant identifier
            target_config: Target configuration dictionary
            
        Returns:
            Created push target configuration
        """
        try:
            target_id = target_config.get("target_id") or str(uuid4())
            
            # Encrypt sensitive connection data
            connection_config = target_config.get("connection_config", {})
            encrypted_config = await self._encrypt_connection_config(connection_config)
            
            # Create target configuration
            target = PushTargetConfig(
                target_id=target_id,
                tenant_id=tenant_id,
                name=target_config["name"],
                description=target_config.get("description"),
                target_type=target_config["target_type"],
                connection_config=encrypted_config,
                format_config=target_config.get("format_config", {}),
                retry_config=target_config.get("retry_config", self._get_default_retry_config()),
                routing_config=target_config.get("routing_config", {}),
                health_check_config=target_config.get("health_check_config", self._get_default_health_check_config()),
                priority=target_config.get("priority", 1),
                weight=target_config.get("weight", 100)
            )
            
            # Store target configuration
            self._targets[target_id] = target
            
            # Initialize circuit breaker
            self._circuit_breakers[target_id] = {
                "state": "closed",  # closed, open, half_open
                "failure_count": 0,
                "last_failure_time": None,
                "next_attempt_time": None
            }
            
            # Initialize connection pool if needed
            await self._initialize_connection_pool(target)
            
            # Perform initial health check
            await self._perform_health_check(target)
            
            # Log target creation
            await self._log_target_audit(
                tenant_id, target_id, AuditAction.SOURCE_CONNECTED, True,
                {"action": "create_target", "target_type": target.target_type}
            )
            
            logger.info(f"Created push target: {target_id} ({target.target_type})")
            return target
            
        except Exception as e:
            logger.error(f"Error creating push target: {e}")
            raise
    
    async def update_target(
        self,
        tenant_id: str,
        target_id: str,
        updates: Dict[str, Any]
    ) -> PushTargetConfig:
        """
        Update an existing push target.
        
        Args:
            tenant_id: Tenant identifier
            target_id: Target identifier
            updates: Dictionary of fields to update
            
        Returns:
            Updated push target configuration
        """
        try:
            target = self._targets.get(target_id)
            if not target or target.tenant_id != tenant_id:
                raise ValueError(f"Push target {target_id} not found")
            
            # Update fields
            for field, value in updates.items():
                if field == "connection_config":
                    # Re-encrypt connection config
                    value = await self._encrypt_connection_config(value)
                
                if hasattr(target, field):
                    setattr(target, field, value)
            
            target.updated_at = datetime.utcnow()
            
            # Reinitialize connection pool if connection config changed
            if "connection_config" in updates:
                await self._initialize_connection_pool(target)
            
            # Log target update
            await self._log_target_audit(
                tenant_id, target_id, AuditAction.SOURCE_CONNECTED, True,
                {"action": "update_target", "updated_fields": list(updates.keys())}
            )
            
            logger.info(f"Updated push target: {target_id}")
            return target
            
        except Exception as e:
            logger.error(f"Error updating push target: {e}")
            raise
    
    async def delete_target(
        self,
        tenant_id: str,
        target_id: str
    ) -> bool:
        """
        Delete a push target.
        
        Args:
            tenant_id: Tenant identifier
            target_id: Target identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            target = self._targets.get(target_id)
            if not target or target.tenant_id != tenant_id:
                raise ValueError(f"Push target {target_id} not found")
            
            # Close connection pool
            await self._close_connection_pool(target_id)
            
            # Remove from all data structures
            del self._targets[target_id]
            self._health_status.pop(target_id, None)
            self._circuit_breakers.pop(target_id, None)
            self._connection_pools.pop(target_id, None)
            
            # Remove from routes
            for route in self._routes.values():
                for group in route.target_groups:
                    if target_id in group.targets:
                        group.targets.remove(target_id)
            
            # Log target deletion
            await self._log_target_audit(
                tenant_id, target_id, AuditAction.SOURCE_DISCONNECTED, True,
                {"action": "delete_target"}
            )
            
            logger.info(f"Deleted push target: {target_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting push target: {e}")
            raise
    
    async def get_target(
        self,
        tenant_id: str,
        target_id: str
    ) -> Optional[PushTargetConfig]:
        """Get push target by ID."""
        target = self._targets.get(target_id)
        if target and target.tenant_id == tenant_id:
            return target
        return None
    
    async def list_targets(
        self,
        tenant_id: str,
        target_type: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[PushTargetConfig]:
        """
        List push targets for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            target_type: Filter by target type
            enabled_only: Only return enabled targets
            
        Returns:
            List of push target configurations
        """
        targets = []
        
        for target in self._targets.values():
            if target.tenant_id != tenant_id:
                continue
            
            if target_type and target.target_type != target_type:
                continue
            
            if enabled_only and not target.enabled:
                continue
            
            targets.append(target)
        
        # Sort by priority (higher first) then by name
        targets.sort(key=lambda t: (-t.priority, t.name))
        return targets
    
    async def create_route(
        self,
        tenant_id: str,
        route_config: Dict[str, Any]
    ) -> PushRoute:
        """
        Create a push route.
        
        Args:
            tenant_id: Tenant identifier
            route_config: Route configuration dictionary
            
        Returns:
            Created push route
        """
        try:
            route_id = route_config.get("route_id") or str(uuid4())
            
            # Validate target groups
            target_groups = []
            for group_config in route_config.get("target_groups", []):
                # Validate that all targets exist
                for target_id in group_config.get("targets", []):
                    if target_id not in self._targets:
                        raise ValueError(f"Target {target_id} not found")
                
                target_groups.append(LoadBalancingStrategy(**group_config))
            
            route = PushRoute(
                route_id=route_id,
                tenant_id=tenant_id,
                name=route_config["name"],
                conditions=route_config.get("conditions", {}),
                target_groups=target_groups,
                priority=route_config.get("priority", 1)
            )
            
            self._routes[route_id] = route
            
            logger.info(f"Created push route: {route_id}")
            return route
            
        except Exception as e:
            logger.error(f"Error creating push route: {e}")
            raise
    
    async def select_targets(
        self,
        tenant_id: str,
        push_context: Dict[str, Any]
    ) -> List[PushTargetConfig]:
        """
        Select appropriate targets for a push operation.
        
        Args:
            tenant_id: Tenant identifier
            push_context: Context information (table_name, operation, etc.)
            
        Returns:
            List of selected push targets
        """
        try:
            # Find matching routes
            matching_routes = []
            for route in self._routes.values():
                if route.tenant_id != tenant_id or not route.enabled:
                    continue
                
                if self._route_matches_context(route, push_context):
                    matching_routes.append(route)
            
            # Sort routes by priority
            matching_routes.sort(key=lambda r: -r.priority)
            
            # Select targets from the highest priority route
            if matching_routes:
                route = matching_routes[0]
                return await self._select_targets_from_route(route, push_context)
            
            # No matching routes, use default selection
            return await self._select_default_targets(tenant_id, push_context)
            
        except Exception as e:
            logger.error(f"Error selecting targets: {e}")
            return []
    
    def _route_matches_context(
        self,
        route: PushRoute,
        context: Dict[str, Any]
    ) -> bool:
        """Check if a route matches the push context."""
        conditions = route.conditions
        
        # Check table name condition
        if "table_names" in conditions:
            table_name = context.get("table_name")
            if table_name not in conditions["table_names"]:
                return False
        
        # Check operation condition
        if "operations" in conditions:
            operation = context.get("operation")
            if operation not in conditions["operations"]:
                return False
        
        # Check data size condition
        if "max_data_size" in conditions:
            data_size = context.get("data_size", 0)
            if data_size > conditions["max_data_size"]:
                return False
        
        # Check time window condition
        if "time_windows" in conditions:
            current_hour = datetime.utcnow().hour
            if current_hour not in conditions["time_windows"]:
                return False
        
        return True
    
    async def _select_targets_from_route(
        self,
        route: PushRoute,
        context: Dict[str, Any]
    ) -> List[PushTargetConfig]:
        """Select targets from a specific route."""
        selected_targets = []
        
        for group in route.target_groups:
            # Filter healthy targets
            healthy_targets = []
            for target_id in group.targets:
                target = self._targets.get(target_id)
                if target and target.enabled and self._is_target_healthy(target_id):
                    healthy_targets.append(target)
            
            if not healthy_targets:
                continue
            
            # Apply load balancing strategy
            if group.strategy == "round_robin":
                target = self._select_round_robin(healthy_targets, group)
            elif group.strategy == "weighted":
                target = self._select_weighted(healthy_targets, group)
            elif group.strategy == "least_connections":
                target = self._select_least_connections(healthy_targets, group)
            elif group.strategy == "random":
                target = random.choice(healthy_targets)
            elif group.strategy == "priority":
                target = max(healthy_targets, key=lambda t: t.priority)
            else:
                target = healthy_targets[0]  # Default to first
            
            if target:
                selected_targets.append(target)
        
        return selected_targets
    
    async def _select_default_targets(
        self,
        tenant_id: str,
        context: Dict[str, Any]
    ) -> List[PushTargetConfig]:
        """Select default targets when no routes match."""
        targets = await self.list_targets(tenant_id, enabled_only=True)
        
        # Filter healthy targets
        healthy_targets = [
            target for target in targets
            if self._is_target_healthy(target.target_id)
        ]
        
        if not healthy_targets:
            return []
        
        # Return highest priority target
        return [max(healthy_targets, key=lambda t: t.priority)]
    
    def _select_round_robin(
        self,
        targets: List[PushTargetConfig],
        group: LoadBalancingStrategy
    ) -> Optional[PushTargetConfig]:
        """Select target using round-robin strategy."""
        # Simple round-robin implementation
        # In production, maintain state for proper round-robin
        return targets[0] if targets else None
    
    def _select_weighted(
        self,
        targets: List[PushTargetConfig],
        group: LoadBalancingStrategy
    ) -> Optional[PushTargetConfig]:
        """Select target using weighted strategy."""
        if not targets:
            return None
        
        # Calculate total weight
        total_weight = sum(target.weight for target in targets)
        if total_weight == 0:
            return targets[0]
        
        # Select based on weight
        rand_val = random.randint(1, total_weight)
        current_weight = 0
        
        for target in targets:
            current_weight += target.weight
            if rand_val <= current_weight:
                return target
        
        return targets[0]
    
    def _select_least_connections(
        self,
        targets: List[PushTargetConfig],
        group: LoadBalancingStrategy
    ) -> Optional[PushTargetConfig]:
        """Select target with least connections."""
        # In production, track active connections per target
        # For now, return random target
        return random.choice(targets) if targets else None
    
    def _is_target_healthy(self, target_id: str) -> bool:
        """Check if a target is healthy."""
        # Check circuit breaker state
        circuit_breaker = self._circuit_breakers.get(target_id, {})
        if circuit_breaker.get("state") == "open":
            # Check if we should try half-open
            next_attempt = circuit_breaker.get("next_attempt_time")
            if next_attempt and datetime.utcnow() < next_attempt:
                return False
        
        # Check health status
        health = self._health_status.get(target_id)
        if health and health.status == "unhealthy":
            return False
        
        return True
    
    async def _perform_health_check(self, target: PushTargetConfig) -> HealthCheckResult:
        """Perform health check on a target."""
        start_time = datetime.utcnow()
        
        try:
            # Perform health check based on target type
            if target.target_type == "database":
                result = await self._health_check_database(target)
            elif target.target_type == "api":
                result = await self._health_check_api(target)
            elif target.target_type == "file":
                result = await self._health_check_file(target)
            elif target.target_type == "webhook":
                result = await self._health_check_webhook(target)
            else:
                result = HealthCheckResult(
                    target_id=target.target_id,
                    status="healthy",  # Default to healthy for unknown types
                    response_time_ms=0.0
                )
            
            # Update health status
            self._health_status[target.target_id] = result
            
            # Update target health status
            target.last_health_check = result.timestamp
            target.health_status = result.status
            
            if result.status == "healthy":
                target.consecutive_failures = 0
                target.last_error = None
                # Close circuit breaker if it was open
                self._circuit_breakers[target.target_id]["state"] = "closed"
                self._circuit_breakers[target.target_id]["failure_count"] = 0
            else:
                target.consecutive_failures += 1
                target.last_error = result.error_message
                # Update circuit breaker
                self._update_circuit_breaker(target.target_id, False)
            
            return result
            
        except Exception as e:
            # Health check failed
            result = HealthCheckResult(
                target_id=target.target_id,
                status="unhealthy",
                response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                error_message=str(e)
            )
            
            self._health_status[target.target_id] = result
            target.consecutive_failures += 1
            target.last_error = str(e)
            target.health_status = "unhealthy"
            
            # Update circuit breaker
            self._update_circuit_breaker(target.target_id, False)
            
            return result
    
    async def _health_check_database(self, target: PushTargetConfig) -> HealthCheckResult:
        """Health check for database targets."""
        start_time = datetime.utcnow()
        
        # Simulate database health check
        await asyncio.sleep(0.01)  # Simulate connection time
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return HealthCheckResult(
            target_id=target.target_id,
            status="healthy",
            response_time_ms=response_time
        )
    
    async def _health_check_api(self, target: PushTargetConfig) -> HealthCheckResult:
        """Health check for API targets."""
        start_time = datetime.utcnow()
        
        # Simulate API health check
        await asyncio.sleep(0.02)  # Simulate HTTP request
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return HealthCheckResult(
            target_id=target.target_id,
            status="healthy",
            response_time_ms=response_time
        )
    
    async def _health_check_file(self, target: PushTargetConfig) -> HealthCheckResult:
        """Health check for file targets."""
        start_time = datetime.utcnow()
        
        # Simulate file system health check
        await asyncio.sleep(0.005)  # Simulate file system access
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return HealthCheckResult(
            target_id=target.target_id,
            status="healthy",
            response_time_ms=response_time
        )
    
    async def _health_check_webhook(self, target: PushTargetConfig) -> HealthCheckResult:
        """Health check for webhook targets."""
        start_time = datetime.utcnow()
        
        # Simulate webhook health check
        await asyncio.sleep(0.03)  # Simulate HTTP request
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return HealthCheckResult(
            target_id=target.target_id,
            status="healthy",
            response_time_ms=response_time
        )
    
    def _update_circuit_breaker(self, target_id: str, success: bool) -> None:
        """Update circuit breaker state based on operation result."""
        circuit_breaker = self._circuit_breakers.get(target_id, {})
        
        if success:
            circuit_breaker["failure_count"] = 0
            circuit_breaker["state"] = "closed"
        else:
            circuit_breaker["failure_count"] += 1
            circuit_breaker["last_failure_time"] = datetime.utcnow()
            
            # Open circuit breaker if threshold exceeded
            threshold = 5  # Default threshold
            if circuit_breaker["failure_count"] >= threshold:
                circuit_breaker["state"] = "open"
                # Set next attempt time (exponential backoff)
                backoff_seconds = min(2 ** circuit_breaker["failure_count"], 300)  # Max 5 minutes
                circuit_breaker["next_attempt_time"] = datetime.utcnow() + timedelta(seconds=backoff_seconds)
    
    async def _encrypt_connection_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in connection configuration."""
        encrypted_config = config.copy()
        
        # Fields that should be encrypted
        sensitive_fields = ["password", "api_key", "secret", "token", "private_key"]
        
        for field in sensitive_fields:
            if field in encrypted_config:
                encrypted_config[field] = encrypt_sensitive_data(str(encrypted_config[field]))
        
        return encrypted_config
    
    async def _decrypt_connection_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in connection configuration."""
        decrypted_config = config.copy()
        
        # Fields that should be decrypted
        sensitive_fields = ["password", "api_key", "secret", "token", "private_key"]
        
        for field in sensitive_fields:
            if field in decrypted_config:
                decrypted_config[field] = decrypt_sensitive_data(decrypted_config[field])
        
        return decrypted_config
    
    async def _initialize_connection_pool(self, target: PushTargetConfig) -> None:
        """Initialize connection pool for a target."""
        # In production, create actual connection pools based on target type
        logger.info(f"Initializing connection pool for target {target.target_id}")
        
        # Placeholder for connection pool initialization
        self._connection_pools[target.target_id] = {
            "initialized": True,
            "created_at": datetime.utcnow()
        }
    
    async def _close_connection_pool(self, target_id: str) -> None:
        """Close connection pool for a target."""
        if target_id in self._connection_pools:
            logger.info(f"Closing connection pool for target {target_id}")
            del self._connection_pools[target_id]
    
    def _get_default_retry_config(self) -> Dict[str, Any]:
        """Get default retry configuration."""
        return {
            "max_retries": 3,
            "initial_delay_ms": 1000,
            "max_delay_ms": 30000,
            "backoff_multiplier": 2.0,
            "jitter": True
        }
    
    def _get_default_health_check_config(self) -> Dict[str, Any]:
        """Get default health check configuration."""
        return {
            "enabled": True,
            "interval_seconds": 60,
            "timeout_seconds": 10,
            "failure_threshold": 3,
            "success_threshold": 2
        }
    
    async def _log_target_audit(
        self,
        tenant_id: str,
        target_id: str,
        action: AuditAction,
        success: bool,
        details: Dict[str, Any]
    ) -> None:
        """Log target management operation to audit trail."""
        try:
            with db_manager.get_session() as session:
                audit_log = SyncAuditLogModel(
                    tenant_id=tenant_id,
                    action=action,
                    actor_type="system",
                    action_details={
                        "target_id": target_id,
                        **details
                    },
                    success=success
                )
                
                session.add(audit_log)
                session.commit()
                
        except Exception as e:
            logger.error(f"Error logging target audit: {e}")
    
    async def run_health_checks(self, tenant_id: Optional[str] = None) -> Dict[str, HealthCheckResult]:
        """Run health checks on all targets."""
        results = {}
        
        targets_to_check = []
        for target in self._targets.values():
            if tenant_id and target.tenant_id != tenant_id:
                continue
            if target.enabled and target.health_check_config.get("enabled", True):
                targets_to_check.append(target)
        
        # Run health checks concurrently
        tasks = [self._perform_health_check(target) for target in targets_to_check]
        if tasks:
            health_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(health_results):
                if isinstance(result, Exception):
                    logger.error(f"Health check failed for {targets_to_check[i].target_id}: {result}")
                else:
                    results[targets_to_check[i].target_id] = result
        
        return results
    
    def get_target_statistics(self, tenant_id: str) -> Dict[str, Any]:
        """Get statistics for all targets."""
        tenant_targets = [t for t in self._targets.values() if t.tenant_id == tenant_id]
        
        stats = {
            "total_targets": len(tenant_targets),
            "enabled_targets": len([t for t in tenant_targets if t.enabled]),
            "healthy_targets": len([t for t in tenant_targets if t.health_status == "healthy"]),
            "unhealthy_targets": len([t for t in tenant_targets if t.health_status == "unhealthy"]),
            "targets_by_type": {},
            "circuit_breakers_open": 0,
            "total_routes": len([r for r in self._routes.values() if r.tenant_id == tenant_id])
        }
        
        # Count by type
        for target in tenant_targets:
            target_type = target.target_type
            if target_type not in stats["targets_by_type"]:
                stats["targets_by_type"][target_type] = 0
            stats["targets_by_type"][target_type] += 1
        
        # Count open circuit breakers
        for target in tenant_targets:
            circuit_breaker = self._circuit_breakers.get(target.target_id, {})
            if circuit_breaker.get("state") == "open":
                stats["circuit_breakers_open"] += 1
        
        return stats