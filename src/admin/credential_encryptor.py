"""
Credential Encryptor for SuperInsight Platform.

Provides secure encryption, decryption, and masking of sensitive credentials
such as API keys, passwords, and other secrets.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256).
"""

import os
import base64
import logging
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class CredentialEncryptor:
    """
    Credential encryptor for secure handling of sensitive information.
    
    Features:
    - AES-128-CBC encryption with HMAC-SHA256 authentication
    - Key derivation from master password using PBKDF2
    - Masking for display purposes
    - Encrypted value detection
    
    Usage:
        encryptor = CredentialEncryptor()
        encrypted = encryptor.encrypt("my-secret-api-key")
        decrypted = encryptor.decrypt(encrypted)
        masked = encryptor.mask("my-secret-api-key")  # "my-s****-key"
    """
    
    # Prefix to identify encrypted values
    ENCRYPTED_PREFIX = "enc:"
    
    def __init__(self, encryption_key: Optional[str] = None, salt: Optional[bytes] = None):
        """
        Initialize the credential encryptor.
        
        Args:
            encryption_key: Master encryption key. If not provided, uses
                           ADMIN_ENCRYPTION_KEY environment variable or generates one.
            salt: Salt for key derivation. If not provided, uses a default salt.
        """
        self._salt = salt or self._get_default_salt()
        self._fernet = self._create_fernet(encryption_key)
    
    def _get_default_salt(self) -> bytes:
        """Get default salt from environment or use a fixed value."""
        env_salt = os.environ.get("ADMIN_ENCRYPTION_SALT")
        if env_salt:
            return env_salt.encode()
        # Default salt (should be overridden in production)
        return b"superinsight_admin_salt_v1"
    
    def _create_fernet(self, encryption_key: Optional[str] = None) -> Fernet:
        """
        Create Fernet instance with derived key.
        
        Args:
            encryption_key: Master encryption key
            
        Returns:
            Fernet instance for encryption/decryption
        """
        # Get encryption key from parameter, environment, or generate
        key = encryption_key or os.environ.get("ADMIN_ENCRYPTION_KEY")
        
        if not key:
            # Generate a deterministic key for development (NOT for production!)
            logger.warning(
                "No ADMIN_ENCRYPTION_KEY set. Using development key. "
                "Set ADMIN_ENCRYPTION_KEY environment variable in production!"
            )
            key = "superinsight_dev_key_change_in_production"
        
        # Derive a proper Fernet key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        
        return Fernet(derived_key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Encrypted string with prefix for identification
            
        Raises:
            ValueError: If plaintext is empty or None
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty or None value")
        
        # Don't double-encrypt
        if self.is_encrypted(plaintext):
            return plaintext
        
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            encrypted_str = base64.urlsafe_b64encode(encrypted_bytes).decode()
            return f"{self.ENCRYPTED_PREFIX}{encrypted_str}"
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Encryption failed: {e}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            ciphertext: The encrypted string (with or without prefix)
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            ValueError: If decryption fails or ciphertext is invalid
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty or None value")
        
        # Remove prefix if present
        if ciphertext.startswith(self.ENCRYPTED_PREFIX):
            ciphertext = ciphertext[len(self.ENCRYPTED_PREFIX):]
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except InvalidToken:
            logger.error("Decryption failed: Invalid token or wrong key")
            raise ValueError("Decryption failed: Invalid token or wrong key")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Decryption failed: {e}")
    
    def mask(self, value: str, visible_chars: int = 4) -> str:
        """
        Mask a sensitive value for display purposes.
        
        Shows only the first and last N characters, replacing the middle with asterisks.
        
        Args:
            value: The value to mask
            visible_chars: Number of characters to show at start and end (default: 4)
            
        Returns:
            Masked string (e.g., "my-s****-key" for "my-secret-key")
            
        Examples:
            mask("api-key-12345") -> "api-****2345"
            mask("short") -> "*****"
            mask("ab") -> "**"
        """
        if not value:
            return ""
        
        length = len(value)
        
        # For very short values, mask everything
        if length <= visible_chars * 2:
            return "*" * length
        
        # Show first and last visible_chars characters
        start = value[:visible_chars]
        end = value[-visible_chars:]
        middle_length = length - (visible_chars * 2)
        
        return f"{start}{'*' * middle_length}{end}"
    
    def is_encrypted(self, value: str) -> bool:
        """
        Check if a value is already encrypted.
        
        Args:
            value: The value to check
            
        Returns:
            True if the value appears to be encrypted, False otherwise
        """
        if not value:
            return False
        
        # Check for our encryption prefix
        if value.startswith(self.ENCRYPTED_PREFIX):
            return True
        
        # Additional heuristic: check if it looks like base64-encoded Fernet token
        try:
            if len(value) > 100:  # Fernet tokens are typically long
                decoded = base64.urlsafe_b64decode(value.encode())
                # Fernet tokens start with version byte
                return len(decoded) > 0 and decoded[0] == 128
        except Exception:
            pass
        
        return False
    
    def encrypt_if_needed(self, value: str) -> str:
        """
        Encrypt a value only if it's not already encrypted.
        
        Args:
            value: The value to potentially encrypt
            
        Returns:
            Encrypted value (or original if already encrypted)
        """
        if not value:
            return value
        
        if self.is_encrypted(value):
            return value
        
        return self.encrypt(value)
    
    def decrypt_if_needed(self, value: str) -> str:
        """
        Decrypt a value only if it appears to be encrypted.
        
        Args:
            value: The value to potentially decrypt
            
        Returns:
            Decrypted value (or original if not encrypted)
        """
        if not value:
            return value
        
        if not self.is_encrypted(value):
            return value
        
        return self.decrypt(value)
    
    def hash_value(self, value: str) -> str:
        """
        Create a one-way hash of a value (for comparison without storing plaintext).
        
        Args:
            value: The value to hash
            
        Returns:
            SHA-256 hash of the value
        """
        if not value:
            return ""
        
        return hashlib.sha256(value.encode()).hexdigest()
    
    def rotate_key(self, old_key: str, new_key: str, encrypted_value: str) -> str:
        """
        Re-encrypt a value with a new key.
        
        Args:
            old_key: The current encryption key
            new_key: The new encryption key
            encrypted_value: The value encrypted with the old key
            
        Returns:
            Value encrypted with the new key
        """
        # Create encryptor with old key
        old_encryptor = CredentialEncryptor(encryption_key=old_key, salt=self._salt)
        
        # Decrypt with old key
        plaintext = old_encryptor.decrypt(encrypted_value)
        
        # Create encryptor with new key
        new_encryptor = CredentialEncryptor(encryption_key=new_key, salt=self._salt)
        
        # Encrypt with new key
        return new_encryptor.encrypt(plaintext)


# Global encryptor instance
_default_encryptor: Optional[CredentialEncryptor] = None


def get_credential_encryptor() -> CredentialEncryptor:
    """
    Get the default credential encryptor instance.
    
    Returns:
        CredentialEncryptor instance
    """
    global _default_encryptor
    if _default_encryptor is None:
        _default_encryptor = CredentialEncryptor()
    return _default_encryptor


def encrypt_credential(value: str) -> str:
    """
    Convenience function to encrypt a credential.
    
    Args:
        value: The value to encrypt
        
    Returns:
        Encrypted value
    """
    return get_credential_encryptor().encrypt(value)


def decrypt_credential(value: str) -> str:
    """
    Convenience function to decrypt a credential.
    
    Args:
        value: The encrypted value
        
    Returns:
        Decrypted value
    """
    return get_credential_encryptor().decrypt(value)


def mask_credential(value: str, visible_chars: int = 4) -> str:
    """
    Convenience function to mask a credential.
    
    Args:
        value: The value to mask
        visible_chars: Number of visible characters at start and end
        
    Returns:
        Masked value
    """
    return get_credential_encryptor().mask(value, visible_chars)
