"""
Locust Performance Testing Framework for SuperInsight Platform.

This module provides load testing, stress testing, and performance benchmarking
for the SuperInsight API endpoints.

Usage:
    # Run with 100 concurrent users for 60 seconds
    locust -f tests/performance/locustfile.py --host=http://localhost:8000 -u 100 -t 60s
    
    # Run with HTML report
    locust -f tests/performance/locustfile.py --host=http://localhost:8000 -u 100 -t 60s --html-report=report.html
    
    # Run headless for CI
    locust -f tests/performance/locustfile.py --host=http://localhost:8000 -u 100 -t 60s --headless
"""

import os
import json
import time
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

import locust
from locust import HttpUser, TaskSet, task, between, events, constant
from locust.runners import MasterRunner

# Import test configuration
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tests.conftest import setup_test_environment


# =============================================================================
# Configuration
# =============================================================================

# Performance thresholds (in milliseconds)
P95_THRESHOLD_MS = 500  # Critical endpoint threshold
P99_THRESHOLD_MS = 1000  # Maximum acceptable for any endpoint
THROUGHPUT_MIN_RPS = 50  # Minimum acceptable requests per second
ERROR_RATE_THRESHOLD = 0.01  # 1% maximum error rate

# Test configuration
CONCURRENT_USERS = 100
TEST_DURATION_SECONDS = 60
RAMP_UP_TIME_SECONDS = 30


# =============================================================================
# Performance Metrics Storage
# =============================================================================

@dataclass
class EndpointMetrics:
    """Metrics for a single endpoint."""
    endpoint: str
    method: str
    request_count: int = 0
    error_count: int = 0
    response_times: List[float] = field(default_factory=list)
    
    @property
    def p50(self) -> float:
        if not self.response_times:
            return 0
        return statistics.median(self.response_times)
    
    @property
    def p95(self) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]
    
    @property
    def p99(self) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[min(idx, len(sorted_times) - 1)]
    
    @property
    def avg(self) -> float:
        if not self.response_times:
            return 0
        return statistics.mean(self.response_times)
    
    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0
        return self.error_count / self.request_count


