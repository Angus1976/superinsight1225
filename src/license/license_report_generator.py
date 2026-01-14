"""
License Report Generator for SuperInsight Platform.

Generates license usage reports and statistics.
"""

import io
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.license import (
    LicenseModel, LicenseAuditLogModel, ConcurrentSessionModel,
    LicenseEventType, LicenseStatus
)
from src.schemas.license import LicenseUsageReport, UsageReportRequest


class LicenseReportGenerator:
    """
    License Report Generator.
    
    Generates comprehensive license usage reports.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize License Report Generator.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def generate_usage_report(
        self,
        request: UsageReportRequest,
        license_id: Optional[UUID] = None
    ) -> LicenseUsageReport:
        """
        Generate comprehensive usage report.
        
        Args:
            request: Report request parameters
            license_id: Specific license ID (or use active license)
            
        Returns:
            Usage report
        """
        # Get license
        if license_id:
            result = await self.db.execute(
                select(LicenseModel).where(LicenseModel.id == license_id)
            )
        else:
            result = await self.db.execute(
                select(LicenseModel)
                .where(LicenseModel.status == LicenseStatus.ACTIVE)
                .order_by(LicenseModel.activated_at.desc())
                .limit(1)
            )
        
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            raise ValueError("No license found")
        
        # Generate report sections
        concurrent_stats = {}
        resource_stats = {}
        feature_stats = {}
        
        if request.include_sessions:
            concurrent_stats = await self._get_concurrent_user_stats(
                request.start_date, request.end_date
            )
        
        if request.include_resources:
            resource_stats = await self._get_resource_usage_stats(
                license_model.id, request.start_date, request.end_date
            )
        
        if request.include_features:
            feature_stats = await self._get_feature_usage_stats(
                license_model.id, request.start_date, request.end_date
            )
        
        # Get audit summary
        audit_summary = await self._get_audit_summary(
            license_model.id, request.start_date, request.end_date
        )
        
        return LicenseUsageReport(
            license_id=license_model.id,
            license_type=license_model.license_type,
            report_period={
                "start": request.start_date,
                "end": request.end_date,
            },
            concurrent_user_stats=concurrent_stats,
            resource_usage_stats=resource_stats,
            feature_usage_stats=feature_stats,
            audit_summary=audit_summary,
            generated_at=datetime.now(timezone.utc),
        )
    
    async def _get_concurrent_user_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get concurrent user statistics."""
        # Get session data
        result = await self.db.execute(
            select(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.login_time >= start_date)
            .where(ConcurrentSessionModel.login_time <= end_date)
        )
        sessions = result.scalars().all()
        
        if not sessions:
            return {
                "total_sessions": 0,
                "unique_users": 0,
                "peak_concurrent": 0,
                "average_session_duration_minutes": 0,
            }
        
        # Calculate statistics
        unique_users = len(set(s.user_id for s in sessions))
        
        # Calculate average session duration
        durations = []
        for session in sessions:
            if session.logout_time:
                duration = (session.logout_time - session.login_time).total_seconds() / 60
                durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Get peak concurrent from audit logs
        peak_result = await self.db.execute(
            select(func.max(LicenseAuditLogModel.details['current_users'].astext.cast(int)))
            .where(LicenseAuditLogModel.event_type == LicenseEventType.CONCURRENT_CHECK)
            .where(LicenseAuditLogModel.timestamp >= start_date)
            .where(LicenseAuditLogModel.timestamp <= end_date)
        )
        peak_concurrent = peak_result.scalar() or 0
        
        return {
            "total_sessions": len(sessions),
            "unique_users": unique_users,
            "peak_concurrent": peak_concurrent,
            "average_session_duration_minutes": round(avg_duration, 2),
        }
    
    async def _get_resource_usage_stats(
        self,
        license_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get resource usage statistics."""
        # Get resource check logs
        result = await self.db.execute(
            select(LicenseAuditLogModel)
            .where(LicenseAuditLogModel.event_type == LicenseEventType.RESOURCE_CHECK)
            .where(LicenseAuditLogModel.timestamp >= start_date)
            .where(LicenseAuditLogModel.timestamp <= end_date)
        )
        logs = result.scalars().all()
        
        if not logs:
            return {
                "cpu": {"checks": 0},
                "storage": {"checks": 0},
            }
        
        # Aggregate by resource type
        stats = {}
        for log in logs:
            resource_type = log.details.get("resource_type", "unknown")
            if resource_type not in stats:
                stats[resource_type] = {
                    "checks": 0,
                    "max_utilization": 0,
                    "avg_utilization": 0,
                    "utilizations": [],
                }
            
            stats[resource_type]["checks"] += 1
            utilization = log.details.get("utilization_percent", 0)
            stats[resource_type]["utilizations"].append(utilization)
            stats[resource_type]["max_utilization"] = max(
                stats[resource_type]["max_utilization"], utilization
            )
        
        # Calculate averages
        for resource_type in stats:
            utils = stats[resource_type].pop("utilizations")
            stats[resource_type]["avg_utilization"] = round(
                sum(utils) / len(utils) if utils else 0, 2
            )
        
        return stats
    
    async def _get_feature_usage_stats(
        self,
        license_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get feature usage statistics."""
        # Get feature access logs
        result = await self.db.execute(
            select(LicenseAuditLogModel)
            .where(LicenseAuditLogModel.event_type == LicenseEventType.FEATURE_ACCESS)
            .where(LicenseAuditLogModel.timestamp >= start_date)
            .where(LicenseAuditLogModel.timestamp <= end_date)
        )
        logs = result.scalars().all()
        
        if not logs:
            return {"total_accesses": 0, "by_feature": {}}
        
        # Aggregate by feature
        by_feature = {}
        for log in logs:
            feature = log.details.get("feature", "unknown")
            if feature not in by_feature:
                by_feature[feature] = {
                    "total": 0,
                    "allowed": 0,
                    "denied": 0,
                }
            
            by_feature[feature]["total"] += 1
            if log.success:
                by_feature[feature]["allowed"] += 1
            else:
                by_feature[feature]["denied"] += 1
        
        return {
            "total_accesses": len(logs),
            "by_feature": by_feature,
        }
    
    async def _get_audit_summary(
        self,
        license_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, int]:
        """Get audit event summary."""
        result = await self.db.execute(
            select(
                LicenseAuditLogModel.event_type,
                func.count(LicenseAuditLogModel.id)
            )
            .where(LicenseAuditLogModel.timestamp >= start_date)
            .where(LicenseAuditLogModel.timestamp <= end_date)
            .group_by(LicenseAuditLogModel.event_type)
        )
        rows = result.all()
        
        return {row[0].value: row[1] for row in rows}
    
    async def generate_daily_summary(
        self,
        date: datetime
    ) -> Dict[str, Any]:
        """
        Generate daily summary report.
        
        Args:
            date: Date for the summary
            
        Returns:
            Daily summary data
        """
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        request = UsageReportRequest(
            start_date=start,
            end_date=end,
            include_sessions=True,
            include_resources=True,
            include_features=True,
        )
        
        report = await self.generate_usage_report(request)
        
        return {
            "date": date.date().isoformat(),
            "license_id": str(report.license_id),
            "concurrent_users": report.concurrent_user_stats,
            "resources": report.resource_usage_stats,
            "features": report.feature_usage_stats,
            "events": report.audit_summary,
        }
    
    async def generate_trend_report(
        self,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Generate trend report for the last N days.
        
        Args:
            days: Number of days to include
            
        Returns:
            List of daily summaries
        """
        trends = []
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        for i in range(days):
            date = today - timedelta(days=i)
            try:
                summary = await self.generate_daily_summary(date)
                trends.append(summary)
            except Exception:
                # Skip days with no data
                pass
        
        return list(reversed(trends))
    
    async def export_report(
        self,
        report: LicenseUsageReport,
        format: str = "json"
    ) -> bytes:
        """
        Export report to file format.
        
        Args:
            report: Report to export
            format: Export format (json)
            
        Returns:
            Exported data as bytes
        """
        data = {
            "license_id": str(report.license_id),
            "license_type": report.license_type.value,
            "report_period": {
                "start": report.report_period["start"].isoformat(),
                "end": report.report_period["end"].isoformat(),
            },
            "concurrent_user_stats": report.concurrent_user_stats,
            "resource_usage_stats": report.resource_usage_stats,
            "feature_usage_stats": report.feature_usage_stats,
            "audit_summary": report.audit_summary,
            "generated_at": report.generated_at.isoformat(),
        }
        
        return json.dumps(data, indent=2).encode()
