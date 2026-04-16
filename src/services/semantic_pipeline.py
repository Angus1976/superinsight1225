"""
Semantic pipeline — LLM-based entity, relationship, and summary extraction.

Orchestrates the semantic analysis workflow:
extract content → LLM extract entities → LLM extract relationships
→ LLM generate summary → store semantic records.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from src.database.connection import db_manager
from src.models.structuring import (
    JobStatus,
    SemanticRecord,
    StructuringJob,
)
from src.services.structuring_pipeline import get_celery_app

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM prompts
# ---------------------------------------------------------------------------

_ENTITY_SYSTEM_PROMPT = (
    "You are an expert at extracting named entities from text. "
    "Return a JSON array of objects, each with keys: "
    '"name" (string), "type" (string, e.g. person/organization/location/date/concept), '
    '"properties" (object with extra attributes), '
    '"confidence" (float 0-1). '
    "Return ONLY valid JSON, no markdown fences."
)

_RELATIONSHIP_SYSTEM_PROMPT = (
    "You are an expert at extracting relationships between entities in text. "
    "Return a JSON array of objects, each with keys: "
    '"source" (string), "target" (string), "relation" (string describing the relationship), '
    '"confidence" (float 0-1). '
    "Return ONLY valid JSON, no markdown fences."
)

_SUMMARY_SYSTEM_PROMPT = (
    "You are an expert at summarizing documents. "
    "Return a JSON object with keys: "
    '"text" (string, a concise summary of the document), '
    '"confidence" (float 0-1). '
    "Return ONLY valid JSON, no markdown fences."
)


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------


def _call_llm(text: str, system_prompt: str, tenant_id: str | None) -> str:
    """Call LLM with *system_prompt* and return the raw response text.

    Iterates through all configured providers (priority order) and falls
    back to the next one on HTTP / auth errors.
    """
    from src.services.structuring_pipeline import _load_all_cloud_configs
    from src.ai.llm_schemas import openai_compatible_chat_headers

    configs = asyncio.run(
        _load_all_cloud_configs(tenant_id=tenant_id, application_code="semantic_analysis")
    )

    import httpx

    last_error: Exception | None = None
    for cfg in configs:
        base_url = cfg.openai_base_url.rstrip("/")
        try:
            resp = httpx.post(
                f"{base_url}/chat/completions",
                headers=openai_compatible_chat_headers(cfg),
                json={
                    "model": cfg.openai_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.2,
                },
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning(
                "LLM call failed for %s (%s): %s — trying next config",
                cfg.openai_model, base_url, exc,
            )
            last_error = exc

    raise RuntimeError(f"All LLM configs failed. Last error: {last_error}")


def _parse_json(raw: str) -> Any:
    """Best-effort parse of JSON from LLM output.

    Strips optional markdown fences before parsing.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (with optional language tag) and closing fence
        lines = cleaned.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# Extraction steps
# ---------------------------------------------------------------------------


def _extract_entities(text: str, tenant_id: str | None) -> list[dict]:
    """Ask LLM to extract entities from *text*.

    Returns a list of dicts with keys: name, type, properties, confidence.
    """
    raw = _call_llm(text, _ENTITY_SYSTEM_PROMPT, tenant_id)
    entities = _parse_json(raw)
    if not isinstance(entities, list):
        raise ValueError("LLM entity response is not a JSON array")
    return entities


def _extract_relationships(text: str, tenant_id: str | None) -> list[dict]:
    """Ask LLM to extract relationships from *text*.

    Returns a list of dicts with keys: source, target, relation, confidence.
    """
    raw = _call_llm(text, _RELATIONSHIP_SYSTEM_PROMPT, tenant_id)
    relationships = _parse_json(raw)
    if not isinstance(relationships, list):
        raise ValueError("LLM relationship response is not a JSON array")
    return relationships


def _generate_summary(text: str, tenant_id: str | None) -> dict:
    """Ask LLM to generate a summary of *text*.

    Returns a dict with keys: text, confidence.
    """
    raw = _call_llm(text, _SUMMARY_SYSTEM_PROMPT, tenant_id)
    summary = _parse_json(raw)
    if not isinstance(summary, dict):
        raise ValueError("LLM summary response is not a JSON object")
    return summary


# ---------------------------------------------------------------------------
# Store semantic records
# ---------------------------------------------------------------------------


