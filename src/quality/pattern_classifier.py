"""
问题模式识别和分类器

实现质量问题的模式识别、分类和智能归类功能。
"""

from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import numpy as np
from collections import defaultdict, Counter
# Removed sklearn dependencies for compatibility
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.cluster import KMeans, DBSCAN
# from sklearn.metrics.pairwise import cosine_similarity
import logging

from .root_cause_analyzer import QualityIssue, ProblemCategory, RootCauseType, SeverityLevel

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """模式类型"""
    RECURRING = "recurring"  # 重复模式
    SEASONAL = "seasonal"  # 季节性模式
    ESCALATING = "escalating"  # 升级模式
    CLUSTERED = "clustered"  # 聚集模式
    ANOMALY = "anomaly"  # 异常模式


class PatternStatus(str, Enum):
    """模式状态"""
    ACTIVE = "active"  # 活跃
    DORMANT = "dormant"  # 休眠
    RESOLVED = "resolved"  # 已解决
    MONITORING = "monitoring"  # 监控中


@dataclass
class PatternFeature:
    """模式特征"""
    name: str
    value: Any
    weight: float
    description: str


@dataclass
class QualityPattern:
    """质量问题模式"""
    pattern_id: str
    name: str
    pattern_type: PatternType
    category: ProblemCategory
    description: str
    features: List[PatternFeature]
    
    # 统计信息
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime
    affected_users: Set[str] = field(default_factory=set)
    affected_data_types: Set[str] = field(default_factory=set)
    
    # 模式特征
    frequency_pattern: Dict[str, int] = field(default_factory=dict)  # 时间频率
    severity_distribution: Dict[SeverityLevel, int] = field(default_factory=dict)
    root_cause_distribution: Dict[RootCauseType, int] = field(default_factory=dict)
    
    # 状态和预测
    status: PatternStatus = PatternStatus.ACTIVE
    confidence_score: float = 0.0
    next_occurrence_prediction: Optional[datetime] = None
    
    # 关联信息
    related_patterns: List[str] = field(default_factory=list)
    prevention_measures: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'pattern_id': self.pattern_id,
            'name': self.name,
            'pattern_type': self.pattern_type.value,
            'category': self.category.value,
            'description': self.description,
            'features': [
                {
                    'name': f.name,
                    'value': f.value,
                    'weight': f.weight,
                    'description': f.description
                } for f in self.features
            ],
            'occurrence_count': self.occurrence_count,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'affected_users': list(self.affected_users),
            'affected_data_types': list(self.affected_data_types),
            'frequency_pattern': self.frequency_pattern,
            'severity_distribution': {k.value: v for k, v in self.severity_distribution.items()},
            'root_cause_distribution': {k.value: v for k, v in self.root_cause_distribution.items()},
            'status': self.status.value,
            'confidence_score': self.confidence_score,
            'next_occurrence_prediction': self.next_occurrence_prediction.isoformat() if self.next_occurrence_prediction else None,
            'related_patterns': self.related_patterns,
            'prevention_measures': self.prevention_measures
        }


