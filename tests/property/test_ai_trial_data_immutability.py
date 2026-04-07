"""
Property-Based Tests for AI Trial Data Immutability

Tests Property 15: AI Trial Data Immutability

**Validates: Requirements 7.1, 7.5**

Trial operations must not modify production data. Source data passed to
execute_trial must remain unchanged, snapshots must be independent from
source, and multiple trials must not interfere with each other.
"""

import copy
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

# Strategy for generating data item dicts with various field types
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

# Strategy for generating lists of data items
source_data_strategy = st.lists(data_item_strategy, min_size=1, max_size=10)

# Strategy for DataStage
data_stage_strategy = st.sampled_from(list(DataStage))

# Strategy for model names
model_name_strategy = st.sampled_from([
    "gpt-4", "bert-base", "llama-7b", "t5-small", "roberta-large",
])


# ============================================================================
# Property 15: AI Trial Data Immutability
# **Validates: Requirements 7.1, 7.5**
# ============================================================================

@pytest.mark.property
class TestAITrialDataImmutability:
    """
    Property 15: AI Trial Data Immutability

    For any AI trial execution, the source data at any lifecycle stage
    must remain unchanged after the trial completes. Trial operations
    must not modify production data.
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
    def test_source_data_unchanged_after_execution(
        self,
        db_session: Session,
        source_data: list,
        data_stage: DataStage,
        model_name: str,
    ):
        """
        Property: Source data passed to execute_trial must remain
        unchanged after execution completes.

        **Validates: Requirements 7.1, 7.5**
        """
        service = AITrialService(db_session)
        # Snapshot before execution
        source_before = copy.deepcopy(source_data)

        config = TrialConfig(
            name="immutability-test",
            data_stage=data_stage,
            model_name=model_name,
        )
        trial = service.create_trial(config, created_by=str(uuid4()))
        service.execute_trial(trial.id, source_data)

        # Source data must be identical to snapshot taken before execution
        assert source_data == source_before, (
            "Source data was modified by execute_trial. "
            f"Expected {source_before}, got {source_data}"
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
    def test_snapshot_independent_from_source(
        self,
        db_session: Session,
        source_data: list,
        data_stage: DataStage,
        model_name: str,
    ):
        """
        Property: The data_snapshot stored in the trial must be
        independent from source data — modifying source after execution
        must not affect the snapshot.

        **Validates: Requirements 7.1, 7.5**
        """
        service = AITrialService(db_session)
        snapshot_before = copy.deepcopy(source_data)

        config = TrialConfig(
            name="snapshot-independence-test",
            data_stage=data_stage,
            model_name=model_name,
        )
        trial = service.create_trial(config, created_by=str(uuid4()))
        service.execute_trial(trial.id, source_data)

        # Mutate source data after execution
        source_data.append({"injected": True})
        for item in source_data:
            item["mutated"] = "yes"

        # Snapshot must still match the original source
        stored_trial = service.get_trial(trial.id)
        assert stored_trial.data_snapshot == snapshot_before, (
            "Trial snapshot was affected by post-execution source mutation. "
            f"Expected {snapshot_before}, got {stored_trial.data_snapshot}"
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
    def test_multiple_trials_no_interference(
        self,
        db_session: Session,
        source_data: list,
        data_stage: DataStage,
        model_name: str,
    ):
        """
        Property: Multiple trials on the same source data must not
        interfere with each other — each trial's snapshot is independent.

        **Validates: Requirements 7.1, 7.5**
        """
        service = AITrialService(db_session)
        source_snapshot = copy.deepcopy(source_data)

        # Execute two trials on the same source data
        config1 = TrialConfig(
            name="trial-1",
            data_stage=data_stage,
            model_name=model_name,
        )
        config2 = TrialConfig(
            name="trial-2",
            data_stage=data_stage,
            model_name=model_name,
            parameters={"temperature": 0.5},
        )

        trial1 = service.create_trial(config1, created_by=str(uuid4()))
        trial2 = service.create_trial(config2, created_by=str(uuid4()))

        service.execute_trial(trial1.id, source_data)
        service.execute_trial(trial2.id, source_data)

        t1 = service.get_trial(trial1.id)
        t2 = service.get_trial(trial2.id)

        # Both snapshots must equal the original source
        assert t1.data_snapshot == source_snapshot, (
            "Trial 1 snapshot differs from original source"
        )
        assert t2.data_snapshot == source_snapshot, (
            "Trial 2 snapshot differs from original source"
        )

        # Snapshots must be independent objects (not same reference)
        if t1.data_snapshot and t2.data_snapshot:
            assert t1.data_snapshot is not t2.data_snapshot, (
                "Trial snapshots share the same object reference"
            )

        # Source data must remain unchanged
        assert source_data == source_snapshot, (
            "Source data was modified after multiple trial executions"
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
    def test_trial_uses_read_operation_type(
        self,
        db_session: Session,
        source_data: list,
        data_stage: DataStage,
        model_name: str,
    ):
        """
        Property: Trial execution must use READ operation type in audit
        logs, not CREATE/UPDATE — confirming no production data mutation.

        **Validates: Requirements 7.5**
        """
        service = AITrialService(db_session)

        config = TrialConfig(
            name="audit-check-test",
            data_stage=data_stage,
            model_name=model_name,
        )
        trial = service.create_trial(config, created_by=str(uuid4()))
        service.execute_trial(trial.id, source_data)

        # Query audit logs for this trial's execution
        from src.models.data_lifecycle import OperationType, OperationResult
        logs = (
            db_session.query(AuditLogModel)
            .filter(
                AuditLogModel.resource_id == trial.id,
                AuditLogModel.result == OperationResult.SUCCESS,
            )
            .all()
        )

        # There should be at least a CREATE (for create_trial) and
        # a READ (for execute_trial)
        execute_logs = [
            log for log in logs
            if log.details.get("action") == "execute_trial"
        ]
        assert len(execute_logs) >= 1, (
            "No audit log found for trial execution"
        )
        for log in execute_logs:
            assert log.operation_type == OperationType.READ, (
                f"Trial execution used {log.operation_type.value} "
                f"instead of READ — indicates production data mutation"
            )
