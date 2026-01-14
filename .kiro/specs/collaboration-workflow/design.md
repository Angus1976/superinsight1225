# Design Document: Collaboration Workflow (协作与审核流程)

## Overview

本设计文档描述 Collaboration Workflow 模块的架构设计，该模块扩展现有 `src/quality/` 和 `src/label_studio/`，实现完整的协作与审核流程，包括任务分配、多人协作、审核流程、冲突解决、质量控制和众包标注。

设计原则：
- **智能分配**：基于技能和负载的智能任务分配
- **实时协作**：支持多人同时协作和实时同步
- **质量优先**：多级审核和质量控制确保标注质量
- **开放众包**：支持非敏感数据的众包标注

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        CollabUI[Collaboration UI]
        ReviewUI[Review UI]
        QualityDashboard[Quality Dashboard]
        CrowdsourcePortal[Crowdsource Portal]
        CrowdsourceAdmin[Crowdsource Admin]
    end

    subgraph API["API 层"]
        TaskRouter[/api/v1/tasks]
        ReviewRouter[/api/v1/reviews]
        QualityRouter[/api/v1/quality]
        CrowdsourceRouter[/api/v1/crowdsource]
    end
    
    subgraph Core["核心层"]
        TaskDispatcher[Task Dispatcher]
        CollabEngine[Collaboration Engine]
        ReviewFlowManager[Review Flow Manager]
        ConflictResolver[Conflict Resolver]
        QualityController[Quality Controller]
        NotificationService[Notification Service]
        CrowdsourceManager[Crowdsource Manager]
        CrowdsourceBilling[Crowdsource Billing]
    end
    
    subgraph External["外部服务"]
        LabelStudio[Label Studio]
        WebSocket[WebSocket Server]
        EmailService[Email Service]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        Cache[(Redis)]
        MQ[(Message Queue)]
    end
    
    CollabUI --> TaskRouter
    ReviewUI --> ReviewRouter
    QualityDashboard --> QualityRouter
    CrowdsourcePortal --> CrowdsourceRouter
    CrowdsourceAdmin --> CrowdsourceRouter
    
    TaskRouter --> TaskDispatcher
    TaskRouter --> CollabEngine
    ReviewRouter --> ReviewFlowManager
    ReviewRouter --> ConflictResolver
    QualityRouter --> QualityController
    CrowdsourceRouter --> CrowdsourceManager
    CrowdsourceRouter --> CrowdsourceBilling
    
    TaskDispatcher --> NotificationService
    ReviewFlowManager --> NotificationService
    ConflictResolver --> NotificationService
    QualityController --> NotificationService
    
    CollabEngine --> WebSocket
    CollabEngine --> LabelStudio
    
    NotificationService --> EmailService
    NotificationService --> MQ
    
    TaskDispatcher --> DB
    ReviewFlowManager --> DB
    QualityController --> DB
    CrowdsourceManager --> DB
    CrowdsourceBilling --> DB
    CollabEngine --> Cache
```

## Components and Interfaces

### 1. Task Dispatcher (任务分配器)

**文件**: `src/collaboration/task_dispatcher.py`

**职责**: 智能分配标注任务给合适的标注员

```python
class TaskDispatcher:
    """任务分配器"""
    
    def __init__(self, db: AsyncSession, notification_service: NotificationService):
        self.db = db
        self.notification_service = notification_service
    
    async def assign_task(
        self,
        task_id: str,
        mode: AssignmentMode = AssignmentMode.AUTO,
        annotator_id: str = None
    ) -> TaskAssignment:
        """分配任务"""
        if mode == AssignmentMode.MANUAL:
            return await self._manual_assign(task_id, annotator_id)
        else:
            return await self._auto_assign(task_id)
    
    async def _auto_assign(self, task_id: str) -> TaskAssignment:
        """自动分配"""
        task = await self.get_task(task_id)
        
        # 获取匹配技能的标注员
        candidates = await self._get_skill_matched_annotators(task.required_skills)
        
        # 按工作负载排序
        candidates = await self._sort_by_workload(candidates)
        
        # 选择最佳候选人
        annotator = candidates[0] if candidates else None
        
        assignment = await self._create_assignment(task_id, annotator.id)
        await self.notification_service.notify_task_assigned(annotator.id, task_id)
        
        return assignment
    
    async def _get_skill_matched_annotators(self, required_skills: List[str]) -> List[Annotator]:
        """获取技能匹配的标注员"""
        pass
    
    async def _sort_by_workload(self, annotators: List[Annotator]) -> List[Annotator]:
        """按工作负载排序"""
        pass
    
    async def set_priority(self, task_id: str, priority: int) -> Task:
        """设置任务优先级"""
        pass
    
    async def set_deadline(self, task_id: str, deadline: datetime) -> Task:
        """设置截止时间"""
        pass
    
    async def get_pending_tasks(self, annotator_id: str) -> List[Task]:
        """获取待处理任务"""
        pass

class AssignmentMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"

class TaskAssignment(BaseModel):
    task_id: str
    annotator_id: str
    assigned_at: datetime
    priority: int
    deadline: Optional[datetime]
```

### 2. Collaboration Engine (协作引擎)

**文件**: `src/collaboration/collaboration_engine.py`

**职责**: 支持多人同时协作标注

```python
class CollaborationEngine:
    """协作引擎"""
    
    def __init__(self, db: AsyncSession, cache: Redis, ws_manager: WebSocketManager):
        self.db = db
        self.cache = cache
        self.ws_manager = ws_manager
    
    async def acquire_task_lock(self, task_id: str, annotator_id: str) -> bool:
        """获取任务锁，防止重复标注"""
        lock_key = f"task_lock:{task_id}"
        return await self.cache.set(lock_key, annotator_id, nx=True, ex=3600)
    
    async def release_task_lock(self, task_id: str, annotator_id: str) -> bool:
        """释放任务锁"""
        pass
    
    async def sync_progress(self, project_id: str, progress: ProgressUpdate) -> None:
        """同步标注进度"""
        await self.ws_manager.broadcast(
            f"project:{project_id}",
            {"type": "progress_update", "data": progress.dict()}
        )
    
    async def save_annotation_version(
        self,
        task_id: str,
        annotator_id: str,
        annotation: Dict
    ) -> AnnotationVersion:
        """保存标注版本"""
        version = AnnotationVersion(
            task_id=task_id,
            annotator_id=annotator_id,
            annotation=annotation,
            version=await self._get_next_version(task_id)
        )
        await self.db.add(version)
        return version
    
    async def get_annotation_versions(self, task_id: str) -> List[AnnotationVersion]:
        """获取所有标注版本"""
        pass
    
    async def get_online_members(self, project_id: str) -> List[OnlineMember]:
        """获取在线成员"""
        pass
    
    async def send_message(self, project_id: str, sender_id: str, message: str) -> ChatMessage:
        """发送消息"""
        pass

class AnnotationVersion(BaseModel):
    id: str
    task_id: str
    annotator_id: str
    annotation: Dict
    version: int
    created_at: datetime
```

### 3. Review Flow Manager (审核流管理器)

**文件**: `src/collaboration/review_flow_manager.py`

**职责**: 管理多级审核流程

```python
class ReviewFlowManager:
    """审核流管理器"""
    
    def __init__(self, db: AsyncSession, notification_service: NotificationService):
        self.db = db
        self.notification_service = notification_service
    
    async def configure_flow(self, project_id: str, config: ReviewFlowConfig) -> ReviewFlow:
        """配置审核流程"""
        pass
    
    async def submit_for_review(self, annotation_id: str) -> ReviewTask:
        """提交审核"""
        annotation = await self.get_annotation(annotation_id)
        flow = await self.get_flow(annotation.project_id)
        
        review_task = ReviewTask(
            annotation_id=annotation_id,
            current_level=1,
            max_level=flow.levels,
            status=ReviewStatus.PENDING
        )
        await self.db.add(review_task)
        return review_task
    
    async def approve(self, review_task_id: str, reviewer_id: str) -> ReviewResult:
        """审核通过"""
        task = await self.get_review_task(review_task_id)
        
        if task.current_level < task.max_level:
            # 进入下一级审核
            task.current_level += 1
            task.status = ReviewStatus.PENDING
        else:
            # 终审通过
            task.status = ReviewStatus.APPROVED
        
        await self._record_history(task, reviewer_id, "approve")
        return ReviewResult(task=task, action="approve")
    
    async def reject(self, review_task_id: str, reviewer_id: str, reason: str) -> ReviewResult:
        """审核驳回"""
        task = await self.get_review_task(review_task_id)
        task.status = ReviewStatus.REJECTED
        
        # 退回给原标注员
        annotation = await self.get_annotation(task.annotation_id)
        await self.notification_service.notify_rejection(
            annotation.annotator_id, task.annotation_id, reason
        )
        
        await self._record_history(task, reviewer_id, "reject", reason)
        return ReviewResult(task=task, action="reject")
    
    async def batch_approve(self, review_task_ids: List[str], reviewer_id: str) -> List[ReviewResult]:
        """批量审核"""
        pass
    
    async def get_review_history(self, annotation_id: str) -> List[ReviewHistory]:
        """获取审核历史"""
        pass

