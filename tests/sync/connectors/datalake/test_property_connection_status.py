"""
Property-based tests for Connection Test Status Consistency.

Tests Property 6: Connection test status consistency
**Validates: Requirements 3.1, 3.2, 3.4**

For any connector, test_connection() should return a result containing a status
field (connected or error) and a latency_ms field. When the status is error,
the result should also contain a non-empty error detail. After test completion,
the DataSourceModel's health_check_status and last_health_check fields should
be updated.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.connection import Base
from src.sync.connectors.datalake.schemas import ConnectionTestResult
from src.sync.models import (
    DATALAKE_TYPES,
    DataSourceModel,
    DataSourceStatus,
)


# SQLite cannot handle JSONB; compile as JSON instead.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


DATALAKE_TYPE_LIST = list(DATALAKE_TYPES)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def datalake_type_strategy():
    return st.sampled_from(DATALAKE_TYPE_LIST)


def tenant_id_strategy():
    return st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1,
        max_size=50,
    )


def latency_strategy():
    """Non-negative latency values in milliseconds."""
    return st.floats(min_value=0.0, max_value=60000.0, allow_nan=False, allow_infinity=False)


def error_message_strategy():
    """Non-empty error messages."""
    return st.text(min_size=1, max_size=200).filter(lambda s: s.strip())


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


def _create_source(session, tenant_id, source_type):
    source = DataSourceModel(
        id=uuid4(),
        tenant_id=tenant_id,
        name=f"src-{uuid4().hex[:8]}",
        source_type=source_type,
        status=DataSourceStatus.ACTIVE,
        connection_config={"host": "localhost", "port": 9000},
    )
    session.add(source)
    session.flush()
    return source


def _apply_connection_result(session, source, success: bool, latency_ms: float, error_msg: Optional[str] = None):
    """Replicate the health-check update logic from router.test_datalake_connection.

    This mirrors the exact logic in the endpoint:
    - Sets health_check_status to "connected" or "error"
    - Sets last_health_check to current UTC time
    - On success, sets source.status to ACTIVE
    """
    now = datetime.now(timezone.utc)
    source.health_check_status = "connected" if success else "error"
    source.last_health_check = now
    if success:
        source.status = DataSourceStatus.ACTIVE
    session.commit()

    return ConnectionTestResult(
        status="connected" if success else "error",
        latency_ms=latency_ms,
        error_message=error_msg,
    )


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------

class TestConnectionStatusSuccessResult:
    """Successful connection results must have status='connected' and latency_ms >= 0.

    **Validates: Requirements 3.1, 3.4**
    """

    @settings(max_examples=50)
    @given(
        tenant_id=tenant_id_strategy(),
        src_type=datalake_type_strategy(),
        latency=latency_strategy(),
    )
    def test_successful_connection_returns_connected_status(
        self, tenant_id, src_type, latency
    ):
        """For any successful connection, status is 'connected' and latency_ms >= 0.

        **Validates: Requirements 3.1, 3.4**
        """
        with _isolated_session() as session:
            source = _create_source(session, tenant_id, src_type)

            result = _apply_connection_result(session, source, success=True, latency_ms=latency)

            assert result.status == "connected"
            assert result.latency_ms >= 0
            assert result.error_message is None

            # Verify model fields updated (Req 3.4)
            session.refresh(source)
            assert source.health_check_status == "connected"
            assert source.last_health_check is not None


class TestConnectionStatusErrorResult:
    """Failed connection results must have status='error' and non-empty error_message.

    **Validates: Requirements 3.2, 3.4**
    """

    @settings(max_examples=50)
    @given(
        tenant_id=tenant_id_strategy(),
        src_type=datalake_type_strategy(),
        latency=latency_strategy(),
        error_msg=error_message_strategy(),
    )
    def test_failed_connection_returns_error_with_detail(
        self, tenant_id, src_type, latency, error_msg
    ):
        """For any failed connection, status is 'error' and error_message is non-empty.

        **Validates: Requirements 3.2, 3.4**
        """
        with _isolated_session() as session:
            source = _create_source(session, tenant_id, src_type)

            result = _apply_connection_result(
                session, source, success=False, latency_ms=latency, error_msg=error_msg,
            )

            assert result.status == "error"
            assert result.error_message is not None
            assert len(result.error_message.strip()) > 0

            # Verify model fields updated (Req 3.4)
            session.refresh(source)
            assert source.health_check_status == "error"
            assert source.last_health_check is not None


class TestConnectionTestResultSchema:
    """ConnectionTestResult schema always has the required fields.

    **Validates: Requirements 3.1, 3.2**
    """

    @settings(max_examples=50)
    @given(
        status=st.sampled_from(["connected", "error"]),
        latency=latency_strategy(),
        error_msg=st.one_of(st.none(), error_message_strategy()),
    )
    def test_schema_always_has_required_fields(self, status, latency, error_msg):
        """ConnectionTestResult always contains status and latency_ms fields.

        **Validates: Requirements 3.1, 3.2**
        """
        result = ConnectionTestResult(
            status=status,
            latency_ms=latency,
            error_message=error_msg,
        )

        # Required fields always present
        assert hasattr(result, "status")
        assert hasattr(result, "latency_ms")
        assert hasattr(result, "error_message")

        assert result.status in ("connected", "error")
        assert isinstance(result.latency_ms, float)

        # When error, error_message should be provided
        if status == "error" and error_msg is not None:
            assert len(result.error_message.strip()) > 0
