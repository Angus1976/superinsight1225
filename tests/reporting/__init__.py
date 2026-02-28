"""
Test Reporting and Analysis Module

Provides comprehensive test reporting capabilities:
- Test result aggregation from multiple sources
- Test failure analysis with error capture
- Coverage reporting with threshold validation
- Comprehensive test report generation

Requirements: 9.1-9.6, 14.1-14.7
"""

from .test_result_aggregation import (
    TestCategory,
    TestStatus,
    FailureType,
    TestResult,
    CoverageMetrics,
    PerformanceMetrics,
    Vulnerability,
    AggregatedTestResults,
    TestResultAggregator,
    aggregate_test_results,
)

from .test_failure_analysis import (
    FailureType as TestFailureType,
    Severity,
    ErrorDetails,
    LogCapture,
    E2EArtifacts,
    TestFailure,
    FailureSummaryReport,
    TestFailureAnalyzer,
    capture_test_failure,
)

from .coverage_reporting import (
    CoverageMetrics as CoverageMetricsReport,
    ModuleCoverage,
    CoverageThresholdResult,
    CoverageReporter,
    parse_coverage_report,
)

from .test_report_generator import (
    TestReport,
    TestReportGenerator,
    generate_comprehensive_test_report,
)

__all__ = [
    # Test result aggregation
    'TestCategory',
    'TestStatus',
    'FailureType',
    'TestResult',
    'CoverageMetrics',
    'PerformanceMetrics',
    'Vulnerability',
    'AggregatedTestResults',
    'TestResultAggregator',
    'aggregate_test_results',
    # Test failure analysis
    'TestFailureType',
    'Severity',
    'ErrorDetails',
    'LogCapture',
    'E2EArtifacts',
    'TestFailure',
    'FailureSummaryReport',
    'TestFailureAnalyzer',
    'capture_test_failure',
    # Coverage reporting
    'CoverageMetricsReport',
    'ModuleCoverage',
    'CoverageThresholdResult',
    'CoverageReporter',
    'parse_coverage_report',
    # Report generation
    'TestReport',
    'TestReportGenerator',
    'generate_comprehensive_test_report',
]