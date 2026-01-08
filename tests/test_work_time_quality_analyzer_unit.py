"""
工时质量关联分析系统单元测试

测试工时与质量分数关联分析、效率评估、基准制定和预测功能
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import statistics

# Handle numpy import gracefully
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    # Fallback for numpy functions
    class np:
        @staticmethod
        def random():
            import random
            return random
        
        @staticmethod
        def percentile(data, percentile):
            if not data:
                return 0
            sorted_data = sorted(data)
            index = int(len(sorted_data) * percentile / 100)
            return sorted_data[min(index, len(sorted_data) - 1)]
        
        @staticmethod
        def mean(data):
            return statistics.mean(data) if data else 0
        
        @staticmethod
        def std(data):
            return statistics.stdev(data) if len(data) > 1 else 0
    
    # Mock numpy.random methods
    np.random.normal = lambda mean, std, size=None: mean + (0.1 * std)  # Simple fallback
    np.random.uniform = lambda low, high, size=None: (low + high) / 2  # Simple fallback
    np.random.exponential = lambda scale, size=None: scale  # Simple fallback
    
    NUMPY_AVAILABLE = False

from src.quality_billing.work_time_quality_analyzer import (
    WorkTimeQualityAnalyzer, WorkTimeQualityCorrelation, QualityMetrics,
    EfficiencyBenchmark, WorkTimePrediction, EfficiencyOptimization,
    EfficiencyLevel, QualityTrend, PredictionAccuracy
)


class TestWorkTimeQualityAnalyzer:
    """工时质量关联分析器测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.analyzer = WorkTimeQualityAnalyzer()
        self.user_id = "test_user_001"
        self.task_type = "annotation_task"
        self.project_id = "test_project_001"
    
    def test_analyze_work_time_quality_correlation_success(self):
        """测试成功分析工时质量关联性"""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        # 模拟有足够数据的情况
        with patch.object(self.analyzer, '_fetch_work_time_data') as mock_work_data, \
             patch.object(self.analyzer, '_fetch_quality_data') as mock_quality_data:
            
            # 设置模拟数据
            mock_work_data.return_value = self._create_mock_work_time_data()
            mock_quality_data.return_value = self._create_mock_quality_data()
            
            result = self.analyzer.analyze_work_time_quality_correlation(
                self.user_id, start_date, end_date
            )
            
            assert result['success'] is True
            assert result['user_id'] == self.user_id
            assert 'correlation_metrics' in result
            assert 'efficiency_patterns' in result
            assert 'quality_factors' in result
            assert 'insights' in result
            assert 'recommendations' in result
            assert result['data_points'] > 0
    
    def test_analyze_work_time_quality_correlation_insufficient_data(self):
        """测试数据不足时的关联分析"""
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        # 模拟数据不足的情况
        with patch.object(self.analyzer, '_fetch_work_time_data') as mock_work_data, \
             patch.object(self.analyzer, '_fetch_quality_data') as mock_quality_data:
            
            mock_work_data.return_value = []
            mock_quality_data.return_value = []
            
            result = self.analyzer.analyze_work_time_quality_correlation(
                self.user_id, start_date, end_date
            )
            
            assert result['success'] is False
            assert 'Insufficient data' in result['error']
    
    def test_assess_efficiency_and_optimization_success(self):
        """测试成功评估效率和优化"""
        with patch.object(self.analyzer, '_get_user_historical_data') as mock_historical, \
             patch.object(self.analyzer, '_calculate_current_efficiency') as mock_efficiency, \
             patch.object(self.analyzer, '_get_efficiency_benchmark') as mock_benchmark:
            
            # 设置模拟数据
            mock_historical.return_value = self._create_mock_historical_data()
            mock_efficiency.return_value = {
                'overall_score': 85.0,
                'quality_score': 88.0,
                'speed_score': 82.0,
                'consistency_score': 85.0
            }
            mock_benchmark.return_value = self._create_mock_benchmark()
            
            result = self.analyzer.assess_efficiency_and_optimization(
                self.user_id, self.task_type, self.project_id
            )
            
            assert result['success'] is True
            assert result['user_id'] == self.user_id
            assert 'current_efficiency' in result
            assert 'benchmark_comparison' in result
            assert 'improvement_opportunities' in result
            assert 'optimization_plan' in result
            assert 'efficiency_level' in result
    
    def test_assess_efficiency_no_historical_data(self):
        """测试无历史数据时的效率评估"""
        with patch.object(self.analyzer, '_get_user_historical_data') as mock_historical:
            mock_historical.return_value = []
            
            result = self.analyzer.assess_efficiency_and_optimization(
                self.user_id, self.task_type, self.project_id
            )
            
            assert result['success'] is False
            assert 'No historical data found' in result['error']
    
    def test_configure_work_time_benchmarks_success(self):
        """测试成功配置工时基准"""
        sample_data = self._create_benchmark_sample_data(20)  # 20个样本
        
        result = self.analyzer.configure_work_time_benchmarks(
            self.task_type, "web_annotation", "intermediate", sample_data
        )
        
        assert result['success'] is True
        assert 'benchmark_id' in result
        assert 'benchmark' in result
        assert 'percentiles' in result
        assert 'statistics' in result
        
        benchmark = result['benchmark']
        assert benchmark['task_type'] == self.task_type
        assert benchmark['project_type'] == "web_annotation"
        assert benchmark['skill_level'] == "intermediate"
        assert benchmark['sample_size'] == 20
        
        # 检查百分位数
        percentiles = result['percentiles']
        assert 'hours' in percentiles
        assert 'quality' in percentiles
        assert 'efficiency' in percentiles
        
        # 检查统计指标
        statistics_data = result['statistics']
        assert 'mean_hours' in statistics_data
        assert 'correlation_hours_quality' in statistics_data
    
    def test_configure_work_time_benchmarks_insufficient_samples(self):
        """测试样本不足时的基准配置"""
        sample_data = self._create_benchmark_sample_data(5)  # 只有5个样本
        
        result = self.analyzer.configure_work_time_benchmarks(
            self.task_type, "web_annotation", "intermediate", sample_data
        )
        
        assert result['success'] is False
        assert 'Insufficient sample data' in result['error']
    
    def test_predict_work_time_and_quality_success(self):
        """测试成功预测工时和质量"""
        task_complexity = 0.7
        
        with patch.object(self.analyzer, '_get_prediction_training_data') as mock_training, \
             patch.object(self.analyzer, '_train_prediction_models') as mock_train:
            
            # 设置模拟训练数据
            mock_training.return_value = self._create_prediction_training_data(15)
            mock_train.return_value = {
                'time_model_r2': 0.75,
                'quality_model_r2': 0.68,
                'time_model_error': 1.2,
                'quality_model_error': 8.5
            }
            
            # 模拟模型训练成功
            self.analyzer.model_trained = True
            
            result = self.analyzer.predict_work_time_and_quality(
                self.user_id, self.task_type, task_complexity
            )
            
            assert result['success'] is True
            assert 'prediction_id' in result
            assert 'predictions' in result
            assert 'model_performance' in result
            assert 'recommendations' in result
            
            predictions = result['predictions']
            assert 'work_hours' in predictions
            assert 'quality_score' in predictions
            
            # 检查预测值的合理性
            work_hours_pred = predictions['work_hours']
            assert work_hours_pred['value'] > 0
            assert len(work_hours_pred['confidence_interval']) == 2
            
            quality_pred = predictions['quality_score']
            assert 0 <= quality_pred['value'] <= 100
    
    def test_predict_work_time_and_quality_insufficient_training_data(self):
        """测试训练数据不足时的预测"""
        with patch.object(self.analyzer, '_get_prediction_training_data') as mock_training:
            mock_training.return_value = self._create_prediction_training_data(5)  # 只有5个样本
            
            result = self.analyzer.predict_work_time_and_quality(
                self.user_id, self.task_type, 0.5
            )
            
            assert result['success'] is False
            assert 'Insufficient historical data' in result['error']
    
    def test_generate_efficiency_planning_report_success(self):
        """测试成功生成效率规划报告"""
        team_ids = ["user_001", "user_002", "user_003"]
        planning_horizon_weeks = 4
        
        with patch.object(self.analyzer, 'assess_efficiency_and_optimization') as mock_assess, \
             patch.object(self.analyzer, 'predict_work_time_and_quality') as mock_predict:
            
            # 模拟效率评估结果
            mock_assess.return_value = {
                'success': True,
                'current_efficiency': {'overall_score': 85.0},
                'optimization_plan': {'priority_actions': []}
            }
            
            # 模拟预测结果
            mock_predict.return_value = {
                'success': True,
                'predictions': {
                    'work_hours': {'value': 7.5},
                    'quality_score': {'value': 82.0}
                }
            }
            
            result = self.analyzer.generate_efficiency_planning_report(
                team_ids, self.project_id, planning_horizon_weeks
            )
            
            assert result['success'] is True
            assert result['project_id'] == self.project_id
            assert result['planning_horizon_weeks'] == planning_horizon_weeks
            assert result['team_size'] == len(team_ids)
            assert 'individual_analysis' in result
            assert 'team_analysis' in result
            assert 'resource_allocation' in result
            assert 'risk_assessment' in result
            assert 'recommendations' in result
    
    def test_calculate_correlation_metrics(self):
        """测试计算相关性指标"""
        # 创建测试数据
        correlation_data = self._create_correlation_test_data()
        
        metrics = self.analyzer._calculate_correlation_metrics(correlation_data)
        
        assert 'correlations' in metrics
        assert 'statistics' in metrics
        assert 'sample_size' in metrics
        assert 'correlation_strength' in metrics
        
        correlations = metrics['correlations']
        assert 'hours_quality' in correlations
        assert 'hours_efficiency' in correlations
        assert 'quality_efficiency' in correlations
        
        # 检查相关系数的范围
        for corr_value in correlations.values():
            assert -1 <= corr_value <= 1
        
        # 检查统计指标
        statistics_data = metrics['statistics']
        assert 'work_hours' in statistics_data
        assert 'quality_scores' in statistics_data
        assert 'efficiency_ratios' in statistics_data
        
        for stat_group in statistics_data.values():
            assert 'mean' in stat_group
            assert 'median' in stat_group
            assert 'std' in stat_group
            assert 'min' in stat_group
            assert 'max' in stat_group
    
    def test_analyze_efficiency_patterns(self):
        """测试分析效率模式"""
        correlation_data = self._create_correlation_test_data()
        
        patterns = self.analyzer._analyze_efficiency_patterns(correlation_data)
        
        assert 'efficiency_trend' in patterns
        assert 'quality_trend' in patterns
        assert 'optimal_work_hours' in patterns
        assert 'efficiency_volatility' in patterns
        assert 'peak_performance_periods' in patterns
        assert 'efficiency_consistency' in patterns
        
        # 检查趋势值
        assert patterns['efficiency_trend'] in ['improving', 'declining', 'stable', 'insufficient_data']
        assert patterns['quality_trend'] in ['improving', 'declining', 'stable', 'insufficient_data']
        
        # 检查最优工时
        optimal_hours = patterns['optimal_work_hours']
        assert 'optimal_hours' in optimal_hours
        assert 'max_quality' in optimal_hours
        assert optimal_hours['optimal_hours'] > 0
        assert 0 <= optimal_hours['max_quality'] <= 100
        
        # 检查一致性分数
        assert 0 <= patterns['efficiency_consistency'] <= 1
    
    def test_determine_efficiency_level(self):
        """测试确定效率等级"""
        # 测试各个等级
        assert self.analyzer._determine_efficiency_level(95) == EfficiencyLevel.EXCELLENT
        assert self.analyzer._determine_efficiency_level(85) == EfficiencyLevel.GOOD
        assert self.analyzer._determine_efficiency_level(75) == EfficiencyLevel.AVERAGE
        assert self.analyzer._determine_efficiency_level(65) == EfficiencyLevel.BELOW_AVERAGE
        assert self.analyzer._determine_efficiency_level(55) == EfficiencyLevel.POOR
        
        # 测试边界值
        assert self.analyzer._determine_efficiency_level(90) == EfficiencyLevel.EXCELLENT
        assert self.analyzer._determine_efficiency_level(89.9) == EfficiencyLevel.GOOD
        assert self.analyzer._determine_efficiency_level(80) == EfficiencyLevel.GOOD
        assert self.analyzer._determine_efficiency_level(79.9) == EfficiencyLevel.AVERAGE
    
    def test_calculate_productivity_score(self):
        """测试计算生产力分数"""
        # 测试正常情况
        score1 = self.analyzer._calculate_productivity_score(8.0, 85.0, 0.8)
        assert 0 <= score1 <= 100
        
        # 测试高质量高效率
        score2 = self.analyzer._calculate_productivity_score(8.0, 95.0, 0.9)
        assert score2 > score1  # 应该更高
        
        # 测试工时过长的情况
        score3 = self.analyzer._calculate_productivity_score(12.0, 85.0, 0.8)
        assert score3 < score1  # 应该更低
        
        # 测试边界情况
        score4 = self.analyzer._calculate_productivity_score(0, 85.0, 0.8)
        assert score4 == 0  # 工时为0应该返回0
    
    def test_calculate_cost_effectiveness(self):
        """测试计算成本效益"""
        # 测试正常情况
        ce1 = self.analyzer._calculate_cost_effectiveness(8.0, 85.0, 0.05)
        assert ce1 > 0
        
        # 测试高质量低返工率
        ce2 = self.analyzer._calculate_cost_effectiveness(8.0, 95.0, 0.02)
        assert ce2 > ce1  # 应该更高
        
        # 测试高返工率的情况
        ce3 = self.analyzer._calculate_cost_effectiveness(8.0, 85.0, 0.15)
        assert ce3 < ce1  # 应该更低
        
        # 测试边界情况
        ce4 = self.analyzer._calculate_cost_effectiveness(0, 85.0, 0.05)
        assert ce4 == 0  # 工时为0应该返回0
    
    def test_clean_benchmark_data(self):
        """测试清洗基准数据"""
        # 创建包含无效数据的样本
        dirty_data = [
            {'work_hours': 8.0, 'quality_score': 85.0, 'efficiency_ratio': 0.8},  # 有效
            {'work_hours': -1.0, 'quality_score': 85.0, 'efficiency_ratio': 0.8},  # 无效工时
            {'work_hours': 8.0, 'quality_score': 150.0, 'efficiency_ratio': 0.8},  # 无效质量分数
            {'work_hours': 8.0, 'quality_score': 85.0, 'efficiency_ratio': 1.5},  # 无效效率比率
            {'work_hours': 7.5, 'quality_score': 90.0, 'efficiency_ratio': 0.85},  # 有效
        ]
        
        cleaned_data = self.analyzer._clean_benchmark_data(dirty_data)
        
        # 应该只保留2个有效记录
        assert len(cleaned_data) == 2
        
        # 检查清洗后的数据都是有效的
        for item in cleaned_data:
            assert item['work_hours'] > 0
            assert 0 <= item['quality_score'] <= 100
            assert 0 <= item['efficiency_ratio'] <= 1
    
    def test_assess_prediction_accuracy(self):
        """测试评估预测准确度"""
        # 测试高准确度
        high_perf = {'time_model_r2': 0.85, 'quality_model_r2': 0.82}
        assert self.analyzer._assess_prediction_accuracy(high_perf) == PredictionAccuracy.HIGH
        
        # 测试中等准确度
        medium_perf = {'time_model_r2': 0.75, 'quality_model_r2': 0.68}
        assert self.analyzer._assess_prediction_accuracy(medium_perf) == PredictionAccuracy.MEDIUM
        
        # 测试低准确度
        low_perf = {'time_model_r2': 0.55, 'quality_model_r2': 0.48}
        assert self.analyzer._assess_prediction_accuracy(low_perf) == PredictionAccuracy.LOW
        
        # 测试不可靠
        unreliable_perf = {'time_model_r2': 0.35, 'quality_model_r2': 0.28}
        assert self.analyzer._assess_prediction_accuracy(unreliable_perf) == PredictionAccuracy.UNRELIABLE
    
    # 辅助方法
    
    def _create_mock_work_time_data(self):
        """创建模拟工时数据"""
        data = []
        base_date = datetime.now() - timedelta(days=20)
        
        for i in range(15):  # 15天的数据
            date = base_date + timedelta(days=i)
            if date.weekday() < 5:  # 工作日
                data.append({
                    'date': date.date(),
                    'user_id': self.user_id,
                    'task_id': f"task_{i}",
                    'work_hours': np.random.normal(8, 1),
                    'efficiency_ratio': np.random.normal(0.8, 0.1),
                    'pause_hours': np.random.normal(1, 0.2)
                })
        
        return data
    
    def _create_mock_quality_data(self):
        """创建模拟质量数据"""
        data = []
        base_date = datetime.now() - timedelta(days=20)
        
        for i in range(15):
            date = base_date + timedelta(days=i)
            if date.weekday() < 5:  # 工作日
                base_quality = 85
                variation = np.random.normal(0, 5)
                
                data.append({
                    'date': date.date(),
                    'user_id': self.user_id,
                    'task_id': f"task_{i}",
                    'accuracy_score': max(0, min(100, base_quality + variation)),
                    'consistency_score': max(0, min(100, base_quality + np.random.normal(0, 3))),
                    'completeness_score': max(0, min(100, base_quality + np.random.normal(0, 4))),
                    'overall_quality_score': max(0, min(100, base_quality + variation)),
                    'defect_rate': max(0, np.random.exponential(0.05)),
                    'rework_rate': max(0, np.random.exponential(0.03))
                })
        
        return data
    
    def _create_mock_historical_data(self):
        """创建模拟历史数据"""
        return [
            {'work_hours': 8.0, 'quality_score': 85.0, 'efficiency': 0.8},
            {'work_hours': 7.5, 'quality_score': 88.0, 'efficiency': 0.85},
            {'work_hours': 8.5, 'quality_score': 82.0, 'efficiency': 0.75},
        ]
    
    def _create_mock_benchmark(self):
        """创建模拟基准"""
        return EfficiencyBenchmark(
            benchmark_id="test_benchmark",
            task_type=self.task_type,
            project_type="test_project",
            skill_level="intermediate",
            target_hours_per_task=8.0,
            target_quality_score=85.0,
            target_efficiency_ratio=0.8,
            percentile_25=6.5,
            percentile_50=8.0,
            percentile_75=9.5,
            percentile_90=11.0,
            sample_size=50,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def _create_benchmark_sample_data(self, count: int):
        """创建基准样本数据"""
        data = []
        for i in range(count):
            data.append({
                'work_hours': np.random.normal(8, 1.5),
                'quality_score': np.random.normal(85, 8),
                'efficiency_ratio': np.random.normal(0.8, 0.1)
            })
        return data
    
    def _create_prediction_training_data(self, count: int):
        """创建预测训练数据"""
        data = []
        for i in range(count):
            data.append({
                'work_hours': np.random.normal(8, 1),
                'quality_score': np.random.normal(85, 5),
                'task_complexity': np.random.uniform(0.3, 0.9),
                'user_skill_level': np.random.uniform(0.6, 0.95)
            })
        return data
    
    def _create_correlation_test_data(self):
        """创建关联测试数据"""
        data = []
        base_time = datetime.now() - timedelta(days=10)
        
        for i in range(10):
            timestamp = base_time + timedelta(days=i)
            
            # 创建质量指标
            quality_metrics = QualityMetrics(
                accuracy_score=np.random.normal(85, 5),
                consistency_score=np.random.normal(83, 4),
                completeness_score=np.random.normal(87, 3),
                efficiency_score=np.random.normal(80, 6),
                overall_quality_score=np.random.normal(85, 5),
                defect_rate=np.random.exponential(0.05),
                rework_rate=np.random.exponential(0.03),
                customer_satisfaction=np.random.normal(85, 8)
            )
            
            work_hours = np.random.normal(8, 1)
            efficiency_ratio = np.random.normal(0.8, 0.1)
            
            correlation = WorkTimeQualityCorrelation(
                user_id=self.user_id,
                task_id=f"task_{i}",
                project_id=self.project_id,
                work_hours=work_hours,
                quality_metrics=quality_metrics,
                efficiency_ratio=efficiency_ratio,
                productivity_score=self.analyzer._calculate_productivity_score(
                    work_hours, quality_metrics.overall_quality_score, efficiency_ratio
                ),
                cost_effectiveness=self.analyzer._calculate_cost_effectiveness(
                    work_hours, quality_metrics.overall_quality_score, quality_metrics.rework_rate
                ),
                timestamp=timestamp
            )
            
            data.append(correlation)
        
        return data


class TestQualityMetrics:
    """质量指标测试类"""
    
    def test_quality_metrics_creation(self):
        """测试质量指标创建"""
        metrics = QualityMetrics(
            accuracy_score=85.0,
            consistency_score=83.0,
            completeness_score=87.0,
            efficiency_score=80.0,
            overall_quality_score=85.0,
            defect_rate=0.05,
            rework_rate=0.03,
            customer_satisfaction=88.0
        )
        
        assert metrics.accuracy_score == 85.0
        assert metrics.consistency_score == 83.0
        assert metrics.completeness_score == 87.0
        assert metrics.efficiency_score == 80.0
        assert metrics.overall_quality_score == 85.0
        assert metrics.defect_rate == 0.05
        assert metrics.rework_rate == 0.03
        assert metrics.customer_satisfaction == 88.0


class TestWorkTimeQualityCorrelation:
    """工时质量关联测试类"""
    
    def test_correlation_creation(self):
        """测试关联对象创建"""
        quality_metrics = QualityMetrics(
            accuracy_score=85.0,
            consistency_score=83.0,
            completeness_score=87.0,
            efficiency_score=80.0,
            overall_quality_score=85.0,
            defect_rate=0.05,
            rework_rate=0.03,
            customer_satisfaction=88.0
        )
        
        correlation = WorkTimeQualityCorrelation(
            user_id="test_user",
            task_id="test_task",
            project_id="test_project",
            work_hours=8.0,
            quality_metrics=quality_metrics,
            efficiency_ratio=0.8,
            productivity_score=82.5,
            cost_effectiveness=10.6,
            timestamp=datetime.now()
        )
        
        assert correlation.user_id == "test_user"
        assert correlation.task_id == "test_task"
        assert correlation.project_id == "test_project"
        assert correlation.work_hours == 8.0
        assert correlation.quality_metrics == quality_metrics
        assert correlation.efficiency_ratio == 0.8
        assert correlation.productivity_score == 82.5
        assert correlation.cost_effectiveness == 10.6


class TestEfficiencyBenchmark:
    """效率基准测试类"""
    
    def test_benchmark_creation(self):
        """测试基准创建"""
        benchmark = EfficiencyBenchmark(
            benchmark_id="test_benchmark_001",
            task_type="annotation",
            project_type="web_annotation",
            skill_level="intermediate",
            target_hours_per_task=8.0,
            target_quality_score=85.0,
            target_efficiency_ratio=0.8,
            percentile_25=6.5,
            percentile_50=8.0,
            percentile_75=9.5,
            percentile_90=11.0,
            sample_size=100,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert benchmark.benchmark_id == "test_benchmark_001"
        assert benchmark.task_type == "annotation"
        assert benchmark.project_type == "web_annotation"
        assert benchmark.skill_level == "intermediate"
        assert benchmark.target_hours_per_task == 8.0
        assert benchmark.target_quality_score == 85.0
        assert benchmark.target_efficiency_ratio == 0.8
        assert benchmark.sample_size == 100
        
        # 检查百分位数的合理性
        assert benchmark.percentile_25 <= benchmark.percentile_50
        assert benchmark.percentile_50 <= benchmark.percentile_75
        assert benchmark.percentile_75 <= benchmark.percentile_90


class TestWorkTimePrediction:
    """工时预测测试类"""
    
    def test_prediction_creation(self):
        """测试预测对象创建"""
        prediction = WorkTimePrediction(
            prediction_id="pred_001",
            user_id="test_user",
            task_type="annotation",
            predicted_hours=7.5,
            predicted_quality_score=82.0,
            confidence_interval=(6.5, 8.5),
            accuracy_level=PredictionAccuracy.MEDIUM,
            factors_considered=["historical_performance", "task_complexity"],
            prediction_date=datetime.now()
        )
        
        assert prediction.prediction_id == "pred_001"
        assert prediction.user_id == "test_user"
        assert prediction.task_type == "annotation"
        assert prediction.predicted_hours == 7.5
        assert prediction.predicted_quality_score == 82.0
        assert prediction.confidence_interval == (6.5, 8.5)
        assert prediction.accuracy_level == PredictionAccuracy.MEDIUM
        assert len(prediction.factors_considered) == 2
        assert prediction.actual_hours is None  # 初始值
        assert prediction.actual_quality_score is None  # 初始值


if __name__ == "__main__":
    pytest.main([__file__, "-v"])