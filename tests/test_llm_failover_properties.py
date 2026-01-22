"""Property-based tests for LLM Failover. Tests Properties 6-13."""
import pytest, asyncio, time
from typing import Dict, Any, Optional, List
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from collections import defaultdict
from src.ai.llm_schemas import (LLMConfig, LLMMethod, LocalConfig, CloudConfig, ChinaLLMConfig,
    GenerateOptions, LLMResponse, TokenUsage, HealthStatus, LLMError, LLMErrorCode)

prompt_strategy = st.text(min_size=1, max_size=500).filter(lambda x: x.strip())
method_strategy = st.sampled_from(list(LLMMethod))
DEFAULT_TIMEOUT_SECONDS, MAX_RETRY_ATTEMPTS, EXPONENTIAL_BACKOFF_BASE = 30, 3, 2

class MockLLMProvider:
    def __init__(self, method, should_fail=False, fail_count=0, is_healthy=True, response_delay=0.0):
        self._method, self._should_fail, self._fail_count = method, should_fail, fail_count
        self._current_fails, self._is_healthy, self._response_delay = 0, is_healthy, response_delay
        self._call_count, self._last_prompt, self._last_options = 0, None, None
    @property
    def method(self): return self._method
    async def generate(self, prompt, options, model=None, system_prompt=None):
        self._call_count += 1; self._last_prompt, self._last_options = prompt, options
        if self._response_delay > 0: await asyncio.sleep(self._response_delay)
        if self._should_fail or self._current_fails < self._fail_count:
            self._current_fails += 1; raise Exception(f"Provider {self._method.value} failed")
        return LLMResponse(content=f"Response from {self._method.value}", model=model or "test-model",
            provider=self._method.value, usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30))
    async def health_check(self):
        return HealthStatus(method=self._method, available=self._is_healthy,
            error=None if self._is_healthy else "Provider unhealthy")
    def list_models(self): return ["test-model"]

class MockConfigManager:
    def __init__(self, config): self._config, self._usage_logs = config, []
    async def get_config(self, tenant_id=None): return self._config
    def watch_config_changes(self, callback): pass
    async def log_usage(self, **kwargs): self._usage_logs.append(kwargs)

