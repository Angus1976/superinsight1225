"""
Unit tests for annotation module.

Tests cover:
- Annotation creation and validation
- Annotation retrieval and filtering
- Annotation update operations
- Annotation deletion
- Annotation export functionality

Tests target:
- src/models/annotation.py (Annotation domain model)
- src/ai/annotation_history_service.py (versioning & CRUD)
- src/ai/annotation_export_service.py (multi-format export)

Requirements: 1.1
"""

import json
import pytest
import asyncio
from uuid import uuid4, UUID
from datetime import datetime, timedelta

from src.models.annotation import Annotation
from src.ai.annotation_history_service import (
    AnnotationHistoryService,
    AnnotationVersionRecord,
    ChangeType,
    VersionStatus,
    VersionDiff,
    HistoryTimeline,
)
from src.ai.annotation_export_service import (
    AnnotationExportService,
    AnnotationExportRecord,
    ExportFilter,
    ExportFormat,
    ExportStatus,
    ExportJob,
)


# =============================================================================
# Constants
# =============================================================================

TENANT_ID = uuid4()
USER_ID = uuid4()
PROJECT_ID = uuid4()


# =============================================================================
# Helpers
# =============================================================================

def _make_annotation(**overrides) -> Annotation:
    """Create a valid Annotation with sensible defaults."""
    defaults = dict(
        task_id=uuid4(),
        annotator_id="annotator_001",
        annotation_data={"label": "positive", "score": 0.9},
        confidence=0.85,
        time_spent=60,
    )
    defaults.update(overrides)
    return Annotation(**defaults)


def _make_export_record(**overrides) -> AnnotationExportRecord:
    """Create a valid AnnotationExportRecord with sensible defaults."""
    defaults = dict(
        task_id=uuid4(),
        project_id=PROJECT_ID,
        annotation_type="text_classification",
        annotation_data={"label": "positive"},
        created_by=USER_ID,
        ai_generated=False,
    )
    defaults.update(overrides)
    return AnnotationExportRecord(**defaults)


async def _seed_history(
    service: AnnotationHistoryService,
    annotation_id: UUID,
    versions: int = 1,
) -> list[AnnotationVersionRecord]:
    """Create N versions for an annotation, returning all records."""
    records = []
    for i in range(versions):
        rec = await service.create_version(
            annotation_id=annotation_id,
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            annotation_data={"label": f"v{i + 1}", "iteration": i + 1},
            change_type=ChangeType.CREATED if i == 0 else ChangeType.UPDATED,
            change_description=f"Version {i + 1}",
        )
        records.append(rec)
    return records


# =============================================================================
# 1. Annotation Creation and Validation
# =============================================================================

class TestAnnotationCreation:
    """Test annotation creation and validation via the domain model."""

    def test_create_annotation_with_defaults(self):
        ann = _make_annotation()
        assert ann.id is not None
        assert ann.confidence == 0.85
        assert ann.time_spent == 60

    def test_create_annotation_default_confidence(self):
        ann = Annotation(
            task_id=uuid4(),
            annotator_id="user1",
            annotation_data={"label": "ok"},
        )
        assert ann.confidence == 1.0
        assert ann.time_spent == 0

    def test_reject_empty_annotation_data(self):
        with pytest.raises(ValueError, match="annotation_data cannot be empty"):
            _make_annotation(annotation_data={})

    def test_reject_empty_annotator_id(self):
        with pytest.raises(ValueError, match="annotator_id cannot be empty"):
            _make_annotation(annotator_id="")

    def test_reject_confidence_out_of_range(self):
        with pytest.raises(ValueError, match="confidence must be between"):
            _make_annotation(confidence=1.5)
        with pytest.raises(ValueError, match="confidence must be between"):
            _make_annotation(confidence=-0.1)

    def test_reject_negative_time_spent(self):
        with pytest.raises(ValueError, match="time_spent must be non-negative"):
            _make_annotation(time_spent=-1)

    def test_boundary_confidence_values(self):
        ann_zero = _make_annotation(confidence=0.0)
        ann_one = _make_annotation(confidence=1.0)
        assert ann_zero.confidence == 0.0
        assert ann_one.confidence == 1.0


