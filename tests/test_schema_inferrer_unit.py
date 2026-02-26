"""
Unit tests for SchemaInferrer.

Tests schema inference from text and tabular data, field deduplication,
confidence clamping, error handling, and input validation.
Validates: Requirements 2.1, 2.2
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.llm_schemas import CloudConfig
from src.ai.schema_inferrer import (
    FieldType,
    InferredSchema,
    SchemaField,
    SchemaInferenceError,
    SchemaInferrer,
    _clamp_confidence,
    _deduplicate_fields,
    _tabular_to_preview,
    _truncate_text,
    MAX_TEXT_LENGTH,
)
from src.extractors.tabular import TabularData


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cloud_config():
    return CloudConfig(
        openai_api_key="test-key-123",
        openai_base_url="https://api.openai.com/v1",
        openai_model="gpt-4o-mini",
    )


@pytest.fixture
def sample_schema():
    return InferredSchema(
        fields=[
            SchemaField(name="name", field_type=FieldType.STRING, description="Person name"),
            SchemaField(name="age", field_type=FieldType.INTEGER, description="Age in years"),
        ],
        confidence=0.85,
        source_description="A list of people with names and ages",
    )


@pytest.fixture
def sample_tabular():
    return TabularData(
        headers=["name", "age", "city"],
        rows=[
            {"name": "Alice", "age": 30, "city": "Beijing"},
            {"name": "Bob", "age": 25, "city": "Shanghai"},
        ],
        row_count=2,
        file_type="csv",
    )


def _build_inferrer(cloud_config, sample_schema=None):
    """Build a SchemaInferrer with mocked LLM client.

    Returns (inferrer, mock_create) where mock_create is the
    AsyncMock for client.chat.completions.create.
    """
    mock_create = AsyncMock(return_value=sample_schema)
    mock_client = MagicMock()
    mock_client.chat.completions.create = mock_create

    mock_instructor = MagicMock()
    mock_instructor.from_openai.return_value = mock_client

    mock_async_openai = MagicMock()

    with patch.dict(sys.modules, {
        "instructor": mock_instructor,
        "openai": MagicMock(AsyncOpenAI=mock_async_openai),
    }):
        inferrer = SchemaInferrer(cloud_config)

    return inferrer, mock_create


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestClampConfidence:
    def test_within_range(self):
        assert _clamp_confidence(0.5) == 0.5

    def test_below_zero(self):
        assert _clamp_confidence(-0.3) == 0.0

    def test_above_one(self):
        assert _clamp_confidence(1.5) == 1.0

    def test_boundaries(self):
        assert _clamp_confidence(0.0) == 0.0
        assert _clamp_confidence(1.0) == 1.0


class TestDeduplicateFields:
    def test_no_duplicates(self):
        fields = [
            SchemaField(name="a", field_type=FieldType.STRING, description="A"),
            SchemaField(name="b", field_type=FieldType.INTEGER, description="B"),
        ]
        result = _deduplicate_fields(fields)
        assert len(result) == 2

    def test_removes_duplicates_keeps_first(self):
        fields = [
            SchemaField(name="x", field_type=FieldType.STRING, description="First"),
            SchemaField(name="x", field_type=FieldType.INTEGER, description="Second"),
            SchemaField(name="y", field_type=FieldType.FLOAT, description="Y"),
        ]
        result = _deduplicate_fields(fields)
        assert len(result) == 2
        assert result[0].description == "First"
        assert result[1].name == "y"

    def test_empty_list(self):
        assert _deduplicate_fields([]) == []


class TestTruncateText:
    def test_short_text_unchanged(self):
        assert _truncate_text("hello") == "hello"

    def test_long_text_truncated(self):
        text = "a" * (MAX_TEXT_LENGTH + 100)
        result = _truncate_text(text)
        assert len(result) == MAX_TEXT_LENGTH

    def test_exact_limit(self):
        text = "b" * MAX_TEXT_LENGTH
        assert _truncate_text(text) == text


class TestTabularToPreview:
    def test_basic_preview(self, sample_tabular):
        preview = _tabular_to_preview(sample_tabular)
        assert "csv" in preview
        assert "name" in preview
        assert "Alice" in preview
        assert "Total rows: 2" in preview

    def test_with_sheet_name(self):
        data = TabularData(
            headers=["col"],
            rows=[{"col": 1}],
            row_count=1,
            file_type="excel",
            sheet_name="Sheet1",
        )
        preview = _tabular_to_preview(data)
        assert "Sheet1" in preview


# ---------------------------------------------------------------------------
# SchemaInferrer init
# ---------------------------------------------------------------------------

class TestSchemaInferrerInit:
    def test_missing_api_key_raises(self):
        config = CloudConfig(openai_api_key=None)
        with pytest.raises(ValueError, match="API key"):
            # Even with missing key, the guard runs before import
            SchemaInferrer(config)


# ---------------------------------------------------------------------------
# infer_from_text
# ---------------------------------------------------------------------------

class TestInferFromText:
    @pytest.mark.asyncio
    async def test_empty_text_raises(self, cloud_config, sample_schema):
        inferrer, _ = _build_inferrer(cloud_config, sample_schema)
        with pytest.raises(ValueError, match="non-empty"):
            await inferrer.infer_from_text("")

    @pytest.mark.asyncio
    async def test_whitespace_only_raises(self, cloud_config, sample_schema):
        inferrer, _ = _build_inferrer(cloud_config, sample_schema)
        with pytest.raises(ValueError, match="non-empty"):
            await inferrer.infer_from_text("   ")

    @pytest.mark.asyncio
    async def test_successful_inference(self, cloud_config, sample_schema):
        inferrer, mock_create = _build_inferrer(cloud_config, sample_schema)

        result = await inferrer.infer_from_text("Alice is 30 years old.")

        assert len(result.fields) == 2
        assert result.confidence == 0.85
        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_with_hint(self, cloud_config, sample_schema):
        inferrer, mock_create = _build_inferrer(cloud_config, sample_schema)

        result = await inferrer.infer_from_text("Some text", hint="people data")

        assert result is not None
        call_kwargs = mock_create.call_args
        user_msg = call_kwargs.kwargs["messages"][1]["content"]
        assert "people data" in user_msg

    @pytest.mark.asyncio
    async def test_llm_failure_raises_schema_error(self, cloud_config, sample_schema):
        inferrer, mock_create = _build_inferrer(cloud_config, sample_schema)
        mock_create.side_effect = RuntimeError("API down")

        with pytest.raises(SchemaInferenceError, match="LLM call failed"):
            await inferrer.infer_from_text("some text")

    @pytest.mark.asyncio
    async def test_long_text_truncated(self, cloud_config, sample_schema):
        inferrer, mock_create = _build_inferrer(cloud_config, sample_schema)

        long_text = "x" * (MAX_TEXT_LENGTH + 5000)
        await inferrer.infer_from_text(long_text)

        call_kwargs = mock_create.call_args
        user_msg = call_kwargs.kwargs["messages"][1]["content"]
        # The user content should not contain the full long text
        assert len(user_msg) < len(long_text)


# ---------------------------------------------------------------------------
# infer_from_tabular
# ---------------------------------------------------------------------------

class TestInferFromTabular:
    @pytest.mark.asyncio
    async def test_empty_headers_raises(self, cloud_config, sample_schema):
        inferrer, _ = _build_inferrer(cloud_config, sample_schema)
        data = TabularData(headers=[], rows=[], row_count=0, file_type="csv")

        with pytest.raises(ValueError, match="at least one header"):
            await inferrer.infer_from_tabular(data)

    @pytest.mark.asyncio
    async def test_successful_tabular_inference(self, cloud_config, sample_schema, sample_tabular):
        inferrer, mock_create = _build_inferrer(cloud_config, sample_schema)

        result = await inferrer.infer_from_tabular(sample_tabular)

        assert len(result.fields) >= 1
        assert 0.0 <= result.confidence <= 1.0
        mock_create.assert_awaited_once()


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

class TestPostProcess:
    def test_deduplicates_fields(self):
        schema = InferredSchema(
            fields=[
                SchemaField(name="dup", field_type=FieldType.STRING, description="A"),
                SchemaField(name="dup", field_type=FieldType.INTEGER, description="B"),
                SchemaField(name="unique", field_type=FieldType.FLOAT, description="C"),
            ],
            confidence=0.9,
            source_description="test",
        )
        result = SchemaInferrer._post_process(schema)
        names = [f.name for f in result.fields]
        assert len(names) == len(set(names))

    def test_clamps_confidence(self):
        schema = InferredSchema(
            fields=[SchemaField(name="a", field_type=FieldType.STRING, description="A")],
            confidence=0.95,
            source_description="test",
        )
        result = SchemaInferrer._post_process(schema)
        assert 0.0 <= result.confidence <= 1.0

    def test_field_names_unique_in_result(self):
        schema = InferredSchema(
            fields=[
                SchemaField(name="x", field_type=FieldType.STRING, description="X1"),
                SchemaField(name="y", field_type=FieldType.STRING, description="Y"),
                SchemaField(name="x", field_type=FieldType.STRING, description="X2"),
            ],
            confidence=0.7,
            source_description="test",
        )
        result = SchemaInferrer._post_process(schema)
        names = [f.name for f in result.fields]
        assert names == ["x", "y"]
