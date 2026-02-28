"""
Load Test Scenarios for SuperInsight Platform.

This module defines specific load test scenarios for different user workflows
including authentication, task management, annotations, and data export.

**Validates: Requirements 5.1, 5.2**
**Validates: Properties 14, 15, 16**
"""

import json
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from locust import HttpUser, TaskSet, task, between, constant, events
from locust.runners import MasterRunner


# =============================================================================
# Configuration
# =============================================================================

# Load test configuration
CONCURRENT_USERS = 100
TEST_DURATION_SECONDS = 60
RAMP_UP_SECONDS = 30
SPAWN_RATE = CONCURRENT_USERS / RAMP_UP_SECONDS  # Users per second

# Task weights for different user types
AUTH_WEIGHT = 2
TASK_WEIGHT = 3
ANNOTATION_WEIGHT = 2
EXPORT_WEIGHT = 1


# =============================================================================
# Test Data Management
# =============================================================================

class TestDataManager:
    """Manages test data for load tests."""
    
    _instance = None
    _test_users: List[Dict] = []
    _test_tasks: List[int] = []
    _test_annotations: List[int] = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def generate_test_user(cls) -> Dict[str, str]:
        """Generate a unique test user."""
        user_id = uuid.uuid4().hex[:8]
        return {
            "username": f"loadtest_{user_id}",
            "email": f"loadtest_{user_id}@test.example.com",
            "password": "TestPassword123!"
        }
    
    @classmethod
    def generate_test_task(cls) -> Dict[str, Any]:
        """Generate test task data."""
        return {
            "title": f"Load Test Task {uuid.uuid4().hex[:8]}",
            "description": "Task created during load testing",
            "priority": "medium",
            "metadata": {"source": "load_test", "timestamp": datetime.utcnow().isoformat()}
        }
    
    @classmethod
    def generate_test_annotation(cls, task_id: int) -> Dict[str, Any]:
        """Generate test annotation data."""
        return {
            "task_id": task_id,
            "annotation_type": "text",
            "data": {
                "start": 0,
                "end": 100,
                "text": f"Test annotation content {uuid.uuid4().hex[:8]}",
                "labels": ["positive", "relevant"]
            }
        }
    
    @classmethod
    def generate_test_export(cls) -> Dict[str, Any]:
        """Generate test export configuration."""
        return {
            "format": "json",
            "include_annotations": True,
            "filters": {
                "status": "completed",
                "date_from": "2024-01-01"
            }
        }


# =============================================================================
# Authentication Load Test Scenarios
# =============================================================================

