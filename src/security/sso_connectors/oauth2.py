"""
OAuth 2.0 SSO Connector for SuperInsight Platform.

Re-exports the OAuth 2.0 connector implementation from the sso module.
"""

from src.security.sso.oauth2 import OAuth2Connector

__all__ = ["OAuth2Connector"]