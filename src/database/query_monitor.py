"""
Slow query monitoring module for SuperInsight Platform.

Provides query performance monitoring and slow query detection.
Implements Requirement 9.5 for database query optimization.

i18n Translation Keys:
- database.monitor.slow_query_detected: 检测到慢查询: {duration}ms, SQL: {sql}
- database.monitor.stats_reset: 慢查询统计已重置
- database.monitor.threshold_updated: 慢查询阈值已更新: {threshold}ms
- database.monitor.query_recorded: 查询已记录: {duration}ms
"""

import logging
import time
import traceback
import threading
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class SlowQueryRecord:
    """Record of a slow query.
    
    Attributes:
        sql: The SQL query string
        duration_ms: Query execution time in milliseconds
        params: Query parameters
        timestamp: When the query was executed
        stack_trace: Optional stack trace for debugging
        query_type: Type of query (SELECT, INSERT, UPDATE, DELETE)
        table_name: Primary table involved in the query
    """
    sql: str
    duration_ms: float
    params: Dict[str, Any]
    timestamp: datetime
    stack_trace: Optional[str] = None
    query_type: Optional[str] = None
    table_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "sql": self.sql,
            "duration_ms": self.duration_ms,
            "params": self.params,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace,
            "query_type": self.query_type,
            "table_name": self.table_name
        }


@dataclass
class QueryStats:
    """Statistics for query monitoring.
    
    Attributes:
        total_queries: Total number of queries recorded
        slow_queries: Number of slow queries detected
        total_duration_ms: Total duration of all queries
        avg_duration_ms: Average query duration
        max_duration_ms: Maximum query duration
        min_duration_ms: Minimum query duration
        queries_by_type: Count of queries by type
        slowest_queries: List of slowest queries
    """
    total_queries: int = 0
    slow_queries: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    queries_by_type: Dict[str, int] = field(default_factory=dict)
    slowest_queries: List[SlowQueryRecord] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_queries": self.total_queries,
            "slow_queries": self.slow_queries,
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": self.avg_duration_ms,
            "max_duration_ms": self.max_duration_ms,
            "min_duration_ms": self.min_duration_ms if self.min_duration_ms != float('inf') else 0.0,
            "queries_by_type": self.queries_by_type,
            "slow_query_percentage": (self.slow_queries / self.total_queries * 100) if self.total_queries > 0 else 0.0,
            "slowest_queries": [q.to_dict() for q in self.slowest_queries[:10]]
        }


