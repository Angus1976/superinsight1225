"""
Main SSO Provider for SuperInsight Platform.

Manages multiple SSO connectors and handles provider configuration.
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.security import SSOProviderModel, SSOProtocol
from src.models.user import User
from src.security.sso.base import (
    SSOConnector, SSOUserInfo, LoginInitiation, SSOLoginResult, LogoutResult,
    SSOAuthenticationError, SSOConfigurationError, ProviderNotFoundError
)
from src.security.sso.saml import SAMLConnector
from src.security.sso.oauth2 import OAuth2Connector
from src.security.sso.oidc import OIDCConnector
from src.security.sso.ldap import LDAPConnector


class SSOProvider:
    """
    Main SSO Provider that manages multiple SSO connectors.
    
    Supports SAML 2.0, OAuth 2.0, OIDC, and LDAP/AD protocols.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.connectors: Dict[str, SSOConnector] = {}
        self._connector_classes = {
            SSOProtocol.SAML: SAMLConnector,
            SSOProtocol.OAUTH2: OAuth2Connector,
            SSOProtocol.OIDC: OIDCConnector,
            SSOProtocol.LDAP: LDAPConnector,
        }
    
    async def configure_provider(
        self,
        name: str,
        protocol: SSOProtocol,
        config: Dict[str, Any],
        enabled: bool = True
    ) -> SSOProviderModel:
        """
        Configure a new SSO provider.
        
        Args:
            name: Provider name (unique identifier)
            protocol: SSO protocol type
            config: Provider-specific configuration
            enabled: Whether provider is enabled
            
        Returns:
            Created SSOProviderModel
            
        Raises:
            SSOConfigurationError: If configuration is invalid
        """
        self.logger.info(f"Configuring SSO provider: {name} ({protocol.value})")
        
        # Validate configuration
        connector_class = self._connector_classes.get(protocol)
        if not connector_class:
            raise SSOConfigurationError(f"Unsupported protocol: {protocol.value}")
        
        # Create temporary connector to validate config
        temp_connector = connector_class(config)
        validation_errors = temp_connector.validate_config()
        if validation_errors:
            raise SSOConfigurationError(f"Configuration errors: {', '.join(validation_errors)}")
        
        # Check if provider already exists
        stmt = select(SSOProviderModel).where(SSOProviderModel.name == name)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing provider
            existing.protocol = protocol
            existing.config = config
            existing.enabled = enabled
            existing.updated_at = datetime.utcnow()
            provider = existing
        else:
            # Create new provider
            provider = SSOProviderModel(
                id=uuid4(),
                name=name,
                protocol=protocol,
                config=config,
                enabled=enabled
            )
            self.db.add(provider)
        
        await self.db.commit()
        
        # Initialize connector
        if enabled:
            self.connectors[name] = connector_class(config)
            self.connectors[name].name = name
        
        self.logger.info(f"SSO provider configured successfully: {name}")
        return provider
    
    async def get_provider(self, name: str) -> Optional[SSOProviderModel]:
        """Get SSO provider by name."""
        stmt = select(SSOProviderModel).where(SSOProviderModel.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_providers(self, enabled_only: bool = False) -> List[SSOProviderModel]:
        """List all SSO providers."""
        stmt = select(SSOProviderModel)
        if enabled_only:
            stmt = stmt.where(SSOProviderModel.enabled == True)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def load_providers(self) -> None:
        """Load all enabled providers from database."""
        providers = await self.list_providers(enabled_only=True)
        
        for provider in providers:
            try:
                connector_class = self._connector_classes.get(provider.protocol)
                if connector_class:
                    connector = connector_class(provider.config)
                    connector.name = provider.name
                    self.connectors[provider.name] = connector
                    self.logger.info(f"Loaded SSO provider: {provider.name}")
                else:
                    self.logger.warning(f"Unknown protocol for provider {provider.name}: {provider.protocol}")
            except Exception as e:
                self.logger.error(f"Failed to load SSO provider {provider.name}: {e}")
    
    async def initiate_login(self, provider_name: str, redirect_uri: str, state: Optional[str] = None) -> LoginInitiation:
        """
        Initiate SSO login flow.
        
        Args:
            provider_name: Name of SSO provider
            redirect_uri: URI to redirect after authentication
            state: Optional state parameter for CSRF protection
            
        Returns:
            LoginInitiation with redirect URL
            
        Raises:
            ProviderNotFoundError: If provider not found
        """
        connector = self.connectors.get(provider_name)
        if not connector:
            raise ProviderNotFoundError(provider_name)
        
        self.logger.info(f"Initiating SSO login for provider: {provider_name}")
        
        try:
            result = await connector.initiate_login(redirect_uri, state)
            result.provider_name = provider_name
            return result
        except Exception as e:
            self.logger.error(f"Failed to initiate SSO login for {provider_name}: {e}")
            raise SSOAuthenticationError(f"Login initiation failed: {e}", provider_name)
    
    async def handle_callback(self, provider_name: str, callback_data: Dict[str, Any]) -> SSOLoginResult:
        """
        Handle SSO callback and authenticate user.
        
        Args:
            provider_name: Name of SSO provider
            callback_data: Data received from SSO provider callback
            
        Returns:
            SSOLoginResult with user information
            
        Raises:
            ProviderNotFoundError: If provider not found
            SSOAuthenticationError: If authentication fails
        """
        connector = self.connectors.get(provider_name)
        if not connector:
            raise ProviderNotFoundError(provider_name)
        
        self.logger.info(f"Handling SSO callback for provider: {provider_name}")
        
        try:
            # Validate callback and get user info
            user_info = await connector.validate_callback(callback_data)
            user_info.provider_name = provider_name
            
            # Sync user to local database
            user = await self._sync_user(user_info, provider_name)
            
            # Create session (this would be handled by session manager)
            session_id = str(uuid4())
            
            return SSOLoginResult(
                success=True,
                user_info=user_info,
                session_id=session_id
            )
            
        except SSOAuthenticationError:
            raise
        except Exception as e:
            self.logger.error(f"SSO callback handling failed for {provider_name}: {e}")
            return SSOLoginResult(
                success=False,
                error=f"Authentication failed: {e}"
            )
    
    async def initiate_logout(self, provider_name: str, user_id: str, session_id: Optional[str] = None) -> LogoutResult:
        """
        Initiate SSO logout (Single Logout).
        
        Args:
            provider_name: Name of SSO provider
            user_id: User to log out
            session_id: Optional session ID
            
        Returns:
            LogoutResult
        """
        connector = self.connectors.get(provider_name)
        if not connector:
            return LogoutResult(success=True)  # Graceful degradation
        
        self.logger.info(f"Initiating SSO logout for provider: {provider_name}, user: {user_id}")
        
        try:
            return await connector.initiate_logout(user_id, session_id)
        except Exception as e:
            self.logger.error(f"SSO logout failed for {provider_name}: {e}")
            return LogoutResult(success=False, error=str(e))
    
    async def _sync_user(self, user_info: SSOUserInfo, provider_name: str) -> User:
        """
        Sync SSO user to local database.
        
        Args:
            user_info: User information from SSO provider
            provider_name: Name of SSO provider
            
        Returns:
            Local User object
        """
        # Look for existing user by SSO ID
        stmt = select(User).where(
            User.sso_id == user_info.sso_id,
            User.sso_provider == provider_name
        )
        result = await self.db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Update existing user
            existing_user.email = user_info.email
            existing_user.name = user_info.name or existing_user.name
            existing_user.first_name = user_info.first_name or existing_user.first_name
            existing_user.last_name = user_info.last_name or existing_user.last_name
            existing_user.username = user_info.username or existing_user.username
            existing_user.sso_attributes = user_info.attributes
            existing_user.updated_at = datetime.utcnow()
            
            self.logger.info(f"Updated existing user: {existing_user.id}")
            user = existing_user
        else:
            # Check if user exists by email
            stmt = select(User).where(User.email == user_info.email)
            result = await self.db.execute(stmt)
            email_user = result.scalar_one_or_none()
            
            if email_user:
                # Link existing email user to SSO
                email_user.sso_id = user_info.sso_id
                email_user.sso_provider = provider_name
                email_user.sso_attributes = user_info.attributes
                email_user.updated_at = datetime.utcnow()
                
                self.logger.info(f"Linked existing email user to SSO: {email_user.id}")
                user = email_user
            else:
                # Create new user
                user = User(
                    id=uuid4(),
                    email=user_info.email,
                    name=user_info.name,
                    first_name=user_info.first_name,
                    last_name=user_info.last_name,
                    username=user_info.username,
                    sso_id=user_info.sso_id,
                    sso_provider=provider_name,
                    sso_attributes=user_info.attributes,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                self.db.add(user)
                
                self.logger.info(f"Created new SSO user: {user.id}")
        
        await self.db.commit()
        return user
    
    async def test_provider(self, provider_name: str) -> Dict[str, Any]:
        """
        Test SSO provider configuration.
        
        Args:
            provider_name: Name of SSO provider to test
            
        Returns:
            Test results
        """
        connector = self.connectors.get(provider_name)
        if not connector:
            return {"success": False, "error": "Provider not found"}
        
        try:
            # Basic configuration validation
            validation_errors = connector.validate_config()
            if validation_errors:
                return {
                    "success": False,
                    "error": "Configuration validation failed",
                    "details": validation_errors
                }
            
            # Protocol-specific tests would be implemented in each connector
            return {"success": True, "message": "Provider configuration is valid"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def disable_provider(self, provider_name: str) -> bool:
        """Disable SSO provider."""
        provider = await self.get_provider(provider_name)
        if provider:
            provider.enabled = False
            provider.updated_at = datetime.utcnow()
            await self.db.commit()
            
            # Remove from active connectors
            if provider_name in self.connectors:
                del self.connectors[provider_name]
            
            return True
        return False
    
    async def enable_provider(self, provider_name: str) -> bool:
        """Enable SSO provider."""
        provider = await self.get_provider(provider_name)
        if provider:
            provider.enabled = True
            provider.updated_at = datetime.utcnow()
            await self.db.commit()
            
            # Load connector
            connector_class = self._connector_classes.get(provider.protocol)
            if connector_class:
                connector = connector_class(provider.config)
                connector.name = provider_name
                self.connectors[provider_name] = connector
            
            return True
        return False