class PatternClassifier:
    """问题模式分类器"""
    
    def __init__(self):
        self.patterns: Dict[str, QualityPattern] = {}
        self.issue_history: List[QualityIssue] = []
        # Removed sklearn dependencies
        # self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.pattern_counter = 0
        
        # 分类参数
        self.similarity_threshold = 0.7
        self.min_pattern_occurrences = 3
        self.time_window_days = 30
        
    def add_issue(self, issue: QualityIssue):
        """添加新问题到历史记录"""
        self.issue_history.append(issue)
        logger.info(f"添加问题 {issue.id} 到历史记录")
        
        # 触发模式识别
        self._update_patterns(issue)
    
    def classify_issue(self, issue: QualityIssue) -> Dict[str, Any]:
        """对问题进行分类"""
        logger.info(f"开始分类问题 {issue.id}")
        
        # 1. 特征提取
        features = self._extract_features(issue)
        
        # 2. 查找匹配的模式
        matching_patterns = self._find_matching_patterns(issue, features)
        
        # 3. 计算相似度分数
        similarity_scores = self._calculate_similarity_scores(issue, matching_patterns)
        
        # 4. 生成分类结果
        classification_result = {
            'issue_id': issue.id,
            'primary_category': issue.category.value,
            'extracted_features': [
                {
                    'name': f.name,
                    'value': f.value,
                    'weight': f.weight
                } for f in features
            ],
            'matching_patterns': [
                {
                    'pattern_id': pattern_id,
                    'pattern_name': self.patterns[pattern_id].name,
                    'similarity_score': score,
                    'confidence': self.patterns[pattern_id].confidence_score
                } for pattern_id, score in similarity_scores.items()
            ],
            'classification_confidence': self._calculate_classification_confidence(similarity_scores),
            'recommended_actions': self._generate_classification_recommendations(issue, matching_patterns),
            'classified_at': datetime.now()
        }
        
        logger.info(f"完成问题 {issue.id} 的分类，匹配到 {len(matching_patterns)} 个模式")
        return classification_result
    
    def _extract_features(self, issue: QualityIssue) -> List[PatternFeature]:
        """提取问题特征"""
        features = []
        
        # 基本特征
        features.append(PatternFeature(
            name="category",
            value=issue.category.value,
            weight=1.0,
            description="问题类别"
        ))
        
        features.append(PatternFeature(
            name="severity",
            value=issue.severity.value,
            weight=0.8,
            description="严重程度"
        ))
        
        # 时间特征
        hour = issue.created_at.hour
        features.append(PatternFeature(
            name="hour_of_day",
            value=hour,
            weight=0.3,
            description="发生时间（小时）"
        ))
        
        weekday = issue.created_at.weekday()
        features.append(PatternFeature(
            name="day_of_week",
            value=weekday,
            weight=0.3,
            description="发生时间（星期）"
        ))
        
        # 数据特征
        features.append(PatternFeature(
            name="affected_data_count",
            value=len(issue.affected_data),
            weight=0.6,
            description="影响数据量"
        ))
        
        # 文本特征
        description_length = len(issue.description)
        features.append(PatternFeature(
            name="description_length",
            value=description_length,
            weight=0.2,
            description="描述长度"
        ))
        
        # 关键词特征
        keywords = self._extract_keywords(issue.description)
        for keyword in keywords:
            features.append(PatternFeature(
                name=f"keyword_{keyword}",
                value=1,
                weight=0.4,
                description=f"关键词: {keyword}"
            ))
        
        # 上下文特征
        if issue.context:
            for key, value in issue.context.items():
                features.append(PatternFeature(
                    name=f"context_{key}",
                    value=str(value),
                    weight=0.3,
                    description=f"上下文: {key}"
                ))
        
        return features
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（可以改进为更复杂的NLP方法）
        keywords = []
        
        # 预定义的重要关键词
        important_keywords = [
            '错误', '失败', '异常', '超时', '崩溃', '丢失', '重复', '不一致',
            '格式', '编码', '权限', '网络', '数据库', '服务器', '客户端',
            '登录', '上传', '下载', '同步', '备份', '恢复', '更新', '删除'
        ]
        
        text_lower = text.lower()
        for keyword in important_keywords:
            if keyword in text_lower:
                keywords.append(keyword)
        
        return keywords[:5]  # 最多返回5个关键词
    
    def _find_matching_patterns(self, issue: QualityIssue, features: List[PatternFeature]) -> List[str]:
        """查找匹配的模式"""
        matching_patterns = []
        
        for pattern_id, pattern in self.patterns.items():
            if self._is_pattern_match(issue, features, pattern):
                matching_patterns.append(pattern_id)
        
        return matching_patterns
    
    def _is_pattern_match(self, issue: QualityIssue, features: List[PatternFeature], 
                         pattern: QualityPattern) -> bool:
        """判断是否匹配模式"""
        
        # 基本类别匹配
        if issue.category != pattern.category:
            return False
        
        # 特征匹配度计算
        feature_dict = {f.name: f.value for f in features}
        pattern_feature_dict = {f.name: f.value for f in pattern.features}
        
        match_score = 0
        total_weight = 0
        
        for feature_name, feature_value in feature_dict.items():
            if feature_name in pattern_feature_dict:
                pattern_value = pattern_feature_dict[feature_name]
                
                # 计算特征相似度
                if isinstance(feature_value, str) and isinstance(pattern_value, str):
                    similarity = 1.0 if feature_value == pattern_value else 0.0
                elif isinstance(feature_value, (int, float)) and isinstance(pattern_value, (int, float)):
                    # 数值特征的相似度计算
                    max_val = max(abs(feature_value), abs(pattern_value), 1)
                    similarity = 1.0 - abs(feature_value - pattern_value) / max_val
                else:
                    similarity = 1.0 if str(feature_value) == str(pattern_value) else 0.0
                
                # 获取特征权重
                feature_weight = next((f.weight for f in features if f.name == feature_name), 0.5)
                match_score += similarity * feature_weight
                total_weight += feature_weight
        
        # 计算总体匹配度
        if total_weight > 0:
            overall_similarity = match_score / total_weight
            return overall_similarity >= self.similarity_threshold
        
        return False
    
    def _calculate_similarity_scores(self, issue: QualityIssue, 
                                   matching_patterns: List[str]) -> Dict[str, float]:
        """计算相似度分数"""
        similarity_scores = {}
        
        issue_features = self._extract_features(issue)
        issue_feature_dict = {f.name: f.value for f in issue_features}
        
        for pattern_id in matching_patterns:
            pattern = self.patterns[pattern_id]
            pattern_feature_dict = {f.name: f.value for f in pattern.features}
            
            # 计算详细相似度
            similarity = self._calculate_detailed_similarity(issue_feature_dict, pattern_feature_dict)
            similarity_scores[pattern_id] = similarity
        
        return similarity_scores
    
    def _calculate_detailed_similarity(self, features1: Dict[str, Any], 
                                     features2: Dict[str, Any]) -> float:
        """计算详细相似度"""
        common_features = set(features1.keys()) & set(features2.keys())
        
        if not common_features:
            return 0.0
        
        similarity_sum = 0
        for feature in common_features:
            val1, val2 = features1[feature], features2[feature]
            
            if isinstance(val1, str) and isinstance(val2, str):
                similarity = 1.0 if val1 == val2 else 0.0
            elif isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                max_val = max(abs(val1), abs(val2), 1)
                similarity = 1.0 - abs(val1 - val2) / max_val
            else:
                similarity = 1.0 if str(val1) == str(val2) else 0.0
            
            similarity_sum += similarity
        
        return similarity_sum / len(common_features)
    
    def _calculate_classification_confidence(self, similarity_scores: Dict[str, float]) -> float:
        """计算分类置信度"""
        if not similarity_scores:
            return 0.0
        
        max_similarity = max(similarity_scores.values())
        avg_similarity = np.mean(list(similarity_scores.values()))
        
        # 置信度基于最高相似度和平均相似度
        confidence = (max_similarity + avg_similarity) / 2
        return min(confidence, 1.0)
    
    def _generate_classification_recommendations(self, issue: QualityIssue, 
                                              matching_patterns: List[str]) -> List[str]:
        """生成分类建议"""
        recommendations = []
        
        if not matching_patterns:
            recommendations.append("这是一个新类型的问题，建议创建新的处理模式")
            recommendations.append("收集更多相似问题以建立模式库")
        else:
            # 基于匹配模式的建议
            for pattern_id in matching_patterns[:3]:  # 最多3个模式
                pattern = self.patterns[pattern_id]
                recommendations.extend(pattern.prevention_measures[:2])  # 每个模式最多2个建议
        
        # 基于问题特征的通用建议
        if issue.severity == SeverityLevel.CRITICAL:
            recommendations.insert(0, "立即启动紧急响应流程")
        
        if len(issue.affected_data) > 100:
            recommendations.append("考虑批量处理和数据恢复策略")
        
        return list(set(recommendations))  # 去重
    
    def _update_patterns(self, issue: QualityIssue):
        """更新模式库"""
        # 查找现有模式
        matching_patterns = []
        issue_features = self._extract_features(issue)
        
        for pattern_id, pattern in self.patterns.items():
            if self._is_pattern_match(issue, issue_features, pattern):
                matching_patterns.append(pattern_id)
        
        if matching_patterns:
            # 更新现有模式
            for pattern_id in matching_patterns:
                self._update_existing_pattern(pattern_id, issue)
        else:
            # 检查是否需要创建新模式
            self._check_create_new_pattern(issue)
    
    def _update_existing_pattern(self, pattern_id: str, issue: QualityIssue):
        """更新现有模式"""
        pattern = self.patterns[pattern_id]
        
        # 更新统计信息
        pattern.occurrence_count += 1
        pattern.last_seen = issue.created_at
        pattern.affected_users.add(issue.reporter)
        
        # 更新严重程度分布
        if issue.severity in pattern.severity_distribution:
            pattern.severity_distribution[issue.severity] += 1
        else:
            pattern.severity_distribution[issue.severity] = 1
        
        # 更新时间模式
        time_key = f"{issue.created_at.hour}h"
        if time_key in pattern.frequency_pattern:
            pattern.frequency_pattern[time_key] += 1
        else:
            pattern.frequency_pattern[time_key] = 1
        
        # 更新置信度
        pattern.confidence_score = min(pattern.confidence_score + 0.1, 1.0)
        
        logger.info(f"更新模式 {pattern_id}，发生次数: {pattern.occurrence_count}")
    
    def _check_create_new_pattern(self, issue: QualityIssue):
        """检查是否创建新模式"""
        # 查找相似的历史问题
        similar_issues = self._find_similar_historical_issues(issue)
        
        if len(similar_issues) >= self.min_pattern_occurrences:
            # 创建新模式
            new_pattern = self._create_pattern_from_issues([issue] + similar_issues)
            self.patterns[new_pattern.pattern_id] = new_pattern
            logger.info(f"创建新模式 {new_pattern.pattern_id}: {new_pattern.name}")
    
    def _find_similar_historical_issues(self, issue: QualityIssue) -> List[QualityIssue]:
        """查找相似的历史问题"""
        similar_issues = []
        issue_features = self._extract_features(issue)
        
        # 时间窗口
        time_threshold = issue.created_at - timedelta(days=self.time_window_days)
        
        for historical_issue in self.issue_history:
            if (historical_issue.created_at >= time_threshold and 
                historical_issue.id != issue.id and
                historical_issue.category == issue.category):
                
                # 计算相似度
                historical_features = self._extract_features(historical_issue)
                similarity = self._calculate_feature_similarity(issue_features, historical_features)
                
                if similarity >= self.similarity_threshold:
                    similar_issues.append(historical_issue)
        
        return similar_issues
    
    def _calculate_feature_similarity(self, features1: List[PatternFeature], 
                                    features2: List[PatternFeature]) -> float:
        """计算特征相似度"""
        dict1 = {f.name: f.value for f in features1}
        dict2 = {f.name: f.value for f in features2}
        
        return self._calculate_detailed_similarity(dict1, dict2)
    
    def _create_pattern_from_issues(self, issues: List[QualityIssue]) -> QualityPattern:
        """从问题列表创建模式"""
        self.pattern_counter += 1
        pattern_id = f"pattern_{self.pattern_counter:04d}"
        
        # 分析共同特征
        common_features = self._extract_common_features(issues)
        
        # 统计信息
        severity_dist = Counter(issue.severity for issue in issues)
        affected_users = set(issue.reporter for issue in issues)
        
        # 生成模式名称
        pattern_name = self._generate_pattern_name(issues[0].category, common_features)
        
        # 确定模式类型
        pattern_type = self._determine_pattern_type(issues)
        
        # 生成预防措施
        prevention_measures = self._generate_prevention_measures(issues[0].category, common_features)
        
        pattern = QualityPattern(
            pattern_id=pattern_id,
            name=pattern_name,
            pattern_type=pattern_type,
            category=issues[0].category,
            description=f"基于 {len(issues)} 个相似问题识别的模式",
            features=common_features,
            occurrence_count=len(issues),
            first_seen=min(issue.created_at for issue in issues),
            last_seen=max(issue.created_at for issue in issues),
            affected_users=affected_users,
            severity_distribution=dict(severity_dist),
            confidence_score=0.7,  # 初始置信度
            prevention_measures=prevention_measures
        )
        
        return pattern
    
    def _extract_common_features(self, issues: List[QualityIssue]) -> List[PatternFeature]:
        """提取共同特征"""
        all_features = []
        for issue in issues:
            all_features.extend(self._extract_features(issue))
        
        # 统计特征频率
        feature_counts = defaultdict(lambda: defaultdict(int))
        for feature in all_features:
            feature_counts[feature.name][feature.value] += 1
        
        # 选择共同特征
        common_features = []
        total_issues = len(issues)
        
        for feature_name, value_counts in feature_counts.items():
            # 选择出现频率最高的值
            most_common_value, count = max(value_counts.items(), key=lambda x: x[1])
            
            # 如果超过一半的问题都有这个特征值，则认为是共同特征
            if count >= total_issues * 0.5:
                weight = count / total_issues  # 权重基于出现频率
                common_features.append(PatternFeature(
                    name=feature_name,
                    value=most_common_value,
                    weight=weight,
                    description=f"共同特征 (出现率: {weight:.2f})"
                ))
        
        return common_features
    
    def _generate_pattern_name(self, category: ProblemCategory, 
                             features: List[PatternFeature]) -> str:
        """生成模式名称"""
        # 基于类别和主要特征生成名称
        category_names = {
            ProblemCategory.ACCURACY: "准确性",
            ProblemCategory.CONSISTENCY: "一致性", 
            ProblemCategory.COMPLETENESS: "完整性",
            ProblemCategory.FORMAT: "格式",
            ProblemCategory.GUIDELINE: "规范",
            ProblemCategory.PERFORMANCE: "性能",
            ProblemCategory.SYSTEM: "系统"
        }
        
        base_name = category_names.get(category, "未知")
        
        # 添加主要特征描述
        high_weight_features = [f for f in features if f.weight > 0.7]
        if high_weight_features:
            feature_desc = high_weight_features[0].name.replace('_', ' ')
            return f"{base_name}问题-{feature_desc}"
        
        return f"{base_name}问题模式"
    
    def _determine_pattern_type(self, issues: List[QualityIssue]) -> PatternType:
        """确定模式类型"""
        # 基于时间分布确定模式类型
        time_diffs = []
        sorted_issues = sorted(issues, key=lambda x: x.created_at)
        
        for i in range(1, len(sorted_issues)):
            diff = (sorted_issues[i].created_at - sorted_issues[i-1].created_at).total_seconds()
            time_diffs.append(diff)
        
        if not time_diffs:
            return PatternType.ANOMALY
        
        avg_interval = np.mean(time_diffs)
        std_interval = np.std(time_diffs)
        
        # 判断模式类型
        if std_interval / avg_interval < 0.3:  # 间隔相对稳定
            if avg_interval < 3600:  # 小于1小时
                return PatternType.CLUSTERED
            elif avg_interval < 86400:  # 小于1天
                return PatternType.RECURRING
            else:
                return PatternType.SEASONAL
        else:
            return PatternType.ESCALATING
    
    def _generate_prevention_measures(self, category: ProblemCategory, 
                                    features: List[PatternFeature]) -> List[str]:
        """生成预防措施"""
        measures = []
        
        # 基于类别的通用预防措施
        category_measures = {
            ProblemCategory.ACCURACY: [
                "加强数据验证检查",
                "实施双重审核机制",
                "提供准确性培训"
            ],
            ProblemCategory.CONSISTENCY: [
                "建立标准化流程",
                "实施一致性检查",
                "统一操作规范"
            ],
            ProblemCategory.COMPLETENESS: [
                "添加必填字段验证",
                "实施完整性检查",
                "提供数据补全工具"
            ],
            ProblemCategory.FORMAT: [
                "实施格式验证",
                "提供格式转换工具",
                "标准化数据格式"
            ],
            ProblemCategory.GUIDELINE: [
                "完善操作指南",
                "提供培训材料",
                "建立FAQ系统"
            ],
            ProblemCategory.PERFORMANCE: [
                "优化系统性能",
                "增加资源配置",
                "实施性能监控"
            ],
            ProblemCategory.SYSTEM: [
                "修复系统缺陷",
                "升级系统版本",
                "加强系统测试"
            ]
        }
        
        measures.extend(category_measures.get(category, []))
        
        # 基于特征的特定预防措施
        for feature in features:
            if feature.weight > 0.8:  # 高权重特征
                if 'time' in feature.name or 'hour' in feature.name:
                    measures.append("优化工作时间安排")
                elif 'user' in feature.name:
                    measures.append("加强用户培训")
                elif 'data' in feature.name:
                    measures.append("改进数据质量管理")
        
        return list(set(measures))[:5]  # 去重并限制数量
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """获取模式统计信息"""
        if not self.patterns:
            return {"message": "暂无模式数据"}
        
        # 基本统计
        total_patterns = len(self.patterns)
        active_patterns = len([p for p in self.patterns.values() if p.status == PatternStatus.ACTIVE])
        
        # 类别分布
        category_dist = Counter(p.category for p in self.patterns.values())
        
        # 类型分布
        type_dist = Counter(p.pattern_type for p in self.patterns.values())
        
        # 最活跃的模式
        most_active = max(self.patterns.values(), key=lambda p: p.occurrence_count)
        
        return {
            "total_patterns": total_patterns,
            "active_patterns": active_patterns,
            "category_distribution": dict(category_dist),
            "type_distribution": dict(type_dist),
            "most_active_pattern": {
                "id": most_active.pattern_id,
                "name": most_active.name,
                "occurrences": most_active.occurrence_count
            },
            "average_confidence": np.mean([p.confidence_score for p in self.patterns.values()]),
            "total_issues_processed": len(self.issue_history)
        }
    
    def get_pattern_by_id(self, pattern_id: str) -> Optional[QualityPattern]:
        """根据ID获取模式"""
        return self.patterns.get(pattern_id)
    
    def get_patterns_by_category(self, category: ProblemCategory) -> List[QualityPattern]:
        """根据类别获取模式"""
        return [p for p in self.patterns.values() if p.category == category]
    
    def export_patterns(self) -> Dict[str, Any]:
        """导出所有模式"""
        return {
            "patterns": [pattern.to_dict() for pattern in self.patterns.values()],
            "export_time": datetime.now().isoformat(),
            "total_count": len(self.patterns)
        }