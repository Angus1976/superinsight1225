# Design Document: AI Annotation (AI 标注)

## Overview

本设计文档描述 AI Annotation 模块的架构设计，该模块扩展现有 `src/ai/` 和 `src/label_studio/`，实现事前预标/事中覆盖/事后验证的完整 AI 标注流程，支持第三方工具对接和人机协作。

设计原则：
- **扩展现有**：基于现有 AI 模块和 Label Studio 集成扩展
- **方法可插拔**：支持多种 AI 标注方法和第三方工具切换
- **人机协作**：清晰的角色分工和审核流程
- **质量优先**：多维验证确保标注质量

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        AnnotationUI[Annotation UI]
        ReviewUI[Review UI]
        PluginConfigUI[Plugin Config UI]
        DashboardUI[Dashboard UI]
    end
    
    subgraph API["API 层"]
        AnnotationRouter[/api/v1/annotation]
        TaskAPI[Task API]
        ReviewAPI[Review API]
        CollabAPI[Collaboration API]
        PluginAPI[Plugin API]
    end
    
    subgraph Core["核心层"]
        PreEngine[Pre-Annotation Engine]
        MidEngine[Mid-Coverage Engine]
        PostEngine[Post-Validation Engine]
        MethodSwitcher[Method Switcher]
        CollabManager[Collaboration Manager]
        ReviewFlow[Review Flow Engine]
        PluginManager[Plugin Manager]
        ThirdPartyAdapter[Third Party Adapter]
    end
    
    subgraph AI["AI 服务层"]
        LLMService[LLM Service]
        MLBackend[ML Backend]
        Argilla[Argilla]
        Ragas[Ragas]
        DeepEval[DeepEval]
    end
    
    subgraph ThirdParty["第三方工具"]
        Prodigy[Prodigy]
        Doccano[Doccano]
        CVAT[CVAT]
        Labelbox[Labelbox]
        ScaleAI[Scale AI]
    end
    
    subgraph External["外部服务"]
        LabelStudio[Label Studio]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        Cache[(Redis)]
    end
    
    AnnotationUI --> AnnotationRouter
    ReviewUI --> AnnotationRouter
    PluginConfigUI --> AnnotationRouter
    DashboardUI --> AnnotationRouter
    
    AnnotationRouter --> TaskAPI
    AnnotationRouter --> ReviewAPI
    AnnotationRouter --> CollabAPI
    AnnotationRouter --> PluginAPI
    
    TaskAPI --> PreEngine
    TaskAPI --> MidEngine
    TaskAPI --> PostEngine
    TaskAPI --> MethodSwitcher
    
    ReviewAPI --> ReviewFlow
    CollabAPI --> CollabManager
    PluginAPI --> PluginManager
    
    MethodSwitcher --> LLMService
    MethodSwitcher --> MLBackend
    MethodSwitcher --> Argilla
    MethodSwitcher --> ThirdPartyAdapter
    
    ThirdPartyAdapter --> Prodigy
    ThirdPartyAdapter --> Doccano
    ThirdPartyAdapter --> CVAT
    ThirdPartyAdapter --> Labelbox
    ThirdPartyAdapter --> ScaleAI
    
    PostEngine --> Ragas
    PostEngine --> DeepEval
    
    PreEngine --> LabelStudio
    MidEngine --> LabelStudio
    
    PluginManager --> DB
    CollabManager --> DB
    ReviewFlow --> DB
    PreEngine --> Cache