class MetricsCollector:
    """Collects and stores performance metrics during test execution."""
    
    def __init__(self):
        self.endpoints: Dict[str, EndpointMetrics] = {}
        self.start_time: Optional[datetime] = None
        self.total_requests: int = 0
        self.total_errors: int = 0
        self.baseline_metrics: Dict[str, Dict] = {}
        
    def record_request(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int
    ):
        """Record a request to an endpoint."""
        key = f"{method}:{endpoint}"
        
        if key not in self.endpoints:
            self.endpoints[key] = EndpointMetrics(endpoint=endpoint, method=method)
        
        metrics = self.endpoints[key]
        metrics.request_count += 1
        metrics.response_times.append(response_time)
        
        if status_code >= 400:
            metrics.error_count += 1
            self.total_errors += 1
        
        self.total_requests += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all collected metrics."""
        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "overall_error_rate": self.total_errors / self.total_requests if self.total_requests > 0 else 0,
            "endpoints": {
                key: {
                    "endpoint": metrics.endpoint,
                    "method": metrics.method,
                    "request_count": metrics.request_count,
                    "error_count": metrics.error_count,
                    "p50_ms": round(metrics.p50, 2),
                    "p95_ms": round(metrics.p95, 2),
                    "p99_ms": round(metrics.p99, 2),
                    "avg_ms": round(metrics.avg, 2),
                    "error_rate": round(metrics.error_rate, 4),
                }
                for key, metrics in self.endpoints.items()
            }
        }
    
    def check_thresholds(self) -> List[str]:
        """Check if metrics exceed defined thresholds."""
        violations = []
        
        for key, metrics in self.endpoints.items():
            if metrics.p95 > P95_THRESHOLD_MS:
                violations.append(
                    f"{key}: P95={metrics.p95:.2f}ms exceeds threshold {P95_THRESHOLD_MS}ms"
                )
            if metrics.error_rate > ERROR_RATE_THRESHOLD:
                violations.append(
                    f"{key}: Error rate={metrics.error_rate:.2%} exceeds threshold {ERROR_RATE_THRESHOLD:.2%}"
                )
        
        return violations
    
    def save_baseline(self, filepath: str = "tests/performance/baseline.json"):
        """Save current metrics as baseline."""
        baseline = {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoints": {}
        }
        
        for key, metrics in self.endpoints.items():
            baseline["endpoints"][key] = {
                "p50_ms": metrics.p50,
                "p95_ms": metrics.p95,
                "p99_ms": metrics.p99,
                "avg_ms": metrics.avg,
            }
        
        with open(filepath, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        self.baseline_metrics = baseline
        return filepath
    
    def compare_with_baseline(self, baseline_path: str = "tests/performance/baseline.json") -> Dict[str, Any]:
        """Compare current metrics with baseline."""
        try:
            with open(baseline_path, 'r') as f:
                baseline = json.load(f)
        except FileNotFoundError:
            return {"error": "Baseline not found"}
        
        comparison = {
            "timestamp": datetime.utcnow().isoformat(),
            "degradations": [],
            "improvements": []
        }
        
        for key, metrics in self.endpoints.items():
            if key in baseline["endpoints"]:
                base = baseline["endpoints"][key]
                p95_degradation = (metrics.p95 - base["p95_ms"]) / base["p95_ms"] if base["p95_ms"] > 0 else 0
                
                if p95_degradation > 0.20:  # 20% degradation threshold
                    comparison["degradations"].append({
                        "endpoint": key,
                        "baseline_p95_ms": base["p95_ms"],
                        "current_p95_ms": metrics.p95,
                        "degradation_percent": round(p95_degradation * 100, 2)
                    })
                elif p95_degradation < -0.10:  # 10% improvement
                    comparison["improvements"].append({
                        "endpoint": key,
                        "baseline_p95_ms": base["p95_ms"],
                        "current_p95_ms": metrics.p95,
                        "improvement_percent": round(abs(p95_degradation) * 100, 2)
                    })
        
        return comparison


# Global metrics collector
metrics_collector = MetricsCollector()


# =============================================================================
# Custom Events
# =============================================================================

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize metrics collector on Locust start."""
    if isinstance(environment.runner, MasterRunner):
        print("Performance test initialized with master node")
    else:
        print("Performance test initialized with worker node")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Start metrics collection on test start."""
    metrics_collector.start_time = datetime.utcnow()
    print(f"Performance test started at {metrics_collector.start_time}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Stop metrics collection and generate report on test stop."""
    end_time = datetime.utcnow()
    duration = (end_time - metrics_collector.start_time).total_seconds() if metrics_collector.start_time else 0
    
    summary = metrics_collector.get_summary()
    summary["duration_seconds"] = duration
    summary["throughput_rps"] = summary["total_requests"] / duration if duration > 0 else 0
    
    # Check thresholds
    violations = metrics_collector.check_thresholds()
    summary["threshold_violations"] = violations
    summary["passed"] = len(violations) == 0
    
    # Print summary
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 60)
    print(f"Duration: {duration:.2f}s")
    print(f"Total Requests: {summary['total_requests']}")
    print(f"Total Errors: {summary['total_errors']}")
    print(f"Overall Error Rate: {summary['overall_error_rate']:.2%}")
    print(f"Throughput: {summary['throughput_rps']:.2f} requests/second")
    print("-" * 60)
    print("Endpoint Metrics:")
    for key, data in summary.get("endpoints", {}).items():
        status = "✓" if data["p95_ms"] < P95_THRESHOLD_MS else "✗"
        print(f"  {status} {key}: P50={data['p50_ms']:.2f}ms, P95={data['p95_ms']:.2f}ms, P99={data['p99_ms']:.2f}ms")
    print("-" * 60)
    
    if violations:
        print("THRESHOLD VIOLATIONS:")
        for v in violations:
            print(f"  ✗ {v}")
    else:
        print("All thresholds passed!")
    
    print("=" * 60 + "\n")
    
    # Save report
    report_path = f"tests/performance/report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Report saved to: {report_path}")


# =============================================================================
# Request Hooks
# =============================================================================

@events.request.add_listener
def on_request(
    name: str,
    response_time: float,
    response_length: int,
    exception: Optional[Exception],
    **kwargs
):
    """Record request metrics."""
    # Extract endpoint and method from request name
    # Locust names are typically like "GET /api/v1/auth/login"
    if exception:
        metrics_collector.total_errors += 1
    
    # Note: We can't easily get status_code here, so we track errors separately


