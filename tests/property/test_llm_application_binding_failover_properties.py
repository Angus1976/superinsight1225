"""
Property-based tests for LLM Application Binding - Failover Behavior.

Uses Hypothesis library for property testing with minimum 100 iterations.
Tests Properties 11, 12, 13 from the LLM Application Binding design document.

Feature: llm-application-binding
Properties: 11 - Retry With Exponential Backoff
            12 - Failover On Exhausted Retries
            13 - Timeout Triggers Failover
"""

import pytest
import asyncio
from uuid import uuid4
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import AsyncMock, MagicMock, patch

# Patch target: backoff uses ``await asyncio.sleep`` inside ApplicationLLMManager
MANAGER_SLEEP = "src.ai.application_llm_manager.asyncio.sleep"

from src.ai.application_llm_manager import ApplicationLLMManager
from src.ai.cache_manager import CacheManager
from src.ai.encryption_service import EncryptionService
from src.ai.llm_schemas import CloudConfig
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding


# ==================== Custom Strategies ====================

# Strategy for application codes
application_code_strategy = st.sampled_from([
    'structuring', 'knowledge_graph', 'ai_assistant',
    'semantic_analysis', 'rag_agent', 'text_to_sql'
])

# Strategy for tenant IDs (UUID strings or None)
tenant_id_strategy = st.one_of(
    st.none(),
    st.uuids().map(str)
)

# Strategy for max_retries (0-10)
max_retries_strategy = st.integers(min_value=0, max_value=10)

# Strategy for timeout_seconds (1-60)
timeout_seconds_strategy = st.integers(min_value=1, max_value=60)

# Strategy for priority values
priority_strategy = st.integers(min_value=1, max_value=99)


# ==================== Fixtures ====================

