"""
LLM Configuration Audit Service.

Provides audit logging for LLM configuration changes including:
- Create, update, delete operations
- User ID, timestamp, and change details
- Integration with existing audit system
- Automatic sanitization of sensitive data

This module ensures compliance with security requirements by
logging all configuration changes while protecting sensitive data.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.ai.llm.log_sanitizer import sanitize_for_audit, get_sanitizer

logger = logging.getLogger(__name__)


class LLMConfigAction(str, Enum):
    """LLM configuration action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    TEST_CONNECTION = "test_connection"


class LLMAuditEntry:
    """
    Represents an audit log entry for LLM configuration changes.
    
    Attributes:
        action: The type of action performed
        user_id: ID of the user who performed the action
        tenant_id: Tenant ID for multi-tenant isolation
        provider_id: ID of the LLM provider configuration
        timestamp: When the action occurred
        change_details: Details of what changed (sanitized)
        ip_address: IP address of the request
        user_agent: User agent of the request
    """
    
    def __init__(
        self,
        action: LLMConfigAction,
        user_id: Optional[str],
        tenant_id: str,
        provider_id: Optional[str] = None,
        change_details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.action = action
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.provider_id = provider_id
        self.change_details = change_details or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "action": self.action.value,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "provider_id": self.provider_id,
            "change_details": self.change_details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat()
        }


