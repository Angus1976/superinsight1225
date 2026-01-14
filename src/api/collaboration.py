"""
Collaboration API Routes (协作与审核流程 API)

RESTful API endpoints for collaboration workflow management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

# Import collaboration modules
from src.collaboration.task_dispatcher import TaskDispatcher
from src.collaboration.collaboration_engine import CollaborationEngine
from src.collaboration.review_flow_manager import ReviewFlowManager
from src.collaboration.conflict_resolver import ConflictResolver
from src.collaboration.quality_controller import QualityController
from src.collaboration.notification_service import NotificationService
from src.collaboration.crowdsource_manager import CrowdsourceManager
from src.collaboration.crowdsource_annotator_manager import CrowdsourceAnnotatorManager, AnnotatorStatus
from src.collaboration.crowdsource_billing import CrowdsourceBilling, WithdrawalMethod
from src.collaboration.third_party_platform_adapter import ThirdPartyPlatformAdapter

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


# ============== Request/Response Schemas ==============

class TaskAssignmentRequest(BaseModel):
    task_id: str
    annotator_id: Optional[str] = None
    auto_assign: bool = True
    priority: int = Field(default=1, ge=1, le=5)


class TaskAssignmentResponse(BaseModel):
    task_id: str
    annotator_id: str
    status: str
    assigned_at: datetime


class TaskLockRequest(BaseModel):
    task_id: str
    user_id: str


class TaskLockResponse(BaseModel):
    task_id: str
    locked_by: str
    locked_at: datetime
    success: bool


class AnnotationVersionRequest(BaseModel):
    task_id: str
    user_id: str
    annotation: Dict[str, Any]


class ReviewSubmitRequest(BaseModel):
    annotation_id: str
    annotator_id: str


class ReviewActionRequest(BaseModel):
    review_task_id: str
    reviewer_id: str
    comment: Optional[str] = None
    reason: Optional[str] = None


class ConflictResolveRequest(BaseModel):
    conflict_id: str
    resolution_method: str = "voting"  # voting, expert
    expert_id: Optional[str] = None
    expert_decision: Optional[Dict[str, Any]] = None


class QualityThresholdRequest(BaseModel):
    annotator_id: str
    threshold: float = 0.8


class CrowdsourceTaskRequest(BaseModel):
    project_id: str
    sensitivity_level: int = Field(default=1, ge=1, le=3)
    price_per_task: float = 0.1
    max_annotators: int = 3


class CrowdsourceClaimRequest(BaseModel):
    task_id: str
    annotator_id: str
    duration_hours: int = 2


class CrowdsourceSubmitRequest(BaseModel):
    task_id: str
    annotator_id: str
    annotation: Dict[str, Any]


class AnnotatorRegisterRequest(BaseModel):
    email: str
    name: str
    phone: Optional[str] = None
    password: str


class IdentityVerifyRequest(BaseModel):
    annotator_id: str
    doc_type: str
    doc_number: str


class WithdrawalRequest(BaseModel):
    annotator_id: str
    amount: float
    method: str  # bank_transfer, alipay, wechat
    account_info: Optional[Dict[str, str]] = None


class PlatformRegisterRequest(BaseModel):
    name: str
    platform_type: str  # mturk, scale_ai, custom
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    endpoint: Optional[str] = None


# ============== Service Instances ==============

# Initialize services (in production, use dependency injection)
notification_service = NotificationService()
task_dispatcher = TaskDispatcher(notification_service=notification_service)
collaboration_engine = CollaborationEngine(notification_service=notification_service)
review_flow_manager = ReviewFlowManager(notification_service=notification_service)
conflict_resolver = ConflictResolver(notification_service=notification_service)
quality_controller = QualityController(notification_service=notification_service)
crowdsource_manager = CrowdsourceManager()
annotator_manager = CrowdsourceAnnotatorManager()
crowdsource_billing = CrowdsourceBilling(
    crowdsource_manager=crowdsource_manager,
    annotator_manager=annotator_manager,
    quality_controller=quality_controller
)
platform_adapter = ThirdPartyPlatformAdapter()


# ============== Task Assignment APIs ==============

@router.post("/tasks/assign", response_model=TaskAssignmentResponse)
async def assign_task(request: TaskAssignmentRequest):
    """分配任务给标注员"""
    try:
        result = await task_dispatcher.assign_task(
            task_id=request.task_id,
            annotator_id=request.annotator_id,
            auto_assign=request.auto_assign
        )
        return TaskAssignmentResponse(
            task_id=result["task_id"],
            annotator_id=result["annotator_id"],
            status=result["status"],
            assigned_at=result.get("assigned_at", datetime.utcnow())
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tasks/{task_id}/priority")
async def set_task_priority(task_id: str, priority: int = Query(ge=1, le=5)):
    """设置任务优先级"""
    result = await task_dispatcher.set_priority(task_id, priority)
    return result


@router.post("/tasks/{task_id}/deadline")
async def set_task_deadline(task_id: str, deadline: datetime):
    """设置任务截止时间"""
    result = await task_dispatcher.set_deadline(task_id, deadline)
    return result


@router.get("/tasks/{task_id}/assignment")
async def get_task_assignment(task_id: str):
    """获取任务分配信息"""
    result = await task_dispatcher.get_assignment(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task assignment not found")
    return result


# ============== Collaboration APIs ==============

@router.post("/tasks/lock", response_model=TaskLockResponse)
async def lock_task(request: TaskLockRequest):
    """锁定任务"""
    result = await collaboration_engine.lock_task(request.task_id, request.user_id)
    return TaskLockResponse(
        task_id=request.task_id,
        locked_by=request.user_id,
        locked_at=datetime.utcnow(),
        success=result
    )


@router.post("/tasks/unlock")
async def unlock_task(request: TaskLockRequest):
    """解锁任务"""
    result = await collaboration_engine.unlock_task(request.task_id, request.user_id)
    return {"success": result}


@router.post("/annotations/version")
async def save_annotation_version(request: AnnotationVersionRequest):
    """保存标注版本"""
    result = await collaboration_engine.save_annotation_version(
        task_id=request.task_id,
        user_id=request.user_id,
        annotation=request.annotation
    )
    return result


@router.get("/annotations/{task_id}/versions")
async def get_annotation_versions(task_id: str):
    """获取标注版本历史"""
    versions = await collaboration_engine.get_annotation_versions(task_id)
    return {"versions": versions}


# ============== Review APIs ==============

@router.post("/reviews/submit")
async def submit_for_review(request: ReviewSubmitRequest):
    """提交审核"""
    result = await review_flow_manager.submit_for_review(
        annotation_id=request.annotation_id,
        annotator_id=request.annotator_id
    )
    return result


@router.post("/reviews/approve")
async def approve_review(request: ReviewActionRequest):
    """审核通过"""
    result = await review_flow_manager.approve(
        review_task_id=request.review_task_id,
        reviewer_id=request.reviewer_id,
        comment=request.comment
    )
    return result


@router.post("/reviews/reject")
async def reject_review(request: ReviewActionRequest):
    """审核驳回"""
    if not request.reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    result = await review_flow_manager.reject(
        review_task_id=request.review_task_id,
        reviewer_id=request.reviewer_id,
        reason=request.reason
    )
    return result


@router.get("/reviews/{annotation_id}/history")
async def get_review_history(annotation_id: str):
    """获取审核历史"""
    history = await review_flow_manager.get_review_history(annotation_id)
    return {"history": history}


# ============== Conflict APIs ==============

@router.get("/conflicts/{task_id}")
async def detect_conflicts(task_id: str):
    """检测冲突"""
    conflicts = await conflict_resolver.detect_conflicts(task_id)
    return {"conflicts": conflicts}


@router.post("/conflicts/resolve")
async def resolve_conflict(request: ConflictResolveRequest):
    """解决冲突"""
    if request.resolution_method == "voting":
        result = await conflict_resolver.resolve_by_voting(request.conflict_id)
    elif request.resolution_method == "expert":
        if not request.expert_id or not request.expert_decision:
            raise HTTPException(status_code=400, detail="Expert ID and decision required")
        result = await conflict_resolver.resolve_by_expert(
            conflict_id=request.conflict_id,
            expert_id=request.expert_id,
            decision=request.expert_decision
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid resolution method")
    return result


@router.get("/conflicts/{task_id}/report")
async def get_conflict_report(task_id: str):
    """获取冲突报告"""
    report = await conflict_resolver.generate_conflict_report(task_id)
    return report


# ============== Quality APIs ==============

@router.get("/quality/{annotator_id}/accuracy")
async def get_annotator_accuracy(annotator_id: str, project_id: Optional[str] = None):
    """获取标注员准确率"""
    accuracy = await quality_controller.calculate_accuracy(annotator_id, project_id)
    return {"annotator_id": annotator_id, "accuracy": accuracy}


@router.post("/quality/threshold/check")
async def check_quality_threshold(request: QualityThresholdRequest):
    """检查质量阈值"""
    passed = await quality_controller.check_quality_threshold(
        annotator_id=request.annotator_id,
        threshold=request.threshold
    )
    return {"annotator_id": request.annotator_id, "passed": passed}


@router.get("/quality/{project_id}/ranking")
async def get_quality_ranking(project_id: str):
    """获取质量排名"""
    ranking = await quality_controller.get_quality_ranking(project_id)
    return {"ranking": ranking}


@router.get("/quality/{project_id}/report")
async def get_quality_report(project_id: str):
    """获取质量报告"""
    report = await quality_controller.generate_quality_report(project_id)
    return report



# ============== Crowdsource Task APIs ==============

@router.post("/crowdsource/tasks")
async def create_crowdsource_task(request: CrowdsourceTaskRequest):
    """创建众包任务"""
    result = await crowdsource_manager.create_crowdsource_task(
        project_id=request.project_id,
        config={
            "sensitivity_level": request.sensitivity_level,
            "price_per_task": request.price_per_task,
            "max_annotators": request.max_annotators
        }
    )
    return result


@router.get("/crowdsource/tasks/{task_id}")
async def get_crowdsource_task(task_id: str):
    """获取众包任务"""
    task = await crowdsource_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/crowdsource/tasks/available")
async def get_available_tasks(annotator_id: str):
    """获取可领取任务"""
    tasks = await crowdsource_manager.get_available_tasks(annotator_id)
    return {"tasks": tasks}


@router.post("/crowdsource/tasks/claim")
async def claim_crowdsource_task(request: CrowdsourceClaimRequest):
    """领取众包任务"""
    try:
        result = await crowdsource_manager.claim_task(
            task_id=request.task_id,
            annotator_id=request.annotator_id,
            claim_duration_hours=request.duration_hours
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/crowdsource/tasks/submit")
async def submit_crowdsource_annotation(request: CrowdsourceSubmitRequest):
    """提交众包标注"""
    try:
        result = await crowdsource_manager.submit_annotation(
            task_id=request.task_id,
            annotator_id=request.annotator_id,
            annotation=request.annotation
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/crowdsource/submissions/{submission_id}/approve")
async def approve_crowdsource_submission(submission_id: str):
    """审核通过众包提交"""
    try:
        result = await crowdsource_manager.approve_submission(submission_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/crowdsource/submissions/{submission_id}/reject")
async def reject_crowdsource_submission(submission_id: str, reason: str):
    """驳回众包提交"""
    try:
        result = await crowdsource_manager.reject_submission(submission_id, reason)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============== Crowdsource Annotator APIs ==============

@router.post("/crowdsource/annotators/register")
async def register_annotator(request: AnnotatorRegisterRequest):
    """注册众包标注员"""
    try:
        result = await annotator_manager.register({
            "email": request.email,
            "name": request.name,
            "phone": request.phone,
            "password": request.password
        })
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/crowdsource/annotators/{annotator_id}")
async def get_annotator(annotator_id: str):
    """获取标注员信息"""
    annotator = await annotator_manager.get_annotator(annotator_id)
    if not annotator:
        raise HTTPException(status_code=404, detail="Annotator not found")
    return annotator


@router.post("/crowdsource/annotators/verify")
async def verify_annotator_identity(request: IdentityVerifyRequest):
    """实名认证"""
    try:
        result = await annotator_manager.verify_identity(
            annotator_id=request.annotator_id,
            identity_doc={
                "doc_type": request.doc_type,
                "doc_number": request.doc_number
            }
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/crowdsource/annotators/{annotator_id}/ability-test")
async def conduct_ability_test(annotator_id: str, test_tasks: List[Dict[str, Any]]):
    """能力测试"""
    try:
        result = await annotator_manager.conduct_ability_test(annotator_id, test_tasks)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/crowdsource/annotators/{annotator_id}/star-rating")
async def update_star_rating(annotator_id: str, rating: int = Query(ge=1, le=5)):
    """更新星级"""
    try:
        result = await annotator_manager.update_star_rating(annotator_id, rating)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/crowdsource/annotators/{annotator_id}/ability-tags")
async def add_ability_tags(annotator_id: str, tags: List[str]):
    """添加能力标签"""
    try:
        result = await annotator_manager.add_ability_tags(annotator_id, tags)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/crowdsource/annotators/{annotator_id}/status")
async def set_annotator_status(annotator_id: str, status: str):
    """设置标注员状态"""
    try:
        annotator_status = AnnotatorStatus(status)
        result = await annotator_manager.set_status(annotator_id, annotator_status)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============== Crowdsource Billing APIs ==============

@router.post("/crowdsource/billing/pricing")
async def configure_pricing(project_id: str, pricing: Dict[str, Any]):
    """配置计费"""
    result = await crowdsource_billing.configure_pricing(project_id, pricing)
    return result


@router.get("/crowdsource/billing/{annotator_id}/earnings")
async def get_annotator_earnings(
    annotator_id: str,
    period_start: datetime,
    period_end: datetime
):
    """获取标注员收益"""
    result = await crowdsource_billing.calculate_earnings(
        annotator_id=annotator_id,
        period_start=period_start,
        period_end=period_end
    )
    return result


@router.get("/crowdsource/billing/settlement-report")
async def get_settlement_report(period_start: datetime, period_end: datetime):
    """获取结算报表"""
    result = await crowdsource_billing.generate_settlement_report(
        period_start=period_start,
        period_end=period_end
    )
    return result


@router.post("/crowdsource/billing/{annotator_id}/invoice")
async def generate_invoice(annotator_id: str, period: str):
    """生成发票"""
    result = await crowdsource_billing.generate_invoice(annotator_id, period)
    return result


@router.post("/crowdsource/billing/withdrawal")
async def process_withdrawal(request: WithdrawalRequest):
    """处理提现"""
    try:
        method = WithdrawalMethod(request.method)
        result = await crowdsource_billing.process_withdrawal(
            annotator_id=request.annotator_id,
            amount=request.amount,
            method=method,
            account_info=request.account_info
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/crowdsource/billing/{annotator_id}/balance")
async def get_annotator_balance(annotator_id: str):
    """获取标注员余额"""
    balance = await crowdsource_billing.get_annotator_balance(annotator_id)
    return {"annotator_id": annotator_id, "balance": balance}


# ============== Third Party Platform APIs ==============

@router.post("/platforms/register")
async def register_platform(request: PlatformRegisterRequest):
    """注册第三方平台"""
    result = await platform_adapter.register_platform({
        "name": request.name,
        "platform_type": request.platform_type,
        "api_key": request.api_key,
        "api_secret": request.api_secret,
        "endpoint": request.endpoint
    })
    return result


@router.delete("/platforms/{platform_name}")
async def unregister_platform(platform_name: str):
    """注销第三方平台"""
    result = await platform_adapter.unregister_platform(platform_name)
    if not result:
        raise HTTPException(status_code=404, detail="Platform not found")
    return {"success": True}


@router.get("/platforms/{platform_name}")
async def get_platform(platform_name: str):
    """获取平台信息"""
    platform = await platform_adapter.get_platform(platform_name)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    return platform


@router.get("/platforms")
async def get_all_platforms():
    """获取所有平台"""
    platforms = await platform_adapter.get_all_platforms()
    return {"platforms": platforms}


@router.get("/platforms/{platform_name}/status")
async def get_platform_status(platform_name: str):
    """获取平台状态"""
    status = await platform_adapter.get_platform_status(platform_name)
    return status


@router.post("/platforms/{platform_name}/test")
async def test_platform_connection(platform_name: str):
    """测试平台连接"""
    result = await platform_adapter.test_connection(platform_name)
    return result


@router.post("/platforms/sync-task")
async def sync_task_to_platform(task: Dict[str, Any]):
    """同步任务到第三方平台"""
    result = await platform_adapter.sync_task(task)
    return result


@router.get("/platforms/{platform_name}/results/{task_id}")
async def fetch_platform_results(platform_name: str, task_id: str):
    """获取第三方平台结果"""
    results = await platform_adapter.fetch_results(task_id, platform_name)
    return {"results": results}
