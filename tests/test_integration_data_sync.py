"""
Integration tests for data synchronization.

Tests data sync between frontend and backend, real-time updates
with WebSocket, conflict resolution, and offline data handling.

Requirements: 3.3
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID as PyUUID
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, INET

from src.database.connection import Base, get_db_session
from src.database.models import (
    TaskModel, TaskStatus, TaskPriority,
    AnnotationType, DocumentModel,
)
from src.security.models import UserModel
from src.security.controller import SecurityController
from src.sync.conflict_resolver import (
    ConflictDetector, ConflictResolver, ConflictManager,
    ConflictContext, ConflictRecord, ConflictType,
    ConflictStatus, ResolutionStrategy, ResolutionPolicy,
)
from src.sync.websocket.ws_server import (
    WebSocketConnectionManager, WebSocketMessage, MessageType,
    ConnectionState, SubscriptionType, ConnectionInfo,
)


# ---------------------------------------------------------------------------
# SQLite compatibility
# ---------------------------------------------------------------------------

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TENANT_ID = "test_tenant"
JWT_SECRET = "test-secret-key-do-not-use-in-production"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_engine():
    """Create an isolated SQLite in-memory engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _seed_user(
    session: Session,
    *,
    username: str = "syncuser",
    email: str = "sync@example.com",
    role: str = "admin",
) -> UserModel:
    """Insert a user and return the ORM instance."""
    sc = SecurityController(secret_key=JWT_SECRET)
    user = UserModel(
        id=uuid4(),
        username=username,
        email=email,
        password_hash=sc.hash_password("TestPass123!"),
        full_name=f"Test {username.title()}",
        role=role,
        tenant_id=TENANT_ID,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _build_app(session_factory, current_user_obj):
    """Build a test FastAPI app with tasks router."""
    from src.api.auth_simple import get_current_user as get_current_user_simple
    from src.api.tasks import router as tasks_router
    from src.api.auth import (
        router as auth_router,
        get_current_user as get_current_user_auth,
    )

    app = FastAPI()
    app.include_router(tasks_router)
    app.include_router(auth_router)

    def _override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    async def _override_user():
        return current_user_obj

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_current_user_simple] = _override_user
    app.dependency_overrides[get_current_user_auth] = _override_user

    return app


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def sync_env():
    """
    Isolated test environment for data sync integration tests.

    Yields (client, session_factory, user).
    """
    engine = _create_engine()
    sf = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with sf() as session:
        user = _seed_user(session)

    from src.api.auth_simple import SimpleUser
    fake_user = SimpleUser(
        user_id=str(user.id),
        email=user.email,
        username=user.username,
        name=user.full_name,
        is_active=True,
        is_superuser=False,
    )
    fake_user.tenant_id = TENANT_ID

    app = _build_app(sf, fake_user)
    client = TestClient(app)

    yield client, sf, user

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ===========================================================================
# 1. Data Sync Between Frontend and Backend (API-based data flow)
# ===========================================================================

