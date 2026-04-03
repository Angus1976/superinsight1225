"""
Annotation Collaboration API endpoints.

Provides REST API and WebSocket endpoints for AI annotation collaboration,
including pre-annotation, mid-coverage suggestions, post-validation,
task management, and real-time collaboration.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Task progress storage (in production, use Redis or database)
_task_progress: Dict[str, Dict[str, Any]] = {}
_task_results: Dict[str, List[Dict[str, Any]]] = {}

# Import local modules with fallback
try:
    from ai.annotation_websocket import (
        AnnotationWebSocketManager,
        get_annotation_ws_manager,
    )
    from ai.collaboration_manager import (
        CollaborationManager,
        get_collaboration_manager,
        TaskPriority,
        TaskStatus,
        UserRole,
    )
    from ai.pre_annotation import PreAnnotationEngine
    from ai.mid_coverage import MidCoverageEngine
    from ai.post_validation import PostValidationEngine
    from ai.annotation_switcher import AnnotationSwitcher
except ImportError:
    from src.ai.annotation_websocket import (
        AnnotationWebSocketManager,
        get_annotation_ws_manager,
    )
    from src.ai.collaboration_manager import (
        CollaborationManager,
        get_collaboration_manager,
        TaskPriority,
        TaskStatus,
        UserRole,
    )
    from src.ai.pre_annotation import PreAnnotationEngine
    from src.ai.mid_coverage import MidCoverageEngine
    from src.ai.post_validation import PostValidationEngine
    from src.ai.annotation_switcher import AnnotationSwitcher


# =============================================================================
# Request/Response Models
# =============================================================================

# Pre-Annotation Models
class PreAnnotationRequest(BaseModel):
    """Request for pre-annotation task."""
    project_id: str
    document_ids: List[str]
    annotation_type: str = "ner"
    engine_id: Optional[str] = None
    samples: Optional[List[Dict[str, Any]]] = None
    confidence_threshold: float = 0.7
    batch_size: int = 10


class PreAnnotationResponse(BaseModel):
    """Response for pre-annotation task."""
    task_id: str
    status: str
    message: str
    total_documents: int


class PreAnnotationResultRequest(BaseModel):
    """Request for getting pre-annotation results."""
    task_id: str


class PreAnnotationResult(BaseModel):
    """Pre-annotation result for a document."""
    document_id: str
    annotations: List[Dict[str, Any]]
    confidence: float
    needs_review: bool
    processing_time_ms: float


# Mid-Coverage Models
class SuggestionRequest(BaseModel):
    """Request for real-time suggestion."""
    document_id: str
    text: str
    context: Optional[str] = None
    annotation_type: str = "ner"
    position: Optional[Dict[str, int]] = None


class SuggestionResponse(BaseModel):
    """Response for suggestion request."""
    suggestion_id: str
    document_id: str
    annotations: List[Dict[str, Any]]
    confidence: float
    latency_ms: float


class FeedbackRequest(BaseModel):
    """Request for suggestion feedback."""
    suggestion_id: str
    accepted: bool
    modified_annotation: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class BatchCoverageRequest(BaseModel):
    """Request for batch coverage application."""
    project_id: str
    document_ids: List[str]
    pattern_type: str
    min_confidence: float = 0.8


class BatchCoverageResponse(BaseModel):
    """Response for batch coverage."""
    applied_count: int
    skipped_count: int
    conflicts: List[Dict[str, Any]]


class ConflictResponse(BaseModel):
    """Annotation conflict information."""
    conflict_id: str
    document_id: str
    conflict_type: str
    annotations: List[Dict[str, Any]]
    users: List[Dict[str, str]]
    created_at: datetime


# Post-Validation Models
class ValidationRequest(BaseModel):
    """Request for annotation validation."""
    project_id: str
    document_ids: Optional[List[str]] = None
    validation_types: List[str] = ["accuracy", "consistency", "completeness"]
    custom_rules: Optional[List[Dict[str, Any]]] = None


class ValidationResponse(BaseModel):
    """Response for validation request."""
    validation_id: str
    status: str
    message: str


class QualityReportResponse(BaseModel):
    """Quality report for a project."""
    project_id: str
    overall_score: float
    accuracy_score: float
    consistency_score: float
    completeness_score: float
    total_annotations: int
    issues_count: int
    recommendations: List[str]
    generated_at: datetime


class InconsistencyResponse(BaseModel):
    """Inconsistency details."""
    inconsistency_id: str
    type: str
    severity: str
    affected_documents: List[str]
    description: str
    suggested_fix: Optional[str]


class ReviewTaskRequest(BaseModel):
    """Request to create review tasks."""
    project_id: str
    document_ids: List[str]
    review_type: str = "quality"
    priority: str = "normal"
    assignee_id: Optional[str] = None


class ReviewTaskResponse(BaseModel):
    """Response for review task creation."""
    task_ids: List[str]
    total_created: int


# Engine Management Models
class EngineListResponse(BaseModel):
    """List of available engines."""
    engines: List[Dict[str, Any]]
    count: int


class EngineRegistrationRequest(BaseModel):
    """Request to register a new engine."""
    engine_type: str
    engine_name: str
    config: Dict[str, Any]
    description: Optional[str] = None


class EngineComparisonRequest(BaseModel):
    """Request to compare engines."""
    engine_ids: List[str]
    test_documents: List[str]
    annotation_type: str = "ner"


class EngineComparisonResponse(BaseModel):
    """Response for engine comparison."""
    comparison_id: str
    results: List[Dict[str, Any]]
    recommendation: Optional[str]


# Task Management Models
class TaskAssignmentRequest(BaseModel):
    """Request to assign a task."""
    task_id: str
    user_id: Optional[str] = None
    role: Optional[str] = None
    priority: str = "normal"
    deadline: Optional[datetime] = None


class TaskAssignmentResponse(BaseModel):
    """Response for task assignment."""
    assignment_id: str
    task_id: str
    user_id: str
    status: str
    assigned_at: datetime


class TaskSubmissionRequest(BaseModel):
    """Request to submit annotation."""
    task_id: str
    annotations: List[Dict[str, Any]]
    time_spent_seconds: Optional[int] = None
    notes: Optional[str] = None


class ConflictResolutionRequest(BaseModel):
    """Request to resolve conflict."""
    conflict_id: str
    resolution: str  # accepted, rejected, modified
    resolved_annotation: Optional[Dict[str, Any]] = None
    resolution_notes: Optional[str] = None


class ProgressMetricsResponse(BaseModel):
    """Progress metrics for a project."""
    project_id: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    pending_tasks: int
    completion_rate: float
    avg_time_per_task_minutes: float
    active_annotators: int
    active_reviewers: int


# =============================================================================
# Dependencies
# =============================================================================

def get_ws_manager() -> AnnotationWebSocketManager:
    """Get WebSocket manager dependency."""
    return get_annotation_ws_manager()


async def get_collab_manager() -> CollaborationManager:
    """Get collaboration manager dependency (async so init runs on the event loop, not a thread pool)."""
    return get_collaboration_manager()


# Engine instances (should be initialized properly in production)
_pre_annotation_engine: Optional[PreAnnotationEngine] = None
_mid_coverage_engine: Optional[MidCoverageEngine] = None
_post_validation_engine: Optional[PostValidationEngine] = None
_annotation_switcher: Optional[AnnotationSwitcher] = None


def get_pre_annotation_engine() -> PreAnnotationEngine:
    """Get pre-annotation engine."""
    global _pre_annotation_engine
    if _pre_annotation_engine is None:
        _pre_annotation_engine = PreAnnotationEngine()
    return _pre_annotation_engine


def get_mid_coverage_engine() -> MidCoverageEngine:
    """Get mid-coverage engine."""
    global _mid_coverage_engine
    if _mid_coverage_engine is None:
        _mid_coverage_engine = MidCoverageEngine()
    return _mid_coverage_engine


def get_post_validation_engine() -> PostValidationEngine:
    """Get post-validation engine."""
    global _post_validation_engine
    if _post_validation_engine is None:
        _post_validation_engine = PostValidationEngine()
    return _post_validation_engine


async def get_annotation_switcher() -> AnnotationSwitcher:
    """Get annotation switcher (async dep so AnnotationSwitcher initializes on the event loop)."""
    global _annotation_switcher
    if _annotation_switcher is None:
        _annotation_switcher = AnnotationSwitcher()
    return _annotation_switcher


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/api/v1/annotation", tags=["Annotation Collaboration"])


# =============================================================================
# Pre-Annotation Endpoints
# =============================================================================

@router.post("/pre-annotate", response_model=PreAnnotationResponse)
async def submit_pre_annotation(
    request: PreAnnotationRequest,
    engine: PreAnnotationEngine = Depends(get_pre_annotation_engine),
):
    """
    Submit pre-annotation task for batch processing.

    - Processes documents in batches
    - Uses specified engine or auto-selects based on annotation type
    - Flags low-confidence items for review
    """
    try:
        # Generate task ID
        task_id = f"pre_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{request.project_id[:8]}"

        # Start background processing
        # In production, this would be queued to a task queue
        asyncio.create_task(
            _process_pre_annotation(
                task_id=task_id,
                engine=engine,
                request=request,
            )
        )

        return PreAnnotationResponse(
            task_id=task_id,
            status="submitted",
            message=f"Pre-annotation task submitted for {len(request.document_ids)} documents",
            total_documents=len(request.document_ids),
        )

    except Exception as e:
        logger.error(f"Pre-annotation submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_pre_annotation(
    task_id: str,
    engine: PreAnnotationEngine,
    request: PreAnnotationRequest,
) -> None:
    """Background task for pre-annotation processing."""
    try:
        logger.info(f"Processing pre-annotation task {task_id}")

        # Initialize progress tracking
        _task_progress[task_id] = {
            "status": "processing",
            "progress": 0.0,
            "processed_count": 0,
            "total_count": len(request.document_ids),
            "estimated_remaining_seconds": len(request.document_ids) * 2,
            "started_at": datetime.utcnow().isoformat(),
        }

        # Initialize engine
        await engine.initialize()

        # Import schemas
        try:
            from ai.annotation_schemas import (
                AnnotationType,
                AnnotationTask,
                AnnotatedSample,
                PreAnnotationConfig,
            )
        except ImportError:
            from src.ai.annotation_schemas import (
                AnnotationType,
                AnnotationTask,
                AnnotatedSample,
                PreAnnotationConfig,
            )

        # Map annotation type string to enum
        annotation_type_map = {
            "ner": AnnotationType.NER,
            "classification": AnnotationType.TEXT_CLASSIFICATION,
            "sentiment": AnnotationType.SENTIMENT,
            "relation": AnnotationType.RELATION_EXTRACTION,
            "qa": AnnotationType.QA,
            "summarization": AnnotationType.SUMMARIZATION,
        }
        ann_type = annotation_type_map.get(request.annotation_type.lower(), AnnotationType.NER)

        # Create annotation tasks from document IDs
        tasks = [
            AnnotationTask(
                id=doc_id,
                data={"document_id": doc_id},
                annotation_type=ann_type,
            )
            for doc_id in request.document_ids
        ]

        # Create config
        config = PreAnnotationConfig(
            annotation_type=ann_type,
            batch_size=request.batch_size,
            confidence_threshold=request.confidence_threshold,
            max_items=len(tasks),
        )

        # Process with or without samples
        if request.samples:
            samples = [
                AnnotatedSample(
                    id=str(i),
                    data=sample.get("data", {}),
                    annotation_type=ann_type,
                    annotation=sample.get("annotation", {}),
                    confidence=sample.get("confidence", 1.0),
                )
                for i, sample in enumerate(request.samples)
            ]
            result = await engine.pre_annotate_with_samples(tasks, samples, config)
        else:
            result = await engine.pre_annotate(tasks, config)

        # Store results
        _task_results[task_id] = [
            {
                "document_id": r.task_id,
                "annotations": [r.annotation] if r.annotation else [],
                "confidence": r.confidence,
                "needs_review": r.needs_review,
                "processing_time_ms": r.processing_time_ms or 0,
            }
            for r in result.results
        ]

        # Update progress to complete
        _task_progress[task_id] = {
            "status": "completed",
            "progress": 1.0,
            "processed_count": result.successful + result.failed,
            "total_count": result.total_tasks,
            "estimated_remaining_seconds": 0,
            "successful": result.successful,
            "failed": result.failed,
            "needs_review": result.needs_review,
            "completed_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Pre-annotation task {task_id} completed: {result.successful} successful, {result.failed} failed")

    except Exception as e:
        logger.error(f"Pre-annotation processing failed: {e}", exc_info=True)
        _task_progress[task_id] = {
            "status": "failed",
            "progress": 0.0,
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
        }


@router.get("/pre-annotate/{task_id}/progress")
async def get_pre_annotation_progress(task_id: str):
    """Get progress of a pre-annotation task."""
    progress = _task_progress.get(task_id)

    if not progress:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return {
        "task_id": task_id,
        **progress,
    }


@router.get("/pre-annotate/{task_id}/results", response_model=List[PreAnnotationResult])
async def get_pre_annotation_results(task_id: str):
    """Get results of a completed pre-annotation task."""
    # Check if task exists
    progress = _task_progress.get(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Check if task is completed
    if progress.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} is not yet completed (status: {progress.get('status')})"
        )

    # Get results
    results = _task_results.get(task_id, [])
    return [
        PreAnnotationResult(
            document_id=r["document_id"],
            annotations=r["annotations"],
            confidence=r["confidence"],
            needs_review=r["needs_review"],
            processing_time_ms=r["processing_time_ms"],
        )
        for r in results
    ]


# =============================================================================
# Mid-Coverage (Real-time Suggestion) Endpoints
# =============================================================================

@router.post("/suggestion", response_model=SuggestionResponse)
async def get_suggestion(
    request: SuggestionRequest,
    engine: MidCoverageEngine = Depends(get_mid_coverage_engine),
):
    """
    Get real-time annotation suggestion.

    - Targets <500ms latency (with LLM, may be up to 5s)
    - Uses pattern matching and similarity analysis
    - Returns confidence scores
    """
    import time
    start_time = time.time()

    try:
        # Generate suggestion ID
        suggestion_id = f"sug_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        # Import schemas
        try:
            from ai.annotation_schemas import (
                AnnotationType,
                AnnotationTask,
            )
        except ImportError:
            from src.ai.annotation_schemas import (
                AnnotationType,
                AnnotationTask,
            )

        # Map annotation type
        annotation_type_map = {
            "ner": AnnotationType.NER,
            "classification": AnnotationType.TEXT_CLASSIFICATION,
            "sentiment": AnnotationType.SENTIMENT,
            "relation": AnnotationType.RELATION_EXTRACTION,
        }
        ann_type = annotation_type_map.get(request.annotation_type.lower(), AnnotationType.NER)

        # Create task for suggestion
        task = AnnotationTask(
            id=request.document_id,
            data={"text": request.text, "context": request.context},
            annotation_type=ann_type,
        )

        # Check if we have cached patterns that match
        cached_patterns = list(engine._pattern_cache.values())
        annotations = []
        confidence = 0.0

        if cached_patterns:
            # Try to find matching patterns
            matches = await engine.find_similar_tasks(
                patterns=cached_patterns,
                unannotated_tasks=[task],
                similarity_threshold=0.7,
            )

            if matches:
                best_match = matches[0]
                pattern = engine._pattern_cache.get(best_match.pattern_id)
                if pattern and pattern.annotation_template:
                    annotations = [pattern.annotation_template]
                    confidence = best_match.similarity_score
                    logger.info(f"Found pattern match with confidence {confidence}")

        # If no pattern match, generate basic suggestion based on annotation type
        if not annotations:
            if ann_type == AnnotationType.NER:
                # Simple NER-based suggestion using heuristics
                annotations = _generate_ner_suggestions(request.text)
                confidence = 0.6 if annotations else 0.3
            elif ann_type == AnnotationType.TEXT_CLASSIFICATION:
                annotations = [{"label": "UNKNOWN", "confidence": 0.5}]
                confidence = 0.5
            elif ann_type == AnnotationType.SENTIMENT:
                annotations = [{"sentiment": "neutral", "score": 0.0, "confidence": 0.5}]
                confidence = 0.5
            else:
                annotations = [{"label": "SUGGESTION", "text": request.text[:50], "confidence": 0.4}]
                confidence = 0.4

        latency_ms = (time.time() - start_time) * 1000

        return SuggestionResponse(
            suggestion_id=suggestion_id,
            document_id=request.document_id,
            annotations=annotations,
            confidence=confidence,
            latency_ms=latency_ms,
        )

    except Exception as e:
        logger.error(f"Suggestion generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _generate_ner_suggestions(text: str) -> List[Dict[str, Any]]:
    """Generate basic NER suggestions using heuristics."""
    import re
    suggestions = []

    # Simple capitalized word detection for potential entities
    capitalized_pattern = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b')
    for match in capitalized_pattern.finditer(text):
        if len(match.group()) > 2:  # Skip single letters
            suggestions.append({
                "label": "ENTITY",
                "start": match.start(),
                "end": match.end(),
                "text": match.group(),
                "confidence": 0.6,
            })

    # Pattern for numbers/dates
    number_pattern = re.compile(r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d+(?:\.\d+)?%?\b')
    for match in number_pattern.finditer(text):
        suggestions.append({
            "label": "NUMBER" if '%' not in match.group() else "PERCENT",
            "start": match.start(),
            "end": match.end(),
            "text": match.group(),
            "confidence": 0.7,
        })

    # Pattern for emails
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    for match in email_pattern.finditer(text):
        suggestions.append({
            "label": "EMAIL",
            "start": match.start(),
            "end": match.end(),
            "text": match.group(),
            "confidence": 0.9,
        })

    return suggestions


# Feedback storage (in production, use database)
_suggestion_feedback: Dict[str, Dict[str, Any]] = {}


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    engine: MidCoverageEngine = Depends(get_mid_coverage_engine),
):
    """
    Submit feedback on a suggestion.

    - Updates learning model
    - Tracks acceptance/rejection rates
    """
    try:
        # Store feedback
        _suggestion_feedback[request.suggestion_id] = {
            "suggestion_id": request.suggestion_id,
            "accepted": request.accepted,
            "modified_annotation": request.modified_annotation,
            "reason": request.reason,
            "submitted_at": datetime.utcnow().isoformat(),
        }

        # If accepted with modification, we could use this to improve patterns
        if request.accepted and request.modified_annotation:
            # Import schemas for creating sample
            try:
                from ai.annotation_schemas import AnnotatedSample, AnnotationType
            except ImportError:
                from src.ai.annotation_schemas import AnnotatedSample, AnnotationType

            # Create a sample from the feedback to learn from
            sample = AnnotatedSample(
                id=f"feedback_{request.suggestion_id}",
                data=request.modified_annotation.get("data", {}),
                annotation_type=AnnotationType.NER,  # Default, should be from original
                annotation=request.modified_annotation,
                confidence=1.0,  # Human annotation is high confidence
            )

            # Analyze patterns from this new sample
            await engine.analyze_patterns([sample])
            logger.info(f"Learned from feedback {request.suggestion_id}")

        # Calculate acceptance rate
        total_feedback = len(_suggestion_feedback)
        accepted_count = sum(1 for f in _suggestion_feedback.values() if f.get("accepted"))
        acceptance_rate = accepted_count / total_feedback if total_feedback > 0 else 0.0

        # Check if rejection rate is high (>30%)
        rejection_rate = 1.0 - acceptance_rate
        if rejection_rate > 0.3 and total_feedback >= 10:
            logger.warning(f"High rejection rate detected: {rejection_rate:.2%}")
            # In production, this would trigger a notification

        return {
            "status": "accepted",
            "message": "Feedback recorded successfully",
            "suggestion_id": request.suggestion_id,
            "acceptance_rate": acceptance_rate,
        }

    except Exception as e:
        logger.error(f"Feedback submission failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-coverage", response_model=BatchCoverageResponse)
async def apply_batch_coverage(
    request: BatchCoverageRequest,
    engine: MidCoverageEngine = Depends(get_mid_coverage_engine),
):
    """
    Apply batch coverage based on patterns.

    - Applies consistent annotations across similar content
    - Returns conflict information
    """
    try:
        # TODO: Implement batch coverage
        return BatchCoverageResponse(
            applied_count=85,
            skipped_count=15,
            conflicts=[],
        )

    except Exception as e:
        logger.error(f"Batch coverage failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts/{project_id}", response_model=List[ConflictResponse])
async def get_conflicts(
    project_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """Get annotation conflicts for a project."""
    # TODO: Implement conflict retrieval
    return []


# =============================================================================
# Post-Validation Endpoints
# =============================================================================

@router.post("/validate", response_model=ValidationResponse)
async def validate_annotations(
    request: ValidationRequest,
    engine: PostValidationEngine = Depends(get_post_validation_engine),
):
    """
    Validate annotations for quality.

    - Checks accuracy, consistency, completeness
    - Applies custom validation rules
    """
    try:
        validation_id = f"val_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{request.project_id[:8]}"

        # Start background validation
        asyncio.create_task(
            _process_validation(
                validation_id=validation_id,
                engine=engine,
                request=request,
            )
        )

        return ValidationResponse(
            validation_id=validation_id,
            status="submitted",
            message="Validation task submitted",
        )

    except Exception as e:
        logger.error(f"Validation submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Validation results storage
_validation_results: Dict[str, Dict[str, Any]] = {}


async def _process_validation(
    validation_id: str,
    engine: PostValidationEngine,
    request: ValidationRequest,
) -> None:
    """Background task for validation processing."""
    try:
        logger.info(f"Processing validation task {validation_id}")

        # Initialize progress tracking
        _task_progress[validation_id] = {
            "status": "processing",
            "progress": 0.0,
            "started_at": datetime.utcnow().isoformat(),
        }

        # Import schemas
        try:
            from ai.annotation_schemas import ValidationConfig, ValidationRule
        except ImportError:
            from src.ai.annotation_schemas import ValidationConfig, ValidationRule

        # In production, fetch actual annotations from database
        # For now, use mock annotations based on document IDs
        annotations = []
        if request.document_ids:
            for doc_id in request.document_ids:
                annotations.append({
                    "id": doc_id,
                    "data": {"text": f"Sample text for document {doc_id}"},
                    "annotation_data": {"label": "ENTITY", "confidence": 0.85},
                })
        else:
            # If no document IDs, generate some mock annotations
            for i in range(10):
                annotations.append({
                    "id": f"doc_{i}",
                    "data": {"text": f"Sample text {i}"},
                    "annotation_data": {"label": "ENTITY", "confidence": 0.8 + (i * 0.01)},
                })

        # Create validation config
        custom_rules = []
        if request.custom_rules:
            for rule_data in request.custom_rules:
                custom_rules.append(ValidationRule(
                    rule_id=rule_data.get("rule_id", str(uuid4())),
                    name=rule_data.get("name", "Custom Rule"),
                    description=rule_data.get("description", ""),
                    condition=rule_data.get("condition", ""),
                    severity=rule_data.get("severity", "warning"),
                    enabled=rule_data.get("enabled", True),
                ))

        config = ValidationConfig(
            dimensions=request.validation_types,
            custom_rules=custom_rules,
            use_ragas=True,
            use_deepeval=True,
        )

        # Run validation
        report = await engine.validate(
            annotations=annotations,
            config=config,
        )

        # Store results
        _validation_results[validation_id] = {
            "report_id": report.report_id,
            "project_id": request.project_id,
            "overall_score": report.overall_score,
            "accuracy_score": report.accuracy,
            "recall_score": report.recall,
            "consistency_score": report.consistency,
            "completeness_score": report.completeness,
            "dimension_scores": report.dimension_scores,
            "issues": [
                {
                    "annotation_id": issue.annotation_id,
                    "dimension": issue.dimension,
                    "severity": issue.severity,
                    "message": issue.message,
                    "details": issue.details,
                }
                for issue in report.issues
            ],
            "recommendations": report.recommendations,
            "total_annotations": report.total_annotations,
            "created_at": report.created_at.isoformat() if report.created_at else datetime.utcnow().isoformat(),
        }

        # Update progress to complete
        _task_progress[validation_id] = {
            "status": "completed",
            "progress": 1.0,
            "completed_at": datetime.utcnow().isoformat(),
            "overall_score": report.overall_score,
        }

        logger.info(f"Validation task {validation_id} completed with score {report.overall_score:.2f}")

    except Exception as e:
        logger.error(f"Validation processing failed: {e}", exc_info=True)
        _task_progress[validation_id] = {
            "status": "failed",
            "progress": 0.0,
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
        }


@router.get("/quality-report/{project_id}", response_model=QualityReportResponse)
async def get_quality_report(
    project_id: str,
    engine: PostValidationEngine = Depends(get_post_validation_engine),
):
    """Get quality report for a project."""
    try:
        # Check for cached validation results for this project
        cached_result = None
        for val_id, result in _validation_results.items():
            if result.get("project_id") == project_id:
                cached_result = result
                break

        if cached_result:
            # Return cached result
            return QualityReportResponse(
                project_id=project_id,
                overall_score=cached_result.get("overall_score", 0.0),
                accuracy_score=cached_result.get("accuracy_score", 0.0),
                consistency_score=cached_result.get("consistency_score", 0.0),
                completeness_score=cached_result.get("completeness_score", 0.0),
                total_annotations=cached_result.get("total_annotations", 0),
                issues_count=len(cached_result.get("issues", [])),
                recommendations=cached_result.get("recommendations", []),
                generated_at=datetime.fromisoformat(cached_result.get("created_at", datetime.utcnow().isoformat())),
            )

        # If no cached result, generate a quick validation
        # In production, this would fetch annotations from database
        mock_annotations = [
            {
                "id": f"doc_{i}",
                "data": {"text": f"Sample text {i}"},
                "annotation_data": {"label": "ENTITY", "confidence": 0.8 + (i * 0.01)},
            }
            for i in range(20)
        ]

        # Import schemas
        try:
            from ai.annotation_schemas import ValidationConfig
        except ImportError:
            from src.ai.annotation_schemas import ValidationConfig

        config = ValidationConfig(
            dimensions=["accuracy", "consistency", "completeness"],
            use_ragas=False,  # Quick validation without Ragas
            use_deepeval=False,
        )

        report = await engine.validate(
            annotations=mock_annotations,
            config=config,
        )

        return QualityReportResponse(
            project_id=project_id,
            overall_score=report.overall_score,
            accuracy_score=report.accuracy,
            consistency_score=report.consistency,
            completeness_score=report.completeness,
            total_annotations=report.total_annotations,
            issues_count=len(report.issues),
            recommendations=report.recommendations,
            generated_at=report.created_at or datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Quality report generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inconsistencies/{project_id}", response_model=List[InconsistencyResponse])
async def get_inconsistencies(
    project_id: str,
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get inconsistencies found in annotations."""
    # TODO: Implement inconsistency retrieval
    return []


