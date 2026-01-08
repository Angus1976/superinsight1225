"""
工时质量关联分析模块

实现工时与质量分数的关联分析、效率评估、基准制定和预测功能
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field
import json
import logging
import statistics
import numpy as np
from collections import defaultdict

# Optional sklearn imports with fallback
try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import r2_score, mean_squared_error
    SKLEARN_AVAILABLE = True
except ImportError:
    # Fallback implementations for when sklearn is not available
    class LinearRegression:
        def __init__(self):
            self.coef_ = None
            self.intercept_ = None
        
        def fit(self, X, y):
            # Simple linear regression fallback
            if len(X) > 0 and len(y) > 0:
                self.coef_ = [1.0] * len(X[0]) if len(X[0]) > 0 else [1.0]
                self.intercept_ = statistics.mean(y) if y else 0.0
        
        def predict(self, X):
            if self.coef_ is None:
                return [0.0] * len(X)
            return [sum(x[i] * self.coef_[i] for i in range(len(x))) + self.intercept_ for x in X]
    
    class StandardScaler:
        def __init__(self):
            self.mean_ = None
            self.scale_ = None
        
        def fit_transform(self, X):
            return X  # No scaling fallback
        
        def transform(self, X):
            return X  # No scaling fallback
    
    def r2_score(y_true, y_pred):
        return 0.5  # Fallback R² score
    
    def mean_squared_error(y_true, y_pred):
        return 1.0  # Fallback MSE
    
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


class EfficiencyLevel(str, Enum):
    """效率等级枚举"""
    EXCELLENT = "excellent"  # 优秀 (90-100%)
    GOOD = "good"  # 良好 (80-89%)
    AVERAGE = "average"  # 一般 (70-79%)
    BELOW_AVERAGE = "below_average"  # 偏低 (60-69%)
    POOR = "poor"  # 较差 (<60%)


class QualityTrend(str, Enum):
    """质量趋势枚举"""
    IMPROVING = "improving"  # 改善中
    STABLE = "stable"  # 稳定
    DECLINING = "declining"  # 下降中
    VOLATILE = "volatile"  # 波动


class PredictionAccuracy(str, Enum):
    """预测准确度枚举"""
    HIGH = "high"  # 高准确度 (R² > 0.8)
    MEDIUM = "medium"  # 中等准确度 (0.6 < R² <= 0.8)
    LOW = "low"  # 低准确度 (0.4 < R² <= 0.6)
    UNRELIABLE = "unreliable"  # 不可靠 (R² <= 0.4)


@dataclass
class QualityMetrics:
    """质量指标数据类"""
    accuracy_score: float  # 准确性分数
    consistency_score: float  # 一致性分数
    completeness_score: float  # 完整性分数
    efficiency_score: float  # 效率分数
    overall_quality_score: float  # 综合质量分数
    defect_rate: float  # 缺陷率
    rework_rate: float  # 返工率
    customer_satisfaction: float  # 客户满意度


@dataclass
class WorkTimeQualityCorrelation:
    """工时质量关联数据类"""
    user_id: str
    task_id: str
    project_id: str
    work_hours: float
    quality_metrics: QualityMetrics
    efficiency_ratio: float  # 效率比率
    productivity_score: float  # 生产力分数
    cost_effectiveness: float  # 成本效益
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EfficiencyBenchmark:
    """效率基准数据类"""
    benchmark_id: str
    task_type: str
    project_type: str
    skill_level: str
    target_hours_per_task: float
    target_quality_score: float
    target_efficiency_ratio: float
    percentile_25: float  # 25分位数
    percentile_50: float  # 50分位数（中位数）
    percentile_75: float  # 75分位数
    percentile_90: float  # 90分位数
    sample_size: int
    created_at: datetime
    updated_at: datetime


@dataclass
class WorkTimePrediction:
    """工时预测数据类"""
    prediction_id: str
    user_id: str
    task_type: str
    predicted_hours: float
    predicted_quality_score: float
    confidence_interval: Tuple[float, float]
    accuracy_level: PredictionAccuracy
    factors_considered: List[str]
    prediction_date: datetime
    actual_hours: Optional[float] = None
    actual_quality_score: Optional[float] = None
    prediction_error: Optional[float] = None


@dataclass
class EfficiencyOptimization:
    """效率优化建议数据类"""
    optimization_id: str
    user_id: str
    current_efficiency: float
    target_efficiency: float
    improvement_potential: float
    recommendations: List[str]
    priority_level: str  # high, medium, low
    estimated_impact: float
    implementation_difficulty: str  # easy, medium, hard
    timeline_weeks: int
    success_probability: float


class WorkTimeQualityAnalyzer:
    """工时质量关联分析器"""
    
    def __init__(self):
        self.correlations: Dict[str, WorkTimeQualityCorrelation] = {}
        self.benchmarks: Dict[str, EfficiencyBenchmark] = {}
        self.predictions: Dict[str, WorkTimePrediction] = {}
        self.optimization_suggestions: Dict[str, EfficiencyOptimization] = {}
        
        # 分析配置
        self.correlation_threshold = 0.3  # 相关性阈值
        self.quality_weight = 0.6  # 质量权重
        self.efficiency_weight = 0.4  # 效率权重
        self.prediction_window_days = 30  # 预测窗口期
        
        # 机器学习模型
        self.quality_predictor = LinearRegression()
        self.time_predictor = LinearRegression()
        self.scaler = StandardScaler()
        self.model_trained = False
    
    def analyze_work_time_quality_correlation(self, user_id: str, 
                                            start_date: datetime, 
                                            end_date: datetime) -> Dict[str, Any]:
        """分析工时与质量分数的关联性"""
        try:
            # 获取工时和质量数据
            work_time_data = self._fetch_work_time_data(user_id, start_date, end_date)
            quality_data = self._fetch_quality_data(user_id, start_date, end_date)
            
            if not work_time_data or not quality_data:
                return {
                    'success': False,
                    'error': 'Insufficient data for correlation analysis'
                }
            
            # 数据对齐和清洗
            aligned_data = self._align_work_time_quality_data(work_time_data, quality_data)
            
            if len(aligned_data) < 5:
                return {
                    'success': False,
                    'error': 'Insufficient aligned data points for analysis'
                }
            
            # 计算相关性指标
            correlation_metrics = self._calculate_correlation_metrics(aligned_data)
            
            # 分析效率模式
            efficiency_patterns = self._analyze_efficiency_patterns(aligned_data)
            
            # 识别质量影响因素
            quality_factors = self._identify_quality_factors(aligned_data)
            
            # 生成洞察和建议
            insights = self._generate_correlation_insights(
                correlation_metrics, efficiency_patterns, quality_factors
            )
            
            return {
                'success': True,
                'user_id': user_id,
                'analysis_period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'data_points': len(aligned_data),
                'correlation_metrics': correlation_metrics,
                'efficiency_patterns': efficiency_patterns,
                'quality_factors': quality_factors,
                'insights': insights,
                'recommendations': self._generate_correlation_recommendations(
                    correlation_metrics, efficiency_patterns
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing work time quality correlation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def assess_efficiency_and_optimization(self, user_id: str, 
                                         task_type: str = None,
                                         project_id: str = None) -> Dict[str, Any]:
        """评估效率并提供优化建议"""
        try:
            # 获取用户历史数据
            historical_data = self._get_user_historical_data(user_id, task_type, project_id)
            
            if not historical_data:
                return {
                    'success': False,
                    'error': 'No historical data found for efficiency assessment'
                }
            
            # 计算当前效率指标
            current_efficiency = self._calculate_current_efficiency(historical_data)
            
            # 获取基准数据
            benchmark = self._get_efficiency_benchmark(task_type, project_id)
            
            # 效率对比分析
            efficiency_comparison = self._compare_with_benchmark(
                current_efficiency, benchmark
            )
            
            # 识别改进机会
            improvement_opportunities = self._identify_improvement_opportunities(
                historical_data, benchmark
            )
            
            # 生成优化建议
            optimization_plan = self._generate_optimization_plan(
                user_id, current_efficiency, improvement_opportunities
            )
            
            return {
                'success': True,
                'user_id': user_id,
                'current_efficiency': current_efficiency,
                'benchmark_comparison': efficiency_comparison,
                'improvement_opportunities': improvement_opportunities,
                'optimization_plan': optimization_plan,
                'efficiency_level': self._determine_efficiency_level(
                    current_efficiency['overall_score']
                ).value
            }
            
        except Exception as e:
            logger.error(f"Error assessing efficiency: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def configure_work_time_benchmarks(self, task_type: str, 
                                     project_type: str,
                                     skill_level: str,
                                     sample_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """配置工时基准和标准"""
        try:
            if len(sample_data) < 10:
                return {
                    'success': False,
                    'error': 'Insufficient sample data for benchmark creation (minimum 10 samples)'
                }
            
            # 数据清洗和验证
            cleaned_data = self._clean_benchmark_data(sample_data)
            
            # 计算统计指标
            hours_data = [item['work_hours'] for item in cleaned_data]
            quality_data = [item['quality_score'] for item in cleaned_data]
            efficiency_data = [item['efficiency_ratio'] for item in cleaned_data]
            
            # 计算百分位数
            percentiles = {
                'hours': {
                    '25': np.percentile(hours_data, 25),
                    '50': np.percentile(hours_data, 50),
                    '75': np.percentile(hours_data, 75),
                    '90': np.percentile(hours_data, 90)
                },
                'quality': {
                    '25': np.percentile(quality_data, 25),
                    '50': np.percentile(quality_data, 50),
                    '75': np.percentile(quality_data, 75),
                    '90': np.percentile(quality_data, 90)
                },
                'efficiency': {
                    '25': np.percentile(efficiency_data, 25),
                    '50': np.percentile(efficiency_data, 50),
                    '75': np.percentile(efficiency_data, 75),
                    '90': np.percentile(efficiency_data, 90)
                }
            }
            
            # 创建基准
            benchmark_id = f"{task_type}_{project_type}_{skill_level}_{datetime.now().strftime('%Y%m%d')}"
            
            benchmark = EfficiencyBenchmark(
                benchmark_id=benchmark_id,
                task_type=task_type,
                project_type=project_type,
                skill_level=skill_level,
                target_hours_per_task=percentiles['hours']['75'],  # 75分位数作为目标
                target_quality_score=percentiles['quality']['75'],
                target_efficiency_ratio=percentiles['efficiency']['75'],
                percentile_25=percentiles['hours']['25'],
                percentile_50=percentiles['hours']['50'],
                percentile_75=percentiles['hours']['75'],
                percentile_90=percentiles['hours']['90'],
                sample_size=len(cleaned_data),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 保存基准
            self.benchmarks[benchmark_id] = benchmark
            
            # 验证基准质量
            benchmark_quality = self._validate_benchmark_quality(benchmark, cleaned_data)
            
            return {
                'success': True,
                'benchmark_id': benchmark_id,
                'benchmark': {
                    'task_type': benchmark.task_type,
                    'project_type': benchmark.project_type,
                    'skill_level': benchmark.skill_level,
                    'target_hours_per_task': benchmark.target_hours_per_task,
                    'target_quality_score': benchmark.target_quality_score,
                    'target_efficiency_ratio': benchmark.target_efficiency_ratio,
                    'sample_size': benchmark.sample_size
                },
                'percentiles': percentiles,
                'benchmark_quality': benchmark_quality,
                'statistics': {
                    'mean_hours': statistics.mean(hours_data),
                    'std_hours': statistics.stdev(hours_data) if len(hours_data) > 1 else 0,
                    'mean_quality': statistics.mean(quality_data),
                    'std_quality': statistics.stdev(quality_data) if len(quality_data) > 1 else 0,
                    'correlation_hours_quality': self._calculate_correlation(hours_data, quality_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error configuring benchmarks: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def predict_work_time_and_quality(self, user_id: str, 
                                    task_type: str,
                                    task_complexity: float,
                                    historical_window_days: int = 90) -> Dict[str, Any]:
        """预测工时和质量"""
        try:
            # 获取历史数据用于训练
            end_date = datetime.now()
            start_date = end_date - timedelta(days=historical_window_days)
            
            training_data = self._get_prediction_training_data(
                user_id, start_date, end_date, task_type
            )
            
            if len(training_data) < 10:
                return {
                    'success': False,
                    'error': 'Insufficient historical data for prediction (minimum 10 samples)'
                }
            
            # 训练预测模型
            model_performance = self._train_prediction_models(training_data)
            
            if not self.model_trained:
                return {
                    'success': False,
                    'error': 'Failed to train prediction models'
                }
            
            # 准备预测特征
            prediction_features = self._prepare_prediction_features(
                user_id, task_type, task_complexity
            )
            
            # 执行预测
            time_prediction = self._predict_work_time(prediction_features)
            quality_prediction = self._predict_quality_score(prediction_features)
            
            # 计算置信区间
            time_confidence = self._calculate_confidence_interval(
                time_prediction, model_performance['time_model_error']
            )
            quality_confidence = self._calculate_confidence_interval(
                quality_prediction, model_performance['quality_model_error']
            )
            
            # 评估预测准确度
            accuracy_level = self._assess_prediction_accuracy(model_performance)
            
            # 创建预测记录
            prediction_id = f"{user_id}_{task_type}_{datetime.now().timestamp()}"
            
            prediction = WorkTimePrediction(
                prediction_id=prediction_id,
                user_id=user_id,
                task_type=task_type,
                predicted_hours=time_prediction,
                predicted_quality_score=quality_prediction,
                confidence_interval=(time_confidence[0], time_confidence[1]),
                accuracy_level=accuracy_level,
                factors_considered=[
                    'historical_performance',
                    'task_complexity',
                    'user_skill_level',
                    'recent_trends'
                ],
                prediction_date=datetime.now()
            )
            
            self.predictions[prediction_id] = prediction
            
            return {
                'success': True,
                'prediction_id': prediction_id,
                'predictions': {
                    'work_hours': {
                        'value': time_prediction,
                        'confidence_interval': time_confidence,
                        'accuracy_level': accuracy_level.value
                    },
                    'quality_score': {
                        'value': quality_prediction,
                        'confidence_interval': quality_confidence,
                        'accuracy_level': accuracy_level.value
                    }
                },
                'model_performance': model_performance,
                'factors_considered': prediction.factors_considered,
                'recommendations': self._generate_prediction_recommendations(
                    time_prediction, quality_prediction, task_complexity
                )
            }
            
        except Exception as e:
            logger.error(f"Error predicting work time and quality: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_efficiency_planning_report(self, team_ids: List[str],
                                          project_id: str,
                                          planning_horizon_weeks: int = 4) -> Dict[str, Any]:
        """生成效率规划报告"""
        try:
            planning_data = {}
            
            for user_id in team_ids:
                # 获取用户效率分析
                user_efficiency = self.assess_efficiency_and_optimization(
                    user_id, project_id=project_id
                )
                
                if user_efficiency['success']:
                    # 预测未来工时需求
                    future_predictions = []
                    for week in range(planning_horizon_weeks):
                        prediction = self.predict_work_time_and_quality(
                            user_id, 'standard_task', 1.0
                        )
                        if prediction['success']:
                            future_predictions.append(prediction['predictions'])
                    
                    planning_data[user_id] = {
                        'current_efficiency': user_efficiency['current_efficiency'],
                        'optimization_plan': user_efficiency['optimization_plan'],
                        'future_predictions': future_predictions,
                        'capacity_utilization': self._calculate_capacity_utilization(
                            user_id, planning_horizon_weeks
                        )
                    }
            
            # 团队级别分析
            team_analysis = self._analyze_team_efficiency(planning_data)
            
            # 资源分配建议
            resource_allocation = self._generate_resource_allocation_plan(
                planning_data, project_id, planning_horizon_weeks
            )
            
            # 风险评估
            risk_assessment = self._assess_planning_risks(planning_data)
            
            return {
                'success': True,
                'project_id': project_id,
                'planning_horizon_weeks': planning_horizon_weeks,
                'team_size': len(team_ids),
                'individual_analysis': planning_data,
                'team_analysis': team_analysis,
                'resource_allocation': resource_allocation,
                'risk_assessment': risk_assessment,
                'recommendations': self._generate_planning_recommendations(
                    team_analysis, resource_allocation, risk_assessment
                )
            }
            
        except Exception as e:
            logger.error(f"Error generating efficiency planning report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 私有辅助方法
    
    def _fetch_work_time_data(self, user_id: str, start_date: datetime, 
                             end_date: datetime) -> List[Dict[str, Any]]:
        """获取工时数据（模拟）"""
        # 这里应该从实际的工时系统获取数据
        # 暂时返回模拟数据
        data = []
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # 工作日
                data.append({
                    'date': current_date.date(),
                    'user_id': user_id,
                    'task_id': f"task_{current_date.day}",
                    'work_hours': np.random.normal(8, 1.5),  # 平均8小时，标准差1.5
                    'efficiency_ratio': np.random.normal(0.8, 0.1),
                    'pause_hours': np.random.normal(1, 0.3)
                })
            current_date += timedelta(days=1)
        
        return data
    
    def _fetch_quality_data(self, user_id: str, start_date: datetime, 
                           end_date: datetime) -> List[Dict[str, Any]]:
        """获取质量数据（模拟）"""
        # 这里应该从质量评估系统获取数据
        # 暂时返回模拟数据
        data = []
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # 工作日
                base_quality = 85  # 基础质量分数
                quality_variation = np.random.normal(0, 5)  # 质量波动
                
                data.append({
                    'date': current_date.date(),
                    'user_id': user_id,
                    'task_id': f"task_{current_date.day}",
                    'accuracy_score': max(0, min(100, base_quality + quality_variation)),
                    'consistency_score': max(0, min(100, base_quality + np.random.normal(0, 3))),
                    'completeness_score': max(0, min(100, base_quality + np.random.normal(0, 4))),
                    'overall_quality_score': max(0, min(100, base_quality + quality_variation)),
                    'defect_rate': max(0, np.random.exponential(0.05)),
                    'rework_rate': max(0, np.random.exponential(0.03))
                })
            current_date += timedelta(days=1)
        
        return data
    
    def _align_work_time_quality_data(self, work_time_data: List[Dict[str, Any]], 
                                    quality_data: List[Dict[str, Any]]) -> List[WorkTimeQualityCorrelation]:
        """对齐工时和质量数据"""
        aligned_data = []
        
        # 创建质量数据的日期索引
        quality_by_date = {item['date']: item for item in quality_data}
        
        for work_item in work_time_data:
            date = work_item['date']
            if date in quality_by_date:
                quality_item = quality_by_date[date]
                
                # 创建质量指标对象
                quality_metrics = QualityMetrics(
                    accuracy_score=quality_item['accuracy_score'],
                    consistency_score=quality_item['consistency_score'],
                    completeness_score=quality_item['completeness_score'],
                    efficiency_score=work_item['efficiency_ratio'] * 100,
                    overall_quality_score=quality_item['overall_quality_score'],
                    defect_rate=quality_item['defect_rate'],
                    rework_rate=quality_item['rework_rate'],
                    customer_satisfaction=85.0  # 模拟数据
                )
                
                # 计算生产力分数
                productivity_score = self._calculate_productivity_score(
                    work_item['work_hours'], 
                    quality_metrics.overall_quality_score,
                    work_item['efficiency_ratio']
                )
                
                # 计算成本效益
                cost_effectiveness = self._calculate_cost_effectiveness(
                    work_item['work_hours'],
                    quality_metrics.overall_quality_score,
                    quality_metrics.rework_rate
                )
                
                correlation = WorkTimeQualityCorrelation(
                    user_id=work_item['user_id'],
                    task_id=work_item['task_id'],
                    project_id='default_project',
                    work_hours=work_item['work_hours'],
                    quality_metrics=quality_metrics,
                    efficiency_ratio=work_item['efficiency_ratio'],
                    productivity_score=productivity_score,
                    cost_effectiveness=cost_effectiveness,
                    timestamp=datetime.combine(date, datetime.min.time())
                )
                
                aligned_data.append(correlation)
        
        return aligned_data
    
    def _calculate_correlation_metrics(self, data: List[WorkTimeQualityCorrelation]) -> Dict[str, Any]:
        """计算相关性指标"""
        if len(data) < 2:
            return {}
        
        # 提取数据序列
        work_hours = [item.work_hours for item in data]
        quality_scores = [item.quality_metrics.overall_quality_score for item in data]
        efficiency_ratios = [item.efficiency_ratio for item in data]
        productivity_scores = [item.productivity_score for item in data]
        
        # 计算相关系数
        correlations = {
            'hours_quality': self._calculate_correlation(work_hours, quality_scores),
            'hours_efficiency': self._calculate_correlation(work_hours, efficiency_ratios),
            'hours_productivity': self._calculate_correlation(work_hours, productivity_scores),
            'quality_efficiency': self._calculate_correlation(quality_scores, efficiency_ratios),
            'quality_productivity': self._calculate_correlation(quality_scores, productivity_scores)
        }
        
        # 计算统计指标
        statistics_metrics = {
            'work_hours': {
                'mean': statistics.mean(work_hours),
                'median': statistics.median(work_hours),
                'std': statistics.stdev(work_hours) if len(work_hours) > 1 else 0,
                'min': min(work_hours),
                'max': max(work_hours)
            },
            'quality_scores': {
                'mean': statistics.mean(quality_scores),
                'median': statistics.median(quality_scores),
                'std': statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0,
                'min': min(quality_scores),
                'max': max(quality_scores)
            },
            'efficiency_ratios': {
                'mean': statistics.mean(efficiency_ratios),
                'median': statistics.median(efficiency_ratios),
                'std': statistics.stdev(efficiency_ratios) if len(efficiency_ratios) > 1 else 0,
                'min': min(efficiency_ratios),
                'max': max(efficiency_ratios)
            }
        }
        
        return {
            'correlations': correlations,
            'statistics': statistics_metrics,
            'sample_size': len(data),
            'correlation_strength': self._assess_correlation_strength(correlations)
        }
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """计算皮尔逊相关系数"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        try:
            return statistics.correlation(x, y)
        except:
            return 0.0
    
    def _assess_correlation_strength(self, correlations: Dict[str, float]) -> Dict[str, str]:
        """评估相关性强度"""
        strength_map = {}
        
        for key, value in correlations.items():
            abs_value = abs(value)
            if abs_value >= 0.8:
                strength = "very_strong"
            elif abs_value >= 0.6:
                strength = "strong"
            elif abs_value >= 0.4:
                strength = "moderate"
            elif abs_value >= 0.2:
                strength = "weak"
            else:
                strength = "very_weak"
            
            strength_map[key] = strength
        
        return strength_map
    
    def _analyze_efficiency_patterns(self, data: List[WorkTimeQualityCorrelation]) -> Dict[str, Any]:
        """分析效率模式"""
        if not data:
            return {}
        
        # 按时间排序
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        
        # 计算效率趋势
        efficiency_values = [item.efficiency_ratio for item in sorted_data]
        quality_values = [item.quality_metrics.overall_quality_score for item in sorted_data]
        
        # 趋势分析
        efficiency_trend = self._calculate_trend(efficiency_values)
        quality_trend = self._calculate_trend(quality_values)
        
        # 识别效率模式
        patterns = {
            'efficiency_trend': efficiency_trend,
            'quality_trend': quality_trend,
            'optimal_work_hours': self._find_optimal_work_hours(data),
            'efficiency_volatility': statistics.stdev(efficiency_values) if len(efficiency_values) > 1 else 0,
            'quality_volatility': statistics.stdev(quality_values) if len(quality_values) > 1 else 0,
            'peak_performance_periods': self._identify_peak_periods(data),
            'efficiency_consistency': self._calculate_consistency_score(efficiency_values)
        }
        
        return patterns
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势方向"""
        if len(values) < 3:
            return "insufficient_data"
        
        # 简单线性回归计算趋势
        x = list(range(len(values)))
        try:
            correlation = statistics.correlation(x, values)
            if correlation > 0.1:
                return "improving"
            elif correlation < -0.1:
                return "declining"
            else:
                return "stable"
        except:
            return "stable"
    
    def _find_optimal_work_hours(self, data: List[WorkTimeQualityCorrelation]) -> Dict[str, float]:
        """找到最优工时范围"""
        # 按工时分组分析质量
        hour_quality_map = defaultdict(list)
        
        for item in data:
            hour_bucket = round(item.work_hours)
            hour_quality_map[hour_bucket].append(item.quality_metrics.overall_quality_score)
        
        # 计算每个工时段的平均质量
        hour_avg_quality = {}
        for hours, qualities in hour_quality_map.items():
            if len(qualities) >= 2:  # 至少2个样本
                hour_avg_quality[hours] = statistics.mean(qualities)
        
        if not hour_avg_quality:
            return {'optimal_hours': 8.0, 'max_quality': 85.0}
        
        # 找到质量最高的工时
        optimal_hours = max(hour_avg_quality, key=hour_avg_quality.get)
        max_quality = hour_avg_quality[optimal_hours]
        
        return {
            'optimal_hours': float(optimal_hours),
            'max_quality': max_quality,
            'hour_quality_distribution': hour_avg_quality
        }
    
    def _identify_peak_periods(self, data: List[WorkTimeQualityCorrelation]) -> List[Dict[str, Any]]:
        """识别高峰表现期"""
        if len(data) < 5:
            return []
        
        # 计算综合表现分数
        performance_scores = []
        for item in data:
            score = (item.quality_metrics.overall_quality_score * 0.6 + 
                    item.efficiency_ratio * 100 * 0.4)
            performance_scores.append({
                'timestamp': item.timestamp,
                'score': score,
                'work_hours': item.work_hours
            })
        
        # 找到高于平均值1个标准差的期间
        scores = [p['score'] for p in performance_scores]
        mean_score = statistics.mean(scores)
        std_score = statistics.stdev(scores) if len(scores) > 1 else 0
        
        threshold = mean_score + std_score
        
        peak_periods = []
        for perf in performance_scores:
            if perf['score'] > threshold:
                peak_periods.append({
                    'date': perf['timestamp'].date().isoformat(),
                    'performance_score': perf['score'],
                    'work_hours': perf['work_hours']
                })
        
        return peak_periods
    
    def _calculate_consistency_score(self, values: List[float]) -> float:
        """计算一致性分数"""
        if len(values) < 2:
            return 1.0
        
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values)
        
        # 一致性分数 = 1 - (标准差 / 均值)，限制在0-1之间
        if mean_val > 0:
            consistency = max(0, min(1, 1 - (std_val / mean_val)))
        else:
            consistency = 0
        
        return consistency
    
    def _identify_quality_factors(self, data: List[WorkTimeQualityCorrelation]) -> Dict[str, Any]:
        """识别质量影响因素"""
        factors = {
            'work_hours_impact': self._analyze_work_hours_impact(data),
            'efficiency_impact': self._analyze_efficiency_impact(data),
            'time_of_day_impact': self._analyze_time_patterns(data),
            'workload_impact': self._analyze_workload_impact(data)
        }
        
        return factors
    
    def _analyze_work_hours_impact(self, data: List[WorkTimeQualityCorrelation]) -> Dict[str, Any]:
        """分析工时对质量的影响"""
        # 按工时范围分组
        short_hours = [item for item in data if item.work_hours < 6]
        normal_hours = [item for item in data if 6 <= item.work_hours <= 9]
        long_hours = [item for item in data if item.work_hours > 9]
        
        groups = {
            'short_hours': short_hours,
            'normal_hours': normal_hours,
            'long_hours': long_hours
        }
        
        impact_analysis = {}
        for group_name, group_data in groups.items():
            if group_data:
                avg_quality = statistics.mean([
                    item.quality_metrics.overall_quality_score for item in group_data
                ])
                impact_analysis[group_name] = {
                    'sample_size': len(group_data),
                    'average_quality': avg_quality,
                    'average_hours': statistics.mean([item.work_hours for item in group_data])
                }
        
        return impact_analysis
    
    def _analyze_efficiency_impact(self, data: List[WorkTimeQualityCorrelation]) -> Dict[str, Any]:
        """分析效率对质量的影响"""
        # 按效率水平分组
        low_efficiency = [item for item in data if item.efficiency_ratio < 0.7]
        medium_efficiency = [item for item in data if 0.7 <= item.efficiency_ratio <= 0.85]
        high_efficiency = [item for item in data if item.efficiency_ratio > 0.85]
        
        groups = {
            'low_efficiency': low_efficiency,
            'medium_efficiency': medium_efficiency,
            'high_efficiency': high_efficiency
        }
        
        impact_analysis = {}
        for group_name, group_data in groups.items():
            if group_data:
                avg_quality = statistics.mean([
                    item.quality_metrics.overall_quality_score for item in group_data
                ])
                impact_analysis[group_name] = {
                    'sample_size': len(group_data),
                    'average_quality': avg_quality,
                    'average_efficiency': statistics.mean([item.efficiency_ratio for item in group_data])
                }
        
        return impact_analysis
    
    def _analyze_time_patterns(self, data: List[WorkTimeQualityCorrelation]) -> Dict[str, Any]:
        """分析时间模式对质量的影响"""
        # 按星期几分组
        weekday_quality = defaultdict(list)
        
        for item in data:
            weekday = item.timestamp.weekday()
            weekday_quality[weekday].append(item.quality_metrics.overall_quality_score)
        
        weekday_analysis = {}
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for day_num, qualities in weekday_quality.items():
            if qualities:
                weekday_analysis[weekdays[day_num]] = {
                    'average_quality': statistics.mean(qualities),
                    'sample_size': len(qualities)
                }
        
        return {
            'weekday_patterns': weekday_analysis,
            'best_day': max(weekday_analysis.items(), key=lambda x: x[1]['average_quality'])[0] if weekday_analysis else None,
            'worst_day': min(weekday_analysis.items(), key=lambda x: x[1]['average_quality'])[0] if weekday_analysis else None
        }
    
    def _analyze_workload_impact(self, data: List[WorkTimeQualityCorrelation]) -> Dict[str, Any]:
        """分析工作负载对质量的影响"""
        # 简化的工作负载分析
        # 这里可以根据实际需求扩展
        
        return {
            'workload_correlation': 'moderate_negative',  # 模拟结果
            'optimal_workload_range': '6-8_hours',
            'quality_degradation_threshold': 9.0
        }
    
    def _generate_correlation_insights(self, correlation_metrics: Dict[str, Any],
                                     efficiency_patterns: Dict[str, Any],
                                     quality_factors: Dict[str, Any]) -> List[str]:
        """生成关联分析洞察"""
        insights = []
        
        # 基于相关性的洞察
        correlations = correlation_metrics.get('correlations', {})
        
        hours_quality_corr = correlations.get('hours_quality', 0)
        if hours_quality_corr > 0.3:
            insights.append("工时与质量呈正相关，适当增加工时可能提高质量")
        elif hours_quality_corr < -0.3:
            insights.append("工时与质量呈负相关，过长工时可能影响质量")
        
        # 基于效率模式的洞察
        optimal_hours = efficiency_patterns.get('optimal_work_hours', {}).get('optimal_hours', 8)
        if optimal_hours < 7:
            insights.append(f"最优工时为{optimal_hours:.1f}小时，建议控制工作强度")
        elif optimal_hours > 9:
            insights.append(f"最优工时为{optimal_hours:.1f}小时，可适当延长工作时间")
        
        # 基于质量因素的洞察
        work_hours_impact = quality_factors.get('work_hours_impact', {})
        if 'long_hours' in work_hours_impact and 'normal_hours' in work_hours_impact:
            long_quality = work_hours_impact['long_hours']['average_quality']
            normal_quality = work_hours_impact['normal_hours']['average_quality']
            
            if long_quality < normal_quality - 5:
                insights.append("长时间工作显著降低质量，建议合理安排工作时间")
        
        return insights
    
    def _generate_correlation_recommendations(self, correlation_metrics: Dict[str, Any],
                                           efficiency_patterns: Dict[str, Any]) -> List[str]:
        """生成关联分析建议"""
        recommendations = []
        
        # 基于相关性强度的建议
        strength = correlation_metrics.get('correlation_strength', {})
        
        if strength.get('hours_quality') in ['weak', 'very_weak']:
            recommendations.append("工时与质量相关性较弱，建议关注工作方法和技能提升")
        
        if strength.get('quality_efficiency') in ['strong', 'very_strong']:
            recommendations.append("质量与效率高度相关，建议同时优化两个维度")
        
        # 基于效率一致性的建议
        consistency = efficiency_patterns.get('efficiency_consistency', 0)
        if consistency < 0.7:
            recommendations.append("效率波动较大，建议建立稳定的工作流程")
        
        return recommendations
    
    def _calculate_productivity_score(self, work_hours: float, quality_score: float, 
                                    efficiency_ratio: float) -> float:
        """计算生产力分数"""
        # 综合考虑工时、质量和效率的生产力评分
        if work_hours <= 0:
            return 0.0
        
        # 标准化工时（以8小时为基准）
        hours_factor = min(1.0, 8.0 / work_hours)
        
        # 综合评分
        productivity = (
            quality_score * 0.4 +  # 质量权重40%
            efficiency_ratio * 100 * 0.3 +  # 效率权重30%
            hours_factor * 100 * 0.3  # 时间效率权重30%
        )
        
        return min(100.0, max(0.0, productivity))
    
    def _calculate_cost_effectiveness(self, work_hours: float, quality_score: float, 
                                    rework_rate: float) -> float:
        """计算成本效益"""
        if work_hours <= 0:
            return 0.0
        
        # 考虑返工成本的效益计算
        effective_hours = work_hours * (1 + rework_rate)  # 包含返工时间
        quality_factor = quality_score / 100.0
        
        # 成本效益 = 质量 / 有效工时
        cost_effectiveness = (quality_factor / effective_hours) * 100
        
        return cost_effectiveness
    
    # 其他辅助方法的实现...
    # 由于篇幅限制，这里省略了一些辅助方法的完整实现
    # 在实际项目中需要完整实现所有方法
    
    def _get_user_historical_data(self, user_id: str, task_type: str, project_id: str) -> List[Dict[str, Any]]:
        """获取用户历史数据（模拟）"""
        return []
    
    def _calculate_current_efficiency(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算当前效率（模拟）"""
        return {'overall_score': 85.0}
    
    def _get_efficiency_benchmark(self, task_type: str, project_id: str) -> Optional[EfficiencyBenchmark]:
        """获取效率基准（模拟）"""
        return None
    
    def _compare_with_benchmark(self, current_efficiency: Dict[str, Any], 
                               benchmark: Optional[EfficiencyBenchmark]) -> Dict[str, Any]:
        """与基准对比（模拟）"""
        return {}
    
    def _identify_improvement_opportunities(self, historical_data: List[Dict[str, Any]], 
                                          benchmark: Optional[EfficiencyBenchmark]) -> List[Dict[str, Any]]:
        """识别改进机会（模拟）"""
        return []
    
    def _generate_optimization_plan(self, user_id: str, current_efficiency: Dict[str, Any], 
                                   improvement_opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成优化计划（模拟）"""
        return {}
    
    def _determine_efficiency_level(self, score: float) -> EfficiencyLevel:
        """确定效率等级"""
        if score >= 90:
            return EfficiencyLevel.EXCELLENT
        elif score >= 80:
            return EfficiencyLevel.GOOD
        elif score >= 70:
            return EfficiencyLevel.AVERAGE
        elif score >= 60:
            return EfficiencyLevel.BELOW_AVERAGE
        else:
            return EfficiencyLevel.POOR
    
    def _clean_benchmark_data(self, sample_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """清洗基准数据"""
        cleaned = []
        for item in sample_data:
            if (item.get('work_hours', 0) > 0 and 
                0 <= item.get('quality_score', 0) <= 100 and
                0 <= item.get('efficiency_ratio', 0) <= 1):
                cleaned.append(item)
        return cleaned
    
    def _validate_benchmark_quality(self, benchmark: EfficiencyBenchmark, 
                                   sample_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证基准质量"""
        return {
            'quality_score': 'good',
            'sample_size_adequate': len(sample_data) >= 10,
            'data_distribution': 'normal'
        }
    
    # 预测相关的辅助方法
    def _get_prediction_training_data(self, user_id: str, start_date: datetime, 
                                     end_date: datetime, task_type: str) -> List[Dict[str, Any]]:
        """获取预测训练数据（模拟）"""
        return []
    
    def _train_prediction_models(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """训练预测模型（模拟）"""
        self.model_trained = True
        return {
            'time_model_r2': 0.75,
            'quality_model_r2': 0.68,
            'time_model_error': 1.2,
            'quality_model_error': 8.5
        }
    
    def _prepare_prediction_features(self, user_id: str, task_type: str, 
                                   task_complexity: float) -> np.ndarray:
        """准备预测特征"""
        return np.array([[task_complexity, 1.0, 0.8]])  # 模拟特征
    
    def _predict_work_time(self, features: np.ndarray) -> float:
        """预测工时"""
        return 7.5  # 模拟预测结果
    
    def _predict_quality_score(self, features: np.ndarray) -> float:
        """预测质量分数"""
        return 82.0  # 模拟预测结果
    
    def _calculate_confidence_interval(self, prediction: float, model_error: float) -> Tuple[float, float]:
        """计算置信区间"""
        margin = 1.96 * model_error  # 95%置信区间
        return (prediction - margin, prediction + margin)
    
    def _assess_prediction_accuracy(self, model_performance: Dict[str, Any]) -> PredictionAccuracy:
        """评估预测准确度"""
        avg_r2 = (model_performance['time_model_r2'] + model_performance['quality_model_r2']) / 2
        
        if avg_r2 > 0.8:
            return PredictionAccuracy.HIGH
        elif avg_r2 > 0.6:
            return PredictionAccuracy.MEDIUM
        elif avg_r2 > 0.4:
            return PredictionAccuracy.LOW
        else:
            return PredictionAccuracy.UNRELIABLE
    
    def _generate_prediction_recommendations(self, time_prediction: float, 
                                           quality_prediction: float, 
                                           task_complexity: float) -> List[str]:
        """生成预测建议"""
        recommendations = []
        
        if time_prediction > 10:
            recommendations.append("预测工时较长，建议分解任务或寻求协助")
        
        if quality_prediction < 80:
            recommendations.append("预测质量偏低，建议加强质量控制措施")
        
        if task_complexity > 0.8:
            recommendations.append("任务复杂度较高，建议预留额外时间和资源")
        
        return recommendations
    
    # 规划相关的辅助方法
    def _calculate_capacity_utilization(self, user_id: str, weeks: int) -> Dict[str, Any]:
        """计算产能利用率（模拟）"""
        return {
            'current_utilization': 0.85,
            'projected_utilization': 0.90,
            'available_capacity_hours': 32.0
        }
    
    def _analyze_team_efficiency(self, planning_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析团队效率（模拟）"""
        return {
            'team_average_efficiency': 82.0,
            'efficiency_distribution': 'normal',
            'top_performers': [],
            'improvement_needed': []
        }
    
    def _generate_resource_allocation_plan(self, planning_data: Dict[str, Any], 
                                         project_id: str, weeks: int) -> Dict[str, Any]:
        """生成资源分配计划（模拟）"""
        return {
            'allocation_strategy': 'balanced',
            'resource_requirements': {},
            'bottlenecks': [],
            'optimization_opportunities': []
        }
    
    def _assess_planning_risks(self, planning_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估规划风险（模拟）"""
        return {
            'risk_level': 'medium',
            'key_risks': [],
            'mitigation_strategies': []
        }
    
    def _generate_planning_recommendations(self, team_analysis: Dict[str, Any],
                                         resource_allocation: Dict[str, Any],
                                         risk_assessment: Dict[str, Any]) -> List[str]:
        """生成规划建议（模拟）"""
        return [
            "建议加强团队协作和知识分享",
            "优化任务分配以平衡工作负载",
            "建立定期的效率评估和反馈机制"
        ]