class TestDataSyncFrontendBackend:
    """Test data synchronization between frontend API calls and backend DB."""

    def test_create_via_api_persists_to_db(self, sync_env):
        """Data submitted via API is persisted in the database."""
        client, sf, _ = sync_env
        resp = client.post("/api/tasks", json={
            "name": "Sync task alpha",
            "description": "Created from frontend",
            "total_items": 25,
            "priority": "high",
        })
        assert resp.status_code == 200
        task_id = resp.json()["id"]

        with sf() as session:
            task = session.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task is not None
            assert task.name == "Sync task alpha"
            assert task.total_items == 25

    def test_update_via_api_reflects_in_db(self, sync_env):
        """Updates through the API are reflected in the database."""
        client, sf, _ = sync_env
        create = client.post("/api/tasks", json={
            "name": "Before update",
            "total_items": 10,
        })
        task_id = create.json()["id"]

        client.patch(f"/api/tasks/{task_id}", json={
            "name": "After update",
            "status": "in_progress",
        })

        with sf() as session:
            task = session.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.name == "After update"

    def test_delete_via_api_removes_from_db(self, sync_env):
        """Deleting via API removes the record from the database."""
        client, sf, _ = sync_env
        create = client.post("/api/tasks", json={
            "name": "To be deleted",
            "total_items": 1,
        })
        task_id = create.json()["id"]

        client.delete(f"/api/tasks/{task_id}")

        with sf() as session:
            assert session.query(TaskModel).filter_by(
                id=PyUUID(task_id)
            ).first() is None

    def test_read_after_write_consistency(self, sync_env):
        """GET immediately after POST returns the created data."""
        client, _, _ = sync_env
        create = client.post("/api/tasks", json={
            "name": "Consistency check",
            "total_items": 5,
        })
        task_id = create.json()["id"]

        get_resp = client.get(f"/api/tasks/{task_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "Consistency check"

    def test_batch_create_all_persisted(self, sync_env):
        """Multiple sequential creates all persist correctly."""
        client, sf, _ = sync_env
        ids = []
        for i in range(5):
            resp = client.post("/api/tasks", json={
                "name": f"Batch item {i}",
                "total_items": i + 1,
            })
            assert resp.status_code == 200
            ids.append(resp.json()["id"])

        with sf() as session:
            count = session.query(TaskModel).filter(
                TaskModel.id.in_([PyUUID(tid) for tid in ids])
            ).count()
            assert count == 5

    def test_data_integrity_after_update_cycle(self, sync_env):
        """Data integrity is maintained through create-update-read cycle."""
        client, sf, _ = sync_env
        create = client.post("/api/tasks", json={
            "name": "Integrity test",
            "description": "Original description",
            "total_items": 100,
        })
        task_id = create.json()["id"]

        client.patch(f"/api/tasks/{task_id}", json={
            "description": "Updated description",
        })

        with sf() as session:
            task = session.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.name == "Integrity test"
            assert task.total_items == 100


# ===========================================================================
# 2. Real-Time Updates with WebSocket
# ===========================================================================

class TestWebSocketRealTimeUpdates:
    """Test real-time update capabilities via WebSocket connection manager."""

    @pytest.fixture()
    def ws_manager(self):
        """Provide a fresh WebSocketConnectionManager."""
        return WebSocketConnectionManager(max_connections_per_tenant=50)

    @pytest.fixture()
    def mock_ws(self):
        """Create a mock WebSocket that records sent messages."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_json = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_registers_connection(self, ws_manager, mock_ws):
        """Connecting a WebSocket registers it in the manager."""
        conn = await ws_manager.connect(mock_ws, connection_id="conn-1")

        assert conn.connection_id == "conn-1"
        assert conn.state == ConnectionState.CONNECTED
        assert ws_manager.get_connection("conn-1") is not None

    @pytest.mark.asyncio
    async def test_authenticate_updates_state(self, ws_manager, mock_ws):
        """Authenticating a connection updates its state and tenant."""
        await ws_manager.connect(mock_ws, connection_id="conn-auth")

        result = await ws_manager.authenticate(
            "conn-auth", token="valid-token",
            tenant_id=TENANT_ID, user_id="user-1",
        )

        assert result is True
        conn = ws_manager.get_connection("conn-auth")
        assert conn.state == ConnectionState.AUTHENTICATED
        assert conn.tenant_id == TENANT_ID

    @pytest.mark.asyncio
    async def test_subscribe_to_data_changes(self, ws_manager, mock_ws):
        """Authenticated connection can subscribe to data change events."""
        await ws_manager.connect(mock_ws, connection_id="conn-sub")
        await ws_manager.authenticate(
            "conn-sub", token="t", tenant_id=TENANT_ID, user_id="u1",
        )

        result = await ws_manager.subscribe(
            "conn-sub", SubscriptionType.DATA_CHANGES,
        )

        assert result is True
        conn = ws_manager.get_connection("conn-sub")
        assert conn.state == ConnectionState.SUBSCRIBED
        assert len(conn.subscriptions) == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_tenant(self, ws_manager, mock_ws):
        """Broadcast reaches all connections of a tenant."""
        ws1, ws2 = AsyncMock(), AsyncMock()
        for ws in (ws1, ws2):
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.send_text = AsyncMock()

        await ws_manager.connect(ws1, connection_id="t1-c1")
        await ws_manager.connect(ws2, connection_id="t1-c2")
        await ws_manager.authenticate("t1-c1", "tok", TENANT_ID, "u1")
        await ws_manager.authenticate("t1-c2", "tok", TENANT_ID, "u2")

        msg = WebSocketMessage(
            type=MessageType.DATA_UPDATE,
            payload={"entity": "task", "action": "created"},
        )
        sent = await ws_manager.broadcast_to_tenant(TENANT_ID, msg)

        assert sent == 2

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, ws_manager, mock_ws):
        """Disconnecting removes the connection from the manager."""
        await ws_manager.connect(mock_ws, connection_id="conn-dc")
        await ws_manager.disconnect("conn-dc")

        assert ws_manager.get_connection("conn-dc") is None

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_subscribe(self, ws_manager, mock_ws):
        """An unauthenticated connection cannot subscribe."""
        await ws_manager.connect(mock_ws, connection_id="conn-noauth")

        result = await ws_manager.subscribe(
            "conn-noauth", SubscriptionType.DATA_CHANGES,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_to_subscription(self, ws_manager):
        """Broadcast targets only connections subscribed to a specific type."""
        ws_sub = AsyncMock()
        ws_sub.accept = AsyncMock()
        ws_sub.send_json = AsyncMock()
        ws_sub.send_text = AsyncMock()

        ws_nosub = AsyncMock()
        ws_nosub.accept = AsyncMock()
        ws_nosub.send_json = AsyncMock()
        ws_nosub.send_text = AsyncMock()

        await ws_manager.connect(ws_sub, connection_id="sub-yes")
        await ws_manager.connect(ws_nosub, connection_id="sub-no")
        await ws_manager.authenticate("sub-yes", "t", TENANT_ID, "u1")
        await ws_manager.authenticate("sub-no", "t", TENANT_ID, "u2")
        await ws_manager.subscribe("sub-yes", SubscriptionType.CONFLICTS)

        msg = WebSocketMessage(
            type=MessageType.DATA_UPDATE,
            payload={"conflict": "detected"},
        )
        sent = await ws_manager.broadcast_to_subscription(
            SubscriptionType.CONFLICTS, TENANT_ID, msg,
        )

        assert sent == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_receiving(self, ws_manager):
        """After unsubscribing, connection no longer receives broadcasts."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.send_text = AsyncMock()

        await ws_manager.connect(ws, connection_id="unsub-test")
        await ws_manager.authenticate("unsub-test", "t", TENANT_ID, "u1")
        await ws_manager.subscribe("unsub-test", SubscriptionType.ALERTS)
        await ws_manager.unsubscribe("unsub-test", SubscriptionType.ALERTS)

        msg = WebSocketMessage(
            type=MessageType.DATA_UPDATE,
            payload={"alert": "test"},
        )
        sent = await ws_manager.broadcast_to_subscription(
            SubscriptionType.ALERTS, TENANT_ID, msg,
        )

        assert sent == 0

    @pytest.mark.asyncio
    async def test_connection_stats(self, ws_manager, mock_ws):
        """Manager reports accurate connection statistics."""
        await ws_manager.connect(mock_ws, connection_id="stats-1")
        stats = ws_manager.get_stats()

        assert stats["total_connections"] >= 1


# ===========================================================================
# 3. Conflict Resolution
# ===========================================================================

class TestConflictResolution:
    """Test conflict detection and resolution for concurrent data modifications."""

    def _make_context(self, table="tasks", operation="update"):
        """Create a ConflictContext for testing."""
        return ConflictContext(
            sync_id="sync-1",
            source_id="source-1",
            target_id="target-1",
            table=table,
            operation=operation,
        )

    # -- Detection ----------------------------------------------------------

    @pytest.mark.asyncio
    async def test_no_conflict_when_target_is_none(self):
        """No conflict is detected for a new record (no target data)."""
        detector = ConflictDetector()
        ctx = self._make_context()

        result = await detector.detect(ctx, {"name": "new"}, None)

        assert result is None

    @pytest.mark.asyncio
    async def test_content_conflict_detected(self):
        """Content differences between source and target trigger a conflict."""
        detector = ConflictDetector()
        ctx = self._make_context()

        result = await detector.detect(
            ctx,
            {"name": "updated", "status": "active"},
            {"name": "original", "status": "active"},
        )

        assert result is not None
        assert result.conflict_type == ConflictType.CONCURRENT_UPDATE
        assert result.status == ConflictStatus.DETECTED

    @pytest.mark.asyncio
    async def test_version_conflict_detected(self):
        """Stale version in source triggers a version conflict."""
        detector = ConflictDetector()
        detector.configure_table("tasks", version_field="version")
        ctx = self._make_context()

        result = await detector.detect(
            ctx,
            {"name": "src", "version": 1},
            {"name": "tgt", "version": 2},
        )

        assert result is not None
        assert result.conflict_type == ConflictType.CONCURRENT_UPDATE

    @pytest.mark.asyncio
    async def test_timestamp_conflict_detected(self):
        """Older source timestamp triggers a stale-update conflict."""
        detector = ConflictDetector()
        ctx = self._make_context()
        old_ts = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        new_ts = datetime.utcnow().isoformat()

        result = await detector.detect(
            ctx,
            {"name": "src", "updated_at": old_ts},
            {"name": "tgt", "updated_at": new_ts},
        )

        assert result is not None
        assert result.conflict_type == ConflictType.STALE_UPDATE

    @pytest.mark.asyncio
    async def test_delete_update_conflict(self):
        """Deleting a modified record triggers a delete-update conflict."""
        detector = ConflictDetector()
        ctx = self._make_context(operation="delete")

        result = await detector.detect(
            ctx,
            {"name": "to-delete"},
            {"name": "modified-target"},
        )

        assert result is not None
        assert result.conflict_type == ConflictType.DELETE_UPDATE

    # -- Resolution strategies ----------------------------------------------

    @pytest.mark.asyncio
    async def test_last_write_wins_strategy(self):
        """LAST_WRITE_WINS resolves by keeping source data."""
        policy = ResolutionPolicy(
            name="lww",
            default_strategy=ResolutionStrategy.LAST_WRITE_WINS,
        )
        resolver = ConflictResolver(policy)
        ctx = self._make_context()
        conflict = ConflictRecord(
            id=str(uuid4()),
            conflict_type=ConflictType.CONCURRENT_UPDATE,
            status=ConflictStatus.DETECTED,
            context=ctx,
            source_data={"name": "source-wins"},
            target_data={"name": "target-loses"},
        )

        resolved = await resolver.resolve(conflict)

        assert resolved.status == ConflictStatus.RESOLVED
        assert resolved.resolved_data["name"] == "source-wins"

    @pytest.mark.asyncio
    async def test_first_write_wins_strategy(self):
        """FIRST_WRITE_WINS resolves by keeping target data."""
        policy = ResolutionPolicy(
            name="fww",
            default_strategy=ResolutionStrategy.FIRST_WRITE_WINS,
        )
        resolver = ConflictResolver(policy)
        ctx = self._make_context()
        conflict = ConflictRecord(
            id=str(uuid4()),
            conflict_type=ConflictType.CONCURRENT_UPDATE,
            status=ConflictStatus.DETECTED,
            context=ctx,
            source_data={"name": "source"},
            target_data={"name": "target-wins"},
        )

        resolved = await resolver.resolve(conflict)

        assert resolved.status == ConflictStatus.RESOLVED
        assert resolved.resolved_data["name"] == "target-wins"

    @pytest.mark.asyncio
    async def test_merge_deep_strategy(self):
        """MERGE_DEEP merges nested dictionaries from source into target."""
        policy = ResolutionPolicy(
            name="merge",
            default_strategy=ResolutionStrategy.MERGE_DEEP,
        )
        resolver = ConflictResolver(policy)
        ctx = self._make_context()
        conflict = ConflictRecord(
            id=str(uuid4()),
            conflict_type=ConflictType.CONCURRENT_UPDATE,
            status=ConflictStatus.DETECTED,
            context=ctx,
            source_data={"meta": {"a": 1, "b": 2}},
            target_data={"meta": {"a": 0, "c": 3}},
        )

        resolved = await resolver.resolve(conflict)

        assert resolved.status == ConflictStatus.RESOLVED
        merged = resolved.resolved_data["meta"]
        assert merged["a"] == 1  # source overrides
        assert merged["b"] == 2  # source-only key
        assert merged["c"] == 3  # target-only key preserved

    @pytest.mark.asyncio
    async def test_manual_resolution_strategy(self):
        """MANUAL strategy sets conflict to PENDING_MANUAL."""
        policy = ResolutionPolicy(
            name="manual",
            default_strategy=ResolutionStrategy.MANUAL,
        )
        resolver = ConflictResolver(policy)
        ctx = self._make_context()
        conflict = ConflictRecord(
            id=str(uuid4()),
            conflict_type=ConflictType.CONCURRENT_UPDATE,
            status=ConflictStatus.DETECTED,
            context=ctx,
            source_data={"name": "src"},
            target_data={"name": "tgt"},
        )

        resolved = await resolver.resolve(conflict)

        assert resolved.status == ConflictStatus.PENDING_MANUAL

    @pytest.mark.asyncio
    async def test_manual_resolve_by_user(self):
        """A pending conflict can be manually resolved by a user."""
        resolver = ConflictResolver()
        ctx = self._make_context()
        conflict = ConflictRecord(
            id=str(uuid4()),
            conflict_type=ConflictType.CONCURRENT_UPDATE,
            status=ConflictStatus.PENDING_MANUAL,
            context=ctx,
            source_data={"name": "src"},
            target_data={"name": "tgt"},
        )

        resolved = await resolver.resolve_manually(
            conflict,
            resolved_data={"name": "user-choice"},
            user_id="admin-1",
            reason="Picked the better name",
        )

        assert resolved.status == ConflictStatus.RESOLVED
        assert resolved.resolved_data["name"] == "user-choice"
        assert resolved.resolved_by == "admin-1"

    # -- ConflictManager integration ----------------------------------------

    @pytest.mark.asyncio
    async def test_manager_detects_and_resolves(self):
        """ConflictManager detects and auto-resolves a conflict."""
        manager = ConflictManager()
        policy = ResolutionPolicy(
            name="auto",
            default_strategy=ResolutionStrategy.LAST_WRITE_WINS,
        )
        manager.configure_resolver("auto", policy)
        ctx = self._make_context()

        result = await manager.process(
            "auto", ctx,
            source_data={"name": "new-value"},
            target_data={"name": "old-value"},
        )

        assert result is not None
        assert result.status == ConflictStatus.RESOLVED
        assert manager.stats["total_detected"] == 1
        assert manager.stats["total_resolved"] == 1

    @pytest.mark.asyncio
    async def test_manager_tracks_pending_manual(self):
        """ConflictManager tracks conflicts pending manual resolution."""
        manager = ConflictManager()
        policy = ResolutionPolicy(
            name="manual",
            default_strategy=ResolutionStrategy.MANUAL,
        )
        manager.configure_resolver("manual", policy)
        ctx = self._make_context()

        await manager.process(
            "manual", ctx,
            source_data={"name": "a"},
            target_data={"name": "b"},
        )

        pending = manager.get_pending_conflicts()
        assert len(pending) == 1
        assert pending[0].status == ConflictStatus.PENDING_MANUAL

    @pytest.mark.asyncio
    async def test_manager_event_handlers_called(self):
        """ConflictManager emits events to registered handlers."""
        manager = ConflictManager()
        policy = ResolutionPolicy(
            name="auto",
            default_strategy=ResolutionStrategy.LAST_WRITE_WINS,
        )
        manager.configure_resolver("auto", policy)

        events_received = []
        manager.on_event("conflict_detected", lambda c: events_received.append("detected"))
        manager.on_event("conflict_resolved", lambda c: events_received.append("resolved"))

        ctx = self._make_context()
        await manager.process(
            "auto", ctx,
            source_data={"x": 1},
            target_data={"x": 2},
        )

        assert "detected" in events_received
        assert "resolved" in events_received


# ===========================================================================
# 4. Offline Data Handling and Reconnection
# ===========================================================================

class TestOfflineDataHandling:
    """Test offline data handling, queuing, and reconnection scenarios."""

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_subscriptions(self):
        """Disconnecting removes all subscriptions for that connection."""
        manager = WebSocketConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        await manager.connect(ws, connection_id="offline-1")
        await manager.authenticate("offline-1", "t", TENANT_ID, "u1")
        await manager.subscribe("offline-1", SubscriptionType.DATA_CHANGES)
        await manager.subscribe("offline-1", SubscriptionType.ALERTS)

        await manager.disconnect("offline-1")

        # Broadcasts should reach zero connections now
        msg = WebSocketMessage(
            type=MessageType.DATA_UPDATE, payload={"x": 1},
        )
        sent = await manager.broadcast_to_subscription(
            SubscriptionType.DATA_CHANGES, TENANT_ID, msg,
        )
        assert sent == 0

    @pytest.mark.asyncio
    async def test_reconnect_requires_reauthentication(self):
        """After reconnecting, the client must authenticate again."""
        manager = WebSocketConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()

        # First session
        await manager.connect(ws, connection_id="recon-1")
        await manager.authenticate("recon-1", "t", TENANT_ID, "u1")
        await manager.disconnect("recon-1")

        # Reconnect with new connection
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        ws2.send_text = AsyncMock()

        conn = await manager.connect(ws2, connection_id="recon-2")
        assert conn.state == ConnectionState.CONNECTED  # not authenticated

        # Cannot subscribe without auth
        result = await manager.subscribe("recon-2", SubscriptionType.DATA_CHANGES)
        assert result is False

    @pytest.mark.asyncio
    async def test_reconnect_can_resubscribe(self):
        """After reconnecting and re-authenticating, subscriptions work."""
        manager = WebSocketConnectionManager()

        def _mock_ws():
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.send_text = AsyncMock()
            ws.close = AsyncMock()
            return ws

        # First session
        ws1 = _mock_ws()
        await manager.connect(ws1, connection_id="resub-1")
        await manager.authenticate("resub-1", "t", TENANT_ID, "u1")
        await manager.subscribe("resub-1", SubscriptionType.SYNC_JOB)
        await manager.disconnect("resub-1")

        # Reconnect
        ws2 = _mock_ws()
        await manager.connect(ws2, connection_id="resub-2")
        await manager.authenticate("resub-2", "t", TENANT_ID, "u1")
        result = await manager.subscribe("resub-2", SubscriptionType.SYNC_JOB)
        assert result is True

        msg = WebSocketMessage(
            type=MessageType.SYNC_EVENT, payload={"job": "running"},
        )
        sent = await manager.broadcast_to_subscription(
            SubscriptionType.SYNC_JOB, TENANT_ID, msg,
        )
        assert sent == 1

    def test_offline_changes_applied_on_sync(self, sync_env):
        """Changes queued while offline can be applied when back online."""
        client, sf, user = sync_env

        # Simulate "offline" changes as a batch of operations
        offline_queue = [
            {"name": "Offline task 1", "total_items": 10},
            {"name": "Offline task 2", "total_items": 20},
            {"name": "Offline task 3", "total_items": 30},
        ]

        # "Reconnect" — apply queued changes
        created_ids = []
        for payload in offline_queue:
            resp = client.post("/api/tasks", json=payload)
            assert resp.status_code == 200
            created_ids.append(resp.json()["id"])

        # Verify all persisted
        with sf() as session:
            count = session.query(TaskModel).filter(
                TaskModel.id.in_([PyUUID(tid) for tid in created_ids])
            ).count()
            assert count == 3

    def test_offline_update_conflict_with_server(self, sync_env):
        """An offline update that conflicts with a server change is detectable."""
        client, sf, user = sync_env

        # Create a task (server state)
        resp = client.post("/api/tasks", json={
            "name": "Server version",
            "total_items": 5,
        })
        task_id = resp.json()["id"]

        # Server updates the task while client is "offline"
        client.patch(f"/api/tasks/{task_id}", json={"name": "Server updated"})

        # Client comes back online with a stale update
        # The conflict detector can identify this
        detector = ConflictDetector()
        detector.configure_table("tasks", timestamp_field="updated_at")

        with sf() as session:
            server_task = session.query(TaskModel).filter_by(
                id=PyUUID(task_id)
            ).first()
            server_name = server_task.name

        # Client's offline version is stale
        offline_data = {"name": "Offline edit", "status": "pending"}
        server_data = {"name": server_name, "status": "pending"}

        loop = asyncio.new_event_loop()
        try:
            ctx = ConflictContext(
                sync_id="offline-sync",
                source_id="client",
                target_id="server",
                table="tasks",
                operation="update",
            )
            conflict = loop.run_until_complete(
                detector.detect(ctx, offline_data, server_data)
            )
        finally:
            loop.close()

        # Content differs → conflict detected
        assert conflict is not None

    @pytest.mark.asyncio
    async def test_tenant_isolation_during_broadcast(self):
        """Broadcasts to one tenant do not leak to another tenant."""
        manager = WebSocketConnectionManager()

        def _mock_ws():
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.send_text = AsyncMock()
            return ws

        ws_t1 = _mock_ws()
        ws_t2 = _mock_ws()

        await manager.connect(ws_t1, connection_id="t1-conn")
        await manager.connect(ws_t2, connection_id="t2-conn")
        await manager.authenticate("t1-conn", "t", "tenant_A", "u1")
        await manager.authenticate("t2-conn", "t", "tenant_B", "u2")

        msg = WebSocketMessage(
            type=MessageType.DATA_UPDATE,
            payload={"secret": "tenant_A_only"},
        )
        sent = await manager.broadcast_to_tenant("tenant_A", msg)

        assert sent == 1
        # tenant_B's websocket should not have received the message
        # (only the connect ack + auth success were sent to ws_t2)

    @pytest.mark.asyncio
    async def test_max_connections_per_tenant_enforced(self):
        """Exceeding max connections per tenant is rejected."""
        manager = WebSocketConnectionManager(max_connections_per_tenant=2)

        mocks = []
        for i in range(3):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.send_text = AsyncMock()
            mocks.append(ws)
            await manager.connect(ws, connection_id=f"limit-{i}")

        # First two should authenticate fine
        assert await manager.authenticate("limit-0", "t", TENANT_ID, "u0")
        assert await manager.authenticate("limit-1", "t", TENANT_ID, "u1")

        # Third should be rejected
        result = await manager.authenticate("limit-2", "t", TENANT_ID, "u2")
        assert result is False
