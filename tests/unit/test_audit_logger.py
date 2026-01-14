"""
Unit tests for Audit Logger.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta
import hashlib
import json

from src.security.audit_logger import AuditLogger, IntegrityResult


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def audit_logger(mock_db):
    """Create audit logger instance."""
    return AuditLogger(mock_db)


class TestAuditLogger:
    """Tests for AuditLogger class."""

    @pytest.mark.asyncio
    async def test_log_creates_entry(self, audit_logger, mock_db):
        """Test that log method creates an audit entry."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        log_entry = await audit_logger.log(
            event_type="login_attempt",
            user_id="user123",
            resource="auth/login",
            action="login",
            result=True,
            ip_address="192.168.1.1"
        )

        assert log_entry is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_with_details(self, audit_logger, mock_db):
        """Test logging with additional details."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        details = {"browser": "Chrome", "os": "Windows"}
        
        log_entry = await audit_logger.log(
            event_type="data_access",
            user_id="user123",
            details=details
        )

        assert log_entry is not None
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_calculates_hash(self, audit_logger, mock_db):
        """Test that log entry hash is calculated."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        log_entry = await audit_logger.log(
            event_type="test_event",
            user_id="user123"
        )

        assert log_entry.hash is not None
        assert len(log_entry.hash) == 64  # SHA-256 hex length

    @pytest.mark.asyncio
    async def test_log_chains_to_previous(self, audit_logger, mock_db):
        """Test that log entries chain to previous hash."""
        # First log entry
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        first_entry = await audit_logger.log(
            event_type="first_event",
            user_id="user123"
        )

        # Second log entry should reference first
        second_entry = await audit_logger.log(
            event_type="second_event",
            user_id="user123"
        )

        assert second_entry.previous_hash == first_entry.hash


class TestHashCalculation:
    """Tests for hash calculation."""

    def test_calculate_hash_deterministic(self, audit_logger):
        """Test that hash calculation is deterministic."""
        mock_entry = MagicMock()
        mock_entry.event_type = "test"
        mock_entry.user_id = "user123"
        mock_entry.resource = "resource"
        mock_entry.action = "action"
        mock_entry.result = True
        mock_entry.timestamp = datetime(2025, 1, 1, 12, 0, 0)
        mock_entry.previous_hash = "prev_hash"
        mock_entry.details = {"key": "value"}
        mock_entry.ip_address = "192.168.1.1"

        hash1 = audit_logger._calculate_hash(mock_entry)
        hash2 = audit_logger._calculate_hash(mock_entry)

        assert hash1 == hash2

    def test_calculate_hash_changes_with_data(self, audit_logger):
        """Test that hash changes when data changes."""
        mock_entry1 = MagicMock()
        mock_entry1.event_type = "test"
        mock_entry1.user_id = "user123"
        mock_entry1.resource = None
        mock_entry1.action = None
        mock_entry1.result = True
        mock_entry1.timestamp = datetime(2025, 1, 1, 12, 0, 0)
        mock_entry1.previous_hash = None
        mock_entry1.details = {}
        mock_entry1.ip_address = None

        mock_entry2 = MagicMock()
        mock_entry2.event_type = "test"
        mock_entry2.user_id = "user456"  # Different user
        mock_entry2.resource = None
        mock_entry2.action = None
        mock_entry2.result = True
        mock_entry2.timestamp = datetime(2025, 1, 1, 12, 0, 0)
        mock_entry2.previous_hash = None
        mock_entry2.details = {}
        mock_entry2.ip_address = None

        hash1 = audit_logger._calculate_hash(mock_entry1)
        hash2 = audit_logger._calculate_hash(mock_entry2)

        assert hash1 != hash2


