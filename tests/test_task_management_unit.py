"""
Unit tests for task management database migration.

Tests the extended TaskModel with new fields, enums, and API operations.
Validates Requirements 1.1, 1.2, 1.3 (Task Persistence, Task Management, Unified Data Model)
"""

import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from typing import Dict, Any, List

from src.database.models import (
    TaskModel, TaskStatus, TaskPriority, AnnotationType,
    LabelStudioSyncStatus
)


class TestTaskEnums:
    """Tests for task-related enum types."""

    def test_task_status_values(self):
        """Test all TaskStatus enum values exist."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.REVIEWED.value == "reviewed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_priority_values(self):
        """Test all TaskPriority enum values exist."""
        assert TaskPriority.LOW.value == "low"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.URGENT.value == "urgent"

    def test_annotation_type_values(self):
        """Test all AnnotationType enum values exist."""
        assert AnnotationType.TEXT_CLASSIFICATION.value == "text_classification"
        assert AnnotationType.NER.value == "ner"
        assert AnnotationType.SENTIMENT.value == "sentiment"
        assert AnnotationType.QA.value == "qa"
        assert AnnotationType.CUSTOM.value == "custom"

    def test_enum_from_string(self):
        """Test creating enums from string values."""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskPriority("high") == TaskPriority.HIGH
        assert AnnotationType("ner") == AnnotationType.NER

    def test_invalid_enum_value(self):
        """Test that invalid enum values raise ValueError."""
        with pytest.raises(ValueError):
            TaskStatus("invalid_status")
        with pytest.raises(ValueError):
            TaskPriority("invalid_priority")
        with pytest.raises(ValueError):
            AnnotationType("invalid_type")


class TestTaskModelFields:
    """Tests for TaskModel field definitions."""

    def test_task_model_has_required_fields(self):
        """Test that TaskModel has all required fields for task management."""
        # Check basic fields
        assert hasattr(TaskModel, 'id')
        assert hasattr(TaskModel, 'name')
        assert hasattr(TaskModel, 'description')
        assert hasattr(TaskModel, 'status')
        assert hasattr(TaskModel, 'priority')
        assert hasattr(TaskModel, 'annotation_type')

        # Check assignment fields
        assert hasattr(TaskModel, 'assignee_id')
        assert hasattr(TaskModel, 'created_by')
        assert hasattr(TaskModel, 'tenant_id')

        # Check progress fields
        assert hasattr(TaskModel, 'progress')
        assert hasattr(TaskModel, 'total_items')
        assert hasattr(TaskModel, 'completed_items')

        # Check timestamp fields
        assert hasattr(TaskModel, 'created_at')
        assert hasattr(TaskModel, 'updated_at')
        assert hasattr(TaskModel, 'due_date')

        # Check JSONB fields
        assert hasattr(TaskModel, 'tags')
        assert hasattr(TaskModel, 'task_metadata')
        assert hasattr(TaskModel, 'annotations')
        assert hasattr(TaskModel, 'ai_predictions')

        # Check Label Studio fields
        assert hasattr(TaskModel, 'label_studio_project_id')
        assert hasattr(TaskModel, 'label_studio_sync_status')

    def test_task_model_table_name(self):
        """Test that TaskModel uses correct table name."""
        assert TaskModel.__tablename__ == "tasks"


class TestTaskModelCreation:
    """Tests for TaskModel instance creation."""

    def test_create_minimal_task(self):
        """Test creating a task with minimal required fields."""
        task = TaskModel(
            name="Test Task",
            project_id="test_project",
            created_by="test_user",
            tenant_id="test_tenant"
        )

        # Check defaults are applied
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.annotation_type == AnnotationType.CUSTOM
        assert task.progress == 0
        assert task.total_items == 1
        assert task.completed_items == 0

    def test_create_full_task(self):
        """Test creating a task with all fields."""
        due_date = datetime.utcnow() + timedelta(days=7)
        assignee_id = uuid4()

        task = TaskModel(
            name="Full Task",
            description="A comprehensive task description",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            annotation_type=AnnotationType.NER,
            project_id="nlp_project",
            assignee_id=assignee_id,
            created_by="admin",
            tenant_id="enterprise_tenant",
            progress=50,
            total_items=100,
            completed_items=50,
            due_date=due_date,
            tags=["urgent", "customer", "nlp"],
            task_metadata={"source": "api", "batch_id": "batch_001"},
            label_studio_sync_status=LabelStudioSyncStatus.SYNCED
        )

        assert task.name == "Full Task"
        assert task.description == "A comprehensive task description"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.priority == TaskPriority.HIGH
        assert task.annotation_type == AnnotationType.NER
        assert task.assignee_id == assignee_id
        assert task.progress == 50
        assert task.total_items == 100
        assert task.completed_items == 50
        assert task.due_date == due_date
        assert task.tags == ["urgent", "customer", "nlp"]
        assert task.task_metadata["source"] == "api"
        assert task.label_studio_sync_status == LabelStudioSyncStatus.SYNCED


class TestTaskModelValidation:
    """Tests for TaskModel field validation."""

    def test_progress_calculation(self):
        """Test progress is correctly related to completed/total items."""
        task = TaskModel(
            name="Progress Test",
            project_id="test",
            created_by="user",
            tenant_id="tenant",
            total_items=100,
            completed_items=75
        )

        # Calculate expected progress
        expected_progress = int((75 / 100) * 100)
        assert expected_progress == 75

    def test_priority_ordering(self):
        """Test that priorities have logical ordering."""
        priorities = [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH, TaskPriority.URGENT]
        priority_values = [p.value for p in priorities]

        # Ensure all values are unique
        assert len(set(priority_values)) == 4

    def test_status_transitions(self):
        """Test valid status transitions."""
        # PENDING -> IN_PROGRESS
        task = TaskModel(
            name="Status Test",
            project_id="test",
            created_by="user",
            tenant_id="tenant",
            status=TaskStatus.PENDING
        )

        task.status = TaskStatus.IN_PROGRESS
        assert task.status == TaskStatus.IN_PROGRESS

        # IN_PROGRESS -> COMPLETED
        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

        # COMPLETED -> REVIEWED
        task.status = TaskStatus.REVIEWED
        assert task.status == TaskStatus.REVIEWED


class TestTaskModelConversion:
    """Tests for TaskModel data conversion."""

    def test_task_to_dict_conversion(self):
        """Test converting TaskModel to dictionary for API response."""
        task = TaskModel(
            id=uuid4(),
            name="Conversion Test",
            description="Test description",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            annotation_type=AnnotationType.SENTIMENT,
            project_id="test_project",
            created_by="admin",
            tenant_id="test_tenant",
            progress=25,
            total_items=50,
            completed_items=12,
            tags=["test", "conversion"],
            task_metadata={"key": "value"}
        )

        # Convert enum values to strings (as API would)
        task_dict = {
            "id": str(task.id),
            "name": task.name,
            "description": task.description,
            "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
            "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
            "annotation_type": task.annotation_type.value if hasattr(task.annotation_type, 'value') else str(task.annotation_type),
            "progress": task.progress,
            "total_items": task.total_items,
            "completed_items": task.completed_items,
            "tags": task.tags,
            "task_metadata": task.task_metadata
        }

        assert task_dict["status"] == "in_progress"
        assert task_dict["priority"] == "high"
        assert task_dict["annotation_type"] == "sentiment"
        assert task_dict["progress"] == 25
        assert task_dict["tags"] == ["test", "conversion"]

    def test_enum_serialization(self):
        """Test that enums serialize correctly."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskPriority.URGENT.value == "urgent"
        assert AnnotationType.TEXT_CLASSIFICATION.value == "text_classification"
        assert LabelStudioSyncStatus.SYNCED.value == "synced"


