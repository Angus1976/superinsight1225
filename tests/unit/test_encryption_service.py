"""
Unit tests for Encryption Service.
"""

import pytest
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from src.security.encryption_service import (
    DataEncryptionService, EncryptedData
)
from src.security.key_store import KeyStore, EncryptionKey


@pytest.fixture
def mock_key_store():
    """Create mock key store."""
    key_store = AsyncMock(spec=KeyStore)
    return key_store


@pytest.fixture
def sample_encryption_key():
    """Create sample encryption key."""
    return EncryptionKey(
        id="key123",
        key_bytes=b"0123456789abcdef0123456789abcdef",  # 32 bytes for AES-256
        algorithm="AES-256",
        status="active",
        created_at=datetime.utcnow()
    )


@pytest.fixture
def encryption_service(mock_key_store):
    """Create encryption service instance."""
    return DataEncryptionService(key_store=mock_key_store)


class TestEncryptedData:
    """Tests for EncryptedData dataclass."""

    def test_encrypted_data_creation(self):
        """Test creating encrypted data."""
        data = EncryptedData(
            ciphertext=b"encrypted_content",
            iv=b"initialization_v",
            tag=b"auth_tag_here123",
            key_id="key123",
            algorithm="AES-256-GCM"
        )
        
        assert data.ciphertext == b"encrypted_content"
        assert data.iv == b"initialization_v"
        assert data.tag == b"auth_tag_here123"
        assert data.key_id == "key123"
        assert data.algorithm == "AES-256-GCM"

    def test_encrypted_data_to_dict(self):
        """Test encrypted data dictionary conversion."""
        data = EncryptedData(
            ciphertext=b"test_cipher",
            iv=b"test_iv_1234",
            tag=b"test_tag_567890",
            key_id="key456",
            algorithm="AES-256-GCM"
        )
        
        result = data.to_dict()
        
        assert result["key_id"] == "key456"
        assert result["algorithm"] == "AES-256-GCM"
        assert "ciphertext" in result
        assert "iv" in result
        assert "tag" in result
        
        # Verify base64 encoding
        assert base64.b64decode(result["ciphertext"]) == b"test_cipher"
        assert base64.b64decode(result["iv"]) == b"test_iv_1234"
        assert base64.b64decode(result["tag"]) == b"test_tag_567890"

    def test_encrypted_data_from_dict(self):
        """Test creating encrypted data from dictionary."""
        data_dict = {
            "ciphertext": base64.b64encode(b"cipher_data").decode('utf-8'),
            "iv": base64.b64encode(b"iv_data_1234").decode('utf-8'),
            "tag": base64.b64encode(b"tag_data_567").decode('utf-8'),
            "key_id": "key789",
            "algorithm": "AES-256-GCM"
        }
        
        data = EncryptedData.from_dict(data_dict)
        
        assert data.ciphertext == b"cipher_data"
        assert data.iv == b"iv_data_1234"
        assert data.tag == b"tag_data_567"
        assert data.key_id == "key789"
        assert data.algorithm == "AES-256-GCM"

    def test_encrypted_data_from_dict_default_algorithm(self):
        """Test creating encrypted data from dictionary with default algorithm."""
        data_dict = {
            "ciphertext": base64.b64encode(b"cipher").decode('utf-8'),
            "iv": base64.b64encode(b"iv_123456789").decode('utf-8'),
            "tag": base64.b64encode(b"tag_12345678").decode('utf-8'),
            "key_id": "key999"
        }
        
        data = EncryptedData.from_dict(data_dict)
        
        assert data.algorithm == "AES-256-GCM"  # Default value


