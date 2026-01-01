"""
WebSocket Real-time Communication Tests.

Tests for WebSocket server, connection management, stream processing,
backpressure control, and message filtering/transformation.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.sync.websocket.ws_server import (
    ConnectionState,
    MessageType,
    SubscriptionType,
    WebSocketMessage,
    AuthPayload,
    SubscriptionPayload,
    ConnectionInfo,
    WebSocketConnectionManager,
)
from src.sync.websocket.stream_processor import (
    StreamState,
    BackpressureStrategy,
    StreamMetrics,
    StreamMessage,
    FilterRule,
    StreamFilter,
    IdentityTransformer,
    FieldMappingTransformer,
    AggregatingTransformer,
    BackpressureController,
    RetryPolicy,
    StreamProcessor,
    StreamProcessorManager,
    create_sync_data_processor,
    create_event_processor,
)


# =============================================================================
# Test Fixtures
# =============================================================================

class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.accepted = False
        self.closed = False
        self.close_code = None
        self.sent_messages = []

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000):
        self.closed = True
        self.close_code = code

    async def send_json(self, data):
        self.sent_messages.append(data)

    async def receive_json(self):
        return {}


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    return MockWebSocket()


@pytest.fixture
def connection_manager():
    """Create a connection manager for testing."""
    return WebSocketConnectionManager(
        max_connections_per_tenant=10,
        ping_interval=30.0,
        ping_timeout=10.0
    )


@pytest.fixture
def stream_message():
    """Create a sample stream message."""
    return StreamMessage(
        id="msg_001",
        source="test_source",
        type="data_update",
        data={"field1": "value1", "count": 10},
        timestamp=datetime.utcnow(),
        metadata={"tenant": "test_tenant"}
    )


# =============================================================================
# WebSocket Connection Manager Tests
# =============================================================================

class TestWebSocketConnectionManager:
    """Tests for WebSocket connection manager."""

    @pytest.mark.asyncio
    async def test_connect_establishes_connection(self, connection_manager, mock_websocket):
        """Test that connect accepts WebSocket and creates connection info."""
        connection = await connection_manager.connect(mock_websocket)

        assert mock_websocket.accepted
        assert connection.state == ConnectionState.CONNECTED
        assert connection.connection_id is not None
        assert connection.websocket == mock_websocket

    @pytest.mark.asyncio
    async def test_connect_with_custom_id(self, connection_manager, mock_websocket):
        """Test connecting with a custom connection ID."""
        custom_id = "custom_conn_123"
        connection = await connection_manager.connect(mock_websocket, connection_id=custom_id)

        assert connection.connection_id == custom_id

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, connection_manager, mock_websocket):
        """Test that disconnect properly removes connection."""
        connection = await connection_manager.connect(mock_websocket)
        conn_id = connection.connection_id

        await connection_manager.disconnect(conn_id, reason="Test disconnect")

        assert connection_manager.get_connection(conn_id) is None
        assert mock_websocket.closed

    @pytest.mark.asyncio
    async def test_authenticate_success(self, connection_manager, mock_websocket):
        """Test successful authentication."""
        connection = await connection_manager.connect(mock_websocket)

        result = await connection_manager.authenticate(
            connection.connection_id,
            token="valid_token",
            tenant_id="tenant_001",
            user_id="user_001"
        )

        assert result is True
        assert connection.state == ConnectionState.AUTHENTICATED
        assert connection.tenant_id == "tenant_001"
        assert connection.user_id == "user_001"

    @pytest.mark.asyncio
    async def test_authenticate_with_custom_handler_success(self, mock_websocket):
        """Test authentication with custom handler success."""
        async def custom_auth(token, tenant_id, user_id):
            return token == "valid_token"

        manager = WebSocketConnectionManager(auth_handler=custom_auth)
        connection = await manager.connect(mock_websocket)

        result = await manager.authenticate(
            connection.connection_id,
            token="valid_token",
            tenant_id="tenant_001"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_authenticate_with_custom_handler_failure(self, mock_websocket):
        """Test authentication with custom handler failure."""
        async def custom_auth(token, tenant_id, user_id):
            return token == "valid_token"

        manager = WebSocketConnectionManager(auth_handler=custom_auth)
        connection = await manager.connect(mock_websocket)

        result = await manager.authenticate(
            connection.connection_id,
            token="invalid_token",
            tenant_id="tenant_001"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_tenant_connection_limit(self, connection_manager, mock_websocket):
        """Test that tenant connection limit is enforced."""
        # Set limit to 2 for testing
        connection_manager._max_connections_per_tenant = 2

        # Create and authenticate 2 connections
        for i in range(2):
            ws = MockWebSocket()
            conn = await connection_manager.connect(ws)
            await connection_manager.authenticate(conn.connection_id, "token", "tenant_001")

        # Third connection should fail
        ws3 = MockWebSocket()
        conn3 = await connection_manager.connect(ws3)
        result = await connection_manager.authenticate(conn3.connection_id, "token", "tenant_001")

        assert result is False

    @pytest.mark.asyncio
    async def test_subscribe_success(self, connection_manager, mock_websocket):
        """Test successful subscription."""
        connection = await connection_manager.connect(mock_websocket)
        await connection_manager.authenticate(connection.connection_id, "token", "tenant_001")

        result = await connection_manager.subscribe(
            connection.connection_id,
            SubscriptionType.SYNC_JOB,
            filters={"job_id": "job_001"}
        )

        assert result is True
        assert connection.state == ConnectionState.SUBSCRIBED
        assert len(connection.subscriptions) == 1

    @pytest.mark.asyncio
    async def test_subscribe_requires_authentication(self, connection_manager, mock_websocket):
        """Test that subscription requires authentication."""
        connection = await connection_manager.connect(mock_websocket)

        # Not authenticated yet
        result = await connection_manager.subscribe(
            connection.connection_id,
            SubscriptionType.SYNC_JOB
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe(self, connection_manager, mock_websocket):
        """Test unsubscription."""
        connection = await connection_manager.connect(mock_websocket)
        await connection_manager.authenticate(connection.connection_id, "token", "tenant_001")
        await connection_manager.subscribe(connection.connection_id, SubscriptionType.SYNC_JOB)

        result = await connection_manager.unsubscribe(
            connection.connection_id,
            SubscriptionType.SYNC_JOB
        )

        assert result is True
        assert len(connection.subscriptions) == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_subscription(self, connection_manager):
        """Test broadcasting to subscription."""
        # Create and subscribe two connections
        ws1, ws2 = MockWebSocket(), MockWebSocket()
        conn1 = await connection_manager.connect(ws1)
        conn2 = await connection_manager.connect(ws2)

        await connection_manager.authenticate(conn1.connection_id, "token", "tenant_001")
        await connection_manager.authenticate(conn2.connection_id, "token", "tenant_001")

        await connection_manager.subscribe(conn1.connection_id, SubscriptionType.SYNC_JOB)
        await connection_manager.subscribe(conn2.connection_id, SubscriptionType.SYNC_JOB)

        # Broadcast message
        message = WebSocketMessage(
            type=MessageType.DATA_UPDATE,
            payload={"data": "test"}
        )

        sent_count = await connection_manager.broadcast_to_subscription(
            SubscriptionType.SYNC_JOB,
            "tenant_001",
            message
        )

        assert sent_count == 2
        assert len(ws1.sent_messages) > 1  # Including connection message
        assert len(ws2.sent_messages) > 1

    @pytest.mark.asyncio
    async def test_broadcast_to_tenant(self, connection_manager):
        """Test broadcasting to all connections of a tenant."""
        ws1, ws2 = MockWebSocket(), MockWebSocket()
        conn1 = await connection_manager.connect(ws1)
        conn2 = await connection_manager.connect(ws2)

        await connection_manager.authenticate(conn1.connection_id, "token", "tenant_001")
        await connection_manager.authenticate(conn2.connection_id, "token", "tenant_001")

        message = WebSocketMessage(
            type=MessageType.SYSTEM_NOTIFICATION,
            payload={"message": "test notification"}
        )

        sent_count = await connection_manager.broadcast_to_tenant("tenant_001", message)

        assert sent_count == 2

    @pytest.mark.asyncio
    async def test_send_to_connection(self, connection_manager, mock_websocket):
        """Test sending to specific connection."""
        connection = await connection_manager.connect(mock_websocket)

        message = WebSocketMessage(
            type=MessageType.PONG,
            payload={"timestamp": "2024-01-01T00:00:00"}
        )

        result = await connection_manager.send_to_connection(connection.connection_id, message)

        assert result is True
        assert len(mock_websocket.sent_messages) == 2  # Connect ack + sent message

    @pytest.mark.asyncio
    async def test_get_stats(self, connection_manager):
        """Test getting connection statistics."""
        ws1, ws2 = MockWebSocket(), MockWebSocket()
        await connection_manager.connect(ws1)
        conn2 = await connection_manager.connect(ws2)
        await connection_manager.authenticate(conn2.connection_id, "token", "tenant_001")

        stats = connection_manager.get_stats()

        assert stats["total_connections"] == 2
        assert "connections_by_state" in stats
        assert stats["tenants"] == 1

    @pytest.mark.asyncio
    async def test_get_tenant_connections(self, connection_manager):
        """Test getting all connections for a tenant."""
        ws1, ws2 = MockWebSocket(), MockWebSocket()
        conn1 = await connection_manager.connect(ws1)
        conn2 = await connection_manager.connect(ws2)

        await connection_manager.authenticate(conn1.connection_id, "token", "tenant_001")
        await connection_manager.authenticate(conn2.connection_id, "token", "tenant_001")

        connections = connection_manager.get_tenant_connections("tenant_001")

        assert len(connections) == 2


class TestWebSocketMessage:
    """Tests for WebSocket message model."""

    def test_message_creation(self):
        """Test creating a WebSocket message."""
        message = WebSocketMessage(
            type=MessageType.DATA_UPDATE,
            payload={"data": "test"}
        )

        assert message.type == MessageType.DATA_UPDATE
        assert message.payload == {"data": "test"}
        assert message.message_id is not None
        assert message.timestamp is not None

    def test_message_with_correlation_id(self):
        """Test message with correlation ID."""
        message = WebSocketMessage(
            type=MessageType.PONG,
            payload={},
            correlation_id="corr_123"
        )

        assert message.correlation_id == "corr_123"


class TestConnectionInfo:
    """Tests for connection info dataclass."""

    def test_update_activity(self, mock_websocket):
        """Test updating activity timestamp."""
        conn = ConnectionInfo(
            connection_id="conn_001",
            websocket=mock_websocket
        )

        old_activity = conn.last_activity

        # Small delay to ensure time difference
        import time
        time.sleep(0.01)

        conn.update_activity()

        assert conn.last_activity >= old_activity


# =============================================================================
# Stream Processor Tests
# =============================================================================

class TestFilterRule:
    """Tests for filter rules."""

    def test_eq_operator(self):
        """Test equality operator."""
        rule = FilterRule(field="status", operator="eq", value="active")

        assert rule.matches({"status": "active"}) is True
        assert rule.matches({"status": "inactive"}) is False

    def test_ne_operator(self):
        """Test not equal operator."""
        rule = FilterRule(field="status", operator="ne", value="deleted")

        assert rule.matches({"status": "active"}) is True
        assert rule.matches({"status": "deleted"}) is False

    def test_gt_operator(self):
        """Test greater than operator."""
        rule = FilterRule(field="count", operator="gt", value=10)

        assert rule.matches({"count": 15}) is True
        assert rule.matches({"count": 5}) is False

    def test_lt_operator(self):
        """Test less than operator."""
        rule = FilterRule(field="count", operator="lt", value=10)

        assert rule.matches({"count": 5}) is True
        assert rule.matches({"count": 15}) is False

    def test_gte_operator(self):
        """Test greater than or equal operator."""
        rule = FilterRule(field="count", operator="gte", value=10)

        assert rule.matches({"count": 10}) is True
        assert rule.matches({"count": 15}) is True
        assert rule.matches({"count": 5}) is False

    def test_lte_operator(self):
        """Test less than or equal operator."""
        rule = FilterRule(field="count", operator="lte", value=10)

        assert rule.matches({"count": 10}) is True
        assert rule.matches({"count": 5}) is True
        assert rule.matches({"count": 15}) is False

    def test_contains_operator(self):
        """Test contains operator."""
        rule = FilterRule(field="message", operator="contains", value="error")

        assert rule.matches({"message": "An error occurred"}) is True
        assert rule.matches({"message": "Success"}) is False

    def test_in_operator(self):
        """Test in operator."""
        rule = FilterRule(field="status", operator="in", value=["active", "pending"])

        assert rule.matches({"status": "active"}) is True
        assert rule.matches({"status": "pending"}) is True
        assert rule.matches({"status": "deleted"}) is False

    def test_regex_operator(self):
        """Test regex operator."""
        rule = FilterRule(field="email", operator="regex", value=r".*@example\.com")

        assert rule.matches({"email": "user@example.com"}) is True
        assert rule.matches({"email": "user@other.com"}) is False

    def test_negate_modifier(self):
        """Test negation modifier."""
        rule = FilterRule(field="status", operator="eq", value="deleted", negate=True)

        assert rule.matches({"status": "active"}) is True
        assert rule.matches({"status": "deleted"}) is False

    def test_missing_field(self):
        """Test matching with missing field."""
        rule = FilterRule(field="missing", operator="eq", value="value")

        assert rule.matches({"other": "value"}) is False

        # Negated should return True for missing field
        rule_neg = FilterRule(field="missing", operator="eq", value="value", negate=True)
        assert rule_neg.matches({"other": "value"}) is True


class TestStreamFilter:
    """Tests for stream filter."""

    def test_empty_filter_matches_all(self, stream_message):
        """Test that empty filter matches all messages."""
        filter = StreamFilter()

        assert filter.matches(stream_message) is True

    def test_match_all_rules(self, stream_message):
        """Test matching all rules."""
        filter = StreamFilter(
            rules=[
                FilterRule(field="type", operator="eq", value="data_update"),
                FilterRule(field="source", operator="eq", value="test_source")
            ],
            match_all=True
        )

        assert filter.matches(stream_message) is True

        # Change one condition to fail
        stream_message.type = "other_type"
        assert filter.matches(stream_message) is False

    def test_match_any_rules(self, stream_message):
        """Test matching any rule."""
        filter = StreamFilter(
            rules=[
                FilterRule(field="type", operator="eq", value="other_type"),
                FilterRule(field="source", operator="eq", value="test_source")
            ],
            match_all=False
        )

        assert filter.matches(stream_message) is True


class TestTransformers:
    """Tests for data transformers."""

    @pytest.mark.asyncio
    async def test_identity_transformer(self, stream_message):
        """Test identity transformer returns message unchanged."""
        transformer = IdentityTransformer()

        result = await transformer.transform(stream_message)

        assert result.id == stream_message.id
        assert result.data == stream_message.data

    @pytest.mark.asyncio
    async def test_field_mapping_transformer(self, stream_message):
        """Test field mapping transformer."""
        transformer = FieldMappingTransformer(
            field_mappings={"field1": "renamed_field1"}
        )

        result = await transformer.transform(stream_message)

        assert "renamed_field1" in result.data
        assert "field1" not in result.data
        assert result.data["renamed_field1"] == "value1"
        # Unmapped fields should be preserved
        assert result.data["count"] == 10

    @pytest.mark.asyncio
    async def test_aggregating_transformer(self):
        """Test aggregating transformer."""
        transformer = AggregatingTransformer(
            aggregation_field="value",
            aggregation_func="sum",
            window_size_seconds=60.0
        )

        # Submit multiple messages
        for i in range(5):
            msg = StreamMessage(
                id=f"msg_{i}",
                source="test",
                type="metric",
                data={"value": 10}
            )
            result = await transformer.transform(msg)

        assert result.data["value_sum"] == 50
        assert result.data["window_count"] == 5

    @pytest.mark.asyncio
    async def test_aggregating_transformer_avg(self):
        """Test aggregating transformer with average."""
        transformer = AggregatingTransformer(
            aggregation_field="value",
            aggregation_func="avg"
        )

        for value in [10, 20, 30]:
            msg = StreamMessage(
                id="msg",
                source="test",
                type="metric",
                data={"value": value}
            )
            result = await transformer.transform(msg)

        assert result.data["value_avg"] == 20.0


class TestBackpressureController:
    """Tests for backpressure controller."""

    @pytest.mark.asyncio
    async def test_push_within_capacity(self, stream_message):
        """Test pushing messages within capacity."""
        controller = BackpressureController(max_buffer_size=100)

        result = await controller.push(stream_message)

        assert result is True
        assert controller.buffer_utilization > 0

    @pytest.mark.asyncio
    async def test_pop_message(self, stream_message):
        """Test popping messages from buffer."""
        controller = BackpressureController(max_buffer_size=100)
        await controller.push(stream_message)

        result = await controller.pop()

        assert result is not None
        assert result.id == stream_message.id

    @pytest.mark.asyncio
    async def test_backpressure_activated(self):
        """Test backpressure activation at high watermark."""
        controller = BackpressureController(
            max_buffer_size=10,
            high_watermark=0.8,
            strategy=BackpressureStrategy.DROP_OLDEST
        )

        # Fill buffer to trigger backpressure
        for i in range(9):  # 90% utilization
            msg = StreamMessage(
                id=f"msg_{i}",
                source="test",
                type="test",
                data={}
            )
            await controller.push(msg)

        assert controller.is_backpressure_active is True

    @pytest.mark.asyncio
    async def test_drop_oldest_strategy(self):
        """Test DROP_OLDEST backpressure strategy."""
        controller = BackpressureController(
            max_buffer_size=5,
            high_watermark=0.8,
            strategy=BackpressureStrategy.DROP_OLDEST
        )

        # Fill buffer completely
        for i in range(6):
            msg = StreamMessage(
                id=f"msg_{i}",
                source="test",
                type="test",
                data={"order": i}
            )
            await controller.push(msg)

        # First message should have been dropped
        first_msg = await controller.pop()
        assert first_msg.data["order"] == 1  # msg_0 was dropped

    @pytest.mark.asyncio
    async def test_drop_newest_strategy(self):
        """Test DROP_NEWEST backpressure strategy."""
        controller = BackpressureController(
            max_buffer_size=5,
            high_watermark=0.6,
            strategy=BackpressureStrategy.DROP_NEWEST
        )

        # Fill buffer
        accepted_count = 0
        for i in range(10):
            msg = StreamMessage(
                id=f"msg_{i}",
                source="test",
                type="test",
                data={}
            )
            if await controller.push(msg):
                accepted_count += 1

        assert accepted_count == 5  # Only first 5 accepted

    @pytest.mark.asyncio
    async def test_sample_strategy(self):
        """Test SAMPLE backpressure strategy."""
        controller = BackpressureController(
            max_buffer_size=10,
            high_watermark=0.5,
            strategy=BackpressureStrategy.SAMPLE,
            sample_rate=0.5  # Accept every other message
        )

        # Trigger backpressure
        for i in range(6):
            msg = StreamMessage(
                id=f"msg_{i}",
                source="test",
                type="test",
                data={}
            )
            await controller.push(msg)

        # Some messages should be sampled out
        buffer_size = len(controller.buffer)
        assert buffer_size < 10

    @pytest.mark.asyncio
    async def test_clear_buffer(self, stream_message):
        """Test clearing the buffer."""
        controller = BackpressureController(max_buffer_size=100)

        for _ in range(5):
            await controller.push(stream_message)

        cleared = await controller.clear()

        assert cleared == 5
        assert len(controller.buffer) == 0

    @pytest.mark.asyncio
    async def test_backpressure_deactivation(self):
        """Test backpressure deactivation at low watermark."""
        controller = BackpressureController(
            max_buffer_size=10,
            high_watermark=0.8,
            low_watermark=0.3
        )

        # Fill to trigger backpressure
        for i in range(9):
            msg = StreamMessage(
                id=f"msg_{i}",
                source="test",
                type="test",
                data={}
            )
            await controller.push(msg)

        assert controller.is_backpressure_active is True

        # Drain below low watermark
        for _ in range(7):
            await controller.pop()

        # Check one more pop to trigger deactivation check
        await controller.pop()

        assert controller.is_backpressure_active is False


class TestRetryPolicy:
    """Tests for retry policy."""

    def test_should_retry_within_limit(self):
        """Test retry within limit."""
        policy = RetryPolicy(max_retries=3)

        assert policy.should_retry(0) is True
        assert policy.should_retry(1) is True
        assert policy.should_retry(2) is True
        assert policy.should_retry(3) is False

    def test_exponential_delay(self):
        """Test exponential backoff delay."""
        policy = RetryPolicy(
            base_delay_seconds=1.0,
            exponential_base=2.0,
            max_delay_seconds=60.0
        )

        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
        assert policy.get_delay(3) == 8.0

    def test_max_delay_cap(self):
        """Test that delay is capped at max."""
        policy = RetryPolicy(
            base_delay_seconds=1.0,
            exponential_base=2.0,
            max_delay_seconds=10.0
        )

        assert policy.get_delay(10) == 10.0  # Capped at max


class TestStreamProcessor:
    """Tests for stream processor."""

    @pytest.fixture
    def mock_handler(self):
        """Create a mock message handler."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_processor_start_stop(self, mock_handler):
        """Test starting and stopping processor."""
        processor = StreamProcessor(
            processor_id="test_processor",
            handler=mock_handler
        )

        await processor.start()
        assert processor.state == StreamState.RUNNING

        await processor.stop()
        assert processor.state == StreamState.STOPPED

    @pytest.mark.asyncio
    async def test_processor_pause_resume(self, mock_handler):
        """Test pausing and resuming processor."""
        processor = StreamProcessor(
            processor_id="test_processor",
            handler=mock_handler
        )

        await processor.start()

        await processor.pause()
        assert processor.state == StreamState.PAUSED

        await processor.resume()
        assert processor.state == StreamState.RUNNING

        await processor.stop()

    @pytest.mark.asyncio
    async def test_submit_message(self, mock_handler, stream_message):
        """Test submitting a message."""
        processor = StreamProcessor(
            processor_id="test_processor",
            handler=mock_handler
        )

        result = await processor.submit(stream_message)

        assert result is True
        assert processor.metrics.messages_received == 1

    @pytest.mark.asyncio
    async def test_submit_filtered_message(self, mock_handler, stream_message):
        """Test that filtered messages are counted."""
        filter = StreamFilter(
            rules=[FilterRule(field="type", operator="eq", value="other_type")]
        )

        processor = StreamProcessor(
            processor_id="test_processor",
            handler=mock_handler,
            filter=filter
        )

        await processor.submit(stream_message)

        assert processor.metrics.messages_filtered == 1

    @pytest.mark.asyncio
    async def test_message_processing(self, mock_handler, stream_message):
        """Test full message processing flow."""
        processor = StreamProcessor(
            processor_id="test_processor",
            handler=mock_handler,
            batch_size=1,
            batch_timeout_seconds=0.1
        )

        await processor.start()
        await processor.submit(stream_message)

        # Wait for processing
        await asyncio.sleep(0.2)

        await processor.stop()

        assert mock_handler.called
        assert processor.metrics.messages_processed >= 1

    @pytest.mark.asyncio
    async def test_get_metrics(self, mock_handler, stream_message):
        """Test getting processor metrics."""
        processor = StreamProcessor(
            processor_id="test_processor",
            handler=mock_handler
        )

        await processor.submit(stream_message)

        metrics = processor.get_metrics()

        assert "messages_received" in metrics
        assert "messages_processed" in metrics
        assert "state" in metrics
        assert "buffer_utilization" in metrics

    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, stream_message):
        """Test messages going to dead letter queue after retries."""
        # Handler that always fails
        async def failing_handler(msg):
            raise Exception("Processing failed")

        processor = StreamProcessor(
            processor_id="test_processor",
            handler=failing_handler,
            retry_policy=RetryPolicy(max_retries=0),  # No retries
            batch_size=1,
            batch_timeout_seconds=0.1
        )

        await processor.start()
        await processor.submit(stream_message)

        # Wait for processing
        await asyncio.sleep(0.3)

        await processor.stop()

        dlq_messages = processor.get_dead_letter_messages()
        assert len(dlq_messages) >= 1


