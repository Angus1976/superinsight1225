"""
质量改进系统集成模块

整合根因分析、模式识别、修复建议生成、效果预测和指导培训等功能，
提供统一的质量改进服务接口。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

from .root_cause_analyzer import (
    RootCauseAnalyzer, QualityIssue, RootCauseAnalysis
)
from .pattern_classifier import (
    PatternClassifier, QualityPattern
)
from .repair_suggestion_generator import (
    RepairSuggestionGenerator, RepairSuggestion, RepairPlan
)
from .repair_effect_predictor import (
    RepairEffectPredictor, EffectPrediction
)
from .repair_guidance_system import (
    RepairGuidanceSystem
)

logger = logging.getLogger(__name__)


@dataclass
class QualityImprovementResult:
    """质量改进结果"""
    issue_id: str
    root_cause_analysis: RootCauseAnalysis
    matching_patterns: List[QualityPattern]
    repair_suggestions: List[RepairSuggestion]
    repair_plan: RepairPlan
    effect_predictions: List[EffectPrediction]
    personalized_guidance: Dict[str, Any]
    
    # 综合评估
    overall_success_probability: float
    recommended_approach: str
    priority_level: str
    
    # 元数据
    processed_at: datetime
    processing_time_seconds: float


class QualityImprovementSystem:
    """质量改进系统"""
    
    def __init__(self):
        # 初始化各个子系统
        self.root_cause_analyzer = RootCauseAnalyzer()
        self.pattern_classifier = PatternClassifier()
        self.suggestion_generator = RepairSuggestionGenerator()
        self.effect_predictor = RepairEffectPredictor()
        self.guidance_system = RepairGuidanceSystem()
        
        logger.info("质量改进系统初始化完成")
    
    def process_quality_issue(self, issue: QualityIssue, 
                            user_id: Optional[str] = None) -> QualityImprovementResult:
        """处理质量问题的完整流程"""
        start_time = datetime.now()
        logger.info(f"开始处理质量问题 {issue.id}")
        
        try:
            # 1. 根因分析
            logger.info("执行根因分析...")
            root_cause_analysis = self.root_cause_analyzer.analyze_root_cause(issue)
            
            # 2. 模式识别和分类
            logger.info("执行模式识别...")
            self.pattern_classifier.add_issue(issue)
            classification_result = self.pattern_classifier.classify_issue(issue)
            
            # 获取匹配的模式
            matching_patterns = []
            for pattern_info in classification_result['matching_patterns']:
                pattern = self.pattern_classifier.get_pattern_by_id(pattern_info['pattern_id'])
                if pattern:
                    matching_patterns.append(pattern)
            
            # 3. 生成修复建议
            logger.info("生成修复建议...")
            repair_suggestions = self.suggestion_generator.generate_suggestions(
                issue, root_cause_analysis, matching_patterns
            )
            
            # 4. 创建修复计划
            logger.info("创建修复计划...")
            repair_plan = self.suggestion_generator.create_repair_plan(issue, repair_suggestions)
            
            # 5. 预测修复效果
            logger.info("预测修复效果...")
            effect_predictions = []
            for suggestion in repair_suggestions[:5]:  # 只预测前5个建议
                prediction = self.effect_predictor.predict_repair_effect(issue, suggestion)
                effect_predictions.append(prediction)
            
            # 6. 生成个性化指导（如果提供了用户ID）
            personalized_guidance = {}
            if user_id and repair_suggestions:
                logger.info(f"生成用户 {user_id} 的个性化指导...")
                personalized_guidance = self.guidance_system.get_personalized_guidance(
                    user_id, issue, repair_suggestions[0]
                )
            
            # 7. 综合评估
            logger.info("执行综合评估...")
            overall_assessment = self._perform_overall_assessment(
                issue, root_cause_analysis, repair_suggestions, effect_predictions
            )
            
            # 8. 生成结果
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = QualityImprovementResult(
                issue_id=issue.id,
                root_cause_analysis=root_cause_analysis,
                matching_patterns=matching_patterns,
                repair_suggestions=repair_suggestions,
                repair_plan=repair_plan,
                effect_predictions=effect_predictions,
                personalized_guidance=personalized_guidance,
                overall_success_probability=overall_assessment['success_probability'],
                recommended_approach=overall_assessment['recommended_approach'],
                priority_level=overall_assessment['priority_level'],
                processed_at=datetime.now(),
                processing_time_seconds=processing_time
            )
            
            logger.info(f"质量问题 {issue.id} 处理完成，耗时 {processing_time:.2f} 秒")
            return result
            
        except Exception as e:
            logger.error(f"处理质量问题 {issue.id} 时发生错误: {str(e)}")
            raise
    
    def _perform_overall_assessment(self, issue: QualityIssue,
                                  root_cause_analysis: RootCauseAnalysis,
                                  suggestions: List[RepairSuggestion],
                                  predictions: List[EffectPrediction]) -> Dict[str, Any]:
        """执行综合评估"""
        
        # 计算整体成功概率
        if predictions:
            success_probabilities = [p.success_probability for p in predictions]
            overall_success_probability = max(success_probabilities)  # 取最高概率
        else:
            overall_success_probability = root_cause_analysis.confidence_score
        
        # 确定推荐方法
        recommended_approach = self._determine_recommended_approach(
            issue, root_cause_analysis, suggestions
        )
        
        # 确定优先级
        priority_level = self._determine_priority_level(
            issue, root_cause_analysis, overall_success_probability
        )
        
        return {
            'success_probability': overall_success_probability,
            'recommended_approach': recommended_approach,
            'priority_level': priority_level
        }
    
    def _determine_recommended_approach(self, issue: QualityIssue,
                                     root_cause_analysis: RootCauseAnalysis,
                                     suggestions: List[RepairSuggestion]) -> str:
        """确定推荐方法"""
        
        if not suggestions:
            return "需要进一步分析"
        
        # 基于根因类型确定方法
        primary_cause = root_cause_analysis.primary_cause
        
        if primary_cause.value in ['human_error', 'training_gap']:
            return "培训和流程改进"
        elif primary_cause.value in ['system_bug', 'tool_limitation']:
            return "技术修复和系统升级"
        elif primary_cause.value in ['process_issue', 'guideline_unclear']:
            return "流程优化和规范完善"
        else:
            return "综合改进措施"
    
    def _determine_priority_level(self, issue: QualityIssue,
                                root_cause_analysis: RootCauseAnalysis,
                                success_probability: float) -> str:
        """确定优先级"""
        
        # 基于问题严重程度
        severity_weight = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }.get(issue.severity.value, 2)
        
        # 基于影响范围
        impact_weight = min(len(issue.affected_data) / 100, 3)  # 最大权重3
        
        # 基于成功概率
        success_weight = success_probability * 2
        
        # 综合评分
        total_score = severity_weight + impact_weight + success_weight
        
        if total_score >= 7:
            return "critical"
        elif total_score >= 5:
            return "high"
        elif total_score >= 3:
            return "medium"
        else:
            return "low"
    
    def get_quality_insights(self, time_period_days: int = 30) -> Dict[str, Any]:
        """获取质量洞察"""
        
        # 根因分析统计
        root_cause_stats = self.root_cause_analyzer.get_analysis_statistics()
        
        # 模式识别统计
        pattern_stats = self.pattern_classifier.get_pattern_statistics()
        
        # 建议生成统计
        suggestion_stats = self.suggestion_generator.get_suggestion_statistics()
        
        # 预测统计
        prediction_stats = self.effect_predictor.get_prediction_statistics()
        
        # 指导系统统计
        guidance_stats = self.guidance_system.get_system_statistics()
        
        return {
            'time_period_days': time_period_days,
            'root_cause_analysis': root_cause_stats,
            'pattern_recognition': pattern_stats,
            'suggestion_generation': suggestion_stats,
            'effect_prediction': prediction_stats,
            'guidance_system': guidance_stats,
            'generated_at': datetime.now().isoformat()
        }
    
    def export_knowledge_base(self) -> Dict[str, Any]:
        """导出知识库"""
        
        return {
            'patterns': self.pattern_classifier.export_patterns(),
            'guidance_content': {
                content_id: content.to_dict() 
                for content_id, content in self.guidance_system.guidance_content.items()
            },
            'training_resources': {
                resource_id: resource.to_dict()
                for resource_id, resource in self.guidance_system.training_resources.items()
            },
            'best_practices': {
                case_id: case.to_dict()
                for case_id, case in self.guidance_system.best_practice_cases.items()
            },
            'exported_at': datetime.now().isoformat()
        }
    
    def import_knowledge_base(self, knowledge_data: Dict[str, Any]):
        """导入知识库"""
        
        try:
            # 导入模式数据
            if 'patterns' in knowledge_data:
                # 这里需要实现模式导入逻辑
                pass
            
            # 导入指导内容
            if 'guidance_content' in knowledge_data:
                # 这里需要实现指导内容导入逻辑
                pass
            
            # 导入培训资源
            if 'training_resources' in knowledge_data:
                # 这里需要实现培训资源导入逻辑
                pass
            
            # 导入最佳实践
            if 'best_practices' in knowledge_data:
                # 这里需要实现最佳实践导入逻辑
                pass
            
            logger.info("知识库导入完成")
            
        except Exception as e:
            logger.error(f"导入知识库时发生错误: {str(e)}")
            raise
    
    def update_user_feedback(self, issue_id: str, user_id: str, 
                           feedback_data: Dict[str, Any]):
        """更新用户反馈"""
        
        try:
            # 更新指导内容反馈
            if 'guidance_feedback' in feedback_data:
                for content_id, feedback in feedback_data['guidance_feedback'].items():
                    self.guidance_system.record_guidance_feedback(
                        content_id, feedback['success'], feedback['rating']
                    )
            
            # 更新培训完成情况
            if 'training_completion' in feedback_data:
                for resource_id, completion in feedback_data['training_completion'].items():
                    self.guidance_system.record_training_completion(
                        user_id, resource_id, completion['success'], 
                        completion.get('rating')
                    )
            
            # 更新技能提升跟踪
            if 'skill_improvement' in feedback_data:
                for category_str, improvement in feedback_data['skill_improvement'].items():
                    from .root_cause_analyzer import ProblemCategory
                    category = ProblemCategory(category_str)
                    self.guidance_system.track_skill_improvement(
                        user_id, category, improvement
                    )
            
            logger.info(f"更新用户 {user_id} 对问题 {issue_id} 的反馈")
            
        except Exception as e:
            logger.error(f"更新用户反馈时发生错误: {str(e)}")
            raise
    
    def get_user_dashboard(self, user_id: str) -> Dict[str, Any]:
        """获取用户仪表板数据"""
        
        # 获取用户档案
        user_profile = self.guidance_system.user_profiles.get(user_id)
        if not user_profile:
            return {"error": "用户档案不存在"}
        
        # 获取学习路径推荐
        learning_paths = {}
        from .root_cause_analyzer import ProblemCategory
        for category in ProblemCategory:
            learning_path = self.guidance_system.get_user_learning_path(user_id, category)
            learning_paths[category.value] = learning_path
        
        return {
            'user_profile': user_profile.to_dict(),
            'learning_paths': learning_paths,
            'system_statistics': self.get_quality_insights(7),  # 最近7天
            'generated_at': datetime.now().isoformat()
        }


# 创建全局实例
quality_improvement_system = QualityImprovementSystem()