# =============================================================================
# Task Sets
# =============================================================================

class AuthTaskSet(TaskSet):
    """Task set for authentication endpoints."""
    
    def on_start(self):
        """Set up authentication for the user."""
        self.token = None
        self.user_id = None
    
    @task(10)
    def health_check(self):
        """Health check endpoint."""
        with self.client.get("/health", name="GET /health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(5)
    def login(self):
        """User login endpoint."""
        # Use test credentials
        payload = {
            "username": "test_user",
            "password": "test_password"
        }
        
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            name="POST /api/v1/auth/login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
            elif response.status_code == 401:
                # Expected for test credentials
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(3)
    def register(self):
        """User registration endpoint."""
        import uuid
        payload = {
            "username": f"test_user_{uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "password": "test_password123"
        }
        
        with self.client.post(
            "/api/v1/auth/register",
            json=payload,
            name="POST /api/v1/auth/register",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 400]:  # 400 for existing user
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


class TaskTaskSet(TaskSet):
    """Task set for task management endpoints."""
    
    def on_start(self):
        """Authenticate the user."""
        self.token = None
        self._authenticate()
    
    def _authenticate(self):
        """Get authentication token."""
        payload = {
            "username": "test_user",
            "password": "test_password"
        }
        
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            name="POST /api/v1/auth/login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    @task(5)
    def list_tasks(self):
        """List tasks endpoint."""
        with self.client.get(
            "/api/v1/tasks",
            headers=self._get_headers(),
            name="GET /api/v1/tasks",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(3)
    def get_task(self):
        """Get single task endpoint."""
        with self.client.get(
            "/api/v1/tasks/1",
            headers=self._get_headers(),
            name="GET /api/v1/tasks/{id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def create_task(self):
        """Create task endpoint."""
        payload = {
            "title": f"Test Task {time.time()}",
            "description": "Performance test task"
        }
        
        with self.client.post(
            "/api/v1/tasks",
            json=payload,
            headers=self._get_headers(),
            name="POST /api/v1/tasks",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 401, 400]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def update_task(self):
        """Update task endpoint."""
        payload = {
            "title": f"Updated Task {time.time()}"
        }
        
        with self.client.put(
            "/api/v1/tasks/1",
            json=payload,
            headers=self._get_headers(),
            name="PUT /api/v1/tasks/{id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


class AnnotationTaskSet(TaskSet):
    """Task set for annotation endpoints."""
    
    def on_start(self):
        """Authenticate the user."""
        self.token = None
        self._authenticate()
    
    def _authenticate(self):
        """Get authentication token."""
        payload = {
            "username": "test_user",
            "password": "test_password"
        }
        
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            name="POST /api/v1/auth/login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    @task(4)
    def list_annotations(self):
        """List annotations endpoint."""
        with self.client.get(
            "/api/v1/annotations",
            headers=self._get_headers(),
            name="GET /api/v1/annotations",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(3)
    def get_annotation(self):
        """Get single annotation endpoint."""
        with self.client.get(
            "/api/v1/annotations/1",
            headers=self._get_headers(),
            name="GET /api/v1/annotations/{id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def create_annotation(self):
        """Create annotation endpoint."""
        payload = {
            "task_id": 1,
            "data": {"label": "test", "start": 0, "end": 10}
        }
        
        with self.client.post(
            "/api/v1/annotations",
            json=payload,
            headers=self._get_headers(),
            name="POST /api/v1/annotations",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 401, 400]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


class ExportTaskSet(TaskSet):
    """Task set for data export endpoints."""
    
    def on_start(self):
        """Authenticate the user."""
        self.token = None
        self._authenticate()
    
    def _authenticate(self):
        """Get authentication token."""
        payload = {
            "username": "test_user",
            "password": "test_password"
        }
        
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            name="POST /api/v1/auth/login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    @task(3)
    def list_exports(self):
        """List exports endpoint."""
        with self.client.get(
            "/api/v1/exports",
            headers=self._get_headers(),
            name="GET /api/v1/exports",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def create_export(self):
        """Create export endpoint."""
        payload = {
            "format": "json",
            "filters": {}
        }
        
        with self.client.post(
            "/api/v1/exports",
            json=payload,
            headers=self._get_headers(),
            name="POST /api/v1/exports",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 401, 400]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def get_export_status(self):
        """Get export status endpoint."""
        with self.client.get(
            "/api/v1/exports/1/status",
            headers=self._get_headers(),
            name="GET /api/v1/exports/{id}/status",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


# =============================================================================
# User Classes
# =============================================================================

class StandardUser(HttpUser):
    """
    Standard user with mixed workload.
    
    Simulates typical user behavior with authentication,
    task management, and annotation operations.
    """
    
    wait_time = between(1, 3)
    tasks = {
        AuthTaskSet: 2,
        TaskTaskSet: 3,
        AnnotationTaskSet: 2,
        ExportTaskSet: 1
    }


class AuthOnlyUser(HttpUser):
    """User focused on authentication operations."""
    
    wait_time = between(0.5, 1.5)
    tasks = {
        AuthTaskSet: 5,
        TaskTaskSet: 1,
        AnnotationTaskSet: 1,
        ExportTaskSet: 1
    }


class TaskUser(HttpUser):
    """User focused on task management operations."""
    
    wait_time = between(1, 2)
    tasks = {
        AuthTaskSet: 1,
        TaskTaskSet: 5,
        AnnotationTaskSet: 2,
        ExportTaskSet: 1
    }


class AnnotationUser(HttpUser):
    """User focused on annotation operations."""
    
    wait_time = between(2, 5)
    tasks = {
        AuthTaskSet: 1,
        TaskTaskSet: 2,
        AnnotationTaskSet: 5,
        ExportTaskSet: 1
    }


class ExportUser(HttpUser):
    """User focused on export operations."""
    
    wait_time = between(3, 8)
    tasks = {
        AuthTaskSet: 1,
        TaskTaskSet: 1,
        AnnotationTaskSet: 1,
        ExportTaskSet: 5
    }


# =============================================================================
# Stress Test Configuration
# =============================================================================

class StressTestUser(HttpUser):
    """
    Stress test user with rapid requests.
    
    Used for stress testing to identify breaking points.
    """
    
    wait_time = between(0.1, 0.5)  # Fast requests
    tasks = {
        AuthTaskSet: 3,
        TaskTaskSet: 3,
        AnnotationTaskSet: 2,
        ExportTaskSet: 2
    }


# =============================================================================
# Performance Test Runner
# =============================================================================

def run_performance_test(
    host: str = "http://localhost:8000",
    users: int = CONCURRENT_USERS,
    duration: int = TEST_DURATION_SECONDS,
    spawn_rate: float = 10
) -> Dict[str, Any]:
    """
    Run a performance test programmatically.
    
    Args:
        host: Target host URL
        users: Number of concurrent users
        duration: Test duration in seconds
        spawn_rate: Users spawned per second
    
    Returns:
        Test results dictionary
    """
    from locust.env import Environment
    
    env = Environment(
        user_classes=[StandardUser],
        host=host,
        reset_stats=True
    )
    
    env.runner.start(user_count=users, spawn_rate=spawn_rate)
    env.runner.schedule_hatching(1)
    
    # Run for specified duration
    import time
    start_time = time.time()
    while time.time() - start_time < duration:
        time.sleep(1)
        if not env.runner.hatching:
            break
    
    env.runner.stop()
    env.runner.join()
    
    return metrics_collector.get_summary()


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SuperInsight Performance Testing")
    parser.add_argument("--host", default="http://localhost:8000", help="Target host")
    parser.add_argument("-u", "--users", type=int, default=CONCURRENT_USERS, help="Number of users")
    parser.add_argument("-t", "--time", type=str, default=f"{TEST_DURATION_SECONDS}s", help="Test duration")
    parser.add_argument("-r", "--rate", type=float, default=10, help="Spawn rate")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--html-report", help="HTML report output path")
    parser.add_argument("--save-baseline", action="store_true", help="Save as baseline")
    
    args = parser.parse_args()
    
    print(f"Starting performance test against {args.host}")
    print(f"Users: {args.users}, Duration: {args.time}, Spawn rate: {args.rate}")
    
    # Note: Locust is typically run via command line
    # This script provides the locustfile for that command