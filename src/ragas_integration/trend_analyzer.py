"""
Ragas Quality Trend Analyzer.

Implements quality trend monitoring, analysis, and prediction
for the Ragas evaluation system integration.
"""

import asyncio
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from collections import defaultdict, deque

from .evaluator import RagasEvaluationResult


logger = logging.getLogger(__name__)


class TrendDirection(str, Enum):
    """Quality trend direction."""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"
    INSUFFICIENT_DATA = "insufficient_data"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class QualityTrend:
    """Quality trend analysis result."""
    
    metric_name: str
    direction: TrendDirection
    slope: float
    confidence: float
    current_value: float
    predicted_value: Optional[float] = None
    volatility: float = 0.0
    data_points: int = 0
    analysis_period: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metric_name": self.metric_name,
            "direction": self.direction.value,
            "slope": self.slope,
            "confidence": self.confidence,
            "current_value": self.current_value,
            "predicted_value": self.predicted_value,
            "volatility": self.volatility,
            "data_points": self.data_points,
            "analysis_period": self.analysis_period
        }


@dataclass
class QualityAlert:
    """Quality alert for trend monitoring."""
    
    alert_id: str
    severity: AlertSeverity
    metric_name: str
    message: str
    current_value: float
    threshold_value: float
    trend_direction: TrendDirection
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "metric_name": self.metric_name,
            "message": self.message,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "trend_direction": self.trend_direction.value,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged
        }


@dataclass
class QualityForecast:
    """Quality forecast result."""
    
    metric_name: str
    forecast_horizon: int  # days
    predicted_values: List[float]
    confidence_intervals: List[Tuple[float, float]]
    forecast_accuracy: float
    risk_assessment: str
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metric_name": self.metric_name,
            "forecast_horizon": self.forecast_horizon,
            "predicted_values": self.predicted_values,
            "confidence_intervals": self.confidence_intervals,
            "forecast_accuracy": self.forecast_accuracy,
            "risk_assessment": self.risk_assessment,
            "recommendations": self.recommendations
        }


