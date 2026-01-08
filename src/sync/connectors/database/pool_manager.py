"""
Database Connection Pool Manager.

Provides centralized connection pool management with health monitoring,
failover support, and performance optimization.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from src.sync.connectors.base import BaseConnector, ConnectorConfig, ConnectionStatus

logger = logging.getLogger(__name__)


class PoolStatus(str, Enum):
    """Connection pool status."""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class FailoverStrategy(str, Enum):
    """Failover strategy for connection pools."""
    ROUND_ROBIN = "round_robin"
    PRIORITY = "priority"
    LEAST_CONNECTIONS = "least_connections"
    FASTEST_RESPONSE = "fastest_response"


@dataclass
class ConnectionMetrics:
    """Metrics for a database connection."""
    connection_id: str
    created_at: datetime
    last_used: datetime
    total_queries: int = 0
    failed_queries: int = 0
    avg_response_time: float = 0.0
    is_healthy: bool = True
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class PoolMetrics:
    """Metrics for a connection pool."""
    pool_id: str
    status: PoolStatus
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_queries: int = 0
    failed_queries: int = 0
    avg_response_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_health_check: Optional[datetime] = None


class PoolConfig(BaseModel):
    """Configuration for connection pool."""
    name: str
    min_size: int = Field(default=1, ge=1)
    max_size: int = Field(default=10, ge=1)
    max_overflow: int = Field(default=5, ge=0)
    
    # Health check settings
    health_check_interval: int = Field(default=30, ge=1)  # seconds
    max_idle_time: int = Field(default=300, ge=1)  # seconds
    connection_timeout: int = Field(default=30, ge=1)  # seconds
    
    # Failover settings
    failover_strategy: FailoverStrategy = FailoverStrategy.ROUND_ROBIN
    max_retries: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=1.0, ge=0.1)
    circuit_breaker_threshold: int = Field(default=5, ge=1)
    circuit_breaker_timeout: int = Field(default=60, ge=1)  # seconds
    
    # Performance settings
    query_timeout: int = Field(default=60, ge=1)  # seconds
    slow_query_threshold: float = Field(default=5.0, ge=0.1)  # seconds


class DatabaseConnectionPool:
    """
    Database connection pool with health monitoring and failover support.
    
    Features:
    - Automatic connection health monitoring
    - Circuit breaker pattern for failed connections
    - Multiple failover strategies
    - Connection lifecycle management
    - Performance metrics collection
    """

    def __init__(
        self,
        pool_config: PoolConfig,
        connector_configs: List[Dict[str, Any]],
        connector_factory_func
    ):
        self.config = pool_config
        self.connector_configs = connector_configs
        self.connector_factory = connector_factory_func
        
        self.pool_id = str(uuid4())
        self.status = PoolStatus.INITIALIZING
        self.connections: Dict[str, BaseConnector] = {}
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}
        self.pool_metrics = PoolMetrics(pool_id=self.pool_id, status=self.status)
        
        # Circuit breaker state
        self.circuit_breaker_open: Set[str] = set()
        self.circuit_breaker_last_failure: Dict[str, datetime] = {}
        
        # Health monitoring
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> bool:
        """Initialize the connection pool."""
        try:
            logger.info(f"Initializing connection pool: {self.config.name}")
            
            # Create initial connections
            for i, config in enumerate(self.connector_configs[:self.config.min_size]):
                connection_id = f"{self.pool_id}_{i}"
                connector = await self._create_connection(connection_id, config)
                if connector:
                    self.connections[connection_id] = connector
                    self.connection_metrics[connection_id] = ConnectionMetrics(
                        connection_id=connection_id,
                        created_at=datetime.utcnow(),
                        last_used=datetime.utcnow()
                    )
            
            if self.connections:
                self.status = PoolStatus.HEALTHY
                self.pool_metrics.status = self.status
                
                # Start health monitoring
                self._health_check_task = asyncio.create_task(self._health_monitor())
                
                logger.info(
                    f"Connection pool initialized: {len(self.connections)} connections"
                )
                return True
            else:
                self.status = PoolStatus.FAILED
                self.pool_metrics.status = self.status
                logger.error("Failed to create any connections")
                return False
                
        except Exception as e:
            self.status = PoolStatus.FAILED
            self.pool_metrics.status = self.status
            logger.error(f"Failed to initialize connection pool: {e}")
            return False

    async def get_connection(self) -> Optional[BaseConnector]:
        """
        Get a healthy connection from the pool.
        
        Returns:
            Database connector or None if no healthy connections available
        """
        if self.status == PoolStatus.FAILED:
            return None
        
        # Find healthy connections
        healthy_connections = [
            (conn_id, conn) for conn_id, conn in self.connections.items()
            if (conn_id not in self.circuit_breaker_open and 
                self.connection_metrics[conn_id].is_healthy and
                conn.is_connected)
        ]
        
        if not healthy_connections:
            # Try to create new connection if under max size
            if len(self.connections) < self.config.max_size + self.config.max_overflow:
                for config in self.connector_configs:
                    connection_id = f"{self.pool_id}_{len(self.connections)}"
                    connector = await self._create_connection(connection_id, config)
                    if connector:
                        self.connections[connection_id] = connector
                        self.connection_metrics[connection_id] = ConnectionMetrics(
                            connection_id=connection_id,
                            created_at=datetime.utcnow(),
                            last_used=datetime.utcnow()
                        )
                        return connector
            
            logger.warning("No healthy connections available")
            return None
        
        # Select connection based on failover strategy
        selected_conn = self._select_connection(healthy_connections)
        
        # Update metrics
        if selected_conn:
            conn_id = next(
                conn_id for conn_id, conn in healthy_connections 
                if conn == selected_conn
            )
            self.connection_metrics[conn_id].last_used = datetime.utcnow()
        
        return selected_conn

    def _select_connection(
        self, 
        healthy_connections: List[tuple[str, BaseConnector]]
    ) -> Optional[BaseConnector]:
        """Select connection based on failover strategy."""
        if not healthy_connections:
            return None
        
        if self.config.failover_strategy == FailoverStrategy.ROUND_ROBIN:
            # Simple round-robin selection
            return healthy_connections[0][1]
        
        elif self.config.failover_strategy == FailoverStrategy.LEAST_CONNECTIONS:
            # Select connection with least active queries
            min_queries = min(
                self.connection_metrics[conn_id].total_queries
                for conn_id, _ in healthy_connections
            )
            for conn_id, conn in healthy_connections:
                if self.connection_metrics[conn_id].total_queries == min_queries:
                    return conn
        
        elif self.config.failover_strategy == FailoverStrategy.FASTEST_RESPONSE:
            # Select connection with fastest average response time
            min_response_time = min(
                self.connection_metrics[conn_id].avg_response_time
                for conn_id, _ in healthy_connections
            )
            for conn_id, conn in healthy_connections:
                if self.connection_metrics[conn_id].avg_response_time == min_response_time:
                    return conn
        
        # Default to first available
        return healthy_connections[0][1]

    async def _create_connection(
        self, 
        connection_id: str, 
        config: Dict[str, Any]
    ) -> Optional[BaseConnector]:
        """Create a new database connection."""
        try:
            connector = self.connector_factory(config)
            if await connector.connect():
                logger.debug(f"Created connection: {connection_id}")
                return connector
            else:
                logger.warning(f"Failed to connect: {connection_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating connection {connection_id}: {e}")
            return None

    async def _health_monitor(self) -> None:
        """Background task for monitoring connection health."""
        while not self._shutdown_event.is_set():
            try:
                await self._perform_health_checks()
                await self._cleanup_idle_connections()
                await self._update_pool_metrics()
                
                # Check circuit breakers
                await self._check_circuit_breakers()
                
                await asyncio.sleep(self.config.health_check_interval)
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)  # Short delay on error

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all connections."""
        for conn_id, connector in list(self.connections.items()):
            try:
                start_time = time.time()
                is_healthy = await connector.health_check()
                response_time = time.time() - start_time
                
                metrics = self.connection_metrics[conn_id]
                metrics.is_healthy = is_healthy
                
                # Update response time (exponential moving average)
                if metrics.avg_response_time == 0:
                    metrics.avg_response_time = response_time
                else:
                    metrics.avg_response_time = (
                        0.7 * metrics.avg_response_time + 0.3 * response_time
                    )
                
                if not is_healthy:
                    metrics.error_count += 1
                    metrics.last_error = "Health check failed"
                    
                    # Check circuit breaker threshold
                    if metrics.error_count >= self.config.circuit_breaker_threshold:
                        self.circuit_breaker_open.add(conn_id)
                        self.circuit_breaker_last_failure[conn_id] = datetime.utcnow()
                        logger.warning(f"Circuit breaker opened for connection: {conn_id}")
                
            except Exception as e:
                logger.error(f"Health check failed for {conn_id}: {e}")
                self.connection_metrics[conn_id].is_healthy = False
                self.connection_metrics[conn_id].error_count += 1
                self.connection_metrics[conn_id].last_error = str(e)

    async def _cleanup_idle_connections(self) -> None:
        """Clean up idle connections that exceed max idle time."""
        current_time = datetime.utcnow()
        max_idle_delta = timedelta(seconds=self.config.max_idle_time)
        
        for conn_id in list(self.connections.keys()):
            metrics = self.connection_metrics[conn_id]
            if (current_time - metrics.last_used) > max_idle_delta:
                if len(self.connections) > self.config.min_size:
                    await self._remove_connection(conn_id)
                    logger.debug(f"Removed idle connection: {conn_id}")

    async def _check_circuit_breakers(self) -> None:
        """Check and potentially close circuit breakers."""
        current_time = datetime.utcnow()
        timeout_delta = timedelta(seconds=self.config.circuit_breaker_timeout)
        
        for conn_id in list(self.circuit_breaker_open):
            last_failure = self.circuit_breaker_last_failure.get(conn_id)
            if last_failure and (current_time - last_failure) > timeout_delta:
                # Try to reconnect
                connector = self.connections.get(conn_id)
                if connector:
                    try:
                        if await connector.reconnect():
                            self.circuit_breaker_open.discard(conn_id)
                            self.connection_metrics[conn_id].error_count = 0
                            self.connection_metrics[conn_id].is_healthy = True
                            logger.info(f"Circuit breaker closed for connection: {conn_id}")
                    except Exception as e:
                        logger.error(f"Failed to reconnect {conn_id}: {e}")

    async def _update_pool_metrics(self) -> None:
        """Update pool-level metrics."""
        self.pool_metrics.total_connections = len(self.connections)
        self.pool_metrics.active_connections = sum(
            1 for metrics in self.connection_metrics.values()
            if metrics.is_healthy
        )
        self.pool_metrics.idle_connections = (
            self.pool_metrics.total_connections - self.pool_metrics.active_connections
        )
        self.pool_metrics.failed_connections = len(self.circuit_breaker_open)
        self.pool_metrics.last_health_check = datetime.utcnow()
        
        # Update pool status
        if self.pool_metrics.active_connections == 0:
            self.status = PoolStatus.FAILED
        elif self.pool_metrics.failed_connections > 0:
            self.status = PoolStatus.DEGRADED
        else:
            self.status = PoolStatus.HEALTHY
        
        self.pool_metrics.status = self.status

    async def _remove_connection(self, connection_id: str) -> None:
        """Remove a connection from the pool."""
        try:
            connector = self.connections.pop(connection_id, None)
            if connector:
                await connector.disconnect()
            
            self.connection_metrics.pop(connection_id, None)
            self.circuit_breaker_open.discard(connection_id)
            self.circuit_breaker_last_failure.pop(connection_id, None)
            
        except Exception as e:
            logger.error(f"Error removing connection {connection_id}: {e}")

    async def shutdown(self) -> None:
        """Shutdown the connection pool."""
        logger.info(f"Shutting down connection pool: {self.config.name}")
        
        # Stop health monitoring
        self._shutdown_event.set()
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for conn_id in list(self.connections.keys()):
            await self._remove_connection(conn_id)
        
        self.status = PoolStatus.MAINTENANCE
        logger.info("Connection pool shutdown complete")

    def get_metrics(self) -> Dict[str, Any]:
        """Get pool and connection metrics."""
        return {
            "pool": {
                "id": self.pool_metrics.pool_id,
                "name": self.config.name,
                "status": self.pool_metrics.status.value,
                "total_connections": self.pool_metrics.total_connections,
                "active_connections": self.pool_metrics.active_connections,
                "idle_connections": self.pool_metrics.idle_connections,
                "failed_connections": self.pool_metrics.failed_connections,
                "created_at": self.pool_metrics.created_at.isoformat(),
                "last_health_check": (
                    self.pool_metrics.last_health_check.isoformat()
                    if self.pool_metrics.last_health_check else None
                ),
            },
            "connections": [
                {
                    "id": metrics.connection_id,
                    "created_at": metrics.created_at.isoformat(),
                    "last_used": metrics.last_used.isoformat(),
                    "total_queries": metrics.total_queries,
                    "failed_queries": metrics.failed_queries,
                    "avg_response_time": metrics.avg_response_time,
                    "is_healthy": metrics.is_healthy,
                    "error_count": metrics.error_count,
                    "last_error": metrics.last_error,
                    "circuit_breaker_open": conn_id in self.circuit_breaker_open,
                }
                for conn_id, metrics in self.connection_metrics.items()
            ]
        }


