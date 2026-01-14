"""
AI Annotation Schemas for SuperInsight platform.

Defines Pydantic models for AI annotation, pre-annotation, mid-coverage,
post-validation, plugin management, and review flow.
"""

from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# Enums
# ============================================================================

class AnnotationType(str, Enum):
    """Supported annotation types."""
    TEXT_CLASSIFICATION = "text_classification"
    NER = "ner"
    SENTIMENT = "sentiment"
    RELATION_EXTRACTION = "relation_extraction"
    SEQUENCE_LABELING = "sequence_labeling"
    QA = "qa"
    SUMMARIZATION = "summarization"


class AnnotationMethod(str, Enum):
    """Supported annotation methods."""
    CUSTOM_LLM = "custom_llm"
    ML_BACKEND = "ml_backend"
    ARGILLA = "argilla"
    THIRD_PARTY = "third_party"


class ConnectionType(str, Enum):
    """Third-party tool connection types."""
    REST_API = "rest_api"
    GRPC = "grpc"
    WEBHOOK = "webhook"


class ReviewStatus(str, Enum):
    """Review task status."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFICATION_REQUESTED = "modification_requested"


class ReviewAction(str, Enum):
    """Review actions."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


class UserRole(str, Enum):
    """User roles for collaboration."""
    ANNOTATOR = "annotator"
    EXPERT = "expert"
    CONTRACTOR = "contractor"
    REVIEWER = "reviewer"


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


# ============================================================================
# Pre-Annotation Schemas
# ============================================================================

class AnnotationTask(BaseModel):
    """Annotation task input."""
    id: str = Field(..., description="Task ID")
    data: Dict[str, Any] = Field(..., description="Task data to annotate")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Task metadata")


class AnnotatedSample(BaseModel):
    """Annotated sample for learning."""
    id: str = Field(..., description="Sample ID")
    data: Dict[str, Any] = Field(..., description="Sample data")
    annotation: Dict[str, Any] = Field(..., description="Sample annotation")
    annotation_type: AnnotationType = Field(..., description="Annotation type")


class PreAnnotationConfig(BaseModel):
    """Configuration for pre-annotation."""
    annotation_type: AnnotationType = Field(..., description="Type of annotation")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Confidence threshold")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Batch size")
    max_items: int = Field(default=1000, ge=1, le=1000, description="Maximum items to process")
    use_samples: bool = Field(default=False, description="Use sample learning")
    method: Optional[AnnotationMethod] = Field(default=None, description="Override method")
    model: Optional[str] = Field(default=None, description="Override model")


class PreAnnotationResult(BaseModel):
    """Result of pre-annotation for a single task."""
    task_id: str = Field(..., description="Task ID")
    annotation: Dict[str, Any] = Field(..., description="Annotation result")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    needs_review: bool = Field(default=False, description="Needs human review")
    method_used: str = Field(..., description="Method used for annotation")
    processing_time_ms: float = Field(default=0.0, ge=0.0, description="Processing time in ms")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class PreAnnotationBatchResult(BaseModel):
    """Result of batch pre-annotation."""
    job_id: str = Field(default_factory=lambda: str(uuid4()), description="Job ID")
    total_tasks: int = Field(..., description="Total tasks processed")
    successful: int = Field(default=0, description="Successful annotations")
    failed: int = Field(default=0, description="Failed annotations")
    needs_review: int = Field(default=0, description="Tasks needing review")
    results: List[PreAnnotationResult] = Field(default_factory=list, description="Individual results")
    processing_time_ms: float = Field(default=0.0, description="Total processing time")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


# ============================================================================
# Mid-Coverage Schemas
# ============================================================================

class AnnotationPattern(BaseModel):
    """Pattern extracted from annotations."""
    pattern_id: str = Field(default_factory=lambda: str(uuid4()), description="Pattern ID")
    source_annotations: List[str] = Field(..., description="Source annotation IDs")
    pattern_features: Dict[str, Any] = Field(..., description="Pattern features")
    annotation_template: Dict[str, Any] = Field(..., description="Annotation template")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Pattern confidence")


class SimilarTaskMatch(BaseModel):
    """Match between pattern and task."""
    task_id: str = Field(..., description="Task ID")
    pattern_id: str = Field(..., description="Matched pattern ID")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    suggested_annotation: Dict[str, Any] = Field(..., description="Suggested annotation")


class CoverageConfig(BaseModel):
    """Configuration for mid-coverage."""
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0, description="Similarity threshold")
    max_coverage: int = Field(default=100, ge=1, description="Maximum tasks to cover")
    auto_apply: bool = Field(default=False, description="Auto-apply annotations")
    notify_annotator: bool = Field(default=True, description="Notify annotator for review")