```


## Components and Interfaces

### 1. Pre-Annotation Engine (事前预标引擎)

**文件**: `src/ai/pre_annotation.py`

**职责**: 使用 LLM 和样本学习进行批量预标注

```python
class PreAnnotationEngine:
    """事前预标注引擎"""
    
    def __init__(self, llm_switcher: LLMSwitcher, method_switcher: MethodSwitcher):
        self.llm = llm_switcher
        self.method = method_switcher
    
    async def pre_annotate(
        self,
        task_ids: List[str],
        annotation_type: AnnotationType,
        config: PreAnnotationConfig
    ) -> PreAnnotationResult:
        """批量预标注"""
        pass
    
    async def pre_annotate_with_samples(
        self,
        task_ids: List[str],
        samples: List[AnnotationSample],
        config: PreAnnotationConfig
    ) -> PreAnnotationResult:
        """基于样本的预标注"""
        pass
    
    def calculate_confidence(self, prediction: Dict) -> float:
        """计算置信度"""
        pass
    
    def mark_for_review(self, result: AnnotationResult, threshold: float) -> bool:
        """标记需要人工审核"""
        pass

class AnnotationType(str, Enum):
    TEXT_CLASSIFICATION = "text_classification"
    NER = "ner"
    SENTIMENT = "sentiment"
    RELATION_EXTRACTION = "relation_extraction"

class PreAnnotationConfig(BaseModel):
    annotation_type: AnnotationType
    confidence_threshold: float = 0.7
    batch_size: int = 100
    max_items: int = 1000
    use_samples: bool = False
```

### 2. Mid-Coverage Engine (事中覆盖引擎)

**文件**: `src/ai/mid_coverage.py`

**职责**: 基于人类样本进行批量覆盖标注

```python
class MidCoverageEngine:
    """事中覆盖引擎"""
    
    async def analyze_patterns(self, annotations: List[Annotation]) -> List[AnnotationPattern]:
        """分析标注模式"""
        pass
    
    async def find_similar_tasks(
        self,
        pattern: AnnotationPattern,
        similarity_threshold: float = 0.85
    ) -> List[Task]:
        """查找相似任务"""
        pass
    
    async def auto_cover(
        self,
        pattern: AnnotationPattern,
        tasks: List[Task]
    ) -> CoverageResult:
        """自动覆盖标注"""
        pass
    
    async def notify_for_review(self, coverage_result: CoverageResult) -> None:
        """通知审核"""
        pass

class AnnotationPattern(BaseModel):
    pattern_id: str
    source_annotations: List[str]
    pattern_features: Dict[str, Any]
    confidence: float

class CoverageResult(BaseModel):
    covered_tasks: List[str]
    coverage_count: int
    average_similarity: float
    needs_review: bool
```

### 3. Post-Validation Engine (事后验证引擎)

**文件**: `src/ai/post_validation.py`

**职责**: 使用 Ragas/DeepEval 进行多维验证

```python
class PostValidationEngine:
    """事后验证引擎"""
    
    def __init__(self):
        self.ragas_evaluator = RagasEvaluator()
        self.deepeval_evaluator = DeepEvalEvaluator()
    
    async def validate(
        self,
        annotations: List[Annotation],
        config: ValidationConfig
    ) -> ValidationReport:
        """执行验证"""
        pass
    
    async def validate_accuracy(self, annotations: List[Annotation]) -> float:
        """验证准确率"""
        pass
    
    async def validate_consistency(self, annotations: List[Annotation]) -> float:
        """验证一致性"""
        pass
    
    async def validate_completeness(self, annotations: List[Annotation]) -> float:
        """验证完整性"""
        pass
    
    async def generate_report(self, results: Dict[str, float]) -> ValidationReport:
        """生成验证报告"""
        pass

class ValidationConfig(BaseModel):
    dimensions: List[str] = ["accuracy", "recall", "consistency", "completeness"]
    use_ragas: bool = True
    use_deepeval: bool = True
    custom_rules: List[ValidationRule] = []

class ValidationReport(BaseModel):
    overall_score: float
    dimension_scores: Dict[str, float]
    issues: List[ValidationIssue]
    recommendations: List[str]
