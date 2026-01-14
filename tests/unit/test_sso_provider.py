"""
Unit tests for SSO Provider.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.security.sso.provider import SSOProvider
from src.security.sso.base import (
    SSOUserInfo, LoginInitiation, SSOLoginResult, LogoutResult,
    SSOAuthenticationError, SSOConfigurationError, ProviderNotFoundError
)
from src.models.security import SSOProtocol
from src.models.user import User


@pytest.fixture
def mock_db():
    """Create mock async database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def sso_provider(mock_db):
    """Create SSO provider instance."""
    return SSOProvider(db=mock_db)


@pytest.fixture
def sample_sso_config():
    """Sample SSO configuration."""
    return {
        "entity_id": "https://example.com/saml",
        "sso_url": "https://idp.example.com/sso",
        "acs_url": "https://app.example.com/acs",
        "x509_cert": "-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----"
    }


@pytest.fixture
def sample_user_info():
    """Sample SSO user information."""
    return SSOUserInfo(
        sso_id="user123",
        email="user@example.com",
        name="John Doe",
        first_name="John",
        last_name="Doe",
        username="johndoe",
        attributes={"department": "engineering"}
    )


class TestSSOProvider:
    """Tests for SSOProvider class."""

    def test_sso_provider_creation(self, sso_provider):
        """Test creating SSO provider instance."""
        assert sso_provider is not None
        assert sso_provider.connectors == {}
        assert len(sso_provider._connector_classes) == 4

    @pytest.mark.asyncio
    async def test_configure_provider_invalid_config(self, sso_provider, mock_db):
        """Test configuring provider with invalid configuration."""
        # Mock no existing provider
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Mock connector validation failure
        with patch('src.security.sso.saml.SAMLConnector') as mock_connector_class:
            mock_connector = MagicMock()
            mock_connector.validate_config.return_value = ["Missing entity_id", "Invalid certificate"]
            mock_connector_class.return_value = mock_connector
            
            with pytest.raises(SSOConfigurationError, match="Configuration errors"):
                await sso_provider.configure_provider(
                    name="test_invalid",
                    protocol=SSOProtocol.SAML,
                    config={"invalid": "config"}
                )

    @pytest.mark.asyncio
    async def test_get_provider(self, sso_provider, mock_db):
        """Test getting SSO provider by name."""
        expected_provider = MagicMock()
        expected_provider.name = "test_provider"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_provider
        mock_db.execute.return_value = mock_result
        
        provider = await sso_provider.get_provider("test_provider")
        
        assert provider == expected_provider
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_provider_not_found(self, sso_provider, mock_db):
        """Test getting non-existent SSO provider."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        provider = await sso_provider.get_provider("nonexistent")
        
        assert provider is None

    @pytest.mark.asyncio
    async def test_list_providers(self, sso_provider, mock_db):
        """Test listing all SSO providers."""
        expected_providers = [
            MagicMock(name="provider1"),
            MagicMock(name="provider2")
        ]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = expected_providers
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        providers = await sso_provider.list_providers()
        
        assert len(providers) == 2
        assert providers == expected_providers

    @pytest.mark.asyncio
    async def test_initiate_login_success(self, sso_provider):
        """Test successful login initiation."""
        # Set up mock connector
        mock_connector = AsyncMock()
        expected_result = LoginInitiation(
            redirect_url="https://idp.example.com/sso?SAMLRequest=...",
            state="state123"
        )
        mock_connector.initiate_login.return_value = expected_result
        sso_provider.connectors["test_provider"] = mock_connector
        
        result = await sso_provider.initiate_login(
            provider_name="test_provider",
            redirect_uri="https://app.example.com/callback",
            state="state123"
        )
        
        assert result == expected_result
        assert result.provider_name == "test_provider"
        mock_connector.initiate_login.assert_called_once_with(
            "https://app.example.com/callback", "state123"
        )

    @pytest.mark.asyncio
    async def test_initiate_login_provider_not_found(self, sso_provider):
        """Test login initiation with non-existent provider."""
        with pytest.raises(ProviderNotFoundError):
            await sso_provider.initiate_login(
                provider_name="nonexistent",
                redirect_uri="https://app.example.com/callback"
            )

    @pytest.mark.asyncio
    async def test_handle_callback_success(self, sso_provider, mock_db, sample_user_info):
        """Test successful callback handling."""
        # Set up mock connector
        mock_connector = AsyncMock()
        mock_connector.validate_callback.return_value = sample_user_info
        sso_provider.connectors["test_provider"] = mock_connector
        
        # Mock user sync
        mock_user = User(id=uuid4(), email=sample_user_info.email)
        with patch.object(sso_provider, '_sync_user', return_value=mock_user) as mock_sync:
            result = await sso_provider.handle_callback(
                provider_name="test_provider",
                callback_data={"code": "auth_code", "state": "state123"}
            )
        
        assert result.success is True
        assert result.user_info == sample_user_info
        assert result.session_id is not None
        mock_sync.assert_called_once_with(sample_user_info, "test_provider")

    @pytest.mark.asyncio
    async def test_handle_callback_provider_not_found(self, sso_provider):
        """Test callback handling with non-existent provider."""
        with pytest.raises(ProviderNotFoundError):
            await sso_provider.handle_callback(
                provider_name="nonexistent",
                callback_data={"code": "auth_code"}
            )

    @pytest.mark.asyncio
    async def test_initiate_logout_success(self, sso_provider):
        """Test successful logout initiation."""
        mock_connector = AsyncMock()
        expected_result = LogoutResult(success=True, redirect_url="https://idp.example.com/logout")
        mock_connector.initiate_logout.return_value = expected_result
        sso_provider.connectors["test_provider"] = mock_connector
        
        result = await sso_provider.initiate_logout(
            provider_name="test_provider",
            user_id="user123",
            session_id="session456"
        )
        
        assert result == expected_result
        mock_connector.initiate_logout.assert_called_once_with("user123", "session456")

    @pytest.mark.asyncio
    async def test_initiate_logout_provider_not_found(self, sso_provider):
        """Test logout with non-existent provider (graceful degradation)."""
        result = await sso_provider.initiate_logout(
            provider_name="nonexistent",
            user_id="user123"
        )
        
        assert result.success is True  # Graceful degradation


class TestUserSync:
    """Tests for user synchronization functionality."""

    @pytest.mark.asyncio
    async def test_sync_user_create_new(self, sso_provider, mock_db, sample_user_info):
        """Test creating new user from SSO."""
        # Mock database queries - no existing users
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        user = await sso_provider._sync_user(sample_user_info, "test_provider")
        
        assert user.email == sample_user_info.email
        assert user.name == sample_user_info.name
        assert user.sso_id == sample_user_info.sso_id
        assert user.sso_provider == "test_provider"
        assert user.is_active is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestProviderManagement:
    """Tests for provider management operations."""

    @pytest.mark.asyncio
    async def test_test_provider_success(self, sso_provider):
        """Test successful provider testing."""
        mock_connector = MagicMock()
        mock_connector.validate_config.return_value = []
        sso_provider.connectors["test_provider"] = mock_connector
        
        result = await sso_provider.test_provider("test_provider")
        
        assert result["success"] is True
        assert "valid" in result["message"]

    @pytest.mark.asyncio
    async def test_test_provider_not_found(self, sso_provider):
        """Test testing non-existent provider."""
        result = await sso_provider.test_provider("nonexistent")
        
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_disable_provider_success(self, sso_provider, mock_db):
        """Test disabling provider successfully."""
        provider = MagicMock()
        provider.name = "test_provider"
        provider.enabled = True
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = provider
        mock_db.execute.return_value = mock_result
        
        # Add provider to connectors
        sso_provider.connectors["test_provider"] = MagicMock()
        
        result = await sso_provider.disable_provider("test_provider")
        
        assert result is True
        assert provider.enabled is False
        assert "test_provider" not in sso_provider.connectors
        mock_db.commit.assert_called_once()


class TestSSOUserInfo:
    """Tests for SSOUserInfo dataclass."""

    def test_sso_user_info_creation(self):
        """Test creating SSO user info."""
        user_info = SSOUserInfo(
            sso_id="user123",
            email="user@example.com",
            name="John Doe"
        )
        
        assert user_info.sso_id == "user123"
        assert user_info.email == "user@example.com"
        assert user_info.name == "John Doe"
        assert user_info.attributes == {}


class TestLoginInitiation:
    """Tests for LoginInitiation dataclass."""

    def test_login_initiation_creation(self):
        """Test creating login initiation."""
        initiation = LoginInitiation(
            redirect_url="https://idp.example.com/sso",
            state="state123"
        )
        
        assert initiation.redirect_url == "https://idp.example.com/sso"
        assert initiation.state == "state123"
        assert initiation.provider_name == ""  # Default value


class TestSSOLoginResult:
    """Tests for SSOLoginResult dataclass."""

    def test_sso_login_result_success(self, sample_user_info):
        """Test successful SSO login result."""
        result = SSOLoginResult(
            success=True,
            user_info=sample_user_info,
            session_id="session123"
        )
        
        assert result.success is True
        assert result.user_info == sample_user_info
        assert result.session_id == "session123"
        assert result.error is None

    def test_sso_login_result_failure(self):
        """Test failed SSO login result."""
        result = SSOLoginResult(
            success=False,
            error="Authentication failed"
        )
        
        assert result.success is False
        assert result.error == "Authentication failed"
        assert result.user_info is None
        assert result.session_id is None


class TestLogoutResult:
    """Tests for LogoutResult dataclass."""

    def test_logout_result_success(self):
        """Test successful logout result."""
        result = LogoutResult(
            success=True,
            redirect_url="https://idp.example.com/logout"
        )
        
        assert result.success is True
        assert result.redirect_url == "https://idp.example.com/logout"
        assert result.error is None

    def test_logout_result_failure(self):
        """Test failed logout result."""
        result = LogoutResult(
            success=False,
            error="Logout failed"
        )
        
        assert result.success is False
        assert result.error == "Logout failed"
        assert result.redirect_url is None


class TestSSOExceptions:
    """Tests for SSO exception classes."""

    def test_sso_authentication_error(self):
        """Test SSO authentication error."""
        error = SSOAuthenticationError("Auth failed", "test_provider")
        
        assert str(error) == "Auth failed"
        assert error.provider == "test_provider"

    def test_sso_configuration_error(self):
        """Test SSO configuration error."""
        error = SSOConfigurationError("Config invalid")
        
        assert str(error) == "Config invalid"

    def test_provider_not_found_error(self):
        """Test provider not found error."""
        error = ProviderNotFoundError("test_provider")
        
        assert "test_provider" in str(error)
        assert error.provider_name == "test_provider"