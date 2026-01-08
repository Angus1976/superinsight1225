"""
质量问题根因分析器

实现质量问题的自动根因分析，包括问题模式识别、分类和修复建议生成。
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import numpy as np
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)


class ProblemCategory(str, Enum):
    """问题分类"""
    ACCURACY = "accuracy"  # 准确性问题
    CONSISTENCY = "consistency"  # 一致性问题
    COMPLETENESS = "completeness"  # 完整性问题
    FORMAT = "format"  # 格式问题
    GUIDELINE = "guideline"  # 规范问题
    PERFORMANCE = "performance"  # 性能问题
    SYSTEM = "system"  # 系统问题


class RootCauseType(str, Enum):
    """根因类型"""
    HUMAN_ERROR = "human_error"  # 人为错误
    PROCESS_ISSUE = "process_issue"  # 流程问题
    TOOL_LIMITATION = "tool_limitation"  # 工具限制
    TRAINING_GAP = "training_gap"  # 培训不足
    GUIDELINE_UNCLEAR = "guideline_unclear"  # 规范不清
    SYSTEM_BUG = "system_bug"  # 系统缺陷
    DATA_QUALITY = "data_quality"  # 数据质量
    RESOURCE_CONSTRAINT = "resource_constraint"  # 资源约束


class SeverityLevel(str, Enum):
    """严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QualityIssue:
    """质量问题数据结构"""
    id: str
    category: ProblemCategory
    description: str
    affected_data: List[str]
    reporter: str
    created_at: datetime
    severity: SeverityLevel
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RootCauseAnalysis:
    """根因分析结果"""
    issue_id: str
    primary_cause: RootCauseType
    contributing_factors: List[RootCauseType]
    confidence_score: float  # 0-1
    evidence: List[str]
    impact_assessment: Dict[str, Any]
    recommendations: List[str]
    analyzed_at: datetime
    analysis_method: str


@dataclass
class ProblemPattern:
    """问题模式"""
    pattern_id: str
    name: str
    description: str
    category: ProblemCategory
    root_causes: List[RootCauseType]
    frequency: int
    severity_distribution: Dict[SeverityLevel, int]
    typical_context: Dict[str, Any]
    prevention_measures: List[str]


