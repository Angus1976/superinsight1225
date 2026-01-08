"""
Data Pull Scheduler and Monitor.

Provides intelligent scheduling for data pull operations with comprehensive
monitoring, performance optimization, and alerting capabilities.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

from src.sync.connectors.base import BaseConnector, SyncResult
from src.sync.connectors.incremental_sync import IncrementalSyncEngine, IncrementalSyncConfig
from src.sync.scheduler.job_scheduler import ScheduledJob, JobTrigger, IntervalTrigger, CronTrigger
from src.sync.scheduler.executor import SyncExecutor, ExecutionContext

logger = logging.getLogger(__name__)


class PullJobType(str, Enum):
    """Types of pull jobs."""
    FULL_SYNC = "full_sync"
    INCREMENTAL_SYNC = "incremental_sync"
    SCHEMA_DISCOVERY = "schema_discovery"
    HEALTH_CHECK = "health_check"
    PERFORMANCE_TEST = "performance_test"


class PullJobPriority(str, Enum):
    """Pull job priorities."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MonitoringLevel(str, Enum):
    """Monitoring detail levels."""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


@dataclass
class PullJobConfig:
    """Configuration for a pull job."""
    job_id: str
    name: str
    job_type: PullJobType
    priority: PullJobPriority = PullJobPriority.NORMAL
    
    # Source configuration
    source_config: Dict[str, Any] = field(default_factory=dict)
    tables: List[str] = field(default_factory=list)
    
    # Sync configuration
    batch_size: int = 1000
    max_batch_size: int = 10000
    timeout_seconds: int = 3600
    
    # Incremental sync settings
    enable_incremental: bool = True
    incremental_config: Optional[IncrementalSyncConfig] = None
    
    # Monitoring settings
    monitoring_level: MonitoringLevel = MonitoringLevel.BASIC
    enable_performance_tracking: bool = True
    enable_alerting: bool = True
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: float = 60.0
    
    # Scheduling
    schedule_expression: Optional[str] = None  # Cron expression
    interval_seconds: Optional[int] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PullJobMetrics:
    """Metrics for a pull job."""
    job_id: str
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    # Performance metrics
    avg_duration_seconds: float = 0.0
    min_duration_seconds: float = 0.0
    max_duration_seconds: float = 0.0
    
    # Throughput metrics
    avg_records_per_second: float = 0.0
    max_records_per_second: float = 0.0
    total_records_processed: int = 0
    
    # Data metrics
    avg_batch_size: float = 0.0
    total_bytes_transferred: int = 0
    
    # Error metrics
    error_rate: float = 0.0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    # Timing metrics
    last_execution_time: Optional[datetime] = None
    next_scheduled_time: Optional[datetime] = None
    
    # Updated timestamp
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PullJobExecution:
    """Represents a single pull job execution."""
    execution_id: str
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "running"
    
    # Results
    records_processed: int = 0
    records_per_second: float = 0.0
    bytes_transferred: int = 0
    duration_seconds: float = 0.0
    
    # Errors
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    
    # Performance data
    performance_data: Dict[str, Any] = field(default_factory=dict)


class PullSchedulerConfig(BaseModel):
    """Configuration for pull scheduler."""
    # Scheduler settings
    max_concurrent_jobs: int = Field(default=5, ge=1)
    check_interval_seconds: float = Field(default=1.0, ge=0.1)
    
    # Performance settings
    enable_performance_optimization: bool = True
    adaptive_batch_sizing: bool = True
    
    # Monitoring settings
    metrics_retention_days: int = Field(default=30, ge=1)
    execution_history_limit: int = Field(default=1000, ge=1)
    
    # Alerting settings
    enable_alerting: bool = True
    alert_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "error_rate": 0.1,  # 10%
        "duration_increase": 2.0,  # 2x normal
        "throughput_decrease": 0.5  # 50% of normal
    })
    
    # Health check settings
    health_check_interval_seconds: int = Field(default=300, ge=1)
    connection_timeout_seconds: int = Field(default=30, ge=1)