class CoverageResult(BaseModel):
    """Result of auto-coverage for a single task."""
    task_id: str = Field(..., description="Task ID")
    source_sample_id: str = Field(..., description="Source sample ID")
    pattern_id: str = Field(..., description="Pattern ID used")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    annotation: Dict[str, Any] = Field(..., description="Applied annotation")
    auto_covered: bool = Field(default=True, description="Was auto-covered")
    reviewed: bool = Field(default=False, description="Has been reviewed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


class CoverageBatchResult(BaseModel):
    """Result of batch coverage."""
    total_matched: int = Field(..., description="Total matched tasks")
    covered_count: int = Field(default=0, description="Tasks covered")
    average_similarity: float = Field(default=0.0, description="Average similarity")
    results: List[CoverageResult] = Field(default_factory=list, description="Individual results")
    needs_review: bool = Field(default=True, description="Needs review")


# ============================================================================
# Post-Validation Schemas
# ============================================================================

class ValidationRule(BaseModel):
    """Custom validation rule."""
    name: str = Field(..., description="Rule name")
    description: str = Field(default="", description="Rule description")
    rule_type: str = Field(..., description="Rule type")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Rule parameters")
    enabled: bool = Field(default=True, description="Rule enabled")


class ValidationConfig(BaseModel):
    """Configuration for post-validation."""
    dimensions: List[str] = Field(
        default=["accuracy", "recall", "consistency", "completeness"],
        description="Validation dimensions"
    )
    use_ragas: bool = Field(default=True, description="Use Ragas framework")
    use_deepeval: bool = Field(default=True, description="Use DeepEval framework")
    custom_rules: List[ValidationRule] = Field(default_factory=list, description="Custom rules")
    sample_size: Optional[int] = Field(default=None, description="Sample size for validation")


class ValidationIssue(BaseModel):
    """Validation issue found."""
    issue_id: str = Field(default_factory=lambda: str(uuid4()), description="Issue ID")
    annotation_id: str = Field(..., description="Related annotation ID")
    dimension: str = Field(..., description="Validation dimension")
    severity: str = Field(default="warning", description="Issue severity")
    message: str = Field(..., description="Issue message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Issue details")


class ValidationReport(BaseModel):
    """Validation report."""
    report_id: str = Field(default_factory=lambda: str(uuid4()), description="Report ID")
    project_id: Optional[str] = Field(default=None, description="Project ID")
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall score")
    accuracy: float = Field(default=0.0, ge=0.0, le=1.0, description="Accuracy score")
    recall: float = Field(default=0.0, ge=0.0, le=1.0, description="Recall score")
    consistency: float = Field(default=0.0, ge=0.0, le=1.0, description="Consistency score")
    completeness: float = Field(default=0.0, ge=0.0, le=1.0, description="Completeness score")
    dimension_scores: Dict[str, float] = Field(default_factory=dict, description="All dimension scores")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Issues found")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    total_annotations: int = Field(default=0, description="Total annotations validated")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


# ============================================================================
# Plugin Management Schemas
# ============================================================================

class PluginInfo(BaseModel):
    """Plugin information."""
    name: str = Field(..., description="Plugin name")
    version: str = Field(default="1.0.0", description="Plugin version")
    description: str = Field(default="", description="Plugin description")
    connection_type: ConnectionType = Field(..., description="Connection type")
    supported_annotation_types: List[AnnotationType] = Field(
        default_factory=list, description="Supported annotation types"
    )
    config_schema: Dict[str, Any] = Field(default_factory=dict, description="Config schema")
    enabled: bool = Field(default=True, description="Plugin enabled")
    priority: int = Field(default=0, description="Plugin priority")


class PluginConfig(BaseModel):
    """Plugin configuration."""
    name: str = Field(..., description="Plugin name")
    connection_type: ConnectionType = Field(..., description="Connection type")
    endpoint: Optional[str] = Field(default=None, description="API endpoint")
    api_key: Optional[str] = Field(default=None, description="API key")
    timeout: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")
    enabled: bool = Field(default=True, description="Plugin enabled")
    priority: int = Field(default=0, description="Plugin priority")
    type_mapping: Dict[str, str] = Field(default_factory=dict, description="Type mapping")
    extra_config: Dict[str, Any] = Field(default_factory=dict, description="Extra config")


class PluginStatistics(BaseModel):
    """Plugin call statistics."""
    plugin_name: str = Field(..., description="Plugin name")
    total_calls: int = Field(default=0, description="Total calls")
    success_count: int = Field(default=0, description="Successful calls")
    failure_count: int = Field(default=0, description="Failed calls")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Success rate")
    avg_latency_ms: float = Field(default=0.0, ge=0.0, description="Average latency")
    total_cost: float = Field(default=0.0, ge=0.0, description="Total cost")
    last_call_at: Optional[datetime] = Field(default=None, description="Last call time")


class PluginCallLog(BaseModel):
    """Plugin call log entry."""
    log_id: str = Field(default_factory=lambda: str(uuid4()), description="Log ID")
    plugin_name: str = Field(..., description="Plugin name")
    task_count: int = Field(default=0, description="Tasks processed")
    success: bool = Field(default=True, description="Call successful")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Latency in ms")
    cost: float = Field(default=0.0, ge=0.0, description="Call cost")
    error_message: Optional[str] = Field(default=None, description="Error message")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


# ============================================================================
# Method Switcher Schemas
# ============================================================================

class MethodInfo(BaseModel):
    """Annotation method information."""
    method: AnnotationMethod = Field(..., description="Method identifier")
    name: str = Field(..., description="Method name")
    description: str = Field(default="", description="Method description")
    enabled: bool = Field(default=True, description="Method enabled")
    configured: bool = Field(default=False, description="Method configured")
    supported_types: List[AnnotationType] = Field(
        default_factory=list, description="Supported annotation types"
    )


class MethodStats(BaseModel):
    """Method statistics."""
    method: AnnotationMethod = Field(..., description="Method identifier")
    total_calls: int = Field(default=0, description="Total calls")
    success_count: int = Field(default=0, description="Successful calls")
    avg_latency_ms: float = Field(default=0.0, description="Average latency")
    avg_confidence: float = Field(default=0.0, description="Average confidence")


class MethodComparisonReport(BaseModel):
    """Method comparison report."""
    task_count: int = Field(..., description="Tasks compared")
    methods_compared: List[str] = Field(..., description="Methods compared")
    results: Dict[str, MethodStats] = Field(default_factory=dict, description="Results by method")
    recommendation: Optional[str] = Field(default=None, description="Recommended method")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


# ============================================================================
# Collaboration Schemas
# ============================================================================

class TaskAssignment(BaseModel):
    """Task assignment."""
    assignment_id: str = Field(default_factory=lambda: str(uuid4()), description="Assignment ID")
    task_id: str = Field(..., description="Task ID")
    user_id: str = Field(..., description="Assigned user ID")
    role: UserRole = Field(..., description="User role")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    assigned_at: datetime = Field(default_factory=datetime.utcnow, description="Assignment time")
    deadline: Optional[datetime] = Field(default=None, description="Task deadline")
    completed_at: Optional[datetime] = Field(default=None, description="Completion time")


class WorkloadStatistics(BaseModel):
    """User workload statistics."""
    user_id: str = Field(..., description="User ID")
    role: UserRole = Field(..., description="User role")
    total_assigned: int = Field(default=0, description="Total assigned tasks")
    completed: int = Field(default=0, description="Completed tasks")
    pending: int = Field(default=0, description="Pending tasks")
    avg_completion_time_minutes: float = Field(default=0.0, description="Avg completion time")
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Completion rate")


class TeamStatistics(BaseModel):
    """Team statistics."""
    project_id: str = Field(..., description="Project ID")
    total_members: int = Field(default=0, description="Total team members")
    total_tasks: int = Field(default=0, description="Total tasks")
    completed_tasks: int = Field(default=0, description="Completed tasks")
    pending_tasks: int = Field(default=0, description="Pending tasks")
    by_role: Dict[str, int] = Field(default_factory=dict, description="Tasks by role")
    member_stats: List[WorkloadStatistics] = Field(default_factory=list, description="Member stats")


# ============================================================================
# Review Flow Schemas
# ============================================================================

class ReviewTask(BaseModel):
    """Review task."""
    review_id: str = Field(default_factory=lambda: str(uuid4()), description="Review ID")
    annotation_id: str = Field(..., description="Annotation ID")
    task_id: str = Field(..., description="Original task ID")
    annotator_id: str = Field(..., description="Original annotator ID")
    reviewer_id: Optional[str] = Field(default=None, description="Assigned reviewer ID")
    status: ReviewStatus = Field(default=ReviewStatus.PENDING, description="Review status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update time")


class ReviewRecord(BaseModel):
    """Review record."""
    record_id: str = Field(default_factory=lambda: str(uuid4()), description="Record ID")
    review_id: str = Field(..., description="Review task ID")
    annotation_id: str = Field(..., description="Annotation ID")
    reviewer_id: str = Field(..., description="Reviewer ID")
    action: ReviewAction = Field(..., description="Review action")
    reason: Optional[str] = Field(default=None, description="Reason for action")
    modifications: Optional[Dict[str, Any]] = Field(default=None, description="Modifications made")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


class ReviewResult(BaseModel):
    """Review result."""
    review_id: str = Field(..., description="Review ID")
    annotation_id: str = Field(..., description="Annotation ID")
    status: ReviewStatus = Field(..., description="Final status")
    action: ReviewAction = Field(..., description="Action taken")
    reviewer_id: str = Field(..., description="Reviewer ID")
    reason: Optional[str] = Field(default=None, description="Reason")
    modifications: Optional[Dict[str, Any]] = Field(default=None, description="Modifications")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Process time")


class ReviewFlowConfig(BaseModel):
    """Review flow configuration."""
    project_id: str = Field(..., description="Project ID")
    review_levels: int = Field(default=1, ge=1, le=3, description="Number of review levels")
    auto_assign: bool = Field(default=True, description="Auto-assign reviewers")
    require_reason_on_reject: bool = Field(default=True, description="Require reason on reject")
    allow_batch_approve: bool = Field(default=True, description="Allow batch approval")


# ============================================================================
# API Request/Response Schemas
# ============================================================================

class PreAnnotateRequest(BaseModel):
    """Pre-annotation API request."""
    task_ids: List[str] = Field(..., min_length=1, max_length=1000, description="Task IDs")
    config: PreAnnotationConfig = Field(..., description="Pre-annotation config")
    samples: List[AnnotatedSample] = Field(default_factory=list, description="Learning samples")


class AutoCoverRequest(BaseModel):
    """Auto-cover API request."""
    annotated_sample_ids: List[str] = Field(..., min_length=1, description="Annotated sample IDs")
    unannotated_task_ids: List[str] = Field(..., min_length=1, description="Unannotated task IDs")
    config: CoverageConfig = Field(default_factory=CoverageConfig, description="Coverage config")


class ValidateRequest(BaseModel):
    """Validation API request."""
    annotation_ids: List[str] = Field(..., min_length=1, description="Annotation IDs to validate")
    config: ValidationConfig = Field(default_factory=ValidationConfig, description="Validation config")
    ground_truth_ids: List[str] = Field(default_factory=list, description="Ground truth annotation IDs")


class AssignTaskRequest(BaseModel):
    """Task assignment API request."""
    task_id: str = Field(..., description="Task ID")
    user_id: Optional[str] = Field(default=None, description="User ID to assign")
    role: Optional[UserRole] = Field(default=None, description="Role to assign")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    deadline: Optional[datetime] = Field(default=None, description="Task deadline")


class SubmitReviewRequest(BaseModel):
    """Submit review API request."""
    annotation_id: str = Field(..., description="Annotation ID")
    reviewer_id: Optional[str] = Field(default=None, description="Preferred reviewer ID")


class RejectReviewRequest(BaseModel):
    """Reject review API request."""
    reason: str = Field(..., min_length=1, description="Rejection reason")


class ModifyReviewRequest(BaseModel):
    """Modify review API request."""
    modifications: Dict[str, Any] = Field(..., description="Modifications to apply")
    comments: Optional[str] = Field(default=None, description="Review comments")


class BatchApproveRequest(BaseModel):
    """Batch approve API request."""
    review_ids: List[str] = Field(..., min_length=1, description="Review IDs to approve")


# ============================================================================
# Error Schemas
# ============================================================================

class AnnotationErrorCode(str, Enum):
    """Annotation error codes."""
    PRE_ANNOTATION_ERROR = "ANN_PRE_ANNOTATION_ERROR"
    PLUGIN_UNAVAILABLE = "ANN_PLUGIN_UNAVAILABLE"
    PLUGIN_NOT_FOUND = "ANN_PLUGIN_NOT_FOUND"
    VALIDATION_ERROR = "ANN_VALIDATION_ERROR"
    REVIEW_CONFLICT = "ANN_REVIEW_CONFLICT"
    ASSIGNMENT_ERROR = "ANN_ASSIGNMENT_ERROR"
    METHOD_UNAVAILABLE = "ANN_METHOD_UNAVAILABLE"
    INVALID_CONFIG = "ANN_INVALID_CONFIG"
    TASK_NOT_FOUND = "ANN_TASK_NOT_FOUND"
    PERMISSION_DENIED = "ANN_PERMISSION_DENIED"


class AnnotationError(BaseModel):
    """Annotation error."""
    error_code: AnnotationErrorCode = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
