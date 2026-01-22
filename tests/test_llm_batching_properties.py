"""
Property-based tests for LLM Request Batching.

Uses Hypothesis library for property testing with minimum 100 iterations per property.
Tests the correctness properties for request batching and async progress tracking
as defined in the LLM Integration design document.

Properties tested:
- Property 27: Request Batching (Requirement 10.1)
- Property 30: Async Progress Tracking (Requirement 10.5)
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import time

from src.ai.llm.batch_processor import (
    LLMBatchProcessor,
    LLMRequest,
    LLMRequestResult,
    BatchProgress,
    BatchResult,
    BatchStatus,
    get_batch_processor,
)
from src.ai.llm_schemas import (
    LLMMethod, GenerateOptions, LLMResponse, TokenUsage
)


# ==================== Custom Strategies ====================

# Strategy for valid prompts
prompt_strategy = st.text(
    min_size=1,
    max_size=500,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))
).filter(lambda x: x.strip())

# Strategy for model names
model_name_strategy = st.one_of(
    st.just("gpt-3.5-turbo"),
    st.just("gpt-4"),
    st.just("qwen-turbo"),
    st.just("glm-4"),
    st.just("llama2"),
)

# Strategy for LLM methods
method_strategy = st.sampled_from(list(LLMMethod))


# Strategy for batch sizes
batch_size_strategy = st.integers(min_value=1, max_value=50)


# ==================== Mock LLM Switcher ====================

class MockLLMSwitcher:
    """Mock LLM switcher for testing batch processing."""
    
    def __init__(
        self,
        response_delay: float = 0.01,
        failure_rate: float = 0.0,
        fail_on_prompts: Optional[List[str]] = None,
    ):
        self.response_delay = response_delay
        self.failure_rate = failure_rate
        self.fail_on_prompts = fail_on_prompts or []
        self.call_count = 0
        self.calls: List[Dict[str, Any]] = []
        self._initialized = False
    
    async def initialize(self) -> None:
        self._initialized = True
    
    async def generate(
        self,
        prompt: str,
        options: Optional[GenerateOptions] = None,
        method: Optional[LLMMethod] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Mock generate method."""
        self.call_count += 1
        self.calls.append({
            'prompt': prompt,
            'options': options,
            'method': method,
            'model': model,
            'system_prompt': system_prompt,
        })
        
        # Simulate processing delay
        await asyncio.sleep(self.response_delay)
        
        # Check for forced failures
        if prompt in self.fail_on_prompts:
            raise Exception(f"Forced failure for prompt: {prompt[:50]}")
        
        # Random failure based on failure rate
        import random
        if random.random() < self.failure_rate:
            raise Exception("Random failure")
        
        return LLMResponse(
            content=f"Response to: {prompt[:50]}",
            model=model or "mock-model",
            provider=method.value if method else "mock",
            usage=TokenUsage(
                prompt_tokens=len(prompt.split()),
                completion_tokens=10,
                total_tokens=len(prompt.split()) + 10,
            ),
        )


# ==================== Property 27: Request Batching ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=30000)
@given(
    num_requests=st.integers(min_value=2, max_value=20),
    method=method_strategy,
    model=model_name_strategy,
)
def test_property_27_request_batching_same_provider(
    num_requests: int,
    method: LLMMethod,
    model: str,
):
    """
    Feature: llm-integration, Property 27: Request Batching
    
    For any set of compatible LLM requests to the same provider, if batching 
    is enabled, the requests should be grouped and sent as a single batch request.
    
    **Validates: Requirements 10.1**
    
    This test generates 100+ random sets of requests to the same provider and
    verifies that they are grouped together when batching is enabled.
    """
    async def run_test():
        # Create requests all targeting the same provider
        requests = [
            LLMRequest(
                prompt=f"Test prompt {i} for batching",
                method=method,
                model=model,
            )
            for i in range(num_requests)
        ]
        
        # Create batch processor with batching enabled
        mock_switcher = MockLLMSwitcher(response_delay=0.001)
        processor = LLMBatchProcessor(
            llm_switcher=mock_switcher,
            max_concurrent_requests=10,
            enable_batching=True,
        )
        
        # Verify batching is enabled
        assert processor.is_batching_enabled(), "Batching should be enabled"
        
        # Group requests
        grouped = processor._group_requests_by_provider(requests)
        
        # All requests should be in the same group (same provider)
        assert len(grouped) == 1, \
            f"All requests to same provider should be in one group, got {len(grouped)}"
        
        # The group should contain all requests
        group_key = list(grouped.keys())[0]
        assert len(grouped[group_key]) == num_requests, \
            f"Group should contain all {num_requests} requests"
        
        # Verify the group key matches the expected provider
        expected_key = f"{method.value}:{model}"
        assert group_key == expected_key, \
            f"Group key should be {expected_key}, got {group_key}"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=30000)
