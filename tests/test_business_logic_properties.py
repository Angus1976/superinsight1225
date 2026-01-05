#!/usr/bin/env python3
"""
业务逻辑属性测试
使用 Hypothesis 框架测试业务逻辑的正确性属性

实现需求 13: 客户业务逻辑提炼与智能化

属性测试:
- 属性 11: 业务规则置信度单调性 (验证: 需求 13.6)
- 属性 12: 业务模式检测一致性 (验证: 需求 13.1, 13.2)  
- 属性 13: 业务逻辑变化追踪完整性 (验证: 需求 13.7)
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
import numpy as np

# Hypothesis imports
from hypothesis import given, strategies as st, settings, assume, example
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, initialize

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.business_logic.extractor import (
    BusinessLogicExtractor, PatternType, RuleType, 
    BusinessRule, Pattern, PatternAnalysis, AnnotationExample
)
from src.business_logic.service import BusinessLogicService
from src.business_logic.models import (
    RuleTypeEnum, PatternTypeEnum, InsightTypeEnum
)

# Hypothesis strategies for generating test data

@st.composite
def annotation_data(draw):
    """生成标注数据的策略"""
    # 使用固定的时间范围避免flaky测试
    base_time = datetime(2026, 1, 1)
    return {
        "id": draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        "text": draw(st.text(min_size=5, max_size=200)),
        "sentiment": draw(st.sampled_from(["positive", "negative", "neutral"])),
        "rating": draw(st.integers(min_value=1, max_value=5)),
        "annotator": draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        "created_at": base_time + timedelta(days=draw(st.integers(min_value=0, max_value=30)))
    }

@st.composite
def annotation_list(draw, min_size=1, max_size=50):
    """生成标注数据列表的策略"""
    return draw(st.lists(annotation_data(), min_size=min_size, max_size=max_size))

@st.composite
def business_rule_data(draw):
    """生成业务规则数据的策略"""
    # 使用固定的时间范围避免flaky测试
    base_time = datetime(2026, 1, 1)
    created_time = base_time + timedelta(days=draw(st.integers(min_value=0, max_value=30)))
    updated_time = created_time + timedelta(hours=draw(st.integers(min_value=0, max_value=24)))
    
    return BusinessRule(
        id=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        name=draw(st.text(min_size=1, max_size=100)),
        description=draw(st.text(min_size=1, max_size=200)),
        pattern=draw(st.text(min_size=10, max_size=100)),
        rule_type=draw(st.sampled_from(list(RuleType))),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        frequency=draw(st.integers(min_value=0, max_value=1000)),
        examples=[],
        is_active=draw(st.booleans()),
        created_at=created_time,
        updated_at=updated_time
    )


class TestBusinessLogicProperties:
    """业务逻辑属性测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.extractor = BusinessLogicExtractor()
        self.service = BusinessLogicService()


