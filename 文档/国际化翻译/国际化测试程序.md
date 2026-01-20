# SuperInsight i18n Testing Procedures

## Overview

This document provides comprehensive testing procedures for the SuperInsight i18n system, covering unit tests, integration tests, property-based tests, and performance testing.

## Testing Strategy

### Test Pyramid

```
    /\
   /  \
  /E2E \     End-to-End Tests (Few)
 /______\
/        \   Integration Tests (Some)
/__________\
/          \ Unit Tests (Many)
/____________\
/            \ Property-Based Tests (Comprehensive)
/______________\
```

### Test Categories

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **Property-Based Tests**: Test universal properties across all inputs
4. **Performance Tests**: Test performance characteristics
5. **End-to-End Tests**: Test complete user workflows

## Unit Testing Procedures

### 1. Translation Manager Tests

```python
# tests/unit/test_translation_manager.py

import pytest
from src.i18n.manager import TranslationManager, get_manager
from src.i18n.translations import TRANSLATIONS

class TestTranslationManager:
    def setup_method(self):
        """Set up test environment before each test."""
        self.manager = TranslationManager()
    
    def test_initialization(self):
        """Test manager initialization."""
        assert self.manager.get_language() == 'zh'  # Default language
        assert 'zh' in self.manager.get_supported_languages()
        assert 'en' in self.manager.get_supported_languages()
    
    def test_language_setting(self):
        """Test language setting functionality."""
        # Test valid language
        self.manager.set_language('en')
        assert self.manager.get_language() == 'en'
        
        # Test invalid language (should raise exception or fallback)
        with pytest.raises(ValueError):
            self.manager.set_language('invalid')
    
    def test_basic_translation(self):
        """Test basic translation functionality."""
        # Test Chinese translation
        self.manager.set_language('zh')
        assert self.manager.translate('login') == '登录'
        
        # Test English translation
        self.manager.set_language('en')
        assert self.manager.translate('login') == 'Login'
    
    def test_missing_key_fallback(self):
        """Test fallback behavior for missing keys."""
        result = self.manager.translate('nonexistent_key')
        assert result == 'nonexistent_key'  # Should return key itself
    
    def test_parameterized_translation(self):
        """Test translations with parameters."""
        # Add test translation with parameters
        TRANSLATIONS['en']['welcome_user'] = 'Welcome, {username}!'
        TRANSLATIONS['zh']['welcome_user'] = '欢迎，{username}！'
        
        self.manager.set_language('en')
        result = self.manager.translate('welcome_user', username='John')
        assert result == 'Welcome, John!'
        
        self.manager.set_language('zh')
        result = self.manager.translate('welcome_user', username='张三')
        assert result == '欢迎，张三！'
    
    def test_batch_translation(self):
        """Test batch translation operations."""
        keys = ['login', 'logout', 'dashboard']
        
        self.manager.set_language('en')
        results = self.manager.translate_list(keys)
        
        expected = ['Login', 'Logout', 'Dashboard']
        assert results == expected
    
    def test_get_all_translations(self):
        """Test retrieving all translations."""
        all_zh = self.manager.get_all('zh')
        all_en = self.manager.get_all('en')
        
        assert isinstance(all_zh, dict)
        assert isinstance(all_en, dict)
        assert 'login' in all_zh
        assert 'login' in all_en
        assert all_zh['login'] == '登录'
        assert all_en['login'] == 'Login'
```

### 2. Context Variable Tests