class QueryMonitor:
    """Slow query monitoring class.
    
    Monitors database query performance and records slow queries
    that exceed the configured threshold.
    
    Example:
        ```python
        monitor = QueryMonitor(threshold_ms=1000)
        
        # Record a query
        monitor.record_query(
            sql="SELECT * FROM users WHERE id = :id",
            duration_ms=1500,
            params={"id": 123}
        )
        
        # Get slow queries
        slow_queries = monitor.get_slow_queries(limit=10)
        
        # Get statistics
        stats = monitor.get_stats()
        ```
    
    Thread Safety:
        This class is thread-safe and can be used in multi-threaded
        environments.
    """
    
    # Default threshold: 1 second (1000ms)
    DEFAULT_THRESHOLD_MS = 1000.0
    
    # Maximum number of slow queries to keep in memory
    MAX_SLOW_QUERIES = 1000
    
    # Maximum number of slowest queries to track
    MAX_SLOWEST_QUERIES = 100
    
    def __init__(
        self,
        threshold_ms: float = DEFAULT_THRESHOLD_MS,
        max_records: int = MAX_SLOW_QUERIES,
        capture_stack_trace: bool = False
    ):
        """Initialize QueryMonitor.
        
        Args:
            threshold_ms: Threshold in milliseconds for slow query detection
            max_records: Maximum number of slow query records to keep
            capture_stack_trace: Whether to capture stack traces for slow queries
        """
        self.threshold_ms = threshold_ms
        self.max_records = max_records
        self.capture_stack_trace = capture_stack_trace
        
        # Thread-safe storage using deque
        self._slow_queries: deque = deque(maxlen=max_records)
        self._slowest_queries: List[SlowQueryRecord] = []
        self._lock = threading.RLock()
        
        # Statistics
        self._total_queries = 0
        self._slow_query_count = 0
        self._total_duration_ms = 0.0
        self._max_duration_ms = 0.0
        self._min_duration_ms = float('inf')
        self._queries_by_type: Dict[str, int] = {}
    
    def record_query(
        self,
        sql: str,
        duration_ms: float,
        params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record a query execution.
        
        Args:
            sql: The SQL query string
            duration_ms: Query execution time in milliseconds
            params: Optional query parameters
            
        Returns:
            True if the query was recorded as slow, False otherwise
        """
        params = params or {}
        is_slow = duration_ms >= self.threshold_ms
        
        with self._lock:
            # Update statistics
            self._total_queries += 1
            self._total_duration_ms += duration_ms
            self._max_duration_ms = max(self._max_duration_ms, duration_ms)
            self._min_duration_ms = min(self._min_duration_ms, duration_ms)
            
            # Track query type
            query_type = self._extract_query_type(sql)
            self._queries_by_type[query_type] = self._queries_by_type.get(query_type, 0) + 1
            
            if is_slow:
                self._slow_query_count += 1
                
                # Create slow query record
                record = SlowQueryRecord(
                    sql=sql[:2000],  # Truncate very long queries
                    duration_ms=duration_ms,
                    params=self._sanitize_params(params),
                    timestamp=datetime.now(),
                    stack_trace=self._capture_stack_trace() if self.capture_stack_trace else None,
                    query_type=query_type,
                    table_name=self._extract_table_name(sql)
                )
                
                # Add to slow queries
                self._slow_queries.append(record)
                
                # Update slowest queries list
                self._update_slowest_queries(record)
                
                # Log warning - i18n key: database.monitor.slow_query_detected
                logger.warning(
                    f"database.monitor.slow_query_detected: duration={duration_ms:.2f}ms, sql={sql[:200]}",
                    extra={
                        "duration": duration_ms,
                        "sql": sql[:200],
                        "query_type": query_type
                    }
                )
        
        return is_slow
    
    def get_slow_queries(
        self,
        limit: int = 100,
        min_duration_ms: Optional[float] = None,
        query_type: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[SlowQueryRecord]:
        """Get recorded slow queries.
        
        Args:
            limit: Maximum number of queries to return
            min_duration_ms: Optional minimum duration filter
            query_type: Optional query type filter (SELECT, INSERT, etc.)
            since: Optional timestamp filter (queries after this time)
            
        Returns:
            List of SlowQueryRecord objects
        """
        with self._lock:
            queries = list(self._slow_queries)
        
        # Apply filters
        if min_duration_ms is not None:
            queries = [q for q in queries if q.duration_ms >= min_duration_ms]
        
        if query_type is not None:
            queries = [q for q in queries if q.query_type == query_type.upper()]
        
        if since is not None:
            queries = [q for q in queries if q.timestamp >= since]
        
        # Sort by duration (slowest first) and limit
        queries.sort(key=lambda q: q.duration_ms, reverse=True)
        return queries[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query monitoring statistics.
        
        Returns:
            Dictionary containing query statistics
        """
        with self._lock:
            avg_duration = (
                self._total_duration_ms / self._total_queries
                if self._total_queries > 0 else 0.0
            )
            
            stats = QueryStats(
                total_queries=self._total_queries,
                slow_queries=self._slow_query_count,
                total_duration_ms=self._total_duration_ms,
                avg_duration_ms=avg_duration,
                max_duration_ms=self._max_duration_ms,
                min_duration_ms=self._min_duration_ms,
                queries_by_type=self._queries_by_type.copy(),
                slowest_queries=self._slowest_queries.copy()
            )
            
            return stats.to_dict()
    
    def reset(self) -> None:
        """Reset all statistics and clear recorded queries.
        
        i18n key: database.monitor.stats_reset
        """
        with self._lock:
            self._slow_queries.clear()
            self._slowest_queries.clear()
            self._total_queries = 0
            self._slow_query_count = 0
            self._total_duration_ms = 0.0
            self._max_duration_ms = 0.0
            self._min_duration_ms = float('inf')
            self._queries_by_type.clear()
        
        logger.info("database.monitor.stats_reset")
    
    def set_threshold(self, threshold_ms: float) -> None:
        """Update the slow query threshold.
        
        Args:
            threshold_ms: New threshold in milliseconds
            
        i18n key: database.monitor.threshold_updated
        """
        self.threshold_ms = threshold_ms
        logger.info(
            f"database.monitor.threshold_updated: threshold={threshold_ms}ms",
            extra={"threshold": threshold_ms}
        )
    
    @contextmanager
    def monitor_query(self, sql: str, params: Optional[Dict[str, Any]] = None):
        """Context manager for monitoring query execution.
        
        Example:
            ```python
            with monitor.monitor_query("SELECT * FROM users") as ctx:
                result = session.execute(query)
            # Query duration is automatically recorded
            ```
        
        Args:
            sql: The SQL query string
            params: Optional query parameters
            
        Yields:
            Context object with duration_ms attribute after execution
        """
        class QueryContext:
            def __init__(self):
                self.duration_ms = 0.0
                self.is_slow = False
        
        ctx = QueryContext()
        start_time = time.time()
        
        try:
            yield ctx
        finally:
            ctx.duration_ms = (time.time() - start_time) * 1000
            ctx.is_slow = self.record_query(sql, ctx.duration_ms, params)
    
    def query_decorator(self, sql_extractor: Optional[Callable] = None):
        """Decorator for monitoring function execution as a query.
        
        Args:
            sql_extractor: Optional function to extract SQL from function args
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                sql = func.__name__
                if sql_extractor:
                    try:
                        sql = sql_extractor(*args, **kwargs)
                    except Exception:
                        pass
                
                start_time = time.time()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    self.record_query(sql, duration_ms, kwargs)
            
            return wrapper
        return decorator
    
    def _extract_query_type(self, sql: str) -> str:
        """Extract query type from SQL string."""
        sql_upper = sql.strip().upper()
        for query_type in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']:
            if sql_upper.startswith(query_type):
                return query_type
        return 'OTHER'
    
    def _extract_table_name(self, sql: str) -> Optional[str]:
        """Extract primary table name from SQL string."""
        sql_upper = sql.strip().upper()
        
        # Try to extract table name based on query type
        try:
            if 'FROM' in sql_upper:
                # SELECT ... FROM table_name
                parts = sql_upper.split('FROM')
                if len(parts) > 1:
                    table_part = parts[1].strip().split()[0]
                    return table_part.strip('`"[]').lower()
            elif sql_upper.startswith('INSERT INTO'):
                # INSERT INTO table_name
                parts = sql_upper.split('INSERT INTO')
                if len(parts) > 1:
                    table_part = parts[1].strip().split()[0]
                    return table_part.strip('`"[]').lower()
            elif sql_upper.startswith('UPDATE'):
                # UPDATE table_name
                parts = sql_upper.split('UPDATE')
                if len(parts) > 1:
                    table_part = parts[1].strip().split()[0]
                    return table_part.strip('`"[]').lower()
            elif sql_upper.startswith('DELETE FROM'):
                # DELETE FROM table_name
                parts = sql_upper.split('DELETE FROM')
                if len(parts) > 1:
                    table_part = parts[1].strip().split()[0]
                    return table_part.strip('`"[]').lower()
        except Exception:
            pass
        
        return None
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize query parameters for logging.
        
        Removes or masks sensitive information.
        """
        sensitive_keys = {'password', 'secret', 'token', 'api_key', 'credential'}
        sanitized = {}
        
        for key, value in params.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, str) and len(value) > 100:
                sanitized[key] = value[:100] + '...'
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _capture_stack_trace(self) -> str:
        """Capture current stack trace for debugging."""
        return ''.join(traceback.format_stack()[:-2])
    
    def _update_slowest_queries(self, record: SlowQueryRecord) -> None:
        """Update the list of slowest queries."""
        self._slowest_queries.append(record)
        self._slowest_queries.sort(key=lambda q: q.duration_ms, reverse=True)
        self._slowest_queries = self._slowest_queries[:self.MAX_SLOWEST_QUERIES]


