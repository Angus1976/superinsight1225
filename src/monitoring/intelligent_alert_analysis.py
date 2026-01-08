"""
Intelligent Alert Analysis System

Provides advanced alert analysis capabilities including:
- Alert pattern recognition and classification
- Root cause analysis and correlation
- Alert prediction and prevention
- Alert effectiveness evaluation and optimization
- Machine learning-based alert insights
"""

import logging
import asyncio
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque, Counter
import hashlib
import statistics

from .alert_rule_engine import Alert, AlertLevel, AlertCategory, AlertStatus

logger = logging.getLogger(__name__)


class AlertPattern(str, Enum):
    """Alert pattern types."""
    BURST = "burst"                    # Sudden spike in alerts
    CASCADE = "cascade"                # Cascading failure pattern
    PERIODIC = "periodic"              # Recurring pattern
    ESCALATION = "escalation"          # Escalating severity pattern
    CORRELATION = "correlation"        # Correlated alerts
    ANOMALY = "anomaly"               # Anomalous alert behavior
    STORM = "storm"                   # Alert storm pattern


class RootCauseCategory(str, Enum):
    """Root cause categories."""
    INFRASTRUCTURE = "infrastructure"   # Infrastructure issues
    APPLICATION = "application"        # Application bugs/issues
    CONFIGURATION = "configuration"    # Configuration problems
    CAPACITY = "capacity"             # Capacity/resource issues
    EXTERNAL = "external"             # External dependencies
    HUMAN_ERROR = "human_error"       # Human operational errors
    SECURITY = "security"             # Security incidents
    UNKNOWN = "unknown"               # Unknown root cause


