"""
Integration tests for Argilla Platform integration.

Tests the ArgillaEngine class for:
- Dataset creation and management
- Record import/export
- Feedback collection
- Annotation statistics

Validates: Requirements 6.2
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime

from src.ai.argilla_integration import (
    ArgillaEngine,
    ArgillaDataset,
    ArgillaRecord,
    ArgillaField,
    ArgillaQuestion,
    ArgillaSuggestion,
    ArgillaResponse,
    RecordStatus,
    FeedbackType,
    DatasetStatistics,
    get_argilla_engine,
    remove_argilla_engine,
    reset_argilla_engines,
)


class TestArgillaEngineInitialization:
    """Tests for Argilla engine initialization."""

    def test_engine_initialization(self):
        """Test engine initializes with correct parameters."""
        engine = ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test-api-key",
            workspace="test-workspace",
        )
        
        assert engine.api_url == "http://localhost:6900"
        assert engine.api_key == "test-api-key"
        assert engine.workspace == "test-workspace"
        assert len(engine.datasets) == 0

    def test_engine_strips_trailing_slash(self):
        """Test engine strips trailing slash from api_url."""
        engine = ArgillaEngine(
            api_url="http://localhost:6900/",
            api_key="test-api-key",
        )
        
        assert engine.api_url == "http://localhost:6900"

    def test_engine_default_workspace(self):
        """Test engine uses default workspace."""
        engine = ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test-api-key",
        )
        
        assert engine.workspace == "default"


class TestArgillaDatasetManagement:
    """Tests for Argilla dataset management."""

    @pytest.fixture
    def engine(self):
        """Create an ArgillaEngine instance for testing."""
        return ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test-api-key",
            workspace="test-workspace",
        )

    @pytest.fixture
    def sample_fields(self):
        """Create sample field definitions."""
        return [
            ArgillaField(name="text", title="Text", type="text"),
            ArgillaField(name="metadata", title="Metadata", type="text", required=False),
        ]

    @pytest.fixture
    def sample_questions(self):
        """Create sample question definitions."""
        return [
            ArgillaQuestion(
                name="sentiment",
                title="Sentiment",
                type=FeedbackType.LABEL,
                settings={"options": ["positive", "negative", "neutral"]},
            ),
            ArgillaQuestion(
                name="rating",
                title="Quality Rating",
                type=FeedbackType.RATING,
                settings={"min": 1, "max": 5},
            ),
        ]

    @pytest.mark.asyncio
    async def test_create_dataset(self, engine, sample_fields, sample_questions):
        """Test creating a new dataset."""
        dataset = await engine.create_dataset(
            name="test-dataset",
            fields=sample_fields,
            questions=sample_questions,
            guidelines="Annotate the sentiment of the text.",
        )
        
        assert dataset is not None
        assert dataset.name == "test-dataset"
        assert dataset.workspace == "test-workspace"
        assert dataset.guidelines == "Annotate the sentiment of the text."
        assert len(dataset.fields) == 2
        assert len(dataset.questions) == 2

    @pytest.mark.asyncio
    async def test_create_dataset_custom_workspace(self, engine, sample_fields, sample_questions):
        """Test creating dataset in custom workspace."""
        dataset = await engine.create_dataset(
            name="test-dataset",
            fields=sample_fields,
            questions=sample_questions,
            workspace="custom-workspace",
        )
        
        assert dataset.workspace == "custom-workspace"

    @pytest.mark.asyncio
    async def test_create_dataset_duplicate(self, engine, sample_fields, sample_questions):
        """Test creating duplicate dataset returns existing."""
        dataset1 = await engine.create_dataset(
            name="test-dataset",
            fields=sample_fields,
            questions=sample_questions,
        )
        
        dataset2 = await engine.create_dataset(
            name="test-dataset",
            fields=sample_fields,
            questions=sample_questions,
        )
        
        assert dataset1.id == dataset2.id

    @pytest.mark.asyncio
    async def test_get_dataset(self, engine, sample_fields, sample_questions):
        """Test getting dataset by name."""
        await engine.create_dataset(
            name="test-dataset",
            fields=sample_fields,
            questions=sample_questions,
        )
        
        dataset = await engine.get_dataset("test-dataset")
        
        assert dataset is not None
        assert dataset.name == "test-dataset"

    @pytest.mark.asyncio
    async def test_get_dataset_not_found(self, engine):
        """Test getting non-existent dataset."""
        dataset = await engine.get_dataset("non-existent")
        
        assert dataset is None

    @pytest.mark.asyncio
    async def test_list_datasets(self, engine, sample_fields, sample_questions):
        """Test listing datasets in workspace."""
        await engine.create_dataset(
            name="dataset1",
            fields=sample_fields,
            questions=sample_questions,
        )
        await engine.create_dataset(
            name="dataset2",
            fields=sample_fields,
            questions=sample_questions,
        )
        
        datasets = await engine.list_datasets()
        
        assert len(datasets) == 2

    @pytest.mark.asyncio
    async def test_list_datasets_filters_by_workspace(self, engine, sample_fields, sample_questions):
        """Test listing datasets filters by workspace."""
        await engine.create_dataset(
            name="dataset1",
            fields=sample_fields,
            questions=sample_questions,
            workspace="workspace1",
        )
        await engine.create_dataset(
            name="dataset2",
            fields=sample_fields,
            questions=sample_questions,
            workspace="workspace2",
        )
        
        datasets = await engine.list_datasets(workspace="workspace1")
        
        assert len(datasets) == 1
        assert datasets[0].name == "dataset1"

    @pytest.mark.asyncio
    async def test_delete_dataset(self, engine, sample_fields, sample_questions):
        """Test deleting dataset."""
        await engine.create_dataset(
            name="test-dataset",
            fields=sample_fields,
            questions=sample_questions,
        )
        
        result = await engine.delete_dataset("test-dataset")
        
        assert result is True
        assert await engine.get_dataset("test-dataset") is None

    @pytest.mark.asyncio
    async def test_delete_dataset_not_found(self, engine):
        """Test deleting non-existent dataset."""
        result = await engine.delete_dataset("non-existent")
        
        assert result is False


class TestArgillaRecordManagement:
    """Tests for Argilla record management."""

    @pytest_asyncio.fixture
    async def engine_with_dataset(self):
        """Create engine with a dataset."""
        engine = ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test-api-key",
            workspace="test-workspace",
        )
        
        await engine.create_dataset(
            name="test-dataset",
            fields=[ArgillaField(name="text", title="Text", type="text")],
            questions=[ArgillaQuestion(name="label", title="Label", type=FeedbackType.LABEL)],
        )
        
        return engine

    @pytest.mark.asyncio
    async def test_add_records(self, engine_with_dataset):
        """Test adding records to dataset."""
        records = [
            ArgillaRecord(id="1", fields={"text": "Hello world"}),
            ArgillaRecord(id="2", fields={"text": "Goodbye world"}),
        ]
        
        count = await engine_with_dataset.add_records("test-dataset", records)
        
        assert count == 2
        
        # Check dataset record count updated
        dataset = await engine_with_dataset.get_dataset("test-dataset")
        assert dataset.num_records == 2

    @pytest.mark.asyncio
    async def test_add_records_dataset_not_found(self, engine_with_dataset):
        """Test adding records to non-existent dataset."""
        records = [ArgillaRecord(id="1", fields={"text": "Hello"})]
        
        with pytest.raises(ValueError, match="not found"):
            await engine_with_dataset.add_records("non-existent", records)

    @pytest.mark.asyncio
    async def test_get_records(self, engine_with_dataset):
        """Test getting records from dataset."""
        records = await engine_with_dataset.get_records("test-dataset")
        
        # Returns empty list in mock implementation
        assert isinstance(records, list)

    @pytest.mark.asyncio
    async def test_get_records_dataset_not_found(self, engine_with_dataset):
        """Test getting records from non-existent dataset."""
        with pytest.raises(ValueError, match="not found"):
            await engine_with_dataset.get_records("non-existent")

    @pytest.mark.asyncio
    async def test_update_record(self, engine_with_dataset):
        """Test updating record."""
        result = await engine_with_dataset.update_record(
            dataset_name="test-dataset",
            record_id="1",
            updates={"fields": {"text": "Updated text"}},
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_record(self, engine_with_dataset):
        """Test deleting record."""
        # First add a record
        await engine_with_dataset.add_records(
            "test-dataset",
            [ArgillaRecord(id="1", fields={"text": "Hello"})],
        )
        
        result = await engine_with_dataset.delete_record("test-dataset", "1")
        
        assert result is True


class TestArgillaSuggestions:
    """Tests for Argilla suggestions (AI predictions)."""

    @pytest_asyncio.fixture
    async def engine_with_dataset(self):
        """Create engine with a dataset."""
        engine = ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test-api-key",
        )
        
        await engine.create_dataset(
            name="test-dataset",
            fields=[ArgillaField(name="text", title="Text", type="text")],
            questions=[ArgillaQuestion(name="label", title="Label", type=FeedbackType.LABEL)],
        )
        
        return engine

    @pytest.mark.asyncio
    async def test_add_suggestions(self, engine_with_dataset):
        """Test adding suggestions to record."""
        suggestions = [
            ArgillaSuggestion(
                question_name="label",
                value="positive",
                score=0.95,
                agent="ai-model-v1",
            ),
        ]
        
        result = await engine_with_dataset.add_suggestions(
            dataset_name="test-dataset",
            record_id="1",
            suggestions=suggestions,
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_add_batch_suggestions(self, engine_with_dataset):
        """Test adding suggestions for multiple records."""
        suggestions_map = {
            "1": [ArgillaSuggestion(question_name="label", value="positive", score=0.9)],
            "2": [ArgillaSuggestion(question_name="label", value="negative", score=0.85)],
            "3": [ArgillaSuggestion(question_name="label", value="neutral", score=0.7)],
        }
        
        count = await engine_with_dataset.add_batch_suggestions(
            dataset_name="test-dataset",
            suggestions_map=suggestions_map,
        )
        
        assert count == 3


class TestArgillaResponses:
    """Tests for Argilla responses (human annotations)."""

    @pytest_asyncio.fixture
    async def engine_with_dataset(self):
        """Create engine with a dataset."""
        engine = ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test-api-key",
        )
        
        await engine.create_dataset(
            name="test-dataset",
            fields=[ArgillaField(name="text", title="Text", type="text")],
            questions=[ArgillaQuestion(name="label", title="Label", type=FeedbackType.LABEL)],
        )
        
        return engine

    @pytest.mark.asyncio
    async def test_submit_response(self, engine_with_dataset):
        """Test submitting annotation response."""
        response = await engine_with_dataset.submit_response(
            dataset_name="test-dataset",
            record_id="1",
            user_id="user-123",
            values={"label": "positive"},
        )
        
        assert response is not None
        assert response.user_id == "user-123"
        assert response.values == {"label": "positive"}
        assert response.status == RecordStatus.SUBMITTED

    @pytest.mark.asyncio
    async def test_get_responses(self, engine_with_dataset):
        """Test getting responses from dataset."""
        responses = await engine_with_dataset.get_responses("test-dataset")
        
        # Returns empty list in mock implementation
        assert isinstance(responses, list)


class TestArgillaStatistics:
    """Tests for Argilla statistics and analytics."""

    @pytest_asyncio.fixture
    async def engine_with_dataset(self):
        """Create engine with a dataset."""
        engine = ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test-api-key",
        )
        
        await engine.create_dataset(
            name="test-dataset",
            fields=[ArgillaField(name="text", title="Text", type="text")],
            questions=[ArgillaQuestion(name="label", title="Label", type=FeedbackType.LABEL)],
        )
        
        # Add some records
        await engine.add_records(
            "test-dataset",
            [
                ArgillaRecord(id="1", fields={"text": "Hello"}),
                ArgillaRecord(id="2", fields={"text": "World"}),
            ],
        )
        
        return engine

    @pytest.mark.asyncio
    async def test_get_dataset_statistics(self, engine_with_dataset):
        """Test getting dataset statistics."""
        stats = await engine_with_dataset.get_dataset_statistics("test-dataset")
        
        assert isinstance(stats, DatasetStatistics)
        assert stats.total_records == 2

    @pytest.mark.asyncio
    async def test_calculate_agreement(self, engine_with_dataset):
        """Test calculating inter-annotator agreement."""
        agreement = await engine_with_dataset.calculate_agreement(
            dataset_name="test-dataset",
            question_name="label",
        )
        
        assert isinstance(agreement, float)
        assert 0.0 <= agreement <= 1.0


class TestArgillaExportImport:
    """Tests for Argilla export and import."""

    @pytest_asyncio.fixture
    async def engine_with_dataset(self):
        """Create engine with a dataset."""
        engine = ArgillaEngine(
            api_url="http://localhost:6900",
            api_key="test-api-key",
        )
        
        await engine.create_dataset(
            name="test-dataset",
            fields=[ArgillaField(name="text", title="Text", type="text")],
            questions=[ArgillaQuestion(name="label", title="Label", type=FeedbackType.LABEL)],
            guidelines="Test guidelines",
        )
        
        return engine

    @pytest.mark.asyncio
    async def test_export_dataset(self, engine_with_dataset):
        """Test exporting dataset."""
        export_data = await engine_with_dataset.export_dataset("test-dataset")
        
        assert "dataset" in export_data
        assert "records" in export_data
        assert export_data["dataset"]["name"] == "test-dataset"

    @pytest.mark.asyncio
    async def test_import_dataset(self, engine_with_dataset):
        """Test importing dataset."""
        import_data = {
            "dataset": {
                "name": "imported-dataset",
                "fields": [{"name": "text", "title": "Text", "type": "text", "required": True, "settings": {}}],
                "questions": [{"name": "label", "title": "Label", "type": "label", "required": True, "settings": {}}],
                "guidelines": "Imported guidelines",
            },
            "records": [],
        }
        
        dataset = await engine_with_dataset.import_dataset(import_data)
        
        assert dataset.name == "imported-dataset"

    @pytest.mark.asyncio
    async def test_import_dataset_no_name(self, engine_with_dataset):
        """Test importing dataset without name fails."""
        import_data = {"dataset": {}, "records": []}
        
        with pytest.raises(ValueError, match="name required"):
            await engine_with_dataset.import_dataset(import_data)


class TestArgillaGlobalManagement:
    """Tests for global engine instance management."""

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self):
        """Clean up engines after each test."""
        yield
        await reset_argilla_engines()

    @pytest.mark.asyncio
    async def test_get_engine_creates_new(self):
        """Test getting engine creates new instance."""
        engine = await get_argilla_engine(
            engine_id="test-engine",
            api_url="http://localhost:6900",
            api_key="test-key",
            workspace="test-workspace",
        )
        
        assert engine is not None
        assert engine.api_url == "http://localhost:6900"
        assert engine.workspace == "test-workspace"

    @pytest.mark.asyncio
    async def test_get_engine_reuses_existing(self):
        """Test getting engine reuses existing instance."""
        engine1 = await get_argilla_engine(
            engine_id="test-engine",
            api_url="http://localhost:6900",
            api_key="test-key",
        )
        
        engine2 = await get_argilla_engine(
            engine_id="test-engine",
            api_url="http://localhost:7000",  # Different URL
            api_key="different-key",
        )
        
        # Should return same instance
        assert engine1 is engine2
        assert engine1.api_url == "http://localhost:6900"

    @pytest.mark.asyncio
    async def test_remove_engine(self):
        """Test removing engine instance."""
        await get_argilla_engine(
            engine_id="test-engine",
            api_url="http://localhost:6900",
            api_key="test-key",
        )
        
        await remove_argilla_engine("test-engine")
        
        # Getting again should create new instance
        engine = await get_argilla_engine(
            engine_id="test-engine",
            api_url="http://localhost:7000",
            api_key="new-key",
        )
        
        assert engine.api_url == "http://localhost:7000"

    @pytest.mark.asyncio
    async def test_reset_engines(self):
        """Test resetting all engine instances."""
        await get_argilla_engine(
            engine_id="engine1",
            api_url="http://localhost:6900",
            api_key="key1",
        )
        await get_argilla_engine(
            engine_id="engine2",
            api_url="http://localhost:6901",
            api_key="key2",
        )
        
        await reset_argilla_engines()
        
        # All engines should be cleared
        engine = await get_argilla_engine(
            engine_id="engine1",
            api_url="http://localhost:7000",
            api_key="new-key",
        )
        
        assert engine.api_url == "http://localhost:7000"
