"""
Test Result Aggregation System

Aggregates test results from all test categories:
- Unit tests (pytest)
- Integration tests
- Property-based tests (Hypothesis)
- E2E tests (Playwright)
- Performance tests
- Security tests

Requirements: 9.5, 9.6, 14.1, 14.2
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import xml.etree.ElementTree as ET


class TestCategory(Enum):
    """Test category classification."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PROPERTY = "property"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DEPLOYMENT = "deployment"


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


class FailureType(Enum):
    """Test failure type categorization."""
    ASSERTION = "assertion"
    TIMEOUT = "timeout"
    INFRASTRUCTURE = "infrastructure"
    FLAKY = "flaky"


@dataclass
class TestResult:
    """Individual test result."""
    test_name: str
    category: TestCategory
    status: TestStatus
    duration: float  # seconds
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    failure_type: Optional[FailureType] = None
    module: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['category'] = self.category.value
        data['status'] = self.status.value
        if self.failure_type:
            data['failure_type'] = self.failure_type.value
        return data


@dataclass
class CoverageMetrics:
    """Code coverage metrics."""
    statement_coverage: float = 0.0
    branch_coverage: float = 0.0
    function_coverage: float = 0.0
    line_coverage: float = 0.0
    coverage_by_module: Dict[str, float] = field(default_factory=dict)
    untested_paths: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """Performance test metrics."""
    endpoint: str = ""
    concurrent_users: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_time_p50: float = 0.0
    response_time_p95: float = 0.0
    response_time_p99: float = 0.0
    throughput: float = 0.0
    error_rate: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


@dataclass
class Vulnerability:
    """Security vulnerability finding."""
    vulnerability_id: str
    title: str
    description: str
    severity: str  # critical, high, medium, low
    category: str
    affected_component: str
    remediation: str
    cve_id: Optional[str] = None
    discovered_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AggregatedTestResults:
    """Aggregated test results from all categories."""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    execution_time: float = 0.0
    execution_time_by_category: Dict[str, float] = field(default_factory=dict)
    results_by_category: Dict[str, List[TestResult]] = field(default_factory=dict)
    coverage_metrics: Optional[CoverageMetrics] = None
    performance_metrics: List[PerformanceMetrics] = field(default_factory=list)
    security_findings: List[Vulnerability] = field(default_factory=list)
    failures: List[TestResult] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def overall_status(self) -> TestStatus:
        """Determine overall test status."""
        if self.failed > 0 or self.errors > 0:
            return TestStatus.FAILED
        if self.skipped == self.total_tests:
            return TestStatus.SKIPPED
        return TestStatus.PASSED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'overall_status': self.overall_status.value,
            'total_tests': self.total_tests,
            'passed': self.passed,
            'failed': self.failed,
            'skipped': self.skipped,
            'errors': self.errors,
            'execution_time': self.execution_time,
            'execution_time_by_category': self.execution_time_by_category,
            'results_by_category': {
                cat: [r.to_dict() for r in results]
                for cat, results in self.results_by_category.items()
            },
            'coverage_metrics': self.coverage_metrics.to_dict() if self.coverage_metrics else None,
            'performance_metrics': [pm.to_dict() for pm in self.performance_metrics],
            'security_findings': [vf.to_dict() for vf in self.security_findings],
            'failures': [f.to_dict() for f in self.failures],
            'generated_at': self.generated_at.isoformat(),
        }