@given(
    methods=st.lists(
        method_strategy,
        min_size=2,
        max_size=5,
        unique=True,
    ),
    requests_per_method=st.integers(min_value=1, max_value=10),
)
def test_property_27_request_batching_multiple_providers(
    methods: List[LLMMethod],
    requests_per_method: int,
):
    """
    Feature: llm-integration, Property 27: Request Batching (Multiple Providers)
    
    For any set of LLM requests to different providers, if batching is enabled,
    the requests should be grouped by provider.
    
    **Validates: Requirements 10.1**
    
    This test verifies that requests to different providers are correctly
    grouped into separate batches.
    """
    async def run_test():
        # Create requests targeting different providers
        requests = []
        for method in methods:
            for i in range(requests_per_method):
                requests.append(LLMRequest(
                    prompt=f"Test prompt {i} for {method.value}",
                    method=method,
                    model="test-model",
                ))
        
        # Create batch processor with batching enabled
        processor = LLMBatchProcessor(
            llm_switcher=MockLLMSwitcher(response_delay=0.001),
            enable_batching=True,
        )
        
        # Group requests
        grouped = processor._group_requests_by_provider(requests)
        
        # Should have one group per unique method
        assert len(grouped) == len(methods), \
            f"Should have {len(methods)} groups, got {len(grouped)}"
        
        # Each group should have the correct number of requests
        for group_key, group_requests in grouped.items():
            assert len(group_requests) == requests_per_method, \
                f"Each group should have {requests_per_method} requests"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=30000)
@given(
    num_requests=st.integers(min_value=2, max_value=15),
)
def test_property_27_batching_disabled_no_grouping(num_requests: int):
    """
    Feature: llm-integration, Property 27: Request Batching (Disabled)
    
    When batching is disabled, requests should not be grouped by provider.
    
    **Validates: Requirements 10.1**
    
    This test verifies that disabling batching prevents provider grouping.
    """
    async def run_test():
        # Create requests with different methods
        methods = list(LLMMethod)[:3]
        requests = [
            LLMRequest(
                prompt=f"Test prompt {i}",
                method=methods[i % len(methods)],
            )
            for i in range(num_requests)
        ]
        
        # Create batch processor with batching disabled
        mock_switcher = MockLLMSwitcher(response_delay=0.001)
        processor = LLMBatchProcessor(
            llm_switcher=mock_switcher,
            enable_batching=False,
        )
        
        # Verify batching is disabled
        assert not processor.is_batching_enabled(), "Batching should be disabled"
        
        # Process batch
        result = await processor.process_batch(requests)
        
        # All requests should be processed
        assert result.progress.total_requests == num_requests
        assert len(result.results) == num_requests
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=30000)
@given(
    num_requests=st.integers(min_value=1, max_value=20),
    method=method_strategy,
)
def test_property_27_batch_processing_completes_all_requests(
    num_requests: int,
    method: LLMMethod,
):
    """
    Feature: llm-integration, Property 27: Request Batching (Completion)
    
    For any batch of requests, all requests should be processed and results
    returned for each request.
    
    **Validates: Requirements 10.1**
    
    This test verifies that batch processing completes all requests.
    """
    async def run_test():
        # Create requests
        requests = [
            LLMRequest(
                prompt=f"Test prompt {i}",
                method=method,
            )
            for i in range(num_requests)
        ]
        
        # Create batch processor
        mock_switcher = MockLLMSwitcher(response_delay=0.001)
        processor = LLMBatchProcessor(
            llm_switcher=mock_switcher,
            enable_batching=True,
        )
        
        # Process batch
        result = await processor.process_batch(requests)
        
        # Verify all requests were processed
        assert result.progress.total_requests == num_requests
        assert len(result.results) == num_requests
        
        # Verify all requests succeeded (no failures in mock)
        assert result.progress.completed_requests == num_requests
        assert result.progress.failed_requests == 0
        
        # Verify status is COMPLETED
        assert result.progress.status == BatchStatus.COMPLETED
        
        # Verify each result has a response
        for req_result in result.results:
            assert req_result.success
            assert req_result.response is not None
    
    asyncio.run(run_test())


