"""
质量改进系统单元测试

测试质量改进系统的核心功能，包括根因分析、模式识别、修复建议生成等。
"""

import unittest
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.quality.root_cause_analyzer import (
    RootCauseAnalyzer, QualityIssue, ProblemCategory, SeverityLevel, RootCauseType
)
from src.quality.pattern_classifier import PatternClassifier
from src.quality.repair_suggestion_generator import RepairSuggestionGenerator
from src.quality.repair_effect_predictor import RepairEffectPredictor
from src.quality.repair_guidance_system import RepairGuidanceSystem
from src.quality.quality_improvement_system import QualityImprovementSystem


class TestQualityImprovementSystem(unittest.TestCase):
    """质量改进系统测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.system = QualityImprovementSystem()
        
        # 创建测试用的质量问题
        self.test_issue = QualityIssue(
            id="test_issue_001",
            category=ProblemCategory.ACCURACY,
            description="测试数据准确性问题",
            affected_data=["data_001", "data_002", "data_003"],
            reporter="test_user",
            created_at=datetime.now(),
            severity=SeverityLevel.HIGH,
            context={"test_context": "value"},
            metadata={"test_metadata": "value"}
        )
    
    def test_root_cause_analyzer(self):
        """测试根因分析器"""
        analyzer = RootCauseAnalyzer()
        
        # 测试根因分析
        analysis = analyzer.analyze_root_cause(self.test_issue)
        
        # 验证分析结果
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.issue_id, self.test_issue.id)
        self.assertIsInstance(analysis.primary_cause, RootCauseType)
        self.assertIsInstance(analysis.confidence_score, float)
        self.assertGreaterEqual(analysis.confidence_score, 0.0)
        self.assertLessEqual(analysis.confidence_score, 1.0)
        self.assertIsInstance(analysis.evidence, list)
        self.assertIsInstance(analysis.recommendations, list)
    
    def test_pattern_classifier(self):
        """测试模式分类器"""
        classifier = PatternClassifier()
        
        # 添加问题到历史记录
        classifier.add_issue(self.test_issue)
        
        # 测试问题分类
        classification = classifier.classify_issue(self.test_issue)
        
        # 验证分类结果
        self.assertIsNotNone(classification)
        self.assertIn('issue_id', classification)
        self.assertEqual(classification['issue_id'], self.test_issue.id)
        self.assertIn('primary_category', classification)
        self.assertIn('extracted_features', classification)
        self.assertIn('matching_patterns', classification)
        self.assertIn('classification_confidence', classification)
    
    def test_repair_suggestion_generator(self):
        """测试修复建议生成器"""
        generator = RepairSuggestionGenerator()
        analyzer = RootCauseAnalyzer()
        
        # 先进行根因分析
        root_cause_analysis = analyzer.analyze_root_cause(self.test_issue)
        
        # 生成修复建议
        suggestions = generator.generate_suggestions(self.test_issue, root_cause_analysis)
        
        # 验证建议结果
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        for suggestion in suggestions:
            self.assertIsNotNone(suggestion.suggestion_id)
            self.assertIsNotNone(suggestion.title)
            self.assertIsNotNone(suggestion.description)
            self.assertGreaterEqual(suggestion.success_probability, 0.0)
            self.assertLessEqual(suggestion.success_probability, 1.0)
    
    def test_repair_effect_predictor(self):
        """测试修复效果预测器"""
        predictor = RepairEffectPredictor()
        generator = RepairSuggestionGenerator()
        analyzer = RootCauseAnalyzer()
        
        # 生成建议
        root_cause_analysis = analyzer.analyze_root_cause(self.test_issue)
        suggestions = generator.generate_suggestions(self.test_issue, root_cause_analysis)
        
        if suggestions:
            # 预测修复效果
            prediction = predictor.predict_repair_effect(self.test_issue, suggestions[0])
            
            # 验证预测结果
            self.assertIsNotNone(prediction)
            self.assertEqual(prediction.suggestion_id, suggestions[0].suggestion_id)
            self.assertGreaterEqual(prediction.success_probability, 0.0)
            self.assertLessEqual(prediction.success_probability, 1.0)
            self.assertGreater(prediction.time_to_resolution, 0)
            self.assertIsInstance(prediction.risk_factors, list)
            self.assertIsInstance(prediction.success_factors, list)
    
    def test_repair_guidance_system(self):
        """测试修复指导系统"""
        guidance_system = RepairGuidanceSystem()
        generator = RepairSuggestionGenerator()
        analyzer = RootCauseAnalyzer()
        
        # 生成建议
        root_cause_analysis = analyzer.analyze_root_cause(self.test_issue)
        suggestions = generator.generate_suggestions(self.test_issue, root_cause_analysis)
        
        if suggestions:
            # 获取个性化指导
            guidance = guidance_system.get_personalized_guidance(
                "test_user", self.test_issue, suggestions[0]
            )
            
            # 验证指导结果
            self.assertIsNotNone(guidance)
            self.assertIn('user_id', guidance)
            self.assertEqual(guidance['user_id'], "test_user")
            self.assertIn('guidance_content', guidance)
            self.assertIn('training_recommendations', guidance)
            self.assertIn('personalized_tips', guidance)
    
    def test_quality_improvement_system_integration(self):
        """测试质量改进系统集成"""
        # 处理质量问题
        result = self.system.process_quality_issue(self.test_issue, "test_user")
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result.issue_id, self.test_issue.id)
        
        # 验证根因分析
        self.assertIsNotNone(result.root_cause_analysis)
        self.assertIsInstance(result.root_cause_analysis.primary_cause, RootCauseType)
        
        # 验证修复建议
        self.assertIsInstance(result.repair_suggestions, list)
        self.assertGreater(len(result.repair_suggestions), 0)
        
        # 验证修复计划
        self.assertIsNotNone(result.repair_plan)
        self.assertEqual(result.repair_plan.issue_id, self.test_issue.id)
        
        # 验证效果预测
        self.assertIsInstance(result.effect_predictions, list)
        
        # 验证个性化指导
        self.assertIsInstance(result.personalized_guidance, dict)
        
        # 验证综合评估
        self.assertGreaterEqual(result.overall_success_probability, 0.0)
        self.assertLessEqual(result.overall_success_probability, 1.0)
        self.assertIsNotNone(result.recommended_approach)
        self.assertIsNotNone(result.priority_level)
    
    def test_system_statistics(self):
        """测试系统统计功能"""
        # 处理一个问题以生成统计数据
        self.system.process_quality_issue(self.test_issue)
        
        # 获取质量洞察
        insights = self.system.get_quality_insights(7)
        
        # 验证洞察结果
        self.assertIsNotNone(insights)
        self.assertIn('root_cause_analysis', insights)
        self.assertIn('pattern_recognition', insights)
        self.assertIn('suggestion_generation', insights)
        self.assertIn('effect_prediction', insights)
        self.assertIn('guidance_system', insights)
    
    def test_knowledge_base_export(self):
        """测试知识库导出"""
        knowledge_base = self.system.export_knowledge_base()
        
        # 验证导出结果
        self.assertIsNotNone(knowledge_base)
        self.assertIn('patterns', knowledge_base)
        self.assertIn('guidance_content', knowledge_base)
        self.assertIn('training_resources', knowledge_base)
        self.assertIn('best_practices', knowledge_base)
        self.assertIn('exported_at', knowledge_base)
    
    def test_user_feedback_update(self):
        """测试用户反馈更新"""
        # 处理问题以创建用户档案
        result = self.system.process_quality_issue(self.test_issue, "test_user")
        
        # 模拟用户反馈
        feedback_data = {
            'guidance_feedback': {
                'guidance_001': {
                    'success': True,
                    'rating': 4.5
                }
            },
            'training_completion': {
                'training_001': {
                    'success': True,
                    'rating': 4.0
                }
            }
        }
        
        # 更新反馈（不应该抛出异常）
        try:
            self.system.update_user_feedback(self.test_issue.id, "test_user", feedback_data)
        except Exception as e:
            self.fail(f"更新用户反馈时发生异常: {str(e)}")


class TestIndividualComponents(unittest.TestCase):
    """测试各个组件的独立功能"""
    
    def test_quality_issue_creation(self):
        """测试质量问题对象创建"""
        issue = QualityIssue(
            id="test_001",
            category=ProblemCategory.ACCURACY,
            description="测试问题",
            affected_data=["data1", "data2"],
            reporter="tester",
            created_at=datetime.now(),
            severity=SeverityLevel.MEDIUM
        )
        
        self.assertEqual(issue.id, "test_001")
        self.assertEqual(issue.category, ProblemCategory.ACCURACY)
        self.assertEqual(issue.severity, SeverityLevel.MEDIUM)
        self.assertEqual(len(issue.affected_data), 2)
    
    def test_root_cause_types(self):
        """测试根因类型枚举"""
        # 验证所有根因类型都存在
        expected_causes = [
            'human_error', 'process_issue', 'tool_limitation', 'training_gap',
            'guideline_unclear', 'system_bug', 'data_quality', 'resource_constraint'
        ]
        
        for cause in expected_causes:
            self.assertTrue(hasattr(RootCauseType, cause.upper()))
    
    def test_problem_categories(self):
        """测试问题类别枚举"""
        # 验证所有问题类别都存在
        expected_categories = [
            'accuracy', 'consistency', 'completeness', 'format',
            'guideline', 'performance', 'system'
        ]
        
        for category in expected_categories:
            self.assertTrue(hasattr(ProblemCategory, category.upper()))


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)