"""
Unit tests for Label Studio retry decorator module.

Tests the retry functionality including exponential backoff, error handling,
and logging for Label Studio API calls.

Validates: Requirements 1.4 - IF sync fails, THEN system retries with exponential backoff
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx

from src.label_studio.retry import (
    LabelStudioRetryConfig,
    LabelStudioRetryExecutor,
    label_studio_retry,
    label_studio_retry_with_circuit_breaker,
    create_label_studio_retry_executor,
    LABEL_STUDIO_RETRYABLE_EXCEPTIONS,
    LABEL_STUDIO_NON_RETRYABLE_EXCEPTIONS,
)
from src.utils.retry import RetryStrategy, CircuitBreakerError


class TestLabelStudioRetryConfig:
    """Tests for LabelStudioRetryConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = LabelStudioRetryConfig()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.strategy == RetryStrategy.EXPONENTIAL
        assert config.backoff_multiplier == 2.0
        assert config.jitter is True
        assert config.jitter_range == 0.1
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = LabelStudioRetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=60.0,
            backoff_multiplier=3.0,
            jitter=False,
        )
        
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 3.0
        assert config.jitter is False
    
    def test_retryable_exceptions_default(self):
        """Test default retryable exceptions include network errors."""
        config = LabelStudioRetryConfig()
        
        # Should include common network/timeout exceptions
        assert httpx.TimeoutException in config.retryable_exceptions
        assert httpx.ConnectError in config.retryable_exceptions
        assert ConnectionError in config.retryable_exceptions
        assert TimeoutError in config.retryable_exceptions
    
    def test_non_retryable_exceptions_default(self):
        """Test default non-retryable exceptions."""
        config = LabelStudioRetryConfig()
        
        # Should include programming errors that shouldn't be retried
        assert ValueError in config.non_retryable_exceptions
        assert TypeError in config.non_retryable_exceptions


