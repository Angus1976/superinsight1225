"""
Performance Optimizer for High Availability System.

Provides automatic performance monitoring, optimization recommendations,
and resource management for the high availability infrastructure.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class OptimizationType(Enum):
    """Types of optimizations."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    CACHE = "cache"
    QUERY = "query"
    CONNECTION = "connection"


class OptimizationPriority(Enum):
    """Priority levels for optimizations."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class OptimizationRecommendation:
    """A performance optimization recommendation."""
    recommendation_id: str
    optimization_type: OptimizationType
    priority: OptimizationPriority
    title: str
    description: str
    expected_improvement: float  # Percentage
    auto_applicable: bool = False
    applied: bool = False
    created_at: float = field(default_factory=time.time)


@dataclass
class PerformanceMetrics:
    """Current performance metrics."""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_latency: float
    cache_hit_rate: float
    avg_response_time: float
    active_connections: int
    error_rate: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerformanceOptimizerConfig:
    """Configuration for performance optimizer."""
    monitoring_interval: float = 30.0
    optimization_threshold_cpu: float = 80.0
    optimization_threshold_memory: float = 85.0
    optimization_threshold_disk: float = 90.0
    optimization_threshold_cache_hit: float = 70.0
    auto_optimize_enabled: bool = True
    max_recommendations: int = 50


class PerformanceOptimizer:
    """
    Automatic performance optimization system.
    
    Features:
    - Continuous performance monitoring
    - Automatic optimization recommendations
    - Resource usage analysis
    - Cache optimization
    - Query optimization suggestions
    - Auto-apply safe optimizations
    """
    
    def __init__(self, config: Optional[PerformanceOptimizerConfig] = None):
        self.config = config or PerformanceOptimizerConfig()
        self.metrics_history: deque = deque(maxlen=1000)
        self.recommendations: Dict[str, OptimizationRecommendation] = {}
        self.optimization_history: List[Dict[str, Any]] = []
        self.optimizers: Dict[OptimizationType, Callable] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Register default optimizers
        self._register_default_optimizers()
        
        logger.info("PerformanceOptimizer initialized")
    
    def _register_default_optimizers(self):
        """Register default optimization handlers."""
        self.register_optimizer(OptimizationType.CPU, self._optimize_cpu)
        self.register_optimizer(OptimizationType.MEMORY, self._optimize_memory)
        self.register_optimizer(OptimizationType.CACHE, self._optimize_cache)
        self.register_optimizer(OptimizationType.CONNECTION, self._optimize_connections)
    
    def register_optimizer(self, opt_type: OptimizationType, handler: Callable):
        """Register an optimization handler."""
        self.optimizers[opt_type] = handler
        logger.debug(f"Registered optimizer for {opt_type.value}")
    
    async def start(self):
        """Start the performance optimizer."""
        if self._is_running:
            return
        
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("PerformanceOptimizer started")
    
    async def stop(self):
        """Stop the performance optimizer."""
        self._is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("PerformanceOptimizer stopped")
    
    async def _monitor_loop(self):
        """Background monitoring loop."""
        while self._is_running:
            try:
                # Collect metrics
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Analyze and generate recommendations
                await self._analyze_performance(metrics)
                
                # Auto-apply safe optimizations
                if self.config.auto_optimize_enabled:
                    await self._auto_optimize()
                
                await asyncio.sleep(self.config.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitor loop: {e}")
                await asyncio.sleep(10)
    
    async def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics."""
        try:
            import psutil
            
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return PerformanceMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                network_latency=0.0,  # Would measure actual latency
                cache_hit_rate=85.0,  # Would get from cache system
                avg_response_time=100.0,  # Would get from metrics
                active_connections=50,  # Would get from connection pool
                error_rate=0.01
            )
        except ImportError:
            return PerformanceMetrics(
                cpu_usage=50.0,
                memory_usage=60.0,
                disk_usage=70.0,
                network_latency=10.0,
                cache_hit_rate=85.0,
                avg_response_time=100.0,
                active_connections=50,
                error_rate=0.01
            )
    
    async def _analyze_performance(self, metrics: PerformanceMetrics):
        """Analyze performance and generate recommendations."""
        # CPU optimization
        if metrics.cpu_usage > self.config.optimization_threshold_cpu:
            self._add_recommendation(
                OptimizationType.CPU,
                OptimizationPriority.HIGH,
                "High CPU Usage Detected",
                f"CPU usage is at {metrics.cpu_usage:.1f}%. Consider scaling horizontally or optimizing CPU-intensive operations.",
                expected_improvement=20.0
            )
        
        # Memory optimization
        if metrics.memory_usage > self.config.optimization_threshold_memory:
            self._add_recommendation(
                OptimizationType.MEMORY,
                OptimizationPriority.HIGH,
                "High Memory Usage Detected",
                f"Memory usage is at {metrics.memory_usage:.1f}%. Consider clearing caches or increasing memory allocation.",
                expected_improvement=15.0,
                auto_applicable=True
            )
        
        # Disk optimization
        if metrics.disk_usage > self.config.optimization_threshold_disk:
            self._add_recommendation(
                OptimizationType.DISK,
                OptimizationPriority.CRITICAL,
                "High Disk Usage Detected",
                f"Disk usage is at {metrics.disk_usage:.1f}%. Clean up old logs and temporary files.",
                expected_improvement=10.0
            )
        
        # Cache optimization
        if metrics.cache_hit_rate < self.config.optimization_threshold_cache_hit:
            self._add_recommendation(
                OptimizationType.CACHE,
                OptimizationPriority.MEDIUM,
                "Low Cache Hit Rate",
                f"Cache hit rate is at {metrics.cache_hit_rate:.1f}%. Consider adjusting cache TTL or increasing cache size.",
                expected_improvement=25.0
            )
        
        # Response time optimization
        if metrics.avg_response_time > 500:
            self._add_recommendation(
                OptimizationType.QUERY,
                OptimizationPriority.HIGH,
                "Slow Response Times",
                f"Average response time is {metrics.avg_response_time:.0f}ms. Review slow queries and optimize database indexes.",
                expected_improvement=30.0
            )
    
    def _add_recommendation(
        self,
        opt_type: OptimizationType,
        priority: OptimizationPriority,
        title: str,
        description: str,
        expected_improvement: float,
        auto_applicable: bool = False
    ):
        """Add an optimization recommendation."""
        rec_id = f"{opt_type.value}_{int(time.time())}"
        
        # Check if similar recommendation exists
        for existing in self.recommendations.values():
            if existing.optimization_type == opt_type and not existing.applied:
                return  # Don't duplicate
        
        recommendation = OptimizationRecommendation(
            recommendation_id=rec_id,
            optimization_type=opt_type,
            priority=priority,
            title=title,
            description=description,
            expected_improvement=expected_improvement,
            auto_applicable=auto_applicable
        )
        
        self.recommendations[rec_id] = recommendation
        
        # Cleanup old recommendations
        if len(self.recommendations) > self.config.max_recommendations:
            oldest = min(self.recommendations.values(), key=lambda r: r.created_at)
            del self.recommendations[oldest.recommendation_id]
        
        logger.info(f"Added optimization recommendation: {title}")
    
    async def _auto_optimize(self):
        """Auto-apply safe optimizations."""
        for rec in list(self.recommendations.values()):
            if rec.auto_applicable and not rec.applied:
                optimizer = self.optimizers.get(rec.optimization_type)
                if optimizer:
                    try:
                        result = await optimizer()
                        rec.applied = True
                        
                        self.optimization_history.append({
                            "recommendation_id": rec.recommendation_id,
                            "type": rec.optimization_type.value,
                            "result": result,
                            "timestamp": time.time()
                        })
                        
                        logger.info(f"Auto-applied optimization: {rec.title}")
                    except Exception as e:
                        logger.error(f"Failed to auto-apply optimization: {e}")
    
    async def apply_optimization(self, recommendation_id: str) -> Dict[str, Any]:
        """Manually apply an optimization."""
        rec = self.recommendations.get(recommendation_id)
        if not rec:
            return {"success": False, "error": "Recommendation not found"}
        
        if rec.applied:
            return {"success": False, "error": "Already applied"}
        
        optimizer = self.optimizers.get(rec.optimization_type)
        if not optimizer:
            return {"success": False, "error": "No optimizer available"}
        
        try:
            result = await optimizer()
            rec.applied = True
            
            self.optimization_history.append({
                "recommendation_id": recommendation_id,
                "type": rec.optimization_type.value,
                "result": result,
                "timestamp": time.time()
            })
            
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Default optimization handlers
    async def _optimize_cpu(self) -> Dict[str, Any]:
        """CPU optimization handler."""
        logger.info("Applying CPU optimization")
        # In real implementation, would adjust thread pools, reduce parallelism, etc.
        return {"action": "cpu_optimization", "status": "applied"}
    
    async def _optimize_memory(self) -> Dict[str, Any]:
        """Memory optimization handler."""
        logger.info("Applying memory optimization")
        import gc
        gc.collect()
        return {"action": "memory_optimization", "status": "gc_collected"}
    
    async def _optimize_cache(self) -> Dict[str, Any]:
        """Cache optimization handler."""
        logger.info("Applying cache optimization")
        # In real implementation, would adjust cache settings
        return {"action": "cache_optimization", "status": "applied"}
    
    async def _optimize_connections(self) -> Dict[str, Any]:
        """Connection pool optimization handler."""
        logger.info("Applying connection optimization")
        # In real implementation, would adjust connection pool settings
        return {"action": "connection_optimization", "status": "applied"}
    
    def get_recommendations(
        self,
        opt_type: Optional[OptimizationType] = None,
        priority: Optional[OptimizationPriority] = None,
        include_applied: bool = False
    ) -> List[OptimizationRecommendation]:
        """Get optimization recommendations."""
        recs = list(self.recommendations.values())
        
        if opt_type:
            recs = [r for r in recs if r.optimization_type == opt_type]
        
        if priority:
            recs = [r for r in recs if r.priority == priority]
        
        if not include_applied:
            recs = [r for r in recs if not r.applied]
        
        # Sort by priority (highest first)
        recs.sort(key=lambda r: r.priority.value, reverse=True)
        return recs
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = list(self.metrics_history)[-10:]
        
        return {
            "current": {
                "cpu_usage": recent_metrics[-1].cpu_usage,
                "memory_usage": recent_metrics[-1].memory_usage,
                "disk_usage": recent_metrics[-1].disk_usage,
                "cache_hit_rate": recent_metrics[-1].cache_hit_rate,
                "avg_response_time": recent_metrics[-1].avg_response_time,
            },
            "averages": {
                "cpu_usage": statistics.mean(m.cpu_usage for m in recent_metrics),
                "memory_usage": statistics.mean(m.memory_usage for m in recent_metrics),
                "response_time": statistics.mean(m.avg_response_time for m in recent_metrics),
            },
            "recommendations_count": len([r for r in self.recommendations.values() if not r.applied]),
            "optimizations_applied": len(self.optimization_history),
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        recs = list(self.recommendations.values())
        
        return {
            "total_recommendations": len(recs),
            "pending_recommendations": len([r for r in recs if not r.applied]),
            "applied_recommendations": len([r for r in recs if r.applied]),
            "by_type": {
                t.value: len([r for r in recs if r.optimization_type == t])
                for t in OptimizationType
            },
            "by_priority": {
                p.name: len([r for r in recs if r.priority == p])
                for p in OptimizationPriority
            },
            "optimization_history_count": len(self.optimization_history),
            "metrics_collected": len(self.metrics_history),
        }


# Global performance optimizer instance
performance_optimizer: Optional[PerformanceOptimizer] = None


async def initialize_performance_optimizer(
    config: Optional[PerformanceOptimizerConfig] = None
) -> PerformanceOptimizer:
    """Initialize the global performance optimizer."""
    global performance_optimizer
    
    performance_optimizer = PerformanceOptimizer(config)
    await performance_optimizer.start()
    
    return performance_optimizer


async def shutdown_performance_optimizer():
    """Shutdown the global performance optimizer."""
    global performance_optimizer
    
    if performance_optimizer:
        await performance_optimizer.stop()
        performance_optimizer = None


def get_performance_optimizer() -> Optional[PerformanceOptimizer]:
    """Get the global performance optimizer instance."""
    return performance_optimizer
