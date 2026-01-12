"""
Quality Benchmark Manager for SuperInsight Platform.

Manages quality benchmarks and standards:
- Benchmark definition and storage
- Quality comparison against benchmarks
- Benchmark trend tracking
- Benchmark report generation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class BenchmarkType(str, Enum):
    """Types of quality benchmarks."""
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    COMPLETENESS = "completeness"
    TIMELINESS = "timeliness"
    AGREEMENT = "agreement"
    CUSTOM = "custom"


class BenchmarkStatus(str, Enum):
    """Status of benchmark comparison."""
    ABOVE = "above"
    MEETS = "meets"
    BELOW = "below"
    CRITICAL = "critical"


@dataclass
class QualityBenchmark:
    """Defines a quality benchmark."""
    benchmark_id: str
    name: str
    benchmark_type: BenchmarkType
    description: str
    target_value: float
    warning_threshold: float
    critical_threshold: float
    unit: str = "score"
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "name": self.name,
            "benchmark_type": self.benchmark_type.value,
            "description": self.description,
            "target_value": self.target_value,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "unit": self.unit,
            "enabled": self.enabled,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class BenchmarkComparison:
    """Result of comparing against a benchmark."""
    benchmark_id: str
    benchmark_name: str
    current_value: float
    target_value: float
    status: BenchmarkStatus
    deviation: float
    deviation_percent: float
    trend: str  # improving, stable, declining
    recommendations: List[str] = field(default_factory=list)
    compared_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "benchmark_name": self.benchmark_name,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "status": self.status.value,
            "deviation": self.deviation,
            "deviation_percent": self.deviation_percent,
            "trend": self.trend,
            "recommendations": self.recommendations,
            "compared_at": self.compared_at.isoformat()
        }


@dataclass
class BenchmarkHistory:
    """Historical benchmark data point."""
    benchmark_id: str
    value: float
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }


@dataclass
class BenchmarkReport:
    """Comprehensive benchmark report."""
    report_id: str
    project_id: str
    period_start: datetime
    period_end: datetime
    comparisons: List[BenchmarkComparison]
    overall_status: BenchmarkStatus
    summary: Dict[str, Any]
    trends: Dict[str, str]
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "project_id": self.project_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "comparisons": [c.to_dict() for c in self.comparisons],
            "overall_status": self.overall_status.value,
            "summary": self.summary,
            "trends": self.trends,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat()
        }


class BenchmarkManager:
    """
    Manages quality benchmarks and comparisons.
    
    Provides benchmark definition, tracking, and reporting.
    """

    def __init__(self):
        self.benchmarks: Dict[str, QualityBenchmark] = {}
        self.history: Dict[str, List[BenchmarkHistory]] = defaultdict(list)
        self.max_history_size = 10000
        self._initialize_default_benchmarks()

    def _initialize_default_benchmarks(self):
        """Initialize default quality benchmarks."""
        default_benchmarks = [
            QualityBenchmark(
                benchmark_id="accuracy_benchmark",
                name="标注准确率基准",
                benchmark_type=BenchmarkType.ACCURACY,
                description="标注结果与黄金标准的一致性",
                target_value=0.95,
                warning_threshold=0.90,
                critical_threshold=0.80,
                unit="ratio"
            ),
            QualityBenchmark(
                benchmark_id="consistency_benchmark",
                name="标注一致性基准",
                benchmark_type=BenchmarkType.CONSISTENCY,
                description="同一数据多次标注的一致性",
                target_value=0.90,
                warning_threshold=0.85,
                critical_threshold=0.75,
                unit="ratio"
            ),
            QualityBenchmark(
                benchmark_id="completeness_benchmark",
                name="标注完整性基准",
                benchmark_type=BenchmarkType.COMPLETENESS,
                description="标注字段的完整程度",
                target_value=1.0,
                warning_threshold=0.95,
                critical_threshold=0.90,
                unit="ratio"
            ),
            QualityBenchmark(
                benchmark_id="timeliness_benchmark",
                name="标注及时性基准",
                benchmark_type=BenchmarkType.TIMELINESS,
                description="标注任务完成的及时程度",
                target_value=0.95,
                warning_threshold=0.85,
                critical_threshold=0.70,
                unit="ratio"
            ),
            QualityBenchmark(
                benchmark_id="agreement_benchmark",
                name="标注员一致性基准",
                benchmark_type=BenchmarkType.AGREEMENT,
                description="多标注员之间的一致性",
                target_value=0.85,
                warning_threshold=0.75,
                critical_threshold=0.60,
                unit="kappa"
            )
        ]

        for benchmark in default_benchmarks:
            self.benchmarks[benchmark.benchmark_id] = benchmark

    def add_benchmark(self, benchmark: QualityBenchmark):
        """Add or update a benchmark."""
        benchmark.updated_at = datetime.now()
        self.benchmarks[benchmark.benchmark_id] = benchmark
        logger.info(f"Added benchmark: {benchmark.name}")

    def remove_benchmark(self, benchmark_id: str) -> bool:
        """Remove a benchmark."""
        if benchmark_id in self.benchmarks:
            del self.benchmarks[benchmark_id]
            return True
        return False

    def get_benchmark(self, benchmark_id: str) -> Optional[QualityBenchmark]:
        """Get a benchmark by ID."""
        return self.benchmarks.get(benchmark_id)

    def list_benchmarks(
        self,
        benchmark_type: Optional[BenchmarkType] = None,
        enabled_only: bool = True
    ) -> List[QualityBenchmark]:
        """List benchmarks with optional filters."""
        benchmarks = list(self.benchmarks.values())
        
        if benchmark_type:
            benchmarks = [b for b in benchmarks if b.benchmark_type == benchmark_type]
        
        if enabled_only:
            benchmarks = [b for b in benchmarks if b.enabled]
        
        return benchmarks

    def record_value(
        self,
        benchmark_id: str,
        value: float,
        context: Optional[Dict[str, Any]] = None
    ):
        """Record a value for benchmark tracking."""
        if benchmark_id not in self.benchmarks:
            logger.warning(f"Benchmark {benchmark_id} not found")
            return

        history_entry = BenchmarkHistory(
            benchmark_id=benchmark_id,
            value=value,
            timestamp=datetime.now(),
            context=context or {}
        )

        self.history[benchmark_id].append(history_entry)

        # Trim history if needed
        if len(self.history[benchmark_id]) > self.max_history_size:
            self.history[benchmark_id] = self.history[benchmark_id][-self.max_history_size:]

    def compare_to_benchmark(
        self,
        benchmark_id: str,
        current_value: float
    ) -> Optional[BenchmarkComparison]:
        """
        Compare a value against a benchmark.
        
        Args:
            benchmark_id: Benchmark identifier
            current_value: Current value to compare
            
        Returns:
            BenchmarkComparison result
        """
        benchmark = self.benchmarks.get(benchmark_id)
        if not benchmark:
            return None

        # Calculate deviation
        deviation = current_value - benchmark.target_value
        deviation_percent = (deviation / benchmark.target_value * 100) if benchmark.target_value != 0 else 0

        # Determine status
        if current_value >= benchmark.target_value:
            status = BenchmarkStatus.ABOVE
        elif current_value >= benchmark.warning_threshold:
            status = BenchmarkStatus.MEETS
        elif current_value >= benchmark.critical_threshold:
            status = BenchmarkStatus.BELOW
        else:
            status = BenchmarkStatus.CRITICAL

        # Calculate trend
        trend = self._calculate_trend(benchmark_id)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            benchmark, current_value, status, trend
        )

        # Record the value
        self.record_value(benchmark_id, current_value)

        return BenchmarkComparison(
            benchmark_id=benchmark_id,
            benchmark_name=benchmark.name,
            current_value=current_value,
            target_value=benchmark.target_value,
            status=status,
            deviation=deviation,
            deviation_percent=deviation_percent,
            trend=trend,
            recommendations=recommendations
        )

    def _calculate_trend(self, benchmark_id: str) -> str:
        """Calculate trend from historical data."""
        history = self.history.get(benchmark_id, [])
        
        if len(history) < 3:
            return "stable"

        # Get recent values
        recent = history[-10:]
        values = [h.value for h in recent]

        # Calculate simple trend
        first_half = statistics.mean(values[:len(values)//2])
        second_half = statistics.mean(values[len(values)//2:])

        diff = second_half - first_half
        threshold = 0.02  # 2% change threshold

        if diff > threshold:
            return "improving"
        elif diff < -threshold:
            return "declining"
        else:
            return "stable"

    def _generate_recommendations(
        self,
        benchmark: QualityBenchmark,
        current_value: float,
        status: BenchmarkStatus,
        trend: str
    ) -> List[str]:
        """Generate recommendations based on comparison."""
        recommendations = []

        if status == BenchmarkStatus.CRITICAL:
            recommendations.append(f"紧急：{benchmark.name}严重低于标准，需要立即采取行动")
            recommendations.append("建议暂停相关任务进行质量审查")
        elif status == BenchmarkStatus.BELOW:
            recommendations.append(f"{benchmark.name}低于警告阈值，需要关注")
            recommendations.append("建议增加质量检查频率")

        if trend == "declining":
            recommendations.append("质量呈下降趋势，建议分析根本原因")
        elif trend == "improving" and status != BenchmarkStatus.ABOVE:
            recommendations.append("质量正在改善，继续当前改进措施")

        if benchmark.benchmark_type == BenchmarkType.ACCURACY:
            if current_value < benchmark.target_value:
                recommendations.append("建议增加标注员培训")
        elif benchmark.benchmark_type == BenchmarkType.AGREEMENT:
            if current_value < benchmark.target_value:
                recommendations.append("建议组织标注校准会议")

        return recommendations

    def get_history(
        self,
        benchmark_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[BenchmarkHistory]:
        """Get historical data for a benchmark."""
        history = self.history.get(benchmark_id, [])

        if start_time:
            history = [h for h in history if h.timestamp >= start_time]
        if end_time:
            history = [h for h in history if h.timestamp <= end_time]

        return history[-limit:]

    def generate_report(
        self,
        project_id: str,
        current_values: Dict[str, float],
        period_days: int = 30
    ) -> BenchmarkReport:
        """
        Generate comprehensive benchmark report.
        
        Args:
            project_id: Project identifier
            current_values: Dictionary of benchmark_id -> current_value
            period_days: Report period in days
            
        Returns:
            BenchmarkReport with all comparisons
        """
        import uuid
        
        period_end = datetime.now()
        period_start = period_end - timedelta(days=period_days)

        comparisons = []
        trends = {}
        all_recommendations = []

        for benchmark_id, value in current_values.items():
            comparison = self.compare_to_benchmark(benchmark_id, value)
            if comparison:
                comparisons.append(comparison)
                trends[benchmark_id] = comparison.trend
                all_recommendations.extend(comparison.recommendations)

        # Determine overall status
        if any(c.status == BenchmarkStatus.CRITICAL for c in comparisons):
            overall_status = BenchmarkStatus.CRITICAL
        elif any(c.status == BenchmarkStatus.BELOW for c in comparisons):
            overall_status = BenchmarkStatus.BELOW
        elif all(c.status == BenchmarkStatus.ABOVE for c in comparisons):
            overall_status = BenchmarkStatus.ABOVE
        else:
            overall_status = BenchmarkStatus.MEETS

        # Generate summary
        summary = {
            "total_benchmarks": len(comparisons),
            "above_target": len([c for c in comparisons if c.status == BenchmarkStatus.ABOVE]),
            "meets_target": len([c for c in comparisons if c.status == BenchmarkStatus.MEETS]),
            "below_target": len([c for c in comparisons if c.status == BenchmarkStatus.BELOW]),
            "critical": len([c for c in comparisons if c.status == BenchmarkStatus.CRITICAL]),
            "improving": len([c for c in comparisons if c.trend == "improving"]),
            "declining": len([c for c in comparisons if c.trend == "declining"])
        }

        # Deduplicate recommendations
        unique_recommendations = list(dict.fromkeys(all_recommendations))

        return BenchmarkReport(
            report_id=str(uuid.uuid4()),
            project_id=project_id,
            period_start=period_start,
            period_end=period_end,
            comparisons=comparisons,
            overall_status=overall_status,
            summary=summary,
            trends=trends,
            recommendations=unique_recommendations[:10]  # Top 10 recommendations
        )

    def get_benchmark_statistics(
        self,
        benchmark_id: str,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get statistics for a benchmark over a period."""
        history = self.get_history(
            benchmark_id,
            start_time=datetime.now() - timedelta(days=period_days)
        )

        if not history:
            return {
                "benchmark_id": benchmark_id,
                "period_days": period_days,
                "data_points": 0
            }

        values = [h.value for h in history]

        return {
            "benchmark_id": benchmark_id,
            "period_days": period_days,
            "data_points": len(values),
            "current": values[-1] if values else None,
            "average": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "trend": self._calculate_trend(benchmark_id)
        }


# Global instance
benchmark_manager = BenchmarkManager()
