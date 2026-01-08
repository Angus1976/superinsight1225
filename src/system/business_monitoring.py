"""
Enhanced Business Monitoring and Analytics for SuperInsight Platform.

Provides comprehensive business intelligence monitoring including:
- Real-time annotation efficiency tracking
- User engagement and activity analytics
- Project progress and completion monitoring
- AI model performance and quality metrics
- Cost and revenue analysis
- SLA compliance monitoring
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from decimal import Decimal
import statistics
import json

from src.system.monitoring import metrics_collector
from src.system.prometheus_integration import prometheus_exporter

logger = logging.getLogger(__name__)


@dataclass
class AnnotationTaskMetrics:
    """Detailed annotation task metrics."""
    task_id: str
    project_id: str
    user_id: str
    task_type: str
    start_time: float
    completion_time: Optional[float] = None
    quality_score: Optional[float] = None
    revision_count: int = 0
    ai_assistance_used: bool = False
    complexity_score: float = 1.0
    estimated_duration: Optional[float] = None
    actual_duration: Optional[float] = None


@dataclass
class UserEngagementMetrics:
    """User engagement and activity metrics."""
    user_id: str
    session_start: float
    last_activity: float
    actions_count: int = 0
    tasks_completed: int = 0
    quality_average: float = 0.0
    efficiency_score: float = 0.0
    engagement_level: str = "low"  # low, medium, high
    session_duration: float = 0.0


@dataclass
class ProjectHealthMetrics:
    """Project health and progress metrics."""
    project_id: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    pending_tasks: int
    blocked_tasks: int
    average_quality: float
    completion_velocity: float  # tasks per day
    estimated_completion: Optional[datetime] = None
    budget_utilization: float = 0.0
    team_size: int = 0
    health_score: float = 0.0


@dataclass
class AIModelPerformanceMetrics:
    """AI model performance and quality metrics."""
    model_name: str
    inference_count: int
    success_rate: float
    average_confidence: float
    accuracy_score: float
    processing_time_avg: float
    cost_per_inference: float = 0.0
    user_satisfaction: float = 0.0
    improvement_trend: str = "stable"  # improving, stable, declining


@dataclass
class BusinessKPIMetrics:
    """Key business performance indicators."""
    timestamp: float
    daily_annotations: int
    daily_revenue: Decimal
    user_retention_rate: float
    customer_satisfaction: float
    operational_efficiency: float
    cost_per_annotation: Decimal
    profit_margin: float
    sla_compliance: float


class BusinessMonitoringService:
    """
    Enhanced business monitoring and analytics service.
    
    Provides real-time business intelligence and performance monitoring
    for operational insights and decision support.
    """
    
    def __init__(self):
        # Metrics storage
        self.annotation_tasks: Dict[str, AnnotationTaskMetrics] = {}
        self.user_sessions: Dict[str, UserEngagementMetrics] = {}
        self.project_health: Dict[str, ProjectHealthMetrics] = {}
        self.ai_performance: Dict[str, AIModelPerformanceMetrics] = {}
        self.business_kpis: deque = deque(maxlen=1000)
        
        # Real-time tracking
        self.active_tasks: Dict[str, float] = {}  # task_id -> start_time
        self.user_activities: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.quality_trends: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Configuration
        self.collection_interval = 30  # seconds
        self.is_collecting = False
        self._collection_task: Optional[asyncio.Task] = None
        
        # SLA thresholds
        self.sla_thresholds = {
            "annotation_quality_min": 0.85,
            "task_completion_time_max": 3600,  # 1 hour
            "user_response_time_max": 300,     # 5 minutes
            "system_availability_min": 0.99,
            "ai_accuracy_min": 0.90
        }
        
        logger.info("Business monitoring service initialized")
    
    async def start_monitoring(self):
        """Start business monitoring collection."""
        if self.is_collecting:
            logger.warning("Business monitoring is already running")
            return
        
        self.is_collecting = True
        self._collection_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started business monitoring")
    
    async def stop_monitoring(self):
        """Stop business monitoring collection."""
        self.is_collecting = False
        
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped business monitoring")
    
    async def _monitoring_loop(self):
        """Main business monitoring loop."""
        while self.is_collecting:
            try:
                await self._collect_business_metrics()
                await self._update_project_health()
                await self._calculate_business_kpis()
                await self._check_sla_compliance()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in business monitoring loop: {e}")
                await asyncio.sleep(10)  # Short delay before retrying
    
    async def _collect_business_metrics(self):
        """Collect comprehensive business metrics."""
        try:
            current_time = time.time()
            
            # Update user engagement metrics
            await self._update_user_engagement()
            
            # Update annotation efficiency metrics
            await self._update_annotation_efficiency()
            
            # Update AI model performance
            await self._update_ai_performance()
            
            # Record metrics to Prometheus
            await self._record_prometheus_metrics()
            
        except Exception as e:
            logger.error(f"Failed to collect business metrics: {e}")
    
    async def _update_user_engagement(self):
        """Update user engagement and activity metrics."""
        try:
            current_time = time.time()
            
            # Clean up old sessions
            expired_sessions = []
            for user_id, session in self.user_sessions.items():
                if current_time - session.last_activity > 1800:  # 30 minutes timeout
                    expired_sessions.append(user_id)
            
            for user_id in expired_sessions:
                session = self.user_sessions[user_id]
                session.session_duration = session.last_activity - session.session_start
                
                # Calculate engagement level
                if session.session_duration > 3600 and session.actions_count > 50:
                    session.engagement_level = "high"
                elif session.session_duration > 1800 and session.actions_count > 20:
                    session.engagement_level = "medium"
                else:
                    session.engagement_level = "low"
                
                # Record final metrics
                prometheus_exporter.record_http_request("USER", "session_end", 200, session.session_duration)
                
                del self.user_sessions[user_id]
            
            # Update active session metrics
            active_users = len(self.user_sessions)
            high_engagement_users = len([s for s in self.user_sessions.values() if s.engagement_level == "high"])
            
            # Record to metrics collector
            metrics_collector.record_metric("business.users.active_count", active_users)
            metrics_collector.record_metric("business.users.high_engagement_count", high_engagement_users)
            
        except Exception as e:
            logger.error(f"Failed to update user engagement: {e}")
    
    async def _update_annotation_efficiency(self):
        """Update annotation efficiency and quality metrics."""
        try:
            current_time = time.time()
            
            # Calculate efficiency metrics
            completed_tasks = [task for task in self.annotation_tasks.values() 
                             if task.completion_time is not None]
            
            if completed_tasks:
                # Calculate average metrics
                avg_quality = statistics.mean([task.quality_score for task in completed_tasks 
                                             if task.quality_score is not None])
                avg_duration = statistics.mean([task.actual_duration for task in completed_tasks 
                                              if task.actual_duration is not None])
                
                # Calculate efficiency (quality / time)
                efficiency_scores = []
                for task in completed_tasks:
                    if task.quality_score and task.actual_duration and task.actual_duration > 0:
                        efficiency = task.quality_score / (task.actual_duration / 3600)  # per hour
                        efficiency_scores.append(efficiency)
                
                avg_efficiency = statistics.mean(efficiency_scores) if efficiency_scores else 0
                
                # Record metrics
                metrics_collector.record_metric("business.annotation.quality_average", avg_quality)
                metrics_collector.record_metric("business.annotation.duration_average", avg_duration)
                metrics_collector.record_metric("business.annotation.efficiency_average", avg_efficiency)
                
                # Calculate hourly annotation rate
                recent_tasks = [task for task in completed_tasks 
                              if task.completion_time and task.completion_time > current_time - 3600]
                hourly_rate = len(recent_tasks)
                
                metrics_collector.record_metric("business.annotation.hourly_rate", hourly_rate)
            
        except Exception as e:
            logger.error(f"Failed to update annotation efficiency: {e}")
    
    async def _update_ai_performance(self):
        """Update AI model performance metrics."""
        try:
            for model_name, performance in self.ai_performance.items():
                # Record AI performance metrics
                metrics_collector.record_metric(f"business.ai.{model_name}.success_rate", performance.success_rate)
                metrics_collector.record_metric(f"business.ai.{model_name}.confidence_avg", performance.average_confidence)
                metrics_collector.record_metric(f"business.ai.{model_name}.accuracy", performance.accuracy_score)
                metrics_collector.record_metric(f"business.ai.{model_name}.processing_time", performance.processing_time_avg)
                
                # Calculate cost efficiency
                if performance.cost_per_inference > 0:
                    cost_efficiency = performance.accuracy_score / performance.cost_per_inference
                    metrics_collector.record_metric(f"business.ai.{model_name}.cost_efficiency", cost_efficiency)
            
        except Exception as e:
            logger.error(f"Failed to update AI performance: {e}")
    
    async def _update_project_health(self):
        """Update project health and progress metrics."""
        try:
            for project_id, health in self.project_health.items():
                # Calculate completion percentage
                completion_percentage = (health.completed_tasks / health.total_tasks * 100) if health.total_tasks > 0 else 0
                
                # Calculate health score based on multiple factors
                quality_factor = min(health.average_quality / 0.85, 1.0)  # Normalize to 85% target
                velocity_factor = min(health.completion_velocity / 10, 1.0)  # Normalize to 10 tasks/day target
                blocked_factor = 1.0 - (health.blocked_tasks / health.total_tasks) if health.total_tasks > 0 else 1.0
                
                health.health_score = (quality_factor + velocity_factor + blocked_factor) / 3
                
                # Record project metrics
                metrics_collector.record_metric(f"business.project.{project_id}.completion_percentage", completion_percentage)
                metrics_collector.record_metric(f"business.project.{project_id}.health_score", health.health_score)
                metrics_collector.record_metric(f"business.project.{project_id}.velocity", health.completion_velocity)
                metrics_collector.record_metric(f"business.project.{project_id}.quality_average", health.average_quality)
                
                # Estimate completion date
                if health.completion_velocity > 0 and health.pending_tasks > 0:
                    days_remaining = health.pending_tasks / health.completion_velocity
                    health.estimated_completion = datetime.now() + timedelta(days=days_remaining)
            
        except Exception as e:
            logger.error(f"Failed to update project health: {e}")
    
    async def _calculate_business_kpis(self):
        """Calculate key business performance indicators."""
        try:
            current_time = time.time()
            
            # Calculate daily metrics
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            
            # Daily annotations
            daily_annotations = len([task for task in self.annotation_tasks.values() 
                                   if task.completion_time and task.completion_time >= today_start])
            
            # Daily revenue (placeholder calculation)
            daily_revenue = Decimal(str(daily_annotations * 5.0))  # $5 per annotation
            
            # User retention rate (placeholder)
            total_users = len(self.user_sessions) + len([s for s in self.user_sessions.values()])
            returning_users = len([s for s in self.user_sessions.values() if s.actions_count > 1])
            user_retention_rate = (returning_users / total_users) if total_users > 0 else 0
            
            # Customer satisfaction (based on quality scores)
            quality_scores = [task.quality_score for task in self.annotation_tasks.values() 
                            if task.quality_score is not None]
            customer_satisfaction = statistics.mean(quality_scores) if quality_scores else 0
            
            # Operational efficiency (tasks completed vs. time spent)
            completed_tasks = [task for task in self.annotation_tasks.values() 
                             if task.completion_time is not None]
            total_time = sum([task.actual_duration for task in completed_tasks 
                            if task.actual_duration is not None])
            operational_efficiency = len(completed_tasks) / (total_time / 3600) if total_time > 0 else 0
            
            # Cost per annotation
            cost_per_annotation = daily_revenue / daily_annotations if daily_annotations > 0 else Decimal('0')
            
            # Profit margin (placeholder)
            profit_margin = 0.3  # 30%
            
            # SLA compliance
            sla_compliance = await self._calculate_sla_compliance()
            
            # Create KPI metrics
            kpi_metrics = BusinessKPIMetrics(
                timestamp=current_time,
                daily_annotations=daily_annotations,
                daily_revenue=daily_revenue,
                user_retention_rate=user_retention_rate,
                customer_satisfaction=customer_satisfaction,
                operational_efficiency=operational_efficiency,
                cost_per_annotation=cost_per_annotation,
                profit_margin=profit_margin,
                sla_compliance=sla_compliance
            )
            
            self.business_kpis.append(kpi_metrics)
            
            # Record KPI metrics
            metrics_collector.record_metric("business.kpi.daily_annotations", daily_annotations)
            metrics_collector.record_metric("business.kpi.daily_revenue", float(daily_revenue))
            metrics_collector.record_metric("business.kpi.user_retention_rate", user_retention_rate)
            metrics_collector.record_metric("business.kpi.customer_satisfaction", customer_satisfaction)
            metrics_collector.record_metric("business.kpi.operational_efficiency", operational_efficiency)
            metrics_collector.record_metric("business.kpi.sla_compliance", sla_compliance)
            
        except Exception as e:
            logger.error(f"Failed to calculate business KPIs: {e}")
    
    async def _calculate_sla_compliance(self) -> float:
        """Calculate SLA compliance score."""
        try:
            compliance_scores = []
            
            # Quality compliance
            quality_scores = [task.quality_score for task in self.annotation_tasks.values() 
                            if task.quality_score is not None]
            if quality_scores:
                quality_compliance = len([q for q in quality_scores if q >= self.sla_thresholds["annotation_quality_min"]]) / len(quality_scores)
                compliance_scores.append(quality_compliance)
            
            # Task completion time compliance
            completed_tasks = [task for task in self.annotation_tasks.values() 
                             if task.actual_duration is not None]
            if completed_tasks:
                time_compliance = len([task for task in completed_tasks 
                                     if task.actual_duration <= self.sla_thresholds["task_completion_time_max"]]) / len(completed_tasks)
                compliance_scores.append(time_compliance)
            
            # AI accuracy compliance
            ai_accuracies = [perf.accuracy_score for perf in self.ai_performance.values()]
            if ai_accuracies:
                ai_compliance = len([acc for acc in ai_accuracies if acc >= self.sla_thresholds["ai_accuracy_min"]]) / len(ai_accuracies)
                compliance_scores.append(ai_compliance)
            
            # Overall compliance
            return statistics.mean(compliance_scores) if compliance_scores else 1.0
            
        except Exception as e:
            logger.error(f"Failed to calculate SLA compliance: {e}")
            return 0.0
    
    async def _check_sla_compliance(self):
        """Check SLA compliance and trigger alerts if needed."""
        try:
            sla_compliance = await self._calculate_sla_compliance()
            
            if sla_compliance < 0.95:  # 95% compliance threshold
                # Trigger SLA compliance alert
                metrics_collector.record_metric("business.sla.violation", 1.0)
                logger.warning(f"SLA compliance below threshold: {sla_compliance:.2%}")
            
        except Exception as e:
            logger.error(f"Failed to check SLA compliance: {e}")
    
    async def _record_prometheus_metrics(self):
        """Record business metrics to Prometheus."""
        try:
            # User metrics
            active_users = len(self.user_sessions)
            prometheus_exporter.business_metrics['users_active_count'].set(active_users)
            
            # Annotation metrics
            completed_tasks = [task for task in self.annotation_tasks.values() 
                             if task.completion_time is not None]
            
            if completed_tasks:
                avg_quality = statistics.mean([task.quality_score for task in completed_tasks 
                                             if task.quality_score is not None])
                prometheus_exporter.business_metrics['annotation_quality_score'].labels(
                    project='all', user='all'
                ).set(avg_quality)
            
            # Project metrics
            for project_id, health in self.project_health.items():
                completion_percentage = (health.completed_tasks / health.total_tasks * 100) if health.total_tasks > 0 else 0
                prometheus_exporter.business_metrics['project_completion_percentage'].labels(
                    project=project_id
                ).set(completion_percentage)
            
            # AI metrics
            for model_name, performance in self.ai_performance.items():
                prometheus_exporter.business_metrics['ai_confidence_score'].labels(
                    model=model_name
                ).set(performance.average_confidence)
                
                prometheus_exporter.business_metrics['ai_accuracy_score'].labels(
                    model=model_name
                ).set(performance.accuracy_score)
            
        except Exception as e:
            logger.error(f"Failed to record Prometheus metrics: {e}")
    
    # Public API methods for tracking business events
    
    def start_annotation_task(
        self,
        task_id: str,
        project_id: str,
        user_id: str,
        task_type: str,
        complexity_score: float = 1.0,
        estimated_duration: Optional[float] = None
    ):
        """Start tracking an annotation task."""
        task_metrics = AnnotationTaskMetrics(
            task_id=task_id,
            project_id=project_id,
            user_id=user_id,
            task_type=task_type,
            start_time=time.time(),
            complexity_score=complexity_score,
            estimated_duration=estimated_duration
        )
        
        self.annotation_tasks[task_id] = task_metrics
        self.active_tasks[task_id] = time.time()
        
        # Record task start
        metrics_collector.increment_counter("business.annotation.tasks_started")
    
    def complete_annotation_task(
        self,
        task_id: str,
        quality_score: float,
        revision_count: int = 0,
        ai_assistance_used: bool = False
    ):
        """Complete an annotation task with quality metrics."""
        if task_id not in self.annotation_tasks:
            logger.warning(f"Task {task_id} not found in active tasks")
            return
        
        task = self.annotation_tasks[task_id]
        current_time = time.time()
        
        task.completion_time = current_time
        task.quality_score = quality_score
        task.revision_count = revision_count
        task.ai_assistance_used = ai_assistance_used
        task.actual_duration = current_time - task.start_time
        
        # Remove from active tasks
        self.active_tasks.pop(task_id, None)
        
        # Update quality trends
        self.quality_trends[task.project_id].append(quality_score)
        
        # Record completion metrics
        metrics_collector.increment_counter("business.annotation.tasks_completed")
        metrics_collector.record_metric("business.annotation.quality_score", quality_score)
        metrics_collector.record_metric("business.annotation.task_duration", task.actual_duration)
        
        # Record to Prometheus
        prometheus_exporter.record_http_request("TASK", "complete", 200, task.actual_duration)
    
    def start_user_session(self, user_id: str):
        """Start tracking a user session."""
        session = UserEngagementMetrics(
            user_id=user_id,
            session_start=time.time(),
            last_activity=time.time()
        )
        
        self.user_sessions[user_id] = session
        
        # Record session start
        metrics_collector.increment_counter("business.users.sessions_started")
    
    def track_user_activity(
        self,
        user_id: str,
        activity_type: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Track user activity within a session."""
        if user_id not in self.user_sessions:
            # Auto-start session if not exists
            self.start_user_session(user_id)
        
        session = self.user_sessions[user_id]
        session.last_activity = time.time()
        session.actions_count += 1
        
        # Store activity details
        activity = {
            "type": activity_type,
            "timestamp": time.time(),
            "details": details or {}
        }
        
        self.user_activities[user_id].append(activity)
        
        # Keep only recent activities
        cutoff_time = time.time() - 86400  # 24 hours
        self.user_activities[user_id] = [
            a for a in self.user_activities[user_id] 
            if a["timestamp"] > cutoff_time
        ]
        
        # Record activity
        metrics_collector.increment_counter("business.users.activities", tags={"type": activity_type})
    
    def update_project_status(
        self,
        project_id: str,
        total_tasks: int,
        completed_tasks: int,
        in_progress_tasks: int,
        pending_tasks: int,
        blocked_tasks: int = 0,
        team_size: int = 1
    ):
        """Update project status and health metrics."""
        # Calculate average quality for the project
        project_tasks = [task for task in self.annotation_tasks.values() 
                        if task.project_id == project_id and task.quality_score is not None]
        average_quality = statistics.mean([task.quality_score for task in project_tasks]) if project_tasks else 0
        
        # Calculate completion velocity (tasks per day)
        recent_completions = [task for task in project_tasks 
                            if task.completion_time and task.completion_time > time.time() - 86400]
        completion_velocity = len(recent_completions)
        
        health = ProjectHealthMetrics(
            project_id=project_id,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            in_progress_tasks=in_progress_tasks,
            pending_tasks=pending_tasks,
            blocked_tasks=blocked_tasks,
            average_quality=average_quality,
            completion_velocity=completion_velocity,
            team_size=team_size
        )
        
        self.project_health[project_id] = health
    
    def update_ai_model_performance(
        self,
        model_name: str,
        inference_count: int,
        success_rate: float,
        average_confidence: float,
        accuracy_score: float,
        processing_time_avg: float,
        cost_per_inference: float = 0.0
    ):
        """Update AI model performance metrics."""
        performance = AIModelPerformanceMetrics(
            model_name=model_name,
            inference_count=inference_count,
            success_rate=success_rate,
            average_confidence=average_confidence,
            accuracy_score=accuracy_score,
            processing_time_avg=processing_time_avg,
            cost_per_inference=cost_per_inference
        )
        
        self.ai_performance[model_name] = performance
    
    # Analytics and reporting methods
    
    def get_business_summary(self) -> Dict[str, Any]:
        """Get comprehensive business metrics summary."""
        current_time = time.time()
        
        # Latest KPIs
        latest_kpis = self.business_kpis[-1] if self.business_kpis else None
        
        # Active metrics
        active_users = len(self.user_sessions)
        active_tasks = len(self.active_tasks)
        
        # Quality metrics
        quality_scores = [task.quality_score for task in self.annotation_tasks.values() 
                         if task.quality_score is not None]
        avg_quality = statistics.mean(quality_scores) if quality_scores else 0
        
        # Project summary
        project_summary = {}
        for project_id, health in self.project_health.items():
            completion_percentage = (health.completed_tasks / health.total_tasks * 100) if health.total_tasks > 0 else 0
            project_summary[project_id] = {
                "completion_percentage": completion_percentage,
                "health_score": health.health_score,
                "quality_average": health.average_quality,
                "velocity": health.completion_velocity
            }
        
        # AI summary
        ai_summary = {}
        for model_name, performance in self.ai_performance.items():
            ai_summary[model_name] = {
                "success_rate": performance.success_rate,
                "accuracy": performance.accuracy_score,
                "confidence_avg": performance.average_confidence,
                "processing_time": performance.processing_time_avg
            }
        
        return {
            "timestamp": current_time,
            "active_metrics": {
                "active_users": active_users,
                "active_tasks": active_tasks,
                "average_quality": avg_quality
            },
            "latest_kpis": {
                "daily_annotations": latest_kpis.daily_annotations if latest_kpis else 0,
                "daily_revenue": float(latest_kpis.daily_revenue) if latest_kpis else 0,
                "user_retention_rate": latest_kpis.user_retention_rate if latest_kpis else 0,
                "sla_compliance": latest_kpis.sla_compliance if latest_kpis else 0
            } if latest_kpis else {},
            "projects": project_summary,
            "ai_models": ai_summary
        }
    
    def get_quality_trends(self, project_id: Optional[str] = None, hours: int = 24) -> List[float]:
        """Get quality score trends for analysis."""
        cutoff_time = time.time() - (hours * 3600)
        
        if project_id:
            return list(self.quality_trends.get(project_id, []))
        else:
            # Aggregate all projects
            all_scores = []
            for scores in self.quality_trends.values():
                all_scores.extend(scores)
            return all_scores
    
    def get_user_engagement_report(self) -> Dict[str, Any]:
        """Get detailed user engagement report."""
        total_sessions = len(self.user_sessions)
        
        if total_sessions == 0:
            return {"total_sessions": 0, "engagement_levels": {}}
        
        engagement_levels = defaultdict(int)
        total_actions = 0
        total_duration = 0
        
        for session in self.user_sessions.values():
            engagement_levels[session.engagement_level] += 1
            total_actions += session.actions_count
            if session.session_duration > 0:
                total_duration += session.session_duration
        
        return {
            "total_sessions": total_sessions,
            "engagement_levels": dict(engagement_levels),
            "average_actions_per_session": total_actions / total_sessions,
            "average_session_duration": total_duration / total_sessions if total_duration > 0 else 0,
            "high_engagement_percentage": (engagement_levels["high"] / total_sessions) * 100
        }


# Global business monitoring service
business_monitoring_service = BusinessMonitoringService()


# Convenience functions
async def start_business_monitoring():
    """Start business monitoring service."""
    await business_monitoring_service.start_monitoring()


async def stop_business_monitoring():
    """Stop business monitoring service."""
    await business_monitoring_service.stop_monitoring()


def get_business_monitoring_service() -> BusinessMonitoringService:
    """Get the global business monitoring service instance."""
    return business_monitoring_service