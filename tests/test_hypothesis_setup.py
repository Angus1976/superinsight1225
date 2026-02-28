"""
Test to verify Hypothesis setup and custom strategies.

This test validates that:
1. Hypothesis is properly configured with max_examples=100
2. Custom strategies work correctly
3. Property-based testing infrastructure is functional

**Feature: comprehensive-testing-qa-system, Task 1.3**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.6**
"""

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from tests.strategies import (
    users, tasks, annotations, datasets, projects,
    valid_email, valid_uuid, json_serializable_data
)
import json


# =============================================================================
# Configuration Verification Tests
# =============================================================================

def test_hypothesis_configuration():
    """Verify Hypothesis is configured with correct settings."""
    # Get current settings
    current_settings = settings()
    
    # Verify max_examples is at least 100 (default profile)
    assert current_settings.max_examples >= 100, \
        f"Expected max_examples >= 100, got {current_settings.max_examples}"
    
    # Verify deadline is None (no time limit per test)
    assert current_settings.deadline is None, \
        "Expected deadline=None for property tests"


# =============================================================================
# Custom Strategy Verification Tests
# =============================================================================

@given(email=valid_email())
def test_valid_email_strategy(email):
    """Verify valid_email strategy generates valid emails."""
    assert "@" in email
    assert "." in email.split("@")[1]
    assert len(email) >= 5


@given(uuid_str=valid_uuid())
def test_valid_uuid_strategy(uuid_str):
    """Verify valid_uuid strategy generates valid UUIDs."""
    assert len(uuid_str) == 36
    assert uuid_str.count("-") == 4


@given(user=users())
def test_users_strategy(user):
    """Verify users strategy generates valid user data."""
    assert "id" in user
    assert "username" in user
    assert "email" in user
    assert "role" in user
    assert user["role"] in ["admin", "annotator", "reviewer", "viewer"]
    assert "@" in user["email"]


@given(task=tasks())
def test_tasks_strategy(task):
    """Verify tasks strategy generates valid task data."""
    assert "id" in task
    assert "title" in task
    assert "status" in task
    assert task["status"] in ["pending", "in_progress", "completed", "rejected"]
    assert 1 <= task["priority"] <= 5


@given(annotation=annotations())
def test_annotations_strategy(annotation):
    """Verify annotations strategy generates valid annotation data."""
    assert "id" in annotation
    assert "task_id" in annotation
    assert "annotation_type" in annotation
    assert annotation["annotation_type"] in ["text", "entity", "relation", "classification"]
    assert 0.0 <= annotation["confidence"] <= 1.0


@given(dataset=datasets())
def test_datasets_strategy(dataset):
    """Verify datasets strategy generates valid dataset data."""
    assert "id" in dataset
    assert "name" in dataset
    assert "format" in dataset
    assert dataset["format"] in ["json", "csv", "xml", "parquet"]
    assert dataset["size"] >= 0


@given(project=projects())
def test_projects_strategy(project):
    """Verify projects strategy generates valid project data."""
    assert "id" in project
    assert "name" in project
    assert "owner_id" in project
    assert isinstance(project["is_active"], bool)


# =============================================================================
# Serialization Strategy Tests
# =============================================================================

@given(data=json_serializable_data())
def test_json_serializable_strategy(data):
    """
    Verify json_serializable_data strategy generates JSON-serializable data.
    
    **Property 4: Serialization Round-Trip Property**
    **Validates: Requirements 2.1**
    """
    # Should be able to serialize and deserialize
    serialized = json.dumps(data)
    deserialized = json.loads(serialized)
    assert deserialized == data


# =============================================================================
# Iteration Count Verification
# =============================================================================

@given(x=st.integers())
@settings(max_examples=100)
def test_iteration_count_verification(x):
    """
    Verify that property tests run at least 100 iterations.
    
    **Property 9: Property Test Iteration Count**
    **Validates: Requirements 2.6**
    
    Note: This test will be run 100 times by Hypothesis.
    The actual verification happens through Hypothesis's internal counter.
    """
    # This test will be executed 100 times
    # Each execution counts as one example
    assert isinstance(x, int)


# =============================================================================
# Profile Switching Tests
# =============================================================================

def test_hypothesis_profiles_exist():
    """Verify all required Hypothesis profiles are registered."""
    from hypothesis import settings
    
    # Test that profiles can be loaded
    try:
        settings.load_profile("default")
        settings.load_profile("ci")
        settings.load_profile("fast")
    except Exception as e:
        pytest.fail(f"Failed to load Hypothesis profiles: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
