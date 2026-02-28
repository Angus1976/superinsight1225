"""
Performance Threshold Validation and Benchmarking Module.

This module provides threshold checking, baseline comparison, and
performance degradation detection for the SuperInsight platform.

**Validates: Requirements 5.6, 13.5, 13.6**
**Validates: Properties 17, 32, 33**
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# =============================================================================
# Threshold Definitions
# =============================================================================

@dataclass
class ThresholdConfig:
    """Configuration for performance thresholds."""
    # Response time thresholds (P95 in milliseconds)
    p95_threshold_ms: float = 500.0
    p99_threshold_ms: float = 1000.0
    p50_threshold_ms: float = 200.0
    
    # Error rate thresholds
    error_rate_threshold: float = 0.01  # 1%
    critical_error_rate_threshold: float = 0.05  # 5%
    
    # Throughput thresholds
    min_throughput_rps: float = 50.0
    
    # Degradation thresholds
    performance_degradation_threshold: float = 0.20  # 20%
    
    # Critical endpoints with custom thresholds
    critical_endpoints: Dict[str, float] = field(default_factory=lambda: {
        "GET /health": 100.0,
        "POST /api/v1/auth/login": 200.0,
        "POST /api/v1/auth/register": 300.0,
        "GET /api/v1/tasks": 300.0,
        "POST /api/v1/tasks": 500.0,
        "GET /api/v1/annotations": 300.0,
        "POST /api/v1/annotations": 500.0,
        "GET /api/v1/exports": 300.0,
        "POST /api/v1/exports": 500.0,
    })


# =============================================================================
# Threshold Validation
# =============================================================================

class ThresholdValidator:
    """Validates performance metrics against defined thresholds."""
    
    def __init__(self, config: ThresholdConfig = None):
        self.config = config or ThresholdConfig()
    
    def validate_endpoint(
        self,
        endpoint: str,
        p95_ms: float,
        error_rate: float = 0.0,
        throughput_rps: float = 0.0
    ) -> Tuple[bool, List[str]]:
        """
        Validate a single endpoint against thresholds.
        
        Args:
            endpoint: Endpoint identifier (e.g., "GET /api/v1/tasks")
            p95_ms: P95 response time in milliseconds
            error_rate: Error rate as decimal (0.01 = 1%)
            throughput_rps: Throughput in requests per second
            
        Returns:
            Tuple of (passed, list of violations)
        """
        violations = []
        
        # Check critical endpoint threshold
        if endpoint in self.config.critical_endpoints:
            threshold = self.config.critical_endpoints[endpoint]
            if p95_ms > threshold:
                violations.append(
                    f"{endpoint}: P95={p95_ms:.2f}ms exceeds critical threshold {threshold}ms"
                )
        else:
            # Use general threshold
            if p95_ms > self.config.p95_threshold_ms:
                violations.append(
                    f"{endpoint}: P95={p95_ms:.2f}ms exceeds general threshold {self.config.p95_threshold_ms}ms"
                )
        
        # Check error rate
        if error_rate > self.config.error_rate_threshold:
            violations.append(
                f"{endpoint}: Error rate={error_rate:.2%} exceeds threshold {self.config.error_rate_threshold:.2%}"
            )
        
        # Check throughput
        if throughput_rps > 0 and throughput_rps < self.config.min_throughput_rps:
            violations.append(
                f"{endpoint}: Throughput={throughput_rps:.1f} req/s below minimum {self.config.min_throughput_rps} req/s"
            )
        
        return len(violations) == 0, violations
    
    def validate_report(self, report: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a complete performance report.
        
        Args:
            report: Performance report dictionary
            
        Returns:
            Tuple of (passed, list of violations)
        """
        all_violations = []
        
        endpoints = report.get("endpoints", {})
        for key, data in endpoints.items():
            endpoint = f"{data.get('method', 'GET')} {data.get('endpoint', key)}"
            passed, violations = self.validate_endpoint(
                endpoint=endpoint,
                p95_ms=data.get("p95_ms", 0),
                error_rate=data.get("error_rate", 0),
                throughput_rps=data.get("throughput_rps", 0)
            )
            all_violations.extend(violations)
        
        return len(all_violations) == 0, all_violations


# =============================================================================
# Baseline Management
# =============================================================================