class TestStreamProcessorManager:
    """Tests for stream processor manager."""

    @pytest.fixture
    def manager(self):
        return StreamProcessorManager()

    @pytest.fixture
    def test_processor(self):
        return StreamProcessor(
            processor_id="test_proc",
            handler=AsyncMock()
        )

    @pytest.mark.asyncio
    async def test_register_processor(self, manager, test_processor):
        """Test registering a processor."""
        await manager.register_processor(test_processor)

        assert "test_proc" in manager.processors

    @pytest.mark.asyncio
    async def test_register_duplicate_processor_fails(self, manager, test_processor):
        """Test that registering duplicate processor fails."""
        await manager.register_processor(test_processor)

        with pytest.raises(ValueError):
            await manager.register_processor(test_processor)

    @pytest.mark.asyncio
    async def test_unregister_processor(self, manager, test_processor):
        """Test unregistering a processor."""
        await manager.register_processor(test_processor)
        await manager.unregister_processor("test_proc")

        assert "test_proc" not in manager.processors

    @pytest.mark.asyncio
    async def test_start_all(self, manager):
        """Test starting all processors."""
        proc1 = StreamProcessor(processor_id="proc1", handler=AsyncMock())
        proc2 = StreamProcessor(processor_id="proc2", handler=AsyncMock())

        await manager.register_processor(proc1)
        await manager.register_processor(proc2)

        await manager.start_all()

        assert proc1.state == StreamState.RUNNING
        assert proc2.state == StreamState.RUNNING

        await manager.stop_all()

    @pytest.mark.asyncio
    async def test_stop_all(self, manager):
        """Test stopping all processors."""
        proc1 = StreamProcessor(processor_id="proc1", handler=AsyncMock())
        proc2 = StreamProcessor(processor_id="proc2", handler=AsyncMock())

        await manager.register_processor(proc1)
        await manager.register_processor(proc2)
        await manager.start_all()

        await manager.stop_all()

        assert proc1.state == StreamState.STOPPED
        assert proc2.state == StreamState.STOPPED

    @pytest.mark.asyncio
    async def test_submit_to_processor(self, manager, test_processor, stream_message):
        """Test submitting to specific processor."""
        await manager.register_processor(test_processor)

        result = await manager.submit_to_processor("test_proc", stream_message)

        assert result is True

    @pytest.mark.asyncio
    async def test_submit_to_unknown_processor_fails(self, manager, stream_message):
        """Test that submitting to unknown processor fails."""
        with pytest.raises(ValueError):
            await manager.submit_to_processor("unknown", stream_message)

    @pytest.mark.asyncio
    async def test_broadcast(self, manager, stream_message):
        """Test broadcasting to all processors."""
        proc1 = StreamProcessor(processor_id="proc1", handler=AsyncMock())
        proc2 = StreamProcessor(processor_id="proc2", handler=AsyncMock())

        await manager.register_processor(proc1)
        await manager.register_processor(proc2)

        results = await manager.broadcast(stream_message)

        assert results["proc1"] is True
        assert results["proc2"] is True

    @pytest.mark.asyncio
    async def test_get_all_metrics(self, manager):
        """Test getting metrics from all processors."""
        proc1 = StreamProcessor(processor_id="proc1", handler=AsyncMock())
        proc2 = StreamProcessor(processor_id="proc2", handler=AsyncMock())

        await manager.register_processor(proc1)
        await manager.register_processor(proc2)

        metrics = manager.get_all_metrics()

        assert "proc1" in metrics
        assert "proc2" in metrics


