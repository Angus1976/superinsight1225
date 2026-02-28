"""
Custom Hypothesis strategies for SuperInsight domain models.

This module provides reusable strategies for generating test data
for property-based testing with Hypothesis.

Usage:
    from tests.strategies import users, tasks, annotations
    
    @given(user=users())
    def test_user_property(user):
        assert user.email is not None
"""

from hypothesis import strategies as st
from datetime import datetime, timedelta
from typing import Optional
import uuid


# =============================================================================
# Basic Strategies
# =============================================================================

def valid_email() -> st.SearchStrategy[str]:
    """Generate valid email addresses."""
    username = st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=3,
        max_size=20
    )
    domain = st.text(
        alphabet=st.characters(whitelist_categories=("Ll",)),
        min_size=3,
        max_size=15
    )
    tld = st.sampled_from(["com", "org", "net", "edu", "io"])
    
    return st.builds(
        lambda u, d, t: f"{u}@{d}.{t}",
        username, domain, tld
    )


def valid_username() -> st.SearchStrategy[str]:
    """Generate valid usernames (alphanumeric, 3-30 chars)."""
    return st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_-"),
        min_size=3,
        max_size=30
    ).filter(lambda x: x[0].isalpha())


def valid_uuid() -> st.SearchStrategy[str]:
    """Generate valid UUID strings."""
    return st.builds(lambda: str(uuid.uuid4()))


def past_datetime(days_ago: int = 365) -> st.SearchStrategy[datetime]:
    """Generate datetime in the past (fixed reference point for consistency)."""
    # Use fixed reference point to avoid flaky tests
    reference = datetime(2024, 1, 1, 0, 0, 0)
    start = reference - timedelta(days=days_ago)
    return st.datetimes(min_value=start, max_value=reference)


def future_datetime(days_ahead: int = 365) -> st.SearchStrategy[datetime]:
    """Generate datetime in the future (fixed reference point for consistency)."""
    # Use fixed reference point to avoid flaky tests
    reference = datetime(2024, 1, 1, 0, 0, 0)
    end = reference + timedelta(days=days_ahead)
    return st.datetimes(min_value=reference, max_value=end)


# =============================================================================
# User Strategies
# =============================================================================

@st.composite
def users(draw, role: Optional[str] = None, is_active: Optional[bool] = None):
    """
    Generate user data for testing.
    
    Args:
        role: Optional fixed role (admin, annotator, reviewer)
        is_active: Optional fixed active status
    """
    roles = ["admin", "annotator", "reviewer", "viewer"]
    
    return {
        "id": draw(valid_uuid()),
        "username": draw(valid_username()),
        "email": draw(valid_email()),
        "role": role if role is not None else draw(st.sampled_from(roles)),
        "is_active": is_active if is_active is not None else draw(st.booleans()),
        "created_at": draw(past_datetime(180)),
        "updated_at": draw(past_datetime(30)),
    }


# =============================================================================
# Task Strategies
# =============================================================================

@st.composite
def tasks(draw, status: Optional[str] = None):
    """
    Generate task data for testing.
    
    Args:
        status: Optional fixed status (pending, in_progress, completed, rejected)
    """
    statuses = ["pending", "in_progress", "completed", "rejected"]
    
    return {
        "id": draw(valid_uuid()),
        "title": draw(st.text(min_size=5, max_size=100)),
        "description": draw(st.text(min_size=10, max_size=500)),
        "status": status if status is not None else draw(st.sampled_from(statuses)),
        "priority": draw(st.integers(min_value=1, max_value=5)),
        "assigned_to": draw(valid_uuid()),
        "created_by": draw(valid_uuid()),
        "created_at": draw(past_datetime(90)),
        "updated_at": draw(past_datetime(30)),
        "due_date": draw(future_datetime(90)),
    }


# =============================================================================
# Annotation Strategies
# =============================================================================

