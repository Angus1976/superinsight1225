#!/usr/bin/env python3
"""
Performance and Load Testing Script for i18n Support
Tests concurrent user scenarios, translation lookup performance, memory usage, and thread safety
"""

import sys
import os
import time
import threading
import concurrent.futures
import psutil
import gc
from typing import List, Dict, Any
from statistics import mean, median, stdev

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from i18n.manager import TranslationManager, get_manager
from i18n.translations import set_language, get_current_language, get_translation, get_supported_languages
from i18n.performance import get_performance_report, reset_performance_stats
from i18n.thread_safety import ThreadSafetyValidator, validate_thread_safety

class PerformanceLoadTest:
    """Comprehensive performance and load testing for i18n system"""
    
    def __init__(self):
        self.results = []
        self.manager = get_manager()
        
    def log_result(self, test_name: str, passed: bool, message: str = "", metrics: Dict = None):
        """Log test result with optional metrics"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'metrics': metrics or {}
        })
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
        if metrics:
            for key, value in metrics.items():
                print(f"    {key}: {value}")
    
    def test_concurrent_user_scenarios(self):
        """Test 1: Concurrent user scenarios"""
        print("\n=== Testing Concurrent User Scenarios ===")
        
        # Test 1.1: Multiple users with different languages
        def user_session(user_id: int, language: str, iterations: int = 10):
            """Simulate a user session with specific language"""
            results = []
            try:
                for i in range(iterations):
                    set_language(language)
                    translation = get_translation('app_name')
                    current_lang = get_current_language()
                    
                    # Verify language isolation
                    if current_lang == language:
                        results.append(True)
                    else:
                        results.append(False)
                        
                return results
            except Exception as e:
                return [False] * iterations
        
        try:
            # Test with 10 concurrent users, 5 Chinese, 5 English
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                
                # Submit Chinese users
                for i in range(5):
                    future = executor.submit(user_session, i, 'zh', 20)
                    futures.append(('zh', future))
                
                # Submit English users
                for i in range(5, 10):
                    future = executor.submit(user_session, i, 'en', 20)
                    futures.append(('en', future))
                
                # Collect results
                all_results = []
                for lang, future in futures:
                    results = future.result()
                    all_results.extend(results)
                
                success_rate = sum(all_results) / len(all_results)
                
                self.log_result(
                    "Concurrent user language isolation",
                    success_rate >= 0.95,
                    f"Success rate: {success_rate:.2%}",
                    {"total_operations": len(all_results), "successful": sum(all_results)}
                )
        except Exception as e:
            self.log_result("Concurrent user language isolation", False, str(e))
        
        # Test 1.2: High-frequency translation requests
        def high_frequency_requests(duration_seconds: int = 5):
            """Generate high-frequency translation requests"""
            start_time = time.time()
            request_count = 0
            errors = 0
            
            keys = ['app_name', 'login', 'logout', 'error', 'success']
            
            while time.time() - start_time < duration_seconds:
                try:
                    key = keys[request_count % len(keys)]
                    translation = get_translation(key)
                    request_count += 1
                except Exception:
                    errors += 1
                    request_count += 1
            
            return request_count, errors
        
        try:
            # Test high-frequency requests for 5 seconds
            total_requests, total_errors = high_frequency_requests(5)
            requests_per_second = total_requests / 5
            error_rate = total_errors / total_requests if total_requests > 0 else 0
            
            self.log_result(
                "High-frequency translation requests",
                requests_per_second >= 1000 and error_rate < 0.01,
                f"Performance: {requests_per_second:.0f} req/s, Error rate: {error_rate:.2%}",
                {"requests_per_second": requests_per_second, "total_requests": total_requests, "errors": total_errors}
            )
        except Exception as e:
            self.log_result("High-frequency translation requests", False, str(e))
    
    def test_translation_lookup_performance(self):
        """Test 2: Translation lookup performance"""
        print("\n=== Testing Translation Lookup Performance ===")
        
        # Test 2.1: Single translation lookup performance
        try:
            set_language('zh')
            
            # Warm up
            for _ in range(100):
                get_translation('app_name')
            
            # Measure performance
            times = []
            for _ in range(1000):
                start = time.perf_counter()
                get_translation('app_name')
                end = time.perf_counter()
                times.append((end - start) * 1000)  # Convert to milliseconds
            
            avg_time = mean(times)
            median_time = median(times)
            max_time = max(times)
            
            # Should be under 1ms for O(1) lookup
            self.log_result(
                "Single translation lookup performance",
                avg_time < 1.0,
                f"Average: {avg_time:.3f}ms, Median: {median_time:.3f}ms, Max: {max_time:.3f}ms",
                {"avg_ms": avg_time, "median_ms": median_time, "max_ms": max_time}
            )
        except Exception as e:
            self.log_result("Single translation lookup performance", False, str(e))
        
        # Test 2.2: Batch translation performance
        try:
            keys = ['app_name', 'login', 'logout', 'error', 'success', 'warning', 'info']
            
            # Test batch translation
            start = time.perf_counter()
            for _ in range(100):
                for key in keys:
                    get_translation(key)
            end = time.perf_counter()
            
            total_time = (end - start) * 1000  # milliseconds
            per_translation = total_time / (100 * len(keys))
            
            self.log_result(
                "Batch translation performance",
                per_translation < 0.5,
                f"Per translation: {per_translation:.3f}ms, Total: {total_time:.1f}ms",
                {"per_translation_ms": per_translation, "total_ms": total_time}
            )
        except Exception as e:
            self.log_result("Batch translation performance", False, str(e))
        
        # Test 2.3: Language switching performance
        try:
            times = []
            languages = ['zh', 'en']
            
            for _ in range(500):
                lang = languages[_ % 2]
                start = time.perf_counter()
                set_language(lang)
                end = time.perf_counter()
                times.append((end - start) * 1000)
            
            avg_switch_time = mean(times)
            
            self.log_result(
                "Language switching performance",
                avg_switch_time < 0.1,
                f"Average switch time: {avg_switch_time:.3f}ms",
                {"avg_switch_ms": avg_switch_time}
            )
        except Exception as e:
            self.log_result("Language switching performance", False, str(e))
    
    def test_memory_usage_under_load(self):
        """Test 3: Memory usage under load"""
        print("\n=== Testing Memory Usage Under Load ===")
        
        # Test 3.1: Memory usage baseline
        try:
            gc.collect()  # Force garbage collection
            process = psutil.Process()
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Perform intensive operations
            for _ in range(1000):
                set_language('zh')
                for key in ['app_name', 'login', 'logout', 'error', 'success']:
                    get_translation(key)
                set_language('en')
                for key in ['app_name', 'login', 'logout', 'error', 'success']:
                    get_translation(key)
            
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - baseline_memory
            
            # Memory increase should be minimal (< 10MB)
            self.log_result(
                "Memory usage under load",
                memory_increase < 10,
                f"Baseline: {baseline_memory:.1f}MB, Final: {final_memory:.1f}MB, Increase: {memory_increase:.1f}MB",
                {"baseline_mb": baseline_memory, "final_mb": final_memory, "increase_mb": memory_increase}
            )
        except Exception as e:
            self.log_result("Memory usage under load", False, str(e))
        
        # Test 3.2: Memory optimization effectiveness
        try:
            from i18n.performance import optimize_memory_usage
            
            gc.collect()
            before_optimization = process.memory_info().rss / 1024 / 1024
            
            # Run memory optimization
            optimize_memory_usage()
            
            gc.collect()
            after_optimization = process.memory_info().rss / 1024 / 1024
            memory_saved = before_optimization - after_optimization
            
            self.log_result(
                "Memory optimization effectiveness",
                memory_saved >= 0,  # Should not increase memory
                f"Before: {before_optimization:.1f}MB, After: {after_optimization:.1f}MB, Saved: {memory_saved:.1f}MB",
                {"before_mb": before_optimization, "after_mb": after_optimization, "saved_mb": memory_saved}
            )
        except Exception as e:
            self.log_result("Memory optimization effectiveness", False, str(e))
    
    def test_thread_safety_under_concurrent_access(self):
        """Test 4: Thread safety under concurrent access"""
        print("\n=== Testing Thread Safety Under Concurrent Access ===")
        
        # Test 4.1: Context variable isolation under load
        try:
            def worker_thread(thread_id: int, language: str, iterations: int = 50):
                """Worker thread that sets language and performs translations"""
                results = []
                for i in range(iterations):
                    try:
                        set_language(language)
                        current = get_current_language()
                        translation = get_translation('app_name')
                        
                        # Verify language consistency
                        if current == language:
                            results.append(True)
                        else:
                            results.append(False)
                            
                        # Small delay to increase chance of race conditions
                        time.sleep(0.001)
                    except Exception:
                        results.append(False)
                
                return results
            
            # Run 20 threads, 10 Chinese, 10 English
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = []
                
                for i in range(10):
                    future = executor.submit(worker_thread, i, 'zh', 50)
                    futures.append(future)
                
                for i in range(10, 20):
                    future = executor.submit(worker_thread, i, 'en', 50)
                    futures.append(future)
                
                # Collect results
                all_results = []
                for future in futures:
                    results = future.result()
                    all_results.extend(results)
                
                success_rate = sum(all_results) / len(all_results)
                
                self.log_result(
                    "Thread safety under concurrent access",
                    success_rate >= 0.99,
                    f"Success rate: {success_rate:.2%} ({sum(all_results)}/{len(all_results)})",
                    {"success_rate": success_rate, "total_operations": len(all_results)}
                )
        except Exception as e:
            self.log_result("Thread safety under concurrent access", False, str(e))
        
        # Test 4.2: Thread safety validator
        try:
            validator = ThreadSafetyValidator()
            
            # Run comprehensive thread safety test
            is_thread_safe = validator.run_comprehensive_test(
                num_threads=10,
                operations_per_thread=100,
                languages=['zh', 'en']
            )
            
            self.log_result(
                "Thread safety validation",
                is_thread_safe,
                f"Comprehensive thread safety test: {'PASSED' if is_thread_safe else 'FAILED'}",
                {"thread_safe": is_thread_safe}
            )
        except Exception as e:
            self.log_result("Thread safety validation", False, str(e))
        
        # Test 4.3: Race condition detection
        try:
            def race_condition_test():
                """Test for race conditions in language switching"""
                errors = []
                
                def rapid_switcher(iterations: int = 100):
                    for i in range(iterations):
                        try:
                            lang = 'zh' if i % 2 == 0 else 'en'
                            set_language(lang)
                            current = get_current_language()
                            if current not in ['zh', 'en']:
                                errors.append(f"Invalid language: {current}")
                        except Exception as e:
                            errors.append(str(e))
                
                # Run multiple rapid switchers concurrently
                threads = []
                for _ in range(5):
                    thread = threading.Thread(target=rapid_switcher, args=(200,))
                    threads.append(thread)
                    thread.start()
                
                for thread in threads:
                    thread.join()
                
                return len(errors)
            
            error_count = race_condition_test()
            
            self.log_result(
                "Race condition detection",
                error_count == 0,
                f"Race condition errors: {error_count}",
                {"race_condition_errors": error_count}
            )
        except Exception as e:
            self.log_result("Race condition detection", False, str(e))
    
    def run_all_tests(self):
        """Run all performance and load tests"""
        print("🚀 Starting Performance and Load Testing for i18n Support")
        print("=" * 70)
        
        # Reset performance stats
        try:
            reset_performance_stats()
        except:
            pass
        
        # Run all test categories
        self.test_concurrent_user_scenarios()
        self.test_translation_lookup_performance()
        self.test_memory_usage_under_load()
        self.test_thread_safety_under_concurrent_access()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 PERFORMANCE TEST SUMMARY")
        print("=" * 70)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Performance metrics summary
        print("\n📈 PERFORMANCE METRICS:")
        for result in self.results:
            if result['metrics']:
                print(f"  {result['test']}:")
                for key, value in result['metrics'].items():
                    print(f"    - {key}: {value}")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n" + "=" * 70)
        overall_success = failed_tests == 0
        print(f"🎯 OVERALL RESULT: {'SUCCESS' if overall_success else 'NEEDS ATTENTION'}")
        
        return overall_success

if __name__ == "__main__":
    tester = PerformanceLoadTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)