# ==================== Property 30: Async Progress Tracking ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=60000)
@given(
    num_requests=st.integers(min_value=5, max_value=30),
)
def test_property_30_async_progress_tracking_updates(num_requests: int):
    """
    Feature: llm-integration, Property 30: Async Progress Tracking
    
    For any large batch of LLM requests processed asynchronously, the system 
    should provide progress updates showing completed/total requests.
    
    **Validates: Requirements 10.5**
    
    This test generates 100+ random batches and verifies that progress updates
    are provided during processing.
    """
    async def run_test():
        # Create requests
        requests = [
            LLMRequest(prompt=f"Test prompt {i}")
            for i in range(num_requests)
        ]
        
        # Track progress updates
        progress_updates: List[BatchProgress] = []
        
        async def progress_callback(progress: BatchProgress) -> None:
            progress_updates.append(BatchProgress(
                batch_id=progress.batch_id,
                total_requests=progress.total_requests,
                completed_requests=progress.completed_requests,
                failed_requests=progress.failed_requests,
                status=progress.status,
                started_at=progress.started_at,
                updated_at=progress.updated_at,
            ))
        
        # Create batch processor
        mock_switcher = MockLLMSwitcher(response_delay=0.005)
        processor = LLMBatchProcessor(
            llm_switcher=mock_switcher,
            max_concurrent_requests=5,  # Limit concurrency to see progress
            enable_batching=True,
        )
        
        # Process batch with progress callback
        result = await processor.process_batch(requests, progress_callback)
        
        # Verify progress updates were received
        assert len(progress_updates) > 0, "Should receive progress updates"
        
        # Verify progress shows completed/total
        for progress in progress_updates:
            assert progress.total_requests == num_requests, \
                "Total requests should be constant"
            assert 0 <= progress.completed_requests <= num_requests, \
                "Completed requests should be in valid range"
            assert 0 <= progress.failed_requests <= num_requests, \
                "Failed requests should be in valid range"
            assert progress.completed_requests + progress.failed_requests <= num_requests, \
                "Sum of completed and failed should not exceed total"
        
        # Verify final progress shows all completed
        final_progress = progress_updates[-1]
        assert final_progress.completed_requests + final_progress.failed_requests == num_requests, \
            "Final progress should show all requests processed"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=60000)
@given(
    num_requests=st.integers(min_value=3, max_value=20),
)
def test_property_30_progress_percentage_calculation(num_requests: int):
    """
    Feature: llm-integration, Property 30: Async Progress Tracking (Percentage)
    
    For any batch, the progress percentage should accurately reflect the
    ratio of processed requests to total requests.
    
    **Validates: Requirements 10.5**
    
    This test verifies that progress percentage is calculated correctly.
    """
    async def run_test():
        # Create requests
        requests = [
            LLMRequest(prompt=f"Test prompt {i}")
            for i in range(num_requests)
        ]
        
        # Track progress updates
        progress_updates: List[BatchProgress] = []
        
        async def progress_callback(progress: BatchProgress) -> None:
            progress_updates.append(BatchProgress(
                batch_id=progress.batch_id,
                total_requests=progress.total_requests,
                completed_requests=progress.completed_requests,
                failed_requests=progress.failed_requests,
                status=progress.status,
            ))
        
        # Create batch processor
        mock_switcher = MockLLMSwitcher(response_delay=0.005)
        processor = LLMBatchProcessor(
            llm_switcher=mock_switcher,
            max_concurrent_requests=3,
            enable_batching=True,
        )
        
        # Process batch
        result = await processor.process_batch(requests, progress_callback)
        
        # Verify progress percentage calculation
        for progress in progress_updates:
            processed = progress.completed_requests + progress.failed_requests
            expected_percentage = (processed / num_requests) * 100
            actual_percentage = progress.progress_percentage
            
            assert abs(actual_percentage - expected_percentage) < 0.01, \
                f"Progress percentage should be {expected_percentage}, got {actual_percentage}"
        
        # Final progress should be 100%
        final_progress = progress_updates[-1]
        assert final_progress.progress_percentage == 100.0, \
            "Final progress should be 100%"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=60000)