```

### 4. Method Switcher (方法切换器)

**文件**: `src/ai/annotation_switcher.py`

**职责**: 支持多种 AI 标注方法切换

```python
class AnnotationMethodSwitcher:
    """AI 标注方法切换器"""
    
    def __init__(self):
        self.methods: Dict[str, AnnotationMethod] = {}
        self.default_method: str = "custom_llm"
    
    def register_method(self, name: str, method: AnnotationMethod) -> None:
        """注册方法"""
        pass
    
    async def annotate(
        self,
        tasks: List[Task],
        method: str = None
    ) -> List[AnnotationResult]:
        """执行标注"""
        pass
    
    def switch_method(self, method: str) -> None:
        """切换默认方法"""
        pass
    
    def get_method_stats(self) -> Dict[str, MethodStats]:
        """获取方法统计"""
        pass

class AnnotationMethod(ABC):
    @abstractmethod
    async def annotate(self, task: Task) -> AnnotationResult:
        pass
    
    @abstractmethod
    def get_info(self) -> MethodInfo:
        pass

class MLBackendMethod(AnnotationMethod):
    """Label Studio ML Backend 方法"""
    pass

class ArgillaMethod(AnnotationMethod):
    """Argilla 方法"""
    pass

class CustomLLMMethod(AnnotationMethod):
    """自定义 LLM 方法"""
    pass
```

### 5. Collaboration Manager (人机协作管理器)

**文件**: `src/ai/collaboration_manager.py`

**职责**: 管理标注团队的角色分工

```python
class CollaborationManager:
    """人机协作管理器"""
    
    async def assign_task(
        self,
        task: Task,
        role: UserRole = None,
        user_id: str = None
    ) -> TaskAssignment:
        """分配任务"""
        pass
    
    async def get_available_tasks(self, user_id: str) -> List[Task]:
        """获取可用任务"""
        pass
    
    async def complete_task(self, task_id: str, user_id: str) -> None:
        """完成任务"""
        pass
    
    async def get_workload_stats(self, user_id: str = None) -> WorkloadStats:
        """获取工作量统计"""
        pass
    
    async def reassign_task(self, task_id: str, new_user_id: str) -> TaskAssignment:
        """重新分配任务"""
        pass

class UserRole(str, Enum):
    ANNOTATOR = "annotator"      # 标注员
    EXPERT = "expert"            # 专家
    CONTRACTOR = "contractor"    # 外包
    REVIEWER = "reviewer"        # 审核员

class TaskAssignment(BaseModel):
    task_id: str
    user_id: str
    role: UserRole
    assigned_at: datetime
    priority: int = 0
    deadline: Optional[datetime] = None
```

### 6. Review Flow Engine (审核流引擎)

**文件**: `src/ai/review_flow.py`

**职责**: 管理标注审核流程

```python
class ReviewFlowEngine:
    """审核流引擎"""
    
    async def submit_for_review(self, annotation_id: str) -> ReviewTask:
        """提交审核"""
        pass
    
    async def assign_reviewer(self, review_task_id: str, reviewer_id: str = None) -> ReviewTask:
        """分配审核员"""
        pass
    
    async def approve(self, review_task_id: str, reviewer_id: str) -> ReviewResult:
        """审核通过"""
        pass
    
    async def reject(
        self,
        review_task_id: str,
        reviewer_id: str,
        reason: str
    ) -> ReviewResult:
        """审核驳回"""
        pass
    
    async def request_modification(
        self,
        review_task_id: str,
        reviewer_id: str,
        comments: str
    ) -> ReviewResult:
        """请求修改"""
        pass
    
    async def get_review_history(self, annotation_id: str) -> List[ReviewRecord]:
        """获取审核历史"""
        pass
    
    async def batch_approve(self, review_task_ids: List[str], reviewer_id: str) -> List[ReviewResult]:
        """批量审核"""
        pass

class ReviewTask(BaseModel):
    id: str
    annotation_id: str
    status: ReviewStatus
    reviewer_id: Optional[str]
    created_at: datetime
    
class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFICATION_REQUESTED = "modification_requested"
```

### 7. API Router (API 路由)

**文件**: `src/api/annotation.py`

```python
router = APIRouter(prefix="/api/v1/annotation", tags=["Annotation"])

