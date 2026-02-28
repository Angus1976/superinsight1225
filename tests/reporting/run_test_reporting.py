#!/usr/bin/env python3
"""
Test Reporting Runner

Aggregates all test results and generates comprehensive reports.

Usage:
    python run_test_reporting.py --help
    python run_test_reporting.py --all
    python run_test_reporting.py --pytest results.json --playwright results.json --vitest results.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from reporting.test_result_aggregation import (
    TestResultAggregator,
    aggregate_test_results,
)
from reporting.test_failure_analysis import (
    TestFailureAnalyzer,
)
from reporting.coverage_reporting import (
    CoverageReporter,
)
from reporting.test_report_generator import (
    TestReportGenerator,
    generate_comprehensive_test_report,
)


def run_aggregation(
    pytest_results: Optional[str] = None,
    playwright_results: Optional[str] = None,
    vitest_results: Optional[str] = None,
    coverage_report: Optional[str] = None,
) -> Dict:
    """Run test result aggregation."""
    aggregator = TestResultAggregator()

    results = aggregator.aggregate_all_results(
        pytest_results=pytest_results,
        playwright_results=playwright_results,
        vitest_results=vitest_results,
        coverage_report=coverage_report,
    )

    return results.to_dict()


def run_failure_analysis(failures: List[Dict]) -> Dict:
    """Run failure analysis on test failures."""
    analyzer = TestFailureAnalyzer()

    for failure in failures:
        analyzer.analyze_failure(
            test_name=failure.get('test_name', 'unknown'),
            test_file=failure.get('test_file', ''),
            error=Exception(failure.get('error_message', 'Unknown error')),
            category=failure.get('category', 'unit'),
        )

    report = analyzer.generate_summary_report()
    return report.to_dict()


def run_coverage_analysis(
    coverage_file: str,
    threshold: float = 80.0,
) -> Dict:
    """Run coverage analysis."""
    reporter = CoverageReporter(statement_threshold=threshold)

    metrics = reporter.parse_coverage_report(coverage_file)
    validation = reporter.validate_thresholds(metrics)
    untested_paths = reporter.identify_untested_paths(metrics)

    return {
        'metrics': metrics.to_dict(),
        'validation': {k: v.to_dict() for k, v in validation.items()},
        'untested_paths': untested_paths,
        'threshold_check': reporter.check_coverage_threshold(metrics, threshold),
    }


def run_report_generation(
    test_results: Dict,
    output_dir: str = "test-reports",
    project_name: str = "SuperInsight",
    coverage_metrics: Optional[Dict] = None,
    performance_metrics: Optional[List[Dict]] = None,
    security_findings: Optional[List[Dict]] = None,
) -> str:
    """Generate comprehensive test report."""
    report = generate_comprehensive_test_report(
        test_results=test_results,
        output_dir=output_dir,
        project_name=project_name,
        coverage_metrics=coverage_metrics,
        performance_metrics=performance_metrics,
        security_findings=security_findings,
    )

    return f"Report generated: {output_dir}/test-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"


def main():
    parser = argparse.ArgumentParser(
        description="Test Reporting and Analysis Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Aggregate all test results
    python run_test_reporting.py --all

    # Aggregate specific test results
    python run_test_reporting.py --pytest results.json --playwright results.json

    # Run full analysis with coverage
    python run_test_reporting.py --all --coverage coverage.json --threshold 80

    # Generate report only
    python run_test_reporting.py --report-only --input results.json
        """,
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all analysis (aggregation, failure analysis, coverage)',
    )

    parser.add_argument(
        '--pytest',
        type=str,
        help='Path to pytest JSON results',
    )

    parser.add_argument(
        '--playwright',
        type=str,
        help='Path to Playwright JSON results',
    )

    parser.add_argument(
        '--vitest',
        type=str,
        help='Path to vitest JSON results',
    )

    parser.add_argument(
        '--coverage',
        type=str,
        help='Path to coverage JSON report',
    )

    parser.add_argument(
        '--threshold',
        type=float,
        default=80.0,
        help='Coverage threshold (default: 80.0)',
    )

    parser.add_argument(
        '--output',
        type=str,
        default='test-reports',
        help='Output directory for reports (default: test-reports)',
    )

    parser.add_argument(
        '--project',
        type=str,
        default='SuperInsight',
        help='Project name for report (default: SuperInsight)',
    )

    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Generate report from existing results file',
    )

    parser.add_argument(
        '--input',
        type=str,
        help='Input JSON file with aggregated results',
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON',
    )

    args = parser.parse_args()

    if not any([args.all, args.pytest, args.playwright, args.vitest, args.report_only]):
        parser.print_help()
        return 0

    results = {}

    if args.report_only and args.input:
        # Load existing results
        with open(args.input, 'r') as f:
            results = json.load(f)
    elif args.all or any([args.pytest, args.playwright, args.vitest]):
        # Aggregate test results
        aggregation = run_aggregation(
            pytest_results=args.pytest,
            playwright_results=args.playwright,
            vitest_results=args.vitest,
            coverage_report=args.coverage,
        )
        results['aggregation'] = aggregation

        # Run failure analysis on failures
        if aggregation.get('failures'):
            failure_results = run_failure_analysis(aggregation['failures'])
            results['failures'] = failure_results

        # Run coverage analysis
        if args.coverage:
            coverage_results = run_coverage_analysis(args.coverage, args.threshold)
            results['coverage'] = coverage_results

    # Generate report
    if results:
        report = run_report_generation(
            test_results=results.get('aggregation', {}),
            output_dir=args.output,
            project_name=args.project,
            coverage_metrics=results.get('coverage', {}).get('metrics'),
        )
        print(report)

    # Output JSON if requested
    if args.json and results:
        print(json.dumps(results, indent=2, default=str))

    return 0


if __name__ == '__main__':
    sys.exit(main())