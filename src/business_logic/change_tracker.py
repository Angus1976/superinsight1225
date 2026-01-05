#!/usr/bin/env python3
"""
变化趋势跟踪系统
实现业务指标变化监控、异常检测算法、趋势预测模型、变化影响评估、自动报告生成功能

实现需求 13: 客户业务逻辑提炼与智能化 - 任务 47.3
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.cluster import DBSCAN
from scipy import stats
from scipy.stats import zscore, pearsonr
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChangePoint:
    """变化点"""
    timestamp: datetime
    metric_name: str
    old_value: float
    new_value: float
    change_magnitude: float
    change_type: str  # increase, decrease, spike, drop, shift
    significance: float
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TrendPrediction:
    """趋势预测"""
    metric_name: str
    current_value: float
    predicted_values: List[float]
    prediction_dates: List[datetime]
    confidence_intervals: List[Tuple[float, float]]
    trend_direction: str  # increasing, decreasing, stable, cyclical
    trend_strength: float
    model_accuracy: float
    seasonality_detected: bool = False
    forecast_horizon: int = 7

@dataclass
class AnomalyAlert:
    """异常警报"""
    timestamp: datetime
    metric_name: str
    observed_value: float
    expected_value: float
    anomaly_score: float
    severity: str  # low, medium, high, critical
    anomaly_type: str  # point, contextual, collective
    description: str
    recommended_actions: List[str]
    correlation_analysis: Dict[str, float] = field(default_factory=dict)

@dataclass
class ImpactAssessment:
    """影响评估"""
    overall_risk: str
    stability_score: float
    affected_metrics: List[str]
    cascade_effects: Dict[str, List[str]]
    business_impact: str
    recovery_time_estimate: Optional[int]  # hours
    mitigation_strategies: List[str]

class AdvancedBusinessMetricTracker:
    """高级业务指标跟踪器 - 增强版"""
    
    def __init__(self, window_size: int = 30, sensitivity: float = 2.0):
        self.window_size = window_size
        self.sensitivity = sensitivity
        self.metric_history = defaultdict(deque)
        self.baseline_stats = {}
        self.scaler = StandardScaler()
        self.min_max_scaler = MinMaxScaler()
        
        # 高级检测器
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.dbscan = DBSCAN(eps=0.5, min_samples=3)
        
        # 季节性检测参数
        self.seasonality_window = 24  # 24小时周期
        self.trend_models = {}
        
        # 早期警告系统
        self.warning_thresholds = {
            'critical': 4.0,
            'high': 3.0,
            'medium': 2.0,
            'low': 1.5
        }
        
        # 相关性分析缓存
        self.correlation_cache = {}
        self.last_correlation_update = None
        
    def track_metrics(self, annotations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        跟踪业务指标变化 - 增强版
        
        Args:
            annotations: 标注数据列表
            
        Returns:
            Dict: 跟踪结果
        """
        try:
            logger.info(f"开始高级跟踪 {len(annotations)} 条标注数据的业务指标")
            
            df = pd.DataFrame(annotations)
            
            # 计算各种业务指标
            metrics = self._calculate_enhanced_business_metrics(df)
            
            # 更新指标历史
            self._update_metric_history(metrics)
            
            # 多层异常检测
            anomalies = self._multi_layer_anomaly_detection()
            
            # 检测变化点 - 增强版
            change_points = self._enhanced_change_point_detection()
            
            # 智能趋势预测
            predictions = self._intelligent_trend_prediction()
            
            # 相关性分析
            correlations = self._correlation_analysis()
            
            # 综合影响评估
            impact_assessment = self._comprehensive_impact_assessment(change_points, anomalies)
            
            # 早期警告系统
            early_warnings = self._early_warning_system(metrics, anomalies)
            
            return {
                "current_metrics": metrics,
                "change_points": [self._change_point_to_dict(cp) for cp in change_points],
                "anomalies": [self._anomaly_to_dict(a) for a in anomalies],
                "trend_predictions": [self._prediction_to_dict(p) for p in predictions],
                "correlations": correlations,
                "impact_assessment": impact_assessment,
                "early_warnings": early_warnings,
                "tracking_timestamp": datetime.now().isoformat(),
                "metrics_tracked": len(metrics),
                "advanced_features": {
                    "seasonality_detected": any(p.seasonality_detected for p in predictions),
                    "correlation_strength": max(correlations.values()) if correlations else 0,
                    "anomaly_clusters": len(set(a.anomaly_type for a in anomalies))
                }
            }
            
        except Exception as e:
            logger.error(f"高级业务指标跟踪失败: {e}")
            return {"error": str(e)}
    
    def _calculate_enhanced_business_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算增强的业务指标"""
        metrics = {}
        
        try:
            # 基础指标
            metrics["total_annotations"] = len(df)
            metrics["unique_annotators"] = df['annotator'].nunique() if 'annotator' in df.columns else 0
            
            # 情感分析指标 - 增强版
            if 'sentiment' in df.columns:
                sentiment_dist = df['sentiment'].value_counts(normalize=True)
                metrics["positive_sentiment_ratio"] = sentiment_dist.get('positive', 0)
                metrics["negative_sentiment_ratio"] = sentiment_dist.get('negative', 0)
                metrics["neutral_sentiment_ratio"] = sentiment_dist.get('neutral', 0)
                
                # 情感多样性 (Shannon熵)
                sentiment_counts = df['sentiment'].value_counts()
                total = len(df)
                if total > 0:
                    probs = sentiment_counts / total
                    entropy = -sum(p * np.log2(p) for p in probs if p > 0)
                    metrics["sentiment_diversity"] = entropy
                    
                # 情感极化度 (正负情感比例差异)
                pos_ratio = sentiment_dist.get('positive', 0)
                neg_ratio = sentiment_dist.get('negative', 0)
                metrics["sentiment_polarization"] = abs(pos_ratio - neg_ratio)
                
                # 情感稳定性 (基于时间序列的方差)
                if 'created_at' in df.columns:
                    df_time = df.copy()
                    df_time['created_at'] = pd.to_datetime(df_time['created_at'], errors='coerce')
                    df_time = df_time.dropna(subset=['created_at']).sort_values('created_at')
                    
                    if len(df_time) > 5:
                        # 计算滑动窗口内的情感分布方差
                        window_size = min(10, len(df_time) // 2)
                        sentiment_stability = []
                        
                        for i in range(window_size, len(df_time)):
                            window_data = df_time.iloc[i-window_size:i]
                            window_sentiment = window_data['sentiment'].value_counts(normalize=True)
                            # 计算分布的方差
                            variance = np.var(list(window_sentiment.values))
                            sentiment_stability.append(variance)
                        
                        metrics["sentiment_stability"] = np.mean(sentiment_stability) if sentiment_stability else 0
            
            # 评分指标 - 增强版
            if 'rating' in df.columns:
                ratings = df['rating'].dropna()
                if len(ratings) > 0:
                    metrics["average_rating"] = ratings.mean()
                    metrics["rating_std"] = ratings.std()
                    metrics["rating_median"] = ratings.median()
                    metrics["rating_skewness"] = stats.skew(ratings)
                    metrics["rating_kurtosis"] = stats.kurtosis(ratings)
                    
                    # 评分分布指标
                    metrics["high_rating_ratio"] = (ratings >= 4).mean()
                    metrics["low_rating_ratio"] = (ratings <= 2).mean()
                    metrics["rating_concentration"] = (ratings == ratings.mode().iloc[0]).mean() if len(ratings.mode()) > 0 else 0
                    
                    # 评分趋势 (如果有时间信息)
                    if 'created_at' in df.columns:
                        df_rating = df.dropna(subset=['rating', 'created_at']).copy()
                        df_rating['created_at'] = pd.to_datetime(df_rating['created_at'], errors='coerce')
                        df_rating = df_rating.dropna(subset=['created_at']).sort_values('created_at')
                        
                        if len(df_rating) > 3:
                            # 计算评分趋势斜率
                            x = np.arange(len(df_rating))
                            y = df_rating['rating'].values
                            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                            metrics["rating_trend_slope"] = slope
                            metrics["rating_trend_correlation"] = r_value
            
            # 活动指标 - 增强版
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                valid_dates = df['created_at'].dropna()
                
                if len(valid_dates) > 0:
                    # 时间跨度
                    time_span = (valid_dates.max() - valid_dates.min()).total_seconds() / 3600  # 小时
                    metrics["activity_time_span_hours"] = time_span
                    
                    # 标注频率
                    if time_span > 0:
                        metrics["annotations_per_hour"] = len(df) / time_span
                    
                    # 活跃天数和时间分布
                    active_days = valid_dates.dt.date.nunique()
                    metrics["active_days"] = active_days
                    
                    # 日均标注数
                    if active_days > 0:
                        metrics["annotations_per_day"] = len(df) / active_days
                    
                    # 时间分布分析
                    hours = valid_dates.dt.hour
                    metrics["peak_hour"] = hours.mode().iloc[0] if len(hours.mode()) > 0 else 0
                    metrics["activity_concentration"] = (hours == metrics["peak_hour"]).mean()
                    
                    # 工作日vs周末分析
                    weekdays = valid_dates.dt.weekday < 5  # 0-4是工作日
                    metrics["weekday_ratio"] = weekdays.mean()
                    
                    # 活动规律性 (基于小时分布的熵)
                    hour_dist = hours.value_counts(normalize=True)
                    hour_entropy = -sum(p * np.log2(p) for p in hour_dist if p > 0)
                    metrics["activity_regularity"] = hour_entropy
            
            # 质量指标 - 增强版
            if 'text' in df.columns:
                text_lengths = df['text'].str.len().dropna()
                if len(text_lengths) > 0:
                    metrics["average_text_length"] = text_lengths.mean()
                    metrics["text_length_std"] = text_lengths.std()
                    metrics["text_length_median"] = text_lengths.median()
                    metrics["text_length_skewness"] = stats.skew(text_lengths)
                    
                    # 文本长度分布
                    metrics["short_text_ratio"] = (text_lengths < 50).mean()
                    metrics["long_text_ratio"] = (text_lengths > 200).mean()
                    
                # 文本复杂度分析
                texts = df['text'].fillna('').tolist()
                if texts:
                    # 词汇多样性
                    all_words = []
                    sentence_lengths = []
                    
                    for text in texts:
                        words = text.split()
                        all_words.extend(words)
                        sentences = text.split('.')
                        sentence_lengths.extend([len(s.split()) for s in sentences if s.strip()])
                    
                    if all_words:
                        unique_words = set(all_words)
                        metrics["vocabulary_diversity"] = len(unique_words) / len(all_words)
                        metrics["average_word_length"] = np.mean([len(word) for word in all_words])
                    
                    if sentence_lengths:
                        metrics["average_sentence_length"] = np.mean(sentence_lengths)
                        metrics["sentence_length_std"] = np.std(sentence_lengths)
            
            # 协作指标 - 增强版
            if 'task_id' in df.columns and 'annotator' in df.columns:
                task_annotators = df.groupby('task_id')['annotator'].nunique()
                metrics["average_annotators_per_task"] = task_annotators.mean()
                metrics["max_annotators_per_task"] = task_annotators.max()
                metrics["multi_annotator_task_ratio"] = (task_annotators > 1).mean()
                
                # 标注员工作负载分析
                annotator_workload = df['annotator'].value_counts()
                metrics["workload_balance"] = 1 - (annotator_workload.std() / annotator_workload.mean()) if annotator_workload.mean() > 0 else 0
                metrics["most_active_annotator_ratio"] = annotator_workload.max() / len(df) if len(df) > 0 else 0
                
                # 任务完成度分析
                if 'status' in df.columns:
                    completion_rate = (df['status'] == 'completed').mean()
                    metrics["task_completion_rate"] = completion_rate
                    
                    # 按标注员的完成率
                    annotator_completion = df.groupby('annotator')['status'].apply(lambda x: (x == 'completed').mean())
                    metrics["annotator_completion_consistency"] = 1 - annotator_completion.std() if len(annotator_completion) > 1 else 1
            
            # 业务价值指标
            if 'priority' in df.columns:
                priority_dist = df['priority'].value_counts(normalize=True)
                metrics["high_priority_ratio"] = priority_dist.get('high', 0)
                metrics["critical_priority_ratio"] = priority_dist.get('critical', 0)
            
            # 数据质量指标
            total_fields = len(df.columns)
            missing_ratios = df.isnull().mean()
            metrics["data_completeness"] = 1 - missing_ratios.mean()
            metrics["critical_field_completeness"] = 1 - missing_ratios[['text', 'sentiment']].mean() if all(col in df.columns for col in ['text', 'sentiment']) else 1
            
            return metrics
            
        except Exception as e:
            logger.error(f"增强业务指标计算失败: {e}")
            return {}
    
    def _update_metric_history(self, metrics: Dict[str, float]):
        """更新指标历史"""
        timestamp = datetime.now()
        
        for metric_name, value in metrics.items():
            # 添加到历史记录
            self.metric_history[metric_name].append((timestamp, value))
            
            # 保持窗口大小
            if len(self.metric_history[metric_name]) > self.window_size:
                self.metric_history[metric_name].popleft()
            
            # 更新基线统计
            if len(self.metric_history[metric_name]) >= 5:
                values = [v for _, v in self.metric_history[metric_name]]
                self.baseline_stats[metric_name] = {
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "median": np.median(values)
                }
    
    def _multi_layer_anomaly_detection(self) -> List[AnomalyAlert]:
        """多层异常检测算法"""
        anomalies = []
        
        for metric_name, history in self.metric_history.items():
            if len(history) < 10:
                continue
            
            try:
                timestamps, values = zip(*history)
                values = np.array(values)
                
                # 第一层：统计异常检测 (Z-score)
                z_scores = np.abs(zscore(values))
                statistical_anomalies = np.where(z_scores > 3)[0]
                
                # 第二层：机器学习异常检测 (Isolation Forest)
                if len(values) >= 10:
                    iso_forest = IsolationForest(contamination=0.1, random_state=42)
                    ml_anomalies = iso_forest.fit_predict(values.reshape(-1, 1))
                    ml_anomaly_indices = np.where(ml_anomalies == -1)[0]
                else:
                    ml_anomaly_indices = []
                
                # 第三层：时间序列异常检测 (基于趋势偏离)
                if len(values) >= 15:
                    # 计算移动平均和标准差
                    window = min(7, len(values) // 3)
                    rolling_mean = pd.Series(values).rolling(window=window, center=True).mean()
                    rolling_std = pd.Series(values).rolling(window=window, center=True).std()
                    
                    # 检测偏离移动平均的异常点
                    deviations = np.abs(values - rolling_mean.fillna(np.mean(values)))
                    threshold = rolling_std.fillna(np.std(values)) * 2.5
                    trend_anomalies = np.where(deviations > threshold)[0]
                else:
                    trend_anomalies = []
                
                # 第四层：上下文异常检测 (基于相邻点的关系)
                context_anomalies = []
                if len(values) >= 5:
                    for i in range(2, len(values) - 2):
                        # 检查当前点与前后点的关系
                        current = values[i]
                        neighbors = values[i-2:i+3]
                        neighbor_mean = np.mean([v for j, v in enumerate(neighbors) if j != 2])  # 排除当前点
                        neighbor_std = np.std([v for j, v in enumerate(neighbors) if j != 2])
                        
                        if neighbor_std > 0 and abs(current - neighbor_mean) > neighbor_std * 3:
                            context_anomalies.append(i)
                
                # 合并所有异常检测结果
                all_anomaly_indices = set(statistical_anomalies) | set(ml_anomaly_indices) | set(trend_anomalies) | set(context_anomalies)
                
                for idx in all_anomaly_indices:
                    if idx < len(timestamps):
                        timestamp = timestamps[idx]
                        value = values[idx]
                        
                        # 计算期望值
                        if metric_name in self.baseline_stats:
                            expected_value = self.baseline_stats[metric_name]["mean"]
                        else:
                            expected_value = np.mean(values)
                        
                        # 计算综合异常分数
                        anomaly_score = 0
                        anomaly_types = []
                        
                        if idx in statistical_anomalies:
                            anomaly_score += z_scores[idx]
                            anomaly_types.append("statistical")
                        
                        if idx in ml_anomaly_indices:
                            anomaly_score += 2.0  # ML检测权重
                            anomaly_types.append("machine_learning")
                        
                        if idx in trend_anomalies:
                            anomaly_score += 1.5  # 趋势偏离权重
                            anomaly_types.append("trend_deviation")
                        
                        if idx in context_anomalies:
                            anomaly_score += 1.0  # 上下文异常权重
                            anomaly_types.append("contextual")
                        
                        # 确定严重程度
                        if anomaly_score > self.warning_thresholds['critical']:
                            severity = "critical"
                        elif anomaly_score > self.warning_thresholds['high']:
                            severity = "high"
                        elif anomaly_score > self.warning_thresholds['medium']:
                            severity = "medium"
                        else:
                            severity = "low"
                        
                        # 确定异常类型
                        if len(anomaly_types) > 2:
                            anomaly_type = "collective"
                        elif "contextual" in anomaly_types:
                            anomaly_type = "contextual"
                        else:
                            anomaly_type = "point"
                        
                        # 生成描述和建议
                        description, actions = self._generate_enhanced_anomaly_description(
                            metric_name, value, expected_value, severity, anomaly_types
                        )
                        
                        # 计算与其他指标的相关性
                        correlations = self._calculate_anomaly_correlations(metric_name, timestamp)
                        
                        anomaly = AnomalyAlert(
                            timestamp=timestamp,
                            metric_name=metric_name,
                            observed_value=value,
                            expected_value=expected_value,
                            anomaly_score=anomaly_score,
                            severity=severity,
                            anomaly_type=anomaly_type,
                            description=description,
                            recommended_actions=actions,
                            correlation_analysis=correlations
                        )
                        
                        anomalies.append(anomaly)
                        
            except Exception as e:
                logger.error(f"多层异常检测失败 ({metric_name}): {e}")
        
        return anomalies
    
    def _enhanced_change_point_detection(self) -> List[ChangePoint]:
        """增强的变化点检测"""
        change_points = []
        
        for metric_name, history in self.metric_history.items():
            if len(history) < 15:  # 需要更多历史数据进行准确检测
                continue
            
            try:
                timestamps, values = zip(*history)
                values = np.array(values)
                
                # 方法1：改进的CUSUM算法
                cusum_changes = self._enhanced_cusum_detection(values)
                
                # 方法2：基于方差变化的检测
                variance_changes = self._variance_change_detection(values)
                
                # 方法3：基于趋势变化的检测
                trend_changes = self._trend_change_detection(values)
                
                # 方法4：基于分布变化的检测
                distribution_changes = self._distribution_change_detection(values)
                
                # 合并所有变化点
                all_changes = set(cusum_changes) | set(variance_changes) | set(trend_changes) | set(distribution_changes)
                
                for idx in all_changes:
                    if idx > 0 and idx < len(values) - 1:
                        old_value = values[idx - 1]
                        new_value = values[idx]
                        change_magnitude = abs(new_value - old_value)
                        
                        # 计算变化的统计显著性
                        if metric_name in self.baseline_stats:
                            baseline_std = self.baseline_stats[metric_name]["std"]
                            significance = change_magnitude / baseline_std if baseline_std > 0 else 0
                        else:
                            significance = change_magnitude / np.std(values) if np.std(values) > 0 else 0
                        
                        # 计算置信度 (基于多种方法的一致性)
                        detection_methods = []
                        if idx in cusum_changes:
                            detection_methods.append("cusum")
                        if idx in variance_changes:
                            detection_methods.append("variance")
                        if idx in trend_changes:
                            detection_methods.append("trend")
                        if idx in distribution_changes:
                            detection_methods.append("distribution")
                        
                        confidence = len(detection_methods) / 4.0  # 最多4种方法
                        
                        # 确定变化类型 - 更精细的分类
                        change_type = self._classify_change_type(values, idx, change_magnitude)
                        
                        # 分析变化的持续性
                        persistence = self._analyze_change_persistence(values, idx)
                        
                        change_point = ChangePoint(
                            timestamp=timestamps[idx],
                            metric_name=metric_name,
                            old_value=old_value,
                            new_value=new_value,
                            change_magnitude=change_magnitude,
                            change_type=change_type,
                            significance=significance,
                            confidence=confidence,
                            context={
                                "index": idx,
                                "window_size": len(values),
                                "detection_methods": detection_methods,
                                "persistence": persistence,
                                "relative_position": idx / len(values)
                            }
                        )
                        
                        change_points.append(change_point)
                        
            except Exception as e:
                logger.error(f"增强变化点检测失败 ({metric_name}): {e}")
        
        return change_points
    
    def _intelligent_trend_prediction(self) -> List[TrendPrediction]:
        """智能趋势预测 - 包含季节性检测"""
        predictions = []
        
        for metric_name, history in self.metric_history.items():
            if len(history) < 20:  # 需要足够的历史数据进行预测
                continue
            
            try:
                timestamps, values = zip(*history)
                values = np.array(values)
                
                # 季节性检测
                seasonality_detected, seasonal_period = self._detect_seasonality(values)
                
                # 选择合适的预测模型
                if seasonality_detected:
                    predictions_result = self._seasonal_trend_prediction(values, seasonal_period)
                else:
                    predictions_result = self._linear_trend_prediction(values)
                
                if predictions_result:
                    # 生成预测日期
                    last_timestamp = timestamps[-1]
                    prediction_dates = []
                    for i in range(7):
                        pred_date = last_timestamp + timedelta(hours=i+1)
                        prediction_dates.append(pred_date)
                    
                    # 计算趋势强度和方向
                    trend_direction, trend_strength = self._analyze_trend_characteristics(values)
                    
                    # 计算模型准确性
                    model_accuracy = self._calculate_prediction_accuracy(values, predictions_result['model'])
                    
                    # 风险评估
                    prediction_risk = self._assess_prediction_risk(values, predictions_result['predictions'])
                    
                    prediction = TrendPrediction(
                        metric_name=metric_name,
                        current_value=values[-1],
                        predicted_values=predictions_result['predictions'],
                        prediction_dates=prediction_dates,
                        confidence_intervals=predictions_result['confidence_intervals'],
                        trend_direction=trend_direction,
                        trend_strength=trend_strength,
                        model_accuracy=model_accuracy,
                        seasonality_detected=seasonality_detected,
                        forecast_horizon=7
                    )
                    
                    predictions.append(prediction)
                    
            except Exception as e:
                logger.error(f"智能趋势预测失败 ({metric_name}): {e}")
        
        return predictions
    
    def _correlation_analysis(self) -> Dict[str, float]:
        """相关性分析"""
        correlations = {}
        
        try:
            # 检查是否需要更新相关性缓存
            now = datetime.now()
            if (self.last_correlation_update is None or 
                (now - self.last_correlation_update).total_seconds() > 3600):  # 1小时更新一次
                
                # 构建指标矩阵
                metric_matrix = {}
                min_length = float('inf')
                
                for metric_name, history in self.metric_history.items():
                    if len(history) >= 10:
                        _, values = zip(*history)
                        metric_matrix[metric_name] = list(values)
                        min_length = min(min_length, len(values))
                
                if len(metric_matrix) >= 2 and min_length >= 10:
                    # 截取相同长度的数据
                    for metric_name in metric_matrix:
                        metric_matrix[metric_name] = metric_matrix[metric_name][-min_length:]
                    
                    # 计算相关性矩阵
                    metric_names = list(metric_matrix.keys())
                    for i, metric1 in enumerate(metric_names):
                        for j, metric2 in enumerate(metric_names[i+1:], i+1):
                            try:
                                correlation, p_value = pearsonr(metric_matrix[metric1], metric_matrix[metric2])
                                if not np.isnan(correlation) and p_value < 0.05:  # 显著性检验
                                    correlations[f"{metric1}_vs_{metric2}"] = correlation
                            except Exception as e:
                                logger.warning(f"相关性计算失败 ({metric1} vs {metric2}): {e}")
                
                self.correlation_cache = correlations
                self.last_correlation_update = now
            else:
                correlations = self.correlation_cache
                
        except Exception as e:
            logger.error(f"相关性分析失败: {e}")
        
        return correlations
    
    def _comprehensive_impact_assessment(self, change_points: List[ChangePoint], anomalies: List[AnomalyAlert]) -> Dict[str, Any]:
        """综合影响评估"""
        try:
            impact_assessment = {
                "overall_stability": "stable",
                "risk_level": "low",
                "stability_score": 1.0,
                "critical_changes": 0,
                "high_impact_anomalies": 0,
                "affected_metrics": set(),
                "cascade_effects": {},
                "business_impact": "minimal",
                "recovery_time_estimate": None,
                "mitigation_strategies": [],
                "confidence_level": 0.8
            }
            
            # 分析变化点影响
            significant_changes = [cp for cp in change_points if cp.significance > 2]
            critical_changes = [cp for cp in change_points if cp.significance > 4]
            
            impact_assessment["critical_changes"] = len(critical_changes)
            
            for cp in significant_changes:
                impact_assessment["affected_metrics"].add(cp.metric_name)
            
            # 分析异常影响
            high_severity_anomalies = [a for a in anomalies if a.severity in ["high", "critical"]]
            critical_anomalies = [a for a in anomalies if a.severity == "critical"]
            
            impact_assessment["high_impact_anomalies"] = len(high_severity_anomalies)
            
            for anomaly in high_severity_anomalies:
                impact_assessment["affected_metrics"].add(anomaly.metric_name)
            
            # 级联效应分析
            cascade_effects = {}
            for metric in impact_assessment["affected_metrics"]:
                # 查找与该指标相关的其他指标
                related_metrics = []
                for corr_key, corr_value in self.correlation_cache.items():
                    if metric in corr_key and abs(corr_value) > 0.5:
                        other_metric = corr_key.replace(metric, "").replace("_vs_", "").strip("_")
                        if other_metric and other_metric != metric:
                            related_metrics.append(other_metric)
                
                if related_metrics:
                    cascade_effects[metric] = related_metrics
            
            impact_assessment["cascade_effects"] = cascade_effects
            
            # 计算稳定性分数
            stability_factors = []
            
            # 基于变化点的稳定性
            if len(significant_changes) == 0:
                stability_factors.append(1.0)
            elif len(significant_changes) <= 2:
                stability_factors.append(0.8)
            elif len(significant_changes) <= 5:
                stability_factors.append(0.6)
            else:
                stability_factors.append(0.3)
            
            # 基于异常的稳定性
            if len(high_severity_anomalies) == 0:
                stability_factors.append(1.0)
            elif len(high_severity_anomalies) <= 1:
                stability_factors.append(0.7)
            elif len(high_severity_anomalies) <= 3:
                stability_factors.append(0.5)
            else:
                stability_factors.append(0.2)
            
            # 基于级联效应的稳定性
            cascade_risk = len(cascade_effects) / max(len(impact_assessment["affected_metrics"]), 1)
            if cascade_risk < 0.2:
                stability_factors.append(1.0)
            elif cascade_risk < 0.5:
                stability_factors.append(0.8)
            else:
                stability_factors.append(0.6)
            
            impact_assessment["stability_score"] = np.mean(stability_factors)
            
            # 确定整体稳定性和风险级别
            if impact_assessment["stability_score"] > 0.8:
                impact_assessment["overall_stability"] = "stable"
                impact_assessment["risk_level"] = "low"
                impact_assessment["business_impact"] = "minimal"
            elif impact_assessment["stability_score"] > 0.6:
                impact_assessment["overall_stability"] = "moderate"
                impact_assessment["risk_level"] = "medium"
                impact_assessment["business_impact"] = "moderate"
            elif impact_assessment["stability_score"] > 0.4:
                impact_assessment["overall_stability"] = "unstable"
                impact_assessment["risk_level"] = "high"
                impact_assessment["business_impact"] = "significant"
            else:
                impact_assessment["overall_stability"] = "critical"
                impact_assessment["risk_level"] = "critical"
                impact_assessment["business_impact"] = "severe"
            
            # 恢复时间估算
            if impact_assessment["risk_level"] == "critical":
                impact_assessment["recovery_time_estimate"] = 24  # 24小时
            elif impact_assessment["risk_level"] == "high":
                impact_assessment["recovery_time_estimate"] = 8   # 8小时
            elif impact_assessment["risk_level"] == "medium":
                impact_assessment["recovery_time_estimate"] = 2   # 2小时
            
            # 生成缓解策略
            strategies = []
            
            if len(critical_anomalies) > 0:
                strategies.append("立即启动应急响应程序")
                strategies.append("隔离受影响的系统组件")
            
            if len(critical_changes) > 0:
                strategies.append("回滚最近的系统变更")
                strategies.append("激活备用系统")
            
            if cascade_effects:
                strategies.append("监控级联效应传播")
                strategies.append("预防性维护相关系统")
            
            if impact_assessment["risk_level"] in ["high", "critical"]:
                strategies.extend([
                    "通知所有相关业务专家",
                    "启动24/7监控模式",
                    "准备业务连续性计划"
                ])
            elif impact_assessment["risk_level"] == "medium":
                strategies.extend([
                    "加强监控频率",
                    "检查受影响的业务流程",
                    "准备应急预案"
                ])
            else:
                strategies.extend([
                    "继续正常监控",
                    "定期审查趋势变化"
                ])
            
            impact_assessment["mitigation_strategies"] = strategies
            impact_assessment["affected_metrics"] = list(impact_assessment["affected_metrics"])
            
            return impact_assessment
            
        except Exception as e:
            logger.error(f"综合影响评估失败: {e}")
            return {"error": str(e)}
    
    def _early_warning_system(self, current_metrics: Dict[str, float], anomalies: List[AnomalyAlert]) -> Dict[str, Any]:
        """早期警告系统"""
        warnings = {
            "active_warnings": [],
            "risk_indicators": {},
            "preventive_actions": [],
            "monitoring_recommendations": []
        }
        
        try:
            # 基于当前指标的预警
            for metric_name, value in current_metrics.items():
                if metric_name in self.baseline_stats:
                    baseline = self.baseline_stats[metric_name]
                    
                    # 计算偏离程度
                    if baseline["std"] > 0:
                        deviation = abs(value - baseline["mean"]) / baseline["std"]
                        
                        if deviation > 2.5:
                            warnings["active_warnings"].append({
                                "type": "metric_deviation",
                                "metric": metric_name,
                                "current_value": value,
                                "expected_range": [
                                    baseline["mean"] - 2 * baseline["std"],
                                    baseline["mean"] + 2 * baseline["std"]
                                ],
                                "severity": "high" if deviation > 3.5 else "medium",
                                "message": f"{metric_name} 偏离正常范围 {deviation:.1f} 个标准差"
                            })
                        
                        warnings["risk_indicators"][metric_name] = {
                            "deviation_score": deviation,
                            "trend": "increasing" if value > baseline["mean"] else "decreasing",
                            "risk_level": "high" if deviation > 3 else "medium" if deviation > 2 else "low"
                        }
            
            # 基于异常模式的预警
            anomaly_patterns = {}
            for anomaly in anomalies:
                metric = anomaly.metric_name
                if metric not in anomaly_patterns:
                    anomaly_patterns[metric] = []
                anomaly_patterns[metric].append(anomaly)
            
            for metric, metric_anomalies in anomaly_patterns.items():
                if len(metric_anomalies) > 1:
                    warnings["active_warnings"].append({
                        "type": "anomaly_cluster",
                        "metric": metric,
                        "anomaly_count": len(metric_anomalies),
                        "severity": "critical" if len(metric_anomalies) > 3 else "high",
                        "message": f"{metric} 出现 {len(metric_anomalies)} 个异常，可能存在系统性问题"
                    })
            
            # 生成预防性行动建议
            if warnings["active_warnings"]:
                high_severity_warnings = [w for w in warnings["active_warnings"] if w["severity"] in ["high", "critical"]]
                
                if high_severity_warnings:
                    warnings["preventive_actions"].extend([
                        "立即检查数据源和处理流程",
                        "验证系统配置和参数设置",
                        "检查网络连接和服务状态",
                        "准备回滚计划"
                    ])
                else:
                    warnings["preventive_actions"].extend([
                        "增加监控频率",
                        "检查相关业务流程",
                        "准备应急响应计划"
                    ])
            
            # 监控建议
            critical_metrics = [w["metric"] for w in warnings["active_warnings"] if w["severity"] == "critical"]
            high_risk_metrics = [w["metric"] for w in warnings["active_warnings"] if w["severity"] == "high"]
            
            if critical_metrics:
                warnings["monitoring_recommendations"].append(f"对 {', '.join(critical_metrics)} 实施实时监控")
            
            if high_risk_metrics:
                warnings["monitoring_recommendations"].append(f"对 {', '.join(high_risk_metrics)} 增加监控频率至每15分钟")
            
            if not warnings["active_warnings"]:
                warnings["monitoring_recommendations"].append("系统运行正常，维持当前监控策略")
            
        except Exception as e:
            logger.error(f"早期警告系统失败: {e}")
            warnings["error"] = str(e)
        
        return warnings
    
    def _enhanced_cusum_detection(self, values: np.ndarray, threshold: float = None) -> List[int]:
        """增强的CUSUM变化点检测算法"""
        if threshold is None:
            threshold = self.sensitivity * np.std(values)
        
        change_points = []
        cumsum_pos = 0
        cumsum_neg = 0
        
        # 使用滑动窗口的均值作为参考
        window_size = min(10, len(values) // 4)
        
        for i in range(window_size, len(values)):
            # 计算局部均值
            local_mean = np.mean(values[i-window_size:i])
            diff = values[i] - local_mean
            
            cumsum_pos = max(0, cumsum_pos + diff - threshold/2)
            cumsum_neg = max(0, cumsum_neg - diff - threshold/2)
            
            if cumsum_pos > threshold or cumsum_neg > threshold:
                change_points.append(i)
                cumsum_pos = 0
                cumsum_neg = 0
        
        return change_points
    
    def _variance_change_detection(self, values: np.ndarray) -> List[int]:
        """基于方差变化的检测"""
        change_points = []
        window_size = min(10, len(values) // 4)
        
        if len(values) < window_size * 2:
            return change_points
        
        for i in range(window_size, len(values) - window_size):
            # 计算前后窗口的方差
            before_var = np.var(values[i-window_size:i])
            after_var = np.var(values[i:i+window_size])
            
            # 使用F检验检测方差变化
            if before_var > 0 and after_var > 0:
                f_stat = max(before_var, after_var) / min(before_var, after_var)
                if f_stat > 4.0:  # 显著的方差变化
                    change_points.append(i)
        
        return change_points
    
    def _trend_change_detection(self, values: np.ndarray) -> List[int]:
        """基于趋势变化的检测"""
        change_points = []
        window_size = min(8, len(values) // 5)
        
        if len(values) < window_size * 2:
            return change_points
        
        for i in range(window_size, len(values) - window_size):
            # 计算前后窗口的趋势斜率
            x_before = np.arange(window_size)
            y_before = values[i-window_size:i]
            slope_before, _, _, _, _ = stats.linregress(x_before, y_before)
            
            x_after = np.arange(window_size)
            y_after = values[i:i+window_size]
            slope_after, _, _, _, _ = stats.linregress(x_after, y_after)
            
            # 检测趋势方向的显著变化
            if abs(slope_before - slope_after) > np.std(values) * 0.5:
                change_points.append(i)
        
        return change_points
    
    def _distribution_change_detection(self, values: np.ndarray) -> List[int]:
        """基于分布变化的检测"""
        change_points = []
        window_size = min(15, len(values) // 3)
        
        if len(values) < window_size * 2:
            return change_points
        
        for i in range(window_size, len(values) - window_size):
            # 使用Kolmogorov-Smirnov检验检测分布变化
            before_sample = values[i-window_size:i]
            after_sample = values[i:i+window_size]
            
            try:
                ks_stat, p_value = stats.ks_2samp(before_sample, after_sample)
                if p_value < 0.05 and ks_stat > 0.3:  # 显著的分布变化
                    change_points.append(i)
            except Exception:
                continue
        
        return change_points
    
    def _classify_change_type(self, values: np.ndarray, idx: int, magnitude: float) -> str:
        """分类变化类型"""
        if idx <= 0 or idx >= len(values) - 1:
            return "unknown"
        
        old_value = values[idx - 1]
        new_value = values[idx]
        std_dev = np.std(values)
        
        # 计算相对变化
        relative_change = (new_value - old_value) / old_value if old_value != 0 else 0
        
        # 检查是否是突发变化
        is_spike = magnitude > std_dev * 2.5
        
        # 检查变化方向
        if new_value > old_value:
            if is_spike:
                return "spike"
            elif relative_change > 0.2:
                return "jump"
            else:
                return "increase"
        else:
            if is_spike:
                return "drop"
            elif relative_change < -0.2:
                return "fall"
            else:
                return "decrease"
    
    def _analyze_change_persistence(self, values: np.ndarray, idx: int) -> float:
        """分析变化的持续性"""
        if idx >= len(values) - 3:
            return 0.0
        
        # 检查变化后的几个点是否保持在新水平
        change_value = values[idx]
        subsequent_values = values[idx+1:idx+4]  # 检查后续3个点
        
        if len(subsequent_values) == 0:
            return 0.0
        
        # 计算后续值与变化点的相似度
        similarities = []
        for val in subsequent_values:
            if change_value != 0:
                similarity = 1 - abs(val - change_value) / abs(change_value)
            else:
                similarity = 1 if val == change_value else 0
            similarities.append(max(0, similarity))
        
        return np.mean(similarities)
    
    def _detect_seasonality(self, values: np.ndarray) -> Tuple[bool, int]:
        """检测季节性模式"""
        if len(values) < self.seasonality_window * 2:
            return False, 0
        
        # 尝试不同的周期长度
        potential_periods = [24, 12, 8, 6, 4]  # 小时级别的常见周期
        
        best_period = 0
        best_score = 0
        
        for period in potential_periods:
            if len(values) < period * 3:
                continue
            
            # 计算自相关
            try:
                # 简化的季节性检测：比较不同周期的相关性
                correlations = []
                for lag in range(1, min(4, len(values) // period)):
                    if len(values) >= period * lag + period:
                        segment1 = values[:period]
                        segment2 = values[period * lag:period * lag + period]
                        
                        if len(segment1) == len(segment2):
                            corr, _ = pearsonr(segment1, segment2)
                            if not np.isnan(corr):
                                correlations.append(abs(corr))
                
                if correlations:
                    avg_correlation = np.mean(correlations)
                    if avg_correlation > best_score:
                        best_score = avg_correlation
                        best_period = period
                        
            except Exception:
                continue
        
        # 如果相关性足够高，认为存在季节性
        seasonality_detected = best_score > 0.3
        
        return seasonality_detected, best_period if seasonality_detected else 0
    
    def _seasonal_trend_prediction(self, values: np.ndarray, period: int) -> Dict[str, Any]:
        """基于季节性的趋势预测"""
        try:
            # 分解时间序列：趋势 + 季节性 + 残差
            trend = self._extract_trend(values)
            seasonal = self._extract_seasonal_pattern(values, period)
            
            # 预测趋势
            trend_model = LinearRegression()
            X_trend = np.arange(len(trend)).reshape(-1, 1)
            trend_model.fit(X_trend, trend)
            
            # 预测未来7个点的趋势
            future_X = np.arange(len(trend), len(trend) + 7).reshape(-1, 1)
            future_trend = trend_model.predict(future_X)
            
            # 添加季节性模式
            seasonal_pattern = seasonal[-period:] if len(seasonal) >= period else seasonal
            future_seasonal = []
            
            for i in range(7):
                seasonal_idx = i % len(seasonal_pattern)
                future_seasonal.append(seasonal_pattern[seasonal_idx])
            
            # 组合预测
            predictions = future_trend + np.array(future_seasonal)
            
            # 计算置信区间
            residuals = values - (trend + seasonal[:len(values)])
            prediction_std = np.std(residuals)
            
            confidence_intervals = []
            for pred in predictions:
                lower = pred - 1.96 * prediction_std
                upper = pred + 1.96 * prediction_std
                confidence_intervals.append((lower, upper))
            
            return {
                'predictions': predictions.tolist(),
                'confidence_intervals': confidence_intervals,
                'model': trend_model
            }
            
        except Exception as e:
            logger.error(f"季节性趋势预测失败: {e}")
            return self._linear_trend_prediction(values)
    
    def _linear_trend_prediction(self, values: np.ndarray) -> Dict[str, Any]:
        """线性趋势预测"""
        try:
            # 使用多项式回归捕获非线性趋势
            X = np.arange(len(values)).reshape(-1, 1)
            
            # 尝试不同的多项式度数
            best_model = None
            best_score = -float('inf')
            
            for degree in [1, 2, 3]:
                try:
                    from sklearn.preprocessing import PolynomialFeatures
                    poly_features = PolynomialFeatures(degree=degree)
                    X_poly = poly_features.fit_transform(X)
                    
                    model = Ridge(alpha=1.0)  # 使用Ridge回归防止过拟合
                    model.fit(X_poly, values)
                    
                    score = model.score(X_poly, values)
                    if score > best_score:
                        best_score = score
                        best_model = (model, poly_features)
                        
                except Exception:
                    continue
            
            if best_model is None:
                # 回退到简单线性回归
                model = LinearRegression()
                model.fit(X, values)
                best_model = (model, None)
            
            # 预测
            future_X = np.arange(len(values), len(values) + 7).reshape(-1, 1)
            
            if best_model[1] is not None:  # 多项式特征
                future_X_poly = best_model[1].transform(future_X)
                predictions = best_model[0].predict(future_X_poly)
            else:  # 线性模型
                predictions = best_model[0].predict(future_X)
            
            # 计算置信区间
            if best_model[1] is not None:
                X_poly = best_model[1].transform(X)
                residuals = values - best_model[0].predict(X_poly)
            else:
                residuals = values - best_model[0].predict(X)
            
            prediction_std = np.std(residuals)
            
            confidence_intervals = []
            for pred in predictions:
                lower = pred - 1.96 * prediction_std
                upper = pred + 1.96 * prediction_std
                confidence_intervals.append((lower, upper))
            
            return {
                'predictions': predictions.tolist(),
                'confidence_intervals': confidence_intervals,
                'model': best_model[0]
            }
            
        except Exception as e:
            logger.error(f"线性趋势预测失败: {e}")
            return None
    
    def _extract_trend(self, values: np.ndarray) -> np.ndarray:
        """提取趋势分量"""
        # 使用移动平均提取趋势
        window_size = min(7, len(values) // 4)
        if window_size < 3:
            return values
        
        trend = pd.Series(values).rolling(window=window_size, center=True).mean()
        return trend.fillna(method='bfill').fillna(method='ffill').values
    
    def _extract_seasonal_pattern(self, values: np.ndarray, period: int) -> np.ndarray:
        """提取季节性模式"""
        if len(values) < period:
            return np.zeros(len(values))
        
        # 计算每个季节位置的平均值
        seasonal_means = []
        for i in range(period):
            positions = list(range(i, len(values), period))
            if positions:
                seasonal_means.append(np.mean([values[pos] for pos in positions]))
            else:
                seasonal_means.append(0)
        
        # 扩展到整个序列长度
        seasonal = []
        for i in range(len(values)):
            seasonal.append(seasonal_means[i % period])
        
        return np.array(seasonal)
    
    def _analyze_trend_characteristics(self, values: np.ndarray) -> Tuple[str, float]:
        """分析趋势特征"""
        if len(values) < 5:
            return "stable", 0.0
        
        # 计算整体趋势
        X = np.arange(len(values)).reshape(-1, 1)
        model = LinearRegression()
        model.fit(X, values)
        
        slope = model.coef_[0]
        r_squared = model.score(X, values)
        
        # 确定趋势方向
        if abs(slope) < np.std(values) * 0.01:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        # 计算趋势强度 (结合斜率和拟合度)
        strength = abs(slope) * r_squared / np.std(values) if np.std(values) > 0 else 0
        
        return direction, min(strength, 1.0)  # 限制在0-1之间
    
    def _calculate_prediction_accuracy(self, values: np.ndarray, model) -> float:
        """计算预测模型准确性"""
        try:
            if len(values) < 10:
                return 0.5
            
            # 使用交叉验证评估模型
            split_point = len(values) * 3 // 4
            train_values = values[:split_point]
            test_values = values[split_point:]
            
            # 重新训练模型
            X_train = np.arange(len(train_values)).reshape(-1, 1)
            X_test = np.arange(len(train_values), len(values)).reshape(-1, 1)
            
            if hasattr(model, 'fit'):
                model.fit(X_train, train_values)
                predictions = model.predict(X_test)
                
                # 计算准确性指标
                mae = mean_absolute_error(test_values, predictions)
                mse = mean_squared_error(test_values, predictions)
                
                # 转换为0-1之间的准确性分数
                mean_value = np.mean(test_values)
                if mean_value != 0:
                    accuracy = 1 - (mae / abs(mean_value))
                else:
                    accuracy = 1 - (mae / (np.std(test_values) + 1e-8))
                
                return max(0, min(1, accuracy))
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"预测准确性计算失败: {e}")
            return 0.5
    
    def _assess_prediction_risk(self, values: np.ndarray, predictions: List[float]) -> Dict[str, float]:
        """评估预测风险"""
        risk_assessment = {
            "volatility_risk": 0.0,
            "trend_reversal_risk": 0.0,
            "outlier_risk": 0.0,
            "overall_risk": 0.0
        }
        
        try:
            # 波动性风险
            historical_volatility = np.std(values)
            prediction_volatility = np.std(predictions)
            risk_assessment["volatility_risk"] = min(1.0, prediction_volatility / (historical_volatility + 1e-8))
            
            # 趋势反转风险
            if len(values) >= 5:
                recent_trend = np.mean(np.diff(values[-5:]))
                prediction_trend = np.mean(np.diff(predictions))
                
                if recent_trend * prediction_trend < 0:  # 趋势反转
                    risk_assessment["trend_reversal_risk"] = 0.8
                else:
                    risk_assessment["trend_reversal_risk"] = 0.2
            
            # 异常值风险
            value_range = np.max(values) - np.min(values)
            prediction_range = max(predictions) - min(predictions)
            
            if value_range > 0:
                risk_assessment["outlier_risk"] = min(1.0, prediction_range / value_range)
            
            # 综合风险
            risk_assessment["overall_risk"] = np.mean(list(risk_assessment.values()))
            
        except Exception as e:
            logger.error(f"预测风险评估失败: {e}")
        
        return risk_assessment
    
    def _generate_enhanced_anomaly_description(self, metric_name: str, observed: float, expected: float, 
                                             severity: str, anomaly_types: List[str]) -> Tuple[str, List[str]]:
        """生成增强的异常描述和建议"""
        direction = "高于" if observed > expected else "低于"
        change_pct = abs(observed - expected) / expected * 100 if expected != 0 else 0
        
        # 基础描述
        description = f"{metric_name} 异常：观测值 {observed:.2f} {direction}期望值 {expected:.2f}，偏差 {change_pct:.1f}%"
        
        # 添加检测方法信息
        if len(anomaly_types) > 1:
            description += f"（通过 {', '.join(anomaly_types)} 方法检测）"
        
        # 生成建议
        actions = []
        
        # 基于严重程度的建议
        if severity in ["critical", "high"]:
            actions.extend([
                "立即检查数据源和标注流程",
                "通知相关业务专家进行人工审核",
                "启动应急响应程序"
            ])
        elif severity == "medium":
            actions.extend([
                "检查数据质量和处理流程",
                "增加监控频率",
                "准备应急预案"
            ])
        else:
            actions.extend([
                "继续监控数据变化",
                "记录异常模式"
            ])
        
        # 基于指标类型的建议
        if "sentiment" in metric_name:
            actions.extend([
                "检查情感标注的一致性",
                "审查标注指南是否需要更新",
                "分析情感分布变化的业务原因"
            ])
        elif "rating" in metric_name:
            actions.extend([
                "检查评分标准的执行情况",
                "分析评分分布的变化原因",
                "验证评分数据的完整性"
            ])
        elif "annotation" in metric_name:
            actions.extend([
                "检查标注工具和流程",
                "分析标注员的工作负载",
                "验证任务分配的合理性"
            ])
        elif "activity" in metric_name:
            actions.extend([
                "检查系统性能和可用性",
                "分析用户行为模式变化",
                "验证时间统计的准确性"
            ])
        
        # 基于异常类型的建议
        if "machine_learning" in anomaly_types:
            actions.append("使用机器学习模型进行深度分析")
        
        if "contextual" in anomaly_types:
            actions.append("分析异常发生的上下文环境")
        
        if "trend_deviation" in anomaly_types:
            actions.append("检查是否存在系统性趋势变化")
        
        return description, list(set(actions))  # 去重
    
    def _calculate_anomaly_correlations(self, metric_name: str, timestamp: datetime) -> Dict[str, float]:
        """计算异常与其他指标的相关性"""
        correlations = {}
        
        try:
            # 查找同一时间点附近的其他指标值
            time_window = timedelta(minutes=30)  # 30分钟窗口
            
            for other_metric, history in self.metric_history.items():
                if other_metric == metric_name:
                    continue
                
                # 查找时间窗口内的值
                nearby_values = []
                for ts, value in history:
                    if abs((ts - timestamp).total_seconds()) <= time_window.total_seconds():
                        nearby_values.append(value)
                
                if nearby_values:
                    # 计算与基线的偏离程度
                    if other_metric in self.baseline_stats:
                        baseline_mean = self.baseline_stats[other_metric]["mean"]
                        baseline_std = self.baseline_stats[other_metric]["std"]
                        
                        if baseline_std > 0:
                            avg_deviation = np.mean([abs(v - baseline_mean) / baseline_std for v in nearby_values])
                            correlations[other_metric] = min(1.0, avg_deviation)
                        
        except Exception as e:
            logger.error(f"异常相关性计算失败: {e}")
        
        return correlations
    
    def _detect_anomalies(self) -> List[AnomalyAlert]:
        """检测异常值 - 重定向到多层检测"""
        return self._multi_layer_anomaly_detection()
    
    def _generate_trend_predictions(self) -> List[TrendPrediction]:
        """生成趋势预测 - 重定向到智能预测"""
        return self._intelligent_trend_prediction()
    
    def _assess_change_impact(self, change_points: List[ChangePoint], anomalies: List[AnomalyAlert]) -> Dict[str, Any]:
        """评估变化影响 - 重定向到综合评估"""
        return self._comprehensive_impact_assessment(change_points, anomalies)
    
    # 辅助方法：转换数据结构为字典
    def _change_point_to_dict(self, cp: ChangePoint) -> Dict[str, Any]:
        """变化点转字典"""
        return {
            "timestamp": cp.timestamp.isoformat(),
            "metric_name": cp.metric_name,
            "old_value": cp.old_value,
            "new_value": cp.new_value,
            "change_magnitude": cp.change_magnitude,
            "change_type": cp.change_type,
            "significance": cp.significance,
            "context": cp.context
        }
    
    def _anomaly_to_dict(self, anomaly: AnomalyAlert) -> Dict[str, Any]:
        """异常转字典"""
        return {
            "timestamp": anomaly.timestamp.isoformat(),
            "metric_name": anomaly.metric_name,
            "observed_value": anomaly.observed_value,
            "expected_value": anomaly.expected_value,
            "anomaly_score": anomaly.anomaly_score,
            "severity": anomaly.severity,
            "description": anomaly.description,
            "recommended_actions": anomaly.recommended_actions
        }
    
    def _prediction_to_dict(self, prediction: TrendPrediction) -> Dict[str, Any]:
        """预测转字典"""
        return {
            "metric_name": prediction.metric_name,
            "current_value": prediction.current_value,
            "predicted_values": prediction.predicted_values,
            "prediction_dates": [d.isoformat() for d in prediction.prediction_dates],
            "confidence_intervals": prediction.confidence_intervals,
            "trend_direction": prediction.trend_direction,
            "trend_strength": prediction.trend_strength,
            "model_accuracy": prediction.model_accuracy
        }

class AutoReportGenerator:
    """自动报告生成器"""
    
    def __init__(self):
        self.report_templates = {
            "daily": self._generate_daily_report,
            "weekly": self._generate_weekly_report,
            "monthly": self._generate_monthly_report,
            "alert": self._generate_alert_report
        }
    
    def generate_report(self, report_type: str, tracking_data: Dict[str, Any], 
                       project_id: str) -> Dict[str, Any]:
        """
        生成自动报告
        
        Args:
            report_type: 报告类型
            tracking_data: 跟踪数据
            project_id: 项目ID
            
        Returns:
            Dict: 生成的报告
        """
        try:
            logger.info(f"生成 {report_type} 报告，项目: {project_id}")
            
            if report_type not in self.report_templates:
                return {"error": f"不支持的报告类型: {report_type}"}
            
            report_generator = self.report_templates[report_type]
            report = report_generator(tracking_data, project_id)
            
            # 添加通用信息
            report.update({
                "report_type": report_type,
                "project_id": project_id,
                "generated_at": datetime.now().isoformat(),
                "data_period": self._calculate_data_period(tracking_data)
            })
            
            logger.info(f"{report_type} 报告生成完成")
            return report
            
        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            return {"error": str(e)}
    
    def _generate_daily_report(self, tracking_data: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        """生成日报"""
        report = {
            "title": f"项目 {project_id} 日度业务逻辑分析报告",
            "summary": {},
            "key_findings": [],
            "recommendations": [],
            "detailed_metrics": tracking_data.get("current_metrics", {}),
            "charts_data": []
        }
        
        # 摘要统计
        metrics = tracking_data.get("current_metrics", {})
        change_points = tracking_data.get("change_points", [])
        anomalies = tracking_data.get("anomalies", [])
        
        report["summary"] = {
            "total_annotations": metrics.get("total_annotations", 0),
            "unique_annotators": metrics.get("unique_annotators", 0),
            "change_points_detected": len(change_points),
            "anomalies_detected": len(anomalies),
            "overall_health": self._assess_overall_health(tracking_data)
        }
        
        # 关键发现
        findings = []
        
        # 分析变化点
        significant_changes = [cp for cp in change_points if cp.get("significance", 0) > 2]
        if significant_changes:
            findings.append(f"检测到 {len(significant_changes)} 个显著变化点")
            for change in significant_changes[:3]:  # 只显示前3个
                findings.append(f"- {change['metric_name']}: {change['change_type']} ({change['change_magnitude']:.2f})")
        
        # 分析异常
        critical_anomalies = [a for a in anomalies if a.get("severity") in ["high", "critical"]]
        if critical_anomalies:
            findings.append(f"发现 {len(critical_anomalies)} 个高严重性异常")
            for anomaly in critical_anomalies[:3]:
                findings.append(f"- {anomaly['metric_name']}: {anomaly['description']}")
        
        if not findings:
            findings.append("系统运行正常，未发现显著异常")
        
        report["key_findings"] = findings
        
        # 建议
        recommendations = []
        impact_assessment = tracking_data.get("impact_assessment", {})
        
        if impact_assessment.get("risk_level") == "high":
            recommendations.extend([
                "立即检查系统状态和数据质量",
                "通知相关业务专家进行人工审核",
                "考虑暂停自动化流程"
            ])
        elif impact_assessment.get("risk_level") == "medium":
            recommendations.extend([
                "加强监控频率",
                "检查受影响的业务流程",
                "准备应急预案"
            ])
        else:
            recommendations.extend([
                "继续正常监控",
                "定期审查业务指标趋势"
            ])
        
        report["recommendations"] = recommendations
        
        return report
    
    def _generate_weekly_report(self, tracking_data: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        """生成周报"""
        report = {
            "title": f"项目 {project_id} 周度业务逻辑分析报告",
            "executive_summary": "",
            "trend_analysis": {},
            "performance_metrics": {},
            "risk_assessment": {},
            "action_items": []
        }
        
        # 执行摘要
        metrics = tracking_data.get("current_metrics", {})
        predictions = tracking_data.get("trend_predictions", [])
        
        total_annotations = metrics.get("total_annotations", 0)
        avg_rating = metrics.get("average_rating", 0)
        
        report["executive_summary"] = (
            f"本周共处理 {total_annotations} 条标注数据，"
            f"平均评分 {avg_rating:.2f}。"
            f"系统识别出 {len(predictions)} 个趋势预测。"
        )
        
        # 趋势分析
        trend_summary = {}
        for pred in predictions:
            metric_name = pred.get("metric_name", "")
            trend_direction = pred.get("trend_direction", "stable")
            trend_strength = pred.get("trend_strength", 0)
            
            trend_summary[metric_name] = {
                "direction": trend_direction,
                "strength": trend_strength,
                "confidence": pred.get("model_accuracy", 0)
            }
        
        report["trend_analysis"] = trend_summary
        
        # 性能指标
        report["performance_metrics"] = {
            "annotation_volume": metrics.get("total_annotations", 0),
            "quality_score": metrics.get("average_rating", 0),
            "efficiency": metrics.get("annotations_per_hour", 0),
            "consistency": metrics.get("sentiment_diversity", 0)
        }
        
        # 风险评估
        impact_assessment = tracking_data.get("impact_assessment", {})
        report["risk_assessment"] = {
            "overall_risk": impact_assessment.get("risk_level", "low"),
            "stability": impact_assessment.get("overall_stability", "stable"),
            "critical_issues": impact_assessment.get("critical_changes", 0),
            "mitigation_status": "monitoring"
        }
        
        return report
    
    def _generate_monthly_report(self, tracking_data: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        """生成月报"""
        report = {
            "title": f"项目 {project_id} 月度业务逻辑分析报告",
            "strategic_overview": "",
            "kpi_dashboard": {},
            "business_insights": [],
            "improvement_opportunities": [],
            "next_month_forecast": {}
        }
        
        # 战略概览
        metrics = tracking_data.get("current_metrics", {})
        
        report["strategic_overview"] = (
            f"本月业务逻辑分析显示系统整体运行{tracking_data.get('impact_assessment', {}).get('overall_stability', '稳定')}，"
            f"共处理 {metrics.get('total_annotations', 0)} 条标注数据，"
            f"涉及 {metrics.get('unique_annotators', 0)} 名标注员。"
        )
        
        # KPI仪表板
        report["kpi_dashboard"] = {
            "数据处理量": metrics.get("total_annotations", 0),
            "平均质量评分": metrics.get("average_rating", 0),
            "标注效率": metrics.get("annotations_per_hour", 0),
            "团队协作度": metrics.get("average_annotators_per_task", 0),
            "系统稳定性": tracking_data.get("impact_assessment", {}).get("overall_stability", "stable")
        }
        
        # 业务洞察
        insights = []
        
        # 基于趋势预测生成洞察
        predictions = tracking_data.get("trend_predictions", [])
        for pred in predictions:
            if pred.get("trend_direction") != "stable":
                insight = f"{pred['metric_name']} 呈现 {pred['trend_direction']} 趋势，预测强度 {pred.get('trend_strength', 0):.2f}"
                insights.append(insight)
        
        if not insights:
            insights.append("系统各项指标保持稳定，未发现显著趋势变化")
        
        report["business_insights"] = insights
        
        return report
    
    def _generate_alert_report(self, tracking_data: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        """生成警报报告"""
        report = {
            "title": f"项目 {project_id} 异常警报报告",
            "alert_level": "info",
            "immediate_actions": [],
            "affected_systems": [],
            "timeline": [],
            "contact_list": []
        }
        
        anomalies = tracking_data.get("anomalies", [])
        change_points = tracking_data.get("change_points", [])
        
        # 确定警报级别
        critical_anomalies = [a for a in anomalies if a.get("severity") == "critical"]
        high_anomalies = [a for a in anomalies if a.get("severity") == "high"]
        
        if critical_anomalies:
            report["alert_level"] = "critical"
        elif high_anomalies:
            report["alert_level"] = "high"
        elif anomalies:
            report["alert_level"] = "medium"
        
        # 立即行动
        actions = []
        for anomaly in critical_anomalies + high_anomalies:
            actions.extend(anomaly.get("recommended_actions", []))
        
        report["immediate_actions"] = list(set(actions))  # 去重
        
        # 受影响系统
        affected_metrics = set()
        for anomaly in anomalies:
            affected_metrics.add(anomaly.get("metric_name", ""))
        for change in change_points:
            affected_metrics.add(change.get("metric_name", ""))
        
        report["affected_systems"] = list(affected_metrics)
        
        return report
    
    def _assess_overall_health(self, tracking_data: Dict[str, Any]) -> str:
        """评估整体健康状况"""
        impact_assessment = tracking_data.get("impact_assessment", {})
        risk_level = impact_assessment.get("risk_level", "low")
        
        if risk_level == "high":
            return "需要关注"
        elif risk_level == "medium":
            return "基本正常"
        else:
            return "良好"
    
    def _calculate_data_period(self, tracking_data: Dict[str, Any]) -> Dict[str, str]:
        """计算数据周期"""
        # 简化实现，实际应该基于数据时间戳计算
        now = datetime.now()
        return {
            "start_date": (now - timedelta(days=1)).date().isoformat(),
            "end_date": now.date().isoformat()
        }


# 主要的变化跟踪管理器
class ChangeTrackingManager:
    """变化跟踪管理器 - 增强版"""
    
    def __init__(self):
        self.metric_tracker = AdvancedBusinessMetricTracker()
        self.report_generator = AutoReportGenerator()
        
    def run_comprehensive_tracking(self, annotations: List[Dict[str, Any]], 
                                 project_id: str) -> Dict[str, Any]:
        """
        运行综合变化跟踪
        
        Args:
            annotations: 标注数据列表
            project_id: 项目ID
            
        Returns:
            Dict: 综合跟踪结果
        """
        logger.info(f"开始运行项目 {project_id} 的综合变化跟踪")
        
        try:
            # 1. 跟踪业务指标
            tracking_results = self.metric_tracker.track_metrics(annotations)
            
            # 2. 生成自动报告
            daily_report = self.report_generator.generate_report("daily", tracking_results, project_id)
            
            # 3. 检查是否需要生成警报
            alert_report = None
            impact_assessment = tracking_results.get("impact_assessment", {})
            
            if impact_assessment.get("risk_level") in ["high", "critical"]:
                alert_report = self.report_generator.generate_report("alert", tracking_results, project_id)
            
            # 4. 整合结果
            comprehensive_results = {
                "project_id": project_id,
                "tracking_results": tracking_results,
                "daily_report": daily_report,
                "alert_report": alert_report,
                "tracking_timestamp": datetime.now().isoformat(),
                "next_tracking_time": (datetime.now() + timedelta(hours=1)).isoformat()
            }
            
            logger.info(f"项目 {project_id} 综合变化跟踪完成")
            return comprehensive_results
            
        except Exception as e:
            logger.error(f"综合变化跟踪失败: {e}")
            return {"error": str(e), "project_id": project_id}
    
    def get_tracking_summary(self, project_id: str) -> Dict[str, Any]:
        """获取跟踪摘要"""
        try:
            # 获取当前指标历史
            metric_history = {}
            for metric_name, history in self.metric_tracker.metric_history.items():
                if history:
                    timestamps, values = zip(*history)
                    metric_history[metric_name] = {
                        "current_value": values[-1],
                        "trend": "increasing" if len(values) > 1 and values[-1] > values[0] else "stable",
                        "data_points": len(values),
                        "last_updated": timestamps[-1].isoformat()
                    }
            
            baseline_stats = self.metric_tracker.baseline_stats
            
            return {
                "project_id": project_id,
                "metric_history": metric_history,
                "baseline_statistics": baseline_stats,
                "tracking_status": "active",
                "last_analysis": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取跟踪摘要失败: {e}")
            return {"error": str(e), "project_id": project_id}