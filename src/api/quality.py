"""
Quality API - 质量评分和检查 API
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from src.quality.quality_scorer import QualityScorer, QualityScore, ConsistencyScore
from src.quality.quality_checker import QualityChecker, CheckResult, BatchCheckResult
from src.quality.quality_rule_engine import QualityRuleEngine
from src.quality.ragas_evaluator import RagasEvaluator, RagasEvaluationResult, BatchRagasResult


router = APIRouter(prefix="/api/v1/quality", tags=["Quality"])


# 全局实例
_rule_engine: Optional[QualityRuleEngine] = None
_scorer: Optional[QualityScorer] = None
_checker: Optional[QualityChecker] = None
_ragas_evaluator: Optional[RagasEvaluator] = None


def get_rule_engine() -> QualityRuleEngine:
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = QualityRuleEngine()
    return _rule_engine


def get_scorer() -> QualityScorer:
    global _scorer
    if _scorer is None:
        _scorer = QualityScorer(rule_engine=get_rule_engine())
    return _scorer


def get_checker() -> QualityChecker:
    global _checker
    if _checker is None:
        _checker = QualityChecker(rule_engine=get_rule_engine())
    return _checker


def get_ragas_evaluator() -> RagasEvaluator:
    global _ragas_evaluator
    if _ragas_evaluator is None:
        _ragas_evaluator = RagasEvaluator()
    return _ragas_evaluator


# Request/Response Models
class ScoreRequest(BaseModel):
    """评分请求"""
    gold_standard: Optional[Dict[str, Any]] = None
    project_id: Optional[str] = None


class ScoreResponse(BaseModel):
    """评分响应"""
    id: str
    annotation_id: str
    project_id: Optional[str] = None
    dimension_scores: Dict[str, float]
    total_score: float
    weights: Dict[str, float]
    scored_at: datetime


class ConsistencyRequest(BaseModel):
    """一致性评分请求"""
    annotations: List[Dict[str, Any]]


class ConsistencyResponse(BaseModel):
    """一致性评分响应"""
    task_id: str
    score: float
    method: str
    annotator_count: int


class CheckRequest(BaseModel):
    """检查请求"""
    annotation_data: Optional[Dict[str, Any]] = None
    project_id: Optional[str] = None


class CheckResponse(BaseModel):
    """检查响应"""
    id: str
    annotation_id: str
    passed: bool
    issues: List[Dict[str, Any]]
    checked_rules: int
    checked_at: datetime


class BatchCheckRequest(BaseModel):
    """批量检查请求"""
    project_id: str
    annotation_ids: Optional[List[str]] = None
    annotations: Optional[List[Dict[str, Any]]] = None


class BatchCheckResponse(BaseModel):
    """批量检查响应"""
    project_id: str
    total_checked: int
    passed_count: int
    failed_count: int
    results: List[CheckResponse]


class RagasEvaluateRequest(BaseModel):
    """Ragas 评估请求"""
    question: str
    answer: str
    contexts: List[str] = Field(default_factory=list)
    ground_truth: Optional[str] = None
    metrics: Optional[List[str]] = None


class RagasEvaluateResponse(BaseModel):
    """Ragas 评估响应"""
    id: str
    question: str
    answer: str
    contexts: List[str]
    ground_truth: Optional[str] = None
    scores: Dict[str, float]
    overall_score: float
    metrics_used: List[str]


class RagasBatchRequest(BaseModel):
    """Ragas 批量评估请求"""
    dataset: List[Dict[str, Any]]
    metrics: Optional[List[str]] = None


class RagasBatchResponse(BaseModel):
    """Ragas 批量评估响应"""
    total_evaluated: int
    average_scores: Dict[str, float]
    results: List[RagasEvaluateResponse]


# API Endpoints
@router.post("/score/{annotation_id}", response_model=ScoreResponse)
async def score_annotation(
    annotation_id: str,
    request: ScoreRequest = None,
    scorer: QualityScorer = Depends(get_scorer)
) -> ScoreResponse:
    """
    评估标注质量
    
    - **annotation_id**: 标注ID
    - **gold_standard**: 黄金标准数据 (可选)
    - **project_id**: 项目ID (可选)
    """
    request = request or ScoreRequest()
    
    score = await scorer.score_annotation(
        annotation_id=annotation_id,
        gold_standard=request.gold_standard,
        project_id=request.project_id
    )
    
    return ScoreResponse(
        id=score.id,
        annotation_id=score.annotation_id,
        project_id=score.project_id,
        dimension_scores=score.dimension_scores,
        total_score=score.total_score,
        weights=score.weights,
        scored_at=score.scored_at
    )


@router.post("/consistency/{task_id}", response_model=ConsistencyResponse)
async def calculate_consistency(
    task_id: str,
    request: ConsistencyRequest,
    scorer: QualityScorer = Depends(get_scorer)
) -> ConsistencyResponse:
    """
    计算标注员间一致性
    
    - **task_id**: 任务ID
    - **annotations**: 标注数据列表
    """
    result = await scorer.calculate_consistency(
        task_id=task_id,
        annotations=request.annotations
    )
    
    return ConsistencyResponse(
        task_id=result.task_id,
        score=result.score,
        method=result.method,
        annotator_count=result.annotator_count
    )


@router.post("/check/{annotation_id}", response_model=CheckResponse)
async def check_annotation(
    annotation_id: str,
    request: CheckRequest = None,
    checker: QualityChecker = Depends(get_checker)
) -> CheckResponse:
    """
    检查标注质量
    
    - **annotation_id**: 标注ID
    - **annotation_data**: 标注数据 (可选)
    - **project_id**: 项目ID (可选)
    """
    request = request or CheckRequest()
    
    result = await checker.check_annotation(
        annotation_id=annotation_id,
        annotation_data=request.annotation_data,
        project_id=request.project_id
    )
    
    return CheckResponse(
        id=result.id,
        annotation_id=result.annotation_id,
        passed=result.passed,
        issues=[i.dict() for i in result.issues],
        checked_rules=result.checked_rules,
        checked_at=result.checked_at
    )


@router.post("/batch-check", response_model=BatchCheckResponse)
async def batch_check(
    request: BatchCheckRequest,
    checker: QualityChecker = Depends(get_checker)
) -> BatchCheckResponse:
    """
    批量检查标注质量
    
    - **project_id**: 项目ID
    - **annotation_ids**: 标注ID列表 (可选)
    - **annotations**: 标注数据列表 (可选)
    """
    result = await checker.batch_check(
        project_id=request.project_id,
        annotation_ids=request.annotation_ids,
        annotations=request.annotations
    )
    
    return BatchCheckResponse(
        project_id=result.project_id,
        total_checked=result.total_checked,
        passed_count=result.passed_count,
        failed_count=result.failed_count,
        results=[
            CheckResponse(
                id=r.id,
                annotation_id=r.annotation_id,
                passed=r.passed,
                issues=[i.dict() for i in r.issues],
                checked_rules=r.checked_rules,
                checked_at=r.checked_at
            )
            for r in result.results
        ]
    )


@router.post("/ragas/evaluate", response_model=RagasEvaluateResponse)
async def ragas_evaluate(
    request: RagasEvaluateRequest,
    evaluator: RagasEvaluator = Depends(get_ragas_evaluator)
) -> RagasEvaluateResponse:
    """
    Ragas 单条评估
    
    - **question**: 问题
    - **answer**: 答案
    - **contexts**: 上下文列表
    - **ground_truth**: 标准答案 (可选)
    - **metrics**: 评估指标列表 (可选)
    """
    result = await evaluator.evaluate(
        question=request.question,
        answer=request.answer,
        contexts=request.contexts,
        ground_truth=request.ground_truth,
        metrics=request.metrics
    )
    
    return RagasEvaluateResponse(
        id=result.id,
        question=result.question,
        answer=result.answer,
        contexts=result.contexts,
        ground_truth=result.ground_truth,
        scores=result.scores,
        overall_score=result.overall_score,
        metrics_used=result.metrics_used
    )


@router.post("/ragas/batch-evaluate", response_model=RagasBatchResponse)
async def ragas_batch_evaluate(
    request: RagasBatchRequest,
    evaluator: RagasEvaluator = Depends(get_ragas_evaluator)
) -> RagasBatchResponse:
    """
    Ragas 批量评估
    
    - **dataset**: 数据集列表
    - **metrics**: 评估指标列表 (可选)
    """
    result = await evaluator.batch_evaluate(
        dataset=request.dataset,
        metrics=request.metrics
    )
    
    return RagasBatchResponse(
        total_evaluated=result.total_evaluated,
        average_scores=result.average_scores,
        results=[
            RagasEvaluateResponse(
                id=r.id,
                question=r.question,
                answer=r.answer,
                contexts=r.contexts,
                ground_truth=r.ground_truth,
                scores=r.scores,
                overall_score=r.overall_score,
                metrics_used=r.metrics_used
            )
            for r in result.results
        ]
    )


# 配置端点
class WeightsRequest(BaseModel):
    """权重配置请求"""
    weights: Dict[str, float]


class RequiredFieldsRequest(BaseModel):
    """必填字段配置请求"""
    fields: List[str]


class DurationRequest(BaseModel):
    """时长配置请求"""
    duration: int


@router.post("/config/{project_id}/weights")
async def set_score_weights(
    project_id: str,
    request: WeightsRequest,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> Dict[str, Any]:
    """设置评分权重"""
    await rule_engine.set_score_weights(project_id, request.weights)
    return {"success": True, "weights": request.weights}


@router.get("/config/{project_id}/weights")
async def get_score_weights(
    project_id: str,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> Dict[str, float]:
    """获取评分权重"""
    return await rule_engine.get_score_weights(project_id)


@router.post("/config/{project_id}/required-fields")
async def set_required_fields(
    project_id: str,
    request: RequiredFieldsRequest,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> Dict[str, Any]:
    """设置必填字段"""
    await rule_engine.set_required_fields(project_id, request.fields)
    return {"success": True, "fields": request.fields}


@router.get("/config/{project_id}/required-fields")
async def get_required_fields(
    project_id: str,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> List[str]:
    """获取必填字段"""
    return await rule_engine.get_required_fields(project_id)


@router.post("/config/{project_id}/expected-duration")
async def set_expected_duration(
    project_id: str,
    request: DurationRequest,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> Dict[str, Any]:
    """设置预期标注时长"""
    await rule_engine.set_expected_duration(project_id, request.duration)
    return {"success": True, "duration": request.duration}


@router.get("/config/{project_id}/expected-duration")
async def get_expected_duration(
    project_id: str,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> int:
    """获取预期标注时长"""
    return await rule_engine.get_expected_duration(project_id)