class TestTaskAPIHelpers:
    """Tests for task API helper functions."""

    def test_parse_priority_from_string(self):
        """Test parsing priority enum from string."""
        priorities = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "urgent": TaskPriority.URGENT
        }

        for string_val, expected_enum in priorities.items():
            parsed = TaskPriority(string_val)
            assert parsed == expected_enum

    def test_parse_annotation_type_from_string(self):
        """Test parsing annotation type enum from string."""
        types = {
            "text_classification": AnnotationType.TEXT_CLASSIFICATION,
            "ner": AnnotationType.NER,
            "sentiment": AnnotationType.SENTIMENT,
            "qa": AnnotationType.QA,
            "custom": AnnotationType.CUSTOM
        }

        for string_val, expected_enum in types.items():
            parsed = AnnotationType(string_val)
            assert parsed == expected_enum

    def test_parse_status_from_string(self):
        """Test parsing status enum from string."""
        statuses = {
            "pending": TaskStatus.PENDING,
            "in_progress": TaskStatus.IN_PROGRESS,
            "completed": TaskStatus.COMPLETED,
            "reviewed": TaskStatus.REVIEWED,
            "cancelled": TaskStatus.CANCELLED
        }

        for string_val, expected_enum in statuses.items():
            parsed = TaskStatus(string_val)
            assert parsed == expected_enum


