"""
FastAPI application for SuperInsight Platform.

Main web application with all API endpoints and system integration.
"""

import logging
import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import settings
from src.database.connection import init_database, test_database_connection, close_database
from src.system.integration import system_manager, system_lifespan
from src.system.error_handler import error_handler, ErrorCategory, ErrorSeverity
from src.system.monitoring import metrics_collector, performance_monitor, health_monitor, RequestTracker
from src.system.health import health_checker

# Import API routers
from src.api.extraction import router as extraction_router

logger = logging.getLogger(__name__)

# Middleware for request tracking and monitoring
class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for request monitoring and performance tracking."""
    
    async def dispatch(self, request: Request, call_next):
        # Start request tracking
        request_id = f"req_{int(asyncio.get_event_loop().time() * 1000)}"
        endpoint = f"{request.method} {request.url.path}"
        start_time = time.time()
        
        with RequestTracker(endpoint, request_id) as tracker:
            try:
                response = await call_next(request)
                tracker.set_status_code(response.status_code)
                
                # Track Prometheus metrics
                try:
                    from src.system.prometheus_exporter import prometheus_exporter
                    duration = time.time() - start_time
                    prometheus_exporter.track_http_request(
                        method=request.method,
                        endpoint=request.url.path,
                        status_code=response.status_code,
                        duration=duration
                    )
                except ImportError:
                    pass  # Prometheus exporter not available
                except Exception as e:
                    logger.warning(f"Failed to track Prometheus metrics: {e}")
                
                return response
            except Exception as e:
                tracker.set_status_code(500)
                
                # Track error in Prometheus
                try:
                    from src.system.prometheus_exporter import prometheus_exporter
                    duration = time.time() - start_time
                    prometheus_exporter.track_http_request(
                        method=request.method,
                        endpoint=request.url.path,
                        status_code=500,
                        duration=duration
                    )
                except ImportError:
                    pass
                except Exception:
                    pass  # Don't let metrics tracking break the request
                
                # Handle error through error handler
                error_handler.handle_error(
                    exception=e,
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.HIGH,
                    service_name="api",
                    request_id=request_id,
                    endpoint=endpoint
                )
                raise


async def register_system_services():
    """Register all system services with the integration manager."""
    
    # Database service
    def database_startup():
        init_database()
        if not test_database_connection():
            raise Exception("Database connection test failed")
    
    def database_shutdown():
        close_database()
    
    def database_health_check():
        return test_database_connection()
    
    system_manager.register_service(
        name="database",
        startup_func=database_startup,
        shutdown_func=database_shutdown,
        health_check=database_health_check,
        service_type="core"
    )
    
    # Metrics collection service
    async def metrics_startup():
        await metrics_collector.start_collection()
    
    async def metrics_shutdown():
        await metrics_collector.stop_collection()
    
    system_manager.register_service(
        name="metrics",
        startup_func=metrics_startup,
        shutdown_func=metrics_shutdown,
        dependencies=["database"],
        service_type="monitoring"
    )
    
    # Health monitoring service
    def health_startup():
        # Set up health monitoring thresholds
        health_monitor.set_threshold("system.cpu.usage_percent", warning=80.0, critical=95.0)
        health_monitor.set_threshold("system.memory.usage_percent", warning=85.0, critical=95.0)
        health_monitor.set_threshold("system.disk.usage_percent", warning=85.0, critical=95.0)
    
    system_manager.register_service(
        name="health_monitor",
        startup_func=health_startup,
        dependencies=["metrics"],
        service_type="monitoring"
    )
    
    # Try to register optional services
    try:
        from src.api.quality import router as quality_router
        
        def quality_service_startup():
            logger.info("Quality management service initialized")
        
        system_manager.register_service(
            name="quality_service",
            startup_func=quality_service_startup,
            dependencies=["database"],
            service_type="feature"
        )
        
    except ImportError:
        logger.warning("Quality management service not available")
    
    try:
        from src.api.ai_annotation import router as ai_router
        
        def ai_service_startup():
            logger.info("AI annotation service initialized")
        
        system_manager.register_service(
            name="ai_service",
            startup_func=ai_service_startup,
            dependencies=["database"],
            service_type="feature"
        )
        
    except ImportError:
        logger.warning("AI annotation service not available")
    
    try:
        from src.api.billing import router as billing_router
        
        def billing_service_startup():
            logger.info("Billing service initialized")
        
        system_manager.register_service(
            name="billing_service",
            startup_func=billing_service_startup,
            dependencies=["database"],
            service_type="feature"
        )
        
    except ImportError:
        logger.warning("Billing service not available")
    
    try:
        from src.api.security import router as security_router
        
        def security_service_startup():
            logger.info("Security service initialized")
        
        system_manager.register_service(
            name="security_service",
            startup_func=security_service_startup,
            dependencies=["database"],
            service_type="security"
        )
        
    except ImportError:
        logger.warning("Security service not available")
    
    try:
        from src.system.business_metrics import business_metrics_collector
        
        async def business_metrics_startup():
            await business_metrics_collector.start_collection()
            logger.info("Business metrics collection service initialized")
        
        async def business_metrics_shutdown():
            await business_metrics_collector.stop_collection()
        
        system_manager.register_service(
            name="business_metrics",
            startup_func=business_metrics_startup,
            shutdown_func=business_metrics_shutdown,
            dependencies=["database", "metrics"],
            service_type="monitoring"
        )
        
    except ImportError:
        logger.warning("Business metrics service not available")
    
    # Complete Event Capture System (100% Security Event Capture)
    try:
        from src.security.complete_event_capture_system import initialize_complete_capture_system
        from src.security.security_event_monitor import get_security_monitor
        from src.security.threat_detector import get_threat_detector
        
        async def complete_capture_startup():
            security_monitor = get_security_monitor()
            threat_detector = get_threat_detector()
            
            if security_monitor and threat_detector:
                capture_system = await initialize_complete_capture_system(
                    security_monitor, threat_detector
                )
                logger.info("Complete Event Capture System initialized successfully")
                return capture_system
            else:
                logger.warning("Security monitor or threat detector not available for complete capture")
        
        async def complete_capture_shutdown():
            from src.security.complete_event_capture_system import get_complete_capture_system
            capture_system = get_complete_capture_system()
            if capture_system:
                await capture_system.stop_capture_system()
                logger.info("Complete Event Capture System shutdown successfully")
        
        system_manager.register_service(
            name="complete_event_capture",
            startup_func=complete_capture_startup,
            shutdown_func=complete_capture_shutdown,
            dependencies=["database", "security_service"],
            service_type="security"
        )
        
    except ImportError:
        logger.warning("Complete Event Capture System not available")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with system integration."""
    # Startup
    logger.info(f"Starting {settings.app.app_name} v{settings.app.app_version}")
    
    try:
        # Simplified startup - skip service orchestration for now
        # Just initialize database connection
        init_database()
        if test_database_connection():
            logger.info("Database connection established")
        else:
            logger.warning("Database connection test failed")
        
        logger.info("Application startup completed (simplified mode)")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application")
        close_database()

