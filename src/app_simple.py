"""
Simple FastAPI application for SuperInsight Platform.
This version includes only basic endpoints without complex imports.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SuperInsight API - Simple",
    version="2.3.0",
    description="Simple SuperInsight API for testing"
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
        content={"status": "healthy", "message": "Simple API is running"}
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "SuperInsight Simple API",
        "version": "2.3.0",
        "status": "running",
        "features": ["health_check"]
    }

# Mock API endpoints for testing
@app.get("/api/v1/tasks")
async def list_tasks():
    """Mock tasks endpoint."""
    return {
        "items": [
            {
                "id": "task-1",
                "name": "Sample Task 1",
                "status": "pending",
                "priority": "medium"
            },
            {
                "id": "task-2", 
                "name": "Sample Task 2",
                "status": "in_progress",
                "priority": "high"
            }
        ],
        "total": 2,
        "page": 1,
        "size": 10
    }

@app.get("/api/v1/dashboard/metrics")
async def dashboard_metrics():
    """Mock dashboard metrics endpoint."""
    return {
        "tasks": {
            "total": 150,
            "pending": 45,
            "in_progress": 30,
            "completed": 75
        },
        "users": {
            "total": 25,
            "active": 18
        },
        "projects": {
            "total": 12,
            "active": 8
        }
    }

@app.get("/auth/me")
async def get_current_user():
    """Mock user profile endpoint."""
    return {
        "id": "user-1",
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "tenant_id": "default_tenant"
    }

logger.info("Simple FastAPI app initialized")