class TestIntegrityVerification:
    """Tests for integrity verification."""

    @pytest.mark.asyncio
    async def test_verify_integrity_empty_logs(self, audit_logger, mock_db):
        """Test integrity verification with no logs."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await audit_logger.verify_integrity()

        assert result.valid is True
        assert result.verified_count == 0

    @pytest.mark.asyncio
    async def test_verify_integrity_valid_chain(self, audit_logger, mock_db):
        """Test integrity verification with valid chain."""
        # Create mock log entries with valid chain
        entry1 = MagicMock()
        entry1.id = uuid4()
        entry1.event_type = "test1"
        entry1.user_id = "user123"
        entry1.resource = None
        entry1.action = None
        entry1.result = True
        entry1.timestamp = datetime(2025, 1, 1, 12, 0, 0)
        entry1.previous_hash = None
        entry1.details = {}
        entry1.ip_address = None
        entry1.hash = audit_logger._calculate_hash(entry1)

        entry2 = MagicMock()
        entry2.id = uuid4()
        entry2.event_type = "test2"
        entry2.user_id = "user123"
        entry2.resource = None
        entry2.action = None
        entry2.result = True
        entry2.timestamp = datetime(2025, 1, 1, 12, 1, 0)
        entry2.previous_hash = entry1.hash
        entry2.details = {}
        entry2.ip_address = None
        entry2.hash = audit_logger._calculate_hash(entry2)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [entry1, entry2]
        mock_db.execute.return_value = mock_result

        result = await audit_logger.verify_integrity()

        assert result.valid is True
        assert result.verified_count == 2

    @pytest.mark.asyncio
    async def test_verify_integrity_tampered_hash(self, audit_logger, mock_db):
        """Test integrity verification detects tampered hash."""
        entry = MagicMock()
        entry.id = uuid4()
        entry.event_type = "test"
        entry.user_id = "user123"
        entry.resource = None
        entry.action = None
        entry.result = True
        entry.timestamp = datetime(2025, 1, 1, 12, 0, 0)
        entry.previous_hash = None
        entry.details = {}
        entry.ip_address = None
        entry.hash = "tampered_hash_value"  # Invalid hash

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [entry]
        mock_db.execute.return_value = mock_result

        result = await audit_logger.verify_integrity()

        assert result.valid is False
        assert "Hash mismatch" in result.error


class TestQueryLogs:
    """Tests for log querying."""

    @pytest.mark.asyncio
    async def test_query_logs_no_filters(self, audit_logger, mock_db):
        """Test querying logs without filters."""
        mock_logs = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute.return_value = mock_result

        logs = await audit_logger.query_logs()

        assert len(logs) == 2

    @pytest.mark.asyncio
    async def test_query_logs_with_user_filter(self, audit_logger, mock_db):
        """Test querying logs filtered by user."""
        mock_logs = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute.return_value = mock_result

        logs = await audit_logger.query_logs(user_id="user123")

        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_query_logs_with_time_range(self, audit_logger, mock_db):
        """Test querying logs with time range."""
        mock_logs = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute.return_value = mock_result

        start_time = datetime.utcnow() - timedelta(days=7)
        end_time = datetime.utcnow()

        logs = await audit_logger.query_logs(
            start_time=start_time,
            end_time=end_time
        )

        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_query_logs_pagination(self, audit_logger, mock_db):
        """Test log query pagination."""
        mock_logs = [MagicMock() for _ in range(10)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute.return_value = mock_result

        logs = await audit_logger.query_logs(limit=10, offset=0)

        assert len(logs) == 10


class TestExportLogs:
    """Tests for log export functionality."""

    @pytest.mark.asyncio
    async def test_export_logs_json(self, audit_logger, mock_db):
        """Test exporting logs as JSON."""
        mock_log = MagicMock()
        mock_log.id = uuid4()
        mock_log.event_type = "test"
        mock_log.user_id = "user123"
        mock_log.resource = "resource"
        mock_log.action = "action"
        mock_log.result = True
        mock_log.details = {}
        mock_log.ip_address = "192.168.1.1"
        mock_log.user_agent = "Mozilla"
        mock_log.session_id = "session123"
        mock_log.timestamp = datetime(2025, 1, 1, 12, 0, 0)
        mock_log.hash = "hash123"
        mock_log.previous_hash = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_log]
        mock_db.execute.return_value = mock_result

        data = await audit_logger.export_logs(
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 1, 2),
            format="json"
        )

        assert isinstance(data, bytes)
        parsed = json.loads(data.decode('utf-8'))
        assert len(parsed) == 1

    @pytest.mark.asyncio
    async def test_export_logs_csv(self, audit_logger, mock_db):
        """Test exporting logs as CSV."""
        mock_log = MagicMock()
        mock_log.id = uuid4()
        mock_log.event_type = "test"
        mock_log.user_id = "user123"
        mock_log.resource = "resource"
        mock_log.action = "action"
        mock_log.result = True
        mock_log.details = {}
        mock_log.ip_address = "192.168.1.1"
        mock_log.user_agent = "Mozilla"
        mock_log.session_id = "session123"
        mock_log.timestamp = datetime(2025, 1, 1, 12, 0, 0)
        mock_log.hash = "hash123"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_log]
        mock_db.execute.return_value = mock_result

        data = await audit_logger.export_logs(
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 1, 2),
            format="csv"
        )

        assert isinstance(data, bytes)
        content = data.decode('utf-8')
        assert "id" in content
        assert "event_type" in content

    @pytest.mark.asyncio
    async def test_export_logs_invalid_format(self, audit_logger, mock_db):
        """Test export with invalid format raises error."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Unsupported export format"):
            await audit_logger.export_logs(
                start_time=datetime(2025, 1, 1),
                end_time=datetime(2025, 1, 2),
                format="xml"
            )


