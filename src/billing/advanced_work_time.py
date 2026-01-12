"""
Advanced Work Time Calculator for SuperInsight Platform.

Extends the base WorkTimeCalculator with detailed time tracking,
activity monitoring, and productivity analysis capabilities.
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import logging
import statistics
from collections import defaultdict

from src.quality_billing.work_time_calculator import (
    WorkTimeCalculator, WorkTimeRecord, WorkTimeType, 
    WorkTimeStatus, WorkTimeStatistics, WorkTimeAnomaly, AnomalyType
)

logger = logging.getLogger(__name__)


class ActivityType(str, Enum):
    """Activity type enumeration."""
    ANNOTATION = "annotation"
    REVIEW = "review"
    CORRECTION = "correction"
    RESEARCH = "research"
    COMMUNICATION = "communication"
    IDLE = "idle"
    BREAK = "break"


class ProductivityLevel(str, Enum):
    """Productivity level enumeration."""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    BELOW_AVERAGE = "below_average"
    POOR = "poor"


@dataclass
class ActivityRecord:
    """Activity record for detailed tracking."""
    id: str
    user_id: str
    session_id: str
    activity_type: ActivityType
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: int = 0
    items_processed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DetailedWorkTime:
    """Detailed work time analysis result."""
    user_id: str
    period_start: datetime
    period_end: datetime
    total_hours: float
    billable_hours: float
    productive_hours: float
    break_time: float
    overtime_hours: float
    activity_breakdown: Dict[str, float]
    productivity_score: float
    validation_status: str
    quality_factor: float
    efficiency_ratio: float
    cost_per_hour: Decimal
    total_cost: Decimal


@dataclass
class ProductivityMetrics:
    """Productivity analysis metrics."""
    user_id: str
    period: str
    productive_hours: float
    total_hours: float
    productivity_ratio: float
    score: float
    level: ProductivityLevel
    items_per_hour: float
    quality_adjusted_output: float
    trend: str  # improving, stable, declining
    recommendations: List[str]


class ActivityMonitor:
    """
    Activity monitoring for detailed work tracking.
    
    Tracks user activities during work sessions for accurate
    billing and productivity analysis.
    """
    
    def __init__(self):
        self.activities: Dict[str, List[ActivityRecord]] = defaultdict(list)
        self.active_activities: Dict[str, ActivityRecord] = {}
        
        # Activity weights for productivity calculation
        self.activity_weights = {
            ActivityType.ANNOTATION: 1.0,
            ActivityType.REVIEW: 0.9,
            ActivityType.CORRECTION: 0.8,
            ActivityType.RESEARCH: 0.6,
            ActivityType.COMMUNICATION: 0.4,
            ActivityType.IDLE: 0.0,
            ActivityType.BREAK: 0.0
        }
    
    def start_activity(self, user_id: str, session_id: str, 
                      activity_type: ActivityType,
                      metadata: Dict[str, Any] = None) -> str:
        """Start tracking an activity."""
        activity_id = f"{user_id}_{session_id}_{datetime.now().timestamp()}"
        
        # End any existing activity for this user
        if user_id in self.active_activities:
            self.end_activity(user_id)
        
        activity = ActivityRecord(
            id=activity_id,
            user_id=user_id,
            session_id=session_id,
            activity_type=activity_type,
            start_time=datetime.now(),
            metadata=metadata or {}
        )
        
        self.active_activities[user_id] = activity
        logger.debug(f"Started activity {activity_id} for user {user_id}")
        return activity_id
    
    def end_activity(self, user_id: str, items_processed: int = 0) -> Optional[ActivityRecord]:
        """End the current activity for a user."""
        if user_id not in self.active_activities:
            return None
        
        activity = self.active_activities.pop(user_id)
        activity.end_time = datetime.now()
        activity.duration_seconds = int(
            (activity.end_time - activity.start_time).total_seconds()
        )
        activity.items_processed = items_processed
        
        self.activities[user_id].append(activity)
        logger.debug(f"Ended activity {activity.id}, duration: {activity.duration_seconds}s")
        return activity
    
    def get_activity_data(self, user_id: str, start_time: datetime, 
                         end_time: datetime) -> Dict[str, Any]:
        """Get activity data for a time period."""
        user_activities = [
            a for a in self.activities.get(user_id, [])
            if a.start_time >= start_time and 
               (a.end_time is None or a.end_time <= end_time)
        ]
        
        # Calculate breakdown by activity type
        breakdown = defaultdict(float)
        total_items = 0
        total_duration = 0
        
        for activity in user_activities:
            duration_hours = activity.duration_seconds / 3600
            breakdown[activity.activity_type.value] += duration_hours
            total_items += activity.items_processed
            total_duration += activity.duration_seconds
        
        # Calculate break time
        break_time = breakdown.get(ActivityType.BREAK.value, 0) + \
                    breakdown.get(ActivityType.IDLE.value, 0)
        
        return {
            'user_id': user_id,
            'period_start': start_time.isoformat(),
            'period_end': end_time.isoformat(),
            'breakdown': dict(breakdown),
            'total_items': total_items,
            'total_duration_hours': total_duration / 3600,
            'break_time': break_time,
            'activity_count': len(user_activities)
        }
    
    def calculate_weighted_productivity(self, user_id: str, 
                                       start_time: datetime,
                                       end_time: datetime) -> float:
        """Calculate weighted productivity score."""
        user_activities = [
            a for a in self.activities.get(user_id, [])
            if a.start_time >= start_time and 
               (a.end_time is None or a.end_time <= end_time)
        ]
        
        if not user_activities:
            return 0.0
        
        weighted_sum = 0.0
        total_duration = 0.0
        
        for activity in user_activities:
            weight = self.activity_weights.get(activity.activity_type, 0.5)
            duration = activity.duration_seconds / 3600
            weighted_sum += weight * duration
            total_duration += duration
        
        if total_duration == 0:
            return 0.0
        
        return weighted_sum / total_duration


class ProductivityAnalyzer:
    """
    Productivity analysis for work time optimization.
    
    Analyzes work patterns and provides productivity insights.
    """
    
    def __init__(self):
        self.historical_data: Dict[str, List[ProductivityMetrics]] = defaultdict(list)
        
        # Productivity thresholds
        self.thresholds = {
            ProductivityLevel.EXCELLENT: 0.90,
            ProductivityLevel.GOOD: 0.75,
            ProductivityLevel.AVERAGE: 0.60,
            ProductivityLevel.BELOW_AVERAGE: 0.45,
            ProductivityLevel.POOR: 0.0
        }
    
    def analyze(self, user_id: str, activity_data: Dict[str, Any],
               task_context: Dict[str, Any] = None) -> ProductivityMetrics:
        """Analyze productivity for a user."""
        total_hours = activity_data.get('total_duration_hours', 0)
        break_time = activity_data.get('break_time', 0)
        total_items = activity_data.get('total_items', 0)
        
        # Calculate productive hours (excluding breaks)
        productive_hours = max(0, total_hours - break_time)
        
        # Calculate productivity ratio
        productivity_ratio = productive_hours / total_hours if total_hours > 0 else 0
        
        # Calculate items per hour
        items_per_hour = total_items / productive_hours if productive_hours > 0 else 0
        
        # Get expected items per hour from task context
        expected_items_per_hour = 10.0  # Default
        if task_context:
            expected_items_per_hour = task_context.get('expected_items_per_hour', 10.0)
        
        # Calculate productivity score
        efficiency = items_per_hour / expected_items_per_hour if expected_items_per_hour > 0 else 0
        score = min(1.0, productivity_ratio * 0.4 + min(efficiency, 1.0) * 0.6)
        
        # Determine productivity level
        level = self._determine_level(score)
        
        # Calculate trend
        trend = self._calculate_trend(user_id)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            score, productivity_ratio, items_per_hour, expected_items_per_hour
        )
        
        metrics = ProductivityMetrics(
            user_id=user_id,
            period=activity_data.get('period_start', ''),
            productive_hours=productive_hours,
            total_hours=total_hours,
            productivity_ratio=productivity_ratio,
            score=score,
            level=level,
            items_per_hour=items_per_hour,
            quality_adjusted_output=total_items * score,
            trend=trend,
            recommendations=recommendations
        )
        
        # Store for trend analysis
        self.historical_data[user_id].append(metrics)
        
        return metrics
    
    def _determine_level(self, score: float) -> ProductivityLevel:
        """Determine productivity level from score."""
        if score >= self.thresholds[ProductivityLevel.EXCELLENT]:
            return ProductivityLevel.EXCELLENT
        elif score >= self.thresholds[ProductivityLevel.GOOD]:
            return ProductivityLevel.GOOD
        elif score >= self.thresholds[ProductivityLevel.AVERAGE]:
            return ProductivityLevel.AVERAGE
        elif score >= self.thresholds[ProductivityLevel.BELOW_AVERAGE]:
            return ProductivityLevel.BELOW_AVERAGE
        else:
            return ProductivityLevel.POOR
    
    def _calculate_trend(self, user_id: str) -> str:
        """Calculate productivity trend."""
        history = self.historical_data.get(user_id, [])
        if len(history) < 3:
            return "stable"
        
        recent_scores = [m.score for m in history[-5:]]
        if len(recent_scores) < 2:
            return "stable"
        
        # Simple trend detection
        avg_first_half = statistics.mean(recent_scores[:len(recent_scores)//2])
        avg_second_half = statistics.mean(recent_scores[len(recent_scores)//2:])
        
        diff = avg_second_half - avg_first_half
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        else:
            return "stable"
    
    def _generate_recommendations(self, score: float, productivity_ratio: float,
                                 items_per_hour: float, 
                                 expected_items_per_hour: float) -> List[str]:
        """Generate productivity improvement recommendations."""
        recommendations = []
        
        if productivity_ratio < 0.7:
            recommendations.append("Consider reducing break time to improve productivity ratio")
        
        if items_per_hour < expected_items_per_hour * 0.8:
            recommendations.append("Focus on improving processing speed through practice")
        
        if score < 0.6:
            recommendations.append("Review work processes for potential optimizations")
        
        if score >= 0.9:
            recommendations.append("Excellent performance! Consider mentoring others")
        
        return recommendations


class TimeValidator:
    """
    Time entry validation and anomaly detection.
    
    Validates work time entries and detects anomalies.
    """
    
    def __init__(self):
        self.validation_rules = {
            'max_daily_hours': 14,
            'min_session_minutes': 5,
            'max_session_hours': 6,
            'max_idle_percentage': 0.3,
            'min_items_per_hour': 1
        }
    
    def validate_time_entries(self, user_id: str, start_time: datetime,
                             end_time: datetime, 
                             activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate time entries for a period."""
        issues = []
        warnings = []
        
        total_hours = activity_data.get('total_duration_hours', 0)
        break_time = activity_data.get('break_time', 0)
        total_items = activity_data.get('total_items', 0)
        
        # Check daily hours limit
        if total_hours > self.validation_rules['max_daily_hours']:
            issues.append({
                'type': 'excessive_hours',
                'message': f"Total hours ({total_hours:.1f}) exceeds daily limit",
                'severity': 'high'
            })
        
        # Check idle percentage
        if total_hours > 0:
            idle_ratio = break_time / total_hours
            if idle_ratio > self.validation_rules['max_idle_percentage']:
                warnings.append({
                    'type': 'high_idle_time',
                    'message': f"Idle time ({idle_ratio:.1%}) exceeds threshold",
                    'severity': 'medium'
                })
        
        # Check minimum productivity
        productive_hours = total_hours - break_time
        if productive_hours > 0:
            items_per_hour = total_items / productive_hours
            if items_per_hour < self.validation_rules['min_items_per_hour']:
                warnings.append({
                    'type': 'low_productivity',
                    'message': f"Items per hour ({items_per_hour:.1f}) below minimum",
                    'severity': 'low'
                })
        
        status = 'valid' if not issues else 'invalid'
        if warnings and not issues:
            status = 'valid_with_warnings'
        
        return {
            'user_id': user_id,
            'period_start': start_time.isoformat(),
            'period_end': end_time.isoformat(),
            'status': status,
            'issues': issues,
            'warnings': warnings,
            'validated_at': datetime.now().isoformat()
        }
    
    def detect_anomalies(self, user_id: str, 
                        work_records: List[WorkTimeRecord]) -> List[Dict[str, Any]]:
        """Detect anomalies in work records."""
        anomalies = []
        
        if not work_records:
            return anomalies
        
        # Group by date
        daily_records = defaultdict(list)
        for record in work_records:
            date_key = record.start_time.date()
            daily_records[date_key].append(record)
        
        for date_key, records in daily_records.items():
            # Check for overlapping sessions
            sorted_records = sorted(records, key=lambda r: r.start_time)
            for i in range(1, len(sorted_records)):
                prev = sorted_records[i-1]
                curr = sorted_records[i]
                if prev.end_time and curr.start_time < prev.end_time:
                    anomalies.append({
                        'type': 'overlapping_sessions',
                        'date': date_key.isoformat(),
                        'records': [prev.id, curr.id],
                        'severity': 'high'
                    })
            
            # Check for unusual patterns
            total_minutes = sum(r.duration_minutes for r in records)
            if total_minutes > self.validation_rules['max_daily_hours'] * 60:
                anomalies.append({
                    'type': 'excessive_daily_hours',
                    'date': date_key.isoformat(),
                    'total_hours': total_minutes / 60,
                    'severity': 'medium'
                })
        
        return anomalies


