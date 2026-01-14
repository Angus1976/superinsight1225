"""
OpenID Connect (OIDC) SSO Connector for SuperInsight Platform.

Re-exports the OIDC connector implementation from the sso module.
"""

from src.security.sso.oidc import OIDCConnector

__all__ = ["OIDCConnector"]