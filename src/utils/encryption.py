"""
Encryption utilities for sensitive data.

Provides functions for encrypting and decrypting sensitive data
such as passwords, API keys, and other credentials.
"""

import base64
import hashlib
import logging
from typing import Any, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Default encryption key (in production, this should come from environment/config)
DEFAULT_ENCRYPTION_KEY = "superinsight-default-encryption-key-2024"


def _get_encryption_key(password: str = DEFAULT_ENCRYPTION_KEY) -> bytes:
    """Generate encryption key from password."""
    # Use a fixed salt for consistency (in production, use random salt per record)
    salt = b"superinsight_salt_2024"
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def encrypt_sensitive_data(data: Union[str, bytes]) -> str:
    """
    Encrypt sensitive data.
    
    Args:
        data: Data to encrypt (string or bytes)
        
    Returns:
        Base64 encoded encrypted data
    """
    try:
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        key = _get_encryption_key()
        fernet = Fernet(key)
        
        encrypted_data = fernet.encrypt(data)
        return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        
    except Exception as e:
        logger.error(f"Error encrypting data: {e}")
        # In case of encryption failure, return the original data with a prefix
        # This ensures the system doesn't break, but logs the issue
        return f"ENCRYPT_FAILED:{data.decode('utf-8') if isinstance(data, bytes) else data}"


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data.
    
    Args:
        encrypted_data: Base64 encoded encrypted data
        
    Returns:
        Decrypted data as string
    """
    try:
        # Handle encryption failure case
        if encrypted_data.startswith("ENCRYPT_FAILED:"):
            return encrypted_data[15:]  # Remove prefix
        
        key = _get_encryption_key()
        fernet = Fernet(key)
        
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
        decrypted_data = fernet.decrypt(encrypted_bytes)
        
        return decrypted_data.decode('utf-8')
        
    except Exception as e:
        logger.error(f"Error decrypting data: {e}")
        # Return the encrypted data as-is if decryption fails
        return encrypted_data


def hash_data(data: str, algorithm: str = "sha256") -> str:
    """
    Hash data using specified algorithm.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm (sha256, md5, sha1)
        
    Returns:
        Hexadecimal hash string
    """
    try:
        if algorithm == "sha256":
            hasher = hashlib.sha256()
        elif algorithm == "md5":
            hasher = hashlib.md5()
        elif algorithm == "sha1":
            hasher = hashlib.sha1()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        hasher.update(data.encode('utf-8'))
        return hasher.hexdigest()
        
    except Exception as e:
        logger.error(f"Error hashing data: {e}")
        return ""


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Mask sensitive data for display purposes.
    
    Args:
        data: Data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to keep visible at the end
        
    Returns:
        Masked data string
    """
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ""
    
    masked_length = len(data) - visible_chars
    return mask_char * masked_length + data[-visible_chars:]


def is_encrypted_data(data: str) -> bool:
    """
    Check if data appears to be encrypted.
    
    Args:
        data: Data to check
        
    Returns:
        True if data appears to be encrypted
    """
    if not data:
        return False
    
    # Check for encryption failure prefix
    if data.startswith("ENCRYPT_FAILED:"):
        return False
    
    # Check if it looks like base64 encoded data
    try:
        # Base64 encoded data should be decodable
        decoded = base64.urlsafe_b64decode(data.encode('utf-8'))
        # Encrypted data typically has a certain length and randomness
        return len(decoded) > 16 and len(data) > 20
    except Exception:
        return False