class RootCauseAnalyzer:
    """根因分析器"""
    
    def __init__(self):
        self.analysis_history: List[RootCauseAnalysis] = []
        self.problem_patterns: Dict[str, ProblemPattern] = {}
        self.cause_frequency: Dict[RootCauseType, int] = defaultdict(int)
        self.category_cause_mapping: Dict[ProblemCategory, Dict[RootCauseType, float]] = defaultdict(lambda: defaultdict(float))
        
        # 初始化分析规则
        self._initialize_analysis_rules()
    
    def _initialize_analysis_rules(self):
        """初始化分析规则"""
        # 问题类别与根因的关联权重
        self.category_cause_mapping = {
            ProblemCategory.ACCURACY: {
                RootCauseType.HUMAN_ERROR: 0.4,
                RootCauseType.TRAINING_GAP: 0.3,
                RootCauseType.GUIDELINE_UNCLEAR: 0.2,
                RootCauseType.TOOL_LIMITATION: 0.1
            },
            ProblemCategory.CONSISTENCY: {
                RootCauseType.PROCESS_ISSUE: 0.4,
                RootCauseType.GUIDELINE_UNCLEAR: 0.3,
                RootCauseType.TRAINING_GAP: 0.2,
                RootCauseType.HUMAN_ERROR: 0.1
            },
            ProblemCategory.COMPLETENESS: {
                RootCauseType.PROCESS_ISSUE: 0.3,
                RootCauseType.HUMAN_ERROR: 0.3,
                RootCauseType.RESOURCE_CONSTRAINT: 0.2,
                RootCauseType.TOOL_LIMITATION: 0.2
            },
            ProblemCategory.FORMAT: {
                RootCauseType.TOOL_LIMITATION: 0.4,
                RootCauseType.SYSTEM_BUG: 0.3,
                RootCauseType.GUIDELINE_UNCLEAR: 0.2,
                RootCauseType.HUMAN_ERROR: 0.1
            },
            ProblemCategory.GUIDELINE: {
                RootCauseType.GUIDELINE_UNCLEAR: 0.5,
                RootCauseType.TRAINING_GAP: 0.3,
                RootCauseType.PROCESS_ISSUE: 0.2
            },
            ProblemCategory.PERFORMANCE: {
                RootCauseType.RESOURCE_CONSTRAINT: 0.4,
                RootCauseType.SYSTEM_BUG: 0.3,
                RootCauseType.PROCESS_ISSUE: 0.2,
                RootCauseType.TOOL_LIMITATION: 0.1
            },
            ProblemCategory.SYSTEM: {
                RootCauseType.SYSTEM_BUG: 0.5,
                RootCauseType.TOOL_LIMITATION: 0.3,
                RootCauseType.DATA_QUALITY: 0.2
            }
        }
    
    def analyze_root_cause(self, issue: QualityIssue) -> RootCauseAnalysis:
        """分析质量问题的根因"""
        logger.info(f"开始分析问题 {issue.id} 的根因")
        
        # 1. 基于规则的初步分析
        rule_based_causes = self._rule_based_analysis(issue)
        
        # 2. 基于历史模式的分析
        pattern_based_causes = self._pattern_based_analysis(issue)
        
        # 3. 基于上下文的分析
        context_based_causes = self._context_based_analysis(issue)
        
        # 4. 综合分析结果
        final_analysis = self._synthesize_analysis(
            issue, rule_based_causes, pattern_based_causes, context_based_causes
        )
        
        # 5. 生成修复建议
        recommendations = self._generate_recommendations(issue, final_analysis)
        final_analysis.recommendations = recommendations
        
        # 6. 保存分析结果
        self.analysis_history.append(final_analysis)
        self._update_statistics(final_analysis)
        
        logger.info(f"完成问题 {issue.id} 的根因分析，主要原因: {final_analysis.primary_cause}")
        return final_analysis
    
    def _rule_based_analysis(self, issue: QualityIssue) -> Dict[RootCauseType, float]:
        """基于规则的根因分析"""
        scores = defaultdict(float)
        
        # 基于问题类别的基础权重
        category_weights = self.category_cause_mapping.get(issue.category, {})
        for cause, weight in category_weights.items():
            scores[cause] += weight * 0.5  # 基础权重占50%
        
        # 基于严重程度的调整
        severity_multiplier = {
            SeverityLevel.LOW: 0.8,
            SeverityLevel.MEDIUM: 1.0,
            SeverityLevel.HIGH: 1.2,
            SeverityLevel.CRITICAL: 1.5
        }
        multiplier = severity_multiplier.get(issue.severity, 1.0)
        
        for cause in scores:
            scores[cause] *= multiplier
        
        # 基于描述关键词的分析
        keyword_analysis = self._analyze_description_keywords(issue.description)
        for cause, weight in keyword_analysis.items():
            scores[cause] += weight * 0.3  # 关键词分析占30%
        
        return dict(scores)
    
    def _pattern_based_analysis(self, issue: QualityIssue) -> Dict[RootCauseType, float]:
        """基于历史模式的根因分析"""
        scores = defaultdict(float)
        
        # 查找相似的历史问题
        similar_issues = self._find_similar_issues(issue)
        
        if similar_issues:
            # 基于相似问题的根因统计
            cause_counts = defaultdict(int)
            total_similar = len(similar_issues)
            
            for similar_analysis in similar_issues:
                cause_counts[similar_analysis.primary_cause] += 2  # 主要原因权重更高
                for contributing_cause in similar_analysis.contributing_factors:
                    cause_counts[contributing_cause] += 1
            
            # 转换为概率分数
            for cause, count in cause_counts.items():
                scores[cause] = count / (total_similar * 3)  # 归一化
        
        return dict(scores)
    
    def _context_based_analysis(self, issue: QualityIssue) -> Dict[RootCauseType, float]:
        """基于上下文的根因分析"""
        scores = defaultdict(float)
        
        context = issue.context
        metadata = issue.metadata
        
        # 分析时间模式
        if 'timestamp' in context:
            time_analysis = self._analyze_time_patterns(context['timestamp'])
            scores.update(time_analysis)
        
        # 分析用户模式
        if 'user_id' in context:
            user_analysis = self._analyze_user_patterns(context['user_id'])
            scores.update(user_analysis)
        
        # 分析数据模式
        if 'data_source' in metadata:
            data_analysis = self._analyze_data_patterns(metadata['data_source'])
            scores.update(data_analysis)
        
        # 分析工具使用模式
        if 'tool_version' in metadata:
            tool_analysis = self._analyze_tool_patterns(metadata['tool_version'])
            scores.update(tool_analysis)
        
        return dict(scores)
    
    def _analyze_description_keywords(self, description: str) -> Dict[RootCauseType, float]:
        """分析描述中的关键词"""
        scores = defaultdict(float)
        
        # 关键词映射
        keyword_mappings = {
            RootCauseType.HUMAN_ERROR: ['错误', '失误', '疏忽', '遗漏', '误操作'],
            RootCauseType.TRAINING_GAP: ['不熟悉', '不了解', '培训', '学习', '经验不足'],
            RootCauseType.GUIDELINE_UNCLEAR: ['不清楚', '模糊', '规范', '标准', '指导'],
            RootCauseType.TOOL_LIMITATION: ['工具', '功能', '限制', '不支持', '缺少'],
            RootCauseType.SYSTEM_BUG: ['系统', '错误', '故障', '异常', 'bug'],
            RootCauseType.PROCESS_ISSUE: ['流程', '步骤', '顺序', '程序', '方法'],
            RootCauseType.DATA_QUALITY: ['数据', '质量', '格式', '完整性', '准确性'],
            RootCauseType.RESOURCE_CONSTRAINT: ['时间', '资源', '人力', '紧急', '压力']
        }
        
        description_lower = description.lower()
        
        for cause, keywords in keyword_mappings.items():
            keyword_count = sum(1 for keyword in keywords if keyword in description_lower)
            if keyword_count > 0:
                scores[cause] = min(keyword_count * 0.2, 1.0)  # 最大1.0
        
        return dict(scores)
    
    def _find_similar_issues(self, issue: QualityIssue, limit: int = 10) -> List[RootCauseAnalysis]:
        """查找相似的历史问题"""
        similar_analyses = []
        
        for analysis in self.analysis_history:
            # 简单的相似度计算（可以改进为更复杂的算法）
            similarity_score = 0
            
            # 基于问题类别的相似度
            if analysis.issue_id != issue.id:  # 排除自身
                # 这里需要获取历史问题的信息，简化处理
                similarity_score += 0.5  # 基础相似度
                
                if similarity_score > 0.3:  # 相似度阈值
                    similar_analyses.append(analysis)
        
        return similar_analyses[:limit]
    
    def _analyze_time_patterns(self, timestamp: datetime) -> Dict[RootCauseType, float]:
        """分析时间模式"""
        scores = defaultdict(float)
        
        # 工作时间外的问题可能是资源约束
        hour = timestamp.hour
        if hour < 9 or hour > 18:
            scores[RootCauseType.RESOURCE_CONSTRAINT] += 0.2
        
        # 周末的问题可能是紧急处理导致的人为错误
        if timestamp.weekday() >= 5:  # 周六、周日
            scores[RootCauseType.HUMAN_ERROR] += 0.1
            scores[RootCauseType.RESOURCE_CONSTRAINT] += 0.1
        
        return dict(scores)
    
    def _analyze_user_patterns(self, user_id: str) -> Dict[RootCauseType, float]:
        """分析用户模式"""
        scores = defaultdict(float)
        
        # 分析该用户的历史问题模式
        user_issues = [analysis for analysis in self.analysis_history 
                      if analysis.issue_id.startswith(user_id)]  # 简化处理
        
        if user_issues:
            # 统计该用户最常见的根因
            user_causes = [analysis.primary_cause for analysis in user_issues]
            cause_freq = Counter(user_causes)
            
            total_issues = len(user_issues)
            for cause, count in cause_freq.items():
                scores[cause] += (count / total_issues) * 0.3
        
        return dict(scores)
    
    def _analyze_data_patterns(self, data_source: str) -> Dict[RootCauseType, float]:
        """分析数据模式"""
        scores = defaultdict(float)
        
        # 基于数据源的问题模式
        if 'external' in data_source.lower():
            scores[RootCauseType.DATA_QUALITY] += 0.2
        
        if 'legacy' in data_source.lower():
            scores[RootCauseType.SYSTEM_BUG] += 0.1
            scores[RootCauseType.TOOL_LIMITATION] += 0.1
        
        return dict(scores)
    
    def _analyze_tool_patterns(self, tool_version: str) -> Dict[RootCauseType, float]:
        """分析工具模式"""
        scores = defaultdict(float)
        
        # 基于工具版本的问题模式
        if 'beta' in tool_version.lower() or 'alpha' in tool_version.lower():
            scores[RootCauseType.TOOL_LIMITATION] += 0.3
            scores[RootCauseType.SYSTEM_BUG] += 0.2
        
        return dict(scores)
    
    def _synthesize_analysis(self, issue: QualityIssue, 
                           rule_scores: Dict[RootCauseType, float],
                           pattern_scores: Dict[RootCauseType, float],
                           context_scores: Dict[RootCauseType, float]) -> RootCauseAnalysis:
        """综合分析结果"""
        
        # 合并所有分数
        final_scores = defaultdict(float)
        
        # 权重分配：规则40%，模式30%，上下文30%
        for cause, score in rule_scores.items():
            final_scores[cause] += score * 0.4
        
        for cause, score in pattern_scores.items():
            final_scores[cause] += score * 0.3
        
        for cause, score in context_scores.items():
            final_scores[cause] += score * 0.3
        
        # 排序并选择主要原因和贡献因素
        sorted_causes = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_causes:
            # 默认分析
            primary_cause = RootCauseType.HUMAN_ERROR
            contributing_factors = []
            confidence_score = 0.3
        else:
            primary_cause = sorted_causes[0][0]
            confidence_score = min(sorted_causes[0][1], 1.0)
            
            # 选择贡献因素（分数大于0.1的其他原因）
            contributing_factors = [cause for cause, score in sorted_causes[1:] 
                                  if score > 0.1][:3]  # 最多3个贡献因素
        
        # 生成证据
        evidence = self._generate_evidence(issue, primary_cause, contributing_factors)
        
        # 影响评估
        impact_assessment = self._assess_impact(issue, primary_cause)
        
        return RootCauseAnalysis(
            issue_id=issue.id,
            primary_cause=primary_cause,
            contributing_factors=contributing_factors,
            confidence_score=confidence_score,
            evidence=evidence,
            impact_assessment=impact_assessment,
            recommendations=[],  # 将在后续步骤中生成
            analyzed_at=datetime.now(),
            analysis_method="multi_factor_synthesis"
        )
    
    def _generate_evidence(self, issue: QualityIssue, primary_cause: RootCauseType, 
                          contributing_factors: List[RootCauseType]) -> List[str]:
        """生成证据"""
        evidence = []
        
        # 基于主要原因生成证据
        evidence_templates = {
            RootCauseType.HUMAN_ERROR: [
                f"问题描述中包含人为操作相关关键词",
                f"问题发生在 {issue.created_at.strftime('%H:%M')}，可能存在操作疏忽"
            ],
            RootCauseType.TRAINING_GAP: [
                f"问题类型为 {issue.category.value}，常见于培训不足场景",
                f"报告人员可能需要相关技能培训"
            ],
            RootCauseType.SYSTEM_BUG: [
                f"问题具有系统性特征",
                f"影响数据范围: {len(issue.affected_data)} 条记录"
            ],
            RootCauseType.PROCESS_ISSUE: [
                f"问题模式表明流程存在缺陷",
                f"需要检查相关操作流程"
            ]
        }
        
        if primary_cause in evidence_templates:
            evidence.extend(evidence_templates[primary_cause])
        
        # 基于贡献因素添加证据
        for factor in contributing_factors:
            if factor in evidence_templates:
                evidence.append(f"贡献因素: {evidence_templates[factor][0]}")
        
        return evidence
    
    def _assess_impact(self, issue: QualityIssue, primary_cause: RootCauseType) -> Dict[str, Any]:
        """评估影响"""
        impact = {
            'affected_records': len(issue.affected_data),
            'severity_level': issue.severity.value,
            'business_impact': self._calculate_business_impact(issue),
            'recurrence_risk': self._calculate_recurrence_risk(primary_cause),
            'fix_complexity': self._estimate_fix_complexity(primary_cause)
        }
        
        return impact
    
    def _calculate_business_impact(self, issue: QualityIssue) -> str:
        """计算业务影响"""
        severity_impact = {
            SeverityLevel.LOW: "minimal",
            SeverityLevel.MEDIUM: "moderate", 
            SeverityLevel.HIGH: "significant",
            SeverityLevel.CRITICAL: "severe"
        }
        
        return severity_impact.get(issue.severity, "unknown")
    
    def _calculate_recurrence_risk(self, primary_cause: RootCauseType) -> str:
        """计算复发风险"""
        risk_levels = {
            RootCauseType.HUMAN_ERROR: "high",
            RootCauseType.TRAINING_GAP: "medium",
            RootCauseType.SYSTEM_BUG: "low",
            RootCauseType.PROCESS_ISSUE: "medium",
            RootCauseType.GUIDELINE_UNCLEAR: "high",
            RootCauseType.TOOL_LIMITATION: "low",
            RootCauseType.DATA_QUALITY: "medium",
            RootCauseType.RESOURCE_CONSTRAINT: "high"
        }
        
        return risk_levels.get(primary_cause, "medium")
    
    def _estimate_fix_complexity(self, primary_cause: RootCauseType) -> str:
        """估算修复复杂度"""
        complexity_levels = {
            RootCauseType.HUMAN_ERROR: "low",
            RootCauseType.TRAINING_GAP: "medium",
            RootCauseType.SYSTEM_BUG: "high",
            RootCauseType.PROCESS_ISSUE: "medium",
            RootCauseType.GUIDELINE_UNCLEAR: "low",
            RootCauseType.TOOL_LIMITATION: "high",
            RootCauseType.DATA_QUALITY: "medium",
            RootCauseType.RESOURCE_CONSTRAINT: "medium"
        }
        
        return complexity_levels.get(primary_cause, "medium")
    
    def _generate_recommendations(self, issue: QualityIssue, analysis: RootCauseAnalysis) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        # 基于主要原因的建议
        primary_recommendations = {
            RootCauseType.HUMAN_ERROR: [
                "加强操作规范培训",
                "实施双重检查机制",
                "优化操作界面设计"
            ],
            RootCauseType.TRAINING_GAP: [
                "制定针对性培训计划",
                "提供相关技能认证",
                "建立导师制度"
            ],
            RootCauseType.SYSTEM_BUG: [
                "提交系统缺陷报告",
                "实施临时解决方案",
                "升级系统版本"
            ],
            RootCauseType.PROCESS_ISSUE: [
                "重新设计操作流程",
                "增加流程检查点",
                "自动化关键步骤"
            ],
            RootCauseType.GUIDELINE_UNCLEAR: [
                "完善操作指南",
                "提供示例和模板",
                "建立FAQ知识库"
            ],
            RootCauseType.TOOL_LIMITATION: [
                "评估工具升级需求",
                "寻找替代解决方案",
                "开发定制功能"
            ],
            RootCauseType.DATA_QUALITY: [
                "实施数据质量检查",
                "建立数据清洗流程",
                "加强数据源管理"
            ],
            RootCauseType.RESOURCE_CONSTRAINT: [
                "合理分配工作负载",
                "增加人力资源",
                "优化工作优先级"
            ]
        }
        
        if analysis.primary_cause in primary_recommendations:
            recommendations.extend(primary_recommendations[analysis.primary_cause])
        
        # 基于严重程度的紧急建议
        if issue.severity == SeverityLevel.CRITICAL:
            recommendations.insert(0, "立即启动应急响应流程")
            recommendations.insert(1, "通知相关负责人和管理层")
        
        # 基于影响范围的建议
        if len(issue.affected_data) > 100:
            recommendations.append("实施批量数据修复")
            recommendations.append("建立数据恢复检查点")
        
        return recommendations
    
    def _update_statistics(self, analysis: RootCauseAnalysis):
        """更新统计信息"""
        self.cause_frequency[analysis.primary_cause] += 1
        for factor in analysis.contributing_factors:
            self.cause_frequency[factor] += 1
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        total_analyses = len(self.analysis_history)
        
        if total_analyses == 0:
            return {"message": "暂无分析数据"}
        
        # 根因频率统计
        cause_stats = dict(self.cause_frequency)
        
        # 置信度统计
        confidence_scores = [analysis.confidence_score for analysis in self.analysis_history]
        avg_confidence = np.mean(confidence_scores)
        
        # 最近分析趋势
        recent_analyses = self.analysis_history[-10:] if len(self.analysis_history) >= 10 else self.analysis_history
        recent_causes = [analysis.primary_cause for analysis in recent_analyses]
        recent_cause_freq = Counter(recent_causes)
        
        return {
            "total_analyses": total_analyses,
            "average_confidence": avg_confidence,
            "cause_frequency": cause_stats,
            "recent_trends": dict(recent_cause_freq),
            "analysis_period": {
                "start": self.analysis_history[0].analyzed_at.isoformat() if self.analysis_history else None,
                "end": self.analysis_history[-1].analyzed_at.isoformat() if self.analysis_history else None
            }
        }