class TestStreamMetrics:
    """Tests for stream metrics."""

    def test_average_processing_time_empty(self):
        """Test average processing time with no messages."""
        metrics = StreamMetrics()

        assert metrics.average_processing_time_ms == 0.0

    def test_average_processing_time(self):
        """Test average processing time calculation."""
        metrics = StreamMetrics()
        metrics.messages_processed = 10
        metrics.total_processing_time_ms = 100.0

        assert metrics.average_processing_time_ms == 10.0

    def test_throughput_no_start_time(self):
        """Test throughput with no start time."""
        metrics = StreamMetrics()

        assert metrics.throughput_per_second == 0.0

    def test_throughput_calculation(self):
        """Test throughput calculation."""
        metrics = StreamMetrics()
        metrics.stream_start_time = datetime.utcnow() - timedelta(seconds=10)
        metrics.messages_processed = 100

        assert metrics.throughput_per_second == pytest.approx(10.0, rel=0.1)

    def test_to_dict(self):
        """Test metrics conversion to dict."""
        metrics = StreamMetrics()
        metrics.messages_received = 100
        metrics.messages_processed = 90
        metrics.messages_dropped = 5

        result = metrics.to_dict()

        assert result["messages_received"] == 100
        assert result["messages_processed"] == 90
        assert result["messages_dropped"] == 5