```python
# tests/unit/test_context_variables.py

import pytest
import asyncio
from contextvars import copy_context
from src.i18n.manager import set_language, get_current_language

class TestContextVariables:
    def test_context_isolation(self):
        """Test that context variables are isolated between contexts."""
        # Set language in current context
        set_language('en')
        assert get_current_language() == 'en'
        
        # Create new context and set different language
        def set_chinese():
            set_language('zh')
            return get_current_language()
        
        ctx = copy_context()
        result = ctx.run(set_chinese)
        
        # New context should have Chinese
        assert result == 'zh'
        
        # Original context should still have English
        assert get_current_language() == 'en'
    
    @pytest.mark.asyncio
    async def test_async_context_propagation(self):
        """Test context propagation in async functions."""
        set_language('en')
        
        async def async_translation_check():
            # Context should be propagated to async function
            return get_current_language()
        
        result = await async_translation_check()
        assert result == 'en'
    
    def test_thread_safety(self):
        """Test thread safety of context variables."""
        import threading
        import time
        
        results = {}
        
        def worker(language, worker_id):
            set_language(language)
            time.sleep(0.1)  # Simulate work
            results[worker_id] = get_current_language()
        
        threads = []
        for i in range(10):
            lang = 'en' if i % 2 == 0 else 'zh'
            thread = threading.Thread(target=worker, args=(lang, i))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify each thread maintained its own language
        for i in range(10):
            expected_lang = 'en' if i % 2 == 0 else 'zh'
            assert results[i] == expected_lang
```

### 3. Validation Tests

```python
# tests/unit/test_validation.py

import pytest
from src.i18n.validation import (
    validate_translation_completeness,
    validate_language_code,
    validate_translation_key
)

class TestValidation:
    def test_translation_completeness(self):
        """Test translation completeness validation."""
        # Should pass with current translations
        assert validate_translation_completeness() == True
    
    def test_language_code_validation(self):
        """Test language code validation."""
        # Valid codes
        assert validate_language_code('zh') == 'zh'
        assert validate_language_code('en') == 'en'
        
        # Invalid codes
        with pytest.raises(ValueError):
            validate_language_code('invalid')
        
        with pytest.raises(ValueError):
            validate_language_code('')
        
        with pytest.raises(ValueError):
            validate_language_code(None)
    
    def test_translation_key_validation(self):
        """Test translation key validation."""
        # Valid keys
        assert validate_translation_key('login') == 'login'
        assert validate_translation_key('user_profile') == 'user_profile'
        assert validate_translation_key('app.name') == 'app.name'
        
        # Invalid keys
        with pytest.raises(ValueError):
            validate_translation_key('')  # Empty
        
        with pytest.raises(ValueError):
            validate_translation_key('key with spaces')  # Spaces
        
        with pytest.raises(ValueError):
            validate_translation_key('key@invalid')  # Special chars
```

## Integration Testing Procedures

### 1. API Integration Tests

```python
# tests/integration/test_api_integration.py

import pytest
from fastapi.testclient import TestClient
from src.app import app

class TestAPIIntegration:
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_language_detection_from_query(self):
        """Test language detection from query parameters."""
        # Test English
        response = self.client.get("/api/test?language=en")
        assert response.status_code == 200
        assert response.headers.get("Content-Language") == "en"
        
        # Test Chinese
        response = self.client.get("/api/test?language=zh")
        assert response.status_code == 200
        assert response.headers.get("Content-Language") == "zh"
    
    def test_language_detection_from_header(self):
        """Test language detection from Accept-Language header."""
        # Test English header
        response = self.client.get(
            "/api/test",
            headers={"Accept-Language": "en"}
        )
        assert response.status_code == 200
        assert response.headers.get("Content-Language") == "en"
        
        # Test Chinese header
        response = self.client.get(
            "/api/test",
            headers={"Accept-Language": "zh"}
        )
        assert response.status_code == 200
        assert response.headers.get("Content-Language") == "zh"
    
    def test_language_priority(self):
        """Test language detection priority (query > header)."""
        response = self.client.get(
            "/api/test?language=en",
            headers={"Accept-Language": "zh"}
        )
        assert response.status_code == 200
        # Query parameter should take priority
        assert response.headers.get("Content-Language") == "en"
    
    def test_language_management_endpoints(self):
        """Test language management API endpoints."""
        # Get current language settings
        response = self.client.get("/api/settings/language")
        assert response.status_code == 200
        data = response.json()
        assert "current_language" in data
        assert "supported_languages" in data
        
        # Change language
        response = self.client.post(
            "/api/settings/language",
            json={"language": "en"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_language"] == "en"
    
    def test_translation_endpoints(self):
        """Test translation retrieval endpoints."""
        # Get all translations
        response = self.client.get("/api/i18n/translations?language=en")
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "en"
        assert "translations" in data
        assert "login" in data["translations"]
        
        # Get supported languages
        response = self.client.get("/api/i18n/languages")
        assert response.status_code == 200
        data = response.json()
        assert "supported_languages" in data
        assert "zh" in data["supported_languages"]
        assert "en" in data["supported_languages"]
```

