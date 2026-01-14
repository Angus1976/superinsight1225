"""
LDAP/Active Directory SSO Connector for SuperInsight Platform.

Implements LDAP authentication and user synchronization.
"""

import logging
from typing import Dict, Any, Optional, List
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.models.security import SSOProtocol
from src.security.sso.base import (
    SSOConnector, SSOUserInfo, LoginInitiation, SSOLoginResult,
    LogoutResult, SSOAuthenticationError
)

# LDAP is typically synchronous, so we'll use a thread pool for async operations
try:
    import ldap3
    from ldap3 import Server, Connection, ALL, SUBTREE
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False
    ldap3 = None


class LDAPConnector(SSOConnector):
    """
    LDAP/Active Directory SSO Connector.
    
    Implements LDAP bind authentication and user attribute synchronization.
    """
    
    @property
    def protocol(self) -> SSOProtocol:
        return SSOProtocol.LDAP
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        if not LDAP_AVAILABLE:
            raise ImportError("ldap3 library is required for LDAP connector")
        
        self.server_url = config.get("server_url")
        self.base_dn = config.get("base_dn")
        self.bind_dn = config.get("bind_dn")
        self.bind_password = config.get("bind_password")
        self.user_search_base = config.get("user_search_base", self.base_dn)
        self.user_search_filter = config.get("user_search_filter", "(uid={username})")
        self.group_search_base = config.get("group_search_base", self.base_dn)
        self.group_search_filter = config.get("group_search_filter", "(member={user_dn})")
        self.use_ssl = config.get("use_ssl", True)
        self.use_tls = config.get("use_tls", False)
        self.timeout = config.get("timeout", 30)
        
        # Attribute mapping for LDAP attributes
        self.attribute_mapping = config.get("attribute_mapping", {
            "email": "mail",
            "name": "displayName",
            "first_name": "givenName",
            "last_name": "sn",
            "username": "uid",
            "groups": "memberOf"
        })
        
        # Thread pool for async operations
        self._executor = ThreadPoolExecutor(max_workers=5)
        
        # LDAP doesn't support traditional logout
        self.supports_slo = False
    
    async def initiate_login(self, redirect_uri: str, state: Optional[str] = None) -> LoginInitiation:
        """
        LDAP doesn't use redirect-based login.
        This method should not be called for LDAP authentication.
        
        Args:
            redirect_uri: Not used for LDAP
            state: Not used for LDAP
            
        Returns:
            LoginInitiation (not applicable for LDAP)
        """
        raise SSOAuthenticationError("LDAP authentication does not use redirect-based login", self.name)
    
    async def validate_callback(self, callback_data: Dict[str, Any]) -> SSOUserInfo:
        """
        LDAP doesn't use callback-based authentication.
        Use authenticate_user method instead.
        
        Args:
            callback_data: Not used for LDAP
            
        Returns:
            SSOUserInfo (not applicable for LDAP)
        """
        raise SSOAuthenticationError("LDAP authentication does not use callback validation", self.name)
    
    async def authenticate_user(self, username: str, password: str) -> SSOUserInfo:
        """
        Authenticate user against LDAP directory.
        
        Args:
            username: Username to authenticate
            password: User password
            
        Returns:
            SSOUserInfo with user details
            
        Raises:
            SSOAuthenticationError: If authentication fails
        """
        try:
            # Run LDAP operations in thread pool
            user_info = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._authenticate_sync,
                username,
                password
            )
            
            return user_info
            
        except Exception as e:
            self.logger.error(f"LDAP authentication error: {e}")
            raise SSOAuthenticationError(f"LDAP authentication failed: {e}", self.name)
    
    def _authenticate_sync(self, username: str, password: str) -> SSOUserInfo:
        """Synchronous LDAP authentication."""
        # Create LDAP server connection
        server = self._create_server()
        
        # First, bind with service account to search for user
        search_conn = Connection(
            server,
            user=self.bind_dn,
            password=self.bind_password,
            auto_bind=True,
            raise_exceptions=True
        )
        
        try:
            # Search for user
            user_dn, user_attrs = self._search_user(search_conn, username)
            
            if not user_dn:
                raise SSOAuthenticationError(f"User not found: {username}", self.name)
            
            # Attempt to bind as the user to verify password
            user_conn = Connection(
                server,
                user=user_dn,
                password=password,
                raise_exceptions=True
            )
            
            if not user_conn.bind():
                raise SSOAuthenticationError("Invalid credentials", self.name)
            
            user_conn.unbind()
            
            # Get user groups
            groups = self._get_user_groups(search_conn, user_dn)
            
            # Map attributes to standard format
            mapped_attrs = self.map_attributes(user_attrs)
            
            # Extract user information
            sso_id = user_attrs.get(self.attribute_mapping.get("username", "uid"), [username])[0]
            email = mapped_attrs.get("email")
            
            if not email:
                raise SSOAuthenticationError("No email found for user", self.name)
            
            return SSOUserInfo(
                sso_id=str(sso_id),
                email=email,
                name=mapped_attrs.get("name"),
                first_name=mapped_attrs.get("first_name"),
                last_name=mapped_attrs.get("last_name"),
                username=username,
                groups=groups,
                attributes=user_attrs,
                provider_name=self.name
            )
            
        finally:
            search_conn.unbind()
    
    def _create_server(self) -> 'ldap3.Server':
        """Create LDAP server object."""
        port = 636 if self.use_ssl else 389
        
        server = Server(
            self.server_url,
            port=port,
            use_ssl=self.use_ssl,
            get_info=ALL,
            connect_timeout=self.timeout
        )
        
        return server
    
    def _search_user(self, connection: 'ldap3.Connection', username: str) -> tuple[Optional[str], Dict[str, Any]]:
        """Search for user in LDAP directory."""
        search_filter = self.user_search_filter.format(username=username)
        
        connection.search(
            search_base=self.user_search_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=list(self.attribute_mapping.values()) + ['dn']
        )
        
        if not connection.entries:
            return None, {}
        
        entry = connection.entries[0]
        user_dn = entry.entry_dn
        
        # Convert attributes to dict
        user_attrs = {}
        for attr_name in entry.entry_attributes:
            attr_values = entry[attr_name].values
            user_attrs[attr_name] = attr_values if len(attr_values) > 1 else attr_values[0] if attr_values else None
        
        return user_dn, user_attrs
    
    def _get_user_groups(self, connection: 'ldap3.Connection', user_dn: str) -> List[str]:
        """Get groups for user."""
        groups = []
        
        # Search for groups where user is a member
        search_filter = self.group_search_filter.format(user_dn=user_dn)
        
        connection.search(
            search_base=self.group_search_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['cn', 'name', 'displayName']
        )
        
        for entry in connection.entries:
            # Try different group name attributes
            group_name = None
            for attr in ['cn', 'name', 'displayName']:
                if hasattr(entry, attr) and entry[attr].value:
                    group_name = entry[attr].value
                    break
            
            if group_name:
                groups.append(group_name)
        
        return groups
    
    async def sync_user(self, username: str) -> Optional[SSOUserInfo]:
        """
        Synchronize user information from LDAP without authentication.
        
        Args:
            username: Username to synchronize
            
        Returns:
            SSOUserInfo if user found, None otherwise
        """
        try:
            user_info = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._sync_user_sync,
                username
            )
            
            return user_info
            
        except Exception as e:
            self.logger.error(f"LDAP user sync error: {e}")
            return None
    
    def _sync_user_sync(self, username: str) -> Optional[SSOUserInfo]:
        """Synchronous user synchronization."""
        server = self._create_server()
        
        connection = Connection(
            server,
            user=self.bind_dn,
            password=self.bind_password,
            auto_bind=True,
            raise_exceptions=True
        )
        
        try:
            user_dn, user_attrs = self._search_user(connection, username)
            
            if not user_dn:
                return None
            
            groups = self._get_user_groups(connection, user_dn)
            mapped_attrs = self.map_attributes(user_attrs)
            
            sso_id = user_attrs.get(self.attribute_mapping.get("username", "uid"), [username])[0]
            email = mapped_attrs.get("email")
            
            if not email:
                return None
            
            return SSOUserInfo(
                sso_id=str(sso_id),
                email=email,
                name=mapped_attrs.get("name"),
                first_name=mapped_attrs.get("first_name"),
                last_name=mapped_attrs.get("last_name"),
                username=username,
                groups=groups,
                attributes=user_attrs,
                provider_name=self.name
            )
            
        finally:
            connection.unbind()
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test LDAP connection and configuration."""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._test_connection_sync
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _test_connection_sync(self) -> Dict[str, Any]:
        """Synchronous connection test."""
        try:
            server = self._create_server()
            
            connection = Connection(
                server,
                user=self.bind_dn,
                password=self.bind_password,
                raise_exceptions=True
            )
            
            if not connection.bind():
                return {
                    "success": False,
                    "error": "Failed to bind to LDAP server"
                }
            
            # Test search
            connection.search(
                search_base=self.base_dn,
                search_filter="(objectClass=*)",
                search_scope=ldap3.BASE,
                attributes=['objectClass']
            )
            
            connection.unbind()
            
            return {
                "success": True,
                "message": "LDAP connection successful",
                "server_info": {
                    "server": self.server_url,
                    "base_dn": self.base_dn,
                    "ssl": self.use_ssl,
                    "tls": self.use_tls
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection test failed: {e}"
            }
    
    def validate_config(self) -> List[str]:
        """Validate LDAP connector configuration."""
        errors = []
        
        if not LDAP_AVAILABLE:
            errors.append("ldap3 library is not installed")
        
        if not self.server_url:
            errors.append("server_url is required")
        
        if not self.base_dn:
            errors.append("base_dn is required")
        
        if not self.bind_dn:
            errors.append("bind_dn is required")
        
        if not self.bind_password:
            errors.append("bind_password is required")
        
        # Validate server URL format
        if self.server_url and not self._is_valid_ldap_url(self.server_url):
            errors.append("server_url is not a valid LDAP URL")
        
        # Validate DN formats
        if self.base_dn and not self._is_valid_dn(self.base_dn):
            errors.append("base_dn is not a valid DN")
        
        if self.bind_dn and not self._is_valid_dn(self.bind_dn):
            errors.append("bind_dn is not a valid DN")
        
        return errors
    
    def _is_valid_ldap_url(self, url: str) -> bool:
        """Check if LDAP URL is valid."""
        return url.startswith(('ldap://', 'ldaps://'))
    
    def _is_valid_dn(self, dn: str) -> bool:
        """Check if DN format is valid (basic check)."""
        return '=' in dn and ('dc=' in dn.lower() or 'cn=' in dn.lower() or 'ou=' in dn.lower())
    
    def __del__(self):
        """Cleanup thread pool on destruction."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)