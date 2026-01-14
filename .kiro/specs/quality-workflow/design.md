# Design Document: Quality Workflow (质量评分与工作流)

## Overview

本设计文档描述 Quality Workflow 模块的架构设计，该模块实现完整的质量评分和工作流管理功能，包括多维度质量评估、自动化质量检查、质量报告生成和质量改进工作流。

设计原则：
- **多维评估**：从多个维度全面评估质量
- **自动化检查**：减少人工检查工作量
- **持续改进**：建立质量改进闭环
- **语义评估**：集成 Ragas 框架进行语义质量评估

## Architecture

```mermaid
graph TB
    subgraph Frontend["前端层"]
        QualityDashboard[Quality Dashboard]
        RuleUI[Rule Config UI]
        ReportUI[Report UI]
        WorkflowUI[Workflow UI]
    end

    subgraph API["API 层"]
        QualityRouter[/api/v1/quality]
        RuleRouter[/api/v1/quality-rules]
        ReportRouter[/api/v1/quality-reports]
        WorkflowRouter[/api/v1/quality-workflow]
    end
    
    subgraph Core["核心层"]
        QualityScorer[Quality Scorer]
        QualityChecker[Quality Checker]
        QualityReporter[Quality Reporter]
        WorkflowEngine[Workflow Engine]
        RuleEngine[Rule Engine]
        AlertService[Alert Service]
        RagasEvaluator[Ragas Evaluator]
    end
    
    subgraph External["外部服务"]
        Ragas[Ragas Framework]
        EmailService[Email Service]
        Webhook[Webhook Service]
    end
    
    subgraph Storage["存储层"]
        DB[(PostgreSQL)]
        Cache[(Redis)]
    end
    
    QualityDashboard --> QualityRouter
    RuleUI --> RuleRouter
    ReportUI --> ReportRouter
    WorkflowUI --> WorkflowRouter
    
    QualityRouter --> QualityScorer
    QualityRouter --> QualityChecker
    RuleRouter --> RuleEngine
    ReportRouter --> QualityReporter
    WorkflowRouter --> WorkflowEngine
    
    QualityScorer --> RuleEngine
    QualityChecker --> RuleEngine
    QualityChecker --> AlertService
    QualityScorer --> RagasEvaluator
    
    RagasEvaluator --> Ragas
    AlertService --> EmailService
    AlertService --> Webhook
    
    QualityScorer --> DB
    QualityChecker --> DB
    QualityReporter --> DB
    WorkflowEngine --> DB
    RuleEngine --> Cache
```

## Components and Interfaces

### 1. Quality Scorer (质量评分器)

**文件**: `src/quality/quality_scorer.py`

**职责**: 计算多维度质量分数

```python
class QualityScorer:
    """质量评分器"""
    
    def __init__(
        self,
        db: AsyncSession,
        rule_engine: QualityRuleEngine,
        ragas_evaluator: RagasEvaluator
    ):
        self.db = db
        self.rule_engine = rule_engine
        self.ragas_evaluator = ragas_evaluator
    
    async def score_annotation(
        self,
        annotation_id: str,
        gold_standard: Dict = None
    ) -> QualityScore:
        """评估单个标注的质量"""
        annotation = await self.get_annotation(annotation_id)
        
        scores = {}
        
        # 准确性评分
        if gold_standard:
            scores["accuracy"] = await self._calculate_accuracy(
                annotation.data, gold_standard
            )
        
        # 完整性评分
        scores["completeness"] = await self._calculate_completeness(annotation)
        
        # 时效性评分
        scores["timeliness"] = await self._calculate_timeliness(annotation)
        
        # 获取评分权重
        weights = await self.rule_engine.get_score_weights(annotation.project_id)
        
        # 计算综合分数
        total_score = self._calculate_weighted_score(scores, weights)
        
        return QualityScore(
            annotation_id=annotation_id,
            dimension_scores=scores,
            total_score=total_score,
            weights=weights
        )
    
    async def _calculate_accuracy(self, annotation: Dict, gold_standard: Dict) -> float:
        """计算准确性分数"""
        matching_fields = 0
        total_fields = len(gold_standard)
        
        for key, expected in gold_standard.items():
            if key in annotation and annotation[key] == expected:
                matching_fields += 1
        
        return matching_fields / total_fields if total_fields > 0 else 0.0
    
    async def _calculate_completeness(self, annotation) -> float:
        """计算完整性分数"""
        required_fields = await self.rule_engine.get_required_fields(annotation.project_id)
        filled_fields = sum(1 for f in required_fields if f in annotation.data and annotation.data[f])
        
        return filled_fields / len(required_fields) if required_fields else 1.0
    
    async def _calculate_timeliness(self, annotation) -> float:
        """计算时效性分数"""
        expected_duration = await self.rule_engine.get_expected_duration(annotation.project_id)
        actual_duration = (annotation.completed_at - annotation.started_at).total_seconds()
        
        if actual_duration <= expected_duration:
            return 1.0
        elif actual_duration <= expected_duration * 2:
            return 0.8
        elif actual_duration <= expected_duration * 3:
            return 0.6
        else:
            return 0.4
    
    def _calculate_weighted_score(self, scores: Dict[str, float], weights: Dict[str, float]) -> float:
        """计算加权综合分数"""
        total_weight = sum(weights.values())
        weighted_sum = sum(scores.get(dim, 0) * weights.get(dim, 0) for dim in weights)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    async def calculate_consistency(
        self,
        task_id: str,
        annotator_ids: List[str]
    ) -> ConsistencyScore:
        """计算标注员间一致性"""
        annotations = await self.get_annotations_by_task(task_id, annotator_ids)
        
        if len(annotations) < 2:
            return ConsistencyScore(task_id=task_id, score=1.0, method="single_annotator")
        
        # 计算 Cohen's Kappa 或 Fleiss' Kappa
        if len(annotations) == 2:
            kappa = self._calculate_cohens_kappa(annotations[0], annotations[1])
        else:
            kappa = self._calculate_fleiss_kappa(annotations)
        
        return ConsistencyScore(
            task_id=task_id,
            score=kappa,
            method="cohens_kappa" if len(annotations) == 2 else "fleiss_kappa",
            annotator_count=len(annotations)
        )

class QualityScore(BaseModel):
    annotation_id: str
    dimension_scores: Dict[str, float]
    total_score: float
    weights: Dict[str, float]
    scored_at: datetime = Field(default_factory=datetime.utcnow)

class ConsistencyScore(BaseModel):
    task_id: str
    score: float
    method: str
    annotator_count: int
```

