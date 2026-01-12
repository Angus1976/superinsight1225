"""
Task model extensions for comprehensive task management.

Extends the existing TaskModel with additional fields needed for task management UI.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from typing import Optional, List

from src.database.connection import Base


class TaskPriority(str, enum.Enum):
    """Task priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AnnotationType(str, enum.Enum):
    """Annotation type enumeration."""
    TEXT_CLASSIFICATION = "text_classification"
    NER = "ner"
    SENTIMENT = "sentiment"
    QA = "qa"
    CUSTOM = "custom"


class ExtendedTaskModel(Base):
    """
    Extended task model for comprehensive task management.
    
    This extends the basic TaskModel with additional fields needed for
    task management, assignment, progress tracking, and UI display.
    """
    __tablename__ = "extended_tasks"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    annotation_type: Mapped[AnnotationType] = mapped_column(SQLEnum(AnnotationType), default=AnnotationType.CUSTOM)
    priority: Mapped[TaskPriority] = mapped_column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, in_progress, completed, cancelled
    
    # Assignment and ownership
    assignee_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Progress tracking
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    total_items: Mapped[int] = mapped_column(Integer, default=1)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Label Studio integration
    label_studio_project_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Additional metadata
    tags: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    task_metadata: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Relationships
    assignee: Mapped[Optional["UserModel"]] = relationship("UserModel", foreign_keys=[assignee_id])


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
            "label_studio_project_id": task_model.project_id,
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
        
        for i in range(count):
            task_id = str(uuid4())
            status = random.choice(statuses)
            progress = random.randint(0, 100) if status != "pending" else 0
            if status == "completed":
                progress = 100
            
            total_items = random.randint(50, 1000)
            completed_items = int(total_items * progress / 100)
            
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
                "tags": random.sample(["urgent", "customer", "product", "support", "quality"], random.randint(0, 3))
            })
        
        return mock_tasks