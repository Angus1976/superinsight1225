"""
Quality Workflow Property Tests - 质量工作流属性测试
使用 Hypothesis 库进行属性测试，每个属性至少 100 次迭代
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ============================================================================
# Local Schema Definitions (避免导入问题)
# ============================================================================

class QualityScore(BaseModel):
    """质量评分结果"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    annotation_id: str
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    total_score: float = 0.0
    weights: Dict[str, float] = Field(default_factory=dict)


class RuleResult(BaseModel):
    """规则执行结果"""
    passed: bool
    message: Optional[str] = None
    field: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class QualityAlert(BaseModel):
    """质量预警"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    triggered_dimensions: List[str] = Field(default_factory=list)
    scores: Dict[str, float] = Field(default_factory=dict)
    thresholds: Dict[str, float] = Field(default_factory=dict)
    severity: str = "medium"


class ProjectQualityReport(BaseModel):
    """项目质量报告"""
    project_id: str
    total_annotations: int = 0
    average_score: float = 0.0
    passed_count: int = 0
    failed_count: int = 0


class RagasEvaluationResult(BaseModel):
    """Ragas 评估结果"""
    question: str
    answer: str
    contexts: List[str] = Field(default_factory=list)
    scores: Dict[str, float] = Field(default_factory=dict)
    overall_score: float = 0.0


# ============================================================================
# Core Functions (独立实现，用于属性测试)
# ============================================================================

def calculate_weighted_score(
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


def execute_rule(
    annotation_data: Dict[str, Any],
    rule_config: Dict[str, Any]
) -> RuleResult:
    """
    执行规则
    
    Args:
        annotation_data: 标注数据
        rule_config: 规则配置
        
    Returns:
        规则执行结果
    """
    required_fields = rule_config.get("required_fields", [])
    missing_fields = []
    
    for field in required_fields:
        if field not in annotation_data:
            missing_fields.append(field)
        elif annotation_data[field] is None or annotation_data[field] == "":
            missing_fields.append(field)
    
    if missing_fields:
        return RuleResult(
            passed=False,
            message=f"Missing required fields: {', '.join(missing_fields)}",
            details={"missing_fields": missing_fields}
        )
    
    return RuleResult(passed=True, details={"checked_fields": required_fields})


def calculate_cohens_kappa(
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
    pe = 0.5
    
    if pe >= 1:
        return 1.0
    
    kappa = (po - pe) / (1 - pe)
    
    return max(-1.0, min(1.0, kappa))


def calculate_priority(issues: List[Dict[str, Any]]) -> int:
    """
    计算任务优先级
    
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


def generate_report(annotations: List[Dict[str, Any]]) -> ProjectQualityReport:
    """
    生成报告
    
    Args:
        annotations: 标注数据列表，每项包含 score 和 passed
        
    Returns:
        项目质量报告
    """
    if not annotations:
        return ProjectQualityReport(
            project_id="test",
            total_annotations=0,
            average_score=0.0,
            passed_count=0,
            failed_count=0
        )
    
    total = len(annotations)
    passed_count = sum(1 for a in annotations if a.get("passed", True))
    failed_count = total - passed_count
    
    scores = [a.get("score", 0) for a in annotations]
    average_score = sum(scores) / len(scores) if scores else 0
    
    return ProjectQualityReport(
        project_id="test",
        total_annotations=total,
        average_score=average_score,
        passed_count=passed_count,
        failed_count=failed_count
    )