class PredictionConfidence(str, Enum):
    """Prediction confidence levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class AlertPatternMatch:
    """Alert pattern match result."""
    pattern_id: str
    pattern_type: AlertPattern
    confidence: float
    alerts: List[UUID]
    time_window: Tuple[datetime, datetime]
    characteristics: Dict[str, Any]
    
    # Pattern-specific data
    burst_rate: Optional[float] = None
    cascade_depth: Optional[int] = None
    period_hours: Optional[float] = None
    correlation_strength: Optional[float] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "confidence": self.confidence,
            "alerts": [str(alert_id) for alert_id in self.alerts],
            "time_window": [
                self.time_window[0].isoformat(),
                self.time_window[1].isoformat()
            ],
            "characteristics": self.characteristics,
            "burst_rate": self.burst_rate,
            "cascade_depth": self.cascade_depth,
            "period_hours": self.period_hours,
            "correlation_strength": self.correlation_strength,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class RootCauseAnalysis:
    """Root cause analysis result."""
    analysis_id: str
    alert_ids: List[UUID]
    root_cause_category: RootCauseCategory
    confidence: float
    description: str
    
    # Evidence and reasoning
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Related patterns
    related_patterns: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "analysis_id": self.analysis_id,
            "alert_ids": [str(alert_id) for alert_id in self.alert_ids],
            "root_cause_category": self.root_cause_category.value,
            "confidence": self.confidence,
            "description": self.description,
            "evidence": self.evidence,
            "reasoning": self.reasoning,
            "recommendations": self.recommendations,
            "related_patterns": self.related_patterns,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class AlertPrediction:
    """Alert prediction result."""
    prediction_id: str
    predicted_alert_type: str
    predicted_level: AlertLevel
    predicted_category: AlertCategory
    confidence: PredictionConfidence
    probability: float
    
    # Prediction details
    time_window: Tuple[datetime, datetime]
    triggering_conditions: Dict[str, Any]
    prevention_actions: List[str] = field(default_factory=list)
    
    # Model information
    model_name: str = "ensemble"
    model_version: str = "1.0"
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "prediction_id": self.prediction_id,
            "predicted_alert_type": self.predicted_alert_type,
            "predicted_level": self.predicted_level.value,
            "predicted_category": self.predicted_category.value,
            "confidence": self.confidence.value,
            "probability": self.probability,
            "time_window": [
                self.time_window[0].isoformat(),
                self.time_window[1].isoformat()
            ],
            "triggering_conditions": self.triggering_conditions,
            "prevention_actions": self.prevention_actions,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class AlertEffectivenessMetrics:
    """Alert effectiveness evaluation metrics."""
    rule_id: str
    evaluation_period: Tuple[datetime, datetime]
    
    # Basic metrics
    total_alerts: int
    true_positives: int
    false_positives: int
    false_negatives: int
    
    # Calculated metrics
    precision: float
    recall: float
    f1_score: float
    
    # Response metrics
    avg_response_time: float
    avg_resolution_time: float
    escalation_rate: float
    
    # Effectiveness score
    effectiveness_score: float
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "evaluation_period": [
                self.evaluation_period[0].isoformat(),
                self.evaluation_period[1].isoformat()
            ],
            "total_alerts": self.total_alerts,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "avg_response_time": self.avg_response_time,
            "avg_resolution_time": self.avg_resolution_time,
            "escalation_rate": self.escalation_rate,
            "effectiveness_score": self.effectiveness_score,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat()
        }


class AlertPatternRecognizer:
    """
    Alert pattern recognition engine.
    
    Identifies common alert patterns such as bursts, cascades, and periodic patterns.
    """
    
    def __init__(self):
        self.pattern_history: List[AlertPatternMatch] = []
        self.alert_sequences: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Pattern detection thresholds
        self.burst_threshold = 5  # alerts per minute
        self.cascade_threshold = 3  # levels of cascade
        self.correlation_threshold = 0.7  # correlation coefficient
        self.period_detection_window = 24  # hours
    
    async def analyze_alerts(self, alerts: List[Alert], time_window_hours: int = 1) -> List[AlertPatternMatch]:
        """Analyze alerts for patterns."""
        patterns = []
        
        if not alerts:
            return patterns
        
        # Sort alerts by timestamp
        sorted_alerts = sorted(alerts, key=lambda a: a.created_at)
        
        # Detect different pattern types
        patterns.extend(await self._detect_burst_patterns(sorted_alerts, time_window_hours))
        patterns.extend(await self._detect_cascade_patterns(sorted_alerts))
        patterns.extend(await self._detect_periodic_patterns(sorted_alerts))
        patterns.extend(await self._detect_correlation_patterns(sorted_alerts))
        patterns.extend(await self._detect_storm_patterns(sorted_alerts, time_window_hours))
        
        # Store patterns in history
        self.pattern_history.extend(patterns)
        
        # Keep only recent patterns
        cutoff = datetime.now() - timedelta(days=7)
        self.pattern_history = [p for p in self.pattern_history if p.created_at >= cutoff]
        
        return patterns
    
    async def _detect_burst_patterns(self, alerts: List[Alert], time_window_hours: int) -> List[AlertPatternMatch]:
        """Detect burst patterns (sudden spike in alerts)."""
        patterns = []
        
        if len(alerts) < 3:
            return patterns
        
        # Group alerts by time windows
        window_size = timedelta(minutes=5)  # 5-minute windows
        windows = {}
        
        for alert in alerts:
            window_start = alert.created_at.replace(second=0, microsecond=0)
            window_start = window_start.replace(minute=(window_start.minute // 5) * 5)
            
            if window_start not in windows:
                windows[window_start] = []
            windows[window_start].append(alert)
        
        # Find windows with burst activity
        for window_start, window_alerts in windows.items():
            alert_rate = len(window_alerts) / 5.0  # alerts per minute
            
            if alert_rate >= self.burst_threshold:
                pattern_id = f"burst_{hashlib.md5(f'{window_start}'.encode()).hexdigest()[:8]}"
                
                pattern = AlertPatternMatch(
                    pattern_id=pattern_id,
                    pattern_type=AlertPattern.BURST,
                    confidence=min(1.0, alert_rate / (self.burst_threshold * 2)),
                    alerts=[alert.id for alert in window_alerts],
                    time_window=(window_start, window_start + window_size),
                    characteristics={
                        "alert_count": len(window_alerts),
                        "time_window_minutes": 5,
                        "alert_rate_per_minute": alert_rate
                    },
                    burst_rate=alert_rate
                )
                
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_cascade_patterns(self, alerts: List[Alert]) -> List[AlertPatternMatch]:
        """Detect cascade patterns (escalating severity)."""
        patterns = []
        
        if len(alerts) < 3:
            return patterns
        
        # Group alerts by source/component
        by_source = defaultdict(list)
        for alert in alerts:
            by_source[alert.source].append(alert)
        
        # Look for escalating patterns within each source
        for source, source_alerts in by_source.items():
            if len(source_alerts) < 3:
                continue
            
            # Sort by time
            source_alerts.sort(key=lambda a: a.created_at)
            
            # Check for severity escalation
            severity_levels = {
                AlertLevel.INFO: 1,
                AlertLevel.WARNING: 2,
                AlertLevel.HIGH: 3,
                AlertLevel.CRITICAL: 4,
                AlertLevel.EMERGENCY: 5
            }
            
            escalation_sequences = []
            current_sequence = [source_alerts[0]]
            
            for i in range(1, len(source_alerts)):
                prev_alert = source_alerts[i-1]
                curr_alert = source_alerts[i]
                
                # Check if severity increased and time gap is reasonable
                time_gap = (curr_alert.created_at - prev_alert.created_at).total_seconds()
                if (severity_levels[curr_alert.level] > severity_levels[prev_alert.level] and
                    time_gap <= 3600):  # Within 1 hour
                    current_sequence.append(curr_alert)
                else:
                    if len(current_sequence) >= self.cascade_threshold:
                        escalation_sequences.append(current_sequence)
                    current_sequence = [curr_alert]
            
            # Check final sequence
            if len(current_sequence) >= self.cascade_threshold:
                escalation_sequences.append(current_sequence)
            
            # Create patterns for escalation sequences
            for sequence in escalation_sequences:
                pattern_id = f"cascade_{hashlib.md5(f'{source}_{sequence[0].id}'.encode()).hexdigest()[:8]}"
                
                pattern = AlertPatternMatch(
                    pattern_id=pattern_id,
                    pattern_type=AlertPattern.CASCADE,
                    confidence=min(1.0, len(sequence) / 5.0),
                    alerts=[alert.id for alert in sequence],
                    time_window=(sequence[0].created_at, sequence[-1].created_at),
                    characteristics={
                        "source": source,
                        "escalation_steps": len(sequence),
                        "severity_progression": [alert.level.value for alert in sequence],
                        "total_duration_minutes": (sequence[-1].created_at - sequence[0].created_at).total_seconds() / 60
                    },
                    cascade_depth=len(sequence)
                )
                
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_periodic_patterns(self, alerts: List[Alert]) -> List[AlertPatternMatch]:
        """Detect periodic patterns (recurring alerts)."""
        patterns = []
        
        if len(alerts) < 5:
            return patterns
        
        # Group alerts by type/source
        by_type = defaultdict(list)
        for alert in alerts:
            key = f"{alert.source}:{alert.metric_name or 'unknown'}"
            by_type[key].append(alert)
        
        # Analyze each type for periodicity
        for alert_type, type_alerts in by_type.items():
            if len(type_alerts) < 5:
                continue
            
            # Sort by time
            type_alerts.sort(key=lambda a: a.created_at)
            
            # Calculate time intervals between alerts
            intervals = []
            for i in range(1, len(type_alerts)):
                interval = (type_alerts[i].created_at - type_alerts[i-1].created_at).total_seconds() / 3600  # hours
                intervals.append(interval)
            
            if len(intervals) < 4:
                continue
            
            # Check for consistent intervals (periodic pattern)
            mean_interval = statistics.mean(intervals)
            std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
            
            # Consider it periodic if standard deviation is low relative to mean
            if mean_interval > 0 and std_interval / mean_interval < 0.3:  # 30% variation allowed
                pattern_id = f"periodic_{hashlib.md5(alert_type.encode()).hexdigest()[:8]}"
                
                pattern = AlertPatternMatch(
                    pattern_id=pattern_id,
                    pattern_type=AlertPattern.PERIODIC,
                    confidence=max(0.5, 1.0 - (std_interval / mean_interval)),
                    alerts=[alert.id for alert in type_alerts],
                    time_window=(type_alerts[0].created_at, type_alerts[-1].created_at),
                    characteristics={
                        "alert_type": alert_type,
                        "occurrence_count": len(type_alerts),
                        "mean_interval_hours": mean_interval,
                        "interval_std_hours": std_interval,
                        "regularity_score": 1.0 - (std_interval / mean_interval) if mean_interval > 0 else 0
                    },
                    period_hours=mean_interval
                )
                
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_correlation_patterns(self, alerts: List[Alert]) -> List[AlertPatternMatch]:
        """Detect correlation patterns (related alerts)."""
        patterns = []
        
        if len(alerts) < 4:
            return patterns
        
        # Group alerts by time windows
        window_size = timedelta(minutes=10)
        windows = {}
        
        for alert in alerts:
            window_start = alert.created_at.replace(second=0, microsecond=0)
            window_start = window_start.replace(minute=(window_start.minute // 10) * 10)
            
            if window_start not in windows:
                windows[window_start] = []
            windows[window_start].append(alert)
        
        # Find correlated alert types within windows
        for window_start, window_alerts in windows.items():
            if len(window_alerts) < 3:
                continue
            
            # Group by alert characteristics
            by_category = defaultdict(list)
            by_source = defaultdict(list)
            
            for alert in window_alerts:
                by_category[alert.category].append(alert)
                by_source[alert.source].append(alert)
            
            # Check for strong correlations
            correlations = []
            
            # Category correlations
            if len(by_category) >= 2:
                categories = list(by_category.keys())
                for i in range(len(categories)):
                    for j in range(i+1, len(categories)):
                        cat1, cat2 = categories[i], categories[j]
                        correlation_strength = min(len(by_category[cat1]), len(by_category[cat2])) / max(len(by_category[cat1]), len(by_category[cat2]))
                        
                        if correlation_strength >= self.correlation_threshold:
                            correlations.append({
                                "type": "category",
                                "entities": [cat1.value, cat2.value],
                                "strength": correlation_strength
                            })
            
            # Source correlations
            if len(by_source) >= 2:
                sources = list(by_source.keys())
                for i in range(len(sources)):
                    for j in range(i+1, len(sources)):
                        src1, src2 = sources[i], sources[j]
                        correlation_strength = min(len(by_source[src1]), len(by_source[src2])) / max(len(by_source[src1]), len(by_source[src2]))
                        
                        if correlation_strength >= self.correlation_threshold:
                            correlations.append({
                                "type": "source",
                                "entities": [src1, src2],
                                "strength": correlation_strength
                            })
            
            # Create correlation patterns
            for correlation in correlations:
                pattern_id = f"correlation_{hashlib.md5(f'{window_start}_{correlation}'.encode()).hexdigest()[:8]}"
                
                pattern = AlertPatternMatch(
                    pattern_id=pattern_id,
                    pattern_type=AlertPattern.CORRELATION,
                    confidence=correlation["strength"],
                    alerts=[alert.id for alert in window_alerts],
                    time_window=(window_start, window_start + window_size),
                    characteristics={
                        "correlation_type": correlation["type"],
                        "correlated_entities": correlation["entities"],
                        "alert_count": len(window_alerts),
                        "time_window_minutes": 10
                    },
                    correlation_strength=correlation["strength"]
                )
                
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_storm_patterns(self, alerts: List[Alert], time_window_hours: int) -> List[AlertPatternMatch]:
        """Detect alert storm patterns (overwhelming number of alerts)."""
        patterns = []
        
        storm_threshold = 20  # alerts in short time period
        
        if len(alerts) < storm_threshold:
            return patterns
        
        # Group alerts by short time windows (1 minute)
        window_size = timedelta(minutes=1)
        windows = {}
        
        for alert in alerts:
            window_start = alert.created_at.replace(second=0, microsecond=0)
            
            if window_start not in windows:
                windows[window_start] = []
            windows[window_start].append(alert)
        
        # Find storm windows
        storm_windows = []
        for window_start, window_alerts in windows.items():
            if len(window_alerts) >= storm_threshold:
                storm_windows.append((window_start, window_alerts))
        
        # Merge adjacent storm windows
        if storm_windows:
            merged_storms = []
            current_storm = storm_windows[0]
            
            for i in range(1, len(storm_windows)):
                next_window_start, next_alerts = storm_windows[i]
                current_window_start, current_alerts = current_storm
                
                # If windows are adjacent (within 2 minutes), merge them
                if (next_window_start - current_window_start).total_seconds() <= 120:
                    current_storm = (current_window_start, current_alerts + next_alerts)
                else:
                    merged_storms.append(current_storm)
                    current_storm = storm_windows[i]
            
            merged_storms.append(current_storm)
            
            # Create storm patterns
            for storm_start, storm_alerts in merged_storms:
                pattern_id = f"storm_{hashlib.md5(f'{storm_start}'.encode()).hexdigest()[:8]}"
                
                storm_end = max(alert.created_at for alert in storm_alerts)
                storm_duration = (storm_end - storm_start).total_seconds() / 60  # minutes
                
                pattern = AlertPatternMatch(
                    pattern_id=pattern_id,
                    pattern_type=AlertPattern.STORM,
                    confidence=min(1.0, len(storm_alerts) / (storm_threshold * 3)),
                    alerts=[alert.id for alert in storm_alerts],
                    time_window=(storm_start, storm_end),
                    characteristics={
                        "alert_count": len(storm_alerts),
                        "duration_minutes": storm_duration,
                        "alert_rate_per_minute": len(storm_alerts) / max(1, storm_duration),
                        "unique_sources": len(set(alert.source for alert in storm_alerts)),
                        "severity_distribution": dict(Counter(alert.level.value for alert in storm_alerts))
                    }
                )
                
                patterns.append(pattern)
        
        return patterns
    
    def get_pattern_history(self, pattern_type: Optional[AlertPattern] = None, days: int = 7) -> List[Dict[str, Any]]:
        """Get pattern detection history."""
        cutoff = datetime.now() - timedelta(days=days)
        patterns = [p for p in self.pattern_history if p.created_at >= cutoff]
        
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        
        return [pattern.to_dict() for pattern in patterns]


class RootCauseAnalyzer:
    """
    Root cause analysis engine.
    
    Analyzes alert patterns and context to identify likely root causes.
    """
    
    def __init__(self):
        self.analysis_history: List[RootCauseAnalysis] = []
        
        # Root cause rules and heuristics
        self.cause_rules = self._initialize_cause_rules()
    
    def _initialize_cause_rules(self) -> List[Dict[str, Any]]:
        """Initialize root cause analysis rules."""
        return [
            {
                "name": "Infrastructure Cascade",
                "category": RootCauseCategory.INFRASTRUCTURE,
                "conditions": {
                    "pattern_types": [AlertPattern.CASCADE],
                    "sources": ["system", "network", "storage"],
                    "escalation_time": 300  # 5 minutes
                },
                "confidence_base": 0.8,
                "description": "Infrastructure component failure causing cascading alerts"
            },
            {
                "name": "Capacity Burst",
                "category": RootCauseCategory.CAPACITY,
                "conditions": {
                    "pattern_types": [AlertPattern.BURST, AlertPattern.STORM],
                    "metrics": ["cpu", "memory", "disk", "network"],
                    "threshold_exceeded": True
                },
                "confidence_base": 0.7,
                "description": "Resource capacity exceeded causing performance degradation"
            },
            {
                "name": "Application Bug",
                "category": RootCauseCategory.APPLICATION,
                "conditions": {
                    "pattern_types": [AlertPattern.PERIODIC],
                    "sources": ["application", "service"],
                    "error_patterns": ["exception", "timeout", "failure"]
                },
                "confidence_base": 0.6,
                "description": "Application bug causing recurring issues"
            },
            {
                "name": "Configuration Change",
                "category": RootCauseCategory.CONFIGURATION,
                "conditions": {
                    "pattern_types": [AlertPattern.BURST],
                    "time_correlation": "deployment",
                    "affected_components": "multiple"
                },
                "confidence_base": 0.75,
                "description": "Configuration change causing system instability"
            },
            {
                "name": "External Dependency",
                "category": RootCauseCategory.EXTERNAL,
                "conditions": {
                    "pattern_types": [AlertPattern.CORRELATION],
                    "sources": ["external", "api", "database"],
                    "correlation_strength": 0.7
                },
                "confidence_base": 0.65,
                "description": "External service dependency failure"
            }
        ]
    
    async def analyze_root_cause(
        self,
        alerts: List[Alert],
        patterns: List[AlertPatternMatch],
        context: Optional[Dict[str, Any]] = None
    ) -> List[RootCauseAnalysis]:
        """Analyze root cause for alerts and patterns."""
        analyses = []
        
        if not alerts and not patterns:
            return analyses
        
        # Analyze each rule against the evidence
        for rule in self.cause_rules:
            analysis = await self._evaluate_cause_rule(rule, alerts, patterns, context or {})
            if analysis:
                analyses.append(analysis)
        
        # Sort by confidence
        analyses.sort(key=lambda a: a.confidence, reverse=True)
        
        # Store in history
        self.analysis_history.extend(analyses)
        
        # Keep only recent analyses
        cutoff = datetime.now() - timedelta(days=30)
        self.analysis_history = [a for a in self.analysis_history if a.created_at >= cutoff]
        
        return analyses
    
    async def _evaluate_cause_rule(
        self,
        rule: Dict[str, Any],
        alerts: List[Alert],
        patterns: List[AlertPatternMatch],
        context: Dict[str, Any]
    ) -> Optional[RootCauseAnalysis]:
        """Evaluate a single root cause rule."""
        conditions = rule["conditions"]
        evidence = []
        confidence_factors = []
        
        # Check pattern type conditions
        if "pattern_types" in conditions:
            required_patterns = conditions["pattern_types"]
            matching_patterns = [p for p in patterns if p.pattern_type in required_patterns]
            
            if matching_patterns:
                evidence.append({
                    "type": "pattern_match",
                    "description": f"Found {len(matching_patterns)} matching patterns: {[p.pattern_type.value for p in matching_patterns]}",
                    "patterns": [p.pattern_id for p in matching_patterns]
                })
                confidence_factors.append(0.3)
            else:
                return None  # Required patterns not found
        
        # Check source conditions
        if "sources" in conditions:
            required_sources = conditions["sources"]
            alert_sources = set(alert.source for alert in alerts)
            matching_sources = [s for s in required_sources if any(s in source for source in alert_sources)]
            
            if matching_sources:
                evidence.append({
                    "type": "source_match",
                    "description": f"Alerts from relevant sources: {matching_sources}",
                    "sources": matching_sources
                })
                confidence_factors.append(0.2)
        
        # Check metric conditions
        if "metrics" in conditions:
            required_metrics = conditions["metrics"]
            alert_metrics = set(alert.metric_name for alert in alerts if alert.metric_name)
            matching_metrics = [m for m in required_metrics if any(m in metric for metric in alert_metrics)]
            
            if matching_metrics:
                evidence.append({
                    "type": "metric_match",
                    "description": f"Relevant metrics involved: {matching_metrics}",
                    "metrics": matching_metrics
                })
                confidence_factors.append(0.2)
        
        # Check escalation time conditions
        if "escalation_time" in conditions and patterns:
            max_escalation_time = conditions["escalation_time"]
            cascade_patterns = [p for p in patterns if p.pattern_type == AlertPattern.CASCADE]
            
            for pattern in cascade_patterns:
                duration = (pattern.time_window[1] - pattern.time_window[0]).total_seconds()
                if duration <= max_escalation_time:
                    evidence.append({
                        "type": "escalation_timing",
                        "description": f"Rapid escalation within {duration:.0f} seconds",
                        "duration_seconds": duration
                    })
                    confidence_factors.append(0.15)
        
        # Check correlation strength
        if "correlation_strength" in conditions and patterns:
            min_correlation = conditions["correlation_strength"]
            correlation_patterns = [p for p in patterns if p.pattern_type == AlertPattern.CORRELATION]
            
            for pattern in correlation_patterns:
                if pattern.correlation_strength and pattern.correlation_strength >= min_correlation:
                    evidence.append({
                        "type": "correlation_strength",
                        "description": f"Strong correlation detected: {pattern.correlation_strength:.2f}",
                        "correlation_strength": pattern.correlation_strength
                    })
                    confidence_factors.append(0.25)
        
        # Check context conditions
        if "time_correlation" in conditions:
            correlation_type = conditions["time_correlation"]
            if correlation_type in context:
                evidence.append({
                    "type": "context_correlation",
                    "description": f"Temporal correlation with {correlation_type}",
                    "context_data": context[correlation_type]
                })
                confidence_factors.append(0.2)
        
        # Calculate overall confidence
        if not evidence:
            return None
        
        base_confidence = rule["confidence_base"]
        evidence_boost = sum(confidence_factors)
        final_confidence = min(1.0, base_confidence + evidence_boost)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(rule["category"], evidence, context)
        
        # Create analysis
        analysis_id = f"rca_{uuid4().hex[:8]}"
        alert_ids = [alert.id for alert in alerts]
        
        analysis = RootCauseAnalysis(
            analysis_id=analysis_id,
            alert_ids=alert_ids,
            root_cause_category=rule["category"],
            confidence=final_confidence,
            description=rule["description"],
            evidence=evidence,
            reasoning=self._generate_reasoning(rule, evidence),
            recommendations=recommendations,
            related_patterns=[p.pattern_id for p in patterns]
        )
        
        return analysis
    
    def _generate_reasoning(self, rule: Dict[str, Any], evidence: List[Dict[str, Any]]) -> str:
        """Generate reasoning explanation."""
        reasoning_parts = [
            f"Analysis based on rule: {rule['name']}",
            f"Root cause category: {rule['category'].value}",
            "",
            "Evidence supporting this analysis:"
        ]
        
        for i, ev in enumerate(evidence, 1):
            reasoning_parts.append(f"{i}. {ev['description']}")
        
        return "\n".join(reasoning_parts)
    
    def _generate_recommendations(
        self,
        category: RootCauseCategory,
        evidence: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on root cause category."""
        recommendations = []
        
        if category == RootCauseCategory.INFRASTRUCTURE:
            recommendations.extend([
                "Check infrastructure component health and connectivity",
                "Review recent infrastructure changes or deployments",
                "Verify network connectivity and bandwidth",
                "Check hardware status and resource utilization"
            ])
        
        elif category == RootCauseCategory.CAPACITY:
            recommendations.extend([
                "Scale up resources (CPU, memory, storage) as needed",
                "Implement auto-scaling policies",
                "Review capacity planning and forecasting",
                "Optimize resource-intensive operations"
            ])
        
        elif category == RootCauseCategory.APPLICATION:
            recommendations.extend([
                "Review application logs for errors and exceptions",
                "Check recent code deployments and changes",
                "Analyze application performance metrics",
                "Consider rolling back recent changes if applicable"
            ])
        
        elif category == RootCauseCategory.CONFIGURATION:
            recommendations.extend([
                "Review recent configuration changes",
                "Validate configuration files and settings",
                "Check environment-specific configurations",
                "Consider reverting to last known good configuration"
            ])
        
        elif category == RootCauseCategory.EXTERNAL:
            recommendations.extend([
                "Check external service status and availability",
                "Review API rate limits and quotas",
                "Verify network connectivity to external services",
                "Implement circuit breakers and fallback mechanisms"
            ])
        
        elif category == RootCauseCategory.SECURITY:
            recommendations.extend([
                "Review security logs and access patterns",
                "Check for unauthorized access attempts",
                "Verify SSL/TLS certificate validity",
                "Review firewall and security group configurations"
            ])
        
        return recommendations
    
    def get_analysis_history(self, category: Optional[RootCauseCategory] = None, days: int = 30) -> List[Dict[str, Any]]:
        """Get root cause analysis history."""
        cutoff = datetime.now() - timedelta(days=days)
        analyses = [a for a in self.analysis_history if a.created_at >= cutoff]
        
        if category:
            analyses = [a for a in analyses if a.root_cause_category == category]
        
        return [analysis.to_dict() for analysis in analyses]


