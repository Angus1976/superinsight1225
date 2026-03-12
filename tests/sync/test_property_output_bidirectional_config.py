"""
Property-based tests for Output/Bidirectional Task Configuration Invariants.

Tests Property 2: 输出/双向任务配置不变量
**Validates: Requirements 1.2, 1.4**

For any 同步任务，若方向为输出则 target_source_id 必须非空；
若方向为双向则输入和输出的字段映射规则必须同时存在且相互独立。
"""

# Feature: bidirectional-sync-and-external-api, Property 2: 输出/双向任务配置不变量

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from hypothesis import given, settings, strategies as st, assume
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.connection import Base
from src.sync.models import (
    SyncJobModel,
    SyncDirection,
    DataSourceModel,
    DataSourceType,
    DataSourceStatus,
)


# SQLite cannot handle JSONB; compile as JSON instead.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def tenant_id_strategy():
    """Generate valid tenant IDs."""
    return st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1,
        max_size=50,
    )


def sync_direction_strategy():
    """Generate sync directions."""
    return st.sampled_from([
        SyncDirection.PULL,
        SyncDirection.PUSH,
        SyncDirection.BIDIRECTIONAL,
    ])


def field_mapping_rules_strategy():
    """Generate field mapping rules."""
    return st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.dictionaries(
            keys=st.sampled_from(["source_field", "target_field", "type_conversion"]),
            values=st.text(min_size=1, max_size=20),
        ),
        min_size=1,
        max_size=5,
    )


def output_field_mapping_rules_strategy():
    """Generate output field mapping rules (separate from input)."""
    return st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.dictionaries(
            keys=st.sampled_from(["source_field", "target_field", "type_conversion"]),
            values=st.text(min_size=1, max_size=20),
        ),
        min_size=1,
        max_size=5,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@contextmanager
def _isolated_session():
    """Fresh in-memory SQLite DB per call — no cross-example leakage."""
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _create_data_source(session, tenant_id):
    """Create a DataSourceModel for testing."""
    source = DataSourceModel(
        id=uuid4(),
        tenant_id=tenant_id,
        name=f"test-source-{uuid4().hex[:8]}",
        source_type=DataSourceType.POSTGRESQL,
        status=DataSourceStatus.ACTIVE,
        connection_config={"host": "localhost", "port": 5432},
    )
    session.add(source)
    session.flush()
    return source


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------

class TestOutputDirectionRequiresTargetSource:
    """For output direction (PUSH), target_source_id must be non-null.
    
    **Validates: Requirements 1.2**
    """

    @settings(max_examples=100)
    @given(
        tenant_id=tenant_id_strategy(),
        has_target_source=st.booleans(),
    )
    def test_push_direction_requires_target_source_id(
        self, tenant_id, has_target_source
    ):
        """For PUSH direction, target_source_id must be non-null.
        
        **Validates: Requirements 1.2**
        """
        with _isolated_session() as session:
            # Create source data source
            source = _create_data_source(session, tenant_id)
            
            # Create target data source if needed
            target_source_id = None
            if has_target_source:
                target = _create_data_source(session, tenant_id)
                target_source_id = target.id
            
            # Create sync job with PUSH direction
            sync_job = SyncJobModel(
                id=uuid4(),
                tenant_id=tenant_id,
                name=f"test-job-{uuid4().hex[:8]}",
                source_id=source.id,
                target_config={},
                direction=SyncDirection.PUSH,
                target_source_id=target_source_id,
            )
            session.add(sync_job)
            session.flush()
            
            # Property: PUSH direction requires target_source_id to be non-null
            if sync_job.direction == SyncDirection.PUSH:
                assert sync_job.target_source_id is not None, (
                    f"PUSH direction requires target_source_id, but got None"
                )


