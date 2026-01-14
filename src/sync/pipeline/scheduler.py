"""
Sync Scheduler for Data Sync Pipeline.

Manages scheduled sync jobs with status tracking and history.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from src.sync.pipeline.enums import JobStatus
from src.sync.pipeline.schemas import (
    PullConfig,
    PullResult,
    ScheduleConfig,
    ScheduledJob,
    SyncHistoryRecord,
    SyncResult,
)


class SyncScheduler:
    """
    Sync Scheduler for managing scheduled sync jobs.
    
    Features:
    - Job scheduling with cron expressions
    - Manual job triggering
    - Status tracking
    - Failure alerting
    - Priority management
    - History recording
    """
    
    def __init__(self, data_puller=None, notification_service=None):
        """
        Initialize the Sync Scheduler.
        
        Args:
            data_puller: DataPuller for executing sync operations
            notification_service: Service for sending notifications
        """
        self.data_puller = data_puller
        self.notification_service = notification_service
        self._jobs: Dict[str, ScheduledJob] = {}
        self._history: Dict[str, List[SyncHistoryRecord]] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
    
    async def schedule(
        self,
        job_id: str,
        source_id: str,
        config: ScheduleConfig
    ) -> ScheduledJob:
        """
        Create or update a scheduled sync job.
        
        Args:
            job_id: Unique job identifier
            source_id: Data source identifier
            config: Schedule configuration
            
        Returns:
            ScheduledJob with schedule details
        """
        now = datetime.utcnow()
        next_run = self._calculate_next_run(config.cron_expression, now)
        
        job = ScheduledJob(
            job_id=job_id,
            source_id=source_id,
            config=config,
            status=JobStatus.PENDING if config.enabled else JobStatus.PENDING,
            last_run_at=None,
            next_run_at=next_run if config.enabled else None,
            created_at=now
        )
        
        self._jobs[job_id] = job
        
        # Initialize history list
        if job_id not in self._history:
            self._history[job_id] = []
        
        return job
    
    async def trigger_manual(self, job_id: str) -> SyncResult:
        """
        Manually trigger a sync job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            SyncResult with execution details
        """
        if job_id not in self._jobs:
            return SyncResult(
                job_id=job_id,
                success=False,
                error_message=f"Job {job_id} not found"
            )
        
        job = self._jobs[job_id]
        return await self._execute_job(job)
    
    async def _execute_job(self, job: ScheduledJob) -> SyncResult:
        """Execute a sync job."""
        started_at = datetime.utcnow()
        
        # Update status to running
        await self.update_status(job.job_id, JobStatus.RUNNING)
        
        try:
            # Execute the pull operation
            if self.data_puller:
                pull_config = PullConfig(
                    cron_expression=job.config.cron_expression,
                    incremental=True
                )
                pull_result = await self.data_puller.pull(
                    job.source_id,
                    pull_config
                )
                rows_synced = pull_result.rows_pulled
                success = pull_result.success
                error_message = pull_result.error_message
            else:
                # Simulate successful sync without data puller
                rows_synced = 0
                success = True
                error_message = None
            
            # Update status
            status = JobStatus.COMPLETED if success else JobStatus.FAILED
            await self.update_status(job.job_id, status)
            
            # Record history
            completed_at = datetime.utcnow()
            history_record = SyncHistoryRecord(
                job_id=job.job_id,
                started_at=started_at,
                completed_at=completed_at,
                status=status,
                rows_synced=rows_synced,
                error_message=error_message
            )
            self._add_history(job.job_id, history_record)
            
            # Update job timestamps
            job.last_run_at = started_at
            if job.config.enabled:
                job.next_run_at = self._calculate_next_run(
                    job.config.cron_expression,
                    completed_at
                )
            
            return SyncResult(
                job_id=job.job_id,
                success=success,
                rows_synced=rows_synced,
                started_at=started_at,
                completed_at=completed_at,
                error_message=error_message
            )
            
        except Exception as e:
            # Handle failure
            await self.on_failure(job.job_id, e)
            
            completed_at = datetime.utcnow()
            history_record = SyncHistoryRecord(
                job_id=job.job_id,
                started_at=started_at,
                completed_at=completed_at,
                status=JobStatus.FAILED,
                rows_synced=0,
                error_message=str(e)
            )
            self._add_history(job.job_id, history_record)
            
            return SyncResult(
                job_id=job.job_id,
                success=False,
                rows_synced=0,
                started_at=started_at,
                completed_at=completed_at,
                error_message=str(e)
            )
    
    async def get_status(self, job_id: str) -> Optional[JobStatus]:
        """
        Get the current status of a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobStatus or None if job not found
        """
        job = self._jobs.get(job_id)
        return job.status if job else None
    
    async def update_status(self, job_id: str, status: JobStatus) -> None:
        """
        Update the status of a job.
        
        Args:
            job_id: Job identifier
            status: New status
        """
        if job_id in self._jobs:
            self._jobs[job_id].status = status
    
    async def on_failure(self, job_id: str, error: Exception) -> None:
        """
        Handle sync failure.
        
        Args:
            job_id: Job identifier
            error: Exception that caused the failure
        """
        await self.update_status(job_id, JobStatus.FAILED)
        
        # Send notification if service available
        if self.notification_service:
            await self.notification_service.send_alert(
                alert_type="SYNC_FAILURE",
                data={
                    "job_id": job_id,
                    "error": str(error),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    async def set_priority(self, job_id: str, priority: int) -> None:
        """
        Set the priority of a job.
        
        Args:
            job_id: Job identifier
            priority: Priority level (0-10, higher is more important)
        """
        if job_id in self._jobs:
            self._jobs[job_id].config.priority = max(0, min(10, priority))
    
    async def get_history(
        self,
        job_id: str,
        limit: int = 100
    ) -> List[SyncHistoryRecord]:
        """
        Get sync history for a job.
        
        Args:
            job_id: Job identifier
            limit: Maximum number of records to return
            
        Returns:
            List of SyncHistoryRecord, most recent first
        """
        history = self._history.get(job_id, [])
        # Return most recent first
        return sorted(
            history,
            key=lambda x: x.started_at,
            reverse=True
        )[:limit]
    
    async def list_jobs(
        self,
        status: Optional[JobStatus] = None
    ) -> List[ScheduledJob]:
        """
        List all scheduled jobs.
        
        Args:
            status: Filter by status (optional)
            
        Returns:
            List of ScheduledJob
        """
        jobs = list(self._jobs.values())
        
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        
        # Sort by priority (descending) then by next_run_at
        return sorted(
            jobs,
            key=lambda x: (-x.config.priority, x.next_run_at or datetime.max)
        )
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a scheduled job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancelled, False if not found
        """
        if job_id not in self._jobs:
            return False
        
        # Cancel running task if any
        if job_id in self._running_tasks:
            self._running_tasks[job_id].cancel()
            del self._running_tasks[job_id]
        
        # Update status
        self._jobs[job_id].status = JobStatus.PENDING
        self._jobs[job_id].config.enabled = False
        self._jobs[job_id].next_run_at = None
        
        return True
    
    async def delete_job(self, job_id: str) -> bool:
        """
        Delete a scheduled job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if deleted, False if not found
        """
        if job_id not in self._jobs:
            return False
        
        # Cancel if running
        await self.cancel_job(job_id)
        
        # Remove job and history
        del self._jobs[job_id]
        self._history.pop(job_id, None)
        
        return True
    
    async def enable_job(self, job_id: str) -> bool:
        """
        Enable a disabled job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if enabled, False if not found
        """
        if job_id not in self._jobs:
            return False
        
        job = self._jobs[job_id]
        job.config.enabled = True
        job.next_run_at = self._calculate_next_run(
            job.config.cron_expression,
            datetime.utcnow()
        )
        
        return True
    
    async def disable_job(self, job_id: str) -> bool:
        """
        Disable a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if disabled, False if not found
        """
        if job_id not in self._jobs:
            return False
        
        job = self._jobs[job_id]
        job.config.enabled = False
        job.next_run_at = None
        
        return True
    
    def _add_history(self, job_id: str, record: SyncHistoryRecord) -> None:
        """Add a history record for a job."""
        if job_id not in self._history:
            self._history[job_id] = []
        
        self._history[job_id].append(record)
        
        # Keep only last 1000 records per job
        if len(self._history[job_id]) > 1000:
            self._history[job_id] = sorted(
                self._history[job_id],
                key=lambda x: x.started_at,
                reverse=True
            )[:1000]
    
    def _calculate_next_run(
        self,
        cron_expression: str,
        from_time: datetime
    ) -> datetime:
        """
        Calculate the next run time based on cron expression.
        
        This is a simplified implementation. In production, use a proper
        cron parser like croniter.
        
        Args:
            cron_expression: Cron expression string
            from_time: Starting time for calculation
            
        Returns:
            Next scheduled run time
        """
        # Simple implementation: add 1 minute for any cron expression
        # In production, use croniter or similar library
        parts = cron_expression.split()
        
        if len(parts) >= 5:
            # Try to parse minute field
            minute_field = parts[0]
            if minute_field == "*":
                # Every minute
                return from_time + timedelta(minutes=1)
            elif minute_field.startswith("*/"):
                # Every N minutes
                try:
                    interval = int(minute_field[2:])
                    return from_time + timedelta(minutes=interval)
                except ValueError:
                    pass
        
        # Default: next minute
        return from_time + timedelta(minutes=1)
    
    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """
        Get a job by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            ScheduledJob or None if not found
        """
        return self._jobs.get(job_id)
    
    @property
    def job_count(self) -> int:
        """Get the total number of jobs."""
        return len(self._jobs)
    
    @property
    def active_job_count(self) -> int:
        """Get the number of enabled jobs."""
        return sum(1 for j in self._jobs.values() if j.config.enabled)
    
    def get_history_count(self, job_id: str) -> int:
        """Get the number of history records for a job."""
        return len(self._history.get(job_id, []))
