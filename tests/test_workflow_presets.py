"""
Tests for create_preset_workflows() — system preset workflow creation.

Verifies that the 4 system preset workflows are created correctly,
are idempotent, and have the expected configurations.

# Feature: ai-workflow-engine
"""

import pytest
from unittest.mock import MagicMock, call

from src.ai.workflow_service import WorkflowService
from src.models.ai_workflow import AIWorkflow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PRESET_NAMES = [
    "销售预测分析",
    "数据质量检查",
    "智能标注建议",
    "任务进度追踪",
]


def _make_service() -> WorkflowService:
    """Create a WorkflowService with a mocked DB session."""
    svc = WorkflowService.__new__(WorkflowService)
    svc.db = MagicMock()
    return svc


def _mock_no_existing(mock_db: MagicMock) -> None:
    """Configure mock DB so no preset workflows exist yet."""
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = None
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query


def _mock_all_existing(mock_db: MagicMock) -> None:
    """Configure mock DB so all preset workflows already exist."""
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = MagicMock()  # non-None = exists
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreatePresetWorkflows:
    """Tests for WorkflowService.create_preset_workflows()."""

    def test_creates_four_presets_when_none_exist(self):
        """All 4 preset workflows are created when DB is empty."""
        service = _make_service()
        _mock_no_existing(service.db)

        created = service.create_preset_workflows()

        assert len(created) == 4
        assert service.db.add.call_count == 4
        service.db.commit.assert_called_once()

    def test_all_presets_have_correct_names(self):
        """Created presets match the expected Chinese names."""
        service = _make_service()
        _mock_no_existing(service.db)

        created = service.create_preset_workflows()
        names = [w.name for w in created]

        for expected in PRESET_NAMES:
            assert expected in names

    def test_all_presets_marked_is_preset_true(self):
        """Every created workflow has is_preset=True."""
        service = _make_service()
        _mock_no_existing(service.db)

        created = service.create_preset_workflows()

        for w in created:
            assert w.is_preset is True

    def test_all_presets_have_enabled_status(self):
        """Every created workflow has status='enabled'."""
        service = _make_service()
        _mock_no_existing(service.db)

        created = service.create_preset_workflows()

        for w in created:
            assert w.status == "enabled"

    def test_all_presets_have_system_preset_creator(self):
        """Every created workflow has created_by='system_preset'."""
        service = _make_service()
        _mock_no_existing(service.db)

        created = service.create_preset_workflows()

        for w in created:
            assert w.created_by == "system_preset"

    def test_all_presets_have_english_names(self):
        """Every created workflow has a non-empty name_en."""
        service = _make_service()
        _mock_no_existing(service.db)

        created = service.create_preset_workflows()

        for w in created:
            assert w.name_en is not None
            assert len(w.name_en) > 0

    def test_all_presets_have_merge_output_mode(self):
        """Every created workflow includes 'merge' in output_modes."""
        service = _make_service()
        _mock_no_existing(service.db)

        created = service.create_preset_workflows()

        for w in created:
            assert "merge" in w.output_modes

    def test_all_presets_have_empty_skill_ids(self):
        """Preset workflows start with empty skill_ids."""
        service = _make_service()
        _mock_no_existing(service.db)

        created = service.create_preset_workflows()

        for w in created:
            assert w.skill_ids == []

    def test_all_presets_have_empty_data_source_auth(self):
        """Preset workflows start with empty data_source_auth."""
        service = _make_service()
        _mock_no_existing(service.db)

        created = service.create_preset_workflows()

        for w in created:
            assert w.data_source_auth == []

    def test_all_presets_have_preset_prompt(self):
        """Every preset workflow has a non-empty preset_prompt."""
        service = _make_service()
        _mock_no_existing(service.db)

        created = service.create_preset_workflows()

        for w in created:
            assert w.preset_prompt is not None
            assert len(w.preset_prompt) > 0

    def test_visible_roles_vary_by_preset(self):
        """Different presets have different visible_roles configurations."""
        service = _make_service()
        _mock_no_existing(service.db)

        created = service.create_preset_workflows()
        by_name = {w.name: w for w in created}

        assert set(by_name["销售预测分析"].visible_roles) == {
            "admin", "business_expert",
        }
        assert set(by_name["数据质量检查"].visible_roles) == {
            "admin", "business_expert", "annotator",
        }
        assert set(by_name["智能标注建议"].visible_roles) == {
            "admin", "annotator",
        }
        assert set(by_name["任务进度追踪"].visible_roles) == {
            "admin", "business_expert", "annotator", "viewer",
        }

    def test_idempotent_skips_all_when_existing(self):
        """No workflows created when all 4 already exist."""
        service = _make_service()
        _mock_all_existing(service.db)

        created = service.create_preset_workflows()

        assert len(created) == 0
        service.db.add.assert_not_called()
        service.db.commit.assert_not_called()

    def test_no_commit_when_nothing_created(self):
        """db.commit() is not called when all presets already exist."""
        service = _make_service()
        _mock_all_existing(service.db)

        service.create_preset_workflows()

        service.db.commit.assert_not_called()
