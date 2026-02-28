"""
Stress Testing Module for SuperInsight Platform.

This module provides stress testing capabilities to identify system breaking
points and measure performance under extreme load conditions.

**Validates: Requirements 5.2, 13.1**
**Validates: Properties 14, 15, 16, 17**
"""

import time
import threading
import statistics
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager


# =============================================================================
# Configuration
# =============================================================================

# Stress test configuration
INITIAL_USERS = 10
MAX_USERS = 500
RAMP_UP_STEP = 10
RAMP_UP_INTERVAL_SECONDS = 10
STEP_DURATION_SECONDS = 30

# Breakpoint detection
BREAKPOINT_THRESHOLD_ERROR_RATE = 0.10  # 10% error rate
BREAKPOINT_THRESHOLD_P95_MS = 2000  # 2 second P95
BREAKPOINT_THRESHOLD_TIMEOUT = 0.05  # 5% timeout rate


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class StressTestResult:
    """Result of a stress test step."""
    step: int
    concurrent_users: int
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    avg_ms: float
    throughput_rps: float
    timeout_count: int = 0
    is_breakpoint: bool = False
    breakpoint_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "concurrent_users": self.concurrent_users,
            "duration_seconds": self.duration_seconds,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "error_rate": self.error_rate,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "avg_ms": self.avg_ms,
            "throughput_rps": self.throughput_rps,
            "timeout_count": self.timeout_count,
            "is_breakpoint": self.is_breakpoint,
            "breakpoint_reason": self.breakpoint_reason,
        }


@dataclass
class StressTestReport:
    """Complete stress test report."""
    start_time: str
    end_time: str
    total_duration_seconds: float
    initial_users: int
    max_users: int
    breakpoint_users: Optional[int]
    breakpoint_reason: Optional[str]
    results: List[StressTestResult]
    system_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_seconds": self.total_duration_seconds,
            "initial_users": self.initial_users,
            "max_users": self.max_users,
            "breakpoint_users": self.breakpoint_users,
            "breakpoint_reason": self.breakpoint_reason,
            "results": [r.to_dict() for r in self.results],
            "system_info": self.system_info,
        }


# =============================================================================
# HTTP Client for Stress Testing
# =============================================================================

import httpx
from urllib.parse import urljoin


