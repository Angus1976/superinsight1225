"""
Collaboration Workflow Schemas (协作与审核流程 Pydantic 模型)

Defines all Pydantic models for request/response validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


# ============== Enums ==============

class AssignmentMode(str, Enum):
    """任务分配模式"""
    AUTO = "auto"
    MANUAL = "manual"


class ReviewStatus(str, Enum):
    """审核状态"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ConflictStatus(str, Enum):
    """冲突状态"""
    UNRESOLVED = "unresolved"
    VOTING = "voting"
    RESOLVED = "resolved"


class AnnotatorStatus(str, Enum):
    """众包标注员状态"""
    PENDING_VERIFICATION = "pending_verification"
    PENDING_TEST = "pending_test"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


class WithdrawalMethod(str, Enum):
    """提现方式"""
    BANK_TRANSFER = "bank_transfer"
    ALIPAY = "alipay"
    WECHAT = "wechat"


class NotificationChannel(str, Enum):
    """通知渠道"""
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"


class PlatformType(str, Enum):
    """第三方平台类型"""
    MTURK = "mturk"
    SCALE_AI = "scale_ai"
    CUSTOM = "custom"


# ============== Task Assignment Schemas ==============

class TaskAssignmentCreate(BaseModel):
    """创建任务分配请求"""
    task_id: str
    mode: AssignmentMode = AssignmentMode.AUTO
    annotator_id: Optional[str] = None
    priority: int = 0
    deadline: Optional[datetime] = None


class TaskAssignmentResponse(BaseModel):
    """任务分配响应"""
    id: str
    task_id: str
    annotator_id: str
    priority: int
    deadline: Optional[datetime]
    status: str
    assigned_at: datetime

    class Config:
        from_attributes = True


class AssignRequest(BaseModel):
    """分配请求"""
    mode: AssignmentMode = AssignmentMode.AUTO
    annotator_id: Optional[str] = None
    priority: int = 0
    deadline: Optional[datetime] = None


# ============== Collaboration Schemas ==============

class LockResult(BaseModel):
    """锁定结果"""
    success: bool
    task_id: str
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    message: str = ""


class AnnotationVersionResponse(BaseModel):
    """标注版本响应"""
    id: str
    task_id: str
    annotator_id: str
    annotation: Dict[str, Any]
    version: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProgressUpdate(BaseModel):
    """进度更新"""
    project_id: str
    task_id: str
    annotator_id: str
    progress: float
    status: str


class OnlineMember(BaseModel):
    """在线成员"""
    user_id: str
    username: str
    status: str = "online"
    current_task_id: Optional[str] = None
    last_active: datetime


class ChatMessage(BaseModel):
    """聊天消息"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    sender_id: str
    sender_name: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============== Review Flow Schemas ==============

class ReviewFlowConfig(BaseModel):
    """审核流程配置"""
    levels: int = 2
    pass_threshold: float = 0.8
    auto_approve: bool = False


class ReviewTaskResponse(BaseModel):
    """审核任务响应"""
    id: str
    annotation_id: str
    current_level: int
    max_level: int
    status: ReviewStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewResult(BaseModel):
    """审核结果"""
    task_id: str
    action: str
    status: ReviewStatus
    level: int
    reviewer_id: str
    reason: Optional[str] = None
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


class RejectRequest(BaseModel):
    """驳回请求"""
    reason: str


class BatchApproveRequest(BaseModel):
    """批量审核请求"""
    review_task_ids: List[str]


class ReviewHistoryResponse(BaseModel):
    """审核历史响应"""
    id: str
    review_task_id: str
    reviewer_id: str
    action: str
    reason: Optional[str]
    level: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Conflict Resolution Schemas ==============

class ConflictResponse(BaseModel):
    """冲突响应"""
    id: str
    task_id: str
    version1_id: str
    version2_id: str
    conflict_type: str
    status: ConflictStatus
    created_at: datetime

    class Config:
        from_attributes = True


class VoteRequest(BaseModel):
    """投票请求"""
    choice: str


class Vote(BaseModel):
    """投票"""
    conflict_id: str
    voter_id: str
    choice: str
    voted_at: datetime = Field(default_factory=datetime.utcnow)


class ExpertDecisionRequest(BaseModel):
    """专家决策请求"""
    decision: Dict[str, Any]


class ConflictResolutionResponse(BaseModel):
    """冲突解决响应"""
    id: str
    conflict_id: str
    method: str
    result: Dict[str, Any]
    vote_counts: Optional[Dict[str, int]] = None
    expert_id: Optional[str] = None
    resolved_at: datetime

    class Config:
        from_attributes = True


class ConflictReport(BaseModel):
    """冲突分析报告"""
    project_id: str
    total_conflicts: int
    resolved_conflicts: int
    unresolved_conflicts: int
    resolution_methods: Dict[str, int]
    conflict_types: Dict[str, int]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============== Quality Control Schemas ==============

class GoldTask(BaseModel):
    """黄金标准任务"""
    task_id: str
    gold_answer: Dict[str, Any]


class GoldTestRequest(BaseModel):
    """黄金测试请求"""
    annotator_id: str
    gold_tasks: List[GoldTask]


class GoldTestResult(BaseModel):
    """黄金测试结果"""
    annotator_id: str
    accuracy: float
    passed: bool
    details: List[bool]
    tested_at: datetime = Field(default_factory=datetime.utcnow)


class QualityRanking(BaseModel):
    """质量排名"""
    annotator_id: str
    annotator_name: str
    accuracy: float
    total_annotations: int
    approved_annotations: int
    rank: int


class QualityReport(BaseModel):
    """质量报告"""
    project_id: str
    period_start: datetime
    period_end: datetime
    overall_accuracy: float
    annotator_rankings: List[QualityRanking]
    trend_data: List[Dict[str, Any]]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============== Notification Schemas ==============

class NotificationPreference(BaseModel):
    """通知偏好"""
    user_id: str
    channels: List[NotificationChannel] = [NotificationChannel.IN_APP]
    task_assigned: bool = True
    review_completed: bool = True
    deadline_reminder: bool = True
    quality_warning: bool = True


class Notification(BaseModel):
    """通知"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    channel: NotificationChannel
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============== Crowdsource Schemas ==============