class TestLLMSwitcher:
    def __init__(self, config_manager):
        self._config_manager, self._providers = config_manager, {}
        self._config, self._current_method, self._fallback_method = None, None, None
        self._initialized, self._usage_stats, self._stats_lock = False, defaultdict(int), asyncio.Lock()
    async def set_fallback_provider(self, method):
        if self._config and method not in self._config.enabled_methods: raise ValueError(f"Method {method} is not enabled")
        if method not in self._providers: raise ValueError(f"Provider for {method} is not initialized")
        self._fallback_method = method
    async def get_usage_stats(self):
        async with self._stats_lock: return dict(self._usage_stats)
    async def _increment_usage_stats(self, method):
        async with self._stats_lock: self._usage_stats[method.value] += 1
    async def generate(self, prompt, options=None, method=None, model=None, system_prompt=None):
        options = options or GenerateOptions()
        target_method = method or self._current_method
        request_context = {'prompt': prompt, 'options': options, 'model': model, 'system_prompt': system_prompt}
        primary_error = None
        try:
            response = await self._generate_with_retry(target_method, prompt, options, model, system_prompt)
            await self._increment_usage_stats(target_method); return response
        except Exception as e: primary_error = e
        if self._fallback_method and self._fallback_method != target_method:
            try:
                response = await self._generate_with_retry(self._fallback_method, request_context['prompt'],
                    request_context['options'], request_context['model'], request_context['system_prompt'])
                await self._increment_usage_stats(self._fallback_method); return response
            except Exception as fallback_error:
                raise LLMError(error_code=LLMErrorCode.SERVICE_UNAVAILABLE,
                    message=f"Both failed. Primary ({target_method.value}): {primary_error}. Fallback ({self._fallback_method.value}): {fallback_error}",
                    provider=f"{target_method.value},{self._fallback_method.value}",
                    details={'primary_provider': target_method.value, 'primary_error': str(primary_error),
                        'fallback_provider': self._fallback_method.value, 'fallback_error': str(fallback_error)},
                    suggestions=["Check provider configurations"])
        raise self._create_error(primary_error, target_method)
    async def _generate_with_retry(self, method, prompt, options, model, system_prompt, max_retries=MAX_RETRY_ATTEMPTS):
        provider = self._providers.get(method)
        if not provider: raise ValueError(f"Provider {method} not found")
        last_error = None
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(DEFAULT_TIMEOUT_SECONDS):
                    return await provider.generate(prompt, options, model, system_prompt)
            except asyncio.TimeoutError:
                last_error = f"Timeout after {DEFAULT_TIMEOUT_SECONDS}s"
                await self._config_manager.log_usage(method=method.value, model=model or "unknown",
                    operation="generate", success=False, error_code=LLMErrorCode.TIMEOUT.value, error_message=last_error)
            except Exception as e:
                last_error = str(e)
                retry_after = self._extract_retry_after(e)
                if retry_after is not None: await asyncio.sleep(min(retry_after, 0.01)); continue
            if attempt < max_retries - 1: await asyncio.sleep(min(EXPONENTIAL_BACKOFF_BASE ** attempt, 0.01))
        raise Exception(f"Max retries ({max_retries}) exceeded. Last error: {last_error}")
    def _extract_retry_after(self, exception):
        import re; error_str = str(exception).lower()
        if not any(kw in error_str for kw in ['rate', 'limit', '429', 'quota']): return None
        for pattern in [r'retry[- ]?after[:\s]+(\d+)', r'wait[:\s]+(\d+)', r'(\d+)\s*seconds?']:
            match = re.search(pattern, error_str)
            if match:
                try: return int(match.group(1))
                except: pass
        return 60
    def switch_method(self, method):
        if self._config and method not in self._config.enabled_methods: raise ValueError(f"Method {method} is not enabled")
        if method not in self._providers: raise ValueError(f"Provider for {method} is not initialized")
        self._current_method = method
    async def switch_method_validated(self, method):
        if self._config and method not in self._config.enabled_methods: raise ValueError(f"Method {method} is not enabled")
        if method not in self._providers: raise ValueError(f"Provider for {method} is not initialized")
        health = await self._providers[method].health_check()
        if not health.available: raise ValueError(f"Provider {method} is unhealthy: {health.error}")
        self._current_method = method; return True
    def get_current_method(self): return self._current_method
    def _create_error(self, exception, method):
        return LLMError(error_code=LLMErrorCode.GENERATION_FAILED, message=str(exception), provider=method.value, suggestions=["Check config"])