# 预标注
@router.post("/pre-annotate")
async def pre_annotate(request: PreAnnotateRequest) -> PreAnnotationResult:
    pass

# 事中覆盖
@router.post("/auto-cover")
async def auto_cover(request: AutoCoverRequest) -> CoverageResult:
    pass

# 事后验证
@router.post("/validate")
async def validate(request: ValidateRequest) -> ValidationReport:
    pass

# 方法管理
@router.get("/methods")
async def list_methods() -> List[MethodInfo]:
    pass

@router.put("/methods/default")
async def set_default_method(method: str) -> None:
    pass

# 任务分配
@router.post("/tasks/{task_id}/assign")
async def assign_task(task_id: str, request: AssignRequest) -> TaskAssignment:
    pass

@router.get("/tasks/available")
async def get_available_tasks() -> List[Task]:
    pass

# 审核流程
@router.post("/review/submit")
async def submit_review(request: SubmitReviewRequest) -> ReviewTask:
    pass

@router.post("/review/{review_id}/approve")
async def approve_review(review_id: str) -> ReviewResult:
    pass

@router.post("/review/{review_id}/reject")
async def reject_review(review_id: str, request: RejectRequest) -> ReviewResult:
    pass

@router.get("/review/history/{annotation_id}")
async def get_review_history(annotation_id: str) -> List[ReviewRecord]:
    pass
```

## Data Models

### 数据库模型

```python
class PreAnnotationJob(Base):
    """预标注任务表"""
    __tablename__ = "pre_annotation_jobs"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    project_id = Column(UUID, ForeignKey("projects.id"), nullable=False)
    annotation_type = Column(String(50), nullable=False)
    config = Column(JSONB, nullable=False)
    status = Column(String(20), default="pending")
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class AnnotationResult(Base):
    """标注结果表"""
    __tablename__ = "annotation_results"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    task_id = Column(UUID, ForeignKey("tasks.id"), nullable=False)
    annotation_data = Column(JSONB, nullable=False)
    confidence = Column(Float, default=0)
    method_used = Column(String(50), nullable=False)
    is_auto = Column(Boolean, default=False)
    needs_review = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ReviewRecord(Base):
    """审核记录表"""
    __tablename__ = "review_records"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    annotation_id = Column(UUID, ForeignKey("annotation_results.id"), nullable=False)
    reviewer_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    action = Column(String(20), nullable=False)  # approve/reject/modify
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: 置信度处理

*For any* 预标注结果，都应包含置信度分数，且置信度低于阈值的结果应被标记为需要人工审核。

**Validates: Requirements 1.3, 1.5**

### Property 2: 方法路由正确性

*For any* 配置的默认方法和调用时指定的方法，Method Switcher 应正确路由到对应的标注方法，且指定方法优先于默认方法。

**Validates: Requirements 4.2, 4.3**

### Property 3: 自动覆盖记录

*For any* 自动覆盖的标注，系统应记录覆盖来源和相似度，便于后续审核追溯。

**Validates: Requirements 2.4**

### Property 4: 任务分配正确性

*For any* 任务分配，应根据用户角色权限分配合适的任务，且标注完成后应自动分配给审核员。

**Validates: Requirements 5.2, 5.4**

### Property 5: 审核驳回退回

*For any* 审核驳回操作，任务应退回给原标注员，并附带驳回原因。

**Validates: Requirements 6.4**

### Property 6: 审核历史完整性

*For any* 标注的审核操作，系统应记录完整的审核历史，包括操作类型、操作人、时间、备注。

**Validates: Requirements 6.5**

### Property 7: 验证维度覆盖

*For any* 事后验证，应覆盖配置的所有验证维度（准确率、召回率、一致性、完整性）。

**Validates: Requirements 3.2**

## Error Handling