### 2. Middleware Integration Tests

```python
# tests/integration/test_middleware_integration.py

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from src.i18n.middleware import I18nMiddleware
from src.i18n.manager import get_current_language

class TestMiddlewareIntegration:
    def setup_method(self):
        """Set up test app with middleware."""
        self.app = FastAPI()
        self.app.add_middleware(I18nMiddleware)
        
        @self.app.get("/test")
        async def test_endpoint(request: Request):
            current_lang = get_current_language()
            return {"language": current_lang, "message": "test"}
        
        self.client = TestClient(self.app)
    
    def test_middleware_language_detection(self):
        """Test middleware language detection."""
        # Test query parameter detection
        response = self.client.get("/test?language=en")
        data = response.json()
        assert data["language"] == "en"
        assert response.headers.get("Content-Language") == "en"
        
        # Test header detection
        response = self.client.get(
            "/test",
            headers={"Accept-Language": "zh"}
        )
        data = response.json()
        assert data["language"] == "zh"
        assert response.headers.get("Content-Language") == "zh"
    
    def test_middleware_fallback(self):
        """Test middleware fallback to default language."""
        response = self.client.get("/test")
        data = response.json()
        assert data["language"] == "zh"  # Default language
        assert response.headers.get("Content-Language") == "zh"
    
    def test_middleware_invalid_language(self):
        """Test middleware handling of invalid language."""
        response = self.client.get("/test?language=invalid")
        data = response.json()
        assert data["language"] == "zh"  # Should fallback to default
        assert response.headers.get("Content-Language") == "zh"
```

## Property-Based Testing Procedures

### 1. Translation Properties

```python
# tests/property/test_translation_properties.py

import pytest
from hypothesis import given, strategies as st
from src.i18n.manager import get_manager
from src.i18n.translations import TRANSLATIONS

class TestTranslationProperties:
    @given(st.sampled_from(['zh', 'en']))
    def test_language_support_consistency(self, language):
        """Property 1: Language Support Consistency"""
        manager = get_manager()
        supported_languages = manager.get_supported_languages()
        
        # Any supported language should be in the supported list
        assert language in supported_languages
        
        # Should be able to set supported language
        manager.set_language(language)
        assert manager.get_language() == language
    
    @given(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))))
    def test_translation_key_consistency(self, key):
        """Property: Translation lookup should be consistent"""
        manager = get_manager()
        
        # Same key should return same translation
        translation1 = manager.translate(key, 'en')
        translation2 = manager.translate(key, 'en')
        
        assert translation1 == translation2
    
    @given(st.sampled_from(['zh', 'en']))
    def test_language_switching_immediacy(self, language):
        """Property 3: Language Switching Immediacy"""
        manager = get_manager()
        
        # Set language
        manager.set_language(language)
        
        # Should immediately reflect in current language
        assert manager.get_language() == language
        
        # Should immediately affect translations
        translation = manager.translate('login')
        expected = TRANSLATIONS[language]['login']
        assert translation == expected
    
    @given(st.text(min_size=1, max_size=10).filter(lambda x: x not in ['zh', 'en']))
    def test_invalid_language_validation(self, invalid_language):
        """Property 4: Invalid Language Validation"""
        manager = get_manager()
        original_language = manager.get_language()
        
        # Invalid language should raise exception or be rejected
        with pytest.raises(ValueError):
            manager.set_language(invalid_language)
        
        # Original language should be maintained
        assert manager.get_language() == original_language
    
    @given(st.lists(st.sampled_from(list(TRANSLATIONS['zh'].keys())), min_size=1, max_size=10))
    def test_batch_translation_consistency(self, keys):
        """Property 12: Batch Translation Consistency"""
        manager = get_manager()
        manager.set_language('en')
        
        # Batch translation
        batch_results = manager.translate_list(keys)
        
        # Individual translations
        individual_results = [manager.translate(key) for key in keys]
        
        # Should be identical
        assert batch_results == individual_results
    
    @given(st.sampled_from(['zh', 'en']))
    def test_complete_translation_retrieval(self, language):
        """Property 13: Complete Translation Retrieval"""
        manager = get_manager()
        
        all_translations = manager.get_all(language)
        
        # Should be a dictionary
        assert isinstance(all_translations, dict)
        
        # Should contain expected keys
        expected_keys = set(TRANSLATIONS[language].keys())
        actual_keys = set(all_translations.keys())
        
        assert expected_keys == actual_keys
```