# Global query monitor instance
query_monitor = QueryMonitor()


# SQLAlchemy event listener integration
def setup_sqlalchemy_monitoring(engine, monitor: Optional[QueryMonitor] = None):
    """Set up SQLAlchemy event listeners for query monitoring.
    
    Args:
        engine: SQLAlchemy engine
        monitor: Optional QueryMonitor instance (uses global if not provided)
    """
    from sqlalchemy import event
    
    monitor = monitor or query_monitor
    
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault('query_start_time', []).append(time.time())
    
    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        start_times = conn.info.get('query_start_time', [])
        if start_times:
            start_time = start_times.pop()
            duration_ms = (time.time() - start_time) * 1000
            
            # Convert parameters to dict if needed
            params = {}
            if isinstance(parameters, dict):
                params = parameters
            elif isinstance(parameters, (list, tuple)) and parameters:
                params = {"params": str(parameters)[:200]}
            
            monitor.record_query(statement, duration_ms, params)


# Async context manager for monitoring
class AsyncQueryMonitor:
    """Async context manager for query monitoring."""
    
    def __init__(self, monitor: QueryMonitor, sql: str, params: Optional[Dict[str, Any]] = None):
        self.monitor = monitor
        self.sql = sql
        self.params = params
        self.start_time = None
        self.duration_ms = 0.0
        self.is_slow = False
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            self.duration_ms = (time.time() - self.start_time) * 1000
            self.is_slow = self.monitor.record_query(self.sql, self.duration_ms, self.params)