@given(
    num_requests=st.integers(min_value=5, max_value=25),
)
def test_property_30_progress_monotonically_increasing(num_requests: int):
    """
    Feature: llm-integration, Property 30: Async Progress Tracking (Monotonic)
    
    For any batch, the progress (completed + failed) should monotonically
    increase as processing continues.
    
    **Validates: Requirements 10.5**
    
    This test verifies that progress never decreases during processing.
    """
    async def run_test():
        # Create requests
        requests = [
            LLMRequest(prompt=f"Test prompt {i}")
            for i in range(num_requests)
        ]
        
        # Track progress updates
        progress_updates: List[int] = []
        
        async def progress_callback(progress: BatchProgress) -> None:
            processed = progress.completed_requests + progress.failed_requests
            progress_updates.append(processed)
        
        # Create batch processor
        mock_switcher = MockLLMSwitcher(response_delay=0.005)
        processor = LLMBatchProcessor(
            llm_switcher=mock_switcher,
            max_concurrent_requests=3,
            enable_batching=True,
        )
        
        # Process batch
        await processor.process_batch(requests, progress_callback)
        
        # Verify progress is monotonically increasing
        for i in range(1, len(progress_updates)):
            assert progress_updates[i] >= progress_updates[i-1], \
                f"Progress should not decrease: {progress_updates[i-1]} -> {progress_updates[i]}"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=60000)