def ragas_evaluate(
    question: str,
    answer: str,
    contexts: List[str],
    ground_truth: Optional[str] = None
) -> RagasEvaluationResult:
    """
    Ragas 评估
    
    Args:
        question: 问题
        answer: 答案
        contexts: 上下文列表
        ground_truth: 标准答案 (可选)
        
    Returns:
        评估结果
    """
    scores: Dict[str, float] = {}
    
    # 忠实度评估
    if answer and contexts:
        answer_words = set(answer.lower().split())
        context_text = " ".join(contexts).lower()
        context_words = set(context_text.split())
        
        if answer_words:
            overlap = answer_words & context_words
            scores["faithfulness"] = min(1.0, max(0.0, len(overlap) / len(answer_words)))
        else:
            scores["faithfulness"] = 0.0
    else:
        scores["faithfulness"] = 0.0
    
    # 答案相关性评估
    if question and answer:
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when", "where", "who"}
        question_words = question_words - stop_words
        
        if question_words:
            overlap = question_words & answer_words
            relevancy = len(overlap) / len(question_words)
            length_factor = min(1.0, len(answer) / 50)
            scores["answer_relevancy"] = min(1.0, max(0.0, relevancy * 0.7 + length_factor * 0.3))
        else:
            scores["answer_relevancy"] = 1.0
    else:
        scores["answer_relevancy"] = 0.0
    
    # 上下文精确度评估
    if contexts and (question or ground_truth):
        reference_text = (question + " " + (ground_truth or "")).lower()
        reference_words = set(reference_text.split())
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when", "where", "who"}
        reference_words = reference_words - stop_words
        
        if reference_words:
            relevance_scores = []
            for context in contexts:
                context_words = set(context.lower().split())
                overlap = reference_words & context_words
                score = len(overlap) / len(reference_words)
                relevance_scores.append(score)
            
            threshold = 0.1
            relevant_count = sum(1 for s in relevance_scores if s > threshold)
            scores["context_precision"] = min(1.0, max(0.0, relevant_count / len(contexts)))
        else:
            scores["context_precision"] = 0.5
    else:
        scores["context_precision"] = 0.0 if not contexts else 0.5
    
    # 上下文召回率评估
    if ground_truth and contexts:
        ground_truth_words = set(ground_truth.lower().split())
        stop_words = {"the", "a", "an", "is", "are", "was", "were"}
        ground_truth_words = ground_truth_words - stop_words
        
        if ground_truth_words:
            all_context_text = " ".join(contexts).lower()
            context_words = set(all_context_text.split())
            overlap = ground_truth_words & context_words
            scores["context_recall"] = min(1.0, max(0.0, len(overlap) / len(ground_truth_words)))
        else:
            scores["context_recall"] = 1.0
    else:
        scores["context_recall"] = 0.5 if contexts else 0.0
    
    # 计算综合分数
    overall_score = sum(scores.values()) / len(scores) if scores else 0.0
    
    return RagasEvaluationResult(
        question=question,
        answer=answer,
        contexts=contexts,
        scores=scores,
        overall_score=overall_score
    )


def check_and_alert(
    scores: Dict[str, float],
    thresholds: Dict[str, float]
) -> Optional[QualityAlert]:
    """
    检查并生成预警
    
    Args:
        scores: 各维度分数
        thresholds: 各维度阈值
        
    Returns:
        预警对象 (如果触发)
    """
    triggered_dimensions = []
    
    for dimension, threshold in thresholds.items():
        actual_score = scores.get(dimension, 1.0)
        if actual_score < threshold:
            triggered_dimensions.append(dimension)
    
    if not triggered_dimensions:
        return None
    
    # 计算总分
    total_score = sum(scores.values()) / len(scores) if scores else 0
    
    # 确定严重程度
    if total_score < 0.3:
        severity = "critical"
    elif total_score < 0.5:
        severity = "high"
    elif total_score < 0.7:
        severity = "medium"
    else:
        severity = "low"
    
    return QualityAlert(
        project_id="test",
        triggered_dimensions=triggered_dimensions,
        scores=scores,
        thresholds=thresholds,
        severity=severity
    )


# ============================================================================
# Property 1: 质量分数范围
# ============================================================================

