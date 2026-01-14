"""
Quality Scorer - 质量评分器
计算多维度质量分数
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
import math

from pydantic import BaseModel, Field

from src.quality.quality_rule_engine import QualityRuleEngine


class QualityScore(BaseModel):
    """质量评分结果"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    annotation_id: str
    project_id: Optional[str] = None
    annotator_id: Optional[str] = None
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    total_score: float = 0.0
    weights: Dict[str, float] = Field(default_factory=dict)
    gold_standard_id: Optional[str] = None
    scoring_method: str = "weighted_average"
    scored_at: datetime = Field(default_factory=datetime.utcnow)


class ConsistencyScore(BaseModel):
    """一致性评分结果"""
    task_id: str
    score: float
    method: str  # cohens_kappa, fleiss_kappa, single_annotator
    annotator_count: int
    details: Dict[str, Any] = Field(default_factory=dict)


class Annotation(BaseModel):
    """标注数据模型 (简化版)"""
    id: str
    project_id: str
    task_id: Optional[str] = None
    annotator_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class QualityScorer:
    """质量评分器"""
    
    def __init__(
        self,
        rule_engine: Optional[QualityRuleEngine] = None,
        ragas_evaluator: Optional[Any] = None
    ):
        """
        初始化质量评分器
        
        Args:
            rule_engine: 质量规则引擎
            ragas_evaluator: Ragas评估器 (可选)
        """
        self.rule_engine = rule_engine or QualityRuleEngine()
        self.ragas_evaluator = ragas_evaluator
        
        # 内存存储 (用于无数据库场景)
        self._annotations: Dict[str, Annotation] = {}
        self._scores: Dict[str, QualityScore] = {}
    
    def add_annotation(self, annotation: Annotation) -> None:
        """添加标注数据 (用于测试)"""
        self._annotations[annotation.id] = annotation
    
    async def get_annotation(self, annotation_id: str) -> Optional[Annotation]:
        """获取标注数据"""
        return self._annotations.get(annotation_id)
    
    async def score_annotation(
        self,
        annotation_id: str,
        gold_standard: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None
    ) -> QualityScore:
        """
        评估单个标注的质量
        
        Args:
            annotation_id: 标注ID
            gold_standard: 黄金标准数据 (可选)
            project_id: 项目ID (可选)
            
        Returns:
            质量评分结果
        """
        annotation = await self.get_annotation(annotation_id)
        if not annotation:
            # 创建一个空标注用于评分
            annotation = Annotation(
                id=annotation_id,
                project_id=project_id or "default",
                data={}
            )
        
        project_id = project_id or annotation.project_id
        scores: Dict[str, float] = {}
        
        # 准确性评分
        if gold_standard:
            scores["accuracy"] = await self._calculate_accuracy(
                annotation.data, gold_standard
            )
        
        # 完整性评分
        scores["completeness"] = await self._calculate_completeness(
            annotation, project_id
        )
        
        # 时效性评分
        scores["timeliness"] = await self._calculate_timeliness(
            annotation, project_id
        )
        
        # 获取评分权重
        weights = await self.rule_engine.get_score_weights(project_id)
        
        # 计算综合分数
        total_score = self._calculate_weighted_score(scores, weights)
        
        quality_score = QualityScore(
            annotation_id=annotation_id,
            project_id=project_id,
            annotator_id=annotation.annotator_id,
            dimension_scores=scores,
            total_score=total_score,
            weights=weights,
            gold_standard_id=str(uuid4()) if gold_standard else None
        )
        
        # 存储评分结果
        self._scores[quality_score.id] = quality_score
        
        return quality_score
    
    async def _calculate_accuracy(
        self,
        annotation: Dict[str, Any],
        gold_standard: Dict[str, Any]
    ) -> float:
        """
        计算准确性分数
        
        Args:
            annotation: 标注数据
            gold_standard: 黄金标准数据
            
        Returns:
            准确性分数 (0-1)
        """
        if not gold_standard:
            return 1.0
        
        matching_fields = 0
        total_fields = len(gold_standard)
        
        for key, expected in gold_standard.items():
            if key in annotation:
                actual = annotation[key]
                if self._values_match(actual, expected):
                    matching_fields += 1
        
        return matching_fields / total_fields if total_fields > 0 else 1.0
    
    def _values_match(self, actual: Any, expected: Any) -> bool:
        """比较两个值是否匹配"""
        if type(actual) != type(expected):
            return False
        
        if isinstance(expected, dict):
            if set(actual.keys()) != set(expected.keys()):
                return False
            return all(
                self._values_match(actual.get(k), v)
                for k, v in expected.items()
            )
        elif isinstance(expected, list):
            if len(actual) != len(expected):
                return False
            return all(
                self._values_match(a, e)
                for a, e in zip(actual, expected)
            )
        else:
            return actual == expected
    
    async def _calculate_completeness(
        self,
        annotation: Annotation,
        project_id: str
    ) -> float:
        """
        计算完整性分数
        
        Args:
            annotation: 标注对象
            project_id: 项目ID
            
        Returns:
            完整性分数 (0-1)
        """
        required_fields = await self.rule_engine.get_required_fields(project_id)
        
        if not required_fields:
            return 1.0
        
        filled_fields = sum(
            1 for f in required_fields
            if f in annotation.data and annotation.data[f] is not None
            and annotation.data[f] != ""
        )
        
        return filled_fields / len(required_fields)
    
    async def _calculate_timeliness(
        self,
        annotation: Annotation,
        project_id: str
    ) -> float:
        """
        计算时效性分数
        
        Args:
            annotation: 标注对象
            project_id: 项目ID
            
        Returns:
            时效性分数 (0-1)
        """
        if not annotation.started_at or not annotation.completed_at:
            return 1.0
        
        expected_duration = await self.rule_engine.get_expected_duration(project_id)
        actual_duration = (annotation.completed_at - annotation.started_at).total_seconds()
        
        if actual_duration <= 0:
            return 1.0
        
        if actual_duration <= expected_duration:
            return 1.0
        elif actual_duration <= expected_duration * 1.5:
            return 0.9
        elif actual_duration <= expected_duration * 2:
            return 0.8
        elif actual_duration <= expected_duration * 3:
            return 0.6
        else:
            return 0.4
    
    def _calculate_weighted_score(
        self,
        scores: Dict[str, float],
        weights: Dict[str, float]
    ) -> float:
        """
        计算加权综合分数
        
        Args:
            scores: 各维度分数
            weights: 各维度权重
            
        Returns:
            综合分数 (0-1)
        """
        if not scores:
            return 0.0
        
        # 只计算有分数的维度
        available_weights = {
            dim: weight for dim, weight in weights.items()
            if dim in scores
        }
        
        if not available_weights:
            # 如果没有匹配的权重，使用平均值
            return sum(scores.values()) / len(scores)
        
        total_weight = sum(available_weights.values())
        if total_weight == 0:
            return sum(scores.values()) / len(scores)
        
        weighted_sum = sum(
            scores.get(dim, 0) * weight
            for dim, weight in available_weights.items()
        )
        
        return weighted_sum / total_weight
    
    async def calculate_consistency(
        self,
        task_id: str,
        annotations: List[Dict[str, Any]]
    ) -> ConsistencyScore:
        """
        计算标注员间一致性
        
        Args:
            task_id: 任务ID
            annotations: 标注数据列表
            
        Returns:
            一致性评分结果
        """
        if len(annotations) < 2:
            return ConsistencyScore(
                task_id=task_id,
                score=1.0,
                method="single_annotator",
                annotator_count=len(annotations)
            )
        
        # 计算 Cohen's Kappa 或 Fleiss' Kappa
        if len(annotations) == 2:
            kappa = self._calculate_cohens_kappa(annotations[0], annotations[1])
            method = "cohens_kappa"
        else:
            kappa = self._calculate_fleiss_kappa(annotations)
            method = "fleiss_kappa"
        
        return ConsistencyScore(
            task_id=task_id,
            score=kappa,
            method=method,
            annotator_count=len(annotations)
        )
    
    def _calculate_cohens_kappa(
        self,
        annotation1: Dict[str, Any],
        annotation2: Dict[str, Any]
    ) -> float:
        """
        计算 Cohen's Kappa 系数
        
        Args:
            annotation1: 第一个标注
            annotation2: 第二个标注
            
        Returns:
            Kappa系数 (-1 到 1)
        """
        # 获取所有键
        all_keys = set(annotation1.keys()) | set(annotation2.keys())
        
        if not all_keys:
            return 1.0
        
        # 计算一致的数量
        agreements = 0
        for key in all_keys:
            val1 = annotation1.get(key)
            val2 = annotation2.get(key)
            if val1 == val2:
                agreements += 1
        
        # 观察一致率
        po = agreements / len(all_keys)
        
        # 期望一致率 (简化计算)
        # 假设随机情况下的一致率
        pe = 0.5  # 简化假设
        
        # 计算 Kappa
        if pe == 1:
            return 1.0
        
        kappa = (po - pe) / (1 - pe)
        
        # 确保在有效范围内
        return max(-1.0, min(1.0, kappa))
    
    def _calculate_fleiss_kappa(
        self,
        annotations: List[Dict[str, Any]]
    ) -> float:
        """
        计算 Fleiss' Kappa 系数
        
        Args:
            annotations: 标注数据列表
            
        Returns:
            Kappa系数 (-1 到 1)
        """
        n = len(annotations)  # 标注员数量
        
        if n < 2:
            return 1.0
        
        # 获取所有键
        all_keys = set()
        for ann in annotations:
            all_keys.update(ann.keys())
        
        if not all_keys:
            return 1.0
        
        # 计算每个键的一致性
        total_agreement = 0
        for key in all_keys:
            values = [ann.get(key) for ann in annotations]
            # 计算最常见值的出现次数
            value_counts: Dict[Any, int] = {}
            for v in values:
                v_str = str(v)
                value_counts[v_str] = value_counts.get(v_str, 0) + 1
            
            max_count = max(value_counts.values()) if value_counts else 0
            agreement_ratio = max_count / n
            total_agreement += agreement_ratio
        
        # 平均一致率
        po = total_agreement / len(all_keys)
        
        # 期望一致率 (简化)
        pe = 1 / n
        
        if pe >= 1:
            return 1.0
        
        kappa = (po - pe) / (1 - pe)
        
        return max(-1.0, min(1.0, kappa))
    
    async def get_scores_by_project(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[QualityScore]:
        """
        获取项目的质量评分列表
        
        Args:
            project_id: 项目ID
            start_date: 开始日期 (可选)
            end_date: 结束日期 (可选)
            
        Returns:
            评分列表
        """
        scores = [
            s for s in self._scores.values()
            if s.project_id == project_id
        ]
        
        if start_date:
            scores = [s for s in scores if s.scored_at >= start_date]
        if end_date:
            scores = [s for s in scores if s.scored_at <= end_date]
        
        return scores
    
    async def get_annotator_scores(
        self,
        annotator_id: str,
        project_id: Optional[str] = None
    ) -> List[QualityScore]:
        """
        获取标注员的质量评分列表
        
        Args:
            annotator_id: 标注员ID
            project_id: 项目ID (可选)
            
        Returns:
            评分列表
        """
        scores = [
            s for s in self._scores.values()
            if s.annotator_id == annotator_id
        ]
        
        if project_id:
            scores = [s for s in scores if s.project_id == project_id]
        
        return scores


# 独立函数 (用于属性测试)
def calculate_weighted_score(
    scores: Dict[str, float],
    weights: Dict[str, float]
) -> float:
    """
    计算加权综合分数 (独立函数)
    
    Args:
        scores: 各维度分数
        weights: 各维度权重
        
    Returns:
        综合分数 (0-1)
    """
    if not scores:
        return 0.0
    
    # 确保所有分数在0-1范围内
    normalized_scores = {
        k: max(0.0, min(1.0, v)) for k, v in scores.items()
    }
    
    # 只计算有分数的维度
    available_weights = {
        dim: weight for dim, weight in weights.items()
        if dim in normalized_scores
    }
    
    if not available_weights:
        # 如果没有匹配的权重，使用平均值
        return sum(normalized_scores.values()) / len(normalized_scores)
    
    total_weight = sum(available_weights.values())
    if total_weight <= 0:
        return sum(normalized_scores.values()) / len(normalized_scores)
    
    weighted_sum = sum(
        normalized_scores.get(dim, 0) * weight
        for dim, weight in available_weights.items()
    )
    
    result = weighted_sum / total_weight
    
    # 确保结果在0-1范围内
    return max(0.0, min(1.0, result))


def calculate_cohens_kappa(
    annotation1: Dict[str, Any],
    annotation2: Dict[str, Any]
) -> float:
    """
    计算 Cohen's Kappa 系数 (独立函数)
    
    Args:
        annotation1: 第一个标注
        annotation2: 第二个标注
        
    Returns:
        Kappa系数 (-1 到 1)
    """
    # 获取所有键
    all_keys = set(annotation1.keys()) | set(annotation2.keys())
    
    if not all_keys:
        return 1.0
    
    # 计算一致的数量
    agreements = 0
    for key in all_keys:
        val1 = annotation1.get(key)
        val2 = annotation2.get(key)
        if val1 == val2:
            agreements += 1
    
    # 观察一致率
    po = agreements / len(all_keys)
    
    # 期望一致率 (简化计算)
    pe = 0.5
    
    if pe >= 1:
        return 1.0
    
    kappa = (po - pe) / (1 - pe)
    
    return max(-1.0, min(1.0, kappa))
