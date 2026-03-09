"""
Property-Based Tests for Version Checksum Integrity

Tests Property 19: Version Checksum Integrity

**Validates: Requirements 8.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import hashlib
import json

from src.models.data_lifecycle import SampleModel, VersionModel, ChangeType
from src.services.version_control_manager import VersionControlManager


# ============================================================================
# Custom Fixture for Data Lifecycle Tables Only
# ============================================================================

@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Provide a database session with only data lifecycle tables.
    
    This avoids the JSONB compatibility issue with SQLite by only creating
    the data lifecycle tables (which use JSON, not JSONB).
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create only the specific tables we need for this test
    # (samples and versions tables)
    SampleModel.__table__.create(bind=engine, checkfirst=True)
    VersionModel.__table__.create(bind=engine, checkfirst=True)
    
    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    engine.dispose()


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating content variations
content_strategy = st.dictionaries(
    keys=st.sampled_from(['field1', 'field2', 'field3', 'category', 'tags', 'data', 'metadata']),
    values=st.one_of(
        st.text(min_size=1, max_size=100),
        st.integers(min_value=0, max_value=1000),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5),
        st.booleans()
    ),
    min_size=1,
    max_size=10
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

def calculate_expected_checksum(content: dict) -> str:
    """Calculate expected SHA-256 checksum for content"""
    content_json = json.dumps(content, sort_keys=True, ensure_ascii=False)
    hash_obj = hashlib.sha256(content_json.encode('utf-8'))
    return hash_obj.hexdigest()


# ============================================================================
# Property 19: Version Checksum Integrity
# **Validates: Requirements 8.5**
# ============================================================================

@pytest.mark.property
class TestVersionChecksumIntegrity:
    """
    Property 19: Version Checksum Integrity
    
    Every version must have a valid checksum that can be verified. The checksum
    must be deterministic (same content produces same checksum) and detect any
    tampering with the version content.
    """
    
    @given(content=content_strategy)
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_version_has_checksum_on_creation(
        self,
        db_session: Session,
        content: dict
    ):
        """
        Property: Every created version has a non-empty checksum.
        
        When a version is created, it must have a checksum field that is
        a non-empty string.
        """
        assume(len(content) > 0)
        
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create version
        version = version_manager.create_version(
            data_id=data_id,
            content=content,
            change_type=ChangeType.INITIAL,
            created_by=user_id
        )
        
        # Assert: Checksum exists and is non-empty
        assert version.checksum is not None, "Version checksum should not be None"
        assert isinstance(version.checksum, str), "Checksum should be a string"
        assert len(version.checksum) > 0, "Checksum should not be empty"
        
        # Assert: Checksum is SHA-256 format (64 hex characters)
        assert len(version.checksum) == 64, (
            f"SHA-256 checksum should be 64 characters, got {len(version.checksum)}"
        )
        assert all(c in '0123456789abcdef' for c in version.checksum), (
            "Checksum should be hexadecimal"
        )
    
    @given(content=content_strategy)
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_checksum_is_deterministic(
        self,
        db_session: Session,
        content: dict
    ):
        """
        Property: Same content produces same checksum (deterministic).
        
        Creating multiple versions with identical content should produce
        identical checksums.
        """
        assume(len(content) > 0)
        
        version_manager = VersionControlManager(db_session)
        user_id = str(uuid4())
        
        # Create two versions with identical content for different data items
        data_id1 = str(uuid4())
        data_id2 = str(uuid4())
        
        version1 = version_manager.create_version(
            data_id=data_id1,
            content=content,
            change_type=ChangeType.INITIAL,
            created_by=user_id
        )
        
        version2 = version_manager.create_version(
            data_id=data_id2,
            content=content,
            change_type=ChangeType.INITIAL,
            created_by=user_id
        )
        
        # Assert: Identical content produces identical checksums
        assert version1.checksum == version2.checksum, (
            f"Identical content should produce identical checksums: "
            f"{version1.checksum} != {version2.checksum}"
        )
    
    @given(content=content_strategy)
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_checksum_verification_succeeds_for_valid_version(
        self,
        db_session: Session,
        content: dict
    ):
        """
        Property: Checksum verification succeeds for unmodified versions.
        
        For any version that hasn't been tampered with, verifying its
        checksum should return True.
        """
        assume(len(content) > 0)
        
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create version
        version = version_manager.create_version(
            data_id=data_id,
            content=content,
            change_type=ChangeType.INITIAL,
            created_by=user_id
        )
        
        # Verify checksum
        is_valid, error_message = version_manager.verify_checksum(str(version.id))
        
        # Assert: Verification succeeds
        assert is_valid is True, f"Checksum verification should succeed: {error_message}"
        assert error_message is None, f"Error message should be None for valid checksum: {error_message}"
    
    @given(content=content_strategy)
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_checksum_matches_expected_sha256(
        self,
        db_session: Session,
        content: dict
    ):
        """
        Property: Checksum matches expected SHA-256 hash of content.
        
        The stored checksum should match the SHA-256 hash calculated
        from the content using the same algorithm.
        """
        assume(len(content) > 0)
        
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create version
        version = version_manager.create_version(
            data_id=data_id,
            content=content,
            change_type=ChangeType.INITIAL,
            created_by=user_id
        )
        
        # Calculate expected checksum
        expected_checksum = calculate_expected_checksum(content)
        
        # Assert: Stored checksum matches expected
        assert version.checksum == expected_checksum, (
            f"Stored checksum {version.checksum} does not match "
            f"expected checksum {expected_checksum}"
        )
    
    @given(
        content1=content_strategy,
        content2=content_strategy
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_different_content_produces_different_checksums(
        self,
        db_session: Session,
        content1: dict,
        content2: dict
    ):
        """
        Property: Different content produces different checksums.
        
        Creating versions with different content should produce different
        checksums (collision resistance).
        """
        assume(len(content1) > 0 and len(content2) > 0)
        assume(content1 != content2)  # Ensure contents are actually different
        
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create two versions with different content
        version1 = version_manager.create_version(
            data_id=data_id,
            content=content1,
            change_type=ChangeType.INITIAL,
            created_by=user_id
        )
        
        version2 = version_manager.create_version(
            data_id=data_id,
            content=content2,
            change_type=ChangeType.ANNOTATION,
            created_by=user_id
        )
        
        # Assert: Different content produces different checksums
        assert version1.checksum != version2.checksum, (
            f"Different content should produce different checksums, "
            f"but both have checksum: {version1.checksum}"
        )
    
    @given(content=content_strategy)
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_checksum_detects_content_tampering(
        self,
        db_session: Session,
        content: dict
    ):
        """
        Property: Checksum verification detects tampered content.
        
        If version content is modified after creation, checksum verification
        should fail and report the mismatch.
        """
        assume(len(content) > 0)
        
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create version
        version = version_manager.create_version(
            data_id=data_id,
            content=content,
            change_type=ChangeType.INITIAL,
            created_by=user_id
        )
        
        # Store original checksum
        original_checksum = version.checksum
        
        # Tamper with content (simulate database corruption)
        tampered_content = {**content, 'tampered': True, 'extra_field': 'malicious'}
        version.content = tampered_content
        db_session.commit()
        db_session.refresh(version)
        
        # Verify checksum (should fail)
        is_valid, error_message = version_manager.verify_checksum(str(version.id))
        
        # Assert: Verification fails
        assert is_valid is False, "Checksum verification should fail for tampered content"
        assert error_message is not None, "Error message should be provided for failed verification"
        assert "mismatch" in error_message.lower(), (
            f"Error message should mention mismatch: {error_message}"
        )
        assert original_checksum in error_message, (
            f"Error message should include original checksum: {error_message}"
        )
    
    @given(
        content=content_strategy,
        change_type=change_type_strategy
    )
    @settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_checksum_independent_of_change_type(
        self,
        db_session: Session,
        content: dict,
        change_type: ChangeType
    ):
        """
        Property: Checksum depends only on content, not change type.
        
        Versions with identical content but different change types should
        have identical checksums.
        """
        assume(len(content) > 0)
        
        version_manager = VersionControlManager(db_session)
        user_id = str(uuid4())
        
        # Create two versions with same content but different change types
        data_id1 = str(uuid4())
        data_id2 = str(uuid4())
        
        version1 = version_manager.create_version(
            data_id=data_id1,
            content=content,
            change_type=ChangeType.INITIAL,
            created_by=user_id
        )
        
        # Use different change type for second version
        other_change_type = change_type if change_type != ChangeType.INITIAL else ChangeType.ANNOTATION
        
        version2 = version_manager.create_version(
            data_id=data_id2,
            content=content,
            change_type=other_change_type,
            created_by=user_id
        )
        
        # Assert: Same content produces same checksum regardless of change type
        assert version1.checksum == version2.checksum, (
            f"Checksum should be independent of change type: "
            f"{version1.checksum} != {version2.checksum}"
        )
    
    @given(content=content_strategy)
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_checksum_independent_of_metadata(
        self,
        db_session: Session,
        content: dict
    ):
        """
        Property: Checksum depends only on content, not metadata.
        
        Versions with identical content but different metadata should
        have identical checksums.
        """
        assume(len(content) > 0)
        
        version_manager = VersionControlManager(db_session)
        user_id = str(uuid4())
        
        # Create two versions with same content but different metadata
        data_id1 = str(uuid4())
        data_id2 = str(uuid4())
        
        version1 = version_manager.create_version(
            data_id=data_id1,
            content=content,
            change_type=ChangeType.INITIAL,
            created_by=user_id,
            metadata={'source': 'test1', 'priority': 'high'}
        )
        
        version2 = version_manager.create_version(
            data_id=data_id2,
            content=content,
            change_type=ChangeType.INITIAL,
            created_by=user_id,
            metadata={'source': 'test2', 'priority': 'low'}
        )
        
        # Assert: Same content produces same checksum regardless of metadata
        assert version1.checksum == version2.checksum, (
            f"Checksum should be independent of metadata: "
            f"{version1.checksum} != {version2.checksum}"
        )
    
    @given(content=content_strategy)
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_checksum_persists_across_retrieval(
        self,
        db_session: Session,
        content: dict
    ):
        """
        Property: Checksum persists correctly across database operations.
        
        Retrieving a version from the database should return the same
        checksum that was stored.
        """
        assume(len(content) > 0)
        
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create version
        created_version = version_manager.create_version(
            data_id=data_id,
            content=content,
            change_type=ChangeType.INITIAL,
            created_by=user_id
        )
        
        original_checksum = created_version.checksum
        version_id = str(created_version.id)
        
        # Clear session to force fresh retrieval
        db_session.expire_all()
        
        # Retrieve version
        retrieved_version = version_manager.get_version(version_id)
        
        # Assert: Checksum persists
        assert retrieved_version is not None, "Version should be retrievable"
        assert retrieved_version.checksum == original_checksum, (
            f"Checksum should persist across retrieval: "
            f"{retrieved_version.checksum} != {original_checksum}"
        )
    
    @given(
        content=content_strategy,
        num_versions=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_all_versions_have_valid_checksums(
        self,
        db_session: Session,
        content: dict,
        num_versions: int
    ):
        """
        Property: All versions in history have valid checksums.
        
        When creating multiple versions, each should have a valid checksum
        that can be verified.
        """
        assume(len(content) > 0)
        
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create multiple versions
        versions = []
        for i in range(num_versions):
            version_content = {**content, 'iteration': i}
            change_type = ChangeType.INITIAL if i == 0 else ChangeType.CORRECTION
            
            version = version_manager.create_version(
                data_id=data_id,
                content=version_content,
                change_type=change_type,
                created_by=user_id
            )
            versions.append(version)
        
        # Assert: All versions have valid checksums
        for version in versions:
            assert version.checksum is not None, (
                f"Version {version.version_number} should have checksum"
            )
            assert len(version.checksum) == 64, (
                f"Version {version.version_number} checksum should be 64 chars"
            )
            
            # Verify each checksum
            is_valid, error_msg = version_manager.verify_checksum(str(version.id))
            assert is_valid is True, (
                f"Version {version.version_number} checksum verification failed: {error_msg}"
            )
    
    @given(content=content_strategy)
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rollback_version_has_valid_checksum(
        self,
        db_session: Session,
        content: dict
    ):
        """
        Property: Rollback versions have valid checksums.
        
        When rolling back to a previous version, the new rollback version
        should have a valid checksum matching its content.
        """
        assume(len(content) > 0)
        
        version_manager = VersionControlManager(db_session)
        data_id = str(uuid4())
        user_id = str(uuid4())
        
        # Create initial version
        version1 = version_manager.create_version(
            data_id=data_id,
            content=content,
            change_type=ChangeType.INITIAL,
            created_by=user_id
        )
        
        # Create second version with different content
        content2 = {**content, 'modified': True}
        version2 = version_manager.create_version(
            data_id=data_id,
            content=content2,
            change_type=ChangeType.ANNOTATION,
            created_by=user_id
        )
        
        # Rollback to version 1
        rollback_version = version_manager.rollback_to_version(
            data_id=data_id,
            version_id=str(version1.id),
            rolled_back_by=user_id,
            reason="Testing checksum"
        )
        
        # Assert: Rollback version has valid checksum
        assert rollback_version.checksum is not None, "Rollback version should have checksum"
        assert len(rollback_version.checksum) == 64, "Rollback checksum should be 64 chars"
        
        # Assert: Rollback checksum matches original content
        assert rollback_version.checksum == version1.checksum, (
            f"Rollback version should have same checksum as original: "
            f"{rollback_version.checksum} != {version1.checksum}"
        )
        
        # Assert: Rollback checksum can be verified
        is_valid, error_msg = version_manager.verify_checksum(str(rollback_version.id))
        assert is_valid is True, f"Rollback checksum verification failed: {error_msg}"
    
    @given(content=content_strategy)
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_checksum_verification_fails_for_nonexistent_version(
        self,
        db_session: Session,
        content: dict
    ):
        """
        Property: Checksum verification fails gracefully for non-existent versions.
        
        Attempting to verify a checksum for a non-existent version should
        return False with an appropriate error message.
        """
        version_manager = VersionControlManager(db_session)
        
        # Try to verify non-existent version
        fake_version_id = str(uuid4())
        is_valid, error_message = version_manager.verify_checksum(fake_version_id)
        
        # Assert: Verification fails
        assert is_valid is False, "Verification should fail for non-existent version"
        assert error_message is not None, "Error message should be provided"
        assert "not found" in error_message.lower(), (
            f"Error message should mention version not found: {error_message}"
        )
