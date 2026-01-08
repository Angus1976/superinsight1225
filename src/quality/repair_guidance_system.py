"""
修复指导和培训系统

提供个性化修复指导推荐、最佳实践案例库、培训资源推荐和修复技能提升跟踪。
"""

from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import logging
from collections import defaultdict, Counter

from .root_cause_analyzer import QualityIssue, RootCauseType, ProblemCategory, SeverityLevel
from .repair_suggestion_generator import RepairSuggestion, ActionCategory

logger = logging.getLogger(__name__)


class GuidanceType(str, Enum):
    """指导类型"""
    STEP_BY_STEP = "step_by_step"  # 分步指导
    BEST_PRACTICE = "best_practice"  # 最佳实践
    TROUBLESHOOTING = "troubleshooting"  # 故障排除
    PREVENTION = "prevention"  # 预防指导
    TRAINING = "training"  # 培训指导


class SkillLevel(str, Enum):
    """技能水平"""
    BEGINNER = "beginner"  # 初级
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"  # 高级
    EXPERT = "expert"  # 专家


class TrainingType(str, Enum):
    """培训类型"""
    ONLINE_COURSE = "online_course"  # 在线课程
    WORKSHOP = "workshop"  # 工作坊
    DOCUMENTATION = "documentation"  # 文档
    VIDEO_TUTORIAL = "video_tutorial"  # 视频教程
    HANDS_ON_PRACTICE = "hands_on_practice"  # 实践练习
    MENTORING = "mentoring"  # 导师指导


