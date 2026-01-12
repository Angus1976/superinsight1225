"""
Minimal FastAPI application for SuperInsight Platform.
This version includes only essential endpoints for testing.
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SuperInsight API - Minimal",
    version="2.3.0",
    description="Minimal SuperInsight API for testing"
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
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "message": "Minimal API is running"}
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "SuperInsight Minimal API",
        "version": "2.3.0",
        "status": "running",
        "features": ["health_check"]
    }

# Include auth API
try:
    from src.api.auth import router as auth_router
    app.include_router(auth_router)
    logger.info("Auth API loaded successfully")
except Exception as e:
    logger.error(f"Auth API failed to load: {e}")

# Include tasks API
try:
    from src.api.tasks import router as tasks_router
    app.include_router(tasks_router)
    logger.info("Tasks API loaded successfully")
except Exception as e:
    logger.error(f"Tasks API failed to load: {e}")

# Include dashboard API
try:
    from src.api.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
    logger.info("Dashboard API loaded successfully")
except Exception as e:
    logger.error(f"Dashboard API failed to load: {e}")

logger.info("Minimal FastAPI app initialized")