class StressTestClient:
    """HTTP client for stress testing with connection pooling."""
    
    def __init__(
        self,
        base_url: str,
        max_connections: int = 100,
        timeout: float = 30.0
    ):
        self.base_url = base_url
        self.timeout = timeout
        
        # Create connection pool
        self.client = httpx.Client(
            timeout=timeout,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=max_connections,
                keepalive_expiry=30.0
            )
        )
    
    def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> tuple[int, float]:
        """
        Make an HTTP request and return status code and response time.
        
        Returns:
            Tuple of (status_code, response_time_ms)
        """
        url = urljoin(self.base_url, endpoint)
        start = time.perf_counter()
        
        try:
            response = self.client.request(method, url, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            return response.status_code, elapsed
        except httpx.TimeoutException:
            elapsed = (time.perf_counter() - start) * 1000
            return 504, elapsed  # Gateway Timeout
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return 500, elapsed
    
    def get(self, endpoint: str, **kwargs) -> tuple[int, float]:
        """GET request."""
        return self.request("GET", endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> tuple[int, float]:
        """POST request."""
        return self.request("POST", endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> tuple[int, float]:
        """PUT request."""
        return self.request("PUT", endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> tuple[int, float]:
        """DELETE request."""
        return self.request("DELETE", endpoint, **kwargs)
    
    def close(self):
        """Close the client."""
        self.client.close()


# =============================================================================
# Stress Test Runner
# =============================================================================

class StressTestRunner:
    """Runner for stress tests with automatic ramp-up and breakpoint detection."""
    
    def __init__(
        self,
        base_url: str,
        initial_users: int = INITIAL_USERS,
        max_users: int = MAX_USERS,
        ramp_up_step: int = RAMP_UP_STEP,
        step_duration: int = STEP_DURATION_SECONDS,
        ramp_up_interval: int = RAMP_UP_INTERVAL_SECONDS
    ):
        self.base_url = base_url
        self.initial_users = initial_users
        self.max_users = max_users
        self.ramp_up_step = ramp_up_step
        self.step_duration = step_duration
        self.ramp_up_interval = ramp_up_interval
        
        self.results: List[StressTestResult] = []
        self.breakpoint_found = False
        self.breakpoint_info: Optional[tuple[int, str]] = None
        self._stop_event = threading.Event()
    
    def _create_worker(
        self,
        client: StressTestClient,
        endpoints: List[tuple[str, str, Dict]]
    ) -> Callable:
        """Create a worker function for a single user."""
        def worker() -> List[tuple[int, float]]:
            results = []
            for method, endpoint, kwargs in endpoints:
                status, elapsed = client.request(method, endpoint, **kwargs)
                results.append((status, elapsed))
            return results
        return worker
    
    def _run_step(
        self,
        num_users: int,
        endpoints: List[tuple[str, str, Dict]]
    ) -> StressTestResult:
        """Run a single stress test step with specified number of users."""
        step = len(self.results) + 1
        start_time = time.perf_counter()
        
        # Create client
        client = StressTestClient(self.base_url)
        
        # Create workers
        workers = []
        for _ in range(num_users):
            worker = self._create_worker(client, endpoints)
            workers.append(worker)
        
        # Execute workers in parallel
        all_results: List[tuple[int, float]] = []
        timeout_count = 0
        
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(worker) for worker in workers * 10]  # Multiple iterations
            
            for future in as_completed(futures):
                try:
                    worker_results = future.result(timeout=self.step_duration)
                    all_results.extend(worker_results)
                except Exception:
                    timeout_count += 1
        
        duration = time.perf_counter() - start_time
        
        # Analyze results
        response_times = [r[1] for r in all_results]
        status_codes = [r[0] for r in all_results]
        
        successful = sum(1 for s in status_codes if s < 400)
        failed = len(status_codes) - successful
        
        error_rate = failed / len(status_codes) if status_codes else 0
        timeout_rate = timeout_count / (num_users * 10) if num_users > 0 else 0
        
        p50 = statistics.median(response_times) if response_times else 0
        p95 = self._percentile(response_times, 95) if response_times else 0
        p99 = self._percentile(response_times, 99) if response_times else 0
        avg = statistics.mean(response_times) if response_times else 0
        
        throughput = len(all_results) / duration if duration > 0 else 0
        
        # Check for breakpoint
        is_breakpoint = False
        breakpoint_reason = None
        
        if error_rate > BREAKPOINT_THRESHOLD_ERROR_RATE:
            is_breakpoint = True
            breakpoint_reason = f"Error rate {error_rate:.2%} exceeds threshold {BREAKPOINT_THRESHOLD_ERROR_RATE:.2%}"
        elif p95 > BREAKPOINT_THRESHOLD_P95_MS:
            is_breakpoint = True
            breakpoint_reason = f"P95 latency {p95:.0f}ms exceeds threshold {BREAKPOINT_THRESHOLD_P95_MS}ms"
        elif timeout_rate > BREAKPOINT_THRESHOLD_TIMEOUT:
            is_breakpoint = True
            breakpoint_reason = f"Timeout rate {timeout_rate:.2%} exceeds threshold {BREAKPOINT_THRESHOLD_TIMEOUT:.2%}"
        
        result = StressTestResult(
            step=step,
            concurrent_users=num_users,
            duration_seconds=duration,
            total_requests=len(all_results),
            successful_requests=successful,
            failed_requests=failed,
            error_rate=error_rate,
            p50_ms=p50,
            p95_ms=p95,
            p99_ms=p99,
            avg_ms=avg,
            throughput_rps=throughput,
            timeout_count=timeout_count,
            is_breakpoint=is_breakpoint,
            breakpoint_reason=breakpoint_reason
        )
        
        client.close()
        
        return result
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]
    
    def run(
        self,
        endpoints: List[tuple[str, str, Dict]] = None
    ) -> StressTestReport:
        """
        Run the complete stress test.
        
        Args:
            endpoints: List of (method, endpoint, kwargs) tuples to test
            
        Returns:
            StressTestReport with all results
        """
        if endpoints is None:
            endpoints = [
                ("GET", "/health", {}),
                ("GET", "/api/v1/tasks", {"headers": {"Authorization": "Bearer test"}}),
                ("POST", "/api/v1/auth/login", {"json": {"username": "test", "password": "test"}}),
            ]
        
        self.results = []
        self.breakpoint_found = False
        self.breakpoint_info = None
        self._stop_event.clear()
        
        start_time = datetime.utcnow()
        
        # Run initial step
        current_users = self.initial_users
        
        while current_users <= self.max_users and not self._stop_event.is_set():
            print(f"\n{'='*60}")
            print(f"STRESS TEST STEP {len(self.results) + 1}")
            print(f"Users: {current_users}")
            print(f"{'='*60}")
            
            result = self._run_step(current_users, endpoints)
            self.results.append(result)
            
            # Print step results
            print(f"\nResults:")
            print(f"  Duration: {result.duration_seconds:.2f}s")
            print(f"  Total Requests: {result.total_requests}")
            print(f"  Error Rate: {result.error_rate:.2%}")
            print(f"  P50: {result.p50_ms:.1f}ms")
            print(f"  P95: {result.p95_ms:.1f}ms")
            print(f"  P99: {result.p99_ms:.1f}ms")
            print(f"  Throughput: {result.throughput_rps:.1f} req/s")
            
            if result.is_breakpoint:
                print(f"\n⚠️  BREAKPOINT DETECTED!")
                print(f"   Reason: {result.breakpoint_reason}")
                self.breakpoint_found = True
                self.breakpoint_info = (current_users, result.breakpoint_reason)
                self._stop_event.set()
                break
            
            # Ramp up
            if current_users < self.max_users:
                print(f"\nRamping up to {current_users + self.ramp_up_step} users...")
                time.sleep(self.ramp_up_interval)
                current_users = min(current_users + self.ramp_up_step, self.max_users)
        
        end_time = datetime.utcnow()
        
        return StressTestReport(
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_duration_seconds=(end_time - start_time).total_seconds(),
            initial_users=self.initial_users,
            max_users=current_users,
            breakpoint_users=self.breakpoint_info[0] if self.breakpoint_info else None,
            breakpoint_reason=self.breakpoint_info[1] if self.breakpoint_info else None,
            results=self.results,
        )
    
    def stop(self):
        """Stop the stress test."""
        self._stop_event.set()


# =============================================================================
# Resource Monitoring
# =============================================================================

class ResourceMonitor:
    """Monitor system resources during stress testing."""
    
    def __init__(self, sample_interval: float = 1.0):
        self.sample_interval = sample_interval
        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.samples: List[Dict] = []
    
    def start(self):
        """Start monitoring in background thread."""
        self._running = True
        self._stop_event.clear()
        self.samples = []
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> List[Dict]:
        """Stop monitoring and return samples."""
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        return self.samples
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        import psutil
        
        while self._running and not self._stop_event.is_set():
            try:
                sample = {
                    "timestamp": time.time(),
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
                    "net_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
                }
                self.samples.append(sample)
            except Exception:
                pass
            
            time.sleep(self.sample_interval)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of resource usage."""
        if not self.samples:
            return {"error": "No samples collected"}
        
        cpu_samples = [s["cpu_percent"] for s in self.samples]
        mem_samples = [s["memory_percent"] for s in self.samples]
        
        return {
            "sample_count": len(self.samples),
            "cpu": {
                "avg_percent": statistics.mean(cpu_samples),
                "max_percent": max(cpu_samples),
                "min_percent": min(cpu_samples),
            },
            "memory": {
                "avg_percent": statistics.mean(mem_samples),
                "max_percent": max(mem_samples),
                "min_percent": min(mem_samples),
            },
        }


# =============================================================================
# Recovery Testing
# =============================================================================

class RecoveryTest:
    """Test system recovery after stress."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = StressTestClient(base_url)
    
    def test_recovery(
        self,
        endpoint: str = "/health",
        iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Test system recovery after stress.
        
        Returns metrics showing how quickly the system recovers.
        """
        results = []
        
        for i in range(iterations):
            status, elapsed = self.client.get(endpoint)
            results.append({
                "iteration": i,
                "status": status,
                "response_time_ms": elapsed,
                "success": status < 400
            })
            time.sleep(1)  # Wait between requests
        
        successful = sum(1 for r in results if r["success"])
        response_times = [r["response_time_ms"] for r in results if r["success"]]
        
        return {
            "total_iterations": iterations,
            "successful": successful,
            "failed": iterations - successful,
            "recovery_rate": successful / iterations,
            "response_times": {
                "avg_ms": statistics.mean(response_times) if response_times else 0,
                "p95_ms": self._percentile(response_times, 95) if response_times else 0,
            },
            "iterations": results,
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]
    
    def close(self):
        """Close the client."""
        self.client.close()


# =============================================================================
# Utility Functions
# =============================================================================

def run_quick_stress_test(
    base_url: str,
    users: int = 50,
    duration: int = 30
) -> Dict[str, Any]:
    """
    Run a quick stress test with specified parameters.
    
    Args:
        base_url: Base URL of the API
        users: Number of concurrent users
        duration: Duration of each user's test in seconds
        
    Returns:
        Test results dictionary
    """
    runner = StressTestRunner(
        base_url=base_url,
        initial_users=users,
        max_users=users,
        ramp_up_step=0,
        step_duration=duration,
        ramp_up_interval=0
    )
    
    endpoints = [
        ("GET", "/health", {}),
        ("GET", "/api/v1/tasks", {"headers": {"Authorization": "Bearer test"}}),
        ("POST", "/api/v1/auth/login", {"json": {"username": "test", "password": "test"}}),
    ]
    
    report = runner.run(endpoints)
    return report.to_dict()


def identify_breaking_point(base_url: str) -> Dict[str, Any]:
    """
    Identify the system breaking point through progressive load increase.
    
    Args:
        base_url: Base URL of the API
        
    Returns:
        Breaking point analysis
    """
    runner = StressTestRunner(
        base_url=base_url,
        initial_users=10,
        max_users=200,
        ramp_up_step=10,
        step_duration=20,
        ramp_up_interval=5
    )
    
    endpoints = [
        ("GET", "/health", {}),
        ("GET", "/api/v1/tasks", {"headers": {"Authorization": "Bearer test"}}),
    ]
    
    report = runner.run(endpoints)
    
    return {
        "breaking_point_users": report.breakpoint_users,
        "breaking_point_reason": report.breakpoint_reason,
        "results": [r.to_dict() for r in report.results],
    }


# Export for use in other modules
__all__ = [
    "StressTestRunner",
    "StressTestClient",
    "ResourceMonitor",
    "RecoveryTest",
    "StressTestResult",
    "StressTestReport",
    "run_quick_stress_test",
    "identify_breaking_point",
]