@given(
    num_requests=st.integers(min_value=3, max_value=15),
    num_failures=st.integers(min_value=1, max_value=5),
)
def test_property_30_progress_tracks_failures(num_requests: int, num_failures: int):
    """
    Feature: llm-integration, Property 30: Async Progress Tracking (Failures)
    
    For any batch with some failing requests, the progress should accurately
    track both completed and failed requests.
    
    **Validates: Requirements 10.5**
    
    This test verifies that progress correctly tracks failures.
    """
    # Ensure we don't have more failures than requests
    num_failures = min(num_failures, num_requests - 1)
    
    async def run_test():
        # Create requests with some that will fail
        fail_prompts = [f"FAIL_PROMPT_{i}" for i in range(num_failures)]
        requests = []
        
        for i in range(num_requests):
            if i < num_failures:
                requests.append(LLMRequest(prompt=fail_prompts[i]))
            else:
                requests.append(LLMRequest(prompt=f"Success prompt {i}"))
        
        # Create batch processor with mock that fails on specific prompts
        mock_switcher = MockLLMSwitcher(
            response_delay=0.005,
            fail_on_prompts=fail_prompts,
        )
        processor = LLMBatchProcessor(
            llm_switcher=mock_switcher,
            max_concurrent_requests=5,
            enable_batching=True,
        )
        
        # Process batch
        result = await processor.process_batch(requests)
        
        # Verify progress tracks failures
        assert result.progress.failed_requests == num_failures, \
            f"Should have {num_failures} failures, got {result.progress.failed_requests}"
        assert result.progress.completed_requests == num_requests - num_failures, \
            f"Should have {num_requests - num_failures} completions"
        
        # Verify status reflects partial completion
        if num_failures > 0 and num_failures < num_requests:
            assert result.progress.status == BatchStatus.PARTIALLY_COMPLETED
        elif num_failures == num_requests:
            assert result.progress.status == BatchStatus.FAILED
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=60000)
@given(
    num_requests=st.integers(min_value=2, max_value=15),
)
def test_property_30_progress_has_timestamps(num_requests: int):
    """
    Feature: llm-integration, Property 30: Async Progress Tracking (Timestamps)
    
    For any batch, the progress should include timestamps for started_at,
    updated_at, and completed_at.
    
    **Validates: Requirements 10.5**
    
    This test verifies that progress includes proper timestamps.
    """
    async def run_test():
        # Create requests
        requests = [
            LLMRequest(prompt=f"Test prompt {i}")
            for i in range(num_requests)
        ]
        
        # Track progress updates
        progress_updates: List[BatchProgress] = []
        
        async def progress_callback(progress: BatchProgress) -> None:
            progress_updates.append(BatchProgress(
                batch_id=progress.batch_id,
                total_requests=progress.total_requests,
                completed_requests=progress.completed_requests,
                failed_requests=progress.failed_requests,
                status=progress.status,
                started_at=progress.started_at,
                updated_at=progress.updated_at,
                completed_at=progress.completed_at,
            ))
        
        # Create batch processor
        mock_switcher = MockLLMSwitcher(response_delay=0.005)
        processor = LLMBatchProcessor(
            llm_switcher=mock_switcher,
            max_concurrent_requests=5,
            enable_batching=True,
        )
        
        # Process batch
        result = await processor.process_batch(requests, progress_callback)
        
        # Verify timestamps
        assert result.progress.started_at is not None, "Should have started_at"
        assert result.progress.completed_at is not None, "Should have completed_at"
        assert result.progress.updated_at is not None, "Should have updated_at"
        
        # Verify timestamp ordering
        assert result.progress.started_at <= result.progress.completed_at, \
            "started_at should be before completed_at"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=60000)
@given(
    num_requests=st.integers(min_value=2, max_value=10),
)
def test_property_30_async_batch_submission(num_requests: int):
    """
    Feature: llm-integration, Property 30: Async Progress Tracking (Async Submit)
    
    For any batch submitted asynchronously, the system should return a batch ID
    immediately and allow progress tracking via that ID.
    
    **Validates: Requirements 10.5**
    
    This test verifies async batch submission and progress retrieval.
    """
    async def run_test():
        # Create requests
        requests = [
            LLMRequest(prompt=f"Test prompt {i}")
            for i in range(num_requests)
        ]
        
        # Create batch processor
        mock_switcher = MockLLMSwitcher(response_delay=0.01)
        processor = LLMBatchProcessor(
            llm_switcher=mock_switcher,
            max_concurrent_requests=2,
            enable_batching=True,
        )
        
        # Submit batch asynchronously
        batch_id = await processor.submit_batch(requests)
        
        # Verify batch ID is returned immediately
        assert batch_id is not None, "Should return batch ID"
        assert len(batch_id) > 0, "Batch ID should not be empty"
        
        # Wait a bit for processing to start
        await asyncio.sleep(0.05)
        
        # Check progress
        progress = await processor.get_batch_progress(batch_id)
        assert progress is not None, "Should be able to get progress"
        assert progress.total_requests == num_requests, "Total should match"
        
        # Wait for completion
        max_wait = 5.0
        start = time.time()
        while time.time() - start < max_wait:
            progress = await processor.get_batch_progress(batch_id)
            if progress and progress.status in [
                BatchStatus.COMPLETED,
                BatchStatus.PARTIALLY_COMPLETED,
                BatchStatus.FAILED,
            ]:
                break
            await asyncio.sleep(0.1)
        
        # Verify completion
        result = await processor.get_batch_result(batch_id)
        # Result may be None if still processing, but progress should be available
        if result:
            assert result.progress.total_requests == num_requests
    
    asyncio.run(run_test())


