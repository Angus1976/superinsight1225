"""
修复建议智能生成器

基于问题分析和历史数据，智能生成针对性的修复建议和解决方案。
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import logging

from .root_cause_analyzer import (
    QualityIssue, RootCauseAnalysis, RootCauseType, 
    ProblemCategory, SeverityLevel
)
from .pattern_classifier import QualityPattern, PatternType

logger = logging.getLogger(__name__)


class SuggestionType(str, Enum):
    """建议类型"""
    IMMEDIATE = "immediate"  # 立即行动
    SHORT_TERM = "short_term"  # 短期措施
    LONG_TERM = "long_term"  # 长期改进
    PREVENTIVE = "preventive"  # 预防措施


class SuggestionPriority(str, Enum):
    """建议优先级"""
    CRITICAL = "critical"  # 关键
    HIGH = "high"  # 高
    MEDIUM = "medium"  # 中
    LOW = "low"  # 低


class ActionCategory(str, Enum):
    """行动类别"""
    TRAINING = "training"  # 培训
    PROCESS = "process"  # 流程改进
    TOOL = "tool"  # 工具优化
    SYSTEM = "system"  # 系统修复
    POLICY = "policy"  # 政策调整
    RESOURCE = "resource"  # 资源配置


@dataclass
class RepairSuggestion:
    """修复建议"""
    suggestion_id: str
    title: str
    description: str
    suggestion_type: SuggestionType
    priority: SuggestionPriority
    category: ActionCategory
    
    # 实施信息
    estimated_effort: str  # 预估工作量
    estimated_duration: str  # 预估时间
    required_resources: List[str]  # 所需资源
    responsible_roles: List[str]  # 负责角色
    
    # 效果预测
    expected_impact: str  # 预期影响
    success_probability: float  # 成功概率 (0-1)
    risk_level: str  # 风险等级
    
    # 实施步骤
    implementation_steps: List[str]  # 实施步骤
    success_criteria: List[str]  # 成功标准
    monitoring_metrics: List[str]  # 监控指标
    
    # 关联信息
    related_issues: List[str] = field(default_factory=list)  # 相关问题
    dependencies: List[str] = field(default_factory=list)  # 依赖项
    alternatives: List[str] = field(default_factory=list)  # 替代方案
    
    # 元数据
    generated_at: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'suggestion_id': self.suggestion_id,
            'title': self.title,
            'description': self.description,
            'suggestion_type': self.suggestion_type.value,
            'priority': self.priority.value,
            'category': self.category.value,
            'estimated_effort': self.estimated_effort,
            'estimated_duration': self.estimated_duration,
            'required_resources': self.required_resources,
            'responsible_roles': self.responsible_roles,
            'expected_impact': self.expected_impact,
            'success_probability': self.success_probability,
            'risk_level': self.risk_level,
            'implementation_steps': self.implementation_steps,
            'success_criteria': self.success_criteria,
            'monitoring_metrics': self.monitoring_metrics,
            'related_issues': self.related_issues,
            'dependencies': self.dependencies,
            'alternatives': self.alternatives,
            'generated_at': self.generated_at.isoformat(),
            'confidence_score': self.confidence_score
        }


@dataclass
class RepairPlan:
    """修复计划"""
    plan_id: str
    issue_id: str
    title: str
    description: str
    
    # 建议列表
    immediate_actions: List[RepairSuggestion]
    short_term_actions: List[RepairSuggestion]
    long_term_actions: List[RepairSuggestion]
    preventive_actions: List[RepairSuggestion]
    
    # 计划信息
    total_estimated_effort: str
    total_estimated_duration: str
    overall_success_probability: float
    overall_risk_assessment: str
    
    # 实施时间线
    timeline: Dict[str, List[str]]  # 时间线安排
    milestones: List[Dict[str, Any]]  # 里程碑
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'plan_id': self.plan_id,
            'issue_id': self.issue_id,
            'title': self.title,
            'description': self.description,
            'immediate_actions': [action.to_dict() for action in self.immediate_actions],
            'short_term_actions': [action.to_dict() for action in self.short_term_actions],
            'long_term_actions': [action.to_dict() for action in self.long_term_actions],
            'preventive_actions': [action.to_dict() for action in self.preventive_actions],
            'total_estimated_effort': self.total_estimated_effort,
            'total_estimated_duration': self.total_estimated_duration,
            'overall_success_probability': self.overall_success_probability,
            'overall_risk_assessment': self.overall_risk_assessment,
            'timeline': self.timeline,
            'milestones': self.milestones,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by
        }


class RepairSuggestionGenerator:
    """修复建议生成器"""
    
    def __init__(self):
        self.suggestion_counter = 0
        self.plan_counter = 0
        self.suggestion_templates = self._initialize_suggestion_templates()
        self.success_history: Dict[str, List[float]] = {}  # 建议成功率历史
        
    def _initialize_suggestion_templates(self) -> Dict[str, Dict]:
        """初始化建议模板"""
        return {
            # 人为错误相关建议
            RootCauseType.HUMAN_ERROR.value: {
                'immediate': [
                    {
                        'title': '立即复查和修正',
                        'description': '对受影响的数据进行人工复查和修正',
                        'category': ActionCategory.PROCESS,
                        'effort': '2-4小时',
                        'duration': '当天完成',
                        'resources': ['质量检查员', '数据修正工具'],
                        'roles': ['质量管理员', '数据分析师'],
                        'steps': [
                            '识别所有受影响的数据记录',
                            '进行逐条人工复查',
                            '修正发现的错误',
                            '验证修正结果'
                        ]
                    }
                ],
                'short_term': [
                    {
                        'title': '实施双重检查机制',
                        'description': '建立双重检查流程，减少人为错误',
                        'category': ActionCategory.PROCESS,
                        'effort': '1-2周',
                        'duration': '2周',
                        'resources': ['流程设计师', '培训材料'],
                        'roles': ['流程经理', '质量主管'],
                        'steps': [
                            '设计双重检查流程',
                            '培训相关人员',
                            '试运行流程',
                            '正式实施'
                        ]
                    }
                ],
                'long_term': [
                    {
                        'title': '自动化验证系统',
                        'description': '开发自动化验证系统，减少人工依赖',
                        'category': ActionCategory.SYSTEM,
                        'effort': '1-3个月',
                        'duration': '3个月',
                        'resources': ['开发团队', '测试环境', '验证规则库'],
                        'roles': ['技术经理', '开发工程师', '测试工程师'],
                        'steps': [
                            '需求分析和设计',
                            '开发验证算法',
                            '系统集成测试',
                            '部署和监控'
                        ]
                    }
                ]
            },
            
            # 培训不足相关建议
            RootCauseType.TRAINING_GAP.value: {
                'immediate': [
                    {
                        'title': '紧急培训补强',
                        'description': '针对相关人员进行紧急培训',
                        'category': ActionCategory.TRAINING,
                        'effort': '4-8小时',
                        'duration': '1-2天',
                        'resources': ['培训师', '培训材料', '培训场地'],
                        'roles': ['培训经理', '技术专家'],
                        'steps': [
                            '识别培训需求',
                            '准备培训材料',
                            '组织培训会议',
                            '评估培训效果'
                        ]
                    }
                ],
                'short_term': [
                    {
                        'title': '系统性技能培训',
                        'description': '制定系统性的技能培训计划',
                        'category': ActionCategory.TRAINING,
                        'effort': '2-4周',
                        'duration': '1个月',
                        'resources': ['培训课程', '在线学习平台', '认证体系'],
                        'roles': ['HR经理', '培训专员', '业务专家'],
                        'steps': [
                            '技能差距分析',
                            '制定培训计划',
                            '开发培训内容',
                            '实施培训项目',
                            '技能认证考核'
                        ]
                    }
                ]
            },
            
            # 系统缺陷相关建议
            RootCauseType.SYSTEM_BUG.value: {
                'immediate': [
                    {
                        'title': '系统热修复',
                        'description': '部署紧急修复补丁',
                        'category': ActionCategory.SYSTEM,
                        'effort': '2-6小时',
                        'duration': '当天',
                        'resources': ['开发团队', '测试环境', '部署工具'],
                        'roles': ['技术经理', '开发工程师', '运维工程师'],
                        'steps': [
                            '问题定位和分析',
                            '开发修复补丁',
                            '测试验证',
                            '部署到生产环境'
                        ]
                    }
                ],
                'long_term': [
                    {
                        'title': '系统架构优化',
                        'description': '优化系统架构，提高稳定性',
                        'category': ActionCategory.SYSTEM,
                        'effort': '2-6个月',
                        'duration': '6个月',
                        'resources': ['架构师', '开发团队', '测试团队'],
                        'roles': ['技术总监', '架构师', '项目经理'],
                        'steps': [
                            '系统架构评估',
                            '优化方案设计',
                            '分阶段实施',
                            '性能测试验证'
                        ]
                    }
                ]
            }
        }
    
    def generate_suggestions(self, issue: QualityIssue, 
                           root_cause_analysis: RootCauseAnalysis,
                           related_patterns: Optional[List[QualityPattern]] = None) -> List[RepairSuggestion]:
        """生成修复建议"""
        logger.info(f"为问题 {issue.id} 生成修复建议")
        
        suggestions = []
        
        # 1. 基于根因分析生成建议
        root_cause_suggestions = self._generate_root_cause_suggestions(
            issue, root_cause_analysis
        )
        suggestions.extend(root_cause_suggestions)
        
        # 2. 基于问题模式生成建议
        if related_patterns:
            pattern_suggestions = self._generate_pattern_suggestions(
                issue, related_patterns
            )
            suggestions.extend(pattern_suggestions)
        
        # 3. 基于问题严重程度生成建议
        severity_suggestions = self._generate_severity_suggestions(issue)
        suggestions.extend(severity_suggestions)
        
        # 4. 基于历史成功经验生成建议
        historical_suggestions = self._generate_historical_suggestions(issue)
        suggestions.extend(historical_suggestions)
        
        # 5. 去重和排序
        unique_suggestions = self._deduplicate_suggestions(suggestions)
        sorted_suggestions = self._sort_suggestions(unique_suggestions)
        
        logger.info(f"为问题 {issue.id} 生成了 {len(sorted_suggestions)} 个建议")
        return sorted_suggestions
    
    def _generate_root_cause_suggestions(self, issue: QualityIssue, 
                                       analysis: RootCauseAnalysis) -> List[RepairSuggestion]:
        """基于根因分析生成建议"""
        suggestions = []
        
        # 主要根因建议
        primary_suggestions = self._get_suggestions_for_cause(
            analysis.primary_cause, issue, weight=1.0
        )
        suggestions.extend(primary_suggestions)
        
        # 贡献因素建议
        for factor in analysis.contributing_factors:
            factor_suggestions = self._get_suggestions_for_cause(
                factor, issue, weight=0.6
            )
            suggestions.extend(factor_suggestions)
        
        return suggestions
    
    def _get_suggestions_for_cause(self, cause: RootCauseType, 
                                 issue: QualityIssue, weight: float) -> List[RepairSuggestion]:
        """获取特定根因的建议"""
        suggestions = []
        cause_templates = self.suggestion_templates.get(cause.value, {})
        
        for suggestion_type in [SuggestionType.IMMEDIATE, SuggestionType.SHORT_TERM, SuggestionType.LONG_TERM]:
            type_templates = cause_templates.get(suggestion_type.value, [])
            
            for template in type_templates:
                suggestion = self._create_suggestion_from_template(
                    template, suggestion_type, issue, weight
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _create_suggestion_from_template(self, template: Dict, 
                                       suggestion_type: SuggestionType,
                                       issue: QualityIssue, weight: float) -> RepairSuggestion:
        """从模板创建建议"""
        self.suggestion_counter += 1
        suggestion_id = f"suggestion_{self.suggestion_counter:06d}"
        
        # 基于问题严重程度调整优先级
        base_priority = self._calculate_priority(suggestion_type, issue.severity)
        
        # 基于权重调整置信度
        confidence_score = min(weight * 0.8, 1.0)
        
        # 预测成功概率
        success_probability = self._predict_success_probability(
            template['category'], issue.category, confidence_score
        )
        
        suggestion = RepairSuggestion(
            suggestion_id=suggestion_id,
            title=template['title'],
            description=template['description'],
            suggestion_type=suggestion_type,
            priority=base_priority,
            category=template['category'],
            estimated_effort=template['effort'],
            estimated_duration=template['duration'],
            required_resources=template['resources'],
            responsible_roles=template['roles'],
            expected_impact=self._calculate_expected_impact(suggestion_type, issue.severity),
            success_probability=success_probability,
            risk_level=self._assess_risk_level(template['category'], suggestion_type),
            implementation_steps=template['steps'],
            success_criteria=self._generate_success_criteria(template, issue),
            monitoring_metrics=self._generate_monitoring_metrics(template, issue),
            related_issues=[issue.id],
            confidence_score=confidence_score
        )
        
        return suggestion
    
    def _calculate_priority(self, suggestion_type: SuggestionType, 
                          severity: SeverityLevel) -> SuggestionPriority:
        """计算建议优先级"""
        # 基础优先级映射
        type_priority = {
            SuggestionType.IMMEDIATE: SuggestionPriority.CRITICAL,
            SuggestionType.SHORT_TERM: SuggestionPriority.HIGH,
            SuggestionType.LONG_TERM: SuggestionPriority.MEDIUM,
            SuggestionType.PREVENTIVE: SuggestionPriority.LOW
        }
        
        base_priority = type_priority[suggestion_type]
        
        # 基于严重程度调整
        if severity == SeverityLevel.CRITICAL:
            if base_priority == SuggestionPriority.HIGH:
                return SuggestionPriority.CRITICAL
        elif severity == SeverityLevel.LOW:
            if base_priority == SuggestionPriority.MEDIUM:
                return SuggestionPriority.LOW
        
        return base_priority
    
    def _predict_success_probability(self, category: ActionCategory, 
                                   problem_category: ProblemCategory,
                                   confidence_score: float) -> float:
        """预测成功概率"""
        # 基础成功率
        base_rates = {
            ActionCategory.TRAINING: 0.75,
            ActionCategory.PROCESS: 0.80,
            ActionCategory.TOOL: 0.70,
            ActionCategory.SYSTEM: 0.85,
            ActionCategory.POLICY: 0.65,
            ActionCategory.RESOURCE: 0.70
        }
        
        base_rate = base_rates.get(category, 0.70)
        
        # 基于历史数据调整
        category_key = f"{category.value}_{problem_category.value}"
        if category_key in self.success_history:
            historical_rate = sum(self.success_history[category_key]) / len(self.success_history[category_key])
            # 历史数据权重30%，基础率权重70%
            adjusted_rate = base_rate * 0.7 + historical_rate * 0.3
        else:
            adjusted_rate = base_rate
        
        # 基于置信度调整
        final_rate = adjusted_rate * confidence_score
        
        return min(max(final_rate, 0.1), 0.95)  # 限制在0.1-0.95之间
    
    def _calculate_expected_impact(self, suggestion_type: SuggestionType, 
                                 severity: SeverityLevel) -> str:
        """计算预期影响"""
        impact_matrix = {
            (SuggestionType.IMMEDIATE, SeverityLevel.CRITICAL): "显著改善",
            (SuggestionType.IMMEDIATE, SeverityLevel.HIGH): "明显改善",
            (SuggestionType.IMMEDIATE, SeverityLevel.MEDIUM): "适度改善",
            (SuggestionType.IMMEDIATE, SeverityLevel.LOW): "轻微改善",
            
            (SuggestionType.SHORT_TERM, SeverityLevel.CRITICAL): "根本性改善",
            (SuggestionType.SHORT_TERM, SeverityLevel.HIGH): "显著改善",
            (SuggestionType.SHORT_TERM, SeverityLevel.MEDIUM): "明显改善",
            (SuggestionType.SHORT_TERM, SeverityLevel.LOW): "适度改善",
            
            (SuggestionType.LONG_TERM, SeverityLevel.CRITICAL): "系统性改善",
            (SuggestionType.LONG_TERM, SeverityLevel.HIGH): "根本性改善",
            (SuggestionType.LONG_TERM, SeverityLevel.MEDIUM): "显著改善",
            (SuggestionType.LONG_TERM, SeverityLevel.LOW): "明显改善"
        }
        
        return impact_matrix.get((suggestion_type, severity), "适度改善")
    
    def _assess_risk_level(self, category: ActionCategory, 
                          suggestion_type: SuggestionType) -> str:
        """评估风险等级"""
        # 基于类别的基础风险
        category_risk = {
            ActionCategory.TRAINING: "低",
            ActionCategory.PROCESS: "中",
            ActionCategory.TOOL: "中",
            ActionCategory.SYSTEM: "高",
            ActionCategory.POLICY: "中",
            ActionCategory.RESOURCE: "低"
        }
        
        base_risk = category_risk.get(category, "中")
        
        # 基于类型调整风险
        if suggestion_type == SuggestionType.IMMEDIATE:
            if base_risk == "低":
                return "中"
            elif base_risk == "中":
                return "高"
        
        return base_risk
    
    def _generate_success_criteria(self, template: Dict, issue: QualityIssue) -> List[str]:
        """生成成功标准"""
        criteria = [
            "问题不再重复出现",
            "相关质量指标改善",
            "用户满意度提升"
        ]
        
        # 基于问题类别添加特定标准
        if issue.category == ProblemCategory.ACCURACY:
            criteria.append("准确率提升至95%以上")
        elif issue.category == ProblemCategory.PERFORMANCE:
            criteria.append("响应时间改善50%以上")
        elif issue.category == ProblemCategory.CONSISTENCY:
            criteria.append("一致性检查通过率达到98%")
        
        return criteria
    
    def _generate_monitoring_metrics(self, template: Dict, issue: QualityIssue) -> List[str]:
        """生成监控指标"""
        metrics = [
            "问题发生频率",
            "修复时间",
            "客户满意度"
        ]
        
        # 基于行动类别添加特定指标
        category = template['category']
        if category == ActionCategory.TRAINING:
            metrics.extend(["培训完成率", "技能测试分数"])
        elif category == ActionCategory.SYSTEM:
            metrics.extend(["系统可用性", "错误率"])
        elif category == ActionCategory.PROCESS:
            metrics.extend(["流程合规率", "处理效率"])
        
        return metrics
    
    def _generate_pattern_suggestions(self, issue: QualityIssue, 
                                    patterns: List[QualityPattern]) -> List[RepairSuggestion]:
        """基于问题模式生成建议"""
        suggestions = []
        
        for pattern in patterns:
            # 使用模式的预防措施作为建议
            for measure in pattern.prevention_measures:
                suggestion = self._create_pattern_suggestion(measure, pattern, issue)
                suggestions.append(suggestion)
        
        return suggestions
    
    def _create_pattern_suggestion(self, measure: str, pattern: QualityPattern, 
                                 issue: QualityIssue) -> RepairSuggestion:
        """创建基于模式的建议"""
        self.suggestion_counter += 1
        suggestion_id = f"pattern_suggestion_{self.suggestion_counter:06d}"
        
        # 基于模式类型确定建议类型
        suggestion_type = self._determine_suggestion_type_from_pattern(pattern.pattern_type)
        
        suggestion = RepairSuggestion(
            suggestion_id=suggestion_id,
            title=f"模式预防: {measure}",
            description=f"基于模式 '{pattern.name}' 的预防措施",
            suggestion_type=suggestion_type,
            priority=SuggestionPriority.MEDIUM,
            category=ActionCategory.PROCESS,  # 默认为流程类
            estimated_effort="1-2周",
            estimated_duration="2周",
            required_resources=["流程团队", "相关工具"],
            responsible_roles=["流程经理", "质量主管"],
            expected_impact="预防类似问题",
            success_probability=0.75,
            risk_level="中",
            implementation_steps=[
                "分析当前状况",
                "制定实施计划",
                "执行预防措施",
                "监控效果"
            ],
            success_criteria=["模式发生频率降低", "相关问题减少"],
            monitoring_metrics=["模式匹配率", "问题发生频率"],
            related_issues=[issue.id],
            confidence_score=pattern.confidence_score
        )
        
        return suggestion
    
    def _determine_suggestion_type_from_pattern(self, pattern_type: PatternType) -> SuggestionType:
        """基于模式类型确定建议类型"""
        type_mapping = {
            PatternType.RECURRING: SuggestionType.SHORT_TERM,
            PatternType.SEASONAL: SuggestionType.LONG_TERM,
            PatternType.ESCALATING: SuggestionType.IMMEDIATE,
            PatternType.CLUSTERED: SuggestionType.SHORT_TERM,
            PatternType.ANOMALY: SuggestionType.PREVENTIVE
        }
        
        return type_mapping.get(pattern_type, SuggestionType.SHORT_TERM)
    
    def _generate_severity_suggestions(self, issue: QualityIssue) -> List[RepairSuggestion]:
        """基于问题严重程度生成建议"""
        suggestions = []
        
        if issue.severity == SeverityLevel.CRITICAL:
            # 关键问题的紧急建议
            emergency_suggestion = self._create_emergency_suggestion(issue)
            suggestions.append(emergency_suggestion)
        
        return suggestions
    
    def _create_emergency_suggestion(self, issue: QualityIssue) -> RepairSuggestion:
        """创建紧急建议"""
        self.suggestion_counter += 1
        suggestion_id = f"emergency_{self.suggestion_counter:06d}"
        
        suggestion = RepairSuggestion(
            suggestion_id=suggestion_id,
            title="紧急响应流程",
            description="启动紧急响应流程，立即处理关键问题",
            suggestion_type=SuggestionType.IMMEDIATE,
            priority=SuggestionPriority.CRITICAL,
            category=ActionCategory.PROCESS,
            estimated_effort="立即",
            estimated_duration="2-4小时",
            required_resources=["应急团队", "管理层支持"],
            responsible_roles=["应急响应经理", "技术负责人"],
            expected_impact="快速控制问题影响",
            success_probability=0.90,
            risk_level="低",
            implementation_steps=[
                "立即通知相关人员",
                "评估问题影响范围",
                "实施临时解决方案",
                "监控问题状态"
            ],
            success_criteria=["问题得到控制", "影响范围不扩大"],
            monitoring_metrics=["响应时间", "问题状态"],
            related_issues=[issue.id],
            confidence_score=0.95
        )
        
        return suggestion
    
    def _generate_historical_suggestions(self, issue: QualityIssue) -> List[RepairSuggestion]:
        """基于历史成功经验生成建议"""
        # 这里可以基于历史数据生成建议
        # 简化实现，返回空列表
        return []
    
    def _deduplicate_suggestions(self, suggestions: List[RepairSuggestion]) -> List[RepairSuggestion]:
        """去重建议"""
        seen_titles = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            if suggestion.title not in seen_titles:
                seen_titles.add(suggestion.title)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions
    
    def _sort_suggestions(self, suggestions: List[RepairSuggestion]) -> List[RepairSuggestion]:
        """排序建议"""
        # 优先级权重
        priority_weights = {
            SuggestionPriority.CRITICAL: 4,
            SuggestionPriority.HIGH: 3,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 1
        }
        
        # 类型权重
        type_weights = {
            SuggestionType.IMMEDIATE: 4,
            SuggestionType.SHORT_TERM: 3,
            SuggestionType.LONG_TERM: 2,
            SuggestionType.PREVENTIVE: 1
        }
        
        def sort_key(suggestion: RepairSuggestion) -> Tuple[int, int, float]:
            priority_weight = priority_weights.get(suggestion.priority, 1)
            type_weight = type_weights.get(suggestion.suggestion_type, 1)
            confidence = suggestion.confidence_score
            
            return (-priority_weight, -type_weight, -confidence)
        
        return sorted(suggestions, key=sort_key)
    
    def create_repair_plan(self, issue: QualityIssue, 
                          suggestions: List[RepairSuggestion]) -> RepairPlan:
        """创建修复计划"""
        self.plan_counter += 1
        plan_id = f"repair_plan_{self.plan_counter:06d}"
        
        # 按类型分组建议
        immediate_actions = [s for s in suggestions if s.suggestion_type == SuggestionType.IMMEDIATE]
        short_term_actions = [s for s in suggestions if s.suggestion_type == SuggestionType.SHORT_TERM]
        long_term_actions = [s for s in suggestions if s.suggestion_type == SuggestionType.LONG_TERM]
        preventive_actions = [s for s in suggestions if s.suggestion_type == SuggestionType.PREVENTIVE]
        
        # 计算总体信息
        total_effort = self._calculate_total_effort(suggestions)
        total_duration = self._calculate_total_duration(suggestions)
        overall_success_probability = self._calculate_overall_success_probability(suggestions)
        overall_risk = self._assess_overall_risk(suggestions)
        
        # 生成时间线
        timeline = self._generate_timeline(suggestions)
        milestones = self._generate_milestones(suggestions)
        
        plan = RepairPlan(
            plan_id=plan_id,
            issue_id=issue.id,
            title=f"问题修复计划 - {issue.id}",
            description=f"针对 {issue.category.value} 类问题的综合修复计划",
            immediate_actions=immediate_actions,
            short_term_actions=short_term_actions,
            long_term_actions=long_term_actions,
            preventive_actions=preventive_actions,
            total_estimated_effort=total_effort,
            total_estimated_duration=total_duration,
            overall_success_probability=overall_success_probability,
            overall_risk_assessment=overall_risk,
            timeline=timeline,
            milestones=milestones
        )
        
        return plan
    
    def _calculate_total_effort(self, suggestions: List[RepairSuggestion]) -> str:
        """计算总工作量"""
        # 简化计算，基于建议数量
        if len(suggestions) <= 3:
            return "1-2周"
        elif len(suggestions) <= 6:
            return "2-4周"
        else:
            return "1-3个月"
    
    def _calculate_total_duration(self, suggestions: List[RepairSuggestion]) -> str:
        """计算总持续时间"""
        # 简化计算，基于最长的建议
        has_long_term = any(s.suggestion_type == SuggestionType.LONG_TERM for s in suggestions)
        has_short_term = any(s.suggestion_type == SuggestionType.SHORT_TERM for s in suggestions)
        
        if has_long_term:
            return "3-6个月"
        elif has_short_term:
            return "1-2个月"
        else:
            return "1-2周"
    
    def _calculate_overall_success_probability(self, suggestions: List[RepairSuggestion]) -> float:
        """计算总体成功概率"""
        if not suggestions:
            return 0.0
        
        # 使用加权平均
        total_weight = 0
        weighted_sum = 0
        
        for suggestion in suggestions:
            weight = 1.0 if suggestion.priority == SuggestionPriority.CRITICAL else 0.8
            weighted_sum += suggestion.success_probability * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _assess_overall_risk(self, suggestions: List[RepairSuggestion]) -> str:
        """评估总体风险"""
        risk_counts = {"低": 0, "中": 0, "高": 0}
        
        for suggestion in suggestions:
            risk_counts[suggestion.risk_level] += 1
        
        if risk_counts["高"] > 0:
            return "高"
        elif risk_counts["中"] > risk_counts["低"]:
            return "中"
        else:
            return "低"
    
    def _generate_timeline(self, suggestions: List[RepairSuggestion]) -> Dict[str, List[str]]:
        """生成时间线"""
        timeline = {
            "第1周": [],
            "第2-4周": [],
            "第2-3个月": [],
            "长期": []
        }
        
        for suggestion in suggestions:
            if suggestion.suggestion_type == SuggestionType.IMMEDIATE:
                timeline["第1周"].append(suggestion.title)
            elif suggestion.suggestion_type == SuggestionType.SHORT_TERM:
                timeline["第2-4周"].append(suggestion.title)
            elif suggestion.suggestion_type == SuggestionType.LONG_TERM:
                timeline["第2-3个月"].append(suggestion.title)
            else:
                timeline["长期"].append(suggestion.title)
        
        return timeline
    
    def _generate_milestones(self, suggestions: List[RepairSuggestion]) -> List[Dict[str, Any]]:
        """生成里程碑"""
        milestones = []
        
        # 基于建议类型生成里程碑
        if any(s.suggestion_type == SuggestionType.IMMEDIATE for s in suggestions):
            milestones.append({
                "name": "紧急措施完成",
                "description": "所有紧急措施已实施",
                "target_date": "1周内",
                "success_criteria": ["紧急问题得到控制", "影响范围稳定"]
            })
        
        if any(s.suggestion_type == SuggestionType.SHORT_TERM for s in suggestions):
            milestones.append({
                "name": "短期改进完成",
                "description": "短期改进措施已实施",
                "target_date": "1个月内",
                "success_criteria": ["流程改进到位", "问题发生率下降"]
            })
        
        if any(s.suggestion_type == SuggestionType.LONG_TERM for s in suggestions):
            milestones.append({
                "name": "长期优化完成",
                "description": "长期优化措施已实施",
                "target_date": "3-6个月内",
                "success_criteria": ["系统性改进到位", "根本问题解决"]
            })
        
        return milestones
    
    def update_success_history(self, suggestion_id: str, success: bool):
        """更新建议成功历史"""
        # 这里可以实现成功率跟踪
        # 简化实现
        pass
    
    def get_suggestion_statistics(self) -> Dict[str, Any]:
        """获取建议统计信息"""
        return {
            "total_suggestions_generated": self.suggestion_counter,
            "total_plans_created": self.plan_counter,
            "success_history_entries": len(self.success_history)
        }