### 2. API Properties

```python
# tests/property/test_api_properties.py

import pytest
from hypothesis import given, strategies as st
from fastapi.testclient import TestClient
from src.app import app

class TestAPIProperties:
    def setup_method(self):
        self.client = TestClient(app)
    
    @given(st.sampled_from(['zh', 'en']))
    def test_content_language_header_inclusion(self, language):
        """Property 9: Content-Language Header Inclusion"""
        response = self.client.get(f"/api/test?language={language}")
        
        # Should always include Content-Language header
        assert "Content-Language" in response.headers
        assert response.headers["Content-Language"] == language
    
    @given(st.sampled_from(['zh', 'en']))
    def test_http_status_code_appropriateness(self, language):
        """Property 17: HTTP Status Code Appropriateness"""
        # Valid language should return 200
        response = self.client.post(
            "/api/settings/language",
            json={"language": language}
        )
        assert response.status_code == 200
        
        # Invalid language should return 400
        response = self.client.post(
            "/api/settings/language",
            json={"language": "invalid"}
        )
        assert response.status_code == 400
    
    @given(st.text(min_size=1, max_size=20))
    def test_translation_coverage_completeness(self, endpoint_path):
        """Property 20: Translation Coverage Completeness"""
        # This is a simplified test - in practice, you'd test actual endpoints
        response = self.client.get(f"/api/test?language=en")
        
        if response.status_code == 200:
            data = response.json()
            # All text content should be translated (no Chinese characters in English response)
            text_content = str(data)
            # This is a simplified check - you'd implement more sophisticated detection
            assert not any(ord(char) > 0x4E00 and ord(char) < 0x9FFF for char in text_content)
```

## Performance Testing Procedures

### 1. Translation Lookup Performance

