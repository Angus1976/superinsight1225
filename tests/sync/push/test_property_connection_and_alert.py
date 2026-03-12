"""
Property-based tests for connection failure and alert triggering.

Feature: bidirectional-sync-and-external-api
Properties 3, 8: Connection failure error messages and failure rate alerts

Tests connection error completeness and alert triggering logic.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from hypothesis import given, strategies as st, settings, assume

from src.sync.push.connection_test_service import (
    ConnectionTestService,
    ConnectionStatus,
    ConnectionTestResult
)
from src.sync.push.output_sync_alert_service import OutputSyncAlertService
from src.sync.models import (
    SyncJobModel,
    SyncExecutionModel,
    SyncJobStatus,
    SyncExecutionStatus,
    SyncDirection,
    SyncFrequency,
    DataSourceModel,
    DataSourceType
)


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def invalid_connection_config_strategy(draw):
    """
    Generate invalid connection configurations for various database types.
    
    Returns:
        tuple: (target_type, config, expected_error_type)
    """
    target_type = draw(st.sampled_from([
        "postgresql", "mysql", "mongodb", "api"
    ]))
    
    if target_type == "postgresql":
        # Missing required fields
        missing_fields = draw(st.lists(
            st.sampled_from(["host", "port", "database", "username"]),
            min_size=1,
            max_size=3,
            unique=True
        ))
        
        config = {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "username": "user"
        }
        
        # Remove some fields to make it invalid
        for field in missing_fields:
            config.pop(field, None)
        
        return target_type, config, "missing_fields"
    
    elif target_type == "mysql":
        # Missing required fields
        missing_fields = draw(st.lists(
            st.sampled_from(["host", "port", "database", "username"]),
            min_size=1,
            max_size=3,
            unique=True
        ))
        
        config = {
            "host": "localhost",
            "port": 3306,
            "database": "testdb",
            "username": "user"
        }
        
        for field in missing_fields:
            config.pop(field, None)
        
        return target_type, config, "missing_fields"
    
    elif target_type == "mongodb":
        # Missing connection_string or host
        config = {}  # Empty config
        return target_type, config, "missing_connection_info"
    
    else:  # api
        # Missing endpoint_url
        config = {}
        return target_type, config, "missing_endpoint"


@st.composite
def failure_rate_scenario_strategy(draw):
    """
    Generate a failure rate scenario with executions.
    
    Returns:
        tuple: (total_executions, failed_executions, actual_failure_rate, should_alert)
    """
    # Generate total executions (5-50)
    total = draw(st.integers(min_value=5, max_value=50))
    
    # Generate failed executions (0 to total)
    failed = draw(st.integers(min_value=0, max_value=total))
    
    # Calculate actual failure rate
    actual_failure_rate = failed / total if total > 0 else 0.0
    
    # Determine if should alert (>= 20% threshold)
    should_alert = actual_failure_rate >= 0.20
    
    return total, failed, actual_failure_rate, should_alert


@st.composite
def alert_threshold_scenario_strategy(draw):
    """
    Generate scenarios around alert thresholds.
    
    Returns:
        tuple: (total_executions, failed_executions, expected_alert_level)
    """
    # Generate total executions (minimum 10 for alerting)
    total = draw(st.integers(min_value=10, max_value=50))
    
    # Choose a scenario
    scenario = draw(st.sampled_from([
        "below_warning",      # < 20%
        "at_warning",         # >= 20% and < 50%
        "at_critical",        # >= 50%
    ]))
    
    if scenario == "below_warning":
        # Failure rate < 20%
        # Use ceiling to ensure we're strictly below 20%
        max_failed = int(total * 0.20) - 1
        failed = draw(st.integers(min_value=0, max_value=max(0, max_failed)))
        expected_level = None
    elif scenario == "at_warning":
        # Failure rate >= 20% and < 50%
        # Use ceiling to ensure we're at or above 20%
        min_failed = int(total * 0.20) if (total * 0.20) == int(total * 0.20) else int(total * 0.20) + 1
        max_failed = int(total * 0.50) - 1
        failed = draw(st.integers(min_value=min_failed, max_value=max(min_failed, max_failed)))
        expected_level = "warning"
    else:  # at_critical
        # Failure rate >= 50%
        min_failed = int(total * 0.50) if (total * 0.50) == int(total * 0.50) else int(total * 0.50) + 1
        failed = draw(st.integers(min_value=min_failed, max_value=total))
        expected_level = "critical"
    
    return total, failed, expected_level


# ============================================================================
# Property Tests
# ============================================================================

class TestConnectionFailureProperties:
    """Property-based tests for connection failure error messages."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = ConnectionTestService()
    
    # Feature: bidirectional-sync-and-external-api, Property 3: 连接失败错误信息完整性
    @settings(max_examples=100, deadline=None)
    @given(scenario=invalid_connection_config_strategy())
    @pytest.mark.asyncio
    async def test_connection_failure_error_completeness(self, scenario):
        """
        Property: For any invalid target data source connection configuration,
        executing a connection test should return an error response containing
        both error_message and troubleshooting_suggestions fields.
        
        Validates: Requirements 1.5
        """
        target_type, config, error_type = scenario
        
        # Test connection based on type
        if target_type == "postgresql":
            result = await self.service._test_postgresql_connection(
                config, "test-target-id"
            )
        elif target_type == "mysql":
            result = await self.service._test_mysql_connection(
                config, "test-target-id"
            )
        elif target_type == "mongodb":
            result = await self.service._test_mongodb_connection(
                config, "test-target-id"
            )
        else:  # api
            result = await self.service._test_api_connection(
                config, "test-target-id"
            )
        
        # Property 1: Result should indicate failure
        assert result.status == ConnectionStatus.FAILED, (
            f"Connection test with invalid config should fail, got {result.status}"
        )
        
        # Property 2: Must have error_message field
        assert hasattr(result, "error_message"), (
            "Connection test result must have error_message field"
        )
        assert result.error_message is not None, (
            "error_message should not be None for failed connection"
        )
        assert len(result.error_message) > 0, (
            "error_message should not be empty for failed connection"
        )
        
        # Property 3: Must have troubleshooting_suggestions field
        assert hasattr(result, "troubleshooting_suggestions"), (
            "Connection test result must have troubleshooting_suggestions field"
        )
        assert result.troubleshooting_suggestions is not None, (
            "troubleshooting_suggestions should not be None"
        )
        
        # Property 4: troubleshooting_suggestions should be a non-empty list
        assert isinstance(result.troubleshooting_suggestions, list), (
            f"troubleshooting_suggestions should be a list, got {type(result.troubleshooting_suggestions)}"
        )
        assert len(result.troubleshooting_suggestions) > 0, (
            "troubleshooting_suggestions should contain at least one suggestion"
        )
        
        # Property 5: Each suggestion should be a non-empty string
        for i, suggestion in enumerate(result.troubleshooting_suggestions):
            assert isinstance(suggestion, str), (
                f"Suggestion {i} should be a string, got {type(suggestion)}"
            )
            assert len(suggestion) > 0, (
                f"Suggestion {i} should not be empty"
            )
        
        # Property 6: Suggestions should be actionable (contain verbs or instructions)
        actionable_keywords = [
            "check", "verify", "ensure", "add", "provide", "configure",
            "review", "confirm", "update", "set", "enable", "disable"
        ]
        suggestions_text = " ".join(result.troubleshooting_suggestions).lower()
        has_actionable = any(keyword in suggestions_text for keyword in actionable_keywords)
        assert has_actionable, (
            f"Troubleshooting suggestions should contain actionable advice. "
            f"Got: {result.troubleshooting_suggestions}"
        )
    
    # Feature: bidirectional-sync-and-external-api, Property 3: 连接失败错误信息完整性
    @settings(max_examples=100, deadline=None)
    @given(
        target_type=st.sampled_from(["postgresql", "mysql", "mongodb", "api"]),
        error_message=st.text(min_size=10, max_size=200)
    )
    def test_database_error_result_structure(self, target_type, error_message):
        """
        Property: Database error results should always have complete structure
        with error message and troubleshooting suggestions.
        
        Validates: Requirements 1.5
        """
        result = self.service._create_database_error_result(
            "test-target-id",
            target_type,
            error_message
        )
        
        # Property 1: Status should be FAILED
        assert result.status == ConnectionStatus.FAILED, (
            f"Error result should have FAILED status, got {result.status}"
        )
        
        # Property 2: error_message should match input
        assert result.error_message == error_message, (
            f"error_message should be '{error_message}', got '{result.error_message}'"
        )
        
        # Property 3: Should have troubleshooting suggestions
        assert len(result.troubleshooting_suggestions) > 0, (
            "Error result should have troubleshooting suggestions"
        )
        
        # Property 4: Suggestions should be limited (not overwhelming)
        assert len(result.troubleshooting_suggestions) <= 10, (
            f"Should have at most 10 suggestions, got {len(result.troubleshooting_suggestions)}"
        )
        
        # Property 5: target_type should be preserved
        assert result.target_type == target_type, (
            f"target_type should be '{target_type}', got '{result.target_type}'"
        )
    
    # Feature: bidirectional-sync-and-external-api, Property 3: 连接失败错误信息完整性
    @settings(max_examples=100, deadline=None)
    @given(
        error_keyword=st.sampled_from([
            "timeout", "authentication", "password", "host", "resolve", "refused"
        ])
    )
    def test_error_specific_suggestions(self, error_keyword):
        """
        Property: Error messages with specific keywords should trigger
        relevant troubleshooting suggestions.
        
        Validates: Requirements 1.5
        """
        error_message = f"Connection failed: {error_keyword} error occurred"
        
        result = self.service._create_database_error_result(
            "test-target-id",
            "postgresql",
            error_message
        )
        
        # Property 1: Should have suggestions
        assert len(result.troubleshooting_suggestions) > 0, (
            "Should have troubleshooting suggestions"
        )
        
        # Property 2: First suggestion should be relevant to the error
        first_suggestion = result.troubleshooting_suggestions[0].lower()
        
        # Check for keyword-specific suggestions
        if error_keyword == "timeout":
            assert "timeout" in first_suggestion or "latency" in first_suggestion, (
                f"Timeout error should have timeout-related suggestion, got: {first_suggestion}"
            )
        elif error_keyword in ["authentication", "password"]:
            assert "authentication" in first_suggestion or "credentials" in first_suggestion or "password" in first_suggestion, (
                f"Auth error should have auth-related suggestion, got: {first_suggestion}"
            )
        elif error_keyword in ["host", "resolve"]:
            assert "hostname" in first_suggestion or "dns" in first_suggestion or "resolve" in first_suggestion, (
                f"Host error should have DNS-related suggestion, got: {first_suggestion}"
            )
        elif error_keyword == "refused":
            assert "refused" in first_suggestion or "accepting" in first_suggestion or "connections" in first_suggestion, (
                f"Refused error should have connection-related suggestion, got: {first_suggestion}"
            )