class AlertPredictor:
    """
    Alert prediction engine using historical patterns and trends.
    """
    
    def __init__(self):
        self.prediction_history: List[AlertPrediction] = []
        self.historical_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Prediction models (simplified)
        self.trend_model = self._initialize_trend_model()
        self.pattern_model = self._initialize_pattern_model()
    
    def _initialize_trend_model(self) -> Dict[str, Any]:
        """Initialize trend-based prediction model."""
        return {
            "name": "trend_predictor",
            "version": "1.0",
            "parameters": {
                "trend_window": 24,  # hours
                "prediction_horizon": 4,  # hours
                "confidence_threshold": 0.6
            }
        }
    
    def _initialize_pattern_model(self) -> Dict[str, Any]:
        """Initialize pattern-based prediction model."""
        return {
            "name": "pattern_predictor",
            "version": "1.0",
            "parameters": {
                "pattern_history_days": 30,
                "similarity_threshold": 0.7,
                "recurrence_threshold": 3
            }
        }
    
    async def predict_alerts(
        self,
        current_metrics: Dict[str, Any],
        recent_alerts: List[Alert],
        patterns: List[AlertPatternMatch],
        prediction_horizon_hours: int = 4
    ) -> List[AlertPrediction]:
        """Predict potential future alerts."""
        predictions = []
        
        # Trend-based predictions
        trend_predictions = await self._predict_from_trends(
            current_metrics, recent_alerts, prediction_horizon_hours
        )
        predictions.extend(trend_predictions)
        
        # Pattern-based predictions
        pattern_predictions = await self._predict_from_patterns(
            patterns, recent_alerts, prediction_horizon_hours
        )
        predictions.extend(pattern_predictions)
        
        # Store predictions
        self.prediction_history.extend(predictions)
        
        # Keep only recent predictions
        cutoff = datetime.now() - timedelta(days=7)
        self.prediction_history = [p for p in self.prediction_history if p.created_at >= cutoff]
        
        return predictions
    
    async def _predict_from_trends(
        self,
        current_metrics: Dict[str, Any],
        recent_alerts: List[Alert],
        horizon_hours: int
    ) -> List[AlertPrediction]:
        """Predict alerts based on metric trends."""
        predictions = []
        
        # Analyze metric trends
        for metric_name, current_value in current_metrics.items():
            if not isinstance(current_value, (int, float)):
                continue
            
            # Find related historical alerts
            related_alerts = [
                alert for alert in recent_alerts
                if alert.metric_name == metric_name and alert.metric_value is not None
            ]
            
            if len(related_alerts) < 3:
                continue
            
            # Calculate trend
            values = [alert.metric_value for alert in related_alerts[-10:]]  # Last 10 values
            if len(values) < 3:
                continue
            
            # Simple linear trend calculation
            x = list(range(len(values)))
            y = values
            
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            if n * sum_x2 - sum_x ** 2 == 0:
                continue
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            intercept = (sum_y - slope * sum_x) / n
            
            # Predict future value
            future_steps = horizon_hours  # Assuming hourly data points
            predicted_value = slope * (len(values) + future_steps) + intercept
            
            # Check if predicted value would trigger alerts
            threshold_alerts = [
                alert for alert in related_alerts
                if alert.threshold_value is not None
            ]
            
            if threshold_alerts:
                avg_threshold = statistics.mean([alert.threshold_value for alert in threshold_alerts])
                
                # Predict alert if trend suggests threshold breach
                if ((slope > 0 and predicted_value > avg_threshold) or
                    (slope < 0 and predicted_value < avg_threshold)):
                    
                    # Determine confidence based on trend strength
                    trend_strength = abs(slope) / (statistics.stdev(values) if len(values) > 1 else 1)
                    confidence_score = min(1.0, trend_strength)
                    
                    if confidence_score >= self.trend_model["parameters"]["confidence_threshold"]:
                        prediction_id = f"trend_{uuid4().hex[:8]}"
                        
                        # Determine alert level based on severity of breach
                        breach_severity = abs(predicted_value - avg_threshold) / avg_threshold
                        if breach_severity > 0.5:
                            predicted_level = AlertLevel.CRITICAL
                        elif breach_severity > 0.3:
                            predicted_level = AlertLevel.HIGH
                        elif breach_severity > 0.1:
                            predicted_level = AlertLevel.WARNING
                        else:
                            predicted_level = AlertLevel.INFO
                        
                        # Determine confidence level
                        if confidence_score >= 0.9:
                            confidence = PredictionConfidence.VERY_HIGH
                        elif confidence_score >= 0.8:
                            confidence = PredictionConfidence.HIGH
                        elif confidence_score >= 0.7:
                            confidence = PredictionConfidence.MEDIUM
                        else:
                            confidence = PredictionConfidence.LOW
                        
                        now = datetime.now()
                        prediction_time = now + timedelta(hours=horizon_hours)
                        
                        prediction = AlertPrediction(
                            prediction_id=prediction_id,
                            predicted_alert_type=f"threshold_breach_{metric_name}",
                            predicted_level=predicted_level,
                            predicted_category=AlertCategory.PERFORMANCE,  # Default category
                            confidence=confidence,
                            probability=confidence_score,
                            time_window=(now, prediction_time),
                            triggering_conditions={
                                "metric_name": metric_name,
                                "current_value": current_value,
                                "predicted_value": predicted_value,
                                "threshold": avg_threshold,
                                "trend_slope": slope
                            },
                            prevention_actions=[
                                f"Monitor {metric_name} closely",
                                "Consider scaling resources proactively",
                                "Review system capacity and performance",
                                "Implement preventive measures before threshold breach"
                            ],
                            model_name=self.trend_model["name"],
                            model_version=self.trend_model["version"]
                        )
                        
                        predictions.append(prediction)
        
        return predictions
    
    async def _predict_from_patterns(
        self,
        current_patterns: List[AlertPatternMatch],
        recent_alerts: List[Alert],
        horizon_hours: int
    ) -> List[AlertPrediction]:
        """Predict alerts based on historical patterns."""
        predictions = []
        
        # Analyze periodic patterns for recurrence prediction
        periodic_patterns = [p for p in current_patterns if p.pattern_type == AlertPattern.PERIODIC]
        
        for pattern in periodic_patterns:
            if pattern.period_hours and pattern.period_hours > 0:
                # Calculate when next occurrence is expected
                last_occurrence = pattern.time_window[1]
                next_occurrence = last_occurrence + timedelta(hours=pattern.period_hours)
                
                # Check if next occurrence is within prediction horizon
                now = datetime.now()
                time_to_next = (next_occurrence - now).total_seconds() / 3600  # hours
                
                if 0 < time_to_next <= horizon_hours:
                    prediction_id = f"pattern_{uuid4().hex[:8]}"
                    
                    # Get typical alert characteristics from pattern
                    pattern_alerts = [alert for alert in recent_alerts if alert.id in pattern.alerts]
                    if pattern_alerts:
                        typical_level = Counter([alert.level for alert in pattern_alerts]).most_common(1)[0][0]
                        typical_category = Counter([alert.category for alert in pattern_alerts]).most_common(1)[0][0]
                    else:
                        typical_level = AlertLevel.WARNING
                        typical_category = AlertCategory.SYSTEM
                    
                    # Confidence based on pattern regularity
                    regularity_score = pattern.characteristics.get("regularity_score", 0.5)
                    
                    if regularity_score >= 0.8:
                        confidence = PredictionConfidence.HIGH
                    elif regularity_score >= 0.6:
                        confidence = PredictionConfidence.MEDIUM
                    else:
                        confidence = PredictionConfidence.LOW
                    
                    prediction = AlertPrediction(
                        prediction_id=prediction_id,
                        predicted_alert_type=f"periodic_recurrence_{pattern.pattern_id}",
                        predicted_level=typical_level,
                        predicted_category=typical_category,
                        confidence=confidence,
                        probability=regularity_score,
                        time_window=(next_occurrence - timedelta(minutes=30), next_occurrence + timedelta(minutes=30)),
                        triggering_conditions={
                            "pattern_type": pattern.pattern_type.value,
                            "pattern_id": pattern.pattern_id,
                            "period_hours": pattern.period_hours,
                            "last_occurrence": last_occurrence.isoformat(),
                            "expected_occurrence": next_occurrence.isoformat()
                        },
                        prevention_actions=[
                            "Prepare for expected periodic issue",
                            "Review and address root cause of recurring pattern",
                            "Implement preventive measures before expected occurrence",
                            "Monitor system closely around predicted time"
                        ],
                        model_name=self.pattern_model["name"],
                        model_version=self.pattern_model["version"]
                    )
                    
                    predictions.append(prediction)
        
        return predictions
    
    def get_prediction_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get prediction history."""
        cutoff = datetime.now() - timedelta(days=days)
        predictions = [p for p in self.prediction_history if p.created_at >= cutoff]
        
        return [prediction.to_dict() for prediction in predictions]
    
    def get_prediction_accuracy(self, days: int = 7) -> Dict[str, Any]:
        """Calculate prediction accuracy metrics."""
        cutoff = datetime.now() - timedelta(days=days)
        predictions = [p for p in self.prediction_history if p.created_at >= cutoff]
        
        if not predictions:
            return {
                "total_predictions": 0,
                "accuracy_rate": 0.0,
                "by_confidence": {},
                "by_model": {}
            }
        
        # For demonstration, we'll simulate accuracy calculation
        # In production, this would compare predictions with actual alerts
        
        total_predictions = len(predictions)
        
        # Simulate accuracy based on confidence levels
        accuracy_by_confidence = {}
        for prediction in predictions:
            confidence = prediction.confidence.value
            if confidence not in accuracy_by_confidence:
                accuracy_by_confidence[confidence] = {"correct": 0, "total": 0}
            
            accuracy_by_confidence[confidence]["total"] += 1
            
            # Simulate accuracy (higher confidence = higher accuracy)
            if confidence == "very_high":
                accuracy_by_confidence[confidence]["correct"] += 1 if prediction.probability > 0.9 else 0
            elif confidence == "high":
                accuracy_by_confidence[confidence]["correct"] += 1 if prediction.probability > 0.8 else 0
            elif confidence == "medium":
                accuracy_by_confidence[confidence]["correct"] += 1 if prediction.probability > 0.6 else 0
            else:
                accuracy_by_confidence[confidence]["correct"] += 1 if prediction.probability > 0.4 else 0
        
        # Calculate overall accuracy
        total_correct = sum(data["correct"] for data in accuracy_by_confidence.values())
        overall_accuracy = (total_correct / total_predictions) * 100 if total_predictions > 0 else 0
        
        return {
            "total_predictions": total_predictions,
            "accuracy_rate": round(overall_accuracy, 2),
            "by_confidence": {
                conf: {
                    "accuracy": round((data["correct"] / data["total"]) * 100, 2) if data["total"] > 0 else 0,
                    "count": data["total"]
                }
                for conf, data in accuracy_by_confidence.items()
            },
            "evaluation_period_days": days,
            "generated_at": datetime.now().isoformat()
        }


class IntelligentAlertAnalysisSystem:
    """
    Comprehensive intelligent alert analysis system.
    
    Combines pattern recognition, root cause analysis, and prediction capabilities.
    """
    
    def __init__(self):
        self.pattern_recognizer = AlertPatternRecognizer()
        self.root_cause_analyzer = RootCauseAnalyzer()
        self.alert_predictor = AlertPredictor()
        
        # Analysis statistics
        self.analysis_stats = {
            "total_analyses": 0,
            "patterns_detected": 0,
            "root_causes_identified": 0,
            "predictions_made": 0
        }
    
    async def analyze_alerts(
        self,
        alerts: List[Alert],
        current_metrics: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        prediction_horizon_hours: int = 4
    ) -> Dict[str, Any]:
        """Perform comprehensive alert analysis."""
        self.analysis_stats["total_analyses"] += 1
        
        # 1. Pattern Recognition
        patterns = await self.pattern_recognizer.analyze_alerts(alerts)
        self.analysis_stats["patterns_detected"] += len(patterns)
        
        # 2. Root Cause Analysis
        root_causes = await self.root_cause_analyzer.analyze_root_cause(
            alerts, patterns, context
        )
        self.analysis_stats["root_causes_identified"] += len(root_causes)
        
        # 3. Alert Prediction
        predictions = []
        if current_metrics:
            predictions = await self.alert_predictor.predict_alerts(
                current_metrics, alerts, patterns, prediction_horizon_hours
            )
            self.analysis_stats["predictions_made"] += len(predictions)
        
        # 4. Generate insights and recommendations
        insights = self._generate_insights(alerts, patterns, root_causes, predictions)
        
        return {
            "analysis_summary": {
                "total_alerts": len(alerts),
                "patterns_detected": len(patterns),
                "root_causes_identified": len(root_causes),
                "predictions_made": len(predictions),
                "analysis_timestamp": datetime.now().isoformat()
            },
            "patterns": [pattern.to_dict() for pattern in patterns],
            "root_causes": [rca.to_dict() for rca in root_causes],
            "predictions": [pred.to_dict() for pred in predictions],
            "insights": insights,
            "recommendations": self._generate_recommendations(patterns, root_causes, predictions)
        }
    
    def _generate_insights(
        self,
        alerts: List[Alert],
        patterns: List[AlertPatternMatch],
        root_causes: List[RootCauseAnalysis],
        predictions: List[AlertPrediction]
    ) -> List[Dict[str, Any]]:
        """Generate analytical insights."""
        insights = []
        
        # Alert volume insights
        if len(alerts) > 10:
            insights.append({
                "type": "volume",
                "severity": "high",
                "message": f"High alert volume detected: {len(alerts)} alerts",
                "recommendation": "Consider implementing alert aggregation or reviewing alert thresholds"
            })
        
        # Pattern insights
        if patterns:
            pattern_types = [p.pattern_type.value for p in patterns]
            most_common_pattern = Counter(pattern_types).most_common(1)[0]
            
            insights.append({
                "type": "pattern",
                "severity": "medium",
                "message": f"Dominant pattern detected: {most_common_pattern[0]} ({most_common_pattern[1]} occurrences)",
                "recommendation": f"Focus on addressing {most_common_pattern[0]} pattern root causes"
            })
        
        # Root cause insights
        if root_causes:
            high_confidence_causes = [rca for rca in root_causes if rca.confidence > 0.8]
            if high_confidence_causes:
                insights.append({
                    "type": "root_cause",
                    "severity": "high",
                    "message": f"High-confidence root cause identified: {high_confidence_causes[0].root_cause_category.value}",
                    "recommendation": "Prioritize addressing this root cause to prevent future alerts"
                })
        
        # Prediction insights
        if predictions:
            high_risk_predictions = [p for p in predictions if p.confidence in [PredictionConfidence.HIGH, PredictionConfidence.VERY_HIGH]]
            if high_risk_predictions:
                insights.append({
                    "type": "prediction",
                    "severity": "warning",
                    "message": f"{len(high_risk_predictions)} high-confidence alert predictions",
                    "recommendation": "Take preventive action to avoid predicted alerts"
                })
        
        return insights
    
    def _generate_recommendations(
        self,
        patterns: List[AlertPatternMatch],
        root_causes: List[RootCauseAnalysis],
        predictions: List[AlertPrediction]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Pattern-based recommendations
        for pattern in patterns:
            if pattern.pattern_type == AlertPattern.STORM:
                recommendations.append("Implement alert rate limiting to prevent alert storms")
            elif pattern.pattern_type == AlertPattern.CASCADE:
                recommendations.append("Review service dependencies and implement circuit breakers")
            elif pattern.pattern_type == AlertPattern.PERIODIC:
                recommendations.append("Investigate and fix recurring issues to eliminate periodic alerts")
        
        # Root cause recommendations
        for rca in root_causes:
            recommendations.extend(rca.recommendations[:2])  # Top 2 recommendations
        
        # Prediction-based recommendations
        for prediction in predictions:
            if prediction.confidence in [PredictionConfidence.HIGH, PredictionConfidence.VERY_HIGH]:
                recommendations.extend(prediction.prevention_actions[:1])  # Top prevention action
        
        # Remove duplicates and limit
        unique_recommendations = list(dict.fromkeys(recommendations))
        return unique_recommendations[:10]  # Top 10 recommendations
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get analysis system statistics."""
        return {
            **self.analysis_stats,
            "pattern_history_count": len(self.pattern_recognizer.pattern_history),
            "root_cause_history_count": len(self.root_cause_analyzer.analysis_history),
            "prediction_history_count": len(self.alert_predictor.prediction_history),
            "generated_at": datetime.now().isoformat()
        }


# Global instance
intelligent_alert_analysis_system = IntelligentAlertAnalysisSystem()