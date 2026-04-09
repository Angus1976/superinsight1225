"""
Property-Based Tests for Version Monotonicity

Tests Property 10: Version Monotonicity

**Validates: Requirements 8.2, 20.6**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.data_lifecycle import SampleModel, VersionModel, ChangeType
from src.services.version_control_manager import VersionControlManager
from tests.property.sqlite_uuid_compat import (
    snapshot_uuid_columns,
    patch_models_to_sqlite_uuid,
    restore_uuid_columns,
)

PATCHED_MODELS = [SampleModel, VersionModel]
_UUID_COLUMN_SNAPSHOT = snapshot_uuid_columns(PATCHED_MODELS)


# ============================================================================
# Custom Fixture for Data Lifecycle Tables Only
# ============================================================================

@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Provide a database session with only data lifecycle tables.
    Patches UUID columns for SQLite compatibility.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    restore = patch_models_to_sqlite_uuid(PATCHED_MODELS, _UUID_COLUMN_SNAPSHOT)
    try:
        SampleModel.__table__.create(bind=engine, checkfirst=True)
        VersionModel.__table__.create(bind=engine, checkfirst=True)

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

# Strategy for generating number of versions
version_count_strategy = st.integers(min_value=2, max_value=20)

# Strategy for generating content variations
content_strategy = st.dictionaries(
    keys=st.sampled_from(['field1', 'field2', 'field3', 'category', 'tags']),
    values=st.one_of(
        st.text(min_size=1, max_size=50),
        st.integers(min_value=0, max_value=100),
        st.floats(min_value=0.0, max_value=1.0),
        st.lists(st.text(min_size=1, max_size=20), max_size=5)
    ),
    min_size=1,
    max_size=5
)

# Strategy for change types
change_type_strategy = st.sampled_from([
    ChangeType.INITIAL,
    ChangeType.ANNOTATION,
    ChangeType.ENHANCEMENT,
    ChangeType.CORRECTION
])


# ============================================================================
# Helper Functions
# ============================================================================

def create_version_sequence(
    db: Session,
    version_manager: VersionControlManager,
    data_id: str,
    count: int,
    user_id: str
) -> list[VersionModel]:
    """Create a sequence of versions for testing"""
    versions = []
    
    for i in range(count):
        content = {
            'iteration': i,
            'data': f'version_{i}',
            'value': i * 10
        }
        
        change_type = ChangeType.INITIAL if i == 0 else ChangeType.CORRECTION
        
        version = version_manager.create_version(
            data_id=data_id,
            content=content,
            change_type=change_type,
            created_by=user_id,
            description=f"Version {i+1}"
        )
        
        versions.append(version)
    
    return versions


# ============================================================================
# Property 10: Version Monotonicity
# **Validates: Requirements 8.2, 20.6**
# ============================================================================

@pytest.mark.property
class TestVersionMonotonicity:
    """
    Property 10: Version Monotonicity
    
    Version numbers must be strictly monotonically increasing for each data item.
    For any data_id, if version V1 is created before version V2, then
    V1.version_number < V2.version_number. This ensures consistent version ordering.
    """
    
    @given(version_count=version_count_strategy)
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_numbers_strictly_increase(
        self,
        db_session: Session,
        version_count: int
    ):
        """
        Property: Version numbers strictly increase with each new version.
        
        For any sequence of version creations, each new version must have
        a version_number strictly greater than the previous version.
        """
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create sequence of versions
        versions = create_version_sequence(
            db_session,
            version_manager,
            data_id,
            version_count,
            user_id
        )
        
        # Assert: Version numbers are strictly increasing
        for i in range(1, len(versions)):
            assert versions[i].version_number > versions[i-1].version_number, (
                f"Version {i} number {versions[i].version_number} should be "
                f"greater than version {i-1} number {versions[i-1].version_number}"
            )
            
            # Assert: Version numbers increase by exactly 1
            assert versions[i].version_number == versions[i-1].version_number + 1, (
                f"Version numbers should increment by 1, but "
                f"{versions[i].version_number} - {versions[i-1].version_number} = "
                f"{versions[i].version_number - versions[i-1].version_number}"
            )
    
    @given(version_count=version_count_strategy)
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_timestamps_correlate_with_numbers(
        self,
        db_session: Session,
        version_count: int
    ):
        """
        Property: Later version numbers have later or equal creation timestamps.
        
        For any two versions V1 and V2 where V1.version_number < V2.version_number,
        V1.created_at <= V2.created_at must hold.
        """
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create sequence of versions
        versions = create_version_sequence(
            db_session,
            version_manager,
            data_id,
            version_count,
            user_id
        )
        
        # Assert: Timestamps are monotonically non-decreasing
        for i in range(1, len(versions)):
            assert versions[i].created_at >= versions[i-1].created_at, (
                f"Version {i} created_at {versions[i].created_at} should be >= "
                f"version {i-1} created_at {versions[i-1].created_at}"
            )
    
    @given(
        version_count=version_count_strategy,
        content=content_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_monotonicity_independent_of_content(
        self,
        db_session: Session,
        version_count: int,
        content: dict
    ):
        """
        Property: Version monotonicity holds regardless of content changes.
        
        Version numbers must increase monotonically even when content
        changes are arbitrary or minimal.
        """
        assume(len(content) > 0)  # Ensure content is not empty
        
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        versions = []
        
        # Create versions with varying content
        for i in range(version_count):
            # Vary content slightly for each version
            version_content = {**content, 'iteration': i}
            
            change_type = ChangeType.INITIAL if i == 0 else ChangeType.CORRECTION
            
            version = version_manager.create_version(
                data_id=data_id,
                content=version_content,
                change_type=change_type,
                created_by=user_id
            )
            
            versions.append(version)
        
        # Assert: Version numbers are strictly increasing
        for i in range(1, len(versions)):
            assert versions[i].version_number > versions[i-1].version_number, (
                f"Version monotonicity violated: {versions[i].version_number} "
                f"not greater than {versions[i-1].version_number}"
            )
    
    @given(
        num_data_items=st.integers(min_value=2, max_value=5),
        versions_per_item=st.lists(
            st.integers(min_value=2, max_value=10),
            min_size=2,
            max_size=5
        )
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_monotonicity_per_data_item(
        self,
        db_session: Session,
        num_data_items: int,
        versions_per_item: list
    ):
        """
        Property: Version monotonicity is maintained independently per data item.
        
        Each data_id has its own independent version sequence starting from 1,
        and version numbers for different data items do not interfere.
        """
        # Ensure we have enough version counts
        if len(versions_per_item) < num_data_items:
            versions_per_item = versions_per_item + [2] * (num_data_items - len(versions_per_item))
        versions_per_item = versions_per_item[:num_data_items]
        
        version_manager = VersionControlManager(db_session)
        user_id = str(uuid4())
        
        # Create multiple data items with their own version sequences
        all_versions = {}
        
        for item_idx in range(num_data_items):
            data_id = str(uuid4())
            version_count = versions_per_item[item_idx]
            
            versions = create_version_sequence(
                db_session,
                version_manager,
                data_id,
                version_count,
                user_id
            )
            
            all_versions[data_id] = versions
        
        # Assert: Each data item has monotonic version numbers
        for data_id, versions in all_versions.items():
            # Check first version starts at 1
            assert versions[0].version_number == 1, (
                f"First version for {data_id} should be 1, got {versions[0].version_number}"
            )
            
            # Check monotonicity
            for i in range(1, len(versions)):
                assert versions[i].version_number == versions[i-1].version_number + 1, (
                    f"Version sequence broken for {data_id}: "
                    f"{versions[i-1].version_number} -> {versions[i].version_number}"
                )
    
    @given(version_count=version_count_strategy)
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_history_ordered_by_version_number(
        self,
        db_session: Session,
        version_count: int
    ):
        """
        Property: Version history is correctly ordered by version number.
        
        When retrieving version history, versions should be ordered by
        version_number in descending order (newest first).
        """
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create sequence of versions
        created_versions = create_version_sequence(
            db_session,
            version_manager,
            data_id,
            version_count,
            user_id
        )
        
        # Get version history
        history = version_manager.get_version_history(data_id)
        
        # Assert: History length matches created versions
        assert len(history) == version_count, (
            f"Expected {version_count} versions in history, got {len(history)}"
        )
        
        # Assert: History is ordered by version_number descending
        for i in range(1, len(history)):
            assert history[i].version_number < history[i-1].version_number, (
                f"Version history not properly ordered: "
                f"{history[i-1].version_number} should be > {history[i].version_number}"
            )
            
            # Assert: Consecutive versions in history differ by 1
            assert history[i-1].version_number == history[i].version_number + 1, (
                f"Version history has gap: "
                f"{history[i-1].version_number} -> {history[i].version_number}"
            )
    
    @given(
        version_count=version_count_strategy,
        change_type=change_type_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_monotonicity_independent_of_change_type(
        self,
        db_session: Session,
        version_count: int,
        change_type: ChangeType
    ):
        """
        Property: Version monotonicity holds regardless of change type.
        
        Version numbers must increase monotonically regardless of whether
        the change is INITIAL, ANNOTATION, ENHANCEMENT, or CORRECTION.
        """
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        versions = []
        
        # Create versions with specified change type (except first which is INITIAL)
        for i in range(version_count):
            content = {'iteration': i, 'data': f'version_{i}'}
            
            # First version must be INITIAL
            current_change_type = ChangeType.INITIAL if i == 0 else change_type
            
            version = version_manager.create_version(
                data_id=data_id,
                content=content,
                change_type=current_change_type,
                created_by=user_id
            )
            
            versions.append(version)
        
        # Assert: Version numbers are strictly increasing
        for i in range(1, len(versions)):
            assert versions[i].version_number > versions[i-1].version_number, (
                f"Version monotonicity violated with change_type {change_type}: "
                f"{versions[i].version_number} not greater than {versions[i-1].version_number}"
            )
    
    @given(version_count=st.integers(min_value=3, max_value=15))
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_no_version_number_gaps(
        self,
        db_session: Session,
        version_count: int
    ):
        """
        Property: Version numbers have no gaps in the sequence.
        
        For any data item with N versions, the version numbers should be
        exactly [1, 2, 3, ..., N] with no gaps or duplicates.
        """
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create sequence of versions
        versions = create_version_sequence(
            db_session,
            version_manager,
            data_id,
            version_count,
            user_id
        )
        
        # Extract version numbers
        version_numbers = [v.version_number for v in versions]
        
        # Assert: Version numbers form continuous sequence from 1 to N
        expected_sequence = list(range(1, version_count + 1))
        assert version_numbers == expected_sequence, (
            f"Version numbers {version_numbers} do not match expected sequence {expected_sequence}"
        )
        
        # Assert: No duplicates
        assert len(set(version_numbers)) == len(version_numbers), (
            f"Duplicate version numbers found: {version_numbers}"
        )
    
    @given(version_count=version_count_strategy)
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_number_always_positive(
        self,
        db_session: Session,
        version_count: int
    ):
        """
        Property: All version numbers are positive integers.
        
        Version numbers must always be >= 1 (positive integers).
        """
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create sequence of versions
        versions = create_version_sequence(
            db_session,
            version_manager,
            data_id,
            version_count,
            user_id
        )
        
        # Assert: All version numbers are positive
        for version in versions:
            assert version.version_number >= 1, (
                f"Version number {version.version_number} is not positive"
            )
            
            # Assert: Version numbers are integers
            assert isinstance(version.version_number, int), (
                f"Version number {version.version_number} is not an integer"
            )
    
    @given(
        version_count=version_count_strategy,
        rollback_target=st.integers(min_value=1, max_value=10)
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_monotonicity_after_rollback(
        self,
        db_session: Session,
        version_count: int,
        rollback_target: int
    ):
        """
        Property: Version monotonicity is maintained after rollback operations.
        
        When rolling back to a previous version, a new version is created
        with a higher version number, maintaining monotonicity.
        """
        # Ensure rollback target is valid
        assume(rollback_target < version_count)
        
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create initial sequence of versions
        versions = create_version_sequence(
            db_session,
            version_manager,
            data_id,
            version_count,
            user_id
        )
        
        # Get the version to rollback to
        target_version = versions[rollback_target - 1]  # -1 because version numbers start at 1
        
        # Perform rollback
        rollback_version = version_manager.rollback_to_version(
            data_id=data_id,
            version_id=str(target_version.id),
            rolled_back_by=user_id,
            reason="Testing rollback monotonicity"
        )
        
        # Assert: Rollback created a new version with higher number
        assert rollback_version.version_number > versions[-1].version_number, (
            f"Rollback version number {rollback_version.version_number} should be "
            f"greater than last version number {versions[-1].version_number}"
        )
        
        # Assert: Rollback version number is exactly last + 1
        assert rollback_version.version_number == versions[-1].version_number + 1, (
            f"Rollback version number should be {versions[-1].version_number + 1}, "
            f"got {rollback_version.version_number}"
        )
        
        # Get full history and verify monotonicity
        full_history = version_manager.get_version_history(data_id)
        
        # Assert: Full history maintains monotonicity
        for i in range(1, len(full_history)):
            assert full_history[i].version_number < full_history[i-1].version_number, (
                f"Version history monotonicity violated after rollback"
            )
    
    @given(version_count=st.integers(min_value=5, max_value=15))
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_comparison_respects_monotonicity(
        self,
        db_session: Session,
        version_count: int
    ):
        """
        Property: Version comparison correctly identifies newer versions.
        
        For any two versions V1 and V2 where V1.version_number < V2.version_number,
        V2 should be identified as the newer version.
        """
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create sequence of versions
        versions = create_version_sequence(
            db_session,
            version_manager,
            data_id,
            version_count,
            user_id
        )
        
        # Compare first and last versions
        first_version = versions[0]
        last_version = versions[-1]
        
        diff = version_manager.compare_versions(
            str(first_version.id),
            str(last_version.id)
        )
        
        # Assert: Summary correctly identifies version numbers
        assert diff.summary['version1_number'] == first_version.version_number
        assert diff.summary['version2_number'] == last_version.version_number
        
        # Assert: Version 2 has higher number
        assert diff.summary['version2_number'] > diff.summary['version1_number'], (
            f"Version 2 number {diff.summary['version2_number']} should be greater "
            f"than version 1 number {diff.summary['version1_number']}"
        )
        
        # Assert: Timestamps reflect version order
        v1_time = datetime.fromisoformat(diff.summary['version1_created_at'])
        v2_time = datetime.fromisoformat(diff.summary['version2_created_at'])
        assert v2_time >= v1_time, (
            f"Version 2 timestamp {v2_time} should be >= version 1 timestamp {v1_time}"
        )
