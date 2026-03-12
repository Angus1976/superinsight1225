"""
Output Sync Alert Service.

Monitors output sync failures and triggers alerts when thresholds are exceeded.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import db_manager
from src.sync.models import SyncJobModel, SyncExecutionModel, SyncExecutionStatus
from src.sync.monitoring.alert_rules import (
    sync_alert_manager,
    AlertRule,
    AlertSeverity,
    AlertCategory
)
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class OutputSyncAlertService:
    """
    Alert service for output sync monitoring.
    
    Features:
    - Monitor output sync failure rates
    - Trigger alerts when thresholds exceeded
    - Auto-pause jobs with high failure rates
    - Send notifications to administrators
    """
    
    # Default alert thresholds
    DEFAULT_FAILURE_RATE_WARNING = 0.20  # 20%
    DEFAULT_FAILURE_RATE_CRITICAL = 0.50  # 50%
    DEFAULT_EVALUATION_WINDOW_HOURS = 24
    DEFAULT_MIN_EXECUTIONS = 5  # Minimum executions before alerting
    
    def __init__(self, notification_service: Optional[NotificationService] = None):
        self.notification_service = notification_service
        self._register_alert_rules()
    
    def _register_alert_rules(self):
        """Register output sync alert rules."""
        # Output sync high failure rate
        sync_alert_manager.add_rule(AlertRule(
            name="output_sync_high_failure_rate",
            description="Output sync failure rate is high",
            metric="output_sync_failure_rate",
            condition="gt",
            threshold=self.DEFAULT_FAILURE_RATE_WARNING,
            severity=AlertSeverity.WARNING,
            category=AlertCategory.QUALITY,
            duration_seconds=300,  # 5 minutes
            annotations={
                "summary": "Output sync failure rate > 20%",
                "description": "Multiple output sync executions are failing"
            }
        ))
        
        # Output sync critical failure rate
        sync_alert_manager.add_rule(AlertRule(
            name="output_sync_critical_failure_rate",
            description="Output sync failure rate is critically high",
            metric="output_sync_failure_rate",
            condition="gt",
            threshold=self.DEFAULT_FAILURE_RATE_CRITICAL,
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.QUALITY,
            annotations={
                "summary": "Output sync failure rate > 50%",
                "description": "Critical: Most output sync executions are failing"
            }
        ))
        
        # Target database unreachable
        sync_alert_manager.add_rule(AlertRule(
            name="target_database_unreachable",
            description="Target database is unreachable",
            metric="target_connection_failures",
            condition="gt",
            threshold=3,  # 3 consecutive failures
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.AVAILABILITY,
            annotations={
                "summary": "Target database unreachable",
                "description": "Cannot connect to target database"
            }
        ))
    
    async def evaluate_job_failure_rate(
        self,
        job_id: UUID,
        window_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluate failure rate for a specific job.
        
        Args:
            job_id: Sync job ID
            window_hours: Evaluation window in hours
            
        Returns:
            Evaluation result with failure rate and alert status
        """
        window_hours = window_hours or self.DEFAULT_EVALUATION_WINDOW_HOURS
        cutoff_time = datetime.utcnow() - timedelta(hours=window_hours)
        
        async with db_manager.get_session() as session:
            try:
                # Get job
                job_result = await session.execute(
                    select(SyncJobModel).where(SyncJobModel.id == job_id)
                )
                job = job_result.scalar_one_or_none()
                
                if not job:
                    return {
                        "job_id": str(job_id),
                        "error": "Job not found"
                    }
                
                # Count executions in window
                exec_count_result = await session.execute(
                    select(func.count(SyncExecutionModel.id))
                    .where(
                        SyncExecutionModel.job_id == job_id,
                        SyncExecutionModel.sync_direction == "output",
                        SyncExecutionModel.started_at >= cutoff_time
                    )
                )
                total_executions = exec_count_result.scalar() or 0
                
                # Count failed executions
                failed_count_result = await session.execute(
                    select(func.count(SyncExecutionModel.id))
                    .where(
                        SyncExecutionModel.job_id == job_id,
                        SyncExecutionModel.sync_direction == "output",
                        SyncExecutionModel.status == SyncExecutionStatus.FAILED,
                        SyncExecutionModel.started_at >= cutoff_time
                    )
                )
                failed_executions = failed_count_result.scalar() or 0
                
                # Calculate failure rate
                failure_rate = (
                    failed_executions / total_executions
                    if total_executions > 0 else 0.0
                )
                
                # Determine if alert should be triggered
                should_alert = (
                    total_executions >= self.DEFAULT_MIN_EXECUTIONS and
                    failure_rate >= self.DEFAULT_FAILURE_RATE_WARNING
                )
                
                alert_level = None
                if should_alert:
                    if failure_rate >= self.DEFAULT_FAILURE_RATE_CRITICAL:
                        alert_level = "critical"
                    else:
                        alert_level = "warning"
                
                # Report metric to alert manager
                if total_executions >= self.DEFAULT_MIN_EXECUTIONS:
                    sync_alert_manager.process_metric(
                        "output_sync_failure_rate",
                        failure_rate,
                        datetime.utcnow().timestamp(),
                        labels={"job_id": str(job_id)}
                    )
                
                result = {
                    "job_id": str(job_id),
                    "job_name": job.name,
                    "window_hours": window_hours,
                    "total_executions": total_executions,
                    "failed_executions": failed_executions,
                    "failure_rate": failure_rate,
                    "should_alert": should_alert,
                    "alert_level": alert_level,
                    "evaluated_at": datetime.utcnow().isoformat()
                }
                
                # Trigger alert if needed
                if should_alert:
                    await self._trigger_failure_rate_alert(
                        session, job, result
                    )
                
                # Auto-pause job if critical
                if alert_level == "critical":
                    await self._auto_pause_job(session, job, result)
                
                return result
                
            except Exception as e:
                logger.error(f"Failed to evaluate failure rate: {e}")
                return {
                    "job_id": str(job_id),
                    "error": str(e)
                }
    
    async def check_target_connectivity(
        self,
        job_id: UUID
    ) -> Dict[str, Any]:
        """
        Check target database connectivity for a job.
        
        Args:
            job_id: Sync job ID
            
        Returns:
            Connectivity check result
        """
        async with db_manager.get_session() as session:
            try:
                # Get job
                job_result = await session.execute(
                    select(SyncJobModel).where(SyncJobModel.id == job_id)
                )
                job = job_result.scalar_one_or_none()
                
                if not job or not job.target_source_id:
                    return {
                        "job_id": str(job_id),
                        "error": "Job or target not found"
                    }
                
                # Import connection test service
                from src.sync.push.connection_test_service import (
                    ConnectionTestService,
                    ConnectionStatus
                )
                
                test_service = ConnectionTestService()
                test_result = await test_service.test_connection(
                    job.target_source_id
                )
                
                # Track consecutive failures
                if test_result.status != ConnectionStatus.SUCCESS:
                    # Report to alert manager
                    consecutive_failures = getattr(
                        job, 'consecutive_connection_failures', 0
                    ) + 1
                    
                    sync_alert_manager.process_metric(
                        "target_connection_failures",
                        consecutive_failures,
                        datetime.utcnow().timestamp(),
                        labels={"job_id": str(job_id)}
                    )
                    
                    # Trigger alert if threshold exceeded
                    if consecutive_failures >= 3:
                        await self._trigger_connectivity_alert(
                            session, job, test_result
                        )
                        
                        # Auto-pause job
                        await self._auto_pause_job(
                            session, job,
                            {"reason": "target_unreachable"}
                        )
                
                return {
                    "job_id": str(job_id),
                    "target_id": str(job.target_source_id),
                    "status": test_result.status.value,
                    "error_message": test_result.error_message,
                    "troubleshooting": test_result.troubleshooting_suggestions,
                    "checked_at": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Failed to check target connectivity: {e}")
                return {
                    "job_id": str(job_id),
                    "error": str(e)
                }
    
    async def _trigger_failure_rate_alert(
        self,
        session: AsyncSession,
        job: SyncJobModel,
        evaluation_result: Dict[str, Any]
    ):
        """Trigger alert for high failure rate."""
        try:
            alert_message = (
                f"Output sync job '{job.name}' has high failure rate: "
                f"{evaluation_result['failure_rate']:.1%} "
                f"({evaluation_result['failed_executions']}/{evaluation_result['total_executions']} "
                f"executions failed in last {evaluation_result['window_hours']} hours)"
            )
            
            logger.warning(alert_message)
            
            # Send notification if service available
            if self.notification_service:
                # TODO: Get admin users from RBAC
                admin_users = []  # Placeholder
                
                for admin in admin_users:
                    await self.notification_service.send_approval_request_notification(
                        approver=admin,
                        approval=None,  # Custom notification
                        language="zh"
                    )
            
        except Exception as e:
            logger.error(f"Failed to trigger failure rate alert: {e}")
    
    async def _trigger_connectivity_alert(
        self,
        session: AsyncSession,
        job: SyncJobModel,
        test_result
    ):
        """Trigger alert for target connectivity issues."""
        try:
            alert_message = (
                f"Target database unreachable for job '{job.name}': "
                f"{test_result.error_message}"
            )
            
            logger.critical(alert_message)
            
            # Log troubleshooting suggestions
            if test_result.troubleshooting_suggestions:
                logger.info(
                    f"Troubleshooting suggestions: "
                    f"{', '.join(test_result.troubleshooting_suggestions)}"
                )
            
        except Exception as e:
            logger.error(f"Failed to trigger connectivity alert: {e}")
    
    async def _auto_pause_job(
        self,
        session: AsyncSession,
        job: SyncJobModel,
        context: Dict[str, Any]
    ):
        """Auto-pause job due to high failure rate or connectivity issues."""
        try:
            from src.sync.models import SyncJobStatus
            
            if job.status != SyncJobStatus.PAUSED:
                job.status = SyncJobStatus.PAUSED
                await session.flush()
                
                logger.warning(
                    f"Auto-paused job '{job.name}' due to: {context}"
                )
                
        except Exception as e:
            logger.error(f"Failed to auto-pause job: {e}")
    
    async def evaluate_all_output_jobs(
        self,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate failure rates for all output sync jobs.
        
        Args:
            tenant_id: Optional tenant filter
            
        Returns:
            List of evaluation results
        """
        async with db_manager.get_session() as session:
            try:
                # Get all output/bidirectional jobs
                from src.sync.models import SyncDirection
                
                query = select(SyncJobModel).where(
                    SyncJobModel.direction.in_([
                        SyncDirection.PUSH,
                        SyncDirection.BIDIRECTIONAL
                    ])
                )
                
                if tenant_id:
                    query = query.where(SyncJobModel.tenant_id == tenant_id)
                
                result = await session.execute(query)
                jobs = result.scalars().all()
                
                # Evaluate each job
                evaluations = []
                for job in jobs:
                    evaluation = await self.evaluate_job_failure_rate(job.id)
                    evaluations.append(evaluation)
                
                return evaluations
                
            except Exception as e:
                logger.error(f"Failed to evaluate all jobs: {e}")
                return []
