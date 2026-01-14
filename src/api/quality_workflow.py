"""
Quality Workflow API - 质量工作流 API
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from src.quality.quality_workflow_engine import (
    QualityWorkflowEngine,
    QualityWorkflow,
    WorkflowConfig,
    ImprovementTask,
    ImprovementHistory,
    ImprovementEffectReport,
    QualityIssue
)


router = APIRouter(prefix="/api/v1/quality-workflow", tags=["Quality Workflow"])


# 全局实例
_workflow_engine: Optional[QualityWorkflowEngine] = None


def get_workflow_engine() -> QualityWorkflowEngine:
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = QualityWorkflowEngine()
    return _workflow_engine


# Request/Response Models
class WorkflowConfigRequest(BaseModel):
    """工作流配置请求"""
    project_id: str
    stages: List[str] = Field(default_factory=lambda: ["identify", "assign", "improve", "review", "verify"])
    auto_create_task: bool = True
    auto_assign_rules: Dict[str, Any] = Field(default_factory=dict)
    escalation_rules: Dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    """工作流响应"""
    id: str
    project_id: str
    stages: List[str]
    auto_create_task: bool
    auto_assign_rules: Dict[str, Any]
    escalation_rules: Dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class IssueRequest(BaseModel):
    """问题请求"""
    rule_id: str
    rule_name: str
    severity: str
    message: str
    field: Optional[str] = None


class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    annotation_id: str
    issues: List[IssueRequest]
    assignee_id: Optional[str] = None
    project_id: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskResponse(BaseModel):
    """任务响应"""
    id: str
    annotation_id: str
    project_id: str
    issues: List[Dict[str, Any]]
    assignee_id: str
    status: str
    priority: int
    improved_data: Optional[Dict[str, Any]] = None
    original_data: Optional[Dict[str, Any]] = None
    reviewer_id: Optional[str] = None
    review_comments: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskResponse]
    total: int


class SubmitRequest(BaseModel):
    """提交改进请求"""
    improved_data: Dict[str, Any]
    user_id: Optional[str] = None


class ReviewRequest(BaseModel):
    """审核请求"""
    reviewer_id: str
    approved: bool
    comments: Optional[str] = None


class StartRequest(BaseModel):
    """开始改进请求"""
    user_id: str


class ReopenRequest(BaseModel):
    """重新打开请求"""
    user_id: str
    comments: Optional[str] = None


class HistoryResponse(BaseModel):
    """历史响应"""
    id: str
    task_id: str
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    actor_id: str
    comments: Optional[str] = None
    created_at: datetime


class EffectReportResponse(BaseModel):
    """效果报告响应"""
    project_id: str
    period: str
    total_tasks: int
    completed_tasks: int
    average_improvement: float
    by_severity: Dict[str, int]
    generated_at: datetime


# API Endpoints
@router.post("/configure", response_model=WorkflowResponse)
async def configure_workflow(
    request: WorkflowConfigRequest,
    engine: QualityWorkflowEngine = Depends(get_workflow_engine)
) -> WorkflowResponse:
    """
    配置质量改进工作流
    
    - **project_id**: 项目ID
    - **stages**: 工作流阶段
    - **auto_create_task**: 是否自动创建任务
    - **auto_assign_rules**: 自动分配规则
    - **escalation_rules**: 升级规则
    """
    config = WorkflowConfig(
        stages=request.stages,
        auto_create_task=request.auto_create_task,
        auto_assign_rules=request.auto_assign_rules,
        escalation_rules=request.escalation_rules
    )
    
    workflow = await engine.configure_workflow(request.project_id, config)
    
    return WorkflowResponse(
        id=workflow.id,
        project_id=workflow.project_id,
        stages=workflow.stages,
        auto_create_task=workflow.auto_create_task,
        auto_assign_rules=workflow.auto_assign_rules,
        escalation_rules=workflow.escalation_rules,
        enabled=workflow.enabled,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at
    )


@router.get("/config/{project_id}", response_model=WorkflowResponse)
async def get_workflow_config(
    project_id: str,
    engine: QualityWorkflowEngine = Depends(get_workflow_engine)
) -> WorkflowResponse:
    """
    获取工作流配置
    
    - **project_id**: 项目ID
    """
    workflow = await engine.get_workflow(project_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow config not found")
    
    return WorkflowResponse(
        id=workflow.id,
        project_id=workflow.project_id,
        stages=workflow.stages,
        auto_create_task=workflow.auto_create_task,
        auto_assign_rules=workflow.auto_assign_rules,
        escalation_rules=workflow.escalation_rules,
        enabled=workflow.enabled,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at
    )


@router.post("/tasks", response_model=TaskResponse)
async def create_improvement_task(
    request: CreateTaskRequest,
    engine: QualityWorkflowEngine = Depends(get_workflow_engine)
) -> TaskResponse:
    """
    创建改进任务
    
    - **annotation_id**: 标注ID
    - **issues**: 质量问题列表
    - **assignee_id**: 负责人ID (可选)
    - **project_id**: 项目ID (可选)
    - **due_date**: 截止日期 (可选)
    """
    issues = [
        QualityIssue(
            rule_id=i.rule_id,
            rule_name=i.rule_name,
            severity=i.severity,
            message=i.message,
            field=i.field
        )
        for i in request.issues
    ]
    
    task = await engine.create_improvement_task(
        annotation_id=request.annotation_id,
        issues=issues,
        assignee_id=request.assignee_id,
        project_id=request.project_id,
        due_date=request.due_date
    )
    
    return TaskResponse(
        id=task.id,
        annotation_id=task.annotation_id,
        project_id=task.project_id,
        issues=[i.dict() for i in task.issues],
        assignee_id=task.assignee_id,
        status=task.status,
        priority=task.priority,
        improved_data=task.improved_data,
        original_data=task.original_data,
        reviewer_id=task.reviewer_id,
        review_comments=task.review_comments,
        due_date=task.due_date,
        created_at=task.created_at,
        submitted_at=task.submitted_at,
        reviewed_at=task.reviewed_at
    )


@router.get("/tasks", response_model=TaskListResponse)
async def list_improvement_tasks(
    project_id: Optional[str] = Query(None, description="项目ID"),
    assignee_id: Optional[str] = Query(None, description="负责人ID"),
    status: Optional[str] = Query(None, description="状态"),
    engine: QualityWorkflowEngine = Depends(get_workflow_engine)
) -> TaskListResponse:
    """
    获取改进任务列表
    
    - **project_id**: 项目ID (可选)
    - **assignee_id**: 负责人ID (可选)
    - **status**: 状态 (可选)
    """
    tasks = await engine.get_improvement_tasks(
        project_id=project_id,
        assignee_id=assignee_id,
        status=status
    )
    
    task_responses = [
        TaskResponse(
            id=t.id,
            annotation_id=t.annotation_id,
            project_id=t.project_id,
            issues=[i.dict() for i in t.issues],
            assignee_id=t.assignee_id,
            status=t.status,
            priority=t.priority,
            improved_data=t.improved_data,
            original_data=t.original_data,
            reviewer_id=t.reviewer_id,
            review_comments=t.review_comments,
            due_date=t.due_date,
            created_at=t.created_at,
            submitted_at=t.submitted_at,
            reviewed_at=t.reviewed_at
        )
        for t in tasks
    ]
    
    return TaskListResponse(tasks=task_responses, total=len(task_responses))


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_improvement_task(
    task_id: str,
    engine: QualityWorkflowEngine = Depends(get_workflow_engine)
) -> TaskResponse:
    """
    获取单个改进任务
    
    - **task_id**: 任务ID
    """
    task = await engine.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        id=task.id,
        annotation_id=task.annotation_id,
        project_id=task.project_id,
        issues=[i.dict() for i in task.issues],
        assignee_id=task.assignee_id,
        status=task.status,
        priority=task.priority,
        improved_data=task.improved_data,
        original_data=task.original_data,
        reviewer_id=task.reviewer_id,
        review_comments=task.review_comments,
        due_date=task.due_date,
        created_at=task.created_at,
        submitted_at=task.submitted_at,
        reviewed_at=task.reviewed_at
    )


@router.post("/tasks/{task_id}/start", response_model=TaskResponse)
async def start_improvement(
    task_id: str,
    request: StartRequest,
    engine: QualityWorkflowEngine = Depends(get_workflow_engine)
) -> TaskResponse:
    """
    开始改进
    
    - **task_id**: 任务ID
    - **user_id**: 用户ID
    """
    task = await engine.start_improvement(task_id, request.user_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        id=task.id,
        annotation_id=task.annotation_id,
        project_id=task.project_id,
        issues=[i.dict() for i in task.issues],
        assignee_id=task.assignee_id,
        status=task.status,
        priority=task.priority,
        improved_data=task.improved_data,
        original_data=task.original_data,
        reviewer_id=task.reviewer_id,
        review_comments=task.review_comments,
        due_date=task.due_date,
        created_at=task.created_at,
        submitted_at=task.submitted_at,
        reviewed_at=task.reviewed_at
    )


@router.post("/tasks/{task_id}/submit", response_model=TaskResponse)
async def submit_improvement(
    task_id: str,
    request: SubmitRequest,
    engine: QualityWorkflowEngine = Depends(get_workflow_engine)
) -> TaskResponse:
    """
    提交改进
    
    - **task_id**: 任务ID
    - **improved_data**: 改进后的数据
    """
    task = await engine.submit_improvement(
        task_id,
        request.improved_data,
        request.user_id
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        id=task.id,
        annotation_id=task.annotation_id,
        project_id=task.project_id,
        issues=[i.dict() for i in task.issues],
        assignee_id=task.assignee_id,
        status=task.status,
        priority=task.priority,
        improved_data=task.improved_data,
        original_data=task.original_data,
        reviewer_id=task.reviewer_id,
        review_comments=task.review_comments,
        due_date=task.due_date,
        created_at=task.created_at,
        submitted_at=task.submitted_at,
        reviewed_at=task.reviewed_at
    )


@router.post("/tasks/{task_id}/review", response_model=TaskResponse)
async def review_improvement(
    task_id: str,
    request: ReviewRequest,
    engine: QualityWorkflowEngine = Depends(get_workflow_engine)
) -> TaskResponse:
    """
    审核改进
    
    - **task_id**: 任务ID
    - **reviewer_id**: 审核人ID
    - **approved**: 是否通过
    - **comments**: 审核意见
    """
    task = await engine.review_improvement(
        task_id,
        request.reviewer_id,
        request.approved,
        request.comments
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        id=task.id,
        annotation_id=task.annotation_id,
        project_id=task.project_id,
        issues=[i.dict() for i in task.issues],
        assignee_id=task.assignee_id,
        status=task.status,
        priority=task.priority,
        improved_data=task.improved_data,
        original_data=task.original_data,
        reviewer_id=task.reviewer_id,
        review_comments=task.review_comments,
        due_date=task.due_date,
        created_at=task.created_at,
        submitted_at=task.submitted_at,
        reviewed_at=task.reviewed_at
    )


@router.post("/tasks/{task_id}/reopen", response_model=TaskResponse)
async def reopen_task(
    task_id: str,
    request: ReopenRequest,
    engine: QualityWorkflowEngine = Depends(get_workflow_engine)
) -> TaskResponse:
    """
    重新打开任务
    
    - **task_id**: 任务ID
    - **user_id**: 用户ID
    - **comments**: 备注
    """
    task = await engine.reopen_task(task_id, request.user_id, request.comments)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        id=task.id,
        annotation_id=task.annotation_id,
        project_id=task.project_id,
        issues=[i.dict() for i in task.issues],
        assignee_id=task.assignee_id,
        status=task.status,
        priority=task.priority,
        improved_data=task.improved_data,
        original_data=task.original_data,
        reviewer_id=task.reviewer_id,
        review_comments=task.review_comments,
        due_date=task.due_date,
        created_at=task.created_at,
        submitted_at=task.submitted_at,
        reviewed_at=task.reviewed_at
    )


@router.get("/tasks/{task_id}/history", response_model=List[HistoryResponse])
async def get_task_history(
    task_id: str,
    engine: QualityWorkflowEngine = Depends(get_workflow_engine)
) -> List[HistoryResponse]:
    """
    获取任务历史
    
    - **task_id**: 任务ID
    """
    history = await engine.get_task_history(task_id)
    
    return [
        HistoryResponse(
            id=h.id,
            task_id=h.task_id,
            action=h.action,
            from_status=h.from_status,
            to_status=h.to_status,
            actor_id=h.actor_id,
            comments=h.comments,
            created_at=h.created_at
        )
        for h in history
    ]


@router.get("/effect-report/{project_id}", response_model=EffectReportResponse)
async def get_improvement_effect_report(
    project_id: str,
    period: str = Query("month", description="时间周期 (day/week/month)"),
    engine: QualityWorkflowEngine = Depends(get_workflow_engine)
) -> EffectReportResponse:
    """
    获取改进效果报告
    
    - **project_id**: 项目ID
    - **period**: 时间周期
    """
    report = await engine.evaluate_improvement_effect(project_id, period)
    
    return EffectReportResponse(
        project_id=report.project_id,
        period=report.period,
        total_tasks=report.total_tasks,
        completed_tasks=report.completed_tasks,
        average_improvement=report.average_improvement,
        by_severity=report.by_severity,
        generated_at=report.generated_at
    )
