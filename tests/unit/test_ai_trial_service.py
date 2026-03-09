"""
Unit tests for AI Trial Service

Tests trial creation, execution, result retrieval, comparison,
cancellation, data immutability, and metric calculation.
"""

import copy
import pytest
from datetime import datetime
from uuid import uuid4, UUID
from sqlalchemy import create_engine, String, TypeDecorator
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.data_lifecycle import (
    AuditLogModel,
    TrialStatus,
    DataStage,
    ResourceType,
    OperationType,
    OperationResult,
    Action,
)
from src.services.ai_trial_service import (
    AITrialService,
    TrialConfig,
    TrialResult,
    Trial,
)


# ============================================================================
# SQLite UUID Compatibility
# ============================================================================

class SQLiteUUID(TypeDecorator):
    """UUID type that works with SQLite by storing as string."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value) if isinstance(value, UUID) else str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return UUID(value) if not isinstance(value, UUID) else value
        return value


PATCHED_MODELS = [AuditLogModel]


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite database with UUID patching."""
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    for model in PATCHED_MODELS:
        for col in model.__table__.columns:
            if isinstance(col.type, PGUUID):
                col.type = SQLiteUUID()

    for model in PATCHED_MODELS:
        model.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()

    from sqlalchemy.dialects.postgresql import UUID as PGUUID_Restore
    for model in PATCHED_MODELS:
        for col in model.__table__.columns:
            if isinstance(col.type, SQLiteUUID):
                col.type = PGUUID_Restore(as_uuid=True)


@pytest.fixture
def service(db_session):
    """Create an AITrialService instance."""
    return AITrialService(db_session)


@pytest.fixture
def sample_data():
    """Sample data items for trial execution."""
    return [
        {"id": "1", "text": "Sample text one", "label": "positive", "score": 0.8},
        {"id": "2", "text": "Sample text two", "label": "negative", "score": 0.3},
        {"id": "3", "text": "Sample text three", "label": "positive", "score": 0.9},
        {"id": "4", "text": "", "label": "negative", "score": 0.1},
        {"id": "5", "text": "Sample five", "label": "positive", "score": 0.7},
    ]


@pytest.fixture
def default_config():
    """Default trial configuration."""
    return TrialConfig(
        name="Test Trial",
        data_stage=DataStage.SAMPLE_LIBRARY,
        model_name="test-model-v1",
        parameters={"threshold": 0.5},
    )


# ============================================================================
# Test: Create Trial
# ============================================================================

def test_create_trial_success(service, default_config):
    trial = service.create_trial(default_config, created_by="user-1")

    assert trial.id is not None
    assert trial.config.name == "Test Trial"
    assert trial.config.data_stage == DataStage.SAMPLE_LIBRARY
    assert trial.config.model_name == "test-model-v1"
    assert trial.status == TrialStatus.CREATED
    assert trial.created_by == "user-1"
    assert trial.created_at is not None


def test_create_trial_all_data_stages(service):
    for stage in DataStage:
        config = TrialConfig(
            name=f"Trial {stage.value}",
            data_stage=stage,
            model_name="model-1",
        )
        trial = service.create_trial(config, created_by="user-1")
        assert trial.config.data_stage == stage


def test_create_trial_with_sample_size(service):
    config = TrialConfig(
        name="Sized Trial",
        data_stage=DataStage.ANNOTATED,
        model_name="model-1",
        sample_size=10,
    )
    trial = service.create_trial(config, created_by="user-1")
    assert trial.config.sample_size == 10


def test_create_trial_empty_name(service):
    config = TrialConfig(
        name="", data_stage=DataStage.ENHANCED, model_name="model-1"
    )
    with pytest.raises(ValueError, match="Trial name is required"):
        service.create_trial(config, created_by="user-1")


def test_create_trial_empty_model_name(service):
    config = TrialConfig(
        name="Trial", data_stage=DataStage.ENHANCED, model_name=""
    )
    with pytest.raises(ValueError, match="Model name is required"):
        service.create_trial(config, created_by="user-1")


def test_create_trial_empty_created_by(service, default_config):
    with pytest.raises(ValueError, match="created_by is required"):
        service.create_trial(default_config, created_by="")