### 2. Quality Checker (质量检查器)

**文件**: `src/quality/quality_checker.py`

**职责**: 执行自动化质量检查

```python
class QualityChecker:
    """质量检查器"""
    
    def __init__(
        self,
        db: AsyncSession,
        rule_engine: QualityRuleEngine,
        alert_service: QualityAlertService
    ):
        self.db = db
        self.rule_engine = rule_engine
        self.alert_service = alert_service
    
    async def check_annotation(self, annotation_id: str) -> CheckResult:
        """检查单个标注"""
        annotation = await self.get_annotation(annotation_id)
        rules = await self.rule_engine.get_active_rules(annotation.project_id)
        
        issues = []
        for rule in rules:
            result = await self._execute_rule(annotation, rule)
            if not result.passed:
                issues.append(QualityIssue(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=result.message,
                    field=result.field
                ))
        
        # 如果有严重问题，发送预警
        critical_issues = [i for i in issues if i.severity == "critical"]
        if critical_issues:
            await self.alert_service.send_alert(
                annotation_id=annotation_id,
                issues=critical_issues
            )
        
        return CheckResult(
            annotation_id=annotation_id,
            passed=len(issues) == 0,
            issues=issues,
            checked_rules=len(rules)
        )
    
    async def _execute_rule(self, annotation, rule: QualityRule) -> RuleResult:
        """执行单个规则"""
        if rule.rule_type == "builtin":
            return await self._execute_builtin_rule(annotation, rule)
        elif rule.rule_type == "custom":
            return await self._execute_custom_rule(annotation, rule)
        else:
            return RuleResult(passed=True)
    
    async def _execute_builtin_rule(self, annotation, rule: QualityRule) -> RuleResult:
        """执行内置规则"""
        if rule.name == "required_fields":
            return self._check_required_fields(annotation, rule.config)
        elif rule.name == "value_range":
            return self._check_value_range(annotation, rule.config)
        elif rule.name == "format_validation":
            return self._check_format(annotation, rule.config)
        elif rule.name == "length_limit":
            return self._check_length(annotation, rule.config)
        else:
            return RuleResult(passed=True)
    
    async def _execute_custom_rule(self, annotation, rule: QualityRule) -> RuleResult:
        """执行自定义规则（Python 脚本）"""
        try:
            # 安全执行自定义脚本
            result = await self._safe_execute_script(rule.script, annotation.data)
            return RuleResult(passed=result.get("passed", True), message=result.get("message"))
        except Exception as e:
            return RuleResult(passed=False, message=f"Rule execution error: {str(e)}")
    
    async def batch_check(
        self,
        project_id: str,
        annotation_ids: List[str] = None
    ) -> BatchCheckResult:
        """批量检查"""
        if annotation_ids:
            annotations = await self.get_annotations_by_ids(annotation_ids)
        else:
            annotations = await self.get_unchecked_annotations(project_id)
        
        results = []
        for annotation in annotations:
            result = await self.check_annotation(annotation.id)
            results.append(result)
        
        return BatchCheckResult(
            project_id=project_id,
            total_checked=len(results),
            passed_count=sum(1 for r in results if r.passed),
            failed_count=sum(1 for r in results if not r.passed),
            results=results
        )

class QualityIssue(BaseModel):
    rule_id: str
    rule_name: str
    severity: str  # critical/high/medium/low
    message: str
    field: Optional[str] = None

class CheckResult(BaseModel):
    annotation_id: str
    passed: bool
    issues: List[QualityIssue]
    checked_rules: int
    checked_at: datetime = Field(default_factory=datetime.utcnow)
```

### 3. Quality Rule Engine (质量规则引擎)

**文件**: `src/quality/quality_rule_engine.py`

**职责**: 管理和执行质量规则

