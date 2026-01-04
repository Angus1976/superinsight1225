"""
i18n 性能测试
测试翻译系统的性能特征
"""

import pytest
import time
import threading
import concurrent.futures
from typing import List, Dict, Any
import gc
import psutil
import os

from src.i18n import (
    get_translation,
    set_language,
    get_current_language,
    get_all_translations,
    get_performance_statistics,
    reset_translation_performance_stats,
    optimize_translation_memory,
    reinitialize_performance_optimizations,
    configure_performance
)
from src.i18n.performance import (
    get_performance_report,
    reset_performance_stats,
    COMMON_TRANSLATION_KEYS
)


class TestTranslationLookupPerformance:
    """翻译查找性能测试"""
    
    def setup_method(self):
        """测试前重置性能统计"""
        reset_translation_performance_stats()
        set_language('zh')
    
    def test_single_translation_lookup_performance(self):
        """测试单次翻译查找性能"""
        # 预热
        for _ in range(10):
            get_translation('app_name')
        
        # 重置统计
        reset_translation_performance_stats()
        
        # 测试单次查找
        start_time = time.perf_counter()
        result = get_translation('app_name')
        end_time = time.perf_counter()
        
        lookup_time = end_time - start_time
        
        # 验证结果正确
        assert result == 'SuperInsight 平台'
        
        # 验证性能要求：单次查找应在1ms内完成
        assert lookup_time < 0.001, f"查找时间 {lookup_time:.6f}s 超过1ms限制"
        
        # 验证性能统计
        stats = get_performance_statistics()
        assert stats['lookup_count'] >= 1
        assert stats['avg_lookup_time'] < 0.001
    
    def test_batch_translation_lookup_performance(self):
        """测试批量翻译查找性能"""
        # 准备测试键
        test_keys = [
            'app_name', 'login', 'logout', 'error', 'success',
            'warning', 'info', 'status', 'healthy', 'unhealthy'
        ]
        
        # 重置统计
        reset_translation_performance_stats()
        
        # 测试批量查找
        start_time = time.perf_counter()
        results = [get_translation(key) for key in test_keys]
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        avg_time_per_lookup = total_time / len(test_keys)
        
        # 验证所有结果都正确
        assert len(results) == len(test_keys)
        assert all(result for result in results)
        
        # 验证性能要求：平均每次查找应在0.1ms内完成
        assert avg_time_per_lookup < 0.0001, f"平均查找时间 {avg_time_per_lookup:.6f}s 超过0.1ms限制"
        
        # 验证性能统计
        stats = get_performance_statistics()
        assert stats['lookup_count'] >= len(test_keys)
    
    def test_common_keys_cache_performance(self):
        """测试常用键缓存性能"""
        # 测试常用键（应该被预计算缓存）
        common_key = 'app_name'
        assert common_key in COMMON_TRANSLATION_KEYS
        
        # 重置统计
        reset_translation_performance_stats()
        
        # 多次查找同一个常用键
        times = []
        for _ in range(100):
            start_time = time.perf_counter()
            result = get_translation(common_key)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
            assert result == 'SuperInsight 平台'
        
        # 验证缓存效果：后续查找应该更快
        first_10_avg = sum(times[:10]) / 10
        last_10_avg = sum(times[-10:]) / 10
        
        # 缓存预热后，查找时间应该更稳定且更快
        assert last_10_avg <= first_10_avg * 1.5, "缓存未显著提升性能"
        
        # 验证缓存命中率
        stats = get_performance_statistics()
        assert stats['cache_hit_rate'] > 0.5, "缓存命中率过低"
    
    def test_different_language_performance(self):
        """测试不同语言的查找性能"""
        test_key = 'app_name'
        languages = ['zh', 'en']
        
        performance_by_language = {}
        
        for language in languages:
            set_language(language)
            reset_translation_performance_stats()
            
            # 测试查找性能
            start_time = time.perf_counter()
            for _ in range(100):
                get_translation(test_key)
            end_time = time.perf_counter()
            
            avg_time = (end_time - start_time) / 100
            performance_by_language[language] = avg_time
        
        # 验证不同语言的性能差异不应过大
        zh_time = performance_by_language['zh']
        en_time = performance_by_language['en']
        
        # 性能差异不应超过50%
        ratio = max(zh_time, en_time) / min(zh_time, en_time)
        assert ratio < 1.5, f"语言间性能差异过大: zh={zh_time:.6f}s, en={en_time:.6f}s"