class ReviewFlowConfig(BaseModel):
    levels: int = 2  # 审核级数
    pass_threshold: float = 0.8  # 通过率阈值
    auto_approve: bool = False  # 是否自动通过

class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
```

### 4. Conflict Resolver (冲突解决器)

**文件**: `src/collaboration/conflict_resolver.py`

**职责**: 处理标注冲突和分歧

```python
class ConflictResolver:
    """冲突解决器"""
    
    def __init__(self, db: AsyncSession, notification_service: NotificationService):
        self.db = db
        self.notification_service = notification_service
    
    async def detect_conflicts(self, task_id: str) -> List[Conflict]:
        """检测标注冲突"""
        versions = await self.get_annotation_versions(task_id)
        conflicts = []
        
        for i, v1 in enumerate(versions):
            for v2 in versions[i+1:]:
                if self._has_conflict(v1.annotation, v2.annotation):
                    conflicts.append(Conflict(
                        task_id=task_id,
                        version1_id=v1.id,
                        version2_id=v2.id,
                        conflict_type=self._get_conflict_type(v1, v2)
                    ))
        
        if conflicts:
            await self._notify_conflicts(task_id, conflicts)
        
        return conflicts
    
    async def resolve_by_voting(self, conflict_id: str) -> ConflictResolution:
        """投票解决冲突"""
        conflict = await self.get_conflict(conflict_id)
        votes = await self.get_votes(conflict_id)
        
        # 统计投票
        vote_counts = Counter(v.choice for v in votes)
        winner = vote_counts.most_common(1)[0][0]
        
        resolution = ConflictResolution(
            conflict_id=conflict_id,
            method="voting",
            result=winner,
            vote_counts=dict(vote_counts)
        )
        
        await self._record_resolution(resolution)
        return resolution
    
    async def resolve_by_expert(self, conflict_id: str, expert_id: str, decision: Dict) -> ConflictResolution:
        """专家仲裁解决冲突"""
        resolution = ConflictResolution(
            conflict_id=conflict_id,
            method="expert",
            result=decision,
            expert_id=expert_id
        )
        
        await self._record_resolution(resolution)
        return resolution
    
    async def vote(self, conflict_id: str, voter_id: str, choice: str) -> Vote:
        """投票"""
        pass
    
    async def generate_conflict_report(self, project_id: str) -> ConflictReport:
        """生成冲突分析报告"""
        pass

class Conflict(BaseModel):
    id: str
    task_id: str
    version1_id: str
    version2_id: str
    conflict_type: str
    status: str = "unresolved"
    created_at: datetime

class ConflictResolution(BaseModel):
    conflict_id: str
    method: str  # voting/expert
    result: Dict
    vote_counts: Optional[Dict] = None
    expert_id: Optional[str] = None
    resolved_at: datetime
```

### 5. Quality Controller (质量控制器)

**文件**: `src/collaboration/quality_controller.py`

**职责**: 监控和保证标注质量

```python
class QualityController:
    """质量控制器"""
    
    def __init__(self, db: AsyncSession, notification_service: NotificationService):
        self.db = db
        self.notification_service = notification_service
    
    async def calculate_accuracy(self, annotator_id: str, project_id: str = None) -> float:
        """计算标注员准确率"""
        reviewed = await self.get_reviewed_annotations(annotator_id, project_id)
        if not reviewed:
            return 0.0
        
        approved = sum(1 for a in reviewed if a.status == "approved")
        return approved / len(reviewed)
    
    async def sample_for_review(self, project_id: str, sample_rate: float = 0.1) -> List[str]:
        """抽样检查"""
        annotations = await self.get_unreviewed_annotations(project_id)
        sample_size = int(len(annotations) * sample_rate)
        return random.sample([a.id for a in annotations], sample_size)
    
    async def run_gold_standard_test(self, annotator_id: str, gold_tasks: List[GoldTask]) -> GoldTestResult:
        """黄金标准测试"""
        results = []
        for task in gold_tasks:
            annotation = await self.get_annotation(task.task_id, annotator_id)
            is_correct = self._compare_with_gold(annotation, task.gold_answer)
            results.append(is_correct)
        
        accuracy = sum(results) / len(results)
        return GoldTestResult(annotator_id=annotator_id, accuracy=accuracy, details=results)
    
    async def check_quality_threshold(self, annotator_id: str, threshold: float = 0.8) -> bool:
        """检查质量阈值"""
        accuracy = await self.calculate_accuracy(annotator_id)
        
        if accuracy < threshold:
            await self.notification_service.send_quality_warning(annotator_id, accuracy, threshold)
            return False
        
        return True
    
    async def get_quality_ranking(self, project_id: str) -> List[QualityRanking]:
        """获取质量排名"""
        pass
    
    async def generate_quality_report(self, project_id: str) -> QualityReport:
        """生成质量趋势报告"""
        pass

