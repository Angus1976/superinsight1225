"""
Encryption service for data at rest and in transit.

Provides an abstract EncryptionProvider interface and a simple
key-based XOR + base64 implementation suitable for the framework layer.
Real encryption (e.g. Fernet/AES) can be swapped in via the interface.
"""

import base64
import os
from abc import ABC, abstractmethod
from typing import Optional


class EncryptionProvider(ABC):
    """Abstract interface for encryption providers."""

    @abstractmethod
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt raw bytes."""

    @abstractmethod
    def decrypt(self, data: bytes) -> bytes:
        """Decrypt raw bytes."""

    @abstractmethod
    def generate_key(self) -> bytes:
        """Generate a new encryption key."""


class SimpleEncryptionProvider(EncryptionProvider):
    """
    Lightweight XOR + base64 encryption provider.

    NOT suitable for production security — designed as a swappable
    placeholder that exercises the full encrypt/decrypt interface.
    """

    def __init__(self, key: Optional[bytes] = None):
        self._key = key or self.generate_key()

    @property
    def key(self) -> bytes:
        return self._key

    def generate_key(self) -> bytes:
        """Generate a random 32-byte key."""
        return os.urandom(32)

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data using repeating-key XOR then base64-encode."""
        if not data:
            return b""
        xored = self._xor_with_key(data)
        return base64.urlsafe_b64encode(xored)

    def decrypt(self, data: bytes) -> bytes:
        """Base64-decode then XOR-decrypt data."""
        if not data:
            return b""
        decoded = base64.urlsafe_b64decode(data)
        return self._xor_with_key(decoded)

    def encrypt_string(self, text: str) -> str:
        """Encrypt a string, returning a base64-encoded string."""
        return self.encrypt(text.encode("utf-8")).decode("ascii")

    def decrypt_string(self, encrypted: str) -> str:
        """Decrypt a base64-encoded string back to plaintext."""
        return self.decrypt(encrypted.encode("ascii")).decode("utf-8")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _xor_with_key(self, data: bytes) -> bytes:
        """XOR each byte of *data* with the corresponding key byte (repeating)."""
        key = self._key
        key_len = len(key)
        return bytes(b ^ key[i % key_len] for i, b in enumerate(data))