class TestProperty11RuleConfidenceMonotonicity:
    """
    属性 11: 业务规则置信度单调性
    验证: 需求 13.6 - 业务规则置信度评分
    
    属性: 对于任何业务规则，随着支持数据的增加，置信度应该单调递增或保持稳定
    """
    
    def setup_method(self):
        """测试前设置"""
        self.extractor = BusinessLogicExtractor()
    
    @given(
        initial_frequency=st.integers(min_value=1, max_value=50),
        additional_frequency=st.integers(min_value=1, max_value=50),
        initial_examples=st.integers(min_value=0, max_value=20),
        additional_examples=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=100, deadline=5000)
    def test_confidence_monotonicity_with_frequency(
        self, 
        initial_frequency, 
        additional_frequency,
        initial_examples,
        additional_examples
    ):
        """
        **Feature: superinsight-platform, Property 11: 业务规则置信度单调性**
        **Validates: Requirements 13.6**
        
        测试随着频率增加，置信度单调递增或保持稳定
        """
        # 创建初始规则
        initial_rule = BusinessRule(
            id="test_rule_001",
            name="测试规则",
            description="测试规则描述",
            pattern="IF text CONTAINS 'test' THEN sentiment = 'positive'",
            rule_type=RuleType.SENTIMENT_RULE,
            confidence=0.0,
            frequency=initial_frequency,
            examples=[
                AnnotationExample(
                    id=f"ex_{i}",
                    text=f"test example {i}",
                    annotation={"sentiment": "positive"},
                    timestamp=datetime.now(),
                    annotator="user_001"
                ) for i in range(initial_examples)
            ],
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 计算初始置信度
        initial_confidence = self.extractor.calculate_rule_confidence(initial_rule)
        
        # 创建增强后的规则（更多频率和示例）
        enhanced_rule = BusinessRule(
            id="test_rule_001",
            name="测试规则",
            description="测试规则描述",
            pattern="IF text CONTAINS 'test' THEN sentiment = 'positive'",
            rule_type=RuleType.SENTIMENT_RULE,
            confidence=0.0,
            frequency=initial_frequency + additional_frequency,
            examples=[
                AnnotationExample(
                    id=f"ex_{i}",
                    text=f"test example {i}",
                    annotation={"sentiment": "positive"},
                    timestamp=datetime.now(),
                    annotator="user_001"
                ) for i in range(initial_examples + additional_examples)
            ],
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 计算增强后的置信度
        enhanced_confidence = self.extractor.calculate_rule_confidence(enhanced_rule)
        
        # 验证单调性：增强后的置信度应该 >= 初始置信度
        assert enhanced_confidence >= initial_confidence, (
            f"置信度单调性违反: 初始置信度 {initial_confidence}, "
            f"增强后置信度 {enhanced_confidence}"
        )
    
    @given(business_rule_data())
    @settings(max_examples=50, deadline=3000)
    def test_confidence_bounds(self, rule):
        """
        **Feature: superinsight-platform, Property 11: 业务规则置信度边界**
        **Validates: Requirements 13.6**
        
        测试置信度计算结果在有效范围内 [0.0, 1.0]
        """
        confidence = self.extractor.calculate_rule_confidence(rule)
        
        assert 0.0 <= confidence <= 1.0, (
            f"置信度超出有效范围: {confidence}"
        )
        assert isinstance(confidence, float), (
            f"置信度应该是浮点数，实际类型: {type(confidence)}"
        )


class TestProperty12PatternDetectionConsistency:
    """
    属性 12: 业务模式检测一致性
    验证: 需求 13.1, 13.2 - 业务模式分析和识别
    
    属性: 对于任何相同的标注数据集，多次运行模式检测应该产生一致的结果
    """
    
    def setup_method(self):
        """测试前设置"""
        self.extractor = BusinessLogicExtractor()
    
    @given(annotation_list(min_size=5, max_size=30))
    @settings(max_examples=50, deadline=10000)
    def test_pattern_detection_consistency(self, annotations):
        """
        **Feature: superinsight-platform, Property 12: 业务模式检测一致性**
        **Validates: Requirements 13.1, 13.2**
        
        测试相同数据的多次模式检测结果一致性
        """
        # 确保数据有效性
        assume(len(annotations) >= 3)
        assume(all('text' in ann and len(ann['text']) > 0 for ann in annotations))
        
        # 第一次模式分析
        result1 = self.extractor.analyze_annotation_patterns(annotations)
        
        # 第二次模式分析（相同数据）
        result2 = self.extractor.analyze_annotation_patterns(annotations)
        
        # 验证基本一致性
        assert result1.total_annotations == result2.total_annotations, (
            f"标注总数不一致: {result1.total_annotations} vs {result2.total_annotations}"
        )
        
        assert len(result1.patterns) == len(result2.patterns), (
            f"模式数量不一致: {len(result1.patterns)} vs {len(result2.patterns)}"
        )
        
        # 验证模式类型一致性
        pattern_types1 = sorted([p.type.value for p in result1.patterns])
        pattern_types2 = sorted([p.type.value for p in result2.patterns])
        
        assert pattern_types1 == pattern_types2, (
            f"模式类型不一致: {pattern_types1} vs {pattern_types2}"
        )
        
        # 验证模式强度的稳定性（允许小的浮点误差）
        for p1, p2 in zip(
            sorted(result1.patterns, key=lambda x: x.type.value),
            sorted(result2.patterns, key=lambda x: x.type.value)
        ):
            if p1.type == p2.type:
                strength_diff = abs(p1.strength - p2.strength)
                assert strength_diff < 0.01, (
                    f"模式强度差异过大: {p1.type.value} - {p1.strength} vs {p2.strength}"
                )
    
    @given(
        annotations=annotation_list(min_size=10, max_size=20),
        threshold1=st.floats(min_value=0.1, max_value=0.9),
        threshold2=st.floats(min_value=0.1, max_value=0.9)
    )
    @settings(max_examples=30, deadline=8000)
    def test_pattern_detection_threshold_consistency(self, annotations, threshold1, threshold2):
        """
        **Feature: superinsight-platform, Property 12: 模式检测阈值一致性**
        **Validates: Requirements 13.1, 13.2**
        
        测试不同置信度阈值下的模式检测一致性
        """
        assume(len(annotations) >= 5)
        assume(all('text' in ann and len(ann['text']) > 0 for ann in annotations))
        assume(abs(threshold1 - threshold2) > 0.1)  # 确保阈值有显著差异
        
        # 使用不同阈值创建提取器
        extractor1 = BusinessLogicExtractor(confidence_threshold=threshold1)
        extractor2 = BusinessLogicExtractor(confidence_threshold=threshold2)
        
        # 分别进行模式分析
        result1 = extractor1.analyze_annotation_patterns(annotations)
        result2 = extractor2.analyze_annotation_patterns(annotations)
        
        # 验证基本数据一致性
        assert result1.total_annotations == result2.total_annotations
        
        # 验证阈值设置正确
        assert result1.confidence_threshold == threshold1
        assert result2.confidence_threshold == threshold2
        
        # 较高阈值应该产生更少或相等的模式
        if threshold1 > threshold2:
            assert len(result1.patterns) <= len(result2.patterns), (
                f"高阈值应产生更少模式: threshold1={threshold1} patterns={len(result1.patterns)}, "
                f"threshold2={threshold2} patterns={len(result2.patterns)}"
            )


class TestProperty13ChangeTrackingCompleteness:
    """
    属性 13: 业务逻辑变化追踪完整性
    验证: 需求 13.7 - 业务逻辑变化追踪
    
    属性: 对于任何业务逻辑的变化，系统应该完整记录变化的时间、内容和影响范围
    """
    
    def setup_method(self):
        """测试前设置"""
        self.service = BusinessLogicService()
    
    @given(
        project_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        time_window=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=30, deadline=5000)
    @pytest.mark.asyncio
    async def test_change_detection_completeness(self, project_id, time_window):
        """
        **Feature: superinsight-platform, Property 13: 业务逻辑变化追踪完整性**
        **Validates: Requirements 13.7**
        
        测试变化检测的完整性
        """
        from src.business_logic.models import ChangeDetectionRequest
        
        request = ChangeDetectionRequest(
            project_id=project_id,
            time_window_days=time_window
        )
        
        # 执行变化检测
        response = await self.service.detect_pattern_changes(request)
        
        # 验证响应完整性
        assert response.project_id == project_id
        assert response.time_window_days == time_window
        assert response.detection_timestamp is not None
        assert isinstance(response.changes_detected, list)
        assert isinstance(response.change_summary, dict)
        
        # 验证每个检测到的变化都包含必要信息
        for change in response.changes_detected:
            assert isinstance(change, dict)
            assert "type" in change, "变化记录必须包含类型"
            assert "description" in change, "变化记录必须包含描述"
            assert "detected_at" in change, "变化记录必须包含检测时间"
            
            # 验证时间戳有效性
            if isinstance(change["detected_at"], datetime):
                # 检测时间应该在合理范围内
                now = datetime.now()
                time_diff = abs((now - change["detected_at"]).total_seconds())
                assert time_diff <= time_window * 24 * 3600 + 3600, (
                    f"变化检测时间超出时间窗口: {change['detected_at']}"
                )
        
        # 验证变化摘要完整性
        summary = response.change_summary
        assert "total_changes" in summary, "摘要必须包含总变化数"
        assert isinstance(summary["total_changes"], int)
        assert summary["total_changes"] >= 0
        
        # 验证总变化数与详细变化列表一致
        assert summary["total_changes"] == len(response.changes_detected), (
            f"摘要中的总变化数 {summary['total_changes']} 与实际变化列表长度 {len(response.changes_detected)} 不一致"
        )
    
    @given(
        annotations_before=annotation_list(min_size=5, max_size=15),
        annotations_after=annotation_list(min_size=5, max_size=15)
    )
    @settings(max_examples=20, deadline=8000)
    def test_pattern_change_tracking(self, annotations_before, annotations_after):
        """
        **Feature: superinsight-platform, Property 13: 模式变化追踪**
        **Validates: Requirements 13.7**
        
        测试模式变化的追踪完整性
        """
        assume(len(annotations_before) >= 3)
        assume(len(annotations_after) >= 3)
        assume(all('text' in ann and len(ann['text']) > 0 for ann in annotations_before))
        assume(all('text' in ann and len(ann['text']) > 0 for ann in annotations_after))
        
        extractor = BusinessLogicExtractor()
        
        # 分析变化前的模式
        patterns_before = extractor.analyze_annotation_patterns(annotations_before)
        
        # 分析变化后的模式
        patterns_after = extractor.analyze_annotation_patterns(annotations_after)
        
        # 验证模式变化可以被检测
        # 如果数据不同，应该能够识别出差异
        if annotations_before != annotations_after:
            # 至少应该有一些可检测的差异
            total_patterns_before = len(patterns_before.patterns)
            total_patterns_after = len(patterns_after.patterns)
            
            # 验证分析结果的有效性
            assert patterns_before.total_annotations == len(annotations_before)
            assert patterns_after.total_annotations == len(annotations_after)
            
            # 如果标注数量发生变化，这应该被记录
            if len(annotations_before) != len(annotations_after):
                assert patterns_before.total_annotations != patterns_after.total_annotations
    
    @given(
        rule=business_rule_data(),
        confidence_change=st.floats(min_value=-0.5, max_value=0.5)
    )
    @settings(max_examples=30, deadline=3000)
    def test_rule_confidence_change_tracking(self, rule, confidence_change):
        """
        **Feature: superinsight-platform, Property 13: 规则置信度变化追踪**
        **Validates: Requirements 13.7**
        
        测试规则置信度变化的追踪
        """
        assume(0.0 <= rule.confidence + confidence_change <= 1.0)
        
        extractor = BusinessLogicExtractor()
        
        # 记录原始置信度
        original_confidence = rule.confidence
        
        # 模拟置信度变化
        modified_rule = BusinessRule(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            pattern=rule.pattern,
            rule_type=rule.rule_type,
            confidence=rule.confidence + confidence_change,
            frequency=rule.frequency,
            examples=rule.examples,
            is_active=rule.is_active,
            created_at=rule.created_at,
            updated_at=max(rule.updated_at, datetime.now())  # 确保更新时间不早于创建时间
        )
        
        # 验证变化可以被检测
        if abs(confidence_change) > 0.01:  # 只有显著变化才需要追踪
            assert modified_rule.confidence != original_confidence
            assert modified_rule.updated_at >= rule.created_at  # 更新时间应该不早于创建时间
            
            # 验证变化幅度
            actual_change = modified_rule.confidence - original_confidence
            assert abs(actual_change - confidence_change) < 0.001, (
                f"置信度变化不准确: 期望 {confidence_change}, 实际 {actual_change}"
            )


class BusinessLogicStateMachine(RuleBasedStateMachine):
    """
    业务逻辑状态机测试
    使用状态机测试复杂的业务逻辑交互
    """
    
    rules = Bundle('rules')
    patterns = Bundle('patterns')
    
    def __init__(self):
        super().__init__()
        self.extractor = BusinessLogicExtractor()
        self.service = BusinessLogicService()
        self.project_id = "test_project_stateful"
        self.annotations = []
        self.extracted_rules = []
        self.detected_patterns = []
    
    @initialize()
    def setup(self):
        """初始化状态机"""
        self.annotations = []
        self.extracted_rules = []
        self.detected_patterns = []
    
    @rule(
        annotation=annotation_data()
    )
    def add_annotation(self, annotation):
        """添加标注数据"""
        self.annotations.append(annotation)
    
    @rule()
    def analyze_patterns(self):
        """分析业务模式"""
        if len(self.annotations) >= 3:
            result = self.extractor.analyze_annotation_patterns(self.annotations)
            self.detected_patterns = result.patterns
            
            # 验证分析结果的一致性
            assert result.total_annotations == len(self.annotations)
            assert len(result.patterns) >= 0
    
    @rule()
    def extract_rules(self):
        """提取业务规则"""
        if len(self.annotations) >= 5:
            rules = self.extractor.extract_business_rules(self.project_id)
            self.extracted_rules = rules
            
            # 验证规则提取的一致性
            assert isinstance(rules, list)
            for rule in rules:
                assert 0.0 <= rule.confidence <= 1.0
                assert rule.frequency >= 0
    
    @rule()
    def verify_consistency(self):
        """验证状态一致性"""
        # 验证标注数据和分析结果的一致性
        if self.detected_patterns:
            # 如果有检测到的模式，应该有足够的标注数据
            assert len(self.annotations) >= 1
        
        if self.extracted_rules:
            # 如果有提取的规则，应该有足够的标注数据
            assert len(self.annotations) >= 1
            
            # 验证规则的有效性
            for rule in self.extracted_rules:
                assert isinstance(rule.confidence, float)
                assert 0.0 <= rule.confidence <= 1.0


# 运行状态机测试
TestBusinessLogicStateMachine = BusinessLogicStateMachine.TestCase


if __name__ == "__main__":
    # 运行属性测试
    pytest.main([__file__, "-v", "--tb=short", "-x"])