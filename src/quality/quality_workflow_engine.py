"""
Quality Workflow Engine - 质量工作流引擎
管理质量改进流程
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class QualityIssue(BaseModel):
    """质量问题"""
    rule_id: str
    rule_name: str
    severity: str  # critical, high, medium, low
    message: str
    field: Optional[str] = None


class ImprovementTask(BaseModel):
    """改进任务"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    annotation_id: str
    project_id: str
    issues: List[QualityIssue] = Field(default_factory=list)
    assignee_id: str
    status: str = "pending"  # pending, in_progress, submitted, approved, rejected
    priority: int = 1  # 1=低, 2=中, 3=高
    improved_data: Optional[Dict[str, Any]] = None
    original_data: Optional[Dict[str, Any]] = None
    reviewer_id: Optional[str] = None
    review_comments: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None


class ImprovementHistory(BaseModel):
    """改进历史"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    action: str  # created, assigned, submitted, approved, rejected, reopened
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    actor_id: str
    comments: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowConfig(BaseModel):
    """工作流配置"""
    stages: List[str] = Field(default_factory=lambda: ["identify", "assign", "improve", "review", "verify"])
    auto_create_task: bool = True
    auto_assign_rules: Dict[str, Any] = Field(default_factory=dict)
    escalation_rules: Dict[str, Any] = Field(default_factory=dict)


class QualityWorkflow(BaseModel):
    """质量工作流"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    stages: List[str] = Field(default_factory=lambda: ["identify", "assign", "improve", "review", "verify"])
    auto_create_task: bool = True
    auto_assign_rules: Dict[str, Any] = Field(default_factory=dict)
    escalation_rules: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ImprovementEffectReport(BaseModel):
    """改进效果报告"""
    project_id: str
    period: str
    total_tasks: int = 0
    completed_tasks: int = 0
    average_improvement: float = 0.0
    by_severity: Dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class QualityWorkflowEngine:
    """质量工作流引擎"""
    
    # 严重程度权重
    SEVERITY_WEIGHTS = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1
    }
    
    def __init__(self, notification_service: Optional[Any] = None):
        """
        初始化工作流引擎
        
        Args:
            notification_service: 通知服务 (可选)
        """
        self.notification_service = notification_service
        
        # 内存存储
        self._workflows: Dict[str, QualityWorkflow] = {}
        self._tasks: Dict[str, ImprovementTask] = {}
        self._history: Dict[str, List[ImprovementHistory]] = {}
        self._annotations: Dict[str, Dict[str, Any]] = {}
    
    def add_annotation(
        self,
        annotation_id: str,
        project_id: str,
        annotator_id: str,
        data: Dict[str, Any]
    ) -> None:
        """添加标注数据 (用于测试)"""
        self._annotations[annotation_id] = {
            "id": annotation_id,
            "project_id": project_id,
            "annotator_id": annotator_id,
            "data": data
        }
    
    async def get_annotation(self, annotation_id: str) -> Optional[Dict[str, Any]]:
        """获取标注数据"""
        return self._annotations.get(annotation_id)
    
    async def configure_workflow(
        self,
        project_id: str,
        config: WorkflowConfig
    ) -> QualityWorkflow:
        """
        配置质量改进流程
        
        Args:
            project_id: 项目ID
            config: 工作流配置
            
        Returns:
            工作流对象
        """
        workflow = QualityWorkflow(
            project_id=project_id,
            stages=config.stages,
            auto_create_task=config.auto_create_task,
            auto_assign_rules=config.auto_assign_rules,
            escalation_rules=config.escalation_rules
        )
        
        self._workflows[project_id] = workflow
        
        return workflow
    
    async def get_workflow(self, project_id: str) -> Optional[QualityWorkflow]:
        """获取工作流配置"""
        return self._workflows.get(project_id)
    
    async def create_improvement_task(
        self,
        annotation_id: str,
        issues: List[QualityIssue],
        assignee_id: Optional[str] = None,
        project_id: Optional[str] = None,
        due_date: Optional[datetime] = None
    ) -> ImprovementTask:
        """
        创建改进任务
        
        Args:
            annotation_id: 标注ID
            issues: 质量问题列表
            assignee_id: 负责人ID (可选)
            project_id: 项目ID (可选)
            due_date: 截止日期 (可选)
            
        Returns:
            改进任务
        """
        annotation = await self.get_annotation(annotation_id)
        
        # 如果没有指定负责人，分配给原标注员
        if not assignee_id:
            if annotation:
                assignee_id = annotation.get("annotator_id", "unknown")
            else:
                assignee_id = "unknown"
        
        # 获取项目ID
        if not project_id:
            if annotation:
                project_id = annotation.get("project_id", "default")
            else:
                project_id = "default"
        
        # 计算优先级
        priority = self._calculate_priority(issues)
        
        # 设置默认截止日期
        if not due_date:
            if priority == 3:
                due_date = datetime.utcnow() + timedelta(days=1)
            elif priority == 2:
                due_date = datetime.utcnow() + timedelta(days=3)
            else:
                due_date = datetime.utcnow() + timedelta(days=7)
        
        task = ImprovementTask(
            annotation_id=annotation_id,
            project_id=project_id,
            issues=issues,
            assignee_id=assignee_id,
            priority=priority,
            original_data=annotation.get("data") if annotation else None,
            due_date=due_date
        )
        
        self._tasks[task.id] = task
        
        # 记录历史
        await self._record_history(task, "created", assignee_id)
        
        # 发送通知
        if self.notification_service:
            try:
                await self.notification_service.send(
                    user_id=assignee_id,
                    channel="in_app",
                    title="新的改进任务",
                    message=f"您有一个新的质量改进任务，优先级: {priority}"
                )
            except Exception:
                pass
        
        return task
    
    def _calculate_priority(self, issues: List[QualityIssue]) -> int:
        """
        计算任务优先级
        
        Args:
            issues: 问题列表
            
        Returns:
            优先级 (1=低, 2=中, 3=高)
        """
        if not issues:
            return 1
        
        total_weight = sum(
            self.SEVERITY_WEIGHTS.get(i.severity, 1)
            for i in issues
        )
        
        if total_weight >= 10:
            return 3  # 高优先级
        elif total_weight >= 5:
            return 2  # 中优先级
        else:
            return 1  # 低优先级
    
    async def get_task(self, task_id: str) -> Optional[ImprovementTask]:
        """获取改进任务"""
        return self._tasks.get(task_id)
    
    async def start_improvement(
        self,
        task_id: str,
        user_id: str
    ) -> Optional[ImprovementTask]:
        """
        开始改进
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            更新后的任务
        """
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        old_status = task.status
        task.status = "in_progress"
        
        await self._record_history(task, "started", user_id, old_status, task.status)
        
        return task
    
    async def submit_improvement(
        self,
        task_id: str,
        improved_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Optional[ImprovementTask]:
        """
        提交改进
        
        Args:
            task_id: 任务ID
            improved_data: 改进后的数据
            user_id: 用户ID (可选)
            
        Returns:
            更新后的任务
        """
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        old_status = task.status
        task.improved_data = improved_data
        task.status = "submitted"
        task.submitted_at = datetime.utcnow()
        
        await self._record_history(
            task, "submitted",
            user_id or task.assignee_id,
            old_status, task.status
        )
        
        return task
    
    async def review_improvement(
        self,
        task_id: str,
        reviewer_id: str,
        approved: bool,
        comments: Optional[str] = None
    ) -> Optional[ImprovementTask]:
        """
        审核改进
        
        Args:
            task_id: 任务ID
            reviewer_id: 审核人ID
            approved: 是否通过
            comments: 审核意见
            
        Returns:
            更新后的任务
        """
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        old_status = task.status
        
        if approved:
            task.status = "approved"
            # 应用改进
            await self._apply_improvement(task)
        else:
            task.status = "rejected"
        
        task.reviewer_id = reviewer_id
        task.review_comments = comments
        task.reviewed_at = datetime.utcnow()
        
        # 记录历史
        action = "approved" if approved else "rejected"
        await self._record_history(task, action, reviewer_id, old_status, task.status, comments)
        
        # 发送通知
        if self.notification_service:
            try:
                await self.notification_service.send(
                    user_id=task.assignee_id,
                    channel="in_app",
                    title=f"改进任务{'已通过' if approved else '被驳回'}",
                    message=comments or ""
                )
            except Exception:
                pass
        
        return task
    
    async def _apply_improvement(self, task: ImprovementTask) -> None:
        """应用改进到原标注"""
        if task.improved_data and task.annotation_id in self._annotations:
            self._annotations[task.annotation_id]["data"] = task.improved_data
    
    async def reopen_task(
        self,
        task_id: str,
        user_id: str,
        comments: Optional[str] = None
    ) -> Optional[ImprovementTask]:
        """
        重新打开任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            comments: 备注
            
        Returns:
            更新后的任务
        """
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        old_status = task.status
        task.status = "pending"
        task.improved_data = None
        task.reviewer_id = None
        task.review_comments = None
        task.submitted_at = None
        task.reviewed_at = None
        
        await self._record_history(task, "reopened", user_id, old_status, task.status, comments)
        
        return task
    
    async def _record_history(
        self,
        task: ImprovementTask,
        action: str,
        actor_id: str,
        from_status: Optional[str] = None,
        to_status: Optional[str] = None,
        comments: Optional[str] = None
    ) -> ImprovementHistory:
        """记录历史"""
        history = ImprovementHistory(
            task_id=task.id,
            action=action,
            from_status=from_status,
            to_status=to_status or task.status,
            actor_id=actor_id,
            comments=comments
        )
        
        if task.id not in self._history:
            self._history[task.id] = []
        self._history[task.id].append(history)
        
        return history
    
    async def get_task_history(self, task_id: str) -> List[ImprovementHistory]:
        """获取任务历史"""
        return self._history.get(task_id, [])
    
    async def get_improvement_tasks(
        self,
        project_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[ImprovementTask]:
        """
        获取改进任务列表
        
        Args:
            project_id: 项目ID (可选)
            assignee_id: 负责人ID (可选)
            status: 状态 (可选)
            
        Returns:
            任务列表
        """
        tasks = list(self._tasks.values())
        
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        if assignee_id:
            tasks = [t for t in tasks if t.assignee_id == assignee_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return tasks
    
    async def evaluate_improvement_effect(
        self,
        project_id: str,
        period: str = "month"
    ) -> ImprovementEffectReport:
        """
        评估改进效果
        
        Args:
            project_id: 项目ID
            period: 时间周期
            
        Returns:
            改进效果报告
        """
        # 计算时间范围
        end_date = datetime.utcnow()
        if period == "day":
            start_date = end_date - timedelta(days=1)
        elif period == "week":
            start_date = end_date - timedelta(weeks=1)
        else:  # month
            start_date = end_date - timedelta(days=30)
        
        # 获取时间范围内的任务
        tasks = [
            t for t in self._tasks.values()
            if t.project_id == project_id
            and t.created_at >= start_date
        ]
        
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == "approved")
        
        # 按严重程度统计
        by_severity: Dict[str, int] = {}
        for task in tasks:
            for issue in task.issues:
                severity = issue.severity
                by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # 计算平均改进率 (简化)
        average_improvement = completed_tasks / total_tasks if total_tasks > 0 else 0
        
        return ImprovementEffectReport(
            project_id=project_id,
            period=period,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            average_improvement=average_improvement,
            by_severity=by_severity
        )


# 独立函数 (用于属性测试)
def calculate_priority(issues: List[Dict[str, Any]]) -> int:
    """
    计算任务优先级 (独立函数)
    
    Args:
        issues: 问题列表，每项包含 severity
        
    Returns:
        优先级 (1=低, 2=中, 3=高)
    """
    if not issues:
        return 1
    
    severity_weights = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1
    }
    
    total_weight = sum(
        severity_weights.get(i.get("severity", "low"), 1)
        for i in issues
    )
    
    if total_weight >= 10:
        return 3  # 高优先级
    elif total_weight >= 5:
        return 2  # 中优先级
    else:
        return 1  # 低优先级