class TestMemoryUsageOptimization:
    """内存使用优化测试"""
    
    def setup_method(self):
        """测试前重置"""
        reset_translation_performance_stats()
        set_language('zh')
    
    def get_memory_usage(self) -> float:
        """获取当前进程内存使用量（MB）"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def test_memory_usage_baseline(self):
        """测试基础内存使用"""
        # 获取初始内存使用
        initial_memory = self.get_memory_usage()
        
        # 执行一些翻译操作
        for _ in range(1000):
            get_translation('app_name')
            get_translation('login')
            get_translation('logout')
        
        # 获取操作后内存使用
        after_memory = self.get_memory_usage()
        
        # 内存增长应该很小（小于10MB）
        memory_growth = after_memory - initial_memory
        assert memory_growth < 10, f"内存增长过大: {memory_growth:.2f}MB"
    
    def test_memory_optimization_function(self):
        """测试内存优化功能"""
        # 执行大量翻译操作以产生缓存
        for i in range(1000):
            get_translation(f'key_{i % 100}')  # 会产生很多缓存未命中
        
        # 获取优化前内存
        before_memory = self.get_memory_usage()
        
        # 执行内存优化
        optimization_report = optimize_translation_memory()
        
        # 获取优化后内存
        after_memory = self.get_memory_usage()
        
        # 验证优化报告
        assert isinstance(optimization_report, dict)
        assert 'garbage_collected_objects' in optimization_report
        assert 'memory_freed' in optimization_report
        
        # 内存使用应该减少或保持稳定
        memory_change = after_memory - before_memory
        assert memory_change <= 5, f"内存优化后内存反而增加: {memory_change:.2f}MB"
    
    def test_cache_size_limits(self):
        """测试缓存大小限制"""
        # 配置较小的缓存大小
        configure_performance(cache_size=50)
        
        # 执行大量不同的翻译查找
        unique_keys = [f'test_key_{i}' for i in range(200)]
        
        for key in unique_keys:
            get_translation(key)  # 大部分会缓存未命中
        
        # 获取性能报告
        stats = get_performance_statistics()
        
        # 验证缓存大小限制生效
        assert stats['lru_cache_size'] <= 50, "LRU缓存大小超过限制"
        
        # 恢复默认配置
        configure_performance(cache_size=1000)


class TestStartupInitializationTime:
    """启动初始化时间测试"""
    
    def test_initialization_performance(self):
        """测试初始化性能"""
        # 重新初始化性能优化
        start_time = time.perf_counter()
        reinitialize_performance_optimizations()
        end_time = time.perf_counter()
        
        initialization_time = end_time - start_time
        
        # 初始化时间应在100ms内完成
        assert initialization_time < 0.1, f"初始化时间 {initialization_time:.4f}s 超过100ms限制"
        
        # 验证初始化后的性能统计
        stats = get_performance_statistics()
        assert stats['startup_time'] < 0.1
        assert stats['precomputed_cache_count'] > 0
    
    def test_precomputation_effectiveness(self):
        """测试预计算效果"""
        # 重新初始化以确保预计算生效
        reinitialize_performance_optimizations()
        
        # 测试预计算的常用键性能
        reset_translation_performance_stats()
        
        # 查找常用键（应该命中预计算缓存）
        common_keys = list(COMMON_TRANSLATION_KEYS)[:10]
        
        start_time = time.perf_counter()
        for key in common_keys:
            get_translation(key)
        end_time = time.perf_counter()
        
        avg_time = (end_time - start_time) / len(common_keys)
        
        # 预计算键的查找应该非常快
        assert avg_time < 0.00001, f"预计算键查找时间 {avg_time:.8f}s 过慢"
        
        # 验证缓存命中率
        stats = get_performance_statistics()
        assert stats['cache_hit_rate'] > 0.8, "预计算缓存命中率过低"


class TestConcurrentAccessPerformance:
    """并发访问性能测试"""
    
    def setup_method(self):
        """测试前重置"""
        reset_translation_performance_stats()
        set_language('zh')
    
    def translation_worker(self, worker_id: int, iterations: int) -> Dict[str, Any]:
        """翻译工作线程"""
        results = []
        start_time = time.perf_counter()
        
        for i in range(iterations):
            key = f'app_name'  # 使用相同的键测试并发
            result = get_translation(key)
            results.append(result)
        
        end_time = time.perf_counter()
        
        return {
            'worker_id': worker_id,
            'iterations': iterations,
            'total_time': end_time - start_time,
            'avg_time': (end_time - start_time) / iterations,
            'results_count': len(results)
        }
    
    def test_concurrent_translation_access(self):
        """测试并发翻译访问"""
        num_workers = 10
        iterations_per_worker = 100
        
        # 使用线程池执行并发翻译
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(self.translation_worker, i, iterations_per_worker)
                for i in range(num_workers)
            ]
            
            # 等待所有任务完成
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 验证所有工作线程都成功完成
        assert len(results) == num_workers
        
        # 验证性能
        total_operations = num_workers * iterations_per_worker
        avg_times = [result['avg_time'] for result in results]
        overall_avg_time = sum(avg_times) / len(avg_times)
        
        # 并发访问的平均时间应该合理
        assert overall_avg_time < 0.001, f"并发访问平均时间 {overall_avg_time:.6f}s 过慢"
        
        # 验证性能统计
        stats = get_performance_statistics()
        assert stats['lookup_count'] >= total_operations
        assert stats['max_concurrent_requests'] >= 1
    
    def test_thread_safety_under_load(self):
        """测试高负载下的线程安全"""
        num_workers = 20
        iterations_per_worker = 50
        
        # 使用不同的语言和键进行测试
        test_cases = [
            ('zh', 'app_name'),
            ('en', 'app_name'),
            ('zh', 'login'),
            ('en', 'login')
        ]
        
        def mixed_worker(worker_id: int) -> Dict[str, Any]:
            """混合操作工作线程"""
            results = []
            
            for i in range(iterations_per_worker):
                # 随机选择测试用例
                language, key = test_cases[i % len(test_cases)]
                
                # 设置语言并获取翻译
                set_language(language)
                result = get_translation(key)
                results.append((language, key, result))
            
            return {
                'worker_id': worker_id,
                'results': results
            }
        
        # 执行并发混合操作
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(mixed_worker, i)
                for i in range(num_workers)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 验证所有结果
        assert len(results) == num_workers
        
        # 验证翻译结果的正确性
        for worker_result in results:
            for language, key, translation in worker_result['results']:
                assert translation is not None
                assert len(translation) > 0
                
                # 验证特定的翻译结果
                if key == 'app_name':
                    if language == 'zh':
                        assert 'SuperInsight' in translation
                    elif language == 'en':
                        assert 'SuperInsight Platform' == translation
    
    def test_performance_monitoring_accuracy(self):
        """测试性能监控准确性"""
        # 重置统计
        reset_translation_performance_stats()
        
        # 执行已知数量的操作
        expected_operations = 50
        
        for i in range(expected_operations):
            get_translation('app_name')
        
        # 验证统计准确性
        stats = get_performance_statistics()
        
        assert stats['lookup_count'] == expected_operations
        assert stats['total_lookup_time'] > 0
        assert stats['avg_lookup_time'] > 0
        assert stats['cache_hits'] + stats['cache_misses'] == expected_operations


if __name__ == '__main__':
    pytest.main([__file__, '-v'])