class TestAnnotationVersionCreation:
    """Test annotation version creation via AnnotationHistoryService."""

    @pytest.mark.asyncio
    async def test_create_first_version(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        rec = await service.create_version(
            annotation_id=ann_id,
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            annotation_data={"label": "positive"},
            change_type=ChangeType.CREATED,
        )
        assert rec.version_number == 1
        assert rec.annotation_id == ann_id
        assert rec.status == VersionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_subsequent_version_increments(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        records = await _seed_history(service, ann_id, versions=3)
        assert [r.version_number for r in records] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_parent_version_superseded(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        records = await _seed_history(service, ann_id, versions=2)
        v1 = await service.get_version(ann_id, 1)
        assert v1.status == VersionStatus.SUPERSEDED

    @pytest.mark.asyncio
    async def test_ai_metadata_stored(self):
        service = AnnotationHistoryService()
        rec = await service.create_version(
            annotation_id=uuid4(),
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            annotation_data={"label": "auto"},
            ai_generated=True,
            ai_model="gpt-4",
            ai_confidence=0.92,
        )
        assert rec.ai_generated is True
        assert rec.ai_model == "gpt-4"
        assert rec.ai_confidence == 0.92


# =============================================================================
# 2. Annotation Retrieval and Filtering
# =============================================================================

class TestAnnotationRetrieval:
    """Test annotation retrieval and filtering."""

    @pytest.mark.asyncio
    async def test_get_version_by_number(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=3)

        v2 = await service.get_version(ann_id, 2)
        assert v2 is not None
        assert v2.version_number == 2

    @pytest.mark.asyncio
    async def test_get_nonexistent_version_returns_none(self):
        service = AnnotationHistoryService()
        result = await service.get_version(uuid4(), 99)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_version(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=3)

        current = await service.get_current_version(ann_id)
        assert current.version_number == 3

    @pytest.mark.asyncio
    async def test_get_current_version_unknown_annotation(self):
        service = AnnotationHistoryService()
        assert await service.get_current_version(uuid4()) is None

    @pytest.mark.asyncio
    async def test_get_all_versions_ordered_newest_first(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=4)

        versions = await service.get_all_versions(ann_id)
        nums = [v.version_number for v in versions]
        assert nums == [4, 3, 2, 1]

    @pytest.mark.asyncio
    async def test_get_all_versions_excludes_deleted_by_default(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=3)
        await service.delete_version(ann_id, 1)

        versions = await service.get_all_versions(ann_id, include_deleted=False)
        nums = [v.version_number for v in versions]
        assert 1 not in nums

    @pytest.mark.asyncio
    async def test_get_all_versions_includes_deleted_when_requested(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=3)
        await service.delete_version(ann_id, 1)

        versions = await service.get_all_versions(ann_id, include_deleted=True)
        nums = [v.version_number for v in versions]
        assert 1 in nums

    @pytest.mark.asyncio
    async def test_filter_versions_by_user(self):
        service = AnnotationHistoryService()
        user_a, user_b = uuid4(), uuid4()
        ann_id = uuid4()

        await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=user_a,
            annotation_data={"by": "a"},
        )
        await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=user_b,
            annotation_data={"by": "b"},
        )

        results = await service.get_versions_by_user(user_a)
        assert all(r.created_by == user_a for r in results)

    @pytest.mark.asyncio
    async def test_filter_versions_by_tenant(self):
        service = AnnotationHistoryService()
        tenant_a, tenant_b = uuid4(), uuid4()

        await service.create_version(
            annotation_id=uuid4(), tenant_id=tenant_a, user_id=USER_ID,
            annotation_data={"t": "a"},
        )
        await service.create_version(
            annotation_id=uuid4(), tenant_id=tenant_b, user_id=USER_ID,
            annotation_data={"t": "b"},
        )

        results = await service.get_versions_by_tenant(tenant_a)
        assert len(results) >= 1
        assert all(r.tenant_id == tenant_a for r in results)

    @pytest.mark.asyncio
    async def test_history_timeline(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=3)

        timeline = await service.get_history_timeline(ann_id)
        assert isinstance(timeline, HistoryTimeline)
        assert timeline.total_versions == 3
        assert timeline.current_version == 3
        assert len(timeline.events) == 3


# =============================================================================
# 3. Annotation Update Operations
# =============================================================================

class TestAnnotationUpdate:
    """Test annotation update operations."""

    def test_update_confidence(self):
        ann = _make_annotation(confidence=0.5)
        ann.update_confidence(0.9)
        assert ann.confidence == 0.9

    def test_update_confidence_rejects_invalid(self):
        ann = _make_annotation()
        with pytest.raises(ValueError, match="Confidence must be between"):
            ann.update_confidence(1.5)

    def test_add_time_spent(self):
        ann = _make_annotation(time_spent=60)
        ann.add_time_spent(30)
        assert ann.time_spent == 90

    def test_add_time_spent_rejects_negative(self):
        ann = _make_annotation()
        with pytest.raises(ValueError, match="Additional time must be non-negative"):
            ann.add_time_spent(-10)

    def test_update_annotation_data(self):
        ann = _make_annotation()
        new_data = {"label": "negative", "entities": []}
        ann.update_annotation_data(new_data)
        assert ann.annotation_data == new_data

    def test_update_annotation_data_rejects_empty(self):
        ann = _make_annotation()
        with pytest.raises(ValueError, match="Annotation data cannot be empty"):
            ann.update_annotation_data({})

    @pytest.mark.asyncio
    async def test_version_tracks_changes(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()

        await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=USER_ID,
            annotation_data={"label": "positive", "score": 0.8},
        )
        v2 = await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=USER_ID,
            annotation_data={"label": "negative", "score": 0.8},
            change_type=ChangeType.UPDATED,
        )

        modified = [c for c in v2.changes if c.change_type == "modified"]
        assert len(modified) == 1
        assert modified[0].field_name == "label"
        assert modified[0].old_value == "positive"
        assert modified[0].new_value == "negative"

    @pytest.mark.asyncio
    async def test_version_detects_added_fields(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()

        await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=USER_ID,
            annotation_data={"label": "ok"},
        )
        v2 = await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=USER_ID,
            annotation_data={"label": "ok", "entities": ["A"]},
            change_type=ChangeType.UPDATED,
        )

        added = [c for c in v2.changes if c.change_type == "added"]
        assert len(added) == 1
        assert added[0].field_name == "entities"

    @pytest.mark.asyncio
    async def test_version_detects_deleted_fields(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()

        await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=USER_ID,
            annotation_data={"label": "ok", "extra": True},
        )
        v2 = await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=USER_ID,
            annotation_data={"label": "ok"},
            change_type=ChangeType.UPDATED,
        )

        deleted = [c for c in v2.changes if c.change_type == "deleted"]
        assert len(deleted) == 1
        assert deleted[0].field_name == "extra"

    @pytest.mark.asyncio
    async def test_rollback_restores_data(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()

        await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=USER_ID,
            annotation_data={"label": "v1_data"},
        )
        await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=USER_ID,
            annotation_data={"label": "v2_data"},
            change_type=ChangeType.UPDATED,
        )

        restored = await service.rollback(
            annotation_id=ann_id, tenant_id=TENANT_ID,
            user_id=USER_ID, target_version=1, reason="revert",
        )

        assert restored.annotation_data["label"] == "v1_data"
        assert restored.change_type == ChangeType.RESTORED
        assert restored.version_number == 3

    @pytest.mark.asyncio
    async def test_rollback_invalid_version_raises(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=1)

        with pytest.raises(ValueError, match="not found"):
            await service.rollback(
                annotation_id=ann_id, tenant_id=TENANT_ID,
                user_id=USER_ID, target_version=99,
            )

    @pytest.mark.asyncio
    async def test_compare_versions(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()

        await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=USER_ID,
            annotation_data={"label": "a", "score": 1},
        )
        await service.create_version(
            annotation_id=ann_id, tenant_id=TENANT_ID, user_id=USER_ID,
            annotation_data={"label": "b", "score": 1},
            change_type=ChangeType.UPDATED,
        )

        diff = await service.compare_versions(ann_id, 1, 2)
        assert isinstance(diff, VersionDiff)
        assert "1 modified" in diff.summary


