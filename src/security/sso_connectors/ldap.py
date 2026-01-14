"""
LDAP/Active Directory SSO Connector for SuperInsight Platform.

Re-exports the LDAP connector implementation from the sso module.
"""

from src.security.sso.ldap import LDAPConnector

__all__ = ["LDAPConnector"]