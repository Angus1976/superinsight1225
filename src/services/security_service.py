"""
Security Service for Data Lifecycle Management

Provides JWT token management, input sanitization, and data encryption
utilities for the data lifecycle system.

Validates: Requirements 24.1, 24.2, 24.3, 24.5
"""

import re
import time
import hashlib
import html
from typing import Optional
from dataclasses import dataclass

import jwt
from cryptography.fernet import Fernet, InvalidToken


# --- Configuration defaults ---

DEFAULT_JWT_SECRET = "change-me-in-production"
DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_TOKEN_EXPIRY_SECONDS = 3600  # 1 hour
MAX_INPUT_LENGTH = 10000


# --- Data classes ---

@dataclass
class TokenPayload:
    """Decoded JWT token payload."""
    user_id: str
    roles: list
    issued_at: float
    expires_at: float
    extra: dict


@dataclass
class SanitizationResult:
    """Result of input sanitization."""
    value: str
    was_modified: bool
    violations: list


# --- JWT Token Management ---

class JWTManager:
    """Handles JWT token creation and validation."""

    def __init__(
        self,
        secret: str = DEFAULT_JWT_SECRET,
        algorithm: str = DEFAULT_JWT_ALGORITHM,
        expiry_seconds: int = DEFAULT_TOKEN_EXPIRY_SECONDS,
    ):
        self.secret = secret
        self.algorithm = algorithm
        self.expiry_seconds = expiry_seconds

    def create_token(
        self,
        user_id: str,
        roles: Optional[list] = None,
        extra: Optional[dict] = None,
        expiry_seconds: Optional[int] = None,
    ) -> str:
        """Create a JWT token for a user."""
        if not user_id:
            raise ValueError("user_id is required")

        now = time.time()
        exp = now + (expiry_seconds or self.expiry_seconds)

        payload = {
            "sub": user_id,
            "roles": roles or [],
            "iat": now,
            "exp": exp,
        }
        if extra:
            payload["extra"] = extra

        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def validate_token(self, token: str) -> TokenPayload:
        """
        Validate and decode a JWT token.

        Raises:
            ValueError: If token is invalid or expired.
        """
        if not token:
            raise ValueError("Token is required")

        try:
            decoded = jwt.decode(
                token, self.secret, algorithms=[self.algorithm]
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")

        return TokenPayload(
            user_id=decoded.get("sub", ""),
            roles=decoded.get("roles", []),
            issued_at=decoded.get("iat", 0),
            expires_at=decoded.get("exp", 0),
            extra=decoded.get("extra", {}),
        )

    def is_token_expired(self, token: str) -> bool:
        """Check if a token is expired without raising."""
        try:
            self.validate_token(token)
            return False
        except ValueError:
            return True


# --- Input Sanitization ---

# Patterns for detecting malicious content
SCRIPT_TAG_PATTERN = re.compile(
    r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL
)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
EVENT_HANDLER_PATTERN = re.compile(
    r"\bon\w+\s*=", re.IGNORECASE
)
JAVASCRIPT_URI_PATTERN = re.compile(
    r"javascript\s*:", re.IGNORECASE
)


def sanitize_input(
    value: str,
    max_length: int = MAX_INPUT_LENGTH,
    strip_html: bool = True,
) -> SanitizationResult:
    """
    Sanitize user input to prevent XSS and other injection attacks.

    Args:
        value: Raw user input string.
        max_length: Maximum allowed length.
        strip_html: Whether to strip HTML tags.

    Returns:
        SanitizationResult with cleaned value and violation info.
    """
    if not isinstance(value, str):
        return SanitizationResult(
            value=str(value), was_modified=True, violations=["non_string_input"]
        )

    violations = []
    original = value

    # Length check
    if len(value) > max_length:
        value = value[:max_length]
        violations.append(f"truncated_to_{max_length}")

    # Strip script tags
    if SCRIPT_TAG_PATTERN.search(value):
        value = SCRIPT_TAG_PATTERN.sub("", value)
        violations.append("script_tags_removed")

    # Strip event handlers (onclick=, onerror=, etc.)
    if EVENT_HANDLER_PATTERN.search(value):
        value = EVENT_HANDLER_PATTERN.sub("", value)
        violations.append("event_handlers_removed")

    # Strip javascript: URIs
    if JAVASCRIPT_URI_PATTERN.search(value):
        value = JAVASCRIPT_URI_PATTERN.sub("", value)
        violations.append("javascript_uri_removed")

    # Strip all HTML tags if requested
    if strip_html and HTML_TAG_PATTERN.search(value):
        value = HTML_TAG_PATTERN.sub("", value)
        violations.append("html_tags_removed")

    # HTML-escape remaining special characters
    value = html.escape(value, quote=True)
    was_modified = value != original

    return SanitizationResult(
        value=value, was_modified=was_modified, violations=violations
    )


def sanitize_dict(
    data: dict,
    max_length: int = MAX_INPUT_LENGTH,
    strip_html: bool = True,
) -> dict:
    """Sanitize all string values in a dictionary recursively."""
    sanitized = {}
    for key, val in data.items():
        if isinstance(val, str):
            result = sanitize_input(val, max_length, strip_html)
            sanitized[key] = result.value
        elif isinstance(val, dict):
            sanitized[key] = sanitize_dict(val, max_length, strip_html)
        elif isinstance(val, list):
            sanitized[key] = [
                sanitize_input(item, max_length, strip_html).value
                if isinstance(item, str) else item
                for item in val
            ]
        else:
            sanitized[key] = val
    return sanitized


# --- Data Encryption at Rest ---

class DataEncryptor:
    """Symmetric encryption for sensitive data at rest using Fernet."""

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize with a Fernet key.

        Args:
            key: 32-byte URL-safe base64-encoded key.
                 If None, generates a new key.
        """
        self._key = key or Fernet.generate_key()
        self._fernet = Fernet(self._key)

    @property
    def key(self) -> bytes:
        """Return the encryption key (for secure storage)."""
        return self._key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
        if not plaintext:
            return ""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a ciphertext string.

        Raises:
            ValueError: If decryption fails (wrong key or corrupted data).
        """
        if not ciphertext:
            return ""
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            raise ValueError("Decryption failed: invalid key or corrupted data")

    def encrypt_dict_fields(
        self, data: dict, fields: list
    ) -> dict:
        """Encrypt specified fields in a dictionary."""
        result = dict(data)
        for field in fields:
            if field in result and isinstance(result[field], str):
                result[field] = self.encrypt(result[field])
        return result

    def decrypt_dict_fields(
        self, data: dict, fields: list
    ) -> dict:
        """Decrypt specified fields in a dictionary."""
        result = dict(data)
        for field in fields:
            if field in result and isinstance(result[field], str):
                result[field] = self.decrypt(result[field])
        return result


# --- Row-Level Security ---

class RowLevelSecurity:
    """Helper for filtering data based on user permissions."""

    # Role-based access rules: role -> allowed resource types
    ROLE_ACCESS_MAP = {
        "admin": ["*"],
        "reviewer": ["temp_data", "sample"],
        "annotator": ["annotation_task", "annotated_data"],
        "viewer": ["sample", "trial"],
    }

    @staticmethod
    def get_accessible_resource_types(user_roles: list) -> list:
        """Return resource types accessible by the user's roles."""
        if not user_roles:
            return []

        accessible = set()
        for role in user_roles:
            allowed = RowLevelSecurity.ROLE_ACCESS_MAP.get(role, [])
            if "*" in allowed:
                return ["*"]
            accessible.update(allowed)

        return list(accessible)

    @staticmethod
    def can_access_resource(
        user_id: str,
        user_roles: list,
        resource_type: str,
        resource_owner_id: Optional[str] = None,
    ) -> bool:
        """
        Check if a user can access a specific resource.

        Admins can access everything. Other roles are checked against
        the role access map. Owners can always access their own resources.
        """
        # Owner always has access
        if resource_owner_id and user_id == resource_owner_id:
            return True

        accessible = RowLevelSecurity.get_accessible_resource_types(user_roles)

        if "*" in accessible:
            return True

        return resource_type in accessible

    @staticmethod
    def filter_query_by_access(
        user_id: str,
        user_roles: list,
        resource_type: str,
    ) -> dict:
        """
        Return filter criteria for row-level security.

        Returns a dict of filters to apply to database queries.
        Admins get no filters (full access).
        Others get filtered to their own resources.
        """
        if "admin" in user_roles:
            return {}

        accessible = RowLevelSecurity.get_accessible_resource_types(user_roles)
        if resource_type not in accessible and "*" not in accessible:
            return {"__deny_all__": True}

        # Non-admin users see only their own resources
        return {"owner_id": user_id}