# Create FastAPI application
app = FastAPI(
    title="SuperInsight AI 数据治理与标注平台",
    description="企业级 AI 语料治理与智能标注平台 API",
    version=settings.app.app_version,
    debug=settings.app.debug,
    lifespan=lifespan
)

# Add monitoring middleware
app.add_middleware(MonitoringMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add automatic desensitization middleware
try:
    from src.security.auto_desensitization_middleware import AutoDesensitizationMiddleware
    app.add_middleware(
        AutoDesensitizationMiddleware,
        enabled=True,
        mask_requests=True,
        mask_responses=True,
        excluded_paths=[
            "/health", "/metrics", "/docs", "/openapi.json", "/static", "/favicon.ico",
            "/system/status", "/system/metrics", "/system/services"
        ]
    )
    logger.info("Automatic desensitization middleware loaded successfully")
except ImportError as e:
    logger.warning(f"Automatic desensitization middleware not available: {e}")
except Exception as e:
    logger.warning(f"Automatic desensitization middleware failed to load: {e}")

# Add i18n middleware
try:
    from src.i18n.middleware import language_middleware
    app.middleware("http")(language_middleware)
    logger.info("i18n middleware loaded successfully")
except ImportError as e:
    logger.warning(f"i18n middleware not available: {e}")
except Exception as e:
    logger.warning(f"i18n middleware failed to load: {e}")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with error tracking."""
    logger.error(f"Unhandled exception: {exc}")
    
    # Handle through error handler
    error_context = error_handler.handle_error(
        exception=exc,
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.HIGH,
        service_name="api",
        endpoint=f"{request.method} {request.url.path}"
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_context.error_id,
            "message": str(exc) if settings.app.debug else "An error occurred"
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint for Docker."""
    try:
        # Simple health check - just verify database connection
        if test_database_connection():
            return JSONResponse(
                status_code=200,
                content={"status": "healthy", "message": "API is running"}
            )
        else:
            logger.error("Database health check failed")
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "error": "Database connection failed"}
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


