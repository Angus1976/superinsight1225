"""
SAML 2.0 SSO Connector for SuperInsight Platform.

Re-exports the SAML connector implementation from the sso module.
"""

from src.security.sso.saml import SAMLConnector

__all__ = ["SAMLConnector"]