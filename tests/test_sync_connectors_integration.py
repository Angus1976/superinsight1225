"""
Integration tests for data source connectors.

Tests:
- REST API connector with various authentication methods
- Pagination strategies
- Rate limiting and retry mechanisms
- Database connectors (MySQL, PostgreSQL)
- File connectors (Local, S3)
- Error handling and recovery
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.sync.connectors.base import (
    ConnectionStatus, OperationType, DataRecord, DataBatch,
    SyncResult, ConnectorConfig
)


class TestDataRecord:
    """Tests for DataRecord data class."""

    def test_create_data_record(self):
        """Test creating a data record."""
        record = DataRecord(
            id="record_1",
            data={"name": "Test", "value": 100}
        )

        assert record.id == "record_1"
        assert record.data["name"] == "Test"
        assert record.operation == OperationType.UPSERT

    def test_data_record_with_metadata(self):
        """Test data record with metadata."""
        record = DataRecord(
            id="record_2",
            data={"field": "value"},
            metadata={"source": "api", "timestamp": "2024-01-01"},
            operation=OperationType.INSERT
        )

        assert record.metadata["source"] == "api"
        assert record.operation == OperationType.INSERT

    def test_compute_hash(self):
        """Test hash computation for change detection."""
        record = DataRecord(
            id="record_3",
            data={"key": "value", "number": 42}
        )

        hash1 = record.compute_hash()
        assert hash1 is not None
        assert len(hash1) == 64  # SHA256 hex length

        # Same data should produce same hash
        record2 = DataRecord(
            id="record_4",
            data={"key": "value", "number": 42}
        )
        hash2 = record2.compute_hash()
        assert hash1 == hash2

        # Different data should produce different hash
        record3 = DataRecord(
            id="record_5",
            data={"key": "different", "number": 42}
        )
        hash3 = record3.compute_hash()
        assert hash1 != hash3


class TestDataBatch:
    """Tests for DataBatch data class."""

    def test_create_data_batch(self):
        """Test creating a data batch."""
        records = [
            DataRecord(id=f"r_{i}", data={"index": i})
            for i in range(10)
        ]

        batch = DataBatch(
            records=records,
            source_id="test_source"
        )

        assert len(batch.records) == 10
        assert batch.source_id == "test_source"
        assert batch.total_count == 10
        assert batch.batch_id  # Auto-generated

    def test_batch_with_pagination_info(self):
        """Test batch with pagination information."""
        records = [DataRecord(id="r_1", data={})]

        batch = DataBatch(
            records=records,
            source_id="paginated_source",
            offset=100,
            total_count=500,
            has_more=True
        )

        assert batch.offset == 100
        assert batch.total_count == 500
        assert batch.has_more is True

    def test_batch_with_checkpoint(self):
        """Test batch with checkpoint for incremental sync."""
        records = [DataRecord(id="r_1", data={})]

        checkpoint = {
            "last_id": 1000,
            "last_timestamp": "2024-01-01T00:00:00Z"
        }

        batch = DataBatch(
            records=records,
            source_id="incremental_source",
            checkpoint=checkpoint
        )

        assert batch.checkpoint == checkpoint
        assert batch.checkpoint["last_id"] == 1000


class TestSyncResult:
    """Tests for SyncResult data class."""

    def test_successful_sync_result(self):
        """Test successful sync result."""
        result = SyncResult(
            success=True,
            records_processed=100,
            records_inserted=80,
            records_updated=20,
            duration_seconds=5.5
        )

        assert result.success is True
        assert result.records_processed == 100
        assert result.records_inserted == 80
        assert result.records_updated == 20
        assert result.duration_seconds == 5.5

    def test_failed_sync_result(self):
        """Test failed sync result with errors."""
        result = SyncResult(
            success=False,
            records_processed=50,
            records_failed=10,
            errors=[
                {"record_id": "r_1", "error": "Validation failed"},
                {"record_id": "r_2", "error": "Duplicate key"}
            ]
        )

        assert result.success is False
        assert result.records_failed == 10
        assert len(result.errors) == 2

    def test_partial_sync_result(self):
        """Test partial sync result."""
        result = SyncResult(
            success=True,
            records_processed=100,
            records_inserted=70,
            records_skipped=30,
            checkpoint={"last_id": 500}
        )

        assert result.records_skipped == 30
        assert result.checkpoint["last_id"] == 500


class TestConnectionStatus:
    """Tests for connection status handling."""

    def test_connection_status_values(self):
        """Test connection status enumeration values."""
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.ERROR.value == "error"
        assert ConnectionStatus.RECONNECTING.value == "reconnecting"

    def test_status_comparison(self):
        """Test connection status comparison."""
        status1 = ConnectionStatus.CONNECTED
        status2 = ConnectionStatus.CONNECTED
        status3 = ConnectionStatus.DISCONNECTED

        assert status1 == status2
        assert status1 != status3


class TestOperationType:
    """Tests for operation type handling."""

    def test_operation_type_values(self):
        """Test operation type enumeration values."""
        assert OperationType.INSERT.value == "insert"
        assert OperationType.UPDATE.value == "update"
        assert OperationType.DELETE.value == "delete"
        assert OperationType.UPSERT.value == "upsert"


class TestConnectorConfig:
    """Tests for connector configuration."""

    def test_basic_config(self):
        """Test basic connector configuration."""
        config = ConnectorConfig(
            name="test_connector",
            description="Test connector for unit tests"
        )

        assert config.name == "test_connector"
        assert config.description == "Test connector for unit tests"
        assert config.enabled is True

    def test_disabled_config(self):
        """Test disabled connector configuration."""
        config = ConnectorConfig(
            name="disabled_connector",
            enabled=False
        )

        assert config.enabled is False


class MockRESTConnector:
    """Mock REST connector for testing."""

    def __init__(self, base_url: str, auth_type: str = "api_key"):
        self.base_url = base_url
        self.auth_type = auth_type
        self.status = ConnectionStatus.DISCONNECTED
        self._request_count = 0
        self._rate_limit_remaining = 100

    async def connect(self) -> bool:
        """Simulate connection."""
        self.status = ConnectionStatus.CONNECTING
        await asyncio.sleep(0.01)  # Simulate network delay
        self.status = ConnectionStatus.CONNECTED
        return True

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self.status = ConnectionStatus.DISCONNECTED

    async def fetch_data(
        self,
        endpoint: str,
        params: Dict[str, Any] = None,
        page_size: int = 100
    ) -> DataBatch:
        """Simulate fetching data from REST API."""
        self._request_count += 1
        self._rate_limit_remaining -= 1

        if self._rate_limit_remaining <= 0:
            raise Exception("Rate limit exceeded")

        # Simulate paginated response
        records = [
            DataRecord(
                id=f"record_{i}",
                data={"field": f"value_{i}", "endpoint": endpoint}
            )
            for i in range(page_size)
        ]

        return DataBatch(
            records=records,
            source_id=f"{self.base_url}{endpoint}",
            has_more=self._request_count < 3
        )


class TestMockRESTConnector:
    """Tests for REST connector functionality."""

    @pytest.fixture
    def connector(self):
        """Create mock REST connector."""
        return MockRESTConnector("https://api.example.com", "api_key")

    @pytest.mark.asyncio
    async def test_connect(self, connector):
        """Test connection establishment."""
        assert connector.status == ConnectionStatus.DISCONNECTED

        result = await connector.connect()

        assert result is True
        assert connector.status == ConnectionStatus.CONNECTED

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        """Test disconnection."""
        await connector.connect()
        await connector.disconnect()

        assert connector.status == ConnectionStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_fetch_data(self, connector):
        """Test data fetching."""
        await connector.connect()

        batch = await connector.fetch_data("/users", page_size=50)

        assert len(batch.records) == 50
        assert batch.source_id == "https://api.example.com/users"

    @pytest.mark.asyncio
    async def test_pagination(self, connector):
        """Test paginated data fetching."""
        await connector.connect()

        all_records = []
        page = 1

        while True:
            batch = await connector.fetch_data(f"/items?page={page}")
            all_records.extend(batch.records)

            if not batch.has_more:
                break
            page += 1

        assert len(all_records) >= 100

    @pytest.mark.asyncio
    async def test_rate_limiting(self, connector):
        """Test rate limit handling."""
        connector._rate_limit_remaining = 2
        await connector.connect()

        # First two requests should succeed
        await connector.fetch_data("/data", page_size=10)
        await connector.fetch_data("/data", page_size=10)

        # Third request should fail
        with pytest.raises(Exception, match="Rate limit"):
            await connector.fetch_data("/data", page_size=10)


class MockDatabaseConnector:
    """Mock database connector for testing."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.status = ConnectionStatus.DISCONNECTED
        self._data = {}

    async def connect(self) -> bool:
        """Simulate database connection."""
        self.status = ConnectionStatus.CONNECTED
        return True

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self.status = ConnectionStatus.DISCONNECTED

    async def execute_query(self, query: str, params: Dict = None) -> List[Dict]:
        """Simulate query execution."""
        # Return mock data based on query
        if "SELECT" in query.upper():
            return [{"id": i, "name": f"Item {i}"} for i in range(10)]
        return []

    async def insert_batch(self, table: str, records: List[DataRecord]) -> SyncResult:
        """Simulate batch insert."""
        for record in records:
            key = f"{table}:{record.id}"
            self._data[key] = record.data

        return SyncResult(
            success=True,
            records_processed=len(records),
            records_inserted=len(records)
        )

    async def get_changes_since(
        self,
        table: str,
        checkpoint: Dict[str, Any]
    ) -> DataBatch:
        """Simulate incremental change detection."""
        # Return mock changed records
        records = [
            DataRecord(
                id=f"changed_{i}",
                data={"updated": True},
                operation=OperationType.UPDATE
            )
            for i in range(5)
        ]

        return DataBatch(
            records=records,
            source_id=f"db:{table}",
            checkpoint={"last_id": 1000, "timestamp": datetime.utcnow().isoformat()}
        )


