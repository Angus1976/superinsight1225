#!/usr/bin/env python3
"""
业务规则自动生成器
基于频率、置信度的规则生成，规则冲突检测和解决，规则优化和合并算法

实现需求 13: 客户业务逻辑提炼与智能化 - 任务 47.2
"""

import logging
import uuid
import re
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
import itertools

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RuleCondition:
    """规则条件"""
    field: str
    operator: str  # contains, equals, greater_than, less_than, in_range, regex_match
    value: Any
    confidence: float = 0.0
    weight: float = 1.0  # 条件权重

@dataclass
class RuleConsequent:
    """规则结果"""
    field: str
    value: Any
    confidence: float = 0.0
    probability: float = 0.0  # 预测概率

@dataclass
class BusinessRuleTemplate:
    """业务规则模板"""
    id: str
    name: str
    description: str = ""
    conditions: List[RuleCondition] = field(default_factory=list)
    consequent: RuleConsequent = None
    rule_type: str = "association"  # association, classification, sequential, temporal
    support: int = 0  # 支持度 (满足条件的样本数)
    confidence: float = 0.0  # 置信度
    lift: float = 0.0  # 提升度
    conviction: float = 0.0  # 确信度
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    is_valid: bool = True
    conflict_rules: List[str] = field(default_factory=list)
    validation_score: float = 0.0
    business_impact: str = "medium"  # low, medium, high
    