@dataclass
class GuidanceContent:
    """指导内容"""
    content_id: str
    title: str
    description: str
    guidance_type: GuidanceType
    target_skill_level: SkillLevel
    
    # 内容详情
    steps: List[str]  # 操作步骤
    tips: List[str]  # 提示和技巧
    warnings: List[str]  # 注意事项
    examples: List[Dict[str, Any]]  # 示例
    
    # 适用范围
    applicable_categories: List[ProblemCategory]
    applicable_root_causes: List[RootCauseType]
    
    # 元数据
    difficulty_level: int  # 1-5
    estimated_time_minutes: int
    prerequisites: List[str]
    related_content: List[str]
    
    # 统计信息
    usage_count: int = 0
    success_rate: float = 0.0
    user_ratings: List[float] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'content_id': self.content_id,
            'title': self.title,
            'description': self.description,
            'guidance_type': self.guidance_type.value,
            'target_skill_level': self.target_skill_level.value,
            'steps': self.steps,
            'tips': self.tips,
            'warnings': self.warnings,
            'examples': self.examples,
            'applicable_categories': [cat.value for cat in self.applicable_categories],
            'applicable_root_causes': [cause.value for cause in self.applicable_root_causes],
            'difficulty_level': self.difficulty_level,
            'estimated_time_minutes': self.estimated_time_minutes,
            'prerequisites': self.prerequisites,
            'related_content': self.related_content,
            'usage_count': self.usage_count,
            'success_rate': self.success_rate,
            'average_rating': sum(self.user_ratings) / len(self.user_ratings) if self.user_ratings else 0.0,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class TrainingResource:
    """培训资源"""
    resource_id: str
    title: str
    description: str
    training_type: TrainingType
    target_skill_level: SkillLevel
    
    # 资源信息
    url: Optional[str] = None
    content: Optional[str] = None
    duration_minutes: int = 0
    
    # 适用范围
    topics: List[str] = field(default_factory=list)
    skills_covered: List[str] = field(default_factory=list)
    applicable_categories: List[ProblemCategory] = field(default_factory=list)
    
    # 质量信息
    difficulty_level: int = 1  # 1-5
    prerequisites: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    
    # 统计信息
    completion_rate: float = 0.0
    effectiveness_score: float = 0.0
    user_feedback: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'resource_id': self.resource_id,
            'title': self.title,
            'description': self.description,
            'training_type': self.training_type.value,
            'target_skill_level': self.target_skill_level.value,
            'url': self.url,
            'duration_minutes': self.duration_minutes,
            'topics': self.topics,
            'skills_covered': self.skills_covered,
            'applicable_categories': [cat.value for cat in self.applicable_categories],
            'difficulty_level': self.difficulty_level,
            'prerequisites': self.prerequisites,
            'learning_objectives': self.learning_objectives,
            'completion_rate': self.completion_rate,
            'effectiveness_score': self.effectiveness_score,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class BestPracticeCase:
    """最佳实践案例"""
    case_id: str
    title: str
    description: str
    
    # 案例详情
    problem_description: str
    solution_approach: str
    implementation_steps: List[str]
    results_achieved: str
    
    # 分类信息
    category: ProblemCategory
    root_causes: List[RootCauseType]
    action_categories: List[ActionCategory]
    
    # 成功指标
    success_metrics: Dict[str, float]
    lessons_learned: List[str]
    key_success_factors: List[str]
    
    # 适用性
    applicable_scenarios: List[str]
    replication_difficulty: int  # 1-5
    
    # 元数据
    organization: str = "internal"
    author: str = "system"
    verified: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'case_id': self.case_id,
            'title': self.title,
            'description': self.description,
            'problem_description': self.problem_description,
            'solution_approach': self.solution_approach,
            'implementation_steps': self.implementation_steps,
            'results_achieved': self.results_achieved,
            'category': self.category.value,
            'root_causes': [cause.value for cause in self.root_causes],
            'action_categories': [cat.value for cat in self.action_categories],
            'success_metrics': self.success_metrics,
            'lessons_learned': self.lessons_learned,
            'key_success_factors': self.key_success_factors,
            'applicable_scenarios': self.applicable_scenarios,
            'replication_difficulty': self.replication_difficulty,
            'organization': self.organization,
            'author': self.author,
            'verified': self.verified,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class UserSkillProfile:
    """用户技能档案"""
    user_id: str
    name: str
    
    # 技能水平
    overall_skill_level: SkillLevel
    category_skills: Dict[ProblemCategory, SkillLevel] = field(default_factory=dict)
    
    # 经验统计
    total_issues_handled: int = 0
    successful_resolutions: int = 0
    average_resolution_time: float = 0.0
    
    # 培训记录
    completed_trainings: List[str] = field(default_factory=list)
    training_hours: float = 0.0
    certifications: List[str] = field(default_factory=list)
    
    # 改进跟踪
    skill_improvement_history: List[Dict[str, Any]] = field(default_factory=list)
    weak_areas: List[str] = field(default_factory=list)
    strength_areas: List[str] = field(default_factory=list)
    
    # 个性化设置
    preferred_learning_style: str = "mixed"
    learning_pace: str = "normal"  # slow, normal, fast
    
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'overall_skill_level': self.overall_skill_level.value,
            'category_skills': {cat.value: skill.value for cat, skill in self.category_skills.items()},
            'total_issues_handled': self.total_issues_handled,
            'successful_resolutions': self.successful_resolutions,
            'success_rate': self.successful_resolutions / max(self.total_issues_handled, 1),
            'average_resolution_time': self.average_resolution_time,
            'completed_trainings': self.completed_trainings,
            'training_hours': self.training_hours,
            'certifications': self.certifications,
            'skill_improvement_history': self.skill_improvement_history,
            'weak_areas': self.weak_areas,
            'strength_areas': self.strength_areas,
            'preferred_learning_style': self.preferred_learning_style,
            'learning_pace': self.learning_pace,
            'last_updated': self.last_updated.isoformat()
        }