```python
# tests/performance/test_translation_performance.py

import pytest
import time
import statistics
from src.i18n.manager import get_manager

class TestTranslationPerformance:
    def setup_method(self):
        self.manager = get_manager()
        self.manager.set_language('en')
    
    def test_single_translation_performance(self):
        """Test single translation lookup performance."""
        # Warm up
        for _ in range(100):
            self.manager.translate('login')
        
        # Measure performance
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            self.manager.translate('login')
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to milliseconds
        
        # Performance assertions
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
        
        assert avg_time < 1.0, f"Average translation time {avg_time:.3f}ms exceeds 1ms"
        assert p95_time < 2.0, f"95th percentile time {p95_time:.3f}ms exceeds 2ms"
    
    def test_batch_translation_performance(self):
        """Test batch translation performance."""
        keys = ['login', 'logout', 'dashboard', 'settings', 'profile'] * 20  # 100 keys
        
        # Measure batch performance
        start = time.perf_counter()
        results = self.manager.translate_list(keys)
        end = time.perf_counter()
        
        batch_time = (end - start) * 1000  # milliseconds
        per_key_time = batch_time / len(keys)
        
        assert len(results) == len(keys)
        assert batch_time < 50.0, f"Batch translation time {batch_time:.3f}ms exceeds 50ms"
        assert per_key_time < 0.5, f"Per-key time {per_key_time:.3f}ms exceeds 0.5ms"
    
    def test_concurrent_translation_performance(self):
        """Test concurrent translation performance."""
        import threading
        import concurrent.futures
        
        def translation_worker():
            times = []
            for _ in range(100):
                start = time.perf_counter()
                self.manager.translate('login')
                end = time.perf_counter()
                times.append((end - start) * 1000)
            return times
        
        # Run concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(translation_worker) for _ in range(10)]
            all_times = []
            
            for future in concurrent.futures.as_completed(futures):
                all_times.extend(future.result())
        
        # Analyze concurrent performance
        avg_time = statistics.mean(all_times)
        p95_time = statistics.quantiles(all_times, n=20)[18]
        
        assert avg_time < 2.0, f"Concurrent avg time {avg_time:.3f}ms exceeds 2ms"
        assert p95_time < 5.0, f"Concurrent 95th percentile {p95_time:.3f}ms exceeds 5ms"
```

### 2. Memory Usage Tests

```python
# tests/performance/test_memory_usage.py

import pytest
import psutil
import os
import gc
from src.i18n.manager import get_manager

class TestMemoryUsage:
    def test_translation_memory_usage(self):
        """Test memory usage of translation operations."""
        process = psutil.Process(os.getpid())
        
        # Get baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss
        
        # Perform many translations
        manager = get_manager()
        for language in ['zh', 'en']:
            manager.set_language(language)
            for _ in range(10000):
                manager.translate('login')
                manager.translate('logout')
                manager.translate('dashboard')
        
        # Check memory after operations
        gc.collect()
        final_memory = process.memory_info().rss
        memory_increase = final_memory - baseline_memory
        
        # Memory increase should be minimal (less than 10MB)
        assert memory_increase < 10 * 1024 * 1024, f"Memory increased by {memory_increase / 1024 / 1024:.2f}MB"
    
    def test_context_variable_memory_leaks(self):
        """Test for context variable memory leaks."""
        import threading
        
        process = psutil.Process(os.getpid())
        gc.collect()
        baseline_memory = process.memory_info().rss
        
        def worker():
            manager = get_manager()
            for i in range(1000):
                language = 'en' if i % 2 == 0 else 'zh'
                manager.set_language(language)
                manager.translate('login')
        
        # Run many threads to test context cleanup
        threads = []
        for _ in range(50):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Force cleanup
        gc.collect()
        final_memory = process.memory_info().rss
        memory_increase = final_memory - baseline_memory
        
        # Should not have significant memory leaks
        assert memory_increase < 50 * 1024 * 1024, f"Potential memory leak: {memory_increase / 1024 / 1024:.2f}MB increase"
```

## End-to-End Testing Procedures

### 1. Complete User Workflows

