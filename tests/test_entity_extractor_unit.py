"""
Unit tests for EntityExtractor.

Tests entity extraction from text, record validation against schema,
confidence computation, batch extraction, and error handling.
Validates: Requirements 3.1, 3.2, 3.3
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.llm_schemas import CloudConfig
from src.ai.schema_inferrer import FieldType, InferredSchema, SchemaField
from src.ai.entity_extractor import (
    EntityExtractionError,
    EntityExtractor,
    ExtractionResult,
    ExtractedStructuredRecord,
    _build_extraction_result,
    _build_schema_description,
    _check_required_fields,
    _clamp_confidence,
    _compute_avg_confidence,
    _LLMExtractionResponse,
    _LLMRecord,
    _truncate_content,
    _validate_record_fields,
    MAX_CONTENT_LENGTH,
)


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
            SchemaField(name="name", field_type=FieldType.STRING, description="Person name", required=True),
            SchemaField(name="age", field_type=FieldType.INTEGER, description="Age in years", required=True),
            SchemaField(name="city", field_type=FieldType.STRING, description="City", required=False),
        ],
        confidence=0.85,
        source_description="People data",
    )


@pytest.fixture
def sample_llm_response():
    return _LLMExtractionResponse(
        records=[
            _LLMRecord(fields={"name": "Alice", "age": 30, "city": "Beijing"}, confidence=0.9, source_span="Alice is 30"),
            _LLMRecord(fields={"name": "Bob", "age": 25}, confidence=0.8, source_span="Bob is 25"),
        ]
    )


def _build_extractor(cloud_config, llm_response=None):
    """Build an EntityExtractor with mocked LLM client."""
    mock_create = AsyncMock(return_value=llm_response)
    mock_client = MagicMock()
    mock_client.chat.completions.create = mock_create

    mock_instructor = MagicMock()
    mock_instructor.from_openai.return_value = mock_client

    mock_async_openai = MagicMock()

    with patch.dict(sys.modules, {
        "instructor": mock_instructor,
        "openai": MagicMock(AsyncOpenAI=mock_async_openai),
    }):
        extractor = EntityExtractor(cloud_config)

    return extractor, mock_create


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


class TestTruncateContent:
    def test_short_content_unchanged(self):
        assert _truncate_content("hello") == "hello"

    def test_long_content_truncated(self):
        text = "a" * (MAX_CONTENT_LENGTH + 100)
        result = _truncate_content(text)
        assert len(result) == MAX_CONTENT_LENGTH

    def test_exact_limit(self):
        text = "b" * MAX_CONTENT_LENGTH
        assert _truncate_content(text) == text


class TestComputeAvgConfidence:
    def test_empty_list(self):
        assert _compute_avg_confidence([]) == 0.0

    def test_single_record(self):
        records = [ExtractedStructuredRecord(fields={"a": 1}, confidence=0.8)]
        assert _compute_avg_confidence(records) == pytest.approx(0.8)

    def test_multiple_records(self):
        records = [
            ExtractedStructuredRecord(fields={"a": 1}, confidence=0.6),
            ExtractedStructuredRecord(fields={"a": 2}, confidence=0.8),
        ]
        assert _compute_avg_confidence(records) == pytest.approx(0.7)


class TestBuildSchemaDescription:
    def test_basic_description(self, sample_schema):
        desc = _build_schema_description(sample_schema)
        assert "name" in desc
        assert "required" in desc
        assert "optional" in desc

    def test_entity_type_included(self):
        schema = InferredSchema(
            fields=[
                SchemaField(
                    name="person", field_type=FieldType.ENTITY,
                    description="A person", entity_type="PERSON",
                ),
            ],
            confidence=0.9,
            source_description="test",
        )
        desc = _build_schema_description(schema)
        assert "PERSON" in desc


class TestValidateRecordFields:
    def test_removes_extra_keys(self, sample_schema):
        record = ExtractedStructuredRecord(fields={"name": "A", "age": 1, "unknown": "x"}, confidence=0.9)
        result = _validate_record_fields(record, sample_schema)
        assert "unknown" not in result.fields
        assert "name" in result.fields

    def test_keeps_valid_keys(self, sample_schema):
        record = ExtractedStructuredRecord(fields={"name": "A", "age": 1, "city": "X"}, confidence=0.9)
        result = _validate_record_fields(record, sample_schema)
        assert len(result.fields) == 3

    def test_clamps_confidence(self, sample_schema):
        record = ExtractedStructuredRecord.model_construct(
            fields={"name": "A", "age": 1}, confidence=1.5, source_span=None,
        )
        result = _validate_record_fields(record, sample_schema)
        assert result.confidence == 1.0


class TestCheckRequiredFields:
    def test_all_required_present(self, sample_schema):
        record = ExtractedStructuredRecord(fields={"name": "A", "age": 1}, confidence=0.9)
        assert _check_required_fields(record, sample_schema) is True

    def test_missing_required_field(self, sample_schema):
        record = ExtractedStructuredRecord(fields={"name": "A"}, confidence=0.9)
        assert _check_required_fields(record, sample_schema) is False

    def test_optional_field_not_required(self, sample_schema):
        record = ExtractedStructuredRecord(fields={"name": "A", "age": 1}, confidence=0.9)
        # city is optional, so this should pass
        assert _check_required_fields(record, sample_schema) is True


class TestBuildExtractionResult:
    def test_empty_records(self):
        result = _build_extraction_result([])
        assert result.total_extracted == 0
        assert result.avg_confidence == 0.0
        assert result.records == []

    def test_computes_totals(self):
        records = [
            ExtractedStructuredRecord(fields={"a": 1}, confidence=0.6),
            ExtractedStructuredRecord(fields={"a": 2}, confidence=0.8),
        ]
        result = _build_extraction_result(records)
        assert result.total_extracted == 2
        assert result.avg_confidence == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# EntityExtractor init
# ---------------------------------------------------------------------------

class TestEntityExtractorInit:
    def test_missing_api_key_raises(self):
        config = CloudConfig(openai_api_key=None)
        with pytest.raises(ValueError, match="API key"):
            EntityExtractor(config)


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

class TestExtract:
    @pytest.mark.asyncio
    async def test_empty_content_raises(self, cloud_config, sample_schema, sample_llm_response):
        extractor, _ = _build_extractor(cloud_config, sample_llm_response)
        with pytest.raises(ValueError, match="non-empty"):
            await extractor.extract("", sample_schema)

    @pytest.mark.asyncio
    async def test_whitespace_only_raises(self, cloud_config, sample_schema, sample_llm_response):
        extractor, _ = _build_extractor(cloud_config, sample_llm_response)
        with pytest.raises(ValueError, match="non-empty"):
            await extractor.extract("   ", sample_schema)

    @pytest.mark.asyncio
    async def test_empty_schema_raises(self, cloud_config, sample_llm_response):
        extractor, _ = _build_extractor(cloud_config, sample_llm_response)
        # Pydantic enforces min_length=1, so we bypass validation to test the guard
        schema = InferredSchema.model_construct(
            fields=[], confidence=0.5, source_description="test",
        )
        with pytest.raises(ValueError, match="at least one field"):
            await extractor.extract("some text", schema)

    @pytest.mark.asyncio
    async def test_successful_extraction(self, cloud_config, sample_schema, sample_llm_response):
        extractor, mock_create = _build_extractor(cloud_config, sample_llm_response)

        result = await extractor.extract("Alice is 30. Bob is 25.", sample_schema)

        assert result.total_extracted == 2
        assert len(result.records) == 2
        assert 0.0 <= result.avg_confidence <= 1.0
        mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_records_fields_subset_of_schema(self, cloud_config, sample_schema, sample_llm_response):
        extractor, _ = _build_extractor(cloud_config, sample_llm_response)

        result = await extractor.extract("Alice is 30.", sample_schema)

        schema_names = {f.name for f in sample_schema.fields}
        for record in result.records:
            assert set(record.fields.keys()).issubset(schema_names)

    @pytest.mark.asyncio
    async def test_required_fields_present(self, cloud_config, sample_schema, sample_llm_response):
        extractor, _ = _build_extractor(cloud_config, sample_llm_response)

        result = await extractor.extract("Alice is 30.", sample_schema)

        required_names = {f.name for f in sample_schema.fields if f.required}
        for record in result.records:
            assert required_names.issubset(record.fields.keys())

    @pytest.mark.asyncio
    async def test_llm_failure_raises_extraction_error(self, cloud_config, sample_schema, sample_llm_response):
        extractor, mock_create = _build_extractor(cloud_config, sample_llm_response)
        mock_create.side_effect = RuntimeError("API down")

        with pytest.raises(EntityExtractionError, match="LLM call failed"):
            await extractor.extract("some text", sample_schema)

    @pytest.mark.asyncio
    async def test_avg_confidence_computed_correctly(self, cloud_config, sample_schema, sample_llm_response):
        extractor, _ = _build_extractor(cloud_config, sample_llm_response)

        result = await extractor.extract("text", sample_schema)

        expected_avg = (0.9 + 0.8) / 2
        assert result.avg_confidence == pytest.approx(expected_avg)

    @pytest.mark.asyncio
    async def test_total_extracted_equals_len_records(self, cloud_config, sample_schema, sample_llm_response):
        extractor, _ = _build_extractor(cloud_config, sample_llm_response)

        result = await extractor.extract("text", sample_schema)

        assert result.total_extracted == len(result.records)


# ---------------------------------------------------------------------------
# extract_batch
# ---------------------------------------------------------------------------

class TestExtractBatch:
    @pytest.mark.asyncio
    async def test_empty_contents_raises(self, cloud_config, sample_schema, sample_llm_response):
        extractor, _ = _build_extractor(cloud_config, sample_llm_response)
        with pytest.raises(ValueError, match="non-empty"):
            await extractor.extract_batch([], sample_schema)

    @pytest.mark.asyncio
    async def test_batch_merges_results(self, cloud_config, sample_schema, sample_llm_response):
        extractor, mock_create = _build_extractor(cloud_config, sample_llm_response)

        result = await extractor.extract_batch(["text1", "text2"], sample_schema)

        # Each call returns 2 records, so batch of 2 → 4 records
        assert result.total_extracted == 4
        assert len(result.records) == 4
        assert mock_create.await_count == 2

    @pytest.mark.asyncio
    async def test_batch_skips_empty_strings(self, cloud_config, sample_schema, sample_llm_response):
        extractor, mock_create = _build_extractor(cloud_config, sample_llm_response)

        result = await extractor.extract_batch(["text1", "", "  ", "text2"], sample_schema)

        # Only 2 non-empty contents processed
        assert mock_create.await_count == 2

    @pytest.mark.asyncio
    async def test_batch_empty_schema_raises(self, cloud_config, sample_llm_response):
        extractor, _ = _build_extractor(cloud_config, sample_llm_response)
        schema = InferredSchema.model_construct(
            fields=[], confidence=0.5, source_description="test",
        )
        with pytest.raises(ValueError, match="at least one field"):
            await extractor.extract_batch(["text"], schema)


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

class TestPostProcess:
    def test_filters_invalid_keys(self, sample_schema):
        response = _LLMExtractionResponse(
            records=[
                _LLMRecord(fields={"name": "A", "age": 1, "extra": "x"}, confidence=0.9),
            ]
        )
        result = EntityExtractor._post_process(response, sample_schema)
        assert "extra" not in result.records[0].fields

    def test_skips_records_missing_required(self, sample_schema):
        response = _LLMExtractionResponse(
            records=[
                _LLMRecord(fields={"name": "A", "age": 1}, confidence=0.9),
                _LLMRecord(fields={"name": "B"}, confidence=0.7),  # missing 'age'
            ]
        )
        result = EntityExtractor._post_process(response, sample_schema)
        assert result.total_extracted == 1
        assert result.records[0].fields["name"] == "A"

    def test_clamps_confidence_in_records(self, sample_schema):
        response = _LLMExtractionResponse(
            records=[
                _LLMRecord(fields={"name": "A", "age": 1}, confidence=1.5),
            ]
        )
        result = EntityExtractor._post_process(response, sample_schema)
        assert result.records[0].confidence == 1.0

    def test_empty_response(self, sample_schema):
        response = _LLMExtractionResponse(records=[])
        result = EntityExtractor._post_process(response, sample_schema)
        assert result.total_extracted == 0
        assert result.avg_confidence == 0.0
