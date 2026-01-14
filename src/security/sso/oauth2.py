"""
OAuth 2.0 SSO Connector for SuperInsight Platform.

Implements OAuth 2.0 Authorization Code flow.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, urlparse, parse_qs
import uuid
import aiohttp
from datetime import datetime, timedelta

from src.models.security import SSOProtocol
from src.security.sso.base import (
    SSOConnector, SSOUserInfo, LoginInitiation, SSOLoginResult,
    LogoutResult, SSOAuthenticationError
)


class OAuth2Connector(SSOConnector):
    """
    OAuth 2.0 SSO Connector.
    
    Implements OAuth 2.0 Authorization Code flow with PKCE support.
    """
    
    @property
    def protocol(self) -> SSOProtocol:
        return SSOProtocol.OAUTH2
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.authorization_url = config.get("authorization_url")
        self.token_url = config.get("token_url")
        self.userinfo_url = config.get("userinfo_url")
        self.logout_url = config.get("logout_url")
        self.scope = config.get("scope", "openid profile email")
        self.use_pkce = config.get("use_pkce", True)
        self.supports_slo = bool(self.logout_url)
        
        # Attribute mapping for user info
        self.attribute_mapping = config.get("attribute_mapping", {
            "email": "email",
            "name": "name",
            "first_name": "given_name",
            "last_name": "family_name",
            "username": "preferred_username",
            "groups": "groups"
        })
    
    async def initiate_login(self, redirect_uri: str, state: Optional[str] = None) -> LoginInitiation:
        """
        Initiate OAuth 2.0 authorization flow.
        
        Args:
            redirect_uri: URI to redirect after authentication
            state: Optional state parameter for CSRF protection
            
        Returns:
            LoginInitiation with OAuth authorization URL
        """
        # Generate state if not provided
        if not state:
            state = f"oauth2_{uuid.uuid4().hex}"
        
        # Build authorization parameters
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": self.scope,
            "state": state
        }
        
        # Add PKCE parameters if enabled
        code_verifier = None
        if self.use_pkce:
            code_verifier = self._generate_code_verifier()
            code_challenge = self._generate_code_challenge(code_verifier)
            params.update({
                "code_challenge": code_challenge,
                "code_challenge_method": "S256"
            })
        
        # Build authorization URL
        auth_url = f"{self.authorization_url}?{urlencode(params)}"
        
        return LoginInitiation(
            redirect_url=auth_url,
            state=state,
            nonce=code_verifier,  # Store code_verifier in nonce for PKCE
            provider_name=self.name
        )
    
    async def validate_callback(self, callback_data: Dict[str, Any]) -> SSOUserInfo:
        """
        Validate OAuth 2.0 callback and exchange code for tokens.
        
        Args:
            callback_data: OAuth callback data with authorization code
            
        Returns:
            SSOUserInfo with user details
            
        Raises:
            SSOAuthenticationError: If validation fails
        """
        # Extract authorization code
        code = callback_data.get("code")
        if not code:
            error = callback_data.get("error", "unknown_error")
            error_description = callback_data.get("error_description", "No authorization code received")
            raise SSOAuthenticationError(f"OAuth error: {error} - {error_description}", self.name)
        
        # Extract state and redirect_uri
        state = callback_data.get("state")
        redirect_uri = callback_data.get("redirect_uri")
        code_verifier = callback_data.get("code_verifier")  # For PKCE
        
        try:
            # Exchange authorization code for access token
            token_response = await self._exchange_code_for_token(code, redirect_uri, code_verifier)
            
            # Get user information using access token
            user_info = await self._get_user_info(token_response["access_token"])
            
            return user_info
            
        except Exception as e:
            self.logger.error(f"OAuth 2.0 callback validation error: {e}")
            raise SSOAuthenticationError(f"Token exchange failed: {e}", self.name)
    
    async def initiate_logout(self, user_id: str, session_id: Optional[str] = None) -> LogoutResult:
        """
        Initiate OAuth 2.0 logout.
        
        Args:
            user_id: User to log out
            session_id: Optional session ID
            
        Returns:
            LogoutResult with logout URL if supported
        """
        if not self.supports_slo:
            return LogoutResult(success=True)
        
        # Build logout URL with parameters
        params = {
            "client_id": self.client_id,
            "post_logout_redirect_uri": callback_data.get("post_logout_redirect_uri", "")
        }
        
        logout_url = f"{self.logout_url}?{urlencode(params)}"
        
        return LogoutResult(success=True, redirect_url=logout_url)
    
    async def _exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id
        }
        
        # Add client secret if not using PKCE
        if not self.use_pkce and self.client_secret:
            token_data["client_secret"] = self.client_secret
        
        # Add PKCE code verifier
        if self.use_pkce and code_verifier:
            token_data["code_verifier"] = code_verifier
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        # Add basic auth if using client secret
        auth = None
        if self.client_secret and not self.use_pkce:
            auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.token_url,
                data=token_data,
                headers=headers,
                auth=auth
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise SSOAuthenticationError(f"Token exchange failed: {error_text}", self.name)
                
                token_response = await response.json()
                
                if "error" in token_response:
                    error = token_response.get("error", "unknown_error")
                    error_description = token_response.get("error_description", "Token exchange failed")
                    raise SSOAuthenticationError(f"Token error: {error} - {error_description}", self.name)
                
                return token_response
    
    async def _get_user_info(self, access_token: str) -> SSOUserInfo:
        """Get user information using access token."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.userinfo_url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise SSOAuthenticationError(f"User info request failed: {error_text}", self.name)
                
                user_data = await response.json()
                
                # Map attributes to standard fields
                mapped_attrs = self.map_attributes(user_data)
                
                # Extract user ID (try multiple common fields)
                sso_id = user_data.get("sub") or user_data.get("id") or user_data.get("user_id")
                if not sso_id:
                    raise SSOAuthenticationError("No user ID found in user info", self.name)
                
                # Extract email
                email = mapped_attrs.get("email")
                if not email:
                    raise SSOAuthenticationError("No email found in user info", self.name)
                
                return SSOUserInfo(
                    sso_id=str(sso_id),
                    email=email,
                    name=mapped_attrs.get("name"),
                    first_name=mapped_attrs.get("first_name"),
                    last_name=mapped_attrs.get("last_name"),
                    username=mapped_attrs.get("username"),
                    groups=self._extract_groups(user_data),
                    attributes=user_data,
                    provider_name=self.name
                )
    
    def _extract_groups(self, user_data: Dict[str, Any]) -> List[str]:
        """Extract groups from user data."""
        groups = user_data.get("groups", [])
        
        # Handle different group formats
        if isinstance(groups, str):
            return [groups]
        elif isinstance(groups, list):
            return [str(g) for g in groups]
        else:
            return []
    
    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier."""
        import secrets
        import string
        
        # Generate random string (43-128 characters)
        alphabet = string.ascii_letters + string.digits + "-._~"
        return ''.join(secrets.choice(alphabet) for _ in range(128))
    
    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate PKCE code challenge from verifier."""
        import hashlib
        import base64
        
        # SHA256 hash of code verifier
        digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        
        # Base64 URL-safe encode
        challenge = base64.urlsafe_b64encode(digest).decode('utf-8')
        
        # Remove padding
        return challenge.rstrip('=')
    
    def validate_config(self) -> List[str]:
        """Validate OAuth 2.0 connector configuration."""
        errors = []
        
        if not self.client_id:
            errors.append("client_id is required")
        
        if not self.authorization_url:
            errors.append("authorization_url is required")
        
        if not self.token_url:
            errors.append("token_url is required")
        
        if not self.userinfo_url:
            errors.append("userinfo_url is required")
        
        if not self.use_pkce and not self.client_secret:
            errors.append("client_secret is required when PKCE is disabled")
        
        # Validate URLs
        urls_to_check = [
            ("authorization_url", self.authorization_url),
            ("token_url", self.token_url),
            ("userinfo_url", self.userinfo_url)
        ]
        
        if self.logout_url:
            urls_to_check.append(("logout_url", self.logout_url))
        
        for name, url in urls_to_check:
            if url and not self._is_valid_url(url):
                errors.append(f"{name} is not a valid URL")
        
        return errors
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False