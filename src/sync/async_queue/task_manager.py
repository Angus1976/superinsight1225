"""
Async Task Manager Module.

Provides unified interface for managing async tasks across different
backends (Celery, Redis Queue) with progress tracking, monitoring,
and failure recovery.
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

from pydantic import BaseModel, Field

from .celery_integration import CeleryTaskManager, TaskPriority, TaskStatus
from .redis_queue import RedisQueue, RedisQueueManager, QueueMessage, QueueType

logger = logging.getLogger(__name__)


class TaskBackend(str, Enum):
    """Task execution backends."""
    CELERY = "celery"
    REDIS_QUEUE = "redis_queue"
    LOCAL = "local"


class TaskType(str, Enum):
    """Task types for sync operations."""
    DATA_PULL = "data_pull"
    DATA_PUSH = "data_push"
    DATA_TRANSFORM = "data_transform"
    CONFLICT_RESOLVE = "conflict_resolve"
    BATCH_PROCESS = "batch_process"
    HEALTH_CHECK = "health_check"
    CLEANUP = "cleanup"
    WORKFLOW = "workflow"


@dataclass
class TaskProgress:
    """Task progress information."""
    task_id: str
    current_step: int = 0
    total_steps: int = 1
    processed_items: int = 0
    total_items: int = 0
    percentage: float = 0.0
    message: str = ""
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def update(
        self,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
        processed_items: Optional[int] = None,
        total_items: Optional[int] = None,
        message: Optional[str] = None
    ) -> None:
        """Update progress information."""
        if current_step is not None:
            self.current_step = current_step
        if total_steps is not None:
            self.total_steps = total_steps
        if processed_items is not None:
            self.processed_items = processed_items
        if total_items is not None:
            self.total_items = total_items
        if message is not None:
            self.message = message
        
        # Calculate percentage
        if self.total_items > 0:
            self.percentage = (self.processed_items / self.total_items) * 100
        elif self.total_steps > 0:
            self.percentage = (self.current_step / self.total_steps) * 100
        
        self.updated_at = datetime.utcnow()


@dataclass
class TaskResult:
    """Task execution result."""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata
        }


class AsyncTaskManager:
    """
    Unified async task manager supporting multiple backends.
    
    Provides a consistent interface for submitting, monitoring, and managing
    async tasks across Celery, Redis Queue, and local execution.
    """
    
    def __init__(
        self,
        default_backend: TaskBackend = TaskBackend.REDIS_QUEUE,
        celery_manager: Optional[CeleryTaskManager] = None,
        redis_queue_manager: Optional[RedisQueueManager] = None
    ):
        self.default_backend = default_backend
        self.celery_manager = celery_manager
        self.redis_queue_manager = redis_queue_manager
        
        # Task tracking
        self._active_tasks: Dict[str, Dict[str, Any]] = {}
        self._task_progress: Dict[str, TaskProgress] = {}
        self._task_results: Dict[str, TaskResult] = {}
        self._task_handlers: Dict[str, Callable] = {}
        
        # Local execution
        self._local_executor = asyncio.create_task(self._local_task_loop())
        self._local_queue: asyncio.Queue = asyncio.Queue()
        
        # Monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the task manager."""
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitor_tasks())
        logger.info("Async task manager started")
    
    async def stop(self) -> None:
        """Stop the task manager."""
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._local_executor:
            self._local_executor.cancel()
            try:
                await self._local_executor
            except asyncio.CancelledError:
                pass
        
        logger.info("Async task manager stopped")
    
    def register_handler(self, task_type: TaskType, handler: Callable) -> None:
        """Register a task handler function."""
        self._task_handlers[task_type.value] = handler
        logger.info(f"Registered handler for task type: {task_type.value}")
    
    async def submit_task(
        self,
        task_type: TaskType,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        backend: Optional[TaskBackend] = None,
        delay: Optional[int] = None,
        expires_in: Optional[int] = None,
        max_retries: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submit a task for execution.
        
        Args:
            task_type: Type of task to execute
            args: Positional arguments
            kwargs: Keyword arguments
            priority: Task priority
            backend: Execution backend (defaults to default_backend)
            delay: Delay before execution (seconds)
            expires_in: Task expiration time (seconds)
            max_retries: Maximum retry attempts
            metadata: Additional metadata
            
        Returns:
            Task ID
        """
        task_id = str(uuid4())
        backend = backend or self.default_backend
        
        task_info = {
            "id": task_id,
            "type": task_type.value,
            "args": args or [],
            "kwargs": kwargs or {},
            "priority": priority,
            "backend": backend,
            "delay": delay,
            "expires_in": expires_in,
            "max_retries": max_retries or 3,
            "metadata": metadata or {},
            "submitted_at": datetime.utcnow(),
            "status": TaskStatus.PENDING
        }
        
        self._active_tasks[task_id] = task_info
        self._task_progress[task_id] = TaskProgress(task_id=task_id)
        
        # Submit to appropriate backend
        if backend == TaskBackend.CELERY and self.celery_manager:
            await self._submit_to_celery(task_info)
        elif backend == TaskBackend.REDIS_QUEUE and self.redis_queue_manager:
            await self._submit_to_redis_queue(task_info)
        else:  # LOCAL
            await self._submit_to_local(task_info)
        
        logger.info(f"Submitted task {task_id} ({task_type.value}) to {backend.value}")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get task status."""
        task_info = self._active_tasks.get(task_id)
        if not task_info:
            # Check if we have a result
            result = self._task_results.get(task_id)
            return result.status if result else None
        
        # Update status from backend
        backend = task_info["backend"]
        
        if backend == TaskBackend.CELERY and self.celery_manager:
            status = self.celery_manager.get_task_status(task_id)
            if status:
                task_info["status"] = status
                return status
        
        return task_info.get("status")
    
    async def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get task progress."""
        return self._task_progress.get(task_id)
    
    async def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """Get task result."""
        # Check if we already have the result
        result = self._task_results.get(task_id)
        if result:
            return result
        
        # Wait for result if timeout specified
        if timeout:
            start_time = time.time()
            while time.time() - start_time < timeout:
                result = self._task_results.get(task_id)
                if result:
                    return result
                await asyncio.sleep(0.1)
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        task_info = self._active_tasks.get(task_id)
        if not task_info:
            return False
        
        backend = task_info["backend"]
        
        if backend == TaskBackend.CELERY and self.celery_manager:
            return self.celery_manager.cancel_task(task_id)
        elif backend == TaskBackend.REDIS_QUEUE:
            # Mark as cancelled (Redis queue doesn't support cancellation)
            task_info["status"] = TaskStatus.REVOKED
            return True
        else:  # LOCAL
            task_info["status"] = TaskStatus.REVOKED
            return True
    
    async def update_progress(
        self,
        task_id: str,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
        processed_items: Optional[int] = None,
        total_items: Optional[int] = None,
        message: Optional[str] = None
    ) -> None:
        """Update task progress."""
        progress = self._task_progress.get(task_id)
        if progress:
            progress.update(
                current_step=current_step,
                total_steps=total_steps,
                processed_items=processed_items,
                total_items=total_items,
                message=message
            )
    
    async def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get list of active tasks."""
        active = []
        
        for task_id, task_info in self._active_tasks.items():
            if task_info["status"] in [TaskStatus.PENDING, TaskStatus.STARTED]:
                progress = self._task_progress.get(task_id)
                active.append({
                    **task_info,
                    "progress": {
                        "percentage": progress.percentage if progress else 0,
                        "message": progress.message if progress else "",
                        "updated_at": progress.updated_at.isoformat() if progress else None
                    }
                })
        
        return active
    
    async def get_task_stats(self) -> Dict[str, Any]:
        """Get task execution statistics."""
        stats = {
            "total_tasks": len(self._active_tasks) + len(self._task_results),
            "active_tasks": len([t for t in self._active_tasks.values() 
                               if t["status"] in [TaskStatus.PENDING, TaskStatus.STARTED]]),
            "completed_tasks": len([r for r in self._task_results.values() 
                                  if r.status == TaskStatus.SUCCESS]),
            "failed_tasks": len([r for r in self._task_results.values() 
                               if r.status == TaskStatus.FAILURE]),
            "by_type": {},
            "by_backend": {},
            "by_status": {}
        }
        
        # Count by type, backend, and status
        all_tasks = list(self._active_tasks.values()) + [
            {"type": r.metadata.get("type", "unknown"), 
             "backend": r.metadata.get("backend", "unknown"),
             "status": r.status}
            for r in self._task_results.values()
        ]
        
        for task in all_tasks:
            task_type = task.get("type", "unknown")
            backend = task.get("backend", "unknown")
            status = task.get("status", "unknown")
            
            stats["by_type"][task_type] = stats["by_type"].get(task_type, 0) + 1
            stats["by_backend"][backend] = stats["by_backend"].get(backend, 0) + 1
            stats["by_status"][str(status)] = stats["by_status"].get(str(status), 0) + 1
        
        return stats
    
    async def cleanup_completed_tasks(self, older_than_hours: int = 24) -> int:
        """Clean up completed tasks older than specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        cleaned = 0
        
        # Clean up results
        to_remove = []
        for task_id, result in self._task_results.items():
            if result.completed_at and result.completed_at < cutoff_time:
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._task_results[task_id]
            self._task_progress.pop(task_id, None)
            cleaned += 1
        
        # Clean up active tasks that are actually completed
        to_remove = []
        for task_id, task_info in self._active_tasks.items():
            if (task_info.get("status") in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED] and
                task_info.get("submitted_at", datetime.utcnow()) < cutoff_time):
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._active_tasks[task_id]
            cleaned += 1
        
        logger.info(f"Cleaned up {cleaned} completed tasks")
        return cleaned
    
    async def _submit_to_celery(self, task_info: Dict[str, Any]) -> None:
        """Submit task to Celery."""
        if not self.celery_manager:
            raise ValueError("Celery manager not configured")
        
        task_name = f"sync.{task_info['type']}"
        
        self.celery_manager.submit_task(
            task_name=task_name,
            args=task_info["args"],
            kwargs=task_info["kwargs"],
            priority=task_info["priority"],
            countdown=task_info["delay"],
            expires=datetime.utcnow() + timedelta(seconds=task_info["expires_in"]) if task_info["expires_in"] else None
        )
    
    async def _submit_to_redis_queue(self, task_info: Dict[str, Any]) -> None:
        """Submit task to Redis queue."""
        if not self.redis_queue_manager:
            raise ValueError("Redis queue manager not configured")
        
        queue_name = f"{task_info['type']}_queue"
        queue = self.redis_queue_manager.get_queue(queue_name)
        
        if not queue:
            # Create queue if it doesn't exist
            queue = self.redis_queue_manager.create_queue(
                queue_name,
                QueueType.PRIORITY if task_info["priority"] != TaskPriority.NORMAL else QueueType.FIFO
            )
        
        await queue.enqueue(
            payload={
                "task_id": task_info["id"],
                "task_type": task_info["type"],
                "args": task_info["args"],
                "kwargs": task_info["kwargs"],
                "metadata": task_info["metadata"]
            },
            priority=self._priority_to_int(task_info["priority"]),
            delay=task_info["delay"],
            expires_in=task_info["expires_in"]
        )
    
    async def _submit_to_local(self, task_info: Dict[str, Any]) -> None:
        """Submit task to local queue."""
        await self._local_queue.put(task_info)
    
    async def _local_task_loop(self) -> None:
        """Local task execution loop."""
        while True:
            try:
                task_info = await self._local_queue.get()
                
                if task_info.get("status") == TaskStatus.REVOKED:
                    continue
                
                await self._execute_local_task(task_info)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Local task loop error: {e}")
    
    async def _execute_local_task(self, task_info: Dict[str, Any]) -> None:
        """Execute a task locally."""
        task_id = task_info["id"]
        task_type = task_info["type"]
        
        try:
            # Update status
            task_info["status"] = TaskStatus.STARTED
            start_time = datetime.utcnow()
            
            # Get handler
            handler = self._task_handlers.get(task_type)
            if not handler:
                raise ValueError(f"No handler registered for task type: {task_type}")
            
            # Execute handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(
                    task_id=task_id,
                    args=task_info["args"],
                    kwargs=task_info["kwargs"],
                    progress_callback=lambda **kwargs: asyncio.create_task(
                        self.update_progress(task_id, **kwargs)
                    )
                )
            else:
                result = handler(
                    task_id=task_id,
                    args=task_info["args"],
                    kwargs=task_info["kwargs"],
                    progress_callback=lambda **kwargs: asyncio.create_task(
                        self.update_progress(task_id, **kwargs)
                    )
                )
            
            # Store result
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self._task_results[task_id] = TaskResult(
                task_id=task_id,
                status=TaskStatus.SUCCESS,
                result=result,
                started_at=start_time,
                completed_at=end_time,
                duration_seconds=duration,
                metadata={
                    "type": task_type,
                    "backend": TaskBackend.LOCAL.value
                }
            )
            
            # Clean up
            self._active_tasks.pop(task_id, None)
            
            logger.info(f"Local task {task_id} completed successfully")
            
        except Exception as e:
            # Store error result
            end_time = datetime.utcnow()
            start_time = task_info.get("started_at", end_time)
            duration = (end_time - start_time).total_seconds()
            
            self._task_results[task_id] = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILURE,
                error=str(e),
                started_at=start_time,
                completed_at=end_time,
                duration_seconds=duration,
                metadata={
                    "type": task_type,
                    "backend": TaskBackend.LOCAL.value
                }
            )
            
            # Clean up
            self._active_tasks.pop(task_id, None)
            
            logger.error(f"Local task {task_id} failed: {e}")
    
    async def _monitor_tasks(self) -> None:
        """Monitor task execution and update statuses."""
        while self._running:
            try:
                # Check Celery tasks
                if self.celery_manager:
                    await self._monitor_celery_tasks()
                
                # Check Redis queue tasks
                if self.redis_queue_manager:
                    await self._monitor_redis_queue_tasks()
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Task monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _monitor_celery_tasks(self) -> None:
        """Monitor Celery tasks."""
        # Implementation would check Celery task statuses
        # and update local tracking
        pass
    
    async def _monitor_redis_queue_tasks(self) -> None:
        """Monitor Redis queue tasks."""
        # Implementation would check Redis queue task statuses
        # and update local tracking
        pass
    
    def _priority_to_int(self, priority: TaskPriority) -> int:
        """Convert priority enum to integer."""
        priority_map = {
            TaskPriority.LOW: 1,
            TaskPriority.NORMAL: 5,
            TaskPriority.HIGH: 8,
            TaskPriority.CRITICAL: 10
        }
        return priority_map.get(priority, 5)


# Pre-defined task handlers
class SyncTaskHandlers:
    """Collection of standard sync task handlers."""
    
    @staticmethod
    async def data_pull_handler(
        task_id: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        progress_callback: Callable
    ) -> Dict[str, Any]:
        """Handle data pull tasks."""
        source_config = kwargs.get("source_config", {})
        sync_config = kwargs.get("sync_config", {})
        
        # Simulate data pulling with progress updates
        total_records = sync_config.get("expected_records", 1000)
        batch_size = sync_config.get("batch_size", 100)
        
        pulled_records = []
        
        for i in range(0, total_records, batch_size):
            # Simulate batch processing
            await asyncio.sleep(0.1)
            
            batch_records = min(batch_size, total_records - i)
            pulled_records.extend([{"id": j, "data": f"record_{j}"} for j in range(i, i + batch_records)])
            
            # Update progress
            await progress_callback(
                processed_items=len(pulled_records),
                total_items=total_records,
                message=f"Pulled {len(pulled_records)}/{total_records} records"
            )
        
        return {
            "status": "success",
            "records_pulled": len(pulled_records),
            "source": source_config.get("name", "unknown")
        }
    
    @staticmethod
    async def data_push_handler(
        task_id: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        progress_callback: Callable
    ) -> Dict[str, Any]:
        """Handle data push tasks."""
        target_config = kwargs.get("target_config", {})
        data = kwargs.get("data", [])
        
        # Simulate data pushing with progress updates
        batch_size = target_config.get("batch_size", 50)
        pushed_count = 0
        
        for i in range(0, len(data), batch_size):
            # Simulate batch pushing
            await asyncio.sleep(0.1)
            
            batch = data[i:i + batch_size]
            pushed_count += len(batch)
            
            # Update progress
            await progress_callback(
                processed_items=pushed_count,
                total_items=len(data),
                message=f"Pushed {pushed_count}/{len(data)} records"
            )
        
        return {
            "status": "success",
            "records_pushed": pushed_count,
            "target": target_config.get("name", "unknown")
        }
    
    @staticmethod
    async def batch_process_handler(
        task_id: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        progress_callback: Callable
    ) -> Dict[str, Any]:
        """Handle batch processing tasks."""
        items = kwargs.get("items", [])
        processor_config = kwargs.get("processor_config", {})
        
        processed = 0
        failed = 0
        results = []
        
        for i, item in enumerate(items):
            try:
                # Simulate item processing
                await asyncio.sleep(0.01)
                
                # Process item (placeholder)
                result = {"item_id": item.get("id"), "processed": True}
                results.append(result)
                processed += 1
                
            except Exception as e:
                failed += 1
                logger.error(f"Failed to process item {item}: {e}")
            
            # Update progress
            if i % 10 == 0 or i == len(items) - 1:
                await progress_callback(
                    processed_items=i + 1,
                    total_items=len(items),
                    message=f"Processed {processed}, Failed {failed}"
                )
        
        return {
            "status": "completed",
            "total_items": len(items),
            "processed": processed,
            "failed": failed,
            "results": results
        }


__all__ = [
    "AsyncTaskManager",
    "TaskBackend",
    "TaskType",
    "TaskProgress",
    "TaskResult",
    "SyncTaskHandlers",
]