"""
Audit Log Archival Scheduler

Provides automated scheduling and execution of audit log archival and cleanup tasks.
Integrates with the existing task management system for background processing.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.security.audit_storage import OptimizedAuditStorage, StorageConfig
from src.database.connection import db_manager
from src.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ArchivalScheduleConfig:
    """Configuration for archival scheduling."""
    # Daily archival at 2 AM
    archival_hour: int = 2
    archival_minute: int = 0
    
    # Weekly cleanup on Sunday at 3 AM
    cleanup_day_of_week: int = 6  # Sunday
    cleanup_hour: int = 3
    cleanup_minute: int = 0
    
    # Monthly partition maintenance on 1st of month at 1 AM
    partition_maintenance_day: int = 1
    partition_maintenance_hour: int = 1
    partition_maintenance_minute: int = 0
    
    # Statistics collection every 6 hours
    stats_interval_hours: int = 6
    
    # Enable/disable individual tasks
    enable_archival: bool = True
    enable_cleanup: bool = True
    enable_partition_maintenance: bool = True
    enable_stats_collection: bool = True


class AuditArchivalScheduler:
    """Scheduler for automated audit log archival and maintenance tasks."""
    
    def __init__(
        self,
        storage_config: StorageConfig = None,
        schedule_config: ArchivalScheduleConfig = None
    ):
        """Initialize archival scheduler."""
        self.storage_config = storage_config or StorageConfig()
        self.schedule_config = schedule_config or ArchivalScheduleConfig()
        self.storage = OptimizedAuditStorage(self.storage_config)
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        
        # Track task execution
        self.task_history: List[Dict[str, Any]] = []
        self.max_history_entries = 100
    
    async def start_scheduler(self):
        """Start the archival scheduler."""
        if self.is_running:
            logger.warning("Archival scheduler is already running")
            return
        
        try:
            # Schedule archival task
            if self.schedule_config.enable_archival:
                self.scheduler.add_job(
                    self._run_archival_task,
                    trigger=CronTrigger(
                        hour=self.schedule_config.archival_hour,
                        minute=self.schedule_config.archival_minute
                    ),
                    id='audit_archival',
                    name='Audit Log Archival',
                    max_instances=1,
                    coalesce=True
                )
                logger.info(f"Scheduled daily archival at {self.schedule_config.archival_hour:02d}:{self.schedule_config.archival_minute:02d}")
            
            # Schedule cleanup task
            if self.schedule_config.enable_cleanup:
                self.scheduler.add_job(
                    self._run_cleanup_task,
                    trigger=CronTrigger(
                        day_of_week=self.schedule_config.cleanup_day_of_week,
                        hour=self.schedule_config.cleanup_hour,
                        minute=self.schedule_config.cleanup_minute
                    ),
                    id='audit_cleanup',
                    name='Audit Log Cleanup',
                    max_instances=1,
                    coalesce=True
                )
                logger.info(f"Scheduled weekly cleanup on day {self.schedule_config.cleanup_day_of_week} at {self.schedule_config.cleanup_hour:02d}:{self.schedule_config.cleanup_minute:02d}")
            
            # Schedule partition maintenance
            if self.schedule_config.enable_partition_maintenance:
                self.scheduler.add_job(
                    self._run_partition_maintenance,
                    trigger=CronTrigger(
                        day=self.schedule_config.partition_maintenance_day,
                        hour=self.schedule_config.partition_maintenance_hour,
                        minute=self.schedule_config.partition_maintenance_minute
                    ),
                    id='partition_maintenance',
                    name='Partition Maintenance',
                    max_instances=1,
                    coalesce=True
                )
                logger.info(f"Scheduled monthly partition maintenance on day {self.schedule_config.partition_maintenance_day} at {self.schedule_config.partition_maintenance_hour:02d}:{self.schedule_config.partition_maintenance_minute:02d}")
            
            # Schedule statistics collection
            if self.schedule_config.enable_stats_collection:
                self.scheduler.add_job(
                    self._collect_storage_statistics,
                    trigger=IntervalTrigger(hours=self.schedule_config.stats_interval_hours),
                    id='storage_stats',
                    name='Storage Statistics Collection',
                    max_instances=1,
                    coalesce=True
                )
                logger.info(f"Scheduled statistics collection every {self.schedule_config.stats_interval_hours} hours")
            
            # Start the scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Audit archival scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start archival scheduler: {e}")
            raise
    
    async def stop_scheduler(self):
        """Stop the archival scheduler."""
        if not self.is_running:
            logger.warning("Archival scheduler is not running")
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Audit archival scheduler stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop archival scheduler: {e}")
            raise
    
    async def _run_archival_task(self):
        """Execute archival task for all tenants."""
        task_start = datetime.now()
        task_id = f"archival_{task_start.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info("Starting scheduled audit log archival task")
        
        try:
            # Get list of all tenants (in a real system, this would query the tenant table)
            tenants = await self._get_active_tenants()
            
            total_stats = {
                "tenants_processed": 0,
                "total_logs_archived": 0,
                "total_logs_deleted": 0,
                "total_archive_files": 0,
                "processing_time_seconds": 0.0,
                "errors": []
            }
            
            # Process each tenant
            for tenant_id in tenants:
                try:
                    tenant_stats = await self.storage.archival_service.archive_old_logs(
                        tenant_id=tenant_id
                    )
                    
                    total_stats["tenants_processed"] += 1
                    total_stats["total_logs_archived"] += tenant_stats.get("logs_archived", 0)
                    total_stats["total_logs_deleted"] += tenant_stats.get("logs_deleted", 0)
                    total_stats["total_archive_files"] += tenant_stats.get("archive_files_created", 0)
                    
                    logger.debug(f"Archived logs for tenant {tenant_id}: {tenant_stats}")
                    
                except Exception as e:
                    error_msg = f"Failed to archive logs for tenant {tenant_id}: {e}"
                    logger.error(error_msg)
                    total_stats["errors"].append(error_msg)
            
            # Record task completion
            task_end = datetime.now()
            total_stats["processing_time_seconds"] = (task_end - task_start).total_seconds()
            
            self._record_task_execution("archival", task_id, total_stats, task_start, task_end)
            
            logger.info(f"Archival task completed: {total_stats['total_logs_archived']} logs archived "
                       f"for {total_stats['tenants_processed']} tenants in "
                       f"{total_stats['processing_time_seconds']:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Archival task failed: {e}")
            self._record_task_execution("archival", task_id, {"error": str(e)}, task_start, datetime.now())
    
    async def _run_cleanup_task(self):
        """Execute cleanup task for expired logs."""
        task_start = datetime.now()
        task_id = f"cleanup_{task_start.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info("Starting scheduled audit log cleanup task")
        
        try:
            # Get list of all tenants
            tenants = await self._get_active_tenants()
            
            total_stats = {
                "tenants_processed": 0,
                "total_logs_deleted": 0,
                "processing_time_seconds": 0.0,
                "errors": []
            }
            
            # Process each tenant
            for tenant_id in tenants:
                try:
                    tenant_stats = await self.storage.archival_service.cleanup_expired_logs(
                        tenant_id=tenant_id,
                        retention_days=self.storage_config.retention_days
                    )
                    
                    total_stats["tenants_processed"] += 1
                    total_stats["total_logs_deleted"] += tenant_stats.get("logs_deleted", 0)
                    
                    logger.debug(f"Cleaned up logs for tenant {tenant_id}: {tenant_stats}")
                    
                except Exception as e:
                    error_msg = f"Failed to cleanup logs for tenant {tenant_id}: {e}"
                    logger.error(error_msg)
                    total_stats["errors"].append(error_msg)
            
            # Record task completion
            task_end = datetime.now()
            total_stats["processing_time_seconds"] = (task_end - task_start).total_seconds()
            
            self._record_task_execution("cleanup", task_id, total_stats, task_start, task_end)
            
            logger.info(f"Cleanup task completed: {total_stats['total_logs_deleted']} logs deleted "
                       f"for {total_stats['tenants_processed']} tenants in "
                       f"{total_stats['processing_time_seconds']:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}")
            self._record_task_execution("cleanup", task_id, {"error": str(e)}, task_start, datetime.now())
    
    async def _run_partition_maintenance(self):
        """Execute partition maintenance tasks."""
        task_start = datetime.now()
        task_id = f"partition_maintenance_{task_start.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info("Starting scheduled partition maintenance task")
        
        try:
            # Create new partitions for the next 12 months
            partitions_created = await self.storage.partition_manager.create_monthly_partitions(
                datetime.now(), months_ahead=12
            )
            
            # Optimize partition indexes
            optimization_stats = await self.storage.partition_manager.optimize_partition_indexes()
            
            # Cleanup old partitions (if enabled)
            cleanup_stats = await self._cleanup_old_partitions()
            
            total_stats = {
                "partitions_created": len(partitions_created),
                "partitions_optimized": optimization_stats.get("partitions_optimized", 0),
                "old_partitions_cleaned": cleanup_stats.get("partitions_dropped", 0),
                "processing_time_seconds": (datetime.now() - task_start).total_seconds()
            }
            
            self._record_task_execution("partition_maintenance", task_id, total_stats, task_start, datetime.now())
            
            logger.info(f"Partition maintenance completed: {total_stats['partitions_created']} created, "
                       f"{total_stats['partitions_optimized']} optimized, "
                       f"{total_stats['old_partitions_cleaned']} cleaned up")
            
        except Exception as e:
            logger.error(f"Partition maintenance task failed: {e}")
            self._record_task_execution("partition_maintenance", task_id, {"error": str(e)}, task_start, datetime.now())
    
    async def _collect_storage_statistics(self):
        """Collect and store storage statistics."""
        task_start = datetime.now()
        task_id = f"stats_collection_{task_start.strftime('%Y%m%d_%H%M%S')}"
        
        logger.debug("Collecting storage statistics")
        
        try:
            # Get storage statistics
            storage_stats = self.storage.get_storage_statistics()
            
            # Store statistics in database
            await self._store_storage_statistics(storage_stats)
            
            total_stats = {
                "statistics_collected": True,
                "processing_time_seconds": (datetime.now() - task_start).total_seconds()
            }
            
            self._record_task_execution("stats_collection", task_id, total_stats, task_start, datetime.now())
            
            logger.debug("Storage statistics collection completed")
            
        except Exception as e:
            logger.error(f"Statistics collection task failed: {e}")
            self._record_task_execution("stats_collection", task_id, {"error": str(e)}, task_start, datetime.now())
    
    async def _get_active_tenants(self) -> List[str]:
        """Get list of active tenants."""
        try:
            with db_manager.get_session() as session:
                # In a real system, this would query the tenants table
                # For now, we'll get unique tenant_ids from audit_logs
                from sqlalchemy import select, distinct
                from src.security.models import AuditLogModel
                
                stmt = select(distinct(AuditLogModel.tenant_id))
                result = session.execute(stmt)
                tenants = [row[0] for row in result.fetchall()]
                
                return tenants
                
        except Exception as e:
            logger.error(f"Failed to get active tenants: {e}")
            return []
    
    async def _cleanup_old_partitions(self) -> Dict[str, Any]:
        """Cleanup old partitions beyond retention period."""
        try:
            with db_manager.get_session() as session:
                # Calculate cutoff date (7 years = 84 months)
                retention_months = (self.storage_config.retention_days // 30) + 1
                
                # Call the PostgreSQL function to cleanup old partitions
                result = session.execute(
                    "SELECT cleanup_old_audit_partitions(:retention_months)",
                    {"retention_months": retention_months}
                )
                
                cleanup_result = result.scalar()
                
                # Parse result to count dropped partitions
                if "No old partitions" in cleanup_result:
                    partitions_dropped = 0
                else:
                    partitions_dropped = cleanup_result.count("Dropped partition")
                
                return {
                    "partitions_dropped": partitions_dropped,
                    "cleanup_result": cleanup_result
                }
                
        except Exception as e:
            logger.error(f"Failed to cleanup old partitions: {e}")
            return {"partitions_dropped": 0, "error": str(e)}
    
    async def _store_storage_statistics(self, stats: Dict[str, Any]):
        """Store storage statistics in database."""
        try:
            with db_manager.get_session() as session:
                from sqlalchemy import text
                
                # Insert or update daily statistics
                # This would typically insert into audit_storage_stats table
                # For now, we'll just log the statistics
                logger.debug(f"Storage statistics: {stats}")
                
        except Exception as e:
            logger.error(f"Failed to store storage statistics: {e}")
    
    def _record_task_execution(
        self,
        task_type: str,
        task_id: str,
        stats: Dict[str, Any],
        start_time: datetime,
        end_time: datetime
    ):
        """Record task execution in history."""
        
        task_record = {
            "task_type": task_type,
            "task_id": task_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "stats": stats,
            "success": "error" not in stats
        }
        
        # Add to history
        self.task_history.append(task_record)
        
        # Limit history size
        if len(self.task_history) > self.max_history_entries:
            self.task_history = self.task_history[-self.max_history_entries:]
    
    def get_task_history(self, task_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get task execution history."""
        
        history = self.task_history
        
        # Filter by task type if specified
        if task_type:
            history = [task for task in history if task["task_type"] == task_type]
        
        # Return most recent entries
        return sorted(history, key=lambda x: x["start_time"], reverse=True)[:limit]
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status and configuration."""
        
        jobs = []
        if self.is_running:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })
        
        return {
            "is_running": self.is_running,
            "scheduled_jobs": jobs,
            "task_history_count": len(self.task_history),
            "configuration": {
                "archival_enabled": self.schedule_config.enable_archival,
                "cleanup_enabled": self.schedule_config.enable_cleanup,
                "partition_maintenance_enabled": self.schedule_config.enable_partition_maintenance,
                "stats_collection_enabled": self.schedule_config.enable_stats_collection,
                "retention_days": self.storage_config.retention_days,
                "archive_threshold_days": self.storage_config.archive_threshold_days
            }
        }
    
    async def run_manual_task(self, task_type: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Run a maintenance task manually."""
        
        if not self.is_running:
            raise RuntimeError("Scheduler is not running")
        
        task_start = datetime.now()
        task_id = f"manual_{task_type}_{task_start.strftime('%Y%m%d_%H%M%S')}"
        
        try:
            if task_type == "archival":
                if tenant_id:
                    stats = await self.storage.archival_service.archive_old_logs(tenant_id=tenant_id)
                else:
                    await self._run_archival_task()
                    stats = {"message": "Archival task completed for all tenants"}
                    
            elif task_type == "cleanup":
                if tenant_id:
                    stats = await self.storage.archival_service.cleanup_expired_logs(tenant_id=tenant_id)
                else:
                    await self._run_cleanup_task()
                    stats = {"message": "Cleanup task completed for all tenants"}
                    
            elif task_type == "partition_maintenance":
                await self._run_partition_maintenance()
                stats = {"message": "Partition maintenance completed"}
                
            elif task_type == "stats_collection":
                await self._collect_storage_statistics()
                stats = {"message": "Statistics collection completed"}
                
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            task_end = datetime.now()
            stats["processing_time_seconds"] = (task_end - task_start).total_seconds()
            
            self._record_task_execution(f"manual_{task_type}", task_id, stats, task_start, task_end)
            
            logger.info(f"Manual {task_type} task completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Manual {task_type} task failed: {e}")
            error_stats = {"error": str(e)}
            self._record_task_execution(f"manual_{task_type}", task_id, error_stats, task_start, datetime.now())
            raise