class AuthLoadTest(TaskSet):
    """Load test scenarios for authentication endpoints."""
    
    def on_start(self):
        """Initialize test user."""
        self.user = TestDataManager.generate_test_user()
        self.token = None
        self._register_user()
    
    def _register_user(self):
        """Register a new test user."""
        with self.client.post(
            "/api/v1/auth/register",
            json=self.user,
            name="POST /api/v1/auth/register",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 400]:  # 400 = already exists
                response.success()
            elif response.status_code == 422:
                # Validation error, try with simpler data
                self.user = {
                    "username": f"loadtest_{uuid.uuid4().hex[:8]}",
                    "email": f"{uuid.uuid4().hex[:8]}@test.com",
                    "password": "Test123!"
                }
                response.success()
            else:
                response.failure(f"Registration failed: {response.status_code}")
    
    @task(10)
    def health_check(self):
        """Health check endpoint - high frequency."""
        with self.client.get(
            "/health",
            name="GET /health",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(5)
    def login(self):
        """User login endpoint."""
        payload = {
            "username": self.user["username"],
            "password": self.user["password"]
        }
        
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            name="POST /api/v1/auth/login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
            elif response.status_code == 401:
                # Invalid credentials, re-register
                self._register_user()
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(3)
    def get_profile(self):
        """Get user profile endpoint."""
        if not self.token:
            self.login()
        
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
        with self.client.get(
            "/api/v1/auth/profile",
            headers=headers,
            name="GET /api/v1/auth/profile",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                # Token expired, re-login
                self.login()
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def refresh_token(self):
        """Refresh access token endpoint."""
        if not self.token:
            self.login()
        
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
        with self.client.post(
            "/api/v1/auth/refresh",
            headers=headers,
            name="POST /api/v1/auth/refresh",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(1)
    def logout(self):
        """User logout endpoint."""
        if not self.token:
            self.login()
        
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
        with self.client.post(
            "/api/v1/auth/logout",
            headers=headers,
            name="POST /api/v1/auth/logout",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


# =============================================================================
# Task Management Load Test Scenarios
# =============================================================================

class TaskLoadTest(TaskSet):
    """Load test scenarios for task management endpoints."""
    
    def on_start(self):
        """Authenticate user."""
        self.user = TestDataManager.generate_test_user()
        self.token = None
        self.created_tasks: List[int] = []
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate and get token."""
        payload = {
            "username": self.user["username"],
            "password": self.user["password"]
        }
        
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            name="POST /api/v1/auth/login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
            else:
                # Try to register
                self._register()
    
    def _register(self):
        """Register a new user."""
        with self.client.post(
            "/api/v1/auth/register",
            json=self.user,
            name="POST /api/v1/auth/register",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                self._authenticate()
            else:
                response.failure(f"Registration failed: {response.status_code}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get auth headers."""
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    @task(8)
    def list_tasks(self):
        """List tasks with pagination."""
        params = {
            "page": 1,
            "page_size": 20,
            "sort_by": "created_at",
            "sort_order": "desc"
        }
        
        with self.client.get(
            "/api/v1/tasks",
            params=params,
            headers=self._get_headers(),
            name="GET /api/v1/tasks",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                self._authenticate()
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(5)
    def get_task(self):
        """Get single task by ID."""
        task_id = self.created_tasks[0] if self.created_tasks else 1
        
        with self.client.get(
            f"/api/v1/tasks/{task_id}",
            headers=self._get_headers(),
            name="GET /api/v1/tasks/{id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(4)
    def create_task(self):
        """Create a new task."""
        task_data = TestDataManager.generate_test_task()
        
        with self.client.post(
            "/api/v1/tasks",
            json=task_data,
            headers=self._get_headers(),
            name="POST /api/v1/tasks",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                data = response.json()
                if "id" in data:
                    self.created_tasks.append(data["id"])
                response.success()
            elif response.status_code == 401:
                self._authenticate()
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(3)
    def update_task(self):
        """Update an existing task."""
        if not self.created_tasks:
            self.create_task()
        
        task_id = self.created_tasks[0]
        update_data = {
            "title": f"Updated Task {uuid.uuid4().hex[:8]}",
            "status": "in_progress"
        }
        
        with self.client.put(
            f"/api/v1/tasks/{task_id}",
            json=update_data,
            headers=self._get_headers(),
            name="PUT /api/v1/tasks/{id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def delete_task(self):
        """Delete a task."""
        if not self.created_tasks:
            return
        
        task_id = self.created_tasks.pop(0)
        
        with self.client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=self._get_headers(),
            name="DELETE /api/v1/tasks/{id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 204, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def search_tasks(self):
        """Search tasks by keyword."""
        params = {"q": "test", "page": 1, "page_size": 10}
        
        with self.client.get(
            "/api/v1/tasks/search",
            params=params,
            headers=self._get_headers(),
            name="GET /api/v1/tasks/search",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(1)
    def bulk_update_tasks(self):
        """Bulk update task status."""
        if len(self.created_tasks) < 2:
            return
        
        task_ids = self.created_tasks[:5]
        update_data = {"status": "completed"}
        
        with self.client.put(
            "/api/v1/tasks/bulk",
            json={"ids": task_ids, "data": update_data},
            headers=self._get_headers(),
            name="PUT /api/v1/tasks/bulk",
            catch_response=True
        ) as response:
            if response.status_code in [200, 400]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


# =============================================================================
# Annotation Load Test Scenarios
# =============================================================================

class AnnotationLoadTest(TaskSet):
    """Load test scenarios for annotation endpoints."""
    
    def on_start(self):
        """Authenticate user."""
        self.user = TestDataManager.generate_test_user()
        self.token = None
        self.created_annotations: List[int] = []
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate and get token."""
        payload = {
            "username": self.user["username"],
            "password": self.user["password"]
        }
        
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            name="POST /api/v1/auth/login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
            else:
                self._register()
    
    def _register(self):
        """Register a new user."""
        with self.client.post(
            "/api/v1/auth/register",
            json=self.user,
            name="POST /api/v1/auth/register",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                self._authenticate()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get auth headers."""
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    @task(6)
    def list_annotations(self):
        """List annotations."""
        params = {"page": 1, "page_size": 20}
        
        with self.client.get(
            "/api/v1/annotations",
            params=params,
            headers=self._get_headers(),
            name="GET /api/v1/annotations",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(4)
    def get_annotation(self):
        """Get single annotation."""
        if not self.created_annotations:
            return
        
        annotation_id = self.created_annotations[0]
        
        with self.client.get(
            f"/api/v1/annotations/{annotation_id}",
            headers=self._get_headers(),
            name="GET /api/v1/annotations/{id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(4)
    def create_annotation(self):
        """Create a new annotation."""
        annotation_data = TestDataManager.generate_test_annotation(1)
        
        with self.client.post(
            "/api/v1/annotations",
            json=annotation_data,
            headers=self._get_headers(),
            name="POST /api/v1/annotations",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                data = response.json()
                if "id" in data:
                    self.created_annotations.append(data["id"])
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(3)
    def update_annotation(self):
        """Update an annotation."""
        if not self.created_annotations:
            return
        
        annotation_id = self.created_annotations[0]
        update_data = {
            "data": {
                "text": f"Updated annotation {uuid.uuid4().hex[:8]}",
                "labels": ["updated"]
            }
        }
        
        with self.client.put(
            f"/api/v1/annotations/{annotation_id}",
            json=update_data,
            headers=self._get_headers(),
            name="PUT /api/v1/annotations/{id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def delete_annotation(self):
        """Delete an annotation."""
        if not self.created_annotations:
            return
        
        annotation_id = self.created_annotations.pop(0)
        
        with self.client.delete(
            f"/api/v1/annotations/{annotation_id}",
            headers=self._get_headers(),
            name="DELETE /api/v1/annotations/{id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 204, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def get_annotation_history(self):
        """Get annotation history."""
        if not self.created_annotations:
            return
        
        annotation_id = self.created_annotations[0]
        
        with self.client.get(
            f"/api/v1/annotations/{annotation_id}/history",
            headers=self._get_headers(),
            name="GET /api/v1/annotations/{id}/history",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


# =============================================================================
# Export Load Test Scenarios
# =============================================================================

class ExportLoadTest(TaskSet):
    """Load test scenarios for data export endpoints."""
    
    def on_start(self):
        """Authenticate user."""
        self.user = TestDataManager.generate_test_user()
        self.token = None
        self.created_exports: List[int] = []
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate and get token."""
        payload = {
            "username": self.user["username"],
            "password": self.user["password"]
        }
        
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            name="POST /api/v1/auth/login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
            else:
                self._register()
    
    def _register(self):
        """Register a new user."""
        with self.client.post(
            "/api/v1/auth/register",
            json=self.user,
            name="POST /api/v1/auth/register",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                self._authenticate()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get auth headers."""
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    @task(5)
    def list_exports(self):
        """List exports."""
        params = {"page": 1, "page_size": 20}
        
        with self.client.get(
            "/api/v1/exports",
            params=params,
            headers=self._get_headers(),
            name="GET /api/v1/exports",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(4)
    def create_export(self):
        """Create a new export."""
        export_config = TestDataManager.generate_test_export()
        
        with self.client.post(
            "/api/v1/exports",
            json=export_config,
            headers=self._get_headers(),
            name="POST /api/v1/exports",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 202]:
                data = response.json()
                if "id" in data:
                    self.created_exports.append(data["id"])
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(3)
    def get_export_status(self):
        """Get export status."""
        if not self.created_exports:
            return
        
        export_id = self.created_exports[0]
        
        with self.client.get(
            f"/api/v1/exports/{export_id}",
            headers=self._get_headers(),
            name="GET /api/v1/exports/{id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def download_export(self):
        """Download export file."""
        if not self.created_exports:
            return
        
        export_id = self.created_exports[0]
        
        with self.client.get(
            f"/api/v1/exports/{export_id}/download",
            headers=self._get_headers(),
            name="GET /api/v1/exports/{id}/download",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404, 202]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def cancel_export(self):
        """Cancel an export."""
        if not self.created_exports:
            return
        
        export_id = self.created_exports.pop(0)
        
        with self.client.delete(
            f"/api/v1/exports/{export_id}",
            headers=self._get_headers(),
            name="DELETE /api/v1/exports/{id}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 204, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


# =============================================================================
# User Classes for Different Load Profiles
# =============================================================================

class StandardLoadUser(HttpUser):
    """
    Standard user with balanced workload.
    
    Simulates typical user behavior with mixed operations
    across all functional areas.
    """
    
    wait_time = between(1, 3)
    tasks = {
        AuthLoadTest: AUTH_WEIGHT,
        TaskLoadTest: TASK_WEIGHT,
        AnnotationLoadTest: ANNOTATION_WEIGHT,
        ExportLoadTest: EXPORT_WEIGHT
    }


class HeavyTaskUser(HttpUser):
    """User focused on task management operations."""
    
    wait_time = between(0.5, 1.5)
    tasks = {
        AuthLoadTest: 1,
        TaskLoadTest: 6,
        AnnotationLoadTest: 2,
        ExportLoadTest: 1
    }


class HeavyAnnotationUser(HttpUser):
    """User focused on annotation operations."""
    
    wait_time = between(1, 2)
    tasks = {
        AuthLoadTest: 1,
        TaskLoadTest: 2,
        AnnotationLoadTest: 6,
        ExportLoadTest: 1
    }


class MixedApiUser(HttpUser):
    """User with random API endpoint access."""
    
    wait_time = between(0.5, 2)
    
    def on_start(self):
        """Authenticate user."""
        self.user = TestDataManager.generate_test_user()
        self.token = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate and get token."""
        payload = {
            "username": self.user["username"],
            "password": self.user["password"]
        }
        
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            name="POST /api/v1/auth/login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
            else:
                self._register()
    
    def _register(self):
        """Register a new user."""
        with self.client.post(
            "/api/v1/auth/register",
            json=self.user,
            name="POST /api/v1/auth/register",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                self._authenticate()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get auth headers."""
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    @task
    def random_endpoint(self):
        """Access random API endpoint."""
        import random
        
        endpoints = [
            ("GET", "/api/v1/tasks", {}),
            ("GET", "/api/v1/annotations", {}),
            ("GET", "/api/v1/exports", {}),
            ("GET", "/api/v1/auth/profile", {}),
        ]
        
        method, endpoint, params = random.choice(endpoints)
        headers = self._get_headers()
        
        with self.client.get(
            endpoint,
            params=params,
            headers=headers,
            name=f"{method} {endpoint}",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 404]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


# =============================================================================
# Load Test Configuration
# =============================================================================

def get_load_test_config() -> Dict[str, Any]:
    """Get load test configuration."""
    return {
        "concurrent_users": CONCURRENT_USERS,
        "duration_seconds": TEST_DURATION_SECONDS,
        "ramp_up_seconds": RAMP_UP_SECONDS,
        "spawn_rate": SPAWN_RATE,
        "task_weights": {
            "auth": AUTH_WEIGHT,
            "task": TASK_WEIGHT,
            "annotation": ANNOTATION_WEIGHT,
            "export": EXPORT_WEIGHT
        }
    }


# Export for use in other modules
__all__ = [
    "AuthLoadTest",
    "TaskLoadTest",
    "AnnotationLoadTest",
    "ExportLoadTest",
    "StandardLoadUser",
    "HeavyTaskUser",
    "HeavyAnnotationUser",
    "MixedApiUser",
    "get_load_test_config",
    "TestDataManager",
]