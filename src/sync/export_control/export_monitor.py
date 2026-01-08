"""
Export Monitor Service for tracking and analyzing export behavior.

Provides comprehensive monitoring of exported data usage, access patterns,
security analysis, and compliance reporting.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from dataclasses import dataclass
import json
from collections import defaultdict

from src.database.connection import get_db_session
from .models import (
    ExportRequestModel, ExportTrackingModel, ExportBehaviorModel,
    ExportBehaviorType
)

logger = logging.getLogger(__name__)


@dataclass
class AccessEvent:
    """Access event data."""
    export_request_id: UUID
    accessor_id: Optional[UUID]
    access_type: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    access_method: str
    file_path: Optional[str]
    bytes_transferred: Optional[int]
    access_duration: Optional[float]


@dataclass
class BehaviorEvent:
    """Behavior event data."""
    export_request_id: UUID
    user_id: UUID
    session_id: str
    behavior_type: ExportBehaviorType
    behavior_details: Dict[str, Any]
    device_type: Optional[str]
    browser_type: Optional[str]
    shared_with: Optional[List[str]]


@dataclass
class SecurityAlert:
    """Security alert for suspicious behavior."""
    alert_id: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    alert_type: str
    export_request_id: UUID
    user_id: Optional[UUID]
    description: str
    risk_score: float
    evidence: Dict[str, Any]
    recommendations: List[str]
    created_at: datetime


class ExportMonitorService:
    """
    Export monitor service for tracking and analyzing export behavior.
    
    Provides comprehensive monitoring, security analysis, and compliance
    reporting for exported data usage.
    """
    
    def __init__(self):
        self.risk_thresholds = {
            "multiple_downloads": 3,
            "unusual_access_time": {"start": 22, "end": 6},  # 10 PM to 6 AM
            "multiple_ips": 3,
            "large_transfer": 100 * 1024 * 1024,  # 100 MB
            "sharing_threshold": 5,
            "access_frequency": 10  # per hour
        }
    
    def track_access_event(
        self,
        event: AccessEvent,
        db: Optional[Session] = None
    ) -> UUID:
        """
        Track data export access event.
        
        Args:
            event: Access event data
            db: Database session
            
        Returns:
            Tracking record ID
        """
        if db is None:
            db = next(get_db_session())
        
        try:
            # Calculate risk score
            risk_score = self._calculate_access_risk_score(event, db)
            
            # Detect anomalies
            anomaly_flags = self._detect_access_anomalies(event, db)
            
            # Determine geographic location (simplified)
            geo_info = self._get_geographic_info(event.ip_address)
            
            # Create tracking record
            tracking_record = ExportTrackingModel(
                export_request_id=event.export_request_id,
                tenant_id=self._get_tenant_id(event.export_request_id, db),
                accessor_id=event.accessor_id,
                access_type=event.access_type,
                session_id=event.session_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                country=geo_info.get("country"),
                region=geo_info.get("region"),
                city=geo_info.get("city"),
                access_method=event.access_method,
                file_path=event.file_path,
                bytes_transferred=event.bytes_transferred,
                access_duration_seconds=event.access_duration,
                suspicious_activity=risk_score > 0.7,
                risk_score=risk_score,
                anomaly_flags=anomaly_flags
            )
            
            db.add(tracking_record)
            db.commit()
            db.refresh(tracking_record)
            
            # Check for security alerts
            if risk_score > 0.7 or anomaly_flags:
                self._check_security_alerts(tracking_record, db)
            
            logger.info(f"Access event tracked: {tracking_record.id}")
            return tracking_record.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error tracking access event: {e}")
            raise
    
    def track_behavior_event(
        self,
        event: BehaviorEvent,
        db: Optional[Session] = None
    ) -> UUID:
        """
        Track user behavior with exported data.
        
        Args:
            event: Behavior event data
            db: Database session
            
        Returns:
            Behavior record ID
        """
        if db is None:
            db = next(get_db_session())
        
        try:
            # Check for existing behavior record for this session
            existing_behavior = db.query(ExportBehaviorModel).filter(
                and_(
                    ExportBehaviorModel.export_request_id == event.export_request_id,
                    ExportBehaviorModel.user_id == event.user_id,
                    ExportBehaviorModel.session_id == event.session_id,
                    ExportBehaviorModel.behavior_type == event.behavior_type
                )
            ).first()
            
            if existing_behavior:
                # Update existing record
                existing_behavior.interaction_count += 1
                existing_behavior.last_interaction = datetime.utcnow()
                existing_behavior.behavior_details.update(event.behavior_details)
                
                if event.shared_with:
                    existing_behavior.shared_with = (existing_behavior.shared_with or []) + event.shared_with
                
                behavior_record = existing_behavior
            else:
                # Create new behavior record
                compliance_status, policy_violations = self._analyze_compliance(event, db)
                risk_indicators = self._identify_risk_indicators(event, db)
                
                behavior_record = ExportBehaviorModel(
                    export_request_id=event.export_request_id,
                    tenant_id=self._get_tenant_id(event.export_request_id, db),
                    user_id=event.user_id,
                    session_id=event.session_id,
                    behavior_type=event.behavior_type,
                    behavior_details=event.behavior_details,
                    device_type=event.device_type,
                    browser_type=event.browser_type,
                    shared_with=event.shared_with,
                    compliance_status=compliance_status,
                    policy_violations=policy_violations,
                    risk_indicators=risk_indicators
                )
                
                db.add(behavior_record)
            
            db.commit()
            db.refresh(behavior_record)
            
            # Check for policy violations
            if policy_violations:
                self._handle_policy_violations(behavior_record, db)
            
            logger.info(f"Behavior event tracked: {behavior_record.id}")
            return behavior_record.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error tracking behavior event: {e}")
            raise
    
    def get_export_usage_analytics(
        self,
        export_request_id: UUID,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive usage analytics for export.
        
        Args:
            export_request_id: Export request ID
            db: Database session
            
        Returns:
            Usage analytics dictionary
        """
        if db is None:
            db = next(get_db_session())
        
        # Get export request
        export_request = db.query(ExportRequestModel).filter(
            ExportRequestModel.id == export_request_id
        ).first()
        
        if not export_request:
            return {"error": "Export request not found"}
        
        # Get tracking records
        tracking_records = db.query(ExportTrackingModel).filter(
            ExportTrackingModel.export_request_id == export_request_id
        ).all()
        
        # Get behavior records
        behavior_records = db.query(ExportBehaviorModel).filter(
            ExportBehaviorModel.export_request_id == export_request_id
        ).all()
        
        # Calculate analytics
        analytics = {
            "export_info": {
                "export_id": str(export_request.id),
                "created_at": export_request.created_at.isoformat(),
                "requester_id": str(export_request.requester_id),
                "status": export_request.status.value,
                "format": export_request.export_format.value,
                "table_count": len(export_request.table_names),
                "estimated_records": export_request.estimated_records
            },
            "access_summary": self._calculate_access_summary(tracking_records),
            "behavior_summary": self._calculate_behavior_summary(behavior_records),
            "security_analysis": self._calculate_security_analysis(tracking_records, behavior_records),
            "compliance_status": self._calculate_compliance_status(behavior_records),
            "geographic_distribution": self._calculate_geographic_distribution(tracking_records),
            "timeline": self._generate_usage_timeline(tracking_records, behavior_records)
        }
        
        return analytics
    
    def get_tenant_export_dashboard(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Get tenant-wide export monitoring dashboard.
        
        Args:
            tenant_id: Tenant ID
            start_date: Start date for analysis
            end_date: End date for analysis
            db: Database session
            
        Returns:
            Dashboard data dictionary
        """
        if db is None:
            db = next(get_db_session())
        
        # Default to last 30 days
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get export requests in period
        export_requests = db.query(ExportRequestModel).filter(
            and_(
                ExportRequestModel.tenant_id == tenant_id,
                ExportRequestModel.created_at >= start_date,
                ExportRequestModel.created_at <= end_date
            )
        ).all()
        
        export_ids = [er.id for er in export_requests]
        
        # Get tracking and behavior data
        tracking_records = db.query(ExportTrackingModel).filter(
            and_(
                ExportTrackingModel.tenant_id == tenant_id,
                ExportTrackingModel.export_request_id.in_(export_ids)
            )
        ).all() if export_ids else []
        
        behavior_records = db.query(ExportBehaviorModel).filter(
            and_(
                ExportBehaviorModel.tenant_id == tenant_id,
                ExportBehaviorModel.export_request_id.in_(export_ids)
            )
        ).all() if export_ids else []
        
        # Calculate dashboard metrics
        dashboard = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": (end_date - start_date).days
            },
            "export_metrics": {
                "total_exports": len(export_requests),
                "approved_exports": len([er for er in export_requests if er.status.value == "approved"]),
                "pending_exports": len([er for er in export_requests if er.status.value == "pending"]),
                "rejected_exports": len([er for er in export_requests if er.status.value == "rejected"]),
                "completed_exports": len([er for er in export_requests if er.status.value == "completed"])
            },
            "access_metrics": {
                "total_accesses": len(tracking_records),
                "unique_accessors": len(set(tr.accessor_id for tr in tracking_records if tr.accessor_id)),
                "total_bytes_transferred": sum(tr.bytes_transferred or 0 for tr in tracking_records),
                "suspicious_accesses": len([tr for tr in tracking_records if tr.suspicious_activity])
            },
            "behavior_metrics": {
                "total_interactions": sum(br.interaction_count for br in behavior_records),
                "sharing_events": len([br for br in behavior_records if br.behavior_type.value == "share"]),
                "policy_violations": len([br for br in behavior_records if br.policy_violations]),
                "compliance_issues": len([br for br in behavior_records if br.compliance_status != "compliant"])
            },
            "security_alerts": self._get_recent_security_alerts(tenant_id, start_date, end_date, db),
            "top_users": self._get_top_export_users(export_requests),
            "format_distribution": self._get_format_distribution(export_requests),
            "geographic_distribution": self._calculate_geographic_distribution(tracking_records)
        }
        
        return dashboard
    
    def detect_suspicious_behavior(
        self,
        tenant_id: str,
        lookback_hours: int = 24,
        db: Optional[Session] = None
    ) -> List[SecurityAlert]:
        """
        Detect suspicious behavior in export usage.
        
        Args:
            tenant_id: Tenant ID
            lookback_hours: Hours to look back for analysis
            db: Database session
            
        Returns:
            List of security alerts
        """
        if db is None:
            db = next(get_db_session())
        
        alerts = []
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        # Get recent tracking records
        tracking_records = db.query(ExportTrackingModel).filter(
            and_(
                ExportTrackingModel.tenant_id == tenant_id,
                ExportTrackingModel.accessed_at >= cutoff_time
            )
        ).all()
        
        # Get recent behavior records
        behavior_records = db.query(ExportBehaviorModel).filter(
            and_(
                ExportBehaviorModel.tenant_id == tenant_id,
                ExportBehaviorModel.last_interaction >= cutoff_time
            )
        ).all()
        
        # Detect multiple downloads from same user
        user_downloads = defaultdict(list)
        for tr in tracking_records:
            if tr.access_type == "download" and tr.accessor_id:
                user_downloads[tr.accessor_id].append(tr)
        
        for user_id, downloads in user_downloads.items():
            if len(downloads) >= self.risk_thresholds["multiple_downloads"]:
                alerts.append(SecurityAlert(
                    alert_id=f"multiple_downloads_{user_id}_{int(datetime.utcnow().timestamp())}",
                    severity="MEDIUM",
                    alert_type="multiple_downloads",
                    export_request_id=downloads[0].export_request_id,
                    user_id=user_id,
                    description=f"User downloaded {len(downloads)} files in {lookback_hours} hours",
                    risk_score=min(1.0, len(downloads) / 10),
                    evidence={"download_count": len(downloads), "files": [d.file_path for d in downloads]},
                    recommendations=["Review user access patterns", "Verify business need for multiple downloads"],
                    created_at=datetime.utcnow()
                ))
        
        # Detect excessive sharing
        sharing_events = [br for br in behavior_records if br.behavior_type == ExportBehaviorType.SHARE]
        user_sharing = defaultdict(int)
        for br in sharing_events:
            user_sharing[br.user_id] += len(br.shared_with or [])
        
        for user_id, share_count in user_sharing.items():
            if share_count >= self.risk_thresholds["sharing_threshold"]:
                alerts.append(SecurityAlert(
                    alert_id=f"excessive_sharing_{user_id}_{int(datetime.utcnow().timestamp())}",
                    severity="HIGH",
                    alert_type="excessive_sharing",
                    export_request_id=sharing_events[0].export_request_id,
                    user_id=user_id,
                    description=f"User shared data with {share_count} recipients",
                    risk_score=min(1.0, share_count / 20),
                    evidence={"share_count": share_count},
                    recommendations=["Review sharing policy compliance", "Verify recipient authorization"],
                    created_at=datetime.utcnow()
                ))
        
        # Detect unusual access times
        unusual_access = [
            tr for tr in tracking_records
            if (tr.accessed_at.hour >= self.risk_thresholds["unusual_access_time"]["start"] or
                tr.accessed_at.hour <= self.risk_thresholds["unusual_access_time"]["end"])
        ]
        
        if unusual_access:
            alerts.append(SecurityAlert(
                alert_id=f"unusual_access_time_{tenant_id}_{int(datetime.utcnow().timestamp())}",
                severity="LOW",
                alert_type="unusual_access_time",
                export_request_id=unusual_access[0].export_request_id,
                user_id=unusual_access[0].accessor_id,
                description=f"{len(unusual_access)} accesses during unusual hours",
                risk_score=0.3,
                evidence={"unusual_access_count": len(unusual_access)},
                recommendations=["Verify legitimate business need for off-hours access"],
                created_at=datetime.utcnow()
            ))
        
        return alerts
    
    def _calculate_access_risk_score(self, event: AccessEvent, db: Session) -> float:
        """Calculate risk score for access event."""
        
        risk_score = 0.0
        
        # Base risk by access type
        access_risk = {
            "download": 0.3,
            "view": 0.1,
            "share": 0.5,
            "copy": 0.4,
            "print": 0.2
        }
        
        risk_score += access_risk.get(event.access_type, 0.1)
        
        # Large file transfer
        if event.bytes_transferred and event.bytes_transferred > self.risk_thresholds["large_transfer"]:
            risk_score += 0.3
        
        # Unusual access time
        current_hour = datetime.utcnow().hour
        if (current_hour >= self.risk_thresholds["unusual_access_time"]["start"] or
            current_hour <= self.risk_thresholds["unusual_access_time"]["end"]):
            risk_score += 0.2
        
        # Multiple IPs for same user (check recent history)
        if event.accessor_id and event.ip_address:
            recent_ips = db.query(ExportTrackingModel.ip_address).filter(
                and_(
                    ExportTrackingModel.accessor_id == event.accessor_id,
                    ExportTrackingModel.accessed_at >= datetime.utcnow() - timedelta(hours=1)
                )
            ).distinct().all()
            
            unique_ips = set(ip[0] for ip in recent_ips if ip[0])
            if len(unique_ips) >= self.risk_thresholds["multiple_ips"]:
                risk_score += 0.4
        
        return min(1.0, risk_score)
    
    def _detect_access_anomalies(self, event: AccessEvent, db: Session) -> List[str]:
        """Detect anomalies in access pattern."""
        
        anomalies = []
        
        if not event.accessor_id:
            return anomalies
        
        # Check access frequency
        recent_accesses = db.query(ExportTrackingModel).filter(
            and_(
                ExportTrackingModel.accessor_id == event.accessor_id,
                ExportTrackingModel.accessed_at >= datetime.utcnow() - timedelta(hours=1)
            )
        ).count()
        
        if recent_accesses >= self.risk_thresholds["access_frequency"]:
            anomalies.append("high_frequency_access")
        
        # Check for new geographic location
        if event.ip_address:
            # Simplified - would use proper geolocation service
            pass
        
        return anomalies
    
    def _get_geographic_info(self, ip_address: Optional[str]) -> Dict[str, str]:
        """Get geographic information for IP address."""
        
        # Simplified implementation - would use proper geolocation service
        if not ip_address:
            return {}
        
        # Mock data for demonstration
        return {
            "country": "Unknown",
            "region": "Unknown", 
            "city": "Unknown"
        }
    
    def _get_tenant_id(self, export_request_id: UUID, db: Session) -> str:
        """Get tenant ID for export request."""
        
        export_request = db.query(ExportRequestModel).filter(
            ExportRequestModel.id == export_request_id
        ).first()
        
        return export_request.tenant_id if export_request else "unknown"
    
    def _calculate_access_summary(self, tracking_records: List[ExportTrackingModel]) -> Dict[str, Any]:
        """Calculate access summary statistics."""
        
        if not tracking_records:
            return {"total_accesses": 0}
        
        return {
            "total_accesses": len(tracking_records),
            "unique_accessors": len(set(tr.accessor_id for tr in tracking_records if tr.accessor_id)),
            "total_bytes_transferred": sum(tr.bytes_transferred or 0 for tr in tracking_records),
            "average_access_duration": sum(tr.access_duration_seconds or 0 for tr in tracking_records) / len(tracking_records),
            "suspicious_accesses": len([tr for tr in tracking_records if tr.suspicious_activity]),
            "access_methods": dict(
                (method, len([tr for tr in tracking_records if tr.access_method == method]))
                for method in set(tr.access_method for tr in tracking_records)
            ),
            "first_access": min(tr.accessed_at for tr in tracking_records).isoformat(),
            "last_access": max(tr.accessed_at for tr in tracking_records).isoformat()
        }
    
    def _calculate_behavior_summary(self, behavior_records: List[ExportBehaviorModel]) -> Dict[str, Any]:
        """Calculate behavior summary statistics."""
        
        if not behavior_records:
            return {"total_behaviors": 0}
        
        behavior_types = defaultdict(int)
        for br in behavior_records:
            behavior_types[br.behavior_type.value] += br.interaction_count
        
        return {
            "total_behaviors": len(behavior_records),
            "total_interactions": sum(br.interaction_count for br in behavior_records),
            "unique_users": len(set(br.user_id for br in behavior_records)),
            "behavior_types": dict(behavior_types),
            "sharing_events": len([br for br in behavior_records if br.behavior_type == ExportBehaviorType.SHARE]),
            "policy_violations": len([br for br in behavior_records if br.policy_violations]),
            "compliance_issues": len([br for br in behavior_records if br.compliance_status != "compliant"])
        }
    
    def _calculate_security_analysis(
        self,
        tracking_records: List[ExportTrackingModel],
        behavior_records: List[ExportBehaviorModel]
    ) -> Dict[str, Any]:
        """Calculate security analysis."""
        
        total_events = len(tracking_records) + len(behavior_records)
        if total_events == 0:
            return {"risk_level": "NONE"}
        
        # Calculate overall risk score
        tracking_risk = sum(tr.risk_score or 0 for tr in tracking_records)
        behavior_risk = len([br for br in behavior_records if br.policy_violations]) * 0.5
        
        overall_risk = (tracking_risk + behavior_risk) / total_events
        
        # Determine risk level
        if overall_risk >= 0.7:
            risk_level = "HIGH"
        elif overall_risk >= 0.4:
            risk_level = "MEDIUM"
        elif overall_risk >= 0.2:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"
        
        return {
            "risk_level": risk_level,
            "overall_risk_score": overall_risk,
            "suspicious_activities": len([tr for tr in tracking_records if tr.suspicious_activity]),
            "anomaly_count": sum(len(tr.anomaly_flags) for tr in tracking_records),
            "policy_violations": sum(len(br.policy_violations) for br in behavior_records)
        }
    
    def _calculate_compliance_status(self, behavior_records: List[ExportBehaviorModel]) -> Dict[str, Any]:
        """Calculate compliance status."""
        
        if not behavior_records:
            return {"status": "COMPLIANT"}
        
        compliant_records = len([br for br in behavior_records if br.compliance_status == "compliant"])
        compliance_rate = compliant_records / len(behavior_records)
        
        violations = []
        for br in behavior_records:
            violations.extend(br.policy_violations)
        
        return {
            "status": "COMPLIANT" if compliance_rate == 1.0 else "NON_COMPLIANT",
            "compliance_rate": compliance_rate,
            "total_violations": len(violations),
            "violation_types": list(set(violations))
        }
    
    def _calculate_geographic_distribution(self, tracking_records: List[ExportTrackingModel]) -> Dict[str, Any]:
        """Calculate geographic distribution of accesses."""
        
        countries = defaultdict(int)
        regions = defaultdict(int)
        
        for tr in tracking_records:
            if tr.country:
                countries[tr.country] += 1
            if tr.region:
                regions[tr.region] += 1
        
        return {
            "countries": dict(countries),
            "regions": dict(regions),
            "unique_countries": len(countries),
            "unique_regions": len(regions)
        }
    
    def _generate_usage_timeline(
        self,
        tracking_records: List[ExportTrackingModel],
        behavior_records: List[ExportBehaviorModel]
    ) -> List[Dict[str, Any]]:
        """Generate usage timeline."""
        
        timeline = []
        
        # Add tracking events
        for tr in tracking_records:
            timeline.append({
                "timestamp": tr.accessed_at.isoformat(),
                "type": "access",
                "event": tr.access_type,
                "user_id": str(tr.accessor_id) if tr.accessor_id else None,
                "details": {
                    "ip_address": tr.ip_address,
                    "bytes_transferred": tr.bytes_transferred,
                    "suspicious": tr.suspicious_activity
                }
            })
        
        # Add behavior events
        for br in behavior_records:
            timeline.append({
                "timestamp": br.last_interaction.isoformat(),
                "type": "behavior",
                "event": br.behavior_type.value,
                "user_id": str(br.user_id),
                "details": {
                    "interaction_count": br.interaction_count,
                    "shared_with": br.shared_with,
                    "policy_violations": br.policy_violations
                }
            })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])
        
        return timeline
    
    def _analyze_compliance(self, event: BehaviorEvent, db: Session) -> Tuple[str, List[str]]:
        """Analyze compliance for behavior event."""
        
        violations = []
        
        # Check sharing violations
        if event.behavior_type == ExportBehaviorType.SHARE:
            if event.shared_with and len(event.shared_with) > self.risk_thresholds["sharing_threshold"]:
                violations.append("excessive_sharing")
        
        # Check forwarding violations
        if event.behavior_type == ExportBehaviorType.FORWARD:
            violations.append("unauthorized_forwarding")
        
        compliance_status = "compliant" if not violations else "non_compliant"
        
        return compliance_status, violations
    
    def _identify_risk_indicators(self, event: BehaviorEvent, db: Session) -> List[str]:
        """Identify risk indicators for behavior event."""
        
        indicators = []
        
        # Multiple sharing recipients
        if event.shared_with and len(event.shared_with) > 3:
            indicators.append("multiple_recipients")
        
        # External sharing (simplified check)
        if event.shared_with:
            for recipient in event.shared_with:
                if "@" in recipient and not recipient.endswith("@company.com"):  # Example domain check
                    indicators.append("external_sharing")
                    break
        
        return indicators
    
    def _check_security_alerts(self, tracking_record: ExportTrackingModel, db: Session) -> None:
        """Check if tracking record should trigger security alerts."""
        
        if tracking_record.risk_score and tracking_record.risk_score > 0.8:
            logger.warning(
                f"High-risk export access: {tracking_record.access_type} "
                f"by {tracking_record.accessor_id} "
                f"(risk score: {tracking_record.risk_score})"
            )
        
        if tracking_record.anomaly_flags:
            logger.warning(
                f"Anomalous export access: {tracking_record.anomaly_flags} "
                f"by {tracking_record.accessor_id}"
            )
    
    def _handle_policy_violations(self, behavior_record: ExportBehaviorModel, db: Session) -> None:
        """Handle policy violations."""
        
        logger.warning(
            f"Policy violations detected: {behavior_record.policy_violations} "
            f"by user {behavior_record.user_id} "
            f"for export {behavior_record.export_request_id}"
        )
        
        # In production, this could trigger automated responses like:
        # - Revoking access
        # - Sending notifications to administrators
        # - Creating incident tickets
    
    def _get_recent_security_alerts(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get recent security alerts for tenant."""
        
        # This would query a security alerts table in production
        # For now, return mock data
        return [
            {
                "alert_id": "mock_alert_1",
                "severity": "MEDIUM",
                "type": "multiple_downloads",
                "description": "User downloaded multiple files",
                "created_at": datetime.utcnow().isoformat()
            }
        ]
    
    def _get_top_export_users(self, export_requests: List[ExportRequestModel]) -> List[Dict[str, Any]]:
        """Get top users by export count."""
        
        user_counts = defaultdict(int)
        for er in export_requests:
            user_counts[er.requester_id] += 1
        
        top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return [
            {"user_id": str(user_id), "export_count": count}
            for user_id, count in top_users
        ]
    
    def _get_format_distribution(self, export_requests: List[ExportRequestModel]) -> Dict[str, int]:
        """Get distribution of export formats."""
        
        format_counts = defaultdict(int)
        for er in export_requests:
            format_counts[er.export_format.value] += 1
        
        return dict(format_counts)