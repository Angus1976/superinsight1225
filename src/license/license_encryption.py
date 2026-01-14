"""
License Encryption for SuperInsight Platform.

Provides encryption and signing utilities for license data.
"""

import base64
import hashlib
import hmac
import json
import os
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class LicenseEncryption:
    """
    License Encryption Service.
    
    Provides AES encryption and HMAC signing for license data.
    """
    
    def __init__(
        self,
        encryption_key: Optional[str] = None,
        signing_key: Optional[str] = None
    ):
        """
        Initialize License Encryption.
        
        Args:
            encryption_key: Key for AES encryption (will derive if not provided)
            signing_key: Key for HMAC signing
        """
        self.signing_key = signing_key or "default_signing_key"
        
        # Derive Fernet key from encryption key
        if encryption_key:
            self._fernet = self._derive_fernet_key(encryption_key)
        else:
            # Generate a new key for this session
            self._fernet = Fernet(Fernet.generate_key())
    
    def _derive_fernet_key(self, password: str) -> Fernet:
        """Derive a Fernet key from a password."""
        salt = b"superinsight_license_salt"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def encrypt_license(self, license_data: Dict[str, Any]) -> bytes:
        """
        Encrypt license data.
        
        Args:
            license_data: License data dictionary
            
        Returns:
            Encrypted bytes
        """
        json_data = json.dumps(license_data, default=str)
        return self._fernet.encrypt(json_data.encode())
    
    def decrypt_license(self, encrypted_data: bytes) -> Dict[str, Any]:
        """
        Decrypt license data.
        
        Args:
            encrypted_data: Encrypted bytes
            
        Returns:
            Decrypted license data dictionary
        """
        decrypted = self._fernet.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
    
    def sign_data(self, data: str) -> str:
        """
        Sign data with HMAC-SHA256.
        
        Args:
            data: Data string to sign
            
        Returns:
            Hex-encoded signature
        """
        signature = hmac.new(
            self.signing_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_signature(self, data: str, signature: str) -> bool:
        """
        Verify HMAC signature.
        
        Args:
            data: Original data string
            signature: Signature to verify
            
        Returns:
            True if signature is valid
        """
        expected = self.sign_data(data)
        return hmac.compare_digest(expected, signature)
    
    def generate_license_signature(self, license_data: Dict[str, Any]) -> str:
        """
        Generate signature for license data.
        
        Args:
            license_data: License data dictionary
            
        Returns:
            Hex-encoded signature
        """
        # Create deterministic string
        data_str = "|".join([
            str(license_data.get("license_key", "")),
            str(license_data.get("license_type", "")),
            str(license_data.get("validity_start", "")),
            str(license_data.get("validity_end", "")),
            str(license_data.get("max_concurrent_users", "")),
            str(license_data.get("hardware_id", "")),
        ])
        return self.sign_data(data_str)
    
    def export_encrypted_license(self, license_data: Dict[str, Any]) -> str:
        """
        Export license as encrypted base64 string.
        
        Args:
            license_data: License data dictionary
            
        Returns:
            Base64-encoded encrypted license
        """
        encrypted = self.encrypt_license(license_data)
        return base64.b64encode(encrypted).decode()
    
    def import_encrypted_license(self, encrypted_str: str) -> Dict[str, Any]:
        """
        Import license from encrypted base64 string.
        
        Args:
            encrypted_str: Base64-encoded encrypted license
            
        Returns:
            Decrypted license data dictionary
        """
        encrypted = base64.b64decode(encrypted_str.encode())
        return self.decrypt_license(encrypted)
