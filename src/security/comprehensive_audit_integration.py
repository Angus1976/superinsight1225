"""
Comprehensive Audit Integration for SuperInsight Platform.

Ensures ALL user operations are comprehensively audited by integrating
audit logging at multiple levels: middleware, decorators, and manual logging.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
from sqlalchemy.orm import Session

from src.security.audit_middleware import ComprehensiveAuditMiddleware
from src.security.audit_service import EnhancedAuditService
from src.security.audit_decorators import audit_decorators
from src.security.models import AuditAction, UserModel
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)


class ComprehensiveAuditIntegration:
    """
    Comprehensive audit integration service that ensures complete audit coverage.
    
    Features:
    - Automatic middleware-based audit logging
    - Decorator-based endpoint audit logging
    - Manual audit logging for system operations
    - Audit coverage analysis and reporting
    - Real-time audit monitoring
    - Compliance reporting integration
    """
    
    def __init__(self):
        self.audit_service = EnhancedAuditService()
        self.middleware_enabled = False
        self.coverage_tracker = AuditCoverageTracker()
        self.real_time_monitor = RealTimeAuditMonitor()
        
        # Track all registered endpoints
        self.registered_endpoints: Set[str] = set()
        self.audited_endpoints: Set[str] = set()
        
    def integrate_with_fastapi(self, app: FastAPI):
        """
        Integrate comprehensive audit logging with FastAPI application.
        
        Args:
            app: FastAPI application instance
        """
        
        # Add comprehensive audit middleware
        app.add_middleware(ComprehensiveAuditMiddleware)
        self.middleware_enabled = True
        
        logger.info("Comprehensive audit middleware integrated with FastAPI")
        
        # Register startup and shutdown events
        @app.on_event("startup")
        async def audit_startup():
            await self.initialize_audit_system()
        
        @app.on_event("shutdown")
        async def audit_shutdown():
            await self.shutdown_audit_system()
    
    async def initialize_audit_system(self):
        """Initialize the comprehensive audit system."""
        
        logger.info("Initializing comprehensive audit system")
        
        try:
            # Start real-time monitoring
            await self.real_time_monitor.start()
            
            # Initialize coverage tracking
            await self.coverage_tracker.initialize()
            
            # Verify audit database tables
            await self._verify_audit_infrastructure()
            
            # Start background audit tasks
            await self._start_background_tasks()
            
            logger.info("Comprehensive audit system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize audit system: {e}")
            raise
    
    async def shutdown_audit_system(self):
        """Shutdown the comprehensive audit system."""
        
        logger.info("Shutting down comprehensive audit system")
        
        try:
            # Stop real-time monitoring
            await self.real_time_monitor.stop()
            
            # Generate final audit report
            await self._generate_shutdown_report()
            
            logger.info("Comprehensive audit system shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during audit system shutdown: {e}")
    
    async def log_system_operation(
        self,
        operation: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        tenant_id: str = "system"
    ):
        """
        Log system-level operations that don't go through API endpoints.
        
        Args:
            operation: Description of the operation
            resource_type: Type of resource affected
            resource_id: ID of the resource (if applicable)
            details: Additional operation details
            user_id: User ID (if operation is user-initiated)
            tenant_id: Tenant ID
        """
        
        try:
            db = get_db_session()
            try:
                await self.audit_service.log_enhanced_audit_event(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    action=AuditAction.UPDATE,  # System operations are typically updates
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details={
                        "operation_type": "system_operation",
                        "operation": operation,
                        "timestamp": datetime.utcnow().isoformat(),
                        **(details or {})
                    },
                    db=db
                )
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to log system operation: {e}")
    
    async def log_batch_operations(
        self,
        operations: List[Dict[str, Any]],
        tenant_id: str
    ):
        """
        Log multiple operations in batch for performance.
        
        Args:
            operations: List of operation dictionaries
            tenant_id: Tenant ID
        """
        
        try:
            db = get_db_session()
            try:
                # Convert operations to audit log format
                audit_actions = []
                
                for op in operations:
                    audit_actions.append({
                        "user_id": op.get("user_id"),
                        "tenant_id": tenant_id,
                        "action": op.get("action", "update"),
                        "resource_type": op.get("resource_type", "system"),
                        "resource_id": op.get("resource_id"),
                        "details": {
                            "batch_operation": True,
                            "operation_details": op.get("details", {}),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    })
                
                # Use bulk logging
                success = self.audit_service.log_bulk_actions(audit_actions, db)
                
                if success:
                    logger.info(f"Successfully logged {len(operations)} batch operations")
                else:
                    logger.error("Failed to log batch operations")
            finally:
                db.close()
                    
        except Exception as e:
            logger.error(f"Error logging batch operations: {e}")
    
    async def get_audit_coverage_report(self) -> Dict[str, Any]:
        """
        Generate audit coverage report showing which operations are being audited.
        
        Returns:
            Dictionary containing coverage statistics and recommendations
        """
        
        return await self.coverage_tracker.generate_coverage_report()
    
    async def get_real_time_audit_stats(self) -> Dict[str, Any]:
        """
        Get real-time audit statistics.
        
        Returns:
            Dictionary containing current audit statistics
        """
        
        return await self.real_time_monitor.get_current_stats()
    
    async def verify_audit_completeness(
        self,
        tenant_id: str,
        time_range: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Verify that all expected operations are being audited.
        
        Args:
            tenant_id: Tenant ID to check
            time_range: Time range to analyze (default: last 24 hours)
        
        Returns:
            Completeness verification report
        """
        
        if not time_range:
            time_range = timedelta(hours=24)
        
        start_time = datetime.utcnow() - time_range
        
        try:
            db = get_db_session()
            try:
                # Get audit statistics for the time range
                audit_stats = self.audit_service.get_security_summary(
                    tenant_id=tenant_id,
                    days=time_range.days or 1,
                    db=db
                )
                
                # Analyze coverage
                coverage_analysis = self._analyze_audit_coverage(
                    tenant_id, start_time, db
                )
                
                return {
                    "tenant_id": tenant_id,
                    "time_range": {
                        "start": start_time.isoformat(),
                        "end": datetime.utcnow().isoformat(),
                        "duration_hours": time_range.total_seconds() / 3600
                    },
                    "audit_statistics": audit_stats,
                    "coverage_analysis": coverage_analysis,
                    "completeness_score": self._calculate_completeness_score(
                        audit_stats, coverage_analysis
                    ),
                    "recommendations": self._generate_audit_recommendations(
                        audit_stats, coverage_analysis
                    )
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error verifying audit completeness: {e}")
            return {
                "error": str(e),
                "tenant_id": tenant_id,
                "status": "verification_failed"
            }
    
    async def _verify_audit_infrastructure(self):
        """Verify that audit infrastructure is properly set up."""
        
        try:
            db = get_db_session()
            try:
                # Test audit logging
                test_result = await self.audit_service.log_enhanced_audit_event(
                    user_id=None,
                    tenant_id="system",
                    action=AuditAction.READ,
                    resource_type="audit_system",
                    details={
                        "test": "infrastructure_verification",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    db=db
                )
                
                if test_result.get("status") == "success":
                    logger.info("Audit infrastructure verification successful")
                else:
                    raise Exception("Audit infrastructure test failed")
            finally:
                db.close()
                    
        except Exception as e:
            logger.error(f"Audit infrastructure verification failed: {e}")
            raise
    
    async def _start_background_tasks(self):
        """Start background audit tasks."""
        
        # Start periodic audit health checks
        asyncio.create_task(self._periodic_audit_health_check())
        
        # Start audit log rotation task
        asyncio.create_task(self._periodic_log_rotation())
        
        logger.info("Background audit tasks started")
    
    async def _periodic_audit_health_check(self):
        """Periodic audit system health check."""
        
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Perform health check
                health_status = await self._check_audit_health()
                
                if not health_status["healthy"]:
                    logger.warning(f"Audit health check failed: {health_status}")
                    
                    # Log health check failure
                    await self.log_system_operation(
                        operation="audit_health_check_failed",
                        resource_type="audit_system",
                        details=health_status
                    )
                
            except Exception as e:
                logger.error(f"Error in periodic audit health check: {e}")
    
    async def _periodic_log_rotation(self):
        """Periodic audit log rotation."""
        
        while True:
            try:
                # Run daily at 2 AM
                await asyncio.sleep(86400)  # 24 hours
                
                current_hour = datetime.utcnow().hour
                if current_hour == 2:  # 2 AM UTC
                    
                    # Perform log rotation for all tenants
                    db = get_db_session()
                    try:
                        rotation_result = self.audit_service.rotate_logs(
                            tenant_id="all",  # Special value for all tenants
                            retention_days=365,  # 1 year retention
                            db=db
                        )
                        
                        logger.info(f"Audit log rotation completed: {rotation_result}")
                    finally:
                        db.close()
                
            except Exception as e:
                logger.error(f"Error in periodic log rotation: {e}")
    
    async def _check_audit_health(self) -> Dict[str, Any]:
        """Check audit system health."""
        
        health_status = {
            "healthy": True,
            "checks": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Check database connectivity
            db = get_db_session()
            try:
                health_status["checks"]["database"] = "connected"
            finally:
                db.close()
            
            # Check middleware status
            health_status["checks"]["middleware"] = "enabled" if self.middleware_enabled else "disabled"
            
            # Check recent audit activity
            recent_activity = await self.real_time_monitor.get_recent_activity_count()
            health_status["checks"]["recent_activity"] = recent_activity
            
            # Check for any critical errors
            if recent_activity == 0:
                health_status["healthy"] = False
                health_status["issues"] = ["No recent audit activity detected"]
            
        except Exception as e:
            health_status["healthy"] = False
            health_status["error"] = str(e)
        
        return health_status
    
    def _analyze_audit_coverage(
        self,
        tenant_id: str,
        start_time: datetime,
        db: Session
    ) -> Dict[str, Any]:
        """Analyze audit coverage for a tenant."""
        
        # Get all audit events in time range
        audit_events = self.audit_service.search_logs(
            tenant_id=tenant_id,
            query_params={
                "start_date": start_time,
                "end_date": datetime.utcnow()
            },
            db=db
        )
        
        # Analyze coverage
        coverage_analysis = {
            "total_events": len(audit_events[0]) if audit_events else 0,
            "unique_actions": set(),
            "unique_resources": set(),
            "unique_users": set(),
            "time_distribution": {},
            "endpoint_coverage": {}
        }
        
        if audit_events and audit_events[0]:
            for event in audit_events[0]:
                coverage_analysis["unique_actions"].add(event.action.value)
                coverage_analysis["unique_resources"].add(event.resource_type)
                if event.user_id:
                    coverage_analysis["unique_users"].add(str(event.user_id))
        
        # Convert sets to counts for JSON serialization
        coverage_analysis["unique_actions"] = len(coverage_analysis["unique_actions"])
        coverage_analysis["unique_resources"] = len(coverage_analysis["unique_resources"])
        coverage_analysis["unique_users"] = len(coverage_analysis["unique_users"])
        
        return coverage_analysis
    
    def _calculate_completeness_score(
        self,
        audit_stats: Dict[str, Any],
        coverage_analysis: Dict[str, Any]
    ) -> float:
        """Calculate audit completeness score (0-100)."""
        
        score = 0.0
        
        # Base score for having audit events
        if audit_stats.get("total_events", 0) > 0:
            score += 30
        
        # Score for action diversity
        unique_actions = coverage_analysis.get("unique_actions", 0)
        if unique_actions >= 5:  # Good action diversity
            score += 25
        elif unique_actions >= 3:
            score += 15
        elif unique_actions >= 1:
            score += 5
        
        # Score for resource diversity
        unique_resources = coverage_analysis.get("unique_resources", 0)
        if unique_resources >= 10:  # Good resource diversity
            score += 25
        elif unique_resources >= 5:
            score += 15
        elif unique_resources >= 1:
            score += 5
        
        # Score for user activity
        unique_users = coverage_analysis.get("unique_users", 0)
        if unique_users >= 5:  # Multiple users active
            score += 20
        elif unique_users >= 1:
            score += 10
        
        return min(score, 100.0)
    
    def _generate_audit_recommendations(
        self,
        audit_stats: Dict[str, Any],
        coverage_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate audit improvement recommendations."""
        
        recommendations = []
        
        # Check for low activity
        if audit_stats.get("total_events", 0) < 100:
            recommendations.append(
                "Low audit activity detected. Verify that all API endpoints have audit decorators."
            )
        
        # Check for action diversity
        if coverage_analysis.get("unique_actions", 0) < 3:
            recommendations.append(
                "Limited action diversity. Ensure CREATE, UPDATE, DELETE operations are being audited."
            )
        
        # Check for resource diversity
        if coverage_analysis.get("unique_resources", 0) < 5:
            recommendations.append(
                "Limited resource diversity. Verify that all resource types are being audited."
            )
        
        # Check for user activity
        if coverage_analysis.get("unique_users", 0) < 2:
            recommendations.append(
                "Limited user activity in audit logs. Verify user authentication is working correctly."
            )
        
        # Check for failed operations
        if audit_stats.get("failed_logins", 0) > 10:
            recommendations.append(
                "High number of failed login attempts detected. Review security measures."
            )
        
        if not recommendations:
            recommendations.append("Audit coverage appears comprehensive. Continue monitoring.")
        
        return recommendations
    
    async def _generate_shutdown_report(self):
        """Generate final audit report during shutdown."""
        
        try:
            # Generate summary report
            summary = await self.get_real_time_audit_stats()
            
            logger.info(f"Final audit summary: {summary}")
            
            # Log shutdown event
            await self.log_system_operation(
                operation="audit_system_shutdown",
                resource_type="audit_system",
                details={
                    "final_stats": summary,
                    "shutdown_time": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating shutdown report: {e}")


class AuditCoverageTracker:
    """Tracks audit coverage across the application."""
    
    def __init__(self):
        self.tracked_endpoints: Set[str] = set()
        self.audited_endpoints: Set[str] = set()
        self.coverage_stats = {}
    
    async def initialize(self):
        """Initialize coverage tracking."""
        logger.info("Audit coverage tracker initialized")
    
    async def register_endpoint(self, endpoint: str, has_audit: bool = False):
        """Register an endpoint for coverage tracking."""
        self.tracked_endpoints.add(endpoint)
        if has_audit:
            self.audited_endpoints.add(endpoint)
    
    async def generate_coverage_report(self) -> Dict[str, Any]:
        """Generate coverage report."""
        
        total_endpoints = len(self.tracked_endpoints)
        audited_endpoints = len(self.audited_endpoints)
        
        coverage_percentage = (
            (audited_endpoints / total_endpoints * 100) 
            if total_endpoints > 0 else 0
        )
        
        return {
            "total_endpoints": total_endpoints,
            "audited_endpoints": audited_endpoints,
            "coverage_percentage": coverage_percentage,
            "unaudited_endpoints": list(
                self.tracked_endpoints - self.audited_endpoints
            ),
            "recommendations": self._generate_coverage_recommendations(coverage_percentage)
        }
    
    def _generate_coverage_recommendations(self, coverage_percentage: float) -> List[str]:
        """Generate coverage improvement recommendations."""
        
        recommendations = []
        
        if coverage_percentage < 50:
            recommendations.append("Critical: Less than 50% of endpoints have audit logging")
        elif coverage_percentage < 80:
            recommendations.append("Warning: Less than 80% of endpoints have audit logging")
        elif coverage_percentage < 95:
            recommendations.append("Good: Most endpoints have audit logging, consider adding to remaining endpoints")
        else:
            recommendations.append("Excellent: Comprehensive audit coverage achieved")
        
        return recommendations


class RealTimeAuditMonitor:
    """Real-time audit monitoring and statistics."""
    
    def __init__(self):
        self.stats = {
            "events_per_minute": 0,
            "total_events": 0,
            "unique_users": set(),
            "unique_resources": set(),
            "start_time": None
        }
        self.running = False
    
    async def start(self):
        """Start real-time monitoring."""
        self.stats["start_time"] = datetime.utcnow()
        self.running = True
        logger.info("Real-time audit monitor started")
    
    async def stop(self):
        """Stop real-time monitoring."""
        self.running = False
        logger.info("Real-time audit monitor stopped")
    
    async def record_event(self, event_data: Dict[str, Any]):
        """Record an audit event for monitoring."""
        if not self.running:
            return
        
        self.stats["total_events"] += 1
        
        if "user_id" in event_data:
            self.stats["unique_users"].add(event_data["user_id"])
        
        if "resource_type" in event_data:
            self.stats["unique_resources"].add(event_data["resource_type"])
    
    async def get_current_stats(self) -> Dict[str, Any]:
        """Get current monitoring statistics."""
        
        uptime = (
            datetime.utcnow() - self.stats["start_time"]
            if self.stats["start_time"] else timedelta(0)
        )
        
        return {
            "running": self.running,
            "uptime_seconds": uptime.total_seconds(),
            "total_events": self.stats["total_events"],
            "unique_users": len(self.stats["unique_users"]),
            "unique_resources": len(self.stats["unique_resources"]),
            "events_per_hour": (
                self.stats["total_events"] / (uptime.total_seconds() / 3600)
                if uptime.total_seconds() > 0 else 0
            )
        }
    
    async def get_recent_activity_count(self, minutes: int = 5) -> int:
        """Get count of recent audit activity."""
        # In a real implementation, this would query the database
        # For now, return a placeholder
        return self.stats["total_events"]


# Global comprehensive audit integration instance
comprehensive_audit = ComprehensiveAuditIntegration()