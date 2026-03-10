"""
Data Transfer Monitoring Metrics

Provides metrics collection and logging helpers for the data transfer system:
- Transfer operation tracking (count, success/failure, duration)
- Approval workflow metrics
- Permission check latency
- Legacy API endpoint usage with deprecation warnings
- Batch transfer performance
"""

import logging
import time
from contextlib import contextmanager
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from src.monitoring.prometheus_metrics import (
    Counter,
    Histogram,
    Gauge,
    metrics_registry,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transfer operation metrics
# ---------------------------------------------------------------------------

transfer_total = metrics_registry.register(
    Counter(
        name="data_transfer_total",
        description="Total number of data transfer operations",
        labels=["source_type", "target_state", "status"],
    )
)

transfer_duration_seconds = metrics_registry.register(
    Histogram(
        name="data_transfer_duration_seconds",
        description="Duration of data transfer operations in seconds",
        labels=["source_type", "target_state"],
        buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    )
)

transfer_record_count = metrics_registry.register(
    Histogram(
        name="data_transfer_record_count",
        description="Number of records per transfer operation",
        labels=["source_type"],
        buckets=[1, 10, 50, 100, 500, 1000, 5000, 10000],
    )
)

# ---------------------------------------------------------------------------
# Approval workflow metrics
# ---------------------------------------------------------------------------

approval_requests_total = metrics_registry.register(
    Counter(
        name="data_transfer_approval_requests_total",
        description="Total approval requests created",
        labels=["requester_role", "target_state"],
    )
)

approval_processing_duration_seconds = metrics_registry.register(
    Histogram(
        name="data_transfer_approval_processing_seconds",
        description="Time from approval creation to resolution",
        labels=["status"],
        buckets=[60, 300, 3600, 86400, 259200, 604800],  # 1m to 7d
    )
)

approval_pending_count = metrics_registry.register(
    Gauge(
        name="data_transfer_approval_pending",
        description="Current number of pending approval requests",
    )
)

# ---------------------------------------------------------------------------
# Permission check metrics
# ---------------------------------------------------------------------------

permission_check_total = metrics_registry.register(
    Counter(
        name="data_transfer_permission_check_total",
        description="Total permission checks performed",
        labels=["user_role", "result"],
    )
)

permission_check_duration_seconds = metrics_registry.register(
    Histogram(
        name="data_transfer_permission_check_duration_seconds",
        description="Permission check latency in seconds",
        labels=["user_role"],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
    )
)

# ---------------------------------------------------------------------------
# Legacy API usage metrics
# ---------------------------------------------------------------------------

legacy_api_calls_total = metrics_registry.register(
    Counter(
        name="data_transfer_legacy_api_calls_total",
        description="Calls to deprecated legacy API endpoints",
        labels=["endpoint", "method"],
    )
)

legacy_api_last_called = metrics_registry.register(
    Gauge(
        name="data_transfer_legacy_api_last_called_timestamp",
        description="Unix timestamp of last call to a deprecated endpoint",
        labels=["endpoint"],
    )
)

# ---------------------------------------------------------------------------
# Batch transfer metrics
# ---------------------------------------------------------------------------

batch_transfer_total = metrics_registry.register(
    Counter(
        name="data_transfer_batch_total",
        description="Total batch transfer operations",
        labels=["status"],
    )
)

batch_transfer_size = metrics_registry.register(
    Histogram(
        name="data_transfer_batch_size",
        description="Number of individual transfers per batch request",
        buckets=[1, 5, 10, 25, 50, 100],
    )
)


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------


def record_transfer(
    source_type: str,
    target_state: str,
    record_count: int,
    success: bool,
    duration: float,
    user_id: Optional[str] = None,
) -> None:
    """Record a completed transfer operation."""
    status = "success" if success else "failure"
    labels = {
        "source_type": source_type,
        "target_state": target_state,
        "status": status,
    }
    transfer_total.inc(labels=labels)
    transfer_duration_seconds.observe(
        duration, labels={"source_type": source_type, "target_state": target_state}
    )
    transfer_record_count.observe(
        record_count, labels={"source_type": source_type}
    )

    log_data: Dict[str, Any] = {
        "event": "data_transfer",
        "source_type": source_type,
        "target_state": target_state,
        "record_count": record_count,
        "status": status,
        "duration_seconds": round(duration, 4),
    }
    if user_id:
        log_data["user_id"] = user_id

    if success:
        logger.info("Transfer completed", extra=log_data)
    else:
        logger.warning("Transfer failed", extra=log_data)


def record_approval_created(
    requester_role: str,
    target_state: str,
) -> None:
    """Record a new approval request."""
    approval_requests_total.inc(
        labels={"requester_role": requester_role, "target_state": target_state}
    )
    approval_pending_count.inc()
    logger.info(
        "Approval request created",
        extra={
            "event": "approval_created",
            "requester_role": requester_role,
            "target_state": target_state,
        },
    )


def record_approval_resolved(
    status: str,
    processing_seconds: float,
) -> None:
    """Record an approval resolution (approved / rejected / expired)."""
    approval_processing_duration_seconds.observe(
        processing_seconds, labels={"status": status}
    )
    approval_pending_count.dec()
    logger.info(
        "Approval resolved",
        extra={
            "event": "approval_resolved",
            "status": status,
            "processing_seconds": round(processing_seconds, 2),
        },
    )


def record_permission_check(
    user_role: str,
    allowed: bool,
    requires_approval: bool,
    duration: float,
) -> None:
    """Record a permission check result."""
    if allowed and not requires_approval:
        result = "allowed"
    elif allowed and requires_approval:
        result = "requires_approval"
    else:
        result = "denied"

    permission_check_total.inc(
        labels={"user_role": user_role, "result": result}
    )
    permission_check_duration_seconds.observe(
        duration, labels={"user_role": user_role}
    )


def record_legacy_api_call(
    endpoint: str,
    method: str = "POST",
) -> None:
    """Record a call to a deprecated legacy API endpoint.

    This should be called from the legacy endpoint handlers so we can
    track how often deprecated endpoints are still being used.
    """
    legacy_api_calls_total.inc(
        labels={"endpoint": endpoint, "method": method}
    )
    now_ts = datetime.now(timezone.utc).timestamp()
    legacy_api_last_called.set(now_ts, labels={"endpoint": endpoint})

    logger.warning(
        "Deprecated API endpoint called",
        extra={
            "event": "legacy_api_call",
            "endpoint": endpoint,
            "method": method,
            "deprecation_notice": (
                "This endpoint is deprecated and will be removed after "
                "the compatibility period. Migrate to POST /api/data-lifecycle/transfer."
            ),
        },
    )


def record_batch_transfer(
    total_requests: int,
    successful: int,
    failed: int,
    duration: float,
) -> None:
    """Record a batch transfer operation."""
    status = "success" if failed == 0 else ("partial" if successful > 0 else "failure")
    batch_transfer_total.inc(labels={"status": status})
    batch_transfer_size.observe(total_requests)

    logger.info(
        "Batch transfer completed",
        extra={
            "event": "batch_transfer",
            "total_requests": total_requests,
            "successful": successful,
            "failed": failed,
            "status": status,
            "duration_seconds": round(duration, 4),
        },
    )


@contextmanager
def track_transfer_duration(source_type: str, target_state: str):
    """Context manager to measure transfer duration.

    Usage::

        with track_transfer_duration("augmentation", "in_sample_library") as ctx:
            result = await service.transfer(request, user)
        ctx["record_count"] = len(request.records)
        ctx["success"] = True
    """
    ctx: Dict[str, Any] = {"success": False, "record_count": 0}
    start = time.monotonic()
    try:
        yield ctx
    finally:
        elapsed = time.monotonic() - start
        record_transfer(
            source_type=source_type,
            target_state=target_state,
            record_count=ctx.get("record_count", 0),
            success=ctx.get("success", False),
            duration=elapsed,
        )


# ---------------------------------------------------------------------------
# Legacy API usage summary
# ---------------------------------------------------------------------------


def get_legacy_api_usage_summary() -> Dict[str, Any]:
    """Return a summary of legacy API endpoint usage.

    Useful for dashboards and migration progress tracking.
    """
    collected = legacy_api_calls_total.collect()
    summary: Dict[str, int] = defaultdict(int)

    for metric in collected:
        labels = metric.get("labels", {})
        endpoint = labels.get("endpoint", "unknown")
        summary[endpoint] += int(metric.get("value", 0))

    return {
        "legacy_endpoints": dict(summary),
        "total_legacy_calls": sum(summary.values()),
        "migration_recommendation": (
            "All legacy endpoints should be migrated to "
            "POST /api/data-lifecycle/transfer before the "
            "compatibility period ends."
        ),
    }


# ---------------------------------------------------------------------------
# Convenience: get all data-transfer metrics at a glance
# ---------------------------------------------------------------------------


def get_transfer_metrics_summary() -> Dict[str, Any]:
    """Aggregate snapshot of all data-transfer related metrics."""
    return {
        "transfers": {
            "total": transfer_total.collect(),
            "duration": transfer_duration_seconds.collect(),
        },
        "approvals": {
            "total_requests": approval_requests_total.collect(),
            "pending": approval_pending_count.collect(),
        },
        "permissions": {
            "checks": permission_check_total.collect(),
        },
        "legacy_api": get_legacy_api_usage_summary(),
        "batch": {
            "total": batch_transfer_total.collect(),
        },
    }


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    # Metrics
    "transfer_total",
    "transfer_duration_seconds",
    "transfer_record_count",
    "approval_requests_total",
    "approval_processing_duration_seconds",
    "approval_pending_count",
    "permission_check_total",
    "permission_check_duration_seconds",
    "legacy_api_calls_total",
    "legacy_api_last_called",
    "batch_transfer_total",
    "batch_transfer_size",
    # Helpers
    "record_transfer",
    "record_approval_created",
    "record_approval_resolved",
    "record_permission_check",
    "record_legacy_api_call",
    "record_batch_transfer",
    "track_transfer_duration",
    # Summaries
    "get_legacy_api_usage_summary",
    "get_transfer_metrics_summary",
]