class PoolManager:
    """
    Centralized manager for multiple database connection pools.
    
    Provides:
    - Pool lifecycle management
    - Cross-pool load balancing
    - Centralized monitoring and metrics
    """

    def __init__(self):
        self.pools: Dict[str, DatabaseConnectionPool] = {}
        self._shutdown_event = asyncio.Event()

    async def create_pool(
        self,
        name: str,
        pool_config: PoolConfig,
        connector_configs: List[Dict[str, Any]],
        connector_factory_func
    ) -> bool:
        """Create and initialize a new connection pool."""
        if name in self.pools:
            logger.warning(f"Pool already exists: {name}")
            return False

        pool = DatabaseConnectionPool(
            pool_config, connector_configs, connector_factory_func
        )
        
        if await pool.initialize():
            self.pools[name] = pool
            logger.info(f"Created connection pool: {name}")
            return True
        else:
            logger.error(f"Failed to create connection pool: {name}")
            return False

    async def get_connection(self, pool_name: str) -> Optional[BaseConnector]:
        """Get a connection from the specified pool."""
        pool = self.pools.get(pool_name)
        if not pool:
            logger.error(f"Pool not found: {pool_name}")
            return None
        
        return await pool.get_connection()

    async def remove_pool(self, name: str) -> bool:
        """Remove and shutdown a connection pool."""
        pool = self.pools.pop(name, None)
        if pool:
            await pool.shutdown()
            logger.info(f"Removed connection pool: {name}")
            return True
        else:
            logger.warning(f"Pool not found: {name}")
            return False

    def get_pool_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for one or all pools."""
        if name:
            pool = self.pools.get(name)
            return pool.get_metrics() if pool else {}
        else:
            return {
                pool_name: pool.get_metrics()
                for pool_name, pool in self.pools.items()
            }

    async def shutdown_all(self) -> None:
        """Shutdown all connection pools."""
        logger.info("Shutting down all connection pools")
        
        for pool_name in list(self.pools.keys()):
            await self.remove_pool(pool_name)
        
        self._shutdown_event.set()
        logger.info("All connection pools shutdown complete")


# Global pool manager instance
pool_manager = PoolManager()