def _store_semantic_records(
    session: Any,
    job: StructuringJob,
    entities: list[dict],
    relationships: list[dict],
    summary: dict,
) -> int:
    """Write SemanticRecord rows for entities, relationships, and summary.

    Returns the total number of records stored.
    """
    count = 0

    for entity in entities:
        record = SemanticRecord(
            job_id=job.id,
            record_type="entity",
            content={
                "name": entity.get("name", ""),
                "type": entity.get("type", ""),
                "properties": entity.get("properties", {}),
            },
            confidence=float(entity.get("confidence", 0.0)),
        )
        session.add(record)
        count += 1

    for rel in relationships:
        record = SemanticRecord(
            job_id=job.id,
            record_type="relationship",
            content={
                "source": rel.get("source", ""),
                "target": rel.get("target", ""),
                "relation": rel.get("relation", ""),
            },
            confidence=float(rel.get("confidence", 0.0)),
        )
        session.add(record)
        count += 1

    summary_record = SemanticRecord(
        job_id=job.id,
        record_type="summary",
        content={"text": summary.get("text", "")},
        confidence=float(summary.get("confidence", 0.0)),
    )
    session.add(summary_record)
    count += 1

    session.flush()
    return count


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

_app = get_celery_app()


@_app.task(
    bind=True,
    name="semantic.run_pipeline",
    max_retries=2,
    soft_time_limit=600,
    time_limit=660,
    acks_late=True,
)
def run_semantic_pipeline(self, job_id: str) -> dict:
    """Execute the semantic analysis pipeline for a given job.

    Steps:
        1. Extract text content from the source file
        2. Call LLM to extract entities
        3. Call LLM to extract relationships
        4. Call LLM to generate summary
        5. Store all results as SemanticRecord entries

    Returns:
        dict with job_id, status, and record_count.
    """
    logger.info("Starting semantic pipeline for job %s", job_id)

    try:
        return _execute_semantic(job_id)
    except Exception as exc:
        logger.exception("Semantic pipeline failed for job %s: %s", job_id, exc)
        _mark_job_failed(job_id, str(exc))
        return {
            "job_id": job_id,
            "status": JobStatus.FAILED.value,
            "error": str(exc),
        }


def _execute_semantic(job_id: str) -> dict:
    """Run all semantic steps inside a single DB session."""
    with db_manager.get_session() as session:
        job = session.query(StructuringJob).filter_by(id=job_id).first()
        if not job:
            raise ValueError(f"StructuringJob not found: {job_id}")
        if job.status != JobStatus.PENDING.value:
            raise ValueError(
                f"Job {job_id} is not pending (current: {job.status})"
            )

        total_steps = 5

        # Step 1 — extract text (reuse vectorization_pipeline helper)
        job.status = JobStatus.EXTRACTING.value
        job.progress_info = {"stage": "extracting", "current": 1, "total": total_steps, "percent": 10}
        session.flush()

        from src.services.vectorization_pipeline import _extract_text

        text = _extract_text(job)
        job.raw_content = text
        session.flush()

        # Step 2 — extract entities
        job.status = "processing"
        job.progress_info = {"stage": "entities", "current": 2, "total": total_steps, "percent": 30}
        session.flush()
        entities = _extract_entities(text, job.tenant_id)

        # Step 3 — extract relationships
        job.progress_info = {"stage": "relationships", "current": 3, "total": total_steps, "percent": 55}
        session.flush()
        relationships = _extract_relationships(text, job.tenant_id)

        # Step 4 — generate summary
        job.progress_info = {"stage": "summary", "current": 4, "total": total_steps, "percent": 75}
        session.flush()
        summary = _generate_summary(text, job.tenant_id)

        # Step 5 — store records
        job.progress_info = {"stage": "storing", "current": 5, "total": total_steps, "percent": 90}
        session.flush()
        count = _store_semantic_records(
            session, job, entities, relationships, summary,
        )

        # Mark completed
        job.status = JobStatus.COMPLETED.value
        job.progress_info = {"stage": "completed", "current": total_steps, "total": total_steps, "percent": 100}
        session.flush()

        logger.info(
            "Semantic pipeline completed for job %s: %d records",
            job_id, count,
        )
        return {
            "job_id": str(job.id),
            "status": JobStatus.COMPLETED.value,
            "record_count": count,
        }


def _mark_job_failed(job_id: str, error: str) -> None:
    """Best-effort: mark the job as failed in a fresh session."""
    try:
        with db_manager.get_session() as session:
            job = session.query(StructuringJob).filter_by(id=job_id).first()
            if job and job.status != JobStatus.FAILED.value:
                job.status = JobStatus.FAILED.value
                job.error_message = error
                session.flush()
    except Exception:
        logger.exception("Could not mark job %s as failed", job_id)