class LLMAuditService:
    """
    Service for auditing LLM configuration changes.
    
    Integrates with the existing audit system to log all LLM
    configuration changes with proper sanitization of sensitive data.
    
    Example usage:
        audit_service = LLMAuditService()
        
        # Log a configuration creation
        await audit_service.log_config_create(
            user_id="user-123",
            tenant_id="tenant-456",
            provider_id="provider-789",
            config_data={"name": "OpenAI", "api_key": "sk-xxx"},
            db=session
        )
    """
    
    def __init__(self):
        """Initialize the LLM audit service."""
        self.sanitizer = get_sanitizer()
        self._audit_logs: List[LLMAuditEntry] = []  # In-memory buffer for testing
    
    async def log_config_create(
        self,
        user_id: Optional[str],
        tenant_id: str,
        provider_id: str,
        config_data: Dict[str, Any],
        db: Optional[AsyncSession] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> LLMAuditEntry:
        """
        Log a configuration creation event.
        
        Args:
            user_id: ID of the user creating the config
            tenant_id: Tenant ID
            provider_id: ID of the new provider configuration
            config_data: The configuration data (will be sanitized)
            db: Database session for persistence
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            The created audit entry
        """
        # Sanitize the configuration data
        sanitized_config = sanitize_for_audit(config_data)
        
        entry = LLMAuditEntry(
            action=LLMConfigAction.CREATE,
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            change_details={
                "operation": "create",
                "new_config": sanitized_config
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self._persist_audit_entry(entry, db)
        return entry
    
    async def log_config_update(
        self,
        user_id: Optional[str],
        tenant_id: str,
        provider_id: str,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        db: Optional[AsyncSession] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> LLMAuditEntry:
        """
        Log a configuration update event.
        
        Args:
            user_id: ID of the user updating the config
            tenant_id: Tenant ID
            provider_id: ID of the provider configuration
            old_config: Previous configuration (will be sanitized)
            new_config: New configuration (will be sanitized)
            db: Database session for persistence
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            The created audit entry
        """
        # Sanitize both configurations
        sanitized_old = sanitize_for_audit(old_config)
        sanitized_new = sanitize_for_audit(new_config)
        
        # Calculate changes
        changes = self._calculate_changes(sanitized_old, sanitized_new)
        
        entry = LLMAuditEntry(
            action=LLMConfigAction.UPDATE,
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            change_details={
                "operation": "update",
                "changes": changes,
                "old_config": sanitized_old,
                "new_config": sanitized_new
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self._persist_audit_entry(entry, db)
        return entry
    
    async def log_config_delete(
        self,
        user_id: Optional[str],
        tenant_id: str,
        provider_id: str,
        config_data: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> LLMAuditEntry:
        """
        Log a configuration deletion event.
        
        Args:
            user_id: ID of the user deleting the config
            tenant_id: Tenant ID
            provider_id: ID of the deleted provider configuration
            config_data: The deleted configuration (will be sanitized)
            db: Database session for persistence
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            The created audit entry
        """
        sanitized_config = sanitize_for_audit(config_data) if config_data else {}
        
        entry = LLMAuditEntry(
            action=LLMConfigAction.DELETE,
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            change_details={
                "operation": "delete",
                "deleted_config": sanitized_config
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self._persist_audit_entry(entry, db)
        return entry
    
    async def log_config_activate(
        self,
        user_id: Optional[str],
        tenant_id: str,
        provider_id: str,
        db: Optional[AsyncSession] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> LLMAuditEntry:
        """
        Log a provider activation event.
        
        Args:
            user_id: ID of the user activating the provider
            tenant_id: Tenant ID
            provider_id: ID of the activated provider
            db: Database session for persistence
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            The created audit entry
        """
        entry = LLMAuditEntry(
            action=LLMConfigAction.ACTIVATE,
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            change_details={
                "operation": "activate",
                "provider_id": provider_id
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self._persist_audit_entry(entry, db)
        return entry
    
    async def log_config_deactivate(
        self,
        user_id: Optional[str],
        tenant_id: str,
        provider_id: str,
        db: Optional[AsyncSession] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> LLMAuditEntry:
        """
        Log a provider deactivation event.
        
        Args:
            user_id: ID of the user deactivating the provider
            tenant_id: Tenant ID
            provider_id: ID of the deactivated provider
            db: Database session for persistence
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            The created audit entry
        """
        entry = LLMAuditEntry(
            action=LLMConfigAction.DEACTIVATE,
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            change_details={
                "operation": "deactivate",
                "provider_id": provider_id
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self._persist_audit_entry(entry, db)
        return entry
    
    async def log_connection_test(
        self,
        user_id: Optional[str],
        tenant_id: str,
        provider_id: str,
        success: bool,
        error_message: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> LLMAuditEntry:
        """
        Log a connection test event.
        
        Args:
            user_id: ID of the user testing the connection
            tenant_id: Tenant ID
            provider_id: ID of the provider being tested
            success: Whether the test succeeded
            error_message: Error message if test failed
            db: Database session for persistence
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            The created audit entry
        """
        entry = LLMAuditEntry(
            action=LLMConfigAction.TEST_CONNECTION,
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            change_details={
                "operation": "test_connection",
                "success": success,
                "error_message": error_message
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self._persist_audit_entry(entry, db)
        return entry
    
    def _calculate_changes(
        self,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate the differences between two configurations.
        
        Args:
            old_config: Previous configuration
            new_config: New configuration
            
        Returns:
            Dictionary describing the changes
        """
        changes = {
            "added": {},
            "removed": {},
            "modified": {}
        }
        
        old_keys = set(old_config.keys())
        new_keys = set(new_config.keys())
        
        # Added keys
        for key in new_keys - old_keys:
            changes["added"][key] = new_config[key]
        
        # Removed keys
        for key in old_keys - new_keys:
            changes["removed"][key] = old_config[key]
        
        # Modified keys
        for key in old_keys & new_keys:
            if old_config[key] != new_config[key]:
                changes["modified"][key] = {
                    "old": old_config[key],
                    "new": new_config[key]
                }
        
        return changes
    
    async def _persist_audit_entry(
        self,
        entry: LLMAuditEntry,
        db: Optional[AsyncSession] = None
    ) -> None:
        """
        Persist an audit entry to the database.
        
        Args:
            entry: The audit entry to persist
            db: Database session
        """
        # Store in memory buffer (for testing and when db is not available)
        self._audit_logs.append(entry)
        
        if db is None:
            logger.debug(f"Audit entry stored in memory: {entry.action.value}")
            return
        
        try:
            # Import here to avoid circular imports
            from src.security.models import SecurityAuditLogModel, AuditAction
            
            # Map LLM action to security audit action
            action_map = {
                LLMConfigAction.CREATE: AuditAction.CREATE,
                LLMConfigAction.UPDATE: AuditAction.UPDATE,
                LLMConfigAction.DELETE: AuditAction.DELETE,
                LLMConfigAction.ACTIVATE: AuditAction.UPDATE,
                LLMConfigAction.DEACTIVATE: AuditAction.UPDATE,
                LLMConfigAction.TEST_CONNECTION: AuditAction.READ,
            }
            
            audit_log = SecurityAuditLogModel(
                user_id=UUID(entry.user_id) if entry.user_id else None,
                tenant_id=entry.tenant_id,
                action=action_map.get(entry.action, AuditAction.UPDATE),
                resource_type="llm_configuration",
                resource_id=entry.provider_id,
                ip_address=entry.ip_address,
                user_agent=entry.user_agent,
                details={
                    "llm_action": entry.action.value,
                    **entry.change_details
                }
            )
            
            db.add(audit_log)
            await db.commit()
            
            logger.info(
                f"LLM config audit logged: action={entry.action.value}, "
                f"provider={entry.provider_id}, user={entry.user_id}"
            )
            
        except ImportError:
            logger.warning("Security models not available, audit entry stored in memory only")
        except Exception as e:
            logger.error(f"Failed to persist audit entry: {e}")
            # Don't raise - audit logging should not break the main operation
    
    def get_audit_logs(
        self,
        tenant_id: Optional[str] = None,
        provider_id: Optional[str] = None,
        action: Optional[LLMConfigAction] = None,
        limit: int = 100
    ) -> List[LLMAuditEntry]:
        """
        Get audit logs from the in-memory buffer.
        
        This is primarily for testing. In production, use the
        database query methods.
        
        Args:
            tenant_id: Filter by tenant ID
            provider_id: Filter by provider ID
            action: Filter by action type
            limit: Maximum number of entries to return
            
        Returns:
            List of matching audit entries
        """
        logs = self._audit_logs
        
        if tenant_id:
            logs = [l for l in logs if l.tenant_id == tenant_id]
        
        if provider_id:
            logs = [l for l in logs if l.provider_id == provider_id]
        
        if action:
            logs = [l for l in logs if l.action == action]
        
        return logs[-limit:]
    
    def clear_audit_logs(self) -> None:
        """Clear the in-memory audit log buffer (for testing)."""
        self._audit_logs.clear()


# Global audit service instance
_audit_service: Optional[LLMAuditService] = None


def get_llm_audit_service() -> LLMAuditService:
    """Get or create the global LLM audit service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = LLMAuditService()
    return _audit_service
