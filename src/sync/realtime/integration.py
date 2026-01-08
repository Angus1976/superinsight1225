"""
Real-time Sync Integration Module.

Integrates CDC, pglogical replication, and async task processing
into a unified real-time synchronization system.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..cdc.debezium_connector import DebeziumCDC, DebeziumConfig, DebeziumManager
from ..cdc.pglogical_replication import PgLogicalReplication, PgLogicalConfig, PgLogicalManager
from ..cdc.database_cdc import CDCManager, ChangeEvent
from ..async_queue.task_manager import AsyncTaskManager, TaskType, TaskBackend
from ..async_queue.celery_integration import create_celery_app, CeleryTaskManager
from ..async_queue.redis_queue import RedisQueueManager, create_redis_queue

logger = logging.getLogger(__name__)


class SyncMode(str, Enum):
    """Synchronization modes."""
    CDC_ONLY = "cdc_only"
    REPLICATION_ONLY = "replication_only"
    HYBRID = "hybrid"
    ASYNC_ONLY = "async_only"


@dataclass
class SyncConfiguration:
    """Configuration for real-time sync system."""
    # General settings
    name: str
    mode: SyncMode = SyncMode.HYBRID
    
    # CDC settings
    enable_debezium: bool = True
    debezium_configs: List[DebeziumConfig] = field(default_factory=list)
    
    # Replication settings
    enable_pglogical: bool = True
    pglogical_configs: List[PgLogicalConfig] = field(default_factory=list)
    
    # Async processing settings
    enable_async_tasks: bool = True
    task_backend: TaskBackend = TaskBackend.REDIS_QUEUE
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: Optional[str] = None
    
    # Performance settings
    batch_size: int = 1000
    max_concurrent_tasks: int = 10
    task_timeout_seconds: int = 300
    
    # Monitoring settings
    enable_monitoring: bool = True
    health_check_interval: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "mode": self.mode.value,
            "enable_debezium": self.enable_debezium,
            "enable_pglogical": self.enable_pglogical,
            "enable_async_tasks": self.enable_async_tasks,
            "task_backend": self.task_backend.value,
            "redis_url": self.redis_url,
            "celery_broker_url": self.celery_broker_url,
            "batch_size": self.batch_size,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "task_timeout_seconds": self.task_timeout_seconds,
            "enable_monitoring": self.enable_monitoring,
            "health_check_interval": self.health_check_interval
        }


class RealTimeSyncManager:
    """
    Unified real-time synchronization manager.
    
    Coordinates CDC, logical replication, and async task processing
    to provide comprehensive real-time data synchronization.
    """
    
    def __init__(self, config: SyncConfiguration):
        self.config = config
        self._running = False
        
        # Component managers
        self.cdc_manager: Optional[CDCManager] = None
        self.debezium_manager: Optional[DebeziumManager] = None
        self.pglogical_manager: Optional[PgLogicalManager] = None
        self.task_manager: Optional[AsyncTaskManager] = None
        
        # Internal components
        self._celery_manager: Optional[CeleryTaskManager] = None
        self._redis_queue_manager: Optional[RedisQueueManager] = None
        
        # Monitoring
        self._health_check_task: Optional[asyncio.Task] = None
        self._stats = {
            "started_at": None,
            "events_processed": 0,
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "last_event_at": None,
            "last_health_check": None
        }
    
    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info(f"Initializing real-time sync system: {self.config.name}")
        
        # Initialize CDC components
        if self.config.mode in [SyncMode.CDC_ONLY, SyncMode.HYBRID]:
            await self._initialize_cdc()
        
        # Initialize replication components
        if self.config.mode in [SyncMode.REPLICATION_ONLY, SyncMode.HYBRID]:
            await self._initialize_replication()
        
        # Initialize async task processing
        if self.config.enable_async_tasks:
            await self._initialize_async_tasks()
        
        logger.info("Real-time sync system initialized successfully")
    
    async def start(self) -> None:
        """Start the real-time sync system."""
        if self._running:
            logger.warning("Real-time sync system is already running")
            return
        
        logger.info("Starting real-time sync system")
        self._running = True
        self._stats["started_at"] = datetime.utcnow()
        
        # Start CDC components
        if self.cdc_manager:
            await self.cdc_manager.start_all()
        
        if self.debezium_manager:
            await self.debezium_manager.start_all()
        
        # Start replication components
        if self.pglogical_manager:
            await self.pglogical_manager.start_all()
        
        # Start async task manager
        if self.task_manager:
            await self.task_manager.start()
        
        # Start monitoring
        if self.config.enable_monitoring:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Real-time sync system started successfully")
    
    async def stop(self) -> None:
        """Stop the real-time sync system."""
        if not self._running:
            return
        
        logger.info("Stopping real-time sync system")
        self._running = False
        
        # Stop monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Stop async task manager
        if self.task_manager:
            await self.task_manager.stop()
        
        # Stop replication components
        if self.pglogical_manager:
            await self.pglogical_manager.stop_all()
        
        # Stop CDC components
        if self.debezium_manager:
            await self.debezium_manager.stop_all()
        
        if self.cdc_manager:
            await self.cdc_manager.stop_all()
        
        logger.info("Real-time sync system stopped")
    
    async def submit_sync_task(
        self,
        task_type: TaskType,
        data: Any,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Submit a synchronization task."""
        if not self.task_manager:
            raise RuntimeError("Task manager not initialized")
        
        task_id = await self.task_manager.submit_task(
            task_type=task_type,
            kwargs={"data": data, "metadata": metadata or {}},
            metadata=metadata
        )
        
        self._stats["tasks_submitted"] += 1
        return task_id
    
    async def process_change_event(self, event: ChangeEvent) -> None:
        """Process a change event from CDC or replication."""
        self._stats["events_processed"] += 1
        self._stats["last_event_at"] = datetime.utcnow()
        
        # Submit async task for processing
        if self.task_manager:
            try:
                await self.submit_sync_task(
                    task_type=TaskType.DATA_TRANSFORM,
                    data=event.to_dict(),
                    metadata={
                        "source": event.metadata.get("source", "unknown"),
                        "table": event.table,
                        "operation": event.operation.value
                    }
                )
            except Exception as e:
                logger.error(f"Failed to submit task for change event {event.id}: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        status = {
            "running": self._running,
            "config": self.config.to_dict(),
            "stats": self._stats.copy(),
            "components": {}
        }
        
        # CDC status
        if self.cdc_manager:
            status["components"]["cdc"] = self.cdc_manager.get_stats()
        
        if self.debezium_manager:
            status["components"]["debezium"] = self.debezium_manager.get_cdc_stats()
        
        # Replication status
        if self.pglogical_manager:
            status["components"]["pglogical"] = await self.pglogical_manager.get_all_replication_info()
        
        # Task manager status
        if self.task_manager:
            status["components"]["tasks"] = await self.task_manager.get_task_stats()
        
        return status
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        metrics = {
            "throughput": {
                "events_per_second": 0,
                "tasks_per_second": 0
            },
            "latency": {
                "avg_processing_time": 0,
                "p95_processing_time": 0
            },
            "resource_usage": {
                "memory_mb": 0,
                "cpu_percent": 0
            }
        }
        
        # Calculate throughput
        if self._stats["started_at"]:
            runtime_seconds = (datetime.utcnow() - self._stats["started_at"]).total_seconds()
            if runtime_seconds > 0:
                metrics["throughput"]["events_per_second"] = self._stats["events_processed"] / runtime_seconds
                metrics["throughput"]["tasks_per_second"] = self._stats["tasks_submitted"] / runtime_seconds
        
        return metrics
    
    async def _initialize_cdc(self) -> None:
        """Initialize CDC components."""
        self.cdc_manager = CDCManager()
        
        # Initialize Debezium if enabled
        if self.config.enable_debezium and self.config.debezium_configs:
            kafka_connect_url = self.config.debezium_configs[0].kafka_connect_url
            self.debezium_manager = DebeziumManager(kafka_connect_url)
            
            for debezium_config in self.config.debezium_configs:
                debezium_cdc = DebeziumCDC(debezium_config)
                
                # Register event handler
                debezium_cdc.on_change(self.process_change_event)
                
                await self.debezium_manager.register_cdc(debezium_cdc)
                self.cdc_manager.register(debezium_cdc)
    
    async def _initialize_replication(self) -> None:
        """Initialize replication components."""
        if self.config.enable_pglogical and self.config.pglogical_configs:
            self.pglogical_manager = PgLogicalManager()
            
            for pglogical_config in self.config.pglogical_configs:
                pglogical_repl = PgLogicalReplication(pglogical_config)
                
                # Register event handler
                pglogical_repl.on_change(self.process_change_event)
                
                self.pglogical_manager.register(pglogical_repl)
    
    async def _initialize_async_tasks(self) -> None:
        """Initialize async task processing."""
        # Initialize Redis queue manager
        if self.config.task_backend in [TaskBackend.REDIS_QUEUE, TaskBackend.LOCAL]:
            import redis.asyncio as redis
            redis_client = redis.from_url(self.config.redis_url)
            self.redis_queue_manager = RedisQueueManager(redis_client)
        
        # Initialize Celery manager
        celery_manager = None
        if self.config.task_backend == TaskBackend.CELERY and self.config.celery_broker_url:
            celery_app = create_celery_app()
            celery_manager = CeleryTaskManager(celery_app)
            self._celery_manager = celery_manager
        
        # Initialize unified task manager
        self.task_manager = AsyncTaskManager(
            default_backend=self.config.task_backend,
            celery_manager=celery_manager,
            redis_queue_manager=self.redis_queue_manager
        )
        
        # Register task handlers
        from ..async_queue.task_manager import SyncTaskHandlers
        
        self.task_manager.register_handler(TaskType.DATA_PULL, SyncTaskHandlers.data_pull_handler)
        self.task_manager.register_handler(TaskType.DATA_PUSH, SyncTaskHandlers.data_push_handler)
        self.task_manager.register_handler(TaskType.BATCH_PROCESS, SyncTaskHandlers.batch_process_handler)
    
    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while self._running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(self.config.health_check_interval)
    
    async def _perform_health_check(self) -> None:
        """Perform system health check."""
        self._stats["last_health_check"] = datetime.utcnow()
        
        # Check CDC components
        if self.cdc_manager:
            cdc_stats = self.cdc_manager.get_stats()
            for name, stats in cdc_stats.items():
                if not stats.get("running", False):
                    logger.warning(f"CDC {name} is not running")
        
        # Check task manager
        if self.task_manager:
            task_stats = await self.task_manager.get_task_stats()
            failed_ratio = task_stats.get("failed_tasks", 0) / max(task_stats.get("total_tasks", 1), 1)
            if failed_ratio > 0.1:  # More than 10% failure rate
                logger.warning(f"High task failure rate: {failed_ratio:.2%}")
        
        logger.debug("Health check completed")


def create_realtime_sync_system(config: SyncConfiguration) -> RealTimeSyncManager:
    """Factory function to create real-time sync system."""
    return RealTimeSyncManager(config)


__all__ = [
    "RealTimeSyncManager",
    "SyncConfiguration",
    "SyncMode",
    "create_realtime_sync_system",
]