"""
i18n 线程安全测试
验证翻译系统在多线程环境下的安全性
"""

import pytest
import threading
import time
import concurrent.futures
from typing import List, Dict, Any
from contextvars import copy_context

from src.i18n import (
    get_translation,
    set_language,
    get_current_language,
    get_all_translations
)
from src.i18n.thread_safety import (
    ThreadSafetyValidator,
    get_thread_safety_validator,
    validate_thread_safety,
    run_thread_safety_benchmark,
    get_context_variable_info
)


class TestContextVariableIsolation:
    """上下文变量隔离测试"""
    
    def setup_method(self):
        """测试前设置"""
        set_language('zh')  # 重置为默认语言
    
    def test_basic_context_isolation(self):
        """测试基本上下文隔离"""
        results = []
        barrier = threading.Barrier(2)
        
        def worker_zh():
            barrier.wait()
            set_language('zh')
            time.sleep(0.01)  # 增加竞争条件
            lang = get_current_language()
            translation = get_translation('app_name')
            results.append(('zh', lang, translation))
        
        def worker_en():
            barrier.wait()
            set_language('en')
            time.sleep(0.01)  # 增加竞争条件
            lang = get_current_language()
            translation = get_translation('app_name')
            results.append(('en', lang, translation))
        
        # 启动两个线程
        thread1 = threading.Thread(target=worker_zh)
        thread2 = threading.Thread(target=worker_en)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # 验证结果
        assert len(results) == 2
        
        # 检查每个线程的结果
        for expected_lang, actual_lang, translation in results:
            assert actual_lang == expected_lang, f"语言不匹配: 期望 {expected_lang}, 实际 {actual_lang}"
            assert translation is not None
            assert len(translation) > 0
            
            # 验证翻译内容正确
            if expected_lang == 'zh':
                assert 'SuperInsight' in translation and '平台' in translation
            elif expected_lang == 'en':
                assert translation == 'SuperInsight Platform'
    
    def test_multiple_threads_context_isolation(self):
        """测试多线程上下文隔离"""
        num_threads = 10
        operations_per_thread = 20
        results = []
        results_lock = threading.Lock()
        
        def thread_worker(thread_id: int, language: str):
            """线程工作函数"""
            thread_results = []
            
            set_language(language)
            
            for i in range(operations_per_thread):
                current_lang = get_current_language()
                translation = get_translation('login')
                
                thread_results.append({
                    'thread_id': thread_id,
                    'operation': i,
                    'expected_language': language,
                    'actual_language': current_lang,
                    'translation': translation,
                    'is_correct': current_lang == language
                })
                
                # 短暂休眠增加竞争
                time.sleep(0.001)
            
            with results_lock:
                results.extend(thread_results)
        
        # 创建多个线程，交替使用不同语言
        threads = []
        for i in range(num_threads):
            language = 'zh' if i % 2 == 0 else 'en'
            thread = threading.Thread(target=thread_worker, args=(i, language))
            threads.append(thread)
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        assert len(results) == num_threads * operations_per_thread
        
        # 检查每个操作的正确性
        correct_operations = sum(1 for r in results if r['is_correct'])
        total_operations = len(results)
        
        assert correct_operations == total_operations, f"上下文隔离失败: {correct_operations}/{total_operations} 操作正确"
    
    def test_context_copying(self):
        """测试上下文复制"""
        # 设置初始语言
        set_language('zh')
        zh_context = copy_context()
        
        # 切换语言
        set_language('en')
        en_context = copy_context()
        
        # 在不同上下文中测试
        def test_in_context(expected_lang: str):
            actual_lang = get_current_language()
            translation = get_translation('app_name')
            return actual_lang, translation
        
        # 在中文上下文中运行
        zh_lang, zh_translation = zh_context.run(test_in_context, 'zh')
        
        # 在英文上下文中运行
        en_lang, en_translation = en_context.run(test_in_context, 'en')
        
        # 验证上下文隔离
        assert zh_lang == 'zh'
        assert en_lang == 'en'
        assert zh_translation != en_translation
        assert 'SuperInsight' in zh_translation and '平台' in zh_translation
        assert en_translation == 'SuperInsight Platform'