# =============================================================================
# 4. Annotation Deletion
# =============================================================================

class TestAnnotationDeletion:
    """Test annotation deletion."""

    @pytest.mark.asyncio
    async def test_soft_delete_version(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=3)

        result = await service.delete_version(ann_id, 1)
        assert result is True

        v1 = await service.get_version(ann_id, 1)
        assert v1.status == VersionStatus.DELETED

    @pytest.mark.asyncio
    async def test_delete_nonexistent_version_returns_false(self):
        service = AnnotationHistoryService()
        result = await service.delete_version(uuid4(), 1)
        assert result is False

    @pytest.mark.asyncio
    async def test_cannot_delete_current_version(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=2)

        with pytest.raises(ValueError, match="Cannot delete current version"):
            await service.delete_version(ann_id, 2)

    @pytest.mark.asyncio
    async def test_deleted_version_excluded_from_default_listing(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=3)
        await service.delete_version(ann_id, 1)

        versions = await service.get_all_versions(ann_id)
        assert all(v.status != VersionStatus.DELETED for v in versions)

    @pytest.mark.asyncio
    async def test_delete_does_not_affect_other_versions(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=3)
        await service.delete_version(ann_id, 1)

        v2 = await service.get_version(ann_id, 2)
        assert v2.status != VersionStatus.DELETED


