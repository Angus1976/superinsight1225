"""Label Studio ML Backend Integration.

This module provides integration with Label Studio's ML Backend framework,
allowing AI annotation models to be used as prediction backends in Label Studio.

Features:
- REST API client for Label Studio
- Model training and prediction
- Version management
- Webhook handling for annotations
- Batch prediction support

Requirements:
- 6.1: Label Studio ML Backend integration
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class LabelStudioTask(BaseModel):
    """Label Studio task format."""
    id: int
    data: Dict[str, Any]
    annotations: List[Dict[str, Any]] = Field(default_factory=list)
    predictions: List[Dict[str, Any]] = Field(default_factory=list)


class LabelStudioPrediction(BaseModel):
    """Label Studio prediction format."""
    result: List[Dict[str, Any]]
    score: Optional[float] = None
    model_version: Optional[str] = None


class LabelStudioProject(BaseModel):
    """Label Studio project metadata."""
    id: int
    title: str
    description: Optional[str] = None
    label_config: str
    expert_instruction: Optional[str] = None
    show_instruction: bool = False
    show_skip_button: bool = True
    enable_empty_annotation: bool = True
    show_annotation_history: bool = False
    organization: Optional[int] = None
    color: Optional[str] = None
    maximum_annotations: int = 1
    is_published: bool = False
    model_version: Optional[str] = None
    is_draft: bool = False
    created_by: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    min_annotations_to_start_training: int = 10
    start_training_on_annotation_update: bool = False
    show_collab_predictions: bool = True
    num_tasks_with_annotations: int = 0
    task_number: int = 0
    useful_annotation_number: int = 0
    ground_truth_number: int = 0
    skipped_annotations_number: int = 0
    total_annotations_number: int = 0
    total_predictions_number: int = 0
    sampling: Optional[str] = None
    show_ground_truth_first: bool = False
    show_overlap_first: bool = False
    overlap_cohort_percentage: int = 100
    task_data_login: Optional[str] = None
    task_data_password: Optional[str] = None
    control_weights: Optional[Dict[str, Any]] = None
    parsed_label_config: Optional[Dict[str, Any]] = None
    evaluate_predictions_automatically: bool = False
    skip_queue: Optional[str] = None
    reveal_preannotations_interactively: bool = False


class ModelVersion(BaseModel):
    """ML model version metadata."""
    version: str
    created_at: datetime
    trained_on_count: int
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrainingStatus(BaseModel):
    """Training job status."""
    job_id: str
    status: str  # "pending", "training", "completed", "failed"
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    model_version: Optional[str] = None


# ============================================================================
# Label Studio ML Backend Engine
# ============================================================================

class LabelStudioMLEngine:
    """Label Studio ML Backend integration engine.

    This class provides a complete integration with Label Studio's ML Backend
    framework, allowing AI models to be used for prediction and training.

    Attributes:
        base_url: Label Studio server URL
        api_key: Label Studio API key
        project_id: Label Studio project ID
        model_versions: Dictionary of trained model versions
        training_jobs: Dictionary of active training jobs
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        project_id: Optional[int] = None,
    ):
        """Initialize Label Studio ML Engine.

        Args:
            base_url: Label Studio server URL (e.g., "http://localhost:8080")
            api_key: Label Studio API authentication token
            project_id: Optional project ID to work with
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.project_id = project_id

        # Model version management
        self.model_versions: Dict[str, ModelVersion] = {}
        self.current_version: Optional[str] = None

        # Training job management
        self.training_jobs: Dict[str, TrainingStatus] = {}

        # HTTP client
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Token {self.api_key}"},
            timeout=30.0,
        )

        # Thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"Initialized Label Studio ML Engine: {base_url}, "
            f"project_id={project_id}"
        )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    # ========================================================================
    # Project Management
    # ========================================================================

    async def get_project(self, project_id: Optional[int] = None) -> LabelStudioProject:
        """Get project details.

        Args:
            project_id: Project ID (uses self.project_id if not provided)

        Returns:
            Project metadata

        Raises:
            ValueError: If no project_id provided or configured
            httpx.HTTPError: If API request fails
        """
        pid = project_id or self.project_id
        if pid is None:
            raise ValueError("No project_id provided or configured")

        url = f"{self.base_url}/api/projects/{pid}"
        response = await self.client.get(url)
        response.raise_for_status()

        data = response.json()
        return LabelStudioProject(**data)

    async def list_projects(self) -> List[LabelStudioProject]:
        """List all accessible projects.

        Returns:
            List of projects
        """
        url = f"{self.base_url}/api/projects"
        response = await self.client.get(url)
        response.raise_for_status()

        data = response.json()
        return [LabelStudioProject(**item) for item in data]

    # ========================================================================
    # Task Management
    # ========================================================================

    async def get_tasks(
        self,
        project_id: Optional[int] = None,
        view_id: Optional[int] = None,
    ) -> List[LabelStudioTask]:
        """Get tasks from project.

        Args:
            project_id: Project ID (uses self.project_id if not provided)
            view_id: Optional view ID to filter tasks

        Returns:
            List of tasks
        """
        pid = project_id or self.project_id
        if pid is None:
            raise ValueError("No project_id provided or configured")

        url = f"{self.base_url}/api/projects/{pid}/tasks"
        params = {}
        if view_id is not None:
            params["view"] = view_id

        response = await self.client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        return [LabelStudioTask(**item) for item in data]

    async def get_task(
        self,
        task_id: int,
        project_id: Optional[int] = None,
    ) -> LabelStudioTask:
        """Get single task.

        Args:
            task_id: Task ID
            project_id: Project ID (uses self.project_id if not provided)

        Returns:
            Task data
        """
        pid = project_id or self.project_id
        if pid is None:
            raise ValueError("No project_id provided or configured")

        url = f"{self.base_url}/api/tasks/{task_id}"
        response = await self.client.get(url)
        response.raise_for_status()

        data = response.json()
        return LabelStudioTask(**data)

    # ========================================================================
    # Prediction (Inference)
    # ========================================================================

    async def predict(
        self,
        tasks: List[LabelStudioTask],
        model_version: Optional[str] = None,
    ) -> List[LabelStudioPrediction]:
        """Generate predictions for tasks.

        This is the main prediction method called by Label Studio ML Backend.

        Args:
            tasks: List of tasks to predict
            model_version: Optional specific model version to use

        Returns:
            List of predictions (one per task)
        """
        version = model_version or self.current_version or "default"

        logger.info(f"Generating predictions for {len(tasks)} tasks (version={version})")

        predictions = []
        for task in tasks:
            try:
                prediction = await self._predict_single(task, version)
                predictions.append(prediction)
            except Exception as e:
                logger.error(f"Prediction failed for task {task.id}: {e}")
                # Return empty prediction on failure
                predictions.append(LabelStudioPrediction(result=[], score=0.0))

        return predictions

    async def _predict_single(
        self,
        task: LabelStudioTask,
        model_version: str,
    ) -> LabelStudioPrediction:
        """Generate prediction for single task.

        This method should be overridden by subclasses to implement
        actual prediction logic.

        Args:
            task: Task to predict
            model_version: Model version to use

        Returns:
            Prediction result
        """
        # Default implementation returns empty prediction
        # Subclasses should override this method
        return LabelStudioPrediction(
            result=[],
            score=0.0,
            model_version=model_version,
        )

    async def create_predictions(
        self,
        task_id: int,
        predictions: List[Dict[str, Any]],
        model_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create predictions for a task via API.

        Args:
            task_id: Task ID
            predictions: Prediction results
            model_version: Optional model version

        Returns:
            API response
        """
        url = f"{self.base_url}/api/predictions"

        payload = {
            "task": task_id,
            "result": predictions,
        }

        if model_version:
            payload["model_version"] = model_version

        response = await self.client.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    # ========================================================================
    # Model Training
    # ========================================================================

    async def train(
        self,
        annotations: List[Dict[str, Any]],
        version_name: Optional[str] = None,
    ) -> TrainingStatus:
        """Train model on annotations.

        Args:
            annotations: Training annotations from Label Studio
            version_name: Optional version name (auto-generated if not provided)

        Returns:
            Training job status
        """
        async with self._lock:
            # Generate version name if not provided
            if version_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                version_name = f"v_{timestamp}"

            # Create training job
            job_id = str(uuid4())
            job = TrainingStatus(
                job_id=job_id,
                status="pending",
                started_at=datetime.now(),
                model_version=version_name,
            )
            self.training_jobs[job_id] = job

            logger.info(
                f"Started training job {job_id} for version {version_name} "
                f"with {len(annotations)} annotations"
            )

        # Start training in background
        asyncio.create_task(self._train_background(job_id, annotations, version_name))

        return job

    async def _train_background(
        self,
        job_id: str,
        annotations: List[Dict[str, Any]],
        version_name: str,
    ):
        """Background training task.

        Args:
            job_id: Training job ID
            annotations: Training data
            version_name: Model version name
        """
        try:
            async with self._lock:
                job = self.training_jobs[job_id]
                job.status = "training"
                job.progress = 0.0

            # Perform training (subclasses should override _train_model)
            metrics = await self._train_model(annotations, version_name, job_id)

            # Create model version
            async with self._lock:
                model_version = ModelVersion(
                    version=version_name,
                    created_at=datetime.now(),
                    trained_on_count=len(annotations),
                    accuracy=metrics.get("accuracy"),
                    precision=metrics.get("precision"),
                    recall=metrics.get("recall"),
                    f1_score=metrics.get("f1_score"),
                    metadata=metrics,
                )
                self.model_versions[version_name] = model_version
                self.current_version = version_name

                # Update job status
                job.status = "completed"
                job.progress = 1.0
                job.completed_at = datetime.now()

            logger.info(f"Training job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Training job {job_id} failed: {e}")
            async with self._lock:
                job = self.training_jobs[job_id]
                job.status = "failed"
                job.error = str(e)
                job.completed_at = datetime.now()

    async def _train_model(
        self,
        annotations: List[Dict[str, Any]],
        version_name: str,
        job_id: str,
    ) -> Dict[str, Any]:
        """Train the actual model.

        This method should be overridden by subclasses to implement
        actual training logic.

        Args:
            annotations: Training data
            version_name: Model version name
            job_id: Training job ID for progress updates

        Returns:
            Training metrics (accuracy, precision, recall, f1_score)
        """
        # Default implementation does nothing
        # Subclasses should override this method
        await asyncio.sleep(1)  # Simulate training
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
        }

    async def get_training_status(self, job_id: str) -> Optional[TrainingStatus]:
        """Get training job status.

        Args:
            job_id: Training job ID

        Returns:
            Training status or None if not found
        """
        return self.training_jobs.get(job_id)

    # ========================================================================
    # Version Management
    # ========================================================================

    async def list_versions(self) -> List[ModelVersion]:
        """List all model versions.

        Returns:
            List of model versions sorted by creation date (newest first)
        """
        versions = list(self.model_versions.values())
        versions.sort(key=lambda v: v.created_at, reverse=True)
        return versions

    async def get_version(self, version: str) -> Optional[ModelVersion]:
        """Get specific model version.

        Args:
            version: Version name

        Returns:
            Model version or None if not found
        """
        return self.model_versions.get(version)

    async def set_current_version(self, version: str) -> bool:
        """Set current active model version.

        Args:
            version: Version name

        Returns:
            True if successful, False if version not found
        """
        if version not in self.model_versions:
            return False

        async with self._lock:
            self.current_version = version

        logger.info(f"Set current model version to {version}")
        return True

    async def delete_version(self, version: str) -> bool:
        """Delete model version.

        Args:
            version: Version name

        Returns:
            True if successful, False if version not found or is current
        """
        if version not in self.model_versions:
            return False

        if version == self.current_version:
            logger.warning(f"Cannot delete current version {version}")
            return False

        async with self._lock:
            del self.model_versions[version]

        logger.info(f"Deleted model version {version}")
        return True

    # ========================================================================
    # Webhook Handling
    # ========================================================================

    async def handle_webhook(
        self,
        event: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle Label Studio webhook event.

        Args:
            event: Event type (e.g., "ANNOTATION_CREATED", "ANNOTATION_UPDATED")
            data: Event payload

        Returns:
            Response data
        """
        logger.info(f"Received webhook event: {event}")

        if event == "ANNOTATION_CREATED":
            return await self._handle_annotation_created(data)
        elif event == "ANNOTATION_UPDATED":
            return await self._handle_annotation_updated(data)
        elif event == "ANNOTATION_DELETED":
            return await self._handle_annotation_deleted(data)
        else:
            logger.warning(f"Unknown webhook event: {event}")
            return {"status": "ignored"}

    async def _handle_annotation_created(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle annotation created event.

        Args:
            data: Event payload

        Returns:
            Response data
        """
        # Default implementation does nothing
        # Subclasses can override to trigger retraining
        return {"status": "ok"}

    async def _handle_annotation_updated(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle annotation updated event.

        Args:
            data: Event payload

        Returns:
            Response data
        """
        return {"status": "ok"}

    async def _handle_annotation_deleted(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle annotation deleted event.

        Args:
            data: Event payload

        Returns:
            Response data
        """
        return {"status": "ok"}


# ============================================================================
# Global Instance Management
# ============================================================================

_label_studio_engines: Dict[str, LabelStudioMLEngine] = {}
_engines_lock = asyncio.Lock()


async def get_label_studio_engine(
    engine_id: str,
    base_url: str,
    api_key: str,
    project_id: Optional[int] = None,
) -> LabelStudioMLEngine:
    """Get or create Label Studio ML Engine instance.

    Args:
        engine_id: Unique engine identifier
        base_url: Label Studio server URL
        api_key: Label Studio API key
        project_id: Optional project ID

    Returns:
        Label Studio ML Engine instance
    """
    async with _engines_lock:
        if engine_id not in _label_studio_engines:
            engine = LabelStudioMLEngine(
                base_url=base_url,
                api_key=api_key,
                project_id=project_id,
            )
            _label_studio_engines[engine_id] = engine

        return _label_studio_engines[engine_id]


async def remove_label_studio_engine(engine_id: str):
    """Remove Label Studio ML Engine instance.

    Args:
        engine_id: Engine identifier
    """
    async with _engines_lock:
        if engine_id in _label_studio_engines:
            engine = _label_studio_engines[engine_id]
            await engine.close()
            del _label_studio_engines[engine_id]


async def reset_label_studio_engines():
    """Reset all Label Studio ML Engine instances (for testing)."""
    async with _engines_lock:
        for engine in _label_studio_engines.values():
            await engine.close()
        _label_studio_engines.clear()