class AdvancedRuleGenerator:
    """高级规则生成器"""
    
    def __init__(self, min_support: int = 3, min_confidence: float = 0.6):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
        self.decision_tree = None
        self.random_forest = None
        
    def generate_comprehensive_rules(self, annotations: List[Dict[str, Any]]) -> List[BusinessRuleTemplate]:
        """
        生成综合业务规则
        
        Args:
            annotations: 标注数据列表
            
        Returns:
            List[BusinessRuleTemplate]: 生成的规则列表
        """
        try:
            logger.info(f"开始从 {len(annotations)} 条标注数据生成综合业务规则")
            
            df = pd.DataFrame(annotations)
            all_rules = []
            
            # 1. 基于频率的关联规则
            frequency_rules = self._generate_frequency_based_rules(df)
            all_rules.extend(frequency_rules)
            
            # 2. 基于机器学习的分类规则
            ml_rules = self._generate_ml_based_rules(df)
            all_rules.extend(ml_rules)
            
            # 3. 时序规则
            temporal_rules = self._generate_temporal_rules(df)
            all_rules.extend(temporal_rules)
            
            # 4. 模式规则
            pattern_rules = self._generate_pattern_rules(df)
            all_rules.extend(pattern_rules)
            
            # 5. 异常检测规则
            anomaly_rules = self._generate_anomaly_detection_rules(df)
            all_rules.extend(anomaly_rules)
            
            # 6. 过滤和排序规则
            valid_rules = self._filter_and_rank_advanced_rules(all_rules, df)
            
            logger.info(f"生成了 {len(valid_rules)} 个高级业务规则")
            return valid_rules
            
        except Exception as e:
            logger.error(f"综合规则生成失败: {e}")
            return []
    
    def _generate_frequency_based_rules(self, df: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """生成基于频率的规则"""
        rules = []
        
        try:
            # 基于原有的频率规则生成逻辑，但增强了
            freq_generator = FrequencyBasedRuleGenerator(self.min_support, self.min_confidence)
            basic_rules = freq_generator.generate_rules_from_annotations(df.to_dict('records'))
            
            # 转换为高级规则格式
            for rule in basic_rules:
                advanced_rule = BusinessRuleTemplate(
                    id=rule.id,
                    name=rule.name,
                    description=f"基于频率分析的关联规则: {rule.name}",
                    conditions=rule.conditions,
                    consequent=rule.consequent,
                    rule_type="association",
                    support=rule.support,
                    confidence=rule.confidence,
                    lift=rule.lift,
                    conviction=rule.conviction,
                    created_at=rule.created_at,
                    business_impact=self._assess_business_impact(rule.confidence, rule.support)
                )
                rules.append(advanced_rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"频率规则生成失败: {e}")
            return []
    
    def _generate_ml_based_rules(self, df: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """生成基于机器学习的分类规则"""
        rules = []
        
        try:
            if len(df) < 10:
                return rules
            
            # 准备特征和目标变量
            features, target_columns = self._prepare_ml_features(df)
            
            if features is None or len(target_columns) == 0:
                return rules
            
            # 为每个目标变量训练模型
            for target_col in target_columns:
                if target_col not in df.columns:
                    continue
                
                y = df[target_col].fillna('unknown')
                
                # 过滤掉样本太少的类别
                value_counts = y.value_counts()
                valid_values = value_counts[value_counts >= self.min_support].index
                
                if len(valid_values) < 2:
                    continue
                
                # 过滤数据
                mask = y.isin(valid_values)
                X_filtered = features[mask]
                y_filtered = y[mask]
                
                # 训练决策树
                dt = DecisionTreeClassifier(
                    max_depth=5, 
                    min_samples_split=self.min_support,
                    min_samples_leaf=2,
                    random_state=42
                )
                
                try:
                    dt.fit(X_filtered, y_filtered)
                    
                    # 提取决策树规则
                    tree_rules = self._extract_decision_tree_rules(dt, X_filtered.columns, target_col)
                    rules.extend(tree_rules)
                    
                except Exception as e:
                    logger.warning(f"决策树训练失败 for {target_col}: {e}")
                    continue
            
            return rules
            
        except Exception as e:
            logger.error(f"机器学习规则生成失败: {e}")
            return []
    
    def _prepare_ml_features(self, df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """准备机器学习特征"""
        try:
            features = pd.DataFrame()
            target_columns = []
            
            # 文本特征
            if 'text' in df.columns:
                # 文本长度
                features['text_length'] = df['text'].str.len().fillna(0)
                
                # 单词数量
                features['word_count'] = df['text'].str.split().str.len().fillna(0)
                
                # 句子数量
                features['sentence_count'] = df['text'].str.count(r'[.!?]').fillna(0)
                
                # 大写字母比例
                features['uppercase_ratio'] = df['text'].apply(
                    lambda x: sum(1 for c in str(x) if c.isupper()) / len(str(x)) if len(str(x)) > 0 else 0
                )
                
                # 标点符号数量
                features['punctuation_count'] = df['text'].str.count(r'[^\w\s]').fillna(0)
            
            # 时间特征
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                features['hour'] = df['created_at'].dt.hour.fillna(12)
                features['day_of_week'] = df['created_at'].dt.dayofweek.fillna(0)
                features['is_weekend'] = (df['created_at'].dt.dayofweek >= 5).astype(int).fillna(0)
            
            # 用户特征
            if 'annotator' in df.columns:
                # 用户标注数量 (需要计算)
                user_counts = df['annotator'].value_counts()
                features['user_annotation_count'] = df['annotator'].map(user_counts).fillna(1)
            
            # 评分特征
            if 'rating' in df.columns:
                features['has_rating'] = df['rating'].notna().astype(int)
                features['rating_value'] = df['rating'].fillna(df['rating'].mean() if not df['rating'].isna().all() else 3)
            
            # 确定目标变量
            potential_targets = ['sentiment', 'rating', 'category', 'label']
            for col in potential_targets:
                if col in df.columns and df[col].nunique() >= 2:
                    target_columns.append(col)
            
            if features.empty:
                return None, []
            
            return features, target_columns
            
        except Exception as e:
            logger.error(f"特征准备失败: {e}")
            return None, []
    
    def _extract_decision_tree_rules(self, dt: DecisionTreeClassifier, feature_names: List[str], target_col: str) -> List[BusinessRuleTemplate]:
        """从决策树提取规则"""
        rules = []
        
        try:
            tree = dt.tree_
            
            def extract_rules_recursive(node_id, conditions, depth=0):
                if depth > 10:  # 防止过深递归
                    return
                
                # 叶子节点
                if tree.children_left[node_id] == tree.children_right[node_id]:
                    # 获取预测类别和概率
                    values = tree.value[node_id][0]
                    predicted_class = dt.classes_[np.argmax(values)]
                    confidence = np.max(values) / np.sum(values)
                    support = int(np.sum(values))
                    
                    if support >= self.min_support and confidence >= self.min_confidence:
                        # 创建规则
                        rule = BusinessRuleTemplate(
                            id=f"ml_rule_{uuid.uuid4().hex[:8]}",
                            name=f"ML规则: 预测 {target_col} = {predicted_class}",
                            description=f"基于决策树的分类规则，置信度 {confidence:.3f}",
                            conditions=conditions.copy(),
                            consequent=RuleConsequent(
                                field=target_col,
                                value=predicted_class,
                                confidence=confidence,
                                probability=confidence
                            ),
                            rule_type="classification",
                            support=support,
                            confidence=confidence,
                            business_impact=self._assess_business_impact(confidence, support)
                        )
                        rules.append(rule)
                    return
                
                # 内部节点
                feature_idx = tree.feature[node_id]
                threshold = tree.threshold[node_id]
                feature_name = feature_names[feature_idx]
                
                # 左子树 (<=)
                left_condition = RuleCondition(
                    field=feature_name,
                    operator="less_than_or_equal",
                    value=threshold,
                    confidence=0.8
                )
                extract_rules_recursive(
                    tree.children_left[node_id], 
                    conditions + [left_condition], 
                    depth + 1
                )
                
                # 右子树 (>)
                right_condition = RuleCondition(
                    field=feature_name,
                    operator="greater_than",
                    value=threshold,
                    confidence=0.8
                )
                extract_rules_recursive(
                    tree.children_right[node_id], 
                    conditions + [right_condition], 
                    depth + 1
                )
            
            # 从根节点开始提取
            extract_rules_recursive(0, [])
            
            return rules
            
        except Exception as e:
            logger.error(f"决策树规则提取失败: {e}")
            return []
    
    def _generate_temporal_rules(self, df: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """生成时序规则"""
        rules = []
        
        try:
            if 'created_at' not in df.columns:
                return rules
            
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
            df = df.dropna(subset=['created_at'])
            
            if len(df) < 10:
                return rules
            
            # 按时间排序
            df_sorted = df.sort_values('created_at')
            
            # 1. 时间段规则
            df_sorted['hour'] = df_sorted['created_at'].dt.hour
            df_sorted['day_of_week'] = df_sorted['created_at'].dt.day_name()
            
            # 分析不同时间段的模式
            for time_field in ['hour', 'day_of_week']:
                for time_value, group in df_sorted.groupby(time_field):
                    if len(group) < self.min_support:
                        continue
                    
                    # 分析该时间段的主要特征
                    for target_col in ['sentiment', 'rating']:
                        if target_col not in group.columns:
                            continue
                        
                        value_counts = group[target_col].value_counts()
                        if len(value_counts) == 0:
                            continue
                        
                        dominant_value = value_counts.index[0]
                        support = value_counts.iloc[0]
                        confidence = support / len(group)
                        
                        if confidence >= self.min_confidence:
                            rule = BusinessRuleTemplate(
                                id=f"temporal_rule_{uuid.uuid4().hex[:8]}",
                                name=f"时间规律: {time_field}={time_value} → {target_col}={dominant_value}",
                                description=f"在{time_field}为{time_value}时，{target_col}倾向于{dominant_value}",
                                conditions=[
                                    RuleCondition(
                                        field=time_field,
                                        operator="equals",
                                        value=time_value,
                                        confidence=confidence
                                    )
                                ],
                                consequent=RuleConsequent(
                                    field=target_col,
                                    value=dominant_value,
                                    confidence=confidence
                                ),
                                rule_type="temporal",
                                support=int(support),
                                confidence=confidence,
                                business_impact=self._assess_business_impact(confidence, support)
                            )
                            rules.append(rule)
            
            # 2. 序列规则 (如果有用户信息)
            if 'annotator' in df_sorted.columns:
                sequence_rules = self._generate_sequence_rules(df_sorted)
                rules.extend(sequence_rules)
            
            return rules
            
        except Exception as e:
            logger.error(f"时序规则生成失败: {e}")
            return []
    
    def _generate_sequence_rules(self, df_sorted: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """生成序列规则"""
        rules = []
        
        try:
            # 按用户分组分析序列模式
            for user, user_data in df_sorted.groupby('annotator'):
                if len(user_data) < 5:  # 至少5个标注才分析序列
                    continue
                
                user_data_sorted = user_data.sort_values('created_at')
                
                # 分析情感序列模式
                if 'sentiment' in user_data_sorted.columns:
                    sentiments = user_data_sorted['sentiment'].tolist()
                    
                    # 寻找连续模式
                    for i in range(len(sentiments) - 2):
                        pattern = sentiments[i:i+3]  # 3个连续的情感
                        
                        # 统计这个模式在该用户中的出现频率
                        pattern_count = 0
                        for j in range(len(sentiments) - 2):
                            if sentiments[j:j+3] == pattern:
                                pattern_count += 1
                        
                        if pattern_count >= 2:  # 至少出现2次
                            confidence = pattern_count / (len(sentiments) - 2)
                            
                            if confidence >= 0.3:  # 序列规则的置信度阈值较低
                                rule = BusinessRuleTemplate(
                                    id=f"sequence_rule_{uuid.uuid4().hex[:8]}",
                                    name=f"序列模式: {pattern[0]}→{pattern[1]}→{pattern[2]}",
                                    description=f"用户{user}的情感序列模式",
                                    conditions=[
                                        RuleCondition(
                                            field="annotator",
                                            operator="equals",
                                            value=user,
                                            confidence=1.0
                                        ),
                                        RuleCondition(
                                            field="previous_sentiment",
                                            operator="equals",
                                            value=f"{pattern[0]}→{pattern[1]}",
                                            confidence=confidence
                                        )
                                    ],
                                    consequent=RuleConsequent(
                                        field="next_sentiment",
                                        value=pattern[2],
                                        confidence=confidence
                                    ),
                                    rule_type="sequential",
                                    support=pattern_count,
                                    confidence=confidence,
                                    business_impact="low"  # 序列规则通常影响较小
                                )
                                rules.append(rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"序列规则生成失败: {e}")
            return []
    
    def _generate_pattern_rules(self, df: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """生成模式规则"""
        rules = []
        
        try:
            # 1. 文本模式规则
            if 'text' in df.columns:
                text_pattern_rules = self._generate_text_pattern_rules(df)
                rules.extend(text_pattern_rules)
            
            # 2. 数值模式规则
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            for col in numeric_columns:
                if col in ['rating'] and not df[col].isna().all():
                    numeric_rules = self._generate_numeric_pattern_rules(df, col)
                    rules.extend(numeric_rules)
            
            return rules
            
        except Exception as e:
            logger.error(f"模式规则生成失败: {e}")
            return []
    
    def _generate_text_pattern_rules(self, df: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """生成文本模式规则"""
        rules = []
        
        try:
            # 分析文本模式
            text_patterns = {
                'question_pattern': r'\?',
                'exclamation_pattern': r'!',
                'uppercase_pattern': r'[A-Z]{3,}',
                'number_pattern': r'\d+',
                'email_pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                'url_pattern': r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            }
            
            for pattern_name, pattern_regex in text_patterns.items():
                # 找到匹配模式的文本
                df[f'has_{pattern_name}'] = df['text'].str.contains(pattern_regex, na=False, regex=True)
                
                pattern_matches = df[df[f'has_{pattern_name}']]
                
                if len(pattern_matches) >= self.min_support:
                    # 分析模式与目标变量的关联
                    for target_col in ['sentiment', 'rating']:
                        if target_col not in df.columns:
                            continue
                        
                        # 计算模式的目标分布
                        pattern_target_dist = pattern_matches[target_col].value_counts()
                        total_target_dist = df[target_col].value_counts()
                        
                        if len(pattern_target_dist) == 0:
                            continue
                        
                        dominant_value = pattern_target_dist.index[0]
                        support = pattern_target_dist.iloc[0]
                        confidence = support / len(pattern_matches)
                        
                        # 计算提升度
                        expected_prob = total_target_dist.get(dominant_value, 0) / len(df)
                        lift = confidence / expected_prob if expected_prob > 0 else 0
                        
                        if confidence >= self.min_confidence and lift > 1.2:
                            rule = BusinessRuleTemplate(
                                id=f"pattern_rule_{uuid.uuid4().hex[:8]}",
                                name=f"文本模式: {pattern_name} → {target_col}={dominant_value}",
                                description=f"包含{pattern_name}的文本倾向于{target_col}为{dominant_value}",
                                conditions=[
                                    RuleCondition(
                                        field="text",
                                        operator="regex_match",
                                        value=pattern_regex,
                                        confidence=confidence
                                    )
                                ],
                                consequent=RuleConsequent(
                                    field=target_col,
                                    value=dominant_value,
                                    confidence=confidence
                                ),
                                rule_type="pattern",
                                support=int(support),
                                confidence=confidence,
                                lift=lift,
                                business_impact=self._assess_business_impact(confidence, support)
                            )
                            rules.append(rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"文本模式规则生成失败: {e}")
            return []
    
    def _generate_numeric_pattern_rules(self, df: pd.DataFrame, numeric_col: str) -> List[BusinessRuleTemplate]:
        """生成数值模式规则"""
        rules = []
        
        try:
            values = df[numeric_col].dropna()
            if len(values) < self.min_support:
                return rules
            
            # 分析数值分布
            quartiles = values.quantile([0.25, 0.5, 0.75])
            
            # 创建数值范围规则
            ranges = [
                ("low", values.min(), quartiles[0.25]),
                ("medium_low", quartiles[0.25], quartiles[0.5]),
                ("medium_high", quartiles[0.5], quartiles[0.75]),
                ("high", quartiles[0.75], values.max())
            ]
            
            for range_name, min_val, max_val in ranges:
                range_mask = (df[numeric_col] >= min_val) & (df[numeric_col] <= max_val)
                range_data = df[range_mask]
                
                if len(range_data) >= self.min_support:
                    # 分析该范围与其他变量的关联
                    for target_col in ['sentiment']:
                        if target_col not in df.columns:
                            continue
                        
                        target_dist = range_data[target_col].value_counts()
                        if len(target_dist) == 0:
                            continue
                        
                        dominant_value = target_dist.index[0]
                        support = target_dist.iloc[0]
                        confidence = support / len(range_data)
                        
                        if confidence >= self.min_confidence:
                            rule = BusinessRuleTemplate(
                                id=f"numeric_rule_{uuid.uuid4().hex[:8]}",
                                name=f"数值模式: {numeric_col} in [{min_val:.2f}, {max_val:.2f}] → {target_col}={dominant_value}",
                                description=f"{numeric_col}在{range_name}范围时，{target_col}倾向于{dominant_value}",
                                conditions=[
                                    RuleCondition(
                                        field=numeric_col,
                                        operator="in_range",
                                        value=[min_val, max_val],
                                        confidence=confidence
                                    )
                                ],
                                consequent=RuleConsequent(
                                    field=target_col,
                                    value=dominant_value,
                                    confidence=confidence
                                ),
                                rule_type="pattern",
                                support=int(support),
                                confidence=confidence,
                                business_impact=self._assess_business_impact(confidence, support)
                            )
                            rules.append(rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"数值模式规则生成失败: {e}")
            return []
    
    def _generate_anomaly_detection_rules(self, df: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """生成异常检测规则"""
        rules = []
        
        try:
            # 1. 文本长度异常
            if 'text' in df.columns:
                text_lengths = df['text'].str.len().dropna()
                if len(text_lengths) >= 10:
                    # 使用IQR方法检测异常
                    Q1 = text_lengths.quantile(0.25)
                    Q3 = text_lengths.quantile(0.75)
                    IQR = Q3 - Q1
                    
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    
                    # 异常短文本规则
                    short_texts = df[df['text'].str.len() < lower_bound]
                    if len(short_texts) >= self.min_support:
                        anomaly_rules = self._create_anomaly_rules(
                            short_texts, df, "text_length", "too_short", 
                            f"文本长度 < {lower_bound:.0f}"
                        )
                        rules.extend(anomaly_rules)
                    
                    # 异常长文本规则
                    long_texts = df[df['text'].str.len() > upper_bound]
                    if len(long_texts) >= self.min_support:
                        anomaly_rules = self._create_anomaly_rules(
                            long_texts, df, "text_length", "too_long", 
                            f"文本长度 > {upper_bound:.0f}"
                        )
                        rules.extend(anomaly_rules)
            
            # 2. 时间异常 (如果有时间字段)
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                df['hour'] = df['created_at'].dt.hour
                
                # 深夜标注异常
                night_annotations = df[(df['hour'] >= 23) | (df['hour'] <= 5)]
                if len(night_annotations) >= self.min_support:
                    anomaly_rules = self._create_anomaly_rules(
                        night_annotations, df, "annotation_time", "night_shift", 
                        "深夜时段标注"
                    )
                    rules.extend(anomaly_rules)
            
            return rules
            
        except Exception as e:
            logger.error(f"异常检测规则生成失败: {e}")
            return []
    
    def _create_anomaly_rules(self, anomaly_data: pd.DataFrame, full_data: pd.DataFrame, 
                            anomaly_type: str, anomaly_name: str, description: str) -> List[BusinessRuleTemplate]:
        """创建异常规则"""
        rules = []
        
        try:
            # 分析异常数据的特征
            for target_col in ['sentiment', 'rating']:
                if target_col not in anomaly_data.columns:
                    continue
                
                anomaly_dist = anomaly_data[target_col].value_counts()
                normal_dist = full_data[target_col].value_counts()
                
                if len(anomaly_dist) == 0:
                    continue
                
                # 找到异常数据中显著不同的分布
                for value, count in anomaly_dist.items():
                    anomaly_prob = count / len(anomaly_data)
                    normal_prob = normal_dist.get(value, 0) / len(full_data)
                    
                    # 如果异常数据中某个值的概率显著高于正常数据
                    if anomaly_prob >= self.min_confidence and anomaly_prob > normal_prob * 1.5:
                        rule = BusinessRuleTemplate(
                            id=f"anomaly_rule_{uuid.uuid4().hex[:8]}",
                            name=f"异常模式: {anomaly_name} → {target_col}={value}",
                            description=f"{description}时，{target_col}异常倾向于{value}",
                            conditions=[
                                RuleCondition(
                                    field=anomaly_type,
                                    operator="anomaly_detected",
                                    value=anomaly_name,
                                    confidence=anomaly_prob
                                )
                            ],
                            consequent=RuleConsequent(
                                field=target_col,
                                value=value,
                                confidence=anomaly_prob
                            ),
                            rule_type="anomaly",
                            support=int(count),
                            confidence=anomaly_prob,
                            business_impact="high"  # 异常规则通常业务影响较大
                        )
                        rules.append(rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"异常规则创建失败: {e}")
            return []
    
    def _assess_business_impact(self, confidence: float, support: int) -> str:
        """评估业务影响"""
        # 综合置信度和支持度评估影响
        if confidence >= 0.8 and support >= 10:
            return "high"
        elif confidence >= 0.6 and support >= 5:
            return "medium"
        else:
            return "low"
    
    def _filter_and_rank_advanced_rules(self, rules: List[BusinessRuleTemplate], df: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """过滤和排序高级规则"""
        try:
            # 过滤低质量规则
            valid_rules = [
                rule for rule in rules
                if rule.support >= self.min_support and rule.confidence >= self.min_confidence
            ]
            
            # 计算综合评分
            for rule in valid_rules:
                score = self._calculate_rule_score(rule)
                rule.validation_score = score
            
            # 按综合评分排序
            valid_rules.sort(key=lambda r: r.validation_score, reverse=True)
            
            # 限制返回数量并去重
            unique_rules = self._remove_duplicate_rules(valid_rules)
            
            return unique_rules[:100]  # 最多返回100个规则
            
        except Exception as e:
            logger.error(f"高级规则过滤排序失败: {e}")
            return rules
    
    def _calculate_rule_score(self, rule: BusinessRuleTemplate) -> float:
        """计算规则综合评分"""
        try:
            # 基础分数
            base_score = (
                rule.confidence * 0.4 +
                min(rule.lift, 5) / 5 * 0.2 +  # 限制lift的影响
                min(rule.support, 50) / 50 * 0.2 +  # 支持度标准化
                min(rule.conviction, 10) / 10 * 0.1  # 限制conviction的影响
            )
            
            # 规则类型权重
            type_weights = {
                "classification": 1.2,
                "association": 1.0,
                "temporal": 0.9,
                "pattern": 1.1,
                "sequential": 0.8,
                "anomaly": 1.3
            }
            
            type_weight = type_weights.get(rule.rule_type, 1.0)
            
            # 业务影响权重
            impact_weights = {
                "high": 1.3,
                "medium": 1.0,
                "low": 0.8
            }
            
            impact_weight = impact_weights.get(rule.business_impact, 1.0)
            
            # 条件复杂度惩罚 (过于复杂的规则降低分数)
            complexity_penalty = max(0.5, 1.0 - len(rule.conditions) * 0.1)
            
            final_score = base_score * type_weight * impact_weight * complexity_penalty
            
            return round(final_score, 3)
            
        except Exception as e:
            logger.error(f"规则评分计算失败: {e}")
            return 0.0
    
    def _remove_duplicate_rules(self, rules: List[BusinessRuleTemplate]) -> List[BusinessRuleTemplate]:
        """移除重复规则"""
        try:
            unique_rules = []
            seen_signatures = set()
            
            for rule in rules:
                # 创建规则签名
                signature = self._create_rule_signature(rule)
                
                if signature not in seen_signatures:
                    unique_rules.append(rule)
                    seen_signatures.add(signature)
            
            return unique_rules
            
        except Exception as e:
            logger.error(f"重复规则移除失败: {e}")
            return rules
    
    def _create_rule_signature(self, rule: BusinessRuleTemplate) -> str:
        """创建规则签名用于去重"""
        try:
            # 基于条件和结果创建签名
            condition_parts = []
            for cond in rule.conditions:
                part = f"{cond.field}_{cond.operator}_{cond.value}"
                condition_parts.append(part)
            
            condition_sig = "|".join(sorted(condition_parts))
            consequent_sig = f"{rule.consequent.field}_{rule.consequent.value}"
            
            return f"{condition_sig}→{consequent_sig}"
            
        except Exception as e:
            logger.error(f"规则签名创建失败: {e}")
            return str(uuid.uuid4())

class FrequencyBasedRuleGenerator:
    """基于频率的规则生成器"""
    
    def __init__(self, min_support: int = 3, min_confidence: float = 0.6):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
        
    def generate_rules_from_annotations(self, annotations: List[Dict[str, Any]]) -> List[BusinessRuleTemplate]:
        """
        从标注数据生成业务规则
        
        Args:
            annotations: 标注数据列表
            
        Returns:
            List[BusinessRuleTemplate]: 生成的规则列表
        """
        try:
            logger.info(f"开始从 {len(annotations)} 条标注数据生成业务规则")
            
            df = pd.DataFrame(annotations)
            rules = []
            
            # 1. 生成情感规则
            sentiment_rules = self._generate_sentiment_rules(df)
            rules.extend(sentiment_rules)
            
            # 2. 生成关键词规则
            keyword_rules = self._generate_keyword_rules(df)
            rules.extend(keyword_rules)
            
            # 3. 生成评分规则
            rating_rules = self._generate_rating_rules(df)
            rules.extend(rating_rules)
            
            # 4. 生成组合规则
            combination_rules = self._generate_combination_rules(df)
            rules.extend(combination_rules)
            
            # 5. 过滤和排序规则
            valid_rules = self._filter_and_rank_rules(rules)
            
            logger.info(f"生成了 {len(valid_rules)} 个有效业务规则")
            return valid_rules
            
        except Exception as e:
            logger.error(f"规则生成失败: {e}")
            return []
    
    def _generate_sentiment_rules(self, df: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """生成情感规则"""
        rules = []
        
        if 'text' not in df.columns or 'sentiment' not in df.columns:
            return rules
        
        try:
            # 按情感分组分析关键词
            for sentiment, group in df.groupby('sentiment'):
                if len(group) < self.min_support:
                    continue
                
                texts = group['text'].fillna('').tolist()
                
                # 提取高频关键词
                keywords = self._extract_frequent_keywords(texts)
                
                for keyword in keywords[:10]:  # 取前10个关键词
                    # 计算规则统计
                    keyword_condition = df['text'].str.contains(keyword, case=False, na=False)
                    sentiment_result = df['sentiment'] == sentiment
                    
                    support = (keyword_condition & sentiment_result).sum()
                    total_keyword = keyword_condition.sum()
                    total_sentiment = sentiment_result.sum()
                    total_samples = len(df)
                    
                    if support >= self.min_support and total_keyword > 0:
                        confidence = support / total_keyword
                        
                        if confidence >= self.min_confidence:
                            # 计算提升度和确信度
                            expected = (total_keyword * total_sentiment) / total_samples
                            lift = support / expected if expected > 0 else 0
                            conviction = (total_keyword * (total_samples - total_sentiment)) / (total_keyword * total_samples - support) if (total_keyword * total_samples - support) > 0 else float('inf')
                            
                            rule = BusinessRuleTemplate(
                                id=f"sentiment_rule_{uuid.uuid4().hex[:8]}",
                                name=f"关键词 '{keyword}' 预测情感 '{sentiment}'",
                                conditions=[
                                    RuleCondition(
                                        field="text",
                                        operator="contains",
                                        value=keyword,
                                        confidence=confidence
                                    )
                                ],
                                consequent=RuleConsequent(
                                    field="sentiment",
                                    value=sentiment,
                                    confidence=confidence
                                ),
                                support=int(support),
                                confidence=confidence,
                                lift=lift,
                                conviction=conviction,
                                created_at=datetime.now()
                            )
                            rules.append(rule)
            
            logger.info(f"生成了 {len(rules)} 个情感规则")
            return rules
            
        except Exception as e:
            logger.error(f"情感规则生成失败: {e}")
            return []
    
    def _generate_keyword_rules(self, df: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """生成关键词规则"""
        rules = []
        
        if 'text' not in df.columns:
            return rules
        
        try:
            # 提取所有文本的关键词
            all_texts = df['text'].fillna('').tolist()
            
            # 使用TF-IDF提取重要关键词
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            feature_names = self.vectorizer.get_feature_names_out()
            
            # 计算每个关键词的平均TF-IDF分数
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
            
            # 获取高分关键词
            top_indices = np.argsort(mean_scores)[::-1][:50]
            top_keywords = [feature_names[i] for i in top_indices if mean_scores[i] > 0.1]
            
            # 为每个目标字段生成关键词规则
            target_fields = ['sentiment', 'rating'] if 'sentiment' in df.columns else ['rating'] if 'rating' in df.columns else []
            
            for target_field in target_fields:
                for keyword in top_keywords:
                    keyword_condition = df['text'].str.contains(keyword, case=False, na=False)
                    keyword_samples = df[keyword_condition]
                    
                    if len(keyword_samples) >= self.min_support:
                        # 找到最常见的目标值
                        if target_field in keyword_samples.columns:
                            target_counts = keyword_samples[target_field].value_counts()
                            if len(target_counts) > 0:
                                most_common_target = target_counts.index[0]
                                support = target_counts.iloc[0]
                                confidence = support / len(keyword_samples)
                                
                                if confidence >= self.min_confidence:
                                    rule = BusinessRuleTemplate(
                                        id=f"keyword_rule_{uuid.uuid4().hex[:8]}",
                                        name=f"关键词 '{keyword}' 预测 {target_field} '{most_common_target}'",
                                        conditions=[
                                            RuleCondition(
                                                field="text",
                                                operator="contains",
                                                value=keyword,
                                                confidence=confidence
                                            )
                                        ],
                                        consequent=RuleConsequent(
                                            field=target_field,
                                            value=most_common_target,
                                            confidence=confidence
                                        ),
                                        support=int(support),
                                        confidence=confidence,
                                        lift=self._calculate_lift(df, keyword_condition, df[target_field] == most_common_target),
                                        conviction=self._calculate_conviction(df, keyword_condition, df[target_field] == most_common_target),
                                        created_at=datetime.now()
                                    )
                                    rules.append(rule)
            
            logger.info(f"生成了 {len(rules)} 个关键词规则")
            return rules
            
        except Exception as e:
            logger.error(f"关键词规则生成失败: {e}")
            return []
    
    def _generate_rating_rules(self, df: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """生成评分规则"""
        rules = []
        
        if 'rating' not in df.columns or 'text' not in df.columns:
            return rules
        
        try:
            # 按评分分组分析
            for rating, group in df.groupby('rating'):
                if len(group) < self.min_support:
                    continue
                
                texts = group['text'].fillna('').tolist()
                keywords = self._extract_frequent_keywords(texts)
                
                for keyword in keywords[:5]:  # 每个评分取前5个关键词
                    keyword_condition = df['text'].str.contains(keyword, case=False, na=False)
                    rating_result = df['rating'] == rating
                    
                    support = (keyword_condition & rating_result).sum()
                    total_keyword = keyword_condition.sum()
                    
                    if support >= self.min_support and total_keyword > 0:
                        confidence = support / total_keyword
                        
                        if confidence >= self.min_confidence:
                            rule = BusinessRuleTemplate(
                                id=f"rating_rule_{uuid.uuid4().hex[:8]}",
                                name=f"关键词 '{keyword}' 预测评分 {rating}",
                                conditions=[
                                    RuleCondition(
                                        field="text",
                                        operator="contains",
                                        value=keyword,
                                        confidence=confidence
                                    )
                                ],
                                consequent=RuleConsequent(
                                    field="rating",
                                    value=rating,
                                    confidence=confidence
                                ),
                                support=int(support),
                                confidence=confidence,
                                lift=self._calculate_lift(df, keyword_condition, rating_result),
                                conviction=self._calculate_conviction(df, keyword_condition, rating_result),
                                created_at=datetime.now()
                            )
                            rules.append(rule)
            
            logger.info(f"生成了 {len(rules)} 个评分规则")
            return rules
            
        except Exception as e:
            logger.error(f"评分规则生成失败: {e}")
            return []
    
    def _generate_combination_rules(self, df: pd.DataFrame) -> List[BusinessRuleTemplate]:
        """生成组合规则"""
        rules = []
        
        try:
            # 生成多条件组合规则
            if 'text' in df.columns and 'sentiment' in df.columns:
                # 文本长度 + 关键词 -> 情感
                df['text_length'] = df['text'].str.len()
                
                # 定义文本长度分组
                length_thresholds = [50, 150, 300]
                
                for threshold in length_thresholds:
                    length_condition = df['text_length'] > threshold
                    
                    if length_condition.sum() >= self.min_support:
                        # 分析长文本的情感分布
                        long_text_sentiments = df[length_condition]['sentiment'].value_counts()
                        
                        if len(long_text_sentiments) > 0:
                            dominant_sentiment = long_text_sentiments.index[0]
                            support = long_text_sentiments.iloc[0]
                            confidence = support / length_condition.sum()
                            
                            if confidence >= self.min_confidence:
                                rule = BusinessRuleTemplate(
                                    id=f"combination_rule_{uuid.uuid4().hex[:8]}",
                                    name=f"文本长度 > {threshold} 字符预测情感 '{dominant_sentiment}'",
                                    conditions=[
                                        RuleCondition(
                                            field="text_length",
                                            operator="greater_than",
                                            value=threshold,
                                            confidence=confidence
                                        )
                                    ],
                                    consequent=RuleConsequent(
                                        field="sentiment",
                                        value=dominant_sentiment,
                                        confidence=confidence
                                    ),
                                    support=int(support),
                                    confidence=confidence,
                                    lift=self._calculate_lift(df, length_condition, df['sentiment'] == dominant_sentiment),
                                    conviction=self._calculate_conviction(df, length_condition, df['sentiment'] == dominant_sentiment),
                                    created_at=datetime.now()
                                )
                                rules.append(rule)
            
            logger.info(f"生成了 {len(rules)} 个组合规则")
            return rules
            
        except Exception as e:
            logger.error(f"组合规则生成失败: {e}")
            return []
    
    def _extract_frequent_keywords(self, texts: List[str]) -> List[str]:
        """提取高频关键词"""
        try:
            # 合并所有文本
            all_text = ' '.join(texts).lower()
            
            # 提取单词
            words = re.findall(r'\b\w+\b', all_text)
            
            # 过滤停用词和短词
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
                'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
            }
            
            filtered_words = [word for word in words if len(word) > 2 and word not in stop_words]
            
            # 统计词频
            word_counts = Counter(filtered_words)
            
            # 返回高频词
            return [word for word, count in word_counts.most_common(20) if count >= 2]
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return []
    
    def _calculate_lift(self, df: pd.DataFrame, condition: pd.Series, result: pd.Series) -> float:
        """计算提升度"""
        try:
            support_both = (condition & result).sum()
            support_condition = condition.sum()
            support_result = result.sum()
            total_samples = len(df)
            
            if support_condition == 0 or support_result == 0:
                return 0.0
            
            expected = (support_condition * support_result) / total_samples
            return support_both / expected if expected > 0 else 0.0
            
        except Exception as e:
            logger.error(f"提升度计算失败: {e}")
            return 0.0
    
    def _calculate_conviction(self, df: pd.DataFrame, condition: pd.Series, result: pd.Series) -> float:
        """计算确信度"""
        try:
            support_condition = condition.sum()
            support_not_result = (~result).sum()
            support_condition_not_result = (condition & ~result).sum()
            total_samples = len(df)
            
            if support_condition_not_result == 0:
                return float('inf')
            
            expected = (support_condition * support_not_result) / total_samples
            return expected / support_condition_not_result if support_condition_not_result > 0 else float('inf')
            
        except Exception as e:
            logger.error(f"确信度计算失败: {e}")
            return 1.0
    
    def _filter_and_rank_rules(self, rules: List[BusinessRuleTemplate]) -> List[BusinessRuleTemplate]:
        """过滤和排序规则"""
        try:
            # 过滤低质量规则
            valid_rules = [
                rule for rule in rules
                if rule.support >= self.min_support and rule.confidence >= self.min_confidence
            ]
            
            # 按综合分数排序
            def rule_score(rule):
                return (
                    rule.confidence * 0.4 +
                    min(rule.lift, 5) / 5 * 0.3 +  # 限制lift的影响
                    rule.support / 100 * 0.2 +  # 支持度标准化
                    min(rule.conviction, 10) / 10 * 0.1  # 限制conviction的影响
                )
            
            valid_rules.sort(key=rule_score, reverse=True)
            
            # 限制返回数量
            return valid_rules[:50]
            
        except Exception as e:
            logger.error(f"规则过滤排序失败: {e}")
            return rules


class EnhancedRuleConflictDetector:
    """增强的规则冲突检测器"""
    
    def __init__(self):
        self.conflict_threshold = 0.1  # 冲突阈值
        self.semantic_threshold = 0.8  # 语义相似度阈值
        
    def detect_comprehensive_conflicts(self, rules: List[BusinessRuleTemplate]) -> Dict[str, Any]:
        """
        检测综合规则冲突
        
        Args:
            rules: 规则列表
            
        Returns:
            Dict: 详细的冲突分析结果
        """
        try:
            logger.info(f"开始检测 {len(rules)} 个规则的综合冲突")
            
            conflict_analysis = {
                "direct_conflicts": {},
                "semantic_conflicts": {},
                "logical_conflicts": {},
                "temporal_conflicts": {},
                "priority_conflicts": {},
                "conflict_summary": {}
            }
            
            # 1. 直接冲突检测
            direct_conflicts = self._detect_direct_conflicts(rules)
            conflict_analysis["direct_conflicts"] = direct_conflicts
            
            # 2. 语义冲突检测
            semantic_conflicts = self._detect_semantic_conflicts(rules)
            conflict_analysis["semantic_conflicts"] = semantic_conflicts
            
            # 3. 逻辑冲突检测
            logical_conflicts = self._detect_logical_conflicts(rules)
            conflict_analysis["logical_conflicts"] = logical_conflicts
            
            # 4. 时序冲突检测
            temporal_conflicts = self._detect_temporal_conflicts(rules)
            conflict_analysis["temporal_conflicts"] = temporal_conflicts
            
            # 5. 优先级冲突检测
            priority_conflicts = self._detect_priority_conflicts(rules)
            conflict_analysis["priority_conflicts"] = priority_conflicts
            
            # 6. 生成冲突摘要
            conflict_summary = self._generate_conflict_summary(conflict_analysis)
            conflict_analysis["conflict_summary"] = conflict_summary
            
            logger.info(f"冲突检测完成，发现 {conflict_summary['total_conflicts']} 个冲突")
            return conflict_analysis
            
        except Exception as e:
            logger.error(f"综合冲突检测失败: {e}")
            return {"error": str(e)}
    
    def _detect_direct_conflicts(self, rules: List[BusinessRuleTemplate]) -> Dict[str, List[Dict[str, Any]]]:
        """检测直接冲突"""
        try:
            conflicts = defaultdict(list)
            
            # 按条件分组规则
            condition_groups = self._group_rules_by_conditions(rules)
            
            # 检测每组内的冲突
            for condition_key, group_rules in condition_groups.items():
                if len(group_rules) > 1:
                    group_conflicts = self._detect_group_conflicts(group_rules)
                    
                    for rule_id, conflict_list in group_conflicts.items():
                        for conflict_rule_id in conflict_list:
                            conflict_info = {
                                "conflicting_rule": conflict_rule_id,
                                "conflict_type": "direct",
                                "severity": "high",
                                "reason": "相同条件但不同结果"
                            }
                            conflicts[rule_id].append(conflict_info)
            
            return dict(conflicts)
            
        except Exception as e:
            logger.error(f"直接冲突检测失败: {e}")
            return {}
    
    def _detect_semantic_conflicts(self, rules: List[BusinessRuleTemplate]) -> Dict[str, List[Dict[str, Any]]]:
        """检测语义冲突"""
        try:
            conflicts = defaultdict(list)
            
            # 计算规则间的语义相似度
            for i, rule1 in enumerate(rules):
                for j, rule2 in enumerate(rules[i+1:], i+1):
                    similarity = self._calculate_semantic_similarity(rule1, rule2)
                    
                    if similarity > self.semantic_threshold:
                        # 检查是否有冲突的结果
                        if (rule1.consequent.field == rule2.consequent.field and
                            rule1.consequent.value != rule2.consequent.value):
                            
                            conflict_info = {
                                "conflicting_rule": rule2.id,
                                "conflict_type": "semantic",
                                "severity": "medium",
                                "similarity_score": round(similarity, 3),
                                "reason": "语义相似但结果不同"
                            }
                            conflicts[rule1.id].append(conflict_info)
                            
                            # 反向冲突
                            conflict_info_reverse = {
                                "conflicting_rule": rule1.id,
                                "conflict_type": "semantic",
                                "severity": "medium",
                                "similarity_score": round(similarity, 3),
                                "reason": "语义相似但结果不同"
                            }
                            conflicts[rule2.id].append(conflict_info_reverse)
            
            return dict(conflicts)
            
        except Exception as e:
            logger.error(f"语义冲突检测失败: {e}")
            return {}
    
    def _calculate_semantic_similarity(self, rule1: BusinessRuleTemplate, rule2: BusinessRuleTemplate) -> float:
        """计算规则间的语义相似度"""
        try:
            # 基于条件字段的相似度
            fields1 = {cond.field for cond in rule1.conditions}
            fields2 = {cond.field for cond in rule2.conditions}
            
            field_similarity = len(fields1 & fields2) / len(fields1 | fields2) if fields1 | fields2 else 0
            
            # 基于条件值的相似度
            values1 = {str(cond.value) for cond in rule1.conditions}
            values2 = {str(cond.value) for cond in rule2.conditions}
            
            value_similarity = len(values1 & values2) / len(values1 | values2) if values1 | values2 else 0
            
            # 综合相似度
            overall_similarity = (field_similarity * 0.6 + value_similarity * 0.4)
            
            return overall_similarity
            
        except Exception as e:
            logger.error(f"语义相似度计算失败: {e}")
            return 0.0
    
    def _detect_logical_conflicts(self, rules: List[BusinessRuleTemplate]) -> Dict[str, List[Dict[str, Any]]]:
        """检测逻辑冲突"""
        try:
            conflicts = defaultdict(list)
            
            # 检测互斥条件
            for i, rule1 in enumerate(rules):
                for j, rule2 in enumerate(rules[i+1:], i+1):
                    if self._have_mutually_exclusive_conditions(rule1, rule2):
                        if rule1.consequent.field == rule2.consequent.field:
                            conflict_info = {
                                "conflicting_rule": rule2.id,
                                "conflict_type": "logical",
                                "severity": "high",
                                "reason": "互斥条件但相同目标字段"
                            }
                            conflicts[rule1.id].append(conflict_info)
                            
                            # 反向冲突
                            conflict_info_reverse = {
                                "conflicting_rule": rule1.id,
                                "conflict_type": "logical",
                                "severity": "high",
                                "reason": "互斥条件但相同目标字段"
                            }
                            conflicts[rule2.id].append(conflict_info_reverse)
            
            return dict(conflicts)
            
        except Exception as e:
            logger.error(f"逻辑冲突检测失败: {e}")
            return {}
    
    def _detect_temporal_conflicts(self, rules: List[BusinessRuleTemplate]) -> Dict[str, List[Dict[str, Any]]]:
        """检测时序冲突"""
        try:
            conflicts = defaultdict(list)
            
            # 找到时序规则
            temporal_rules = [rule for rule in rules if rule.rule_type == "temporal"]
            
            # 检测时序冲突
            for i, rule1 in enumerate(temporal_rules):
                for j, rule2 in enumerate(temporal_rules[i+1:], i+1):
                    # 检查是否有时间重叠但结果不同
                    if self._have_temporal_overlap(rule1, rule2):
                        if (rule1.consequent.field == rule2.consequent.field and
                            rule1.consequent.value != rule2.consequent.value):
                            
                            conflict_info = {
                                "conflicting_rule": rule2.id,
                                "conflict_type": "temporal",
                                "severity": "medium",
                                "reason": "时间重叠但结果不同"
                            }
                            conflicts[rule1.id].append(conflict_info)
            
            return dict(conflicts)
            
        except Exception as e:
            logger.error(f"时序冲突检测失败: {e}")
            return {}
    
    def _have_temporal_overlap(self, rule1: BusinessRuleTemplate, rule2: BusinessRuleTemplate) -> bool:
        """检查两个规则是否有时间重叠"""
        try:
            # 简化的时间重叠检测
            time_fields = ['hour', 'day_of_week', 'created_at']
            
            for field in time_fields:
                conditions1 = [c for c in rule1.conditions if c.field == field]
                conditions2 = [c for c in rule2.conditions if c.field == field]
                
                if conditions1 and conditions2:
                    # 检查值是否有重叠
                    values1 = {c.value for c in conditions1}
                    values2 = {c.value for c in conditions2}
                    
                    if values1 & values2:  # 有交集
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"时间重叠检测失败: {e}")
            return False
    
    def _detect_priority_conflicts(self, rules: List[BusinessRuleTemplate]) -> Dict[str, List[Dict[str, Any]]]:
        """检测优先级冲突"""
        try:
            conflicts = defaultdict(list)
            
            # 按业务影响分组
            high_impact_rules = [r for r in rules if r.business_impact == "high"]
            medium_impact_rules = [r for r in rules if r.business_impact == "medium"]
            
            # 检测高影响规则与中等影响规则的冲突
            for high_rule in high_impact_rules:
                for medium_rule in medium_impact_rules:
                    if self._rules_have_overlapping_scope(high_rule, medium_rule):
                        if (high_rule.consequent.field == medium_rule.consequent.field and
                            high_rule.consequent.value != medium_rule.consequent.value):
                            
                            conflict_info = {
                                "conflicting_rule": medium_rule.id,
                                "conflict_type": "priority",
                                "severity": "low",
                                "reason": "高优先级规则与中等优先级规则冲突"
                            }
                            conflicts[high_rule.id].append(conflict_info)
            
            return dict(conflicts)
            
        except Exception as e:
            logger.error(f"优先级冲突检测失败: {e}")
            return {}
    
    def _rules_have_overlapping_scope(self, rule1: BusinessRuleTemplate, rule2: BusinessRuleTemplate) -> bool:
        """检查两个规则是否有重叠的适用范围"""
        try:
            # 检查条件字段的重叠
            fields1 = {c.field for c in rule1.conditions}
            fields2 = {c.field for c in rule2.conditions}
            
            # 如果有共同的条件字段，认为有重叠
            return len(fields1 & fields2) > 0
            
        except Exception as e:
            logger.error(f"规则范围重叠检测失败: {e}")
            return False
    
    def _generate_conflict_summary(self, conflict_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成冲突摘要"""
        try:
            summary = {
                "total_conflicts": 0,
                "conflict_types": {},
                "severity_distribution": {"high": 0, "medium": 0, "low": 0},
                "most_conflicted_rules": [],
                "conflict_resolution_suggestions": []
            }
            
            # 统计冲突
            all_conflicts = {}
            
            for conflict_type, conflicts in conflict_analysis.items():
                if conflict_type == "conflict_summary":
                    continue
                
                if isinstance(conflicts, dict):
                    summary["conflict_types"][conflict_type] = len(conflicts)
                    
                    for rule_id, rule_conflicts in conflicts.items():
                        if rule_id not in all_conflicts:
                            all_conflicts[rule_id] = []
                        all_conflicts[rule_id].extend(rule_conflicts)
            
            # 计算总冲突数
            summary["total_conflicts"] = sum(len(conflicts) for conflicts in all_conflicts.values())
            
            # 统计严重程度
            for rule_conflicts in all_conflicts.values():
                for conflict in rule_conflicts:
                    severity = conflict.get("severity", "medium")
                    summary["severity_distribution"][severity] += 1
            
            # 找到最多冲突的规则
            if all_conflicts:
                conflict_counts = [(rule_id, len(conflicts)) for rule_id, conflicts in all_conflicts.items()]
                conflict_counts.sort(key=lambda x: x[1], reverse=True)
                summary["most_conflicted_rules"] = conflict_counts[:5]
            
            # 生成解决建议
            summary["conflict_resolution_suggestions"] = self._generate_resolution_suggestions(summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"冲突摘要生成失败: {e}")
            return {"error": str(e)}
    
    def _generate_resolution_suggestions(self, summary: Dict[str, Any]) -> List[str]:
        """生成冲突解决建议"""
        suggestions = []
        
        try:
            total_conflicts = summary["total_conflicts"]
            severity_dist = summary["severity_distribution"]
            
            if total_conflicts == 0:
                suggestions.append("没有检测到规则冲突，系统运行良好")
                return suggestions
            
            if severity_dist["high"] > 0:
                suggestions.append(f"发现 {severity_dist['high']} 个高严重性冲突，建议优先解决")
                suggestions.append("对于直接冲突，考虑合并相似规则或调整条件")
            
            if severity_dist["medium"] > 0:
                suggestions.append(f"发现 {severity_dist['medium']} 个中等严重性冲突，建议审查规则逻辑")
                suggestions.append("对于语义冲突，考虑重新定义规则范围")
            
            if len(summary["most_conflicted_rules"]) > 0:
                most_conflicted = summary["most_conflicted_rules"][0]
                suggestions.append(f"规则 {most_conflicted[0]} 冲突最多({most_conflicted[1]}个)，建议重点审查")
            
            suggestions.append("建议定期运行冲突检测以维护规则质量")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"解决建议生成失败: {e}")
            return ["建议人工审查规则冲突"]
    
    # 继承原有的辅助方法
    def _group_rules_by_conditions(self, rules: List[BusinessRuleTemplate]) -> Dict[str, List[BusinessRuleTemplate]]:
        """按条件分组规则"""
        groups = defaultdict(list)
        
        for rule in rules:
            condition_key = self._create_condition_key(rule.conditions)
            groups[condition_key].append(rule)
        
        return groups
    
    def _create_condition_key(self, conditions: List[RuleCondition]) -> str:
        """创建条件键"""
        condition_parts = []
        for condition in conditions:
            part = f"{condition.field}_{condition.operator}_{condition.value}"
            condition_parts.append(part)
        
        return "|".join(sorted(condition_parts))
    
    def _detect_group_conflicts(self, group_rules: List[BusinessRuleTemplate]) -> Dict[str, List[str]]:
        """检测组内冲突"""
        conflicts = defaultdict(list)
        
        for i, rule1 in enumerate(group_rules):
            for j, rule2 in enumerate(group_rules[i+1:], i+1):
                if self._are_rules_conflicting(rule1, rule2):
                    conflicts[rule1.id].append(rule2.id)
                    conflicts[rule2.id].append(rule1.id)
        
        return conflicts
    
    def _are_rules_conflicting(self, rule1: BusinessRuleTemplate, rule2: BusinessRuleTemplate) -> bool:
        """判断两个规则是否冲突"""
        if (rule1.consequent.field == rule2.consequent.field and
            rule1.consequent.value != rule2.consequent.value):
            
            confidence_diff = abs(rule1.confidence - rule2.confidence)
            if confidence_diff < self.conflict_threshold:
                return True
        
        return False
    
    def _have_mutually_exclusive_conditions(self, rule1: BusinessRuleTemplate, rule2: BusinessRuleTemplate) -> bool:
        """检查是否有互斥条件"""
        for cond1 in rule1.conditions:
            for cond2 in rule2.conditions:
                if (cond1.field == cond2.field and
                    self._are_conditions_mutually_exclusive(cond1, cond2)):
                    return True
        
        return False
    
    def _are_conditions_mutually_exclusive(self, cond1: RuleCondition, cond2: RuleCondition) -> bool:
        """判断两个条件是否互斥"""
        if (cond1.operator == "greater_than" and cond2.operator == "less_than" and
            cond1.value >= cond2.value):
            return True
        
        if (cond1.operator == "less_than" and cond2.operator == "greater_than" and
            cond1.value <= cond2.value):
            return True
        
        if (cond1.operator == "equals" and cond2.operator == "equals" and
            cond1.value != cond2.value):
            return True
        
        return False


class IntelligentRuleOptimizer:
    """智能规则优化器"""
    
    def __init__(self):
        self.merge_threshold = 0.8  # 合并相似度阈值
        self.optimization_strategies = [
            "merge_similar_rules",
            "remove_redundant_rules", 
            "optimize_conditions",
            "resolve_conflicts",
            "enhance_rule_quality"
        ]
        
    def optimize_rule_set(self, rules: List[BusinessRuleTemplate]) -> Dict[str, Any]:
        """
        优化规则集合
        
        Args:
            rules: 原始规则列表
            
        Returns:
            Dict: 优化结果和统计信息
        """
        try:
            logger.info(f"开始智能优化 {len(rules)} 个规则")
            
            optimization_result = {
                "original_rules": len(rules),
                "optimization_steps": [],
                "final_rules": [],
                "optimization_summary": {},
                "quality_improvements": {}
            }
            
            current_rules = rules.copy()
            
            # 执行优化策略
            for strategy in self.optimization_strategies:
                step_result = self._execute_optimization_strategy(strategy, current_rules)
                
                optimization_result["optimization_steps"].append({
                    "strategy": strategy,
                    "before_count": len(current_rules),
                    "after_count": len(step_result["optimized_rules"]),
                    "improvements": step_result["improvements"]
                })
                
                current_rules = step_result["optimized_rules"]
            
            optimization_result["final_rules"] = current_rules
            optimization_result["optimization_summary"] = self._generate_optimization_summary(
                rules, current_rules, optimization_result["optimization_steps"]
            )
            
            logger.info(f"规则优化完成，从 {len(rules)} 个规则优化为 {len(current_rules)} 个规则")
            return optimization_result
            
        except Exception as e:
            logger.error(f"智能规则优化失败: {e}")
            return {"error": str(e), "final_rules": rules}
    
    def _execute_optimization_strategy(self, strategy: str, rules: List[BusinessRuleTemplate]) -> Dict[str, Any]:
        """执行优化策略"""
        try:
            if strategy == "merge_similar_rules":
                return self._merge_similar_rules_enhanced(rules)
            elif strategy == "remove_redundant_rules":
                return self._remove_redundant_rules_enhanced(rules)
            elif strategy == "optimize_conditions":
                return self._optimize_rule_conditions_enhanced(rules)
            elif strategy == "resolve_conflicts":
                return self._resolve_rule_conflicts(rules)
            elif strategy == "enhance_rule_quality":
                return self._enhance_rule_quality(rules)
            else:
                return {"optimized_rules": rules, "improvements": []}
                
        except Exception as e:
            logger.error(f"优化策略 {strategy} 执行失败: {e}")
            return {"optimized_rules": rules, "improvements": []}
    
    def _merge_similar_rules_enhanced(self, rules: List[BusinessRuleTemplate]) -> Dict[str, Any]:
        """增强的相似规则合并"""
        try:
            merged_rules = []
            used_rules = set()
            improvements = []
            
            for i, rule1 in enumerate(rules):
                if rule1.id in used_rules:
                    continue
                
                similar_rules = [rule1]
                used_rules.add(rule1.id)
                
                # 找到相似规则
                for j, rule2 in enumerate(rules[i+1:], i+1):
                    if rule2.id in used_rules:
                        continue
                    
                    similarity = self._calculate_rule_similarity_enhanced(rule1, rule2)
                    
                    if similarity >= self.merge_threshold:
                        similar_rules.append(rule2)
                        used_rules.add(rule2.id)
                
                # 合并相似规则
                if len(similar_rules) > 1:
                    merged_rule = self._merge_rule_group_enhanced(similar_rules)
                    merged_rules.append(merged_rule)
                    
                    improvements.append(f"合并了 {len(similar_rules)} 个相似规则")
                else:
                    merged_rules.append(rule1)
            
            return {
                "optimized_rules": merged_rules,
                "improvements": improvements
            }
            
        except Exception as e:
            logger.error(f"增强规则合并失败: {e}")
            return {"optimized_rules": rules, "improvements": []}
    
    def _calculate_rule_similarity_enhanced(self, rule1: BusinessRuleTemplate, rule2: BusinessRuleTemplate) -> float:
        """计算增强的规则相似度"""
        try:
            # 1. 条件相似度
            condition_similarity = self._calculate_condition_similarity_enhanced(rule1.conditions, rule2.conditions)
            
            # 2. 结果相似度
            result_similarity = 1.0 if (rule1.consequent.field == rule2.consequent.field and 
                                      rule1.consequent.value == rule2.consequent.value) else 0.0
            
            # 3. 规则类型相似度
            type_similarity = 1.0 if rule1.rule_type == rule2.rule_type else 0.5
            
            # 4. 业务影响相似度
            impact_similarity = 1.0 if rule1.business_impact == rule2.business_impact else 0.7
            
            # 5. 统计指标相似度
            confidence_diff = abs(rule1.confidence - rule2.confidence)
            confidence_similarity = max(0, 1.0 - confidence_diff)
            
            # 综合相似度
            overall_similarity = (
                condition_similarity * 0.4 +
                result_similarity * 0.3 +
                type_similarity * 0.1 +
                impact_similarity * 0.1 +
                confidence_similarity * 0.1
            )
            
            return overall_similarity
            
        except Exception as e:
            logger.error(f"增强相似度计算失败: {e}")
            return 0.0
    
    def _calculate_condition_similarity_enhanced(self, conditions1: List[RuleCondition], conditions2: List[RuleCondition]) -> float:
        """计算增强的条件相似度"""
        try:
            if not conditions1 or not conditions2:
                return 0.0
            
            # 字段相似度
            fields1 = {cond.field for cond in conditions1}
            fields2 = {cond.field for cond in conditions2}
            field_similarity = len(fields1 & fields2) / len(fields1 | fields2)
            
            # 操作符相似度
            operators1 = {cond.operator for cond in conditions1}
            operators2 = {cond.operator for cond in conditions2}
            operator_similarity = len(operators1 & operators2) / len(operators1 | operators2)
            
            # 值相似度
            values1 = {str(cond.value) for cond in conditions1}
            values2 = {str(cond.value) for cond in conditions2}
            value_similarity = len(values1 & values2) / len(values1 | values2)
            
            # 综合条件相似度
            condition_similarity = (field_similarity * 0.5 + operator_similarity * 0.3 + value_similarity * 0.2)
            
            return condition_similarity
            
        except Exception as e:
            logger.error(f"增强条件相似度计算失败: {e}")
            return 0.0
    
    def _merge_rule_group_enhanced(self, similar_rules: List[BusinessRuleTemplate]) -> BusinessRuleTemplate:
        """增强的规则组合并"""
        try:
            # 选择最佳基础规则 (综合评分最高)
            base_rule = max(similar_rules, key=lambda r: r.validation_score if hasattr(r, 'validation_score') else r.confidence)
            
            # 合并统计信息
            total_support = sum(rule.support for rule in similar_rules)
            avg_confidence = np.mean([rule.confidence for rule in similar_rules])
            max_lift = max(rule.lift for rule in similar_rules)
            
            # 合并条件 (去重并优化)
            merged_conditions = self._merge_conditions_intelligently(similar_rules)
            
            # 创建合并后的规则
            merged_rule = BusinessRuleTemplate(
                id=f"merged_rule_{uuid.uuid4().hex[:8]}",
                name=f"合并规则: {base_rule.name} (+{len(similar_rules)-1}个)",
                description=f"由 {len(similar_rules)} 个相似规则合并而成",
                conditions=merged_conditions,
                consequent=base_rule.consequent,
                rule_type=base_rule.rule_type,
                support=total_support,
                confidence=avg_confidence,
                lift=max_lift,
                conviction=base_rule.conviction,
                business_impact=base_rule.business_impact,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            return merged_rule
            
        except Exception as e:
            logger.error(f"增强规则组合并失败: {e}")
            return similar_rules[0]  # 返回第一个规则作为备选
    
    def _merge_conditions_intelligently(self, rules: List[BusinessRuleTemplate]) -> List[RuleCondition]:
        """智能合并条件"""
        try:
            # 收集所有条件
            all_conditions = []
            for rule in rules:
                all_conditions.extend(rule.conditions)
            
            # 按字段分组条件
            field_conditions = defaultdict(list)
            for condition in all_conditions:
                field_conditions[condition.field].append(condition)
            
            # 为每个字段选择最佳条件
            merged_conditions = []
            for field, conditions in field_conditions.items():
                if len(conditions) == 1:
                    merged_conditions.append(conditions[0])
                else:
                    # 选择置信度最高的条件
                    best_condition = max(conditions, key=lambda c: c.confidence)
                    merged_conditions.append(best_condition)
            
            return merged_conditions
            
        except Exception as e:
            logger.error(f"智能条件合并失败: {e}")
            return []
    
    def _remove_redundant_rules_enhanced(self, rules: List[BusinessRuleTemplate]) -> Dict[str, Any]:
        """增强的冗余规则移除"""
        try:
            # 按质量评分排序
            sorted_rules = sorted(rules, key=lambda r: (
                getattr(r, 'validation_score', 0) * 0.5 + 
                r.confidence * 0.3 + 
                min(r.support, 50) / 50 * 0.2
            ), reverse=True)
            
            non_redundant_rules = []
            improvements = []
            
            for rule in sorted_rules:
                is_redundant = False
                
                # 检查是否被已有规则覆盖
                for existing_rule in non_redundant_rules:
                    if self._is_rule_redundant_enhanced(rule, existing_rule):
                        is_redundant = True
                        improvements.append(f"移除冗余规则: {rule.name}")
                        break
                
                if not is_redundant:
                    non_redundant_rules.append(rule)
            
            return {
                "optimized_rules": non_redundant_rules,
                "improvements": improvements
            }
            
        except Exception as e:
            logger.error(f"增强冗余规则移除失败: {e}")
            return {"optimized_rules": rules, "improvements": []}
    
    def _is_rule_redundant_enhanced(self, rule: BusinessRuleTemplate, existing_rule: BusinessRuleTemplate) -> bool:
        """增强的冗余规则判断"""
        try:
            # 1. 相同结果
            if not (rule.consequent.field == existing_rule.consequent.field and
                   rule.consequent.value == existing_rule.consequent.value):
                return False
            
            # 2. 条件包含关系
            if not self._conditions_subset_enhanced(rule.conditions, existing_rule.conditions):
                return False
            
            # 3. 质量比较
            rule_quality = getattr(rule, 'validation_score', rule.confidence)
            existing_quality = getattr(existing_rule, 'validation_score', existing_rule.confidence)
            
            # 如果现有规则质量更高，则当前规则冗余
            if existing_quality >= rule_quality:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"增强冗余判断失败: {e}")
            return False
    
    def _conditions_subset_enhanced(self, conditions1: List[RuleCondition], conditions2: List[RuleCondition]) -> bool:
        """增强的条件子集判断"""
        try:
            # 检查条件1是否是条件2的子集或等价
            for cond1 in conditions1:
                found_equivalent = False
                
                for cond2 in conditions2:
                    if self._conditions_equivalent(cond1, cond2):
                        found_equivalent = True
                        break
                
                if not found_equivalent:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"增强条件子集判断失败: {e}")
            return False
    
    def _conditions_equivalent(self, cond1: RuleCondition, cond2: RuleCondition) -> bool:
        """判断两个条件是否等价"""
        return (cond1.field == cond2.field and
                cond1.operator == cond2.operator and
                cond1.value == cond2.value)
    
    def _optimize_rule_conditions_enhanced(self, rules: List[BusinessRuleTemplate]) -> Dict[str, Any]:
        """增强的规则条件优化"""
        try:
            optimized_rules = []
            improvements = []
            
            for rule in rules:
                # 优化条件
                optimized_conditions = self._optimize_conditions_for_rule(rule.conditions)
                
                if len(optimized_conditions) < len(rule.conditions):
                    improvements.append(f"简化规则 {rule.name} 的条件")
                
                # 创建优化后的规则
                optimized_rule = BusinessRuleTemplate(
                    id=rule.id,
                    name=rule.name,
                    description=rule.description,
                    conditions=optimized_conditions,
                    consequent=rule.consequent,
                    rule_type=rule.rule_type,
                    support=rule.support,
                    confidence=rule.confidence,
                    lift=rule.lift,
                    conviction=rule.conviction,
                    business_impact=rule.business_impact,
                    created_at=rule.created_at,
                    updated_at=datetime.now()
                )
                
                optimized_rules.append(optimized_rule)
            
            return {
                "optimized_rules": optimized_rules,
                "improvements": improvements
            }
            
        except Exception as e:
            logger.error(f"增强条件优化失败: {e}")
            return {"optimized_rules": rules, "improvements": []}
    
    def _optimize_conditions_for_rule(self, conditions: List[RuleCondition]) -> List[RuleCondition]:
        """为单个规则优化条件"""
        try:
            # 1. 移除低置信度条件
            high_confidence_conditions = [
                cond for cond in conditions
                if cond.confidence >= 0.5
            ]
            
            # 2. 移除重复条件
            unique_conditions = []
            seen_conditions = set()
            
            for condition in high_confidence_conditions:
                condition_key = f"{condition.field}_{condition.operator}_{condition.value}"
                if condition_key not in seen_conditions:
                    unique_conditions.append(condition)
                    seen_conditions.add(condition_key)
            
            # 3. 如果所有条件都被移除，保留原始条件
            if not unique_conditions:
                return conditions
            
            return unique_conditions
            
        except Exception as e:
            logger.error(f"单规则条件优化失败: {e}")
            return conditions
    
    def _resolve_rule_conflicts(self, rules: List[BusinessRuleTemplate]) -> Dict[str, Any]:
        """解决规则冲突"""
        try:
            # 使用冲突检测器
            conflict_detector = EnhancedRuleConflictDetector()
            conflict_analysis = conflict_detector.detect_comprehensive_conflicts(rules)
            
            resolved_rules = []
            improvements = []
            
            # 创建冲突映射
            all_conflicts = {}
            for conflict_type, conflicts in conflict_analysis.items():
                if conflict_type == "conflict_summary":
                    continue
                if isinstance(conflicts, dict):
                    for rule_id, rule_conflicts in conflicts.items():
                        if rule_id not in all_conflicts:
                            all_conflicts[rule_id] = []
                        all_conflicts[rule_id].extend(rule_conflicts)
            
            # 处理每个规则
            for rule in rules:
                if rule.id in all_conflicts:
                    # 有冲突的规则，尝试解决
                    resolved_rule = self._resolve_single_rule_conflicts(rule, all_conflicts[rule.id], rules)
                    resolved_rules.append(resolved_rule)
                    
                    if resolved_rule.id != rule.id:  # 规则被修改
                        improvements.append(f"解决规则 {rule.name} 的冲突")
                else:
                    # 无冲突的规则直接保留
                    resolved_rules.append(rule)
            
            return {
                "optimized_rules": resolved_rules,
                "improvements": improvements
            }
            
        except Exception as e:
            logger.error(f"规则冲突解决失败: {e}")
            return {"optimized_rules": rules, "improvements": []}
    
    def _resolve_single_rule_conflicts(self, rule: BusinessRuleTemplate, conflicts: List[Dict[str, Any]], all_rules: List[BusinessRuleTemplate]) -> BusinessRuleTemplate:
        """解决单个规则的冲突"""
        try:
            # 简单的冲突解决策略：调整条件权重
            adjusted_conditions = []
            
            for condition in rule.conditions:
                # 降低有冲突条件的权重
                adjusted_condition = RuleCondition(
                    field=condition.field,
                    operator=condition.operator,
                    value=condition.value,
                    confidence=condition.confidence * 0.9,  # 降低置信度
                    weight=getattr(condition, 'weight', 1.0) * 0.9  # 降低权重
                )
                adjusted_conditions.append(adjusted_condition)
            
            # 创建调整后的规则
            resolved_rule = BusinessRuleTemplate(
                id=f"resolved_{rule.id}",
                name=f"已解决冲突: {rule.name}",
                description=f"{rule.description} (已调整以解决冲突)",
                conditions=adjusted_conditions,
                consequent=rule.consequent,
                rule_type=rule.rule_type,
                support=rule.support,
                confidence=rule.confidence * 0.95,  # 略微降低整体置信度
                lift=rule.lift,
                conviction=rule.conviction,
                business_impact=rule.business_impact,
                created_at=rule.created_at,
                updated_at=datetime.now()
            )
            
            return resolved_rule
            
        except Exception as e:
            logger.error(f"单规则冲突解决失败: {e}")
            return rule
    
    def _enhance_rule_quality(self, rules: List[BusinessRuleTemplate]) -> Dict[str, Any]:
        """提升规则质量"""
        try:
            enhanced_rules = []
            improvements = []
            
            for rule in rules:
                enhanced_rule = self._enhance_single_rule_quality(rule)
                enhanced_rules.append(enhanced_rule)
                
                if enhanced_rule.validation_score > getattr(rule, 'validation_score', 0):
                    improvements.append(f"提升规则 {rule.name} 的质量评分")
            
            return {
                "optimized_rules": enhanced_rules,
                "improvements": improvements
            }
            
        except Exception as e:
            logger.error(f"规则质量提升失败: {e}")
            return {"optimized_rules": rules, "improvements": []}
    
    def _enhance_single_rule_quality(self, rule: BusinessRuleTemplate) -> BusinessRuleTemplate:
        """提升单个规则的质量"""
        try:
            # 重新计算质量评分
            quality_score = self._calculate_enhanced_quality_score(rule)
            
            # 优化描述
            enhanced_description = self._generate_enhanced_description(rule)
            
            # 创建增强后的规则
            enhanced_rule = BusinessRuleTemplate(
                id=rule.id,
                name=rule.name,
                description=enhanced_description,
                conditions=rule.conditions,
                consequent=rule.consequent,
                rule_type=rule.rule_type,
                support=rule.support,
                confidence=rule.confidence,
                lift=rule.lift,
                conviction=rule.conviction,
                business_impact=rule.business_impact,
                created_at=rule.created_at,
                updated_at=datetime.now(),
                validation_score=quality_score
            )
            
            return enhanced_rule
            
        except Exception as e:
            logger.error(f"单规则质量提升失败: {e}")
            return rule
    
    def _calculate_enhanced_quality_score(self, rule: BusinessRuleTemplate) -> float:
        """计算增强的质量评分"""
        try:
            # 基础评分
            base_score = (
                rule.confidence * 0.3 +
                min(rule.lift, 5) / 5 * 0.2 +
                min(rule.support, 100) / 100 * 0.2 +
                min(rule.conviction, 10) / 10 * 0.1
            )
            
            # 规则类型加权
            type_weights = {
                "classification": 1.2,
                "association": 1.0,
                "temporal": 1.1,
                "pattern": 1.15,
                "sequential": 0.9,
                "anomaly": 1.25
            }
            
            type_weight = type_weights.get(rule.rule_type, 1.0)
            
            # 业务影响加权
            impact_weights = {"high": 1.3, "medium": 1.0, "low": 0.8}
            impact_weight = impact_weights.get(rule.business_impact, 1.0)
            
            # 条件质量评分
            condition_quality = self._assess_condition_quality(rule.conditions)
            
            # 综合评分
            final_score = base_score * type_weight * impact_weight * condition_quality
            
            return round(min(final_score, 1.0), 3)  # 限制在0-1范围内
            
        except Exception as e:
            logger.error(f"增强质量评分计算失败: {e}")
            return 0.5
    
    def _assess_condition_quality(self, conditions: List[RuleCondition]) -> float:
        """评估条件质量"""
        try:
            if not conditions:
                return 0.5
            
            # 条件数量评分 (适中的条件数量更好)
            count_score = max(0.5, 1.0 - abs(len(conditions) - 2) * 0.1)
            
            # 条件置信度评分
            confidence_scores = [cond.confidence for cond in conditions]
            avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.5
            
            # 条件多样性评分 (不同字段的条件更好)
            unique_fields = len(set(cond.field for cond in conditions))
            diversity_score = min(1.0, unique_fields / len(conditions))
            
            # 综合条件质量
            condition_quality = (count_score * 0.3 + avg_confidence * 0.5 + diversity_score * 0.2)
            
            return condition_quality
            
        except Exception as e:
            logger.error(f"条件质量评估失败: {e}")
            return 0.5
    
    def _generate_enhanced_description(self, rule: BusinessRuleTemplate) -> str:
        """生成增强的规则描述"""
        try:
            # 基础描述
            base_desc = rule.description or rule.name
            
            # 添加统计信息
            stats_desc = f" (置信度: {rule.confidence:.2f}, 支持度: {rule.support})"
            
            # 添加业务影响
            impact_desc = f", 业务影响: {rule.business_impact}"
            
            # 添加规则类型
            type_desc = f", 类型: {rule.rule_type}"
            
            enhanced_desc = base_desc + stats_desc + impact_desc + type_desc
            
            return enhanced_desc
            
        except Exception as e:
            logger.error(f"增强描述生成失败: {e}")
            return rule.description or rule.name
    
    def _generate_optimization_summary(self, original_rules: List[BusinessRuleTemplate], 
                                     final_rules: List[BusinessRuleTemplate], 
                                     optimization_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成优化摘要"""
        try:
            summary = {
                "original_count": len(original_rules),
                "final_count": len(final_rules),
                "reduction_rate": (len(original_rules) - len(final_rules)) / len(original_rules) if original_rules else 0,
                "optimization_steps_count": len(optimization_steps),
                "total_improvements": sum(len(step["improvements"]) for step in optimization_steps),
                "quality_improvement": self._calculate_quality_improvement(original_rules, final_rules),
                "recommendations": self._generate_optimization_recommendations(optimization_steps)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"优化摘要生成失败: {e}")
            return {"error": str(e)}
    
    def _calculate_quality_improvement(self, original_rules: List[BusinessRuleTemplate], 
                                     final_rules: List[BusinessRuleTemplate]) -> float:
        """计算质量改进"""
        try:
            if not original_rules or not final_rules:
                return 0.0
            
            # 计算平均置信度改进
            original_avg_confidence = np.mean([rule.confidence for rule in original_rules])
            final_avg_confidence = np.mean([rule.confidence for rule in final_rules])
            
            confidence_improvement = final_avg_confidence - original_avg_confidence
            
            return round(confidence_improvement, 3)
            
        except Exception as e:
            logger.error(f"质量改进计算失败: {e}")
            return 0.0
    
    def _generate_optimization_recommendations(self, optimization_steps: List[Dict[str, Any]]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        try:
            total_reductions = sum(step["before_count"] - step["after_count"] for step in optimization_steps)
            
            if total_reductions > 0:
                recommendations.append(f"成功减少了 {total_reductions} 个冗余或低质量规则")
            
            # 分析各步骤的效果
            for step in optimization_steps:
                reduction = step["before_count"] - step["after_count"]
                if reduction > 0:
                    recommendations.append(f"{step['strategy']} 步骤减少了 {reduction} 个规则")
            
            recommendations.append("建议定期运行规则优化以维护规则质量")
            recommendations.append("建议监控优化后规则的实际效果")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"优化建议生成失败: {e}")
            return ["建议人工审查优化结果"]
        for cond1 in conditions1:
            found = False
            for cond2 in conditions2:
                if (cond1.field == cond2.field and
                    cond1.operator == cond2.operator and
                    cond1.value == cond2.value):
                    found = True
                    break
            if not found:
                return False
        return True
    
    def _optimize_rule_conditions(self, rules: List[BusinessRuleTemplate]) -> List[BusinessRuleTemplate]:
        """优化规则条件"""
        optimized_rules = []
        
        for rule in rules:
            # 简化条件
            simplified_conditions = self._simplify_conditions(rule.conditions)
            
            # 创建优化后的规则
            optimized_rule = BusinessRuleTemplate(
                id=rule.id,
                name=rule.name,
                conditions=simplified_conditions,
                consequent=rule.consequent,
                support=rule.support,
                confidence=rule.confidence,
                lift=rule.lift,
                conviction=rule.conviction,
                created_at=rule.created_at
            )
            
            optimized_rules.append(optimized_rule)
        
        return optimized_rules
    
    def _simplify_conditions(self, conditions: List[RuleCondition]) -> List[RuleCondition]:
        """简化条件"""
        # 移除低置信度条件
        high_confidence_conditions = [
            cond for cond in conditions
            if cond.confidence >= 0.5
        ]
        
        return high_confidence_conditions if high_confidence_conditions else conditions
    
    def _recalculate_statistics(self, rules: List[BusinessRuleTemplate]) -> List[BusinessRuleTemplate]:
        """重新计算统计指标"""
        # 这里可以基于新的条件重新计算支持度、置信度等
        # 为简化，暂时保持原有统计信息
        return rules


class RuleValidationEngine:
    """规则验证引擎"""
    
    def __init__(self):
        self.validation_threshold = 0.7
        
    def validate_rules(self, rules: List[BusinessRuleTemplate], test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证规则有效性
        
        Args:
            rules: 待验证的规则列表
            test_data: 测试数据
            
        Returns:
            Dict: 验证结果
        """
        try:
            logger.info(f"开始验证 {len(rules)} 个规则")
            
            df_test = pd.DataFrame(test_data)
            validation_results = []
            
            for rule in rules:
                result = self._validate_single_rule(rule, df_test)
                validation_results.append(result)
            
            # 计算整体统计
            valid_rules = [r for r in validation_results if r["is_valid"]]
            
            summary = {
                "total_rules": len(rules),
                "valid_rules": len(valid_rules),
                "validation_rate": len(valid_rules) / len(rules) if rules else 0,
                "average_accuracy": np.mean([r["accuracy"] for r in validation_results]),
                "average_precision": np.mean([r["precision"] for r in validation_results]),
                "average_recall": np.mean([r["recall"] for r in validation_results]),
                "rule_details": validation_results
            }
            
            logger.info(f"规则验证完成，{len(valid_rules)}/{len(rules)} 个规则有效")
            return summary
            
        except Exception as e:
            logger.error(f"规则验证失败: {e}")
            return {"error": str(e)}
    
    def _validate_single_rule(self, rule: BusinessRuleTemplate, df_test: pd.DataFrame) -> Dict[str, Any]:
        """验证单个规则"""
        try:
            # 应用规则条件
            condition_mask = self._apply_rule_conditions(rule.conditions, df_test)
            
            if condition_mask.sum() == 0:
                return {
                    "rule_id": rule.id,
                    "is_valid": False,
                    "accuracy": 0.0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "error": "没有样本满足条件"
                }
            
            # 获取预测和真实值
            predicted = np.zeros(len(df_test))
            predicted[condition_mask] = 1
            
            if rule.consequent.field in df_test.columns:
                actual = (df_test[rule.consequent.field] == rule.consequent.value).astype(int)
                
                # 计算指标
                accuracy = accuracy_score(actual, predicted)
                precision = precision_score(actual, predicted, zero_division=0)
                recall = recall_score(actual, predicted, zero_division=0)
                
                is_valid = accuracy >= self.validation_threshold
                
                return {
                    "rule_id": rule.id,
                    "is_valid": is_valid,
                    "accuracy": round(accuracy, 3),
                    "precision": round(precision, 3),
                    "recall": round(recall, 3),
                    "samples_matched": int(condition_mask.sum())
                }
            else:
                return {
                    "rule_id": rule.id,
                    "is_valid": False,
                    "accuracy": 0.0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "error": f"目标字段 {rule.consequent.field} 不存在"
                }
                
        except Exception as e:
            return {
                "rule_id": rule.id,
                "is_valid": False,
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "error": str(e)
            }
    
    def _apply_rule_conditions(self, conditions: List[RuleCondition], df: pd.DataFrame) -> pd.Series:
        """应用规则条件"""
        mask = pd.Series([True] * len(df))
        
        for condition in conditions:
            if condition.field not in df.columns:
                continue
            
            if condition.operator == "contains":
                condition_mask = df[condition.field].str.contains(str(condition.value), case=False, na=False)
            elif condition.operator == "equals":
                condition_mask = df[condition.field] == condition.value
            elif condition.operator == "greater_than":
                condition_mask = df[condition.field] > condition.value
            elif condition.operator == "less_than":
                condition_mask = df[condition.field] < condition.value
            else:
                continue
            
            mask = mask & condition_mask
        
        return mask