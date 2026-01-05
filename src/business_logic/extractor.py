#!/usr/bin/env python3
"""
业务逻辑提炼器 (Business Logic Extractor)
从标注数据中自动识别和提炼业务规则与模式

实现需求 13: 客户业务逻辑提炼与智能化
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter, defaultdict
import re
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PatternType(Enum):
    """业务模式类型"""
    SENTIMENT_CORRELATION = "sentiment_correlation"
    KEYWORD_ASSOCIATION = "keyword_association"
    TEMPORAL_TREND = "temporal_trend"
    USER_BEHAVIOR = "user_behavior"

class RuleType(Enum):
    """业务规则类型"""
    SENTIMENT_RULE = "sentiment_rule"
    KEYWORD_RULE = "keyword_rule"
    TEMPORAL_RULE = "temporal_rule"
    BEHAVIORAL_RULE = "behavioral_rule"

@dataclass
class AnnotationExample:
    """标注示例"""
    id: str
    text: str
    annotation: Dict[str, Any]
    timestamp: datetime
    annotator: str

@dataclass
class BusinessRule:
    """业务规则"""
    id: str
    name: str
    description: str
    pattern: str
    rule_type: RuleType
    confidence: float
    frequency: int
    examples: List[AnnotationExample]
    is_active: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class Pattern:
    """业务模式"""
    type: PatternType
    description: str
    strength: float
    evidence: List[Dict[str, Any]]

@dataclass
class PatternAnalysis:
    """模式分析结果"""
    patterns: List[Pattern]
    total_annotations: int
    analysis_timestamp: datetime
    confidence_threshold: float

class BusinessLogicExtractor:
    """业务逻辑提炼器主类"""
    
    def __init__(self, confidence_threshold: float = 0.8, min_frequency: int = 3):
        """
        初始化业务逻辑提炼器
        
        Args:
            confidence_threshold: 规则置信度阈值
            min_frequency: 最小频率阈值
        """
        self.confidence_threshold = confidence_threshold
        self.min_frequency = min_frequency
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
    def analyze_annotation_patterns(self, annotations: List[Dict[str, Any]]) -> PatternAnalysis:
        """
        分析标注数据中的业务模式和规律
        
        Args:
            annotations: 标注数据列表
            
        Returns:
            PatternAnalysis: 模式分析结果
        """
        logger.info(f"开始分析 {len(annotations)} 条标注数据的业务模式")
        
        if not annotations:
            return PatternAnalysis(
                patterns=[],
                total_annotations=0,
                analysis_timestamp=datetime.now(),
                confidence_threshold=self.confidence_threshold
            )
        
        # 转换为DataFrame便于分析
        df = pd.DataFrame(annotations)
        
        patterns = []
        
        # 1. 情感关联分析
        sentiment_patterns = self._analyze_sentiment_correlation(df)
        patterns.extend(sentiment_patterns)
        
        # 2. 关键词关联分析
        keyword_patterns = self._analyze_keyword_association(df)
        patterns.extend(keyword_patterns)
        
        # 3. 时间趋势分析
        temporal_patterns = self._analyze_temporal_trends(df)
        patterns.extend(temporal_patterns)
        
        # 4. 用户行为模式分析
        behavior_patterns = self._analyze_user_behavior(df)
        patterns.extend(behavior_patterns)
        
        logger.info(f"识别出 {len(patterns)} 个业务模式")
        
        return PatternAnalysis(
            patterns=patterns,
            total_annotations=len(annotations),
            analysis_timestamp=datetime.now(),
            confidence_threshold=self.confidence_threshold
        )
    
    def _analyze_sentiment_correlation(self, df: pd.DataFrame) -> List[Pattern]:
        """分析情感关联模式"""
        patterns = []
        
        if 'sentiment' not in df.columns or 'text' not in df.columns:
            return patterns
        
        try:
            # 计算情感分布
            sentiment_counts = df['sentiment'].value_counts()
            total_count = len(df)
            
            for sentiment, count in sentiment_counts.items():
                strength = count / total_count
                if strength >= 0.3:  # 至少占30%才认为是显著模式
                    # 提取该情感的典型文本特征
                    sentiment_texts = df[df['sentiment'] == sentiment]['text'].tolist()
                    keywords = self._extract_keywords(sentiment_texts)
                    
                    pattern = Pattern(
                        type=PatternType.SENTIMENT_CORRELATION,
                        description=f"情感 '{sentiment}' 占比 {strength:.1%}，关键词: {', '.join(keywords[:5])}",
                        strength=strength,
                        evidence=[
                            {
                                "sentiment": sentiment,
                                "count": int(count),
                                "percentage": strength,
                                "keywords": keywords[:10]
                            }
                        ]
                    )
                    patterns.append(pattern)
                    
        except Exception as e:
            logger.error(f"情感关联分析失败: {e}")
            
        return patterns
    
    def _analyze_keyword_association(self, df: pd.DataFrame) -> List[Pattern]:
        """分析关键词关联模式"""
        patterns = []
        
        if 'text' not in df.columns:
            return patterns
            
        try:
            # 提取所有文本
            texts = df['text'].fillna('').tolist()
            
            # TF-IDF向量化
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            feature_names = self.vectorizer.get_feature_names_out()
            
            # 计算词汇重要性
            word_scores = np.mean(tfidf_matrix.toarray(), axis=0)
            word_importance = list(zip(feature_names, word_scores))
            word_importance.sort(key=lambda x: x[1], reverse=True)
            
            # 识别高频关键词组合
            top_words = [word for word, score in word_importance[:20] if score > 0.1]
            
            if top_words:
                pattern = Pattern(
                    type=PatternType.KEYWORD_ASSOCIATION,
                    description=f"识别出 {len(top_words)} 个高频关键词",
                    strength=min(1.0, len(top_words) / 10),
                    evidence=[
                        {
                            "top_keywords": top_words,
                            "keyword_scores": dict(word_importance[:20])
                        }
                    ]
                )
                patterns.append(pattern)
                
        except Exception as e:
            logger.error(f"关键词关联分析失败: {e}")
            
        return patterns
    
    def _analyze_temporal_trends(self, df: pd.DataFrame) -> List[Pattern]:
        """分析时间趋势模式"""
        patterns = []
        
        if 'created_at' not in df.columns:
            return patterns
            
        try:
            # 转换时间列
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
            df = df.dropna(subset=['created_at'])
            
            if len(df) < 10:  # 数据太少无法分析趋势
                return patterns
            
            # 按日期分组统计
            daily_counts = df.groupby(df['created_at'].dt.date).size()
            
            if len(daily_counts) >= 7:  # 至少一周的数据
                # 计算趋势强度
                trend_strength = self._calculate_trend_strength(daily_counts.values)
                
                if abs(trend_strength) > 0.3:  # 显著趋势
                    trend_type = "上升" if trend_strength > 0 else "下降"
                    
                    pattern = Pattern(
                        type=PatternType.TEMPORAL_TREND,
                        description=f"标注活动呈现{trend_type}趋势，强度: {abs(trend_strength):.2f}",
                        strength=abs(trend_strength),
                        evidence=[
                            {
                                "trend_direction": trend_type,
                                "trend_strength": trend_strength,
                                "daily_counts": daily_counts.to_dict(),
                                "analysis_period": f"{daily_counts.index[0]} 到 {daily_counts.index[-1]}"
                            }
                        ]
                    )
                    patterns.append(pattern)
                    
        except Exception as e:
            logger.error(f"时间趋势分析失败: {e}")
            
        return patterns
    
    def _analyze_user_behavior(self, df: pd.DataFrame) -> List[Pattern]:
        """分析用户行为模式"""
        patterns = []
        
        if 'annotator' not in df.columns:
            return patterns
            
        try:
            # 用户标注统计
            user_counts = df['annotator'].value_counts()
            total_annotations = len(df)
            
            # 识别活跃用户
            active_users = user_counts[user_counts >= self.min_frequency]
            
            if len(active_users) > 0:
                # 计算用户活跃度分布
                activity_distribution = active_users / total_annotations
                
                pattern = Pattern(
                    type=PatternType.USER_BEHAVIOR,
                    description=f"{len(active_users)} 个活跃用户贡献了 {activity_distribution.sum():.1%} 的标注",
                    strength=activity_distribution.sum(),
                    evidence=[
                        {
                            "active_users": len(active_users),
                            "total_users": len(user_counts),
                            "user_distribution": user_counts.head(10).to_dict(),
                            "top_contributor_percentage": activity_distribution.iloc[0] if len(activity_distribution) > 0 else 0
                        }
                    ]
                )
                patterns.append(pattern)
                
        except Exception as e:
            logger.error(f"用户行为分析失败: {e}")
            
        return patterns
    
    def _extract_keywords(self, texts: List[str], top_k: int = 10) -> List[str]:
        """从文本列表中提取关键词"""
        try:
            if not texts:
                return []
                
            # 简单的关键词提取：基于词频
            all_text = ' '.join(texts).lower()
            words = re.findall(r'\b\w+\b', all_text)
            
            # 过滤停用词和短词
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
            filtered_words = [word for word in words if len(word) > 2 and word not in stop_words]
            
            # 统计词频
            word_counts = Counter(filtered_words)
            return [word for word, count in word_counts.most_common(top_k)]
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return []
    
    def _calculate_trend_strength(self, values: np.ndarray) -> float:
        """计算趋势强度"""
        try:
            if len(values) < 2:
                return 0.0
                
            # 使用线性回归计算趋势
            x = np.arange(len(values))
            coeffs = np.polyfit(x, values, 1)
            slope = coeffs[0]
            
            # 标准化斜率
            mean_value = np.mean(values)
            if mean_value > 0:
                normalized_slope = slope / mean_value
                return np.clip(normalized_slope, -1.0, 1.0)
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"趋势强度计算失败: {e}")
            return 0.0
    
    def extract_business_rules(self, project_id: str, threshold: float = None) -> List[BusinessRule]:
        """
        从项目标注数据中提取业务规则
        
        Args:
            project_id: 项目ID
            threshold: 置信度阈值，默认使用初始化时的值
            
        Returns:
            List[BusinessRule]: 提取的业务规则列表
        """
        if threshold is None:
            threshold = self.confidence_threshold
            
        logger.info(f"开始为项目 {project_id} 提取业务规则，置信度阈值: {threshold}")
        
        # TODO: 从数据库获取项目标注数据
        # 这里先返回示例规则
        rules = []
        
        # 示例规则：基于情感分析的规则
        example_rule = BusinessRule(
            id=f"rule_{project_id}_sentiment_001",
            name="正面情感关键词规则",
            description="包含特定关键词的文本通常被标注为正面情感",
            pattern="IF text CONTAINS ['excellent', 'great', 'amazing'] THEN sentiment = 'positive'",
            rule_type=RuleType.SENTIMENT_RULE,
            confidence=0.85,
            frequency=15,
            examples=[],
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        rules.append(example_rule)
        
        logger.info(f"为项目 {project_id} 提取了 {len(rules)} 个业务规则")
        return rules
    
    def calculate_rule_confidence(self, rule: BusinessRule) -> float:
        """
        计算业务规则的置信度
        
        Args:
            rule: 业务规则
            
        Returns:
            float: 置信度分数 (0.0-1.0)
        """
        try:
            # 基于频率和示例数量计算置信度
            frequency_score = min(1.0, rule.frequency / 20)  # 频率越高置信度越高
            example_score = min(1.0, len(rule.examples) / 10)  # 示例越多置信度越高
            
            # 综合计算置信度
            confidence = (frequency_score * 0.6 + example_score * 0.4)
            
            return round(confidence, 3)
            
        except Exception as e:
            logger.error(f"置信度计算失败: {e}")
            return 0.0