class TestLabelStudioRetryExecutor:
    """Tests for LabelStudioRetryExecutor class."""
    
    def test_successful_execution_no_retry(self):
        """Test successful execution without retry."""
        executor = LabelStudioRetryExecutor()
        
        mock_func = Mock(return_value="success")
        result = executor.execute(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_retry_on_timeout_exception(self):
        """Test retry on timeout exception."""
        config = LabelStudioRetryConfig(
            max_attempts=3,
            base_delay=0.01,  # Short delay for testing
            jitter=False,
        )
        executor = LabelStudioRetryExecutor(config)
        
        # Fail twice, then succeed
        mock_func = Mock(side_effect=[
            httpx.TimeoutException("timeout"),
            httpx.TimeoutException("timeout"),
            "success"
        ])
        
        result = executor.execute(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_retry_on_connection_error(self):
        """Test retry on connection error."""
        config = LabelStudioRetryConfig(
            max_attempts=3,
            base_delay=0.01,
            jitter=False,
        )
        executor = LabelStudioRetryExecutor(config)
        
        # Fail once, then succeed
        mock_func = Mock(side_effect=[
            ConnectionError("connection refused"),
            "success"
        ])
        
        result = executor.execute(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_no_retry_on_value_error(self):
        """Test no retry on ValueError (non-retryable)."""
        config = LabelStudioRetryConfig(
            max_attempts=3,
            base_delay=0.01,
        )
        executor = LabelStudioRetryExecutor(config)
        
        mock_func = Mock(side_effect=ValueError("invalid value"))
        
        with pytest.raises(ValueError):
            executor.execute(mock_func)
        
        # Should only be called once (no retry)
        assert mock_func.call_count == 1
    
    def test_max_attempts_exceeded(self):
        """Test that exception is raised after max attempts."""
        config = LabelStudioRetryConfig(
            max_attempts=3,
            base_delay=0.01,
            jitter=False,
        )
        executor = LabelStudioRetryExecutor(config)
        
        # Always fail with retryable exception
        mock_func = Mock(side_effect=httpx.TimeoutException("timeout"))
        
        with pytest.raises(httpx.TimeoutException):
            executor.execute(mock_func)
        
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_async_successful_execution(self):
        """Test async successful execution without retry."""
        executor = LabelStudioRetryExecutor()
        
        async def async_func():
            return "async success"
        
        result = await executor.async_execute(async_func)
        
        assert result == "async success"
    
    @pytest.mark.asyncio
    async def test_async_retry_on_timeout(self):
        """Test async retry on timeout exception."""
        config = LabelStudioRetryConfig(
            max_attempts=3,
            base_delay=0.01,
            jitter=False,
        )
        executor = LabelStudioRetryExecutor(config)
        
        call_count = 0
        
        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("timeout")
            return "success"
        
        result = await executor.async_execute(async_func)
        
        assert result == "success"
        assert call_count == 3
    
    def test_exponential_backoff_delays(self):
        """Test that delays follow exponential backoff pattern."""
        config = LabelStudioRetryConfig(
            max_attempts=4,
            base_delay=1.0,
            backoff_multiplier=2.0,
            jitter=False,
        )
        executor = LabelStudioRetryExecutor(config)
        
        # Calculate expected delays
        delay_0 = executor._calculate_delay(0)  # 1.0
        delay_1 = executor._calculate_delay(1)  # 2.0
        delay_2 = executor._calculate_delay(2)  # 4.0
        delay_3 = executor._calculate_delay(3)  # 8.0
        
        assert delay_0 == 1.0
        assert delay_1 == 2.0
        assert delay_2 == 4.0
        assert delay_3 == 8.0
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        config = LabelStudioRetryConfig(
            max_attempts=10,
            base_delay=1.0,
            max_delay=10.0,
            backoff_multiplier=2.0,
            jitter=False,
        )
        executor = LabelStudioRetryExecutor(config)
        
        # After several attempts, delay should be capped
        delay = executor._calculate_delay(5)  # Would be 32.0 without cap
        
        assert delay == 10.0


class TestLabelStudioRetryDecorator:
    """Tests for label_studio_retry decorator."""
    
    def test_decorator_sync_function(self):
        """Test decorator on synchronous function."""
        call_count = 0
        
        @label_studio_retry(max_attempts=3, base_delay=0.01, jitter=False)
        def sync_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("timeout")
            return "success"
        
        result = sync_func()
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_decorator_async_function(self):
        """Test decorator on async function."""
        call_count = 0
        
        @label_studio_retry(max_attempts=3, base_delay=0.01, jitter=False)
        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("connection failed")
            return "async success"
        
        result = await async_func()
        
        assert result == "async success"
        assert call_count == 2
    
    def test_decorator_preserves_function_name(self):
        """Test that decorator preserves function metadata."""
        @label_studio_retry()
        def my_function():
            """My docstring."""
            pass
        
        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."
    
    def test_decorator_with_custom_operation_name(self):
        """Test decorator with custom operation name for logging."""
        @label_studio_retry(
            max_attempts=2,
            base_delay=0.01,
            operation_name="create_project"
        )
        def create_project():
            return "project created"
        
        result = create_project()
        assert result == "project created"
    
    def test_decorator_with_arguments(self):
        """Test decorator on function with arguments."""
        @label_studio_retry(max_attempts=2, base_delay=0.01)
        def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"
        
        result = func_with_args("x", "y", c="z")
        assert result == "x-y-z"


class TestLabelStudioRetryWithCircuitBreaker:
    """Tests for label_studio_retry_with_circuit_breaker decorator."""
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after threshold failures."""
        call_count = 0
        
        @label_studio_retry_with_circuit_breaker(
            circuit_name="test_circuit_1",
            max_attempts=1,  # No retry, just circuit breaker
            failure_threshold=2,
            recovery_timeout=60.0,
        )
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("timeout")
        
        # First two calls should fail and increment failure count
        with pytest.raises(httpx.TimeoutException):
            failing_func()
        
        with pytest.raises(httpx.TimeoutException):
            failing_func()
        
        # Third call should be blocked by circuit breaker
        with pytest.raises(CircuitBreakerError):
            failing_func()
        
        # Only 2 actual calls should have been made
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_async_circuit_breaker(self):
        """Test circuit breaker with async function."""
        call_count = 0
        
        @label_studio_retry_with_circuit_breaker(
            circuit_name="test_circuit_2",
            max_attempts=1,
            failure_threshold=2,
            recovery_timeout=60.0,
        )
        async def async_failing_func():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("connection failed")
        
        # First two calls fail
        with pytest.raises(httpx.ConnectError):
            await async_failing_func()
        
        with pytest.raises(httpx.ConnectError):
            await async_failing_func()
        
        # Third call blocked by circuit breaker
        with pytest.raises(CircuitBreakerError):
            await async_failing_func()
        
        assert call_count == 2


class TestCreateLabelStudioRetryExecutor:
    """Tests for create_label_studio_retry_executor function."""
    
    def test_create_executor_with_defaults(self):
        """Test creating executor with default config."""
        executor = create_label_studio_retry_executor()
        
        assert executor.config.max_attempts == 3
        assert executor.config.base_delay == 1.0
        assert executor.operation_name is None
    
    def test_create_executor_with_custom_config(self):
        """Test creating executor with custom config."""
        executor = create_label_studio_retry_executor(
            max_attempts=5,
            base_delay=0.5,
            operation_name="batch_import"
        )
        
        assert executor.config.max_attempts == 5
        assert executor.config.base_delay == 0.5
        assert executor.operation_name == "batch_import"
    
    def test_executor_can_be_reused(self):
        """Test that executor can be reused for multiple operations."""
        executor = create_label_studio_retry_executor(
            max_attempts=2,
            base_delay=0.01,
        )
        
        # Use executor for multiple operations
        result1 = executor.execute(lambda: "result1")
        result2 = executor.execute(lambda: "result2")
        
        assert result1 == "result1"
        assert result2 == "result2"


class TestRetryableExceptions:
    """Tests for retryable exception lists."""
    
    def test_retryable_exceptions_list(self):
        """Test that retryable exceptions list contains expected types."""
        expected_exceptions = [
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
            httpx.NetworkError,
            ConnectionError,
            TimeoutError,
            OSError,
        ]
        
        for exc in expected_exceptions:
            assert exc in LABEL_STUDIO_RETRYABLE_EXCEPTIONS
    
    def test_non_retryable_exceptions_list(self):
        """Test that non-retryable exceptions list contains expected types."""
        expected_exceptions = [
            httpx.HTTPStatusError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
        ]
        
        for exc in expected_exceptions:
            assert exc in LABEL_STUDIO_NON_RETRYABLE_EXCEPTIONS


class TestRetryLogging:
    """Tests for retry logging functionality."""
    
    def test_retry_logs_warning_on_retry(self):
        """Test that retry attempts are logged as warnings."""
        config = LabelStudioRetryConfig(
            max_attempts=2,
            base_delay=0.01,
            jitter=False,
        )
        executor = LabelStudioRetryExecutor(config)
        executor.operation_name = "test_operation"
        
        call_count = 0
        
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("timeout")
            return "success"
        
        with patch('src.label_studio.retry.logger') as mock_logger:
            result = executor.execute(failing_then_success)
        
        assert result == "success"
        # Should have logged a warning for the retry
        mock_logger.warning.assert_called()
    
    def test_retry_logs_error_on_final_failure(self):
        """Test that final failure is logged as error."""
        config = LabelStudioRetryConfig(
            max_attempts=2,
            base_delay=0.01,
            jitter=False,
        )
        executor = LabelStudioRetryExecutor(config)
        executor.operation_name = "test_operation"
        
        def always_fails():
            raise httpx.TimeoutException("timeout")
        
        with patch('src.label_studio.retry.logger') as mock_logger:
            with pytest.raises(httpx.TimeoutException):
                executor.execute(always_fails)
        
        # Should have logged an error for final failure
        mock_logger.error.assert_called()


class TestIntegrationWithLabelStudioMethods:
    """Integration tests simulating Label Studio API call patterns."""
    
    @pytest.mark.asyncio
    async def test_create_project_retry_pattern(self):
        """Test retry pattern for create_project-like operation."""
        call_count = 0
        
        @label_studio_retry(
            max_attempts=3,
            base_delay=0.01,
            operation_name="create_project"
        )
        async def mock_create_project(title: str):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectTimeout("connection timeout")
            return {"id": "123", "title": title}
        
        result = await mock_create_project("Test Project")
        
        assert result["id"] == "123"
        assert result["title"] == "Test Project"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_import_tasks_retry_pattern(self):
        """Test retry pattern for import_tasks-like operation."""
        call_count = 0
        
        @label_studio_retry(
            max_attempts=3,
            base_delay=0.01,
            operation_name="import_tasks"
        )
        async def mock_import_tasks(project_id: str, tasks: list):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ReadTimeout("read timeout")
            return {"imported": len(tasks)}
        
        result = await mock_import_tasks("123", [{"data": "task1"}, {"data": "task2"}])
        
        assert result["imported"] == 2
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_project_info_no_retry_on_404(self):
        """Test that 404 errors are not retried (HTTPStatusError)."""
        call_count = 0
        
        @label_studio_retry(
            max_attempts=3,
            base_delay=0.01,
        )
        async def mock_get_project_info(project_id: str):
            nonlocal call_count
            call_count += 1
            # Simulate 404 response
            response = MagicMock()
            response.status_code = 404
            raise httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=response
            )
        
        with pytest.raises(httpx.HTTPStatusError):
            await mock_get_project_info("nonexistent")
        
        # Should only be called once (no retry for 404)
        assert call_count == 1


class TestErrorRecoveryForProjectCreation:
    """
    Tests for error recovery in project creation operations.
    
    Validates: Requirements 1.5 - Handle network errors, timeouts, authentication failures
    """
    
    @pytest.fixture
    def mock_config(self):
        """Mock Label Studio configuration."""
        from src.label_studio.config import LabelStudioConfig
        config = Mock(spec=LabelStudioConfig)
        config.base_url = "https://labelstudio.example.com"
        config.api_token = "test_token_123"
        config.validate_config.return_value = True
        config.get_default_label_config.return_value = "<View><Text name='text' value='$text'/></View>"
        return config
    
    @pytest.fixture
    def integration(self, mock_config):
        """Label Studio integration instance with mocked config."""
        from src.label_studio.integration import LabelStudioIntegration
        return LabelStudioIntegration(mock_config)
    
    @pytest.fixture
    def project_config(self):
        """Sample project configuration."""
        from src.label_studio.integration import ProjectConfig
        return ProjectConfig(
            title="Test Annotation Project",
            description="Test project for error recovery testing",
            annotation_type="text_classification"
        )
    
    @pytest.mark.asyncio
    async def test_create_project_retries_on_timeout(self, integration, project_config):
        """Test that create_project retries on timeout errors."""
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Connection timeout")
            
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "id": 123,
                "title": "Test Annotation Project",
                "description": "Test project",
                "label_config": "<View><Text name='text' value='$text'/></View>",
                "created_at": "2024-01-01T12:00:00Z"
            }
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=mock_post)
            
            result = await integration.create_project(project_config)
            
            assert result.id == 123
            assert call_count == 3  # Should have retried twice
    
    @pytest.mark.asyncio
    async def test_create_project_retries_on_connection_error(self, integration, project_config):
        """Test that create_project retries on connection errors."""
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection refused")
            
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "id": 456,
                "title": "Test Annotation Project",
                "description": "Test project",
                "label_config": "<View><Text name='text' value='$text'/></View>",
                "created_at": "2024-01-01T12:00:00Z"
            }
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=mock_post)
            
            result = await integration.create_project(project_config)
            
            assert result.id == 456
            assert call_count == 2  # Should have retried once
    
    @pytest.mark.asyncio
    async def test_create_project_no_retry_on_auth_failure(self, integration, project_config):
        """Test that create_project does NOT retry on authentication failures."""
        from src.label_studio.integration import LabelStudioAuthenticationError
        
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=mock_post)
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await integration.create_project(project_config)
            
            # Should only be called once (no retry for auth errors)
            assert call_count == 1
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_project_no_retry_on_forbidden(self, integration, project_config):
        """Test that create_project does NOT retry on 403 Forbidden errors."""
        from src.label_studio.integration import LabelStudioAuthenticationError
        
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=mock_post)
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await integration.create_project(project_config)
            
            # Should only be called once (no retry for auth errors)
            assert call_count == 1
            assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_project_info_retries_on_network_error(self, integration):
        """Test that get_project_info retries on network errors."""
        call_count = 0
        
        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.NetworkError("Network unreachable")
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": 123,
                "title": "Existing Project",
                "description": "Project description",
                "label_config": "<View><Text name='text' value='$text'/></View>",
                "created_at": "2024-01-01T12:00:00Z"
            }
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            result = await integration.get_project_info("123")
            
            assert result.id == 123
            assert call_count == 2  # Should have retried once
    
    @pytest.mark.asyncio
    async def test_get_project_info_no_retry_on_404(self, integration):
        """Test that get_project_info does NOT retry on 404 (project not found)."""
        call_count = 0
        
        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = Mock()
            mock_response.status_code = 404
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            result = await integration.get_project_info("nonexistent")
            
            # Should return None without retrying
            assert result is None
            assert call_count == 1  # No retry for 404
    
    @pytest.mark.asyncio
    async def test_get_project_info_no_retry_on_auth_failure(self, integration):
        """Test that get_project_info does NOT retry on authentication failures."""
        from src.label_studio.integration import LabelStudioAuthenticationError
        
        call_count = 0
        
        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            with pytest.raises(LabelStudioAuthenticationError):
                await integration.get_project_info("123")
            
            # Should only be called once (no retry for auth errors)
            assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_ensure_project_exists_retries_on_network_error(self, integration, project_config):
        """Test that ensure_project_exists retries on network errors during project check."""
        get_call_count = 0
        
        async def mock_get(*args, **kwargs):
            nonlocal get_call_count
            get_call_count += 1
            if get_call_count < 2:
                raise httpx.ReadTimeout("Read timeout")
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": 123,
                "title": "Existing Project",
                "description": "Project description",
                "label_config": "<View><Text name='text' value='$text'/></View>",
                "created_at": "2024-01-01T12:00:00Z"
            }
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            result = await integration.ensure_project_exists("123", project_config)
            
            assert result.id == 123
            assert get_call_count == 2  # Should have retried once
    
    @pytest.mark.asyncio
    async def test_ensure_project_exists_creates_on_not_found(self, integration, project_config):
        """Test that ensure_project_exists creates project when not found."""
        get_call_count = 0
        post_call_count = 0
        
        async def mock_get(*args, **kwargs):
            nonlocal get_call_count
            get_call_count += 1
            mock_response = Mock()
            mock_response.status_code = 404
            return mock_response
        
        async def mock_post(*args, **kwargs):
            nonlocal post_call_count
            post_call_count += 1
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "id": 456,
                "title": "Test Annotation Project",
                "description": "Test project",
                "label_config": "<View><Text name='text' value='$text'/></View>",
                "created_at": "2024-01-01T12:00:00Z"
            }
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=mock_post)
            
            result = await integration.ensure_project_exists("nonexistent", project_config)
            
            assert result.id == 456
            assert get_call_count == 1  # Checked once
            assert post_call_count == 1  # Created once
    
    @pytest.mark.asyncio
    async def test_ensure_project_exists_propagates_auth_error(self, integration, project_config):
        """Test that ensure_project_exists propagates authentication errors."""
        from src.label_studio.integration import LabelStudioAuthenticationError
        
        async def mock_get(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            with pytest.raises(LabelStudioAuthenticationError):
                await integration.ensure_project_exists("123", project_config)
    
    @pytest.mark.asyncio
    async def test_validate_project_retries_on_timeout(self, integration):
        """Test that validate_project retries on timeout errors."""
        call_count = 0
        
        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Connection timeout")
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": 123,
                "title": "Test Project",
                "task_number": 10,
                "num_tasks_with_annotations": 5,
                "is_published": True,
                "is_draft": False,
                "created_at": "2024-01-01T12:00:00Z"
            }
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            result = await integration.validate_project("123")
            
            assert result.exists is True
            assert result.accessible is True
            assert result.task_count == 10
            assert result.annotation_count == 5
            assert call_count == 2  # Should have retried once
    
    @pytest.mark.asyncio
    async def test_validate_project_returns_error_on_auth_failure(self, integration):
        """Test that validate_project returns error result on authentication failure."""
        async def mock_get(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            
            result = await integration.validate_project("123")
            
            # Should return error result, not raise exception
            assert result.exists is False
            assert result.accessible is False
            assert result.status == "error"
            assert "Authentication failed" in result.error_message


class TestLabelStudioExceptionTypes:
    """Tests for Label Studio specific exception types."""
    
    def test_authentication_error_message(self):
        """Test LabelStudioAuthenticationError message formatting."""
        from src.label_studio.integration import LabelStudioAuthenticationError
        
        error = LabelStudioAuthenticationError("Invalid token", status_code=401)
        
        assert error.status_code == 401
        assert error.message == "Invalid token"
        assert "401" in str(error)
        assert "Invalid token" in str(error)
    
    def test_project_not_found_error_message(self):
        """Test LabelStudioProjectNotFoundError message formatting."""
        from src.label_studio.integration import LabelStudioProjectNotFoundError
        
        error = LabelStudioProjectNotFoundError("123")
        
        assert error.project_id == "123"
        assert "123" in str(error)
        assert "not found" in str(error).lower()
    
    def test_network_error_message(self):
        """Test LabelStudioNetworkError message formatting."""
        from src.label_studio.integration import LabelStudioNetworkError
        
        original = httpx.TimeoutException("Connection timeout")
        error = LabelStudioNetworkError("Failed to connect", original_error=original)
        
        assert error.original_error == original
        assert "Failed to connect" in str(error)
        assert "TimeoutException" in str(error)
    
    def test_network_error_without_original(self):
        """Test LabelStudioNetworkError without original error."""
        from src.label_studio.integration import LabelStudioNetworkError
        
        error = LabelStudioNetworkError("Network unreachable")
        
        assert error.original_error is None
        assert "Network unreachable" in str(error)
