"""
Property-based tests for Data Source Validation Round-Trip.

Tests Property 3: Data source validation round-trip
**Validates: Requirements 2.1, 2.2**

For any valid DatalakeSourceCreate payload, creating a data source via the API
and then retrieving it should return an equivalent record. For any invalid
payload (missing required fields or wrong format), the API should return a
422 error.

This is a schema-level test — validates Pydantic serialization/deserialization
round-trip without API calls.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from src.sync.connectors.datalake.schemas import (
    DatalakeSourceCreate,
    DatalakeSourceResponse,
    DatalakeSourceUpdate,
)
from src.sync.models import (
    DATALAKE_TYPES,
    DataSourceStatus,
    DataSourceType,
)


# ============================================================================
# Constants
# ============================================================================

DATALAKE_TYPE_LIST = list(DATALAKE_TYPES)

NON_DATALAKE_TYPES = [t for t in DataSourceType if t not in DATALAKE_TYPES]


# ============================================================================
# Strategies
# ============================================================================

def datalake_type_strategy():
    """Strategy that generates a valid datalake DataSourceType."""
    return st.sampled_from(DATALAKE_TYPE_LIST)


def non_datalake_type_strategy():
    """Strategy that generates a non-datalake DataSourceType."""
    return st.sampled_from(NON_DATALAKE_TYPES)


def valid_name_strategy():
    """Strategy that generates valid source names (1-200 chars, non-empty)."""
    return st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N", "P", "Z"),
            blacklist_characters="\x00",
        ),
        min_size=1,
        max_size=200,
    ).filter(lambda s: s.strip())


def connection_config_strategy():
    """Strategy that generates plausible connection config dicts."""
    return st.fixed_dictionaries({
        "host": st.from_regex(r"[a-z][a-z0-9\-]{0,19}\.[a-z]{2,4}", fullmatch=True),
        "port": st.integers(min_value=1, max_value=65535),
        "database": st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True),
        "username": st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True),
        "password": st.text(min_size=1, max_size=30),
    })


def valid_create_payload_strategy():
    """Strategy that generates a complete valid DatalakeSourceCreate dict."""
    return st.fixed_dictionaries({
        "name": valid_name_strategy(),
        "source_type": datalake_type_strategy(),
        "connection_config": connection_config_strategy(),
        "description": st.one_of(st.none(), st.text(min_size=0, max_size=100)),
    })


# ============================================================================
# Property 3: Data source validation round-trip
# **Validates: Requirements 2.1, 2.2**
# ============================================================================

class TestValidPayloadRoundTrip:
    """Valid DatalakeSourceCreate payloads survive serialization round-trip."""

    @settings(max_examples=100)
    @given(payload=valid_create_payload_strategy())
    def test_create_serialize_deserialize_roundtrip(self, payload):
        """For any valid payload, DatalakeSourceCreate can be constructed,
        serialized to dict, and deserialized back without data loss.

        **Validates: Requirements 2.1, 2.2**
        """
        # Create model from payload
        model = DatalakeSourceCreate(**payload)

        # Serialize to dict
        serialized = model.model_dump()

        # Deserialize back
        restored = DatalakeSourceCreate(**serialized)

        # Round-trip must preserve all fields
        assert restored.name == model.name
        assert restored.source_type == model.source_type
        assert restored.connection_config == model.connection_config
        assert restored.description == model.description

    @settings(max_examples=50)
    @given(payload=valid_create_payload_strategy())
    def test_create_json_roundtrip(self, payload):
        """For any valid payload, JSON serialization round-trip preserves data.

        **Validates: Requirements 2.1, 2.2**
        """
        model = DatalakeSourceCreate(**payload)

        # Serialize to JSON string and back
        json_str = model.model_dump_json()
        restored = DatalakeSourceCreate.model_validate_json(json_str)

        assert restored.name == model.name
        assert restored.source_type == model.source_type
        assert restored.connection_config == model.connection_config
        assert restored.description == model.description

    @settings(max_examples=50)
    @given(
        payload=valid_create_payload_strategy(),
        status=st.sampled_from(list(DataSourceStatus)),
    )
    def test_response_from_create_data(self, payload, status):
        """A DatalakeSourceResponse can be constructed from valid create data
        plus server-generated fields (id, status, created_at).

        **Validates: Requirements 2.1**
        """
        create_model = DatalakeSourceCreate(**payload)

        response = DatalakeSourceResponse(
            id=uuid4(),
            name=create_model.name,
            source_type=create_model.source_type,
            status=status,
            created_at=datetime.now(timezone.utc),
        )

        assert response.name == create_model.name
        assert response.source_type == create_model.source_type


class TestSourceTypeValidatorRejectsNonDatalake:
    """The source_type validator rejects non-datalake types."""

    @settings(max_examples=50)
    @given(
        bad_type=non_datalake_type_strategy(),
        config=connection_config_strategy(),
    )
    def test_non_datalake_type_raises_validation_error(self, bad_type, config):
        """For any non-datalake DataSourceType, DatalakeSourceCreate raises
        ValidationError.

        **Validates: Requirement 2.2**
        """
        with pytest.raises(ValidationError) as exc_info:
            DatalakeSourceCreate(
                name="test-source",
                source_type=bad_type,
                connection_config=config,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source_type",) for e in errors)


class TestInvalidPayloadRejection:
    """Invalid payloads (missing required fields, wrong format) raise
    ValidationError — equivalent to API returning 422."""

    def test_empty_name_rejected(self):
        """Empty name string violates min_length=1 constraint.

        **Validates: Requirement 2.2**
        """
        with pytest.raises(ValidationError):
            DatalakeSourceCreate(
                name="",
                source_type=DataSourceType.CLICKHOUSE,
                connection_config={"host": "localhost"},
            )

    def test_missing_name_rejected(self):
        """Missing required 'name' field raises ValidationError.

        **Validates: Requirement 2.2**
        """
        with pytest.raises(ValidationError):
            DatalakeSourceCreate(
                source_type=DataSourceType.HIVE,
                connection_config={"host": "localhost"},
            )

    def test_missing_source_type_rejected(self):
        """Missing required 'source_type' field raises ValidationError.

        **Validates: Requirement 2.2**
        """
        with pytest.raises(ValidationError):
            DatalakeSourceCreate(
                name="test",
                connection_config={"host": "localhost"},
            )

    def test_missing_connection_config_rejected(self):
        """Missing required 'connection_config' field raises ValidationError.

        **Validates: Requirement 2.2**
        """
        with pytest.raises(ValidationError):
            DatalakeSourceCreate(
                name="test",
                source_type=DataSourceType.DORIS,
            )

    def test_name_exceeding_max_length_rejected(self):
        """Name exceeding 200 characters raises ValidationError.

        **Validates: Requirement 2.2**
        """
        with pytest.raises(ValidationError):
            DatalakeSourceCreate(
                name="x" * 201,
                source_type=DataSourceType.ICEBERG,
                connection_config={"host": "localhost"},
            )
