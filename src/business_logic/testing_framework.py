#!/usr/bin/env python3
"""
业务逻辑测试框架
实现规则准确性测试、性能基准测试、A/B测试框架

实现需求 13: 客户业务逻辑提炼与智能化 - 任务 48.1
"""

import logging
import time
import uuid
import statistics
from typing import List, Dict, Any, Tuple, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.model_selection import train_test_split
    HAS_SKLEARN = True
except ImportError:
    # 如果没有sklearn，使用简化版本
    HAS_SKLEARN = False
    import statistics
    
    def train_test_split(data, test_size=0.5, random_state=None):
        """简化版数据分割"""
        import random
        if random_state:
            random.seed(random_state)
        
        data_copy = data.copy()
        random.shuffle(data_copy)
        
        split_idx = int(len(data_copy) * (1 - test_size))
        return data_copy[:split_idx], data_copy[split_idx:]
    
    def precision_score(y_true, y_pred, zero_division=0):
        """简化版精确率计算"""
        try:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
            return tp / (tp + fp) if (tp + fp) > 0 else zero_division
        except:
            return zero_division
    
    def recall_score(y_true, y_pred, zero_division=0):
        """简化版召回率计算"""
        try:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
            return tp / (tp + fn) if (tp + fn) > 0 else zero_division
        except:
            return zero_division
    
    def f1_score(y_true, y_pred, zero_division=0):
        """简化版F1分数计算"""
        try:
            p = precision_score(y_true, y_pred, zero_division)
            r = recall_score(y_true, y_pred, zero_division)
            return 2 * p * r / (p + r) if (p + r) > 0 else zero_division
        except:
            return zero_division
import psutil
import threading

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    test_name: str
    test_type: str
    success: bool
    score: float
    metrics: Dict[str, float]
    execution_time: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = None

@dataclass
class PerformanceMetrics:
    """性能指标"""
    execution_time: float
    memory_usage: float
    cpu_usage: float
    throughput: float  # 每秒处理的数据量
    latency: float     # 平均响应时间