class CrowdsourceTaskConfig(BaseModel):
    """众包任务配置"""
    sensitivity_level: int = 1  # 1=公开, 2=内部, 3=敏感
    max_annotators: int = 3
    price_per_task: float = 0.1
    quality_bonus_rate: float = 0.2
    platform: str = "internal"


class CreateCrowdsourceTaskRequest(BaseModel):
    """创建众包任务请求"""
    project_id: str
    config: CrowdsourceTaskConfig


class CrowdsourceTaskResponse(BaseModel):
    """众包任务响应"""
    id: str
    project_id: str
    data_ids: List[str]
    config: CrowdsourceTaskConfig
    platform: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TaskClaim(BaseModel):
    """任务领取"""
    task_id: str
    annotator_id: str
    claimed_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


class CrowdsourceSubmissionResponse(BaseModel):
    """众包提交响应"""
    id: str
    task_id: str
    annotator_id: str
    annotation: Dict[str, Any]
    status: str
    price: float
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Crowdsource Annotator Schemas ==============

class AnnotatorRegistration(BaseModel):
    """标注员注册"""
    email: str
    name: str
    phone: str
    password: str


class IdentityDocument(BaseModel):
    """身份证件"""
    doc_type: str  # id_card, passport
    doc_number: str
    doc_image_url: str


class VerificationResult(BaseModel):
    """验证结果"""
    success: bool
    real_name: Optional[str] = None
    message: str


class TestTask(BaseModel):
    """测试任务"""
    id: str
    data: Dict[str, Any]
    gold_answer: Dict[str, Any]


class AbilityTestResult(BaseModel):
    """能力测试结果"""
    annotator_id: str
    score: float
    passed: bool
    details: List[Dict[str, Any]] = []
    tested_at: datetime = Field(default_factory=datetime.utcnow)


class CrowdsourceAnnotatorResponse(BaseModel):
    """众包标注员响应"""
    id: str
    email: str
    name: str
    phone: str
    real_name: Optional[str] = None
    identity_verified: bool
    status: AnnotatorStatus
    star_rating: int
    ability_tags: List[str]
    total_tasks: int
    total_earnings: float
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Billing Schemas ==============

class PricingConfig(BaseModel):
    """计费配置"""
    base_price: float = 0.1
    task_type_prices: Dict[str, float] = {}
    quality_bonus_enabled: bool = True
    star_bonus_enabled: bool = True


class Earnings(BaseModel):
    """收益"""
    annotator_id: str
    base_amount: float
    quality_multiplier: float
    star_multiplier: float
    total_amount: float
    task_count: int
    period_start: datetime
    period_end: datetime


class SettlementReport(BaseModel):
    """结算报表"""
    period_start: datetime
    period_end: datetime
    total_amount: float
    annotator_count: int
    task_count: int
    details: List[Earnings]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class Invoice(BaseModel):
    """发票"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    annotator_id: str
    period: str
    amount: float
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WithdrawalRequest(BaseModel):
    """提现请求"""
    amount: float
    method: WithdrawalMethod
    account_info: Dict[str, str]


class WithdrawalResult(BaseModel):
    """提现结果"""
    success: bool
    transaction_id: Optional[str] = None
    amount: float
    method: WithdrawalMethod
    message: str
    processed_at: datetime = Field(default_factory=datetime.utcnow)


# ============== Third Party Platform Schemas ==============

class PlatformConfig(BaseModel):
    """平台配置"""
    name: str
    platform_type: PlatformType
    api_key: str
    api_secret: Optional[str] = None
    endpoint: Optional[str] = None
    extra_config: Dict[str, Any] = {}


class PlatformInfo(BaseModel):
    """平台信息"""
    name: str
    platform_type: PlatformType
    status: str
    connected_at: Optional[datetime] = None


class SyncResult(BaseModel):
    """同步结果"""
    success: bool
    platform: str
    task_id: str
    external_task_id: Optional[str] = None
    message: str
    synced_at: datetime = Field(default_factory=datetime.utcnow)


class PlatformStatus(BaseModel):
    """平台状态"""
    name: str
    connected: bool
    last_sync: Optional[datetime] = None
    pending_tasks: int = 0
    completed_tasks: int = 0