# Global scheduler instance
_audit_scheduler: Optional[AuditArchivalScheduler] = None


async def get_audit_scheduler() -> AuditArchivalScheduler:
    """Get or create the global audit scheduler instance."""
    global _audit_scheduler
    
    if _audit_scheduler is None:
        _audit_scheduler = AuditArchivalScheduler()
        await _audit_scheduler.start_scheduler()
    
    return _audit_scheduler


async def start_audit_archival_scheduler():
    """Start the audit archival scheduler."""
    scheduler = await get_audit_scheduler()
    logger.info("Audit archival scheduler service started")


async def stop_audit_archival_scheduler():
    """Stop the audit archival scheduler."""
    global _audit_scheduler
    
    if _audit_scheduler:
        await _audit_scheduler.stop_scheduler()
        _audit_scheduler = None
        logger.info("Audit archival scheduler service stopped")


# Utility functions for integration with existing systems

async def schedule_immediate_archival(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Schedule immediate archival for a tenant or all tenants."""
    scheduler = await get_audit_scheduler()
    return await scheduler.run_manual_task("archival", tenant_id)


async def schedule_immediate_cleanup(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Schedule immediate cleanup for a tenant or all tenants."""
    scheduler = await get_audit_scheduler()
    return await scheduler.run_manual_task("cleanup", tenant_id)


async def get_archival_status() -> Dict[str, Any]:
    """Get current archival scheduler status."""
    try:
        scheduler = await get_audit_scheduler()
        return scheduler.get_scheduler_status()
    except Exception as e:
        return {"error": str(e), "is_running": False}