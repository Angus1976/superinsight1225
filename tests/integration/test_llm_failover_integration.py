"""
Integration test for LLM Application Binding complete failover flow.

This module tests the complete failover flow with multiple LLM bindings:
- Primary LLM failure triggers failover to secondary
- Retry logic with exponential backoff
- Timeout handling
- Failover logging
- All LLMs fail scenario

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from sqlalchemy import delete, select

from src.ai.llm_schemas import CloudConfig
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding
from src.ai.application_llm_manager import ApplicationLLMManager
from src.ai.cache_manager import CacheManager
from src.ai.encryption_service import get_encryption_service


@pytest.fixture
def setup_three_llm_bindings(db_session):
    """
    Create test setup with 3 LLM bindings for failover testing.
    
    Sets up:
    - LLMApplication for "test_app"
    - 3 LLMConfigurations (primary, secondary, tertiary)
    - 3 LLMApplicationBindings with priorities 1, 2, 3
    """
    encryption = get_encryption_service()

    existing_id = db_session.execute(
        select(LLMApplication.id).where(LLMApplication.code == "test_app")
    ).scalar_one_or_none()
    if existing_id:
        db_session.execute(
            delete(LLMApplicationBinding).where(
                LLMApplicationBinding.application_id == existing_id
            )
        )
        db_session.execute(delete(LLMApplication).where(LLMApplication.id == existing_id))
        db_session.flush()
    
    # Create application
    app = LLMApplication(
        id=uuid4(),
        code="test_app",
        name="Test Application",
        description="Test application for failover",
        llm_usage_pattern="Test pattern",
        is_active=True
    )
    db_session.add(app)
    db_session.flush()
    
    # Create 3 LLM configurations
    configs = []
    for i, name in enumerate(["Primary", "Secondary", "Tertiary"], 1):
        api_key_encrypted = encryption.encrypt(f"test-key-{i}")
        config = LLMConfiguration(
            id=uuid4(),
            name=f"{name} LLM",
            provider="openai",
            default_method="openai",
            is_active=True,
            tenant_id=None,
            created_by=None,
            updated_by=None,
            config_data={
                "provider": "openai",
                "api_key_encrypted": api_key_encrypted,
                "base_url": f"https://api.{name.lower()}.example.com/v1",
                "model_name": f"gpt-4-{name.lower()}"
            }
        )
        db_session.add(config)
        db_session.flush()
        configs.append(config)
    
    # Create bindings with different priorities and retry settings
    bindings = []
    for i, config in enumerate(configs, 1):
        binding = LLMApplicationBinding(
            id=uuid4(),
            llm_config_id=config.id,
            application_id=app.id,
            priority=i,
            max_retries=2,  # 2 retries per LLM
            timeout_seconds=5,  # 5 second timeout
            is_active=True
        )
        db_session.add(binding)
        bindings.append(binding)
    
    db_session.flush()
    
    return {
        "application": app,
        "configs": configs,
        "bindings": bindings
    }


@pytest.mark.asyncio
class TestCompleteFailoverFlow:
    """Test complete failover flow with multiple LLM bindings."""
    
    async def test_primary_failure_triggers_secondary(
        self, db_session, setup_three_llm_bindings, caplog
    ):
        """
        Test that primary LLM failure triggers failover to secondary.
        
        Validates: Requirements 5.2, 5.5
        """
        # Create manager
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        encryption = get_encryption_service()
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Mock operation that fails on primary, succeeds on secondary
        call_count = 0
        
        async def mock_operation(config: CloudConfig):
            nonlocal call_count
            call_count += 1
            
            if "primary" in config.openai_base_url:
                raise Exception("Primary LLM failed")
            elif "secondary" in config.openai_base_url:
                return "Success from secondary"
            else:
                raise Exception("Tertiary should not be called")
        
        # Execute with failover
        result = await manager.execute_with_failover(
            application_code="test_app",
            operation=mock_operation,
            tenant_id=None
        )
        
        # Verify secondary was used
        assert result == "Success from secondary"
        assert call_count >= 2  # Primary failed, secondary succeeded
        
        # Verify failover was logged
        assert any("failover" in record.message.lower() for record in caplog.records)
    
    async def test_retry_with_exponential_backoff(
        self, db_session, setup_three_llm_bindings
    ):
        """
        Test that retry logic uses exponential backoff.
        
        Validates: Requirements 5.1
        """
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        encryption = get_encryption_service()
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Track retry timings
        retry_times = []
        
        async def mock_operation(config: CloudConfig):
            retry_times.append(time.time())
            if len(retry_times) < 3:  # Fail first 2 attempts
                raise Exception("Temporary failure")
            return "Success after retries"
        
        # Execute with failover
        start_time = time.time()
        result = await manager.execute_with_failover(
            application_code="test_app",
            operation=mock_operation,
            tenant_id=None
        )
        
        # Verify success after retries
        assert result == "Success after retries"
        assert len(retry_times) == 3
        
        # Verify exponential backoff: sleep(2**attempt) after each failure
        # (attempt 0 -> sleep 1s before retry 1; attempt 1 -> sleep 2s before retry 2)
        if len(retry_times) >= 3:
            delay1 = retry_times[1] - retry_times[0]
            delay2 = retry_times[2] - retry_times[1]
            
            assert 0.8 <= delay1 <= 1.4
            assert 1.5 <= delay2 <= 3.0
    
    async def test_timeout_triggers_failover(
        self, db_session, setup_three_llm_bindings, caplog
    ):
        """
        Test that timeout triggers failover to next LLM.
        
        Validates: Requirements 5.3
        """
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        encryption = get_encryption_service()
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Mock operation that times out on primary
        async def mock_operation(config: CloudConfig):
            if "primary" in config.openai_base_url:
                await asyncio.sleep(10)  # Exceeds 5s timeout
                return "Should not reach here"
            elif "secondary" in config.openai_base_url:
                return "Success from secondary after timeout"
            else:
                raise Exception("Tertiary should not be called")
        
        # Execute with failover
        result = await manager.execute_with_failover(
            application_code="test_app",
            operation=mock_operation,
            tenant_id=None
        )
        
        # Verify secondary was used after timeout
        assert result == "Success from secondary after timeout"
        
        # Verify timeout was logged
        assert any("timeout" in record.message.lower() for record in caplog.records)
    
    async def test_all_llms_fail_raises_exception(
        self, db_session, setup_three_llm_bindings
    ):
        """
        Test that exception is raised when all LLMs fail.
        
        Validates: Requirements 5.4
        """
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        encryption = get_encryption_service()
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Mock operation that always fails
        async def mock_operation(config: CloudConfig):
            raise Exception(f"LLM failed: {config.openai_base_url}")
        
        # Execute with failover - should raise exception
        with pytest.raises(Exception) as exc_info:
            await manager.execute_with_failover(
                application_code="test_app",
                operation=mock_operation,
                tenant_id=None
            )
        
        # Verify exception contains details
        assert "failed" in str(exc_info.value).lower()
    
    async def test_failover_logging_details(
        self, db_session, setup_three_llm_bindings, caplog
    ):
        """
        Test that failover events are logged with complete details.
        
        Validates: Requirements 5.5
        """
        import logging
        caplog.set_level(logging.INFO)
        
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        encryption = get_encryption_service()
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Mock operation that fails on primary
        async def mock_operation(config: CloudConfig):
            if "primary" in config.openai_base_url:
                raise Exception("Primary connection refused")
            return "Success from secondary"
        
        # Execute with failover
        await manager.execute_with_failover(
            application_code="test_app",
            operation=mock_operation,
            tenant_id=None
        )
        
        # Verify log contains required details
        log_messages = [record.message for record in caplog.records]
        
        # Should log application code
        assert any("test_app" in msg for msg in log_messages)
        
        # Should log failed LLM
        assert any("primary" in msg.lower() for msg in log_messages)
        
        # Should log failure reason
        assert any("connection refused" in msg.lower() for msg in log_messages)
    
    async def test_failover_with_mixed_errors(
        self, db_session, setup_three_llm_bindings
    ):
        """
        Test failover with different types of errors (timeout, exception).
        
        Validates: Requirements 5.1, 5.2, 5.3
        """
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        encryption = get_encryption_service()
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Mock operation with different failure types
        async def mock_operation(config: CloudConfig):
            if "primary" in config.openai_base_url:
                await asyncio.sleep(10)  # Timeout
            elif "secondary" in config.openai_base_url:
                raise Exception("Secondary connection error")
            else:  # Tertiary
                return "Success from tertiary"
        
        # Execute with failover
        result = await manager.execute_with_failover(
            application_code="test_app",
            operation=mock_operation,
            tenant_id=None
        )
        
        # Verify tertiary was used after primary timeout and secondary failure
        assert result == "Success from tertiary"
    
    async def test_partial_retry_success(
        self, db_session, setup_three_llm_bindings
    ):
        """
        Test that operation succeeds on retry without moving to next LLM.
        
        Validates: Requirements 5.1
        """
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        encryption = get_encryption_service()
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Track attempts
        attempt_count = 0
        
        async def mock_operation(config: CloudConfig):
            nonlocal attempt_count
            attempt_count += 1
            
            # Fail first attempt, succeed on retry
            if attempt_count == 1:
                raise Exception("Temporary network glitch")
            return f"Success from {config.openai_base_url}"
        
        # Execute with failover
        result = await manager.execute_with_failover(
            application_code="test_app",
            operation=mock_operation,
            tenant_id=None
        )
        
        # Verify success on retry with same LLM
        assert "primary" in result.lower()
        assert attempt_count == 2  # Failed once, succeeded on retry


@pytest.mark.asyncio
class TestFailoverPerformance:
    """Test failover performance characteristics."""
    
    async def test_failover_completes_within_reasonable_time(
        self, db_session, setup_three_llm_bindings
    ):
        """
        Test that failover completes within expected time bounds.
        
        With 2 retries per LLM and 5s timeout:
        - Max time per LLM: 5s timeout + 2s + 4s backoff = ~11s
        - Max total time for 3 LLMs: ~33s
        """
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        encryption = get_encryption_service()
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Mock operation that succeeds on secondary
        async def mock_operation(config: CloudConfig):
            if "primary" in config.openai_base_url:
                raise Exception("Primary failed")
            return "Success"
        
        # Measure execution time
        start_time = time.time()
        result = await manager.execute_with_failover(
            application_code="test_app",
            operation=mock_operation,
            tenant_id=None
        )
        elapsed_time = time.time() - start_time
        
        # Verify success
        assert result == "Success"
        
        # Verify reasonable time (should be < 15s for primary fail + secondary success)
        assert elapsed_time < 15.0
    
    async def test_immediate_success_is_fast(
        self, db_session, setup_three_llm_bindings
    ):
        """
        Test that immediate success on primary LLM is fast.
        """
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        encryption = get_encryption_service()
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Mock operation that succeeds immediately
        async def mock_operation(config: CloudConfig):
            return "Immediate success"
        
        # Measure execution time
        start_time = time.time()
        result = await manager.execute_with_failover(
            application_code="test_app",
            operation=mock_operation,
            tenant_id=None
        )
        elapsed_time = time.time() - start_time
        
        # Verify success
        assert result == "Immediate success"
        
        # Verify fast execution (< 1s)
        assert elapsed_time < 1.0


@pytest.mark.asyncio
class TestFailoverEdgeCases:
    """Test edge cases in failover logic."""
    
    async def test_single_llm_binding_retries_only(
        self, db_session
    ):
        """
        Test that with only one LLM binding, retries are attempted
        but no failover occurs.
        """
        encryption = get_encryption_service()
        
        # Create application with single binding
        app = LLMApplication(
            id=uuid4(),
            code="single_llm_app",
            name="Single LLM App",
            is_active=True
        )
        db_session.add(app)
        db_session.flush()
        
        api_key_encrypted = encryption.encrypt("single-key")
        config = LLMConfiguration(
            id=uuid4(),
            name="Single LLM",
            provider="openai",
            default_method="openai",
            is_active=True,
            tenant_id=None,
            created_by=None,
            updated_by=None,
            config_data={
                "provider": "openai",
                "api_key_encrypted": api_key_encrypted,
                "base_url": "https://api.single.example.com/v1",
                "model_name": "gpt-4"
            }
        )
        db_session.add(config)
        db_session.flush()
        
        binding = LLMApplicationBinding(
            id=uuid4(),
            llm_config_id=config.id,
            application_id=app.id,
            priority=1,
            max_retries=2,
            timeout_seconds=5,
            is_active=True
        )
        db_session.add(binding)
        db_session.commit()
        
        # Create manager
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Track attempts
        attempt_count = 0
        
        async def mock_operation(config: CloudConfig):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary failure")
            return "Success after retries"
        
        # Execute
        result = await manager.execute_with_failover(
            application_code="single_llm_app",
            operation=mock_operation,
            tenant_id=None
        )
        
        # Verify retries occurred
        assert result == "Success after retries"
        assert attempt_count == 3  # Initial + 2 retries
    
    async def test_inactive_bindings_are_skipped(
        self, db_session, setup_three_llm_bindings
    ):
        """
        Test that inactive bindings are not used in failover.
        """
        # Deactivate secondary binding
        bindings = setup_three_llm_bindings["bindings"]
        bindings[1].is_active = False
        db_session.commit()
        
        # Create manager
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        encryption = get_encryption_service()
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Mock operation that fails on primary
        async def mock_operation(config: CloudConfig):
            if "primary" in config.openai_base_url:
                raise Exception("Primary failed")
            elif "secondary" in config.openai_base_url:
                raise Exception("Secondary should be skipped")
            else:  # Tertiary
                return "Success from tertiary"
        
        # Execute with failover
        result = await manager.execute_with_failover(
            application_code="test_app",
            operation=mock_operation,
            tenant_id=None
        )
        
        # Verify tertiary was used (secondary was skipped)
        assert result == "Success from tertiary"