```python
class QualityRuleEngine:
    """质量规则引擎"""
    
    def __init__(self, db: AsyncSession, cache: Redis):
        self.db = db
        self.cache = cache
    
    async def create_rule(self, rule: CreateRuleRequest) -> QualityRule:
        """创建规则"""
        new_rule = QualityRule(
            name=rule.name,
            description=rule.description,
            rule_type=rule.rule_type,
            config=rule.config,
            script=rule.script,
            severity=rule.severity,
            priority=rule.priority,
            project_id=rule.project_id,
            enabled=True
        )
        
        await self.db.add(new_rule)
        await self._invalidate_cache(rule.project_id)
        
        return new_rule
    
    async def update_rule(self, rule_id: str, updates: UpdateRuleRequest) -> QualityRule:
        """更新规则"""
        rule = await self.get_rule(rule_id)
        
        for key, value in updates.dict(exclude_unset=True).items():
            setattr(rule, key, value)
        
        rule.version += 1
        await self._invalidate_cache(rule.project_id)
        
        return rule
    
    async def get_active_rules(self, project_id: str) -> List[QualityRule]:
        """获取项目的活跃规则"""
        cache_key = f"quality_rules:{project_id}"
        
        # 尝试从缓存获取
        cached = await self.cache.get(cache_key)
        if cached:
            return [QualityRule.parse_raw(r) for r in json.loads(cached)]
        
        # 从数据库获取
        rules = await self.db.query(QualityRule).filter(
            QualityRule.project_id == project_id,
            QualityRule.enabled == True
        ).order_by(QualityRule.priority.desc()).all()
        
        # 缓存结果
        await self.cache.set(
            cache_key,
            json.dumps([r.json() for r in rules]),
            ex=3600
        )
        
        return rules
    
    async def get_score_weights(self, project_id: str) -> Dict[str, float]:
        """获取评分权重"""
        config = await self.get_project_quality_config(project_id)
        return config.score_weights or {
            "accuracy": 0.4,
            "completeness": 0.3,
            "timeliness": 0.2,
            "consistency": 0.1
        }
    
    async def get_required_fields(self, project_id: str) -> List[str]:
        """获取必填字段"""
        config = await self.get_project_quality_config(project_id)
        return config.required_fields or []
    
    async def create_from_template(self, template_id: str, project_id: str) -> List[QualityRule]:
        """从模板创建规则"""
        template = await self.get_template(template_id)
        rules = []
        
        for rule_config in template.rules:
            rule = await self.create_rule(CreateRuleRequest(
                **rule_config,
                project_id=project_id
            ))
            rules.append(rule)
        
        return rules
    
    async def get_rule_history(self, rule_id: str) -> List[RuleVersion]:
        """获取规则版本历史"""
        pass

class QualityRule(BaseModel):
    id: str
    name: str
    description: str
    rule_type: str  # builtin/custom
    config: Dict = {}
    script: Optional[str] = None
    severity: str = "medium"
    priority: int = 0
    project_id: str
    enabled: bool = True
    version: int = 1
    created_at: datetime
    updated_at: datetime
```

### 4. Quality Reporter (质量报告器)

**文件**: `src/quality/quality_reporter.py`

**职责**: 生成质量分析报告

```python
class QualityReporter:
    """质量报告器"""
    
    def __init__(self, db: AsyncSession, quality_scorer: QualityScorer):
        self.db = db
        self.quality_scorer = quality_scorer
    
    async def generate_project_report(
        self,
        project_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> ProjectQualityReport:
        """生成项目质量汇总报告"""
        # 获取时间范围内的所有标注
        annotations = await self.get_annotations_in_range(project_id, start_date, end_date)
        
        # 计算各维度平均分
        scores = await self._calculate_average_scores(annotations)
        
        # 计算质量趋势
        trend = await self._calculate_quality_trend(project_id, start_date, end_date)
        
        # 统计问题分布
        issue_distribution = await self._get_issue_distribution(project_id, start_date, end_date)
        
        return ProjectQualityReport(
            project_id=project_id,
            period_start=start_date,
            period_end=end_date,
            total_annotations=len(annotations),
            average_scores=scores,
            quality_trend=trend,
            issue_distribution=issue_distribution
        )
    
    async def generate_annotator_ranking(
        self,
        project_id: str,
        period: str = "month"
    ) -> AnnotatorRankingReport:
        """生成标注员质量排名报告"""
        annotators = await self.get_project_annotators(project_id)
        rankings = []
        
        for annotator in annotators:
            stats = await self._calculate_annotator_stats(annotator.id, project_id, period)
            rankings.append(AnnotatorRanking(
                annotator_id=annotator.id,
                annotator_name=annotator.name,
                total_annotations=stats.total,
                average_score=stats.average_score,
                accuracy=stats.accuracy,
                pass_rate=stats.pass_rate
            ))
        
        # 按平均分排序
        rankings.sort(key=lambda x: x.average_score, reverse=True)
        
        # 添加排名
        for i, ranking in enumerate(rankings):
            ranking.rank = i + 1
        
        return AnnotatorRankingReport(
            project_id=project_id,
            period=period,
            rankings=rankings
        )
    
    async def generate_trend_report(
        self,
        project_id: str,
        granularity: str = "day"  # day/week/month
    ) -> QualityTrendReport:
        """生成质量趋势分析报告"""
        pass
    
    async def export_report(
        self,
        report: Union[ProjectQualityReport, AnnotatorRankingReport],
        format: str = "pdf"
    ) -> bytes:
        """导出报告"""
        if format == "pdf":
            return await self._export_to_pdf(report)
        elif format == "excel":
            return await self._export_to_excel(report)
        elif format == "html":
            return await self._export_to_html(report)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def schedule_report(
        self,
        project_id: str,
        report_type: str,
        schedule: str,  # cron 表达式
        recipients: List[str]
    ) -> ReportSchedule:
        """创建定时报告"""
        pass

class ProjectQualityReport(BaseModel):
    project_id: str
    period_start: datetime
    period_end: datetime
    total_annotations: int
    average_scores: Dict[str, float]
    quality_trend: List[TrendPoint]
    issue_distribution: Dict[str, int]
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class AnnotatorRanking(BaseModel):
    annotator_id: str
    annotator_name: str
    rank: int = 0
    total_annotations: int
    average_score: float
    accuracy: float
    pass_rate: float
```

