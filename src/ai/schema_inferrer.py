"""
Schema inference using instructor + OpenAI.

Infers structured Schema (field names, types, descriptions) from
unstructured text or tabular data via LLM.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

try:
    from src.ai.llm_schemas import CloudConfig
    from src.ai.retry import retry_with_backoff
    from src.extractors.tabular import TabularData
except ImportError:
    from ai.llm_schemas import CloudConfig
    from ai.retry import retry_with_backoff
    from extractors.tabular import TabularData

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 50_000
MAX_TABULAR_PREVIEW_ROWS = 30


class SchemaInferenceError(Exception):
    """Raised when LLM-based schema inference fails."""


class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    ENTITY = "entity"
    LIST = "list"


class SchemaField(BaseModel):
    """A single field in the inferred schema."""
    name: str = Field(description="Field name (snake_case)")
    field_type: FieldType = Field(description="Data type of the field")
    description: str = Field(description="Brief description of what this field contains")
    required: bool = Field(default=True, description="Whether this field is required")
    entity_type: Optional[str] = Field(
        default=None,
        description="Entity sub-type when field_type is ENTITY, e.g. PERSON, ORG, LOCATION",
    )


class InferredSchema(BaseModel):
    """Schema inferred by the LLM from source data."""
    fields: list[SchemaField] = Field(min_length=1, description="List of inferred fields")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    source_description: str = Field(description="LLM description of the data source")


# ---------------------------------------------------------------------------
# Pure helper functions (no LLM dependency)
# ---------------------------------------------------------------------------

def _clamp_confidence(value: float) -> float:
    """Clamp confidence to [0.0, 1.0]."""
    return max(0.0, min(1.0, value))


def _deduplicate_fields(fields: list[SchemaField]) -> list[SchemaField]:
    """Remove duplicate field names, keeping the first occurrence."""
    seen: set[str] = set()
    unique: list[SchemaField] = []
    for field in fields:
        if field.name not in seen:
            seen.add(field.name)
            unique.append(field)
    return unique


def _truncate_text(text: str) -> str:
    """Truncate text to MAX_TEXT_LENGTH characters."""
    if len(text) > MAX_TEXT_LENGTH:
        return text[:MAX_TEXT_LENGTH]
    return text


def _tabular_to_preview(data: TabularData) -> str:
    """Convert TabularData to a text preview for the LLM prompt."""
    lines: list[str] = []
    lines.append(f"File type: {data.file_type}, Total rows: {data.row_count}")
    if data.sheet_name:
        lines.append(f"Sheet: {data.sheet_name}")
    lines.append(f"Headers: {', '.join(data.headers)}")
    lines.append("")

    preview_rows = data.rows[:MAX_TABULAR_PREVIEW_ROWS]
    for i, row in enumerate(preview_rows):
        row_str = " | ".join(f"{k}: {v}" for k, v in row.items())
        lines.append(f"Row {i + 1}: {row_str}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_TEXT_SYSTEM_PROMPT = (
    "You are a data schema analyst. Analyze the provided text and infer a structured schema. "
    "Identify all meaningful fields, their data types, and whether they are required. "
    "For named entities (people, organizations, locations), use field_type='entity' "
    "and specify the entity_type (PERSON, ORG, LOCATION, etc.). "
    "Return a confidence score reflecting how clearly the text implies a schema."
)

_TABULAR_SYSTEM_PROMPT = (
    "You are a data schema analyst. Analyze the provided tabular data (headers and sample rows) "
    "and infer a structured schema. Determine the best data type for each column based on "
    "the actual values. For named entities, use field_type='entity' with the appropriate "
    "entity_type. Return a confidence score reflecting how clearly the data implies a schema."
)


# ---------------------------------------------------------------------------
# SchemaInferrer
# ---------------------------------------------------------------------------

class SchemaInferrer:
    """Infers data schema from text or tabular data using instructor + OpenAI.

    The ``instructor`` and ``openai`` packages are imported lazily in the
    constructor so that the rest of this module (data-classes, helpers) can
    be used on Python 3.9 even when the installed ``instructor`` version
    requires Python ≥ 3.10 at import time.
    """

    def __init__(self, cloud_config: CloudConfig) -> None:
        if not cloud_config.openai_api_key:
            raise ValueError("OpenAI API key is required for SchemaInferrer")

        # Lazy import — instructor 1.13 uses ``str | Path`` syntax that
        # breaks on Python 3.9 at module-level import time.
        import instructor
        from openai import AsyncOpenAI

        self._config = cloud_config
        self._client = instructor.from_openai(
            AsyncOpenAI(
                api_key=cloud_config.openai_api_key,
                base_url=cloud_config.openai_base_url,
                timeout=cloud_config.timeout,
                max_retries=0,  # retries handled externally
            )
        )
        self._model = cloud_config.openai_model

    async def infer_from_text(
        self,
        text: str,
        hint: Optional[str] = None,
    ) -> InferredSchema:
        """Infer schema from unstructured text.

        Args:
            text: Source text (truncated to 50 000 chars if longer).
            hint: Optional hint describing expected data structure.

        Returns:
            InferredSchema with at least one field.

        Raises:
            ValueError: If text is empty.
            SchemaInferenceError: If LLM call fails.
        """
        if not text or not text.strip():
            raise ValueError("text must be non-empty")

        truncated = _truncate_text(text)
        user_content = f"Analyze the following text and infer a data schema:\n\n{truncated}"
        if hint:
            user_content += f"\n\nHint: {hint}"

        return await self._call_llm(
            system_prompt=_TEXT_SYSTEM_PROMPT,
            user_content=user_content,
        )

    async def infer_from_tabular(self, data: TabularData) -> InferredSchema:
        """Infer schema from tabular data (CSV/Excel).

        Args:
            data: Parsed tabular data with headers and rows.

        Returns:
            InferredSchema with at least one field.

        Raises:
            ValueError: If data has no headers.
            SchemaInferenceError: If LLM call fails.
        """
        if not data.headers:
            raise ValueError("TabularData must have at least one header")

        preview = _tabular_to_preview(data)
        user_content = (
            "Analyze the following tabular data and infer a data schema:\n\n" + preview
        )

        return await self._call_llm(
            system_prompt=_TABULAR_SYSTEM_PROMPT,
            user_content=user_content,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        system_prompt: str,
        user_content: str,
    ) -> InferredSchema:
        """Call the LLM via instructor with retry and post-process the result."""
        try:
            schema: InferredSchema = await retry_with_backoff(
                self._raw_llm_call,
                system_prompt,
                user_content,
                operation_name="SchemaInferrer",
            )
        except Exception as exc:
            logger.error("Schema inference LLM call failed: %s", exc)
            raise SchemaInferenceError(f"LLM call failed: {exc}") from exc

        return self._post_process(schema)

    async def _raw_llm_call(
        self,
        system_prompt: str,
        user_content: str,
    ) -> InferredSchema:
        """Single LLM call without retry (called by retry_with_backoff)."""
        return await self._client.chat.completions.create(
            model=self._model,
            response_model=InferredSchema,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
        )

    @staticmethod
    def _post_process(schema: InferredSchema) -> InferredSchema:
        """Ensure field uniqueness and confidence clamping."""
        unique_fields = _deduplicate_fields(schema.fields)
        if not unique_fields:
            raise SchemaInferenceError("LLM returned no valid fields")

        return InferredSchema(
            fields=unique_fields,
            confidence=_clamp_confidence(schema.confidence),
            source_description=schema.source_description,
        )
