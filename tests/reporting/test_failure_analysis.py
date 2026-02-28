"""
Test Failure Analysis Module

Analyzes test failures with detailed error capture, log collection, and categorization.

Requirements: 1.3, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
Properties: 1, 8, 23, 24, 25
"""

import json
import os
import re
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET


class FailureType(Enum):
    """Categorization of test failure types."""
    ASSERTION = "assertion"
    TIMEOUT = "timeout"
    INFRASTRUCTURE = "infrastructure"
    FLAKY = "flaky"
    VALIDATION = "validation"
    PERMISSION = "permission"
    NETWORK = "network"
    DATABASE = "database"
    UNKNOWN = "unknown"


class Severity(Enum):
    """Severity level of a failure."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ErrorDetails:
    """Detailed error information."""
    error_type: str  # Exception class name
    error_message: str
    stack_trace: str
    exception_module: str = ""
    line_number: Optional[int] = None
    file_path: Optional[str] = None
    function_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'error_type': self.error_type,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'exception_module': self.exception_module,
            'line_number': self.line_number,
            'file_path': self.file_path,
            'function_name': self.function_name,
        }


@dataclass
class LogCapture:
    """Captured log output for a test failure."""
    logs: List[str] = field(default_factory=list)
    log_level: str = "INFO"
    captured_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'logs': self.logs,
            'log_level': self.log_level,
            'captured_at': self.captured_at.isoformat(),
        }


@dataclass
class E2EArtifacts:
    """Artifacts captured from E2E test failures."""
    screenshots: List[str] = field(default_factory=list)
    browser_console_logs: List[str] = field(default_factory=list)
    trace_files: List[str] = field(default_factory=list)
    html_dumps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'screenshots': self.screenshots,
            'browser_console_logs': self.browser_console_logs,
            'trace_files': self.trace_files,
            'html_dumps': self.html_dumps,
        }


@dataclass
class TestFailure:
    """Complete test failure information."""
    test_name: str
    test_file: str
    line_number: Optional[int]
    category: str  # unit, integration, e2e, performance, security
    error_details: ErrorDetails
    failure_type: FailureType
    severity: Severity
    log_capture: Optional[LogCapture] = None
    e2e_artifacts: Optional[E2EArtifacts] = None
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    is_flaky: bool = False
    related_failures: List['TestFailure'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'test_name': self.test_name,
            'test_file': self.test_file,
            'line_number': self.line_number,
            'category': self.category,
            'error_details': self.error_details.to_dict(),
            'failure_type': self.failure_type.value,
            'severity': self.severity.value,
            'log_capture': self.log_capture.to_dict() if self.log_capture else None,
            'e2e_artifacts': self.e2e_artifacts.to_dict() if self.e2e_artifacts else None,
            'timestamp': self.timestamp.isoformat(),
            'retry_count': self.retry_count,
            'is_flaky': self.is_flaky,
        }


@dataclass
class FailureSummaryReport:
    """Summary report of all test failures."""
    total_failures: int = 0
    failures_by_type: Dict[str, int] = field(default_factory=dict)
    failures_by_category: Dict[str, int] = field(default_factory=dict)
    failures_by_severity: Dict[str, int] = field(default_factory=dict)
    failures: List[TestFailure] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_failures': self.total_failures,
            'failures_by_type': self.failures_by_type,
            'failures_by_category': self.failures_by_category,
            'failures_by_severity': self.failures_by_severity,
            'failures': [f.to_dict() for f in self.failures],
            'recommendations': self.recommendations,
            'generated_at': self.generated_at.isoformat(),
        }


class TestFailureAnalyzer:
    """Analyzes test failures with detailed error capture and categorization."""

    # Error patterns for automatic failure type detection
    ERROR_PATTERNS = {
        FailureType.ASSERTION: [
            r'assertionerror',
            r'assert\s+',
            r'expected.*got',
            r'not equal',
            r'match',
        ],
        FailureType.TIMEOUT: [
            r'timeout',
            r'timed out',
            r'too much time',
            r'exceeded',
        ],
        FailureType.INFRASTRUCTURE: [
            r'connection.*refused',
            r'database.*error',
            r'redis.*error',
            r'oserror',
            r'importerror',
            r'modulenotfounderror',
        ],
        FailureType.VALIDATION: [
            r'validationerror',
            r'invalid.*value',
            r'value.*error',
            r'constraint',
            r'pydantic',
        ],
        FailureType.PERMISSION: [
            r'permission.*denied',
            r'unauthorized',
            r'forbidden',
            r'access.*denied',
        ],
        FailureType.NETWORK: [
            r'connection.*reset',
            r'network.*error',
            r'httperror',
            r'request.*failed',
        ],
        FailureType.DATABASE: [
            r'sql.*error',
            r'duplicate.*key',
            r'foreign.*key',
            r'integrity.*error',
            r'operational.*error',
        ],
    }

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = log_dir
        self.failures: List[TestFailure] = []

    def analyze_failure(
        self,
        test_name: str,
        test_file: str,
        error: Exception,
        category: str = "unit",
        log_output: Optional[List[str]] = None,
        e2e_artifacts: Optional[E2EArtifacts] = None,
    ) -> TestFailure:
        """Analyze a single test failure."""
        error_details = self._extract_error_details(error)
        failure_type = self._categorize_failure(error_details.error_message, error_details.stack_trace)
        severity = self._assess_severity(failure_type, error_details)

        log_capture = None
        if log_output:
            log_capture = LogCapture(logs=log_output)

        failure = TestFailure(
            test_name=test_name,
            test_file=test_file,
            line_number=error_details.line_number,
            category=category,
            error_details=error_details,
            failure_type=failure_type,
            severity=severity,
            log_capture=log_capture,
            e2e_artifacts=e2e_artifacts,
        )

        self.failures.append(failure)
        return failure

    def analyze_from_exception_info(
        self,
        test_name: str,
        test_file: str,
        exc_info: Tuple[type, BaseException, Any],
        category: str = "unit",
        log_output: Optional[List[str]] = None,
    ) -> TestFailure:
        """Analyze a failure from sys.exc_info tuple."""
        exc_type, exc_value, exc_tb = exc_info

        error_details = ErrorDetails(
            error_type=exc_type.__name__,
            error_message=str(exc_value),
            stack_trace=''.join(traceback.format_exception(exc_type, exc_value, exc_tb)),
            exception_module=exc_type.__module__,
        )

        # Extract line number and file from traceback
        tb = exc_tb
        while tb:
            frame = tb.tb_frame
            if test_file in str(frame.f_code.co_filename):
                error_details.line_number = tb.tb_lineno
                error_details.file_path = frame.f_code.co_filename
                error_details.function_name = frame.f_code.co_name
                break
            tb = tb.tb_next

        failure_type = self._categorize_failure(error_details.error_message, error_details.stack_trace)
        severity = self._assess_severity(failure_type, error_details)

        log_capture = None
        if log_output:
            log_capture = LogCapture(logs=log_output)

        failure = TestFailure(
            test_name=test_name,
            test_file=test_file,
            line_number=error_details.line_number,
            category=category,
            error_details=error_details,
            failure_type=failure_type,
            severity=severity,
            log_capture=log_capture,
        )

        self.failures.append(failure)
        return failure

    def _extract_error_details(self, error: Exception) -> ErrorDetails:
        """Extract detailed error information from an exception."""
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))

        # Extract line number from traceback
        line_number = None
        file_path = None
        function_name = None

        tb = error.__traceback__
        while tb:
            frame = tb.tb_frame
            if 'test' in str(frame.f_code.co_filename).lower():
                line_number = tb.tb_lineno
                file_path = frame.f_code.co_filename
                function_name = frame.f_code.co_name
                break
            tb = tb.tb_next

        return ErrorDetails(
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            exception_module=type(error).__module__,
            line_number=line_number,
            file_path=file_path,
            function_name=function_name,
        )

    def _categorize_failure(
        self, error_message: str, stack_trace: str
    ) -> FailureType:
        """Categorize failure type based on error patterns."""
        combined_text = f"{error_message} {stack_trace}".lower()

        for failure_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined_text):
                    return failure_type

        return FailureType.UNKNOWN

    def _assess_severity(
        self, failure_type: FailureType, error_details: ErrorDetails
    ) -> Severity:
        """Assess the severity of a failure."""
        # Infrastructure failures are typically more severe
        if failure_type in [FailureType.INFRASTRUCTURE, FailureType.DATABASE, FailureType.NETWORK]:
            return Severity.HIGH

        # Permission failures are critical
        if failure_type == FailureType.PERMISSION:
            return Severity.CRITICAL

        # Assertion failures in critical paths
        if 'auth' in error_details.error_message.lower() or 'login' in error_details.error_message.lower():
            return Severity.HIGH

        # Timeout failures are medium-high
        if failure_type == FailureType.TIMEOUT:
            return Severity.MEDIUM

        return Severity.LOW

    def analyze_pytest_failures(
        self, pytest_output: str
    ) -> List[TestFailure]:
        """Analyze failures from pytest output."""
        failures = []

        # Parse pytest JSON output if available
        try:
            import json
            data = json.loads(pytest_output)
            if 'tests' in data:
                for test in data['tests']:
                    if test.get('status') == 'failed':
                        failure = self._parse_pytest_test_failure(test)
                        if failure:
                            failures.append(failure)
        except (json.JSONDecodeError, TypeError):
            pass

        return failures

    def _parse_pytest_test_failure(self, test: Dict[str, Any]) -> Optional[TestFailure]:
        """Parse a single pytest test failure."""
        try:
            call = test.get('call', {})
            longrepr = call.get('longrepr', '')

            # Extract error info from longrepr
            error_type = "AssertionError"
            error_message = str(longrepr)

            if isinstance(longrepr, tuple):
                error_message = str(longrepr[0]) if longrepr else ""
                error_type = longrepr[1] if len(longrepr) > 1 else "Error"

            error_details = ErrorDetails(
                error_type=error_type,
                error_message=error_message,
                stack_trace=str(longrepr),
            )

            failure_type = self._categorize_failure(error_message, str(longrepr))
            severity = self._assess_severity(failure_type, error_details)

            return TestFailure(
                test_name=test.get('name', 'unknown'),
                test_file=test.get('file', ''),
                line_number=test.get('line'),
                category="unit",
                error_details=error_details,
                failure_type=failure_type,
                severity=severity,
            )
        except Exception:
            return None

    def analyze_playwright_failures(
        self, playwright_output: str
    ) -> List[TestFailure]:
        """Analyze failures from Playwright test output."""
        failures = []

        try:
            import json
            data = json.loads(playwright_output)

            for suite in data.get('suites', []):
                failures.extend(self._parse_playwright_suite_failures(suite))

        except (json.JSONDecodeError, TypeError):
            pass

        return failures

    def _parse_playwright_suite_failures(self, suite: Dict[str, Any]) -> List[TestFailure]:
        """Parse Playwright suite failures recursively."""
        failures = []

        for spec in suite.get('specs', []):
            for test in spec.get('tests', []):
                if test.get('status') == 'failed':
                    failure = self._parse_playwright_test_failure(test)
                    if failure:
                        failures.append(failure)

        for child_suite in suite.get('suites', []):
            failures.extend(self._parse_playwright_suite_failures(child_suite))

        return failures

    def _parse_playwright_test_failure(self, test: Dict[str, Any]) -> Optional[TestFailure]:
        """Parse a single Playwright test failure."""
        try:
            error_info = {}
            for result in test.get('results', []):
                if result.get('status') == 'failed':
                    error_info = result.get('error', {})

            error_details = ErrorDetails(
                error_type=error_info.get('name', 'Error'),
                error_message=error_info.get('message', ''),
                stack_trace=error_info.get('stack', ''),
            )

            failure_type = self._categorize_failure(
                error_details.error_message,
                error_details.stack_trace
            )
            severity = self._assess_severity(failure_type, error_details)

            # Collect E2E artifacts
            e2e_artifacts = E2EArtifacts()
            for result in test.get('results', []):
                for attachment in result.get('attachments', []):
                    name = attachment.get('name', '')
                    if 'screenshot' in name:
                        e2e_artifacts.screenshots.append(name)
                    elif 'trace' in name:
                        e2e_artifacts.trace_files.append(name)
                    elif 'console' in name:
                        e2e_artifacts.browser_console_logs.append(name)

            return TestFailure(
                test_name=test.get('title', 'unknown'),
                test_file=test.get('file', ''),
                line_number=test.get('line'),
                category="e2e",
                error_details=error_details,
                failure_type=failure_type,
                severity=severity,
                e2e_artifacts=e2e_artifacts,
            )
        except Exception:
            return None

    def generate_summary_report(self) -> FailureSummaryReport:
        """Generate a summary report of all analyzed failures."""
        report = FailureSummaryReport()

        for failure in self.failures:
            report.total_failures += 1

            # Count by type
            type_key = failure.failure_type.value
            report.failures_by_type[type_key] = report.failures_by_type.get(type_key, 0) + 1

            # Count by category
            cat_key = failure.category
            report.failures_by_category[cat_key] = report.failures_by_category.get(cat_key, 0) + 1

            # Count by severity
            sev_key = failure.severity.value
            report.failures_by_severity[sev_key] = report.failures_by_severity.get(sev_key, 0) + 1

            report.failures.append(failure)

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        return report

    def _generate_recommendations(self, report: FailureSummaryReport) -> List[str]:
        """Generate recommendations based on failure analysis."""
        recommendations = []

        # Infrastructure failures
        if report.failures_by_type.get('infrastructure', 0) > 0:
            recommendations.append(
                "Review infrastructure failures - check database and Redis connectivity"
            )

        # Timeout failures
        if report.failures_by_type.get('timeout', 0) > 0:
            recommendations.append(
                "Consider increasing test timeouts or optimizing slow operations"
            )

        # Assertion failures
        if report.failures_by_type.get('assertion', 0) > 0:
            recommendations.append(
                "Review assertion failures - check test expectations and test data"
            )

        # Flaky tests
        if report.failures_by_type.get('flaky', 0) > 0:
            recommendations.append(
                "Investigate and stabilize flaky tests - consider adding retries or fixing race conditions"
            )

        # E2E failures
        if report.failures_by_category.get('e2e', 0) > 0:
            recommendations.append(
                "Review E2E test failures - check for UI changes or timing issues"
            )

        # Critical severity failures
        if report.failures_by_severity.get('critical', 0) > 0:
            recommendations.append(
                "URGENT: Address all critical severity failures before deployment"
            )

        return recommendations

    def detect_flaky_tests(
        self, historical_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Detect flaky tests based on historical results."""
        test_runs: Dict[str, List[str]] = {}

        for result in historical_results:
            test_name = result.get('test_name', '')
            status = result.get('status', '')
            if test_name:
                if test_name not in test_runs:
                    test_runs[test_name] = []
                test_runs[test_name].append(status)

        flaky_tests = []
        for test_name, statuses in test_runs.items():
            if len(statuses) >= 2:
                unique_statuses = set(statuses)
                if len(unique_statuses) > 1:
                    # Test has both passed and failed
                    flaky_tests.append(test_name)

        return flaky_tests


def capture_test_failure(
    test_name: str,
    test_file: str,
    exc_info: Tuple[type, BaseException, Any],
    category: str = "unit",
    log_output: Optional[List[str]] = None,
) -> TestFailure:
    """Convenience function to capture a test failure."""
    analyzer = TestFailureAnalyzer()
    return analyzer.analyze_from_exception_info(
        test_name=test_name,
        test_file=test_file,
        exc_info=exc_info,
        category=category,
        log_output=log_output,
    )