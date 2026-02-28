"""
Integration tests for external service integrations with mocks.

Verifies that external service calls (email, file storage, third-party APIs)
are properly intercepted by mock services during testing, ensuring no real
external calls are made.

Requirements: 3.4, 12.4
Property 28: External Service Mocking
"""

import os
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.collaboration.notification_service import (
    NotificationService,
    NotificationChannel,
)
from src.collaboration.third_party_platform_adapter import (
    ThirdPartyPlatformAdapter,
    PlatformType,
    MTurkConnector,
    ScaleAIConnector,
    CustomRESTConnector,
)
from src.export.service import ExportService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_email_service():
    """Mock email service that records calls without sending."""
    service = AsyncMock()
    service.send = AsyncMock(return_value=True)
    service.send_calls = []

    async def _track_send(user_id, title, message):
        service.send_calls.append({
            "user_id": user_id,
            "title": title,
            "message": message,
        })
        return True

    service.send.side_effect = _track_send
    return service


@pytest.fixture
def mock_webhook_client():
    """Mock webhook client that records calls without posting."""
    client = AsyncMock()
    client.post = AsyncMock(return_value={"status": "ok"})
    client.post_calls = []

    async def _track_post(payload):
        client.post_calls.append(payload)
        return {"status": "ok"}

    client.post.side_effect = _track_post
    return client


@pytest.fixture
def notification_service(mock_email_service, mock_webhook_client):
    """NotificationService wired with mock email and webhook."""
    return NotificationService(
        db=None,
        email_service=mock_email_service,
        webhook_client=mock_webhook_client,
    )


@pytest.fixture
def platform_adapter():
    """ThirdPartyPlatformAdapter with no real DB."""
    return ThirdPartyPlatformAdapter(db=None)


@pytest.fixture
def export_service(tmp_path):
    """ExportService using a temporary directory."""
    return ExportService(export_dir=str(tmp_path / "exports"))


# ============================================================================
# 1. Email Service Integration with Mocks
# ============================================================================

class TestEmailServiceIntegration:
    """Test email service integration is properly mocked."""


    @pytest.mark.asyncio
    async def test_email_notification_uses_mock(
        self, notification_service, mock_email_service
    ):
        """Email channel delegates to mock service, not real SMTP."""
        user_id = str(uuid4())
        await notification_service.send_notification(
            user_id=user_id,
            title="Test Alert",
            message="This is a test",
            channels=[NotificationChannel.EMAIL],
        )

        mock_email_service.send.assert_awaited_once()
        assert len(mock_email_service.send_calls) == 1
        assert mock_email_service.send_calls[0]["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_task_assigned_email(
        self, notification_service, mock_email_service
    ):
        """Task assignment triggers email via mock service."""
        user_id = str(uuid4())
        task_id = str(uuid4())

        # Enable email channel for user
        await notification_service.set_preferences(
            user_id, {"channels": ["email"]}
        )
        result = await notification_service.notify_task_assigned(user_id, task_id)

        assert len(result) >= 1
        mock_email_service.send.assert_awaited()
        call = mock_email_service.send_calls[-1]
        assert call["user_id"] == user_id
        assert task_id in call["message"]

    @pytest.mark.asyncio
    async def test_review_completed_email(
        self, notification_service, mock_email_service
    ):
        """Review completion triggers email via mock service."""
        user_id = str(uuid4())
        annotation_id = str(uuid4())

        await notification_service.set_preferences(
            user_id, {"channels": ["email"]}
        )
        result = await notification_service.notify_review_completed(
            user_id, annotation_id, "approved"
        )

        assert len(result) >= 1
        mock_email_service.send.assert_awaited()

    @pytest.mark.asyncio
    async def test_quality_warning_email(
        self, notification_service, mock_email_service
    ):
        """Quality warning triggers email via mock service."""
        user_id = str(uuid4())
        await notification_service.set_preferences(
            user_id, {"channels": ["email"]}
        )
        result = await notification_service.send_quality_warning(
            user_id, accuracy=0.65, threshold=0.80
        )

        assert len(result) >= 1
        mock_email_service.send.assert_awaited()

    @pytest.mark.asyncio
    async def test_no_email_without_service(self):
        """Without email_service, email channel stores but doesn't send."""
        svc = NotificationService(db=None, email_service=None)
        user_id = str(uuid4())
        result = await svc.send_notification(
            user_id=user_id,
            title="No Email",
            message="Should not crash",
            channels=[NotificationChannel.EMAIL],
        )
        # Notification is still recorded in-app
        assert len(result) == 1
        assert result[0]["channel"] == "email"