# Liveness probe endpoint (for Kubernetes/container orchestration)
@app.get("/health/live")
async def liveness_probe():
    """Liveness probe - checks if application is running."""
    return {
        "status": "alive",
        "timestamp": asyncio.get_event_loop().time()
    }


# Readiness probe endpoint (for Kubernetes/container orchestration)
@app.get("/health/ready")
async def readiness_probe():
    """Readiness probe - checks if application is ready to serve traffic."""
    try:
        # Check critical services
        db_healthy = test_database_connection()
        system_status = system_manager.get_system_status()
        
        is_ready = db_healthy and system_status["overall_status"] == "healthy"
        
        return JSONResponse(
            status_code=200 if is_ready else 503,
            content={
                "status": "ready" if is_ready else "not_ready",
                "database": "connected" if db_healthy else "disconnected",
                "services": system_status["overall_status"]
            }
        )
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "error": str(e)
            }
        )


# System status endpoint
@app.get("/system/status")
async def system_status():
    """Get comprehensive system status."""
    try:
        return {
            "system": system_manager.get_system_status(),
            "metrics": metrics_collector.get_all_metrics_summary(),
            "performance": performance_monitor.get_performance_summary(),
            "errors": error_handler.get_error_statistics()
        }
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Metrics endpoint
@app.get("/system/metrics")
async def system_metrics():
    """Get system metrics."""
    try:
        return metrics_collector.get_all_metrics_summary()
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Prometheus metrics endpoint
@app.get("/metrics")
async def prometheus_metrics():
    """Get metrics in Prometheus format."""
    try:
        from src.system.prometheus_exporter import prometheus_exporter
        return prometheus_exporter.get_metrics_response()
    except Exception as e:
        logger.error(f"Failed to get Prometheus metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Service status endpoint
@app.get("/system/services")
async def services_status():
    """Get status of all registered services."""
    try:
        return system_manager.get_system_status()
    except Exception as e:
        logger.error(f"Failed to get services status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Service-specific status endpoint
@app.get("/system/services/{service_name}")
async def service_status(service_name: str):
    """Get status of a specific service."""
    try:
        status = system_manager.get_service_status(service_name)
        if status is None:
            return JSONResponse(
                status_code=404,
                content={"error": f"Service '{service_name}' not found"}
            )
        return status
    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app.app_name,
        "version": settings.app.app_version,
        "description": "SuperInsight AI 数据治理与标注平台 API",
        "docs_url": "/docs",
        "health_url": "/health"
    }


# Include routers
app.include_router(extraction_router)

# Include tasks API router
try:
    from src.api.tasks import router as tasks_router
    app.include_router(tasks_router)
    logger.info("Tasks API loaded successfully")
except ImportError as e:
    logger.error(f"Tasks API not available: {e}")
except Exception as e:
    logger.error(f"Tasks API failed to load: {e}")

# Include dashboard API router
try:
    from src.api.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
    logger.info("Dashboard API loaded successfully")
except ImportError as e:
    logger.error(f"Dashboard API not available: {e}")
except Exception as e:
    logger.error(f"Dashboard API failed to load: {e}")

# Include SOX Compliance API router - critical for compliance functionality
try:
    from src.api.sox_compliance_api import router as sox_compliance_router
    app.include_router(sox_compliance_router)
    logger.info("SOX Compliance API loaded successfully")
except ImportError as e:
    logger.error(f"SOX Compliance API not available: {e}")
except Exception as e:
    logger.error(f"SOX Compliance API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include comprehensive audit integration
try:
    from src.security.comprehensive_audit_integration import comprehensive_audit
    comprehensive_audit.integrate_with_fastapi(app)
    logger.info("Comprehensive audit system integrated successfully")
except Exception as e:
    logger.error(f"Failed to integrate comprehensive audit system: {e}")
    import traceback
    traceback.print_exc()

# Include admin router
try:
    from src.api.admin import router as admin_router
    app.include_router(admin_router)
    logger.info("Admin API loaded successfully")
except Exception as e:
    logger.error(f"Admin API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include auth router - CRITICAL for login functionality
try:
    from src.api.auth import router as auth_router
    app.include_router(auth_router)
    logger.info("Auth API loaded successfully")
except Exception as e:
    logger.error(f"Auth API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include enhanced admin router
try:
    from src.api.admin_enhanced import router as admin_enhanced_router
    app.include_router(admin_enhanced_router)
    logger.info("Enhanced Admin API loaded successfully")
except Exception as e:
    logger.error(f"Enhanced Admin API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Force include security router
try:
    from src.api.security import router as security_router
    app.include_router(security_router)
    logger.info("Security API loaded successfully")
except Exception as e:
    logger.error(f"Security API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Force include audit API router
try:
    from src.api.audit_api import router as audit_router
    app.include_router(audit_router)
    logger.info("Audit API loaded successfully")
except Exception as e:
    logger.error(f"Audit API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Force include audit integrity API router
try:
    from src.api.audit_integrity_api import router as audit_integrity_router
    app.include_router(audit_integrity_router)
    logger.info("Audit Integrity API loaded successfully")
except Exception as e:
    logger.error(f"Audit Integrity API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include business metrics router - required for dashboard
try:
    from src.api.business_metrics import router as business_metrics_router
    app.include_router(business_metrics_router)
    logger.info("Business metrics API loaded successfully")
except Exception as e:
    logger.error(f"Business metrics API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include metrics router (alternative business metrics)
try:
    from src.api.metrics import router as metrics_router
    app.include_router(metrics_router)
    logger.info("Metrics API loaded successfully")
except Exception as e:
    logger.error(f"Metrics API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include dashboard router
try:
    from src.api.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
    logger.info("Dashboard API loaded successfully")
except Exception as e:
    logger.error(f"Dashboard API failed to load: {e}")
    import traceback
    traceback.print_exc()

# Include workspace router for multi-tenant support
try:
    from src.api.workspace import router as workspace_router
    app.include_router(workspace_router)
    logger.info("Workspace API loaded successfully")
except Exception as e:
    logger.warning(f"Workspace API not available: {e}")

# Dynamically include available API routers
async def include_optional_routers():
    """Include optional API routers if available."""
    
    # Quality management router
    try:
        from src.api.quality import router as quality_router
        app.include_router(quality_router)
        logger.info("Quality management API loaded successfully")
    except ImportError as e:
        logger.warning(f"Quality management API not available: {e}")
    except Exception as e:
        logger.warning(f"Quality management API failed to load: {e}")
    
    # AI annotation router
    try:
        from src.api.ai_annotation import router as ai_router
        app.include_router(ai_router)
        logger.info("AI annotation API loaded successfully")
    except ImportError as e:
        logger.warning(f"AI annotation API not available: {e}")
    except Exception as e:
        logger.warning(f"AI annotation API failed to load: {e}")
    
    # Billing router
    try:
        from src.api.billing import router as billing_router
        app.include_router(billing_router)
        logger.info("Billing API loaded successfully")
    except ImportError as e:
        logger.warning(f"Billing API not available: {e}")
    except Exception as e:
        logger.warning(f"Billing API failed to load: {e}")

    # Ticket management router
    try:
        from src.api.ticket_api import router as ticket_router
        app.include_router(ticket_router)
        logger.info("Ticket management API loaded successfully")
    except ImportError as e:
        logger.warning(f"Ticket management API not available: {e}")
    except Exception as e:
        logger.warning(f"Ticket management API failed to load: {e}")

    # Performance evaluation router
    try:
        from src.api.evaluation_api import router as evaluation_router
        app.include_router(evaluation_router)
        logger.info("Performance evaluation API loaded successfully")
    except ImportError as e:
        logger.warning(f"Performance evaluation API not available: {e}")
    except Exception as e:
        logger.warning(f"Performance evaluation API failed to load: {e}")

    # Quality analysis router (trends, auto-retrain, pricing, incentives)
    try:
        from src.api.quality_api import router as quality_analysis_router
        app.include_router(quality_analysis_router)
        logger.info("Quality analysis API loaded successfully")
    except ImportError as e:
        logger.warning(f"Quality analysis API not available: {e}")
    except Exception as e:
        logger.warning(f"Quality analysis API failed to load: {e}")

    # Quality monitoring router (dashboard, alerts, anomalies)
    try:
        from src.api.monitoring_api import router as monitoring_router
        app.include_router(monitoring_router)
        logger.info("Quality monitoring API loaded successfully")
    except ImportError as e:
        logger.warning(f"Quality monitoring API not available: {e}")
    except Exception as e:
        logger.warning(f"Quality monitoring API failed to load: {e}")

    # Enhancement router
    try:
        from src.api.enhancement import router as enhancement_router
        app.include_router(enhancement_router)
        logger.info("Enhancement API loaded successfully")
    except ImportError as e:
        logger.warning(f"Enhancement API not available: {e}")
    except Exception as e:
        logger.warning(f"Enhancement API failed to load: {e}")
    
    # Export router
    try:
        from src.api.export import router as export_router
        app.include_router(export_router)
        logger.info("Export API loaded successfully")
    except ImportError as e:
        logger.warning(f"Export API not available: {e}")
    except Exception as e:
        logger.warning(f"Export API failed to load: {e}")
    
    # RAG Agent router
    try:
        from src.api.rag_agent import router as rag_router
        app.include_router(rag_router)
        logger.info("RAG Agent API loaded successfully")
    except ImportError as e:
        logger.warning(f"RAG Agent API not available: {e}")
    except Exception as e:
        logger.warning(f"RAG Agent API failed to load: {e}")
    
    # Security router
    try:
        from src.api.security import router as security_router
        app.include_router(security_router)
        logger.info("Security API loaded successfully")
    except ImportError as e:
        logger.warning(f"Security API not available: {e}")
    except Exception as e:
        logger.warning(f"Security API failed to load: {e}")
    
    # Collaboration router
    try:
        from src.api.collaboration import router as collaboration_router
        app.include_router(collaboration_router)
        logger.info("Collaboration API loaded successfully")
    except ImportError as e:
        logger.warning(f"Collaboration API not available: {e}")
    except Exception as e:
        logger.warning(f"Collaboration API failed to load: {e}")
    
    # Business metrics router
    try:
        from src.api.business_metrics import router as business_metrics_router
        app.include_router(business_metrics_router)
        logger.info("Business metrics API loaded successfully")
    except ImportError as e:
        logger.warning(f"Business metrics API not available: {e}")
    except Exception as e:
        logger.warning(f"Business metrics API failed to load: {e}")

    # Text-to-SQL router
    try:
        from src.api.text_to_sql import router as text_to_sql_router
        app.include_router(text_to_sql_router)
        logger.info("Text-to-SQL API loaded successfully")
    except ImportError as e:
        logger.warning(f"Text-to-SQL API not available: {e}")
    except Exception as e:
        logger.warning(f"Text-to-SQL API failed to load: {e}")

    # Knowledge Graph router
    try:
        from src.knowledge_graph.api.knowledge_graph_api import router as knowledge_graph_router
        app.include_router(knowledge_graph_router)
        logger.info("Knowledge Graph API loaded successfully")
    except ImportError as e:
        logger.warning(f"Knowledge Graph API not available: {e}")
    except Exception as e:
        logger.warning(f"Knowledge Graph API failed to load: {e}")

    # i18n router
    try:
        from src.api.i18n import router as i18n_router
        app.include_router(i18n_router)
        logger.info("i18n API loaded successfully")
    except ImportError as e:
        logger.warning(f"i18n API not available: {e}")
    except Exception as e:
        logger.warning(f"i18n API failed to load: {e}")

    # Compliance Reports API
    try:
        from src.api.compliance_reports import router as compliance_router
        app.include_router(compliance_router)
        logger.info("Compliance Reports API loaded successfully")
    except ImportError as e:
        logger.warning(f"Compliance Reports API not available: {e}")
    except Exception as e:
        logger.warning(f"Compliance Reports API failed to load: {e}")
    
    # SOX Compliance API - moved to main app setup for immediate availability
    # This is handled in the main app setup section below

    # Desensitization API (if not already included)
    try:
        from src.api.desensitization import router as desensitization_router
        app.include_router(desensitization_router)
        logger.info("Desensitization API loaded successfully")
    except ImportError as e:
        logger.warning(f"Desensitization API not available: {e}")
    except Exception as e:
        logger.warning(f"Desensitization API failed to load: {e}")

    # Auto-Desensitization API
    try:
        from src.api.auto_desensitization import router as auto_desensitization_router
        app.include_router(auto_desensitization_router)
        logger.info("Auto-Desensitization API loaded successfully")
    except ImportError as e:
        logger.warning(f"Auto-Desensitization API not available: {e}")
    except Exception as e:
        logger.warning(f"Auto-Desensitization API failed to load: {e}")

    # Real-time Alert API
    try:
        from src.api.real_time_alert_api import router as real_time_alert_router
        app.include_router(real_time_alert_router)
        logger.info("Real-time Alert API loaded successfully")
    except ImportError as e:
        logger.warning(f"Real-time Alert API not available: {e}")
    
    # Security Monitoring API (if not already included)
    try:
        from src.api.security_monitoring_api import router as security_monitoring_router
        app.include_router(security_monitoring_router)
        logger.info("Security Monitoring API loaded successfully")
    except ImportError as e:
        logger.warning(f"Security Monitoring API not available: {e}")
    except Exception as e:
        logger.warning(f"Security Monitoring API failed to load: {e}")

    # Permission Monitoring API (if not already included)
    try:
        from src.api.permission_monitoring import router as permission_monitoring_router
        app.include_router(permission_monitoring_router)
        logger.info("Permission Monitoring API loaded successfully")
    except ImportError as e:
        logger.warning(f"Permission Monitoring API not available: {e}")
    except Exception as e:
        logger.warning(f"Permission Monitoring API failed to load: {e}")

    # Cache Management API (if not already included)
    try:
        from src.api.cache_management import router as cache_management_router
        app.include_router(cache_management_router)
        logger.info("Cache Management API loaded successfully")
    except ImportError as e:
        logger.warning(f"Cache Management API not available: {e}")
    except Exception as e:
        logger.warning(f"Cache Management API failed to load: {e}")

    # Security Dashboard API (if not already included)
    try:
        from src.api.security_dashboard_api import router as security_dashboard_router
        app.include_router(security_dashboard_router)
        logger.info("Security Dashboard API loaded successfully")
    except ImportError as e:
        logger.warning(f"Security Dashboard API not available: {e}")
    except Exception as e:
        logger.warning(f"Security Dashboard API failed to load: {e}")
    
    # Zero Leakage Prevention API
    try:
        from src.api.zero_leakage_api import router as zero_leakage_router
        app.include_router(zero_leakage_router)
        logger.info("Zero Leakage Prevention API loaded successfully")
    except ImportError as e:
        logger.warning(f"Zero Leakage Prevention API not available: {e}")
    except Exception as e:
        logger.warning(f"Zero Leakage Prevention API failed to load: {e}")
    
    # Compliance Performance API (< 30 seconds target)
    try:
        from src.api.compliance_performance_api import router as compliance_performance_router
        app.include_router(compliance_performance_router)
        logger.info("Compliance Performance API loaded successfully")
    except ImportError as e:
        logger.warning(f"Compliance Performance API not available: {e}")
    except Exception as e:
        logger.warning(f"Compliance Performance API failed to load: {e}")
    
    # Complete Event Capture API (100% Security Event Capture)
    try:
        from src.api.complete_event_capture_api import router as complete_capture_router
        app.include_router(complete_capture_router)
        logger.info("Complete Event Capture API loaded successfully")
    except ImportError as e:
        logger.warning(f"Complete Event Capture API not available: {e}")
    except Exception as e:
        logger.warning(f"Complete Event Capture API failed to load: {e}")
    
    # GDPR Compliance Verification API
    try:
        from src.api.gdpr_verification_api import router as gdpr_verification_router
        app.include_router(gdpr_verification_router)
        logger.info("GDPR Compliance Verification API loaded successfully")
    except ImportError as e:
        logger.warning(f"GDPR Compliance Verification API not available: {e}")
    except Exception as e:
        logger.warning(f"GDPR Compliance Verification API failed to load: {e}")

    # Quality Governance API (Quality Workflow Module)
    try:
        from src.api.quality_governance_api import router as quality_governance_router
        app.include_router(quality_governance_router)
        logger.info("Quality Governance API loaded successfully")
    except ImportError as e:
        logger.warning(f"Quality Governance API not available: {e}")
    except Exception as e:
        logger.warning(f"Quality Governance API failed to load: {e}")

# Include ISO 27001 Compliance API router - comprehensive information security management
try:
    from src.api.iso27001_compliance_api import router as iso27001_compliance_router
    app.include_router(iso27001_compliance_router)
    logger.info("ISO 27001 Compliance API loaded successfully")
except ImportError as e:
    logger.warning(f"ISO 27001 Compliance API not available: {e}")
except Exception as e:
    logger.warning(f"ISO 27001 Compliance API failed to load: {e}")

# Include Data Protection Compliance API router - multi-regulation data protection compliance
try:
    from src.api.data_protection_compliance_api import router as data_protection_compliance_router
    app.include_router(data_protection_compliance_router)
    logger.info("Data Protection Compliance API loaded successfully")
except ImportError as e:
    logger.warning(f"Data Protection Compliance API not available: {e}")
except Exception as e:
    logger.warning(f"Data Protection Compliance API failed to load: {e}")

# Include Industry-Specific Compliance API router - HIPAA, PCI-DSS, PIPL, etc.
try:
    from src.api.industry_compliance_api import router as industry_compliance_router
    app.include_router(industry_compliance_router)
    logger.info("Industry-Specific Compliance API loaded successfully")
except ImportError as e:
    logger.warning(f"Industry-Specific Compliance API not available: {e}")
except Exception as e:
    logger.warning(f"Industry-Specific Compliance API failed to load: {e}")

# Include Version Control API router - data version management
try:
    from src.api.version_api import router as version_router
    app.include_router(version_router)
    logger.info("Version Control API loaded successfully")
except ImportError as e:
    logger.warning(f"Version Control API not available: {e}")
except Exception as e:
    logger.warning(f"Version Control API failed to load: {e}")

# Include Data Lineage API router - lineage tracking and impact analysis
try:
    from src.api.lineage_api import router as lineage_router
    app.include_router(lineage_router)
    logger.info("Data Lineage API loaded successfully")
except ImportError as e:
    logger.warning(f"Data Lineage API not available: {e}")
except Exception as e:
    logger.warning(f"Data Lineage API failed to load: {e}")

# LLM Integration API
try:
    from src.api.llm import router as llm_router
    app.include_router(llm_router)
    logger.info("LLM Integration API loaded successfully")
except ImportError as e:
    logger.warning(f"LLM Integration API not available: {e}")
except Exception as e:
    logger.warning(f"LLM Integration API failed to load: {e}")

# Multi-Tenant Workspace API
try:
    from src.api.multi_tenant import router as multi_tenant_router
    app.include_router(multi_tenant_router)
    logger.info("Multi-Tenant Workspace API loaded successfully")
except ImportError as e:
    logger.warning(f"Multi-Tenant Workspace API not available: {e}")
except Exception as e:
    logger.warning(f"Multi-Tenant Workspace API failed to load: {e}")


# Include routers on startup
# Startup event temporarily disabled for debugging
# @app.on_event("startup")
# async def startup_event():
#     """Application startup event."""
#     logger.info("Starting SuperInsight application...")
#     await include_optional_routers()
#     logger.info("SuperInsight application startup completed")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down SuperInsight application...")
    
    # Shutdown real-time alert system
    try:
        from src.security.alert_system_startup import shutdown_real_time_alerts
        alert_success = await shutdown_real_time_alerts()
        if alert_success:
            logger.info("Real-time alert system shutdown successfully")
        else:
            logger.warning("Real-time alert system failed to shutdown cleanly")
    except Exception as e:
        logger.error(f"Failed to shutdown real-time alerts: {e}")
    
    logger.info("SuperInsight application shutdown completed")


# Additional API information
@app.get("/api/info")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.app.app_name,
        "version": settings.app.app_version,
        "endpoints": {
            "extraction": "/api/v1/extraction",
            "quality": "/api/quality",
            "quality_analysis": "/api/v1/quality",
            "monitoring": "/api/v1/monitoring",
            "ai_annotation": "/api/ai",
            "billing": "/api/billing",
            "ticket": "/api/v1/tickets",
            "evaluation": "/api/v1/evaluation",
            "enhancement": "/api/enhancement",
            "export": "/api/export",
            "rag_agent": "/api/rag",
            "security": "/api/security",
            "audit": "/api/audit",
            "collaboration": "/api/collaboration",
            "business_metrics": "/api/business-metrics",
            "text_to_sql": "/api/v1/text-to-sql",
            "knowledge_graph": "/api/v1/knowledge-graph",
            "i18n": "/api/i18n",
            "desensitization": "/api/desensitization",
            "auto_desensitization": "/api/auto-desensitization",
            "zero_leakage": "/api/zero-leakage",
            "compliance_reports": "/api/compliance",
            "compliance_performance": "/api/compliance/performance",
            "complete_event_capture": "/api/v1/security/capture",
            "data_protection_compliance": "/api/data-protection-compliance",
            "language_settings": "/api/settings/language",
            "multi_tenant": "/api/v1/tenants",
            "workspaces": "/api/v1/workspaces",
            "quotas": "/api/v1/quotas",
            "shares": "/api/v1/shares",
            "admin": "/api/v1/admin",
            "health": "/health",
            "system_status": "/system/status",
            "metrics": "/system/metrics",
            "services": "/system/services",
            "docs": "/docs"
        },
        "features": [
            "安全数据提取 (Database, File, Web, API)",
            "批量数据处理",
            "异步任务处理",
            "进度跟踪",
            "多格式支持 (PDF, DOCX, HTML, JSON)",
            "数据库支持 (MySQL, PostgreSQL, Oracle)",
            "质量管理与评估 (Ragas 集成)",
            "质量工单管理",
            "数据修复功能",
            "AI 预标注服务",
            "计费结算系统",
            "数据增强与重构",
            "多格式数据导出",
            "RAG 和 Agent 测试接口",
            "Text-to-SQL 自然语言查询",
            "知识图谱 (Neo4j 图数据库)",
            "实体抽取与关系挖掘 (spaCy + jieba)",
            "图查询与智能推理",
            "安全控制与权限管理",
            "企业级审计日志系统",
            "审计事件查询与导出",
            "风险评估与威胁检测",
            "安全监控与告警",
            "合规报告生成",
            "敏感数据自动检测与脱敏",
            "实时数据脱敏中间件",
            "批量数据脱敏处理",
            "脱敏质量验证与监控",
            "脱敏策略管理",
            "系统监控与健康检查",
            "统一错误处理",
            "性能指标收集",
            "业务指标监控 (标注效率、用户活跃度、AI 性能)",
            "实时业务分析与趋势预测",
            "智能工单派发 (技能匹配、负载均衡)",
            "SLA 监控与告警",
            "绩效考核与申诉",
            "质量趋势分析与预测",
            "自动重训练触发",
            "质量驱动计费",
            "激励与惩罚机制",
            "实时质量监控仪表盘",
            "异常检测与告警",
            "培训需求分析",
            "客户反馈收集与情感分析",
            "多语言支持 (中文/英文)",
            "动态语言切换",
            "国际化 (i18n) API"
        ],
        "deployment_modes": [
            "腾讯云 TCB 云托管",
            "Docker Compose 私有化部署",
            "混合云部署"
        ],
        "system_status": system_manager.get_system_status()["overall_status"]
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.debug,
        log_level=settings.app.log_level.lower()
    )