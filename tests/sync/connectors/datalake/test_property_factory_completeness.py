"""
Property-based tests for Connector Factory Completeness.

Tests Property 1: Connector factory completeness
**Validates: Requirements 1.1, 1.2, 1.4**

For any data source type in DATALAKE_TYPES and any valid configuration
for that type, ConnectorFactory.create() should return a connector instance
of the correct class that exposes test_connection, fetch_databases,
fetch_tables, fetch_table_preview, and execute_query methods.
"""

import pytest
from hypothesis import given, settings, strategies as st

from src.sync.connectors.base import ConnectorFactory
from src.sync.connectors.datalake.base import DatalakeBaseConnector
from src.sync.models import DATALAKE_TYPES, DataSourceType


# ============================================================================
# Constants
# ============================================================================

# The 7 datalake/warehouse type values that must be registered
DATALAKE_TYPE_VALUES = [dt.value for dt in DATALAKE_TYPES]

# Required methods that every datalake connector must expose
REQUIRED_METHODS = [
    "test_connection",
    "fetch_databases",
    "fetch_tables",
    "fetch_table_preview",
    "execute_query",
]


# ============================================================================
# Strategies
# ============================================================================

def datalake_type_strategy():
    """Strategy that generates any datalake type value."""
    return st.sampled_from(DATALAKE_TYPE_VALUES)


def valid_config_strategy():
    """Strategy that generates valid datalake connector config dicts.

    Produces configs with randomized but valid connection parameters.
    ConnectorConfig requires a `name` field.
    """
    return st.fixed_dictionaries({
        "name": st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True),
        "host": st.from_regex(r"[a-z][a-z0-9\-]{0,19}\.[a-z]{2,4}", fullmatch=True),
        "port": st.integers(min_value=1, max_value=65535),
        "database": st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True),
        "username": st.from_regex(r"[a-z][a-z0-9_]{0,9}", fullmatch=True),
        "password": st.text(min_size=1, max_size=30),
        "use_ssl": st.booleans(),
        "query_timeout": st.integers(min_value=1, max_value=3600),
        "max_query_rows": st.integers(min_value=1, max_value=1000000),
    })


# ============================================================================
# Property 1: Connector factory completeness
# **Validates: Requirements 1.1, 1.2, 1.4**
# ============================================================================

class TestConnectorFactoryCompleteness:
    """Property 1: Connector factory completeness."""

    def test_all_datalake_types_registered(self):
        """Every type in DATALAKE_TYPES must be registered in ConnectorFactory.

        **Validates: Requirements 1.1**
        """
        registered = ConnectorFactory.list_types()
        for dt_value in DATALAKE_TYPE_VALUES:
            assert dt_value in registered, (
                f"Datalake type '{dt_value}' is not registered in ConnectorFactory. "
                f"Registered types: {registered}"
            )

    @settings(max_examples=50)
    @given(
        source_type=datalake_type_strategy(),
        config=valid_config_strategy(),
    )
    def test_factory_creates_datalake_connector(self, source_type, config):
        """For any datalake type and valid config, factory returns a
        DatalakeBaseConnector instance.

        **Validates: Requirements 1.1, 1.2**
        """
        connector = ConnectorFactory.create(source_type, config)
        assert isinstance(connector, DatalakeBaseConnector), (
            f"ConnectorFactory.create('{source_type}', ...) returned "
            f"{type(connector).__name__}, expected DatalakeBaseConnector subclass"
        )

    @settings(max_examples=50)
    @given(
        source_type=datalake_type_strategy(),
        config=valid_config_strategy(),
    )
    def test_connector_exposes_required_methods(self, source_type, config):
        """For any datalake type and valid config, the created connector
        exposes all required methods.

        **Validates: Requirements 1.4**
        """
        connector = ConnectorFactory.create(source_type, config)
        for method_name in REQUIRED_METHODS:
            assert hasattr(connector, method_name), (
                f"Connector for '{source_type}' missing method '{method_name}'"
            )
            assert callable(getattr(connector, method_name)), (
                f"'{method_name}' on connector for '{source_type}' is not callable"
            )

    @settings(max_examples=50)
    @given(
        source_type=datalake_type_strategy(),
        config=valid_config_strategy(),
    )
    def test_connector_methods_are_async(self, source_type, config):
        """All required methods should be coroutine functions (async).

        **Validates: Requirements 1.4**
        """
        import asyncio

        connector = ConnectorFactory.create(source_type, config)
        for method_name in REQUIRED_METHODS:
            method = getattr(connector, method_name)
            assert asyncio.iscoroutinefunction(method), (
                f"'{method_name}' on connector for '{source_type}' "
                f"should be async but is not"
            )
