"""
Main SSO Provider for SuperInsight Platform.

Manages multiple SSO connectors and handles provider configuration.
This is the main entry point for SSO functionality as specified in Task 4.
"""

# Import the actual implementation from the sso module
from src.security.sso.provider import SSOProvider as _SSOProvider
from src.security.sso.base import (
    SSOUserInfo, LoginInitiation, SSOLoginResult, LogoutResult,
    SSOAuthenticationError, SSOConfigurationError, ProviderNotFoundError
)

# Re-export the main class and related types
SSOProvider = _SSOProvider

__all__ = [
    "SSOProvider",
    "SSOUserInfo",
    "LoginInitiation", 
    "SSOLoginResult",
    "LogoutResult",
    "SSOAuthenticationError",
    "SSOConfigurationError",
    "ProviderNotFoundError"
]