### 5. Quality Workflow Engine (质量工作流引擎)

**文件**: `src/quality/quality_workflow_engine.py`

**职责**: 管理质量改进流程

```python
class QualityWorkflowEngine:
    """质量工作流引擎"""
    
    def __init__(self, db: AsyncSession, notification_service: NotificationService):
        self.db = db
        self.notification_service = notification_service
    
    async def configure_workflow(
        self,
        project_id: str,
        config: WorkflowConfig
    ) -> QualityWorkflow:
        """配置质量改进流程"""
        workflow = QualityWorkflow(
            project_id=project_id,
            stages=config.stages,
            auto_create_task=config.auto_create_task,
            escalation_rules=config.escalation_rules
        )
        
        await self.db.add(workflow)
        return workflow
    
    async def create_improvement_task(
        self,
        annotation_id: str,
        issues: List[QualityIssue],
        assignee_id: str = None
    ) -> ImprovementTask:
        """创建改进任务"""
        annotation = await self.get_annotation(annotation_id)
        
        # 如果没有指定负责人，分配给原标注员
        if not assignee_id:
            assignee_id = annotation.annotator_id
        
        task = ImprovementTask(
            annotation_id=annotation_id,
            project_id=annotation.project_id,
            issues=issues,
            assignee_id=assignee_id,
            status="pending",
            priority=self._calculate_priority(issues)
        )
        
        await self.db.add(task)
        
        # 发送通知
        await self.notification_service.notify_improvement_task(assignee_id, task)
        
        return task
    
    def _calculate_priority(self, issues: List[QualityIssue]) -> int:
        """计算任务优先级"""
        severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        total_weight = sum(severity_weights.get(i.severity, 1) for i in issues)
        
        if total_weight >= 10:
            return 3  # 高优先级
        elif total_weight >= 5:
            return 2  # 中优先级
        else:
            return 1  # 低优先级
    
    async def submit_improvement(
        self,
        task_id: str,
        improved_data: Dict
    ) -> ImprovementTask:
        """提交改进"""
        task = await self.get_task(task_id)
        task.improved_data = improved_data
        task.status = "submitted"
        task.submitted_at = datetime.utcnow()
        
        return task
    
    async def review_improvement(
        self,
        task_id: str,
        reviewer_id: str,
        approved: bool,
        comments: str = None
    ) -> ImprovementTask:
        """审核改进"""
        task = await self.get_task(task_id)
        
        if approved:
            task.status = "approved"
            # 更新原标注
            await self._apply_improvement(task)
        else:
            task.status = "rejected"
        
        task.reviewer_id = reviewer_id
        task.review_comments = comments
        task.reviewed_at = datetime.utcnow()
        
        # 记录历史
        await self._record_history(task, "review", reviewer_id, approved)
        
        return task
    
    async def get_improvement_tasks(
        self,
        project_id: str = None,
        assignee_id: str = None,
        status: str = None
    ) -> List[ImprovementTask]:
        """获取改进任务列表"""
        pass
    
    async def evaluate_improvement_effect(
        self,
        project_id: str,
        period: str = "month"
    ) -> ImprovementEffectReport:
        """评估改进效果"""
        pass

class ImprovementTask(BaseModel):
    id: str
    annotation_id: str
    project_id: str
    issues: List[QualityIssue]
    assignee_id: str
    status: str  # pending/in_progress/submitted/approved/rejected
    priority: int
    improved_data: Optional[Dict] = None
    reviewer_id: Optional[str] = None
    review_comments: Optional[str] = None
    created_at: datetime
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None

class WorkflowConfig(BaseModel):
    stages: List[str] = ["identify", "assign", "improve", "review", "verify"]
    auto_create_task: bool = True
    escalation_rules: Dict = {}
```

### 6. Ragas Evaluator (Ragas 评估器)

**文件**: `src/quality/ragas_evaluator.py`

**职责**: 使用 Ragas 框架评估语义质量