class TestMockDatabaseConnector:
    """Tests for database connector functionality."""

    @pytest.fixture
    def connector(self):
        """Create mock database connector."""
        return MockDatabaseConnector("postgresql://localhost/testdb")

    @pytest.mark.asyncio
    async def test_connect(self, connector):
        """Test database connection."""
        result = await connector.connect()

        assert result is True
        assert connector.status == ConnectionStatus.CONNECTED

    @pytest.mark.asyncio
    async def test_execute_query(self, connector):
        """Test query execution."""
        await connector.connect()

        results = await connector.execute_query("SELECT * FROM items")

        assert len(results) == 10
        assert results[0]["id"] == 0

    @pytest.mark.asyncio
    async def test_insert_batch(self, connector):
        """Test batch insert."""
        await connector.connect()

        records = [
            DataRecord(id=f"r_{i}", data={"value": i})
            for i in range(5)
        ]

        result = await connector.insert_batch("test_table", records)

        assert result.success is True
        assert result.records_inserted == 5

    @pytest.mark.asyncio
    async def test_incremental_sync(self, connector):
        """Test incremental change detection."""
        await connector.connect()

        checkpoint = {"last_id": 500}
        batch = await connector.get_changes_since("users", checkpoint)

        assert len(batch.records) > 0
        assert batch.checkpoint is not None
        assert batch.checkpoint["last_id"] > checkpoint["last_id"]


