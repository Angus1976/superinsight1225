"""
Performance Testing Module for SuperInsight Platform.

This module provides comprehensive performance testing capabilities including:
- Load testing with Locust
- Stress testing with automatic breakpoint detection
- Performance metrics collection and analysis
- Threshold validation and baseline comparison
- Frontend page load time measurement

**Validates: Requirements 5.1-5.6, 13.1-13.6**
**Validates: Properties 14-17, 31-33**
"""

from .locustfile import (
    StandardUser,
    AuthOnlyUser,
    TaskUser,
    AnnotationUser,
    ExportUser,
    StressTestUser,
    MetricsCollector,
    P95_THRESHOLD_MS,
    CONCURRENT_USERS,
    TEST_DURATION_SECONDS,
)

from .metrics import (
    MetricsCollector,
    FrontendMetricsCollector,
    PerformanceThresholds,
    PerformanceReport,
    EndpointMetrics,
    DatabaseMetrics,
    PageLoadMetrics,
    format_metrics_summary,
    metrics_collector,
)

from .load_tests import (
    AuthLoadTest,
    TaskLoadTest,
    AnnotationLoadTest,
    ExportLoadTest,
    StandardLoadUser,
    HeavyTaskUser,
    HeavyAnnotationUser,
    MixedApiUser,
    get_load_test_config,
    TestDataManager,
)

from .stress_tests import (
    StressTestRunner,
    StressTestClient,
    ResourceMonitor,
    RecoveryTest,
    StressTestResult,
    StressTestReport,
    run_quick_stress_test,
    identify_breaking_point,
)

from .thresholds import (
    ThresholdConfig,
    ThresholdValidator,
    BaselineManager,
    PerformanceComparator,
    PerformanceReportGenerator,
    LocustThresholdChecker,
    run_threshold_check,
)

from .frontend import (
    PageLoadMetrics,
    FrontendPerformanceReport,
    FrontendPerformanceMeasurer,
    FrontendPerformanceThresholds,
    FrontendBaselineManager,
    measure_frontend_performance,
    get_common_pages,
)

__all__ = [
    # Locust
    "StandardUser",
    "AuthOnlyUser",
    "TaskUser",
    "AnnotationUser",
    "ExportUser",
    "StressTestUser",
    "MetricsCollector",
    "P95_THRESHOLD_MS",
    "CONCURRENT_USERS",
    "TEST_DURATION_SECONDS",
    
    # Metrics
    "MetricsCollector",
    "FrontendMetricsCollector",
    "PerformanceThresholds",
    "PerformanceReport",
    "EndpointMetrics",
    "DatabaseMetrics",
    "PageLoadMetrics",
    "format_metrics_summary",
    "metrics_collector",
    
    # Load Tests
    "AuthLoadTest",
    "TaskLoadTest",
    "AnnotationLoadTest",
    "ExportLoadTest",
    "StandardLoadUser",
    "HeavyTaskUser",
    "HeavyAnnotationUser",
    "MixedApiUser",
    "get_load_test_config",
    "TestDataManager",
    
    # Stress Tests
    "StressTestRunner",
    "StressTestClient",
    "ResourceMonitor",
    "RecoveryTest",
    "StressTestResult",
    "StressTestReport",
    "run_quick_stress_test",
    "identify_breaking_point",
    
    # Thresholds
    "ThresholdConfig",
    "ThresholdValidator",
    "BaselineManager",
    "PerformanceComparator",
    "PerformanceReportGenerator",
    "LocustThresholdChecker",
    "run_threshold_check",
    
    # Frontend
    "PageLoadMetrics",
    "FrontendPerformanceReport",
    "FrontendPerformanceMeasurer",
    "FrontendPerformanceThresholds",
    "FrontendBaselineManager",
    "measure_frontend_performance",
    "get_common_pages",
]