class DataPullScheduler:
    """
    Intelligent data pull scheduler with comprehensive monitoring.
    
    Features:
    - Flexible job scheduling (cron, interval, manual)
    - Performance monitoring and optimization
    - Adaptive batch sizing
    - Error tracking and alerting
    - Health monitoring
    - Resource usage optimization
    """

    def __init__(self, config: PullSchedulerConfig):
        self.config = config
        self.scheduler_id = str(uuid4())
        
        # Job management
        self.jobs: Dict[str, PullJobConfig] = {}
        self.scheduled_jobs: Dict[str, ScheduledJob] = {}
        self.job_metrics: Dict[str, PullJobMetrics] = {}
        self.execution_history: List[PullJobExecution] = []
        
        # Active executions
        self.active_executions: Dict[str, PullJobExecution] = {}
        
        # Connectors and engines
        self.connectors: Dict[str, BaseConnector] = {}
        self.sync_engines: Dict[str, IncrementalSyncEngine] = {}
        
        # Scheduler components
        self.executor = SyncExecutor(
            max_concurrent_batches=self.config.max_concurrent_jobs
        )
        
        # Monitoring
        self.alert_handlers: List[Callable] = []
        self.performance_data: Dict[str, List[Dict[str, Any]]] = {}
        
        # Control
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the pull scheduler."""
        if self._running:
            return
        
        logger.info("Starting data pull scheduler")
        self._running = True
        
        # Start scheduler and monitor tasks
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop the pull scheduler."""
        if not self._running:
            return
        
        logger.info("Stopping data pull scheduler")
        self._running = False
        self._shutdown_event.set()
        
        # Cancel tasks
        if self._scheduler_task:
            self._scheduler_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()
        
        # Wait for tasks to complete
        tasks = [t for t in [self._scheduler_task, self._monitor_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def add_pull_job(self, job_config: PullJobConfig) -> str:
        """
        Add a new pull job to the scheduler.
        
        Args:
            job_config: Configuration for the pull job
            
        Returns:
            Job ID
        """
        job_id = job_config.job_id
        
        if job_id in self.jobs:
            raise ValueError(f"Job already exists: {job_id}")
        
        # Store job configuration
        self.jobs[job_id] = job_config
        
        # Initialize metrics
        self.job_metrics[job_id] = PullJobMetrics(job_id=job_id)
        
        # Create scheduled job
        trigger = self._create_job_trigger(job_config)
        if trigger:
            scheduled_job = ScheduledJob(
                id=f"pull_{job_id}",
                job_id=job_id,
                tenant_id=job_config.metadata.get("tenant_id", "default"),
                name=job_config.name,
                trigger=trigger,
                priority=self._get_priority_value(job_config.priority),
                max_retries=job_config.max_retries,
                timeout_seconds=job_config.timeout_seconds
            )
            
            self.scheduled_jobs[job_id] = scheduled_job
        
        # Create sync engine if incremental
        if job_config.enable_incremental and job_config.incremental_config:
            self.sync_engines[job_id] = IncrementalSyncEngine(job_config.incremental_config)
        
        logger.info(f"Added pull job: {job_id}")
        return job_id

    def remove_pull_job(self, job_id: str) -> bool:
        """
        Remove a pull job from the scheduler.
        
        Args:
            job_id: ID of the job to remove
            
        Returns:
            True if job was removed
        """
        if job_id not in self.jobs:
            return False
        
        # Remove from all collections
        self.jobs.pop(job_id, None)
        self.scheduled_jobs.pop(job_id, None)
        self.job_metrics.pop(job_id, None)
        self.sync_engines.pop(job_id, None)
        self.connectors.pop(job_id, None)
        
        logger.info(f"Removed pull job: {job_id}")
        return True

    def trigger_job(self, job_id: str) -> bool:
        """
        Manually trigger a pull job.
        
        Args:
            job_id: ID of the job to trigger
            
        Returns:
            True if job was triggered
        """
        if job_id not in self.jobs:
            return False
        
        # Create immediate execution
        asyncio.create_task(self._execute_pull_job(job_id))
        logger.info(f"Manually triggered pull job: {job_id}")
        return True

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_scheduled_jobs()
                await asyncio.sleep(self.config.check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(5)

    async def _check_scheduled_jobs(self) -> None:
        """Check for jobs that should be executed."""
        now = datetime.utcnow()
        
        # Check if we have capacity
        if len(self.active_executions) >= self.config.max_concurrent_jobs:
            return
        
        # Find jobs that should run
        for job_id, scheduled_job in self.scheduled_jobs.items():
            if job_id in self.active_executions:
                continue  # Already running
            
            if scheduled_job.should_run(now):
                asyncio.create_task(self._execute_pull_job(job_id))

    async def _execute_pull_job(self, job_id: str) -> None:
        """
        Execute a pull job.
        
        Args:
            job_id: ID of the job to execute
        """
        job_config = self.jobs.get(job_id)
        if not job_config:
            logger.error(f"Job configuration not found: {job_id}")
            return
        
        execution_id = str(uuid4())
        execution = PullJobExecution(
            execution_id=execution_id,
            job_id=job_id,
            started_at=datetime.utcnow()
        )
        
        self.active_executions[job_id] = execution
        
        try:
            logger.info(f"Starting pull job execution: {job_id}")
            
            # Get or create connector
            connector = await self._get_connector(job_id, job_config)
            
            # Execute based on job type
            if job_config.job_type == PullJobType.FULL_SYNC:
                result = await self._execute_full_sync(job_config, connector)
            elif job_config.job_type == PullJobType.INCREMENTAL_SYNC:
                result = await self._execute_incremental_sync(job_config, connector)
            elif job_config.job_type == PullJobType.SCHEMA_DISCOVERY:
                result = await self._execute_schema_discovery(job_config, connector)
            elif job_config.job_type == PullJobType.HEALTH_CHECK:
                result = await self._execute_health_check(job_config, connector)
            elif job_config.job_type == PullJobType.PERFORMANCE_TEST:
                result = await self._execute_performance_test(job_config, connector)
            else:
                raise ValueError(f"Unknown job type: {job_config.job_type}")
            
            # Update execution with results
            execution.completed_at = datetime.utcnow()
            execution.status = "completed" if result.success else "failed"
            execution.records_processed = result.records_processed
            execution.bytes_transferred = getattr(result, 'bytes_transferred', 0)
            execution.duration_seconds = result.duration_seconds
            
            if execution.duration_seconds > 0:
                execution.records_per_second = execution.records_processed / execution.duration_seconds
            
            if not result.success:
                execution.error_message = str(result.errors[0]) if result.errors else "Unknown error"
                execution.error_details = {"errors": result.errors}
            
            # Update metrics
            await self._update_job_metrics(job_id, execution, result)
            
            # Check for alerts
            if self.config.enable_alerting:
                await self._check_alerts(job_id, execution)
            
            logger.info(
                f"Pull job completed: {job_id}, "
                f"records: {execution.records_processed}, "
                f"duration: {execution.duration_seconds:.2f}s"
            )
            
        except Exception as e:
            execution.completed_at = datetime.utcnow()
            execution.status = "failed"
            execution.error_message = str(e)
            execution.error_details = {"exception": type(e).__name__}
            
            logger.error(f"Pull job failed: {job_id}, error: {e}")
            
        finally:
            # Store execution in history
            self.execution_history.append(execution)
            
            # Maintain history limit
            if len(self.execution_history) > self.config.execution_history_limit:
                self.execution_history = self.execution_history[-self.config.execution_history_limit//2:]
            
            # Remove from active executions
            self.active_executions.pop(job_id, None)
            
            # Schedule next run
            scheduled_job = self.scheduled_jobs.get(job_id)
            if scheduled_job:
                scheduled_job.schedule_next(datetime.utcnow())

    async def _get_connector(self, job_id: str, job_config: PullJobConfig) -> BaseConnector:
        """Get or create connector for job."""
        if job_id in self.connectors:
            connector = self.connectors[job_id]
            if not connector.is_connected:
                await connector.connect()
            return connector
        
        # Create new connector based on source config
        # This would use the connector factory in production
        from src.sync.connectors.database import PostgreSQLConnector
        from src.sync.connectors.database.postgresql import PostgreSQLConfig
        
        config = PostgreSQLConfig(**job_config.source_config)
        connector = PostgreSQLConnector(config)
        await connector.connect()
        
        self.connectors[job_id] = connector
        return connector

    async def _execute_full_sync(
        self,
        job_config: PullJobConfig,
        connector: BaseConnector
    ) -> SyncResult:
        """Execute full synchronization."""
        total_records = 0
        total_duration = 0.0
        
        for table in job_config.tables:
            start_time = time.time()
            
            # Fetch all data from table
            batch_count = 0
            async for batch in connector.fetch_data_stream(
                table=table,
                batch_size=job_config.batch_size
            ):
                batch_count += 1
                total_records += len(batch.records)
                
                # Process batch (would write to target in production)
                await asyncio.sleep(0.01)  # Simulate processing
            
            duration = time.time() - start_time
            total_duration += duration
            
            logger.debug(f"Full sync completed for table {table}: {batch_count} batches")
        
        return SyncResult(
            success=True,
            records_processed=total_records,
            duration_seconds=total_duration
        )

    async def _execute_incremental_sync(
        self,
        job_config: PullJobConfig,
        connector: BaseConnector
    ) -> SyncResult:
        """Execute incremental synchronization."""
        sync_engine = self.sync_engines.get(job_config.job_id)
        if not sync_engine:
            raise ValueError(f"No sync engine for job: {job_config.job_id}")
        
        total_result = SyncResult(success=True, records_processed=0, duration_seconds=0.0)
        
        for table in job_config.tables:
            result = await sync_engine.sync_table(connector, table)
            
            total_result.records_processed += result.records_processed
            total_result.records_inserted += result.records_inserted
            total_result.records_updated += result.records_updated
            total_result.records_deleted += result.records_deleted
            total_result.duration_seconds += result.duration_seconds
            
            if not result.success:
                total_result.success = False
                total_result.errors.extend(result.errors)
        
        return total_result

    async def _execute_schema_discovery(
        self,
        job_config: PullJobConfig,
        connector: BaseConnector
    ) -> SyncResult:
        """Execute schema discovery."""
        start_time = time.time()
        
        try:
            schema = await connector.fetch_schema()
            duration = time.time() - start_time
            
            return SyncResult(
                success=True,
                records_processed=len(schema.get("tables", [])),
                duration_seconds=duration,
                metadata={"schema": schema}
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                duration_seconds=time.time() - start_time,
                errors=[{"error": str(e)}]
            )

    async def _execute_health_check(
        self,
        job_config: PullJobConfig,
        connector: BaseConnector
    ) -> SyncResult:
        """Execute health check."""
        start_time = time.time()
        
        try:
            is_healthy = await connector.health_check()
            stats = connector.stats
            
            return SyncResult(
                success=is_healthy,
                records_processed=1,
                duration_seconds=time.time() - start_time,
                metadata={"health_check": is_healthy, "stats": stats}
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                duration_seconds=time.time() - start_time,
                errors=[{"error": str(e)}]
            )

    async def _execute_performance_test(
        self,
        job_config: PullJobConfig,
        connector: BaseConnector
    ) -> SyncResult:
        """Execute performance test."""
        start_time = time.time()
        
        try:
            # Test connection performance
            test_result = await connector.test_connection()
            
            # Test query performance if tables specified
            query_times = []
            if job_config.tables:
                for table in job_config.tables[:3]:  # Test first 3 tables
                    query_start = time.time()
                    count = await connector.get_record_count(table)
                    query_time = time.time() - query_start
                    query_times.append(query_time)
            
            duration = time.time() - start_time
            
            return SyncResult(
                success=test_result.get("success", False),
                records_processed=len(query_times),
                duration_seconds=duration,
                metadata={
                    "connection_test": test_result,
                    "query_times": query_times,
                    "avg_query_time": sum(query_times) / len(query_times) if query_times else 0
                }
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                duration_seconds=time.time() - start_time,
                errors=[{"error": str(e)}]
            )

    async def _update_job_metrics(
        self,
        job_id: str,
        execution: PullJobExecution,
        result: SyncResult
    ) -> None:
        """Update job metrics with execution results."""
        metrics = self.job_metrics[job_id]
        
        # Update counters
        metrics.execution_count += 1
        if execution.status == "completed":
            metrics.success_count += 1
        else:
            metrics.failure_count += 1
        
        # Update performance metrics
        if execution.duration_seconds > 0:
            if metrics.avg_duration_seconds == 0:
                metrics.avg_duration_seconds = execution.duration_seconds
            else:
                metrics.avg_duration_seconds = (
                    (metrics.avg_duration_seconds * (metrics.execution_count - 1) + 
                     execution.duration_seconds) / metrics.execution_count
                )
            
            metrics.min_duration_seconds = min(
                metrics.min_duration_seconds or float('inf'),
                execution.duration_seconds
            )
            metrics.max_duration_seconds = max(
                metrics.max_duration_seconds,
                execution.duration_seconds
            )
        
        # Update throughput metrics
        if execution.records_per_second > 0:
            if metrics.avg_records_per_second == 0:
                metrics.avg_records_per_second = execution.records_per_second
            else:
                metrics.avg_records_per_second = (
                    (metrics.avg_records_per_second * (metrics.execution_count - 1) + 
                     execution.records_per_second) / metrics.execution_count
                )
            
            metrics.max_records_per_second = max(
                metrics.max_records_per_second,
                execution.records_per_second
            )
        
        # Update data metrics
        metrics.total_records_processed += execution.records_processed
        metrics.total_bytes_transferred += execution.bytes_transferred
        
        # Update error metrics
        metrics.error_rate = metrics.failure_count / metrics.execution_count
        if execution.status == "failed":
            metrics.last_error = execution.error_message
            metrics.last_error_time = execution.completed_at
        
        # Update timing
        metrics.last_execution_time = execution.completed_at
        
        scheduled_job = self.scheduled_jobs.get(job_id)
        if scheduled_job:
            metrics.next_scheduled_time = scheduled_job.next_run_at
        
        metrics.updated_at = datetime.utcnow()

    async def _check_alerts(self, job_id: str, execution: PullJobExecution) -> None:
        """Check for alert conditions."""
        metrics = self.job_metrics[job_id]
        job_config = self.jobs[job_id]
        
        if not job_config.enable_alerting:
            return
        
        alerts = []
        
        # Check error rate
        error_threshold = self.config.alert_thresholds.get("error_rate", 0.1)
        if metrics.error_rate > error_threshold:
            alerts.append({
                "type": "high_error_rate",
                "message": f"Error rate {metrics.error_rate:.2%} exceeds threshold {error_threshold:.2%}",
                "job_id": job_id,
                "metric_value": metrics.error_rate,
                "threshold": error_threshold
            })
        
        # Check duration increase
        duration_threshold = self.config.alert_thresholds.get("duration_increase", 2.0)
        if (metrics.avg_duration_seconds > 0 and 
            execution.duration_seconds > metrics.avg_duration_seconds * duration_threshold):
            alerts.append({
                "type": "duration_increase",
                "message": f"Execution duration {execution.duration_seconds:.2f}s is {duration_threshold}x average",
                "job_id": job_id,
                "metric_value": execution.duration_seconds,
                "threshold": metrics.avg_duration_seconds * duration_threshold
            })
        
        # Check throughput decrease
        throughput_threshold = self.config.alert_thresholds.get("throughput_decrease", 0.5)
        if (metrics.avg_records_per_second > 0 and 
            execution.records_per_second < metrics.avg_records_per_second * throughput_threshold):
            alerts.append({
                "type": "throughput_decrease",
                "message": f"Throughput {execution.records_per_second:.2f} rps is below threshold",
                "job_id": job_id,
                "metric_value": execution.records_per_second,
                "threshold": metrics.avg_records_per_second * throughput_threshold
            })
        
        # Send alerts
        for alert in alerts:
            await self._send_alert(alert)

    async def _send_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert to registered handlers."""
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self._collect_performance_data()
                await self._cleanup_old_data()
                await asyncio.sleep(self.config.health_check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(30)

    async def _collect_performance_data(self) -> None:
        """Collect performance data from active jobs."""
        timestamp = datetime.utcnow()
        
        for job_id, connector in self.connectors.items():
            if connector.is_connected:
                stats = connector.stats
                
                if job_id not in self.performance_data:
                    self.performance_data[job_id] = []
                
                self.performance_data[job_id].append({
                    "timestamp": timestamp,
                    "stats": stats
                })
                
                # Keep only recent data
                cutoff = timestamp - timedelta(hours=24)
                self.performance_data[job_id] = [
                    data for data in self.performance_data[job_id]
                    if data["timestamp"] > cutoff
                ]

    async def _cleanup_old_data(self) -> None:
        """Clean up old execution history and metrics."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.metrics_retention_days)
        
        # Clean execution history
        self.execution_history = [
            execution for execution in self.execution_history
            if execution.started_at > cutoff_date
        ]

    def _create_job_trigger(self, job_config: PullJobConfig) -> Optional[JobTrigger]:
        """Create job trigger from configuration."""
        if job_config.schedule_expression:
            return CronTrigger(cron_expression=job_config.schedule_expression)
        elif job_config.interval_seconds:
            return IntervalTrigger(interval_seconds=job_config.interval_seconds)
        else:
            return None  # Manual trigger only

    def _get_priority_value(self, priority: PullJobPriority) -> int:
        """Convert priority enum to numeric value."""
        priority_map = {
            PullJobPriority.LOW: 1,
            PullJobPriority.NORMAL: 5,
            PullJobPriority.HIGH: 8,
            PullJobPriority.CRITICAL: 10
        }
        return priority_map.get(priority, 5)

    def add_alert_handler(self, handler: Callable) -> None:
        """Add an alert handler."""
        self.alert_handlers.append(handler)

    def get_job_metrics(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for jobs."""
        if job_id:
            return self.job_metrics.get(job_id, {}).__dict__
        else:
            return {
                job_id: metrics.__dict__
                for job_id, metrics in self.job_metrics.items()
            }

    def get_execution_history(
        self,
        job_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get execution history."""
        history = self.execution_history
        
        if job_id:
            history = [e for e in history if e.job_id == job_id]
        
        return [execution.__dict__ for execution in history[-limit:]]

    def get_performance_data(self, job_id: str) -> List[Dict[str, Any]]:
        """Get performance data for a job."""
        return self.performance_data.get(job_id, [])

    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "scheduler_id": self.scheduler_id,
            "running": self._running,
            "total_jobs": len(self.jobs),
            "active_executions": len(self.active_executions),
            "total_executions": len(self.execution_history),
            "successful_executions": len([e for e in self.execution_history if e.status == "completed"]),
            "failed_executions": len([e for e in self.execution_history if e.status == "failed"]),
            "jobs_by_type": {
                job_type.value: len([j for j in self.jobs.values() if j.job_type == job_type])
                for job_type in PullJobType
            }
        }