def test_create_trial_invalid_sample_size(service):
    config = TrialConfig(
        name="Trial",
        data_stage=DataStage.ENHANCED,
        model_name="model-1",
        sample_size=0,
    )
    with pytest.raises(ValueError, match="sample_size must be at least 1"):
        service.create_trial(config, created_by="user-1")


# ============================================================================
# Test: Execute Trial
# ============================================================================

def test_execute_trial_success(service, default_config, sample_data):
    trial = service.create_trial(default_config, created_by="user-1")
    result = service.execute_trial(trial.id, sample_data)

    assert result.trial_id == trial.id
    assert "accuracy" in result.metrics
    assert "precision" in result.metrics
    assert "recall" in result.metrics
    assert "f1_score" in result.metrics
    assert result.execution_time >= 0
    assert 0 <= result.data_quality_score <= 1
    assert len(result.predictions) == len(sample_data)
    assert result.completed_at is not None


def test_execute_trial_with_sample_size(service, sample_data):
    config = TrialConfig(
        name="Sized",
        data_stage=DataStage.SAMPLE_LIBRARY,
        model_name="model-1",
        sample_size=2,
    )
    trial = service.create_trial(config, created_by="user-1")
    result = service.execute_trial(trial.id, sample_data)

    assert len(result.predictions) == 2


def test_execute_trial_empty_data(service, default_config):
    trial = service.create_trial(default_config, created_by="user-1")
    result = service.execute_trial(trial.id, [])

    assert result.metrics["accuracy"] == 0.0
    assert result.data_quality_score == 0.0
    assert len(result.predictions) == 0


def test_execute_trial_not_found(service):
    with pytest.raises(ValueError, match="not found"):
        service.execute_trial("nonexistent-id", [])


def test_execute_trial_already_completed(service, default_config, sample_data):
    trial = service.create_trial(default_config, created_by="user-1")
    service.execute_trial(trial.id, sample_data)

    with pytest.raises(ValueError, match="Cannot execute trial"):
        service.execute_trial(trial.id, sample_data)


def test_execute_trial_data_immutability(service, default_config, sample_data):
    """Source data must remain unchanged after trial execution (Req 7.1, 7.5)."""
    original_data = copy.deepcopy(sample_data)
    trial = service.create_trial(default_config, created_by="user-1")
    service.execute_trial(trial.id, sample_data)

    assert sample_data == original_data


def test_execute_trial_snapshot_independence(service, default_config, sample_data):
    """Modifying source data after execution must not affect the snapshot."""
    trial = service.create_trial(default_config, created_by="user-1")
    service.execute_trial(trial.id, sample_data)

    snapshot_before = copy.deepcopy(service.get_trial(trial.id).data_snapshot)
    sample_data[0]["text"] = "MUTATED"

    assert service.get_trial(trial.id).data_snapshot == snapshot_before


# ============================================================================
# Test: Get Trial Result
# ============================================================================

def test_get_trial_result_success(service, default_config, sample_data):
    trial = service.create_trial(default_config, created_by="user-1")
    service.execute_trial(trial.id, sample_data)

    result = service.get_trial_result(trial.id)
    assert result.trial_id == trial.id
    assert "accuracy" in result.metrics


def test_get_trial_result_not_completed(service, default_config):
    trial = service.create_trial(default_config, created_by="user-1")

    with pytest.raises(ValueError, match="not completed"):
        service.get_trial_result(trial.id)


def test_get_trial_result_not_found(service):
    with pytest.raises(ValueError, match="not found"):
        service.get_trial_result("nonexistent-id")


# ============================================================================
# Test: Compare Trials
# ============================================================================

def test_compare_trials_success(service, sample_data):
    config_a = TrialConfig(
        name="Trial A",
        data_stage=DataStage.SAMPLE_LIBRARY,
        model_name="model-a",
    )
    config_b = TrialConfig(
        name="Trial B",
        data_stage=DataStage.ENHANCED,
        model_name="model-b",
    )

    trial_a = service.create_trial(config_a, created_by="user-1")
    trial_b = service.create_trial(config_b, created_by="user-1")
    service.execute_trial(trial_a.id, sample_data)
    service.execute_trial(trial_b.id, sample_data)

    comparison = service.compare_trials([trial_a.id, trial_b.id])

    assert len(comparison.trial_ids) == 2
    assert len(comparison.metrics_comparison) == 2
    assert comparison.best_trial_id is not None
    assert "accuracy" in comparison.summary
    assert "precision" in comparison.summary
    assert "recall" in comparison.summary
    assert "f1_score" in comparison.summary