| 错误类型 | 错误码 | 处理策略 |
|---------|--------|---------|
| 预标注失败 | ANN_PRE_ANNOTATION_ERROR | 记录错误，标记任务失败 |
| 方法不可用 | ANN_METHOD_UNAVAILABLE | 回退到默认方法 |
| 验证失败 | ANN_VALIDATION_ERROR | 生成问题报告 |
| 任务分配失败 | ANN_ASSIGNMENT_ERROR | 返回错误，建议手动分配 |
| 审核流程错误 | ANN_REVIEW_ERROR | 返回错误详情 |

## Testing Strategy

### 单元测试
- 测试预标注逻辑
- 测试置信度计算
- 测试方法路由
- 测试任务分配逻辑
- 测试审核流程

### 属性测试
```python
@given(st.floats(min_value=0, max_value=1))
def test_confidence_threshold_marking(confidence: float):
    """Property 1: 置信度处理"""
    threshold = 0.7
    result = AnnotationResult(confidence=confidence)
    needs_review = pre_engine.mark_for_review(result, threshold)
    assert needs_review == (confidence < threshold)
```

### 集成测试
- 测试完整的预标注 → 审核流程
- 测试人机协作场景
- 测试 Label Studio 集成


## Components and Interfaces

### 1. Pre-Annotation Engine (事前预标引擎)

**文件**: `src/ai/pre_annotation.py`

**职责**: 使用 LLM 和样本学习进行批量预标注

```python
class PreAnnotationEngine:
    """事前预标注引擎"""
    
    def __init__(self, llm_switcher: LLMSwitcher, method_switcher: MethodSwitcher):
        self.llm = llm_switcher
        self.method_switcher = method_switcher
    
    async def pre_annotate(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
        samples: List[AnnotatedSample] = None,
        confidence_threshold: float = 0.7
    ) -> List[PreAnnotationResult]:
        """批量预标注"""
        pass
    
    async def pre_annotate_with_samples(
        self,
        tasks: List[AnnotationTask],
        samples: List[AnnotatedSample]
    ) -> List[PreAnnotationResult]:
        """基于样本学习的预标注"""
        pass
    
    def calculate_confidence(self, result: Dict) -> float:
        """计算置信度"""
        pass
    
    def mark_for_review(self, results: List[PreAnnotationResult], threshold: float) -> List[PreAnnotationResult]:
        """标记需要人工审核的结果"""
        pass

class PreAnnotationResult(BaseModel):
    task_id: str
    annotation: Dict
    confidence: float
    needs_review: bool
    method_used: str
    processing_time_ms: float
```

### 2. Mid-Coverage Engine (事中覆盖引擎)

**文件**: `src/ai/mid_coverage.py`

**职责**: 基于人类样本进行批量覆盖标注

```python
class MidCoverageEngine:
    """事中覆盖引擎"""
    
    async def analyze_patterns(self, annotated_samples: List[AnnotatedSample]) -> List[AnnotationPattern]:
        """分析标注模式"""
        pass
    
    async def find_similar_tasks(
        self,
        patterns: List[AnnotationPattern],
        unannotated_tasks: List[AnnotationTask],
        similarity_threshold: float = 0.85
    ) -> List[SimilarTaskMatch]:
        """查找相似任务"""
        pass
    
    async def auto_cover(
        self,
        matches: List[SimilarTaskMatch]
    ) -> List[CoverageResult]:
        """自动覆盖标注"""
        pass
    
    async def notify_annotator(self, annotator_id: str, coverage_results: List[CoverageResult]) -> None:
        """通知标注员审核"""
        pass

class CoverageResult(BaseModel):
    task_id: str
    source_sample_id: str
    similarity_score: float
    annotation: Dict
    auto_covered: bool
    reviewed: bool = False
```

### 3. Post-Validation Engine (事后验证引擎)

**文件**: `src/ai/post_validation.py`

**职责**: 使用 Ragas/DeepEval 进行多维验证