class QualityTrendAnalyzer:
    """Analyzer for quality trends and patterns."""
    
    def __init__(self, max_history_size: int = 1000):
        """Initialize trend analyzer."""
        self.max_history_size = max_history_size
        self.evaluation_history: deque = deque(maxlen=max_history_size)
        self.trend_cache: Dict[str, QualityTrend] = {}
        self.alert_thresholds = self._initialize_alert_thresholds()
        self.active_alerts: List[QualityAlert] = []
        
    def _initialize_alert_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Initialize default alert thresholds."""
        return {
            "ragas_faithfulness": {
                "critical": 0.5,
                "high": 0.6,
                "medium": 0.7,
                "low": 0.8
            },
            "ragas_answer_relevancy": {
                "critical": 0.5,
                "high": 0.6,
                "medium": 0.7,
                "low": 0.8
            },
            "ragas_context_precision": {
                "critical": 0.4,
                "high": 0.5,
                "medium": 0.6,
                "low": 0.7
            },
            "ragas_context_recall": {
                "critical": 0.4,
                "high": 0.5,
                "medium": 0.6,
                "low": 0.7
            },
            "overall_score": {
                "critical": 0.5,
                "high": 0.6,
                "medium": 0.7,
                "low": 0.8
            }
        }
    
    def add_evaluation_result(self, result: RagasEvaluationResult) -> None:
        """Add evaluation result to history for trend analysis."""
        self.evaluation_history.append(result)
        
        # Clear cache to force recalculation
        self.trend_cache.clear()
        
        # Check for alerts
        self._check_quality_alerts(result)
    
    def analyze_metric_trend(self, 
                           metric_name: str, 
                           analysis_period: Optional[timedelta] = None) -> QualityTrend:
        """
        Analyze trend for a specific metric.
        
        Args:
            metric_name: Name of the metric to analyze
            analysis_period: Optional time period for analysis
            
        Returns:
            Quality trend analysis result
        """
        cache_key = f"{metric_name}_{analysis_period}"
        if cache_key in self.trend_cache:
            return self.trend_cache[cache_key]
        
        # Filter evaluations by period if specified
        evaluations = list(self.evaluation_history)
        if analysis_period:
            cutoff_time = datetime.now() - analysis_period
            evaluations = [
                eval_result for eval_result in evaluations
                if eval_result.evaluation_date >= cutoff_time
            ]
        
        if len(evaluations) < 2:
            trend = QualityTrend(
                metric_name=metric_name,
                direction=TrendDirection.INSUFFICIENT_DATA,
                slope=0.0,
                confidence=0.0,
                current_value=0.0,
                data_points=len(evaluations),
                analysis_period=str(analysis_period) if analysis_period else "all_time"
            )
            self.trend_cache[cache_key] = trend
            return trend
        
        # Extract metric values
        values = []
        timestamps = []
        
        for eval_result in evaluations:
            if metric_name == "overall_score":
                value = eval_result.overall_score
            elif metric_name in eval_result.metrics:
                value = eval_result.metrics[metric_name]
            else:
                continue
            
            values.append(value)
            timestamps.append(eval_result.evaluation_date.timestamp())
        
        if len(values) < 2:
            trend = QualityTrend(
                metric_name=metric_name,
                direction=TrendDirection.INSUFFICIENT_DATA,
                slope=0.0,
                confidence=0.0,
                current_value=values[0] if values else 0.0,
                data_points=len(values),
                analysis_period=str(analysis_period) if analysis_period else "all_time"
            )
            self.trend_cache[cache_key] = trend
            return trend
        
        # Calculate trend statistics
        slope, confidence = self._calculate_trend_slope(timestamps, values)
        direction = self._determine_trend_direction(slope, confidence)
        volatility = self._calculate_volatility(values)
        current_value = values[-1]
        
        # Predict next value
        predicted_value = None
        if len(values) >= 3 and confidence > 0.5:
            predicted_value = current_value + slope * 86400  # Next day prediction
        
        trend = QualityTrend(
            metric_name=metric_name,
            direction=direction,
            slope=slope,
            confidence=confidence,
            current_value=current_value,
            predicted_value=predicted_value,
            volatility=volatility,
            data_points=len(values),
            analysis_period=str(analysis_period) if analysis_period else "all_time"
        )
        
        self.trend_cache[cache_key] = trend
        return trend
    
    def _calculate_trend_slope(self, timestamps: List[float], values: List[float]) -> Tuple[float, float]:
        """Calculate trend slope and confidence using linear regression."""
        if len(timestamps) != len(values) or len(timestamps) < 2:
            return 0.0, 0.0
        
        try:
            # Convert to numpy arrays for calculation
            x = np.array(timestamps)
            y = np.array(values)
            
            # Normalize timestamps to start from 0
            x = x - x[0]
            
            # Calculate linear regression
            n = len(x)
            sum_x = np.sum(x)
            sum_y = np.sum(y)
            sum_xy = np.sum(x * y)
            sum_x2 = np.sum(x * x)
            
            # Slope calculation
            denominator = n * sum_x2 - sum_x * sum_x
            if abs(denominator) < 1e-10:
                return 0.0, 0.0
            
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            
            # Calculate R-squared for confidence
            y_mean = np.mean(y)
            y_pred = slope * x + (sum_y - slope * sum_x) / n
            
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - y_mean) ** 2)
            
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            confidence = max(0.0, min(1.0, r_squared))
            
            return float(slope), float(confidence)
            
        except Exception as e:
            logger.warning(f"Failed to calculate trend slope: {e}")
            return 0.0, 0.0
    
    def _determine_trend_direction(self, slope: float, confidence: float) -> TrendDirection:
        """Determine trend direction based on slope and confidence."""
        if confidence < 0.3:
            return TrendDirection.INSUFFICIENT_DATA
        
        # Thresholds for trend classification
        significant_threshold = 0.001  # per second
        
        if abs(slope) < significant_threshold:
            return TrendDirection.STABLE
        elif slope > significant_threshold:
            return TrendDirection.IMPROVING
        else:
            return TrendDirection.DECLINING
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (standard deviation) of values."""
        if len(values) < 2:
            return 0.0
        
        try:
            return float(statistics.stdev(values))
        except Exception:
            return 0.0
    
    def analyze_all_metrics(self, 
                          analysis_period: Optional[timedelta] = None) -> Dict[str, QualityTrend]:
        """Analyze trends for all available metrics."""
        if not self.evaluation_history:
            return {}
        
        # Get all unique metrics from evaluation history
        all_metrics = set()
        for eval_result in self.evaluation_history:
            all_metrics.update(eval_result.metrics.keys())
        all_metrics.add("overall_score")
        
        trends = {}
        for metric in all_metrics:
            trends[metric] = self.analyze_metric_trend(metric, analysis_period)
        
        return trends
    
    def _check_quality_alerts(self, result: RagasEvaluationResult) -> None:
        """Check for quality alerts based on current evaluation."""
        current_time = datetime.now()
        
        # Check overall score
        self._check_metric_alert("overall_score", result.overall_score, current_time)
        
        # Check individual metrics
        for metric_name, value in result.metrics.items():
            self._check_metric_alert(metric_name, value, current_time)
    
    def _check_metric_alert(self, metric_name: str, value: float, timestamp: datetime) -> None:
        """Check if a metric value triggers an alert."""
        if metric_name not in self.alert_thresholds:
            return
        
        thresholds = self.alert_thresholds[metric_name]
        
        # Determine alert severity
        severity = None
        threshold_value = None
        
        if value <= thresholds["critical"]:
            severity = AlertSeverity.CRITICAL
            threshold_value = thresholds["critical"]
        elif value <= thresholds["high"]:
            severity = AlertSeverity.HIGH
            threshold_value = thresholds["high"]
        elif value <= thresholds["medium"]:
            severity = AlertSeverity.MEDIUM
            threshold_value = thresholds["medium"]
        elif value <= thresholds["low"]:
            severity = AlertSeverity.LOW
            threshold_value = thresholds["low"]
        
        if severity:
            # Get trend direction
            trend = self.analyze_metric_trend(metric_name, timedelta(days=7))
            
            # Create alert
            alert = QualityAlert(
                alert_id=f"alert_{metric_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
                severity=severity,
                metric_name=metric_name,
                message=f"{metric_name} 质量指标 ({value:.3f}) 低于 {severity.value} 阈值 ({threshold_value:.3f})",
                current_value=value,
                threshold_value=threshold_value,
                trend_direction=trend.direction,
                created_at=timestamp
            )
            
            self.active_alerts.append(alert)
            logger.warning(f"Quality alert: {alert.message}")
    
    def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None) -> List[QualityAlert]:
        """Get active quality alerts, optionally filtered by severity."""
        if severity_filter:
            return [alert for alert in self.active_alerts if alert.severity == severity_filter]
        return self.active_alerts.copy()
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def clear_acknowledged_alerts(self) -> int:
        """Clear acknowledged alerts and return count of cleared alerts."""
        initial_count = len(self.active_alerts)
        self.active_alerts = [alert for alert in self.active_alerts if not alert.acknowledged]
        return initial_count - len(self.active_alerts)
    
    def forecast_quality(self, 
                        metric_name: str, 
                        forecast_days: int = 7) -> Optional[QualityForecast]:
        """
        Forecast quality metric values for the specified number of days.
        
        Args:
            metric_name: Name of the metric to forecast
            forecast_days: Number of days to forecast
            
        Returns:
            Quality forecast result or None if insufficient data
        """
        # Get recent trend
        trend = self.analyze_metric_trend(metric_name, timedelta(days=30))
        
        if trend.direction == TrendDirection.INSUFFICIENT_DATA or trend.confidence < 0.5:
            return None
        
        # Generate predictions
        predicted_values = []
        confidence_intervals = []
        
        current_value = trend.current_value
        daily_change = trend.slope * 86400  # Convert per-second to per-day
        
        for day in range(1, forecast_days + 1):
            # Simple linear prediction
            predicted = current_value + (daily_change * day)
            
            # Add uncertainty based on volatility and confidence
            uncertainty = trend.volatility * (1 - trend.confidence) * np.sqrt(day)
            
            predicted_values.append(max(0.0, min(1.0, predicted)))  # Clamp to [0, 1]
            confidence_intervals.append((
                max(0.0, predicted - uncertainty),
                min(1.0, predicted + uncertainty)
            ))
        
        # Assess risk
        risk_assessment = self._assess_forecast_risk(predicted_values, trend)
        
        # Generate recommendations
        recommendations = self._generate_forecast_recommendations(metric_name, trend, predicted_values)
        
        return QualityForecast(
            metric_name=metric_name,
            forecast_horizon=forecast_days,
            predicted_values=predicted_values,
            confidence_intervals=confidence_intervals,
            forecast_accuracy=trend.confidence,
            risk_assessment=risk_assessment,
            recommendations=recommendations
        )
    
    def _assess_forecast_risk(self, predicted_values: List[float], trend: QualityTrend) -> str:
        """Assess risk level based on forecast."""
        min_predicted = min(predicted_values)
        trend_direction = trend.direction
        
        if min_predicted < 0.5:
            return "高风险：预测质量可能降至临界水平"
        elif min_predicted < 0.7 and trend_direction == TrendDirection.DECLINING:
            return "中等风险：质量呈下降趋势，需要关注"
        elif trend_direction == TrendDirection.VOLATILE:
            return "中等风险：质量波动较大，不够稳定"
        elif trend_direction == TrendDirection.IMPROVING:
            return "低风险：质量呈改善趋势"
        else:
            return "低风险：质量保持稳定"
    
    def _generate_forecast_recommendations(self, 
                                         metric_name: str, 
                                         trend: QualityTrend, 
                                         predicted_values: List[float]) -> List[str]:
        """Generate recommendations based on forecast."""
        recommendations = []
        
        min_predicted = min(predicted_values)
        trend_direction = trend.direction
        
        # General recommendations based on trend
        if trend_direction == TrendDirection.DECLINING:
            recommendations.append(f"立即调查 {metric_name} 下降的根本原因")
            recommendations.append("考虑暂停相关任务，直到质量问题得到解决")
            
        elif trend_direction == TrendDirection.VOLATILE:
            recommendations.append(f"分析 {metric_name} 波动的影响因素")
            recommendations.append("标准化输入数据和处理流程")
            
        # Specific recommendations based on metric type
        if "faithfulness" in metric_name and min_predicted < 0.7:
            recommendations.extend([
                "检查和优化提示词模板",
                "增强上下文相关性验证",
                "实施更严格的事实核查机制"
            ])
            
        elif "relevancy" in metric_name and min_predicted < 0.7:
            recommendations.extend([
                "优化问题理解和意图识别",
                "改进检索算法的精确度",
                "增加相关性训练数据"
            ])
            
        elif "precision" in metric_name and min_predicted < 0.6:
            recommendations.extend([
                "优化检索排序算法",
                "增加负样本训练",
                "调整检索阈值参数"
            ])
            
        elif "recall" in metric_name and min_predicted < 0.6:
            recommendations.extend([
                "扩大检索范围和知识库",
                "优化向量化和索引策略",
                "检查是否遗漏重要信息源"
            ])
        
        # Preventive recommendations
        if min_predicted > 0.8:
            recommendations.append("当前质量良好，建议保持现有配置和流程")
        
        return recommendations
    
    def get_quality_summary(self, period: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get comprehensive quality summary for the specified period."""
        trends = self.analyze_all_metrics(period)
        active_alerts = self.get_active_alerts()
        
        # Calculate overall health score
        health_scores = []
        for trend in trends.values():
            if trend.direction != TrendDirection.INSUFFICIENT_DATA:
                # Health score based on current value and trend direction
                base_score = trend.current_value
                if trend.direction == TrendDirection.IMPROVING:
                    base_score += 0.1
                elif trend.direction == TrendDirection.DECLINING:
                    base_score -= 0.1
                health_scores.append(base_score)
        
        overall_health = statistics.mean(health_scores) if health_scores else 0.0
        
        # Categorize alerts by severity
        alert_counts = {severity.value: 0 for severity in AlertSeverity}
        for alert in active_alerts:
            alert_counts[alert.severity.value] += 1
        
        return {
            "period": str(period) if period else "all_time",
            "overall_health_score": overall_health,
            "trends": {name: trend.to_dict() for name, trend in trends.items()},
            "active_alerts": {
                "total": len(active_alerts),
                "by_severity": alert_counts,
                "details": [alert.to_dict() for alert in active_alerts]
            },
            "recommendations": self._generate_summary_recommendations(trends, active_alerts),
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_summary_recommendations(self, 
                                        trends: Dict[str, QualityTrend], 
                                        alerts: List[QualityAlert]) -> List[str]:
        """Generate summary recommendations based on trends and alerts."""
        recommendations = []
        
        # Critical alerts
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        if critical_alerts:
            recommendations.append("🚨 存在严重质量问题，需要立即处理")
            
        # Declining trends
        declining_metrics = [name for name, trend in trends.items() 
                           if trend.direction == TrendDirection.DECLINING]
        if declining_metrics:
            recommendations.append(f"📉 以下指标呈下降趋势：{', '.join(declining_metrics)}")
            
        # Volatile metrics
        volatile_metrics = [name for name, trend in trends.items() 
                          if trend.direction == TrendDirection.VOLATILE]
        if volatile_metrics:
            recommendations.append(f"📊 以下指标波动较大：{', '.join(volatile_metrics)}")
            
        # Improving trends
        improving_metrics = [name for name, trend in trends.items() 
                           if trend.direction == TrendDirection.IMPROVING]
        if improving_metrics:
            recommendations.append(f"📈 以下指标呈改善趋势：{', '.join(improving_metrics)}")
            
        # General recommendations
        if not recommendations:
            recommendations.append("✅ 整体质量状况良好，建议保持当前配置")
        
        return recommendations
    
    def configure_alert_thresholds(self, 
                                 metric_name: str, 
                                 thresholds: Dict[str, float]) -> None:
        """Configure alert thresholds for a specific metric."""
        if metric_name not in self.alert_thresholds:
            self.alert_thresholds[metric_name] = {}
        
        self.alert_thresholds[metric_name].update(thresholds)
        logger.info(f"Updated alert thresholds for {metric_name}: {thresholds}")
    
    def export_trend_data(self, 
                         metric_name: str, 
                         period: Optional[timedelta] = None) -> Dict[str, Any]:
        """Export trend data for external analysis."""
        # Filter evaluations by period
        evaluations = list(self.evaluation_history)
        if period:
            cutoff_time = datetime.now() - period
            evaluations = [
                eval_result for eval_result in evaluations
                if eval_result.evaluation_date >= cutoff_time
            ]
        
        # Extract data points
        data_points = []
        for eval_result in evaluations:
            if metric_name == "overall_score":
                value = eval_result.overall_score
            elif metric_name in eval_result.metrics:
                value = eval_result.metrics[metric_name]
            else:
                continue
            
            data_points.append({
                "timestamp": eval_result.evaluation_date.isoformat(),
                "value": value,
                "evaluation_id": eval_result.evaluation_id
            })
        
        # Get trend analysis
        trend = self.analyze_metric_trend(metric_name, period)
        
        return {
            "metric_name": metric_name,
            "period": str(period) if period else "all_time",
            "data_points": data_points,
            "trend_analysis": trend.to_dict(),
            "exported_at": datetime.now().isoformat()
        }