# =============================================================================
# 5. Annotation Export Functionality
# =============================================================================

class TestAnnotationExport:
    """Test annotation export functionality."""

    @pytest.mark.asyncio
    async def test_export_json_format(self):
        service = AnnotationExportService()
        rec = _make_export_record()
        await service.add_annotation(rec)

        filt = ExportFilter(tenant_id=TENANT_ID, project_id=PROJECT_ID)
        data, meta = await service.export_annotations(
            TENANT_ID, USER_ID, filt, ExportFormat.JSON,
        )

        parsed = json.loads(data)
        assert "annotations" in parsed
        assert "metadata" in parsed
        assert len(parsed["annotations"]) == 1
        assert meta.total_annotations == 1

    @pytest.mark.asyncio
    async def test_export_csv_format(self):
        service = AnnotationExportService()
        await service.add_annotation(_make_export_record())

        filt = ExportFilter(tenant_id=TENANT_ID, project_id=PROJECT_ID)
        data, _ = await service.export_annotations(
            TENANT_ID, USER_ID, filt, ExportFormat.CSV,
        )

        lines = data.strip().split("\n")
        assert len(lines) == 2  # header + 1 row
        assert "annotation_id" in lines[0]

    @pytest.mark.asyncio
    async def test_export_jsonl_format(self):
        service = AnnotationExportService()
        await service.add_annotation(_make_export_record())

        filt = ExportFilter(tenant_id=TENANT_ID, project_id=PROJECT_ID)
        data, _ = await service.export_annotations(
            TENANT_ID, USER_ID, filt, ExportFormat.JSONL,
        )

        lines = data.strip().split("\n")
        # metadata line + annotation line
        assert len(lines) == 2
        meta_line = json.loads(lines[0])
        assert meta_line["_type"] == "metadata"

    @pytest.mark.asyncio
    async def test_export_xml_format(self):
        service = AnnotationExportService()
        await service.add_annotation(_make_export_record())

        filt = ExportFilter(tenant_id=TENANT_ID, project_id=PROJECT_ID)
        data, _ = await service.export_annotations(
            TENANT_ID, USER_ID, filt, ExportFormat.XML,
        )

        assert data.startswith('<?xml version="1.0"')
        assert "<annotations>" in data
        assert "<annotation>" in data

    @pytest.mark.asyncio
    async def test_export_filter_by_project(self):
        service = AnnotationExportService()
        proj_a, proj_b = uuid4(), uuid4()
        await service.add_annotation(_make_export_record(project_id=proj_a))
        await service.add_annotation(_make_export_record(project_id=proj_b))

        filt = ExportFilter(tenant_id=TENANT_ID, project_id=proj_a)
        data, meta = await service.export_annotations(
            TENANT_ID, USER_ID, filt, ExportFormat.JSON,
        )
        parsed = json.loads(data)
        assert meta.total_annotations == 1
        assert parsed["annotations"][0]["project_id"] == str(proj_a)

    @pytest.mark.asyncio
    async def test_export_filter_excludes_ai_annotations(self):
        service = AnnotationExportService()
        await service.add_annotation(
            _make_export_record(ai_generated=True)
        )
        await service.add_annotation(
            _make_export_record(ai_generated=False)
        )

        filt = ExportFilter(
            tenant_id=TENANT_ID,
            project_id=PROJECT_ID,
            include_ai_annotations=False,
        )
        _, meta = await service.export_annotations(
            TENANT_ID, USER_ID, filt, ExportFormat.JSON,
        )
        assert meta.total_annotations == 1

    @pytest.mark.asyncio
    async def test_export_without_metadata(self):
        service = AnnotationExportService()
        await service.add_annotation(_make_export_record())

        filt = ExportFilter(tenant_id=TENANT_ID, project_id=PROJECT_ID)
        data, _ = await service.export_annotations(
            TENANT_ID, USER_ID, filt, ExportFormat.JSON,
            include_metadata=False,
        )
        parsed = json.loads(data)
        assert "metadata" not in parsed
        assert "annotations" in parsed

    @pytest.mark.asyncio
    async def test_export_job_lifecycle(self):
        service = AnnotationExportService()
        filt = ExportFilter(tenant_id=TENANT_ID)

        job = await service.create_export_job(
            TENANT_ID, USER_ID, filt, ExportFormat.JSON,
        )
        assert job.status == ExportStatus.PENDING

        updated = await service.update_export_job(
            job.job_id,
            status=ExportStatus.COMPLETED,
            total_records=10,
            file_size=2048,
            download_url="https://example.com/export.json",
        )
        assert updated.status == ExportStatus.COMPLETED
        assert updated.total_records == 10
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_list_export_jobs_by_tenant(self):
        service = AnnotationExportService()
        filt = ExportFilter(tenant_id=TENANT_ID)

        await service.create_export_job(TENANT_ID, USER_ID, filt)
        await service.create_export_job(TENANT_ID, USER_ID, filt)
        other_tenant = uuid4()
        await service.create_export_job(other_tenant, USER_ID, filt)

        jobs = await service.list_export_jobs(TENANT_ID)
        assert len(jobs) == 2
        assert all(j.tenant_id == TENANT_ID for j in jobs)


class TestAnnotationHistoryExport:
    """Test version history export via AnnotationHistoryService."""

    @pytest.mark.asyncio
    async def test_export_json(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=2)

        exported = await service.export_version_history(ann_id, format="json")
        data = json.loads(exported)
        assert len(data) == 2
        assert data[0]["version_number"] == 2  # newest first

    @pytest.mark.asyncio
    async def test_export_unsupported_format_raises(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=1)

        with pytest.raises(ValueError, match="Unsupported format"):
            await service.export_version_history(ann_id, format="yaml")

    @pytest.mark.asyncio
    async def test_export_includes_deleted_versions(self):
        service = AnnotationHistoryService()
        ann_id = uuid4()
        await _seed_history(service, ann_id, versions=3)
        await service.delete_version(ann_id, 1)

        exported = await service.export_version_history(ann_id, format="json")
        data = json.loads(exported)
        statuses = {d["status"] for d in data}
        assert "deleted" in statuses
