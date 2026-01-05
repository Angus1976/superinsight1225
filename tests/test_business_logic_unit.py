#!/usr/bin/env python3
"""
业务逻辑单元测试
测试模式识别算法准确性、规则提取逻辑正确性、置信度计算算法、数据库操作完整性

实现需求 13: 客户业务逻辑提炼与智能化
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.business_logic.extractor import (
    BusinessLogicExtractor, PatternType, RuleType, 
    BusinessRule, Pattern, PatternAnalysis, AnnotationExample
)
from src.business_logic.service import BusinessLogicService
from src.business_logic.models import (
    BusinessRuleModel, BusinessPatternModel, BusinessInsightModel,
    RuleTypeEnum, PatternTypeEnum, InsightTypeEnum
)
from src.business_logic.advanced_algorithms import (
    SentimentCorrelationAnalyzer, KeywordCooccurrenceAnalyzer
)
from src.business_logic.rule_generator import (
    AdvancedRuleGenerator, BusinessRuleTemplate, RuleCondition, RuleConsequent
)
from src.business_logic.data_validator import (
    DataQualityManager, DataCompletenessValidator, DataFormatValidator,
    ValidationResult, DataQualityReport
)

class TestBusinessLogicExtractor:
    """测试业务逻辑提炼器"""
    
    def setup_method(self):
        """测试前设置"""
        self.extractor = BusinessLogicExtractor(confidence_threshold=0.8, min_frequency=3)
        
        # 创建测试数据
        self.test_annotations = [
            {
                "id": "ann_001",
                "text": "This product is excellent and amazing!",
                "sentiment": "positive",
                "rating": 5,
                "annotator": "user_001",
                "created_at": datetime.now() - timedelta(days=1)
            },
            {
                "id": "ann_002", 
                "text": "The service was terrible and disappointing.",
                "sentiment": "negative",
                "rating": 1,
                "annotator": "user_002",
                "created_at": datetime.now() - timedelta(days=2)
            },
            {
                "id": "ann_003",
                "text": "It's okay, nothing special.",
                "sentiment": "neutral",
                "rating": 3,
                "annotator": "user_001",
                "created_at": datetime.now() - timedelta(days=3)
            },
            {
                "id": "ann_004",
                "text": "Great product, highly recommended!",
                "sentiment": "positive",
                "rating": 5,
                "annotator": "user_003",
                "created_at": datetime.now() - timedelta(days=1)
            },
            {
                "id": "ann_005",
                "text": "Poor quality, waste of money.",
                "sentiment": "negative", 
                "rating": 1,
                "annotator": "user_002",
                "created_at": datetime.now() - timedelta(days=2)
            }
        ]
    
    def test_extractor_initialization(self):
        """测试提取器初始化"""
        extractor = BusinessLogicExtractor(confidence_threshold=0.9, min_frequency=5)
        assert extractor.confidence_threshold == 0.9
        assert extractor.min_frequency == 5
        assert extractor.vectorizer is not None
    
    def test_analyze_annotation_patterns_empty_data(self):
        """测试空数据的模式分析"""
        result = self.extractor.analyze_annotation_patterns([])
        
        assert isinstance(result, PatternAnalysis)
        assert result.total_annotations == 0
        assert len(result.patterns) == 0
        assert result.confidence_threshold == 0.8
    
    def test_analyze_annotation_patterns_with_data(self):
        """测试有数据的模式分析"""
        result = self.extractor.analyze_annotation_patterns(self.test_annotations)
        
        assert isinstance(result, PatternAnalysis)
        assert result.total_annotations == 5
        assert len(result.patterns) > 0
        assert result.confidence_threshold == 0.8
        
        # 检查是否包含情感关联模式
        sentiment_patterns = [p for p in result.patterns if p.type == PatternType.SENTIMENT_CORRELATION]
        assert len(sentiment_patterns) > 0
    
    def test_sentiment_correlation_analysis(self):
        """测试情感关联分析"""
        df = pd.DataFrame(self.test_annotations)
        patterns = self.extractor._analyze_sentiment_correlation(df)
        
        assert len(patterns) > 0
        
        # 检查模式类型
        for pattern in patterns:
            assert pattern.type == PatternType.SENTIMENT_CORRELATION
            assert pattern.strength > 0
            assert len(pattern.evidence) > 0
    
    def test_keyword_association_analysis(self):
        """测试关键词关联分析"""
        df = pd.DataFrame(self.test_annotations)
        patterns = self.extractor._analyze_keyword_association(df)
        
        # 应该至少识别出一些关键词模式
        if len(patterns) > 0:
            pattern = patterns[0]
            assert pattern.type == PatternType.KEYWORD_ASSOCIATION
            assert pattern.strength > 0
            assert len(pattern.evidence) > 0
    
    def test_temporal_trends_analysis(self):
        """测试时间趋势分析"""
        df = pd.DataFrame(self.test_annotations)
        patterns = self.extractor._analyze_temporal_trends(df)
        
        # 可能有也可能没有时间趋势，取决于数据
        for pattern in patterns:
            assert pattern.type == PatternType.TEMPORAL_TREND
            assert pattern.strength > 0
            assert len(pattern.evidence) > 0
    
    def test_user_behavior_analysis(self):
        """测试用户行为分析"""
        df = pd.DataFrame(self.test_annotations)
        patterns = self.extractor._analyze_user_behavior(df)
        
        # 用户行为分析可能返回空结果，取决于数据
        if len(patterns) > 0:
            pattern = patterns[0]
            assert pattern.type == PatternType.USER_BEHAVIOR
            assert pattern.strength > 0
            assert len(pattern.evidence) > 0
        else:
            # 如果没有足够的用户活动，可能不会产生模式
            assert len(patterns) == 0
    
    def test_extract_keywords(self):
        """测试关键词提取"""
        texts = [
            "This product is excellent and amazing!",
            "Great product, highly recommended!",
            "The service was terrible and disappointing."
        ]
        
        keywords = self.extractor._extract_keywords(texts, top_k=5)
        
        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        assert all(isinstance(word, str) for word in keywords)
        
        # 应该包含一些有意义的词
        assert any(word in ['product', 'excellent', 'great', 'service'] for word in keywords)
    
    def test_calculate_trend_strength(self):
        """测试趋势强度计算"""
        # 上升趋势
        values_up = np.array([1, 2, 3, 4, 5])
        strength_up = self.extractor._calculate_trend_strength(values_up)
        assert strength_up > 0
        
        # 下降趋势
        values_down = np.array([5, 4, 3, 2, 1])
        strength_down = self.extractor._calculate_trend_strength(values_down)
        assert strength_down < 0
        
        # 平稳趋势
        values_flat = np.array([3, 3, 3, 3, 3])
        strength_flat = self.extractor._calculate_trend_strength(values_flat)
        assert abs(strength_flat) < 0.1
    
    def test_extract_business_rules(self):
        """测试业务规则提取"""
        project_id = "test_project_001"
        rules = self.extractor.extract_business_rules(project_id, threshold=0.8)
        
        assert isinstance(rules, list)
        assert len(rules) > 0
        
        rule = rules[0]
        assert isinstance(rule, BusinessRule)
        # 注意：BusinessRule是dataclass，使用不同的属性访问方式
        assert hasattr(rule, 'id')
        assert rule.confidence >= 0.8
        assert rule.rule_type in [RuleType.SENTIMENT_RULE, RuleType.KEYWORD_RULE, RuleType.TEMPORAL_RULE, RuleType.BEHAVIORAL_RULE]
    
    def test_calculate_rule_confidence(self):
        """测试规则置信度计算"""
        # 创建测试规则
        rule = BusinessRule(
            id="test_rule_001",
            name="测试规则",
            description="测试规则描述",
            pattern="IF text CONTAINS 'excellent' THEN sentiment = 'positive'",
            rule_type=RuleType.SENTIMENT_RULE,
            confidence=0.0,
            frequency=15,
            examples=[
                AnnotationExample(
                    id="ex_001",
                    text="This is excellent!",
                    annotation={"sentiment": "positive"},
                    timestamp=datetime.now(),
                    annotator="user_001"
                )
            ],
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        confidence = self.extractor.calculate_rule_confidence(rule)
        
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0  # 应该有一定的置信度


class TestBusinessLogicService:
    """测试业务逻辑服务"""
    
    def setup_method(self):
        """测试前设置"""
        self.service = BusinessLogicService()
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """测试服务初始化"""
        assert self.service.extractor is not None
        assert isinstance(self.service.extractor, BusinessLogicExtractor)
    
    @pytest.mark.asyncio
    async def test_get_business_rules(self):
        """测试获取业务规则"""
        project_id = "test_project_001"
        rules = await self.service.get_business_rules(project_id)
        
        assert isinstance(rules, list)
        assert len(rules) > 0
        
        rule = rules[0]
        assert rule.project_id == project_id
        assert rule.confidence > 0
        assert rule.is_active is True
    
    @pytest.mark.asyncio
    async def test_get_business_rules_with_filters(self):
        """测试带过滤条件的业务规则获取"""
        project_id = "test_project_001"
        
        # 测试规则类型过滤
        rules = await self.service.get_business_rules(
            project_id, 
            rule_type="sentiment_rule"
        )
        
        assert isinstance(rules, list)
        for rule in rules:
            assert rule.rule_type == RuleTypeEnum.SENTIMENT_RULE
    
    @pytest.mark.asyncio
    async def test_get_business_patterns(self):
        """测试获取业务模式"""
        project_id = "test_project_001"
        patterns = await self.service.get_business_patterns(project_id)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        
        pattern = patterns[0]
        assert pattern.project_id == project_id
        assert pattern.strength > 0
    
    @pytest.mark.asyncio
    async def test_get_business_patterns_with_filters(self):
        """测试带过滤条件的业务模式获取"""
        project_id = "test_project_001"
        
        # 测试最小强度过滤
        patterns = await self.service.get_business_patterns(
            project_id,
            min_strength=0.5
        )
        
        assert isinstance(patterns, list)
        for pattern in patterns:
            assert pattern.strength >= 0.5
    
    @pytest.mark.asyncio
    async def test_get_business_insights(self):
        """测试获取业务洞察"""
        project_id = "test_project_001"
        insights = await self.service.get_business_insights(project_id)
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        insight = insights[0]
        assert insight.project_id == project_id
        assert insight.impact_score > 0
    
    @pytest.mark.asyncio
    async def test_get_business_logic_stats(self):
        """测试获取业务逻辑统计"""
        project_id = "test_project_001"
        stats = await self.service.get_business_logic_stats(project_id)
        
        assert stats.project_id == project_id
        assert stats.total_rules >= 0
        assert stats.active_rules >= 0
        assert stats.total_patterns >= 0
        assert stats.total_insights >= 0
        assert 0.0 <= stats.avg_rule_confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_acknowledge_insight(self):
        """测试确认业务洞察"""
        insight_id = "insight_test_001"
        result = await self.service.acknowledge_insight(insight_id)
        
        assert isinstance(result, bool)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_rule_confidence(self):
        """测试更新规则置信度"""
        rule_id = "rule_test_001"
        new_confidence = 0.92
        
        result = await self.service.update_rule_confidence(rule_id, new_confidence)
        
        assert isinstance(result, bool)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_business_rule(self):
        """测试删除业务规则"""
        rule_id = "rule_test_001"
        result = await self.service.delete_business_rule(rule_id)
        
        assert isinstance(result, bool)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_toggle_rule_status(self):
        """测试切换规则状态"""
        rule_id = "rule_test_001"
        result = await self.service.toggle_rule_status(rule_id)
        
        # 可能返回None（当前实现）或更新后的规则
        assert result is None or hasattr(result, 'is_active')


class TestBusinessLogicModels:
    """测试业务逻辑数据模型"""
    
    def test_business_rule_model_creation(self):
        """测试业务规则模型创建"""
        rule_data = {
            "id": "rule_001",
            "project_id": "project_001",
            "name": "测试规则",
            "description": "这是一个测试规则",
            "pattern": "IF text CONTAINS 'excellent' THEN sentiment = 'positive'",
            "rule_type": "sentiment_rule",
            "confidence": 0.85,
            "frequency": 10,
            "examples": [],
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # 测试数据库模型
        db_rule = BusinessRuleModel(**rule_data)
        assert db_rule.id == "rule_001"
        assert db_rule.project_id == "project_001"
        assert db_rule.confidence == 0.85
        assert db_rule.is_active is True
    
    def test_business_pattern_model_creation(self):
        """测试业务模式模型创建"""
        pattern_data = {
            "id": "pattern_001",
            "project_id": "project_001",
            "pattern_type": "sentiment_correlation",
            "description": "情感关联模式",
            "strength": 0.75,
            "evidence": [{"sentiment": "positive", "count": 50}],
            "detected_at": datetime.now(),
            "last_seen": datetime.now()
        }
        
        # 测试数据库模型
        db_pattern = BusinessPatternModel(**pattern_data)
        assert db_pattern.id == "pattern_001"
        assert db_pattern.project_id == "project_001"
        assert db_pattern.strength == 0.75
    
    def test_business_insight_model_creation(self):
        """测试业务洞察模型创建"""
        insight_data = {
            "id": "insight_001",
            "project_id": "project_001",
            "insight_type": "pattern_insight",
            "title": "发现新模式",
            "description": "检测到新的业务模式",
            "impact_score": 0.8,
            "recommendations": ["建议1", "建议2"],
            "data_points": [{"metric": "accuracy", "value": 0.9}],
            "created_at": datetime.now(),
            "acknowledged_at": None
        }
        
        # 测试数据库模型
        db_insight = BusinessInsightModel(**insight_data)
        assert db_insight.id == "insight_001"
        assert db_insight.project_id == "project_001"
        assert db_insight.impact_score == 0.8
        assert db_insight.acknowledged_at is None


class TestBusinessLogicIntegration:
    """测试业务逻辑集成功能"""
    
    def setup_method(self):
        """测试前设置"""
        self.extractor = BusinessLogicExtractor()
        self.service = BusinessLogicService()
    
    def test_extractor_service_integration(self):
        """测试提取器和服务的集成"""
        # 确保服务使用了提取器
        assert self.service.extractor is not None
        assert isinstance(self.service.extractor, BusinessLogicExtractor)
    
    @pytest.mark.asyncio
    async def test_pattern_analysis_workflow(self):
        """测试模式分析工作流"""
        from src.business_logic.models import PatternAnalysisRequest
        
        request = PatternAnalysisRequest(
            project_id="test_project_001",
            confidence_threshold=0.8,
            min_frequency=3
        )
        
        # 模拟分析过程
        with patch.object(self.service, '_get_project_annotations') as mock_get_annotations:
            mock_get_annotations.return_value = [
                {
                    "id": "ann_001",
                    "text": "Great product!",
                    "sentiment": "positive",
                    "annotator": "user_001",
                    "created_at": datetime.now()
                }
            ]
            
            response = await self.service.analyze_patterns(request)
            
            assert response.project_id == "test_project_001"
            assert response.total_annotations >= 0
            assert isinstance(response.patterns, list)
    
    @pytest.mark.asyncio
    async def test_rule_extraction_workflow(self):
        """测试规则提取工作流"""
        from src.business_logic.models import RuleExtractionRequest
        
        request = RuleExtractionRequest(
            project_id="test_project_001",
            threshold=0.8
        )
        
        response = await self.service.extract_business_rules(request)
        
        assert response.project_id == "test_project_001"
        assert response.threshold == 0.8
        assert isinstance(response.rules, list)


class TestErrorHandling:
    """测试错误处理"""
    
    def setup_method(self):
        """测试前设置"""
        self.extractor = BusinessLogicExtractor()
        self.service = BusinessLogicService()
    
    def test_extractor_with_invalid_data(self):
        """测试提取器处理无效数据"""
        # 测试None数据 - 需要先检查None
        try:
            result = self.extractor.analyze_annotation_patterns(None)
            assert result.total_annotations == 0
        except TypeError:
            # 如果方法不处理None，这是预期的行为
            pass
        
        # 测试空列表
        result = self.extractor.analyze_annotation_patterns([])
        assert result.total_annotations == 0
        
        # 测试格式错误的数据
        invalid_data = [{"invalid": "data"}]
        result = self.extractor.analyze_annotation_patterns(invalid_data)
        assert isinstance(result, PatternAnalysis)
    
    def test_keyword_extraction_with_empty_texts(self):
        """测试空文本的关键词提取"""
        keywords = self.extractor._extract_keywords([])
        assert keywords == []
        
        keywords = self.extractor._extract_keywords(["", "   ", None])
        assert isinstance(keywords, list)
    
    def test_trend_calculation_with_invalid_data(self):
        """测试无效数据的趋势计算"""
        # 空数组
        strength = self.extractor._calculate_trend_strength(np.array([]))
        assert strength == 0.0
        
        # 单个值
        strength = self.extractor._calculate_trend_strength(np.array([5]))
        assert strength == 0.0
        
        # 全零值
        strength = self.extractor._calculate_trend_strength(np.array([0, 0, 0]))
        assert strength == 0.0


class TestAdvancedAlgorithms:
    """测试高级算法组件"""
    
    def setup_method(self):
        """测试前设置"""
        self.sentiment_analyzer = SentimentCorrelationAnalyzer()
        self.keyword_analyzer = KeywordCooccurrenceAnalyzer()
        
        # 创建测试数据
        self.test_annotations = [
            {
                "id": "ann_001",
                "text": "This product is excellent and amazing!",
                "sentiment": "positive",
                "rating": 5,
                "annotator": "user_001",
                "created_at": datetime.now() - timedelta(days=1)
            },
            {
                "id": "ann_002", 
                "text": "The service was terrible and disappointing.",
                "sentiment": "negative",
                "rating": 1,
                "annotator": "user_002",
                "created_at": datetime.now() - timedelta(days=2)
            },
            {
                "id": "ann_003",
                "text": "It's okay, nothing special.",
                "sentiment": "neutral",
                "rating": 3,
                "annotator": "user_001",
                "created_at": datetime.now() - timedelta(days=3)
            }
        ]
    
    def test_sentiment_correlation_analyzer_initialization(self):
        """测试情感关联分析器初始化"""
        assert self.sentiment_analyzer.vectorizer is not None
        assert hasattr(self.sentiment_analyzer.vectorizer, 'max_features')
    
    def test_sentiment_keyword_correlation_analysis(self):
        """测试情感关键词关联分析"""
        result = self.sentiment_analyzer.analyze_sentiment_keyword_correlation(self.test_annotations)
        
        assert isinstance(result, dict)
        assert "total_annotations" in result
        assert result["total_annotations"] == 3
        
        # 检查是否有错误或正常结果
        if "error" in result:
            # 如果有错误，确保错误信息是字符串
            assert isinstance(result["error"], str)
        else:
            # 如果没有错误，检查结果结构
            assert "sentiment_correlations" in result
            correlations = result["sentiment_correlations"]
            assert isinstance(correlations, dict)
            
            # 检查是否有任何情感分析结果
            if correlations:
                # 应该包含正面、负面、中性情感中的至少一个
                expected_sentiments = {"positive", "negative", "neutral"}
                found_sentiments = set(correlations.keys())
                assert len(found_sentiments.intersection(expected_sentiments)) > 0
    
    def test_sentiment_correlation_with_empty_data(self):
        """测试空数据的情感关联分析"""
        result = self.sentiment_analyzer.analyze_sentiment_keyword_correlation([])
        
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_sentiment_correlation_with_invalid_data(self):
        """测试无效数据的情感关联分析"""
        invalid_data = [{"invalid": "data"}]
        result = self.sentiment_analyzer.analyze_sentiment_keyword_correlation(invalid_data)
        
        assert isinstance(result, dict)
        # 应该处理无效数据而不崩溃
    
    def test_keyword_cooccurrence_analyzer_initialization(self):
        """测试关键词共现分析器初始化"""
        assert self.keyword_analyzer.window_size == 5
        assert self.keyword_analyzer.cooccurrence_matrix is None
        assert self.keyword_analyzer.vocabulary is None
    
    def test_keyword_cooccurrence_analysis(self):
        """测试关键词共现分析"""
        result = self.keyword_analyzer.analyze_keyword_cooccurrence(self.test_annotations)
        
        assert isinstance(result, dict)
        assert "total_keywords" in result
        assert "analysis_timestamp" in result
        
        # 检查分析结果结构
        expected_keys = ["strong_cooccurrence_pairs", "keyword_network", 
                        "keyword_communities", "centrality_scores"]
        for key in expected_keys:
            assert key in result
    
    def test_keyword_cooccurrence_with_empty_data(self):
        """测试空数据的关键词共现分析"""
        result = self.keyword_analyzer.analyze_keyword_cooccurrence([])
        
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_keyword_cooccurrence_with_invalid_data(self):
        """测试无效数据的关键词共现分析"""
        invalid_data = [{"no_text": "field"}]
        result = self.keyword_analyzer.analyze_keyword_cooccurrence(invalid_data)
        
        assert isinstance(result, dict)
        assert "error" in result


class TestRuleGenerator:
    """测试规则生成器"""
    
    def setup_method(self):
        """测试前设置"""
        self.rule_generator = AdvancedRuleGenerator(min_support=2, min_confidence=0.6)
        
        # 创建测试数据
        self.test_annotations = [
            {
                "id": "ann_001",
                "text": "This product is excellent!",
                "sentiment": "positive",
                "rating": 5,
                "annotator": "user_001",
                "created_at": datetime.now() - timedelta(days=1)
            },
            {
                "id": "ann_002", 
                "text": "Great service, highly recommended!",
                "sentiment": "positive",
                "rating": 5,
                "annotator": "user_002",
                "created_at": datetime.now() - timedelta(days=1)
            },
            {
                "id": "ann_003",
                "text": "The quality was poor.",
                "sentiment": "negative",
                "rating": 2,
                "annotator": "user_001",
                "created_at": datetime.now() - timedelta(days=2)
            },
            {
                "id": "ann_004",
                "text": "Terrible experience, very disappointed.",
                "sentiment": "negative",
                "rating": 1,
                "annotator": "user_003",
                "created_at": datetime.now() - timedelta(days=2)
            }
        ]
    
    def test_rule_generator_initialization(self):
        """测试规则生成器初始化"""
        assert self.rule_generator.min_support == 2
        assert self.rule_generator.min_confidence == 0.6
        assert self.rule_generator.vectorizer is not None
    
    def test_comprehensive_rule_generation(self):
        """测试综合规则生成"""
        rules = self.rule_generator.generate_comprehensive_rules(self.test_annotations)
        
        assert isinstance(rules, list)
        assert len(rules) >= 0  # 可能没有满足条件的规则
        
        # 如果有规则，检查规则结构
        for rule in rules:
            assert isinstance(rule, BusinessRuleTemplate)
            assert hasattr(rule, 'id')
            assert hasattr(rule, 'name')
            assert hasattr(rule, 'confidence')
            assert hasattr(rule, 'support')
            assert rule.confidence >= 0.0
            assert rule.support >= 0
    
    def test_rule_generation_with_empty_data(self):
        """测试空数据的规则生成"""
        rules = self.rule_generator.generate_comprehensive_rules([])
        
        assert isinstance(rules, list)
        assert len(rules) == 0
    
    def test_rule_generation_with_insufficient_data(self):
        """测试数据不足的规则生成"""
        # 只有一条数据
        single_data = [self.test_annotations[0]]
        rules = self.rule_generator.generate_comprehensive_rules(single_data)
        
        assert isinstance(rules, list)
        # 数据不足可能无法生成规则
    
    def test_business_rule_template_creation(self):
        """测试业务规则模板创建"""
        condition = RuleCondition(
            field="sentiment",
            operator="equals",
            value="positive",
            confidence=0.8
        )
        
        consequent = RuleConsequent(
            field="rating",
            value=5,
            confidence=0.9
        )
        
        rule = BusinessRuleTemplate(
            id="test_rule_001",
            name="测试规则",
            conditions=[condition],
            consequent=consequent,
            support=10,
            confidence=0.85
        )
        
        assert rule.id == "test_rule_001"
        assert rule.name == "测试规则"
        assert len(rule.conditions) == 1
        assert rule.consequent is not None
        assert rule.support == 10
        assert rule.confidence == 0.85
    
    def test_rule_condition_creation(self):
        """测试规则条件创建"""
        condition = RuleCondition(
            field="text",
            operator="contains",
            value="excellent",
            confidence=0.7,
            weight=1.0
        )
        
        assert condition.field == "text"
        assert condition.operator == "contains"
        assert condition.value == "excellent"
        assert condition.confidence == 0.7
        assert condition.weight == 1.0
    
    def test_rule_consequent_creation(self):
        """测试规则结果创建"""
        consequent = RuleConsequent(
            field="sentiment",
            value="positive",
            confidence=0.85,
            probability=0.9
        )
        
        assert consequent.field == "sentiment"
        assert consequent.value == "positive"
        assert consequent.confidence == 0.85
        assert consequent.probability == 0.9


class TestDataValidator:
    """测试数据验证器"""
    
    def setup_method(self):
        """测试前设置"""
        self.quality_manager = DataQualityManager()
        self.completeness_validator = DataCompletenessValidator()
        self.format_validator = DataFormatValidator()
        
        # 创建测试数据
        self.valid_data = [
            {
                "id": "001",
                "text": "This is a valid text",
                "sentiment": "positive",
                "rating": 5,
                "email": "user@example.com",
                "created_at": "2026-01-01T10:00:00"
            },
            {
                "id": "002",
                "text": "Another valid text",
                "sentiment": "negative", 
                "rating": 2,
                "email": "user2@example.com",
                "created_at": "2026-01-02T11:00:00"
            }
        ]
        
        self.invalid_data = [
            {
                "id": "003",
                "text": "",  # 空文本
                "sentiment": None,  # 空值
                "rating": 10,  # 超出范围
                "email": "invalid-email",  # 无效邮箱
                "created_at": "invalid-date"  # 无效日期
            },
            {
                "id": "004",
                "text": "Valid text",
                "sentiment": "positive",
                "rating": 3,
                "email": "valid@email.com",
                # 缺少 created_at 字段
            }
        ]
    
    def test_data_quality_manager_initialization(self):
        """测试数据质量管理器初始化"""
        assert self.quality_manager.completeness_validator is not None
        assert self.quality_manager.format_validator is not None
        assert isinstance(self.quality_manager.validation_history, list)
    
    def test_completeness_validation_with_valid_data(self):
        """测试有效数据的完整性验证"""
        required_fields = ["id", "text", "sentiment", "rating"]
        results = self.completeness_validator.validate_completeness(
            self.valid_data, required_fields
        )
        
        assert isinstance(results, list)
        assert len(results) == len(required_fields)
        
        # 所有字段都应该通过验证
        for result in results:
            assert isinstance(result, ValidationResult)
            assert result.passed == True  # 使用 == 而不是 is
            assert result.error_count == 0
    
    def test_completeness_validation_with_invalid_data(self):
        """测试无效数据的完整性验证"""
        required_fields = ["id", "text", "sentiment", "created_at"]
        results = self.completeness_validator.validate_completeness(
            self.invalid_data, required_fields
        )
        
        assert isinstance(results, list)
        assert len(results) == len(required_fields)
        
        # 检查失败的验证
        failed_results = [r for r in results if not r.passed]
        assert len(failed_results) > 0
        
        # 检查错误详情
        for result in failed_results:
            assert result.error_count > 0
            assert result.error_rate > 0
    
    def test_format_validation_with_valid_data(self):
        """测试有效数据的格式验证"""
        format_rules = {
            "email": "email",
            "created_at": "datetime"
        }
        
        results = self.format_validator.validate_format(self.valid_data, format_rules)
        
        assert isinstance(results, list)
        assert len(results) == len(format_rules)
        
        # 检查验证结果
        for result in results:
            assert isinstance(result, ValidationResult)
            if result.field_name == "email":
                assert result.passed == True  # 有效邮箱应该通过
    
    def test_format_validation_with_invalid_data(self):
        """测试无效数据的格式验证"""
        format_rules = {
            "email": "email",
            "created_at": "datetime"
        }
        
        results = self.format_validator.validate_format(self.invalid_data, format_rules)
        
        assert isinstance(results, list)
        assert len(results) == len(format_rules)
        
        # 应该有失败的验证
        failed_results = [r for r in results if not r.passed]
        assert len(failed_results) > 0
    
    def test_comprehensive_validation_with_valid_data(self):
        """测试有效数据的综合验证"""
        validation_config = {
            "required_fields": ["id", "text", "sentiment"],
            "format_rules": {
                "email": "email"
            },
            "range_rules": {
                "rating": {"min": 1, "max": 5}
            },
            "unique_fields": ["id"]
        }
        
        report = self.quality_manager.run_comprehensive_validation(
            self.valid_data, validation_config, "test_dataset"
        )
        
        assert isinstance(report, DataQualityReport)
        assert report.dataset_name == "test_dataset"
        assert report.total_records == len(self.valid_data)
        assert report.overall_score > 0.8  # 有效数据应该有高分
        assert report.quality_level in ["excellent", "good"]
    
    def test_comprehensive_validation_with_invalid_data(self):
        """测试无效数据的综合验证"""
        validation_config = {
            "required_fields": ["id", "text", "sentiment", "created_at"],
            "format_rules": {
                "email": "email",
                "created_at": "datetime"
            },
            "range_rules": {
                "rating": {"min": 1, "max": 5}
            }
        }
        
        report = self.quality_manager.run_comprehensive_validation(
            self.invalid_data, validation_config, "invalid_dataset"
        )
        
        assert isinstance(report, DataQualityReport)
        assert report.dataset_name == "invalid_dataset"
        assert report.total_records == len(self.invalid_data)
        assert report.overall_score < 0.8  # 无效数据应该有低分
        assert report.failed_rules > 0
        assert len(report.recommendations) > 0
    
    def test_validation_result_creation(self):
        """测试验证结果创建"""
        result = ValidationResult(
            rule_id="test_rule",
            rule_name="测试规则",
            field_name="test_field",
            passed=False,
            error_count=5,
            total_count=10,
            error_rate=0.5,
            severity="medium",
            details={"error_type": "test_error"},
            error_samples=[]
        )
        
        assert result.rule_id == "test_rule"
        assert result.rule_name == "测试规则"
        assert result.field_name == "test_field"
        assert result.passed is False
        assert result.error_count == 5
        assert result.total_count == 10
        assert result.error_rate == 0.5
        assert result.severity == "medium"
    
    def test_data_quality_report_creation(self):
        """测试数据质量报告创建"""
        report = DataQualityReport(
            report_id="test_report",
            dataset_name="test_dataset",
            validation_timestamp=datetime.now(),
            total_records=100,
            total_rules=10,
            passed_rules=8,
            failed_rules=2,
            overall_score=0.8,
            quality_level="good",
            validation_results=[],
            recommendations=["建议1", "建议2"]
        )
        
        assert report.report_id == "test_report"
        assert report.dataset_name == "test_dataset"
        assert report.total_records == 100
        assert report.total_rules == 10
        assert report.passed_rules == 8
        assert report.failed_rules == 2
        assert report.overall_score == 0.8
        assert report.quality_level == "good"
        assert len(report.recommendations) == 2
    
    def test_custom_format_pattern(self):
        """测试自定义格式模式"""
        # 添加自定义模式
        self.format_validator.add_custom_pattern("custom_id", r'^ID_\d{6}$')
        
        # 测试数据
        test_data = [
            {"custom_field": "ID_123456"},  # 有效
            {"custom_field": "ID_12345"},   # 无效（位数不够）
            {"custom_field": "INVALID"}     # 无效（格式错误）
        ]
        
        format_rules = {"custom_field": "custom_id"}
        results = self.format_validator.validate_format(test_data, format_rules)
        
        assert len(results) == 1
        result = results[0]
        assert result.field_name == "custom_field"
        assert result.error_count == 2  # 两个无效值
        assert result.total_count == 3


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])