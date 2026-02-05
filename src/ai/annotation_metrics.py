"""
AI Annotation Metrics Module

Provides Prometheus metrics for AI annotation operations:
- Pre-annotation batch processing metrics
- Real-time suggestion latency metrics
- Quality validation metrics
- Collaboration metrics
- Engine performance metrics
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from prometheus_client import Counter, Gauge, Histogram, Summary, Info

logger = logging.getLogger(__name__)


# =============================================================================
# Pre-Annotation Metrics
# =============================================================================

# Batch processing metrics
PRE_ANNOTATION_BATCHES_TOTAL = Counter(
    'ai_annotation_pre_annotation_batches_total',
    'Total number of pre-annotation batches processed',
    ['project_id', 'annotation_type', 'status']
)

PRE_ANNOTATION_DOCUMENTS_TOTAL = Counter(
    'ai_annotation_pre_annotation_documents_total',
    'Total number of documents pre-annotated',
    ['project_id', 'annotation_type', 'needs_review']
)

PRE_ANNOTATION_BATCH_SIZE = Histogram(
    'ai_annotation_pre_annotation_batch_size',
    'Size of pre-annotation batches',
    ['project_id'],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000]
)

PRE_ANNOTATION_PROCESSING_TIME = Histogram(
    'ai_annotation_pre_annotation_processing_seconds',
    'Time to process pre-annotation batch',
    ['project_id', 'annotation_type'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300]
)

PRE_ANNOTATION_CONFIDENCE = Histogram(
    'ai_annotation_pre_annotation_confidence',
    'Confidence scores of pre-annotations',
    ['project_id', 'annotation_type'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
)


# =============================================================================
# Real-Time Suggestion Metrics
# =============================================================================

SUGGESTION_REQUESTS_TOTAL = Counter(
    'ai_annotation_suggestion_requests_total',
    'Total number of suggestion requests',
    ['project_id', 'annotation_type', 'status']
)

SUGGESTION_LATENCY = Histogram(
    'ai_annotation_suggestion_latency_seconds',
    'Latency of suggestion generation',
    ['project_id', 'annotation_type'],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0]
)

SUGGESTION_FEEDBACK_TOTAL = Counter(
    'ai_annotation_suggestion_feedback_total',
    'Total number of suggestion feedbacks',
    ['project_id', 'accepted', 'modified']
)

SUGGESTION_ACCEPTANCE_RATE = Gauge(
    'ai_annotation_suggestion_acceptance_rate',
    'Current suggestion acceptance rate',
    ['project_id', 'annotation_type']
)


# =============================================================================
# Quality Validation Metrics
# =============================================================================

VALIDATION_RUNS_TOTAL = Counter(
    'ai_annotation_validation_runs_total',
    'Total number of validation runs',
    ['project_id', 'validation_type', 'status']
)

VALIDATION_PROCESSING_TIME = Histogram(
    'ai_annotation_validation_processing_seconds',
    'Time to process validation',
    ['project_id', 'validation_type'],
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600]
)

QUALITY_SCORE = Gauge(
    'ai_annotation_quality_score',
    'Current quality score',
    ['project_id', 'metric_type']
)

INCONSISTENCIES_DETECTED = Counter(
    'ai_annotation_inconsistencies_detected_total',
    'Total number of inconsistencies detected',
    ['project_id', 'inconsistency_type', 'severity']
)

QUALITY_ALERTS_TOTAL = Counter(
    'ai_annotation_quality_alerts_total',
    'Total number of quality alerts triggered',
    ['project_id', 'alert_type', 'severity']
)


# =============================================================================
# Collaboration Metrics
# =============================================================================

ACTIVE_COLLABORATORS = Gauge(
    'ai_annotation_active_collaborators',
    'Number of active collaborators',
    ['project_id', 'role']
)

WEBSOCKET_CONNECTIONS = Gauge(
    'ai_annotation_websocket_connections',
    'Number of active WebSocket connections',
    ['project_id']
)

WEBSOCKET_MESSAGES_TOTAL = Counter(
    'ai_annotation_websocket_messages_total',
    'Total number of WebSocket messages',
    ['project_id', 'message_type', 'direction']
)

CONFLICTS_TOTAL = Counter(
    'ai_annotation_conflicts_total',
    'Total number of annotation conflicts',
    ['project_id', 'conflict_type', 'status']
)

CONFLICT_RESOLUTION_TIME = Histogram(
    'ai_annotation_conflict_resolution_seconds',
    'Time to resolve conflicts',
    ['project_id', 'conflict_type'],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800]
)


# =============================================================================
# Task Management Metrics
# =============================================================================

TASKS_TOTAL = Gauge(
    'ai_annotation_tasks_total',
    'Total number of tasks',
    ['project_id', 'status']
)

TASK_ASSIGNMENTS_TOTAL = Counter(
    'ai_annotation_task_assignments_total',
    'Total number of task assignments',
    ['project_id', 'assigned_by', 'role']
)

TASK_COMPLETION_TIME = Histogram(
    'ai_annotation_task_completion_seconds',
    'Time to complete tasks',
    ['project_id', 'task_type'],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400]
)

ANNOTATIONS_SUBMITTED_TOTAL = Counter(
    'ai_annotation_annotations_submitted_total',
    'Total number of annotations submitted',
    ['project_id', 'annotation_type', 'source']
)


# =============================================================================
# Engine Performance Metrics
# =============================================================================

ENGINE_REQUESTS_TOTAL = Counter(
    'ai_annotation_engine_requests_total',
    'Total number of engine requests',
    ['engine_id', 'engine_type', 'status']
)

ENGINE_LATENCY = Histogram(
    'ai_annotation_engine_latency_seconds',
    'Engine request latency',
    ['engine_id', 'engine_type'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10]
)

ENGINE_ERRORS_TOTAL = Counter(
    'ai_annotation_engine_errors_total',
    'Total number of engine errors',
    ['engine_id', 'engine_type', 'error_type']
)

ENGINE_HEALTH_STATUS = Gauge(
    'ai_annotation_engine_health_status',
    'Engine health status (1=healthy, 0.5=degraded, 0=unhealthy)',
    ['engine_id', 'engine_type']
)

ENGINE_FALLBACK_TOTAL = Counter(
    'ai_annotation_engine_fallback_total',
    'Total number of engine fallbacks',
    ['primary_engine', 'fallback_engine', 'reason']
)


# =============================================================================
# Cache Metrics
# =============================================================================

CACHE_HITS_TOTAL = Counter(
    'ai_annotation_cache_hits_total',
    'Total number of cache hits',
    ['cache_type', 'operation']
)

CACHE_MISSES_TOTAL = Counter(
    'ai_annotation_cache_misses_total',
    'Total number of cache misses',
    ['cache_type', 'operation']
)

CACHE_SIZE = Gauge(
    'ai_annotation_cache_size_bytes',
    'Current cache size in bytes',
    ['cache_type']
)


# =============================================================================
# Metrics Helper Class
# =============================================================================

class AnnotationMetricsCollector:
    """Helper class for collecting annotation metrics."""
    
    def __init__(self, project_id: str = "default"):
        self.project_id = project_id
    
    # Pre-Annotation Metrics
    def record_pre_annotation_batch(
        self,
        annotation_type: str,
        batch_size: int,
        processing_time: float,
        status: str = "success"
    ):
        """Record pre-annotation batch metrics."""
        PRE_ANNOTATION_BATCHES_TOTAL.labels(
            project_id=self.project_id,
            annotation_type=annotation_type,
            status=status
        ).inc()
        
        PRE_ANNOTATION_BATCH_SIZE.labels(
            project_id=self.project_id
        ).observe(batch_size)
        
        PRE_ANNOTATION_PROCESSING_TIME.labels(
            project_id=self.project_id,
            annotation_type=annotation_type
        ).observe(processing_time)
    
    def record_pre_annotation_document(
        self,
        annotation_type: str,
        confidence: float,
        needs_review: bool
    ):
        """Record pre-annotation document metrics."""
        PRE_ANNOTATION_DOCUMENTS_TOTAL.labels(
            project_id=self.project_id,
            annotation_type=annotation_type,
            needs_review=str(needs_review).lower()
        ).inc()
        
        PRE_ANNOTATION_CONFIDENCE.labels(
            project_id=self.project_id,
            annotation_type=annotation_type
        ).observe(confidence)
    
    # Suggestion Metrics
    def record_suggestion_request(
        self,
        annotation_type: str,
        latency: float,
        status: str = "success"
    ):
        """Record suggestion request metrics."""
        SUGGESTION_REQUESTS_TOTAL.labels(
            project_id=self.project_id,
            annotation_type=annotation_type,
            status=status
        ).inc()
        
        SUGGESTION_LATENCY.labels(
            project_id=self.project_id,
            annotation_type=annotation_type
        ).observe(latency)
    
    def record_suggestion_feedback(
        self,
        accepted: bool,
        modified: bool = False
    ):
        """Record suggestion feedback metrics."""
        SUGGESTION_FEEDBACK_TOTAL.labels(
            project_id=self.project_id,
            accepted=str(accepted).lower(),
            modified=str(modified).lower()
        ).inc()
    
    def update_acceptance_rate(
        self,
        annotation_type: str,
        rate: float
    ):
        """Update suggestion acceptance rate."""
        SUGGESTION_ACCEPTANCE_RATE.labels(
            project_id=self.project_id,
            annotation_type=annotation_type
        ).set(rate)
    
    # Quality Metrics
    def record_validation_run(
        self,
        validation_type: str,
        processing_time: float,
        status: str = "success"
    ):
        """Record validation run metrics."""
        VALIDATION_RUNS_TOTAL.labels(
            project_id=self.project_id,
            validation_type=validation_type,
            status=status
        ).inc()
        
        VALIDATION_PROCESSING_TIME.labels(
            project_id=self.project_id,
            validation_type=validation_type
        ).observe(processing_time)
    
    def update_quality_score(
        self,
        metric_type: str,
        score: float
    ):
        """Update quality score."""
        QUALITY_SCORE.labels(
            project_id=self.project_id,
            metric_type=metric_type
        ).set(score)
    
    def record_inconsistency(
        self,
        inconsistency_type: str,
        severity: str
    ):
        """Record inconsistency detection."""
        INCONSISTENCIES_DETECTED.labels(
            project_id=self.project_id,
            inconsistency_type=inconsistency_type,
            severity=severity
        ).inc()
    
    def record_quality_alert(
        self,
        alert_type: str,
        severity: str
    ):
        """Record quality alert."""
        QUALITY_ALERTS_TOTAL.labels(
            project_id=self.project_id,
            alert_type=alert_type,
            severity=severity
        ).inc()
    
    # Collaboration Metrics
    def update_active_collaborators(
        self,
        role: str,
        count: int
    ):
        """Update active collaborators count."""
        ACTIVE_COLLABORATORS.labels(
            project_id=self.project_id,
            role=role
        ).set(count)
    
    def update_websocket_connections(
        self,
        count: int
    ):
        """Update WebSocket connections count."""
        WEBSOCKET_CONNECTIONS.labels(
            project_id=self.project_id
        ).set(count)
    
    def record_websocket_message(
        self,
        message_type: str,
        direction: str
    ):
        """Record WebSocket message."""
        WEBSOCKET_MESSAGES_TOTAL.labels(
            project_id=self.project_id,
            message_type=message_type,
            direction=direction
        ).inc()
    
    def record_conflict(
        self,
        conflict_type: str,
        status: str
    ):
        """Record annotation conflict."""
        CONFLICTS_TOTAL.labels(
            project_id=self.project_id,
            conflict_type=conflict_type,
            status=status
        ).inc()
    
    def record_conflict_resolution(
        self,
        conflict_type: str,
        resolution_time: float
    ):
        """Record conflict resolution time."""
        CONFLICT_RESOLUTION_TIME.labels(
            project_id=self.project_id,
            conflict_type=conflict_type
        ).observe(resolution_time)
    
    # Task Metrics
    def update_tasks_count(
        self,
        status: str,
        count: int
    ):
        """Update tasks count by status."""
        TASKS_TOTAL.labels(
            project_id=self.project_id,
            status=status
        ).set(count)
    
    def record_task_assignment(
        self,
        assigned_by: str,
        role: str
    ):
        """Record task assignment."""
        TASK_ASSIGNMENTS_TOTAL.labels(
            project_id=self.project_id,
            assigned_by=assigned_by,
            role=role
        ).inc()
    
    def record_task_completion(
        self,
        task_type: str,
        completion_time: float
    ):
        """Record task completion time."""
        TASK_COMPLETION_TIME.labels(
            project_id=self.project_id,
            task_type=task_type
        ).observe(completion_time)
    
    def record_annotation_submission(
        self,
        annotation_type: str,
        source: str
    ):
        """Record annotation submission."""
        ANNOTATIONS_SUBMITTED_TOTAL.labels(
            project_id=self.project_id,
            annotation_type=annotation_type,
            source=source
        ).inc()
    
    # Engine Metrics
    @staticmethod
    def record_engine_request(
        engine_id: str,
        engine_type: str,
        latency: float,
        status: str = "success"
    ):
        """Record engine request metrics."""
        ENGINE_REQUESTS_TOTAL.labels(
            engine_id=engine_id,
            engine_type=engine_type,
            status=status
        ).inc()
        
        ENGINE_LATENCY.labels(
            engine_id=engine_id,
            engine_type=engine_type
        ).observe(latency)
    
    @staticmethod
    def record_engine_error(
        engine_id: str,
        engine_type: str,
        error_type: str
    ):
        """Record engine error."""
        ENGINE_ERRORS_TOTAL.labels(
            engine_id=engine_id,
            engine_type=engine_type,
            error_type=error_type
        ).inc()
    
    @staticmethod
    def update_engine_health(
        engine_id: str,
        engine_type: str,
        status: str
    ):
        """Update engine health status."""
        status_value = {
            'healthy': 1.0,
            'degraded': 0.5,
            'unhealthy': 0.0
        }.get(status, 0.0)
        
        ENGINE_HEALTH_STATUS.labels(
            engine_id=engine_id,
            engine_type=engine_type
        ).set(status_value)
    
    @staticmethod
    def record_engine_fallback(
        primary_engine: str,
        fallback_engine: str,
        reason: str
    ):
        """Record engine fallback."""
        ENGINE_FALLBACK_TOTAL.labels(
            primary_engine=primary_engine,
            fallback_engine=fallback_engine,
            reason=reason
        ).inc()
    
    # Cache Metrics
    @staticmethod
    def record_cache_hit(
        cache_type: str,
        operation: str
    ):
        """Record cache hit."""
        CACHE_HITS_TOTAL.labels(
            cache_type=cache_type,
            operation=operation
        ).inc()
    
    @staticmethod
    def record_cache_miss(
        cache_type: str,
        operation: str
    ):
        """Record cache miss."""
        CACHE_MISSES_TOTAL.labels(
            cache_type=cache_type,
            operation=operation
        ).inc()
    
    @staticmethod
    def update_cache_size(
        cache_type: str,
        size_bytes: int
    ):
        """Update cache size."""
        CACHE_SIZE.labels(
            cache_type=cache_type
        ).set(size_bytes)


# Global metrics collector instance
_metrics_collector: Optional[AnnotationMetricsCollector] = None


def get_metrics_collector(project_id: str = "default") -> AnnotationMetricsCollector:
    """Get or create metrics collector for a project."""
    global _metrics_collector
    if _metrics_collector is None or _metrics_collector.project_id != project_id:
        _metrics_collector = AnnotationMetricsCollector(project_id)
    return _metrics_collector
