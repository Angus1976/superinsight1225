"""
Property-Based Tests for Version Creation on Modification

Tests Property 9: Version Creation on Modification

**Validates: Requirements 4.6, 6.6, 8.1**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.data_lifecycle import SampleModel, VersionModel, ChangeType
from src.services.sample_library_manager import SampleLibraryManager
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

# Strategy for generating sample categories
category_strategy = st.sampled_from([
    'classification', 'entity_recognition', 'sentiment_analysis',
    'relation_extraction', 'question_answering'
])

# Strategy for generating quality scores (0-1)
quality_score_strategy = st.floats(min_value=0.0, max_value=1.0)

# Strategy for generating tags
tag_strategy = st.lists(
    st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='-_'
    )),
    min_size=0,
    max_size=5,
    unique=True
)

# Strategy for generating update operations
update_field_strategy = st.sampled_from([
    'category', 'tags', 'quality_overall',
    'quality_completeness', 'quality_accuracy', 'quality_consistency'
])

# Strategy for generating number of modifications
modification_count_strategy = st.integers(min_value=1, max_value=10)


# ============================================================================
# Helper Functions
# ============================================================================

def create_sample(db: Session, category: str = 'test') -> SampleModel:
    """Create a sample for testing"""
    sample = SampleModel(
        id=uuid4(),
        data_id=str(uuid4()),
        content={'test': 'data', 'value': 'content'},
        category=category,
        quality_overall=0.8,
        quality_completeness=0.8,
        quality_accuracy=0.8,
        quality_consistency=0.8,
        version=1,
        tags=[],
        usage_count=0,
        last_used_at=None,
        metadata_={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)
    return sample


def generate_update(field: str, category: str, tags: list, quality: float) -> dict:
    """Generate an update dictionary based on field type"""
    if field == 'category':
        return {'category': category}
    elif field == 'tags':
        return {'tags': tags}
    elif field.startswith('quality_'):
        return {field: quality}
    else:
        return {}


# ============================================================================
# Property 9: Version Creation on Modification
# **Validates: Requirements 4.6, 6.6, 8.1**
# ============================================================================

@pytest.mark.property
class TestVersionCreationOnModification:
    """
    Property 9: Version Creation on Modification
    
    Every time data is modified (sample update, annotation completion,
    enhancement completion), a new version must be automatically created.
    This ensures complete version history and traceability.
    
    This test focuses on sample updates with version control enabled.
    """
    
    @given(
        category=category_strategy,
        quality=quality_score_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_created_on_sample_update(
        self,
        db_session: Session,
        category: str,
        quality: float
    ):
        """
        Property: A new version is created when a sample is updated.
        
        For any sample update with version control enabled, a new version
        must be created in the version history.
        """
        # Create managers with version control enabled
        version_manager = VersionControlManager(db_session)
        sample_manager = SampleLibraryManager(db_session, version_manager)
        
        # Create sample
        sample = create_sample(db_session)
        user_id = str(uuid4())
        
        # Get initial version count
        initial_versions = version_manager.get_version_history(sample.data_id)
        initial_version_count = len(initial_versions)
        
        # Update sample
        updates = {'category': category, 'quality_overall': quality}
        updated_sample = sample_manager.update_sample(
            str(sample.id),
            updates,
            updated_by=user_id
        )
        
        # Get version history after update
        versions_after = version_manager.get_version_history(sample.data_id)
        
        # Assert: A new version was created
        assert len(versions_after) == initial_version_count + 1, (
            f"Expected {initial_version_count + 1} versions after update, "
            f"but got {len(versions_after)}"
        )
        
        # Assert: The new version is the most recent
        latest_version = versions_after[0]  # Ordered by version_number desc
        assert latest_version.data_id == sample.data_id, (
            f"Latest version data_id {latest_version.data_id} "
            f"should match sample data_id {sample.data_id}"
        )
        assert latest_version.created_by == user_id, (
            f"Latest version created_by {latest_version.created_by} "
            f"should match user_id {user_id}"
        )
    
    @given(modification_count=modification_count_strategy)
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_count_matches_modification_count(
        self,
        db_session: Session,
        modification_count: int
    ):
        """
        Property: Number of versions equals number of modifications.
        
        For N modifications to a sample, there should be N versions created
        (assuming version control is enabled for all modifications).
        """
        # Create managers with version control enabled
        version_manager = VersionControlManager(db_session)
        sample_manager = SampleLibraryManager(db_session, version_manager)
        
        # Create sample
        sample = create_sample(db_session)
        user_id = str(uuid4())
        
        # Get initial version count
        initial_versions = version_manager.get_version_history(sample.data_id)
        initial_version_count = len(initial_versions)
        
        # Perform N modifications
        for i in range(modification_count):
            # Alternate between different update types
            if i % 3 == 0:
                updates = {'category': f'category_{i}'}
            elif i % 3 == 1:
                updates = {'tags': [f'tag_{i}']}
            else:
                updates = {'quality_overall': min(0.5 + (i * 0.05), 1.0)}
            
            sample_manager.update_sample(
                str(sample.id),
                updates,
                updated_by=user_id
            )
        
        # Get final version count
        final_versions = version_manager.get_version_history(sample.data_id)
        
        # Assert: Version count increased by modification_count
        expected_count = initial_version_count + modification_count
        assert len(final_versions) == expected_count, (
            f"After {modification_count} modifications, expected {expected_count} versions, "
            f"but got {len(final_versions)}"
        )
    
    @given(
        category=category_strategy,
        tags=tag_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_contains_updated_content(
        self,
        db_session: Session,
        category: str,
        tags: list
    ):
        """
        Property: Created version contains the updated content.
        
        When a sample is updated, the new version must contain the
        updated values in its content.
        """
        # Create managers with version control enabled
        version_manager = VersionControlManager(db_session)
        sample_manager = SampleLibraryManager(db_session, version_manager)
        
        # Create sample
        sample = create_sample(db_session)
        user_id = str(uuid4())
        
        # Update sample
        updates = {'category': category, 'tags': tags}
        updated_sample = sample_manager.update_sample(
            str(sample.id),
            updates,
            updated_by=user_id
        )
        
        # Get latest version
        versions = version_manager.get_version_history(sample.data_id)
        latest_version = versions[0]
        
        # Assert: Version content contains updated values
        assert latest_version.content['category'] == category, (
            f"Version content category {latest_version.content['category']} "
            f"should match updated category {category}"
        )
        assert latest_version.content['tags'] == tags, (
            f"Version content tags {latest_version.content['tags']} "
            f"should match updated tags {tags}"
        )
    
    @given(
        field=update_field_strategy,
        category=category_strategy,
        tags=tag_strategy,
        quality=quality_score_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_metadata_records_updated_fields(
        self,
        db_session: Session,
        field: str,
        category: str,
        tags: list,
        quality: float
    ):
        """
        Property: Version metadata records which fields were updated.
        
        When a sample is updated, the version metadata must record
        which fields were modified.
        """
        # Create managers with version control enabled
        version_manager = VersionControlManager(db_session)
        sample_manager = SampleLibraryManager(db_session, version_manager)
        
        # Create sample
        sample = create_sample(db_session)
        user_id = str(uuid4())
        
        # Generate update based on field
        updates = generate_update(field, category, tags, quality)
        assume(len(updates) > 0)  # Skip if no valid update generated
        
        # Update sample
        updated_sample = sample_manager.update_sample(
            str(sample.id),
            updates,
            updated_by=user_id
        )
        
        # Get latest version
        versions = version_manager.get_version_history(sample.data_id)
        latest_version = versions[0]
        
        # Assert: Version metadata contains updated_fields
        assert 'updated_fields' in latest_version.metadata_, (
            "Version metadata should contain 'updated_fields'"
        )
        
        # Assert: Updated fields are recorded
        updated_fields = latest_version.metadata_['updated_fields']
        for update_field in updates.keys():
            assert update_field in updated_fields, (
                f"Field '{update_field}' should be in updated_fields {updated_fields}"
            )
    
    def test_no_version_created_without_version_control(
        self,
        db_session: Session
    ):
        """
        Property: No version is created when version control is disabled.
        
        When a sample is updated without version control enabled,
        no new version should be created.
        """
        # Create manager WITHOUT version control
        sample_manager = SampleLibraryManager(db_session, version_control_manager=None)
        version_manager = VersionControlManager(db_session)
        
        # Create sample
        sample = create_sample(db_session)
        user_id = str(uuid4())
        
        # Get initial version count
        initial_versions = version_manager.get_version_history(sample.data_id)
        initial_version_count = len(initial_versions)
        
        # Update sample (without version control)
        updates = {'category': 'new_category'}
        updated_sample = sample_manager.update_sample(
            str(sample.id),
            updates,
            updated_by=user_id
        )
        
        # Get version count after update
        versions_after = version_manager.get_version_history(sample.data_id)
        
        # Assert: No new version was created
        assert len(versions_after) == initial_version_count, (
            f"Without version control, version count should remain {initial_version_count}, "
            f"but got {len(versions_after)}"
        )
    
    @given(modification_count=st.integers(min_value=2, max_value=5))
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_numbers_increment_monotonically(
        self,
        db_session: Session,
        modification_count: int
    ):
        """
        Property: Version numbers increment monotonically with each modification.
        
        For sequential modifications, version numbers must strictly increase
        by 1 for each modification.
        """
        # Create managers with version control enabled
        version_manager = VersionControlManager(db_session)
        sample_manager = SampleLibraryManager(db_session, version_manager)
        
        # Create sample
        sample = create_sample(db_session)
        user_id = str(uuid4())
        
        # Track version numbers
        version_numbers = []
        
        # Perform modifications and track version numbers
        for i in range(modification_count):
            updates = {'category': f'category_{i}'}
            sample_manager.update_sample(
                str(sample.id),
                updates,
                updated_by=user_id
            )
            
            # Get latest version number
            versions = version_manager.get_version_history(sample.data_id)
            latest_version = versions[0]
            version_numbers.append(latest_version.version_number)
        
        # Assert: Version numbers are strictly increasing
        for i in range(1, len(version_numbers)):
            assert version_numbers[i] > version_numbers[i-1], (
                f"Version number {version_numbers[i]} at index {i} "
                f"should be greater than {version_numbers[i-1]} at index {i-1}"
            )
            
            # Assert: Version numbers increment by at least 1
            assert version_numbers[i] >= version_numbers[i-1] + 1, (
                f"Version number should increment by at least 1, "
                f"but {version_numbers[i]} - {version_numbers[i-1]} = "
                f"{version_numbers[i] - version_numbers[i-1]}"
            )
    
    @given(
        category=category_strategy,
        quality=quality_score_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_change_type_is_correction(
        self,
        db_session: Session,
        category: str,
        quality: float
    ):
        """
        Property: Versions created from sample updates have CORRECTION change type.
        
        When a sample is updated, the created version should have
        change_type set to CORRECTION.
        """
        # Create managers with version control enabled
        version_manager = VersionControlManager(db_session)
        sample_manager = SampleLibraryManager(db_session, version_manager)
        
        # Create sample
        sample = create_sample(db_session)
        user_id = str(uuid4())
        
        # Update sample
        updates = {'category': category, 'quality_overall': quality}
        updated_sample = sample_manager.update_sample(
            str(sample.id),
            updates,
            updated_by=user_id
        )
        
        # Get latest version
        versions = version_manager.get_version_history(sample.data_id)
        latest_version = versions[0]
        
        # Assert: Change type is CORRECTION
        assert latest_version.change_type == ChangeType.CORRECTION, (
            f"Version change_type should be CORRECTION, "
            f"but got {latest_version.change_type}"
        )
    
    @given(
        num_samples=st.integers(min_value=2, max_value=5),
        modifications_per_sample=st.lists(
            st.integers(min_value=1, max_value=3),
            min_size=2,
            max_size=5
        )
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_creation_independent_per_sample(
        self,
        db_session: Session,
        num_samples: int,
        modifications_per_sample: list
    ):
        """
        Property: Version creation is independent per sample.
        
        Modifying one sample should not affect the version history
        of other samples.
        """
        # Ensure we have enough modification counts
        if len(modifications_per_sample) < num_samples:
            modifications_per_sample = modifications_per_sample + [1] * (num_samples - len(modifications_per_sample))
        modifications_per_sample = modifications_per_sample[:num_samples]
        
        # Create managers with version control enabled
        version_manager = VersionControlManager(db_session)
        sample_manager = SampleLibraryManager(db_session, version_manager)
        
        # Create multiple samples
        samples = [create_sample(db_session) for _ in range(num_samples)]
        user_id = str(uuid4())
        
        # Modify each sample independently
        for sample, mod_count in zip(samples, modifications_per_sample):
            for i in range(mod_count):
                updates = {'category': f'category_{i}'}
                sample_manager.update_sample(
                    str(sample.id),
                    updates,
                    updated_by=user_id
                )
        
        # Verify each sample has correct version count
        for sample, expected_count in zip(samples, modifications_per_sample):
            versions = version_manager.get_version_history(sample.data_id)
            
            assert len(versions) == expected_count, (
                f"Sample {sample.id} should have {expected_count} versions, "
                f"but got {len(versions)}"
            )
            
            # Verify all versions belong to this sample
            for version in versions:
                assert version.data_id == sample.data_id, (
                    f"Version {version.id} data_id {version.data_id} "
                    f"should match sample data_id {sample.data_id}"
                )
    
    @given(
        category=category_strategy,
        quality=quality_score_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_has_valid_checksum(
        self,
        db_session: Session,
        category: str,
        quality: float
    ):
        """
        Property: Created versions have valid checksums.
        
        When a version is created from a sample update, it must have
        a valid checksum that can be verified.
        """
        # Create managers with version control enabled
        version_manager = VersionControlManager(db_session)
        sample_manager = SampleLibraryManager(db_session, version_manager)
        
        # Create sample
        sample = create_sample(db_session)
        user_id = str(uuid4())
        
        # Update sample
        updates = {'category': category, 'quality_overall': quality}
        updated_sample = sample_manager.update_sample(
            str(sample.id),
            updates,
            updated_by=user_id
        )
        
        # Get latest version
        versions = version_manager.get_version_history(sample.data_id)
        latest_version = versions[0]
        
        # Assert: Version has a checksum
        assert latest_version.checksum is not None, (
            "Version should have a checksum"
        )
        assert len(latest_version.checksum) > 0, (
            "Version checksum should not be empty"
        )
        
        # Assert: Checksum is valid (can be verified)
        is_valid, error_msg = version_manager.verify_checksum(str(latest_version.id))
        assert is_valid, (
            f"Version checksum should be valid, but verification failed: {error_msg}"
        )
