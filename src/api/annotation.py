"""
Annotation API endpoints for SuperInsight platform.

Provides REST API endpoints for the complete AI annotation workflow:
- Pre-annotation (事前预标)
- Mid-coverage (事中覆盖)
- Post-validation (事后验证)
- Review workflow (审核流程)
- Collaboration (协作管理)
- Plugin management (插件管理)
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Request/Response Models
# ============================================================================

# Pre-Annotation Models
class PreAnnotationRequest(BaseModel):
    """Request for pre-annotation."""
    task_ids: List[str] = Field(..., description="Task IDs to pre-annotate")
    annotation_type: str = Field(..., description="Annotation type")
    model_name: Optional[str] = Field(None, description="Model to use")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Confidence threshold")
    samples: Optional[List[Dict[str, Any]]] = Field(None, description="Sample annotations for learning")


class PreAnnotationResponse(BaseModel):
    """Response for pre-annotation."""
    results: List[Dict[str, Any]] = Field(..., description="Pre-annotation results")
    total: int = Field(..., description="Total tasks processed")
    high_confidence: int = Field(..., description="High confidence count")
    low_confidence: int = Field(..., description="Low confidence count")


# Mid-Coverage Models
class CoverageRequest(BaseModel):
    """Request for mid-coverage analysis."""
    project_id: str = Field(..., description="Project ID")
    annotation_type: str = Field(..., description="Annotation type")
    similarity_threshold: float = Field(0.85, ge=0.0, le=1.0, description="Similarity threshold")


class CoverageResponse(BaseModel):
    """Response for mid-coverage."""
    patterns: List[Dict[str, Any]] = Field(..., description="Detected patterns")
    similar_tasks: List[Dict[str, Any]] = Field(..., description="Similar task groups")
    coverage_stats: Dict[str, Any] = Field(..., description="Coverage statistics")


class AutoCoverRequest(BaseModel):
    """Request for auto-coverage."""
    source_annotation_id: str = Field(..., description="Source annotation ID")
    target_task_ids: List[str] = Field(..., description="Target task IDs")
    similarity_threshold: float = Field(0.85, ge=0.0, le=1.0, description="Similarity threshold")


# Post-Validation Models
class ValidationRequest(BaseModel):
    """Request for post-validation."""
    annotation_ids: List[str] = Field(..., description="Annotation IDs to validate")
    validation_types: List[str] = Field(
        default=["accuracy", "consistency", "completeness"],
        description="Validation types"
    )
    custom_rules: Optional[List[Dict[str, Any]]] = Field(None, description="Custom validation rules")


class ValidationResponse(BaseModel):
    """Response for post-validation."""
    report: Dict[str, Any] = Field(..., description="Validation report")
    passed: bool = Field(..., description="Overall pass status")
    issues: List[Dict[str, Any]] = Field(..., description="Detected issues")


# Review Models
class ReviewSubmitRequest(BaseModel):
    """Request to submit for review."""
    annotation_id: str = Field(..., description="Annotation ID")
    annotator_id: str = Field(..., description="Annotator ID")
    project_id: Optional[str] = Field(None, description="Project ID")


class ReviewActionRequest(BaseModel):
    """Request for review action."""
    reviewer_id: str = Field(..., description="Reviewer ID")
    comments: Optional[str] = Field("", description="Comments")
    reason: Optional[str] = Field("", description="Rejection reason")
    modifications: Optional[Dict[str, Any]] = Field(None, description="Modifications")


class BatchReviewRequest(BaseModel):
    """Request for batch review."""
    review_task_ids: List[str] = Field(..., description="Review task IDs")
    reviewer_id: str = Field(..., description="Reviewer ID")
    action: str = Field(..., description="Action: approve or reject")
    reason: Optional[str] = Field("", description="Reason for rejection")


class ReviewResponse(BaseModel):
    """Response for review action."""
    success: bool = Field(..., description="Success status")
    review_task: Dict[str, Any] = Field(..., description="Review task details")
    message: str = Field(..., description="Result message")


# Collaboration Models
class TaskAssignRequest(BaseModel):
    """Request to assign task."""
    task_id: str = Field(..., description="Task ID")
    user_id: str = Field(..., description="User ID to assign to")
    role: str = Field(..., description="Role: annotator or reviewer")
    priority: int = Field(1, ge=1, le=5, description="Priority level")


class WorkloadResponse(BaseModel):
    """Response for workload query."""
    user_id: str = Field(..., description="User ID")
    pending_tasks: int = Field(..., description="Pending task count")
    completed_tasks: int = Field(..., description="Completed task count")
    in_progress_tasks: int = Field(..., description="In-progress task count")


# Plugin Models
class PluginRegisterRequest(BaseModel):
    """Request to register plugin."""
    name: str = Field(..., description="Plugin name")
    plugin_type: str = Field(..., description="Plugin type")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    config: Dict[str, Any] = Field(default_factory=dict, description="Plugin configuration")
    priority: int = Field(0, description="Priority level")


class PluginResponse(BaseModel):
    """Response for plugin operations."""
    plugin_id: str = Field(..., description="Plugin ID")
    name: str = Field(..., description="Plugin name")
    status: str = Field(..., description="Plugin status")
    message: str = Field(..., description="Result message")


class PluginStatsResponse(BaseModel):
    """Response for plugin statistics."""
    plugin_id: str = Field(..., description="Plugin ID")
    total_calls: int = Field(..., description="Total calls")
    success_rate: float = Field(..., description="Success rate")
    avg_latency_ms: float = Field(..., description="Average latency in ms")
    total_cost: float = Field(..., description="Total cost")


# ============================================================================
# Router
# ============================================================================

router = APIRouter(prefix="/api/v1/annotation", tags=["Annotation Workflow"])


# ============================================================================
# Pre-Annotation Endpoints
# ============================================================================

@router.post("/pre-annotate", response_model=PreAnnotationResponse)
async def pre_annotate(request: PreAnnotationRequest):
    """
    Execute pre-annotation on tasks.
    
    Requirement 1.1: 预标注功能
    """
    try:
        # Import engine
        from src.ai.pre_annotation import get_pre_annotation_engine
        
        engine = get_pre_annotation_engine()
        
        # Build tasks
        from src.ai.annotation_schemas import AnnotationTask, AnnotationType
        
        tasks = [
            AnnotationTask(
                id=task_id,
                data={"text": ""},  # Would be fetched from DB
                annotation_type=AnnotationType(request.annotation_type),
            )
            for task_id in request.task_ids
        ]
        
        # Execute pre-annotation
        if request.samples:
            results = await engine.pre_annotate_with_samples(
                tasks=tasks,
                annotation_type=AnnotationType(request.annotation_type),
                samples=request.samples,
            )
        else:
            results = await engine.pre_annotate(
                tasks=tasks,
                annotation_type=AnnotationType(request.annotation_type),
            )
        
        # Count by confidence
        high_conf = sum(1 for r in results if r.confidence >= request.confidence_threshold)
        low_conf = len(results) - high_conf
        
        return PreAnnotationResponse(
            results=[r.dict() for r in results],
            total=len(results),
            high_confidence=high_conf,
            low_confidence=low_conf,
        )
        
    except Exception as e:
        logger.error(f"Pre-annotation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pre-annotate/mark-review")
async def mark_for_review(
    annotation_ids: List[str] = Body(...),
    threshold: float = Body(0.7),
):
    """
    Mark low-confidence annotations for review.
    
    Requirement 1.5: 阈值标记
    """
    try:
        from src.ai.pre_annotation import get_pre_annotation_engine
        
        engine = get_pre_annotation_engine()
        marked = await engine.mark_for_review(annotation_ids, threshold)
        
        return {
            "marked_count": len(marked),
            "marked_ids": marked,
        }
        
    except Exception as e:
        logger.error(f"Mark for review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Mid-Coverage Endpoints
# ============================================================================

@router.post("/coverage/analyze", response_model=CoverageResponse)
async def analyze_coverage(request: CoverageRequest):
    """
    Analyze annotation patterns for mid-coverage.
    
    Requirement 2.1, 2.2: 模式分析和相似查找
    """
    try:
        from src.ai.mid_coverage import get_mid_coverage_engine
        from src.ai.annotation_schemas import AnnotationType
        
        engine = get_mid_coverage_engine()
        
        # Analyze patterns
        patterns = await engine.analyze_patterns(
            project_id=request.project_id,
            annotation_type=AnnotationType(request.annotation_type),
        )
        
        # Find similar tasks
        similar = await engine.find_similar_tasks(
            project_id=request.project_id,
            similarity_threshold=request.similarity_threshold,
        )
        
        return CoverageResponse(
            patterns=[p.dict() if hasattr(p, 'dict') else p for p in patterns],
            similar_tasks=similar,
            coverage_stats={
                "pattern_count": len(patterns),
                "similar_group_count": len(similar),
            },
        )
        
    except Exception as e:
        logger.error(f"Coverage analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/coverage/auto-cover")
async def auto_cover(request: AutoCoverRequest):
    """
    Auto-cover similar tasks with existing annotation.
    
    Requirement 2.3, 2.4: 自动覆盖
    """
    try:
        from src.ai.mid_coverage import get_mid_coverage_engine
        
        engine = get_mid_coverage_engine()
        
        results = await engine.auto_cover(
            source_annotation_id=request.source_annotation_id,
            target_task_ids=request.target_task_ids,
            similarity_threshold=request.similarity_threshold,
        )
        
        return {
            "covered_count": len([r for r in results if r.get("covered", False)]),
            "results": results,
        }
        
    except Exception as e:
        logger.error(f"Auto-cover failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Post-Validation Endpoints
# ============================================================================

@router.post("/validate", response_model=ValidationResponse)
async def validate_annotations(request: ValidationRequest):
    """
    Validate annotations with multi-dimensional checks.
    
    Requirement 3.1, 3.2: 多维验证
    """
    try:
        from src.ai.post_validation import get_post_validation_engine
        
        engine = get_post_validation_engine()
        
        # Execute validation
        report = await engine.validate(
            annotation_ids=request.annotation_ids,
            validation_types=request.validation_types,
            custom_rules=request.custom_rules,
        )
        
        return ValidationResponse(
            report=report.to_dict() if hasattr(report, 'to_dict') else report,
            passed=report.passed if hasattr(report, 'passed') else report.get("passed", True),
            issues=report.issues if hasattr(report, 'issues') else report.get("issues", []),
        )
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate/report")
async def generate_validation_report(
    annotation_ids: List[str] = Body(...),
    format: str = Body("json"),
):
    """
    Generate validation report.
    
    Requirement 3.5: 报告生成
    """
    try:
        from src.ai.post_validation import get_post_validation_engine
        
        engine = get_post_validation_engine()
        report = await engine.generate_report(annotation_ids, format=format)
        
        return report
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Review Workflow Endpoints
# ============================================================================

@router.post("/review/submit", response_model=ReviewResponse)
async def submit_for_review(request: ReviewSubmitRequest):
    """
    Submit annotation for review.
    
    Requirement 6.1, 6.2: 审核流程
    """
    try:
        from src.ai.review_flow import get_review_flow_engine
        
        engine = get_review_flow_engine()
        
        task = await engine.submit_for_review(
            annotation_id=request.annotation_id,
            annotator_id=request.annotator_id,
            project_id=request.project_id,
        )
        
        return ReviewResponse(
            success=True,
            review_task=task.to_dict(),
            message="Submitted for review",
        )
        
    except Exception as e:
        logger.error(f"Submit for review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review/{review_task_id}/approve", response_model=ReviewResponse)
async def approve_review(review_task_id: str, request: ReviewActionRequest):
    """
    Approve annotation.
    
    Requirement 6.3: 审核操作
    """
    try:
        from src.ai.review_flow import get_review_flow_engine
        
        engine = get_review_flow_engine()
        
        result = await engine.approve(
            review_task_id=review_task_id,
            reviewer_id=request.reviewer_id,
            comments=request.comments or "",
        )
        
        return ReviewResponse(
            success=result.success,
            review_task=result.review_task.to_dict(),
            message=result.message,
        )
        
    except Exception as e:
        logger.error(f"Approve failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review/{review_task_id}/reject", response_model=ReviewResponse)
async def reject_review(review_task_id: str, request: ReviewActionRequest):
    """
    Reject annotation.
    
    Requirement 6.3, 6.4: 审核驳回退回
    """
    try:
        from src.ai.review_flow import get_review_flow_engine
        
        engine = get_review_flow_engine()
        
        result = await engine.reject(
            review_task_id=review_task_id,
            reviewer_id=request.reviewer_id,
            reason=request.reason or "",
        )
        
        return ReviewResponse(
            success=result.success,
            review_task=result.review_task.to_dict(),
            message=result.message,
        )
        
    except Exception as e:
        logger.error(f"Reject failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review/{review_task_id}/modify", response_model=ReviewResponse)
async def modify_review(review_task_id: str, request: ReviewActionRequest):
    """
    Modify annotation during review.
    
    Requirement 6.3: 审核操作
    """
    try:
        from src.ai.review_flow import get_review_flow_engine
        
        engine = get_review_flow_engine()
        
        result = await engine.modify(
            review_task_id=review_task_id,
            reviewer_id=request.reviewer_id,
            modifications=request.modifications or {},
            comments=request.comments or "",
        )
        
        return ReviewResponse(
            success=result.success,
            review_task=result.review_task.to_dict(),
            message=result.message,
        )
        
    except Exception as e:
        logger.error(f"Modify failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review/batch")
async def batch_review(request: BatchReviewRequest):
    """
    Batch review operations.
    
    Requirement 6.6: 批量审核
    """
    try:
        from src.ai.review_flow import get_review_flow_engine
        
        engine = get_review_flow_engine()
        
        if request.action == "approve":
            results = await engine.batch_approve(
                review_task_ids=request.review_task_ids,
                reviewer_id=request.reviewer_id,
                comments=request.reason or "",
            )
        elif request.action == "reject":
            results = await engine.batch_reject(
                review_task_ids=request.review_task_ids,
                reviewer_id=request.reviewer_id,
                reason=request.reason or "",
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")
        
        return {
            "total": len(results),
            "success_count": sum(1 for r in results if r.success),
            "results": [r.to_dict() for r in results],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/review/{annotation_id}/history")
async def get_review_history(annotation_id: str):
    """
    Get review history for annotation.
    
    Requirement 6.5: 审核历史
    """
    try:
        from src.ai.review_flow import get_review_flow_engine
        
        engine = get_review_flow_engine()
        history = await engine.get_review_history(annotation_id)
        
        return {
            "annotation_id": annotation_id,
            "history": [r.to_dict() for r in history],
        }
        
    except Exception as e:
        logger.error(f"Get history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/review/pending")
async def get_pending_reviews(
    reviewer_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Get pending review tasks.
    
    Requirement 6.2: 审核流程
    """
    try:
        from src.ai.review_flow import get_review_flow_engine
        
        engine = get_review_flow_engine()
        tasks = await engine.get_pending_reviews(reviewer_id=reviewer_id, limit=limit)
        
        return {
            "tasks": [t.to_dict() for t in tasks],
            "count": len(tasks),
        }
        
    except Exception as e:
        logger.error(f"Get pending reviews failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Collaboration Endpoints
# ============================================================================

@router.post("/collaboration/assign")
async def assign_task(request: TaskAssignRequest):
    """
    Assign task to user.
    
    Requirement 5.1, 5.2, 5.3: 角色和分配
    """
    try:
        from src.ai.collaboration_manager import get_collaboration_manager
        
        manager = get_collaboration_manager()
        
        result = await manager.assign_task(
            task_id=request.task_id,
            user_id=request.user_id,
            role=request.role,
            priority=request.priority,
        )
        
        return {
            "success": True,
            "assignment": result,
        }
        
    except Exception as e:
        logger.error(f"Task assignment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collaboration/auto-assign")
async def auto_assign_reviewer(
    task_id: str = Body(...),
    project_id: Optional[str] = Body(None),
):
    """
    Auto-assign reviewer to task.
    
    Requirement 5.4: 自动分配
    """
    try:
        from src.ai.collaboration_manager import get_collaboration_manager
        
        manager = get_collaboration_manager()
        result = await manager.auto_assign_to_reviewer(task_id, project_id)
        
        return {
            "success": True,
            "reviewer_id": result.get("reviewer_id"),
            "assignment": result,
        }
        
    except Exception as e:
        logger.error(f"Auto-assign failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collaboration/workload/{user_id}", response_model=WorkloadResponse)
async def get_workload(user_id: str):
    """
    Get user workload statistics.
    
    Requirement 5.5: 工作量统计
    """
    try:
        from src.ai.collaboration_manager import get_collaboration_manager
        
        manager = get_collaboration_manager()
        workload = await manager.get_workload(user_id)
        
        return WorkloadResponse(
            user_id=user_id,
            pending_tasks=workload.get("pending", 0),
            completed_tasks=workload.get("completed", 0),
            in_progress_tasks=workload.get("in_progress", 0),
        )
        
    except Exception as e:
        logger.error(f"Get workload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collaboration/team-stats")
async def get_team_statistics(project_id: Optional[str] = Query(None)):
    """
    Get team statistics.
    
    Requirement 5.6: 团队统计
    """
    try:
        from src.ai.collaboration_manager import get_collaboration_manager
        
        manager = get_collaboration_manager()
        stats = await manager.get_team_statistics(project_id)
        
        return stats
        
    except Exception as e:
        logger.error(f"Get team stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Plugin Management Endpoints
# ============================================================================

@router.post("/plugins/register", response_model=PluginResponse)
async def register_plugin(request: PluginRegisterRequest):
    """
    Register annotation plugin.
    
    Requirement 9.1: 插件注册
    """
    try:
        from src.ai.annotation_plugin_manager import get_plugin_manager
        
        manager = get_plugin_manager()
        
        plugin_id = await manager.register_plugin(
            name=request.name,
            plugin_type=request.plugin_type,
            endpoint=request.endpoint,
            config=request.config,
            priority=request.priority,
        )
        
        return PluginResponse(
            plugin_id=plugin_id,
            name=request.name,
            status="registered",
            message="Plugin registered successfully",
        )
        
    except Exception as e:
        logger.error(f"Plugin registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/plugins/{plugin_id}")
async def unregister_plugin(plugin_id: str):
    """
    Unregister annotation plugin.
    
    Requirement 9.1: 插件管理
    """
    try:
        from src.ai.annotation_plugin_manager import get_plugin_manager
        
        manager = get_plugin_manager()
        await manager.unregister_plugin(plugin_id)
        
        return {"message": f"Plugin {plugin_id} unregistered"}
        
    except Exception as e:
        logger.error(f"Plugin unregistration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str):
    """
    Enable annotation plugin.
    
    Requirement 9.4: 启用/禁用
    """
    try:
        from src.ai.annotation_plugin_manager import get_plugin_manager
        
        manager = get_plugin_manager()
        await manager.enable_plugin(plugin_id)
        
        return {"message": f"Plugin {plugin_id} enabled"}
        
    except Exception as e:
        logger.error(f"Plugin enable failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin(plugin_id: str):
    """
    Disable annotation plugin.
    
    Requirement 9.4: 启用/禁用
    """
    try:
        from src.ai.annotation_plugin_manager import get_plugin_manager
        
        manager = get_plugin_manager()
        await manager.disable_plugin(plugin_id)
        
        return {"message": f"Plugin {plugin_id} disabled"}
        
    except Exception as e:
        logger.error(f"Plugin disable failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plugins")
async def list_plugins(
    enabled_only: bool = Query(False),
):
    """
    List registered plugins.
    
    Requirement 9.1: 插件列表
    """
    try:
        from src.ai.annotation_plugin_manager import get_plugin_manager
        
        manager = get_plugin_manager()
        plugins = await manager.list_plugins(enabled_only=enabled_only)
        
        return {
            "plugins": plugins,
            "count": len(plugins),
        }
        
    except Exception as e:
        logger.error(f"List plugins failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plugins/{plugin_id}/stats", response_model=PluginStatsResponse)
async def get_plugin_stats(plugin_id: str):
    """
    Get plugin statistics.
    
    Requirement 9.5: 调用统计
    """
    try:
        from src.ai.plugin_statistics import get_plugin_statistics_service
        
        service = get_plugin_statistics_service()
        stats = await service.get_plugin_statistics(plugin_id)
        
        return PluginStatsResponse(
            plugin_id=plugin_id,
            total_calls=stats.get("total_calls", 0),
            success_rate=stats.get("success_rate", 0.0),
            avg_latency_ms=stats.get("avg_latency_ms", 0.0),
            total_cost=stats.get("total_cost", 0.0),
        )
        
    except Exception as e:
        logger.error(f"Get plugin stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/{plugin_id}/test")
async def test_plugin_connection(plugin_id: str):
    """
    Test plugin connection.
    
    Requirement 9.3: 连接测试
    """
    try:
        from src.ai.annotation_plugin_manager import get_plugin_manager
        
        manager = get_plugin_manager()
        result = await manager.test_connection(plugin_id)
        
        return {
            "plugin_id": plugin_id,
            "connected": result.get("connected", False),
            "latency_ms": result.get("latency_ms", 0),
            "message": result.get("message", ""),
        }
        
    except Exception as e:
        logger.error(f"Plugin test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plugins/{plugin_id}/priority")
async def set_plugin_priority(
    plugin_id: str,
    priority: int = Body(..., ge=0, le=100),
):
    """
    Set plugin priority.
    
    Requirement 9.6: 优先级配置
    """
    try:
        from src.ai.annotation_plugin_manager import get_plugin_manager
        
        manager = get_plugin_manager()
        await manager.set_priority(plugin_id, priority)
        
        return {"message": f"Plugin {plugin_id} priority set to {priority}"}
        
    except Exception as e:
        logger.error(f"Set priority failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Method Switcher Endpoints
# ============================================================================

@router.post("/method/switch")
async def switch_annotation_method(
    method: str = Body(...),
    reason: str = Body(""),
):
    """
    Switch annotation method.
    
    Requirement 4.4: 热切换
    """
    try:
        from src.ai.annotation_switcher import get_annotation_switcher
        
        switcher = get_annotation_switcher()
        result = switcher.switch_method(method, reason)
        
        return {
            "success": result,
            "current_method": switcher.get_current_method(),
        }
        
    except Exception as e:
        logger.error(f"Method switch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/method/current")
async def get_current_method():
    """
    Get current annotation method.
    
    Requirement 4.1: 方法切换
    """
    try:
        from src.ai.annotation_switcher import get_annotation_switcher
        
        switcher = get_annotation_switcher()
        
        return {
            "current_method": switcher.get_current_method(),
            "available_methods": switcher.list_available_methods(),
        }
        
    except Exception as e:
        logger.error(f"Get current method failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/method/compare")
async def compare_methods(
    task_ids: List[str] = Body(...),
    methods: List[str] = Body(...),
    annotation_type: str = Body(...),
):
    """
    Compare annotation methods.
    
    Requirement 4.5: 方法对比
    """
    try:
        from src.ai.annotation_switcher import get_annotation_switcher
        from src.ai.annotation_schemas import AnnotationTask, AnnotationType
        
        switcher = get_annotation_switcher()
        
        tasks = [
            AnnotationTask(
                id=task_id,
                data={"text": ""},
                annotation_type=AnnotationType(annotation_type),
            )
            for task_id in task_ids
        ]
        
        results = await switcher.compare_methods(
            tasks=tasks,
            methods=methods,
            annotation_type=AnnotationType(annotation_type),
        )
        
        return {
            "comparison": results,
        }
        
    except Exception as e:
        logger.error(f"Method comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/method/history")
async def get_switch_history():
    """
    Get method switch history.
    
    Requirement 4.6: 切换日志
    """
    try:
        from src.ai.annotation_switcher import get_annotation_switcher
        
        switcher = get_annotation_switcher()
        history = switcher.get_switch_history()
        
        return {
            "history": history,
        }
        
    except Exception as e:
        logger.error(f"Get switch history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