class TestDataEncryptionService:
    """Tests for DataEncryptionService class."""

    def test_encryption_service_creation(self, encryption_service):
        """Test creating encryption service instance."""
        assert encryption_service is not None
        assert encryption_service.key_store is not None
        assert encryption_service._current_key is None

    @pytest.mark.asyncio
    async def test_encrypt_string_data(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test encrypting string data."""
        mock_key_store.get_key.return_value = sample_encryption_key
        
        test_data = "Hello, World!"
        
        encrypted = await encryption_service.encrypt(test_data, key_id="key123")
        
        assert isinstance(encrypted, EncryptedData)
        assert encrypted.key_id == "key123"
        assert encrypted.algorithm == "AES-256-GCM"
        assert len(encrypted.iv) == 12  # GCM IV length
        assert len(encrypted.tag) == 16  # GCM tag length
        assert encrypted.ciphertext != test_data.encode()

    @pytest.mark.asyncio
    async def test_encrypt_bytes_data(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test encrypting bytes data."""
        mock_key_store.get_key.return_value = sample_encryption_key
        
        test_data = b"Binary data content"
        
        encrypted = await encryption_service.encrypt(test_data, key_id="key123")
        
        assert isinstance(encrypted, EncryptedData)
        assert encrypted.key_id == "key123"
        assert encrypted.ciphertext != test_data

    @pytest.mark.asyncio
    async def test_encrypt_with_current_key(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test encrypting with current key when no key_id specified."""
        with patch.object(encryption_service, '_get_current_key', return_value=sample_encryption_key):
            test_data = "Test with current key"
            
            encrypted = await encryption_service.encrypt(test_data)
            
            assert encrypted.key_id == "key123"

    @pytest.mark.asyncio
    async def test_encrypt_key_not_found(self, encryption_service, mock_key_store):
        """Test encryption with non-existent key."""
        mock_key_store.get_key.return_value = None
        
        with pytest.raises(ValueError, match="Key not found"):
            await encryption_service.encrypt("test data", key_id="nonexistent")

    @pytest.mark.asyncio
    async def test_decrypt_success(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test successful decryption."""
        # First encrypt some data
        mock_key_store.get_key.return_value = sample_encryption_key
        test_data = "Secret message"
        
        encrypted = await encryption_service.encrypt(test_data, key_id="key123")
        
        # Then decrypt it
        decrypted = await encryption_service.decrypt(encrypted)
        
        assert decrypted.decode('utf-8') == test_data

    @pytest.mark.asyncio
    async def test_decrypt_key_not_found(self, encryption_service, mock_key_store):
        """Test decryption with non-existent key."""
        mock_key_store.get_key.return_value = None
        
        encrypted_data = EncryptedData(
            ciphertext=b"fake_cipher",
            iv=b"fake_iv_1234",
            tag=b"fake_tag_567890",
            key_id="nonexistent"
        )
        
        with pytest.raises(ValueError, match="Decryption key not found"):
            await encryption_service.decrypt(encrypted_data)

    @pytest.mark.asyncio
    async def test_decrypt_corrupted_data(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test decryption with corrupted data."""
        mock_key_store.get_key.return_value = sample_encryption_key
        
        # Create corrupted encrypted data with proper tag length (16 bytes for GCM)
        corrupted_data = EncryptedData(
            ciphertext=b"corrupted_cipher_data",
            iv=b"bad_iv_12345",
            tag=b"bad_tag_67890123",  # 16 bytes
            key_id="key123"
        )
        
        with pytest.raises(ValueError, match="Decryption failed"):
            await encryption_service.decrypt(corrupted_data)

    @pytest.mark.asyncio
    async def test_encrypt_field_success(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test field encryption."""
        with patch.object(encryption_service, '_get_current_key', return_value=sample_encryption_key):
            field_value = "sensitive_data"
            
            encrypted_field = await encryption_service.encrypt_field(field_value, "user_email")
            
            assert isinstance(encrypted_field, str)
            assert encrypted_field != field_value
            
            # Verify it's valid base64
            decoded = base64.b64decode(encrypted_field)
            envelope = json.loads(decoded.decode('utf-8'))
            
            assert envelope["version"] == "1.0"
            assert envelope["field_name"] == "user_email"
            assert "encrypted_data" in envelope

    @pytest.mark.asyncio
    async def test_encrypt_field_empty_value(self, encryption_service):
        """Test field encryption with empty value."""
        result = await encryption_service.encrypt_field("")
        assert result == ""
        
        result = await encryption_service.encrypt_field(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_decrypt_field_success(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test field decryption."""
        with patch.object(encryption_service, '_get_current_key', return_value=sample_encryption_key):
            original_value = "confidential_info"
            
            # Encrypt field
            encrypted_field = await encryption_service.encrypt_field(original_value, "sensitive_field")
            
            # Decrypt field
            mock_key_store.get_key.return_value = sample_encryption_key
            decrypted_value = await encryption_service.decrypt_field(encrypted_field)
            
            assert decrypted_value == original_value

    @pytest.mark.asyncio
    async def test_decrypt_field_empty_value(self, encryption_service):
        """Test field decryption with empty value."""
        result = await encryption_service.decrypt_field("")
        assert result == ""
        
        result = await encryption_service.decrypt_field(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_decrypt_field_corrupted(self, encryption_service):
        """Test field decryption with corrupted data."""
        corrupted_field = "invalid_base64_data"
        
        with pytest.raises(ValueError, match="Field decryption failed"):
            await encryption_service.decrypt_field(corrupted_field)

    @pytest.mark.asyncio
    async def test_rotate_key(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test key rotation."""
        # Set current key
        encryption_service._current_key = sample_encryption_key
        
        # Mock new key generation
        new_key = EncryptionKey(
            id="new_key456",
            key_bytes=b"new_key_bytes_32_characters_long",
            algorithm="AES-256",
            status="active",
            created_at=datetime.utcnow()
        )
        mock_key_store.generate_key.return_value = new_key
        
        rotated_key = await encryption_service.rotate_key()
        
        assert rotated_key.id == "new_key456"
        assert encryption_service._current_key == new_key
        mock_key_store.mark_for_rotation.assert_called_once_with("key123")

    @pytest.mark.asyncio
    async def test_rotate_key_no_current_key(self, encryption_service, mock_key_store):
        """Test key rotation when no current key exists."""
        new_key = EncryptionKey(
            id="first_key789",
            key_bytes=b"first_key_bytes_32_chars_long123",
            algorithm="AES-256",
            status="active",
            created_at=datetime.utcnow()
        )
        mock_key_store.generate_key.return_value = new_key
        
        rotated_key = await encryption_service.rotate_key()
        
        assert rotated_key.id == "first_key789"
        mock_key_store.mark_for_rotation.assert_not_called()

    @pytest.mark.asyncio
    async def test_re_encrypt_with_new_key(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test re-encrypting data with new key."""
        # Create original encrypted data
        original_data = "data to re-encrypt"
        mock_key_store.get_key.return_value = sample_encryption_key
        
        encrypted = await encryption_service.encrypt(original_data, key_id="key123")
        
        # Create new key
        new_key = EncryptionKey(
            id="new_key999",
            key_bytes=b"new_encryption_key_32_bytes_long",
            algorithm="AES-256",
            status="active",
            created_at=datetime.utcnow()
        )
        
        # Mock key retrieval for re-encryption
        def mock_get_key(key_id):
            if key_id == "key123":
                return sample_encryption_key
            elif key_id == "new_key999":
                return new_key
            return None
        
        mock_key_store.get_key.side_effect = mock_get_key
        
        re_encrypted = await encryption_service.re_encrypt_with_new_key(encrypted, "new_key999")
        
        assert re_encrypted.key_id == "new_key999"
        assert re_encrypted.ciphertext != encrypted.ciphertext

    @pytest.mark.asyncio
    async def test_bulk_re_encrypt(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test bulk re-encryption."""
        # Create multiple encrypted items
        items = []
        for i in range(3):
            mock_key_store.get_key.return_value = sample_encryption_key
            encrypted = await encryption_service.encrypt(f"data_{i}", key_id="key123")
            items.append(encrypted)
        
        # Mock re-encryption
        with patch.object(encryption_service, 're_encrypt_with_new_key') as mock_re_encrypt:
            mock_re_encrypt.side_effect = lambda item, key_id: EncryptedData(
                ciphertext=b"re_encrypted",
                iv=b"new_iv_123456",
                tag=b"new_tag_78901234",
                key_id="new_key"
            )
            
            re_encrypted_items = await encryption_service.bulk_re_encrypt(items, "new_key")
        
        assert len(re_encrypted_items) == 3
        assert all(item.key_id == "new_key" for item in re_encrypted_items)

    @pytest.mark.asyncio
    async def test_bulk_re_encrypt_with_failures(self, encryption_service, mock_key_store):
        """Test bulk re-encryption with some failures."""
        items = [
            EncryptedData(b"cipher1", b"iv1_12345678", b"tag1_1234567890", "key1"),
            EncryptedData(b"cipher2", b"iv2_12345678", b"tag2_1234567890", "key2"),
        ]
        
        # Mock re-encryption with one failure
        def mock_re_encrypt(item, key_id):
            if item.key_id == "key1":
                raise Exception("Re-encryption failed")
            return EncryptedData(b"new_cipher", b"new_iv_123456", b"new_tag_789012", "new_key")
        
        with patch.object(encryption_service, 're_encrypt_with_new_key', side_effect=mock_re_encrypt):
            re_encrypted_items = await encryption_service.bulk_re_encrypt(items, "new_key")
        
        assert len(re_encrypted_items) == 2
        assert re_encrypted_items[0].key_id == "key1"  # Original kept due to failure
        assert re_encrypted_items[1].key_id == "new_key"  # Successfully re-encrypted

    @pytest.mark.asyncio
    async def test_get_current_key_cached(self, encryption_service, sample_encryption_key):
        """Test getting current key when cached."""
        encryption_service._current_key = sample_encryption_key
        
        key = await encryption_service._get_current_key()
        
        assert key == sample_encryption_key

    @pytest.mark.asyncio
    async def test_get_current_key_from_store(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test getting current key from key store."""
        mock_key_store.get_active_key.return_value = sample_encryption_key
        
        key = await encryption_service._get_current_key()
        
        assert key == sample_encryption_key
        assert encryption_service._current_key == sample_encryption_key

    @pytest.mark.asyncio
    async def test_get_current_key_generate_new(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test generating new key when none exists."""
        mock_key_store.get_active_key.return_value = None
        mock_key_store.generate_key.return_value = sample_encryption_key
        
        key = await encryption_service._get_current_key()
        
        assert key == sample_encryption_key
        mock_key_store.generate_key.assert_called_once()

    def test_encrypt_string_simple(self, encryption_service):
        """Test simple password-based string encryption."""
        value = "secret configuration"
        password = "strong_password_123"
        
        encrypted = encryption_service.encrypt_string_simple(value, password)
        
        assert isinstance(encrypted, str)
        assert encrypted != value
        
        # Verify it's valid base64
        base64.b64decode(encrypted)

    def test_decrypt_string_simple(self, encryption_service):
        """Test simple password-based string decryption."""
        value = "confidential setting"
        password = "secure_password_456"
        
        encrypted = encryption_service.encrypt_string_simple(value, password)
        decrypted = encryption_service.decrypt_string_simple(encrypted, password)
        
        assert decrypted == value

    def test_decrypt_string_simple_wrong_password(self, encryption_service):
        """Test simple decryption with wrong password."""
        value = "secret value"
        password = "correct_password"
        wrong_password = "wrong_password"
        
        encrypted = encryption_service.encrypt_string_simple(value, password)
        
        with pytest.raises(Exception):  # Should fail with wrong password
            encryption_service.decrypt_string_simple(encrypted, wrong_password)

    @pytest.mark.asyncio
    async def test_get_encryption_statistics(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test getting encryption statistics."""
        encryption_service._current_key = sample_encryption_key
        mock_key_store.get_key_statistics.return_value = {
            "total_keys": 5,
            "active_keys": 1,
            "rotating_keys": 1,
            "retired_keys": 3
        }
        
        stats = await encryption_service.get_encryption_statistics()
        
        assert stats["current_key_id"] == "key123"
        assert stats["key_store_stats"]["total_keys"] == 5
        assert "AES-256-GCM" in stats["supported_algorithms"]
        assert stats["field_encryption_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_get_encryption_statistics_no_current_key(self, encryption_service, mock_key_store):
        """Test getting encryption statistics with no current key."""
        mock_key_store.get_key_statistics.return_value = {"total_keys": 0}
        
        stats = await encryption_service.get_encryption_statistics()
        
        assert stats["current_key_id"] is None


class TestEncryptionServiceIntegration:
    """Integration tests for encryption service."""

    @pytest.mark.asyncio
    async def test_full_encryption_workflow(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test complete encryption/decryption workflow."""
        # Setup
        mock_key_store.get_key.return_value = sample_encryption_key
        with patch.object(encryption_service, '_get_current_key', return_value=sample_encryption_key):
            
            # Test data
            original_data = "This is sensitive information that needs encryption"
            
            # Encrypt
            encrypted = await encryption_service.encrypt(original_data)
            assert encrypted.key_id == "key123"
            
            # Decrypt
            decrypted = await encryption_service.decrypt(encrypted)
            assert decrypted.decode('utf-8') == original_data

    @pytest.mark.asyncio
    async def test_field_encryption_workflow(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test complete field encryption/decryption workflow."""
        # Setup
        with patch.object(encryption_service, '_get_current_key', return_value=sample_encryption_key):
            mock_key_store.get_key.return_value = sample_encryption_key
            
            # Test field data
            field_value = "user@example.com"
            field_name = "email"
            
            # Encrypt field
            encrypted_field = await encryption_service.encrypt_field(field_value, field_name)
            assert encrypted_field != field_value
            
            # Decrypt field
            decrypted_field = await encryption_service.decrypt_field(encrypted_field)
            assert decrypted_field == field_value

    @pytest.mark.asyncio
    async def test_key_rotation_workflow(self, encryption_service, mock_key_store, sample_encryption_key):
        """Test key rotation workflow."""
        # Setup initial key
        encryption_service._current_key = sample_encryption_key
        
        # Encrypt data with old key
        mock_key_store.get_key.return_value = sample_encryption_key
        original_data = "data before rotation"
        encrypted_old = await encryption_service.encrypt(original_data)
        
        # Rotate key
        new_key = EncryptionKey(
            id="rotated_key",
            key_bytes=b"rotated_key_bytes_32_chars_long1",
            algorithm="AES-256",
            status="active",
            created_at=datetime.utcnow()
        )
        mock_key_store.generate_key.return_value = new_key
        
        rotated_key = await encryption_service.rotate_key()
        assert rotated_key.id == "rotated_key"
        
        # Encrypt new data with new key
        new_data = "data after rotation"
        encrypted_new = await encryption_service.encrypt(new_data)
        assert encrypted_new.key_id == "rotated_key"
        
        # Verify both can be decrypted with appropriate keys
        def mock_get_key(key_id):
            if key_id == "key123":
                return sample_encryption_key
            elif key_id == "rotated_key":
                return new_key
            return None
        
        mock_key_store.get_key.side_effect = mock_get_key
        
        decrypted_old = await encryption_service.decrypt(encrypted_old)
        decrypted_new = await encryption_service.decrypt(encrypted_new)
        
        assert decrypted_old.decode('utf-8') == original_data
        assert decrypted_new.decode('utf-8') == new_data