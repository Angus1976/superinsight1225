"""
Plugin Statistics Service for SuperInsight platform.

Provides comprehensive call logging and statistics calculation
for annotation plugins.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import uuid4
from collections import defaultdict
import statistics as stats

logger = logging.getLogger(__name__)


# ============================================================================
# Call Log Entry
# ============================================================================

class PluginCallLog:
    """Individual plugin call log entry."""
    
    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        task_count: int,
        success: bool,
        latency_ms: float,
        cost: float = 0.0,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid4())
        self.plugin_id = plugin_id
        self.plugin_name = plugin_name
        self.task_count = task_count
        self.success = success
        self.latency_ms = latency_ms
        self.cost = cost
        self.error_message = error_message
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "plugin_id": self.plugin_id,
            "plugin_name": self.plugin_name,
            "task_count": self.task_count,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "cost": self.cost,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================================
# Aggregated Statistics
# ============================================================================

class PluginAggregatedStats:
    """Aggregated statistics for a plugin."""
    
    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        self.total_calls = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_tasks = 0
        self.total_latency_ms = 0.0
        self.total_cost = 0.0
        self.latencies: List[float] = []
        self.errors: List[str] = []
        self.first_call_at: Optional[datetime] = None
        self.last_call_at: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 0.0
        return self.success_count / self.total_calls
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if not self.latencies:
            return 0.0
        return stats.mean(self.latencies)
    
    @property
    def p50_latency_ms(self) -> float:
        """Calculate 50th percentile latency."""
        if not self.latencies:
            return 0.0
        return stats.median(self.latencies)
    
    @property
    def p95_latency_ms(self) -> float:
        """Calculate 95th percentile latency."""
        if len(self.latencies) < 2:
            return self.avg_latency_ms
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    @property
    def p99_latency_ms(self) -> float:
        """Calculate 99th percentile latency."""
        if len(self.latencies) < 2:
            return self.avg_latency_ms
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    @property
    def avg_tasks_per_call(self) -> float:
        """Calculate average tasks per call."""
        if self.total_calls == 0:
            return 0.0
        return self.total_tasks / self.total_calls
    
    @property
    def avg_cost_per_task(self) -> float:
        """Calculate average cost per task."""
        if self.total_tasks == 0:
            return 0.0
        return self.total_cost / self.total_tasks
    
    def add_call(self, log: PluginCallLog) -> None:
        """Add a call log to statistics."""
        self.total_calls += 1
        self.total_tasks += log.task_count
        self.total_latency_ms += log.latency_ms
        self.total_cost += log.cost
        self.latencies.append(log.latency_ms)
        
        if log.success:
            self.success_count += 1
        else:
            self.failure_count += 1
            if log.error_message:
                self.errors.append(log.error_message)
        
        if self.first_call_at is None:
            self.first_call_at = log.created_at
        self.last_call_at = log.created_at
        
        # Keep only last 10000 latencies for percentile calculations
        if len(self.latencies) > 10000:
            self.latencies = self.latencies[-10000:]
        
        # Keep only last 100 errors
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plugin_name": self.plugin_name,
            "total_calls": self.total_calls,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "total_tasks": self.total_tasks,
            "avg_tasks_per_call": self.avg_tasks_per_call,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "total_cost": self.total_cost,
            "avg_cost_per_task": self.avg_cost_per_task,
            "first_call_at": self.first_call_at.isoformat() if self.first_call_at else None,
            "last_call_at": self.last_call_at.isoformat() if self.last_call_at else None,
            "recent_errors": self.errors[-10:],  # Last 10 errors
        }


# ============================================================================
# Statistics Service
# ============================================================================

class PluginStatisticsService:
    """
    Plugin statistics service.
    
    Provides comprehensive call logging and statistics calculation
    for annotation plugins.
    """
    
    def __init__(self, max_logs: int = 100000):
        """
        Initialize statistics service.
        
        Args:
            max_logs: Maximum number of logs to keep in memory
        """
        self.max_logs = max_logs
        self._logs: List[PluginCallLog] = []
        self._stats: Dict[str, PluginAggregatedStats] = {}
        self._lock = asyncio.Lock()
    
    async def log_call(
        self,
        plugin_id: str,
        plugin_name: str,
        task_count: int,
        success: bool,
        latency_ms: float,
        cost: float = 0.0,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PluginCallLog:
        """
        Log a plugin call.
        
        Args:
            plugin_id: Plugin ID
            plugin_name: Plugin name
            task_count: Number of tasks processed
            success: Whether call succeeded
            latency_ms: Call latency in milliseconds
            cost: Call cost
            error_message: Error message if failed
            metadata: Additional metadata
            
        Returns:
            PluginCallLog entry
        """
        async with self._lock:
            log = PluginCallLog(
                plugin_id=plugin_id,
                plugin_name=plugin_name,
                task_count=task_count,
                success=success,
                latency_ms=latency_ms,
                cost=cost,
                error_message=error_message,
                metadata=metadata,
            )
            
            # Add to logs
            self._logs.append(log)
            
            # Trim logs if needed
            if len(self._logs) > self.max_logs:
                self._logs = self._logs[-self.max_logs:]
            
            # Update aggregated stats
            if plugin_name not in self._stats:
                self._stats[plugin_name] = PluginAggregatedStats(plugin_name)
            self._stats[plugin_name].add_call(log)
            
            return log
    
    async def get_plugin_stats(
        self,
        plugin_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific plugin.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Statistics dictionary or None
        """
        async with self._lock:
            if plugin_name not in self._stats:
                return None
            return self._stats[plugin_name].to_dict()
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all plugins.
        
        Returns:
            Dictionary mapping plugin names to statistics
        """
        async with self._lock:
            return {
                name: stat.to_dict()
                for name, stat in self._stats.items()
            }
    
    async def get_recent_logs(
        self,
        plugin_name: Optional[str] = None,
        limit: int = 100,
        success_only: bool = False,
        failure_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get recent call logs.
        
        Args:
            plugin_name: Optional filter by plugin name
            limit: Maximum number of logs to return
            success_only: Only return successful calls
            failure_only: Only return failed calls
            
        Returns:
            List of log dictionaries
        """
        async with self._lock:
            logs = self._logs
            
            # Filter by plugin name
            if plugin_name:
                logs = [l for l in logs if l.plugin_name == plugin_name]
            
            # Filter by success/failure
            if success_only:
                logs = [l for l in logs if l.success]
            elif failure_only:
                logs = [l for l in logs if not l.success]
            
            # Return most recent
            return [l.to_dict() for l in logs[-limit:]]
    
    async def get_stats_by_time_range(
        self,
        plugin_name: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics for a time range.
        
        Args:
            plugin_name: Plugin name
            start_time: Start of time range
            end_time: End of time range (default: now)
            
        Returns:
            Statistics dictionary
        """
        end_time = end_time or datetime.utcnow()
        
        async with self._lock:
            # Filter logs by time range
            filtered_logs = [
                l for l in self._logs
                if l.plugin_name == plugin_name
                and start_time <= l.created_at <= end_time
            ]
            
            if not filtered_logs:
                return {
                    "plugin_name": plugin_name,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "total_calls": 0,
                }
            
            # Calculate stats for filtered logs
            temp_stats = PluginAggregatedStats(plugin_name)
            for log in filtered_logs:
                temp_stats.add_call(log)
            
            result = temp_stats.to_dict()
            result["start_time"] = start_time.isoformat()
            result["end_time"] = end_time.isoformat()
            
            return result
    
    async def get_hourly_stats(
        self,
        plugin_name: str,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Get hourly statistics.
        
        Args:
            plugin_name: Plugin name
            hours: Number of hours to look back
            
        Returns:
            List of hourly statistics
        """
        now = datetime.utcnow()
        results = []
        
        for i in range(hours):
            end_time = now - timedelta(hours=i)
            start_time = end_time - timedelta(hours=1)
            
            hourly_stats = await self.get_stats_by_time_range(
                plugin_name, start_time, end_time
            )
            hourly_stats["hour"] = start_time.strftime("%Y-%m-%d %H:00")
            results.append(hourly_stats)
        
        return list(reversed(results))
    
    async def clear_stats(self, plugin_name: Optional[str] = None) -> None:
        """
        Clear statistics.
        
        Args:
            plugin_name: Optional plugin name to clear (None = clear all)
        """
        async with self._lock:
            if plugin_name:
                if plugin_name in self._stats:
                    del self._stats[plugin_name]
                self._logs = [l for l in self._logs if l.plugin_name != plugin_name]
            else:
                self._stats.clear()
                self._logs.clear()


# ============================================================================
# Singleton Instance
# ============================================================================

_service_instance: Optional[PluginStatisticsService] = None


def get_statistics_service() -> PluginStatisticsService:
    """
    Get or create the statistics service instance.
    
    Returns:
        PluginStatisticsService instance
    """
    global _service_instance
    
    if _service_instance is None:
        _service_instance = PluginStatisticsService()
    
    return _service_instance
