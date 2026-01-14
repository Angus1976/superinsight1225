"""
FastAPI application with authentication for SuperInsight Platform.
This version includes authentication endpoints but disables complex initialization.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from src.config.settings import settings
from src.database.connection import get_db_session

# Import API routers
from src.api.auth import router as auth_router
from src.api.metrics import router as metrics_router

logger = logging.getLogger(__name__)

# Import new API routers
try:
    from src.api.tasks import router as tasks_router
    TASKS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Tasks API not available: {e}")
    TASKS_AVAILABLE = False

try:
    from src.api.dashboard import router as dashboard_router
    DASHBOARD_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Dashboard API not available: {e}")
    DASHBOARD_AVAILABLE = False

try:
    from src.api.augmentation import router as augmentation_router
    AUGMENTATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Augmentation API not available: {e}")
    AUGMENTATION_AVAILABLE = False

try:
    from src.api.quality import router as quality_router
    QUALITY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Quality API not available: {e}")
    QUALITY_AVAILABLE = False

try:
    from src.api.security import router as security_router
    SECURITY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Security API not available: {e}")
    SECURITY_AVAILABLE = False

try:
    from src.api.data_sync import router as data_sync_router
    DATA_SYNC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Data Sync API not available: {e}")
    DATA_SYNC_AVAILABLE = False

try:
    from src.api.admin import router as admin_router
    ADMIN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Admin API not available: {e}")
    ADMIN_AVAILABLE = False

try:
    from src.api.billing import router as billing_router
    BILLING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Billing API not available: {e}")
    BILLING_AVAILABLE = False

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Simple lifespan manager."""
    logger.info(f"Starting {settings.app.app_name} with authentication")
    yield
    logger.info(f"Shutting down {settings.app.app_name}")

# Create FastAPI app
app = FastAPI(
    title=settings.app.app_name,
    version=settings.app.app_version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router)
app.include_router(metrics_router)

# Include new API routers if available
if TASKS_AVAILABLE:
    app.include_router(tasks_router)
    logger.info("Tasks API loaded successfully")

if DASHBOARD_AVAILABLE:
    app.include_router(dashboard_router)
    logger.info("Dashboard API loaded successfully")

if AUGMENTATION_AVAILABLE:
    app.include_router(augmentation_router)
    logger.info("Augmentation API loaded successfully")

if QUALITY_AVAILABLE:
    app.include_router(quality_router)
    logger.info("Quality API loaded successfully")

if SECURITY_AVAILABLE:
    app.include_router(security_router)
    logger.info("Security API loaded successfully")

if DATA_SYNC_AVAILABLE:
    app.include_router(data_sync_router)
    logger.info("Data Sync API loaded successfully")

if ADMIN_AVAILABLE:
    app.include_router(admin_router)
    logger.info("Admin API loaded successfully")

if BILLING_AVAILABLE:
    app.include_router(billing_router)
    logger.info("Billing API loaded successfully")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    try:
        db = next(get_db_session())
        db.close()
        return JSONResponse(
            status_code=200,
            content={"status": "healthy", "message": "API is running"}
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "SuperInsight API with Authentication",
        "version": settings.app.app_version,
        "status": "running",
        "features": ["authentication", "health_check", "tasks_management", "dashboard_metrics", "augmentation", "quality", "security", "data_sync", "admin"]
    }

# API info endpoint
@app.get("/api/info")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.app.app_name,
        "version": settings.app.app_version,
        "environment": settings.app.environment,
        "debug": settings.app.debug,
        "features": ["authentication", "health_check", "tasks_management", "dashboard_metrics", "augmentation", "quality", "security", "data_sync", "admin"]
    }

logger.info(f"FastAPI app with auth initialized: {settings.app.app_name} v{settings.app.app_version}")