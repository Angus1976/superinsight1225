"""
Comprehensive Test Report Generator

Generates HTML and JSON test reports with:
- Overall pass/fail status
- Execution times by category
- Coverage metrics by module
- Performance metrics with trends
- Security vulnerability summary
- Quality improvement recommendations

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7
Properties: 34, 35, 36, 37, 38, 39, 40
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET


@dataclass
class TestReport:
    """Comprehensive test report."""
    overall_status: str  # passed, failed, skipped
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    execution_time: float
    execution_time_by_category: Dict[str, float]
    coverage_metrics: Optional[Dict[str, Any]] = None
    performance_metrics: List[Dict[str, Any]] = field(default_factory=list)
    security_findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    test_trends: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_status': self.overall_status,
            'total_tests': self.total_tests,
            'passed': self.passed,
            'failed': self.failed,
            'skipped': self.skipped,
            'errors': self.errors,
            'execution_time': self.execution_time,
            'execution_time_by_category': self.execution_time_by_category,
            'coverage_metrics': self.coverage_metrics,
            'performance_metrics': self.performance_metrics,
            'security_findings': self.security_findings,
            'recommendations': self.recommendations,
            'generated_at': self.generated_at.isoformat(),
            'test_trends': self.test_trends,
        }


class TestReportGenerator:
    """Generates comprehensive test reports in HTML and JSON formats."""

    def __init__(self, project_name: str = "SuperInsight"):
        self.project_name = project_name
        self.report = TestReport(
            overall_status="unknown",
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
            errors=0,
            execution_time=0.0,
            execution_time_by_category={},
        )

    def generate_from_aggregated_results(
        self,
        aggregated_results: Any,
    ) -> TestReport:
        """Generate report from aggregated test results."""
        # Map aggregated results to report
        self.report.total_tests = aggregated_results.total_tests
        self.report.passed = aggregated_results.passed
        self.report.failed = aggregated_results.failed
        self.report.skipped = aggregated_results.skipped
        self.report.errors = aggregated_results.errors
        self.report.execution_time = aggregated_results.execution_time
        self.report.execution_time_by_category = aggregated_results.execution_time_by_category

        # Set overall status
        if self.report.failed > 0 or self.report.errors > 0:
            self.report.overall_status = "failed"
        elif self.report.skipped == self.report.total_tests:
            self.report.overall_status = "skipped"
        else:
            self.report.overall_status = "passed"

        # Add coverage metrics
        if aggregated_results.coverage_metrics:
            self.report.coverage_metrics = aggregated_results.coverage_metrics.to_dict()

        # Add performance metrics
        self.report.performance_metrics = [
            pm.to_dict() for pm in aggregated_results.performance_metrics
        ]

        # Add security findings
        self.report.security_findings = [
            vf.to_dict() for vf in aggregated_results.security_findings
        ]

        # Generate recommendations
        self.report.recommendations = self._generate_recommendations()

        return self.report

    def _generate_recommendations(self) -> List[str]:
        """Generate quality improvement recommendations."""
        recommendations = []

        # Coverage recommendations
        if self.report.coverage_metrics:
            coverage = self.report.coverage_metrics.get('statement_coverage', 0)
            if coverage < 80:
                recommendations.append(
                    f"Coverage is at {coverage:.1f}%. Aim for at least 80% coverage."
                )

        # Failure recommendations
        if self.report.failed > 0:
            recommendations.append(
                f"Review and fix {self.report.failed} failing tests before deployment."
            )

        # Error recommendations
        if self.report.errors > 0:
            recommendations.append(
                f"Investigate {self.report.errors} test errors - may indicate infrastructure issues."
            )

        # Performance recommendations
        if self.report.performance_metrics:
            slow_endpoints = [
                pm['endpoint'] for pm in self.report.performance_metrics
                if pm.get('response_time_p95', 0) > 500
            ]
            if slow_endpoints:
                recommendations.append(
                    f"Optimize slow endpoints: {', '.join(slow_endpoints)} (p95 > 500ms)"
                )

        # Security recommendations
        critical_vulns = [
            f['title'] for f in self.report.security_findings
            if f.get('severity') == 'critical'
        ]
        if critical_vulns:
            recommendations.append(
                f"URGENT: Address {len(critical_vulns)} critical security vulnerabilities"
            )

        return recommendations

    def export_json(self, output_path: str) -> None:
        """Export report as JSON."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.report.to_dict(), f, indent=2, ensure_ascii=False)

    def export_html(self, output_path: str) -> None:
        """Export report as HTML."""
        html_content = self._generate_html_content()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _generate_html_content(self) -> str:
        """Generate HTML content for the report."""
        # Status badge
        status_class = {
            'passed': 'success',
            'failed': 'danger',
            'skipped': 'warning',
            'unknown': 'secondary',
        }.get(self.report.overall_status, 'secondary')

        # Category breakdown
        category_rows = ""
        for category, time in sorted(self.report.execution_time_by_category.items()):
            category_rows += f"""
            <tr>
                <td>{category.upper()}</td>
                <td>{time:.2f}s</td>
            </tr>
            """

        # Coverage section
        coverage_section = ""
        if self.report.coverage_metrics:
            cov = self.report.coverage_metrics
            coverage_section = f"""
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Code Coverage</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="coverage-metric">
                                <div class="metric-value">{cov.get('statement_coverage', 0):.1f}%</div>
                                <div class="metric-label">Statements</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="coverage-metric">
                                <div class="metric-value">{cov.get('branch_coverage', 0):.1f}%</div>
                                <div class="metric-label">Branches</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="coverage-metric">
                                <div class="metric-value">{cov.get('function_coverage', 0):.1f}%</div>
                                <div class="metric-label">Functions</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="coverage-metric">
                                <div class="metric-value">{cov.get('line_coverage', 0):.1f}%</div>
                                <div class="metric-label">Lines</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """

        # Performance section
        perf_section = ""
        if self.report.performance_metrics:
            perf_rows = ""
            for pm in self.report.performance_metrics[:10]:  # Limit to 10
                perf_rows += f"""
                <tr>
                    <td>{pm.get('endpoint', 'N/A')}</td>
                    <td>{pm.get('concurrent_users', 0)}</td>
                    <td>{pm.get('response_time_p50', 0):.0f}ms</td>
                    <td>{pm.get('response_time_p95', 0):.0f}ms</td>
                    <td>{pm.get('response_time_p99', 0):.0f}ms</td>
                    <td>{pm.get('throughput', 0):.1f}/s</td>
                </tr>
                """
            perf_section = f"""
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Performance Metrics</h5>
                </div>
                <div class="card-body">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Endpoint</th>
                                <th>Users</th>
                                <th>p50</th>
                                <th>p95</th>
                                <th>p99</th>
                                <th>Throughput</th>
                            </tr>
                        </thead>
                        <tbody>
                            {perf_rows or '<tr><td colspan="6">No performance data</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
            """

        # Security section
        security_section = ""
        if self.report.security_findings:
            severity_colors = {
                'critical': 'danger',
                'high': 'warning',
                'medium': 'info',
                'low': 'secondary',
            }
            security_rows = ""
            for vuln in self.report.security_findings[:10]:  # Limit to 10
                color = severity_colors.get(vuln.get('severity', 'low'), 'secondary')
                security_rows += f"""
                <tr>
                    <td><span class="badge bg-{color}">{vuln.get('severity', 'unknown')}</span></td>
                    <td>{vuln.get('title', 'N/A')}</td>
                    <td>{vuln.get('category', 'N/A')}</td>
                    <td>{vuln.get('affected_component', 'N/A')}</td>
                </tr>
                """
            security_section = f"""
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Security Findings ({len(self.report.security_findings)} total)</h5>
                </div>
                <div class="card-body">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Severity</th>
                                <th>Title</th>
                                <th>Category</th>
                                <th>Component</th>
                            </tr>
                        </thead>
                        <tbody>
                            {security_rows}
                        </tbody>
                    </table>
                </div>
            </div>
            """

        # Recommendations section
        recommendations_section = ""
        if self.report.recommendations:
            rec_items = ""
            for rec in self.report.recommendations:
                rec_items += f"<li>{rec}</li>"
            recommendations_section = f"""
            <div class="card mb-4">
                <div class="card-header bg-warning">
                    <h5 class="mb-0">Recommendations</h5>
                </div>
                <div class="card-body">
                    <ul class="mb-0">
                        {rec_items}
                    </ul>
                </div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.project_name} - Test Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8f9fa;
            padding: 20px;
        }}
        .report-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .status-badge {{
            font-size: 1.2rem;
            padding: 10px 20px;
        }}
        .stat-card {{
            text-align: center;
            padding: 20px;
            border-radius: 10px;
            color: white;
        }}
        .stat-card.success {{ background: #28a745; }}
        .stat-card.danger {{ background: #dc3545; }}
        .stat-card.warning {{ background: #ffc107; color: #333; }}
        .stat-card.info {{ background: #17a2b8; }}
        .stat-card.secondary {{ background: #6c757d; }}
        .coverage-metric {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #333;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9rem;
        }}
        .card {{
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card-header {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        .table {{
            margin-bottom: 0;
        }}
        .table th {{
            background: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="report-header">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h1 class="mb-2">{self.project_name}</h1>
                    <p class="mb-0">Comprehensive Test Report</p>
                </div>
                <div class="text-end">
                    <span class="badge bg-{status_class} status-badge">{self.report.overall_status.upper()}</span>
                    <p class="mt-2 mb-0">Generated: {self.report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-md-2">
                <div class="stat-card {'success' if self.report.overall_status == 'passed' else 'danger' if self.report.overall_status == 'failed' else 'secondary'}">
                    <div class="stat-value">{self.report.total_tests}</div>
                    <div>Total Tests</div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="stat-card success">
                    <div class="stat-value">{self.report.passed}</div>
                    <div>Passed</div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="stat-card danger">
                    <div class="stat-value">{self.report.failed}</div>
                    <div>Failed</div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="stat-card warning">
                    <div class="stat-value">{self.report.skipped}</div>
                    <div>Skipped</div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="stat-card info">
                    <div class="stat-value">{self.report.errors}</div>
                    <div>Errors</div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="stat-card secondary">
                    <div class="stat-value">{self.report.execution_time:.1f}s</div>
                    <div>Duration</div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Execution Time by Category</h5>
                    </div>
                    <div class="card-body">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Category</th>
                                    <th>Duration</th>
                                </tr>
                            </thead>
                            <tbody>
                                {category_rows or '<tr><td colspan="2">No data</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Test Results Distribution</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="resultsChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        {coverage_section}
        {perf_section}
        {security_section}
        {recommendations_section}

        <div class="text-center text-muted mt-4">
            <small>Report generated by SuperInsight Test Reporting System</small>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Results distribution chart
        const ctx = document.getElementById('resultsChart').getContext('2d');
        new Chart(ctx, {{
            type: 'doughnut',
            data: {{
                labels: ['Passed', 'Failed', 'Skipped', 'Errors'],
                datasets: [{{
                    data: [{self.report.passed}, {self.report.failed}, {self.report.skipped}, {self.report.errors}],
                    backgroundColor: ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

    def generate_summary_report(
        self,
        test_results: Dict[str, Any],
        coverage_metrics: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[List[Dict[str, Any]]] = None,
        security_findings: Optional[List[Dict[str, Any]]] = None,
    ) -> TestReport:
        """Generate a summary report from raw test results."""
        # Calculate summary stats
        self.report.total_tests = test_results.get('total', 0)
        self.report.passed = test_results.get('passed', 0)
        self.report.failed = test_results.get('failed', 0)
        self.report.skipped = test_results.get('skipped', 0)
        self.report.errors = test_results.get('errors', 0)
        self.report.execution_time = test_results.get('duration', 0.0)
        self.report.execution_time_by_category = test_results.get('duration_by_category', {})

        # Set overall status
        if self.report.failed > 0 or self.report.errors > 0:
            self.report.overall_status = "failed"
        elif self.report.skipped == self.report.total_tests:
            self.report.overall_status = "skipped"
        else:
            self.report.overall_status = "passed"

        # Add optional metrics
        if coverage_metrics:
            self.report.coverage_metrics = coverage_metrics

        if performance_metrics:
            self.report.performance_metrics = performance_metrics

        if security_findings:
            self.report.security_findings = security_findings

        # Generate recommendations
        self.report.recommendations = self._generate_recommendations()

        return self.report


def generate_comprehensive_test_report(
    test_results: Dict[str, Any],
    output_dir: str = "test-reports",
    project_name: str = "SuperInsight",
    coverage_metrics: Optional[Dict[str, Any]] = None,
    performance_metrics: Optional[List[Dict[str, Any]]] = None,
    security_findings: Optional[List[Dict[str, Any]]] = None,
) -> TestReport:
    """Generate and export comprehensive test report."""
    generator = TestReportGenerator(project_name)

    report = generator.generate_summary_report(
        test_results=test_results,
        coverage_metrics=coverage_metrics,
        performance_metrics=performance_metrics,
        security_findings=security_findings,
    )

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Export both formats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = Path(output_dir) / f"test-report-{timestamp}.json"
    generator.export_json(str(json_path))

    html_path = Path(output_dir) / f"test-report-{timestamp}.html"
    generator.export_html(str(html_path))

    return report