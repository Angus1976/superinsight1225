"""
Property-Based Tests for Trial Result Completeness

Tests Property 16: Trial Result Completeness

**Validates: Requirements 7.6**

For any completed AI trial, the result must contain all required metrics
and data: accuracy, precision, recall, f1_score in [0,1]; predictions
with index/predicted/actual/confidence per data item; non-negative
execution_time; data_quality_score in [0,1]; and completed_at set.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from uuid import uuid4, UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.data_lifecycle import (
    AuditLogModel,
    DataStage,
    TrialStatus,
)
from src.services.ai_trial_service import (
    AITrialService,
    TrialConfig,
)
from tests.property.sqlite_uuid_compat import (
    snapshot_uuid_columns,
    patch_models_to_sqlite_uuid,
    restore_uuid_columns,
)

PATCHED_MODELS = [AuditLogModel]
_UUID_COLUMN_SNAPSHOT = snapshot_uuid_columns(PATCHED_MODELS)


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Create an in-memory SQLite database with UUID patching."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    restore = patch_models_to_sqlite_uuid(PATCHED_MODELS, _UUID_COLUMN_SNAPSHOT)
    try:
        for model in PATCHED_MODELS:
            model.__table__.create(bind=engine, checkfirst=True)

        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()
    finally:
        restore_uuid_columns(restore)


# ============================================================================
# Test Strategies
# ============================================================================

data_item_strategy = st.fixed_dictionaries(
    {},
    optional={
        "text": st.text(min_size=1, max_size=60),
        "label": st.sampled_from(["positive", "negative", "neutral"]),
        "score": st.floats(
            min_value=0.0, max_value=1.0,
            allow_nan=False, allow_infinity=False,
        ),
        "count": st.integers(min_value=0, max_value=1000),
        "category": st.sampled_from(["A", "B", "C", "D"]),
        "tags": st.lists(st.text(min_size=1, max_size=10), min_size=0, max_size=3),
        "metadata": st.dictionaries(
            keys=st.sampled_from(["key1", "key2", "key3"]),
            values=st.text(min_size=1, max_size=20),
            min_size=0,
            max_size=2,
        ),
    },
)

source_data_strategy = st.lists(data_item_strategy, min_size=1, max_size=10)

data_stage_strategy = st.sampled_from(list(DataStage))

model_name_strategy = st.sampled_from([
    "gpt-4", "bert-base", "llama-7b", "t5-small", "roberta-large",
])

REQUIRED_METRICS = {"accuracy", "precision", "recall", "f1_score"}
REQUIRED_PREDICTION_FIELDS = {"index", "predicted", "actual", "confidence"}


# ============================================================================
# Property 16: Trial Result Completeness
# **Validates: Requirements 7.6**
# ============================================================================

@pytest.mark.property
class TestTrialResultCompleteness:
    """
    Property 16: Trial Result Completeness

    For any completed AI trial, the result must include all required
    metrics (accuracy, precision, recall, f1_score), predictions with
    required fields, non-negative execution_time, data_quality_score
    in [0,1], and completed_at set.
    """

    @given(
        source_data=source_data_strategy,
        data_stage=data_stage_strategy,
        model_name=model_name_strategy,
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_result_contains_all_required_metrics(
        self,
        db_session: Session,
        source_data: list,
        data_stage: DataStage,
        model_name: str,
    ):
        """
        All 4 required metrics must be present and in range [0, 1].

        **Validates: Requirements 7.6**
        """
        service = AITrialService(db_session)
        config = TrialConfig(
            name="metrics-completeness",
            data_stage=data_stage,
            model_name=model_name,
        )
        trial = service.create_trial(config, created_by=str(uuid4()))
        result = service.execute_trial(trial.id, source_data)

        missing = REQUIRED_METRICS - set(result.metrics.keys())
        assert not missing, (
            f"Missing required metrics: {missing}. "
            f"Got keys: {set(result.metrics.keys())}"
        )

        for key in REQUIRED_METRICS:
            val = result.metrics[key]
            assert 0.0 <= val <= 1.0, (
                f"Metric '{key}' = {val} is outside [0, 1]"
            )

    @given(
        source_data=source_data_strategy,
        data_stage=data_stage_strategy,
        model_name=model_name_strategy,
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_predictions_match_data_items(
        self,
        db_session: Session,
        source_data: list,
        data_stage: DataStage,
        model_name: str,
    ):
        """
        Predictions list must have one entry per data item, each with
        index, predicted, actual, and confidence fields.

        **Validates: Requirements 7.6**
        """
        service = AITrialService(db_session)
        config = TrialConfig(
            name="predictions-completeness",
            data_stage=data_stage,
            model_name=model_name,
        )
        trial = service.create_trial(config, created_by=str(uuid4()))
        result = service.execute_trial(trial.id, source_data)

        assert len(result.predictions) == len(source_data), (
            f"Expected {len(source_data)} predictions, "
            f"got {len(result.predictions)}"
        )

        for i, pred in enumerate(result.predictions):
            missing_fields = REQUIRED_PREDICTION_FIELDS - set(pred.keys())
            assert not missing_fields, (
                f"Prediction[{i}] missing fields: {missing_fields}"
            )
            assert pred["index"] == i, (
                f"Prediction[{i}] has index={pred['index']}, expected {i}"
            )

    @given(
        source_data=source_data_strategy,
        data_stage=data_stage_strategy,
        model_name=model_name_strategy,
        sample_size=st.integers(min_value=1, max_value=5),
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_predictions_respect_sample_size(
        self,
        db_session: Session,
        source_data: list,
        data_stage: DataStage,
        model_name: str,
        sample_size: int,
    ):
        """
        When sample_size is set, predictions count must equal
        min(sample_size, len(source_data)).

        **Validates: Requirements 7.6**
        """
        service = AITrialService(db_session)
        config = TrialConfig(
            name="sample-size-predictions",
            data_stage=data_stage,
            model_name=model_name,
            sample_size=sample_size,
        )
        trial = service.create_trial(config, created_by=str(uuid4()))
        result = service.execute_trial(trial.id, source_data)

        expected_count = min(sample_size, len(source_data))
        assert len(result.predictions) == expected_count, (
            f"Expected {expected_count} predictions (sample_size={sample_size}, "
            f"data_len={len(source_data)}), got {len(result.predictions)}"
        )

    @given(
        source_data=source_data_strategy,
        data_stage=data_stage_strategy,
        model_name=model_name_strategy,
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_execution_time_and_quality_score(
        self,
        db_session: Session,
        source_data: list,
        data_stage: DataStage,
        model_name: str,
    ):
        """
        execution_time must be non-negative, data_quality_score must be
        in [0, 1], and completed_at must be set.

        **Validates: Requirements 7.6**
        """
        service = AITrialService(db_session)
        config = TrialConfig(
            name="timing-quality-check",
            data_stage=data_stage,
            model_name=model_name,
        )
        trial = service.create_trial(config, created_by=str(uuid4()))
        result = service.execute_trial(trial.id, source_data)

        assert result.execution_time >= 0, (
            f"execution_time={result.execution_time} is negative"
        )
        assert 0.0 <= result.data_quality_score <= 1.0, (
            f"data_quality_score={result.data_quality_score} outside [0, 1]"
        )
        assert result.completed_at is not None, (
            "completed_at must be set on a completed trial result"
        )
