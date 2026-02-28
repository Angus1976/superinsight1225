"""
Coverage Reporting Module

Generates coverage reports with module breakdown, threshold validation, and untested path identification.

Requirements: 1.5, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 14.3
Properties: 3, 19, 20, 36
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET


@dataclass
class CoverageMetrics:
    """Code coverage metrics."""
    statement_coverage: float = 0.0
    branch_coverage: float = 0.0
    function_coverage: float = 0.0
    line_coverage: float = 0.0
    coverage_by_module: Dict[str, float] = field(default_factory=dict)
    untested_paths: List[str] = field(default_factory=list)
    uncovered_lines: Dict[str, List[int]] = field(default_factory=dict)
    uncovered_branches: Dict[str, List[Tuple[int, int]]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'statement_coverage': self.statement_coverage,
            'branch_coverage': self.branch_coverage,
            'function_coverage': self.function_coverage,
            'line_coverage': self.line_coverage,
            'coverage_by_module': self.coverage_by_module,
            'untested_paths': self.untested_paths,
            'uncovered_lines': self.uncovered_lines,
            'uncovered_branches': self.uncovered_branches,
        }


@dataclass
class ModuleCoverage:
    """Coverage metrics for a single module."""
    module_name: str
    file_path: str
    statement_coverage: float
    branch_coverage: float
    function_coverage: float
    line_coverage: float
    total_statements: int = 0
    covered_statements: int = 0
    total_branches: int = 0
    covered_branches: int = 0
    total_functions: int = 0
    covered_functions: int = 0
    uncovered_lines: List[int] = field(default_factory=list)
    uncovered_branches: List[Tuple[int, int]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'module_name': self.module_name,
            'file_path': self.file_path,
            'statement_coverage': self.statement_coverage,
            'branch_coverage': self.branch_coverage,
            'function_coverage': self.function_coverage,
            'line_coverage': self.line_coverage,
            'total_statements': self.total_statements,
            'covered_statements': self.covered_statements,
            'total_branches': self.total_branches,
            'covered_branches': self.covered_branches,
            'total_functions': self.total_functions,
            'covered_functions': self.covered_functions,
            'uncovered_lines': self.uncovered_lines,
            'uncovered_branches': self.uncovered_branches,
        }


@dataclass
class CoverageThresholdResult:
    """Result of coverage threshold validation."""
    passed: bool
    threshold: float
    actual_coverage: float
    message: str
    failed_modules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'passed': self.passed,
            'threshold': self.threshold,
            'actual_coverage': self.actual_coverage,
            'message': self.message,
            'failed_modules': self.failed_modules,
        }


class CoverageReporter:
    """Generates and analyzes code coverage reports."""

    # Default coverage thresholds
    DEFAULT_STATEMENT_THRESHOLD = 80.0
    DEFAULT_BRANCH_THRESHOLD = 80.0
    DEFAULT_FUNCTION_THRESHOLD = 80.0
    DEFAULT_LINE_THRESHOLD = 80.0

    def __init__(
        self,
        statement_threshold: float = DEFAULT_STATEMENT_THRESHOLD,
        branch_threshold: float = DEFAULT_BRANCH_THRESHOLD,
        function_threshold: float = DEFAULT_FUNCTION_THRESHOLD,
        line_threshold: float = DEFAULT_LINE_THRESHOLD,
    ):
        self.thresholds = {
            'statement': statement_threshold,
            'branch': branch_threshold,
            'function': function_threshold,
            'line': line_threshold,
        }
        self.modules: List[ModuleCoverage] = []

    def parse_coverage_py_json(self, coverage_json: str) -> CoverageMetrics:
        """Parse coverage.py JSON output."""
        metrics = CoverageMetrics()

        try:
            with open(coverage_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract totals
            totals = data.get('totals', {})
            metrics.statement_coverage = totals.get('percent_covered', 0)
            metrics.branch_coverage = totals.get('branch_percent_covered', 0)
            metrics.function_coverage = totals.get('function_percent_covered', 0)
            metrics.line_coverage = totals.get('percent_covered', 0)

            # Extract per-file coverage
            for file_data in data.get('files', []):
                file_path = file_data.get('file_path', '')
                module_name = Path(file_path).stem

                # Calculate module coverage
                n_lines = file_data.get('num_lines', 0)
                n_executed = file_data.get('executed_lines', [])
                n_branches = file_data.get('branch_lines', [])
                n_executed_branches = file_data.get('executed_branches', [])

                module_coverage = (len(n_executed) / n_lines * 100) if n_lines > 0 else 0

                metrics.coverage_by_module[module_name] = module_coverage

                # Track uncovered lines
                all_lines = set(range(1, n_lines + 1))
                uncovered = sorted(list(all_lines - set(n_executed)))
                if uncovered:
                    metrics.uncovered_lines[module_name] = uncovered

                # Track uncovered branches
                if n_branches:
                    uncovered_branches = []
                    for i, branch in enumerate(n_branches):
                        if i not in n_executed_branches:
                            uncovered_branches.append(branch)
                    if uncovered_branches:
                        metrics.uncovered_branches[module_name] = uncovered_branches

        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error parsing coverage JSON: {e}")

        return metrics

    def parse_c8_json(self, c8_json: str) -> CoverageMetrics:
        """Parse c8 (Istanbul) JSON output for frontend."""
        metrics = CoverageMetrics()

        try:
            with open(c8_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract totals
            totals = data.get('total', {})
            metrics.statement_coverage = totals.get('coveredStatements', 0) / max(totals.get('totalStatements', 1), 1) * 100
            metrics.branch_coverage = totals.get('coveredBranches', 0) / max(totals.get('totalBranches', 1), 1) * 100
            metrics.function_coverage = totals.get('coveredFunctions', 0) / max(totals.get('totalFunctions', 1), 1) * 100
            metrics.line_coverage = totals.get('coveredLines', 0) / max(totals.get('totalLines', 1), 1) * 100

            # Extract per-file coverage
            for file_data in data.get('files', []):
                file_path = file_data.get('path', '')
                module_name = Path(file_path).stem

                # Calculate module coverage
                s = file_data.get('statement', {})
                module_coverage = s.get('pct', 0)

                metrics.coverage_by_module[module_name] = module_coverage

        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error parsing c8 JSON: {e}")

        return metrics

    def parse_cobertura_xml(self, xml_path: str) -> CoverageMetrics:
        """Parse Cobertura XML coverage report."""
        metrics = CoverageMetrics()

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Get overall coverage
            for coverage in root.findall('.//*[@line-rate]'):
                metrics.line_coverage = float(coverage.get('line-rate', 0)) * 100
                metrics.branch_coverage = float(coverage.get('branch-rate', 0)) * 100

            # Get per-class coverage
            for package in root.findall('.//package'):
                for clss in package.findall('.//class'):
                    name = clss.get('name', 'unknown')
                    line_rate = float(clss.get('line-rate', 0)) * 100
                    branch_rate = float(clss.get('branch-rate', 0)) * 100

                    metrics.coverage_by_module[name] = line_rate

        except ET.ParseError as e:
            print(f"Error parsing Cobertura XML: {e}")

        return metrics

    def combine_coverage_reports(
        self,
        backend_metrics: CoverageMetrics,
        frontend_metrics: CoverageMetrics,
    ) -> CoverageMetrics:
        """Combine backend and frontend coverage reports."""
        combined = CoverageMetrics()

        # Calculate weighted average
        backend_modules = len(backend_metrics.coverage_by_module)
        frontend_modules = len(frontend_metrics.coverage_by_module)
        total_modules = backend_modules + frontend_modules

        if total_modules > 0:
            backend_weight = backend_modules / total_modules
            frontend_weight = frontend_modules / total_modules

            combined.statement_coverage = (
                backend_metrics.statement_coverage * backend_weight +
                frontend_metrics.statement_coverage * frontend_weight
            )
            combined.branch_coverage = (
                backend_metrics.branch_coverage * backend_weight +
                frontend_metrics.branch_coverage * frontend_weight
            )
            combined.function_coverage = (
                backend_metrics.function_coverage * backend_weight +
                frontend_metrics.function_coverage * frontend_weight
            )
            combined.line_coverage = (
                backend_metrics.line_coverage * backend_weight +
                frontend_metrics.line_coverage * frontend_weight
            )

        # Combine module coverage
        combined.coverage_by_module = {
            f"backend/{k}": v for k, v in backend_metrics.coverage_by_module.items()
        }
        combined.coverage_by_module.update({
            f"frontend/{k}": v for k, v in frontend_metrics.coverage_by_module.items()
        })

        # Combine uncovered paths
        combined.uncovered_lines = backend_metrics.uncovered_lines.copy()
        combined.uncovered_lines.update(frontend_metrics.uncovered_lines)

        return combined

    def validate_thresholds(
        self, metrics: CoverageMetrics
    ) -> Dict[str, CoverageThresholdResult]:
        """Validate coverage against thresholds."""
        results = {}

        # Statement coverage
        results['statement'] = self._validate_threshold(
            'statement',
            metrics.statement_coverage,
            metrics.coverage_by_module,
        )

        # Branch coverage
        results['branch'] = self._validate_threshold(
            'branch',
            metrics.branch_coverage,
            metrics.coverage_by_module,
        )

        # Function coverage
        results['function'] = self._validate_threshold(
            'function',
            metrics.function_coverage,
            metrics.coverage_by_module,
        )

        # Line coverage
        results['line'] = self._validate_threshold(
            'line',
            metrics.line_coverage,
            metrics.coverage_by_module,
        )

        return results

    def _validate_threshold(
        self,
        coverage_type: str,
        overall_coverage: float,
        module_coverage: Dict[str, float],
    ) -> CoverageThresholdResult:
        """Validate a single coverage type against threshold."""
        threshold = self.thresholds.get(coverage_type, 80.0)
        passed = overall_coverage >= threshold

        failed_modules = [
            module for module, coverage in module_coverage.items()
            if coverage < threshold
        ]

        if passed:
            message = f"{coverage_type.capitalize()} coverage ({overall_coverage:.1f}%) meets threshold ({threshold}%)"
        else:
            message = f"{coverage_type.capitalize()} coverage ({overall_coverage:.1f}%) below threshold ({threshold}%)"

        return CoverageThresholdResult(
            passed=passed,
            threshold=threshold,
            actual_coverage=overall_coverage,
            message=message,
            failed_modules=failed_modules,
        )

    def identify_untested_paths(self, metrics: CoverageMetrics) -> List[str]:
        """Identify untested code paths from coverage data."""
        untested_paths = []

        for module, lines in metrics.uncovered_lines.items():
            if lines:
                # Group consecutive lines into path segments
                paths = self._group_lines_into_paths(lines)
                for path in paths:
                    untested_paths.append(f"{module}:{path}")

        # Add uncovered branches
        for module, branches in metrics.uncovered_branches.items():
            for branch in branches:
                untested_paths.append(f"{module}: Branch at line {branch[0]} not taken")

        return untested_paths

    def _group_lines_into_paths(self, lines: List[int]) -> List[str]:
        """Group consecutive line numbers into path descriptions."""
        if not lines:
            return []

        paths = []
        current_start = lines[0]
        current_end = lines[0]

        for line in lines[1:]:
            if line == current_end + 1:
                current_end = line
            else:
                # End current path segment
                if current_start == current_end:
                    paths.append(f"line {current_start}")
                else:
                    paths.append(f"lines {current_start}-{current_end}")
                current_start = line
                current_end = line

        # Add final path segment
        if current_start == current_end:
            paths.append(f"line {current_start}")
        else:
            paths.append(f"lines {current_start}-{current_end}")

        return paths

    def generate_module_report(self, metrics: CoverageMetrics) -> List[ModuleCoverage]:
        """Generate detailed report for each module."""
        modules = []

        for module_name, coverage in metrics.coverage_by_module.items():
            module = ModuleCoverage(
                module_name=module_name,
                file_path=module_name,
                statement_coverage=coverage,
                branch_coverage=metrics.branch_coverage,
                function_coverage=metrics.function_coverage,
                line_coverage=metrics.line_coverage,
            )

            # Add uncovered lines if available
            if module_name in metrics.uncovered_lines:
                module.uncovered_lines = metrics.uncovered_lines[module_name]

            modules.append(module)

        # Sort by coverage (lowest first - most need attention)
        modules.sort(key=lambda m: m.statement_coverage)

        return modules

    def check_coverage_threshold(
        self,
        metrics: CoverageMetrics,
        threshold: float = 80.0,
    ) -> Tuple[bool, str]:
        """Check if coverage meets threshold - returns (passed, message)."""
        if metrics.statement_coverage >= threshold:
            return True, f"Coverage ({metrics.statement_coverage:.1f}%) meets threshold ({threshold}%)"
        return False, f"Coverage ({metrics.statement_coverage:.1f}%) below threshold ({threshold}%)"

    def generate_html_report(
        self,
        metrics: CoverageMetrics,
        output_path: str,
        title: str = "Coverage Report",
    ) -> None:
        """Generate an HTML coverage report."""
        html_content = self._generate_html_content(metrics, title)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _generate_html_content(
        self,
        metrics: CoverageMetrics,
        title: str,
    ) -> str:
        """Generate HTML content for coverage report."""
        # Sort modules by coverage
        sorted_modules = sorted(
            metrics.coverage_by_module.items(),
            key=lambda x: x[1]
        )

        module_rows = ""
        for module_name, coverage in sorted_modules:
            coverage_class = "high" if coverage >= 80 else "medium" if coverage >= 50 else "low"
            module_rows += f"""
            <tr>
                <td>{module_name}</td>
                <td class="{coverage_class}">{coverage:.1f}%</td>
            </tr>
            """

        untested_paths_html = ""
        for path in metrics.untested_paths[:20]:  # Limit to 20 paths
            untested_paths_html += f"<li>{path}</li>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #333;
            margin-bottom: 20px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
        }}
        .metric .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .metric .value.high {{ color: #28a745; }}
        .metric .value.medium {{ color: #ffc107; }}
        .metric .value.low {{ color: #dc3545; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        .high {{ color: #28a745; }}
        .medium {{ color: #ffc107; }}
        .low {{ color: #dc3545; }}
        .untested {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .untested ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .timestamp {{
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>

        <div class="summary">
            <div class="metric">
                <h3>Statements</h3>
                <div class="value {'high' if metrics.statement_coverage >= 80 else 'medium' if metrics.statement_coverage >= 50 else 'low'}">
                    {metrics.statement_coverage:.1f}%
                </div>
            </div>
            <div class="metric">
                <h3>Branches</h3>
                <div class="value {'high' if metrics.branch_coverage >= 80 else 'medium' if metrics.branch_coverage >= 50 else 'low'}">
                    {metrics.branch_coverage:.1f}%
                </div>
            </div>
            <div class="metric">
                <h3>Functions</h3>
                <div class="value {'high' if metrics.function_coverage >= 80 else 'medium' if metrics.function_coverage >= 50 else 'low'}">
                    {metrics.function_coverage:.1f}%
                </div>
            </div>
            <div class="metric">
                <h3>Lines</h3>
                <div class="value {'high' if metrics.line_coverage >= 80 else 'medium' if metrics.line_coverage >= 50 else 'low'}">
                    {metrics.line_coverage:.1f}%
                </div>
            </div>
        </div>

        <h2>Coverage by Module</h2>
        <table>
            <thead>
                <tr>
                    <th>Module</th>
                    <th>Coverage</th>
                </tr>
            </thead>
            <tbody>
                {module_rows}
            </tbody>
        </table>

        <div class="untested">
            <h3>Untested Paths</h3>
            <ul>
                {untested_paths_html or '<li>No untested paths identified</li>'}
            </ul>
        </div>

        <div class="timestamp">
            Generated at {datetime.now().isoformat()}
        </div>
    </div>
</body>
</html>"""


def parse_coverage_report(
    coverage_file: str,
    coverage_format: str = "auto",
) -> CoverageMetrics:
    """Parse a coverage report file and return metrics."""
    reporter = CoverageReporter()

    if coverage_format == "auto":
        ext = Path(coverage_file).suffix.lower()
        if ext == ".json":
            # Try to detect if it's coverage.py or c8 format
            with open(coverage_file, 'r') as f:
                first_char = f.read(100).strip()
                if '"totals"' in first_char or '"files"' in first_char:
                    return reporter.parse_coverage_py_json(coverage_file)
                elif '"total"' in first_char or '"files"' in first_char:
                    return reporter.parse_c8_json(coverage_file)
        elif ext == ".xml":
            return reporter.parse_cobertura_xml(coverage_file)
    elif coverage_format == "coverage.py":
        return reporter.parse_coverage_py_json(coverage_file)
    elif coverage_format == "c8":
        return reporter.parse_c8_json(coverage_file)
    elif coverage_format == "cobertura":
        return reporter.parse_cobertura_xml(coverage_file)

    return CoverageMetrics()