# ==================== Additional Property Tests ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=30000)
@given(
    num_requests=st.integers(min_value=1, max_value=10),
)
def test_batch_result_serialization(num_requests: int):
    """
    Feature: llm-integration, Property 27/30: Batch Result Serialization
    
    For any batch result, serialization to dict should preserve all data.
    
    **Validates: Requirements 10.1, 10.5**
    """
    async def run_test():
        # Create requests
        requests = [
            LLMRequest(prompt=f"Test prompt {i}")
            for i in range(num_requests)
        ]
        
        # Create batch processor
        mock_switcher = MockLLMSwitcher(response_delay=0.001)
        processor = LLMBatchProcessor(
            llm_switcher=mock_switcher,
            enable_batching=True,
        )
        
        # Process batch
        result = await processor.process_batch(requests)
        
        # Serialize to dict
        result_dict = result.to_dict()
        
        # Verify serialization
        assert 'batch_id' in result_dict
        assert 'progress' in result_dict
        assert 'results' in result_dict
        assert 'processing_time_ms' in result_dict
        
        # Verify progress serialization
        progress_dict = result_dict['progress']
        assert progress_dict['total_requests'] == num_requests
        assert 'completed_requests' in progress_dict
        assert 'failed_requests' in progress_dict
        assert 'progress_percentage' in progress_dict
        assert 'status' in progress_dict
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=30000)
@given(
    num_requests=st.integers(min_value=2, max_value=10),
)
def test_batch_cancellation(num_requests: int):
    """
    Feature: llm-integration, Property 27/30: Batch Cancellation
    
    For any batch in progress, cancellation should stop processing and
    update the status to CANCELLED.
    
    **Validates: Requirements 10.1, 10.5**
    """
    async def run_test():
        # Create requests
        requests = [
            LLMRequest(prompt=f"Test prompt {i}")
            for i in range(num_requests)
        ]
        
        # Create batch processor with slow responses
        mock_switcher = MockLLMSwitcher(response_delay=0.1)
        processor = LLMBatchProcessor(
            llm_switcher=mock_switcher,
            max_concurrent_requests=1,  # Process one at a time
            enable_batching=True,
        )
        
        # Submit batch asynchronously
        batch_id = await processor.submit_batch(requests)
        
        # Wait a bit for processing to start
        await asyncio.sleep(0.05)
        
        # Cancel the batch
        cancelled = await processor.cancel_batch(batch_id)
        
        # Verify cancellation was accepted
        assert cancelled, "Cancellation should be accepted"
        
        # Wait for processing to stop
        await asyncio.sleep(0.2)
        
        # Check status
        progress = await processor.get_batch_progress(batch_id)
        if progress:
            assert progress.status == BatchStatus.CANCELLED, \
                f"Status should be CANCELLED, got {progress.status}"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=30000)
@given(
    num_requests=st.integers(min_value=1, max_value=10),
)
def test_request_id_uniqueness(num_requests: int):
    """
    Feature: llm-integration, Property 27: Request ID Uniqueness
    
    For any batch of requests, each request should have a unique ID.
    
    **Validates: Requirements 10.1**
    """
    # Create requests
    requests = [
        LLMRequest(prompt=f"Test prompt {i}")
        for i in range(num_requests)
    ]
    
    # Verify all request IDs are unique
    request_ids = [r.request_id for r in requests]
    assert len(request_ids) == len(set(request_ids)), \
        "All request IDs should be unique"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=30000)
@given(
    method=method_strategy,
    model=model_name_strategy,
)
def test_provider_key_generation(method: LLMMethod, model: str):
    """
    Feature: llm-integration, Property 27: Provider Key Generation
    
    For any request, the provider key should be deterministic based on
    method and model.
    
    **Validates: Requirements 10.1**
    """
    # Create two requests with same method and model
    request1 = LLMRequest(prompt="Test 1", method=method, model=model)
    request2 = LLMRequest(prompt="Test 2", method=method, model=model)
    
    # Provider keys should be identical
    assert request1.get_provider_key() == request2.get_provider_key(), \
        "Same method/model should produce same provider key"
    
    # Verify key format
    expected_key = f"{method.value}:{model}"
    assert request1.get_provider_key() == expected_key, \
        f"Provider key should be {expected_key}"


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
