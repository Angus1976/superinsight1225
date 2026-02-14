"""
Authentication and credential management for AI Application Integration.

This module provides secure API credential generation, hashing, and validation
for AI gateways using bcrypt for secure password hashing, and JWT token
generation and validation using RS256 signing.
"""

import secrets
import string
from typing import Tuple, Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


@dataclass
class APICredentials:
    """
    API credentials for gateway authentication.
    
    Attributes:
        api_key: Plain text API key (only available at generation time)
        api_secret: Plain text API secret (only available at generation time)
        api_key_hash: Bcrypt hash of the API key (for storage)
        api_secret_hash: Bcrypt hash of the API secret (for storage)
    """
    api_key: str
    api_secret: str
    api_key_hash: str
    api_secret_hash: str


@dataclass
class TokenClaims:
    """
    JWT token claims for gateway authentication.
    
    Attributes:
        gateway_id: Unique identifier of the gateway
        tenant_id: Tenant ID for multi-tenant isolation
        permissions: List of permissions granted to the gateway
        issued_at: Token issuance timestamp
        expires_at: Token expiration timestamp
    """
    gateway_id: str
    tenant_id: str
    permissions: List[str]
    issued_at: datetime
    expires_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert claims to dictionary for JWT encoding."""
        return {
            'gateway_id': self.gateway_id,
            'tenant_id': self.tenant_id,
            'permissions': self.permissions,
            'iat': int(self.issued_at.timestamp()),
            'exp': int(self.expires_at.timestamp()),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenClaims':
        """Create TokenClaims from JWT payload dictionary."""
        return cls(
            gateway_id=data['gateway_id'],
            tenant_id=data['tenant_id'],
            permissions=data.get('permissions', []),
            issued_at=datetime.fromtimestamp(data['iat']),
            expires_at=datetime.fromtimestamp(data['exp']),
        )


class JWTTokenService:
    """
    JWT token service for gateway authentication.
    
    Uses RS256 (RSA with SHA-256) for signing tokens. Private key is used
    for signing, public key for verification.
    """
    
    def __init__(self, private_key: Optional[bytes] = None, public_key: Optional[bytes] = None):
        """
        Initialize JWT token service.
        
        Args:
            private_key: RSA private key in PEM format (for signing)
            public_key: RSA public key in PEM format (for verification)
            
        If keys are not provided, they will be generated automatically.
        """
        if private_key and public_key:
            self._private_key = serialization.load_pem_private_key(
                private_key,
                password=None,
                backend=default_backend()
            )
            self._public_key = serialization.load_pem_public_key(
                public_key,
                backend=default_backend()
            )
        else:
            # Generate new RSA key pair
            self._private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self._public_key = self._private_key.public_key()
    
    def get_private_key_pem(self) -> bytes:
        """Get private key in PEM format."""
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    
    def get_public_key_pem(self) -> bytes:
        """Get public key in PEM format."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def generate_token(
        self,
        gateway_id: str,
        tenant_id: str,
        permissions: List[str],
        expires_in_seconds: int = 3600
    ) -> str:
        """
        Generate a JWT token for gateway authentication.
        
        Args:
            gateway_id: Unique identifier of the gateway
            tenant_id: Tenant ID for multi-tenant isolation
            permissions: List of permissions granted to the gateway
            expires_in_seconds: Token expiration time in seconds (default: 1 hour)
            
        Returns:
            JWT token string
            
        Example:
            >>> service = JWTTokenService()
            >>> token = service.generate_token(
            ...     gateway_id="gw_123",
            ...     tenant_id="tenant_456",
            ...     permissions=["read:data", "write:data"]
            ... )
            >>> isinstance(token, str)
            True
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=expires_in_seconds)
        
        claims = TokenClaims(
            gateway_id=gateway_id,
            tenant_id=tenant_id,
            permissions=permissions,
            issued_at=now,
            expires_at=expires_at
        )
        
        token = jwt.encode(
            claims.to_dict(),
            self.get_private_key_pem(),
            algorithm='RS256'
        )
        
        return token
    
    def validate_token(self, token: str) -> TokenClaims:
        """
        Validate a JWT token and extract claims.
        
        Args:
            token: JWT token string to validate
            
        Returns:
            TokenClaims object with extracted claims
            
        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
            
        Example:
            >>> service = JWTTokenService()
            >>> token = service.generate_token("gw_123", "tenant_456", ["read:data"])
            >>> claims = service.validate_token(token)
            >>> claims.gateway_id
            'gw_123'
            >>> claims.tenant_id
            'tenant_456'
        """
        try:
            payload = jwt.decode(
                token,
                self.get_public_key_pem(),
                algorithms=['RS256']
            )
            return TokenClaims.from_dict(payload)
        except jwt.ExpiredSignatureError:
            raise jwt.ExpiredSignatureError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if a token is expired without raising an exception.
        
        Args:
            token: JWT token string to check
            
        Returns:
            True if token is expired, False otherwise
            
        Example:
            >>> service = JWTTokenService()
            >>> token = service.generate_token("gw_123", "tenant_456", [], expires_in_seconds=1)
            >>> service.is_token_expired(token)
            False
        """
        try:
            self.validate_token(token)
            return False
        except jwt.ExpiredSignatureError:
            return True
        except jwt.InvalidTokenError:
            # Invalid tokens are considered expired
            return True


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.
    
    Uses secrets module for cryptographically strong random generation.
    The key contains uppercase, lowercase letters and digits.
    
    Args:
        length: Length of the API key (default: 32)
        
    Returns:
        Secure random API key string
        
    Example:
        >>> key = generate_api_key()
        >>> len(key)
        32
        >>> all(c in string.ascii_letters + string.digits for c in key)
        True
    """
    if length < 16:
        raise ValueError("API key length must be at least 16 characters")
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_api_secret(length: int = 64) -> str:
    """
    Generate a secure random API secret.
    
    Uses secrets module for cryptographically strong random generation.
    The secret is longer than the key for additional security.
    Limited to 64 characters by default to stay within bcrypt's 72-byte limit.
    
    Args:
        length: Length of the API secret (default: 64, max recommended: 64)
        
    Returns:
        Secure random API secret string
        
    Example:
        >>> secret = generate_api_secret()
        >>> len(secret)
        64
    """
    if length < 32:
        raise ValueError("API secret length must be at least 32 characters")
    
    if length > 64:
        raise ValueError("API secret length should not exceed 64 characters (bcrypt 72-byte limit)")
    
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_credential(credential: str) -> str:
    """
    Hash a credential using bcrypt.
    
    Uses bcrypt with a work factor of 12 for secure password hashing.
    The hash includes a random salt automatically.
    Bcrypt has a 72-byte limit, so credentials are truncated if needed.
    
    Args:
        credential: Plain text credential to hash
        
    Returns:
        Bcrypt hash string (includes salt)
        
    Example:
        >>> hash1 = hash_credential("test_key")
        >>> hash2 = hash_credential("test_key")
        >>> hash1 != hash2  # Different salts
        True
        >>> verify_credential("test_key", hash1)
        True
    """
    if not credential:
        raise ValueError("Credential cannot be empty")
    
    # Convert to bytes and truncate to 72 bytes (bcrypt limit)
    credential_bytes = credential.encode('utf-8')[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(credential_bytes, salt)
    
    return hashed.decode('utf-8')


def verify_credential(credential: str, credential_hash: str) -> bool:
    """
    Verify a credential against its bcrypt hash.
    
    Uses constant-time comparison to prevent timing attacks.
    Truncates credential to 72 bytes to match bcrypt limit.
    
    Args:
        credential: Plain text credential to verify
        credential_hash: Bcrypt hash to verify against
        
    Returns:
        True if credential matches hash, False otherwise
        
    Example:
        >>> hash_val = hash_credential("my_secret")
        >>> verify_credential("my_secret", hash_val)
        True
        >>> verify_credential("wrong_secret", hash_val)
        False
    """
    if not credential or not credential_hash:
        return False
    
    try:
        # Truncate to 72 bytes to match bcrypt limit
        credential_bytes = credential.encode('utf-8')[:72]
        hash_bytes = credential_hash.encode('utf-8')
        return bcrypt.checkpw(credential_bytes, hash_bytes)
    except (ValueError, AttributeError):
        return False


def generate_credentials(
    api_key_length: int = 32,
    api_secret_length: int = 64
) -> APICredentials:
    """
    Generate a complete set of API credentials with hashes.
    
    Creates secure random API key and secret, then generates bcrypt hashes
    for storage. The plain text credentials should only be shown to the user
    once at generation time.
    
    Args:
        api_key_length: Length of API key (default: 32)
        api_secret_length: Length of API secret (default: 64)
        
    Returns:
        APICredentials object with plain text and hashed credentials
        
    Example:
        >>> creds = generate_credentials()
        >>> len(creds.api_key)
        32
        >>> len(creds.api_secret)
        64
        >>> verify_credential(creds.api_key, creds.api_key_hash)
        True
        >>> verify_credential(creds.api_secret, creds.api_secret_hash)
        True
    """
    # Generate plain text credentials
    api_key = generate_api_key(api_key_length)
    api_secret = generate_api_secret(api_secret_length)
    
    # Generate hashes for storage
    api_key_hash = hash_credential(api_key)
    api_secret_hash = hash_credential(api_secret)
    
    return APICredentials(
        api_key=api_key,
        api_secret=api_secret,
        api_key_hash=api_key_hash,
        api_secret_hash=api_secret_hash
    )


def validate_credentials(
    api_key: str,
    api_secret: str,
    api_key_hash: str,
    api_secret_hash: str
) -> bool:
    """
    Validate API credentials against stored hashes.
    
    Verifies both API key and secret must match their respective hashes.
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        api_key: Plain text API key to validate
        api_secret: Plain text API secret to validate
        api_key_hash: Stored bcrypt hash of API key
        api_secret_hash: Stored bcrypt hash of API secret
        
    Returns:
        True if both credentials are valid, False otherwise
        
    Example:
        >>> creds = generate_credentials()
        >>> validate_credentials(
        ...     creds.api_key,
        ...     creds.api_secret,
        ...     creds.api_key_hash,
        ...     creds.api_secret_hash
        ... )
        True
        >>> validate_credentials(
        ...     "wrong_key",
        ...     creds.api_secret,
        ...     creds.api_key_hash,
        ...     creds.api_secret_hash
        ... )
        False
    """
    key_valid = verify_credential(api_key, api_key_hash)
    secret_valid = verify_credential(api_secret, api_secret_hash)
    
    return key_valid and secret_valid