# ============================================================================
# 2. File Storage Service Integration
# ============================================================================

class TestFileStorageIntegration:
    """Test file storage operations use local temp dirs, not real storage."""

    def test_export_service_uses_local_dir(self, export_service, tmp_path):
        """ExportService writes to local temp directory, not cloud storage."""
        export_dir = tmp_path / "exports"
        assert str(export_dir) == str(export_service.export_dir)

    def test_export_creates_directory_on_demand(self, tmp_path):
        """Export directory is created when needed."""
        export_dir = tmp_path / "new_exports"
        svc = ExportService(export_dir=str(export_dir))
        assert str(svc.export_dir) == str(export_dir)

    def test_list_exports_empty(self, export_service):
        """Listing exports on fresh service returns empty."""
        result = export_service.list_exports()
        assert result == []

    def test_delete_nonexistent_export(self, export_service):
        """Deleting a missing export returns False gracefully."""
        result = export_service.delete_export("nonexistent-id")
        assert result is False

    def test_start_export_records_job(self, export_service):
        """Starting an export records the job without real DB or storage."""
        from src.export.models import ExportRequest, ExportFormat

        request = ExportRequest(format=ExportFormat.JSON)
        export_id = export_service.start_export(request)

        assert export_id is not None
        assert isinstance(export_id, str)
        assert len(export_id) > 0

    def test_get_export_status_unknown(self, export_service):
        """Querying unknown export returns None."""
        result = export_service.get_export_status("unknown-id")
        assert result is None


# ============================================================================
# 3. Third-Party API Integrations
# ============================================================================