```python
# tests/e2e/test_user_workflows.py

import pytest
from fastapi.testclient import TestClient
from src.app import app

class TestUserWorkflows:
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_language_switching_workflow(self):
        """Test complete language switching workflow."""
        # 1. Get initial language settings
        response = self.client.get("/api/settings/language")
        assert response.status_code == 200
        initial_data = response.json()
        assert initial_data["current_language"] == "zh"  # Default
        
        # 2. Switch to English
        response = self.client.post(
            "/api/settings/language",
            json={"language": "en"}
        )
        assert response.status_code == 200
        switch_data = response.json()
        assert switch_data["current_language"] == "en"
        
        # 3. Verify all subsequent requests use English
        response = self.client.get("/api/test")
        assert response.headers.get("Content-Language") == "en"
        
        # 4. Get translations in English
        response = self.client.get("/api/i18n/translations")
        assert response.status_code == 200
        translations_data = response.json()
        assert translations_data["language"] == "en"
        assert translations_data["translations"]["login"] == "Login"
        
        # 5. Switch back to Chinese
        response = self.client.post(
            "/api/settings/language",
            json={"language": "zh"}
        )
        assert response.status_code == 200
        
        # 6. Verify Chinese is active
        response = self.client.get("/api/i18n/translations")
        translations_data = response.json()
        assert translations_data["language"] == "zh"
        assert translations_data["translations"]["login"] == "登录"
    
    def test_multi_client_language_isolation(self):
        """Test that different clients can have different languages."""
        # Client 1 uses English
        response1 = self.client.get("/api/test?language=en")
        assert response1.headers.get("Content-Language") == "en"
        
        # Client 2 uses Chinese (different session)
        client2 = TestClient(app)
        response2 = client2.get("/api/test?language=zh")
        assert response2.headers.get("Content-Language") == "zh"
        
        # Verify isolation - client 1 still uses English
        response1_again = self.client.get("/api/test?language=en")
        assert response1_again.headers.get("Content-Language") == "en"
```

## Test Automation and CI/CD

### 1. Test Configuration

```yaml
# .github/workflows/i18n-tests.yml
name: I18n Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov hypothesis
    
    - name: Run unit tests
      run: pytest tests/unit/ -v --cov=src/i18n
    
    - name: Run integration tests
      run: pytest tests/integration/ -v
    
    - name: Run property-based tests
      run: pytest tests/property/ -v --hypothesis-show-statistics
    
    - name: Run performance tests
      run: pytest tests/performance/ -v
    
    - name: Generate coverage report
      run: pytest --cov=src/i18n --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v1
```

### 2. Test Data Management

```python
# tests/conftest.py

import pytest
from src.i18n.manager import TranslationManager
from src.i18n.translations import TRANSLATIONS

@pytest.fixture
def translation_manager():
    """Provide a fresh translation manager for each test."""
    return TranslationManager()

@pytest.fixture
def sample_translations():
    """Provide sample translations for testing."""
    return {
        'zh': {
            'test_key': '测试',
            'parameterized': '你好，{name}！'
        },
        'en': {
            'test_key': 'Test',
            'parameterized': 'Hello, {name}!'
        }
    }

@pytest.fixture(autouse=True)
def reset_context():
    """Reset context variables before each test."""
    from src.i18n.manager import set_language
    set_language('zh')  # Reset to default
    yield
    # Cleanup happens automatically with context variables
```

### 3. Test Reporting

```python
# tests/utils/test_reporter.py

import json
import time
from pathlib import Path

class TestReporter:
    def __init__(self):
        self.results = {
            'timestamp': time.time(),
            'test_suites': {},
            'summary': {}
        }
    
    def add_test_result(self, suite_name, test_name, status, duration, details=None):
        """Add a test result to the report."""
        if suite_name not in self.results['test_suites']:
            self.results['test_suites'][suite_name] = []
        
        self.results['test_suites'][suite_name].append({
            'name': test_name,
            'status': status,
            'duration': duration,
            'details': details or {}
        })
    
    def generate_summary(self):
        """Generate test summary statistics."""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        total_duration = 0
        
        for suite_name, tests in self.results['test_suites'].items():
            for test in tests:
                total_tests += 1
                total_duration += test['duration']
                
                if test['status'] == 'passed':
                    passed_tests += 1
                elif test['status'] == 'failed':
                    failed_tests += 1
        
        self.results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'total_duration': total_duration
        }
    
    def save_report(self, filename='test_report.json'):
        """Save the test report to a file."""
        self.generate_summary()
        
        report_path = Path('test_reports') / filename
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        return report_path
```

This comprehensive testing procedures document provides the foundation for ensuring the quality and reliability of the SuperInsight i18n system through systematic testing approaches.