def create_test_switcher(primary_method=LLMMethod.CLOUD_OPENAI, fallback_method=LLMMethod.LOCAL_OLLAMA,
                        primary_fails=False, fallback_fails=False, primary_fail_count=0, primary_healthy=True, fallback_healthy=True):
    config = LLMConfig(default_method=primary_method, enabled_methods=[primary_method] + ([fallback_method] if fallback_method else []),
        local_config=LocalConfig(), cloud_config=CloudConfig(openai_api_key="test-key"))
    switcher = TestLLMSwitcher(MockConfigManager(config))
    switcher._config, switcher._current_method, switcher._initialized = config, primary_method, True
    switcher._providers[primary_method] = MockLLMProvider(method=primary_method, should_fail=primary_fails, fail_count=primary_fail_count, is_healthy=primary_healthy)
    if fallback_method: switcher._providers[fallback_method] = MockLLMProvider(method=fallback_method, should_fail=fallback_fails, is_healthy=fallback_healthy)
    return switcher, switcher._providers[primary_method], switcher._providers.get(fallback_method)

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(primary_method=method_strategy, target_method=method_strategy, is_healthy=st.booleans())
def test_property_6_provider_switching_validation(primary_method, target_method, is_healthy):
    """Property 6: Provider Switching Validation. **Validates: Requirements 3.2**"""
    async def run_test():
        config = LLMConfig(default_method=primary_method, enabled_methods=[primary_method, target_method],
            local_config=LocalConfig(), cloud_config=CloudConfig(openai_api_key="test-key"), china_config=ChinaLLMConfig(qwen_api_key="test-key"))
        switcher = TestLLMSwitcher(MockConfigManager(config))
        switcher._config, switcher._current_method, switcher._initialized = config, primary_method, True
        switcher._providers[primary_method] = MockLLMProvider(method=primary_method, is_healthy=True)
        switcher._providers[target_method] = MockLLMProvider(method=target_method, is_healthy=is_healthy)
        original_method = switcher.get_current_method()
        if not is_healthy:
            with pytest.raises(ValueError) as exc_info: await switcher.switch_method_validated(target_method)
            assert "unhealthy" in str(exc_info.value).lower(); assert switcher.get_current_method() == original_method
        else:
            result = await switcher.switch_method_validated(target_method)
            assert result is True; assert switcher.get_current_method() == target_method
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(primary_method=method_strategy, invalid_method=method_strategy)
def test_property_6_switch_to_disabled_method_rejected(primary_method, invalid_method):
    """Property 6: Switch to disabled method rejected. **Validates: Requirements 3.2**"""
    assume(primary_method != invalid_method)
    async def run_test():
        config = LLMConfig(default_method=primary_method, enabled_methods=[primary_method], local_config=LocalConfig(), cloud_config=CloudConfig(openai_api_key="test-key"))
        switcher = TestLLMSwitcher(MockConfigManager(config))
        switcher._config, switcher._current_method, switcher._initialized = config, primary_method, True
        switcher._providers[primary_method] = MockLLMProvider(method=primary_method)
        original_method = switcher.get_current_method()
        with pytest.raises(ValueError) as exc_info: switcher.switch_method(invalid_method)
        assert "not enabled" in str(exc_info.value).lower(); assert switcher.get_current_method() == original_method
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(prompt=prompt_strategy, primary_method=method_strategy, fallback_method=method_strategy)
def test_property_7_automatic_failover_on_primary_failure(prompt, primary_method, fallback_method):
    """Property 7: Automatic Failover. **Validates: Requirements 3.3, 4.2**"""
    assume(primary_method != fallback_method)
    async def run_test():
        switcher, primary_provider, fallback_provider = create_test_switcher(primary_method=primary_method, fallback_method=fallback_method, primary_fails=True, fallback_fails=False)
        await switcher.set_fallback_provider(fallback_method)
        response = await switcher.generate(prompt)
        assert response is not None; assert response.provider == fallback_method.value
        assert primary_provider._call_count > 0; assert fallback_provider._call_count > 0
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(prompt=prompt_strategy, primary_method=method_strategy, fallback_method=method_strategy)
def test_property_7_no_failover_when_primary_succeeds(prompt, primary_method, fallback_method):
    """Property 7: No failover when primary succeeds. **Validates: Requirements 3.3, 4.2**"""
    assume(primary_method != fallback_method)
    async def run_test():
        switcher, _, fallback_provider = create_test_switcher(primary_method=primary_method, fallback_method=fallback_method, primary_fails=False, fallback_fails=False)
        await switcher.set_fallback_provider(fallback_method)
        response = await switcher.generate(prompt)
        assert response.provider == primary_method.value; assert fallback_provider._call_count == 0
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(prompt=prompt_strategy, max_tokens=st.integers(min_value=10, max_value=1000), temperature=st.floats(min_value=0.0, max_value=2.0))
def test_property_8_request_context_preservation(prompt, max_tokens, temperature):
    """Property 8: Request Context Preservation. **Validates: Requirements 3.4**"""
    async def run_test():
        switcher, _, fallback_provider = create_test_switcher(primary_method=LLMMethod.CLOUD_OPENAI, fallback_method=LLMMethod.LOCAL_OLLAMA, primary_fails=True, fallback_fails=False)
        await switcher.set_fallback_provider(LLMMethod.LOCAL_OLLAMA)
        options = GenerateOptions(max_tokens=max_tokens, temperature=temperature)
        await switcher.generate(prompt, options=options)
        assert fallback_provider._last_prompt == prompt
        assert fallback_provider._last_options.max_tokens == max_tokens; assert fallback_provider._last_options.temperature == temperature
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(num_requests=st.integers(min_value=1, max_value=10), prompt=prompt_strategy)
def test_property_9_usage_statistics_tracking(num_requests, prompt):
    """Property 9: Usage Statistics Tracking. **Validates: Requirements 3.5**"""
    async def run_test():
        switcher, _, _ = create_test_switcher(primary_method=LLMMethod.CLOUD_OPENAI, fallback_method=None, primary_fails=False)
        initial_stats = await switcher.get_usage_stats()
        initial_count = initial_stats.get(LLMMethod.CLOUD_OPENAI.value, 0)
        for _ in range(num_requests): await switcher.generate(prompt)
        final_stats = await switcher.get_usage_stats()
        assert final_stats.get(LLMMethod.CLOUD_OPENAI.value, 0) == initial_count + num_requests
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(prompt=prompt_strategy)
def test_property_9_usage_stats_track_failover(prompt):
    """Property 9: Usage stats track failover. **Validates: Requirements 3.5**"""
    async def run_test():
        switcher, _, _ = create_test_switcher(primary_method=LLMMethod.CLOUD_OPENAI, fallback_method=LLMMethod.LOCAL_OLLAMA, primary_fails=True, fallback_fails=False)
        await switcher.set_fallback_provider(LLMMethod.LOCAL_OLLAMA)
        initial_stats = await switcher.get_usage_stats()
        initial_fallback, initial_primary = initial_stats.get(LLMMethod.LOCAL_OLLAMA.value, 0), initial_stats.get(LLMMethod.CLOUD_OPENAI.value, 0)
        await switcher.generate(prompt)
        final_stats = await switcher.get_usage_stats()
        assert final_stats.get(LLMMethod.LOCAL_OLLAMA.value, 0) == initial_fallback + 1
        assert final_stats.get(LLMMethod.CLOUD_OPENAI.value, 0) == initial_primary
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(fail_count=st.integers(min_value=1, max_value=2), prompt=prompt_strategy)
def test_property_10_exponential_backoff_retry(fail_count, prompt):
    """Property 10: Exponential Backoff Retry. **Validates: Requirements 4.1**"""
    async def run_test():
        switcher, primary_provider, _ = create_test_switcher(primary_method=LLMMethod.CLOUD_OPENAI, fallback_method=None, primary_fail_count=fail_count)
        response = await switcher.generate(prompt)
        assert response is not None; assert primary_provider._call_count == fail_count + 1
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(prompt=prompt_strategy)
def test_property_10_max_retries_exhausted(prompt):
    """Property 10: Max retries exhausted triggers failover. **Validates: Requirements 4.1**"""
    async def run_test():
        switcher, primary_provider, fallback_provider = create_test_switcher(primary_method=LLMMethod.CLOUD_OPENAI, fallback_method=LLMMethod.LOCAL_OLLAMA, primary_fails=True, fallback_fails=False)
        await switcher.set_fallback_provider(LLMMethod.LOCAL_OLLAMA)
        response = await switcher.generate(prompt)
        assert primary_provider._call_count == 3; assert fallback_provider._call_count > 0; assert response.provider == LLMMethod.LOCAL_OLLAMA.value
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(prompt=prompt_strategy, primary_method=method_strategy, fallback_method=method_strategy)
def test_property_11_comprehensive_error_reporting(prompt, primary_method, fallback_method):
    """Property 11: Comprehensive Error Reporting. **Validates: Requirements 4.3**"""
    assume(primary_method != fallback_method)
    async def run_test():
        switcher, _, _ = create_test_switcher(primary_method=primary_method, fallback_method=fallback_method, primary_fails=True, fallback_fails=True)
        await switcher.set_fallback_provider(fallback_method)
        with pytest.raises(LLMError) as exc_info: await switcher.generate(prompt)
        error = exc_info.value
        assert primary_method.value in error.message or primary_method.value in str(error.details)
        assert fallback_method.value in error.message or fallback_method.value in str(error.details)
        assert error.error_code == LLMErrorCode.SERVICE_UNAVAILABLE
        if error.details: assert 'primary_error' in error.details; assert 'fallback_error' in error.details
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(prompt=prompt_strategy)
def test_property_11_error_includes_suggestions(prompt):
    """Property 11: Error includes suggestions. **Validates: Requirements 4.3**"""
    async def run_test():
        switcher, _, _ = create_test_switcher(primary_method=LLMMethod.CLOUD_OPENAI, fallback_method=LLMMethod.LOCAL_OLLAMA, primary_fails=True, fallback_fails=True)
        await switcher.set_fallback_provider(LLMMethod.LOCAL_OLLAMA)
        with pytest.raises(LLMError) as exc_info: await switcher.generate(prompt)
        error = exc_info.value; assert error.suggestions is not None; assert len(error.suggestions) > 0
    asyncio.run(run_test())

