"""
Completely isolated FastAPI application for SuperInsight Platform.
This version doesn't import any complex SuperInsight modules.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SuperInsight API - Isolated",
    version="2.3.0",
    description="Isolated SuperInsight API for testing"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple models
class User(BaseModel):
    id: str
    username: str
    email: str
    role: str
    tenant_id: str

class Task(BaseModel):
    id: str
    name: str
    status: str
    priority: str
    assignee_id: Optional[str] = None

class TaskListResponse(BaseModel):
    items: List[Task]
    total: int
    page: int
    size: int

class DashboardMetrics(BaseModel):
    tasks: dict
    users: dict
    projects: dict

# Mock current user dependency
async def get_current_user() -> User:
    """Mock current user for testing."""
    return User(
        id="user-1",
        username="admin",
        email="admin@example.com",
        role="admin",
        tenant_id="default_tenant"
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "message": "Isolated API is running"}
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "SuperInsight Isolated API",
        "version": "2.3.0",
        "status": "running",
        "features": ["health_check", "tasks", "dashboard", "auth"]
    }

# Auth endpoints
@app.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user

# Tasks endpoints
@app.get("/api/v1/tasks", response_model=TaskListResponse)
async def list_tasks(
    page: int = 1,
    size: int = 10,
    current_user: User = Depends(get_current_user)
):
    """List tasks with pagination."""
    mock_tasks = [
        Task(
            id="task-1",
            name="Customer Reviews Analysis",
            status="pending",
            priority="high",
            assignee_id="user-2"
        ),
        Task(
            id="task-2",
            name="Product Description Annotation",
            status="in_progress",
            priority="medium",
            assignee_id="user-3"
        ),
        Task(
            id="task-3",
            name="Support Ticket Classification",
            status="completed",
            priority="low",
            assignee_id="user-1"
        )
    ]
    
    # Simple pagination
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paginated_tasks = mock_tasks[start_idx:end_idx]
    
    return TaskListResponse(
        items=paginated_tasks,
        total=len(mock_tasks),
        page=page,
        size=size
    )

@app.get("/api/v1/tasks/{task_id}")
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get task by ID."""
    # Mock task lookup
    if task_id == "task-1":
        return Task(
            id="task-1",
            name="Customer Reviews Analysis",
            status="pending",
            priority="high",
            assignee_id="user-2"
        )
    else:
        raise HTTPException(status_code=404, detail="Task not found")

# Dashboard endpoints
@app.get("/api/v1/dashboard/metrics", response_model=DashboardMetrics)
async def dashboard_metrics(current_user: User = Depends(get_current_user)):
    """Get dashboard metrics."""
    return DashboardMetrics(
        tasks={
            "total": 150,
            "pending": 45,
            "in_progress": 30,
            "completed": 75
        },
        users={
            "total": 25,
            "active": 18
        },
        projects={
            "total": 12,
            "active": 8
        }
    )

logger.info("Isolated FastAPI app initialized successfully")