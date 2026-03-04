"""
Encryption service for API key protection.

Provides AES-256-GCM encryption and decryption for sensitive data like API keys.
"""

import os
import base64
import logging
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data using AES-256-GCM.
    
    The encryption key must be provided via the LLM_ENCRYPTION_KEY environment
    variable as a base64-encoded 32-byte key.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the encryption service.
        
        Args:
            encryption_key: Base64-encoded 32-byte key. If None, reads from
                          LLM_ENCRYPTION_KEY environment variable.
        
        Raises:
            ValueError: If encryption key is not set or invalid.
        """
        key_b64 = encryption_key or os.getenv("LLM_ENCRYPTION_KEY")
        if not key_b64:
            raise ValueError(
                "LLM_ENCRYPTION_KEY environment variable not set. "
                "Generate a key with: python -c 'import os, base64; "
                "print(base64.b64encode(os.urandom(32)).decode())'"
            )
        
        try:
            self._key = base64.b64decode(key_b64)
            if len(self._key) != 32:
                raise ValueError(f"Encryption key must be 32 bytes, got {len(self._key)}")
            self._aesgcm = AESGCM(self._key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}") from e
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: The string to encrypt.
        
        Returns:
            Base64-encoded encrypted data (nonce + ciphertext).
        
        Raises:
            EncryptionError: If encryption fails.
        """
        if not plaintext:
            raise ValueError("plaintext cannot be empty")
        
        try:
            # Generate random 12-byte nonce
            nonce = os.urandom(12)
            
            # Encrypt the plaintext
            ciphertext = self._aesgcm.encrypt(
                nonce,
                plaintext.encode('utf-8'),
                None  # No additional authenticated data
            )
            
            # Combine nonce + ciphertext and encode as base64
            encrypted_data = nonce + ciphertext
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}") from e
    
    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            encrypted: Base64-encoded encrypted data (nonce + ciphertext).
        
        Returns:
            The decrypted plaintext string.
        
        Raises:
            EncryptionError: If decryption fails.
        """
        if not encrypted:
            raise ValueError("encrypted cannot be empty")
        
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted)
            
            # Extract nonce (first 12 bytes) and ciphertext (rest)
            if len(encrypted_data) < 12:
                raise ValueError("Encrypted data too short")
            
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            
            # Decrypt the ciphertext
            plaintext_bytes = self._aesgcm.decrypt(
                nonce,
                ciphertext,
                None  # No additional authenticated data
            )
            
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt data: {e}") from e


# Global singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get or create the global EncryptionService instance.
    
    Returns:
        EncryptionService instance.
    """
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    
    return _encryption_service