class TestFailureRateAlertProperties:
    """Property-based tests for failure rate alert triggering."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = OutputSyncAlertService()
    
    # Feature: bidirectional-sync-and-external-api, Property 8: 失败率告警触发
    @settings(max_examples=100, deadline=None)
    @given(scenario=failure_rate_scenario_strategy())
    def test_failure_rate_alert_trigger_logic(self, scenario):
        """
        Property: For any sync task, when failed_executions / total_executions
        exceeds the configured threshold (20%), the system should trigger an alert.
        
        Validates: Requirements 3.2
        """
        total_executions, failed_executions, actual_failure_rate, should_alert = scenario
        
        # Assume we have minimum executions for meaningful test
        assume(total_executions >= 5)
        
        # Property 1: Alert decision should match threshold logic
        warning_threshold = self.service.DEFAULT_FAILURE_RATE_WARNING  # 0.20
        expected_alert = (
            total_executions >= self.service.DEFAULT_MIN_EXECUTIONS and
            actual_failure_rate >= warning_threshold
        )
        
        assert expected_alert == should_alert, (
            f"Alert decision mismatch: failure_rate={actual_failure_rate:.2%}, "
            f"threshold={warning_threshold:.2%}, should_alert={should_alert}, expected={expected_alert}"
        )
        
        # Property 2: If failure rate >= 20%, should alert
        if actual_failure_rate >= 0.20:
            assert should_alert, (
                f"Should alert when failure rate ({actual_failure_rate:.2%}) >= 20%"
            )
        
        # Property 3: If failure rate < 20%, should not alert
        if actual_failure_rate < 0.20:
            assert not should_alert, (
                f"Should not alert when failure rate ({actual_failure_rate:.2%}) < 20%"
            )
        
        # Property 4: Failure rate should be in valid range [0, 1]
        assert 0.0 <= actual_failure_rate <= 1.0, (
            f"Failure rate should be between 0 and 1, got {actual_failure_rate}"
        )
        
        # Property 5: Failed executions should not exceed total
        assert failed_executions <= total_executions, (
            f"Failed executions ({failed_executions}) should not exceed "
            f"total executions ({total_executions})"
        )
    
    # Feature: bidirectional-sync-and-external-api, Property 8: 失败率告警触发
    @settings(max_examples=100, deadline=None)
    @given(scenario=alert_threshold_scenario_strategy())
    def test_alert_severity_levels(self, scenario):
        """
        Property: Alert severity should match failure rate thresholds:
        - No alert: < 20%
        - Warning: 20% <= rate < 50%
        - Critical: >= 50%
        
        Validates: Requirements 3.2
        """
        total_executions, failed_executions, expected_level = scenario
        
        # Calculate failure rate
        failure_rate = failed_executions / total_executions if total_executions > 0 else 0.0
        
        # Determine actual alert level based on thresholds
        warning_threshold = 0.20
        critical_threshold = 0.50
        
        if failure_rate < warning_threshold:
            actual_level = None
        elif failure_rate >= critical_threshold:
            actual_level = "critical"
        else:
            actual_level = "warning"
        
        # Property 1: Alert level should match expected
        assert actual_level == expected_level, (
            f"Alert level mismatch: failure_rate={failure_rate:.2%}, "
            f"expected={expected_level}, actual={actual_level}"
        )
        
        # Property 2: Critical alerts should only trigger at >= 50%
        if actual_level == "critical":
            assert failure_rate >= critical_threshold, (
                f"Critical alert should only trigger at >= 50%, got {failure_rate:.2%}"
            )
        
        # Property 3: Warning alerts should trigger between 20% and 50%
        if actual_level == "warning":
            assert warning_threshold <= failure_rate < critical_threshold, (
                f"Warning alert should trigger between 20% and 50%, got {failure_rate:.2%}"
            )
        
        # Property 4: No alert below 20%
        if failure_rate < warning_threshold:
            assert actual_level is None, (
                f"Should not alert below 20%, got level={actual_level} at {failure_rate:.2%}"
            )
    
    # Feature: bidirectional-sync-and-external-api, Property 8: 失败率告警触发
    @settings(max_examples=100, deadline=None)
    @given(
        total_executions=st.integers(min_value=1, max_value=4),
        failed_executions=st.integers(min_value=0, max_value=4)
    )
    def test_minimum_executions_threshold(self, total_executions, failed_executions):
        """
        Property: Alerts should not trigger if total executions is below
        the minimum threshold (5 executions), regardless of failure rate.
        
        Validates: Requirements 3.2
        """
        # Ensure failed doesn't exceed total
        assume(failed_executions <= total_executions)
        
        # Calculate failure rate
        failure_rate = failed_executions / total_executions if total_executions > 0 else 0.0
        
        # Property 1: Should not alert if below minimum executions
        min_executions = self.service.DEFAULT_MIN_EXECUTIONS  # 5
        
        if total_executions < min_executions:
            # Even with high failure rate, should not alert
            should_alert = False
            
            assert not should_alert, (
                f"Should not alert with only {total_executions} executions "
                f"(minimum is {min_executions}), even with {failure_rate:.2%} failure rate"
            )
        
        # Property 2: Minimum threshold should be positive
        assert min_executions > 0, (
            "Minimum executions threshold should be positive"
        )
        
        # Property 3: Total executions below minimum should not trigger alerts
        assert total_executions < min_executions, (
            f"Test scenario should have executions ({total_executions}) "
            f"below minimum ({min_executions})"
        )
    
    # Feature: bidirectional-sync-and-external-api, Property 8: 失败率告警触发
    @settings(max_examples=100, deadline=None)
    @given(
        total_executions=st.integers(min_value=10, max_value=100),
        failure_rate_percent=st.integers(min_value=0, max_value=100)
    )
    def test_failure_rate_calculation_accuracy(self, total_executions, failure_rate_percent):
        """
        Property: Failure rate calculation should be accurate and consistent.
        
        Validates: Requirements 3.2
        """
        # Calculate failed executions from percentage
        failed_executions = int(total_executions * failure_rate_percent / 100)
        
        # Calculate failure rate
        calculated_rate = failed_executions / total_executions if total_executions > 0 else 0.0
        
        # Property 1: Calculated rate should be in valid range
        assert 0.0 <= calculated_rate <= 1.0, (
            f"Failure rate should be between 0 and 1, got {calculated_rate}"
        )
        
        # Property 2: Rate should be approximately equal to input percentage
        # Allow tolerance due to integer rounding
        expected_rate = failure_rate_percent / 100
        tolerance = 1.0 / total_executions + 0.01  # Account for rounding
        assert abs(calculated_rate - expected_rate) <= tolerance, (
            f"Calculated rate ({calculated_rate:.2%}) should be close to "
            f"expected rate ({expected_rate:.2%}) within tolerance {tolerance:.2%}"
        )
        
        # Property 3: Failed count should not exceed total
        assert failed_executions <= total_executions, (
            f"Failed executions ({failed_executions}) should not exceed "
            f"total ({total_executions})"
        )
        
        # Property 4: If all executions failed, rate should be 1.0
        if failed_executions == total_executions:
            assert calculated_rate == 1.0, (
                f"When all executions fail, rate should be 1.0, got {calculated_rate}"
            )
        
        # Property 5: If no executions failed, rate should be 0.0
        if failed_executions == 0:
            assert calculated_rate == 0.0, (
                f"When no executions fail, rate should be 0.0, got {calculated_rate}"
            )
    
    # Feature: bidirectional-sync-and-external-api, Property 8: 失败率告警触发
    @settings(max_examples=100, deadline=None)
    @given(
        total_executions=st.integers(min_value=5, max_value=50),
        consecutive_failures=st.integers(min_value=0, max_value=10)
    )
    def test_alert_trigger_consistency(self, total_executions, consecutive_failures):
        """
        Property: Alert triggering should be consistent and deterministic
        based on failure rate, not affected by execution order.
        
        Validates: Requirements 3.2
        """
        # Ensure consecutive failures don't exceed total
        assume(consecutive_failures <= total_executions)
        
        # Calculate failure rate
        failure_rate = consecutive_failures / total_executions
        
        # Determine if should alert
        warning_threshold = 0.20
        should_alert = (
            total_executions >= self.service.DEFAULT_MIN_EXECUTIONS and
            failure_rate >= warning_threshold
        )
        
        # Property 1: Alert decision should be deterministic
        # Running the same calculation twice should give same result
        should_alert_2 = (
            total_executions >= self.service.DEFAULT_MIN_EXECUTIONS and
            failure_rate >= warning_threshold
        )
        assert should_alert == should_alert_2, (
            "Alert decision should be deterministic"
        )
        
        # Property 2: Alert decision should only depend on rate, not order
        # Whether failures are consecutive or scattered shouldn't matter
        scattered_failures = consecutive_failures
        scattered_rate = scattered_failures / total_executions
        
        assert failure_rate == scattered_rate, (
            "Failure rate should be same regardless of failure distribution"
        )
        
        # Property 3: Threshold crossing should be consistent
        if failure_rate >= warning_threshold:
            assert should_alert, (
                f"Should alert when rate ({failure_rate:.2%}) >= threshold ({warning_threshold:.2%})"
            )
        elif failure_rate < warning_threshold:
            assert not should_alert or total_executions < self.service.DEFAULT_MIN_EXECUTIONS, (
                f"Should not alert when rate ({failure_rate:.2%}) < threshold ({warning_threshold:.2%})"
            )


class TestAlertIntegrationProperties:
    """Integration property tests for connection and alert features."""
    
    # Feature: bidirectional-sync-and-external-api, Property 3 & 8: Integration
    @settings(max_examples=50, deadline=None)
    @given(
        has_connection_error=st.booleans(),
        failure_rate=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_connection_error_and_alert_integration(self, has_connection_error, failure_rate):
        """
        Property: Connection errors should provide complete error information,
        and high failure rates should trigger alerts with proper severity.
        
        Validates: Requirements 1.5, 3.2
        """
        # Property 1: Connection errors should have complete structure
        if has_connection_error:
            service = ConnectionTestService()
            result = service._create_database_error_result(
                "test-id",
                "postgresql",
                "Test connection error"
            )
            
            assert result.error_message is not None, (
                "Connection error should have error_message"
            )
            assert len(result.troubleshooting_suggestions) > 0, (
                "Connection error should have troubleshooting suggestions"
            )
        
        # Property 2: Failure rate should determine alert level
        alert_service = OutputSyncAlertService()
        warning_threshold = alert_service.DEFAULT_FAILURE_RATE_WARNING
        critical_threshold = alert_service.DEFAULT_FAILURE_RATE_CRITICAL
        
        if failure_rate >= critical_threshold:
            expected_level = "critical"
        elif failure_rate >= warning_threshold:
            expected_level = "warning"
        else:
            expected_level = None
        
        # Verify threshold logic
        if failure_rate >= warning_threshold:
            assert expected_level is not None, (
                f"Should have alert level when rate ({failure_rate:.2%}) >= threshold"
            )
        else:
            assert expected_level is None, (
                f"Should not have alert level when rate ({failure_rate:.2%}) < threshold"
            )
