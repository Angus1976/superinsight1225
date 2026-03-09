"""
Property-Based Tests for Concurrent Modification Detection

Tests Property 31: Concurrent Modification Detection

**Validates: Requirements 22.1, 22.2, 22.3**

For any concurrent modifications to the same data item, version conflicts
must be detected and a 409 Conflict error returned with conflicting
version information.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import MagicMock
from uuid import uuid4

from src.services.concurrent_manager import (
    ConcurrentModificationError,
    OptimisticLockManager,
    retry_on_conflict,
)


# ============================================================================
# Helpers
# ============================================================================


class FakeModel:
    """Lightweight model stand-in with a version field."""

    def __init__(self, id=None, lock_version=1):
        self.id = id or str(uuid4())
        self.lock_version = lock_version


# ============================================================================
# Test Strategies
# ============================================================================

version_strategy = st.integers(min_value=0, max_value=10_000)
resource_id_strategy = st.uuids().map(str)
resource_type_strategy = st.sampled_from([
    "TempDataModel", "SampleModel", "AnnotationTaskModel",
    "EnhancedDataModel", "VersionModel",
])


# ============================================================================
# Property 31: Concurrent Modification Detection
# **Validates: Requirements 22.1, 22.2, 22.3**
# ============================================================================


@pytest.mark.property
class TestConcurrentModificationDetection:
    """
    Property 31: Concurrent Modification Detection

    Verifies that optimistic locking correctly detects version conflicts,
    increments versions on success, retries exhaust properly, and conflict
    detail payloads contain all required fields.
    """

    # ------------------------------------------------------------------ #
    # Sub-property 1: Version mismatch always raises
    # ------------------------------------------------------------------ #

    @given(
        actual_version=version_strategy,
        expected_version=version_strategy,
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_version_mismatch_always_raises(
        self,
        actual_version: int,
        expected_version: int,
    ):
        """
        For any model with lock_version, if expected_version != actual
        lock_version, ConcurrentModificationError is always raised.

        **Validates: Requirements 22.1**
        """
        if actual_version == expected_version:
            # Only test the mismatch case
            return

        db = MagicMock()
        manager = OptimisticLockManager(db)
        model = FakeModel(lock_version=actual_version)

        with pytest.raises(ConcurrentModificationError) as exc_info:
            manager.check_and_increment_version(model, expected_version)

        err = exc_info.value
        assert err.expected_version == expected_version
        assert err.actual_version == actual_version

    # ------------------------------------------------------------------ #
    # Sub-property 2: Version match always increments by exactly 1
    # ------------------------------------------------------------------ #

    @given(version=version_strategy)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_version_match_increments_by_one(self, version: int):
        """
        For any model with lock_version, if expected_version == actual
        lock_version, version is always incremented by exactly 1.

        **Validates: Requirements 22.1**
        """
        db = MagicMock()
        manager = OptimisticLockManager(db)
        model = FakeModel(lock_version=version)

        manager.check_and_increment_version(model, version)

        assert model.lock_version == version + 1, (
            f"Expected lock_version to be {version + 1}, "
            f"got {model.lock_version}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 3: retry_on_conflict raises after max_retries
    # ------------------------------------------------------------------ #

    @given(max_retries=st.integers(min_value=0, max_value=5))
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_retry_exhaustion_always_raises(self, max_retries: int):
        """
        retry_on_conflict always eventually raises if the conflict
        persists beyond max_retries.

        **Validates: Requirements 22.3**
        """
        call_count = 0

        def always_conflict():
            nonlocal call_count
            call_count += 1
            raise ConcurrentModificationError(
                resource_id="res-1",
                resource_type="TestModel",
                expected_version=1,
                actual_version=2,
            )

        with pytest.raises(ConcurrentModificationError):
            retry_on_conflict(
                always_conflict,
                max_retries=max_retries,
                base_delay=0.0,
            )

        # Should have been called exactly max_retries + 1 times
        # (1 initial + max_retries retries)
        assert call_count == max_retries + 1, (
            f"Expected {max_retries + 1} calls, got {call_count}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 4: to_conflict_detail contains all required fields
    # ------------------------------------------------------------------ #

    @given(
        resource_id=resource_id_strategy,
        resource_type=resource_type_strategy,
        expected_version=version_strategy,
        actual_version=version_strategy,
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_conflict_detail_contains_all_fields(
        self,
        resource_id: str,
        resource_type: str,
        expected_version: int,
        actual_version: int,
    ):
        """
        ConcurrentModificationError.to_conflict_detail() always contains
        all required fields: error, message, resource_id, resource_type,
        expected_version, actual_version.

        **Validates: Requirements 22.2**
        """
        err = ConcurrentModificationError(
            resource_id=resource_id,
            resource_type=resource_type,
            expected_version=expected_version,
            actual_version=actual_version,
        )

        detail = err.to_conflict_detail()

        required_keys = {
            "error",
            "message",
            "resource_id",
            "resource_type",
            "expected_version",
            "actual_version",
        }
        assert required_keys.issubset(detail.keys()), (
            f"Missing keys: {required_keys - detail.keys()}"
        )

        # Values must match what was passed in
        assert detail["error"] == "conflict"
        assert detail["resource_id"] == resource_id
        assert detail["resource_type"] == resource_type
        assert detail["expected_version"] == expected_version
        assert detail["actual_version"] == actual_version
        assert isinstance(detail["message"], str)
        assert len(detail["message"]) > 0