class TestConcurrentTranslationAccess:
    """并发翻译访问测试"""
    
    def setup_method(self):
        """测试前设置"""
        set_language('zh')
    
    def test_concurrent_same_key_access(self):
        """测试并发访问同一个键"""
        num_threads = 20
        operations_per_thread = 50
        results = []
        results_lock = threading.Lock()
        
        def concurrent_worker(thread_id: int):
            """并发工作函数"""
            thread_results = []
            
            for i in range(operations_per_thread):
                try:
                    translation = get_translation('app_name')
                    thread_results.append({
                        'thread_id': thread_id,
                        'operation': i,
                        'translation': translation,
                        'success': True
                    })
                except Exception as e:
                    thread_results.append({
                        'thread_id': thread_id,
                        'operation': i,
                        'error': str(e),
                        'success': False
                    })
            
            with results_lock:
                results.extend(thread_results)
        
        # 启动并发线程
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(concurrent_worker, i)
                for i in range(num_threads)
            ]
            
            # 等待所有任务完成
            concurrent.futures.wait(futures)
        
        # 验证结果
        total_operations = num_threads * operations_per_thread
        assert len(results) == total_operations
        
        # 检查成功率
        successful_operations = sum(1 for r in results if r['success'])
        assert successful_operations == total_operations, f"并发访问失败: {successful_operations}/{total_operations} 操作成功"
        
        # 验证翻译结果一致性
        translations = [r['translation'] for r in results if r['success']]
        unique_translations = set(translations)
        assert len(unique_translations) == 1, "并发访问产生了不一致的翻译结果"
    
    def test_concurrent_different_keys_access(self):
        """测试并发访问不同键"""
        num_threads = 15
        test_keys = ['app_name', 'login', 'logout', 'error', 'success', 'warning']
        results = []
        results_lock = threading.Lock()
        
        def multi_key_worker(thread_id: int):
            """多键工作函数"""
            thread_results = []
            
            for key in test_keys:
                try:
                    translation = get_translation(key)
                    thread_results.append({
                        'thread_id': thread_id,
                        'key': key,
                        'translation': translation,
                        'success': True
                    })
                except Exception as e:
                    thread_results.append({
                        'thread_id': thread_id,
                        'key': key,
                        'error': str(e),
                        'success': False
                    })
            
            with results_lock:
                results.extend(thread_results)
        
        # 启动并发线程
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=multi_key_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        expected_operations = num_threads * len(test_keys)
        assert len(results) == expected_operations
        
        # 检查成功率
        successful_operations = sum(1 for r in results if r['success'])
        assert successful_operations == expected_operations
        
        # 验证每个键的翻译一致性
        translations_by_key = {}
        for result in results:
            if result['success']:
                key = result['key']
                translation = result['translation']
                
                if key not in translations_by_key:
                    translations_by_key[key] = set()
                translations_by_key[key].add(translation)
        
        # 每个键应该只有一个唯一的翻译
        for key, translations in translations_by_key.items():
            assert len(translations) == 1, f"键 '{key}' 产生了多个不同的翻译: {translations}"


