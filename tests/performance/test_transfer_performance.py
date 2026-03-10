"""
Performance tests for data transfer operations.

Tests cover:
- 1000 record transfer to all three target states
- Timing verification against the < 3 second requirement
- Permission check response time < 100ms

**Validates: Requirements 3.1**

Performance targets:
- Transfer 1000 records: < 3 seconds
- Permission check: < 100ms
"""

import pytest
import time
from typing import List
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.models.data_lifecycle import TempDataModel, SampleModel, TransferAuditLogModel
from src.models.data_transfer import (
    DataTransferRequest,
    DataAttributes,
    TransferRecord,
)
from src.services.data_transfer_service import DataTransferService, User
from src.services.permission_service import UserRole, PermissionService


# Performance targets from requirements 3.1
TRANSFER_1000_RECORDS_TARGET_S = 3.0
PERMISSION_CHECK_TARGET_MS = 100

# Only the tables required for transfer operations
_REQUIRED_TABLES = [
    TempDataModel.__table__,
    SampleModel.__table__,
    TransferAuditLogModel.__table__,
]


def _create_engine_and_tables():
    """Create in-memory SQLite engine with only the transfer-related tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in _REQUIRED_TABLES:
        table.create(bind=engine, checkfirst=True)
    return engine


def _build_records(count: int) -> List[TransferRecord]:
    """Generate a list of transfer records for benchmarking."""
    return [
        TransferRecord(
            id=f"perf-record-{i}",
            content={"field": f"value-{i}", "index": i},
            metadata={"batch": "perf-test"},
        )
        for i in range(count)
    ]


def _build_transfer_request(
    target_state: str,
    records: List[TransferRecord],
) -> DataTransferRequest:
    """Build a transfer request for the given target state."""
    return DataTransferRequest(
        source_type="structuring",
        source_id=f"perf-source-{uuid4().hex[:8]}",
        target_state=target_state,
        data_attributes=DataAttributes(
            category="performance_test",
            tags=["perf", "benchmark"],
            quality_score=0.9,
            description="Performance benchmark data",
        ),
        records=records,
    )


@pytest.fixture
def db_session() -> Session:
    """Provide an in-memory SQLite session for performance tests."""
    engine = _create_engine_and_tables()
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def admin_user() -> User:
    """Admin user — no approval required for any target state."""
    return User(id="perf-admin-1", role=UserRole.ADMIN)


@pytest.fixture
def transfer_service(db_session) -> DataTransferService:
    """DataTransferService wired to the in-memory database."""
    return DataTransferService(db=db_session)


@pytest.fixture
def records_1000() -> List[TransferRecord]:
    """Pre-built list of 1000 transfer records."""
    return _build_records(1000)


# =========================================================================
# Transfer Performance Tests — 1000 records, all three target states
# =========================================================================

@pytest.mark.performance
class TestTransfer1000Records:
    """Verify 1000-record transfers complete within the 3-second target."""

    @pytest.mark.asyncio
    async def test_transfer_1000_to_temp_stored(
        self, transfer_service, admin_user, records_1000
    ):
        """Transfer 1000 records to temp_stored in < 3 s."""
        request = _build_transfer_request("temp_stored", records_1000)

        start = time.perf_counter()
        result = await transfer_service.transfer(request, admin_user)
        elapsed = time.perf_counter() - start

        assert result["success"] is True
        assert result["transferred_count"] == 1000
        assert result["target_state"] == "temp_stored"
        assert elapsed < TRANSFER_1000_RECORDS_TARGET_S, (
            f"temp_stored transfer took {elapsed:.2f}s, target < {TRANSFER_1000_RECORDS_TARGET_S}s"
        )

    @pytest.mark.asyncio
    async def test_transfer_1000_to_sample_library(
        self, transfer_service, admin_user, records_1000
    ):
        """Transfer 1000 records to in_sample_library in < 3 s."""
        request = _build_transfer_request("in_sample_library", records_1000)

        start = time.perf_counter()
        result = await transfer_service.transfer(request, admin_user)
        elapsed = time.perf_counter() - start

        assert result["success"] is True
        assert result["transferred_count"] == 1000
        assert result["target_state"] == "in_sample_library"
        assert elapsed < TRANSFER_1000_RECORDS_TARGET_S, (
            f"in_sample_library transfer took {elapsed:.2f}s, target < {TRANSFER_1000_RECORDS_TARGET_S}s"
        )

    @pytest.mark.asyncio
    async def test_transfer_1000_to_annotation_pending(
        self, transfer_service, admin_user, records_1000
    ):
        """Transfer 1000 records to annotation_pending in < 3 s."""
        request = _build_transfer_request("annotation_pending", records_1000)

        start = time.perf_counter()
        result = await transfer_service.transfer(request, admin_user)
        elapsed = time.perf_counter() - start

        assert result["success"] is True
        assert result["transferred_count"] == 1000
        assert result["target_state"] == "annotation_pending"
        assert elapsed < TRANSFER_1000_RECORDS_TARGET_S, (
            f"annotation_pending transfer took {elapsed:.2f}s, target < {TRANSFER_1000_RECORDS_TARGET_S}s"
        )


# =========================================================================
# Permission Check Performance Test
# =========================================================================

@pytest.mark.performance
class TestPermissionCheckPerformance:
    """Verify permission checks respond within 100 ms."""

    def test_permission_check_under_100ms(self):
        """Run 1000 permission checks and verify average < 100 ms."""
        service = PermissionService()
        roles = list(UserRole)
        states = ["temp_stored", "in_sample_library", "annotation_pending"]

        start = time.perf_counter()
        iterations = 1000
        for i in range(iterations):
            role = roles[i % len(roles)]
            state = states[i % len(states)]
            service.check_permission(
                user_role=role,
                target_state=state,
                record_count=1,
            )
        elapsed_ms = (time.perf_counter() - start) * 1000

        avg_ms = elapsed_ms / iterations
        assert avg_ms < PERMISSION_CHECK_TARGET_MS, (
            f"Average permission check took {avg_ms:.2f}ms, target < {PERMISSION_CHECK_TARGET_MS}ms"
        )


# Performance target for 10000-record batch transfer (requirements 3.1)
TRANSFER_10000_RECORDS_TARGET_S = 30.0


@pytest.fixture
def records_10000() -> List[TransferRecord]:
    """Pre-built list of 10000 transfer records."""
    return _build_records(10000)


# =========================================================================
# Transfer Performance Tests — 10000 records, batch transfer
# =========================================================================

@pytest.mark.performance
class TestTransfer10000Records:
    """Verify 10000-record batch transfer completes within the 30-second target.

    **Validates: Requirements 3.1**
    """

    @pytest.mark.asyncio
    async def test_transfer_10000_to_temp_stored(
        self, transfer_service, admin_user, records_10000
    ):
        """Transfer 10000 records to temp_stored in < 30 s."""
        request = _build_transfer_request("temp_stored", records_10000)

        start = time.perf_counter()
        result = await transfer_service.transfer(request, admin_user)
        elapsed = time.perf_counter() - start

        assert result["success"] is True
        assert result["transferred_count"] == 10000
        assert result["target_state"] == "temp_stored"
        assert elapsed < TRANSFER_10000_RECORDS_TARGET_S, (
            f"temp_stored transfer took {elapsed:.2f}s, "
            f"target < {TRANSFER_10000_RECORDS_TARGET_S}s"
        )


# =========================================================================
# Concurrent Transfer Stress Tests
# =========================================================================

import asyncio

# Concurrency targets
CONCURRENT_5x100_TARGET_S = 10.0
CONCURRENT_10x50_TARGET_S = 10.0


@pytest.mark.performance
class TestConcurrentTransferStress:
    """Stress tests simulating multiple concurrent users transferring data.

    Each concurrent transfer uses its own DB session and service instance
    to avoid SQLAlchemy session conflicts, mirroring real multi-user usage.

    **Validates: Requirements 3.1**
    """

    @staticmethod
    def _create_session_and_service() -> tuple:
        """Create an independent DB session and transfer service."""
        engine = _create_engine_and_tables()
        session_factory = sessionmaker(bind=engine)
        session = session_factory()
        service = DataTransferService(db=session)
        return engine, session, service

    @staticmethod
    async def _run_transfer(
        service: DataTransferService,
        user: User,
        records: List[TransferRecord],
        target_state: str,
    ) -> dict:
        """Execute a single transfer and return the result."""
        request = _build_transfer_request(target_state, records)
        return await service.transfer(request, user)

    @pytest.mark.asyncio
    async def test_5_concurrent_transfers_of_100_records(self):
        """5 concurrent transfers of 100 records each complete successfully."""
        num_concurrent = 5
        records_per_transfer = 100
        target_states = [
            "temp_stored",
            "in_sample_library",
            "annotation_pending",
            "temp_stored",
            "in_sample_library",
        ]

        resources = []
        tasks = []
        for i in range(num_concurrent):
            engine, session, service = self._create_session_and_service()
            resources.append((engine, session))
            user = User(id=f"concurrent-user-{i}", role=UserRole.ADMIN)
            records = _build_records(records_per_transfer)
            tasks.append(
                self._run_transfer(service, user, records, target_states[i])
            )

        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        # Cleanup
        for engine, session in resources:
            session.close()
            engine.dispose()

        # Verify all transfers succeeded
        for idx, result in enumerate(results):
            assert result["success"] is True, (
                f"Transfer {idx} failed: {result}"
            )
            assert result["transferred_count"] == records_per_transfer

        total_transferred = sum(r["transferred_count"] for r in results)
        assert total_transferred == num_concurrent * records_per_transfer

        assert elapsed < CONCURRENT_5x100_TARGET_S, (
            f"5x100 concurrent transfers took {elapsed:.2f}s, "
            f"target < {CONCURRENT_5x100_TARGET_S}s"
        )

    @pytest.mark.asyncio
    async def test_10_concurrent_transfers_of_50_records(self):
        """10 concurrent transfers of 50 records each complete successfully."""
        num_concurrent = 10
        records_per_transfer = 50
        states = ["temp_stored", "in_sample_library", "annotation_pending"]

        resources = []
        tasks = []
        for i in range(num_concurrent):
            engine, session, service = self._create_session_and_service()
            resources.append((engine, session))
            user = User(id=f"concurrent-user-{i}", role=UserRole.ADMIN)
            records = _build_records(records_per_transfer)
            target = states[i % len(states)]
            tasks.append(self._run_transfer(service, user, records, target))

        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        # Cleanup
        for engine, session in resources:
            session.close()
            engine.dispose()

        # Verify all transfers succeeded without data corruption
        for idx, result in enumerate(results):
            assert result["success"] is True, (
                f"Transfer {idx} failed: {result}"
            )
            assert result["transferred_count"] == records_per_transfer

        total_transferred = sum(r["transferred_count"] for r in results)
        assert total_transferred == num_concurrent * records_per_transfer

        assert elapsed < CONCURRENT_10x50_TARGET_S, (
            f"10x50 concurrent transfers took {elapsed:.2f}s, "
            f"target < {CONCURRENT_10x50_TARGET_S}s"
        )