class TestConvenienceFunctions:
    """Tests for convenience factory functions."""

    def test_create_sync_data_processor(self):
        """Test creating sync data processor."""
        handler = AsyncMock()
        processor = create_sync_data_processor(
            handler=handler,
            source_types=["insert", "update"],
            max_buffer_size=500
        )

        assert processor.processor_id.startswith("sync_data_")
        assert processor.batch_size == 10
        assert processor.backpressure.max_buffer_size == 500

    def test_create_event_processor(self):
        """Test creating event processor."""
        handler = AsyncMock()
        processor = create_event_processor(
            handler=handler,
            event_types=["created", "deleted"]
        )

        assert processor.processor_id.startswith("event_")
        assert processor.batch_size == 1


# =============================================================================
# Message Handling Tests
# =============================================================================

class TestMessageHandling:
    """Tests for message handling in connection manager."""

    @pytest.mark.asyncio
    async def test_handle_ping_message(self, connection_manager, mock_websocket):
        """Test handling ping message."""
        connection = await connection_manager.connect(mock_websocket)

        await connection_manager.handle_message(
            connection.connection_id,
            {
                "type": MessageType.PING.value,
                "payload": {},
                "message_id": "ping_001"
            }
        )

        # Should have sent a pong response
        pong_sent = any(
            msg.get("type") == MessageType.PONG.value
            for msg in mock_websocket.sent_messages
        )
        assert pong_sent

    @pytest.mark.asyncio
    async def test_handle_auth_message(self, connection_manager, mock_websocket):
        """Test handling auth message."""
        connection = await connection_manager.connect(mock_websocket)

        await connection_manager.handle_message(
            connection.connection_id,
            {
                "type": MessageType.AUTH.value,
                "payload": {
                    "token": "valid_token",
                    "tenant_id": "tenant_001",
                    "user_id": "user_001"
                }
            }
        )

        # Should have sent auth success
        auth_success_sent = any(
            msg.get("type") == MessageType.AUTH_SUCCESS.value
            for msg in mock_websocket.sent_messages
        )
        assert auth_success_sent

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, connection_manager, mock_websocket):
        """Test handling unknown message type."""
        connection = await connection_manager.connect(mock_websocket)

        await connection_manager.handle_message(
            connection.connection_id,
            {
                "type": "unknown_type",
                "payload": {}
            }
        )

        # Should have sent an error
        error_sent = any(
            msg.get("type") == MessageType.ERROR.value
            for msg in mock_websocket.sent_messages
        )
        assert error_sent


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
