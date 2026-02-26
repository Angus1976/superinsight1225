"""
Entity extraction using instructor + OpenAI.

Extracts structured records from unstructured text according to
an InferredSchema definition via LLM.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

try:
    from src.ai.llm_schemas import CloudConfig
    from src.ai.retry import retry_with_backoff
    from src.ai.schema_inferrer import FieldType, InferredSchema, SchemaField
except ImportError:
    from ai.llm_schemas import CloudConfig
    from ai.retry import retry_with_backoff
    from ai.schema_inferrer import FieldType, InferredSchema, SchemaField

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 50_000


class EntityExtractionError(Exception):
    """Raised when LLM-based entity extraction fails."""


class StructuredRecord(BaseModel):
    """A single record extracted from source content."""
    fields: dict[str, Any] = Field(description="Extracted field values keyed by field name")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    source_span: Optional[str] = Field(
        default=None,
        description="Source text span this record was extracted from",
    )


class ExtractionResult(BaseModel):
    """Result of entity extraction."""
    records: list[StructuredRecord] = Field(description="Extracted records")
    total_extracted: int = Field(description="Number of records extracted")
    avg_confidence: float = Field(ge=0.0, le=1.0, description="Average confidence")


# ---------------------------------------------------------------------------
# LLM response model (used by instructor to parse structured output)
# ---------------------------------------------------------------------------

class _LLMRecord(BaseModel):
    """Single record as returned by the LLM (no clamping — raw values)."""
    fields: dict[str, Any] = Field(description="Extracted field values")
    confidence: float = Field(description="Confidence 0.0-1.0")  # no ge/le — clamped later
    source_span: Optional[str] = Field(
        default=None, description="Source text fragment",
    )


class _LLMExtractionResponse(BaseModel):
    """Top-level LLM response containing extracted records."""
    records: list[_LLMRecord] = Field(description="List of extracted records")


# ---------------------------------------------------------------------------
# Pure helper functions (no LLM dependency)
# ---------------------------------------------------------------------------

def _clamp_confidence(value: float) -> float:
    """Clamp confidence to [0.0, 1.0]."""
    return max(0.0, min(1.0, value))


def _truncate_content(content: str) -> str:
    """Truncate content to MAX_CONTENT_LENGTH characters."""
    if len(content) > MAX_CONTENT_LENGTH:
        return content[:MAX_CONTENT_LENGTH]
    return content


def _compute_avg_confidence(records: list[StructuredRecord]) -> float:
    """Compute mean confidence across records. Returns 0.0 for empty list."""
    if not records:
        return 0.0
    total = sum(r.confidence for r in records)
    return total / len(records)


def _build_schema_description(schema: InferredSchema) -> str:
    """Build a human-readable schema description for the LLM prompt."""
    lines: list[str] = []
    for field in schema.fields:
        req = "required" if field.required else "optional"
        line = f"- {field.name} ({field.field_type.value}, {req}): {field.description}"
        if field.entity_type:
            line += f" [entity: {field.entity_type}]"
        lines.append(line)
    return "\n".join(lines)


def _validate_record_fields(
    record: StructuredRecord,
    schema: InferredSchema,
) -> StructuredRecord:
    """Validate and filter record fields against the schema.

    - Removes keys not present in the schema
    - Returns the cleaned record (required-field check is done separately)
    """
    valid_names = {f.name for f in schema.fields}
    cleaned = {k: v for k, v in record.fields.items() if k in valid_names}
    return StructuredRecord(
        fields=cleaned,
        confidence=_clamp_confidence(record.confidence),
        source_span=record.source_span,
    )


def _check_required_fields(
    record: StructuredRecord,
    schema: InferredSchema,
) -> bool:
    """Return True if all required fields are present in the record."""
    required_names = {f.name for f in schema.fields if f.required}
    return required_names.issubset(record.fields.keys())


def _build_extraction_result(records: list[StructuredRecord]) -> ExtractionResult:
    """Build ExtractionResult with computed totals."""
    return ExtractionResult(
        records=records,
        total_extracted=len(records),
        avg_confidence=_clamp_confidence(_compute_avg_confidence(records)),
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT = (
    "You are a data extraction specialist. Extract structured records from the "
    "provided text according to the given schema. Each record must contain the "
    "specified fields with appropriate values. Include a confidence score (0.0-1.0) "
    "for each record and optionally quote the source text span. "
    "Extract ALL matching records found in the text."
)


# ---------------------------------------------------------------------------
# EntityExtractor
# ---------------------------------------------------------------------------

class EntityExtractor:
    """Extracts structured records from text using instructor + OpenAI.

    The ``instructor`` and ``openai`` packages are imported lazily in the
    constructor so that the rest of this module (data-classes, helpers) can
    be used without requiring those packages at import time.
    """

    def __init__(self, cloud_config: CloudConfig) -> None:
        if not cloud_config.openai_api_key:
            raise ValueError("OpenAI API key is required for EntityExtractor")

        import instructor
        from openai import AsyncOpenAI

        self._config = cloud_config
        self._client = instructor.from_openai(
            AsyncOpenAI(
                api_key=cloud_config.openai_api_key,
                base_url=cloud_config.openai_base_url,
                timeout=cloud_config.timeout,
                max_retries=0,
            )
        )
        self._model = cloud_config.openai_model

    async def extract(
        self,
        content: str,
        schema: InferredSchema,
    ) -> ExtractionResult:
        """Extract structured records from a single content string.

        Args:
            content: Source text to extract from (truncated to 50 000 chars).
            schema: The schema defining which fields to extract.

        Returns:
            ExtractionResult with validated records.

        Raises:
            ValueError: If content is empty or schema has no fields.
            EntityExtractionError: If LLM call fails.
        """
        if not content or not content.strip():
            raise ValueError("content must be non-empty")
        if not schema.fields:
            raise ValueError("schema must have at least one field")

        truncated = _truncate_content(content)
        return await self._call_llm(truncated, schema)

    async def extract_batch(
        self,
        contents: list[str],
        schema: InferredSchema,
    ) -> ExtractionResult:
        """Extract records from multiple content strings and merge results.

        Args:
            contents: List of source texts.
            schema: The schema defining which fields to extract.

        Returns:
            Merged ExtractionResult across all contents.

        Raises:
            ValueError: If contents is empty or schema has no fields.
            EntityExtractionError: If LLM call fails.
        """
        if not contents:
            raise ValueError("contents must be non-empty")
        if not schema.fields:
            raise ValueError("schema must have at least one field")

        all_records: list[StructuredRecord] = []
        for content in contents:
            if not content or not content.strip():
                continue
            truncated = _truncate_content(content)
            result = await self._call_llm(truncated, schema)
            all_records.extend(result.records)

        return _build_extraction_result(all_records)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        content: str,
        schema: InferredSchema,
    ) -> ExtractionResult:
        """Call the LLM with retry and post-process the extraction result."""
        schema_desc = _build_schema_description(schema)
        user_content = (
            f"Extract structured records from the following text "
            f"according to this schema:\n\n"
            f"Schema:\n{schema_desc}\n\n"
            f"Text:\n{content}"
        )

        try:
            response: _LLMExtractionResponse = await retry_with_backoff(
                self._raw_llm_call,
                user_content,
                operation_name="EntityExtractor",
            )
        except Exception as exc:
            logger.error("Entity extraction LLM call failed: %s", exc)
            raise EntityExtractionError(f"LLM call failed: {exc}") from exc

        return self._post_process(response, schema)

    async def _raw_llm_call(
        self,
        user_content: str,
    ) -> _LLMExtractionResponse:
        """Single LLM call without retry (called by retry_with_backoff)."""
        return await self._client.chat.completions.create(
            model=self._model,
            response_model=_LLMExtractionResponse,
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
        )

    @staticmethod
    def _post_process(
        response: _LLMExtractionResponse,
        schema: InferredSchema,
    ) -> ExtractionResult:
        """Validate records against schema and build the result."""
        validated: list[StructuredRecord] = []
        for raw in response.records:
            record = StructuredRecord(
                fields=raw.fields,
                confidence=_clamp_confidence(raw.confidence),
                source_span=raw.source_span,
            )
            record = _validate_record_fields(record, schema)
            if _check_required_fields(record, schema):
                validated.append(record)
            else:
                logger.warning(
                    "Skipping record missing required fields: %s",
                    record.fields.keys(),
                )

        return _build_extraction_result(validated)