class TestRetentionPolicy:
    """Tests for retention policy."""

    @pytest.mark.asyncio
    async def test_apply_retention_policy(self, audit_logger, mock_db):
        """Test applying retention policy."""
        mock_logs = [MagicMock() for _ in range(5)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute.return_value = mock_result

        archived_count = await audit_logger.apply_retention_policy(retention_days=30)

        assert archived_count == 5


class TestStatistics:
    """Tests for audit statistics."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, audit_logger, mock_db):
        """Test getting audit statistics."""
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 100

        # Mock event type distribution
        mock_event_result = MagicMock()
        mock_event_result.__iter__ = lambda self: iter([
            MagicMock(event_type="login", count=50),
            MagicMock(event_type="data_access", count=50)
        ])

        # Mock result distribution
        mock_result_result = MagicMock()
        mock_result_result.__iter__ = lambda self: iter([
            MagicMock(result=True, count=90),
            MagicMock(result=False, count=10)
        ])

        mock_db.execute.side_effect = [
            mock_count_result,
            mock_event_result,
            mock_result_result
        ]

        stats = await audit_logger.get_statistics()

        assert stats["total_logs"] == 100


class TestIntegrityResult:
    """Tests for IntegrityResult class."""

    def test_integrity_result_valid(self):
        """Test creating valid integrity result."""
        result = IntegrityResult(valid=True, verified_count=100)
        assert result.valid is True
        assert result.verified_count == 100
        assert result.error is None

    def test_integrity_result_invalid(self):
        """Test creating invalid integrity result."""
        result = IntegrityResult(
            valid=False,
            verified_count=50,
            error="Hash mismatch",
            corrupted_entry_id="entry123"
        )
        assert result.valid is False
        assert result.error == "Hash mismatch"
        assert result.corrupted_entry_id == "entry123"

    def test_integrity_result_to_dict(self):
        """Test converting integrity result to dict."""
        result = IntegrityResult(valid=True, verified_count=100, message="All good")
        result_dict = result.to_dict()
        
        assert result_dict["valid"] is True
        assert result_dict["verified_count"] == 100
        assert result_dict["message"] == "All good"