```python
class PostValidationEngine:
    """事后验证引擎"""
    
    def __init__(self):
        self.ragas_evaluator = RagasEvaluator()
        self.deepeval_evaluator = DeepEvalEvaluator()
    
    async def validate(
        self,
        annotations: List[Annotation],
        validation_config: ValidationConfig
    ) -> ValidationReport:
        """执行多维验证"""
        pass
    
    async def validate_accuracy(self, annotations: List[Annotation], ground_truth: List[Annotation]) -> float:
        """验证准确率"""
        pass
    
    async def validate_consistency(self, annotations: List[Annotation]) -> float:
        """验证一致性"""
        pass
    
    async def validate_completeness(self, annotations: List[Annotation], schema: AnnotationSchema) -> float:
        """验证完整性"""
        pass
    
    def generate_report(self, results: Dict) -> ValidationReport:
        """生成验证报告"""
        pass

class ValidationReport(BaseModel):
    accuracy: float
    recall: float
    consistency: float
    completeness: float
    issues: List[ValidationIssue]
    recommendations: List[str]
```

### 4. Third Party Adapter (第三方工具适配器)

**文件**: `src/ai/third_party_adapter.py`

**职责**: 对接第三方专业 AI 标注工具

```python
class ThirdPartyAnnotationAdapter:
    """第三方标注工具适配器"""
    
    def __init__(self, plugin_manager: AnnotationPluginManager):
        self.plugin_manager = plugin_manager
    
    async def annotate(
        self,
        tasks: List[AnnotationTask],
        tool_name: str,
        annotation_type: AnnotationType
    ) -> List[AnnotationResult]:
        """调用第三方工具标注"""
        plugin = self.plugin_manager.get_plugin(tool_name)
        if not plugin:
            raise PluginNotFoundError(tool_name)
        
        # 转换为工具特定格式
        native_tasks = plugin.to_native_format(tasks, annotation_type)
        
        # 调用工具
        native_results = await plugin.annotate(native_tasks)
        
        # 转换为 Label Studio 兼容格式
        return plugin.to_label_studio_format(native_results)
    
    async def fallback_to_builtin(self, tasks: List[AnnotationTask]) -> List[AnnotationResult]:
        """回退到内置方法"""
        pass

class AnnotationPluginInterface(ABC):
    """标注工具插件接口规范"""
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[AnnotationType]:
        """获取支持的标注类型"""
        pass
    
    @abstractmethod
    def to_native_format(self, tasks: List[AnnotationTask], annotation_type: AnnotationType) -> Dict:
        """转换为工具特定格式"""
        pass
    
    @abstractmethod
    async def annotate(self, native_tasks: Dict) -> Dict:
        """执行标注"""
        pass
    
    @abstractmethod
    def to_label_studio_format(self, native_results: Dict) -> List[AnnotationResult]:
        """转换为 Label Studio 格式"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass

class PluginInfo(BaseModel):
    name: str
    version: str
    description: str
    connection_type: str  # rest_api/grpc/webhook
    supported_annotation_types: List[AnnotationType]
    config_schema: Dict[str, Any]
```

### 5. Plugin Manager (插件管理器)

**文件**: `src/ai/annotation_plugin_manager.py`

**职责**: 管理第三方标注工具插件

```python
class AnnotationPluginManager:
    """标注工具插件管理器"""
    
    def __init__(self, db: AsyncSession, cache: Redis):
        self.db = db
        self.cache = cache
        self.plugins: Dict[str, AnnotationPluginInterface] = {}
    
    async def register_plugin(self, config: PluginConfig) -> PluginInfo:
        """注册插件"""
        pass
    
    async def unregister_plugin(self, name: str) -> None:
        """注销插件"""
        pass
    
    def get_plugin(self, name: str) -> Optional[AnnotationPluginInterface]:
        """获取插件"""
        pass
    
    async def list_plugins(self) -> List[PluginInfo]:
        """列出所有插件"""
        pass
    
    async def enable_plugin(self, name: str) -> None:
        """启用插件"""
        pass
    
    async def disable_plugin(self, name: str) -> None:
        """禁用插件"""
        pass
    
    async def set_priority(self, name: str, priority: int) -> None:
        """设置插件优先级"""
        pass
    
    async def get_best_plugin(self, annotation_type: AnnotationType) -> Optional[AnnotationPluginInterface]:
        """根据优先级获取最佳插件"""
        pass
    
    async def health_check_all(self) -> Dict[str, bool]:
        """检查所有插件健康状态"""
        pass
    
    async def get_statistics(self, name: str) -> PluginStatistics:
        """获取插件调用统计"""
        pass

class PluginConfig(BaseModel):
    name: str
    connection_type: str
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    timeout: int = 30
    enabled: bool = True
    priority: int = 0
    type_mapping: Dict[str, str] = {}  # 内部类型 -> 工具类型映射
    extra_config: Dict[str, Any] = {}

class PluginStatistics(BaseModel):
    total_calls: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_latency_ms: float
    total_cost: float
```