class GoldTask(BaseModel):
    task_id: str
    gold_answer: Dict

class QualityRanking(BaseModel):
    annotator_id: str
    accuracy: float
    total_annotations: int
    rank: int
```

### 6. Crowdsource Manager (众包管理器)

**文件**: `src/collaboration/crowdsource_manager.py`

**职责**: 管理众包标注任务和标注员

```python
class CrowdsourceManager:
    """众包管理器"""
    
    def __init__(
        self,
        db: AsyncSession,
        sensitivity_filter: SensitivityFilter,
        platform_adapter: ThirdPartyPlatformAdapter
    ):
        self.db = db
        self.sensitivity_filter = sensitivity_filter
        self.platform_adapter = platform_adapter
    
    async def create_crowdsource_task(
        self,
        project_id: str,
        config: CrowdsourceTaskConfig
    ) -> CrowdsourceTask:
        """创建众包任务"""
        # 获取项目数据
        data = await self.get_project_data(project_id)
        
        # 过滤敏感数据
        filtered_data = await self.sensitivity_filter.filter(
            data, config.sensitivity_level
        )
        
        task = CrowdsourceTask(
            project_id=project_id,
            data_ids=[d.id for d in filtered_data],
            config=config,
            platform=config.platform,
            status="open"
        )
        
        # 如果使用第三方平台，同步任务
        if config.platform != "internal":
            await self.platform_adapter.sync_task(task)
        
        return task
    
    async def claim_task(self, task_id: str, annotator_id: str) -> TaskClaim:
        """领取任务"""
        pass
    
    async def submit_annotation(
        self,
        task_id: str,
        annotator_id: str,
        annotation: Dict
    ) -> CrowdsourceSubmission:
        """提交标注"""
        pass
    
    async def get_available_tasks(self, annotator_id: str) -> List[CrowdsourceTask]:
        """获取可领取任务"""
        pass

class CrowdsourceTaskConfig(BaseModel):
    sensitivity_level: int = 1  # 1=公开, 2=内部, 3=敏感
    max_annotators: int = 3  # 每个数据最多标注人数
    price_per_task: float = 0.1  # 单价
    quality_bonus_rate: float = 0.2  # 质量奖励系数
    platform: str = "internal"  # internal/mturk/scale_ai/custom

class SensitivityFilter:
    """敏感数据过滤器"""
    
    async def filter(self, data: List[DataItem], max_level: int) -> List[DataItem]:
        """过滤敏感数据"""
        return [d for d in data if d.sensitivity_level <= max_level]
```

### 7. Crowdsource Annotator Manager (众包标注员管理器)

**文件**: `src/collaboration/crowdsource_annotator_manager.py`

**职责**: 管理众包标注员的完整生命周期

```python
class CrowdsourceAnnotatorManager:
    """众包标注员管理器"""
    
    def __init__(self, db: AsyncSession, identity_verifier: IdentityVerifier):
        self.db = db
        self.identity_verifier = identity_verifier
    
    async def register(self, registration: AnnotatorRegistration) -> CrowdsourceAnnotator:
        """注册标注员"""
        annotator = CrowdsourceAnnotator(
            email=registration.email,
            name=registration.name,
            phone=registration.phone,
            status="pending_verification"
        )
        return annotator
    
    async def verify_identity(self, annotator_id: str, identity_doc: IdentityDocument) -> VerificationResult:
        """实名认证"""
        result = await self.identity_verifier.verify(identity_doc)
        if result.success:
            annotator = await self.get_annotator(annotator_id)
            annotator.identity_verified = True
            annotator.real_name = result.real_name
            annotator.status = "pending_test"
        return result
    
    async def conduct_ability_test(self, annotator_id: str, test_tasks: List[TestTask]) -> AbilityTestResult:
        """能力测试"""
        results = []
        for task in test_tasks:
            submission = await self.get_test_submission(annotator_id, task.id)
            score = self._evaluate_submission(submission, task.gold_answer)
            results.append(score)
        
        avg_score = sum(results) / len(results)
        passed = avg_score >= 0.8
        
        if passed:
            annotator = await self.get_annotator(annotator_id)
            annotator.status = "active"
            annotator.star_rating = self._calculate_initial_star(avg_score)
        
        return AbilityTestResult(annotator_id=annotator_id, score=avg_score, passed=passed)
    
    async def update_star_rating(self, annotator_id: str, new_rating: int) -> CrowdsourceAnnotator:
        """更新星级评定"""
        pass
    
    async def add_ability_tags(self, annotator_id: str, tags: List[str]) -> CrowdsourceAnnotator:
        """添加能力标签"""
        pass
    
    async def set_status(self, annotator_id: str, status: AnnotatorStatus) -> CrowdsourceAnnotator:
        """设置状态"""
        pass
    
    async def conduct_periodic_review(self, annotator_id: str) -> ReviewResult:
        """定期复评"""
        pass

class AnnotatorStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    PENDING_TEST = "pending_test"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"

class CrowdsourceAnnotator(BaseModel):
    id: str
    email: str
    name: str
    phone: str
    real_name: Optional[str] = None
    identity_verified: bool = False
    status: AnnotatorStatus
    star_rating: int = 0  # 1-5 星
    ability_tags: List[str] = []
    total_tasks: int = 0
    total_earnings: float = 0
```

### 8. Crowdsource Billing (众包计费)

**文件**: `src/collaboration/crowdsource_billing.py`

**职责**: 管理众包标注的计费和结算

```python
class CrowdsourceBilling:
    """众包计费"""
    
    def __init__(self, db: AsyncSession, quality_controller: QualityController):
        self.db = db
        self.quality_controller = quality_controller
    
    async def configure_pricing(self, project_id: str, pricing: PricingConfig) -> None:
        """配置计费"""
        pass
    
    async def calculate_earnings(
        self,
        annotator_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Earnings:
        """计算收益"""
        submissions = await self.get_approved_submissions(annotator_id, period_start, period_end)
        annotator = await self.get_annotator(annotator_id)
        
        base_amount = sum(s.price for s in submissions)
        
        # 质量系数调整
        quality_score = await self.quality_controller.calculate_accuracy(annotator_id)
        quality_multiplier = self._get_quality_multiplier(quality_score)
        
        # 星级系数调整
        star_multiplier = self._get_star_multiplier(annotator.star_rating)
        
        total_amount = base_amount * quality_multiplier * star_multiplier
        
        return Earnings(
            annotator_id=annotator_id,
            base_amount=base_amount,
            quality_multiplier=quality_multiplier,
            star_multiplier=star_multiplier,
            total_amount=total_amount,
            task_count=len(submissions)
        )
    
    def _get_quality_multiplier(self, quality_score: float) -> float:
        """获取质量系数"""
        if quality_score >= 0.95:
            return 1.2
        elif quality_score >= 0.9:
            return 1.1
        elif quality_score >= 0.8:
            return 1.0
        elif quality_score >= 0.7:
            return 0.9
        else:
            return 0.8
    
    def _get_star_multiplier(self, star_rating: int) -> float:
        """获取星级系数"""
        return 1.0 + (star_rating - 3) * 0.1  # 3星=1.0, 5星=1.2, 1星=0.8
    
    async def generate_settlement_report(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> SettlementReport:
        """生成结算报表"""
        pass
    
    async def generate_invoice(self, annotator_id: str, period: str) -> Invoice:
        """生成发票"""
        pass
    
    async def process_withdrawal(self, annotator_id: str, amount: float, method: WithdrawalMethod) -> WithdrawalResult:
        """处理提现"""
        pass

class PricingConfig(BaseModel):
    base_price: float = 0.1
    task_type_prices: Dict[str, float] = {}
    quality_bonus_enabled: bool = True
    star_bonus_enabled: bool = True

class WithdrawalMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    ALIPAY = "alipay"
    WECHAT = "wechat"

class Earnings(BaseModel):
    annotator_id: str
    base_amount: float
    quality_multiplier: float
    star_multiplier: float
    total_amount: float
    task_count: int
    period_start: datetime
    period_end: datetime
```

### 9. Third Party Platform Adapter (第三方平台适配器)

**文件**: `src/collaboration/third_party_platform_adapter.py`

**职责**: 对接第三方标注平台

```python
class ThirdPartyPlatformAdapter:
    """第三方平台适配器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.platforms: Dict[str, PlatformConnector] = {}
    
    async def register_platform(self, config: PlatformConfig) -> PlatformInfo:
        """注册平台"""
        connector = self._create_connector(config)
        self.platforms[config.name] = connector
        
        # 保存配置到数据库
        await self._save_platform_config(config)
        
        return PlatformInfo(name=config.name, status="connected")
    
    def _create_connector(self, config: PlatformConfig) -> PlatformConnector:
        """创建连接器"""
        if config.platform_type == "mturk":
            return MTurkConnector(config)
        elif config.platform_type == "scale_ai":
            return ScaleAIConnector(config)
        else:
            return CustomRESTConnector(config)
    
    async def sync_task(self, task: CrowdsourceTask) -> SyncResult:
        """同步任务到第三方平台"""
        connector = self.platforms.get(task.platform)
        if not connector:
            raise PlatformNotConfiguredError(task.platform)
        
        return await connector.create_task(task)
    
    async def fetch_results(self, task_id: str) -> List[CrowdsourceSubmission]:
        """获取第三方平台结果"""
        pass
    
    async def get_platform_status(self, platform_name: str) -> PlatformStatus:
        """获取平台状态"""
        pass

class PlatformConfig(BaseModel):
    name: str
    platform_type: str  # mturk/scale_ai/custom
    api_key: str
    api_secret: Optional[str] = None
    endpoint: Optional[str] = None
    extra_config: Dict[str, Any] = {}

class PlatformConnector(ABC):
    """平台连接器基类"""
    
    @abstractmethod
    async def create_task(self, task: CrowdsourceTask) -> SyncResult:
        pass
    
    @abstractmethod
    async def fetch_results(self, task_id: str) -> List[Dict]:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass

class MTurkConnector(PlatformConnector):
    """Amazon MTurk 连接器"""
    pass

class ScaleAIConnector(PlatformConnector):
    """Scale AI 连接器"""
    pass

class CustomRESTConnector(PlatformConnector):
    """自定义 REST API 连接器"""
    pass
```

### 8. API Router (API 路由)

**文件**: `src/api/collaboration.py`

```python
router = APIRouter(prefix="/api/v1", tags=["Collaboration"])

# 任务分配
@router.post("/tasks/{task_id}/assign")
async def assign_task(task_id: str, request: AssignRequest) -> TaskAssignment:
    pass

@router.get("/tasks/pending")
async def get_pending_tasks(annotator_id: str = None) -> List[Task]:
    pass

@router.put("/tasks/{task_id}/priority")
async def set_task_priority(task_id: str, priority: int) -> Task:
    pass

# 协作
@router.post("/tasks/{task_id}/lock")
async def acquire_task_lock(task_id: str) -> LockResult:
    pass

@router.delete("/tasks/{task_id}/lock")
async def release_task_lock(task_id: str) -> None:
    pass

@router.get("/tasks/{task_id}/versions")
async def get_annotation_versions(task_id: str) -> List[AnnotationVersion]:
    pass

@router.get("/projects/{project_id}/online-members")
async def get_online_members(project_id: str) -> List[OnlineMember]:
    pass

# 审核
@router.post("/annotations/{annotation_id}/submit-review")
async def submit_for_review(annotation_id: str) -> ReviewTask:
    pass

@router.post("/reviews/{review_id}/approve")
async def approve_review(review_id: str) -> ReviewResult:
    pass

@router.post("/reviews/{review_id}/reject")
async def reject_review(review_id: str, request: RejectRequest) -> ReviewResult:
    pass

@router.post("/reviews/batch-approve")
async def batch_approve(request: BatchApproveRequest) -> List[ReviewResult]:
    pass

@router.get("/annotations/{annotation_id}/review-history")
async def get_review_history(annotation_id: str) -> List[ReviewHistory]:
    pass

# 冲突解决
@router.get("/tasks/{task_id}/conflicts")
async def detect_conflicts(task_id: str) -> List[Conflict]:
    pass

@router.post("/conflicts/{conflict_id}/vote")
async def vote_conflict(conflict_id: str, request: VoteRequest) -> Vote:
    pass

@router.post("/conflicts/{conflict_id}/resolve-expert")
async def resolve_by_expert(conflict_id: str, request: ExpertDecisionRequest) -> ConflictResolution:
    pass

# 质量控制
@router.get("/annotators/{annotator_id}/accuracy")
async def get_annotator_accuracy(annotator_id: str, project_id: str = None) -> float:
    pass

@router.get("/projects/{project_id}/quality-ranking")
async def get_quality_ranking(project_id: str) -> List[QualityRanking]:
    pass

@router.post("/projects/{project_id}/gold-test")
async def run_gold_test(project_id: str, request: GoldTestRequest) -> GoldTestResult:
    pass

# 众包
@router.post("/crowdsource/tasks")
async def create_crowdsource_task(request: CreateCrowdsourceTaskRequest) -> CrowdsourceTask:
    pass

@router.get("/crowdsource/tasks/available")
async def get_available_crowdsource_tasks() -> List[CrowdsourceTask]:
    pass

@router.post("/crowdsource/tasks/{task_id}/claim")
async def claim_crowdsource_task(task_id: str) -> TaskClaim:
    pass

@router.post("/crowdsource/annotators/register")
async def register_crowdsource_annotator(request: AnnotatorRegistration) -> CrowdsourceAnnotator:
    pass

@router.get("/crowdsource/annotators/{annotator_id}/earnings")
async def get_annotator_earnings(annotator_id: str, period: str = "month") -> Earnings:
    pass

@router.get("/crowdsource/settlement-report")
async def get_settlement_report(period_start: datetime, period_end: datetime) -> SettlementReport:
    pass
```

## Data Models

### 数据库模型

```python
class TaskAssignment(Base):
    """任务分配表"""
    __tablename__ = "task_assignments"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    task_id = Column(UUID, ForeignKey("tasks.id"), nullable=False)
    annotator_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    priority = Column(Integer, default=0)
    deadline = Column(DateTime, nullable=True)
    status = Column(String(20), default="assigned")
    assigned_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class AnnotationVersion(Base):
    """标注版本表"""
    __tablename__ = "annotation_versions"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    task_id = Column(UUID, ForeignKey("tasks.id"), nullable=False)
    annotator_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    annotation = Column(JSONB, nullable=False)
    version = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ReviewTask(Base):
    """审核任务表"""
    __tablename__ = "review_tasks"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    annotation_id = Column(UUID, ForeignKey("annotations.id"), nullable=False)
    current_level = Column(Integer, default=1)
    max_level = Column(Integer, default=2)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ReviewHistory(Base):
    """审核历史表"""
    __tablename__ = "review_history"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    review_task_id = Column(UUID, ForeignKey("review_tasks.id"), nullable=False)
    reviewer_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    action = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)
    level = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Conflict(Base):
    """冲突表"""
    __tablename__ = "conflicts"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    task_id = Column(UUID, ForeignKey("tasks.id"), nullable=False)
    version1_id = Column(UUID, ForeignKey("annotation_versions.id"), nullable=False)
    version2_id = Column(UUID, ForeignKey("annotation_versions.id"), nullable=False)
    conflict_type = Column(String(50), nullable=False)
    status = Column(String(20), default="unresolved")
    created_at = Column(DateTime, default=datetime.utcnow)

class ConflictResolution(Base):
    """冲突解决表"""
    __tablename__ = "conflict_resolutions"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    conflict_id = Column(UUID, ForeignKey("conflicts.id"), nullable=False)
    method = Column(String(20), nullable=False)
    result = Column(JSONB, nullable=False)
    vote_counts = Column(JSONB, nullable=True)
    expert_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, default=datetime.utcnow)

class CrowdsourceTask(Base):
    """众包任务表"""
    __tablename__ = "crowdsource_tasks"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    project_id = Column(UUID, ForeignKey("projects.id"), nullable=False)
    data_ids = Column(JSONB, nullable=False)
    config = Column(JSONB, nullable=False)
    status = Column(String(20), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)

class CrowdsourceAnnotator(Base):
    """众包标注员表"""
    __tablename__ = "crowdsource_annotators"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    email = Column(String(200), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    status = Column(String(20), default="pending_review")
    quality_score = Column(Float, default=0)
    total_earnings = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class CrowdsourceSubmission(Base):
    """众包提交表"""
    __tablename__ = "crowdsource_submissions"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    task_id = Column(UUID, ForeignKey("crowdsource_tasks.id"), nullable=False)
    annotator_id = Column(UUID, ForeignKey("crowdsource_annotators.id"), nullable=False)
    annotation = Column(JSONB, nullable=False)
    status = Column(String(20), default="pending")
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: 技能匹配任务分配

*For any* 自动分配的任务，分配的标注员应具备任务所需的技能。

**Validates: Requirements 1.1**

### Property 2: 工作负载均衡

*For any* 一组待分配任务，自动分配后各标注员的工作量差异应在合理范围内（标准差不超过平均值的 20%）。

**Validates: Requirements 1.3**

### Property 3: 任务重复标注防止

*For any* 已被锁定的任务，其他标注员不应能够获取该任务的锁。

**Validates: Requirements 2.3**

### Property 4: 标注版本保留

*For any* 多人标注的任务，所有标注版本应被完整保留，可追溯查询。

**Validates: Requirements 2.4**

### Property 5: 审核流程正确性

*For any* 完成的标注，应自动进入审核队列；审核驳回后应退回给原标注员。

**Validates: Requirements 3.3, 3.5**

### Property 6: 审核历史完整性

*For any* 审核操作，应记录完整的审核历史，包括审核员、操作类型、时间、原因。

**Validates: Requirements 3.6**

### Property 7: 冲突检测和解决

*For any* 存在分歧的多人标注，系统应检测到冲突；投票解决时应采用多数决定。

**Validates: Requirements 4.1, 4.2**

### Property 8: 质量评分准确性

*For any* 标注员的质量评分，应基于其已审核标注的通过率准确计算。

**Validates: Requirements 5.1, 5.6**

### Property 9: 质量阈值预警

*For any* 质量低于阈值的标注员，系统应发送预警通知。

**Validates: Requirements 5.4**

### Property 10: 敏感数据过滤

*For any* 众包任务，应自动过滤敏感级别高于配置阈值的数据，确保敏感数据不暴露给众包标注员。

**Validates: Requirements 8.2, 8.3**

### Property 11: 众包计费准确性

*For any* 众包标注员的收益计算，应基于已审核通过的任务数量和质量系数准确计算。

**Validates: Requirements 8.5, 8.6, 10.3, 10.4**

## Error Handling

### 错误分类

| 错误类型 | 错误码 | 处理策略 |
|---------|--------|---------|
| 任务已锁定 | COLLAB_TASK_LOCKED | 返回锁定信息 |
| 无匹配标注员 | COLLAB_NO_MATCHING_ANNOTATOR | 返回错误，建议手动分配 |
| 审核流程错误 | COLLAB_REVIEW_FLOW_ERROR | 返回错误详情 |
| 冲突未解决 | COLLAB_CONFLICT_UNRESOLVED | 返回冲突详情 |
| 质量不达标 | COLLAB_QUALITY_BELOW_THRESHOLD | 发送预警，暂停分配 |
| 敏感数据泄露 | COLLAB_SENSITIVE_DATA_LEAK | 阻止操作，记录日志 |
| 众包标注员未审核 | COLLAB_ANNOTATOR_NOT_APPROVED | 返回错误，提示等待审核 |

## Testing Strategy

### 单元测试

- 测试任务分配算法
- 测试任务锁机制
- 测试审核流程状态机
- 测试冲突检测算法
- 测试质量评分计算
- 测试敏感数据过滤
- 测试计费计算

### 属性测试

```python
from hypothesis import given, strategies as st

@given(st.lists(st.text(min_size=1), min_size=1), st.lists(st.text(min_size=1), min_size=1))
def test_skill_matching(task_skills: List[str], annotator_skills: List[str]):
    """Property 1: 技能匹配任务分配"""
    task = Task(required_skills=task_skills)
    annotator = Annotator(skills=annotator_skills)
    
    if set(task_skills).issubset(set(annotator_skills)):
        assert dispatcher.is_skill_matched(task, annotator) == True

@given(st.lists(st.integers(min_value=1, max_value=100), min_size=2))
def test_workload_balancing(task_counts: List[int]):
    """Property 2: 工作负载均衡"""
    # 分配后检查标准差
    mean = sum(task_counts) / len(task_counts)
    std = (sum((x - mean) ** 2 for x in task_counts) / len(task_counts)) ** 0.5
    assert std <= mean * 0.2

@given(st.floats(min_value=0, max_value=1), st.floats(min_value=0, max_value=1))
def test_quality_threshold_alerting(accuracy: float, threshold: float):
    """Property 9: 质量阈值预警"""
    result = quality_controller.check_quality_threshold(annotator_id, threshold)
    assert result == (accuracy >= threshold)
```

### 集成测试

- 测试完整的任务分配 → 标注 → 审核流程
- 测试多人协作场景
- 测试冲突检测和解决流程
- 测试众包标注完整流程
- 测试计费结算流程
