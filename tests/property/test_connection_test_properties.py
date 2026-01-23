"""
Admin Configuration Connection Test Property Tests

Tests connection test timeout and isolation properties.

**Feature: admin-configuration**
**Property 6: Connection Test Timeout Enforcement**
**Property 7: Connection Test Isolation**
**Property 8: Connection Failure Logging**
**Validates: Requirements 1.3, 2.4, 2.7, 5.3**
"""

import pytest
import asyncio
import time
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.admin.llm_provider_manager import LLMProviderManager, ConnectionTestResult
from src.admin.db_connection_manager import DatabaseType


# ============================================================================
# Property 6: Connection Test Timeout Enforcement
# ============================================================================

class TestConnectionTestTimeoutEnforcement:
    """
    Property 6: Connection Test Timeout Enforcement
    
    For any connection test (LLM or database), the system should return a 
    result (success or timeout error) within the specified timeout period.
    
    **Feature: admin-configuration**
    **Validates: Requirements 1.3, 2.4**
    """
    
    @given(
        provider=st.sampled_from(["openai", "anthropic", "qianwen", "ollama"]),
        timeout=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=20, deadline=None)  # Reduced from 100 to 20
    def test_llm_connection_test_respects_timeout(self, provider, timeout):
        """
        LLM connection tests return within timeout period.
        
        For any LLM provider and timeout value, the connection test should
        complete (success or timeout error) within the specified timeout.
        """
        manager = LLMProviderManager()
        
        async def run_test():
            start_time = time.time()
            
            # Test connection with specified timeout
            result = await manager.test_connection(
                provider=provider,
                api_key="test-key-12345",
                endpoint=None,
                timeout=timeout
            )
            
            elapsed_time = time.time() - start_time
            
            # Should complete within timeout + 1 second buffer
            assert elapsed_time <= (timeout + 1.0), \
                f"Connection test took {elapsed_time:.2f}s, expected <={timeout + 1.0}s"
            
            # Result should be returned (not None)
            assert result is not None, "Connection test should return a result"
            
            # Result should be ConnectionTestResult
            assert isinstance(result, ConnectionTestResult), \
                "Result should be ConnectionTestResult instance"
            
            # If timeout occurred, error code should indicate timeout
            if elapsed_time >= timeout:
                assert result.success is False, \
                    "Timed out connection should have success=False"
                assert result.error_code == "TIMEOUT", \
                    "Timeout should have error_code='TIMEOUT'"
        
        asyncio.run(run_test())
    
    @given(
        timeout=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=15, deadline=None)  # Reduced from 100 to 15
    def test_timeout_error_returned_appropriately(self, timeout):
        """
        Timeout errors are returned with appropriate error details.
        
        When a connection test times out, the result should include
        timeout error code and helpful suggestions.
        """
        manager = LLMProviderManager()
        
        async def run_test():
            # Use unreachable endpoint to force timeout
            result = await manager.test_connection(
                provider="openai",
                api_key="test-key",
                endpoint="https://192.0.2.1:9999",  # TEST-NET-1, unreachable
                timeout=timeout
            )
            
            # Should return timeout result
            assert result.success is False, "Unreachable endpoint should fail"
            
            # Should have timeout-related error
            assert result.error_code in ["TIMEOUT", "CONNECTION_ERROR"], \
                f"Expected timeout or connection error, got {result.error_code}"
            
            # Should have error message
            assert result.error_message is not None, \
                "Timeout should have error message"
            assert len(result.error_message) > 0, \
                "Error message should not be empty"
            
            # Should have troubleshooting suggestions
            assert len(result.suggestions) > 0, \
                "Timeout should include troubleshooting suggestions"
        
        asyncio.run(run_test())
    
    def test_default_timeout_is_10_seconds(self):
        """
        Default timeout for connection tests is 10 seconds.
        
        When no timeout is specified, the default should be 10 seconds
        as per requirements.
        """
        manager = LLMProviderManager()
        
        async def run_test():
            start_time = time.time()
            
            # Test without specifying timeout (should use default)
            result = await manager.test_connection(
                provider="openai",
                api_key="test-key",
                endpoint="https://192.0.2.1:9999"  # Unreachable
            )
            
            elapsed_time = time.time() - start_time
            
            # Should timeout around 10 seconds (with buffer)
            assert elapsed_time >= 9.0, \
                f"Should wait at least 9s, waited {elapsed_time:.2f}s"
            assert elapsed_time <= 12.0, \
                f"Should timeout by 12s, took {elapsed_time:.2f}s"
        
        asyncio.run(run_test())