class TestResultAggregator:
    """Aggregates test results from multiple sources."""

    def __init__(self):
        self.results = AggregatedTestResults()

    def aggregate_pytest_results(
        self,
        pytest_output: Union[str, Path],
        category: TestCategory = TestCategory.UNIT
    ) -> List[TestResult]:
        """Aggregate results from pytest JSON output or XML report."""
        results = []

        if isinstance(pytest_output, (str, Path)):
            path = Path(pytest_output)
            if path.suffix == '.json':
                results.extend(self._parse_pytest_json(path, category))
            elif path.suffix == '.xml':
                results.extend(self._parse_pytest_xml(path, category))

        return results

    def _parse_pytest_json(self, path: Path, category: TestCategory) -> List[TestResult]:
        """Parse pytest JSON output."""
        results = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different pytest JSON formats
            if 'tests' in data:
                for test in data['tests']:
                    result = self._create_result_from_pytest_test(test, category)
                    results.append(result)
            elif 'report' in data:
                # New pytest-reportlog format
                for test in data.get('report', {}).get('tests', []):
                    result = self._create_result_from_pytest_test(test, category)
                    results.append(result)

        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error parsing pytest JSON: {e}")

        return results

    def _parse_pytest_xml(self, path: Path, category: TestCategory) -> List[TestResult]:
        """Parse pytest XML (JUnit) output."""
        results = []
        try:
            tree = ET.parse(path)
            root = tree.getroot()

            for testcase in root.findall('.//testcase'):
                result = self._create_result_from_junit(testcase, category)
                results.append(result)

        except ET.ParseError as e:
            print(f"Error parsing pytest XML: {e}")

        return results

    def _create_result_from_pytest_test(
        self, test: Dict[str, Any], category: TestCategory
    ) -> TestResult:
        """Create TestResult from pytest test dict."""
        status_str = test.get('status', 'passed')
        status = TestStatus.PASSED
        if status_str == 'failed':
            status = TestStatus.FAILED
        elif status_str == 'skipped':
            status = TestStatus.SKIPPED
        elif status_str == 'error':
            status = TestStatus.ERROR

        # Determine failure type
        failure_type = None
        if status == TestStatus.FAILED:
            failure_type = self._determine_failure_type(
                test.get('call', {}).get('longrepr', '')
            )

        return TestResult(
            test_name=test.get('name', test.get('test_id', 'unknown')),
            category=category,
            status=status,
            duration=test.get('duration', 0.0),
            error_message=test.get('call', {}).get('repr', {}).get('message'),
            stack_trace=test.get('call', {}).get('repr', {}).get('traceback'),
            timestamp=datetime.fromisoformat(test.get('start', datetime.now().isoformat())),
            failure_type=failure_type,
            module=test.get('module'),
            file_path=test.get('file'),
        )

    def _create_result_from_junit(
        self, testcase: ET.Element, category: TestCategory
    ) -> TestResult:
        """Create TestResult from JUnit testcase element."""
        name = testcase.get('name', 'unknown')
        time = float(testcase.get('time', '0'))

        status = TestStatus.PASSED
        error_message = None
        stack_trace = None
        failure_type = None

        # Check for failure or error elements
        failure = testcase.find('failure')
        error = testcase.find('error')
        skipped = testcase.find('skipped')

        if failure is not None:
            status = TestStatus.FAILED
            error_message = failure.get('message', '')
            stack_trace = failure.text or ''
            failure_type = FailureType.ASSERTION
        elif error is not None:
            status = TestStatus.ERROR
            error_message = error.get('message', '')
            stack_trace = error.text or ''
            failure_type = FailureType.INFRASTRUCTURE
        elif skipped is not None:
            status = TestStatus.SKIPPED

        return TestResult(
            test_name=name,
            category=category,
            status=status,
            duration=time,
            error_message=error_message,
            stack_trace=stack_trace,
            failure_type=failure_type,
            module=testcase.get('classname'),
            file_path=testcase.get('file'),
            line_number=int(testcase.get('line', 0)) if testcase.get('line') else None,
        )

    def _determine_failure_type(self, error_output: str) -> Optional[FailureType]:
        """Determine failure type from error output."""
        error_lower = error_output.lower() if error_output else ''

        if 'assertionerror' in error_lower or 'assert' in error_lower:
            return FailureType.ASSERTION
        elif 'timeout' in error_lower or 'timed out' in error_lower:
            return FailureType.TIMEOUT
        elif 'connection' in error_lower or 'database' in error_lower or 'redis' in error_lower:
            return FailureType.INFRASTRUCTURE
        else:
            # Default to assertion for unknown failures
            return FailureType.ASSERTION

    def aggregate_playwright_results(
        self, playwright_output: Union[str, Path]
    ) -> List[TestResult]:
        """Aggregate results from Playwright JSON output."""
        results = []

        if isinstance(playwright_output, (str, Path)):
            path = Path(playwright_output)
            if path.suffix == '.json':
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Handle Playwright JSON format
                    for suite in data.get('suites', []):
                        results.extend(self._parse_playwright_suite(suite))

                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"Error parsing Playwright JSON: {e}")

        return results

    def _parse_playwright_suite(self, suite: Dict[str, Any]) -> List[TestResult]:
        """Parse Playwright suite recursively."""
        results = []

        for spec in suite.get('specs', []):
            for test in spec.get('tests', []):
                result = self._create_result_from_playwright_test(test)
                results.append(result)

        for child_suite in suite.get('suites', []):
            results.extend(self._parse_playwright_suite(child_suite))

        return results

    def _create_result_from_playwright_test(self, test: Dict[str, Any]) -> TestResult:
        """Create TestResult from Playwright test."""
        status_str = test.get('status', 'passed')
        status = TestStatus.PASSED
        if status_str == 'failed':
            status = TestStatus.FAILED
        elif status_str == 'skipped':
            status = TestStatus.SKIPPED

        # Get error info from results
        error_message = None
        stack_trace = None
        artifacts = []

        for result in test.get('results', []):
            if result.get('status') == 'failed':
                error_message = result.get('error', {}).get('message', '')
                stack_trace = result.get('error', {}).get('stack', '')
                # Collect artifacts (screenshots, traces)
                for attachment in result.get('attachments', []):
                    if attachment.get('name'):
                        artifacts.append(attachment['name'])

        return TestResult(
            test_name=test.get('title', 'unknown'),
            category=TestCategory.E2E,
            status=status,
            duration=test.get('timeout', 0) / 1000.0,  # Convert ms to seconds
            error_message=error_message,
            stack_trace=stack_trace,
            artifacts=artifacts,
            failure_type=FailureType.ASSERTION if status == TestStatus.FAILED else None,
            file_path=test.get('file'),
        )

    def aggregate_vitest_results(
        self, vitest_output: Union[str, Path]
    ) -> List[TestResult]:
        """Aggregate results from vitest JSON output."""
        results = []

        if isinstance(vitest_output, (str, Path)):
            path = Path(vitest_output)
            if path.suffix == '.json':
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Handle vitest JSON format
                    for test in data.get('testResults', []):
                        results.extend(self._parse_vitest_test_result(test))

                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"Error parsing vitest JSON: {e}")

        return results

    def _parse_vitest_test_result(self, test_result: Dict[str, Any]) -> List[TestResult]:
        """Parse vitest test result."""
        results = []

        for assertion in test_result.get('assertionResults', []):
            status_str = assertion.get('status', 'passed')
            status = TestStatus.PASSED
            if status_str == 'failed':
                status = TestStatus.FAILED
            elif status_str == 'pending':
                status = TestStatus.SKIPPED

            failure_messages = assertion.get('failureMessages', [])

            results.append(TestResult(
                test_name=assertion.get('fullName', assertion.get('title', 'unknown')),
                category=TestCategory.UNIT,
                status=status,
                duration=assertion.get('duration', 0) / 1000.0,
                error_message=failure_messages[0] if failure_messages else None,
                stack_trace='\n'.join(failure_messages) if len(failure_messages) > 1 else None,
                failure_type=FailureType.ASSERTION if status == TestStatus.FAILED else None,
            ))

        return results

    def aggregate_coverage_report(self, coverage_output: Union[str, Path]) -> CoverageMetrics:
        """Aggregate coverage report from coverage.py JSON output."""
        metrics = CoverageMetrics()

        if isinstance(coverage_output, (str, Path)):
            path = Path(coverage_output)
            if path.suffix == '.json':
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Extract coverage totals
                    totals = data.get('totals', {})
                    metrics.statement_coverage = totals.get('percent_covered', 0)
                    metrics.line_coverage = totals.get('percent_covered', 0)

                    # Extract coverage by module
                    for file_data in data.get('files', []):
                        file_path = file_data.get('file_path', '')
                        file_coverage = file_data.get('percent_covered', 0)
                        module_name = Path(file_path).stem
                        metrics.coverage_by_module[module_name] = file_coverage

                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"Error parsing coverage JSON: {e}")

        return metrics

    def aggregate_all_results(
        self,
        pytest_results: Optional[Union[str, Path, List[Union[str, Path]]]] = None,
        playwright_results: Optional[Union[str, Path]] = None,
        vitest_results: Optional[Union[str, Path]] = None,
        coverage_report: Optional[Union[str, Path]] = None,
    ) -> AggregatedTestResults:
        """Aggregate all test results into a single report."""
        all_results: List[TestResult] = []

        # Aggregate pytest results
        if pytest_results:
            if isinstance(pytest_results, list):
                for result in pytest_results:
                    all_results.extend(self.aggregate_pytest_results(result))
            else:
                all_results.extend(self.aggregate_pytest_results(pytest_results))

        # Aggregate Playwright results
        if playwright_results:
            all_results.extend(self.aggregate_playwright_results(playwright_results))

        # Aggregate vitest results
        if vitest_results:
            all_results.extend(self.aggregate_vitest_results(vitest_results))

        # Aggregate coverage report
        if coverage_report:
            self.results.coverage_metrics = self.aggregate_coverage_report(coverage_report)

        # Categorize and aggregate results
        for result in all_results:
            category_key = result.category.value

            if category_key not in self.results.results_by_category:
                self.results.results_by_category[category_key] = []

            self.results.results_by_category[category_key].append(result)

            # Track execution time by category
            if category_key not in self.results.execution_time_by_category:
                self.results.execution_time_by_category[category_key] = 0.0
            self.results.execution_time_by_category[category_key] += result.duration

            # Track overall stats
            self.results.total_tests += 1
            if result.status == TestStatus.PASSED:
                self.results.passed += 1
            elif result.status == TestStatus.FAILED:
                self.results.failed += 1
                self.results.failures.append(result)
            elif result.status == TestStatus.SKIPPED:
                self.results.skipped += 1
            elif result.status == TestStatus.ERROR:
                self.results.errors += 1

        # Calculate total execution time
        self.results.execution_time = sum(self.results.execution_time_by_category.values())

        return self.results


def aggregate_test_results(
    pytest_output: Optional[Union[str, Path]] = None,
    playwright_output: Optional[Union[str, Path]] = None,
    vitest_output: Optional[Union[str, Path]] = None,
    coverage_output: Optional[Union[str, Path]] = None,
) -> AggregatedTestResults:
    """Convenience function to aggregate all test results."""
    aggregator = TestResultAggregator()
    return aggregator.aggregate_all_results(
        pytest_results=pytest_output,
        playwright_results=playwright_output,
        vitest_results=vitest_output,
        coverage_report=coverage_output,
    )