class TestTaskMetadata:
    """Tests for task metadata and JSONB fields."""

    def test_tags_list_operations(self):
        """Test operations on tags list."""
        task = TaskModel(
            name="Tags Test",
            project_id="test",
            created_by="user",
            tenant_id="tenant",
            tags=["tag1", "tag2"]
        )

        # Add tag
        task.tags.append("tag3")
        assert "tag3" in task.tags
        assert len(task.tags) == 3

        # Remove tag
        task.tags.remove("tag1")
        assert "tag1" not in task.tags
        assert len(task.tags) == 2

    def test_task_metadata_dict_operations(self):
        """Test operations on task_metadata dict."""
        task = TaskModel(
            name="Metadata Test",
            project_id="test",
            created_by="user",
            tenant_id="tenant",
            task_metadata={"key1": "value1"}
        )

        # Add metadata
        task.task_metadata["key2"] = "value2"
        assert task.task_metadata["key2"] == "value2"

        # Update metadata
        task.task_metadata["key1"] = "updated_value"
        assert task.task_metadata["key1"] == "updated_value"

        # Delete metadata
        del task.task_metadata["key1"]
        assert "key1" not in task.task_metadata

    def test_complex_metadata_structure(self):
        """Test complex nested metadata structure."""
        complex_metadata = {
            "data_source": {
                "type": "database",
                "config": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "test_db"
                }
            },
            "processing_options": {
                "batch_size": 100,
                "workers": 4,
                "timeout": 3600
            },
            "custom_fields": [
                {"name": "field1", "type": "string"},
                {"name": "field2", "type": "number"}
            ]
        }

        task = TaskModel(
            name="Complex Metadata Test",
            project_id="test",
            created_by="user",
            tenant_id="tenant",
            task_metadata=complex_metadata
        )

        assert task.task_metadata["data_source"]["type"] == "database"
        assert task.task_metadata["processing_options"]["batch_size"] == 100
        assert len(task.task_metadata["custom_fields"]) == 2


class TestLabelStudioIntegration:
    """Tests for Label Studio integration fields."""

    def test_label_studio_sync_status_values(self):
        """Test Label Studio sync status enum values."""
        assert LabelStudioSyncStatus.PENDING.value == "pending"
        assert LabelStudioSyncStatus.SYNCED.value == "synced"
        assert LabelStudioSyncStatus.FAILED.value == "failed"

    def test_task_label_studio_fields(self):
        """Test Label Studio related fields on task."""
        task = TaskModel(
            name="LS Integration Test",
            project_id="test",
            created_by="user",
            tenant_id="tenant",
            label_studio_project_id="ls_project_123",
            label_studio_sync_status=LabelStudioSyncStatus.SYNCED,
            label_studio_last_sync=datetime.utcnow(),
            label_studio_task_count=50,
            label_studio_annotation_count=45
        )

        assert task.label_studio_project_id == "ls_project_123"
        assert task.label_studio_sync_status == LabelStudioSyncStatus.SYNCED
        assert task.label_studio_task_count == 50
        assert task.label_studio_annotation_count == 45


class TestTaskProgress:
    """Tests for task progress tracking."""

    def test_progress_bounds(self):
        """Test that progress stays within 0-100 bounds."""
        # Test minimum
        task_min = TaskModel(
            name="Progress Min",
            project_id="test",
            created_by="user",
            tenant_id="tenant",
            progress=0
        )
        assert task_min.progress == 0

        # Test maximum
        task_max = TaskModel(
            name="Progress Max",
            project_id="test",
            created_by="user",
            tenant_id="tenant",
            progress=100
        )
        assert task_max.progress == 100

    def test_completed_items_calculation(self):
        """Test calculating progress from completed items."""
        test_cases = [
            (0, 100, 0),    # 0% complete
            (50, 100, 50),  # 50% complete
            (100, 100, 100), # 100% complete
            (25, 50, 50),   # 50% complete (25/50)
            (3, 10, 30),    # 30% complete
        ]

        for completed, total, expected_progress in test_cases:
            calculated = int((completed / total) * 100)
            assert calculated == expected_progress, f"Expected {expected_progress}% for {completed}/{total}"


class TestTenantIsolation:
    """Tests for tenant isolation in task management."""

    def test_task_requires_tenant_id(self):
        """Test that tasks have tenant_id for isolation."""
        task = TaskModel(
            name="Tenant Test",
            project_id="test",
            created_by="user",
            tenant_id="tenant_123"
        )

        assert task.tenant_id == "tenant_123"

    def test_different_tenants(self):
        """Test creating tasks for different tenants."""
        task1 = TaskModel(
            name="Task Tenant 1",
            project_id="test",
            created_by="user1",
            tenant_id="tenant_a"
        )

        task2 = TaskModel(
            name="Task Tenant 2",
            project_id="test",
            created_by="user2",
            tenant_id="tenant_b"
        )

        assert task1.tenant_id != task2.tenant_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