```python
class RagasEvaluator:
    """Ragas 语义质量评估器"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.metrics = {
            "faithfulness": Faithfulness(),
            "answer_relevancy": AnswerRelevancy(),
            "context_precision": ContextPrecision(),
            "context_recall": ContextRecall()
        }
    
    async def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: str = None,
        metrics: List[str] = None
    ) -> RagasEvaluationResult:
        """评估单条数据"""
        if metrics is None:
            metrics = list(self.metrics.keys())
        
        results = {}
        
        for metric_name in metrics:
            if metric_name not in self.metrics:
                continue
            
            metric = self.metrics[metric_name]
            
            if metric_name == "faithfulness":
                score = await self._evaluate_faithfulness(answer, contexts)
            elif metric_name == "answer_relevancy":
                score = await self._evaluate_answer_relevancy(question, answer)
            elif metric_name == "context_precision":
                score = await self._evaluate_context_precision(question, contexts, ground_truth)
            elif metric_name == "context_recall":
                score = await self._evaluate_context_recall(contexts, ground_truth)
            else:
                continue
            
            results[metric_name] = score
        
        return RagasEvaluationResult(
            question=question,
            answer=answer,
            contexts=contexts,
            ground_truth=ground_truth,
            scores=results,
            overall_score=sum(results.values()) / len(results) if results else 0
        )
    
    async def _evaluate_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """评估忠实度 - 答案是否基于上下文"""
        # 使用 LLM 判断答案中的声明是否可以从上下文中推导
        prompt = f"""
        Given the following contexts and answer, evaluate if the answer is faithful to the contexts.
        
        Contexts: {contexts}
        Answer: {answer}
        
        Score from 0 to 1, where 1 means completely faithful.
        """
        
        response = await self.llm_client.generate(prompt)
        return self._parse_score(response)
    
    async def _evaluate_answer_relevancy(self, question: str, answer: str) -> float:
        """评估答案相关性 - 答案是否回答了问题"""
        prompt = f"""
        Given the following question and answer, evaluate if the answer is relevant to the question.
        
        Question: {question}
        Answer: {answer}
        
        Score from 0 to 1, where 1 means completely relevant.
        """
        
        response = await self.llm_client.generate(prompt)
        return self._parse_score(response)
    
    async def _evaluate_context_precision(
        self,
        question: str,
        contexts: List[str],
        ground_truth: str
    ) -> float:
        """评估上下文精确度 - 检索的上下文是否精确"""
        pass
    
    async def _evaluate_context_recall(
        self,
        contexts: List[str],
        ground_truth: str
    ) -> float:
        """评估上下文召回率 - 是否检索到所有相关上下文"""
        pass
    
    async def batch_evaluate(
        self,
        dataset: List[Dict],
        metrics: List[str] = None
    ) -> BatchRagasResult:
        """批量评估"""
        results = []
        
        for item in dataset:
            result = await self.evaluate(
                question=item["question"],
                answer=item["answer"],
                contexts=item.get("contexts", []),
                ground_truth=item.get("ground_truth"),
                metrics=metrics
            )
            results.append(result)
        
        # 计算平均分
        avg_scores = {}
        for metric in metrics or list(self.metrics.keys()):
            scores = [r.scores.get(metric, 0) for r in results if metric in r.scores]
            avg_scores[metric] = sum(scores) / len(scores) if scores else 0
        
        return BatchRagasResult(
            total_evaluated=len(results),
            average_scores=avg_scores,
            results=results
        )

class RagasEvaluationResult(BaseModel):
    question: str
    answer: str
    contexts: List[str]
    ground_truth: Optional[str]
    scores: Dict[str, float]
    overall_score: float
```


### 7. Quality Alert Service (质量预警服务)

**文件**: `src/quality/quality_alert_service.py`

**职责**: 发送质量预警通知

```python
class QualityAlertService:
    """质量预警服务"""
    
    def __init__(
        self,
        db: AsyncSession,
        notification_service: NotificationService
    ):
        self.db = db
        self.notification_service = notification_service
    
    async def configure_thresholds(
        self,
        project_id: str,
        thresholds: Dict[str, float]
    ) -> AlertConfig:
        """配置质量阈值"""
        config = AlertConfig(
            project_id=project_id,
            thresholds=thresholds,
            enabled=True
        )
        
        await self.db.add(config)
        return config
    
    async def check_and_alert(
        self,
        project_id: str,
        score: QualityScore
    ) -> Optional[QualityAlert]:
        """检查并发送预警"""
        config = await self.get_alert_config(project_id)
        
        if not config or not config.enabled:
            return None
        
        # 检查是否在静默期
        if await self._is_in_silence_period(project_id):
            return None
        
        # 检查各维度是否低于阈值
        triggered_dimensions = []
        for dimension, threshold in config.thresholds.items():
            if score.dimension_scores.get(dimension, 1.0) < threshold:
                triggered_dimensions.append(dimension)
        
        if not triggered_dimensions:
            return None
        
        # 创建预警
        alert = QualityAlert(
            project_id=project_id,
            annotation_id=score.annotation_id,
            triggered_dimensions=triggered_dimensions,
            scores=score.dimension_scores,
            severity=self._determine_severity(triggered_dimensions, score)
        )
        
        await self.db.add(alert)
        
        # 发送通知
        await self._send_alert_notification(alert)
        
        return alert
    
    def _determine_severity(
        self,
        triggered_dimensions: List[str],
        score: QualityScore
    ) -> str:
        """确定预警严重程度"""
        if score.total_score < 0.3:
            return "critical"
        elif score.total_score < 0.5:
            return "high"
        elif score.total_score < 0.7:
            return "medium"
        else:
            return "low"
    
    async def _send_alert_notification(self, alert: QualityAlert) -> None:
        """发送预警通知"""
        # 获取通知接收人
        recipients = await self._get_alert_recipients(alert.project_id)
        
        for recipient in recipients:
            await self.notification_service.send(
                user_id=recipient.id,
                channel=recipient.preferred_channel,
                title=f"质量预警 - {alert.severity.upper()}",
                message=f"项目质量低于阈值，触发维度: {', '.join(alert.triggered_dimensions)}"
            )
    
    async def escalate_alert(self, alert_id: str) -> QualityAlert:
        """升级预警"""
        alert = await self.get_alert(alert_id)
        alert.escalation_level += 1
        
        # 获取升级接收人
        escalation_recipients = await self._get_escalation_recipients(
            alert.project_id, alert.escalation_level
        )
        
        for recipient in escalation_recipients:
            await self.notification_service.send(
                user_id=recipient.id,
                channel="email",
                title=f"质量预警升级 - Level {alert.escalation_level}",
                message=f"预警已升级，请立即处理"
            )
        
        return alert
    
    async def set_silence_period(
        self,
        project_id: str,
        duration_minutes: int
    ) -> None:
        """设置静默期"""
        pass

class QualityAlert(BaseModel):
    id: str
    project_id: str
    annotation_id: str
    triggered_dimensions: List[str]
    scores: Dict[str, float]
    severity: str
    escalation_level: int = 0
    status: str = "open"  # open/acknowledged/resolved
    created_at: datetime
    resolved_at: Optional[datetime] = None
```

