"""
Simplified FastAPI application for SuperInsight Platform.
This version disables complex initialization for Docker deployment.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from src.config.settings import settings
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Simple lifespan manager."""
    logger.info(f"Starting {settings.app.app_name}")
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

# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    try:
        db = get_db_session()
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
        "message": "SuperInsight API",
        "version": settings.app.app_version,
        "status": "running"
    }

# API info endpoint
@app.get("/api/info")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.app.app_name,
        "version": settings.app.app_version,
        "environment": settings.app.environment,
        "debug": settings.app.debug
    }

logger.info(f"FastAPI app initialized: {settings.app.app_name} v{settings.app.app_version}")
