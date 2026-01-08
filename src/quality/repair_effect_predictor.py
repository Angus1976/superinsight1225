"""
修复效果预测器

基于历史数据和机器学习模型，预测修复措施的效果和成功概率。
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import numpy as np
import logging
from collections import defaultdict

from .root_cause_analyzer import QualityIssue, RootCauseType, ProblemCategory, SeverityLevel
from .repair_suggestion_generator import RepairSuggestion, RepairPlan, ActionCategory

logger = logging.getLogger(__name__)


class PredictionConfidence(str, Enum):
    """预测置信度"""
    VERY_LOW = "very_low"  # 很低 (<0.3)
    LOW = "low"  # 低 (0.3-0.5)
    MEDIUM = "medium"  # 中 (0.5-0.7)
    HIGH = "high"  # 高 (0.7-0.9)
    VERY_HIGH = "very_high"  # 很高 (>0.9)


class EffectLevel(str, Enum):
    """效果等级"""
    MINIMAL = "minimal"  # 最小
    MODERATE = "moderate"  # 适中
    SIGNIFICANT = "significant"  # 显著
    MAJOR = "major"  # 重大
    TRANSFORMATIVE = "transformative"  # 变革性


@dataclass
class PredictionFeatures:
    """预测特征"""
    # 问题特征
    problem_category: ProblemCategory
    severity_level: SeverityLevel
    affected_data_count: int
    problem_age_days: int
    
    # 修复特征
    action_category: ActionCategory
    estimated_effort_hours: float
    required_resources_count: int
    implementation_complexity: float  # 0-1
    
    # 环境特征
    team_experience_level: float  # 0-1
    available_resources: float  # 0-1
    organizational_support: float  # 0-1
    time_pressure: float  # 0-1
    
    # 历史特征
    similar_issues_count: int
    previous_success_rate: float  # 0-1
    average_resolution_time: float
    
    def to_vector(self) -> np.ndarray:
        """转换为特征向量"""
        # 将分类特征编码为数值
        category_encoding = {
            ProblemCategory.ACCURACY: 0.1,
            ProblemCategory.CONSISTENCY: 0.2,
            ProblemCategory.COMPLETENESS: 0.3,
            ProblemCategory.FORMAT: 0.4,
            ProblemCategory.GUIDELINE: 0.5,
            ProblemCategory.PERFORMANCE: 0.6,
            ProblemCategory.SYSTEM: 0.7
        }
        
        severity_encoding = {
            SeverityLevel.LOW: 0.25,
            SeverityLevel.MEDIUM: 0.5,
            SeverityLevel.HIGH: 0.75,
            SeverityLevel.CRITICAL: 1.0
        }
        
        action_encoding = {
            ActionCategory.TRAINING: 0.1,
            ActionCategory.PROCESS: 0.2,
            ActionCategory.TOOL: 0.3,
            ActionCategory.SYSTEM: 0.4,
            ActionCategory.POLICY: 0.5,
            ActionCategory.RESOURCE: 0.6
        }
        
        return np.array([
            category_encoding.get(self.problem_category, 0.5),
            severity_encoding.get(self.severity_level, 0.5),
            min(self.affected_data_count / 1000, 1.0),  # 归一化
            min(self.problem_age_days / 30, 1.0),  # 归一化到月
            action_encoding.get(self.action_category, 0.5),
            min(self.estimated_effort_hours / 100, 1.0),  # 归一化
            min(self.required_resources_count / 10, 1.0),  # 归一化
            self.implementation_complexity,
            self.team_experience_level,
            self.available_resources,
            self.organizational_support,
            self.time_pressure,
            min(self.similar_issues_count / 20, 1.0),  # 归一化
            self.previous_success_rate,
            min(self.average_resolution_time / 168, 1.0)  # 归一化到周
        ])


@dataclass
class EffectPrediction:
    """效果预测结果"""
    prediction_id: str
    suggestion_id: str
    
    # 预测结果
    success_probability: float  # 成功概率 (0-1)
    effect_level: EffectLevel  # 效果等级
    confidence: PredictionConfidence  # 置信度
    
    # 详细预测
    time_to_resolution: float  # 预计解决时间（小时）
    resource_utilization: float  # 资源利用率 (0-1)
    risk_factors: List[str]  # 风险因素
    success_factors: List[str]  # 成功因素
    
    # 量化指标
    quality_improvement_score: float  # 质量改进分数 (0-100)
    cost_effectiveness: float  # 成本效益 (0-1)
    implementation_difficulty: float  # 实施难度 (0-1)
    
    # 预测依据
    similar_cases_count: int  # 相似案例数量
    model_accuracy: float  # 模型准确率
    feature_importance: Dict[str, float]  # 特征重要性
    
    # 元数据
    predicted_at: datetime = field(default_factory=datetime.now)
    model_version: str = "v1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'prediction_id': self.prediction_id,
            'suggestion_id': self.suggestion_id,
            'success_probability': self.success_probability,
            'effect_level': self.effect_level.value,
            'confidence': self.confidence.value,
            'time_to_resolution': self.time_to_resolution,
            'resource_utilization': self.resource_utilization,
            'risk_factors': self.risk_factors,
            'success_factors': self.success_factors,
            'quality_improvement_score': self.quality_improvement_score,
            'cost_effectiveness': self.cost_effectiveness,
            'implementation_difficulty': self.implementation_difficulty,
            'similar_cases_count': self.similar_cases_count,
            'model_accuracy': self.model_accuracy,
            'feature_importance': self.feature_importance,
            'predicted_at': self.predicted_at.isoformat(),
            'model_version': self.model_version
        }


@dataclass
class HistoricalCase:
    """历史案例"""
    case_id: str
    features: PredictionFeatures
    actual_success: bool
    actual_effect_level: EffectLevel
    actual_resolution_time: float
    actual_cost: float
    lessons_learned: List[str]
    created_at: datetime


class RepairEffectPredictor:
    """修复效果预测器"""
    
    def __init__(self):
        self.historical_cases: List[HistoricalCase] = []
        self.prediction_counter = 0
        self.model_weights = self._initialize_model_weights()
        self.feature_importance = self._initialize_feature_importance()
        
        # 预测模型参数
        self.min_cases_for_prediction = 5
        self.confidence_threshold = 0.6
        
    def _initialize_model_weights(self) -> Dict[str, float]:
        """初始化模型权重"""
        return {
            'problem_severity': 0.2,
            'action_complexity': 0.15,
            'team_experience': 0.15,
            'resource_availability': 0.1,
            'historical_success': 0.2,
            'organizational_support': 0.1,
            'time_pressure': 0.1
        }
    
    def _initialize_feature_importance(self) -> Dict[str, float]:
        """初始化特征重要性"""
        return {
            'problem_category': 0.12,
            'severity_level': 0.15,
            'affected_data_count': 0.08,
            'problem_age_days': 0.05,
            'action_category': 0.10,
            'estimated_effort_hours': 0.08,
            'implementation_complexity': 0.12,
            'team_experience_level': 0.15,
            'available_resources': 0.10,
            'organizational_support': 0.05
        }
    
    def predict_repair_effect(self, issue: QualityIssue, 
                            suggestion: RepairSuggestion) -> EffectPrediction:
        """预测修复效果"""
        logger.info(f"预测建议 {suggestion.suggestion_id} 的修复效果")
        
        # 1. 提取预测特征
        features = self._extract_prediction_features(issue, suggestion)
        
        # 2. 查找相似历史案例
        similar_cases = self._find_similar_cases(features)
        
        # 3. 计算预测结果
        prediction_result = self._calculate_prediction(features, similar_cases)
        
        # 4. 评估预测置信度
        confidence = self._assess_prediction_confidence(similar_cases, features)
        
        # 5. 生成详细预测
        detailed_prediction = self._generate_detailed_prediction(
            features, similar_cases, prediction_result, confidence
        )
        
        self.prediction_counter += 1
        prediction_id = f"prediction_{self.prediction_counter:06d}"
        
        prediction = EffectPrediction(
            prediction_id=prediction_id,
            suggestion_id=suggestion.suggestion_id,
            success_probability=prediction_result['success_probability'],
            effect_level=prediction_result['effect_level'],
            confidence=confidence,
            time_to_resolution=detailed_prediction['time_to_resolution'],
            resource_utilization=detailed_prediction['resource_utilization'],
            risk_factors=detailed_prediction['risk_factors'],
            success_factors=detailed_prediction['success_factors'],
            quality_improvement_score=detailed_prediction['quality_score'],
            cost_effectiveness=detailed_prediction['cost_effectiveness'],
            implementation_difficulty=detailed_prediction['implementation_difficulty'],
            similar_cases_count=len(similar_cases),
            model_accuracy=self._calculate_model_accuracy(),
            feature_importance=self.feature_importance.copy()
        )
        
        logger.info(f"预测完成，成功概率: {prediction.success_probability:.2f}")
        return prediction
    
    def _extract_prediction_features(self, issue: QualityIssue, 
                                   suggestion: RepairSuggestion) -> PredictionFeatures:
        """提取预测特征"""
        
        # 解析工作量估算
        effort_hours = self._parse_effort_estimation(suggestion.estimated_effort)
        
        # 计算问题年龄
        problem_age = (datetime.now() - issue.created_at).days
        
        # 评估实施复杂度
        complexity = self._assess_implementation_complexity(suggestion)
        
        # 获取环境特征（简化实现，实际应从系统获取）
        team_experience = self._get_team_experience_level(suggestion.responsible_roles)
        available_resources = self._assess_resource_availability(suggestion.required_resources)
        organizational_support = self._assess_organizational_support(suggestion.priority)
        time_pressure = self._assess_time_pressure(issue.severity)
        
        # 获取历史特征
        historical_stats = self._get_historical_statistics(issue.category, suggestion.category)
        
        features = PredictionFeatures(
            problem_category=issue.category,
            severity_level=issue.severity,
            affected_data_count=len(issue.affected_data),
            problem_age_days=problem_age,
            action_category=suggestion.category,
            estimated_effort_hours=effort_hours,
            required_resources_count=len(suggestion.required_resources),
            implementation_complexity=complexity,
            team_experience_level=team_experience,
            available_resources=available_resources,
            organizational_support=organizational_support,
            time_pressure=time_pressure,
            similar_issues_count=historical_stats['similar_count'],
            previous_success_rate=historical_stats['success_rate'],
            average_resolution_time=historical_stats['avg_resolution_time']
        )
        
        return features
    
    def _parse_effort_estimation(self, effort_str: str) -> float:
        """解析工作量估算"""
        # 简化解析，实际应更复杂
        effort_mappings = {
            '立即': 1,
            '2-4小时': 3,
            '4-8小时': 6,
            '1-2天': 12,
            '1-2周': 60,
            '2-4周': 120,
            '1-3个月': 300,
            '2-6个月': 600
        }
        
        return effort_mappings.get(effort_str, 40)  # 默认40小时
    
    def _assess_implementation_complexity(self, suggestion: RepairSuggestion) -> float:
        """评估实施复杂度"""
        complexity_factors = {
            ActionCategory.TRAINING: 0.3,
            ActionCategory.PROCESS: 0.5,
            ActionCategory.TOOL: 0.6,
            ActionCategory.SYSTEM: 0.8,
            ActionCategory.POLICY: 0.4,
            ActionCategory.RESOURCE: 0.3
        }
        
        base_complexity = complexity_factors.get(suggestion.category, 0.5)
        
        # 基于步骤数量调整
        step_factor = min(len(suggestion.implementation_steps) / 10, 0.3)
        
        # 基于资源需求调整
        resource_factor = min(len(suggestion.required_resources) / 5, 0.2)
        
        return min(base_complexity + step_factor + resource_factor, 1.0)
    
    def _get_team_experience_level(self, roles: List[str]) -> float:
        """获取团队经验水平"""
        # 简化实现，基于角色类型
        experience_levels = {
            '质量管理员': 0.8,
            '技术经理': 0.9,
            '开发工程师': 0.7,
            '流程经理': 0.8,
            '培训经理': 0.7,
            '项目经理': 0.8
        }
        
        if not roles:
            return 0.5
        
        total_experience = sum(experience_levels.get(role, 0.6) for role in roles)
        return total_experience / len(roles)
    
    def _assess_resource_availability(self, resources: List[str]) -> float:
        """评估资源可用性"""
        # 简化实现，基于资源类型
        availability_scores = {
            '培训师': 0.7,
            '开发团队': 0.6,
            '测试环境': 0.8,
            '培训材料': 0.9,
            '质量检查员': 0.7,
            '管理层支持': 0.5
        }
        
        if not resources:
            return 0.8
        
        total_availability = sum(availability_scores.get(resource, 0.7) for resource in resources)
        return total_availability / len(resources)
    
    def _assess_organizational_support(self, priority: str) -> float:
        """评估组织支持度"""
        support_levels = {
            'critical': 0.9,
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
        
        return support_levels.get(priority, 0.6)
    
    def _assess_time_pressure(self, severity: SeverityLevel) -> float:
        """评估时间压力"""
        pressure_levels = {
            SeverityLevel.CRITICAL: 0.9,
            SeverityLevel.HIGH: 0.7,
            SeverityLevel.MEDIUM: 0.5,
            SeverityLevel.LOW: 0.3
        }
        
        return pressure_levels.get(severity, 0.5)
    
    def _get_historical_statistics(self, problem_category: ProblemCategory, 
                                 action_category: ActionCategory) -> Dict[str, float]:
        """获取历史统计信息"""
        # 过滤相关历史案例
        relevant_cases = [
            case for case in self.historical_cases
            if (case.features.problem_category == problem_category and
                case.features.action_category == action_category)
        ]
        
        if not relevant_cases:
            return {
                'similar_count': 0,
                'success_rate': 0.7,  # 默认成功率
                'avg_resolution_time': 40.0  # 默认解决时间
            }
        
        success_count = sum(1 for case in relevant_cases if case.actual_success)
        success_rate = success_count / len(relevant_cases)
        
        avg_resolution_time = np.mean([case.actual_resolution_time for case in relevant_cases])
        
        return {
            'similar_count': len(relevant_cases),
            'success_rate': success_rate,
            'avg_resolution_time': avg_resolution_time
        }
    
    def _find_similar_cases(self, features: PredictionFeatures, 
                          similarity_threshold: float = 0.7) -> List[HistoricalCase]:
        """查找相似历史案例"""
        similar_cases = []
        target_vector = features.to_vector()
        
        for case in self.historical_cases:
            case_vector = case.features.to_vector()
            
            # 计算余弦相似度
            similarity = self._calculate_cosine_similarity(target_vector, case_vector)
            
            if similarity >= similarity_threshold:
                similar_cases.append(case)
        
        # 按相似度排序
        similar_cases.sort(
            key=lambda case: self._calculate_cosine_similarity(
                target_vector, case.features.to_vector()
            ),
            reverse=True
        )
        
        return similar_cases[:10]  # 最多返回10个最相似的案例
    
    def _calculate_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _calculate_prediction(self, features: PredictionFeatures, 
                            similar_cases: List[HistoricalCase]) -> Dict[str, Any]:
        """计算预测结果"""
        
        if len(similar_cases) >= self.min_cases_for_prediction:
            # 基于相似案例的预测
            success_probability = self._predict_from_similar_cases(similar_cases)
            effect_level = self._predict_effect_level(features, similar_cases)
        else:
            # 基于规则的预测
            success_probability = self._predict_from_rules(features)
            effect_level = self._predict_effect_level_from_rules(features)
        
        return {
            'success_probability': success_probability,
            'effect_level': effect_level
        }
    
    def _predict_from_similar_cases(self, similar_cases: List[HistoricalCase]) -> float:
        """基于相似案例预测成功概率"""
        if not similar_cases:
            return 0.5
        
        # 加权平均，越相似的案例权重越高
        total_weight = 0
        weighted_success = 0
        
        for i, case in enumerate(similar_cases):
            # 权重递减
            weight = 1.0 / (i + 1)
            total_weight += weight
            
            if case.actual_success:
                weighted_success += weight
        
        return weighted_success / total_weight if total_weight > 0 else 0.5
    
    def _predict_from_rules(self, features: PredictionFeatures) -> float:
        """基于规则预测成功概率"""
        base_probability = 0.7
        
        # 基于问题严重程度调整
        severity_adjustments = {
            SeverityLevel.LOW: 0.1,
            SeverityLevel.MEDIUM: 0.0,
            SeverityLevel.HIGH: -0.1,
            SeverityLevel.CRITICAL: -0.2
        }
        
        probability = base_probability + severity_adjustments.get(features.severity_level, 0)
        
        # 基于团队经验调整
        probability += (features.team_experience_level - 0.5) * 0.3
        
        # 基于资源可用性调整
        probability += (features.available_resources - 0.5) * 0.2
        
        # 基于实施复杂度调整
        probability -= features.implementation_complexity * 0.3
        
        # 基于组织支持调整
        probability += (features.organizational_support - 0.5) * 0.2
        
        return max(0.1, min(0.95, probability))
    
    def _predict_effect_level(self, features: PredictionFeatures, 
                            similar_cases: List[HistoricalCase]) -> EffectLevel:
        """预测效果等级"""
        if similar_cases:
            # 基于相似案例
            effect_counts = defaultdict(int)
            for case in similar_cases:
                effect_counts[case.actual_effect_level] += 1
            
            # 返回最常见的效果等级
            most_common_effect = max(effect_counts, key=effect_counts.get)
            return most_common_effect
        else:
            # 基于规则
            return self._predict_effect_level_from_rules(features)
    
    def _predict_effect_level_from_rules(self, features: PredictionFeatures) -> EffectLevel:
        """基于规则预测效果等级"""
        
        # 基于行动类别的基础效果
        category_effects = {
            ActionCategory.TRAINING: EffectLevel.MODERATE,
            ActionCategory.PROCESS: EffectLevel.SIGNIFICANT,
            ActionCategory.TOOL: EffectLevel.MODERATE,
            ActionCategory.SYSTEM: EffectLevel.MAJOR,
            ActionCategory.POLICY: EffectLevel.SIGNIFICANT,
            ActionCategory.RESOURCE: EffectLevel.MODERATE
        }
        
        base_effect = category_effects.get(features.action_category, EffectLevel.MODERATE)
        
        # 基于问题严重程度调整
        if features.severity_level == SeverityLevel.CRITICAL:
            if base_effect == EffectLevel.MODERATE:
                return EffectLevel.SIGNIFICANT
            elif base_effect == EffectLevel.SIGNIFICANT:
                return EffectLevel.MAJOR
        
        return base_effect
    
    def _assess_prediction_confidence(self, similar_cases: List[HistoricalCase], 
                                    features: PredictionFeatures) -> PredictionConfidence:
        """评估预测置信度"""
        
        confidence_score = 0.0
        
        # 基于相似案例数量
        if len(similar_cases) >= 10:
            confidence_score += 0.4
        elif len(similar_cases) >= 5:
            confidence_score += 0.3
        elif len(similar_cases) >= 2:
            confidence_score += 0.2
        else:
            confidence_score += 0.1
        
        # 基于特征完整性
        feature_vector = features.to_vector()
        completeness = np.mean(feature_vector > 0)  # 非零特征比例
        confidence_score += completeness * 0.3
        
        # 基于模型准确率
        model_accuracy = self._calculate_model_accuracy()
        confidence_score += model_accuracy * 0.3
        
        # 转换为置信度等级
        if confidence_score >= 0.9:
            return PredictionConfidence.VERY_HIGH
        elif confidence_score >= 0.7:
            return PredictionConfidence.HIGH
        elif confidence_score >= 0.5:
            return PredictionConfidence.MEDIUM
        elif confidence_score >= 0.3:
            return PredictionConfidence.LOW
        else:
            return PredictionConfidence.VERY_LOW
    
    def _generate_detailed_prediction(self, features: PredictionFeatures,
                                    similar_cases: List[HistoricalCase],
                                    prediction_result: Dict[str, Any],
                                    confidence: PredictionConfidence) -> Dict[str, Any]:
        """生成详细预测"""
        
        # 预测解决时间
        if similar_cases:
            avg_resolution_time = np.mean([case.actual_resolution_time for case in similar_cases])
        else:
            avg_resolution_time = features.estimated_effort_hours
        
        # 调整解决时间
        time_adjustment = 1.0
        if features.team_experience_level < 0.5:
            time_adjustment *= 1.3
        if features.implementation_complexity > 0.7:
            time_adjustment *= 1.2
        if features.time_pressure > 0.8:
            time_adjustment *= 0.8  # 时间压力下可能加快
        
        predicted_time = avg_resolution_time * time_adjustment
        
        # 资源利用率
        resource_utilization = min(
            features.available_resources * 
            (1 + features.organizational_support) * 0.5, 
            1.0
        )
        
        # 风险因素
        risk_factors = self._identify_risk_factors(features)
        
        # 成功因素
        success_factors = self._identify_success_factors(features)
        
        # 质量改进分数
        quality_score = self._calculate_quality_improvement_score(features, prediction_result)
        
        # 成本效益
        cost_effectiveness = self._calculate_cost_effectiveness(features, prediction_result)
        
        # 实施难度
        implementation_difficulty = features.implementation_complexity
        
        return {
            'time_to_resolution': predicted_time,
            'resource_utilization': resource_utilization,
            'risk_factors': risk_factors,
            'success_factors': success_factors,
            'quality_score': quality_score,
            'cost_effectiveness': cost_effectiveness,
            'implementation_difficulty': implementation_difficulty
        }
    
    def _identify_risk_factors(self, features: PredictionFeatures) -> List[str]:
        """识别风险因素"""
        risk_factors = []
        
        if features.team_experience_level < 0.5:
            risk_factors.append("团队经验不足")
        
        if features.available_resources < 0.5:
            risk_factors.append("资源不足")
        
        if features.implementation_complexity > 0.7:
            risk_factors.append("实施复杂度高")
        
        if features.time_pressure > 0.8:
            risk_factors.append("时间压力大")
        
        if features.organizational_support < 0.5:
            risk_factors.append("组织支持不足")
        
        if features.previous_success_rate < 0.5:
            risk_factors.append("历史成功率低")
        
        return risk_factors
    
    def _identify_success_factors(self, features: PredictionFeatures) -> List[str]:
        """识别成功因素"""
        success_factors = []
        
        if features.team_experience_level > 0.7:
            success_factors.append("团队经验丰富")
        
        if features.available_resources > 0.7:
            success_factors.append("资源充足")
        
        if features.organizational_support > 0.7:
            success_factors.append("组织支持强")
        
        if features.previous_success_rate > 0.7:
            success_factors.append("历史成功率高")
        
        if features.implementation_complexity < 0.3:
            success_factors.append("实施相对简单")
        
        return success_factors
    
    def _calculate_quality_improvement_score(self, features: PredictionFeatures,
                                           prediction_result: Dict[str, Any]) -> float:
        """计算质量改进分数"""
        base_score = 60.0
        
        # 基于效果等级调整
        effect_adjustments = {
            EffectLevel.MINIMAL: -20,
            EffectLevel.MODERATE: 0,
            EffectLevel.SIGNIFICANT: 15,
            EffectLevel.MAJOR: 25,
            EffectLevel.TRANSFORMATIVE: 35
        }
        
        effect_level = prediction_result['effect_level']
        score = base_score + effect_adjustments.get(effect_level, 0)
        
        # 基于成功概率调整
        success_prob = prediction_result['success_probability']
        score *= success_prob
        
        return min(max(score, 0), 100)
    
    def _calculate_cost_effectiveness(self, features: PredictionFeatures,
                                    prediction_result: Dict[str, Any]) -> float:
        """计算成本效益"""
        # 简化计算：效果/成本
        effect_value = {
            EffectLevel.MINIMAL: 0.2,
            EffectLevel.MODERATE: 0.4,
            EffectLevel.SIGNIFICANT: 0.6,
            EffectLevel.MAJOR: 0.8,
            EffectLevel.TRANSFORMATIVE: 1.0
        }
        
        effect_level = prediction_result['effect_level']
        effect_score = effect_value.get(effect_level, 0.4)
        
        # 成本基于工作量和复杂度
        cost_factor = (features.estimated_effort_hours / 100) * (1 + features.implementation_complexity)
        cost_factor = max(cost_factor, 0.1)  # 避免除零
        
        effectiveness = effect_score / cost_factor
        return min(effectiveness, 1.0)
    
    def _calculate_model_accuracy(self) -> float:
        """计算模型准确率"""
        if len(self.historical_cases) < 5:
            return 0.7  # 默认准确率
        
        # 简化计算，实际应该用交叉验证
        correct_predictions = 0
        total_predictions = 0
        
        for case in self.historical_cases[-20:]:  # 最近20个案例
            # 模拟预测
            predicted_success = case.features.previous_success_rate > 0.5
            actual_success = case.actual_success
            
            if predicted_success == actual_success:
                correct_predictions += 1
            total_predictions += 1
        
        return correct_predictions / total_predictions if total_predictions > 0 else 0.7
    
    def add_historical_case(self, case: HistoricalCase):
        """添加历史案例"""
        self.historical_cases.append(case)
        logger.info(f"添加历史案例 {case.case_id}，总案例数: {len(self.historical_cases)}")
    
    def predict_plan_effect(self, plan: RepairPlan) -> Dict[str, Any]:
        """预测修复计划的整体效果"""
        all_suggestions = (
            plan.immediate_actions + 
            plan.short_term_actions + 
            plan.long_term_actions + 
            plan.preventive_actions
        )
        
        if not all_suggestions:
            return {"error": "计划中没有建议"}
        
        # 为每个建议生成预测（简化，实际需要问题信息）
        # 这里返回聚合预测
        
        avg_success_prob = np.mean([s.success_probability for s in all_suggestions])
        total_effort = sum(self._parse_effort_estimation(s.estimated_effort) for s in all_suggestions)
        
        return {
            'plan_id': plan.plan_id,
            'overall_success_probability': avg_success_prob,
            'total_estimated_effort': total_effort,
            'risk_assessment': 'medium',  # 简化
            'recommendation': '建议按优先级逐步实施'
        }
    
    def get_prediction_statistics(self) -> Dict[str, Any]:
        """获取预测统计信息"""
        return {
            'total_predictions': self.prediction_counter,
            'historical_cases': len(self.historical_cases),
            'model_accuracy': self._calculate_model_accuracy(),
            'feature_importance': self.feature_importance
        }