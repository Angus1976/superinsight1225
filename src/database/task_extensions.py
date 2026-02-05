"""
Task model extensions for comprehensive task management.

This module provides backward compatibility by re-exporting enums from models.py
and provides the TaskAdapter utility for mock data generation during testing.

Note: The main TaskModel is now defined in src/database/models.py with all
extended fields. This module is kept for backward compatibility.
"""

from datetime import datetime
from uuid import uuid4
from typing import Optional, List

# Re-export enums from models.py for backward compatibility
from src.database.models import TaskPriority, AnnotationType, TaskStatus


# NOTE: ExtendedTaskModel is deprecated. Use TaskModel from src.database.models instead.
# The table "extended_tasks" is no longer used - all task data is in "tasks" table.


# For backward compatibility, we'll use the existing TaskModel but add a view/adapter
class TaskAdapter:
    """
    Adapter to make existing TaskModel work with the task management API.
    
    This provides a compatibility layer between the existing document-focused
    TaskModel and the task management UI expectations.
    """
    
    @staticmethod
    def from_task_model(task_model, document_model=None):
        """Convert TaskModel to task management format."""
        return {
            "id": str(task_model.id),
            "name": f"Annotation Task - {task_model.project_id}",
            "description": f"Document annotation task for project {task_model.project_id}",
            "status": task_model.status.value if hasattr(task_model.status, 'value') else str(task_model.status),
            "priority": "medium",  # Default priority
            "annotation_type": "custom",  # Default type
            "assignee_id": None,  # Not tracked in original model
            "assignee_name": None,
            "created_by": "system",  # Default creator
            "created_at": task_model.created_at,
            "updated_at": task_model.created_at,  # Use created_at as fallback
            "due_date": None,
            "progress": int(task_model.quality_score * 100) if task_model.quality_score else 0,
            "total_items": 1,
            "completed_items": 1 if task_model.status.value == "completed" else 0,
            "tenant_id": task_model.tenant_id or "default_tenant",
            "label_studio_project_id": task_model.label_studio_project_id or task_model.project_id,
            # Label Studio sync tracking fields
            "label_studio_project_created_at": task_model.label_studio_project_created_at,
            "label_studio_sync_status": task_model.label_studio_sync_status.value if hasattr(task_model.label_studio_sync_status, 'value') else str(task_model.label_studio_sync_status) if task_model.label_studio_sync_status else "pending",
            "label_studio_last_sync": task_model.label_studio_last_sync,
            "label_studio_task_count": task_model.label_studio_task_count or 0,
            "label_studio_annotation_count": task_model.label_studio_annotation_count or 0,
            "tags": []
        }
    
    @staticmethod
    def create_mock_tasks(count=3):
        """Create mock tasks for development/testing."""
        from datetime import datetime, timedelta
        import random
        
        mock_tasks = []
        statuses = ["pending", "in_progress", "completed", "cancelled"]
        priorities = ["low", "medium", "high", "urgent"]
        types = ["text_classification", "ner", "sentiment", "qa"]
        label_studio_sync_statuses = ["pending", "synced", "failed"]
        
        for i in range(count):
            task_id = str(uuid4())
            status = random.choice(statuses)
            progress = random.randint(0, 100) if status != "pending" else 0
            if status == "completed":
                progress = 100
            
            total_items = random.randint(50, 1000)
            completed_items = int(total_items * progress / 100)
            
            # Label Studio sync tracking
            ls_sync_status = random.choice(label_studio_sync_statuses)
            ls_task_count = random.randint(10, 100) if ls_sync_status == "synced" else 0
            ls_annotation_count = int(ls_task_count * progress / 100) if ls_sync_status == "synced" else 0
            ls_project_created_at = datetime.utcnow() - timedelta(days=random.randint(1, 30)) if ls_sync_status != "pending" else None
            ls_last_sync = datetime.utcnow() - timedelta(hours=random.randint(1, 24)) if ls_sync_status == "synced" else None
            
            mock_tasks.append({
                "id": task_id,
                "name": f"Task {i+1}: {random.choice(['Customer Reviews', 'Product Descriptions', 'Support Tickets', 'User Feedback'])}",
                "description": f"Annotation task for {random.choice(['sentiment analysis', 'entity recognition', 'classification', 'quality assessment'])}",
                "status": status,
                "priority": random.choice(priorities),
                "annotation_type": random.choice(types),
                "assignee_id": str(uuid4()) if random.choice([True, False]) else None,
                "assignee_name": random.choice(["John Doe", "Jane Smith", "Bob Wilson", None]),
                "created_by": "admin",
                "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                "updated_at": datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                "due_date": datetime.utcnow() + timedelta(days=random.randint(1, 14)) if random.choice([True, False]) else None,
                "progress": progress,
                "total_items": total_items,
                "completed_items": completed_items,
                "tenant_id": "default_tenant",
                "label_studio_project_id": f"project_{i+1}",
                # Label Studio sync tracking fields
                "label_studio_project_created_at": ls_project_created_at,
                "label_studio_sync_status": ls_sync_status,
                "label_studio_last_sync": ls_last_sync,
                "label_studio_task_count": ls_task_count,
                "label_studio_annotation_count": ls_annotation_count,
                "tags": random.sample(["urgent", "customer", "product", "support", "quality"], random.randint(0, 3))
            })
        
        return mock_tasks