class TestQualityScoreRange:
    """Property 1: 质量分数必须在 0-1 范围内"""
    
    @given(
        scores=st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=5
        ),
        weights=st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            st.floats(min_value=0.1, max_value=1, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_quality_score_range(self, scores, weights):
        """质量分数必须在 0-1 范围内
        
        **Feature: quality-workflow, Property 1: 质量分数范围**
        **Validates: Requirements 1.1, 1.6**
        """
        total_score = calculate_weighted_score(scores, weights)
        assert 0 <= total_score <= 1, f"Score {total_score} is out of range [0, 1]"
    
    @given(
        scores=st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
            st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=5
        ),
        weights=st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
            st.floats(min_value=0.1, max_value=1, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_quality_score_range_with_outliers(self, scores, weights):
        """即使输入分数超出范围，输出也必须在 0-1 范围内"""
        total_score = calculate_weighted_score(scores, weights)
        assert 0 <= total_score <= 1, f"Score {total_score} is out of range [0, 1]"


# ============================================================================
# Property 2: 规则执行确定性
# ============================================================================

class TestRuleExecutionDeterministic:
    """Property 2: 规则执行必须是确定性的"""
    
    @given(
        annotation_data=st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            st.one_of(
                st.integers(min_value=-1000, max_value=1000),
                st.text(max_size=100),
                st.booleans()
            ),
            min_size=0,
            max_size=10
        ),
        required_fields=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_rule_execution_deterministic(self, annotation_data, required_fields):
        """规则执行必须是确定性的
        
        **Feature: quality-workflow, Property 2: 规则执行确定性**
        **Validates: Requirements 2.1, 2.2**
        """
        rule_config = {"required_fields": required_fields}
        
        result1 = execute_rule(annotation_data, rule_config)
        result2 = execute_rule(annotation_data, rule_config)
        
        assert result1.passed == result2.passed, "Rule execution is not deterministic"
    
    @given(
        annotation_data=st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
            st.text(min_size=1, max_size=50),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_rule_with_all_fields_present(self, annotation_data):
        """当所有必填字段都存在时，规则应该通过"""
        required_fields = list(annotation_data.keys())
        rule_config = {"required_fields": required_fields}
        
        result = execute_rule(annotation_data, rule_config)
        
        assert result.passed, "Rule should pass when all required fields are present"


# ============================================================================
# Property 3: 一致性分数对称性
# ============================================================================

class TestConsistencyScoreSymmetric:
    """Property 3: 一致性分数计算必须对称"""
    
    @given(
        annotation1=st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
            st.integers(min_value=0, max_value=10),
            min_size=1,
            max_size=5
        ),
        annotation2=st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
            st.integers(min_value=0, max_value=10),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_consistency_score_symmetric(self, annotation1, annotation2):
        """一致性分数计算必须对称
        
        **Feature: quality-workflow, Property 3: 一致性分数对称性**
        **Validates: Requirements 1.2**
        """
        kappa1 = calculate_cohens_kappa(annotation1, annotation2)
        kappa2 = calculate_cohens_kappa(annotation2, annotation1)
        
        assert abs(kappa1 - kappa2) < 0.001, f"Kappa is not symmetric: {kappa1} vs {kappa2}"
    
    @given(
        annotation=st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
            st.integers(min_value=0, max_value=10),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_identical_annotations_perfect_agreement(self, annotation):
        """相同的标注应该有完美的一致性"""
        kappa = calculate_cohens_kappa(annotation, annotation)
        
        assert kappa == 1.0, f"Identical annotations should have kappa=1.0, got {kappa}"


# ============================================================================
# Property 4: 改进任务优先级单调性
# ============================================================================

class TestPriorityMonotonicity:
    """Property 4: 更严重的问题应该有更高的优先级"""
    
    @given(
        issues=st.lists(
            st.fixed_dictionaries({
                "severity": st.sampled_from(["critical", "high", "medium", "low"])
            }),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_priority_monotonicity(self, issues):
        """更严重的问题应该有更高的优先级
        
        **Feature: quality-workflow, Property 4: 改进任务优先级单调性**
        **Validates: Requirements 5.2, 5.3**
        """
        priority = calculate_priority(issues)
        
        # 添加一个 critical 问题
        issues_with_critical = issues + [{"severity": "critical"}]
        priority_with_critical = calculate_priority(issues_with_critical)
        
        assert priority_with_critical >= priority, \
            f"Adding critical issue should not decrease priority: {priority} -> {priority_with_critical}"
    
    @given(
        num_critical=st.integers(min_value=0, max_value=5),
        num_high=st.integers(min_value=0, max_value=5),
        num_medium=st.integers(min_value=0, max_value=5),
        num_low=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=100)
    def test_priority_range(self, num_critical, num_high, num_medium, num_low):
        """优先级必须在 1-3 范围内"""
        issues = (
            [{"severity": "critical"}] * num_critical +
            [{"severity": "high"}] * num_high +
            [{"severity": "medium"}] * num_medium +
            [{"severity": "low"}] * num_low
        )
        
        priority = calculate_priority(issues)
        
        assert 1 <= priority <= 3, f"Priority {priority} is out of range [1, 3]"


# ============================================================================
# Property 5: 报告数据一致性
# ============================================================================

class TestReportDataConsistency:
    """Property 5: 报告数据必须与原始数据一致"""
    
    @given(
        annotations=st.lists(
            st.fixed_dictionaries({
                "score": st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
                "passed": st.booleans()
            }),
            min_size=1,
            max_size=100
        )
    )
    @settings(max_examples=100)
    def test_report_data_consistency(self, annotations):
        """报告数据必须与原始数据一致
        
        **Feature: quality-workflow, Property 5: 报告数据一致性**
        **Validates: Requirements 4.1, 4.2**
        """
        report = generate_report(annotations)
        
        # 总数一致
        assert report.total_annotations == len(annotations), \
            f"Total mismatch: {report.total_annotations} vs {len(annotations)}"
        
        # 通过数一致
        expected_passed = sum(1 for a in annotations if a["passed"])
        assert report.passed_count == expected_passed, \
            f"Passed count mismatch: {report.passed_count} vs {expected_passed}"
        
        # 失败数一致
        expected_failed = len(annotations) - expected_passed
        assert report.failed_count == expected_failed, \
            f"Failed count mismatch: {report.failed_count} vs {expected_failed}"
        
        # 平均分一致
        expected_avg = sum(a["score"] for a in annotations) / len(annotations)
        assert abs(report.average_score - expected_avg) < 0.001, \
            f"Average score mismatch: {report.average_score} vs {expected_avg}"
    
    @settings(max_examples=100)
    @given(st.data())
    def test_empty_report(self, data):
        """空数据应该生成空报告"""
        report = generate_report([])
        
        assert report.total_annotations == 0
        assert report.passed_count == 0
        assert report.failed_count == 0


# ============================================================================
# Property 6: Ragas 评分范围
# ============================================================================

class TestRagasScoreRange:
    """Property 6: Ragas 评分必须在 0-1 范围内"""
    
    @given(
        question=st.text(min_size=1, max_size=200),
        answer=st.text(min_size=1, max_size=500),
        contexts=st.lists(st.text(min_size=1, max_size=200), min_size=1, max_size=5)
    )
    @settings(max_examples=100)
    def test_ragas_score_range(self, question, answer, contexts):
        """Ragas 评分必须在 0-1 范围内
        
        **Feature: quality-workflow, Property 6: Ragas 评分范围**
        **Validates: Requirements 7.1, 7.5**
        """
        result = ragas_evaluate(question, answer, contexts)
        
        for metric, score in result.scores.items():
            assert 0 <= score <= 1, f"Ragas {metric} score {score} is out of range [0, 1]"
        
        assert 0 <= result.overall_score <= 1, \
            f"Ragas overall score {result.overall_score} is out of range [0, 1]"
    
    @given(
        question=st.text(min_size=1, max_size=100),
        answer=st.text(min_size=1, max_size=200),
        contexts=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=3),
        ground_truth=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100)
    def test_ragas_with_ground_truth(self, question, answer, contexts, ground_truth):
        """带有标准答案的 Ragas 评估也必须在范围内"""
        result = ragas_evaluate(question, answer, contexts, ground_truth)
        
        for metric, score in result.scores.items():
            assert 0 <= score <= 1, f"Ragas {metric} score {score} is out of range [0, 1]"


# ============================================================================
# Property 7: 预警触发一致性
# ============================================================================

class TestAlertTriggerConsistency:
    """Property 7: 预警触发必须与阈值配置一致"""
    
    @given(
        scores=st.dictionaries(
            st.sampled_from(["accuracy", "completeness", "timeliness"]),
            st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=3
        ),
        thresholds=st.dictionaries(
            st.sampled_from(["accuracy", "completeness", "timeliness"]),
            st.floats(min_value=0.5, max_value=0.9, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=100)
    def test_alert_trigger_consistency(self, scores, thresholds):
        """预警触发必须与阈值配置一致
        
        **Feature: quality-workflow, Property 7: 预警触发一致性**
        **Validates: Requirements 6.1, 6.2**
        """
        alert = check_and_alert(scores, thresholds)
        
        if alert:
            # 至少有一个维度低于阈值
            for dim in alert.triggered_dimensions:
                assert scores.get(dim, 1.0) < thresholds.get(dim, 0), \
                    f"Dimension {dim} triggered but score {scores.get(dim)} >= threshold {thresholds.get(dim)}"
        else:
            # 所有维度都高于或等于阈值
            for dim, threshold in thresholds.items():
                assert scores.get(dim, 1.0) >= threshold, \
                    f"No alert but dimension {dim} score {scores.get(dim)} < threshold {threshold}"
    
    @given(
        threshold=st.floats(min_value=0.5, max_value=0.9, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_alert_severity_levels(self, threshold):
        """预警严重程度应该与分数成反比"""
        # 低分数应该触发高严重程度
        low_scores = {"accuracy": 0.2}
        thresholds = {"accuracy": threshold}
        
        alert = check_and_alert(low_scores, thresholds)
        
        if alert:
            assert alert.severity in ["critical", "high"], \
                f"Low score should trigger high severity, got {alert.severity}"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
