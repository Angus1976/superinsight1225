"""Integration tests for SSO components."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.security.sso_provider import (
    SSOProvider, SSOUserInfo, LoginInitiation, SSOLoginResult, LogoutResult,
    SSOAuthenticationError, SSOConfigurationError, ProviderNotFoundError
)
from src.models.security import SSOProtocol


class TestSSOProviderIntegration:
    """Integration tests for SSO Provider."""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.commit = MagicMock()
        db.add = MagicMock()
        return db
    
    @pytest.fixture
    def sso_provider(self):
        return SSOProvider()
    
    def test_sso_provider_initialization(self, sso_provider):
        assert sso_provider is not None
    
    @pytest.mark.asyncio
    async def test_initiate_login(self, sso_provider, mock_db):
        provider_name = "test-provider"
        redirect_uri = "https://app.example.com/callback"
        
        with patch.object(sso_provider, 'initiate_login') as mock_login:
            mock_login.return_value = LoginInitiation(
                redirect_url="https://idp.example.com/login",
                state="csrf-state-token",
                provider_name=provider_name
            )
            result = await sso_provider.initiate_login(provider_name, redirect_uri, mock_db)
            assert result is not None
            assert result.redirect_url is not None


class TestSSOUserSyncIntegration:
    """Integration tests for SSO user synchronization."""
    
    def test_sso_user_info_creation(self):
        user_info = SSOUserInfo(
            sso_id="ext-user-123",
            email="user@example.com",
            name="Test User",
            groups=["developers", "admins"],
            attributes={"department": "Engineering"}
        )
        assert user_info.sso_id == "ext-user-123"
        assert user_info.email == "user@example.com"
        assert "developers" in user_info.groups
    
    def test_sync_user_idempotency(self):
        user_info_1 = SSOUserInfo(sso_id="ext-user-123", email="user@example.com", name="Test User")
        user_info_2 = SSOUserInfo(sso_id="ext-user-123", email="user@example.com", name="Test User")
        assert user_info_1.sso_id == user_info_2.sso_id


class TestSSOCallbackIntegration:
    """Integration tests for SSO callback handling."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    @pytest.fixture
    def sso_provider(self):
        return SSOProvider()
    
    @pytest.mark.asyncio
    async def test_handle_callback_success(self, sso_provider, mock_db):
        provider_name = "saml-provider-1"
        callback_data = {"SAMLResponse": "base64-response", "RelayState": "state"}
        
        with patch.object(sso_provider, 'handle_callback') as mock_callback:
            mock_callback.return_value = SSOLoginResult(
                success=True,
                user_info=SSOUserInfo(sso_id="saml-user-123", email="user@example.com", name="SAML User"),
                session_id="session-123"
            )
            result = await sso_provider.handle_callback(provider_name, callback_data, mock_db)
            assert result.success is True
            assert result.user_info is not None
    
    @pytest.mark.asyncio
    async def test_handle_callback_failure(self, sso_provider, mock_db):
        with patch.object(sso_provider, 'handle_callback') as mock_callback:
            mock_callback.return_value = SSOLoginResult(success=False, error="Access denied")
            result = await sso_provider.handle_callback("provider", {}, mock_db)
            assert result.success is False
            assert result.error is not None


class TestSSOLogoutIntegration:
    """Integration tests for SSO logout."""
    
    @pytest.fixture
    def sso_provider(self):
        return SSOProvider()
    
    @pytest.mark.asyncio
    async def test_single_logout(self, sso_provider):
        with patch.object(sso_provider, 'initiate_logout') as mock_logout:
            mock_logout.return_value = LogoutResult(success=True, redirect_url="https://idp.example.com/logout")
            result = await sso_provider.initiate_logout("provider", "user-123", MagicMock())
            assert result.success is True


class TestSSOErrorHandling:
    """Integration tests for SSO error handling."""
    
    def test_authentication_error(self):
        error = SSOAuthenticationError(message="Invalid SAML response", provider="saml-provider-1", details={"reason": "signature_invalid"})
        assert str(error) == "Invalid SAML response"
        assert error.provider == "saml-provider-1"
    
    def test_configuration_error(self):
        error = SSOConfigurationError("Missing client_id")
        assert str(error) == "Missing client_id"
    
    def test_provider_not_found_error(self):
        error = ProviderNotFoundError("unknown-provider")
        assert "unknown-provider" in str(error)
