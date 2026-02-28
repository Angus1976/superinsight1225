"""
Test Data Factories for SuperInsight Backend.

Provides factory functions for generating test data with:
- Sensible defaults for all entities
- Relationship support (foreign keys, associations)
- Override mechanism for custom test scenarios
- Invalid state generation for error testing

Usage:
    from tests.factories import UserFactory, TaskFactory, AnnotationFactory, DatasetFactory
    
    # Basic usage with defaults
    user = UserFactory()
    task = TaskFactory()
    
    # With overrides
    user = UserFactory(role="admin", is_active=True)
    task = TaskFactory(status="completed", assigned_to=user.id)
    
    # With relationships
    task = TaskFactory.with_relationships()
    annotation = AnnotationFactory.with_task(task_id=task.id)
    
    # Invalid states for error testing
    invalid_user = UserFactory.invalid_email()
    invalid_task = TaskFactory.missing_required()
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypeVar, Type
from uuid import UUID, uuid4
import random

T = TypeVar("T")


# =============================================================================
# Base Factory
# =============================================================================

class BaseFactory:
    """Base factory class with common functionality."""
    
    @staticmethod
    def generate_uuid() -> UUID:
        """Generate a new UUID."""
        return uuid4()
    
    @staticmethod
    def get_utc_now() -> datetime:
        """Get current UTC time."""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def random_choice(items: List[T]) -> T:
        """Randomly select an item from a list."""
        return random.choice(items)


# =============================================================================
# User Factory
# =============================================================================

class UserFactory(BaseFactory):
    """
    Factory for creating User test data.
    
    Default values:
    - role: random from [admin, annotator, reviewer, viewer]
    - is_active: True
    - is_verified: False
    - is_superuser: False
    """
    
    ROLES = ["admin", "annotator", "reviewer", "viewer"]
    TIMEZONES = ["UTC", "America/New_York", "Europe/London", "Asia/Shanghai"]
    LANGUAGES = ["en", "zh", "ja", "ko"]
    
    @staticmethod
    def generate_username() -> str:
        """Generate a valid username."""
        prefixes = ["user", "test", "demo", "admin"]
        return f"{random.choice(prefixes)}_{uuid4().hex[:8]}"
    
    @staticmethod
    def generate_email(username: Optional[str] = None) -> str:
        """Generate a valid email address."""
        if username is None:
            username = UserFactory.generate_username()
        domains = ["example.com", "test.com", "demo.org", "example.org"]
        return f"{username}@{random.choice(domains)}"
    
    @staticmethod
    def create(
        id: Optional[UUID] = None,
        email: Optional[str] = None,
        username: Optional[str] = None,
        name: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = True,
        is_verified: Optional[bool] = False,
        is_superuser: Optional[bool] = False,
        password_hash: Optional[str] = None,
        sso_id: Optional[str] = None,
        sso_provider: Optional[str] = None,
        avatar_url: Optional[str] = None,
        timezone: Optional[str] = None,
        language: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_login_at: Optional[datetime] = None,
        user_metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a user with sensible defaults.
        
        Args:
            id: User ID (auto-generated if not provided)
            email: Email address (auto-generated if not provided)
            username: Username (auto-generated if not provided)
            name: Full name
            first_name: First name
            last_name: Last name
            role: User role (admin, annotator, reviewer, viewer)
            is_active: Account active status
            is_verified: Email verified status
            is_superuser: Superuser status
            password_hash: Password hash (for local auth)
            sso_id: SSO provider user ID
            sso_provider: SSO provider name
            avatar_url: Profile picture URL
            timezone: User timezone
            language: User language
            created_at: Creation timestamp
            updated_at: Update timestamp
            last_login_at: Last login timestamp
            user_metadata: Additional metadata
            **kwargs: Additional fields
            
        Returns:
            Dictionary representation of user data
        """
        _username = username or UserFactory.generate_username()
        _email = email or UserFactory.generate_email(_username)
        
        return {
            "id": id or UserFactory.generate_uuid(),
            "email": _email,
            "username": _username,
            "name": name,
            "first_name": first_name,
            "last_name": last_name,
            "role": role or random.choice(UserFactory.ROLES),
            "is_active": is_active,
            "is_verified": is_verified,
            "is_superuser": is_superuser,
            "password_hash": password_hash,
            "sso_id": sso_id,
            "sso_provider": sso_provider,
            "sso_attributes": kwargs.get("sso_attributes"),
            "avatar_url": avatar_url,
            "timezone": timezone or random.choice(UserFactory.TIMEZONES),
            "language": language or random.choice(UserFactory.LANGUAGES),
            "created_at": created_at or UserFactory.get_utc_now(),
            "updated_at": updated_at or UserFactory.get_utc_now(),
            "last_login_at": last_login_at,
            "user_metadata": user_metadata or {},
        }
    
    @staticmethod
    def admin() -> Dict[str, Any]:
        """Create an admin user."""
        return UserFactory.create(role="admin", is_superuser=True)
    
    @staticmethod
    def annotator() -> Dict[str, Any]:
        """Create an annotator user."""
        return UserFactory.create(role="annotator")
    
    @staticmethod
    def reviewer() -> Dict[str, Any]:
        """Create a reviewer user."""
        return UserFactory.create(role="reviewer")
    
    @staticmethod
    def inactive() -> Dict[str, Any]:
        """Create an inactive user."""
        return UserFactory.create(is_active=False)
    
    @staticmethod
    def sso_user() -> Dict[str, Any]:
        """Create an SSO-authenticated user."""
        return UserFactory.create(
            sso_id=str(uuid4()),
            sso_provider="google",
            password_hash=None,
        )
    
    # =========================================================================
    # Invalid States for Error Testing
    # =========================================================================
    
    @staticmethod
    def invalid_email(email: str = "not-an-email") -> Dict[str, Any]:
        """Create a user with invalid email for validation testing."""
        return UserFactory.create(email=email)
    
    @staticmethod
    def empty_email() -> Dict[str, Any]:
        """Create a user with empty email."""
        return UserFactory.create(email="")
    
    @staticmethod
    def duplicate_email(existing_email: str = "existing@example.com") -> Dict[str, Any]:
        """Create a user with duplicate email for uniqueness testing."""
        return UserFactory.create(email=existing_email)
    
    @staticmethod
    def missing_required() -> Dict[str, Any]:
        """Create a user missing required fields for validation testing."""
        return {
            "id": UserFactory.generate_uuid(),
            "email": "",  # Required field
            "username": "",  # Required field
        }
    
    @staticmethod
    def with_custom_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a user with custom metadata."""
        return UserFactory.create(user_metadata=metadata)


# =============================================================================
# Task Factory
# =============================================================================

class TaskFactory(BaseFactory):
    """
    Factory for creating Task test data.
    
    Default values:
    - status: random from [pending, in_progress, completed, failed, cancelled]
    - priority: random from [1, 2, 3, 4, 5]
    """
    
    STATUSES = ["pending", "in_progress", "completed", "failed", "cancelled"]
    PRIORITIES = [1, 2, 3, 4, 5]
    
    @staticmethod
    def generate_title() -> str:
        """Generate a valid task title."""
        prefixes = ["Annotate", "Review", "Validate", "Process", "Check"]
        subjects = ["data", "documents", "images", "text", "records"]
        return f"{random.choice(prefixes)} {random.choice(subjects)} {uuid4().hex[:4]}"
    
    @staticmethod
    def generate_description() -> str:
        """Generate a valid task description."""
        templates = [
            "Task to {action} the {subject} for quality assurance.",
            "Please {action} all {subject} according to guidelines.",
            "Review and {action} the {subject} in the dataset.",
            "{action} the {subject} following the standard procedure.",
        ]
        actions = ["annotate", "review", "validate", "process", "check"]
        subjects = ["data entries", "documents", "images", "text samples", "records"]
        return random.choice(templates).format(
            action=random.choice(actions),
            subject=random.choice(subjects),
        )
    
    @staticmethod
    def create(
        task_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        assigned_to: Optional[UUID] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        due_date: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a task with sensible defaults.
        
        Args:
            task_id: Task ID (auto-generated if not provided)
            project_id: Project ID (auto-generated if not provided)
            tenant_id: Tenant ID (auto-generated if not provided)
            title: Task title
            description: Task description
            assigned_to: Assigned user ID
            status: Task status
            priority: Priority level (1-5)
            created_at: Creation timestamp
            updated_at: Update timestamp
            due_date: Due date
            metadata: Additional metadata
            **kwargs: Additional fields
            
        Returns:
            Dictionary representation of task data
        """
        return {
            "task_id": task_id or TaskFactory.generate_uuid(),
            "project_id": project_id or TaskFactory.generate_uuid(),
            "tenant_id": tenant_id or TaskFactory.generate_uuid(),
            "title": title or TaskFactory.generate_title(),
            "description": description or TaskFactory.generate_description(),
            "assigned_to": assigned_to,
            "status": status or random.choice(TaskFactory.STATUSES),
            "priority": priority or random.choice(TaskFactory.PRIORITIES),
            "created_at": created_at or TaskFactory.get_utc_now(),
            "updated_at": updated_at or TaskFactory.get_utc_now(),
            "due_date": due_date,
            "metadata": metadata or {},
        }
    
    @staticmethod
    def with_relationships(
        owner_id: Optional[UUID] = None,
        assignee_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Create a task with related users."""
        owner = owner_id or UserFactory.generate_uuid()
        assignee = assignee_id or UserFactory.generate_uuid()
        return TaskFactory.create(
            assigned_to=assignee,
            metadata={"created_by": str(owner)},
        )
    
    @staticmethod
    def pending() -> Dict[str, Any]:
        """Create a pending task."""
        return TaskFactory.create(status="pending")
    
    @staticmethod
    def in_progress() -> Dict[str, Any]:
        """Create an in-progress task."""
        return TaskFactory.create(status="in_progress")
    
    @staticmethod
    def completed() -> Dict[str, Any]:
        """Create a completed task."""
        return TaskFactory.create(status="completed")
    
    @staticmethod
    def high_priority() -> Dict[str, Any]:
        """Create a high priority task."""
        return TaskFactory.create(priority=5)
    
    @staticmethod
    def assigned_to(user_id: UUID) -> Dict[str, Any]:
        """Create a task assigned to a specific user."""
        return TaskFactory.create(assigned_to=user_id)
    
    # =========================================================================
    # Invalid States for Error Testing
    # =========================================================================
    
    @staticmethod
    def missing_required() -> Dict[str, Any]:
        """Create a task missing required fields."""
        return {
            "task_id": TaskFactory.generate_uuid(),
            "project_id": None,  # Required
            "tenant_id": None,  # Required
            "title": "",  # Required
        }
    
    @staticmethod
    def invalid_status(status: str = "invalid_status") -> Dict[str, Any]:
        """Create a task with invalid status."""
        return TaskFactory.create(status=status)
    
    @staticmethod
    def invalid_priority(priority: int = 10) -> Dict[str, Any]:
        """Create a task with invalid priority (out of range)."""
        return TaskFactory.create(priority=priority)
    
    @staticmethod
    def empty_title() -> Dict[str, Any]:
        """Create a task with empty title."""
        return TaskFactory.create(title="")
    
    @staticmethod
    def with_nonexistent_assignee() -> Dict[str, Any]:
        """Create a task assigned to non-existent user."""
        return TaskFactory.create(assigned_to=UserFactory.generate_uuid())


# =============================================================================
# Annotation Factory
# # =============================================================================

class AnnotationFactory(BaseFactory):
    """
    Factory for creating Annotation test data.
    
    Default values:
    - annotation_type: random from [text, entity, relation, classification]
    - confidence: random float between 0.0 and 1.0
    """
    
    ANNOTATION_TYPES = ["text", "entity", "relation", "classification"]
    
    @staticmethod
    def generate_annotation_data(annotation_type: str) -> Dict[str, Any]:
        """Generate annotation data based on type."""
        if annotation_type == "text":
            return {
                "text": "Sample text for annotation",
                "start_offset": 0,
                "end_offset": 10,
                "label": "positive",
            }
        elif annotation_type == "entity":
            return {
                "text": "Entity text",
                "entity_type": "PERSON",
                "start_offset": 0,
                "end_offset": 10,
                "attributes": {"confidence": 0.95},
            }
        elif annotation_type == "relation":
            return {
                "relation_type": "WORKS_FOR",
                "from_entity": str(uuid4()),
                "to_entity": str(uuid4()),
            }
        elif annotation_type == "classification":
            return {
                "labels": ["category_a", "category_b"],
                "probabilities": [0.7, 0.3],
            }
        else:
            return {"value": "generic_annotation"}
    
    @staticmethod
    def create(
        annotation_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        annotator_id: Optional[UUID] = None,
        annotation_type: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create an annotation with sensible defaults.
        
        Args:
            annotation_id: Annotation ID (auto-generated if not provided)
            task_id: Related task ID
            annotator_id: Annotator user ID
            annotation_type: Type of annotation
            data: Annotation data/content
            confidence: Confidence score (0.0-1.0)
            created_at: Creation timestamp
            updated_at: Update timestamp
            **kwargs: Additional fields
            
        Returns:
            Dictionary representation of annotation data
        """
        _annotation_type = annotation_type or random.choice(AnnotationFactory.ANNOTATION_TYPES)
        _data = data or AnnotationFactory.generate_annotation_data(_annotation_type)
        
        return {
            "annotation_id": annotation_id or AnnotationFactory.generate_uuid(),
            "task_id": task_id or AnnotationFactory.generate_uuid(),
            "annotator_id": annotator_id or AnnotationFactory.generate_uuid(),
            "annotation_type": _annotation_type,
            "data": _data,
            "confidence": confidence if confidence is not None else random.uniform(0.5, 1.0),
            "created_at": created_at or AnnotationFactory.get_utc_now(),
            "updated_at": updated_at or AnnotationFactory.get_utc_now(),
        }
    
    @staticmethod
    def with_task(
        task_id: Optional[UUID] = None,
        annotator_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Create an annotation linked to a specific task."""
        return AnnotationFactory.create(
            task_id=task_id or TaskFactory.generate_uuid(),
            annotator_id=annotator_id or UserFactory.generate_uuid(),
        )
    
    @staticmethod
    def text_annotation(
        task_id: Optional[UUID] = None,
        annotator_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Create a text annotation."""
        return AnnotationFactory.create(
            task_id=task_id,
            annotator_id=annotator_id,
            annotation_type="text",
            data={
                "text": "Sample text for annotation",
                "start_offset": 0,
                "end_offset": 10,
                "label": "positive",
            },
        )
    
    @staticmethod
    def entity_annotation(
        task_id: Optional[UUID] = None,
        annotator_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Create an entity annotation."""
        return AnnotationFactory.create(
            task_id=task_id,
            annotator_id=annotator_id,
            annotation_type="entity",
            data={
                "text": "Entity text",
                "entity_type": "PERSON",
                "start_offset": 0,
                "end_offset": 10,
            },
        )
    
    @staticmethod
    def high_confidence() -> Dict[str, Any]:
        """Create a high confidence annotation."""
        return AnnotationFactory.create(confidence=0.95)
    
    @staticmethod
    def low_confidence() -> Dict[str, Any]:
        """Create a low confidence annotation."""
        return AnnotationFactory.create(confidence=0.3)
    
    # =========================================================================
    # Invalid States for Error Testing
    # =========================================================================
    
    @staticmethod
    def missing_required() -> Dict[str, Any]:
        """Create an annotation missing required fields."""
        return {
            "annotation_id": AnnotationFactory.generate_uuid(),
            "task_id": None,  # Required
            "annotator_id": None,  # Required
            "annotation_type": "",  # Required
        }
    
    @staticmethod
    def invalid_type(annotation_type: str = "invalid_type") -> Dict[str, Any]:
        """Create an annotation with invalid type."""
        return AnnotationFactory.create(annotation_type=annotation_type)
    
    @staticmethod
    def invalid_confidence(confidence: float = 1.5) -> Dict[str, Any]:
        """Create an annotation with confidence out of range."""
        return AnnotationFactory.create(confidence=confidence)
    
    @staticmethod
    def negative_confidence(confidence: float = -0.5) -> Dict[str, Any]:
        """Create an annotation with negative confidence."""
        return AnnotationFactory.create(confidence=confidence)
    
    @staticmethod
    def with_nonexistent_task() -> Dict[str, Any]:
        """Create an annotation linked to non-existent task."""
        return AnnotationFactory.create(
            task_id=TaskFactory.generate_uuid(),
        )
    
    @staticmethod
    def with_nonexistent_annotator() -> Dict[str, Any]:
        """Create an annotation by non-existent annotator."""
        return AnnotationFactory.create(
            annotator_id=UserFactory.generate_uuid(),
        )


# =============================================================================
# Dataset Factory
# =============================================================================

class DatasetFactory(BaseFactory):
    """
    Factory for creating Dataset test data.
    
    Default values:
    - format: random from [json, csv, xml, parquet]
    - size: random integer between 0 and 1000000
    """
    
    FORMATS = ["json", "csv", "xml", "parquet"]
    
    @staticmethod
    def generate_name() -> str:
        """Generate a valid dataset name."""
        prefixes = ["dataset", "data", "corpus", "collection", "sample"]
        return f"{random.choice(prefixes)}_{uuid4().hex[:6]}"
    
    @staticmethod
    def generate_description() -> str:
        """Generate a valid dataset description."""
        templates = [
            "A {adjective} dataset containing {subject} for {purpose}.",
            "{subject} dataset with {count} samples for analysis.",
            "Collection of {subject} data for machine learning.",
            "Annotated {subject} dataset for training and testing.",
        ]
        adjectives = ["comprehensive", "sample", "training", "test", "balanced"]
        subjects = ["text", "image", "audio", "document", "record"]
        purposes = ["training", "testing", "validation", "analysis"]
        counts = ["100", "1000", "10000", "50000"]
        return random.choice(templates).format(
            adjective=random.choice(adjectives),
            subject=random.choice(subjects),
            purpose=random.choice(purposes),
            count=random.choice(counts),
        )
    
    @staticmethod
    def create(
        dataset_id: Optional[UUID] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        size: Optional[int] = None,
        format: Optional[str] = None,
        created_by: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        file_path: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a dataset with sensible defaults.
        
        Args:
            dataset_id: Dataset ID (auto-generated if not provided)
            name: Dataset name
            description: Dataset description
            size: Number of records
            format: Data format (json, csv, xml, parquet)
            created_by: Creator user ID
            created_at: Creation timestamp
            updated_at: Update timestamp
            file_path: Path to data file
            schema: Dataset schema definition
            metadata: Additional metadata
            **kwargs: Additional fields
            
        Returns:
            Dictionary representation of dataset data
        """
        return {
            "dataset_id": dataset_id or DatasetFactory.generate_uuid(),
            "name": name or DatasetFactory.generate_name(),
            "description": description or DatasetFactory.generate_description(),
            "size": size if size is not None else random.randint(0, 1000000),
            "format": format or random.choice(DatasetFactory.FORMATS),
            "created_by": created_by or DatasetFactory.generate_uuid(),
            "created_at": created_at or DatasetFactory.get_utc_now(),
            "updated_at": updated_at or DatasetFactory.get_utc_now(),
            "file_path": file_path or f"/data/datasets/{uuid4().hex[:8]}.csv",
            "schema": schema or {
                "columns": ["id", "text", "label"],
                "types": ["int", "str", "str"],
            },
            "metadata": metadata or {},
        }
    
    @staticmethod
    def with_file(file_path: str = "/data/datasets/test.csv") -> Dict[str, Any]:
        """Create a dataset with specific file path."""
        return DatasetFactory.create(
            file_path=file_path,
            size=random.randint(100, 10000),
        )
    
    @staticmethod
    def json_format() -> Dict[str, Any]:
        """Create a JSON format dataset."""
        return DatasetFactory.create(format="json")
    
    @staticmethod
    def csv_format() -> Dict[str, Any]:
        """Create a CSV format dataset."""
        return DatasetFactory.create(format="csv")
    
    @staticmethod
    def empty() -> Dict[str, Any]:
        """Create an empty dataset."""
        return DatasetFactory.create(size=0)
    
    @staticmethod
    def large() -> Dict[str, Any]:
        """Create a large dataset."""
        return DatasetFactory.create(size=1000000)
    
    # =========================================================================
    # Invalid States for Error Testing
    # =========================================================================
    
    @staticmethod
    def missing_required() -> Dict[str, Any]:
        """Create a dataset missing required fields."""
        return {
            "dataset_id": DatasetFactory.generate_uuid(),
            "name": "",  # Required
            "description": "",  # Required
        }
    
    @staticmethod
    def invalid_format(format: str = "invalid_format") -> Dict[str, Any]:
        """Create a dataset with invalid format."""
        return DatasetFactory.create(format=format)
    
    @staticmethod
    def negative_size(size: int = -100) -> Dict[str, Any]:
        """Create a dataset with negative size."""
        return DatasetFactory.create(size=size)
    
    @staticmethod
    def empty_name() -> Dict[str, Any]:
        """Create a dataset with empty name."""
        return DatasetFactory.create(name="")
    
    @staticmethod
    def with_nonexistent_creator() -> Dict[str, Any]:
        """Create a dataset by non-existent user."""
        return DatasetFactory.create(
            created_by=UserFactory.generate_uuid(),
        )


# =============================================================================
# Relationship Factory Helpers
# =============================================================================

class RelationshipFactory:
    """Factory for creating entities with valid relationships."""
    
    @staticmethod
    def user_with_tasks(
        user_id: Optional[UUID] = None,
        task_count: int = 3,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Create a user with multiple tasks."""
        user = UserFactory.create(id=user_id)
        tasks = [
            TaskFactory.create(assigned_to=user["id"])
            for _ in range(task_count)
        ]
        return user, tasks
    
    @staticmethod
    def user_with_annotations(
        user_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        annotation_count: int = 5,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Create a user with multiple annotations."""
        user = UserFactory.create(id=user_id)
        annotations = [
            AnnotationFactory.create(
                task_id=task_id or TaskFactory.generate_uuid(),
                annotator_id=user["id"],
            )
            for _ in range(annotation_count)
        ]
        return user, annotations
    
    @staticmethod
    def task_with_annotations(
        task_id: Optional[UUID] = None,
        annotation_count: int = 3,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Create a task with multiple annotations."""
        task = TaskFactory.create(task_id=task_id)
        annotations = [
            AnnotationFactory.create(task_id=task["task_id"])
            for _ in range(annotation_count)
        ]
        return task, annotations
    
    @staticmethod
    def dataset_with_creator(
        dataset_id: Optional[UUID] = None,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Create a dataset with its creator."""
        user = UserFactory.create()
        dataset = DatasetFactory.create(
            dataset_id=dataset_id,
            created_by=user["id"],
        )
        return dataset, user
    
    @staticmethod
    def complete_workflow() -> Dict[str, Any]:
        """Create a complete annotation workflow: user -> task -> annotations."""
        user = UserFactory.create()
        task = TaskFactory.create(
            assigned_to=user["id"],
            metadata={"created_by": user["id"]},
        )
        annotations = [
            AnnotationFactory.create(
                task_id=task["task_id"],
                annotator_id=user["id"],
            )
            for _ in range(3)
        ]
        return {
            "user": user,
            "task": task,
            "annotations": annotations,
        }


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "UserFactory",
    "TaskFactory",
    "AnnotationFactory",
    "DatasetFactory",
    "RelationshipFactory",
]