def test_compare_trials_too_few(service):
    with pytest.raises(ValueError, match="At least 2"):
        service.compare_trials(["single-id"])


def test_compare_trials_not_completed(service, default_config):
    trial = service.create_trial(default_config, created_by="user-1")

    with pytest.raises(ValueError, match="not completed"):
        service.compare_trials([trial.id, trial.id])


# ============================================================================
# Test: Cancel Trial
# ============================================================================

def test_cancel_created_trial(service, default_config):
    trial = service.create_trial(default_config, created_by="user-1")
    service.cancel_trial(trial.id)

    assert service.get_trial(trial.id).status == TrialStatus.FAILED
    assert service.get_trial(trial.id).error == "Cancelled by user"


def test_cancel_completed_trial(service, default_config, sample_data):
    trial = service.create_trial(default_config, created_by="user-1")
    service.execute_trial(trial.id, sample_data)

    with pytest.raises(ValueError, match="Cannot cancel trial"):
        service.cancel_trial(trial.id)


def test_cancel_not_found(service):
    with pytest.raises(ValueError, match="not found"):
        service.cancel_trial("nonexistent-id")


# ============================================================================
# Test: List Trials
# ============================================================================

def test_list_trials_empty(service):
    assert service.list_trials() == []


def test_list_trials_multiple(service):
    for i in range(3):
        config = TrialConfig(
            name=f"Trial {i}",
            data_stage=DataStage.SAMPLE_LIBRARY,
            model_name="model-1",
        )
        service.create_trial(config, created_by="user-1")

    assert len(service.list_trials()) == 3


# ============================================================================
# Test: Metrics Calculation
# ============================================================================

def test_metrics_all_positive(service):
    """All items labeled positive with high quality → high accuracy."""
    data = [
        {"id": str(i), "text": "good text", "label": "positive", "score": 0.9}
        for i in range(5)
    ]
    config = TrialConfig(
        name="All Positive",
        data_stage=DataStage.ANNOTATED,
        model_name="model-1",
    )
    trial = service.create_trial(config, created_by="user-1")
    result = service.execute_trial(trial.id, data)

    assert result.metrics["accuracy"] > 0
    assert result.metrics["precision"] >= 0
    assert result.metrics["recall"] >= 0
    assert result.metrics["f1_score"] >= 0


def test_metrics_values_bounded(service, default_config, sample_data):
    trial = service.create_trial(default_config, created_by="user-1")
    result = service.execute_trial(trial.id, sample_data)

    for key in ("accuracy", "precision", "recall", "f1_score"):
        assert 0 <= result.metrics[key] <= 1


# ============================================================================
# Test: Audit Logging
# ============================================================================

def test_audit_log_on_create(service, default_config, db_session):
    service.create_trial(default_config, created_by="user-1")

    logs = db_session.query(AuditLogModel).all()
    assert len(logs) >= 1
    log = logs[0]
    assert log.resource_type == ResourceType.TRIAL
    assert log.action == Action.TRIAL
    assert log.result == OperationResult.SUCCESS


def test_audit_log_on_execute(service, default_config, sample_data, db_session):
    trial = service.create_trial(default_config, created_by="user-1")
    service.execute_trial(trial.id, sample_data)

    logs = db_session.query(AuditLogModel).all()
    # At least create + execute
    assert len(logs) >= 2
    execute_log = logs[-1]
    assert execute_log.details.get("action") == "execute_trial"


def test_audit_log_on_cancel(service, default_config, db_session):
    trial = service.create_trial(default_config, created_by="user-1")
    service.cancel_trial(trial.id)

    logs = db_session.query(AuditLogModel).all()
    assert len(logs) >= 2
    cancel_log = logs[-1]
    assert cancel_log.details.get("action") == "cancel_trial"