class RepairGuidanceSystem:
    """修复指导系统"""
    
    def __init__(self):
        self.guidance_content: Dict[str, GuidanceContent] = {}
        self.training_resources: Dict[str, TrainingResource] = {}
        self.best_practice_cases: Dict[str, BestPracticeCase] = {}
        self.user_profiles: Dict[str, UserSkillProfile] = {}
        
        self.content_counter = 0
        self.resource_counter = 0
        self.case_counter = 0
        
        # 初始化默认内容
        self._initialize_default_content()
    
    def _initialize_default_content(self):
        """初始化默认内容"""
        self._create_default_guidance_content()
        self._create_default_training_resources()
        self._create_default_best_practices()
    
    def _create_default_guidance_content(self):
        """创建默认指导内容"""
        
        # 准确性问题指导
        accuracy_guidance = GuidanceContent(
            content_id="guidance_001",
            title="数据准确性问题修复指导",
            description="针对数据准确性问题的系统性修复指导",
            guidance_type=GuidanceType.STEP_BY_STEP,
            target_skill_level=SkillLevel.INTERMEDIATE,
            steps=[
                "1. 识别不准确的数据记录",
                "2. 分析错误模式和根本原因",
                "3. 制定修复策略",
                "4. 执行数据修正",
                "5. 验证修复结果",
                "6. 建立预防机制"
            ],
            tips=[
                "使用数据质量检查工具自动识别问题",
                "建立数据验证规则",
                "记录修复过程以便后续参考"
            ],
            warnings=[
                "修复前务必备份原始数据",
                "大批量修复前先小范围测试",
                "注意修复可能对下游系统的影响"
            ],
            examples=[
                {
                    "scenario": "日期格式错误",
                    "problem": "日期字段包含无效格式",
                    "solution": "使用正则表达式识别并转换为标准格式"
                }
            ],
            applicable_categories=[ProblemCategory.ACCURACY],
            applicable_root_causes=[RootCauseType.HUMAN_ERROR, RootCauseType.DATA_QUALITY],
            difficulty_level=3,
            estimated_time_minutes=45,
            prerequisites=["数据质量基础知识", "SQL基本操作"],
            related_content=[]  # 添加缺失的参数
        )
        
        self.guidance_content[accuracy_guidance.content_id] = accuracy_guidance
        
        # 一致性问题指导
        consistency_guidance = GuidanceContent(
            content_id="guidance_002",
            title="数据一致性问题修复指导",
            description="解决数据一致性问题的标准流程",
            guidance_type=GuidanceType.TROUBLESHOOTING,
            target_skill_level=SkillLevel.INTERMEDIATE,
            steps=[
                "1. 识别不一致的数据点",
                "2. 确定标准参考值",
                "3. 分析不一致的原因",
                "4. 制定统一标准",
                "5. 批量修正不一致数据",
                "6. 建立一致性检查机制"
            ],
            tips=[
                "建立数据字典和标准",
                "使用自动化工具检查一致性",
                "定期进行一致性审计"
            ],
            warnings=[
                "确保修正标准的正确性",
                "考虑历史数据的兼容性",
                "注意跨系统的一致性要求"
            ],
            examples=[
                {
                    "scenario": "分类标签不一致",
                    "problem": "同一概念使用不同标签",
                    "solution": "建立标准分类体系并批量更新"
                }
            ],
            applicable_categories=[ProblemCategory.CONSISTENCY],
            applicable_root_causes=[RootCauseType.PROCESS_ISSUE, RootCauseType.GUIDELINE_UNCLEAR],
            difficulty_level=4,
            estimated_time_minutes=60,
            prerequisites=["数据管理基础", "业务规则理解"],
            related_content=[]  # 添加缺失的参数
        )
        
        self.guidance_content[consistency_guidance.content_id] = consistency_guidance
    
    def _create_default_training_resources(self):
        """创建默认培训资源"""
        
        # 数据质量基础培训
        quality_basics = TrainingResource(
            resource_id="training_001",
            title="数据质量管理基础",
            description="数据质量管理的基本概念和方法",
            training_type=TrainingType.ONLINE_COURSE,
            target_skill_level=SkillLevel.BEGINNER,
            duration_minutes=120,
            topics=["数据质量维度", "质量评估方法", "质量改进流程"],
            skills_covered=["质量评估", "问题识别", "改进规划"],
            applicable_categories=[
                ProblemCategory.ACCURACY, 
                ProblemCategory.CONSISTENCY, 
                ProblemCategory.COMPLETENESS
            ],
            difficulty_level=2,
            learning_objectives=[
                "理解数据质量的基本概念",
                "掌握质量评估方法",
                "能够制定质量改进计划"
            ]
        )
        
        self.training_resources[quality_basics.resource_id] = quality_basics
        
        # 高级故障排除培训
        troubleshooting_advanced = TrainingResource(
            resource_id="training_002",
            title="高级故障排除技术",
            description="复杂质量问题的诊断和解决技术",
            training_type=TrainingType.WORKSHOP,
            target_skill_level=SkillLevel.ADVANCED,
            duration_minutes=240,
            topics=["根因分析", "系统性思维", "预防性措施"],
            skills_covered=["问题诊断", "根因分析", "解决方案设计"],
            applicable_categories=[
                ProblemCategory.SYSTEM, 
                ProblemCategory.PERFORMANCE
            ],
            difficulty_level=4,
            learning_objectives=[
                "掌握高级诊断技术",
                "能够进行深度根因分析",
                "设计有效的预防措施"
            ]
        )
        
        self.training_resources[troubleshooting_advanced.resource_id] = troubleshooting_advanced
    
    def _create_default_best_practices(self):
        """创建默认最佳实践"""
        
        # 数据验证最佳实践
        validation_practice = BestPracticeCase(
            case_id="practice_001",
            title="多层数据验证机制",
            description="通过多层验证机制显著提高数据质量",
            problem_description="数据输入错误频发，影响下游分析准确性",
            solution_approach="建立输入验证、业务规则验证、交叉验证三层机制",
            implementation_steps=[
                "设计输入格式验证规则",
                "建立业务逻辑验证",
                "实施数据交叉验证",
                "建立异常数据处理流程",
                "定期审查和更新验证规则"
            ],
            results_achieved="数据错误率降低85%，用户满意度提升40%",
            category=ProblemCategory.ACCURACY,
            root_causes=[RootCauseType.HUMAN_ERROR, RootCauseType.PROCESS_ISSUE],
            action_categories=[ActionCategory.PROCESS, ActionCategory.SYSTEM],
            success_metrics={
                "error_reduction": 0.85,
                "satisfaction_improvement": 0.40,
                "processing_time_reduction": 0.25
            },
            lessons_learned=[
                "早期验证比后期修复更有效",
                "用户培训同样重要",
                "验证规则需要定期更新"
            ],
            key_success_factors=[
                "管理层支持",
                "用户积极配合",
                "技术团队专业能力"
            ],
            applicable_scenarios=[
                "数据输入频繁的业务场景",
                "对数据准确性要求高的系统",
                "多用户协作的数据处理环境"
            ],
            replication_difficulty=3
        )
        
        self.best_practice_cases[validation_practice.case_id] = validation_practice
    
    def get_personalized_guidance(self, user_id: str, issue: QualityIssue, 
                                suggestion: RepairSuggestion) -> Dict[str, Any]:
        """获取个性化修复指导"""
        logger.info(f"为用户 {user_id} 生成个性化修复指导")
        
        # 获取用户技能档案
        user_profile = self.user_profiles.get(user_id)
        if not user_profile:
            user_profile = self._create_default_user_profile(user_id)
        
        # 查找相关指导内容
        relevant_guidance = self._find_relevant_guidance(issue, suggestion, user_profile)
        
        # 推荐最佳实践案例
        relevant_cases = self._find_relevant_best_practices(issue, suggestion)
        
        # 推荐培训资源
        training_recommendations = self._recommend_training_resources(user_profile, issue)
        
        # 生成个性化建议
        personalized_tips = self._generate_personalized_tips(user_profile, issue, suggestion)
        
        guidance_result = {
            'user_id': user_id,
            'issue_id': issue.id,
            'suggestion_id': suggestion.suggestion_id,
            'guidance_content': [content.to_dict() for content in relevant_guidance],
            'best_practice_cases': [case.to_dict() for case in relevant_cases],
            'training_recommendations': [resource.to_dict() for resource in training_recommendations],
            'personalized_tips': personalized_tips,
            'user_skill_level': user_profile.overall_skill_level.value,
            'estimated_success_probability': self._estimate_user_success_probability(
                user_profile, issue, suggestion
            ),
            'generated_at': datetime.now().isoformat()
        }
        
        # 更新使用统计
        for content in relevant_guidance:
            content.usage_count += 1
        
        logger.info(f"生成了 {len(relevant_guidance)} 个指导内容和 {len(training_recommendations)} 个培训推荐")
        return guidance_result
    
    def _create_default_user_profile(self, user_id: str) -> UserSkillProfile:
        """创建默认用户档案"""
        profile = UserSkillProfile(
            user_id=user_id,
            name=f"User_{user_id}",
            overall_skill_level=SkillLevel.INTERMEDIATE,
            category_skills={
                category: SkillLevel.INTERMEDIATE 
                for category in ProblemCategory
            }
        )
        
        self.user_profiles[user_id] = profile
        return profile
    
    def _find_relevant_guidance(self, issue: QualityIssue, suggestion: RepairSuggestion,
                              user_profile: UserSkillProfile) -> List[GuidanceContent]:
        """查找相关指导内容"""
        relevant_content = []
        
        for content in self.guidance_content.values():
            # 检查适用性
            if (issue.category in content.applicable_categories and
                self._is_skill_level_appropriate(content.target_skill_level, user_profile)):
                
                relevant_content.append(content)
        
        # 按相关性和用户评分排序
        relevant_content.sort(
            key=lambda c: (
                c.success_rate,
                sum(c.user_ratings) / len(c.user_ratings) if c.user_ratings else 0,
                -c.difficulty_level
            ),
            reverse=True
        )
        
        return relevant_content[:5]  # 返回最相关的5个
    
    def _find_relevant_best_practices(self, issue: QualityIssue, 
                                    suggestion: RepairSuggestion) -> List[BestPracticeCase]:
        """查找相关最佳实践案例"""
        relevant_cases = []
        
        for case in self.best_practice_cases.values():
            # 检查类别匹配
            if (case.category == issue.category and
                suggestion.category in case.action_categories):
                
                relevant_cases.append(case)
        
        # 按成功指标和验证状态排序
        relevant_cases.sort(
            key=lambda c: (
                c.verified,
                sum(c.success_metrics.values()) / len(c.success_metrics) if c.success_metrics else 0,
                -c.replication_difficulty
            ),
            reverse=True
        )
        
        return relevant_cases[:3]  # 返回最相关的3个
    
    def _recommend_training_resources(self, user_profile: UserSkillProfile, 
                                    issue: QualityIssue) -> List[TrainingResource]:
        """推荐培训资源"""
        recommendations = []
        
        # 获取用户在该类别的技能水平
        user_skill_in_category = user_profile.category_skills.get(
            issue.category, SkillLevel.INTERMEDIATE
        )
        
        for resource in self.training_resources.values():
            # 检查适用性和技能水平匹配
            if (issue.category in resource.applicable_categories and
                self._is_training_appropriate(resource, user_skill_in_category, user_profile)):
                
                recommendations.append(resource)
        
        # 按效果和完成率排序
        recommendations.sort(
            key=lambda r: (r.effectiveness_score, r.completion_rate),
            reverse=True
        )
        
        return recommendations[:4]  # 返回最相关的4个
    
    def _is_skill_level_appropriate(self, target_level: SkillLevel, 
                                  user_profile: UserSkillProfile) -> bool:
        """判断技能水平是否合适"""
        skill_order = [SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED, SkillLevel.EXPERT]
        
        user_index = skill_order.index(user_profile.overall_skill_level)
        target_index = skill_order.index(target_level)
        
        # 允许用户学习同级或稍高一级的内容
        return target_index <= user_index + 1
    
    def _is_training_appropriate(self, resource: TrainingResource, 
                               user_skill: SkillLevel, user_profile: UserSkillProfile) -> bool:
        """判断培训是否合适"""
        # 检查技能水平
        if not self._is_skill_level_appropriate(resource.target_skill_level, user_profile):
            return False
        
        # 检查是否已完成
        if resource.resource_id in user_profile.completed_trainings:
            return False
        
        # 检查前置条件
        for prereq in resource.prerequisites:
            if prereq not in user_profile.completed_trainings and prereq not in user_profile.certifications:
                return False
        
        return True
    
    def _generate_personalized_tips(self, user_profile: UserSkillProfile, 
                                  issue: QualityIssue, suggestion: RepairSuggestion) -> List[str]:
        """生成个性化提示"""
        tips = []
        
        # 基于用户技能水平的提示
        if user_profile.overall_skill_level == SkillLevel.BEGINNER:
            tips.extend([
                "建议先阅读相关基础文档",
                "可以寻求有经验同事的帮助",
                "每个步骤完成后进行验证"
            ])
        elif user_profile.overall_skill_level == SkillLevel.EXPERT:
            tips.extend([
                "可以考虑创新性解决方案",
                "记录解决过程以供他人学习",
                "评估是否可以自动化处理"
            ])
        
        # 基于用户弱项的提示
        for weak_area in user_profile.weak_areas:
            if weak_area in issue.category.value:
                tips.append(f"注意 {weak_area} 相关的细节，这是您需要加强的领域")
        
        # 基于历史成功率的提示
        success_rate = user_profile.successful_resolutions / max(user_profile.total_issues_handled, 1)
        if success_rate < 0.7:
            tips.append("建议仔细按照指导步骤执行，不要跳过验证环节")
        
        # 基于学习偏好的提示
        if user_profile.preferred_learning_style == "visual":
            tips.append("查看相关的图表和示例会对您有帮助")
        elif user_profile.preferred_learning_style == "hands_on":
            tips.append("建议在测试环境中先练习相关操作")
        
        return tips
    
    def _estimate_user_success_probability(self, user_profile: UserSkillProfile,
                                         issue: QualityIssue, suggestion: RepairSuggestion) -> float:
        """估算用户成功概率"""
        base_probability = suggestion.success_probability
        
        # 基于用户技能水平调整
        skill_adjustments = {
            SkillLevel.BEGINNER: -0.2,
            SkillLevel.INTERMEDIATE: 0.0,
            SkillLevel.ADVANCED: 0.1,
            SkillLevel.EXPERT: 0.15
        }
        
        skill_adjustment = skill_adjustments.get(user_profile.overall_skill_level, 0)
        
        # 基于用户历史成功率调整
        user_success_rate = user_profile.successful_resolutions / max(user_profile.total_issues_handled, 1)
        history_adjustment = (user_success_rate - 0.7) * 0.2  # 以70%为基准
        
        # 基于类别专长调整
        category_skill = user_profile.category_skills.get(issue.category, SkillLevel.INTERMEDIATE)
        category_adjustment = skill_adjustments.get(category_skill, 0) * 0.5
        
        # 综合调整
        adjusted_probability = base_probability + skill_adjustment + history_adjustment + category_adjustment
        
        return max(0.1, min(0.95, adjusted_probability))
    
    def add_guidance_content(self, content: GuidanceContent):
        """添加指导内容"""
        self.guidance_content[content.content_id] = content
        logger.info(f"添加指导内容: {content.title}")
    
    def add_training_resource(self, resource: TrainingResource):
        """添加培训资源"""
        self.training_resources[resource.resource_id] = resource
        logger.info(f"添加培训资源: {resource.title}")
    
    def add_best_practice_case(self, case: BestPracticeCase):
        """添加最佳实践案例"""
        self.best_practice_cases[case.case_id] = case
        logger.info(f"添加最佳实践案例: {case.title}")
    
    def update_user_profile(self, user_id: str, **updates):
        """更新用户档案"""
        if user_id in self.user_profiles:
            profile = self.user_profiles[user_id]
            
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            profile.last_updated = datetime.now()
            logger.info(f"更新用户 {user_id} 的档案")
    
    def record_training_completion(self, user_id: str, resource_id: str, 
                                 success: bool, rating: Optional[float] = None):
        """记录培训完成情况"""
        if user_id not in self.user_profiles:
            self._create_default_user_profile(user_id)
        
        profile = self.user_profiles[user_id]
        
        if success and resource_id not in profile.completed_trainings:
            profile.completed_trainings.append(resource_id)
            
            # 更新培训时长
            if resource_id in self.training_resources:
                resource = self.training_resources[resource_id]
                profile.training_hours += resource.duration_minutes / 60
        
        # 更新资源统计
        if resource_id in self.training_resources:
            resource = self.training_resources[resource_id]
            # 这里可以更新完成率和效果评分
            if rating:
                resource.user_feedback.append(f"评分: {rating}")
        
        logger.info(f"记录用户 {user_id} 完成培训 {resource_id}，成功: {success}")
    
    def record_guidance_feedback(self, content_id: str, success: bool, rating: float):
        """记录指导反馈"""
        if content_id in self.guidance_content:
            content = self.guidance_content[content_id]
            
            # 更新成功率
            total_usage = content.usage_count
            if total_usage > 0:
                current_success_count = content.success_rate * (total_usage - 1)
                new_success_count = current_success_count + (1 if success else 0)
                content.success_rate = new_success_count / total_usage
            
            # 添加评分
            content.user_ratings.append(rating)
            content.updated_at = datetime.now()
            
            logger.info(f"记录指导内容 {content_id} 的反馈，成功: {success}，评分: {rating}")
    
    def track_skill_improvement(self, user_id: str, category: ProblemCategory, 
                              improvement_data: Dict[str, Any]):
        """跟踪技能提升"""
        if user_id not in self.user_profiles:
            self._create_default_user_profile(user_id)
        
        profile = self.user_profiles[user_id]
        
        # 添加改进记录
        improvement_record = {
            'category': category.value,
            'timestamp': datetime.now().isoformat(),
            'data': improvement_data
        }
        
        profile.skill_improvement_history.append(improvement_record)
        
        # 更新技能水平（简化逻辑）
        if improvement_data.get('success', False):
            current_skill = profile.category_skills.get(category, SkillLevel.BEGINNER)
            # 这里可以实现更复杂的技能提升逻辑
        
        profile.last_updated = datetime.now()
        logger.info(f"跟踪用户 {user_id} 在 {category.value} 的技能提升")
    
    def get_user_learning_path(self, user_id: str, target_category: ProblemCategory) -> Dict[str, Any]:
        """获取用户学习路径"""
        if user_id not in self.user_profiles:
            profile = self._create_default_user_profile(user_id)
        else:
            profile = self.user_profiles[user_id]
        
        current_skill = profile.category_skills.get(target_category, SkillLevel.BEGINNER)
        
        # 推荐学习路径
        learning_path = []
        
        # 基础培训
        if current_skill == SkillLevel.BEGINNER:
            basic_resources = [
                r for r in self.training_resources.values()
                if (target_category in r.applicable_categories and
                    r.target_skill_level == SkillLevel.BEGINNER)
            ]
            learning_path.extend(basic_resources)
        
        # 进阶培训
        if current_skill in [SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE]:
            intermediate_resources = [
                r for r in self.training_resources.values()
                if (target_category in r.applicable_categories and
                    r.target_skill_level == SkillLevel.INTERMEDIATE)
            ]
            learning_path.extend(intermediate_resources)
        
        # 高级培训
        advanced_resources = [
            r for r in self.training_resources.values()
            if (target_category in r.applicable_categories and
                r.target_skill_level == SkillLevel.ADVANCED)
        ]
        learning_path.extend(advanced_resources)
        
        return {
            'user_id': user_id,
            'target_category': target_category.value,
            'current_skill_level': current_skill.value,
            'learning_path': [resource.to_dict() for resource in learning_path],
            'estimated_duration_hours': sum(r.duration_minutes for r in learning_path) / 60,
            'generated_at': datetime.now().isoformat()
        }
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            'guidance_content_count': len(self.guidance_content),
            'training_resources_count': len(self.training_resources),
            'best_practice_cases_count': len(self.best_practice_cases),
            'user_profiles_count': len(self.user_profiles),
            'total_guidance_usage': sum(c.usage_count for c in self.guidance_content.values()),
            'average_content_rating': np.mean([
                np.mean(c.user_ratings) for c in self.guidance_content.values() 
                if c.user_ratings
            ]) if any(c.user_ratings for c in self.guidance_content.values()) else 0,
            'total_training_hours': sum(
                p.training_hours for p in self.user_profiles.values()
            )
        }