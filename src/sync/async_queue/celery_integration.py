"""
Celery Integration Module.

Provides Celery-based distributed task queue for async data synchronization,
with Redis as message broker and result backend.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

from celery import Celery, Task
from celery.result import AsyncResult
from celery.signals import task_prerun, task_postrun, task_failure, task_success
from kombu import Queue
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


@dataclass
class SyncTask:
    """Represents a synchronization task."""
    id: str
    name: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    eta: Optional[datetime] = None
    countdown: Optional[int] = None
    expires: Optional[datetime] = None
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "args": self.args,
            "kwargs": self.kwargs,
            "priority": self.priority.value,
            "eta": self.eta.isoformat() if self.eta else None,
            "countdown": self.countdown,
            "expires": self.expires.isoformat() if self.expires else None,
            "retry_policy": self.retry_policy,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class CeleryConfig:
    """Celery configuration."""
    
    # Broker settings
    broker_url = "redis://localhost:6379/0"
    result_backend = "redis://localhost:6379/0"
    
    # Task settings
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]
    timezone = "UTC"
    enable_utc = True
    
    # Task routing
    task_routes = {
        "sync.pull.*": {"queue": "pull_queue"},
        "sync.push.*": {"queue": "push_queue"},
        "sync.transform.*": {"queue": "transform_queue"},
        "sync.conflict.*": {"queue": "conflict_queue"},
        "sync.monitor.*": {"queue": "monitor_queue"},
    }
    
    # Queue definitions
    task_default_queue = "default"
    task_queues = (
        Queue("default", routing_key="default"),
        Queue("pull_queue", routing_key="pull"),
        Queue("push_queue", routing_key="push"),
        Queue("transform_queue", routing_key="transform"),
        Queue("conflict_queue", routing_key="conflict"),
        Queue("monitor_queue", routing_key="monitor"),
        Queue("high_priority", routing_key="high"),
        Queue("low_priority", routing_key="low"),
    )
    
    # Worker settings
    worker_prefetch_multiplier = 1
    task_acks_late = True
    worker_disable_rate_limits = False
    
    # Result settings
    result_expires = 3600  # 1 hour
    result_persistent = True
    
    # Retry settings
    task_default_retry_delay = 60  # 1 minute
    task_max_retries = 3
    
    # Monitoring
    worker_send_task_events = True
    task_send_sent_event = True
    
    # Security
    worker_hijack_root_logger = False
    worker_log_color = False


class SyncTaskBase(Task):
    """Base class for sync tasks with enhanced error handling."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True
    retry_backoff_max = 700
    retry_jitter = False
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success."""
        logger.info(f"Task {self.name}[{task_id}] succeeded")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure."""
        logger.error(f"Task {self.name}[{task_id}] failed: {exc}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called on task retry."""
        logger.warning(f"Task {self.name}[{task_id}] retrying: {exc}")


def create_celery_app(
    name: str = "sync_worker",
    config: Optional[CeleryConfig] = None
) -> Celery:
    """Create and configure Celery application."""
    
    app = Celery(name)
    
    # Apply configuration
    if config:
        app.config_from_object(config)
    else:
        app.config_from_object(CeleryConfig)
    
    # Register task signals
    @task_prerun.connect
    def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
        logger.info(f"Task {task.name}[{task_id}] starting")
    
    @task_postrun.connect
    def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
        logger.info(f"Task {task.name}[{task_id}] finished with state: {state}")
    
    @task_failure.connect
    def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
        logger.error(f"Task {sender.name}[{task_id}] failed: {exception}")
    
    @task_success.connect
    def task_success_handler(sender=None, result=None, **kwargs):
        logger.info(f"Task {sender.name} succeeded")
    
    return app


class CeleryTaskManager:
    """
    Manager for Celery-based async tasks.
    
    Provides high-level interface for submitting, monitoring,
    and managing distributed sync tasks.
    """
    
    def __init__(self, celery_app: Celery):
        self.app = celery_app
        self._active_tasks: Dict[str, AsyncResult] = {}
        self._task_registry: Dict[str, Callable] = {}
    
    def register_task(self, name: str, func: Callable, **task_options) -> None:
        """Register a task function."""
        task = self.app.task(name=name, base=SyncTaskBase, **task_options)(func)
        self._task_registry[name] = task
        logger.info(f"Registered task: {name}")
    
    def submit_task(
        self,
        task_name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        eta: Optional[datetime] = None,
        countdown: Optional[int] = None,
        expires: Optional[datetime] = None,
        retry_policy: Optional[Dict[str, Any]] = None,
        queue: Optional[str] = None
    ) -> str:
        """
        Submit a task for execution.
        
        Args:
            task_name: Name of the task to execute
            args: Positional arguments
            kwargs: Keyword arguments
            priority: Task priority
            eta: Estimated time of arrival
            countdown: Delay in seconds
            expires: Expiration time
            retry_policy: Retry configuration
            queue: Target queue name
            
        Returns:
            Task ID
        """
        task_id = str(uuid4())
        
        # Determine queue based on priority if not specified
        if not queue:
            if priority == TaskPriority.HIGH or priority == TaskPriority.CRITICAL:
                queue = "high_priority"
            elif priority == TaskPriority.LOW:
                queue = "low_priority"
            else:
                queue = self._get_default_queue(task_name)
        
        # Submit task
        result = self.app.send_task(
            task_name,
            args=args or [],
            kwargs=kwargs or {},
            task_id=task_id,
            eta=eta,
            countdown=countdown,
            expires=expires,
            retry_policy=retry_policy,
            queue=queue,
            priority=self._priority_to_int(priority)
        )
        
        self._active_tasks[task_id] = result
        
        logger.info(f"Submitted task {task_name}[{task_id}] to queue {queue}")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get task status."""
        result = self._active_tasks.get(task_id)
        if not result:
            # Try to get result from backend
            result = AsyncResult(task_id, app=self.app)
        
        if result:
            return TaskStatus(result.status)
        
        return None
    
    def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Get task result."""
        result = self._active_tasks.get(task_id)
        if not result:
            result = AsyncResult(task_id, app=self.app)
        
        if result:
            return result.get(timeout=timeout)
        
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        result = self._active_tasks.get(task_id)
        if not result:
            result = AsyncResult(task_id, app=self.app)
        
        if result:
            result.revoke(terminate=True)
            self._active_tasks.pop(task_id, None)
            logger.info(f"Cancelled task {task_id}")
            return True
        
        return False
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get list of active tasks."""
        active = []
        
        # Get active tasks from workers
        inspect = self.app.control.inspect()
        active_tasks = inspect.active()
        
        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    active.append({
                        "id": task["id"],
                        "name": task["name"],
                        "worker": worker,
                        "args": task["args"],
                        "kwargs": task["kwargs"],
                        "time_start": task["time_start"]
                    })
        
        return active
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        inspect = self.app.control.inspect()
        
        stats = {
            "active": inspect.active(),
            "scheduled": inspect.scheduled(),
            "reserved": inspect.reserved(),
            "stats": inspect.stats(),
        }
        
        return stats
    
    def purge_queue(self, queue_name: str) -> int:
        """Purge all tasks from a queue."""
        return self.app.control.purge()
    
    def _get_default_queue(self, task_name: str) -> str:
        """Get default queue for task based on name."""
        if "pull" in task_name:
            return "pull_queue"
        elif "push" in task_name:
            return "push_queue"
        elif "transform" in task_name:
            return "transform_queue"
        elif "conflict" in task_name:
            return "conflict_queue"
        elif "monitor" in task_name:
            return "monitor_queue"
        else:
            return "default"
    
    def _priority_to_int(self, priority: TaskPriority) -> int:
        """Convert priority enum to integer."""
        priority_map = {
            TaskPriority.LOW: 1,
            TaskPriority.NORMAL: 5,
            TaskPriority.HIGH: 8,
            TaskPriority.CRITICAL: 10
        }
        return priority_map.get(priority, 5)


# Pre-defined sync tasks
def create_sync_tasks(app: Celery) -> Dict[str, Callable]:
    """Create standard sync tasks."""
    
    @app.task(name="sync.pull.database", base=SyncTaskBase)
    def pull_database_task(source_config: Dict[str, Any], sync_config: Dict[str, Any]) -> Dict[str, Any]:
        """Pull data from database source."""
        from ..connectors.database.base import create_database_connector
        
        try:
            connector = create_database_connector(source_config)
            # Implementation would go here
            return {"status": "success", "records_pulled": 0}
        except Exception as e:
            logger.error(f"Database pull task failed: {e}")
            raise
    
    @app.task(name="sync.push.target", base=SyncTaskBase)
    def push_target_task(target_config: Dict[str, Any], data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Push data to target system."""
        try:
            # Implementation would go here
            return {"status": "success", "records_pushed": len(data)}
        except Exception as e:
            logger.error(f"Push target task failed: {e}")
            raise
    
    @app.task(name="sync.transform.data", base=SyncTaskBase)
    def transform_data_task(data: List[Dict[str, Any]], transform_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform data according to configuration."""
        from ..transformer.transformer import DataTransformer
        
        try:
            transformer = DataTransformer(transform_config)
            # Implementation would go here
            return data  # Transformed data
        except Exception as e:
            logger.error(f"Transform data task failed: {e}")
            raise
    
    @app.task(name="sync.conflict.resolve", base=SyncTaskBase)
    def resolve_conflict_task(conflict_data: Dict[str, Any], resolution_strategy: str) -> Dict[str, Any]:
        """Resolve data conflict."""
        try:
            # Implementation would go here
            return {"status": "resolved", "strategy": resolution_strategy}
        except Exception as e:
            logger.error(f"Conflict resolution task failed: {e}")
            raise
    
    @app.task(name="sync.monitor.health", base=SyncTaskBase)
    def monitor_health_task() -> Dict[str, Any]:
        """Monitor system health."""
        try:
            # Implementation would go here
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            logger.error(f"Health monitoring task failed: {e}")
            raise
    
    @app.task(name="sync.batch.process", base=SyncTaskBase)
    def batch_process_task(batch_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a batch of items."""
        try:
            processed = 0
            failed = 0
            
            for item in items:
                try:
                    # Process individual item
                    processed += 1
                except Exception as e:
                    logger.error(f"Failed to process item: {e}")
                    failed += 1
            
            return {
                "batch_id": batch_id,
                "total": len(items),
                "processed": processed,
                "failed": failed,
                "status": "completed"
            }
        except Exception as e:
            logger.error(f"Batch processing task failed: {e}")
            raise
    
    return {
        "pull_database": pull_database_task,
        "push_target": push_target_task,
        "transform_data": transform_data_task,
        "resolve_conflict": resolve_conflict_task,
        "monitor_health": monitor_health_task,
        "batch_process": batch_process_task,
    }


# Workflow tasks
def create_workflow_tasks(app: Celery) -> Dict[str, Callable]:
    """Create workflow orchestration tasks."""
    
    @app.task(name="sync.workflow.execute", base=SyncTaskBase)
    def execute_workflow_task(workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a sync workflow."""
        from celery import group, chain, chord
        
        try:
            workflow_id = workflow_config.get("id")
            steps = workflow_config.get("steps", [])
            
            # Build task chain
            task_chain = []
            
            for step in steps:
                step_type = step.get("type")
                step_config = step.get("config", {})
                
                if step_type == "pull":
                    task_chain.append(pull_database_task.s(step_config, {}))
                elif step_type == "transform":
                    task_chain.append(transform_data_task.s(step_config))
                elif step_type == "push":
                    task_chain.append(push_target_task.s(step_config, []))
            
            # Execute chain
            if task_chain:
                result = chain(*task_chain).apply_async()
                return {"workflow_id": workflow_id, "task_id": result.id, "status": "started"}
            
            return {"workflow_id": workflow_id, "status": "no_steps"}
            
        except Exception as e:
            logger.error(f"Workflow execution task failed: {e}")
            raise
    
    @app.task(name="sync.workflow.parallel", base=SyncTaskBase)
    def parallel_workflow_task(parallel_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute parallel sync workflows."""
        from celery import group
        
        try:
            # Create parallel task group
            job = group(execute_workflow_task.s(config) for config in parallel_configs)
            result = job.apply_async()
            
            return {"group_id": result.id, "task_count": len(parallel_configs), "status": "started"}
            
        except Exception as e:
            logger.error(f"Parallel workflow task failed: {e}")
            raise
    
    return {
        "execute_workflow": execute_workflow_task,
        "parallel_workflow": parallel_workflow_task,
    }


__all__ = [
    "CeleryTaskManager",
    "SyncTask",
    "TaskPriority",
    "TaskStatus",
    "SyncTaskBase",
    "CeleryConfig",
    "create_celery_app",
    "create_sync_tasks",
    "create_workflow_tasks",
]