class TestThreadSafetyValidator:
    """线程安全验证器测试"""
    
    def test_validator_initialization(self):
        """测试验证器初始化"""
        validator = get_thread_safety_validator()
        
        assert isinstance(validator, ThreadSafetyValidator)
        assert hasattr(validator, 'test_results')
        assert hasattr(validator, 'context_isolation_results')
        assert hasattr(validator, 'concurrent_access_results')
    
    def test_context_isolation_validation(self):
        """测试上下文隔离验证"""
        validator = get_thread_safety_validator()
        
        result = validator.validate_context_variable_isolation(
            num_threads=5,
            operations_per_thread=10
        )
        
        # 验证结果结构
        assert 'test_type' in result
        assert result['test_type'] == 'context_variable_isolation'
        assert 'num_threads' in result
        assert 'total_operations' in result
        assert 'total_violations' in result
        assert 'is_thread_safe' in result
        assert 'thread_results' in result
        
        # 验证线程安全性
        assert result['is_thread_safe'], f"上下文隔离验证失败: {result['total_violations']} 个违规"
        assert result['violation_rate'] == 0.0
    
    def test_concurrent_access_validation(self):
        """测试并发访问验证"""
        validator = get_thread_safety_validator()
        
        result = validator.validate_concurrent_translation_access(
            num_threads=10,
            operations_per_thread=20
        )
        
        # 验证结果结构
        assert 'test_type' in result
        assert result['test_type'] == 'concurrent_translation_access'
        assert 'num_threads' in result
        assert 'total_operations' in result
        assert 'successful_operations' in result
        assert 'is_thread_safe' in result
        
        # 验证线程安全性
        assert result['is_thread_safe'], "并发访问验证失败"
        assert result['success_rate'] >= 0.99  # 至少99%成功率
    
    def test_context_copying_validation(self):
        """测试上下文复制验证"""
        validator = get_thread_safety_validator()
        
        result = validator.validate_context_copying(num_contexts=8)
        
        # 验证结果结构
        assert 'test_type' in result
        assert result['test_type'] == 'context_copying'
        assert 'num_contexts' in result
        assert 'consistent_contexts' in result
        assert 'is_context_safe' in result
        
        # 验证上下文安全性
        assert result['is_context_safe'], "上下文复制验证失败"
        assert result['consistency_rate'] == 1.0
    
    def test_comprehensive_thread_safety_test(self):
        """测试综合线程安全测试"""
        validator = get_thread_safety_validator()
        
        result = validator.run_comprehensive_thread_safety_test()
        
        # 验证结果结构
        assert 'overall_thread_safety' in result
        assert 'tests' in result
        assert 'summary' in result
        
        # 验证包含所有测试
        tests = result['tests']
        assert 'context_isolation' in tests
        assert 'concurrent_access' in tests
        assert 'context_copying' in tests
        
        # 验证总体线程安全性
        assert result['overall_thread_safety'], "综合线程安全测试失败"
        assert result['summary']['passed_tests'] == 3


class TestThreadSafetyUtilities:
    """线程安全工具函数测试"""
    
    def test_validate_thread_safety_function(self):
        """测试线程安全验证函数"""
        result = validate_thread_safety(
            context_isolation=True,
            concurrent_access=True,
            context_copying=True
        )
        
        # 验证返回所有测试结果
        assert 'context_isolation' in result
        assert 'concurrent_access' in result
        assert 'context_copying' in result
        
        # 验证每个测试都通过
        assert result['context_isolation']['is_thread_safe']
        assert result['concurrent_access']['is_thread_safe']
        assert result['context_copying']['is_context_safe']
    
    def test_context_variable_info(self):
        """测试上下文变量信息"""
        info = get_context_variable_info()
        
        assert 'context_var_name' in info
        assert 'current_value' in info
        assert 'default_value' in info
        assert 'is_context_var' in info
        assert 'supports_isolation' in info
        
        assert info['context_var_name'] == 'language'
        assert info['default_value'] == 'zh'
        assert info['is_context_var'] is True
        assert info['supports_isolation'] is True
    
    def test_thread_safety_benchmark(self):
        """测试线程安全基准测试"""
        # 这个测试可能需要较长时间，所以使用较小的参数
        result = run_thread_safety_benchmark()
        
        # 验证基准测试结果
        assert 'overall_thread_safety' in result
        assert 'tests' in result
        assert 'summary' in result
        
        # 验证测试通过
        assert result['overall_thread_safety'], "线程安全基准测试失败"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])