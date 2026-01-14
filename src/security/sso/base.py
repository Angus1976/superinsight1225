"""
Base SSO Connector for SuperInsight Platform.

Defines the abstract base class and common data structures for SSO connectors.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from src.models.security import SSOProtocol


@dataclass
class SSOUserInfo:
    """User information from SSO provider."""
    sso_id: str
    email: str
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    groups: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    provider_name: Optional[str] = None


@dataclass
class LoginInitiation:
    """SSO login initiation response."""
    redirect_url: str
    state: Optional[str] = None
    nonce: Optional[str] = None
    provider_name: str = ""


@dataclass
class SSOLoginResult:
    """SSO login result."""
    success: bool
    user_info: Optional[SSOUserInfo] = None
    error: Optional[str] = None
    session_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None


@dataclass
class LogoutResult:
    """SSO logout result."""
    success: bool
    redirect_url: Optional[str] = None
    error: Optional[str] = None


class SSOConnector(ABC):
    """
    Abstract base class for SSO connectors.
    
    All SSO protocol implementations must inherit from this class.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.name = config.get("name", "unknown")
        self.supports_slo = False
    
    @property
    @abstractmethod
    def protocol(self) -> SSOProtocol:
        """Return the SSO protocol type."""
        pass
    
    @abstractmethod
    async def initiate_login(self, redirect_uri: str, state: Optional[str] = None) -> LoginInitiation:
        """
        Initiate SSO login flow.
        
        Args:
            redirect_uri: URI to redirect after authentication
            state: Optional state parameter for CSRF protection
            
        Returns:
            LoginInitiation with redirect URL
        """
        pass
    
    @abstractmethod
    async def validate_callback(self, callback_data: Dict[str, Any]) -> SSOUserInfo:
        """
        Validate SSO callback and extract user information.
        
        Args:
            callback_data: Data received from SSO provider callback
            
        Returns:
            SSOUserInfo with user details
            
        Raises:
            SSOAuthenticationError: If validation fails
        """
        pass
    
    async def initiate_logout(self, user_id: str, session_id: Optional[str] = None) -> LogoutResult:
        """
        Initiate SSO logout (Single Logout).
        
        Args:
            user_id: User to log out
            session_id: Optional session ID
            
        Returns:
            LogoutResult
        """
        # Default implementation - override in subclasses that support SLO
        return LogoutResult(success=True)
    
    def map_attributes(self, raw_attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map provider attributes to standard attributes.
        
        Args:
            raw_attributes: Raw attributes from provider
            
        Returns:
            Mapped attributes
        """
        mapping = self.config.get("attribute_mapping", {})
        result = {}
        
        for standard_name, provider_name in mapping.items():
            if provider_name in raw_attributes:
                result[standard_name] = raw_attributes[provider_name]
        
        # Include unmapped attributes
        for key, value in raw_attributes.items():
            if key not in result:
                result[key] = value
        
        return result
    
    def validate_config(self) -> List[str]:
        """
        Validate connector configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        return []


class SSOAuthenticationError(Exception):
    """SSO authentication error."""
    
    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.provider = provider
        self.details = details or {}


class SSOConfigurationError(Exception):
    """SSO configuration error."""
    pass


class ProviderNotFoundError(Exception):
    """SSO provider not found error."""
    
    def __init__(self, provider_name: str):
        super().__init__(f"SSO provider not found: {provider_name}")
        self.provider_name = provider_name