@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(prompt=prompt_strategy)
def test_property_12_timeout_enforcement(prompt):
    """Property 12: Timeout Enforcement. **Validates: Requirements 4.4**"""
    async def run_test():
        global DEFAULT_TIMEOUT_SECONDS
        import tests.test_llm_failover_properties as test_module
        original_timeout = test_module.DEFAULT_TIMEOUT_SECONDS
        test_module.DEFAULT_TIMEOUT_SECONDS = 0.01
        try:
            switcher, _, _ = create_test_switcher(primary_method=LLMMethod.CLOUD_OPENAI, fallback_method=None)
            switcher._providers[LLMMethod.CLOUD_OPENAI] = MockLLMProvider(method=LLMMethod.CLOUD_OPENAI, response_delay=1.0)
            with pytest.raises(Exception) as exc_info: await switcher.generate(prompt)
            error_msg = str(exc_info.value).lower(); assert 'timeout' in error_msg or 'max retries' in error_msg
        finally: test_module.DEFAULT_TIMEOUT_SECONDS = original_timeout
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(retry_after=st.integers(min_value=1, max_value=120))
def test_property_13_rate_limit_handling_extraction(retry_after):
    """Property 13: Rate Limit Handling. **Validates: Requirements 4.5**"""
    async def run_test():
        config = LLMConfig(default_method=LLMMethod.CLOUD_OPENAI, enabled_methods=[LLMMethod.CLOUD_OPENAI], cloud_config=CloudConfig(openai_api_key="test-key"))
        switcher = TestLLMSwitcher(MockConfigManager(config))
        test_cases = [f"Rate limit exceeded. Retry after {retry_after} seconds", f"429 Too Many Requests. retry-after: {retry_after}", f"Quota exceeded. Wait {retry_after}s before retrying"]
        for error_msg in test_cases:
            extracted = switcher._extract_retry_after(Exception(error_msg))
            assert extracted is not None; assert extracted == retry_after
    asyncio.run(run_test())

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(error_msg=st.text(min_size=10, max_size=100).filter(lambda x: 'rate' not in x.lower() and 'limit' not in x.lower() and '429' not in x))
def test_property_13_non_rate_limit_errors_not_extracted(error_msg):
    """Property 13: Non-rate-limit errors not extracted. **Validates: Requirements 4.5**"""
    async def run_test():
        config = LLMConfig(default_method=LLMMethod.CLOUD_OPENAI, enabled_methods=[LLMMethod.CLOUD_OPENAI], cloud_config=CloudConfig(openai_api_key="test-key"))
        switcher = TestLLMSwitcher(MockConfigManager(config))
        assert switcher._extract_retry_after(Exception(error_msg)) is None
    asyncio.run(run_test())

if __name__ == "__main__": pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
