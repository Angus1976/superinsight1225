"""
线程安全验证模块
确保i18n系统在多线程环境下的安全性
"""

import threading
import time
import concurrent.futures
from typing import Dict, List, Any, Optional, Callable
from contextvars import ContextVar, copy_context
import weakref
from collections import defaultdict
import uuid

from .translations import (
    get_translation,
    set_language,
    get_current_language,
    get_all_translations,
    _current_language
)


class ThreadSafetyValidator:
    """线程安全验证器"""
    
    def __init__(self):
        self.test_results: Dict[str, Any] = {}
        self.lock = threading.Lock()
        self.context_isolation_results: List[Dict[str, Any]] = []
        self.concurrent_access_results: List[Dict[str, Any]] = []
    
    def validate_context_variable_isolation(self, num_threads: int = 10, operations_per_thread: int = 50) -> Dict[str, Any]:
        """
        验证上下文变量隔离
        
        Args:
            num_threads: 线程数量
            operations_per_thread: 每个线程的操作数量
        
        Returns:
            验证结果
        """
        results = []
        barrier = threading.Barrier(num_threads)
        
        def thread_worker(thread_id: int, assigned_language: str) -> Dict[str, Any]:
            """线程工作函数"""
            thread_results = {
                'thread_id': thread_id,
                'assigned_language': assigned_language,
                'operations': [],
                'context_violations': 0,
                'successful_operations': 0
            }
            
            try:
                # 等待所有线程准备就绪
                barrier.wait()
                
                # 设置线程特定的语言
                set_language(assigned_language)
                
                for i in range(operations_per_thread):
                    # 验证当前语言设置
                    current_lang = get_current_language()
                    
                    # 执行翻译操作
                    translation = get_translation('app_name')
                    
                    # 验证语言一致性
                    if current_lang != assigned_language:
                        thread_results['context_violations'] += 1
                    else:
                        thread_results['successful_operations'] += 1
                    
                    thread_results['operations'].append({
                        'operation_id': i,
                        'expected_language': assigned_language,
                        'actual_language': current_lang,
                        'translation': translation,
                        'is_consistent': current_lang == assigned_language
                    })
                    
                    # 短暂休眠以增加竞争条件
                    time.sleep(0.001)
                
            except Exception as e:
                thread_results['error'] = str(e)
            
            return thread_results
        
        # 创建不同语言的线程
        languages = ['zh', 'en'] * (num_threads // 2)
        if len(languages) < num_threads:
            languages.extend(['zh'] * (num_threads - len(languages)))
        
        # 使用线程池执行
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(thread_worker, i, languages[i])
                for i in range(num_threads)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 分析结果
        total_operations = sum(r['successful_operations'] + r['context_violations'] for r in results)
        total_violations = sum(r['context_violations'] for r in results)
        
        validation_result = {
            'test_type': 'context_variable_isolation',
            'num_threads': num_threads,
            'operations_per_thread': operations_per_thread,
            'total_operations': total_operations,
            'total_violations': total_violations,
            'violation_rate': total_violations / total_operations if total_operations > 0 else 0,
            'is_thread_safe': total_violations == 0,
            'thread_results': results
        }
        
        with self.lock:
            self.context_isolation_results.append(validation_result)
        
        return validation_result
    
    def validate_concurrent_translation_access(self, num_threads: int = 20, operations_per_thread: int = 100) -> Dict[str, Any]:
        """
        验证并发翻译访问
        
        Args:
            num_threads: 线程数量
            operations_per_thread: 每个线程的操作数量
        
        Returns:
            验证结果
        """
        results = []
        shared_counter = {'value': 0}
        counter_lock = threading.Lock()
        
        def concurrent_worker(thread_id: int) -> Dict[str, Any]:
            """并发工作函数"""
            thread_results = {
                'thread_id': thread_id,
                'successful_translations': 0,
                'failed_translations': 0,
                'translation_errors': [],
                'timing_data': []
            }
            
            # 测试键列表
            test_keys = [
                'app_name', 'login', 'logout', 'error', 'success',
                'warning', 'info', 'status', 'healthy', 'unhealthy'
            ]
            
            for i in range(operations_per_thread):
                try:
                    start_time = time.perf_counter()
                    
                    # 选择测试键
                    key = test_keys[i % len(test_keys)]
                    
                    # 执行翻译
                    translation = get_translation(key)
                    
                    end_time = time.perf_counter()
                    
                    # 验证翻译结果
                    if translation and len(translation) > 0:
                        thread_results['successful_translations'] += 1
                        
                        # 更新共享计数器（测试线程安全）
                        with counter_lock:
                            shared_counter['value'] += 1
                    else:
                        thread_results['failed_translations'] += 1
                    
                    thread_results['timing_data'].append({
                        'operation_id': i,
                        'key': key,
                        'duration': end_time - start_time,
                        'translation_length': len(translation) if translation else 0
                    })
                    
                except Exception as e:
                    thread_results['failed_translations'] += 1
                    thread_results['translation_errors'].append({
                        'operation_id': i,
                        'error': str(e)
                    })
            
            return thread_results
        
        # 执行并发测试
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(concurrent_worker, i)
                for i in range(num_threads)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 分析结果
        total_successful = sum(r['successful_translations'] for r in results)
        total_failed = sum(r['failed_translations'] for r in results)
        total_operations = total_successful + total_failed
        
        # 计算性能统计
        all_timings = []
        for result in results:
            all_timings.extend([op['duration'] for op in result['timing_data']])
        
        avg_duration = sum(all_timings) / len(all_timings) if all_timings else 0
        max_duration = max(all_timings) if all_timings else 0
        min_duration = min(all_timings) if all_timings else 0
        
        validation_result = {
            'test_type': 'concurrent_translation_access',
            'num_threads': num_threads,
            'operations_per_thread': operations_per_thread,
            'total_operations': total_operations,
            'successful_operations': total_successful,
            'failed_operations': total_failed,
            'success_rate': total_successful / total_operations if total_operations > 0 else 0,
            'shared_counter_value': shared_counter['value'],
            'expected_counter_value': total_successful,
            'counter_consistency': shared_counter['value'] == total_successful,
            'performance_stats': {
                'avg_duration': avg_duration,
                'max_duration': max_duration,
                'min_duration': min_duration,
                'total_duration': sum(all_timings)
            },
            'is_thread_safe': total_failed == 0 and shared_counter['value'] == total_successful,
            'thread_results': results
        }
        
        with self.lock:
            self.concurrent_access_results.append(validation_result)
        
        return validation_result
    
    def validate_context_copying(self, num_contexts: int = 10) -> Dict[str, Any]:
        """
        验证上下文复制功能
        
        Args:
            num_contexts: 测试的上下文数量
        
        Returns:
            验证结果
        """
        contexts = []
        languages = ['zh', 'en']
        
        # 创建不同的上下文
        for i in range(num_contexts):
            language = languages[i % len(languages)]
            
            # 设置语言并复制上下文
            set_language(language)
            ctx = copy_context()
            
            contexts.append({
                'context_id': i,
                'expected_language': language,
                'context': ctx
            })
        
        # 验证上下文隔离
        validation_results = []
        
        for ctx_info in contexts:
            def test_context():
                # 在复制的上下文中运行
                current_lang = get_current_language()
                translation = get_translation('app_name')
                
                return {
                    'context_id': ctx_info['context_id'],
                    'expected_language': ctx_info['expected_language'],
                    'actual_language': current_lang,
                    'translation': translation,
                    'is_consistent': current_lang == ctx_info['expected_language']
                }
            
            # 在上下文中运行测试
            result = ctx_info['context'].run(test_context)
            validation_results.append(result)
        
        # 分析结果
        consistent_contexts = sum(1 for r in validation_results if r['is_consistent'])
        
        return {
            'test_type': 'context_copying',
            'num_contexts': num_contexts,
            'consistent_contexts': consistent_contexts,
            'inconsistent_contexts': num_contexts - consistent_contexts,
            'consistency_rate': consistent_contexts / num_contexts,
            'is_context_safe': consistent_contexts == num_contexts,
            'context_results': validation_results
        }
    
    def run_comprehensive_thread_safety_test(self) -> Dict[str, Any]:
        """
        运行综合线程安全测试
        
        Returns:
            综合测试结果
        """
        print("开始综合线程安全测试...")
        
        # 1. 上下文变量隔离测试
        print("1. 测试上下文变量隔离...")
        isolation_result = self.validate_context_variable_isolation(
            num_threads=15, 
            operations_per_thread=30
        )
        
        # 2. 并发翻译访问测试
        print("2. 测试并发翻译访问...")
        concurrent_result = self.validate_concurrent_translation_access(
            num_threads=25, 
            operations_per_thread=50
        )
        
        # 3. 上下文复制测试
        print("3. 测试上下文复制...")
        context_copy_result = self.validate_context_copying(num_contexts=20)
        
        # 综合评估
        all_tests_passed = (
            isolation_result['is_thread_safe'] and
            concurrent_result['is_thread_safe'] and
            context_copy_result['is_context_safe']
        )
        
        comprehensive_result = {
            'test_timestamp': time.time(),
            'overall_thread_safety': all_tests_passed,
            'tests': {
                'context_isolation': isolation_result,
                'concurrent_access': concurrent_result,
                'context_copying': context_copy_result
            },
            'summary': {
                'total_tests': 3,
                'passed_tests': sum([
                    isolation_result['is_thread_safe'],
                    concurrent_result['is_thread_safe'],
                    context_copy_result['is_context_safe']
                ]),
                'failed_tests': 3 - sum([
                    isolation_result['is_thread_safe'],
                    concurrent_result['is_thread_safe'],
                    context_copy_result['is_context_safe']
                ])
            }
        }
        
        with self.lock:
            self.test_results['comprehensive'] = comprehensive_result
        
        print(f"综合测试完成。总体线程安全性: {'通过' if all_tests_passed else '失败'}")
        
        return comprehensive_result
    
    def get_thread_safety_report(self) -> Dict[str, Any]:
        """
        获取线程安全报告
        
        Returns:
            线程安全报告
        """
        return {
            'validator_status': 'active',
            'test_results': self.test_results,
            'context_isolation_tests': len(self.context_isolation_results),
            'concurrent_access_tests': len(self.concurrent_access_results),
            'latest_results': {
                'context_isolation': self.context_isolation_results[-1] if self.context_isolation_results else None,
                'concurrent_access': self.concurrent_access_results[-1] if self.concurrent_access_results else None
            }
        }


# 全局线程安全验证器实例
_thread_safety_validator: Optional[ThreadSafetyValidator] = None


def get_thread_safety_validator() -> ThreadSafetyValidator:
    """获取线程安全验证器实例"""
    global _thread_safety_validator
    if _thread_safety_validator is None:
        _thread_safety_validator = ThreadSafetyValidator()
    return _thread_safety_validator


def validate_thread_safety(
    context_isolation: bool = True,
    concurrent_access: bool = True,
    context_copying: bool = True
) -> Dict[str, Any]:
    """
    验证i18n系统的线程安全性
    
    Args:
        context_isolation: 是否测试上下文隔离
        concurrent_access: 是否测试并发访问
        context_copying: 是否测试上下文复制
    
    Returns:
        验证结果
    """
    validator = get_thread_safety_validator()
    results = {}
    
    if context_isolation:
        results['context_isolation'] = validator.validate_context_variable_isolation()
    
    if concurrent_access:
        results['concurrent_access'] = validator.validate_concurrent_translation_access()
    
    if context_copying:
        results['context_copying'] = validator.validate_context_copying()
    
    return results


def run_thread_safety_benchmark() -> Dict[str, Any]:
    """
    运行线程安全基准测试
    
    Returns:
        基准测试结果
    """
    validator = get_thread_safety_validator()
    return validator.run_comprehensive_thread_safety_test()


def get_context_variable_info() -> Dict[str, Any]:
    """
    获取上下文变量信息
    
    Returns:
        上下文变量信息
    """
    return {
        'context_var_name': _current_language.name,
        'current_value': get_current_language(),
        'default_value': 'zh',
        'is_context_var': True,
        'supports_isolation': True
    }