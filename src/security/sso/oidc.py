"""
OpenID Connect (OIDC) SSO Connector for SuperInsight Platform.

Implements OpenID Connect authentication flow.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, urlparse
import uuid
import aiohttp
import jwt
from datetime import datetime, timedelta

from src.models.security import SSOProtocol
from src.security.sso.base import (
    SSOConnector, SSOUserInfo, LoginInitiation, SSOLoginResult,
    LogoutResult, SSOAuthenticationError
)


class OIDCConnector(SSOConnector):
    """
    OpenID Connect (OIDC) SSO Connector.
    
    Implements OIDC authentication flow with ID token validation.
    """
    
    @property
    def protocol(self) -> SSOProtocol:
        return SSOProtocol.OIDC
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.discovery_url = config.get("discovery_url")
        self.issuer = config.get("issuer")
        self.authorization_url = config.get("authorization_url")
        self.token_url = config.get("token_url")
        self.userinfo_url = config.get("userinfo_url")
        self.jwks_url = config.get("jwks_url")
        self.end_session_url = config.get("end_session_url")
        self.scope = config.get("scope", "openid profile email")
        self.use_pkce = config.get("use_pkce", True)
        self.supports_slo = bool(self.end_session_url)
        
        # OIDC-specific settings
        self.response_type = config.get("response_type", "code")
        self.response_mode = config.get("response_mode", "query")
        
        # Attribute mapping
        self.attribute_mapping = config.get("attribute_mapping", {
            "email": "email",
            "name": "name",
            "first_name": "given_name",
            "last_name": "family_name",
            "username": "preferred_username",
            "groups": "groups"
        })
        
        # Cache for OIDC discovery and JWKS
        self._discovery_cache = None
        self._jwks_cache = None
        self._cache_expiry = None
    
    async def initiate_login(self, redirect_uri: str, state: Optional[str] = None) -> LoginInitiation:
        """
        Initiate OIDC authentication flow.
        
        Args:
            redirect_uri: URI to redirect after authentication
            state: Optional state parameter for CSRF protection
            
        Returns:
            LoginInitiation with OIDC authorization URL
        """
        # Ensure we have discovery information
        await self._ensure_discovery()
        
        # Generate state and nonce
        if not state:
            state = f"oidc_{uuid.uuid4().hex}"
        nonce = f"nonce_{uuid.uuid4().hex}"
        
        # Build authorization parameters
        params = {
            "response_type": self.response_type,
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": self.scope,
            "state": state,
            "nonce": nonce
        }
        
        # Add response mode if specified
        if self.response_mode != "query":
            params["response_mode"] = self.response_mode
        
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
            nonce=code_verifier or nonce,  # Store code_verifier or nonce
            provider_name=self.name
        )
    
    async def validate_callback(self, callback_data: Dict[str, Any]) -> SSOUserInfo:
        """
        Validate OIDC callback and process ID token.
        
        Args:
            callback_data: OIDC callback data with authorization code
            
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
            raise SSOAuthenticationError(f"OIDC error: {error} - {error_description}", self.name)
        
        # Extract callback parameters
        state = callback_data.get("state")
        redirect_uri = callback_data.get("redirect_uri")
        code_verifier = callback_data.get("code_verifier")  # For PKCE
        expected_nonce = callback_data.get("nonce")
        
        try:
            # Exchange authorization code for tokens
            token_response = await self._exchange_code_for_tokens(code, redirect_uri, code_verifier)
            
            # Validate and decode ID token
            id_token = token_response.get("id_token")
            if not id_token:
                raise SSOAuthenticationError("No ID token received", self.name)
            
            id_token_claims = await self._validate_id_token(id_token, expected_nonce)
            
            # Get additional user info if needed
            access_token = token_response.get("access_token")
            user_info = {}
            if access_token and self.userinfo_url:
                user_info = await self._get_user_info(access_token)
            
            # Combine ID token claims with user info
            combined_info = {**id_token_claims, **user_info}
            
            # Map attributes and create user info
            mapped_attrs = self.map_attributes(combined_info)
            
            return SSOUserInfo(
                sso_id=id_token_claims["sub"],
                email=mapped_attrs.get("email") or id_token_claims.get("email"),
                name=mapped_attrs.get("name") or id_token_claims.get("name"),
                first_name=mapped_attrs.get("first_name") or id_token_claims.get("given_name"),
                last_name=mapped_attrs.get("last_name") or id_token_claims.get("family_name"),
                username=mapped_attrs.get("username") or id_token_claims.get("preferred_username"),
                groups=self._extract_groups(combined_info),
                attributes=combined_info,
                provider_name=self.name
            )
            
        except Exception as e:
            self.logger.error(f"OIDC callback validation error: {e}")
            raise SSOAuthenticationError(f"OIDC validation failed: {e}", self.name)
    
    async def initiate_logout(self, user_id: str, session_id: Optional[str] = None) -> LogoutResult:
        """
        Initiate OIDC logout (RP-Initiated Logout).
        
        Args:
            user_id: User to log out
            session_id: Optional session ID
            
        Returns:
            LogoutResult with logout URL
        """
        if not self.supports_slo:
            return LogoutResult(success=True)
        
        # Build logout parameters
        params = {
            "client_id": self.client_id,
            "post_logout_redirect_uri": callback_data.get("post_logout_redirect_uri", "")
        }
        
        # Add ID token hint if available
        id_token_hint = callback_data.get("id_token_hint")
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        
        logout_url = f"{self.end_session_url}?{urlencode(params)}"
        
        return LogoutResult(success=True, redirect_url=logout_url)
    
    async def _ensure_discovery(self) -> None:
        """Ensure OIDC discovery information is loaded."""
        if self._discovery_cache and self._cache_expiry and datetime.utcnow() < self._cache_expiry:
            return
        
        if self.discovery_url:
            await self._load_discovery()
        else:
            # Use manually configured endpoints
            self._discovery_cache = {
                "issuer": self.issuer,
                "authorization_endpoint": self.authorization_url,
                "token_endpoint": self.token_url,
                "userinfo_endpoint": self.userinfo_url,
                "jwks_uri": self.jwks_url,
                "end_session_endpoint": self.end_session_url
            }
    
    async def _load_discovery(self) -> None:
        """Load OIDC discovery document."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.discovery_url) as response:
                if response.status != 200:
                    raise SSOConfigurationError(f"Failed to load OIDC discovery: {response.status}")
                
                self._discovery_cache = await response.json()
                self._cache_expiry = datetime.utcnow() + timedelta(hours=1)
                
                # Update endpoints from discovery
                self.issuer = self._discovery_cache.get("issuer", self.issuer)
                self.authorization_url = self._discovery_cache.get("authorization_endpoint", self.authorization_url)
                self.token_url = self._discovery_cache.get("token_endpoint", self.token_url)
                self.userinfo_url = self._discovery_cache.get("userinfo_endpoint", self.userinfo_url)
                self.jwks_url = self._discovery_cache.get("jwks_uri", self.jwks_url)
                self.end_session_url = self._discovery_cache.get("end_session_endpoint", self.end_session_url)
    
    async def _exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
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
                
                return await response.json()
    
    async def _validate_id_token(self, id_token: str, expected_nonce: Optional[str] = None) -> Dict[str, Any]:
        """Validate and decode OIDC ID token."""
        try:
            # Decode without verification first to get header
            unverified_header = jwt.get_unverified_header(id_token)
            
            # Get signing key
            signing_key = await self._get_signing_key(unverified_header.get("kid"))
            
            # Decode and verify token
            claims = jwt.decode(
                id_token,
                signing_key,
                algorithms=["RS256", "HS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={"verify_exp": True, "verify_aud": True, "verify_iss": True}
            )
            
            # Validate nonce if provided
            if expected_nonce and claims.get("nonce") != expected_nonce:
                raise SSOAuthenticationError("Invalid nonce in ID token", self.name)
            
            return claims
            
        except jwt.ExpiredSignatureError:
            raise SSOAuthenticationError("ID token has expired", self.name)
        except jwt.InvalidAudienceError:
            raise SSOAuthenticationError("Invalid audience in ID token", self.name)
        except jwt.InvalidIssuerError:
            raise SSOAuthenticationError("Invalid issuer in ID token", self.name)
        except jwt.InvalidTokenError as e:
            raise SSOAuthenticationError(f"Invalid ID token: {e}", self.name)
    
    async def _get_signing_key(self, kid: Optional[str] = None) -> str:
        """Get signing key from JWKS endpoint."""
        if not self.jwks_url:
            raise SSOConfigurationError("No JWKS URL configured")
        
        # Load JWKS if not cached
        if not self._jwks_cache:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.jwks_url) as response:
                    if response.status != 200:
                        raise SSOConfigurationError(f"Failed to load JWKS: {response.status}")
                    
                    self._jwks_cache = await response.json()
        
        # Find matching key
        keys = self._jwks_cache.get("keys", [])
        
        if kid:
            # Find key by ID
            for key in keys:
                if key.get("kid") == kid:
                    return self._jwk_to_pem(key)
        
        # Use first available key
        if keys:
            return self._jwk_to_pem(keys[0])
        
        raise SSOConfigurationError("No suitable signing key found in JWKS")
    
    def _jwk_to_pem(self, jwk: Dict[str, Any]) -> str:
        """Convert JWK to PEM format (simplified implementation)."""
        # In a real implementation, this would properly convert JWK to PEM
        # For now, return a placeholder
        return "-----BEGIN PUBLIC KEY-----\nplaceholder\n-----END PUBLIC KEY-----"
    
    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get additional user information from userinfo endpoint."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.userinfo_url, headers=headers) as response:
                if response.status != 200:
                    self.logger.warning(f"Failed to get user info: {response.status}")
                    return {}
                
                return await response.json()
    
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
        
        alphabet = string.ascii_letters + string.digits + "-._~"
        return ''.join(secrets.choice(alphabet) for _ in range(128))
    
    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate PKCE code challenge from verifier."""
        import hashlib
        import base64
        
        digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(digest).decode('utf-8')
        return challenge.rstrip('=')
    
    def validate_config(self) -> List[str]:
        """Validate OIDC connector configuration."""
        errors = []
        
        if not self.client_id:
            errors.append("client_id is required")
        
        if not self.discovery_url and not all([self.issuer, self.authorization_url, self.token_url]):
            errors.append("Either discovery_url or manual endpoint configuration is required")
        
        if not self.use_pkce and not self.client_secret:
            errors.append("client_secret is required when PKCE is disabled")
        
        # Validate URLs
        urls_to_check = []
        
        if self.discovery_url:
            urls_to_check.append(("discovery_url", self.discovery_url))
        
        if self.authorization_url:
            urls_to_check.append(("authorization_url", self.authorization_url))
        
        if self.token_url:
            urls_to_check.append(("token_url", self.token_url))
        
        if self.userinfo_url:
            urls_to_check.append(("userinfo_url", self.userinfo_url))
        
        if self.jwks_url:
            urls_to_check.append(("jwks_url", self.jwks_url))
        
        if self.end_session_url:
            urls_to_check.append(("end_session_url", self.end_session_url))
        
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