def _sync_execute_result_scalar(value):
    """Sync Result with ``scalar_one_or_none()`` — matches ``Session.execute`` path in ``_execute``."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _sync_execute_result_bindings(bindings: list):
    """Sync Result with ``scalars().all()``."""
    r = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = bindings
    r.scalars.return_value = scalars
    return r


def _make_db_execute_sequence(app, bindings: list):
    """Fresh sync ``execute`` for each Hypothesis example (side_effect lists are one-shot)."""
    seq = [
        _sync_execute_result_scalar(app),
        _sync_execute_result_bindings(bindings),
        _sync_execute_result_scalar(app),
        _sync_execute_result_bindings(bindings),
    ]

    def execute(stmt):
        if not seq:
            raise AssertionError("unexpected db.execute call; sequence exhausted")
        return seq.pop(0)

    return execute


@pytest.fixture
def mock_db_session():
    """Sync DB mock — ``ApplicationLLMManager._execute`` uses sync ``execute`` unless ``AsyncSession``."""
    session = MagicMock()
    session.execute = MagicMock(return_value=_sync_execute_result_scalar(None))
    return session


@pytest.fixture
def cache_manager():
    """Create a CacheManager instance without Redis."""
    return CacheManager(redis_client=None, local_ttl=300, max_memory_mb=100)


@pytest.fixture
def encryption_service():
    """Create an EncryptionService instance."""
    import os
    # Set a test encryption key (32 bytes base64 encoded)
    test_key = "5QoEylTqwm1/eHusi1j8tWRV3dexqXB50c/AKPyyefE="
    with patch.dict(os.environ, {'LLM_ENCRYPTION_KEY': test_key}):
        return EncryptionService()


@pytest.fixture
def app_llm_manager(mock_db_session, cache_manager, encryption_service):
    """Create an ApplicationLLMManager instance."""
    return ApplicationLLMManager(
        db_session=mock_db_session,
        cache_manager=cache_manager,
        encryption_service=encryption_service
    )


# ==================== Helper Functions ====================

def create_mock_application(code: str) -> LLMApplication:
    """Create a mock LLMApplication."""
    app = MagicMock(spec=LLMApplication)
    app.id = uuid4()
    app.code = code
    app.name = code.replace('_', ' ').title()
    app.is_active = True
    return app


def create_mock_config(
    tenant_id: str = None,
    provider: str = 'openai',
    model_name: str = 'gpt-3.5-turbo',
    api_key: str = 'test_key'
) -> LLMConfiguration:
    """Create a mock LLMConfiguration."""
    config = MagicMock(spec=LLMConfiguration)
    config.id = uuid4()
    config.tenant_id = tenant_id
    config.is_active = True
    config.default_method = provider
    config.config_data = {
        'provider': provider,
        'model_name': model_name,
        'api_key': api_key,
        'base_url': 'https://api.openai.com/v1'
    }
    return config


def create_mock_binding(
    llm_config: LLMConfiguration,
    application: LLMApplication,
    priority: int = 1,
    max_retries: int = 3,
    timeout_seconds: int = 30
) -> LLMApplicationBinding:
    """Create a mock LLMApplicationBinding."""
    binding = MagicMock(spec=LLMApplicationBinding)
    binding.id = uuid4()
    binding.llm_config_id = llm_config.id
    binding.application_id = application.id
    binding.priority = priority
    binding.max_retries = max_retries
    binding.timeout_seconds = timeout_seconds
    binding.is_active = True
    binding.llm_config = llm_config
    binding.application = application
    return binding


async def failing_operation(config: CloudConfig) -> str:
    """Mock operation that always fails."""
    raise RuntimeError("LLM request failed")


async def timeout_operation(config: CloudConfig) -> str:
    """Mock operation that times out."""
    await asyncio.sleep(100)  # Sleep longer than any reasonable timeout
    return "success"


async def successful_operation(config: CloudConfig) -> str:
    """Mock operation that succeeds."""
    return f"success-{config.openai_model}"


# ==================== Property 11: Retry With Exponential Backoff ====================

class TestRetryWithExponentialBackoff:
    """
    Property 11: Retry With Exponential Backoff
    
    For any failed LLM request, the system should retry up to max_retries times 
    with exponential backoff (2^0, 2^1, 2^2, ... seconds).
    
    **Validates: Requirements 5.1**
    
    Requirements:
    - 5.1: WHEN an LLM request fails, THE System SHALL retry up to max_retries 
           times with exponential backoff
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        max_retries=max_retries_strategy,
        timeout_seconds=st.integers(min_value=5, max_value=10)
    )
    @pytest.mark.asyncio
    async def test_property_11_retry_count_matches_max_retries(
        self,
        app_llm_manager,
        max_retries: int,
        timeout_seconds: int
    ):
        """
        Feature: llm-application-binding, Property 11: Retry With Exponential Backoff
        
        When an operation fails, it should be retried exactly max_retries times
        (total attempts = max_retries + 1).
        
        **Validates: Requirements 5.1**
        """
        # Create mock config
        config = CloudConfig(
            openai_api_key="test_key",
            openai_base_url="https://api.openai.com/v1",
            openai_model="gpt-3.5-turbo"
        )
        
        # Track number of attempts
        attempt_count = 0
        
        async def counting_failing_operation(cfg: CloudConfig) -> str:
            nonlocal attempt_count
            attempt_count += 1
            raise RuntimeError("LLM request failed")
        
        # Without patching sleep, max_retries=10 implies ~1023s of real backoff per example.
        with patch(MANAGER_SLEEP, new_callable=AsyncMock):
            with pytest.raises(RuntimeError):
                await app_llm_manager._execute_with_retry(
                    config,
                    counting_failing_operation,
                    max_retries,
                    timeout_seconds
                )
        
        # Verify total attempts = max_retries + 1 (initial + retries)
        expected_attempts = max_retries + 1
        assert attempt_count == expected_attempts, \
            f"Should attempt {expected_attempts} times (1 initial + {max_retries} retries), got {attempt_count}"

    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        max_retries=st.integers(min_value=1, max_value=5),  # Limit for timing test
        timeout_seconds=st.integers(min_value=5, max_value=10)
    )
    @pytest.mark.asyncio
    async def test_property_11_exponential_backoff_timing(
        self,
        app_llm_manager,
        max_retries: int,
        timeout_seconds: int
    ):
        """
        Feature: llm-application-binding, Property 11: Retry With Exponential Backoff
        
        Retry delays should follow exponential backoff pattern: 2^0, 2^1, 2^2, ...
        
        **Validates: Requirements 5.1**
        """
        config = CloudConfig(
            openai_api_key="test_key",
            openai_base_url="https://api.openai.com/v1",
            openai_model="gpt-3.5-turbo"
        )
        
        sleep_durations: list = []
        
        async def timing_failing_operation(cfg: CloudConfig) -> str:
            raise RuntimeError("LLM request failed")
        
        async def record_sleep(delay: float) -> None:
            sleep_durations.append(delay)
        
        with patch(MANAGER_SLEEP, side_effect=record_sleep):
            with pytest.raises(RuntimeError):
                await app_llm_manager._execute_with_retry(
                    config,
                    timing_failing_operation,
                    max_retries,
                    timeout_seconds
                )
        
        assert len(sleep_durations) == max_retries
        for i, d in enumerate(sleep_durations):
            expected = 2 ** i
            assert d == expected, f"Backoff {i} should sleep {expected}s, got {d}"
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        max_retries=st.integers(min_value=1, max_value=3),
        timeout_seconds=st.integers(min_value=5, max_value=10)
    )
    @pytest.mark.asyncio
    async def test_property_11_success_stops_retry(
        self,
        app_llm_manager,
        max_retries: int,
        timeout_seconds: int
    ):
        """
        Feature: llm-application-binding, Property 11: Retry With Exponential Backoff
        
        When operation succeeds, no further retries should occur.
        
        **Validates: Requirements 5.1**
        """
        config = CloudConfig(
            openai_api_key="test_key",
            openai_base_url="https://api.openai.com/v1",
            openai_model="gpt-3.5-turbo"
        )
        
        attempt_count = 0
        
        async def eventually_successful_operation(cfg: CloudConfig) -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise RuntimeError("First attempt fails")
            return "success"
        
        with patch(MANAGER_SLEEP, new_callable=AsyncMock):
            result = await app_llm_manager._execute_with_retry(
                config,
                eventually_successful_operation,
                max_retries,
                timeout_seconds
            )
        
        # Verify success and no extra retries
        assert result == "success", "Should return success"
        assert attempt_count == 2, \
            "Should stop after first success (2 attempts total)"