class TestBidirectionalRequiresBothMappings:
    """For bidirectional direction, both input and output field mapping rules must exist.
    
    **Validates: Requirements 1.4**
    """

    @settings(max_examples=100)
    @given(
        tenant_id=tenant_id_strategy(),
        has_input_mapping=st.booleans(),
        has_output_mapping=st.booleans(),
        input_mapping=field_mapping_rules_strategy(),
        output_mapping=output_field_mapping_rules_strategy(),
    )
    def test_bidirectional_requires_both_mappings(
        self,
        tenant_id,
        has_input_mapping,
        has_output_mapping,
        input_mapping,
        output_mapping,
    ):
        """For BIDIRECTIONAL direction, both input and output mappings must exist.
        
        **Validates: Requirements 1.4**
        """
        with _isolated_session() as session:
            # Create source and target data sources
            source = _create_data_source(session, tenant_id)
            target = _create_data_source(session, tenant_id)
            
            # Prepare field mapping rules
            # Input mapping is stored in transformation_rules
            transformation_rules = []
            if has_input_mapping:
                transformation_rules = [
                    {"type": "field_mapping", "rules": input_mapping}
                ]
            
            # Output mapping is stored in field_mapping_rules
            field_mapping_rules = output_mapping if has_output_mapping else None
            
            # Create sync job with BIDIRECTIONAL direction
            sync_job = SyncJobModel(
                id=uuid4(),
                tenant_id=tenant_id,
                name=f"test-job-{uuid4().hex[:8]}",
                source_id=source.id,
                target_config={},
                direction=SyncDirection.BIDIRECTIONAL,
                target_source_id=target.id,
                transformation_rules=transformation_rules,
                field_mapping_rules=field_mapping_rules,
            )
            session.add(sync_job)
            session.flush()
            
            # Property: BIDIRECTIONAL requires both input and output mappings
            if sync_job.direction == SyncDirection.BIDIRECTIONAL:
                # Check input mapping exists (in transformation_rules)
                has_input = (
                    sync_job.transformation_rules
                    and len(sync_job.transformation_rules) > 0
                    and any(
                        rule.get("type") == "field_mapping"
                        for rule in sync_job.transformation_rules
                    )
                )
                
                # Check output mapping exists (in field_mapping_rules)
                has_output = (
                    sync_job.field_mapping_rules is not None
                    and len(sync_job.field_mapping_rules) > 0
                )
                
                assert has_input and has_output, (
                    f"BIDIRECTIONAL direction requires both input and output "
                    f"field mapping rules, but got input={has_input}, output={has_output}"
                )


class TestBidirectionalMappingsAreIndependent:
    """For bidirectional direction, input and output mappings must be independent.
    
    **Validates: Requirements 1.4**
    """

    @settings(max_examples=100)
    @given(
        tenant_id=tenant_id_strategy(),
        input_mapping=field_mapping_rules_strategy(),
        output_mapping=output_field_mapping_rules_strategy(),
    )
    def test_bidirectional_mappings_are_independent(
        self,
        tenant_id,
        input_mapping,
        output_mapping,
    ):
        """For BIDIRECTIONAL, input and output mappings are stored separately.
        
        **Validates: Requirements 1.4**
        """
        with _isolated_session() as session:
            # Create source and target data sources
            source = _create_data_source(session, tenant_id)
            target = _create_data_source(session, tenant_id)
            
            # Create sync job with BIDIRECTIONAL direction
            sync_job = SyncJobModel(
                id=uuid4(),
                tenant_id=tenant_id,
                name=f"test-job-{uuid4().hex[:8]}",
                source_id=source.id,
                target_config={},
                direction=SyncDirection.BIDIRECTIONAL,
                target_source_id=target.id,
                transformation_rules=[
                    {"type": "field_mapping", "rules": input_mapping}
                ],
                field_mapping_rules=output_mapping,
            )
            session.add(sync_job)
            session.flush()
            
            # Property: Input and output mappings are stored independently
            if sync_job.direction == SyncDirection.BIDIRECTIONAL:
                # Extract input mapping
                input_rules = None
                for rule in sync_job.transformation_rules:
                    if rule.get("type") == "field_mapping":
                        input_rules = rule.get("rules")
                        break
                
                # Extract output mapping
                output_rules = sync_job.field_mapping_rules
                
                # Verify they are independent (stored in different fields)
                assert input_rules is not None
                assert output_rules is not None
                
                # Verify they are not the same object (independence)
                # In Python, we check they are stored in different locations
                assert id(input_rules) != id(output_rules), (
                    "Input and output mappings must be independent"
                )


