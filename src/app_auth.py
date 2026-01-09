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
        "features": ["authentication", "health_check"]
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
        "features": ["authentication", "health_check"]
    }

logger.info(f"FastAPI app with auth initialized: {settings.app.app_name} v{settings.app.app_version}")