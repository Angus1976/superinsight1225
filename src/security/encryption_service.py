"""
Data Encryption Service for SuperInsight Platform.

Provides data encryption and decryption with key management and field-level encryption.
"""

import base64
import json
import logging
import os
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from src.security.key_store import KeyStore, EncryptionKey


@dataclass
class EncryptedData:
    """Encrypted data container."""
    ciphertext: bytes
    iv: bytes
    tag: bytes
    key_id: str
    algorithm: str = "AES-256-GCM"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ciphertext": base64.b64encode(self.ciphertext).decode('utf-8'),
            "iv": base64.b64encode(self.iv).decode('utf-8'),
            "tag": base64.b64encode(self.tag).decode('utf-8'),
            "key_id": self.key_id,
            "algorithm": self.algorithm
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptedData':
        return cls(
            ciphertext=base64.b64decode(data["ciphertext"]),
            iv=base64.b64decode(data["iv"]),
            tag=base64.b64decode(data["tag"]),
            key_id=data["key_id"],
            algorithm=data.get("algorithm", "AES-256-GCM")
        )


class DataEncryptionService:
    """
    Data encryption service with key management integration.
    
    Provides high-level encryption/decryption operations with automatic
    key management and field-level encryption for database storage.
    """
    
    def __init__(self, key_store: KeyStore):
        self.key_store = key_store
        self.logger = logging.getLogger(__name__)
        self._current_key: Optional[EncryptionKey] = None
    
    async def encrypt(
        self,
        data: Union[str, bytes],
        key_id: Optional[str] = None
    ) -> EncryptedData:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            data: Data to encrypt (string or bytes)
            key_id: Specific key ID to use (optional, uses current active key)
            
        Returns:
            EncryptedData container with encrypted data and metadata
        """
        # Convert string to bytes if necessary
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        # Get encryption key
        if key_id:
            key = await self.key_store.get_key(key_id)
            if not key:
                raise ValueError(f"Key not found: {key_id}")
        else:
            key = await self._get_current_key()
        
        # Generate random IV (12 bytes for GCM)
        iv = os.urandom(12)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key.key_bytes),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt data
        ciphertext = encryptor.update(data_bytes) + encryptor.finalize()
        
        # Get authentication tag
        tag = encryptor.tag
        
        encrypted_data = EncryptedData(
            ciphertext=ciphertext,
            iv=iv,
            tag=tag,
            key_id=key.id,
            algorithm="AES-256-GCM"
        )
        
        self.logger.debug(f"Encrypted data using key {key.id}")
        
        return encrypted_data
    
    async def decrypt(self, encrypted: EncryptedData) -> bytes:
        """
        Decrypt data using the specified key.
        
        Args:
            encrypted: EncryptedData container
            
        Returns:
            Decrypted data as bytes
        """
        # Get decryption key
        key = await self.key_store.get_key(encrypted.key_id)
        if not key:
            raise ValueError(f"Decryption key not found: {encrypted.key_id}")
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key.key_bytes),
            modes.GCM(encrypted.iv, encrypted.tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt data
        try:
            plaintext = decryptor.update(encrypted.ciphertext) + decryptor.finalize()
            self.logger.debug(f"Decrypted data using key {key.id}")
            return plaintext
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            raise ValueError("Decryption failed - data may be corrupted or key is incorrect")
    
    async def encrypt_field(
        self,
        value: str,
        field_name: Optional[str] = None
    ) -> str:
        """
        Encrypt a database field value.
        
        Args:
            value: Field value to encrypt
            field_name: Field name for logging (optional)
            
        Returns:
            Base64-encoded encrypted field value
        """
        if not value:
            return value
        
        try:
            encrypted = await self.encrypt(value)
            
            # Create field encryption envelope
            envelope = {
                "version": "1.0",
                "encrypted_data": encrypted.to_dict(),
                "field_name": field_name
            }
            
            # Encode as base64 for database storage
            envelope_json = json.dumps(envelope)
            encoded = base64.b64encode(envelope_json.encode('utf-8')).decode('utf-8')
            
            self.logger.debug(f"Encrypted field: {field_name}")
            
            return encoded
            
        except Exception as e:
            self.logger.error(f"Field encryption failed for {field_name}: {e}")
            raise
    
    async def decrypt_field(self, encrypted_value: str) -> str:
        """
        Decrypt a database field value.
        
        Args:
            encrypted_value: Base64-encoded encrypted field value
            
        Returns:
            Decrypted field value
        """
        if not encrypted_value:
            return encrypted_value
        
        try:
            # Decode from base64
            envelope_json = base64.b64decode(encrypted_value).decode('utf-8')
            envelope = json.loads(envelope_json)
            
            # Extract encrypted data
            encrypted_data = EncryptedData.from_dict(envelope["encrypted_data"])
            
            # Decrypt
            decrypted_bytes = await self.decrypt(encrypted_data)
            decrypted_value = decrypted_bytes.decode('utf-8')
            
            field_name = envelope.get("field_name", "unknown")
            self.logger.debug(f"Decrypted field: {field_name}")
            
            return decrypted_value
            
        except Exception as e:
            self.logger.error(f"Field decryption failed: {e}")
            raise ValueError("Field decryption failed - data may be corrupted")
    
    async def rotate_key(self) -> EncryptionKey:
        """
        Rotate the current encryption key.
        
        Returns:
            New active encryption key
        """
        # Mark current key for rotation
        if self._current_key:
            await self.key_store.mark_for_rotation(self._current_key.id)
        
        # Generate new key
        new_key = await self.key_store.generate_key()
        self._current_key = new_key
        
        self.logger.info(f"Key rotation completed - new key: {new_key.id}")
        
        return new_key
    
    async def re_encrypt_with_new_key(
        self,
        encrypted: EncryptedData,
        new_key_id: Optional[str] = None
    ) -> EncryptedData:
        """
        Re-encrypt data with a new key.
        
        Args:
            encrypted: Currently encrypted data
            new_key_id: New key ID (optional, uses current active key)
            
        Returns:
            EncryptedData with new key
        """
        # Decrypt with old key
        plaintext = await self.decrypt(encrypted)
        
        # Encrypt with new key
        new_encrypted = await self.encrypt(plaintext, new_key_id)
        
        self.logger.info(f"Re-encrypted data from key {encrypted.key_id} to {new_encrypted.key_id}")
        
        return new_encrypted
    
    async def bulk_re_encrypt(
        self,
        encrypted_items: list[EncryptedData],
        new_key_id: Optional[str] = None
    ) -> list[EncryptedData]:
        """
        Re-encrypt multiple items with a new key.
        
        Args:
            encrypted_items: List of encrypted data items
            new_key_id: New key ID (optional, uses current active key)
            
        Returns:
            List of re-encrypted data items
        """
        re_encrypted_items = []
        
        for item in encrypted_items:
            try:
                re_encrypted = await self.re_encrypt_with_new_key(item, new_key_id)
                re_encrypted_items.append(re_encrypted)
            except Exception as e:
                self.logger.error(f"Failed to re-encrypt item: {e}")
                # Continue with other items
                re_encrypted_items.append(item)  # Keep original if re-encryption fails
        
        self.logger.info(f"Bulk re-encryption completed: {len(re_encrypted_items)} items")
        
        return re_encrypted_items
    
    async def _get_current_key(self) -> EncryptionKey:
        """Get the current active encryption key."""
        if self._current_key and self._current_key.status == "active":
            return self._current_key
        
        # Get active key from key store
        key = await self.key_store.get_active_key()
        if not key:
            # Generate new key if none exists
            key = await self.key_store.generate_key()
        
        self._current_key = key
        return key
    
    def encrypt_string_simple(self, value: str, password: str) -> str:
        """
        Simple password-based encryption for configuration values.
        
        Args:
            value: String to encrypt
            password: Password for encryption
            
        Returns:
            Base64-encoded encrypted string
        """
        # Generate salt
        salt = os.urandom(16)
        
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        # Generate IV
        iv = os.urandom(12)
        
        # Encrypt
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(value.encode()) + encryptor.finalize()
        
        # Combine salt, iv, tag, and ciphertext
        encrypted_data = salt + iv + encryptor.tag + ciphertext
        
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_string_simple(self, encrypted_value: str, password: str) -> str:
        """
        Simple password-based decryption for configuration values.
        
        Args:
            encrypted_value: Base64-encoded encrypted string
            password: Password for decryption
            
        Returns:
            Decrypted string
        """
        # Decode from base64
        encrypted_data = base64.b64decode(encrypted_value)
        
        # Extract components
        salt = encrypted_data[:16]
        iv = encrypted_data[16:28]
        tag = encrypted_data[28:44]
        ciphertext = encrypted_data[44:]
        
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        # Decrypt
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext.decode('utf-8')
    
    async def get_encryption_statistics(self) -> Dict[str, Any]:
        """
        Get encryption service statistics.
        
        Returns:
            Dictionary with encryption statistics
        """
        key_stats = await self.key_store.get_key_statistics()
        
        return {
            "current_key_id": self._current_key.id if self._current_key else None,
            "key_store_stats": key_stats,
            "supported_algorithms": ["AES-256-GCM"],
            "field_encryption_version": "1.0"
        }