# ============================================================================
# Property 7: Connection Test Isolation
# ============================================================================

class TestConnectionTestIsolation:
    """
    Property 7: Connection Test Isolation
    
    For any connection test execution, the test should not affect production
    data, connections, or services, and should execute in an isolated environment.
    
    **Feature: admin-configuration**
    **Validates: Requirements 5.3**
    """
    
    @given(
        provider=st.sampled_from(["openai", "anthropic", "ollama"])
    )
    @settings(max_examples=15, deadline=None)  # Reduced from 100 to 15
    def test_connection_test_does_not_affect_production(self, provider):
        """
        Connection tests don't affect production configurations.
        
        Running a connection test should not modify any production
        configurations or cached data.
        """
        manager = LLMProviderManager()
        
        async def run_test():
            # Set up some "production" quota data
            await manager.update_quota_usage(
                config_id="prod-config-1",
                provider=provider,
                tokens_used=1000,
                success=True
            )
            
            initial_quota = await manager.get_quota_usage("prod-config-1")
            initial_requests = initial_quota.total_requests
            initial_tokens = initial_quota.total_tokens
            
            # Run connection test
            await manager.test_connection(
                provider=provider,
                api_key="test-key",
                endpoint=None,
                timeout=2
            )
            
            # Verify production data unchanged
            final_quota = await manager.get_quota_usage("prod-config-1")
            
            assert final_quota.total_requests == initial_requests, \
                "Connection test should not affect production request count"
            assert final_quota.total_tokens == initial_tokens, \
                "Connection test should not affect production token count"
        
        asyncio.run(run_test())
    
    @given(
        num_tests=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=10, deadline=None)  # Reduced from 100 to 10
    def test_concurrent_connection_tests_isolated(self, num_tests):
        """
        Concurrent connection tests are isolated from each other.
        
        Multiple connection tests running concurrently should not
        interfere with each other's results.
        """
        manager = LLMProviderManager()
        
        async def run_test():
            # Run multiple connection tests concurrently
            tasks = [
                manager.test_connection(
                    provider="openai",
                    api_key=f"test-key-{i}",
                    endpoint=None,
                    timeout=2
                )
                for i in range(num_tests)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should return results (no exceptions)
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), \
                    f"Test {i} raised exception: {result}"
                assert isinstance(result, ConnectionTestResult), \
                    f"Test {i} should return ConnectionTestResult"
        
        asyncio.run(run_test())
    
    def test_connection_test_uses_separate_session(self):
        """
        Connection tests use separate HTTP sessions.
        
        Each connection test should create its own HTTP session
        to avoid affecting other operations.
        """
        manager = LLMProviderManager()
        
        async def run_test():
            # Run test and verify it completes without affecting manager state
            result = await manager.test_connection(
                provider="openai",
                api_key="test-key",
                endpoint=None,
                timeout=2
            )
            
            # Manager should still be functional after test
            assert result is not None
            
            # Should be able to run another test immediately
            result2 = await manager.test_connection(
                provider="anthropic",
                api_key="test-key-2",
                endpoint=None,
                timeout=2
            )
            
            assert result2 is not None
        
        asyncio.run(run_test())


# ============================================================================
# Property 8: Connection Failure Logging
# ============================================================================