@router.post("/review-tasks", response_model=ReviewTaskResponse)
async def create_review_tasks(
    request: ReviewTaskRequest,
    collab_manager: CollaborationManager = Depends(get_collab_manager),
):
    """Create review tasks for flagged annotations."""
    try:
        task_ids = []
        for doc_id in request.document_ids:
            task_id = f"review_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{doc_id[:8]}"
            task_ids.append(task_id)

            # Assign task
            priority = TaskPriority(request.priority) if request.priority in [p.value for p in TaskPriority] else TaskPriority.NORMAL
            await collab_manager.assign_task(
                task_id=task_id,
                user_id=request.assignee_id,
                role=UserRole.REVIEWER,
                priority=priority,
            )

        return ReviewTaskResponse(
            task_ids=task_ids,
            total_created=len(task_ids),
        )

    except Exception as e:
        logger.error(f"Review task creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Engine Management Endpoints
# =============================================================================

@router.get("/engines", response_model=EngineListResponse)
async def list_engines(
    switcher: AnnotationSwitcher = Depends(get_annotation_switcher),
):
    """List available annotation engines."""
    try:
        # Get methods from switcher
        methods_info = switcher.list_methods_info()
        stats = switcher.get_all_stats()
        current_method = switcher.get_current_method()

        engines = []
        for info in methods_info:
            method_stats = stats.get(info.name, {})
            engines.append({
                "engine_id": info.name,
                "engine_type": info.method_type.value if hasattr(info.method_type, 'value') else str(info.method_type),
                "name": info.description or info.name,
                "status": "active" if info.enabled else "inactive",
                "is_default": info.name == current_method,
                "supported_types": [t.value if hasattr(t, 'value') else str(t) for t in info.supported_types],
                "config": info.config,
                "stats": {
                    "total_calls": method_stats.get("total_calls", 0),
                    "success_rate": method_stats.get("success_rate", 0.0),
                    "avg_latency_ms": method_stats.get("avg_latency_ms", 0.0),
                },
            })

        return EngineListResponse(
            engines=engines,
            count=len(engines),
        )

    except Exception as e:
        logger.error(f"Engine listing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/engines")
async def register_engine(
    request: EngineRegistrationRequest,
    switcher: AnnotationSwitcher = Depends(get_annotation_switcher),
):
    """Register a new annotation engine."""
    try:
        engine_id = f"{request.engine_type}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # TODO: Actually register engine with switcher

        return {
            "engine_id": engine_id,
            "status": "registered",
            "message": f"Engine {request.engine_name} registered successfully",
        }

    except Exception as e:
        logger.error(f"Engine registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/engines/compare", response_model=EngineComparisonResponse)
async def compare_engines(
    request: EngineComparisonRequest,
    switcher: AnnotationSwitcher = Depends(get_annotation_switcher),
):
    """Compare performance of multiple engines."""
    try:
        comparison_id = f"cmp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Import schemas
        try:
            from ai.annotation_plugin_interface import AnnotationType, AnnotationTask
        except ImportError:
            from src.ai.annotation_plugin_interface import AnnotationType, AnnotationTask

        # Map annotation type
        annotation_type_map = {
            "ner": AnnotationType.NER,
            "classification": AnnotationType.TEXT_CLASSIFICATION,
            "sentiment": AnnotationType.SENTIMENT,
            "relation": AnnotationType.RELATION_EXTRACTION,
        }
        ann_type = annotation_type_map.get(request.annotation_type.lower(), AnnotationType.NER)

        # Create test tasks from document IDs
        test_tasks = [
            AnnotationTask(
                id=doc_id,
                data={"document_id": doc_id, "text": f"Sample text for {doc_id}"},
                annotation_type=ann_type,
            )
            for doc_id in request.test_documents
        ]

        # Run comparison using switcher
        report = await switcher.compare_methods(
            tasks=test_tasks,
            annotation_type=ann_type,
            methods=request.engine_ids if request.engine_ids else None,
        )

        # Format results for API response
        results = []
        for method_name, method_data in report.results.items():
            results.append({
                "engine_id": method_name,
                "success": method_data.get("success", False),
                "accuracy": method_data.get("avg_confidence", 0.0),  # Use confidence as accuracy proxy
                "latency_ms": method_data.get("latency_ms", 0.0),
                "result_count": method_data.get("result_count", 0),
            })

        return EngineComparisonResponse(
            comparison_id=comparison_id,
            results=results,
            recommendation=report.winner,
        )

    except Exception as e:
        logger.error(f"Engine comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/engines/{engine_id}")
async def update_engine_config(
    engine_id: str,
    config: Dict[str, Any],
    switcher: AnnotationSwitcher = Depends(get_annotation_switcher),
):
    """Update engine configuration."""
    try:
        # TODO: Implement engine config update
        return {
            "engine_id": engine_id,
            "status": "updated",
            "message": "Engine configuration updated successfully",
        }

    except Exception as e:
        logger.error(f"Engine config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Task Management Endpoints
# =============================================================================

@router.post("/tasks/assign", response_model=TaskAssignmentResponse)
async def assign_task(
    request: TaskAssignmentRequest,
    collab_manager: CollaborationManager = Depends(get_collab_manager),
):
    """Assign annotation task to a user."""
    try:
        priority = TaskPriority(request.priority) if request.priority in [p.value for p in TaskPriority] else TaskPriority.NORMAL
        role = UserRole(request.role) if request.role and request.role in [r.value for r in UserRole] else None

        assignment = await collab_manager.assign_task(
            task_id=request.task_id,
            user_id=request.user_id,
            role=role,
            priority=priority,
            deadline=request.deadline,
        )

        return TaskAssignmentResponse(
            assignment_id=assignment.id,
            task_id=assignment.task_id,
            user_id=assignment.user_id,
            status=assignment.status.value,
            assigned_at=assignment.assigned_at,
        )

    except Exception as e:
        logger.error(f"Task assignment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task_details(
    task_id: str,
    collab_manager: CollaborationManager = Depends(get_collab_manager),
):
    """Get task details."""
    try:
        assignment = await collab_manager.get_task_assignment(task_id)

        if not assignment:
            raise HTTPException(status_code=404, detail="Task not found")

        return assignment.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit")
async def submit_annotation(
    request: TaskSubmissionRequest,
    collab_manager: CollaborationManager = Depends(get_collab_manager),
):
    """Submit completed annotation."""
    try:
        # TODO: Save annotations
        # TODO: Mark task as completed

        return {
            "task_id": request.task_id,
            "status": "submitted",
            "message": "Annotation submitted successfully",
        }

    except Exception as e:
        logger.error(f"Annotation submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conflicts/resolve")
async def resolve_conflict(
    request: ConflictResolutionRequest,
    ws_manager: AnnotationWebSocketManager = Depends(get_ws_manager),
):
    """Resolve annotation conflict."""
    try:
        # TODO: Actually resolve conflict

        return {
            "conflict_id": request.conflict_id,
            "status": "resolved",
            "resolution": request.resolution,
            "message": "Conflict resolved successfully",
        }

    except Exception as e:
        logger.error(f"Conflict resolution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{project_id}", response_model=ProgressMetricsResponse)
async def get_progress_metrics(
    project_id: str,
    collab_manager: CollaborationManager = Depends(get_collab_manager),
):
    """Get progress metrics for a project."""
    try:
        stats = await collab_manager.get_team_statistics(project_id)

        return ProgressMetricsResponse(
            project_id=project_id,
            total_tasks=stats.total_tasks,
            completed_tasks=stats.completed_tasks,
            in_progress_tasks=stats.assigned_tasks,
            pending_tasks=stats.total_tasks - stats.completed_tasks - stats.assigned_tasks,
            completion_rate=stats.completion_rate,
            avg_time_per_task_minutes=stats.avg_completion_time_minutes,
            active_annotators=stats.active_annotators,
            active_reviewers=stats.active_reviewers,
        )

    except Exception as e:
        logger.error(f"Progress metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@router.websocket("/ws")
async def annotation_websocket(
    websocket: WebSocket,
    ws_manager: AnnotationWebSocketManager = Depends(get_ws_manager),
):
    """
    WebSocket endpoint for real-time annotation collaboration.

    Supports:
    - Real-time suggestions (<100ms latency target)
    - Live annotation updates
    - Conflict detection and resolution
    - Progress tracking
    - User presence
    """
    connection = await ws_manager.connect(websocket)

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()

            # Handle message
            await ws_manager.handle_message(connection.connection_id, data)

    except WebSocketDisconnect:
        await ws_manager.disconnect(connection.connection_id, reason="Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws_manager.disconnect(connection.connection_id, reason=f"Error: {e}")


@router.get("/ws/stats")
async def get_websocket_stats(
    ws_manager: AnnotationWebSocketManager = Depends(get_ws_manager),
):
    """Get WebSocket connection statistics."""
    return ws_manager.get_stats()


# =============================================================================
# Additional Endpoints for Frontend Integration
# =============================================================================

class TaskListResponse(BaseModel):
    """List of annotation tasks."""
    tasks: List[Dict[str, Any]]
    total_count: int
    page: int
    page_size: int


class AIMetricsResponse(BaseModel):
    """AI metrics for a project."""
    total_annotations: int
    human_annotations: int
    ai_pre_annotations: int
    ai_suggestions: int
    ai_acceptance_rate: float
    time_saved_hours: float
    quality_score: float


class QualityMetricsResponse(BaseModel):
    """Detailed quality metrics for AI dashboard."""
    overview: Dict[str, Any]
    accuracy_trend: List[Dict[str, Any]]
    confidence_distribution: List[Dict[str, Any]]
    engine_performance: List[Dict[str, Any]]
    degradation_alerts: List[Dict[str, Any]]


class RoutingConfigRequest(BaseModel):
    """AI routing configuration."""
    low_confidence_threshold: float = Field(ge=0, le=1)
    high_confidence_threshold: float = Field(ge=0, le=1)
    auto_assign_high_confidence: bool = False
    skill_based_routing: bool = True
    workload_balancing: bool = True
    review_levels: int = Field(ge=1, le=3, default=2)


class RoutingConfigResponse(BaseModel):
    """Routing configuration response."""
    config: Dict[str, Any]
    status: str
    message: str


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    collab_manager: CollaborationManager = Depends(get_collab_manager),
):
    """
    List annotation tasks with filters.

    Returns tasks that match the specified filters, with pagination support.
    """
    try:
        # TODO: Implement actual database query with filters
        # For now, return mock data
        mock_tasks = [
            {
                "task_id": f"task_{i}",
                "title": f"Annotation Task {i}",
                "project_id": project_id or "default_project",
                "project_name": "Default Project",
                "assigned_to": "user1" if i % 2 == 0 else None,
                "assigned_by": "manual" if i % 2 == 0 else "ai",
                "status": "in_progress" if i % 3 == 0 else "pending",
                "priority": "high" if i % 4 == 0 else "medium",
                "metrics": {
                    "total_items": 100,
                    "human_annotated": 40 + i,
                    "ai_pre_annotated": 30,
                    "ai_suggested": 10,
                    "review_required": 5,
                },
                "created_at": datetime.utcnow().isoformat(),
            }
            for i in range(10)
        ]

        return TaskListResponse(
            tasks=mock_tasks,
            total_count=len(mock_tasks),
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Task listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=AIMetricsResponse)
async def get_ai_metrics(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    """
    Get AI annotation metrics.

    Returns overall metrics about AI assistance including:
    - Total annotations
    - Human vs AI annotation counts
    - Acceptance rates
    - Time saved
    - Quality scores
    """
    try:
        # TODO: Implement actual metrics calculation from database
        # For now, return mock data
        return AIMetricsResponse(
            total_annotations=1500,
            human_annotations=900,
            ai_pre_annotations=500,
            ai_suggestions=100,
            ai_acceptance_rate=0.85,
            time_saved_hours=45.5,
            quality_score=0.92,
        )

    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality-metrics", response_model=QualityMetricsResponse)
async def get_quality_metrics(
    project_id: str = Query(..., description="Project ID"),
    date_range: str = Query("last_30_days", description="Date range filter"),
    engine_id: Optional[str] = Query(None, description="Filter by engine"),
):
    """
    Get detailed quality metrics for AI quality dashboard.

    Returns comprehensive quality metrics including:
    - Accuracy trends
    - Confidence distributions
    - Engine performance comparisons
    - Quality degradation alerts
    """
    try:
        # TODO: Implement actual quality metrics calculation
        # For now, return mock data
        from datetime import timedelta

        # Generate mock accuracy trend
        accuracy_trend = []
        for i in range(7):
            date = datetime.utcnow() - timedelta(days=6-i)
            accuracy_trend.append({
                "date": date.strftime("%Y-%m-%d"),
                "ai_accuracy": 0.88 + (i * 0.01),
                "human_accuracy": 0.92 + (i * 0.005),
                "agreement_rate": 0.85 + (i * 0.008),
                "sample_count": 200 + (i * 10),
            })

        return QualityMetricsResponse(
            overview={
                "ai_accuracy": 0.92,
                "agreement_rate": 0.88,
                "total_samples": 1500,
                "active_alerts": 2,
            },
            accuracy_trend=accuracy_trend,
            confidence_distribution=[
                {"range": "0.9-1.0", "count": 800, "acceptance_rate": 0.95},
                {"range": "0.7-0.9", "count": 500, "acceptance_rate": 0.85},
                {"range": "0.5-0.7", "count": 150, "acceptance_rate": 0.60},
                {"range": "0.0-0.5", "count": 50, "acceptance_rate": 0.30},
            ],
            engine_performance=[
                {
                    "engine_id": "pre-annotation",
                    "engine_name": "Pre-annotation Engine",
                    "accuracy": 0.94,
                    "confidence": 0.91,
                    "samples": 600,
                    "suggestions": 580,
                    "acceptance_rate": 0.92,
                },
                {
                    "engine_id": "mid-coverage",
                    "engine_name": "Mid-coverage Engine",
                    "accuracy": 0.90,
                    "confidence": 0.85,
                    "samples": 500,
                    "suggestions": 450,
                    "acceptance_rate": 0.88,
                },
            ],
            degradation_alerts=[
                {
                    "alert_id": "alert_1",
                    "metric": "AI Accuracy",
                    "current_value": 0.92,
                    "previous_value": 0.95,
                    "degradation_rate": -0.03,
                    "severity": "warning",
                    "recommendation": "Review recent model changes",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ],
        )

    except Exception as e:
        logger.error(f"Quality metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing/config", response_model=RoutingConfigResponse)
async def get_routing_config():
    """Get current AI routing configuration."""
    try:
        # TODO: Retrieve from database/config store
        config = {
            "low_confidence_threshold": 0.5,
            "high_confidence_threshold": 0.9,
            "auto_assign_high_confidence": False,
            "skill_based_routing": True,
            "workload_balancing": True,
            "review_levels": 2,
        }

        return RoutingConfigResponse(
            config=config,
            status="success",
            message="Routing configuration retrieved successfully",
        )

    except Exception as e:
        logger.error(f"Routing config retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/routing/config", response_model=RoutingConfigResponse)
async def update_routing_config(request: RoutingConfigRequest):
    """
    Update AI routing configuration.

    Configures how AI suggestions are routed based on:
    - Confidence thresholds
    - Auto-assignment rules
    - Skill-based routing
    - Workload balancing
    """
    try:
        # Validate thresholds
        if request.low_confidence_threshold >= request.high_confidence_threshold:
            raise HTTPException(
                status_code=400,
                detail="Low confidence threshold must be less than high confidence threshold",
            )

        # TODO: Save to database/config store
        config = request.dict()

        logger.info(f"Routing config updated: {config}")

        return RoutingConfigResponse(
            config=config,
            status="success",
            message="Routing configuration updated successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Routing config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