class QualityFactorCalculator:
    """
    Quality factor calculation for work time billing.
    
    Calculates quality-based adjustments to work time billing.
    """
    
    def __init__(self):
        self.quality_weights = {
            'accuracy': 0.40,
            'consistency': 0.25,
            'completeness': 0.20,
            'timeliness': 0.15
        }
        
        self.factor_ranges = {
            'excellent': (0.95, 1.0, 1.20),  # min_score, max_score, factor
            'good': (0.85, 0.95, 1.10),
            'average': (0.70, 0.85, 1.00),
            'below_average': (0.50, 0.70, 0.90),
            'poor': (0.0, 0.50, 0.75)
        }
    
    async def calculate_quality_factor(self, user_id: str, 
                                      task_context: Dict[str, Any] = None) -> float:
        """Calculate quality factor for billing adjustment."""
        # Get quality metrics (would integrate with quality system)
        quality_metrics = await self._get_quality_metrics(user_id, task_context)
        
        # Calculate weighted quality score
        weighted_score = 0.0
        for metric, weight in self.quality_weights.items():
            score = quality_metrics.get(metric, 0.75)
            weighted_score += score * weight
        
        # Determine quality factor
        factor = self._score_to_factor(weighted_score)
        
        return factor
    
    def _score_to_factor(self, score: float) -> float:
        """Convert quality score to billing factor."""
        for level, (min_score, max_score, factor) in self.factor_ranges.items():
            if min_score <= score < max_score:
                return factor
        return 1.0
    
    async def _get_quality_metrics(self, user_id: str, 
                                  task_context: Dict[str, Any] = None) -> Dict[str, float]:
        """Get quality metrics for a user."""
        # This would integrate with the quality assessment system
        # For now, return simulated metrics
        return {
            'accuracy': 0.85,
            'consistency': 0.82,
            'completeness': 0.88,
            'timeliness': 0.90
        }