### 8. API Router (API 路由)

**文件**: `src/api/quality.py`

```python
router = APIRouter(prefix="/api/v1", tags=["Quality"])

# 质量评分
@router.post("/quality/score/{annotation_id}")
async def score_annotation(
    annotation_id: str,
    request: ScoreRequest = None
) -> QualityScore:
    """评估标注质量"""
    pass

@router.post("/quality/consistency/{task_id}")
async def calculate_consistency(task_id: str) -> ConsistencyScore:
    """计算一致性分数"""
    pass

# 质量检查
@router.post("/quality/check/{annotation_id}")
async def check_annotation(annotation_id: str) -> CheckResult:
    """检查标注质量"""
    pass

@router.post("/quality/batch-check")
async def batch_check(request: BatchCheckRequest) -> BatchCheckResult:
    """批量检查"""
    pass

# 质量规则
@router.post("/quality-rules")
async def create_rule(request: CreateRuleRequest) -> QualityRule:
    """创建规则"""
    pass

@router.get("/quality-rules")
async def list_rules(project_id: str) -> List[QualityRule]:
    """列出规则"""
    pass

@router.put("/quality-rules/{rule_id}")
async def update_rule(rule_id: str, request: UpdateRuleRequest) -> QualityRule:
    """更新规则"""
    pass

@router.delete("/quality-rules/{rule_id}")
async def delete_rule(rule_id: str) -> None:
    """删除规则"""
    pass

@router.post("/quality-rules/from-template")
async def create_from_template(request: CreateFromTemplateRequest) -> List[QualityRule]:
    """从模板创建规则"""
    pass

# 质量报告
@router.post("/quality-reports/project")
async def generate_project_report(request: ProjectReportRequest) -> ProjectQualityReport:
    """生成项目报告"""
    pass

@router.post("/quality-reports/annotator-ranking")
async def generate_annotator_ranking(request: RankingRequest) -> AnnotatorRankingReport:
    """生成标注员排名"""
    pass

@router.post("/quality-reports/export")
async def export_report(request: ExportRequest) -> Response:
    """导出报告"""
    pass

@router.post("/quality-reports/schedule")
async def schedule_report(request: ScheduleReportRequest) -> ReportSchedule:
    """创建定时报告"""
    pass

# 质量工作流
@router.post("/quality-workflow/configure")
async def configure_workflow(request: WorkflowConfigRequest) -> QualityWorkflow:
    """配置工作流"""
    pass

@router.post("/quality-workflow/tasks")
async def create_improvement_task(request: CreateTaskRequest) -> ImprovementTask:
    """创建改进任务"""
    pass

@router.get("/quality-workflow/tasks")
async def list_improvement_tasks(
    project_id: str = None,
    assignee_id: str = None,
    status: str = None
) -> List[ImprovementTask]:
    """列出改进任务"""
    pass

@router.post("/quality-workflow/tasks/{task_id}/submit")
async def submit_improvement(task_id: str, request: SubmitRequest) -> ImprovementTask:
    """提交改进"""
    pass

@router.post("/quality-workflow/tasks/{task_id}/review")
async def review_improvement(task_id: str, request: ReviewRequest) -> ImprovementTask:
    """审核改进"""
    pass

# Ragas 评估
@router.post("/quality/ragas/evaluate")
async def ragas_evaluate(request: RagasEvaluateRequest) -> RagasEvaluationResult:
    """Ragas 单条评估"""
    pass

@router.post("/quality/ragas/batch-evaluate")
async def ragas_batch_evaluate(request: RagasBatchRequest) -> BatchRagasResult:
    """Ragas 批量评估"""
    pass

# 质量预警
@router.post("/quality-alerts/configure")
async def configure_alerts(request: AlertConfigRequest) -> AlertConfig:
    """配置预警"""
    pass

@router.get("/quality-alerts")
async def list_alerts(project_id: str, status: str = None) -> List[QualityAlert]:
    """列出预警"""
    pass

@router.post("/quality-alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> QualityAlert:
    """确认预警"""
    pass

@router.post("/quality-alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str) -> QualityAlert:
    """解决预警"""
    pass
```

## Data Models

### 数据库模型