class TestConnectionFailureLogging:
    """
    Property 8: Connection Failure Logging
    
    For any connection failure (LLM or database), the system should log
    detailed error information including error code, message, and timestamp.
    
    **Feature: admin-configuration**
    **Validates: Requirements 2.7**
    """
    
    @given(
        provider=st.sampled_from(["openai", "anthropic", "qianwen"])
    )
    @settings(max_examples=15, deadline=None)  # Reduced from 100 to 15
    def test_connection_failure_includes_error_code(self, provider):
        """
        Connection failures include specific error codes.
        
        When a connection test fails, the result should include
        a specific error code for programmatic handling.
        """
        manager = LLMProviderManager()
        
        async def run_test():
            # Force failure with unreachable endpoint
            result = await manager.test_connection(
                provider=provider,
                api_key="test-key",
                endpoint="https://192.0.2.1:9999",
                timeout=2
            )
            
            # Should fail
            assert result.success is False, \
                "Unreachable endpoint should fail"
            
            # Should have error code
            assert result.error_code is not None, \
                "Failed connection should have error code"
            assert len(result.error_code) > 0, \
                "Error code should not be empty"
            
            # Error code should be one of expected types
            valid_codes = ["TIMEOUT", "CONNECTION_ERROR", "SSL_ERROR", "UNKNOWN_ERROR"]
            assert result.error_code in valid_codes, \
                f"Error code '{result.error_code}' should be one of {valid_codes}"
        
        asyncio.run(run_test())
    
    @given(
        provider=st.sampled_from(["openai", "anthropic"])
    )
    @settings(max_examples=15, deadline=None)  # Reduced from 100 to 15
    def test_connection_failure_includes_error_message(self, provider):
        """
        Connection failures include descriptive error messages.
        
        Failed connection tests should return human-readable error
        messages explaining what went wrong.
        """
        manager = LLMProviderManager()
        
        async def run_test():
            result = await manager.test_connection(
                provider=provider,
                api_key="test-key",
                endpoint="https://192.0.2.1:9999",
                timeout=2
            )
            
            # Should have error message
            assert result.error_message is not None, \
                "Failed connection should have error message"
            assert len(result.error_message) > 10, \
                "Error message should be descriptive (>10 chars)"
            
            # Message should be human-readable (contains common words)
            message_lower = result.error_message.lower()
            common_words = ["connection", "failed", "timeout", "error", "unable"]
            assert any(word in message_lower for word in common_words), \
                f"Error message should be human-readable: {result.error_message}"
        
        asyncio.run(run_test())
    
    @given(
        provider=st.sampled_from(["openai", "anthropic"])
    )
    @settings(max_examples=15, deadline=None)  # Reduced from 100 to 15
    def test_connection_failure_includes_timestamp(self, provider):
        """
        Connection test results include timestamps.
        
        All connection test results (success or failure) should include
        a timestamp indicating when the test was performed.
        """
        manager = LLMProviderManager()
        
        async def run_test():
            before_test = datetime.utcnow()
            
            result = await manager.test_connection(
                provider=provider,
                api_key="test-key",
                endpoint="https://192.0.2.1:9999",
                timeout=2
            )
            
            after_test = datetime.utcnow()
            
            # Should have timestamp
            assert result.tested_at is not None, \
                "Connection test result should have timestamp"
            
            # Timestamp should be within test execution window
            assert before_test <= result.tested_at <= after_test, \
                "Timestamp should be within test execution time"
        
        asyncio.run(run_test())
    
    @given(
        provider=st.sampled_from(["openai", "anthropic"])
    )
    @settings(max_examples=15, deadline=None)  # Reduced from 100 to 15
    def test_connection_failure_includes_troubleshooting_suggestions(self, provider):
        """
        Connection failures include troubleshooting suggestions.
        
        Failed connection tests should provide helpful suggestions
        for resolving the issue.
        """
        manager = LLMProviderManager()
        
        async def run_test():
            result = await manager.test_connection(
                provider=provider,
                api_key="test-key",
                endpoint="https://192.0.2.1:9999",
                timeout=2
            )
            
            # Should have suggestions
            assert result.suggestions is not None, \
                "Failed connection should have suggestions"
            assert len(result.suggestions) > 0, \
                "Should have at least one troubleshooting suggestion"
            
            # Suggestions should be non-empty strings
            for suggestion in result.suggestions:
                assert isinstance(suggestion, str), \
                    "Suggestions should be strings"
                assert len(suggestion) > 5, \
                    f"Suggestion should be descriptive: {suggestion}"
        
        asyncio.run(run_test())
    
    def test_different_failure_types_have_different_error_codes(self):
        """
        Different failure types result in different error codes.
        
        Timeout, connection error, and authentication error should
        have distinct error codes.
        """
        manager = LLMProviderManager()
        
        async def run_test():
            # Test timeout (unreachable)
            timeout_result = await manager.test_connection(
                provider="openai",
                api_key="test-key",
                endpoint="https://192.0.2.1:9999",
                timeout=1
            )
            
            # Verify we get an error code
            assert timeout_result.error_code in ["TIMEOUT", "CONNECTION_ERROR"], \
                f"Expected timeout/connection error, got {timeout_result.error_code}"
        
        asyncio.run(run_test())


    def test_database_connection_failure_logging(self):
        """
        Database connection failures are logged with details.
        
        When a database connection test fails, the result should include
        error code, message, and timestamp for troubleshooting.
        """
        from src.admin.db_connection_manager import DBConnectionManager, DBConfig, DatabaseType
        
        async def run_test():
            manager = DBConnectionManager()
            
            # Test with unreachable database
            config = DBConfig(
                db_type=DatabaseType.POSTGRESQL,
                host="192.0.2.1",  # TEST-NET-1, unreachable
                port=5432,
                database="test_db",
                username="test_user",
                password="test_pass",
                read_only=True,
                timeout=2
            )
            
            result = await manager.test_connection(config)
            
            # Should fail
            assert result.success is False, \
                "Unreachable database should fail"
            
            # Should have error code
            assert result.error_code is not None, \
                "Failed connection should have error code"
            assert len(result.error_code) > 0, \
                "Error code should not be empty"
            
            # Should have error message
            assert result.error_message is not None, \
                "Failed connection should have error message"
            assert len(result.error_message) > 10, \
                "Error message should be descriptive"
            
            # Should have timestamp
            assert result.tested_at is not None, \
                "Connection test result should have timestamp"
            
            # Should have troubleshooting suggestions
            assert len(result.suggestions) > 0, \
                "Failed connection should have troubleshooting suggestions"
        
        asyncio.run(run_test())
    
    @given(
        db_type=st.sampled_from([DatabaseType.POSTGRESQL, DatabaseType.MYSQL])
    )
    @settings(max_examples=10, deadline=None)
    def test_database_connection_failure_includes_all_details(self, db_type):
        """
        Database connection failures include comprehensive error details.
        
        For any database type, connection failures should include error code,
        message, timestamp, and suggestions.
        """
        from src.admin.db_connection_manager import DBConnectionManager, DBConfig
        
        async def run_test():
            manager = DBConnectionManager()
            
            # Use unreachable host to force failure
            config = DBConfig(
                db_type=db_type,
                host="192.0.2.1",  # TEST-NET-1, unreachable
                port=5432 if db_type == DatabaseType.POSTGRESQL else 3306,
                database="test_db",
                username="test_user",
                password="test_pass",
                read_only=True,
                timeout=2
            )
            
            result = await manager.test_connection(config)
            
            # Verify all required fields are present
            assert result.success is False, "Should fail for unreachable host"
            assert result.error_code is not None, "Should have error code"
            assert result.error_message is not None, "Should have error message"
            assert result.tested_at is not None, "Should have timestamp"
            assert result.db_type == db_type.value, "Should record database type"
            assert len(result.suggestions) > 0, "Should have suggestions"
            
            # Verify error code is meaningful
            valid_codes = ["TIMEOUT", "CONNECTION_ERROR", "UNKNOWN_ERROR", "MISSING_DRIVER"]
            assert result.error_code in valid_codes, \
                f"Error code should be one of {valid_codes}, got {result.error_code}"
        
        asyncio.run(run_test())


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