@st.composite
def annotations(draw, annotation_type: Optional[str] = None):
    """
    Generate annotation data for testing.
    
    Args:
        annotation_type: Optional fixed type (text, entity, relation, classification)
    """
    types = ["text", "entity", "relation", "classification"]
    
    return {
        "id": draw(valid_uuid()),
        "task_id": draw(valid_uuid()),
        "annotator_id": draw(valid_uuid()),
        "annotation_type": annotation_type if annotation_type is not None else draw(st.sampled_from(types)),
        "data": draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(), st.integers(), st.floats(allow_nan=False), st.booleans())
        )),
        "confidence": draw(st.floats(min_value=0.0, max_value=1.0)),
        "created_at": draw(past_datetime(60)),
        "updated_at": draw(past_datetime(30)),
    }


# =============================================================================
# Dataset Strategies
# =============================================================================

@st.composite
def datasets(draw):
    """Generate dataset data for testing."""
    return {
        "id": draw(valid_uuid()),
        "name": draw(st.text(min_size=3, max_size=50)),
        "description": draw(st.text(min_size=10, max_size=200)),
        "size": draw(st.integers(min_value=0, max_value=1000000)),
        "format": draw(st.sampled_from(["json", "csv", "xml", "parquet"])),
        "created_by": draw(valid_uuid()),
        "created_at": draw(past_datetime(180)),
        "updated_at": draw(past_datetime(30)),
    }


# =============================================================================
# Project Strategies
# =============================================================================

@st.composite
def projects(draw):
    """Generate project data for testing."""
    return {
        "id": draw(valid_uuid()),
        "name": draw(st.text(min_size=3, max_size=50)),
        "description": draw(st.text(min_size=10, max_size=300)),
        "owner_id": draw(valid_uuid()),
        "is_active": draw(st.booleans()),
        "created_at": draw(past_datetime(365)),
        "updated_at": draw(past_datetime(30)),
    }


# =============================================================================
# Serialization Test Strategies
# =============================================================================

@st.composite
def json_serializable_data(draw):
    """
    Generate JSON-serializable data structures for round-trip testing.
    
    Supports nested structures with strings, numbers, booleans, lists, and dicts.
    """
    return draw(st.recursive(
        st.one_of(
            st.none(),
            st.booleans(),
            st.integers(min_value=-1000000, max_value=1000000),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(max_size=100),
        ),
        lambda children: st.one_of(
            st.lists(children, max_size=10),
            st.dictionaries(
                st.text(min_size=1, max_size=20),
                children,
                max_size=10
            )
        ),
        max_leaves=20
    ))


# =============================================================================
# Validation Strategies
# =============================================================================

def invalid_emails() -> st.SearchStrategy[str]:
    """Generate invalid email addresses for error testing."""
    return st.one_of(
        st.text(max_size=50).filter(lambda x: "@" not in x),  # No @ symbol
        st.builds(lambda x: f"{x}@", st.text(min_size=1, max_size=20)),  # No domain
        st.builds(lambda x: f"@{x}", st.text(min_size=1, max_size=20)),  # No username
        st.just(""),  # Empty string
        st.just("invalid..email@test.com"),  # Double dots
    )


def invalid_uuids() -> st.SearchStrategy[str]:
    """Generate invalid UUID strings for error testing."""
    return st.one_of(
        st.text(max_size=20).filter(lambda x: len(x) != 36),  # Wrong length
        st.just("not-a-uuid"),
        st.just(""),
        st.just("12345678-1234-1234-1234-12345678901"),  # Too short
    )


# =============================================================================
# Metamorphic Testing Strategies
# =============================================================================

@st.composite
def operation_pairs(draw, operation_type: str = "commutative"):
    """
    Generate pairs of operations for metamorphic testing.
    
    Args:
        operation_type: Type of metamorphic relationship
            - "commutative": Operations that should produce same result regardless of order
            - "associative": Operations that should be associative
            - "idempotent": Operations that should be idempotent
    """
    if operation_type == "commutative":
        op1 = draw(st.sampled_from(["add", "multiply", "union", "intersection"]))
        op2 = op1
        return (op1, op2)
    elif operation_type == "associative":
        op = draw(st.sampled_from(["add", "multiply", "concat"]))
        return (op, op, op)
    elif operation_type == "idempotent":
        op = draw(st.sampled_from(["normalize", "deduplicate", "sort"]))
        return (op, op)
    else:
        raise ValueError(f"Unknown operation_type: {operation_type}")