```python
class QualityScoreModel(Base):
    """质量评分表"""
    __tablename__ = "quality_scores"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    annotation_id = Column(UUID, ForeignKey("annotations.id"), nullable=False)
    dimension_scores = Column(JSONB, nullable=False)
    total_score = Column(Float, nullable=False)
    weights = Column(JSONB, nullable=False)
    scored_at = Column(DateTime, default=datetime.utcnow)

class QualityRuleModel(Base):
    """质量规则表"""
    __tablename__ = "quality_rules"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(20), nullable=False)
    config = Column(JSONB, default={})
    script = Column(Text, nullable=True)
    severity = Column(String(20), default="medium")
    priority = Column(Integer, default=0)
    project_id = Column(UUID, ForeignKey("projects.id"), nullable=False)
    enabled = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class QualityCheckResultModel(Base):
    """质量检查结果表"""
    __tablename__ = "quality_check_results"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    annotation_id = Column(UUID, ForeignKey("annotations.id"), nullable=False)
    passed = Column(Boolean, nullable=False)
    issues = Column(JSONB, default=[])
    checked_rules = Column(Integer, nullable=False)
    checked_at = Column(DateTime, default=datetime.utcnow)

class ImprovementTaskModel(Base):
    """改进任务表"""
    __tablename__ = "improvement_tasks"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    annotation_id = Column(UUID, ForeignKey("annotations.id"), nullable=False)
    project_id = Column(UUID, ForeignKey("projects.id"), nullable=False)
    issues = Column(JSONB, nullable=False)
    assignee_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")
    priority = Column(Integer, default=1)
    improved_data = Column(JSONB, nullable=True)
    reviewer_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    review_comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

class QualityAlertModel(Base):
    """质量预警表"""
    __tablename__ = "quality_alerts"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    project_id = Column(UUID, ForeignKey("projects.id"), nullable=False)
    annotation_id = Column(UUID, ForeignKey("annotations.id"), nullable=True)
    triggered_dimensions = Column(ARRAY(String), nullable=False)
    scores = Column(JSONB, nullable=False)
    severity = Column(String(20), nullable=False)
    escalation_level = Column(Integer, default=0)
    status = Column(String(20), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
```

## Correctness Properties (Property-Based Testing)

使用 Hypothesis 库进行属性测试，每个属性至少运行 100 次迭代。

### Property 1: 质量分数范围

```python
@given(
    scores=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.floats(min_value=0, max_value=1),
        min_size=1,
        max_size=5
    ),
    weights=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.floats(min_value=0.1, max_value=1),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=100)
def test_quality_score_range(scores, weights):
    """质量分数必须在 0-1 范围内"""
    total_score = calculate_weighted_score(scores, weights)
    assert 0 <= total_score <= 1
```

### Property 2: 规则执行确定性

```python
@given(
    annotation_data=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.integers(), st.text(max_size=100), st.booleans()),
        min_size=1,
        max_size=10
    ),
    rule_config=st.fixed_dictionaries({
        "required_fields": st.lists(st.text(min_size=1, max_size=20), max_size=5)
    })
)
@settings(max_examples=100)
def test_rule_execution_deterministic(annotation_data, rule_config):
    """规则执行必须是确定性的"""
    result1 = execute_rule(annotation_data, rule_config)
    result2 = execute_rule(annotation_data, rule_config)
    
    assert result1.passed == result2.passed
    assert result1.issues == result2.issues
```

### Property 3: 一致性分数对称性

```python
@given(
    annotations=st.lists(
        st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), min_size=1, max_size=5),
        min_size=2,
        max_size=5
    )
)
@settings(max_examples=100)
def test_consistency_score_symmetric(annotations):
    """一致性分数计算必须对称"""
    if len(annotations) == 2:
        kappa1 = calculate_cohens_kappa(annotations[0], annotations[1])
        kappa2 = calculate_cohens_kappa(annotations[1], annotations[0])
        assert abs(kappa1 - kappa2) < 0.001
```

### Property 4: 改进任务优先级单调性

```python
@given(
    issues=st.lists(
        st.fixed_dictionaries({
            "severity": st.sampled_from(["critical", "high", "medium", "low"])
        }),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=100)
def test_priority_monotonicity(issues):
    """更严重的问题应该有更高的优先级"""
    priority = calculate_priority(issues)
    
    # 添加一个 critical 问题
    issues_with_critical = issues + [{"severity": "critical"}]
    priority_with_critical = calculate_priority(issues_with_critical)
    
    assert priority_with_critical >= priority
```

### Property 5: 报告数据一致性

```python
@given(
    annotations=st.lists(
        st.fixed_dictionaries({
            "score": st.floats(min_value=0, max_value=1),
            "passed": st.booleans()
        }),
        min_size=1,
        max_size=100
    )
)
@settings(max_examples=100)
def test_report_data_consistency(annotations):
    """报告数据必须与原始数据一致"""
    report = generate_report(annotations)
    
    # 总数一致
    assert report.total_annotations == len(annotations)
    
    # 通过数一致
    expected_passed = sum(1 for a in annotations if a["passed"])
    assert report.passed_count == expected_passed
    
    # 平均分一致
    expected_avg = sum(a["score"] for a in annotations) / len(annotations)
    assert abs(report.average_score - expected_avg) < 0.001
```

### Property 6: Ragas 评分范围

```python
@given(
    question=st.text(min_size=1, max_size=200),
    answer=st.text(min_size=1, max_size=500),
    contexts=st.lists(st.text(min_size=1, max_size=200), min_size=1, max_size=5)
)
@settings(max_examples=100)
def test_ragas_score_range(question, answer, contexts):
    """Ragas 评分必须在 0-1 范围内"""
    result = ragas_evaluate(question, answer, contexts)
    
    for metric, score in result.scores.items():
        assert 0 <= score <= 1
    
    assert 0 <= result.overall_score <= 1
```

