"""
WebhookManager — Webhook configuration CRUD (data storage only).

MVP reserved module: stores webhook configs per API key.
Actual webhook delivery will be implemented in a future iteration.
"""

import logging
from typing import Callable, List, Optional
from uuid import uuid4

from sqlalchemy import delete, select

from src.database.connection import db_manager
from src.service_engine.models import WebhookConfig

logger = logging.getLogger(__name__)


class WebhookManager:
    """CRUD operations for webhook configurations."""

    def __init__(self, session_factory: Optional[Callable] = None) -> None:
        self._session_factory = session_factory or db_manager.get_session

    # -- public API ----------------------------------------------------------

    async def create(
        self,
        api_key_id: str,
        webhook_url: str,
        webhook_secret: str,
        webhook_events: List[str],
        enabled: bool = True,
    ) -> dict:
        """Create a new webhook config. Return the created record as dict."""
        with self._session_factory() as session:
            config = WebhookConfig(
                id=uuid4(),
                api_key_id=api_key_id,
                webhook_url=webhook_url,
                webhook_secret=webhook_secret,
                webhook_events=webhook_events,
                enabled=enabled,
            )
            session.add(config)
            session.flush()
            return self._row_to_dict(config)

    async def get(self, webhook_id: str) -> Optional[dict]:
        """Get a webhook config by ID. Return None if not found."""
        with self._session_factory() as session:
            stmt = select(WebhookConfig).where(WebhookConfig.id == webhook_id)
            row = session.execute(stmt).scalars().first()
            if row is None:
                return None
            return self._row_to_dict(row)

    async def get_by_api_key(self, api_key_id: str) -> List[dict]:
        """Get all webhook configs for an API key."""
        with self._session_factory() as session:
            stmt = select(WebhookConfig).where(
                WebhookConfig.api_key_id == api_key_id,
            )
            rows = session.execute(stmt).scalars().all()
            return [self._row_to_dict(r) for r in rows]

    async def update(self, webhook_id: str, **fields) -> Optional[dict]:
        """Update webhook config fields. Return updated record or None."""
        if not fields:
            return await self.get(webhook_id)

        with self._session_factory() as session:
            stmt = select(WebhookConfig).where(WebhookConfig.id == webhook_id)
            row = session.execute(stmt).scalars().first()
            if row is None:
                return None
            for key, value in fields.items():
                if hasattr(row, key):
                    setattr(row, key, value)
            session.flush()
            return self._row_to_dict(row)

    async def delete(self, webhook_id: str) -> bool:
        """Delete a webhook config. Return True if deleted, False if not found."""
        with self._session_factory() as session:
            stmt = select(WebhookConfig).where(WebhookConfig.id == webhook_id)
            row = session.execute(stmt).scalars().first()
            if row is None:
                return False
            session.execute(
                delete(WebhookConfig).where(WebhookConfig.id == webhook_id),
            )
            return True

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _row_to_dict(row: WebhookConfig) -> dict:
        return {
            "id": str(row.id),
            "api_key_id": str(row.api_key_id),
            "webhook_url": row.webhook_url,
            "webhook_secret": row.webhook_secret,
            "webhook_events": row.webhook_events,
            "enabled": row.enabled,
        }