### 6. Method Switcher (方法切换器)

**文件**: `src/ai/annotation_switcher.py`

**职责**: 切换 AI 标注方法

```python
class AnnotationMethodSwitcher:
    """标注方法切换器"""
    
    def __init__(
        self,
        llm_service: LLMService,
        ml_backend: MLBackend,
        argilla: ArgillaClient,
        third_party_adapter: ThirdPartyAnnotationAdapter
    ):
        self.methods = {
            "llm": llm_service,
            "ml_backend": ml_backend,
            "argilla": argilla,
            "third_party": third_party_adapter
        }
        self.default_method = "llm"
    
    async def annotate(
        self,
        tasks: List[AnnotationTask],
        method: str = None,
        tool_name: str = None  # 用于第三方工具
    ) -> List[AnnotationResult]:
        """执行标注"""
        pass
    
    def switch_method(self, method: str) -> None:
        """切换默认方法"""
        pass
    
    def get_current_method(self) -> str:
        """获取当前方法"""
        pass
    
    def list_available_methods(self) -> List[str]:
        """列出可用方法"""
        pass
    
    async def compare_methods(self, tasks: List[AnnotationTask]) -> MethodComparisonReport:
        """方法性能对比"""
        pass
```

### 7. Collaboration Manager (协作管理器)

**文件**: `src/ai/collaboration_manager.py`

**职责**: 管理人机协作和角色分工

```python
class CollaborationManager:
    """协作管理器"""
    
    async def assign_task(
        self,
        task: AnnotationTask,
        role: UserRole,
        user_id: str = None
    ) -> TaskAssignment:
        """分配任务"""
        pass
    
    async def auto_assign_to_reviewer(self, task: AnnotationTask) -> TaskAssignment:
        """自动分配给审核员"""
        pass
    
    async def get_workload(self, user_id: str) -> WorkloadStatistics:
        """获取工作量统计"""
        pass
    
    async def get_team_statistics(self, project_id: str) -> TeamStatistics:
        """获取团队统计"""
        pass

class UserRole(str, Enum):
    ANNOTATOR = "annotator"
    EXPERT = "expert"
    CONTRACTOR = "contractor"
    REVIEWER = "reviewer"
```

### 8. Review Flow Engine (审核流引擎)

**文件**: `src/ai/review_flow.py`

**职责**: 管理标注审核流程

```python
class ReviewFlowEngine:
    """审核流引擎"""
    
    async def submit_for_review(self, annotation: Annotation) -> ReviewTask:
        """提交审核"""
        pass
    
    async def approve(self, review_task_id: str, reviewer_id: str) -> Annotation:
        """审核通过"""
        pass
    
    async def reject(self, review_task_id: str, reviewer_id: str, reason: str) -> Annotation:
        """审核驳回"""
        pass
    
    async def modify(self, review_task_id: str, reviewer_id: str, modifications: Dict) -> Annotation:
        """审核修改"""
        pass
    
    async def batch_approve(self, review_task_ids: List[str], reviewer_id: str) -> List[Annotation]:
        """批量审核通过"""
        pass
    
    async def get_review_history(self, annotation_id: str) -> List[ReviewRecord]:
        """获取审核历史"""
        pass
```

## Data Models

