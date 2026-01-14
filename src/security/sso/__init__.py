"""
SSO Module for SuperInsight Platform.

Provides Single Sign-On (SSO) functionality with support for multiple protocols:
- SAML 2.0
- OAuth 2.0
- OpenID Connect (OIDC)
- LDAP/Active Directory
"""

from .base import (
    SSOConnector,
    SSOUserInfo,
    LoginInitiation,
    SSOLoginResult,
    LogoutResult,
    SSOAuthenticationError,
    SSOConfigurationError,
    ProviderNotFoundError
)

from .provider import SSOProvider
from .saml import SAMLConnector
from .oauth2 import OAuth2Connector
from .oidc import OIDCConnector
from .ldap import LDAPConnector

__all__ = [
    # Base classes and data structures
    "SSOConnector",
    "SSOUserInfo", 
    "LoginInitiation",
    "SSOLoginResult",
    "LogoutResult",
    
    # Exceptions
    "SSOAuthenticationError",
    "SSOConfigurationError", 
    "ProviderNotFoundError",
    
    # Main provider
    "SSOProvider",
    
    # Protocol connectors
    "SAMLConnector",
    "OAuth2Connector", 
    "OIDCConnector",
    "LDAPConnector"
]