# ==================== Property 12: Failover On Exhausted Retries ====================

class TestFailoverOnExhaustedRetries:
    """
    Property 12: Failover On Exhausted Retries
    
    For any LLM configuration that fails all retry attempts, if additional LLM 
    configurations exist with higher priority values, the system should attempt 
    the next configuration in priority order.
    
    **Validates: Requirements 5.2**
    
    Requirements:
    - 5.2: WHEN all retries for an LLM fail, THE System SHALL attempt the next 
           LLM in priority order
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy,
        num_configs=st.integers(min_value=2, max_value=5),
        success_index=st.integers(min_value=0, max_value=4)
    )
    @pytest.mark.asyncio
    async def test_property_12_failover_to_next_llm(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str,
        num_configs: int,
        success_index: int
    ):
        """
        Feature: llm-application-binding, Property 12: Failover On Exhausted Retries
        
        When primary LLM fails all retries, system should try next LLM in priority order.
        
        **Validates: Requirements 5.2**
        """
        # Ensure success_index is within range
        assume(success_index < num_configs)
        
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create multiple LLM configs with different priorities
        configs = []
        bindings = []
        for i in range(num_configs):
            config = create_mock_config(
                tenant_id=tenant_id,
                model_name=f"model-{i}"
            )
            binding = create_mock_binding(
                config, app,
                priority=i+1,
                max_retries=0,  # One attempt per config before failover (matches assertion below)
                timeout_seconds=5
            )
            configs.append(config)
            bindings.append(binding)
        
        app_llm_manager.db.execute = MagicMock(side_effect=_make_db_execute_sequence(app, bindings))
        
        # Hypothesis reuses the same manager; avoid stale get_llm_config cache across examples.
        await app_llm_manager.invalidate_cache(application_code)
        
        # Track which configs were attempted
        attempted_configs = []
        
        async def selective_success_operation(cfg: CloudConfig) -> str:
            attempted_configs.append(cfg.openai_model)
            if cfg.openai_model == f"model-{success_index}":
                return f"success-{cfg.openai_model}"
            raise RuntimeError(f"LLM {cfg.openai_model} failed")
        
        # Execute with failover
        result = await app_llm_manager.execute_with_failover(
            application_code,
            selective_success_operation,
            tenant_id
        )
        
        # Verify failover behavior
        assert result == f"success-model-{success_index}", \
            f"Should succeed with model-{success_index}"
        
        # Verify all configs up to and including success_index were attempted
        expected_attempts = success_index + 1
        assert len(attempted_configs) == expected_attempts, \
            f"Should attempt {expected_attempts} configs, attempted {len(attempted_configs)}"
        
        # Verify configs were attempted in priority order
        for i in range(expected_attempts):
            assert attempted_configs[i] == f"model-{i}", \
                f"Config {i} should be model-{i}, got {attempted_configs[i]}"

    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy,
        num_configs=st.integers(min_value=2, max_value=4)
    )
    @pytest.mark.asyncio
    async def test_property_12_all_llms_fail_raises_error(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str,
        num_configs: int
    ):
        """
        Feature: llm-application-binding, Property 12: Failover On Exhausted Retries
        
        When all LLMs fail, system should raise error with details.
        
        **Validates: Requirements 5.2**
        """
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create multiple LLM configs
        configs = []
        bindings = []
        for i in range(num_configs):
            config = create_mock_config(
                tenant_id=tenant_id,
                model_name=f"model-{i}"
            )
            binding = create_mock_binding(
                config, app,
                priority=i+1,
                max_retries=0,
                timeout_seconds=5
            )
            configs.append(config)
            bindings.append(binding)
        
        app_llm_manager.db.execute = MagicMock(side_effect=_make_db_execute_sequence(app, bindings))
        
        await app_llm_manager.invalidate_cache(application_code)
        
        # Track attempts
        attempted_configs = []
        
        async def always_failing_operation(cfg: CloudConfig) -> str:
            attempted_configs.append(cfg.openai_model)
            raise RuntimeError(f"LLM {cfg.openai_model} failed")
        
        # Execute with failover - should raise error
        with pytest.raises(RuntimeError) as exc_info:
            await app_llm_manager.execute_with_failover(
                application_code,
                always_failing_operation,
                tenant_id
            )
        
        # Verify all configs were attempted
        assert len(attempted_configs) == num_configs, \
            f"Should attempt all {num_configs} configs"
        
        # Verify error message mentions the application
        assert application_code in str(exc_info.value), \
            "Error should mention application code"
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy,
        priorities=st.lists(priority_strategy, min_size=2, max_size=4, unique=True)
    )
    @pytest.mark.asyncio
    async def test_property_12_respects_priority_order(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str,
        priorities: list
    ):
        """
        Feature: llm-application-binding, Property 12: Failover On Exhausted Retries
        
        Failover should respect priority order (ascending).
        
        **Validates: Requirements 5.2**
        """
        # Sort priorities
        priorities = sorted(priorities)
        
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create configs with specific priorities
        bindings = []
        for priority in priorities:
            config = create_mock_config(
                tenant_id=tenant_id,
                model_name=f"priority-{priority}"
            )
            binding = create_mock_binding(
                config, app,
                priority=priority,
                max_retries=0,
                timeout_seconds=5
            )
            bindings.append(binding)
        
        app_llm_manager.db.execute = MagicMock(side_effect=_make_db_execute_sequence(app, bindings))
        
        await app_llm_manager.invalidate_cache(application_code)
        
        # Track attempt order
        attempt_order = []
        
        async def tracking_operation(cfg: CloudConfig) -> str:
            attempt_order.append(cfg.openai_model)
            # Last one succeeds
            if cfg.openai_model == f"priority-{priorities[-1]}":
                return "success"
            raise RuntimeError("Failed")
        
        # Execute with failover
        await app_llm_manager.execute_with_failover(
            application_code,
            tracking_operation,
            tenant_id
        )
        
        # Verify priority order was respected
        for i, priority in enumerate(priorities):
            assert attempt_order[i] == f"priority-{priority}", \
                f"Attempt {i} should be priority-{priority}, got {attempt_order[i]}"



# ==================== Property 13: Timeout Triggers Failover ====================

class TestTimeoutTriggersFailover:
    """
    Property 13: Timeout Triggers Failover
    
    For any LLM request that exceeds the configured timeout_seconds, the system 
    should treat it as a failure and trigger the retry/failover logic.
    
    **Validates: Requirements 5.3**
    
    Requirements:
    - 5.3: WHEN an LLM request exceeds timeout_seconds, THE System SHALL treat 
           it as a failure and trigger failover
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        timeout_seconds=st.integers(min_value=1, max_value=3),  # Short timeout for testing
        max_retries=st.integers(min_value=0, max_value=2)
    )
    @pytest.mark.asyncio
    async def test_property_13_timeout_triggers_retry(
        self,
        app_llm_manager,
        timeout_seconds: int,
        max_retries: int
    ):
        """
        Feature: llm-application-binding, Property 13: Timeout Triggers Failover
        
        When operation times out, it should trigger retry logic.
        
        **Validates: Requirements 5.3**
        """
        config = CloudConfig(
            openai_api_key="test_key",
            openai_base_url="https://api.openai.com/v1",
            openai_model="gpt-3.5-turbo"
        )
        
        attempt_count = 0
        
        async def timeout_operation(cfg: CloudConfig) -> str:
            nonlocal attempt_count
            attempt_count += 1
            # Sleep longer than timeout
            await asyncio.sleep(timeout_seconds + 2)
            return "success"
        
        # Execute with retry - should timeout
        with pytest.raises(asyncio.TimeoutError):
            await app_llm_manager._execute_with_retry(
                config,
                timeout_operation,
                max_retries,
                timeout_seconds
            )
        
        # Verify retries occurred
        expected_attempts = max_retries + 1
        assert attempt_count == expected_attempts, \
            f"Should attempt {expected_attempts} times after timeout"
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy,
        timeout_seconds=st.integers(min_value=1, max_value=2)
    )
    @pytest.mark.asyncio
    async def test_property_13_timeout_triggers_failover_to_next_llm(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str,
        timeout_seconds: int
    ):
        """
        Feature: llm-application-binding, Property 13: Timeout Triggers Failover
        
        When primary LLM times out, system should failover to next LLM.
        
        **Validates: Requirements 5.3**
        """
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create two LLM configs
        config1 = create_mock_config(tenant_id=tenant_id, model_name="slow-model")
        config2 = create_mock_config(tenant_id=tenant_id, model_name="fast-model")
        
        binding1 = create_mock_binding(config1, app, priority=1, max_retries=0, timeout_seconds=timeout_seconds)
        binding2 = create_mock_binding(config2, app, priority=2, max_retries=0, timeout_seconds=timeout_seconds)
        
        app_llm_manager.db.execute = MagicMock(
            side_effect=_make_db_execute_sequence(app, [binding1, binding2])
        )
        
        await app_llm_manager.invalidate_cache(application_code)
        
        # Track attempts
        attempted_models = []
        
        async def selective_timeout_operation(cfg: CloudConfig) -> str:
            attempted_models.append(cfg.openai_model)
            if cfg.openai_model == "slow-model":
                # Timeout
                await asyncio.sleep(timeout_seconds + 2)
                return "should-not-reach"
            else:
                # Fast success
                return f"success-{cfg.openai_model}"
        
        # Execute with failover
        result = await app_llm_manager.execute_with_failover(
            application_code,
            selective_timeout_operation,
            tenant_id
        )
        
        # Verify failover occurred
        assert result == "success-fast-model", \
            "Should succeed with fast-model after slow-model timeout"
        assert len(attempted_models) == 2, \
            "Should attempt both models"
        assert attempted_models[0] == "slow-model", \
            "Should try slow-model first"
        assert attempted_models[1] == "fast-model", \
            "Should failover to fast-model"

    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        timeout_seconds=st.integers(min_value=1, max_value=3),
        operation_duration=st.integers(min_value=0, max_value=5)
    )
    @pytest.mark.asyncio
    async def test_property_13_timeout_boundary_behavior(
        self,
        app_llm_manager,
        timeout_seconds: int,
        operation_duration: int
    ):
        """
        Feature: llm-application-binding, Property 13: Timeout Triggers Failover
        
        Operations completing within timeout should succeed, those exceeding should fail.
        
        **Validates: Requirements 5.3**
        """
        config = CloudConfig(
            openai_api_key="test_key",
            openai_base_url="https://api.openai.com/v1",
            openai_model="gpt-3.5-turbo"
        )
        
        async def timed_operation(cfg: CloudConfig) -> str:
            await asyncio.sleep(operation_duration)
            return "success"
        
        if operation_duration < timeout_seconds:
            # Should succeed
            result = await app_llm_manager._execute_with_retry(
                config,
                timed_operation,
                max_retries=0,
                timeout_seconds=timeout_seconds
            )
            assert result == "success", \
                f"Operation taking {operation_duration}s should succeed with {timeout_seconds}s timeout"
        else:
            # Should timeout
            with pytest.raises(asyncio.TimeoutError):
                await app_llm_manager._execute_with_retry(
                    config,
                    timed_operation,
                    max_retries=0,
                    timeout_seconds=timeout_seconds
                )
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy,
        num_configs=st.integers(min_value=2, max_value=3),
        timeout_seconds=st.integers(min_value=1, max_value=2)
    )
    @pytest.mark.asyncio
    async def test_property_13_all_llms_timeout_raises_error(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str,
        num_configs: int,
        timeout_seconds: int
    ):
        """
        Feature: llm-application-binding, Property 13: Timeout Triggers Failover
        
        When all LLMs timeout, system should raise error.
        
        **Validates: Requirements 5.3**
        """
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create multiple LLM configs
        bindings = []
        for i in range(num_configs):
            config = create_mock_config(tenant_id=tenant_id, model_name=f"model-{i}")
            binding = create_mock_binding(
                config, app,
                priority=i+1,
                max_retries=0,
                timeout_seconds=timeout_seconds
            )
            bindings.append(binding)
        
        app_llm_manager.db.execute = MagicMock(side_effect=_make_db_execute_sequence(app, bindings))
        
        await app_llm_manager.invalidate_cache(application_code)
        
        # Track attempts
        attempted_models = []
        
        async def always_timeout_operation(cfg: CloudConfig) -> str:
            attempted_models.append(cfg.openai_model)
            await asyncio.sleep(timeout_seconds + 2)
            return "should-not-reach"
        
        # Execute with failover - should raise error
        with pytest.raises(RuntimeError) as exc_info:
            await app_llm_manager.execute_with_failover(
                application_code,
                always_timeout_operation,
                tenant_id
            )
        
        # Verify all configs were attempted
        assert len(attempted_models) == num_configs, \
            f"Should attempt all {num_configs} configs before giving up"
        
        # Verify error mentions the application
        assert application_code in str(exc_info.value), \
            "Error should mention application code"


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
