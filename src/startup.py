"""Application Startup and Service Integration.

This module handles application initialization, service registration,
and background task startup for all integrated modules.
"""

import asyncio
import logging
import os
from typing import Optional

from fastapi import FastAPI

logger = logging.getLogger(__name__)


# =============================================================================
# Service Initialization
# =============================================================================

async def initialize_services(app: FastAPI):
    """Initialize all application services.

    This function is called on application startup and initializes:
    - AI Annotation services (security, performance, resilience, engines)
    - Text-to-SQL services (service layer, quality monitoring)
    - Health monitoring services
    - Background tasks

    Args:
        app: FastAPI application instance
    """
    logger.info("Initializing SuperInsight services...")

    # -------------------------------------------------------------------------
    # 1. AI Annotation Services
    # -------------------------------------------------------------------------

    # Security features
    if os.getenv("FEATURE_SECURITY_FEATURES", "true").lower() == "true":
        logger.info("Initializing AI Annotation security services...")
        # Audit service, RBAC, PII detection, tenant isolation
        # These are initialized on first use (lazy loading with singletons)

    # Performance optimization
    if os.getenv("FEATURE_PERFORMANCE_OPTIMIZATION", "true").lower() == "true":
        logger.info("Initializing AI Annotation performance services...")
        from src.ai.annotation_performance_optimizer import get_performance_optimizer

        processor = await get_performance_optimizer()
        logger.info(f"Batch processor initialized: "
                   f"batch_size={processor._config.batch_size}, "
                   f"concurrency={processor._config.max_concurrency}")

    # Error handling and resilience
    logger.info("Initializing error handling services...")
    from src.ai.annotation_resilience import (
        get_retry_service,
        get_failure_queue,
        get_notification_service,
    )

    retry_service = await get_retry_service()
    failure_queue = await get_failure_queue()
    notification_service = await get_notification_service()

    # Start network failure queue retry loop
    await failure_queue.start_retry_loop()
    logger.info("Network failure queue started")

    # Register error notification callbacks
    async def log_critical_error(error_record):
        logger.critical(
            f"Critical error: {error_record.error_message} "
            f"(category={error_record.category}, "
            f"operation={error_record.operation})"
        )

    await notification_service.register_notification_callback(log_critical_error)

    # Engine health monitoring
    logger.info("Initializing annotation engine health monitor...")
    from src.ai.annotation_engine_health import get_health_monitor, EngineType

    health_monitor = await get_health_monitor()

    # Register Label Studio engine if configured
    label_studio_url = os.getenv("LABEL_STUDIO_URL")
    if label_studio_url:
        await health_monitor.register_engine(
            engine_id="label-studio-main",
            engine_type=EngineType.LABEL_STUDIO,
            health_check_url=f"{label_studio_url}/health",
            timeout_seconds=5.0,
        )
        logger.info(f"Registered Label Studio engine: {label_studio_url}")

    # Register Argilla engine if configured
    argilla_url = os.getenv("ARGILLA_URL")
    if argilla_url:
        await health_monitor.register_engine(
            engine_id="argilla-main",
            engine_type=EngineType.ARGILLA,
            health_check_url=f"{argilla_url}/api/health",
            timeout_seconds=5.0,
        )
        logger.info(f"Registered Argilla engine: {argilla_url}")

    # Start health monitoring
    await health_monitor.start()
    logger.info("Engine health monitor started")

    # -------------------------------------------------------------------------
    # 2. Text-to-SQL Services
    # -------------------------------------------------------------------------

    if os.getenv("FEATURE_TEXT_TO_SQL", "true").lower() == "true":
        logger.info("Initializing Text-to-SQL services...")

        from src.text_to_sql.text_to_sql_service import get_text_to_sql_service

        text_to_sql_service = await get_text_to_sql_service()
        logger.info("Text-to-SQL service initialized")

        # Quality monitoring
        if os.getenv("FEATURE_QUALITY_MONITORING", "true").lower() == "true":
            from src.text_to_sql.quality_monitoring import get_quality_monitoring_service

            quality_monitor = await get_quality_monitoring_service()
            logger.info("Text-to-SQL quality monitoring initialized")

    # -------------------------------------------------------------------------
    # 3. Store services in app state for access in endpoints
    # -------------------------------------------------------------------------

    app.state.health_monitor = health_monitor
    app.state.retry_service = retry_service
    app.state.failure_queue = failure_queue
    app.state.notification_service = notification_service

    if os.getenv("FEATURE_TEXT_TO_SQL", "true").lower() == "true":
        app.state.text_to_sql_service = text_to_sql_service

    logger.info("✅ All services initialized successfully")


async def shutdown_services(app: FastAPI):
    """Shutdown all application services.

    This function is called on application shutdown and performs cleanup:
    - Stop background tasks
    - Close connections
    - Flush logs and metrics

    Args:
        app: FastAPI application instance
    """
    logger.info("Shutting down SuperInsight services...")

    # Stop health monitor
    if hasattr(app.state, "health_monitor"):
        await app.state.health_monitor.stop()
        logger.info("Health monitor stopped")

    # Stop network failure queue
    if hasattr(app.state, "failure_queue"):
        await app.state.failure_queue.stop_retry_loop()
        logger.info("Network failure queue stopped")

    logger.info("✅ All services shut down successfully")


# =============================================================================
# Application Lifespan
# =============================================================================

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.

    Handles startup and shutdown events for the entire application.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    logger.info("=" * 80)
    logger.info("SuperInsight Platform - Starting...")
    logger.info("=" * 80)

    await initialize_services(app)

    yield

    # Shutdown
    logger.info("=" * 80)
    logger.info("SuperInsight Platform - Shutting down...")
    logger.info("=" * 80)

    await shutdown_services(app)


# =============================================================================
# Health Check Endpoints
# =============================================================================

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

health_router = APIRouter(prefix="/health", tags=["Health"])


class HealthStatus(BaseModel):
    """Overall health status."""
    status: str
    version: str
    services: Dict[str, Any]


@health_router.get("", response_model=HealthStatus)
async def health_check():
    """Get overall application health status.

    Returns:
        Health status including all services
    """
    from src.ai.annotation_engine_health import get_health_monitor

    health_monitor = await get_health_monitor()

    # Get health status for all engines
    engine_statuses = {}
    all_statuses = await health_monitor.get_all_health_statuses()

    for engine_id, status in all_statuses.items():
        engine_statuses[engine_id] = {
            "status": status.status.value,
            "last_check": status.checked_at.isoformat(),
            "consecutive_failures": status.consecutive_failures,
        }

    # Determine overall status
    healthy_count = len(await health_monitor.get_healthy_engines())
    total_count = len(all_statuses)

    if healthy_count == total_count:
        overall_status = "healthy"
    elif healthy_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return HealthStatus(
        status=overall_status,
        version=os.getenv("APP_VERSION", "2.3.0"),
        services={
            "annotation_engines": engine_statuses,
            "healthy_engines": f"{healthy_count}/{total_count}",
        },
    )


@health_router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe.

    Returns:
        200 if ready, 503 if not ready
    """
    from src.ai.annotation_engine_health import get_health_monitor

    health_monitor = await get_health_monitor()
    healthy_engines = await health_monitor.get_healthy_engines()

    if len(healthy_engines) > 0:
        return {"status": "ready"}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="No healthy engines available")


@health_router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe.

    Returns:
        200 if alive
    """
    return {"status": "alive"}
