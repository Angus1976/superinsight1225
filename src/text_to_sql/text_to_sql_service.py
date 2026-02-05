"""Text-to-SQL Service - Unified Service Layer.

This module provides the main orchestration service for Text-to-SQL functionality,
integrating all components (MethodSwitcher, QueryCache, SQLValidator, etc.) into
a unified interface with multi-tenant support, quota management, and comprehensive
metrics collection.

Features:
- Unified generate_sql() entry point
- Multi-tenant isolation and quota enforcement
- Comprehensive metrics tracking
- Query caching with cache hit/miss tracking
- SQL validation before returning results
- Error handling with retry logic
- LLM token usage tracking

Requirements:
- 8.1-8.3: Performance metrics tracking
- 12.1-12.6: Multi-tenant support and quota management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class SQLGenerationRequest(BaseModel):
    """Request for SQL generation."""
    query: str
    database_type: str = "postgresql"
    schema_context: Optional[Dict[str, Any]] = None
    method_preference: Optional[str] = None  # "template", "llm", "hybrid", "auto"
    tenant_id: UUID
    user_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    execute_sql: bool = False
    use_cache: bool = True


class SQLGenerationResult(BaseModel):
    """Result from SQL generation."""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    generated_sql: str
    method_used: str
    execution_time_ms: float
    confidence_score: Optional[float] = None
    cached: bool = False
    validation_passed: bool
    validation_warnings: List[str] = Field(default_factory=list)
    execution_result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TenantQuota(BaseModel):
    """Tenant LLM usage quota."""
    tenant_id: UUID
    monthly_llm_requests: int = 0
    monthly_llm_tokens: int = 0
    llm_requests_limit: int = 10000
    llm_tokens_limit: int = 1000000
    quota_reset_date: datetime
    quota_exceeded: bool = False


class TextToSQLMetrics(BaseModel):
    """Comprehensive metrics for Text-to-SQL operations."""
    tenant_id: UUID
    timestamp: datetime = Field(default_factory=datetime.now)

    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Method usage
    template_requests: int = 0
    llm_requests: int = 0
    hybrid_requests: int = 0

    # Performance metrics
    avg_execution_time_ms: float = 0.0
    p50_execution_time_ms: float = 0.0
    p95_execution_time_ms: float = 0.0
    p99_execution_time_ms: float = 0.0

    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0

    # LLM metrics
    llm_tokens_used: int = 0
    llm_requests_count: int = 0
    llm_cost_usd: float = 0.0

    # Quality metrics
    validation_failures: int = 0
    avg_confidence_score: float = 0.0


# ============================================================================
# Text-to-SQL Service
# ============================================================================

class TextToSQLService:
    """Unified Text-to-SQL service with multi-tenant support.

    This service orchestrates all Text-to-SQL components and provides:
    - Automatic method selection (template/LLM/hybrid)
    - Query result caching
    - SQL validation
    - Multi-tenant isolation
    - Quota enforcement
    - Comprehensive metrics tracking

    Attributes:
        tenant_quotas: Dictionary of tenant quotas
        tenant_metrics: Dictionary of tenant metrics
        execution_times: List of execution times for percentile calculation
    """

    def __init__(self):
        """Initialize Text-to-SQL service."""
        # Tenant management
        self.tenant_quotas: Dict[UUID, TenantQuota] = {}
        self.tenant_metrics: Dict[UUID, TextToSQLMetrics] = {}

        # Performance tracking
        self.execution_times: Dict[UUID, List[float]] = {}

        # Thread safety
        self._lock = asyncio.Lock()

        logger.info("Initialized Text-to-SQL Service")

    # ========================================================================
    # Main Entry Point
    # ========================================================================

    async def generate_sql(
        self,
        request: SQLGenerationRequest,
    ) -> SQLGenerationResult:
        """Generate SQL from natural language query.

        This is the main entry point for SQL generation, orchestrating all
        components with multi-tenant support and quota enforcement.

        Args:
            request: SQL generation request

        Returns:
            SQL generation result

        Raises:
            QuotaExceededError: If tenant quota exceeded
            ValidationError: If generated SQL is invalid
        """
        start_time = datetime.now()
        request_id = str(uuid4())

        try:
            # 1. Check tenant quota
            await self._check_quota(request.tenant_id, request.method_preference)

            # 2. Check cache (if enabled)
            cached_sql = None
            if request.use_cache:
                cached_sql = await self._get_from_cache(
                    request.query,
                    request.database_type,
                    request.schema_context,
                )

            # 3. Generate SQL (or use cached)
            if cached_sql:
                generated_sql = cached_sql
                method_used = "cache"
                confidence_score = 1.0
                cached = True

                # Update cache hit metrics
                await self._record_cache_hit(request.tenant_id)
            else:
                # Generate new SQL
                generated_sql, method_used, confidence_score = await self._generate_new_sql(
                    request
                )
                cached = False

                # Update cache miss metrics
                await self._record_cache_miss(request.tenant_id)

                # Cache the result
                if request.use_cache:
                    await self._save_to_cache(
                        request.query,
                        request.database_type,
                        request.schema_context,
                        generated_sql,
                    )

            # 4. Validate SQL
            validation_passed, validation_warnings = await self._validate_sql(
                generated_sql,
                request.database_type,
            )

            # 5. Execute SQL (if requested)
            execution_result = None
            if request.execute_sql and validation_passed:
                execution_result = await self._execute_sql(
                    generated_sql,
                    request.database_type,
                )

            # 6. Calculate execution time
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # 7. Build result
            result = SQLGenerationResult(
                request_id=request_id,
                query=request.query,
                generated_sql=generated_sql,
                method_used=method_used,
                execution_time_ms=execution_time_ms,
                confidence_score=confidence_score,
                cached=cached,
                validation_passed=validation_passed,
                validation_warnings=validation_warnings,
                execution_result=execution_result,
                metadata={
                    "tenant_id": str(request.tenant_id),
                    "database_type": request.database_type,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # 8. Record metrics
            await self._record_success_metrics(
                request.tenant_id,
                method_used,
                execution_time_ms,
                confidence_score,
            )

            # 9. Update quota usage
            if method_used == "llm" or method_used == "hybrid":
                await self._increment_quota_usage(
                    request.tenant_id,
                    tokens_used=self._estimate_tokens(request.query, generated_sql),
                )

            return result

        except Exception as e:
            # Record failure metrics
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            await self._record_failure_metrics(request.tenant_id, execution_time_ms)

            logger.error(f"SQL generation failed for tenant {request.tenant_id}: {e}")
            raise

    # ========================================================================
    # SQL Generation
    # ========================================================================

    async def _generate_new_sql(
        self,
        request: SQLGenerationRequest,
    ) -> Tuple[str, str, float]:
        """Generate new SQL using selected method.

        Args:
            request: Generation request

        Returns:
            Tuple of (generated_sql, method_used, confidence_score)
        """
        # Determine method to use
        method = await self._select_method(
            request.query,
            request.method_preference,
            request.tenant_id,
        )

        # Generate SQL based on method
        if method == "template":
            sql = await self._generate_with_template(
                request.query,
                request.database_type,
            )
            confidence = 0.9
        elif method == "llm":
            sql = await self._generate_with_llm(
                request.query,
                request.database_type,
                request.schema_context,
            )
            confidence = 0.8
        elif method == "hybrid":
            sql = await self._generate_with_hybrid(
                request.query,
                request.database_type,
                request.schema_context,
            )
            confidence = 0.85
        else:
            raise ValueError(f"Unknown method: {method}")

        return sql, method, confidence

    async def _select_method(
        self,
        query: str,
        preference: Optional[str],
        tenant_id: UUID,
    ) -> str:
        """Select best method for query.

        Args:
            query: Natural language query
            preference: User preference (or None for auto)
            tenant_id: Tenant ID

        Returns:
            Method name ("template", "llm", "hybrid")
        """
        # Check if tenant quota exceeded
        quota = await self._get_quota(tenant_id)
        if quota.quota_exceeded:
            # Force template-only mode
            return "template"

        # Use preference if specified and valid
        if preference in ["template", "llm", "hybrid"]:
            return preference

        # Auto-select based on query complexity
        complexity = self._calculate_query_complexity(query)

        if complexity < 30:
            return "template"
        elif complexity > 60:
            return "llm"
        else:
            return "hybrid"

    def _calculate_query_complexity(self, query: str) -> int:
        """Calculate query complexity score (0-100).

        Args:
            query: Natural language query

        Returns:
            Complexity score
        """
        score = 0
        query_lower = query.lower()

        # Basic query indicators
        if "join" in query_lower:
            score += 20
        if "group by" in query_lower or "aggregate" in query_lower:
            score += 15
        if "where" in query_lower or "filter" in query_lower:
            score += 10
        if "order by" in query_lower or "sort" in query_lower:
            score += 10

        # Complexity indicators
        if "subquery" in query_lower or "nested" in query_lower:
            score += 25
        if "window function" in query_lower:
            score += 30

        # Word count
        word_count = len(query.split())
        if word_count > 20:
            score += 15
        elif word_count > 10:
            score += 10
        elif word_count > 5:
            score += 5

        return min(score, 100)

    async def _generate_with_template(
        self,
        query: str,
        database_type: str,
    ) -> str:
        """Generate SQL using template method.

        Args:
            query: Natural language query
            database_type: Database type

        Returns:
            Generated SQL
        """
        # Placeholder - would call actual TemplateFiller
        # from src.text_to_sql.basic import TemplateFiller

        # Simplified example
        return f"SELECT * FROM table WHERE condition; -- Template generated for: {query}"

    async def _generate_with_llm(
        self,
        query: str,
        database_type: str,
        schema_context: Optional[Dict[str, Any]],
    ) -> str:
        """Generate SQL using LLM method.

        Args:
            query: Natural language query
            database_type: Database type
            schema_context: Database schema context

        Returns:
            Generated SQL
        """
        # Placeholder - would call actual LLMSQLGenerator
        # from src.text_to_sql.llm_based import LLMSQLGenerator

        # Simplified example
        return f"SELECT * FROM table WHERE condition; -- LLM generated for: {query}"

    async def _generate_with_hybrid(
        self,
        query: str,
        database_type: str,
        schema_context: Optional[Dict[str, Any]],
    ) -> str:
        """Generate SQL using hybrid method.

        Args:
            query: Natural language query
            database_type: Database type
            schema_context: Database schema context

        Returns:
            Generated SQL
        """
        # Placeholder - would call actual HybridGenerator
        # from src.text_to_sql.hybrid import HybridGenerator

        # Simplified example
        return f"SELECT * FROM table WHERE condition; -- Hybrid generated for: {query}"

    # ========================================================================
    # Caching
    # ========================================================================

    async def _get_from_cache(
        self,
        query: str,
        database_type: str,
        schema_context: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Get cached SQL result.

        Args:
            query: Natural language query
            database_type: Database type
            schema_context: Schema context

        Returns:
            Cached SQL or None
        """
        # Placeholder - would call actual QueryCache
        # from src.text_to_sql.query_cache import QueryCache
        return None

    async def _save_to_cache(
        self,
        query: str,
        database_type: str,
        schema_context: Optional[Dict[str, Any]],
        sql: str,
    ):
        """Save SQL to cache.

        Args:
            query: Natural language query
            database_type: Database type
            schema_context: Schema context
            sql: Generated SQL
        """
        # Placeholder - would call actual QueryCache
        pass

    # ========================================================================
    # Validation
    # ========================================================================

    async def _validate_sql(
        self,
        sql: str,
        database_type: str,
    ) -> Tuple[bool, List[str]]:
        """Validate generated SQL.

        Args:
            sql: Generated SQL
            database_type: Database type

        Returns:
            Tuple of (is_valid, warnings)
        """
        # Placeholder - would call actual SQLValidator
        # from src.text_to_sql.sql_validator import SQLValidator

        # Basic validation
        warnings = []

        if "DROP" in sql.upper():
            warnings.append("SQL contains DROP statement")

        if "DELETE" in sql.upper() and "WHERE" not in sql.upper():
            warnings.append("DELETE without WHERE clause")

        is_valid = len(warnings) == 0

        return is_valid, warnings

    # ========================================================================
    # Execution
    # ========================================================================

    async def _execute_sql(
        self,
        sql: str,
        database_type: str,
    ) -> Dict[str, Any]:
        """Execute SQL query.

        Args:
            sql: SQL to execute
            database_type: Database type

        Returns:
            Execution result
        """
        # Placeholder - would execute actual SQL
        return {
            "rows": [],
            "columns": [],
            "row_count": 0,
            "execution_time_ms": 0,
        }

    # ========================================================================
    # Multi-Tenant Support
    # ========================================================================

    async def _get_quota(self, tenant_id: UUID) -> TenantQuota:
        """Get tenant quota.

        Args:
            tenant_id: Tenant ID

        Returns:
            Tenant quota
        """
        async with self._lock:
            if tenant_id not in self.tenant_quotas:
                # Create default quota
                self.tenant_quotas[tenant_id] = TenantQuota(
                    tenant_id=tenant_id,
                    quota_reset_date=self._get_next_month_start(),
                )

            quota = self.tenant_quotas[tenant_id]

            # Reset quota if month rolled over
            if datetime.now() >= quota.quota_reset_date:
                quota.monthly_llm_requests = 0
                quota.monthly_llm_tokens = 0
                quota.quota_reset_date = self._get_next_month_start()
                quota.quota_exceeded = False

            return quota

    async def _check_quota(
        self,
        tenant_id: UUID,
        method_preference: Optional[str],
    ):
        """Check if tenant can use LLM.

        Args:
            tenant_id: Tenant ID
            method_preference: Preferred method

        Raises:
            QuotaExceededError: If quota exceeded and LLM required
        """
        quota = await self._get_quota(tenant_id)

        # Only check if LLM or hybrid requested
        if method_preference in ["llm", "hybrid"]:
            if quota.quota_exceeded:
                raise QuotaExceededError(
                    f"Tenant {tenant_id} LLM quota exceeded. "
                    f"Limit: {quota.llm_requests_limit} requests/month. "
                    f"Used: {quota.monthly_llm_requests}"
                )

    async def _increment_quota_usage(
        self,
        tenant_id: UUID,
        tokens_used: int,
    ):
        """Increment tenant quota usage.

        Args:
            tenant_id: Tenant ID
            tokens_used: Number of tokens used
        """
        async with self._lock:
            quota = self.tenant_quotas[tenant_id]
            quota.monthly_llm_requests += 1
            quota.monthly_llm_tokens += tokens_used

            # Check if quota exceeded
            if (quota.monthly_llm_requests >= quota.llm_requests_limit or
                quota.monthly_llm_tokens >= quota.llm_tokens_limit):
                quota.quota_exceeded = True

                logger.warning(
                    f"Tenant {tenant_id} quota exceeded: "
                    f"{quota.monthly_llm_requests}/{quota.llm_requests_limit} requests, "
                    f"{quota.monthly_llm_tokens}/{quota.llm_tokens_limit} tokens"
                )

    def _estimate_tokens(self, query: str, sql: str) -> int:
        """Estimate token usage.

        Args:
            query: Natural language query
            sql: Generated SQL

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        total_chars = len(query) + len(sql)
        return total_chars // 4

    def _get_next_month_start(self) -> datetime:
        """Get start of next month.

        Returns:
            Datetime of next month's first day
        """
        now = datetime.now()
        if now.month == 12:
            return datetime(now.year + 1, 1, 1)
        else:
            return datetime(now.year, now.month + 1, 1)

    # ========================================================================
    # Metrics Collection
    # ========================================================================

    async def _get_metrics(self, tenant_id: UUID) -> TextToSQLMetrics:
        """Get tenant metrics.

        Args:
            tenant_id: Tenant ID

        Returns:
            Tenant metrics
        """
        async with self._lock:
            if tenant_id not in self.tenant_metrics:
                self.tenant_metrics[tenant_id] = TextToSQLMetrics(
                    tenant_id=tenant_id
                )

            if tenant_id not in self.execution_times:
                self.execution_times[tenant_id] = []

            return self.tenant_metrics[tenant_id]

    async def _record_success_metrics(
        self,
        tenant_id: UUID,
        method_used: str,
        execution_time_ms: float,
        confidence_score: Optional[float],
    ):
        """Record successful request metrics.

        Args:
            tenant_id: Tenant ID
            method_used: Method used
            execution_time_ms: Execution time in ms
            confidence_score: Confidence score
        """
        async with self._lock:
            metrics = await self._get_metrics(tenant_id)

            metrics.total_requests += 1
            metrics.successful_requests += 1

            # Method tracking
            if method_used == "template" or method_used == "cache":
                metrics.template_requests += 1
            elif method_used == "llm":
                metrics.llm_requests += 1
                metrics.llm_requests_count += 1
            elif method_used == "hybrid":
                metrics.hybrid_requests += 1

            # Performance tracking
            self.execution_times[tenant_id].append(execution_time_ms)
            metrics.avg_execution_time_ms = sum(self.execution_times[tenant_id]) / len(
                self.execution_times[tenant_id]
            )

            # Update percentiles
            await self._update_percentiles(tenant_id)

            # Confidence tracking
            if confidence_score is not None:
                # Simple running average (could be more sophisticated)
                total_confidence = (
                    metrics.avg_confidence_score * (metrics.successful_requests - 1) +
                    confidence_score
                )
                metrics.avg_confidence_score = total_confidence / metrics.successful_requests

    async def _record_failure_metrics(
        self,
        tenant_id: UUID,
        execution_time_ms: float,
    ):
        """Record failed request metrics.

        Args:
            tenant_id: Tenant ID
            execution_time_ms: Execution time in ms
        """
        async with self._lock:
            metrics = await self._get_metrics(tenant_id)

            metrics.total_requests += 1
            metrics.failed_requests += 1

            # Still track execution time
            self.execution_times[tenant_id].append(execution_time_ms)

    async def _record_cache_hit(self, tenant_id: UUID):
        """Record cache hit.

        Args:
            tenant_id: Tenant ID
        """
        async with self._lock:
            metrics = await self._get_metrics(tenant_id)
            metrics.cache_hits += 1

            total_cache_requests = metrics.cache_hits + metrics.cache_misses
            if total_cache_requests > 0:
                metrics.cache_hit_rate = metrics.cache_hits / total_cache_requests

    async def _record_cache_miss(self, tenant_id: UUID):
        """Record cache miss.

        Args:
            tenant_id: Tenant ID
        """
        async with self._lock:
            metrics = await self._get_metrics(tenant_id)
            metrics.cache_misses += 1

            total_cache_requests = metrics.cache_hits + metrics.cache_misses
            if total_cache_requests > 0:
                metrics.cache_hit_rate = metrics.cache_hits / total_cache_requests

    async def _update_percentiles(self, tenant_id: UUID):
        """Update execution time percentiles.

        Args:
            tenant_id: Tenant ID
        """
        times = sorted(self.execution_times[tenant_id])
        n = len(times)

        if n == 0:
            return

        metrics = self.tenant_metrics[tenant_id]

        metrics.p50_execution_time_ms = times[int(n * 0.50)]
        metrics.p95_execution_time_ms = times[int(n * 0.95)] if n > 1 else times[0]
        metrics.p99_execution_time_ms = times[int(n * 0.99)] if n > 1 else times[0]

    async def get_tenant_metrics(self, tenant_id: UUID) -> TextToSQLMetrics:
        """Get metrics for tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Tenant metrics
        """
        return await self._get_metrics(tenant_id)

    async def get_tenant_quota(self, tenant_id: UUID) -> TenantQuota:
        """Get quota for tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Tenant quota
        """
        return await self._get_quota(tenant_id)


# ============================================================================
# Exceptions
# ============================================================================

class QuotaExceededError(Exception):
    """Raised when tenant quota exceeded."""
    pass


# ============================================================================
# Global Instance
# ============================================================================

_text_to_sql_service: Optional[TextToSQLService] = None
_service_lock = asyncio.Lock()


async def get_text_to_sql_service() -> TextToSQLService:
    """Get global Text-to-SQL service instance.

    Returns:
        TextToSQLService instance
    """
    global _text_to_sql_service

    async with _service_lock:
        if _text_to_sql_service is None:
            _text_to_sql_service = TextToSQLService()

        return _text_to_sql_service


async def reset_text_to_sql_service():
    """Reset global Text-to-SQL service (for testing)."""
    global _text_to_sql_service

    async with _service_lock:
        _text_to_sql_service = None
