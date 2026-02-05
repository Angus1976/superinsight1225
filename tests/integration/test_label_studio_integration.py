"""
Integration tests for Label Studio ML Backend integration.

Tests the LabelStudioMLEngine class for:
- Model training API calls
- Prediction API calls
- Version management
- Webhook handling

Validates: Requirements 6.1
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai.label_studio_integration import (
    LabelStudioMLEngine,
    LabelStudioTask,
    LabelStudioPrediction,
    LabelStudioProject,
    ModelVersion,
    TrainingStatus,
    get_label_studio_engine,
    remove_label_studio_engine,
    reset_label_studio_engines,
)


class TestLabelStudioEngineInitialization:
    """Tests for Label Studio engine initialization."""

    def test_engine_initialization(self):
        """Test engine initializes with correct parameters."""
        engine = LabelStudioMLEngine(
            base_url="http://localhost:8080",
            api_key="test-api-key",
            project_id=1,
        )
        
        assert engine.base_url == "http://localhost:8080"
        assert engine.api_key == "test-api-key"
        assert engine.project_id == 1
        assert engine.current_version is None
        assert len(engine.model_versions) == 0

    def test_engine_strips_trailing_slash(self):
        """Test engine strips trailing slash from base_url."""
        engine = LabelStudioMLEngine(
            base_url="http://localhost:8080/",
            api_key="test-api-key",
        )
        
        assert engine.base_url == "http://localhost:8080"


class TestLabelStudioModelTraining:
    """Tests for Label Studio model training."""

    @pytest.fixture
    def engine(self):
        """Create a LabelStudioMLEngine instance for testing."""
        return LabelStudioMLEngine(
            base_url="http://localhost:8080",
            api_key="test-api-key",
            project_id=1,
        )

    @pytest.mark.asyncio
    async def test_train_model_success(self, engine):
        """Test successful model training."""
        annotations = [
            {"id": 1, "result": [{"type": "labels", "value": {"labels": ["PER"]}}]},
            {"id": 2, "result": [{"type": "labels", "value": {"labels": ["ORG"]}}]},
        ]
        
        job = await engine.train(annotations, version_name="v1.0.0")
        
        assert job is not None
        assert job.job_id is not None
        assert job.status in ["pending", "training"]
        assert job.model_version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_train_model_auto_version_name(self, engine):
        """Test training with auto-generated version name."""
        annotations = [{"id": 1, "result": []}]
        
        job = await engine.train(annotations)
        
        assert job.model_version is not None
        assert job.model_version.startswith("v_")

    @pytest.mark.asyncio
    async def test_training_job_status(self, engine):
        """Test getting training job status."""
        annotations = [{"id": 1, "result": []}]
        
        job = await engine.train(annotations, version_name="v1.0.0")
        
        # Get status
        status = await engine.get_training_status(job.job_id)
        
        assert status is not None
        assert status.job_id == job.job_id

    @pytest.mark.asyncio
    async def test_training_job_not_found(self, engine):
        """Test getting status for non-existent job."""
        status = await engine.get_training_status("non-existent-job")
        
        assert status is None

    @pytest.mark.asyncio
    async def test_training_creates_model_version(self, engine):
        """Test that training creates a model version after completion."""
        annotations = [{"id": 1, "result": []}]
        
        job = await engine.train(annotations, version_name="v1.0.0")
        
        # Wait for background training to complete
        await asyncio.sleep(1.5)
        
        # Check version was created
        version = await engine.get_version("v1.0.0")
        assert version is not None
        assert version.version == "v1.0.0"
        assert version.trained_on_count == 1


class TestLabelStudioPrediction:
    """Tests for Label Studio prediction."""

    @pytest.fixture
    def engine(self):
        """Create a LabelStudioMLEngine instance for testing."""
        return LabelStudioMLEngine(
            base_url="http://localhost:8080",
            api_key="test-api-key",
            project_id=1,
        )

    @pytest.mark.asyncio
    async def test_predict_single_task(self, engine):
        """Test prediction for single task."""
        tasks = [
            LabelStudioTask(
                id=1,
                data={"text": "John works at Google"},
            )
        ]
        
        predictions = await engine.predict(tasks)
        
        assert len(predictions) == 1
        assert isinstance(predictions[0], LabelStudioPrediction)

    @pytest.mark.asyncio
    async def test_predict_batch(self, engine):
        """Test batch prediction."""
        tasks = [
            LabelStudioTask(id=1, data={"text": "John works at Google"}),
            LabelStudioTask(id=2, data={"text": "Microsoft is a company"}),
            LabelStudioTask(id=3, data={"text": "Paris is in France"}),
        ]
        
        predictions = await engine.predict(tasks)
        
        assert len(predictions) == 3

    @pytest.mark.asyncio
    async def test_predict_with_model_version(self, engine):
        """Test prediction with specific model version."""
        # First train a model
        annotations = [{"id": 1, "result": []}]
        await engine.train(annotations, version_name="v1.0.0")
        await asyncio.sleep(1.5)
        
        tasks = [LabelStudioTask(id=1, data={"text": "Test"})]
        
        predictions = await engine.predict(tasks, model_version="v1.0.0")
        
        assert len(predictions) == 1
        assert predictions[0].model_version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_predict_empty_tasks(self, engine):
        """Test prediction with empty task list."""
        predictions = await engine.predict([])
        
        assert len(predictions) == 0


class TestLabelStudioVersionManagement:
    """Tests for Label Studio model version management."""

    @pytest.fixture
    def engine(self):
        """Create a LabelStudioMLEngine instance for testing."""
        return LabelStudioMLEngine(
            base_url="http://localhost:8080",
            api_key="test-api-key",
            project_id=1,
        )

    @pytest.mark.asyncio
    async def test_list_versions_empty(self, engine):
        """Test listing versions when none exist."""
        versions = await engine.list_versions()
        
        assert len(versions) == 0

    @pytest.mark.asyncio
    async def test_list_versions(self, engine):
        """Test listing model versions."""
        # Train multiple versions
        await engine.train([{"id": 1, "result": []}], version_name="v1.0.0")
        await asyncio.sleep(1.5)
        await engine.train([{"id": 2, "result": []}], version_name="v1.1.0")
        await asyncio.sleep(1.5)
        
        versions = await engine.list_versions()
        
        assert len(versions) == 2
        # Should be sorted by creation date (newest first)
        assert versions[0].version == "v1.1.0"
        assert versions[1].version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_get_version(self, engine):
        """Test getting specific model version."""
        await engine.train([{"id": 1, "result": []}], version_name="v1.0.0")
        await asyncio.sleep(1.5)
        
        version = await engine.get_version("v1.0.0")
        
        assert version is not None
        assert version.version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_get_version_not_found(self, engine):
        """Test getting non-existent version."""
        version = await engine.get_version("non-existent")
        
        assert version is None

    @pytest.mark.asyncio
    async def test_set_current_version(self, engine):
        """Test setting current active version."""
        await engine.train([{"id": 1, "result": []}], version_name="v1.0.0")
        await asyncio.sleep(1.5)
        
        result = await engine.set_current_version("v1.0.0")
        
        assert result is True
        assert engine.current_version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_set_current_version_not_found(self, engine):
        """Test setting non-existent version as current."""
        result = await engine.set_current_version("non-existent")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_version(self, engine):
        """Test deleting model version."""
        await engine.train([{"id": 1, "result": []}], version_name="v1.0.0")
        await engine.train([{"id": 2, "result": []}], version_name="v1.1.0")
        await asyncio.sleep(2)
        
        # Set v1.1.0 as current so we can delete v1.0.0
        await engine.set_current_version("v1.1.0")
        
        result = await engine.delete_version("v1.0.0")
        
        assert result is True
        assert await engine.get_version("v1.0.0") is None

    @pytest.mark.asyncio
    async def test_delete_current_version_fails(self, engine):
        """Test that deleting current version fails."""
        await engine.train([{"id": 1, "result": []}], version_name="v1.0.0")
        await asyncio.sleep(1.5)
        
        # v1.0.0 is now current
        result = await engine.delete_version("v1.0.0")
        
        assert result is False


class TestLabelStudioWebhooks:
    """Tests for Label Studio webhook handling."""

    @pytest.fixture
    def engine(self):
        """Create a LabelStudioMLEngine instance for testing."""
        return LabelStudioMLEngine(
            base_url="http://localhost:8080",
            api_key="test-api-key",
            project_id=1,
        )

    @pytest.mark.asyncio
    async def test_handle_annotation_created(self, engine):
        """Test handling annotation created webhook."""
        result = await engine.handle_webhook(
            event="ANNOTATION_CREATED",
            data={"annotation": {"id": 1, "result": []}},
        )
        
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_handle_annotation_updated(self, engine):
        """Test handling annotation updated webhook."""
        result = await engine.handle_webhook(
            event="ANNOTATION_UPDATED",
            data={"annotation": {"id": 1, "result": []}},
        )
        
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_handle_annotation_deleted(self, engine):
        """Test handling annotation deleted webhook."""
        result = await engine.handle_webhook(
            event="ANNOTATION_DELETED",
            data={"annotation_id": 1},
        )
        
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_handle_unknown_event(self, engine):
        """Test handling unknown webhook event."""
        result = await engine.handle_webhook(
            event="UNKNOWN_EVENT",
            data={},
        )
        
        assert result["status"] == "ignored"


class TestLabelStudioGlobalManagement:
    """Tests for global engine instance management."""

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self):
        """Clean up engines after each test."""
        yield
        await reset_label_studio_engines()

    @pytest.mark.asyncio
    async def test_get_engine_creates_new(self):
        """Test getting engine creates new instance."""
        engine = await get_label_studio_engine(
            engine_id="test-engine",
            base_url="http://localhost:8080",
            api_key="test-key",
            project_id=1,
        )
        
        assert engine is not None
        assert engine.base_url == "http://localhost:8080"

    @pytest.mark.asyncio
    async def test_get_engine_reuses_existing(self):
        """Test getting engine reuses existing instance."""
        engine1 = await get_label_studio_engine(
            engine_id="test-engine",
            base_url="http://localhost:8080",
            api_key="test-key",
        )
        
        engine2 = await get_label_studio_engine(
            engine_id="test-engine",
            base_url="http://localhost:9090",  # Different URL
            api_key="different-key",
        )
        
        # Should return same instance
        assert engine1 is engine2
        assert engine1.base_url == "http://localhost:8080"

    @pytest.mark.asyncio
    async def test_remove_engine(self):
        """Test removing engine instance."""
        await get_label_studio_engine(
            engine_id="test-engine",
            base_url="http://localhost:8080",
            api_key="test-key",
        )
        
        await remove_label_studio_engine("test-engine")
        
        # Getting again should create new instance
        engine = await get_label_studio_engine(
            engine_id="test-engine",
            base_url="http://localhost:9090",
            api_key="new-key",
        )
        
        assert engine.base_url == "http://localhost:9090"

    @pytest.mark.asyncio
    async def test_reset_engines(self):
        """Test resetting all engine instances."""
        await get_label_studio_engine(
            engine_id="engine1",
            base_url="http://localhost:8080",
            api_key="key1",
        )
        await get_label_studio_engine(
            engine_id="engine2",
            base_url="http://localhost:8081",
            api_key="key2",
        )
        
        await reset_label_studio_engines()
        
        # All engines should be cleared
        engine = await get_label_studio_engine(
            engine_id="engine1",
            base_url="http://localhost:9090",
            api_key="new-key",
        )
        
        assert engine.base_url == "http://localhost:9090"


class TestLabelStudioProjectAPI:
    """Tests for Label Studio project API (with mocked HTTP)."""

    @pytest.fixture
    def engine(self):
        """Create a LabelStudioMLEngine instance for testing."""
        return LabelStudioMLEngine(
            base_url="http://localhost:8080",
            api_key="test-api-key",
            project_id=1,
        )

    @pytest.mark.asyncio
    async def test_get_project_no_id(self, engine):
        """Test get_project raises error when no project_id."""
        engine.project_id = None
        
        with pytest.raises(ValueError, match="No project_id"):
            await engine.get_project()

    @pytest.mark.asyncio
    async def test_get_tasks_no_id(self, engine):
        """Test get_tasks raises error when no project_id."""
        engine.project_id = None
        
        with pytest.raises(ValueError, match="No project_id"):
            await engine.get_tasks()