class RuleAccuracyTester:
    """规则准确性测试器"""
    
    def __init__(self):
        self.test_results = []
        
    def test_rule_accuracy(self, rules: List[Any], test_data: List[Dict[str, Any]], 
                          target_field: str) -> List[TestResult]:
        """
        测试规则准确性
        
        Args:
            rules: 业务规则列表
            test_data: 测试数据
            target_field: 目标字段名
            
        Returns:
            List[TestResult]: 测试结果列表
        """
        logger.info(f"开始测试 {len(rules)} 个规则的准确性")
        
        test_results = []
        df_test = pd.DataFrame(test_data)
        
        if target_field not in df_test.columns:
            logger.error(f"测试数据中缺少目标字段: {target_field}")
            return []
        
        for i, rule in enumerate(rules):
            try:
                start_time = time.time()
                
                # 应用规则获取预测结果
                predictions = self._apply_rule_to_data(rule, df_test)
                actual = df_test[target_field].tolist()
                
                # 计算准确性指标
                metrics = self._calculate_accuracy_metrics(actual, predictions, rule)
                
                execution_time = time.time() - start_time
                
                # 计算综合分数
                score = self._calculate_rule_score(metrics)
                
                test_result = TestResult(
                    test_id=f"accuracy_test_{uuid.uuid4().hex[:8]}",
                    test_name=f"规则准确性测试 - {getattr(rule, 'name', f'Rule_{i+1}')}",
                    test_type="accuracy",
                    success=True,
                    score=score,
                    metrics=metrics,
                    execution_time=execution_time,
                    details={
                        "rule_id": getattr(rule, 'id', f'rule_{i}'),
                        "test_data_size": len(test_data),
                        "predictions_made": len([p for p in predictions if p is not None])
                    }
                )
                
                test_results.append(test_result)
                
            except Exception as e:
                logger.error(f"规则 {i} 测试失败: {e}")
                test_results.append(TestResult(
                    test_id=f"accuracy_test_{uuid.uuid4().hex[:8]}",
                    test_name=f"规则准确性测试 - Rule_{i+1}",
                    test_type="accuracy",
                    success=False,
                    score=0.0,
                    metrics={},
                    execution_time=0.0,
                    error_message=str(e)
                ))
        
        logger.info(f"规则准确性测试完成，成功测试 {sum(1 for r in test_results if r.success)} 个规则")
        return test_results
    
    def _apply_rule_to_data(self, rule: Any, df: pd.DataFrame) -> List[Any]:
        """将规则应用到数据"""
        predictions = []
        
        for _, row in df.iterrows():
            try:
                # 检查规则条件
                if self._check_rule_conditions(rule, row):
                    # 应用规则结果
                    prediction = getattr(rule.consequent, 'value', None)
                else:
                    prediction = None
                
                predictions.append(prediction)
                
            except Exception as e:
                logger.warning(f"规则应用失败: {e}")
                predictions.append(None)
        
        return predictions
    
    def _check_rule_conditions(self, rule: Any, row: pd.Series) -> bool:
        """检查规则条件是否满足"""
        try:
            conditions = getattr(rule, 'conditions', [])
            
            for condition in conditions:
                field = getattr(condition, 'field', '')
                operator = getattr(condition, 'operator', '')
                value = getattr(condition, 'value', '')
                
                if field not in row:
                    return False
                
                row_value = row[field]
                
                if operator == 'contains':
                    if not isinstance(row_value, str) or str(value).lower() not in row_value.lower():
                        return False
                elif operator == 'equals':
                    if row_value != value:
                        return False
                elif operator == 'greater_than':
                    if not (isinstance(row_value, (int, float)) and row_value > value):
                        return False
                elif operator == 'less_than':
                    if not (isinstance(row_value, (int, float)) and row_value < value):
                        return False
            
            return True
            
        except Exception as e:
            logger.warning(f"条件检查失败: {e}")
            return False
    
    def _calculate_accuracy_metrics(self, actual: List[Any], predictions: List[Any], rule: Any) -> Dict[str, float]:
        """计算准确性指标"""
        try:
            # 过滤有效预测
            valid_pairs = [(a, p) for a, p in zip(actual, predictions) if p is not None]
            
            if not valid_pairs:
                return {
                    "accuracy": 0.0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0,
                    "coverage": 0.0,
                    "support": 0
                }
            
            actual_valid, pred_valid = zip(*valid_pairs)
            
            # 计算基本指标
            accuracy = sum(1 for a, p in valid_pairs if a == p) / len(valid_pairs)
            coverage = len(valid_pairs) / len(actual)
            support = len(valid_pairs)
            
            # 对于分类问题，计算精确率、召回率、F1分数
            try:
                # 转换为二分类问题（规则预测值 vs 其他）
                rule_value = getattr(rule.consequent, 'value', None)
                
                if rule_value is not None:
                    y_true = [1 if a == rule_value else 0 for a in actual_valid]
                    y_pred = [1 if p == rule_value else 0 for p in pred_valid]
                    
                    precision = precision_score(y_true, y_pred, zero_division=0)
                    recall = recall_score(y_true, y_pred, zero_division=0)
                    f1 = f1_score(y_true, y_pred, zero_division=0)
                else:
                    precision = recall = f1 = 0.0
                    
            except Exception:
                precision = recall = f1 = 0.0
            
            return {
                "accuracy": round(accuracy, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "coverage": round(coverage, 4),
                "support": support
            }
            
        except Exception as e:
            logger.error(f"准确性指标计算失败: {e}")
            return {
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "coverage": 0.0,
                "support": 0
            }
    
    def _calculate_rule_score(self, metrics: Dict[str, float]) -> float:
        """计算规则综合分数"""
        try:
            # 加权综合分数
            score = (
                metrics.get("accuracy", 0) * 0.3 +
                metrics.get("precision", 0) * 0.25 +
                metrics.get("recall", 0) * 0.25 +
                metrics.get("f1_score", 0) * 0.2
            )
            
            # 考虑覆盖率的惩罚
            coverage = metrics.get("coverage", 0)
            if coverage < 0.1:  # 覆盖率太低
                score *= 0.5
            
            return round(score, 4)
            
        except Exception as e:
            logger.error(f"规则分数计算失败: {e}")
            return 0.0

class PerformanceBenchmarkTester:
    """性能基准测试器"""
    
    def __init__(self):
        self.benchmark_results = []
        
    def run_performance_benchmark(self, algorithm_func: Callable, 
                                test_data: List[Dict[str, Any]], 
                                test_name: str,
                                iterations: int = 5) -> TestResult:
        """
        运行性能基准测试
        
        Args:
            algorithm_func: 要测试的算法函数
            test_data: 测试数据
            test_name: 测试名称
            iterations: 测试迭代次数
            
        Returns:
            TestResult: 测试结果
        """
        logger.info(f"开始性能基准测试: {test_name}")
        
        try:
            performance_metrics = []
            
            for i in range(iterations):
                logger.info(f"执行第 {i+1}/{iterations} 次测试")
                
                # 测量性能指标
                metrics = self._measure_performance(algorithm_func, test_data)
                performance_metrics.append(metrics)
            
            # 计算平均性能指标
            avg_metrics = self._calculate_average_metrics(performance_metrics)
            
            # 计算性能分数
            score = self._calculate_performance_score(avg_metrics)
            
            test_result = TestResult(
                test_id=f"perf_test_{uuid.uuid4().hex[:8]}",
                test_name=f"性能基准测试 - {test_name}",
                test_type="performance",
                success=True,
                score=score,
                metrics={
                    "avg_execution_time": avg_metrics.execution_time,
                    "avg_memory_usage": avg_metrics.memory_usage,
                    "avg_cpu_usage": avg_metrics.cpu_usage,
                    "throughput": avg_metrics.throughput,
                    "latency": avg_metrics.latency
                },
                execution_time=avg_metrics.execution_time,
                details={
                    "iterations": iterations,
                    "test_data_size": len(test_data),
                    "individual_results": [
                        {
                            "execution_time": m.execution_time,
                            "memory_usage": m.memory_usage,
                            "cpu_usage": m.cpu_usage,
                            "throughput": m.throughput
                        } for m in performance_metrics
                    ]
                }
            )
            
            logger.info(f"性能基准测试完成: {test_name}")
            return test_result
            
        except Exception as e:
            logger.error(f"性能基准测试失败: {e}")
            return TestResult(
                test_id=f"perf_test_{uuid.uuid4().hex[:8]}",
                test_name=f"性能基准测试 - {test_name}",
                test_type="performance",
                success=False,
                score=0.0,
                metrics={},
                execution_time=0.0,
                error_message=str(e)
            )
    
    def _measure_performance(self, algorithm_func: Callable, 
                           test_data: List[Dict[str, Any]]) -> PerformanceMetrics:
        """测量性能指标"""
        # 获取初始系统状态
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # CPU使用率监控
        cpu_percent_before = psutil.cpu_percent(interval=None)
        
        # 执行算法
        start_time = time.time()
        
        try:
            result = algorithm_func(test_data)
            success = True
        except Exception as e:
            logger.warning(f"算法执行出错: {e}")
            result = None
            success = False
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 获取最终系统状态
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_usage = final_memory - initial_memory
        
        cpu_percent_after = psutil.cpu_percent(interval=None)
        cpu_usage = max(0, cpu_percent_after - cpu_percent_before)
        
        # 计算吞吐量和延迟
        data_size = len(test_data)
        throughput = data_size / execution_time if execution_time > 0 else 0
        latency = execution_time / data_size if data_size > 0 else execution_time
        
        return PerformanceMetrics(
            execution_time=execution_time,
            memory_usage=max(0, memory_usage),
            cpu_usage=cpu_usage,
            throughput=throughput,
            latency=latency
        )
    
    def _calculate_average_metrics(self, metrics_list: List[PerformanceMetrics]) -> PerformanceMetrics:
        """计算平均性能指标"""
        if not metrics_list:
            return PerformanceMetrics(0, 0, 0, 0, 0)
        
        return PerformanceMetrics(
            execution_time=statistics.mean(m.execution_time for m in metrics_list),
            memory_usage=statistics.mean(m.memory_usage for m in metrics_list),
            cpu_usage=statistics.mean(m.cpu_usage for m in metrics_list),
            throughput=statistics.mean(m.throughput for m in metrics_list),
            latency=statistics.mean(m.latency for m in metrics_list)
        )
    
    def _calculate_performance_score(self, metrics: PerformanceMetrics) -> float:
        """计算性能分数"""
        try:
            # 基于执行时间、内存使用、吞吐量的综合评分
            # 分数越高表示性能越好
            
            # 执行时间分数 (越短越好)
            time_score = max(0, 1 - metrics.execution_time / 10)  # 假设10秒为基准
            
            # 内存使用分数 (越少越好)
            memory_score = max(0, 1 - metrics.memory_usage / 100)  # 假设100MB为基准
            
            # 吞吐量分数 (越高越好)
            throughput_score = min(1, metrics.throughput / 100)  # 假设100条/秒为满分
            
            # 综合分数
            score = (
                time_score * 0.4 +
                memory_score * 0.3 +
                throughput_score * 0.3
            )
            
            return round(score, 4)
            
        except Exception as e:
            logger.error(f"性能分数计算失败: {e}")
            return 0.0

class ABTestFramework:
    """A/B测试框架"""
    
    def __init__(self):
        self.active_tests = {}
        self.test_results = {}
        
    def create_ab_test(self, test_name: str, 
                      algorithm_a: Callable, 
                      algorithm_b: Callable,
                      test_data: List[Dict[str, Any]],
                      split_ratio: float = 0.5,
                      success_metric: str = "accuracy") -> str:
        """
        创建A/B测试
        
        Args:
            test_name: 测试名称
            algorithm_a: 算法A
            algorithm_b: 算法B
            test_data: 测试数据
            split_ratio: 数据分割比例
            success_metric: 成功指标
            
        Returns:
            str: 测试ID
        """
        test_id = f"ab_test_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"创建A/B测试: {test_name} (ID: {test_id})")
        
        try:
            # 随机分割数据
            data_a, data_b = train_test_split(
                test_data, test_size=1-split_ratio, random_state=42
            )
            
            test_config = {
                "test_id": test_id,
                "test_name": test_name,
                "algorithm_a": algorithm_a,
                "algorithm_b": algorithm_b,
                "data_a": data_a,
                "data_b": data_b,
                "split_ratio": split_ratio,
                "success_metric": success_metric,
                "created_at": datetime.now(),
                "status": "created"
            }
            
            self.active_tests[test_id] = test_config
            
            logger.info(f"A/B测试创建成功: {test_id}")
            return test_id
            
        except Exception as e:
            logger.error(f"A/B测试创建失败: {e}")
            raise
    
    def run_ab_test(self, test_id: str) -> TestResult:
        """
        运行A/B测试
        
        Args:
            test_id: 测试ID
            
        Returns:
            TestResult: 测试结果
        """
        if test_id not in self.active_tests:
            raise ValueError(f"测试ID不存在: {test_id}")
        
        test_config = self.active_tests[test_id]
        test_config["status"] = "running"
        
        logger.info(f"开始运行A/B测试: {test_config['test_name']}")
        
        try:
            start_time = time.time()
            
            # 并行运行两个算法
            with ThreadPoolExecutor(max_workers=2) as executor:
                # 提交任务
                future_a = executor.submit(
                    self._run_algorithm_with_metrics, 
                    test_config["algorithm_a"], 
                    test_config["data_a"],
                    "Algorithm A"
                )
                future_b = executor.submit(
                    self._run_algorithm_with_metrics,
                    test_config["algorithm_b"],
                    test_config["data_b"],
                    "Algorithm B"
                )
                
                # 等待结果
                result_a = future_a.result()
                result_b = future_b.result()
            
            execution_time = time.time() - start_time
            
            # 比较结果
            comparison = self._compare_ab_results(result_a, result_b, test_config["success_metric"])
            
            # 创建测试结果
            test_result = TestResult(
                test_id=test_id,
                test_name=f"A/B测试 - {test_config['test_name']}",
                test_type="ab_test",
                success=True,
                score=comparison["confidence"],
                metrics={
                    "algorithm_a_score": result_a["score"],
                    "algorithm_b_score": result_b["score"],
                    "winner": comparison["winner"],
                    "improvement": comparison["improvement"],
                    "statistical_significance": comparison["statistical_significance"]
                },
                execution_time=execution_time,
                details={
                    "algorithm_a_results": result_a,
                    "algorithm_b_results": result_b,
                    "comparison_details": comparison,
                    "data_split": {
                        "algorithm_a_samples": len(test_config["data_a"]),
                        "algorithm_b_samples": len(test_config["data_b"])
                    }
                }
            )
            
            # 保存结果
            self.test_results[test_id] = test_result
            test_config["status"] = "completed"
            
            logger.info(f"A/B测试完成: {test_config['test_name']}, 获胜者: {comparison['winner']}")
            return test_result
            
        except Exception as e:
            logger.error(f"A/B测试运行失败: {e}")
            test_config["status"] = "failed"
            
            return TestResult(
                test_id=test_id,
                test_name=f"A/B测试 - {test_config['test_name']}",
                test_type="ab_test",
                success=False,
                score=0.0,
                metrics={},
                execution_time=0.0,
                error_message=str(e)
            )
    
    def _run_algorithm_with_metrics(self, algorithm: Callable, 
                                  data: List[Dict[str, Any]], 
                                  algorithm_name: str) -> Dict[str, Any]:
        """运行算法并收集指标"""
        try:
            start_time = time.time()
            
            # 运行算法
            result = algorithm(data)
            
            execution_time = time.time() - start_time
            
            # 计算基本指标
            score = self._calculate_algorithm_score(result, data)
            
            return {
                "algorithm_name": algorithm_name,
                "success": True,
                "score": score,
                "execution_time": execution_time,
                "data_size": len(data),
                "result": result
            }
            
        except Exception as e:
            logger.error(f"算法 {algorithm_name} 运行失败: {e}")
            return {
                "algorithm_name": algorithm_name,
                "success": False,
                "score": 0.0,
                "execution_time": 0.0,
                "data_size": len(data),
                "error": str(e)
            }
    
    def _calculate_algorithm_score(self, result: Any, data: List[Dict[str, Any]]) -> float:
        """计算算法分数"""
        try:
            # 简化的分数计算逻辑
            # 实际应用中应该根据具体的业务指标来计算
            
            if isinstance(result, dict):
                # 如果结果是字典，尝试提取分数
                if "score" in result:
                    return float(result["score"])
                elif "accuracy" in result:
                    return float(result["accuracy"])
                elif "confidence" in result:
                    return float(result["confidence"])
            
            # 默认基于数据处理成功率
            return 1.0 if result is not None else 0.0
            
        except Exception as e:
            logger.warning(f"算法分数计算失败: {e}")
            return 0.0
    
    def _compare_ab_results(self, result_a: Dict[str, Any], 
                          result_b: Dict[str, Any], 
                          success_metric: str) -> Dict[str, Any]:
        """比较A/B测试结果"""
        try:
            score_a = result_a.get("score", 0)
            score_b = result_b.get("score", 0)
            
            # 确定获胜者
            if score_a > score_b:
                winner = "Algorithm A"
                improvement = (score_a - score_b) / score_b * 100 if score_b > 0 else 0
            elif score_b > score_a:
                winner = "Algorithm B"
                improvement = (score_b - score_a) / score_a * 100 if score_a > 0 else 0
            else:
                winner = "Tie"
                improvement = 0
            
            # 计算统计显著性（简化版本）
            score_diff = abs(score_a - score_b)
            avg_score = (score_a + score_b) / 2
            
            # 简单的显著性检验
            if avg_score > 0:
                relative_diff = score_diff / avg_score
                statistical_significance = relative_diff > 0.05  # 5%阈值
            else:
                statistical_significance = False
            
            # 置信度计算
            confidence = min(1.0, score_diff * 2)  # 简化的置信度计算
            
            return {
                "winner": winner,
                "improvement": round(improvement, 2),
                "statistical_significance": statistical_significance,
                "confidence": round(confidence, 4),
                "score_difference": round(score_diff, 4),
                "relative_improvement": round(improvement, 2)
            }
            
        except Exception as e:
            logger.error(f"A/B结果比较失败: {e}")
            return {
                "winner": "Unknown",
                "improvement": 0,
                "statistical_significance": False,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def get_test_status(self, test_id: str) -> Dict[str, Any]:
        """获取测试状态"""
        if test_id not in self.active_tests:
            return {"error": "测试ID不存在"}
        
        test_config = self.active_tests[test_id]
        
        status_info = {
            "test_id": test_id,
            "test_name": test_config["test_name"],
            "status": test_config["status"],
            "created_at": test_config["created_at"].isoformat(),
            "data_split": {
                "algorithm_a_samples": len(test_config["data_a"]),
                "algorithm_b_samples": len(test_config["data_b"])
            }
        }
        
        # 如果测试已完成，添加结果
        if test_id in self.test_results:
            result = self.test_results[test_id]
            status_info["result"] = {
                "success": result.success,
                "winner": result.metrics.get("winner", "Unknown"),
                "improvement": result.metrics.get("improvement", 0),
                "execution_time": result.execution_time
            }
        
        return status_info
    
    def list_active_tests(self) -> List[Dict[str, Any]]:
        """列出所有活跃测试"""
        return [
            {
                "test_id": test_id,
                "test_name": config["test_name"],
                "status": config["status"],
                "created_at": config["created_at"].isoformat()
            }
            for test_id, config in self.active_tests.items()
        ]

class TestingFrameworkManager:
    """测试框架管理器"""
    
    def __init__(self):
        self.accuracy_tester = RuleAccuracyTester()
        self.performance_tester = PerformanceBenchmarkTester()
        self.ab_framework = ABTestFramework()
        
    def run_comprehensive_testing(self, rules: List[Any], 
                                algorithms: Dict[str, Callable],
                                test_data: List[Dict[str, Any]],
                                target_field: str = "sentiment") -> Dict[str, Any]:
        """
        运行综合测试
        
        Args:
            rules: 业务规则列表
            algorithms: 算法字典
            test_data: 测试数据
            target_field: 目标字段
            
        Returns:
            Dict: 综合测试结果
        """
        logger.info("开始运行综合测试框架")
        
        comprehensive_results = {
            "testing_timestamp": datetime.now().isoformat(),
            "test_data_size": len(test_data),
            "rules_tested": len(rules),
            "algorithms_tested": len(algorithms),
            "accuracy_tests": [],
            "performance_tests": [],
            "ab_tests": [],
            "summary": {}
        }
        
        try:
            # 1. 规则准确性测试
            if rules:
                logger.info("运行规则准确性测试")
                accuracy_results = self.accuracy_tester.test_rule_accuracy(
                    rules, test_data, target_field
                )
                comprehensive_results["accuracy_tests"] = [
                    {
                        "test_id": r.test_id,
                        "test_name": r.test_name,
                        "success": r.success,
                        "score": r.score,
                        "metrics": r.metrics,
                        "execution_time": r.execution_time,
                        "error": r.error_message
                    } for r in accuracy_results
                ]
            
            # 2. 性能基准测试
            if algorithms:
                logger.info("运行性能基准测试")
                performance_results = []
                
                for algo_name, algo_func in algorithms.items():
                    perf_result = self.performance_tester.run_performance_benchmark(
                        algo_func, test_data, algo_name
                    )
                    performance_results.append(perf_result)
                
                comprehensive_results["performance_tests"] = [
                    {
                        "test_id": r.test_id,
                        "test_name": r.test_name,
                        "success": r.success,
                        "score": r.score,
                        "metrics": r.metrics,
                        "execution_time": r.execution_time,
                        "error": r.error_message
                    } for r in performance_results
                ]
            
            # 3. A/B测试（如果有多个算法）
            if len(algorithms) >= 2:
                logger.info("运行A/B测试")
                algo_names = list(algorithms.keys())
                
                # 创建并运行A/B测试
                test_id = self.ab_framework.create_ab_test(
                    f"算法对比: {algo_names[0]} vs {algo_names[1]}",
                    algorithms[algo_names[0]],
                    algorithms[algo_names[1]],
                    test_data
                )
                
                ab_result = self.ab_framework.run_ab_test(test_id)
                
                comprehensive_results["ab_tests"] = [{
                    "test_id": ab_result.test_id,
                    "test_name": ab_result.test_name,
                    "success": ab_result.success,
                    "score": ab_result.score,
                    "metrics": ab_result.metrics,
                    "execution_time": ab_result.execution_time,
                    "error": ab_result.error_message
                }]
            
            # 4. 生成测试摘要
            comprehensive_results["summary"] = self._generate_testing_summary(
                comprehensive_results
            )
            
            logger.info("综合测试框架运行完成")
            return comprehensive_results
            
        except Exception as e:
            logger.error(f"综合测试运行失败: {e}")
            comprehensive_results["error"] = str(e)
            return comprehensive_results
    
    def _generate_testing_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试摘要"""
        try:
            summary = {
                "total_tests": 0,
                "successful_tests": 0,
                "failed_tests": 0,
                "average_score": 0.0,
                "best_performing_algorithm": None,
                "recommendations": []
            }
            
            all_tests = []
            all_tests.extend(results.get("accuracy_tests", []))
            all_tests.extend(results.get("performance_tests", []))
            all_tests.extend(results.get("ab_tests", []))
            
            if all_tests:
                summary["total_tests"] = len(all_tests)
                summary["successful_tests"] = sum(1 for t in all_tests if t["success"])
                summary["failed_tests"] = summary["total_tests"] - summary["successful_tests"]
                
                # 计算平均分数
                successful_tests = [t for t in all_tests if t["success"]]
                if successful_tests:
                    summary["average_score"] = statistics.mean(t["score"] for t in successful_tests)
                    
                    # 找到最佳算法
                    best_test = max(successful_tests, key=lambda x: x["score"])
                    summary["best_performing_algorithm"] = best_test["test_name"]
            
            # 生成建议
            recommendations = []
            
            if summary["failed_tests"] > 0:
                recommendations.append(f"有 {summary['failed_tests']} 个测试失败，需要检查算法实现")
            
            if summary["average_score"] < 0.7:
                recommendations.append("整体性能偏低，建议优化算法或增加训练数据")
            elif summary["average_score"] > 0.9:
                recommendations.append("性能表现优秀，可以考虑部署到生产环境")
            
            if not recommendations:
                recommendations.append("测试结果正常，继续监控性能表现")
            
            summary["recommendations"] = recommendations
            
            return summary
            
        except Exception as e:
            logger.error(f"测试摘要生成失败: {e}")
            return {"error": str(e)}
    
    def get_testing_status(self) -> Dict[str, Any]:
        """获取测试框架状态"""
        return {
            "framework_status": "active",
            "active_ab_tests": len(self.ab_framework.active_tests),
            "completed_ab_tests": len(self.ab_framework.test_results),
            "last_updated": datetime.now().isoformat(),
            "components": {
                "accuracy_tester": "loaded",
                "performance_tester": "loaded",
                "ab_framework": "loaded"
            }
        }