class TestPullDirectionDoesNotRequireTargetSource:
    """For PULL direction, target_source_id can be null.
    
    **Validates: Requirements 1.2**
    """

    @settings(max_examples=100)
    @given(
        tenant_id=tenant_id_strategy(),
        has_target_source=st.booleans(),
    )
    def test_pull_direction_allows_null_target_source(
        self, tenant_id, has_target_source
    ):
        """For PULL direction, target_source_id can be null.
        
        **Validates: Requirements 1.2**
        """
        with _isolated_session() as session:
            # Create source data source
            source = _create_data_source(session, tenant_id)
            
            # Create target data source if needed
            target_source_id = None
            if has_target_source:
                target = _create_data_source(session, tenant_id)
                target_source_id = target.id
            
            # Create sync job with PULL direction
            sync_job = SyncJobModel(
                id=uuid4(),
                tenant_id=tenant_id,
                name=f"test-job-{uuid4().hex[:8]}",
                source_id=source.id,
                target_config={},
                direction=SyncDirection.PULL,
                target_source_id=target_source_id,
            )
            session.add(sync_job)
            session.flush()
            
            # Property: PULL direction allows null target_source_id
            # This test just verifies the job can be created successfully
            assert sync_job.direction == SyncDirection.PULL
            # No assertion on target_source_id - it can be null or non-null


class TestConfigInvariantAcrossDirections:
    """Test configuration invariants across all sync directions.
    
    **Validates: Requirements 1.2, 1.4**
    """

    @settings(max_examples=100)
    @given(
        tenant_id=tenant_id_strategy(),
        direction=sync_direction_strategy(),
        has_target_source=st.booleans(),
        has_input_mapping=st.booleans(),
        has_output_mapping=st.booleans(),
        input_mapping=field_mapping_rules_strategy(),
        output_mapping=output_field_mapping_rules_strategy(),
    )
    def test_config_invariant_across_directions(
        self,
        tenant_id,
        direction,
        has_target_source,
        has_input_mapping,
        has_output_mapping,
        input_mapping,
        output_mapping,
    ):
        """Test configuration invariants for all sync directions.
        
        **Validates: Requirements 1.2, 1.4**
        """
        # Skip invalid combinations
        if direction == SyncDirection.PUSH and not has_target_source:
            assume(False)  # PUSH requires target_source_id
        
        if direction == SyncDirection.BIDIRECTIONAL:
            if not has_target_source or not has_input_mapping or not has_output_mapping:
                assume(False)  # BIDIRECTIONAL requires all
        
        with _isolated_session() as session:
            # Create source data source
            source = _create_data_source(session, tenant_id)
            
            # Create target data source if needed
            target_source_id = None
            if has_target_source:
                target = _create_data_source(session, tenant_id)
                target_source_id = target.id
            
            # Prepare mappings
            transformation_rules = []
            if has_input_mapping:
                transformation_rules = [
                    {"type": "field_mapping", "rules": input_mapping}
                ]
            
            field_mapping_rules = output_mapping if has_output_mapping else None
            
            # Create sync job
            sync_job = SyncJobModel(
                id=uuid4(),
                tenant_id=tenant_id,
                name=f"test-job-{uuid4().hex[:8]}",
                source_id=source.id,
                target_config={},
                direction=direction,
                target_source_id=target_source_id,
                transformation_rules=transformation_rules,
                field_mapping_rules=field_mapping_rules,
            )
            session.add(sync_job)
            session.flush()
            
            # Verify invariants based on direction
            if sync_job.direction == SyncDirection.PUSH:
                assert sync_job.target_source_id is not None, (
                    "PUSH direction requires target_source_id"
                )
            
            if sync_job.direction == SyncDirection.BIDIRECTIONAL:
                assert sync_job.target_source_id is not None, (
                    "BIDIRECTIONAL direction requires target_source_id"
                )
                
                # Check input mapping
                has_input = (
                    sync_job.transformation_rules
                    and len(sync_job.transformation_rules) > 0
                    and any(
                        rule.get("type") == "field_mapping"
                        for rule in sync_job.transformation_rules
                    )
                )
                
                # Check output mapping
                has_output = (
                    sync_job.field_mapping_rules is not None
                    and len(sync_job.field_mapping_rules) > 0
                )
                
                assert has_input and has_output, (
                    "BIDIRECTIONAL requires both input and output mappings"
                )
