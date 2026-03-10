"""
Approval Expiry Scheduler

Provides automated scheduling for marking expired approval requests.
Runs periodically to check and expire old pending approvals.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.database.connection import db_manager

logger = logging.getLogger(__name__)


@dataclass
class ApprovalScheduleConfig:
    """Configuration for approval expiry scheduling."""
    # Daily expiry check at 1 AM
    expiry_check_hour: int = 1
    expiry_check_minute: int = 0
    
    # Alternative: Run every N hours
    use_interval: bool = False
    interval_hours: int = 6
    
    # Enable/disable the task
    enable_expiry_check: bool = True


class ApprovalExpiryScheduler:
    """Scheduler for automated approval expiry checks."""
    
    def __init__(self, schedule_config: ApprovalScheduleConfig = None):
        """
        Initialize approval expiry scheduler.
        
        Args:
            schedule_config: Configuration for scheduling (optional)
        """
        self.schedule_config = schedule_config or ApprovalScheduleConfig()
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        
        # Track task execution history
        self.last_run: Optional[datetime] = None
        self.last_expired_count: int = 0
        self.total_runs: int = 0
        self.total_expired: int = 0
    
    async def start_scheduler(self):
        """Start the approval expiry scheduler."""
        if self.is_running:
            logger.warning("Approval expiry scheduler is already running")
            return
        
        try:
            if not self.schedule_config.enable_expiry_check:
                logger.info("Approval expiry check is disabled in configuration")
                return
            
            # Schedule expiry check task
            if self.schedule_config.use_interval:
                # Use interval-based scheduling
                self.scheduler.add_job(
                    self._run_expiry_check,
                    trigger=IntervalTrigger(hours=self.schedule_config.interval_hours),
                    id='approval_expiry_check',
                    name='Approval Expiry Check',
                    max_instances=1,
                    coalesce=True
                )
                logger.info(
                    f"Scheduled approval expiry check every "
                    f"{self.schedule_config.interval_hours} hours"
                )
            else:
                # Use cron-based scheduling (daily at specific time)
                self.scheduler.add_job(
                    self._run_expiry_check,
                    trigger=CronTrigger(
                        hour=self.schedule_config.expiry_check_hour,
                        minute=self.schedule_config.expiry_check_minute
                    ),
                    id='approval_expiry_check',
                    name='Approval Expiry Check',
                    max_instances=1,
                    coalesce=True
                )
                logger.info(
                    f"Scheduled daily approval expiry check at "
                    f"{self.schedule_config.expiry_check_hour:02d}:"
                    f"{self.schedule_config.expiry_check_minute:02d}"
                )
            
            # Start the scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Approval expiry scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start approval expiry scheduler: {e}")
            raise
    
    async def stop_scheduler(self):
        """Stop the approval expiry scheduler."""
        if not self.is_running:
            logger.warning("Approval expiry scheduler is not running")
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Approval expiry scheduler stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop approval expiry scheduler: {e}")
            raise
    
    async def _run_expiry_check(self):
        """Execute the approval expiry check task."""
        task_start = datetime.utcnow()
        
        logger.info("Starting scheduled approval expiry check")
        
        try:
            # Get database session
            async with db_manager.get_session() as session:
                # Import here to avoid circular dependency
                from src.services.approval_service import ApprovalService
                
                # Create approval service
                approval_service = ApprovalService(session)
                
                # Run expiry check
                expired_count = approval_service.expire_old_approvals()
                
                # Update statistics
                self.last_run = task_start
                self.last_expired_count = expired_count
                self.total_runs += 1
                self.total_expired += expired_count
                
                task_duration = (datetime.utcnow() - task_start).total_seconds()
                
                logger.info(
                    f"Approval expiry check completed: "
                    f"{expired_count} approvals expired in {task_duration:.2f}s"
                )
                
                # Log warning if many approvals expired
                if expired_count > 10:
                    logger.warning(
                        f"Large number of approvals expired ({expired_count}). "
                        f"Consider reviewing approval workflow."
                    )
                
        except Exception as e:
            logger.error(f"Failed to run approval expiry check: {e}", exc_info=True)
            raise
    
    async def run_manual_check(self) -> Dict[str, Any]:
        """
        Manually trigger an expiry check (for testing or admin use).
        
        Returns:
            Dictionary with check results
        """
        if not self.is_running:
            raise RuntimeError("Scheduler is not running")
        
        task_start = datetime.utcnow()
        
        try:
            async with db_manager.get_session() as session:
                from src.services.approval_service import ApprovalService
                
                approval_service = ApprovalService(session)
                expired_count = approval_service.expire_old_approvals()
                
                task_duration = (datetime.utcnow() - task_start).total_seconds()
                
                return {
                    "success": True,
                    "expired_count": expired_count,
                    "duration_seconds": task_duration,
                    "timestamp": task_start.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Manual expiry check failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": task_start.isoformat()
            }
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get scheduler status and statistics.
        
        Returns:
            Dictionary with scheduler status information
        """
        jobs = []
        if self.is_running:
            for job in self.scheduler.get_jobs():
                next_run = job.next_run_time
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": next_run.isoformat() if next_run else None,
                    "trigger": str(job.trigger)
                })
        
        return {
            "is_running": self.is_running,
            "config": {
                "use_interval": self.schedule_config.use_interval,
                "interval_hours": self.schedule_config.interval_hours,
                "expiry_check_hour": self.schedule_config.expiry_check_hour,
                "expiry_check_minute": self.schedule_config.expiry_check_minute,
                "enabled": self.schedule_config.enable_expiry_check
            },
            "statistics": {
                "last_run": self.last_run.isoformat() if self.last_run else None,
                "last_expired_count": self.last_expired_count,
                "total_runs": self.total_runs,
                "total_expired": self.total_expired
            },
            "jobs": jobs
        }


# Global scheduler instance
_approval_scheduler: Optional[ApprovalExpiryScheduler] = None


async def get_approval_scheduler() -> ApprovalExpiryScheduler:
    """
    Get or create the global approval scheduler instance.
    
    Returns:
        Global ApprovalExpiryScheduler instance
    """
    global _approval_scheduler
    
    if _approval_scheduler is None:
        _approval_scheduler = ApprovalExpiryScheduler()
        await _approval_scheduler.start_scheduler()
    
    return _approval_scheduler


async def start_approval_scheduler(config: ApprovalScheduleConfig = None):
    """
    Start the global approval scheduler.
    
    Args:
        config: Optional configuration for the scheduler
    """
    global _approval_scheduler
    
    if _approval_scheduler is not None and _approval_scheduler.is_running:
        logger.warning("Approval scheduler is already running")
        return
    
    _approval_scheduler = ApprovalExpiryScheduler(config)
    await _approval_scheduler.start_scheduler()


async def stop_approval_scheduler():
    """Stop the global approval scheduler."""
    global _approval_scheduler
    
    if _approval_scheduler is not None:
        await _approval_scheduler.stop_scheduler()
        _approval_scheduler = None