class TestThirdPartyAPIIntegration:
    """Test third-party platform integrations use mocks."""

    @pytest.mark.asyncio
    async def test_register_mturk_platform(self, platform_adapter):
        """Registering MTurk uses mock connector, not real AWS."""
        config = {
            "name": "test_mturk",
            "platform_type": "mturk",
            "api_key": "fake-key",
            "api_secret": "fake-secret",
        }
        result = await platform_adapter.register_platform(config)

        assert result["name"] == "test_mturk"
        assert result["status"] == "connected"
        assert "test_mturk" in platform_adapter.platforms

    @pytest.mark.asyncio
    async def test_register_scale_ai_platform(self, platform_adapter):
        """Registering Scale AI uses mock connector."""
        config = {
            "name": "test_scale",
            "platform_type": "scale_ai",
            "api_key": "fake-key",
        }
        result = await platform_adapter.register_platform(config)

        assert result["name"] == "test_scale"
        assert result["status"] == "connected"

    @pytest.mark.asyncio
    async def test_sync_task_to_mturk(self, platform_adapter):
        """Syncing a task to MTurk returns mock result, no real API call."""
        await platform_adapter.register_platform({
            "name": "mturk",
            "platform_type": "mturk",
        })
        task = {"id": str(uuid4()), "platform": "mturk", "title": "Test"}
        result = await platform_adapter.sync_task(task)

        assert result["success"] is True
        assert result["platform"] == "mturk"
        assert result["external_task_id"] is not None

    @pytest.mark.asyncio
    async def test_sync_task_to_unregistered_platform(self, platform_adapter):
        """Syncing to unregistered platform fails gracefully."""
        task = {"id": str(uuid4()), "platform": "unknown", "title": "Test"}
        result = await platform_adapter.sync_task(task)

        assert result["success"] is False
        assert "not configured" in result["message"]

    @pytest.mark.asyncio
    async def test_internal_task_skips_sync(self, platform_adapter):
        """Internal tasks skip external sync entirely."""
        task = {"id": str(uuid4()), "platform": "internal"}
        result = await platform_adapter.sync_task(task)

        assert result["success"] is True
        assert result["platform"] == "internal"
        assert result["external_task_id"] is None

    @pytest.mark.asyncio
    async def test_fetch_results_from_platform(self, platform_adapter):
        """Fetching results uses mock connector."""
        await platform_adapter.register_platform({
            "name": "scale",
            "platform_type": "scale_ai",
        })
        results = await platform_adapter.fetch_results("task-1", "scale")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_platform_health_check(self, platform_adapter):
        """Health check uses mock, not real external endpoint."""
        await platform_adapter.register_platform({
            "name": "mturk",
            "platform_type": "mturk",
        })
        result = await platform_adapter.test_connection("mturk")

        assert result["success"] is True
        assert result["platform"] == "mturk"

    @pytest.mark.asyncio
    async def test_unregister_platform(self, platform_adapter):
        """Unregistering removes platform from adapter."""
        await platform_adapter.register_platform({
            "name": "temp",
            "platform_type": "custom",
        })
        assert "temp" in platform_adapter.platforms

        removed = await platform_adapter.unregister_platform("temp")
        assert removed is True
        assert "temp" not in platform_adapter.platforms

    @pytest.mark.asyncio
    async def test_get_all_platforms(self, platform_adapter):
        """Listing platforms returns all registered mocks."""
        for name in ["p1", "p2"]:
            await platform_adapter.register_platform({
                "name": name,
                "platform_type": "custom",
            })
        platforms = await platform_adapter.get_all_platforms()
        assert len(platforms) == 2


# ============================================================================
# 4. Webhook Integration with Mocks
# ============================================================================

class TestWebhookIntegration:
    """Test webhook calls are intercepted by mocks."""

    @pytest.mark.asyncio
    async def test_webhook_notification_uses_mock(
        self, notification_service, mock_webhook_client
    ):
        """Webhook channel delegates to mock client, not real HTTP."""
        user_id = str(uuid4())
        await notification_service.send_notification(
            user_id=user_id,
            title="Webhook Test",
            message="Payload test",
            data={"key": "value"},
            channels=[NotificationChannel.WEBHOOK],
        )

        mock_webhook_client.post.assert_awaited_once()
        payload = mock_webhook_client.post_calls[0]
        assert payload["user_id"] == user_id
        assert payload["title"] == "Webhook Test"

    @pytest.mark.asyncio
    async def test_batch_webhook_notifications(
        self, notification_service, mock_webhook_client
    ):
        """Batch notifications all go through mock webhook."""
        user_ids = [str(uuid4()) for _ in range(3)]
        for uid in user_ids:
            await notification_service.set_preferences(
                uid, {"channels": ["webhook"]}
            )

        result = await notification_service.batch_notify(
            user_ids=user_ids,
            title="Batch Alert",
            message="Batch message",
        )

        assert len(result) == 3
        assert mock_webhook_client.post.await_count == 3


# ============================================================================
# 5. Verify Mock Services Are Used (Property 28)
# ============================================================================