### Property 7: 预警触发一致性

```python
@given(
    scores=st.dictionaries(
        st.sampled_from(["accuracy", "completeness", "timeliness"]),
        st.floats(min_value=0, max_value=1),
        min_size=1,
        max_size=3
    ),
    thresholds=st.dictionaries(
        st.sampled_from(["accuracy", "completeness", "timeliness"]),
        st.floats(min_value=0.5, max_value=0.9),
        min_size=1,
        max_size=3
    )
)
@settings(max_examples=100)
def test_alert_trigger_consistency(scores, thresholds):
    """预警触发必须与阈值配置一致"""
    alert = check_and_alert(scores, thresholds)
    
    if alert:
        # 至少有一个维度低于阈值
        for dim in alert.triggered_dimensions:
            assert scores.get(dim, 1.0) < thresholds.get(dim, 0)
    else:
        # 所有维度都高于阈值
        for dim, threshold in thresholds.items():
            assert scores.get(dim, 1.0) >= threshold
```

## Frontend Components

### 1. 质量仪表板

**文件**: `frontend/src/pages/quality/QualityDashboard.tsx`

```typescript
const QualityDashboard: React.FC<{ projectId: string }> = ({ projectId }) => {
  const { data: overview } = useQuery(
    ['quality-overview', projectId],
    () => qualityApi.getOverview(projectId)
  );

  return (
    <div>
      <Row gutter={16}>
        <Col span={6}>
          <Statistic title="平均质量分" value={overview?.averageScore} suffix="/ 100" />
        </Col>
        <Col span={6}>
          <Statistic title="通过率" value={overview?.passRate} suffix="%" />
        </Col>
        <Col span={6}>
          <Statistic title="待处理问题" value={overview?.pendingIssues} />
        </Col>
        <Col span={6}>
          <Statistic title="活跃预警" value={overview?.activeAlerts} />
        </Col>
      </Row>
      
      <Card title="质量趋势" style={{ marginTop: 16 }}>
        <Line
          data={overview?.trend}
          xField="date"
          yField="score"
          seriesField="dimension"
        />
      </Card>
      
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="问题分布">
            <Pie data={overview?.issueDistribution} angleField="count" colorField="type" />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="标注员排名">
            <Table
              dataSource={overview?.topAnnotators}
              columns={[
                { title: '排名', dataIndex: 'rank' },
                { title: '标注员', dataIndex: 'name' },
                { title: '平均分', dataIndex: 'score' },
              ]}
              pagination={false}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};
```

### 2. 规则配置界面

**文件**: `frontend/src/pages/quality/RuleConfig.tsx`

```typescript
const RuleConfig: React.FC<{ projectId: string }> = ({ projectId }) => {
  const { data: rules, refetch } = useQuery(
    ['quality-rules', projectId],
    () => qualityApi.listRules(projectId)
  );

  const createMutation = useMutation(qualityApi.createRule, {
    onSuccess: () => refetch()
  });

  return (
    <Card title="质量规则配置">
      <Button type="primary" onClick={() => setModalVisible(true)}>
        添加规则
      </Button>
      
      <Table
        dataSource={rules}
        columns={[
          { title: '规则名称', dataIndex: 'name' },
          { title: '类型', dataIndex: 'rule_type' },
          { title: '严重程度', dataIndex: 'severity', render: renderSeverity },
          { title: '优先级', dataIndex: 'priority' },
          { title: '状态', dataIndex: 'enabled', render: (v) => v ? '启用' : '禁用' },
          {
            title: '操作',
            render: (_, record) => (
              <Space>
                <Button size="small" onClick={() => handleEdit(record)}>编辑</Button>
                <Switch checked={record.enabled} onChange={() => handleToggle(record)} />
              </Space>
            )
          }
        ]}
      />
      
      <Modal
        title="添加规则"
        visible={modalVisible}
        onOk={handleCreate}
        onCancel={() => setModalVisible(false)}
      >
        <Form form={form}>
          <Form.Item name="name" label="规则名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="rule_type" label="规则类型" rules={[{ required: true }]}>
            <Select>
              <Option value="builtin">内置规则</Option>
              <Option value="custom">自定义规则</Option>
            </Select>
          </Form.Item>
          <Form.Item name="severity" label="严重程度">
            <Select>
              <Option value="critical">严重</Option>
              <Option value="high">高</Option>
              <Option value="medium">中</Option>
              <Option value="low">低</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};
```

## Error Handling

```python
class QualityError(Exception):
    """质量模块基础异常"""
    pass

class RuleNotFoundError(QualityError):
    """规则不存在"""
    pass

class RuleExecutionError(QualityError):
    """规则执行失败"""
    pass

class ScoreCalculationError(QualityError):
    """分数计算失败"""
    pass

class ReportGenerationError(QualityError):
    """报告生成失败"""
    pass

class RagasEvaluationError(QualityError):
    """Ragas 评估失败"""
    pass
```

## Performance Considerations

1. **规则缓存**: 缓存活跃规则减少数据库查询
2. **批量处理**: 支持批量质量检查提高效率
3. **异步评估**: Ragas 评估使用异步处理
4. **增量报告**: 支持增量生成报告
5. **索引优化**: 为常用查询字段创建索引