### 数据库模型

```python
class AnnotationPlugin(Base):
    """标注工具插件表"""
    __tablename__ = "annotation_plugins"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=True)
    name = Column(String(100), nullable=False, unique=True)
    connection_type = Column(String(50), nullable=False)
    endpoint = Column(String(500), nullable=True)
    api_key_encrypted = Column(Text, nullable=True)
    timeout = Column(Integer, default=30)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    type_mapping = Column(JSONB, default={})
    extra_config = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PluginCallLog(Base):
    """插件调用日志表"""
    __tablename__ = "plugin_call_logs"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    plugin_id = Column(UUID, ForeignKey("annotation_plugins.id"), nullable=False)
    task_count = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    latency_ms = Column(Float, default=0)
    cost = Column(Float, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ReviewRecord(Base):
    """审核记录表"""
    __tablename__ = "review_records"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    annotation_id = Column(UUID, ForeignKey("annotations.id"), nullable=False)
    reviewer_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    action = Column(String(20), nullable=False)  # approve/reject/modify
    reason = Column(Text, nullable=True)
    modifications = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: 置信度阈值标记

*For any* 预标注结果，如果置信度低于配置的阈值，该结果应被标记为需要人工审核。

**Validates: Requirements 1.3, 1.5**

### Property 2: 方法路由正确性

*For any* 配置的默认方法和调用时指定的方法，Method Switcher 应正确路由到对应的服务，且指定方法优先于默认方法。

**Validates: Requirements 4.2, 4.3**

### Property 3: 第三方工具格式转换往返

*For any* 有效的标注任务，经过 Third Party Adapter 转换为工具格式后，结果应能正确转换回 Label Studio 兼容格式。

**Validates: Requirements 8.4, 8.5**

### Property 4: 审核驳回退回

*For any* 审核驳回操作，任务应退回给原标注员，且附带驳回原因。

**Validates: Requirements 6.4**

### Property 5: 自动覆盖记录

*For any* 自动覆盖的标注，系统应记录源样本 ID 和相似度分数，便于后续审核。

**Validates: Requirements 2.4**

### Property 6: 插件接口验证

*For any* 注册的第三方插件，Plugin Manager 应验证其实现了 AnnotationPluginInterface 的所有必要方法。

**Validates: Requirements 8.2**

### Property 7: 自动回退机制

*For any* 第三方工具调用失败，系统应自动回退到内置方法，不返回空结果。

**Validates: Requirements 8.7**

### Property 8: 验证报告完整性

*For any* 验证操作，Post Validation Engine 应生成包含所有配置维度（准确率、召回率、一致性、完整性）的报告。

**Validates: Requirements 3.2**

## Error Handling

### 错误分类

| 错误类型 | 错误码 | 处理策略 |
|---------|--------|---------|
| 预标注失败 | ANN_PRE_ANNOTATION_ERROR | 标记任务需人工处理 |
| 插件不可用 | ANN_PLUGIN_UNAVAILABLE | 回退到内置方法 |
| 验证失败 | ANN_VALIDATION_ERROR | 生成问题报告 |
| 审核冲突 | ANN_REVIEW_CONFLICT | 返回冲突详情 |
| 任务分配失败 | ANN_ASSIGNMENT_ERROR | 返回分配错误 |

## Testing Strategy

### 单元测试

- 测试预标注置信度计算
- 测试相似度匹配算法
- 测试格式转换逻辑
- 测试审核流程状态机

### 属性测试

```python
@given(st.floats(min_value=0, max_value=1), st.floats(min_value=0, max_value=1))
def test_confidence_threshold_marking(confidence: float, threshold: float):
    """Property 1: 置信度阈值标记"""
    result = PreAnnotationResult(confidence=confidence, ...)
    marked = engine.mark_for_review([result], threshold)
    assert marked[0].needs_review == (confidence < threshold)
```

### 集成测试

- 测试完整的预标注 → 审核 → 验证流程
- 测试第三方工具对接
- 测试人机协作场景
