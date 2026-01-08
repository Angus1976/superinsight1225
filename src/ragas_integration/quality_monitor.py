"""
Quality Monitoring Service for Ragas Integration.

Provides real-time quality monitoring, automatic retraining triggers,
and quality control automation.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from .evaluator import RagasEvaluator, RagasEvaluationResult
from .trend_analyzer import QualityTrendAnalyzer, TrendDirection, AlertSeverity
from .model_optimizer import ModelOptimizer, ModelComparisonReport


logger = logging.getLogger(__name__)


class MonitoringStatus(str, Enum):
    """Quality monitoring status."""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class RetrainingTrigger(str, Enum):
    """Retraining trigger types."""
    QUALITY_THRESHOLD = "quality_threshold"
    TREND_DECLINE = "trend_decline"
    ALERT_ACCUMULATION = "alert_accumulation"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


@dataclass
class MonitoringConfig:
    """Configuration for quality monitoring."""
    
    # Monitoring intervals
    evaluation_interval: int = 300  # seconds
    trend_analysis_interval: int = 900  # seconds
    alert_check_interval: int = 60  # seconds
    
    # Quality thresholds
    min_overall_quality: float = 0.7
    min_faithfulness: float = 0.7
    min_relevancy: float = 0.7
    min_precision: float = 0.6
    min_recall: float = 0.6
    
    # Retraining triggers
    enable_auto_retraining: bool = True
    quality_decline_threshold: float = 0.1  # Trigger if quality drops by this amount
    consecutive_alerts_threshold: int = 5
    max_retraining_frequency: timedelta = timedelta(hours=6)
    
    # Notification settings
    enable_notifications: bool = True
    notification_channels: List[str] = field(default_factory=lambda: ["log", "email"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "evaluation_interval": self.evaluation_interval,
            "trend_analysis_interval": self.trend_analysis_interval,
            "alert_check_interval": self.alert_check_interval,
            "min_overall_quality": self.min_overall_quality,
            "min_faithfulness": self.min_faithfulness,
            "min_relevancy": self.min_relevancy,
            "min_precision": self.min_precision,
            "min_recall": self.min_recall,
            "enable_auto_retraining": self.enable_auto_retraining,
            "quality_decline_threshold": self.quality_decline_threshold,
            "consecutive_alerts_threshold": self.consecutive_alerts_threshold,
            "max_retraining_frequency": self.max_retraining_frequency.total_seconds(),
            "enable_notifications": self.enable_notifications,
            "notification_channels": self.notification_channels
        }


@dataclass
class RetrainingEvent:
    """Retraining event record."""
    
    event_id: str
    trigger: RetrainingTrigger
    triggered_at: datetime
    trigger_reason: str
    quality_before: Dict[str, float]
    quality_after: Optional[Dict[str, float]] = None
    retraining_completed: bool = False
    improvement_achieved: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "trigger": self.trigger.value,
            "triggered_at": self.triggered_at.isoformat(),
            "trigger_reason": self.trigger_reason,
            "quality_before": self.quality_before,
            "quality_after": self.quality_after,
            "retraining_completed": self.retraining_completed,
            "improvement_achieved": self.improvement_achieved
        }


class QualityMonitor:
    """Real-time quality monitoring service."""
    
    def __init__(self, 
                 config: Optional[MonitoringConfig] = None,
                 storage_path: Optional[str] = None):
        """Initialize quality monitor."""
        self.config = config or MonitoringConfig()
        self.storage_path = Path(storage_path) if storage_path else Path("./quality_monitoring")
        self.storage_path.mkdir(exist_ok=True)
        
        # Core components
        self.evaluator = RagasEvaluator()
        self.trend_analyzer = QualityTrendAnalyzer()
        self.model_optimizer = ModelOptimizer(str(self.storage_path))
        
        # Monitoring state
        self.status = MonitoringStatus.STOPPED
        self.monitoring_tasks: List[asyncio.Task] = []
        self.last_retraining: Optional[datetime] = None
        self.retraining_history: List[RetrainingEvent] = []
        
        # Callbacks
        self.retraining_callback: Optional[Callable] = None
        self.notification_callback: Optional[Callable] = None
        
        # Load history
        self._load_monitoring_history()
    
    def _load_monitoring_history(self) -> None:
        """Load monitoring history from storage."""
        try:
            history_file = self.storage_path / "retraining_history.json"
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for event_data in data:
                    event = RetrainingEvent(
                        event_id=event_data["event_id"],
                        trigger=RetrainingTrigger(event_data["trigger"]),
                        triggered_at=datetime.fromisoformat(event_data["triggered_at"]),
                        trigger_reason=event_data["trigger_reason"],
                        quality_before=event_data["quality_before"],
                        quality_after=event_data.get("quality_after"),
                        retraining_completed=event_data.get("retraining_completed", False),
                        improvement_achieved=event_data.get("improvement_achieved")
                    )
                    self.retraining_history.append(event)
                    
                # Update last retraining time
                if self.retraining_history:
                    self.last_retraining = max(
                        event.triggered_at for event in self.retraining_history
                        if event.retraining_completed
                    )
                    
        except Exception as e:
            logger.error(f"Failed to load monitoring history: {e}")
    
    def _save_monitoring_history(self) -> None:
        """Save monitoring history to storage."""
        try:
            history_file = self.storage_path / "retraining_history.json"
            data = [event.to_dict() for event in self.retraining_history]
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save monitoring history: {e}")
    
    async def start_monitoring(self) -> None:
        """Start quality monitoring."""
        if self.status == MonitoringStatus.ACTIVE:
            logger.warning("Quality monitoring is already active")
            return
        
        logger.info("Starting quality monitoring")
        self.status = MonitoringStatus.ACTIVE
        
        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._trend_analysis_loop()),
            asyncio.create_task(self._alert_monitoring_loop()),
            asyncio.create_task(self._retraining_check_loop())
        ]
        
        logger.info("Quality monitoring started successfully")
    
    async def stop_monitoring(self) -> None:
        """Stop quality monitoring."""
        if self.status == MonitoringStatus.STOPPED:
            return
        
        logger.info("Stopping quality monitoring")
        self.status = MonitoringStatus.STOPPED
        
        # Cancel monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        self.monitoring_tasks.clear()
        
        logger.info("Quality monitoring stopped")
    
    async def pause_monitoring(self) -> None:
        """Pause quality monitoring."""
        if self.status == MonitoringStatus.ACTIVE:
            self.status = MonitoringStatus.PAUSED
            logger.info("Quality monitoring paused")
    
    async def resume_monitoring(self) -> None:
        """Resume quality monitoring."""
        if self.status == MonitoringStatus.PAUSED:
            self.status = MonitoringStatus.ACTIVE
            logger.info("Quality monitoring resumed")
    
    async def _trend_analysis_loop(self) -> None:
        """Main trend analysis monitoring loop."""
        while self.status != MonitoringStatus.STOPPED:
            try:
                if self.status == MonitoringStatus.ACTIVE:
                    await self._perform_trend_analysis()
                
                await asyncio.sleep(self.config.trend_analysis_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in trend analysis loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _alert_monitoring_loop(self) -> None:
        """Alert monitoring loop."""
        while self.status != MonitoringStatus.STOPPED:
            try:
                if self.status == MonitoringStatus.ACTIVE:
                    await self._check_quality_alerts()
                
                await asyncio.sleep(self.config.alert_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _retraining_check_loop(self) -> None:
        """Retraining check loop."""
        while self.status != MonitoringStatus.STOPPED:
            try:
                if self.status == MonitoringStatus.ACTIVE and self.config.enable_auto_retraining:
                    await self._check_retraining_triggers()
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retraining check loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _perform_trend_analysis(self) -> None:
        """Perform trend analysis on current quality metrics."""
        try:
            # Analyze trends for the last 24 hours
            trends = self.trend_analyzer.analyze_all_metrics(timedelta(hours=24))
            
            # Log trend summary
            declining_metrics = [
                name for name, trend in trends.items()
                if trend.direction == TrendDirection.DECLINING
            ]
            
            if declining_metrics:
                logger.warning(f"Declining quality trends detected: {declining_metrics}")
                
                # Send notification if enabled
                if self.config.enable_notifications:
                    await self._send_notification(
                        "quality_trend_alert",
                        f"质量趋势警告：以下指标呈下降趋势 - {', '.join(declining_metrics)}"
                    )
            
        except Exception as e:
            logger.error(f"Failed to perform trend analysis: {e}")
    
    async def _check_quality_alerts(self) -> None:
        """Check for quality alerts and handle them."""
        try:
            active_alerts = self.trend_analyzer.get_active_alerts()
            
            # Handle critical alerts
            critical_alerts = [
                alert for alert in active_alerts
                if alert.severity == AlertSeverity.CRITICAL and not alert.acknowledged
            ]
            
            if critical_alerts:
                logger.critical(f"Critical quality alerts detected: {len(critical_alerts)}")
                
                for alert in critical_alerts:
                    await self._handle_critical_alert(alert)
            
            # Check for alert accumulation
            recent_alerts = [
                alert for alert in active_alerts
                if alert.created_at >= datetime.now() - timedelta(hours=1)
            ]
            
            if len(recent_alerts) >= self.config.consecutive_alerts_threshold:
                await self._trigger_retraining(
                    RetrainingTrigger.ALERT_ACCUMULATION,
                    f"连续 {len(recent_alerts)} 个质量警报在过去1小时内触发"
                )
            
        except Exception as e:
            logger.error(f"Failed to check quality alerts: {e}")
    
    async def _handle_critical_alert(self, alert) -> None:
        """Handle a critical quality alert."""
        logger.critical(f"Handling critical alert: {alert.message}")
        
        # Send immediate notification
        if self.config.enable_notifications:
            await self._send_notification(
                "critical_quality_alert",
                f"🚨 严重质量警报：{alert.message}"
            )
        
        # Consider triggering retraining for critical alerts
        if alert.metric_name in ["overall_score", "ragas_faithfulness"]:
            await self._trigger_retraining(
                RetrainingTrigger.QUALITY_THRESHOLD,
                f"严重质量警报：{alert.metric_name} = {alert.current_value:.3f}"
            )
        
        # Acknowledge the alert
        self.trend_analyzer.acknowledge_alert(alert.alert_id)
    
    async def _check_retraining_triggers(self) -> None:
        """Check if retraining should be triggered."""
        try:
            # Check if enough time has passed since last retraining
            if self.last_retraining:
                time_since_last = datetime.now() - self.last_retraining
                if time_since_last < self.config.max_retraining_frequency:
                    return
            
            # Check quality thresholds
            await self._check_quality_thresholds()
            
            # Check trend decline
            await self._check_trend_decline()
            
        except Exception as e:
            logger.error(f"Failed to check retraining triggers: {e}")
    
    async def _check_quality_thresholds(self) -> None:
        """Check if quality has fallen below thresholds."""
        # Get recent evaluation results
        if not self.trend_analyzer.evaluation_history:
            return
        
        recent_result = self.trend_analyzer.evaluation_history[-1]
        
        # Check overall quality
        if recent_result.overall_score < self.config.min_overall_quality:
            await self._trigger_retraining(
                RetrainingTrigger.QUALITY_THRESHOLD,
                f"整体质量 ({recent_result.overall_score:.3f}) 低于阈值 ({self.config.min_overall_quality:.3f})"
            )
            return
        
        # Check individual metrics
        thresholds = {
            "ragas_faithfulness": self.config.min_faithfulness,
            "ragas_answer_relevancy": self.config.min_relevancy,
            "ragas_context_precision": self.config.min_precision,
            "ragas_context_recall": self.config.min_recall
        }
        
        for metric, threshold in thresholds.items():
            if metric in recent_result.metrics:
                value = recent_result.metrics[metric]
                if value < threshold:
                    await self._trigger_retraining(
                        RetrainingTrigger.QUALITY_THRESHOLD,
                        f"{metric} ({value:.3f}) 低于阈值 ({threshold:.3f})"
                    )
                    return
    
    async def _check_trend_decline(self) -> None:
        """Check if quality trends show significant decline."""
        trends = self.trend_analyzer.analyze_all_metrics(timedelta(days=7))
        
        for metric_name, trend in trends.items():
            if trend.direction == TrendDirection.DECLINING and trend.confidence > 0.7:
                # Calculate decline magnitude
                if len(self.trend_analyzer.evaluation_history) >= 2:
                    recent_values = []
                    for result in list(self.trend_analyzer.evaluation_history)[-7:]:
                        if metric_name == "overall_score":
                            recent_values.append(result.overall_score)
                        elif metric_name in result.metrics:
                            recent_values.append(result.metrics[metric_name])
                    
                    if len(recent_values) >= 2:
                        decline = recent_values[0] - recent_values[-1]
                        if decline >= self.config.quality_decline_threshold:
                            await self._trigger_retraining(
                                RetrainingTrigger.TREND_DECLINE,
                                f"{metric_name} 在过去7天下降了 {decline:.3f}"
                            )
                            return
    
    async def _trigger_retraining(self, trigger: RetrainingTrigger, reason: str) -> None:
        """Trigger model retraining."""
        try:
            logger.info(f"Triggering retraining: {trigger.value} - {reason}")
            
            # Get current quality metrics
            current_quality = {}
            if self.trend_analyzer.evaluation_history:
                recent_result = self.trend_analyzer.evaluation_history[-1]
                current_quality = {
                    "overall_score": recent_result.overall_score,
                    **recent_result.metrics
                }
            
            # Create retraining event
            event = RetrainingEvent(
                event_id=f"retrain_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                trigger=trigger,
                triggered_at=datetime.now(),
                trigger_reason=reason,
                quality_before=current_quality
            )
            
            self.retraining_history.append(event)
            self._save_monitoring_history()
            
            # Call retraining callback if provided
            if self.retraining_callback:
                try:
                    await self.retraining_callback(event)
                    event.retraining_completed = True
                    self.last_retraining = event.triggered_at
                except Exception as e:
                    logger.error(f"Retraining callback failed: {e}")
            
            # Send notification
            if self.config.enable_notifications:
                await self._send_notification(
                    "retraining_triggered",
                    f"🔄 模型重训练已触发：{reason}"
                )
            
        except Exception as e:
            logger.error(f"Failed to trigger retraining: {e}")
    
    async def _send_notification(self, notification_type: str, message: str) -> None:
        """Send notification through configured channels."""
        try:
            # Log notification
            if "log" in self.config.notification_channels:
                logger.info(f"Notification [{notification_type}]: {message}")
            
            # Call notification callback if provided
            if self.notification_callback:
                await self.notification_callback(notification_type, message)
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def add_evaluation_result(self, result: RagasEvaluationResult) -> None:
        """Add evaluation result to monitoring system."""
        self.trend_analyzer.add_evaluation_result(result)
    
    def set_retraining_callback(self, callback: Callable) -> None:
        """Set callback function for retraining events."""
        self.retraining_callback = callback
    
    def set_notification_callback(self, callback: Callable) -> None:
        """Set callback function for notifications."""
        self.notification_callback = callback
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status and statistics."""
        active_alerts = self.trend_analyzer.get_active_alerts()
        recent_trends = self.trend_analyzer.analyze_all_metrics(timedelta(hours=24))
        
        return {
            "status": self.status.value,
            "config": self.config.to_dict(),
            "statistics": {
                "total_evaluations": len(self.trend_analyzer.evaluation_history),
                "active_alerts": len(active_alerts),
                "critical_alerts": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                "retraining_events": len(self.retraining_history),
                "last_retraining": self.last_retraining.isoformat() if self.last_retraining else None
            },
            "recent_trends": {name: trend.to_dict() for name, trend in recent_trends.items()},
            "last_updated": datetime.now().isoformat()
        }
    
    def update_config(self, new_config: MonitoringConfig) -> None:
        """Update monitoring configuration."""
        self.config = new_config
        
        # Update trend analyzer thresholds
        for metric in ["ragas_faithfulness", "ragas_answer_relevancy", 
                      "ragas_context_precision", "ragas_context_recall", "overall_score"]:
            if hasattr(self.config, f"min_{metric.split('_')[-1]}"):
                threshold_value = getattr(self.config, f"min_{metric.split('_')[-1]}")
                self.trend_analyzer.configure_alert_thresholds(metric, {
                    "critical": threshold_value - 0.2,
                    "high": threshold_value - 0.1,
                    "medium": threshold_value,
                    "low": threshold_value + 0.1
                })
        
        logger.info("Monitoring configuration updated")
    
    async def manual_retraining(self, reason: str = "手动触发") -> None:
        """Manually trigger retraining."""
        await self._trigger_retraining(RetrainingTrigger.MANUAL, reason)
    
    def get_retraining_history(self, limit: Optional[int] = None) -> List[RetrainingEvent]:
        """Get retraining history."""
        history = sorted(self.retraining_history, key=lambda x: x.triggered_at, reverse=True)
        
        if limit:
            history = history[:limit]
        
        return history
    
    async def generate_monitoring_report(self, period: Optional[timedelta] = None) -> Dict[str, Any]:
        """Generate comprehensive monitoring report."""
        period = period or timedelta(days=7)
        
        # Get quality summary
        quality_summary = self.trend_analyzer.get_quality_summary(period)
        
        # Get retraining events in period
        cutoff_time = datetime.now() - period
        recent_retraining = [
            event for event in self.retraining_history
            if event.triggered_at >= cutoff_time
        ]
        
        # Calculate monitoring effectiveness
        total_alerts = len(self.trend_analyzer.get_active_alerts())
        resolved_alerts = len([
            alert for alert in self.trend_analyzer.get_active_alerts()
            if alert.acknowledged
        ])
        
        return {
            "report_period": str(period),
            "generated_at": datetime.now().isoformat(),
            "monitoring_status": self.get_monitoring_status(),
            "quality_summary": quality_summary,
            "retraining_summary": {
                "events_in_period": len(recent_retraining),
                "successful_retraining": len([e for e in recent_retraining if e.retraining_completed]),
                "trigger_breakdown": {
                    trigger.value: len([e for e in recent_retraining if e.trigger == trigger])
                    for trigger in RetrainingTrigger
                }
            },
            "alert_management": {
                "total_alerts": total_alerts,
                "resolved_alerts": resolved_alerts,
                "resolution_rate": resolved_alerts / total_alerts if total_alerts > 0 else 0
            },
            "recommendations": self._generate_monitoring_recommendations(quality_summary, recent_retraining)
        }
    
    def _generate_monitoring_recommendations(self, 
                                          quality_summary: Dict[str, Any], 
                                          recent_retraining: List[RetrainingEvent]) -> List[str]:
        """Generate monitoring recommendations."""
        recommendations = []
        
        # Check monitoring effectiveness
        if quality_summary["overall_health_score"] < 0.7:
            recommendations.append("考虑调整质量阈值或增加监控频率")
        
        # Check retraining frequency
        if len(recent_retraining) > 5:
            recommendations.append("重训练频率较高，建议分析根本原因")
        elif len(recent_retraining) == 0 and quality_summary["overall_health_score"] < 0.8:
            recommendations.append("质量下降但未触发重训练，建议检查触发条件")
        
        # Check alert management
        critical_alerts = quality_summary["active_alerts"]["by_severity"].get("critical", 0)
        if critical_alerts > 0:
            recommendations.append("存在未处理的严重警报，需要立即关注")
        
        return recommendations