"""
Property-based tests for Data Sync Pipeline Connectors.

Tests Property 1: Read-only connection verification
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, MagicMock, patch

from src.sync.pipeline.enums import DatabaseType, ConnectionMethod
from src.sync.pipeline.schemas import DataSourceConfig
from src.sync.pipeline.connectors.base import (
    BaseConnector,
    ConnectorFactory,
    ReadOnlyViolationError,
)


# ============================================================================
# Test Helpers
# ============================================================================

def create_sample_config():
    """Create a sample data source configuration."""
    return DataSourceConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="test_db",
        username="test_user",
        password="test_pass",
        connection_method=ConnectionMethod.JDBC,
        readonly=True
    )


# ============================================================================
# Property 1: Read-only Connection Verification
# Validates: Requirements 1.2
# ============================================================================

# Write operation keywords that should be blocked
WRITE_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE"
]


class MockConnector(BaseConnector):
    """Mock connector for testing read-only validation."""
    
    async def connect(self):
        self._is_connected = True
    
    async def disconnect(self):
        self._is_connected = False
    
    async def execute_query(self, query, params=None):
        self._validate_readonly_query(query)
        return []
    
    async def execute_query_paginated(self, query, page_size=1000, params=None):
        self._validate_readonly_query(query)
        yield
    
    async def get_table_columns(self, table_name):
        return []
    
    async def get_row_count(self, table_name):
        return 0
    
    async def test_connection(self):
        return True


@settings(max_examples=100)
@given(
    keyword=st.sampled_from(WRITE_KEYWORDS),
    table_name=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz_",
        min_size=1,
        max_size=20
    )
)
def test_readonly_blocks_write_operations(keyword, table_name):
    """
    Property 1: Read-only connection verification
    
    For any write operation keyword, the connector should raise
    ReadOnlyViolationError when attempting to execute the query.
    
    **Validates: Requirements 1.2**
    """
    sample_config = create_sample_config()
    connector = MockConnector(sample_config)
    
    # Construct a write query
    if keyword in ["INSERT"]:
        query = f"{keyword} INTO {table_name} VALUES (1)"
    elif keyword in ["UPDATE"]:
        query = f"{keyword} {table_name} SET col = 1"
    elif keyword in ["DELETE"]:
        query = f"{keyword} FROM {table_name}"
    elif keyword in ["DROP", "TRUNCATE"]:
        query = f"{keyword} TABLE {table_name}"
    elif keyword in ["CREATE"]:
        query = f"{keyword} TABLE {table_name} (id INT)"
    elif keyword in ["ALTER"]:
        query = f"{keyword} TABLE {table_name} ADD col INT"
    elif keyword in ["GRANT", "REVOKE"]:
        query = f"{keyword} SELECT ON {table_name} TO user"
    elif keyword in ["REPLACE"]:
        query = f"{keyword} INTO {table_name} VALUES (1)"
    elif keyword in ["MERGE"]:
        query = f"{keyword} INTO {table_name} USING source ON (1=1)"
    else:
        query = f"{keyword} {table_name}"
    
    # Should raise ReadOnlyViolationError
    with pytest.raises(ReadOnlyViolationError):
        connector._validate_readonly_query(query)


@settings(max_examples=100)
@given(
    table_name=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz_",
        min_size=1,
        max_size=20
    ),
    columns=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz_,",
        min_size=1,
        max_size=50
    )
)
def test_readonly_allows_select_operations(table_name, columns):
    """
    Property 1 (inverse): Read-only connection allows SELECT
    
    For any SELECT query, the connector should not raise an error.
    
    **Validates: Requirements 1.2**
    """
    sample_config = create_sample_config()
    connector = MockConnector(sample_config)
    
    # Construct a SELECT query
    query = f"SELECT {columns} FROM {table_name}"
    
    # Should not raise any error
    connector._validate_readonly_query(query)


@settings(max_examples=100)
@given(
    keyword=st.sampled_from(WRITE_KEYWORDS),
    prefix_spaces=st.integers(min_value=0, max_value=5)
)
def test_readonly_handles_whitespace(keyword, prefix_spaces):
    """
    Property 1 (edge case): Read-only validation handles whitespace
    
    Write operations should be blocked even with leading whitespace.
    
    **Validates: Requirements 1.2**
    """
    sample_config = create_sample_config()
    connector = MockConnector(sample_config)
    
    # Query with leading whitespace
    query = " " * prefix_spaces + f"{keyword} table_name"
    
    # Should raise ReadOnlyViolationError
    with pytest.raises(ReadOnlyViolationError):
        connector._validate_readonly_query(query)


@settings(max_examples=100)
@given(
    keyword=st.sampled_from(WRITE_KEYWORDS)
)
def test_readonly_case_insensitive(keyword):
    """
    Property 1 (edge case): Read-only validation is case-insensitive
    
    Write operations should be blocked regardless of case.
    
    **Validates: Requirements 1.2**
    """
    sample_config = create_sample_config()
    connector = MockConnector(sample_config)
    
    # Test lowercase
    query_lower = f"{keyword.lower()} table_name"
    with pytest.raises(ReadOnlyViolationError):
        connector._validate_readonly_query(query_lower)
    
    # Test mixed case
    query_mixed = f"{keyword.capitalize()} table_name"
    with pytest.raises(ReadOnlyViolationError):
        connector._validate_readonly_query(query_mixed)


# ============================================================================
# Connector Factory Tests
# ============================================================================

def test_connector_factory_registration():
    """Test that connectors can be registered and created."""
    # Register mock connector
    ConnectorFactory.register(DatabaseType.POSTGRESQL, MockConnector)
    
    config = DataSourceConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="test",
        username="user",
        password="pass"
    )
    
    connector = ConnectorFactory.create(config)
    assert isinstance(connector, MockConnector)


def test_connector_factory_unsupported_type():
    """Test that unsupported database types raise ValueError."""
    # Create config with a type that might not be registered
    config = DataSourceConfig(
        db_type=DatabaseType.ORACLE,
        host="localhost",
        port=1521,
        database="test",
        username="user",
        password="pass"
    )
    
    # Clear registrations for this test
    original = ConnectorFactory._connectors.copy()
    ConnectorFactory._connectors.clear()
    
    try:
        with pytest.raises(ValueError):
            ConnectorFactory.create(config)
    finally:
        # Restore registrations
        ConnectorFactory._connectors = original


def test_connector_factory_get_supported_types():
    """Test getting list of supported database types."""
    # Register a connector
    ConnectorFactory.register(DatabaseType.SQLITE, MockConnector)
    
    supported = ConnectorFactory.get_supported_types()
    assert DatabaseType.SQLITE in supported