class AdvancedWorkTimeCalculator(WorkTimeCalculator):
    """
    Advanced work time calculator with detailed tracking.
    
    Extends base WorkTimeCalculator with activity monitoring,
    productivity analysis, and quality-based adjustments.
    """
    
    def __init__(self):
        super().__init__()
        self.activity_monitor = ActivityMonitor()
        self.productivity_analyzer = ProductivityAnalyzer()
        self.time_validator = TimeValidator()
        self.quality_calculator = QualityFactorCalculator()
        
        # Billing rates
        self.default_hourly_rate = Decimal("50.00")
        self.overtime_multiplier = Decimal("1.5")
    
    async def calculate_detailed_work_time(
        self, 
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        task_context: Dict[str, Any] = None
    ) -> DetailedWorkTime:
        """Calculate detailed work time with all metrics."""
        # Get base work time from parent
        base_dimensions = self.calculate_multi_dimensional_hours(
            user_id, start_time, end_time
        )
        
        # Get activity data
        activity_data = self.activity_monitor.get_activity_data(
            user_id, start_time, end_time
        )
        
        # Analyze productivity
        productivity_metrics = self.productivity_analyzer.analyze(
            user_id, activity_data, task_context
        )
        
        # Validate time entries
        validation_result = self.time_validator.validate_time_entries(
            user_id, start_time, end_time, activity_data
        )
        
        # Calculate quality factor
        quality_factor = await self.quality_calculator.calculate_quality_factor(
            user_id, task_context
        )
        
        # Calculate billable hours
        total_hours = base_dimensions.get('total_hours', 0)
        break_hours = base_dimensions.get('pause_hours', 0)
        billable_hours = max(0, total_hours - break_hours)
        
        # Calculate overtime
        standard_hours = 8.0
        overtime_hours = max(0, billable_hours - standard_hours)
        
        # Calculate efficiency ratio
        expected_output = task_context.get('expected_items', 0) if task_context else 0
        actual_output = activity_data.get('total_items', 0)
        efficiency_ratio = actual_output / expected_output if expected_output > 0 else 1.0
        
        # Calculate costs
        hourly_rate = task_context.get('hourly_rate', self.default_hourly_rate) \
            if task_context else self.default_hourly_rate
        
        regular_cost = Decimal(str(min(billable_hours, standard_hours))) * hourly_rate
        overtime_cost = Decimal(str(overtime_hours)) * hourly_rate * self.overtime_multiplier
        
        # Apply quality factor
        total_cost = (regular_cost + overtime_cost) * Decimal(str(quality_factor))
        total_cost = total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        cost_per_hour = total_cost / Decimal(str(billable_hours)) \
            if billable_hours > 0 else Decimal("0")
        
        return DetailedWorkTime(
            user_id=user_id,
            period_start=start_time,
            period_end=end_time,
            total_hours=total_hours,
            billable_hours=billable_hours,
            productive_hours=productivity_metrics.productive_hours,
            break_time=break_hours,
            overtime_hours=overtime_hours,
            activity_breakdown=activity_data.get('breakdown', {}),
            productivity_score=productivity_metrics.score,
            validation_status=validation_result['status'],
            quality_factor=quality_factor,
            efficiency_ratio=efficiency_ratio,
            cost_per_hour=cost_per_hour,
            total_cost=total_cost
        )
    
    async def calculate_billable_hours(self, 
                                      activity_data: Dict[str, Any]) -> float:
        """Calculate billable hours from activity data."""
        total_hours = activity_data.get('total_duration_hours', 0)
        break_time = activity_data.get('break_time', 0)
        
        # Subtract breaks and idle time
        billable = total_hours - break_time
        
        # Apply minimum threshold
        if billable < 0.25:  # Less than 15 minutes
            return 0.0
        
        return round(billable, 2)
    
    async def calculate_overtime(self, base_work_time: Any) -> float:
        """Calculate overtime hours."""
        if hasattr(base_work_time, 'total_hours'):
            total = base_work_time.total_hours
        else:
            total = 0
        
        standard_hours = 8.0
        return max(0, total - standard_hours)
    
    def get_detailed_report(self, user_id: str, start_date: datetime,
                           end_date: datetime) -> Dict[str, Any]:
        """Get detailed work time report."""
        # Get base report
        base_report = self.get_work_time_report(user_id, start_date, end_date)
        
        # Get activity breakdown
        activity_data = self.activity_monitor.get_activity_data(
            user_id, start_date, end_date
        )
        
        # Get anomalies
        user_records = [r for r in self.records.values() 
                       if r.user_id == user_id and 
                       start_date <= r.start_time <= end_date]
        anomalies = self.time_validator.detect_anomalies(user_id, user_records)
        
        # Enhance report
        base_report['activity_breakdown'] = activity_data.get('breakdown', {})
        base_report['detected_anomalies'] = anomalies
        base_report['total_items_processed'] = activity_data.get('total_items', 0)
        
        return base_report


# Convenience function for getting calculator instance
def get_advanced_work_time_calculator() -> AdvancedWorkTimeCalculator:
    """Get an instance of the advanced work time calculator."""
    return AdvancedWorkTimeCalculator()