class TestMockServiceVerification:
    """Verify that mock services intercept all external calls."""

    @pytest.mark.asyncio
    async def test_email_handler_uses_smtplib_mock(self):
        """EmailNotificationHandler's SMTP calls are mockable."""
        from src.monitoring.multi_channel_notification import (
            EmailNotificationHandler,
            NotificationRecord,
            NotificationChannel as MCChannel,
            NotificationStatus,
            NotificationPriority,
        )

        handler = EmailNotificationHandler({
            "host": "localhost",
            "port": 587,
            "username": "test",
            "password": "test",
        })

        record = NotificationRecord(
            id=uuid4(),
            alert_id=uuid4(),
            channel=MCChannel.EMAIL,
            recipient="test@example.com",
            subject="Test",
            content="Body",
            priority=NotificationPriority.NORMAL,
            status=NotificationStatus.PENDING,
            created_at=datetime.now(),
        )

        with patch("src.monitoring.multi_channel_notification.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            result = await handler.send_notification(record)

            assert result is True
            mock_smtp.assert_called_once_with("localhost", 587)
            mock_server.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_handler_uses_aiohttp_mock(self):
        """WebhookNotificationHandler's HTTP calls are mockable."""
        from src.monitoring.multi_channel_notification import (
            WebhookNotificationHandler,
            NotificationRecord,
            NotificationChannel as MCChannel,
            NotificationStatus,
            NotificationPriority,
        )

        handler = WebhookNotificationHandler({
            "url": "https://hooks.example.com/test",
            "auth_token": "fake-token",
        })

        record = NotificationRecord(
            id=uuid4(),
            alert_id=uuid4(),
            channel=MCChannel.WEBHOOK,
            recipient="https://hooks.example.com/test",
            subject="Test",
            content="Body",
            priority=NotificationPriority.NORMAL,
            status=NotificationStatus.PENDING,
            created_at=datetime.now(),
            metadata={},
        )

        # Build a proper nested async-context-manager mock for aiohttp
        mock_response = MagicMock()
        mock_response.status = 200

        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_cm)

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.monitoring.multi_channel_notification.aiohttp.ClientSession",
            return_value=mock_session_cm,
        ):
            result = await handler.send_notification(record)

        assert result is True
        assert record.status == NotificationStatus.SENT

    @pytest.mark.asyncio
    async def test_mturk_connector_no_real_aws_call(self):
        """MTurkConnector methods return mock data, no real AWS SDK call."""
        connector = MTurkConnector({"name": "test_mturk"})

        task = {"id": "task-123", "title": "Test HIT"}
        result = await connector.create_task(task)

        assert result["success"] is True
        assert result["platform"] == "mturk"
        # Verify it's a mock external ID, not a real AWS HIT ID
        assert result["external_task_id"].startswith("mturk_")

    @pytest.mark.asyncio
    async def test_scale_ai_connector_no_real_api_call(self):
        """ScaleAIConnector methods return mock data."""
        connector = ScaleAIConnector({"name": "test_scale"})

        result = await connector.create_task({"id": "task-456"})
        assert result["success"] is True
        assert result["external_task_id"].startswith("scale_")

    @pytest.mark.asyncio
    async def test_custom_rest_connector_no_real_http(self):
        """CustomRESTConnector returns mock data without HTTP calls."""
        connector = CustomRESTConnector({
            "name": "custom_platform",
            "endpoint": "https://api.example.com",
        })

        result = await connector.create_task({"id": "task-789"})
        assert result["success"] is True
        assert result["external_task_id"].startswith("custom_")

    @pytest.mark.asyncio
    async def test_no_real_smtp_in_test_env(self):
        """Confirm test environment doesn't connect to real SMTP."""
        assert os.environ.get("APP_ENV") == "test"
        # In test env, email service should always be mocked
        svc = NotificationService(db=None, email_service=None)
        # Without email_service, no SMTP connection is attempted
        result = await svc.send_notification(
            user_id="user-1",
            title="Test",
            message="No SMTP",
            channels=[NotificationChannel.EMAIL],
        )
        assert len(result) == 1  # Recorded but not sent externally

    @pytest.mark.asyncio
    async def test_notification_preferences_disable_external(self):
        """Disabled preferences prevent external service calls."""
        mock_email = AsyncMock()
        mock_email.send = AsyncMock()
        svc = NotificationService(db=None, email_service=mock_email)

        user_id = str(uuid4())
        await svc.set_preferences(user_id, {
            "channels": ["in_app"],
            "task_assigned": False,
        })

        result = await svc.notify_task_assigned(user_id, "task-1")
        assert result == []
        mock_email.send.assert_not_awaited()