class BaselineManager:
    """Manages performance baselines for comparison."""
    
    def __init__(self, baseline_dir: str = "tests/performance/baselines"):
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
    
    def save_baseline(
        self,
        name: str,
        metrics: Dict[str, Any]
    ) -> str:
        """
        Save current metrics as a baseline.
        
        Args:
            name: Name of the baseline
            metrics: Performance metrics dictionary
            
        Returns:
            Path to saved baseline file
        """
        baseline = {
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
            "metrics": metrics
        }
        
        filepath = self.baseline_dir / f"{name}.json"
        with open(filepath, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        return str(filepath)
    
    def load_baseline(self, name: str) -> Optional[Dict]:
        """
        Load a baseline by name.
        
        Args:
            name: Name of the baseline
            
        Returns:
            Baseline dictionary or None if not found
        """
        filepath = self.baseline_dir / f"{name}.json"
        
        if not filepath.exists():
            return None
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def list_baselines(self) -> List[Dict]:
        """List all available baselines."""
        baselines = []
        
        for filepath in self.baseline_dir.glob("*.json"):
            with open(filepath, 'r') as f:
                data = json.load(f)
                baselines.append({
                    "name": data.get("name", filepath.stem),
                    "created_at": data.get("created_at"),
                    "filepath": str(filepath)
                })
        
        return sorted(baselines, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def delete_baseline(self, name: str) -> bool:
        """Delete a baseline by name."""
        filepath = self.baseline_dir / f"{name}.json"
        
        if filepath.exists():
            filepath.unlink()
            return True
        return False


# =============================================================================
# Performance Comparison
# =============================================================================

class PerformanceComparator:
    """Compares current performance against baselines."""
    
    def __init__(self, baseline_manager: BaselineManager = None):
        self.baseline_manager = baseline_manager or BaselineManager()
        self.degradation_threshold = 0.20  # 20%
    
    def compare(
        self,
        current_metrics: Dict[str, Any],
        baseline_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Compare current metrics against a baseline.
        
        Args:
            current_metrics: Current performance metrics
            baseline_name: Name of baseline to compare against
            
        Returns:
            Comparison results dictionary
        """
        baseline = self.baseline_manager.load_baseline(baseline_name)
        
        if not baseline:
            return {
                "error": f"Baseline '{baseline_name}' not found",
                "available_baselines": [b["name"] for b in self.baseline_manager.list_baselines()]
            }
        
        baseline_metrics = baseline.get("metrics", {})
        comparison = {
            "baseline_name": baseline_name,
            "baseline_created_at": baseline.get("created_at"),
            "comparison_time": datetime.utcnow().isoformat(),
            "endpoint_comparisons": [],
            "database_comparisons": [],
            "degradations": [],
            "improvements": [],
            "summary": {
                "total_endpoints": 0,
                "passed": 0,
                "failed": 0,
                "avg_degradation_percent": 0,
            }
        }
        
        # Compare endpoints
        current_endpoints = current_metrics.get("endpoints", {})
        baseline_endpoints = baseline_metrics.get("endpoints", {})
        
        total_degradation = 0
        passed_count = 0
        failed_count = 0
        
        for key, current in current_endpoints.items():
            if key in baseline_endpoints:
                base = baseline_endpoints[key]
                
                base_p95 = base.get("p95_ms", 0)
                current_p95 = current.get("p95_ms", 0)
                
                if base_p95 > 0:
                    degradation = (current_p95 - base_p95) / base_p95
                else:
                    degradation = 0 if current_p95 == 0 else 1.0
                
                endpoint_comparison = {
                    "endpoint": key,
                    "baseline_p95_ms": base_p95,
                    "current_p95_ms": current_p95,
                    "degradation_percent": round(degradation * 100, 2),
                    "passed": degradation <= self.degradation_threshold,
                }
                
                comparison["endpoint_comparisons"].append(endpoint_comparison)
                
                total_degradation += degradation
                
                if degradation <= self.degradation_threshold:
                    passed_count += 1
                    if degradation < -0.10:  # 10% improvement
                        comparison["improvements"].append(endpoint_comparison)
                else:
                    failed_count += 1
                    comparison["degradations"].append(endpoint_comparison)
        
        # Compare database metrics
        current_db = current_metrics.get("database_metrics", {})
        baseline_db = baseline_metrics.get("database_metrics", {})
        
        for key, current in current_db.items():
            if key in baseline_db:
                base = baseline_db[key]
                
                base_avg = base.get("avg_time_ms", 0)
                current_avg = current.get("avg_time_ms", 0)
                
                if base_avg > 0:
                    degradation = (current_avg - base_avg) / base_avg
                else:
                    degradation = 0 if current_avg == 0 else 1.0
                
                comparison["database_comparisons"].append({
                    "query": key,
                    "baseline_avg_ms": base_avg,
                    "current_avg_ms": current_avg,
                    "degradation_percent": round(degradation * 100, 2),
                    "passed": degradation <= self.degradation_threshold,
                })
        
        # Summary
        total = passed_count + failed_count
        comparison["summary"] = {
            "total_endpoints": total,
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate": round(passed_count / total * 100, 2) if total > 0 else 100,
            "avg_degradation_percent": round(
                (total_degradation / total * 100) if total > 0 else 0, 2
            ),
            "passed_all": failed_count == 0,
        }
        
        return comparison
    
    def check_degradation(
        self,
        current_metrics: Dict[str, Any],
        baseline_name: str = "default"
    ) -> Tuple[bool, List[str]]:
        """
        Check if performance has degraded beyond threshold.
        
        Args:
            current_metrics: Current performance metrics
            baseline_name: Name of baseline to compare against
            
        Returns:
            Tuple of (passed, list of degradation issues)
        """
        comparison = self.compare(current_metrics, baseline_name)
        
        if "error" in comparison:
            return True, []  # No degradation if baseline not found
        
        issues = []
        passed = True
        
        for endpoint in comparison.get("degradations", []):
            issues.append(
                f"{endpoint['endpoint']}: Degraded by {endpoint['degradation_percent']:.1f}% "
                f"({endpoint['baseline_p95_ms']:.1f}ms → {endpoint['current_p95_ms']:.1f}ms)"
            )
            passed = False
        
        for db in comparison.get("database_comparisons", []):
            if not db.get("passed", True):
                issues.append(
                    f"Database query {db['query']}: Degraded by {db['degradation_percent']:.1f}%"
                )
                passed = False
        
        return passed, issues


# =============================================================================
# Performance Report Generator
# =============================================================================

class PerformanceReportGenerator:
    """Generates comprehensive performance reports."""
    
    def __init__(
        self,
        threshold_config: ThresholdConfig = None,
        baseline_manager: BaselineManager = None,
        comparator: PerformanceComparator = None
    ):
        self.threshold_config = threshold_config or ThresholdConfig()
        self.baseline_manager = baseline_manager or BaselineManager()
        self.comparator = comparator or PerformanceComparator(self.baseline_manager)
        self.validator = ThresholdValidator(self.threshold_config)
    
    def generate_report(
        self,
        metrics: Dict[str, Any],
        baseline_name: str = None,
        test_name: str = "performance_test"
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report.
        
        Args:
            metrics: Performance metrics from test execution
            baseline_name: Optional baseline name for comparison
            test_name: Name of the test
            
        Returns:
            Complete performance report
        """
        report = {
            "test_name": test_name,
            "generated_at": datetime.utcnow().isoformat(),
            "metrics": metrics,
        }
        
        # Threshold validation
        passed, violations = self.validator.validate_report(metrics)
        report["threshold_validation"] = {
            "passed": passed,
            "violations": violations,
            "violation_count": len(violations),
        }
        
        # Baseline comparison
        if baseline_name:
            comparison = self.comparator.compare(metrics, baseline_name)
            report["baseline_comparison"] = comparison
            
            # Add degradation check result
            degraded, issues = self.comparator.check_degradation(metrics, baseline_name)
            report["degradation_check"] = {
                "passed": degraded,
                "issues": issues,
                "issue_count": len(issues),
            }
        else:
            report["baseline_comparison"] = {"message": "No baseline specified"}
            report["degradation_check"] = {"message": "No baseline specified"}
        
        # Overall status
        report["overall_status"] = "PASSED"
        if not passed or (baseline_name and not degraded):
            report["overall_status"] = "FAILED"
        elif violations or (baseline_name and issues):
            report["overall_status"] = "WARNING"
        
        return report
    
    def save_report(
        self,
        report: Dict[str, Any],
        filepath: str = None
    ) -> str:
        """Save report to file."""
        if filepath is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filepath = f"tests/performance/reports/{report.get('test_name', 'report')}_{timestamp}.json"
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filepath
    
    def print_summary(self, report: Dict[str, Any]):
        """Print a human-readable summary of the report."""
        print("\n" + "=" * 60)
        print("PERFORMANCE REPORT SUMMARY")
        print("=" * 60)
        print(f"Test: {report.get('test_name', 'N/A')}")
        print(f"Generated: {report.get('generated_at', 'N/A')}")
        print("-" * 60)
        
        # Overall status
        status = report.get("overall_status", "UNKNOWN")
        status_icon = "✓" if status == "PASSED" else ("⚠" if status == "WARNING" else "✗")
        print(f"Overall Status: {status_icon} {status}")
        print("-" * 60)
        
        # Threshold validation
        tv = report.get("threshold_validation", {})
        print(f"Threshold Validation: {'✓ PASSED' if tv.get('passed') else '✗ FAILED'}")
        if tv.get("violations"):
            for v in tv["violations"][:5]:  # Show first 5
                print(f"  - {v}")
            if len(tv["violations"]) > 5:
                print(f"  ... and {len(tv['violations']) - 5} more")
        print("-" * 60)
        
        # Baseline comparison
        bc = report.get("baseline_comparison", {})
        if "error" not in bc:
            summary = bc.get("summary", {})
            print(f"Baseline Comparison:")
            print(f"  Endpoints: {summary.get('passed', 0)}/{summary.get('total_endpoints', 0)} passed")
            print(f"  Pass Rate: {summary.get('pass_rate', 0)}%")
            print(f"  Avg Degradation: {summary.get('avg_degradation_percent', 0)}%")
            
            degradations = bc.get("degradations", [])
            if degradations:
                print(f"  Degradations: {len(degradations)}")
                for d in degradations[:3]:
                    print(f"    - {d['endpoint']}: +{d['degradation_percent']:.1f}%")
        else:
            print(f"Baseline Comparison: {bc.get('error')}")
        print("-" * 60)
        
        # Degradation check
        dc = report.get("degradation_check", {})
        if "message" not in dc:
            print(f"Degradation Check: {'✓ PASSED' if dc.get('passed') else '✗ FAILED'}")
            if dc.get("issues"):
                for i in dc["issues"][:3]:
                    print(f"  - {i}")
        print("=" * 60 + "\n")


# =============================================================================
# Integration with Locust
# =============================================================================

class LocustThresholdChecker:
    """Threshold checking integrated with Locust test execution."""
    
    def __init__(self, config: ThresholdConfig = None):
        self.config = config or ThresholdConfig()
        self.validator = ThresholdValidator(self.config)
        self.violations: List[str] = []
    
    def check_locust_stats(self, stats) -> Tuple[bool, List[str]]:
        """
        Check Locust statistics against thresholds.
        
        Args:
            stats: Locust stats object
            
        Returns:
            Tuple of (passed, list of violations)
        """
        violations = []
        
        # Iterate through all entries in stats
        for entry in stats.entries.values():
            name = entry.name
            num_requests = entry.num_requests
            num_failures = entry.num_failures
            
            if num_requests == 0:
                continue
            
            # Calculate metrics
            error_rate = num_failures / num_requests if num_requests > 0 else 0
            
            # Get response time percentiles
            # Locust stores these in the ResponseTimeTracker
            p95 = getattr(entry, "get_response_time_percentile", lambda p: 0)(0.95)
            
            # Validate
            passed, entry_violations = self.validator.validate_endpoint(
                endpoint=name,
                p95_ms=p95,
                error_rate=error_rate
            )
            violations.extend(entry_violations)
        
        return len(violations) == 0, violations
    
    def on_test_stop(self, environment):
        """Called when Locust test stops."""
        if environment.stats:
            passed, violations = self.check_locust_stats(environment.stats)
            self.violations = violations
            
            if not passed:
                print("\n" + "=" * 60)
                print("THRESHOLD VIOLATIONS DETECTED")
                print("=" * 60)
                for v in violations:
                    print(f"  ✗ {v}")
                print("=" * 60 + "\n")


# =============================================================================
# CLI Interface
# =============================================================================

def run_threshold_check(
    metrics_file: str,
    baseline_name: str = "default"
) -> Dict[str, Any]:
    """
    Run threshold check on a metrics file.
    
    Args:
        metrics_file: Path to metrics JSON file
        baseline_name: Name of baseline to compare against
        
    Returns:
        Check results
    """
    with open(metrics_file, 'r') as f:
        metrics = json.load(f)
    
    generator = PerformanceReportGenerator()
    report = generator.generate_report(metrics, baseline_name)
    
    generator.print_summary(report)
    
    return report


# Export for use in other modules
__all__ = [
    "ThresholdConfig",
    "ThresholdValidator",
    "BaselineManager",
    "PerformanceComparator",
    "PerformanceReportGenerator",
    "LocustThresholdChecker",
    "run_threshold_check",
]