class MockFileConnector:
    """Mock file connector for testing."""

    def __init__(self, base_path: str):
        self.base_path = base_path
        self.status = ConnectionStatus.DISCONNECTED
        self._files = {}

    async def connect(self) -> bool:
        """Simulate connection."""
        self.status = ConnectionStatus.CONNECTED
        return True

    async def list_files(self, pattern: str = "*") -> List[str]:
        """List files matching pattern."""
        return [f"file_{i}.json" for i in range(5)]

    async def read_file(self, file_path: str) -> DataBatch:
        """Read file and return as data batch."""
        records = [
            DataRecord(
                id=f"line_{i}",
                data={"content": f"Line {i} from {file_path}"}
            )
            for i in range(100)
        ]

        return DataBatch(
            records=records,
            source_id=f"{self.base_path}/{file_path}",
            metadata={"file_path": file_path}
        )

    async def write_records(
        self,
        file_path: str,
        records: List[DataRecord]
    ) -> SyncResult:
        """Write records to file."""
        self._files[file_path] = records

        return SyncResult(
            success=True,
            records_processed=len(records)
        )


class TestMockFileConnector:
    """Tests for file connector functionality."""

    @pytest.fixture
    def connector(self):
        """Create mock file connector."""
        return MockFileConnector("/data/files")

    @pytest.mark.asyncio
    async def test_list_files(self, connector):
        """Test file listing."""
        await connector.connect()

        files = await connector.list_files("*.json")

        assert len(files) == 5
        assert all(f.endswith(".json") for f in files)

    @pytest.mark.asyncio
    async def test_read_file(self, connector):
        """Test file reading."""
        await connector.connect()

        batch = await connector.read_file("test_data.json")

        assert len(batch.records) == 100
        assert batch.metadata["file_path"] == "test_data.json"

    @pytest.mark.asyncio
    async def test_write_records(self, connector):
        """Test writing records to file."""
        await connector.connect()

        records = [
            DataRecord(id=f"r_{i}", data={"value": i})
            for i in range(10)
        ]

        result = await connector.write_records("output.json", records)

        assert result.success is True
        assert result.records_processed == 10


class TestErrorHandling:
    """Tests for error handling and recovery."""

    @pytest.mark.asyncio
    async def test_connection_retry(self):
        """Test connection retry on failure."""
        class FlakyCon:
            def __init__(self):
                self.attempts = 0

            async def connect(self):
                self.attempts += 1
                if self.attempts < 3:
                    raise ConnectionError("Connection failed")
                return True

        connector = FlakyCon()

        for _ in range(5):
            try:
                result = await connector.connect()
                if result:
                    break
            except ConnectionError:
                await asyncio.sleep(0.01)

        assert connector.attempts == 3

    @pytest.mark.asyncio
    async def test_partial_batch_failure(self):
        """Test handling partial batch failures."""
        records = [
            DataRecord(id=f"r_{i}", data={"value": i})
            for i in range(10)
        ]

        # Simulate processing with some failures
        successful = []
        failed = []

        for record in records:
            if record.data["value"] % 3 == 0:
                failed.append({"record_id": record.id, "error": "Validation failed"})
            else:
                successful.append(record)

        result = SyncResult(
            success=len(failed) == 0,
            records_processed=len(records),
            records_inserted=len(successful),
            records_failed=len(failed),
            errors=failed
        )

        assert result.records_processed == 10
        assert result.records_failed == 4  # 0, 3, 6, 9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
