"""
Property-Based Tests for Credential Encryptor.

Tests the credential encryption, decryption, and masking functionality
using Hypothesis for property-based testing.

**Feature: admin-configuration, Property 1: 敏感信息脱敏**
**Validates: Requirements 2.6, 3.6**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.admin.credential_encryptor import (
    CredentialEncryptor,
    encrypt_credential,
    decrypt_credential,
    mask_credential,
    get_credential_encryptor,
)


class TestCredentialEncryptorProperties:
    """Property-based tests for CredentialEncryptor."""
    
    @pytest.fixture
    def encryptor(self):
        """Create a test encryptor with a fixed key."""
        return CredentialEncryptor(encryption_key="test_key_for_property_tests")
    
    # ========== Property 1: Round-trip encryption/decryption ==========
    
    @given(st.text(min_size=1, max_size=1000))
    @settings(max_examples=100)
    def test_encrypt_decrypt_roundtrip(self, plaintext: str):
        """
        **Feature: admin-configuration, Property 1: 敏感信息脱敏**
        **Validates: Requirements 2.6, 3.6**
        
        For any non-empty plaintext string, encrypting then decrypting
        should return the original plaintext.
        """
        # Skip strings with null bytes (not valid for encryption)
        assume('\x00' not in plaintext)
        
        encryptor = CredentialEncryptor(encryption_key="test_roundtrip_key")
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext, (
            f"Round-trip failed: original={plaintext!r}, "
            f"encrypted={encrypted!r}, decrypted={decrypted!r}"
        )
    
    # ========== Property 2: Encrypted values are different from plaintext ==========
    
    @given(st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_encrypted_differs_from_plaintext(self, plaintext: str):
        """
        For any plaintext, the encrypted value should be different
        from the original plaintext.
        """
        assume('\x00' not in plaintext)
        
        encryptor = CredentialEncryptor(encryption_key="test_differs_key")
        
        encrypted = encryptor.encrypt(plaintext)
        
        # Remove prefix for comparison
        encrypted_content = encrypted.replace("enc:", "")
        
        assert encrypted_content != plaintext, (
            f"Encrypted value should differ from plaintext: {plaintext!r}"
        )
    
    # ========== Property 3: Masking always contains asterisks ==========
    
    @given(st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_mask_contains_asterisks(self, value: str):
        """
        **Feature: admin-configuration, Property 1: 敏感信息脱敏**
        **Validates: Requirements 2.6, 3.6**
        
        For any non-empty value, the masked result should contain asterisks.
        """
        encryptor = CredentialEncryptor(encryption_key="test_mask_key")
        
        masked = encryptor.mask(value)
        
        assert '*' in masked, (
            f"Masked value should contain asterisks: value={value!r}, masked={masked!r}"
        )
    
    # ========== Property 4: Masking preserves length ==========
    
    @given(st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_mask_preserves_length(self, value: str):
        """
        **Feature: admin-configuration, Property 1: 敏感信息脱敏**
        **Validates: Requirements 2.6, 3.6**
        
        For any value, the masked result should have the same length
        as the original value.
        """
        encryptor = CredentialEncryptor(encryption_key="test_length_key")
        
        masked = encryptor.mask(value)
        
        assert len(masked) == len(value), (
            f"Masked length should equal original: "
            f"original_len={len(value)}, masked_len={len(masked)}"
        )
    
    # ========== Property 5: Masking shows correct visible characters ==========
    
    @given(
        st.text(min_size=9, max_size=500),  # Need at least 9 chars for 4+4 visible
        st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_mask_visible_chars(self, value: str, visible_chars: int):
        """
        **Feature: admin-configuration, Property 1: 敏感信息脱敏**
        **Validates: Requirements 2.6, 3.6**
        
        For values longer than 2*visible_chars, the masked result should
        show the first and last visible_chars characters.
        """
        assume(len(value) > visible_chars * 2)
        
        encryptor = CredentialEncryptor(encryption_key="test_visible_key")
        
        masked = encryptor.mask(value, visible_chars=visible_chars)
        
        # Check first visible_chars match
        assert masked[:visible_chars] == value[:visible_chars], (
            f"First {visible_chars} chars should match: "
            f"expected={value[:visible_chars]!r}, got={masked[:visible_chars]!r}"
        )
        
        # Check last visible_chars match
        assert masked[-visible_chars:] == value[-visible_chars:], (
            f"Last {visible_chars} chars should match: "
            f"expected={value[-visible_chars:]!r}, got={masked[-visible_chars:]!r}"
        )
    
    # ========== Property 6: Short values are fully masked ==========
    
    @given(st.text(min_size=1, max_size=8))
    @settings(max_examples=100)
    def test_short_values_fully_masked(self, value: str):
        """
        **Feature: admin-configuration, Property 1: 敏感信息脱敏**
        **Validates: Requirements 2.6, 3.6**
        
        For values with length <= 2*visible_chars (default 8),
        the entire value should be masked with asterisks.
        """
        encryptor = CredentialEncryptor(encryption_key="test_short_key")
        
        masked = encryptor.mask(value, visible_chars=4)
        
        if len(value) <= 8:
            assert masked == '*' * len(value), (
                f"Short value should be fully masked: "
                f"value={value!r}, masked={masked!r}"
            )
    
    # ========== Property 7: is_encrypted detects encrypted values ==========
    
    @given(st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_is_encrypted_detects_encrypted(self, plaintext: str):
        """
        For any plaintext, after encryption, is_encrypted should return True.
        """
        assume('\x00' not in plaintext)
        
        encryptor = CredentialEncryptor(encryption_key="test_detect_key")
        
        encrypted = encryptor.encrypt(plaintext)
        
        assert encryptor.is_encrypted(encrypted), (
            f"is_encrypted should return True for encrypted value: {encrypted!r}"
        )
    
    # ========== Property 8: is_encrypted returns False for plaintext ==========
    
    @given(st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_is_encrypted_false_for_plaintext(self, plaintext: str):
        """
        For any plaintext that doesn't start with 'enc:', 
        is_encrypted should return False.
        """
        assume(not plaintext.startswith("enc:"))
        
        encryptor = CredentialEncryptor(encryption_key="test_plaintext_key")
        
        assert not encryptor.is_encrypted(plaintext), (
            f"is_encrypted should return False for plaintext: {plaintext!r}"
        )
    
    # ========== Property 9: Double encryption is idempotent ==========
    
    @given(st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_encrypt_idempotent(self, plaintext: str):
        """
        Encrypting an already encrypted value should return the same value
        (no double encryption).
        """
        assume('\x00' not in plaintext)
        
        encryptor = CredentialEncryptor(encryption_key="test_idempotent_key")
        
        encrypted_once = encryptor.encrypt(plaintext)
        encrypted_twice = encryptor.encrypt(encrypted_once)
        
        assert encrypted_once == encrypted_twice, (
            f"Double encryption should be idempotent: "
            f"once={encrypted_once!r}, twice={encrypted_twice!r}"
        )
    
    # ========== Property 10: encrypt_if_needed is idempotent ==========
    
    @given(st.text(min_size=1, max_size=500))
    @settings(max_examples=100)
    def test_encrypt_if_needed_idempotent(self, plaintext: str):
        """
        encrypt_if_needed should be idempotent - calling it multiple times
        should produce the same result.
        """
        assume('\x00' not in plaintext)
        
        encryptor = CredentialEncryptor(encryption_key="test_if_needed_key")
        
        result1 = encryptor.encrypt_if_needed(plaintext)
        result2 = encryptor.encrypt_if_needed(result1)
        result3 = encryptor.encrypt_if_needed(result2)
        
        assert result1 == result2 == result3, (
            f"encrypt_if_needed should be idempotent: "
            f"r1={result1!r}, r2={result2!r}, r3={result3!r}"
        )


class TestCredentialEncryptorUnit:
    """Unit tests for CredentialEncryptor edge cases."""
    
    def test_encrypt_empty_raises_error(self):
        """Encrypting empty string should raise ValueError."""
        encryptor = CredentialEncryptor(encryption_key="test_key")
        
        with pytest.raises(ValueError, match="Cannot encrypt empty"):
            encryptor.encrypt("")
    
    def test_encrypt_none_raises_error(self):
        """Encrypting None should raise ValueError."""
        encryptor = CredentialEncryptor(encryption_key="test_key")
        
        with pytest.raises(ValueError, match="Cannot encrypt empty"):
            encryptor.encrypt(None)
    
    def test_decrypt_empty_raises_error(self):
        """Decrypting empty string should raise ValueError."""
        encryptor = CredentialEncryptor(encryption_key="test_key")
        
        with pytest.raises(ValueError, match="Cannot decrypt empty"):
            encryptor.decrypt("")
    
    def test_decrypt_invalid_raises_error(self):
        """Decrypting invalid ciphertext should raise ValueError."""
        encryptor = CredentialEncryptor(encryption_key="test_key")
        
        with pytest.raises(ValueError):
            encryptor.decrypt("invalid_ciphertext")
    
    def test_mask_empty_returns_empty(self):
        """Masking empty string should return empty string."""
        encryptor = CredentialEncryptor(encryption_key="test_key")
        
        assert encryptor.mask("") == ""
    
    def test_mask_none_returns_empty(self):
        """Masking None should return empty string."""
        encryptor = CredentialEncryptor(encryption_key="test_key")
        
        assert encryptor.mask(None) == ""
    
    def test_different_keys_produce_different_ciphertext(self):
        """Different encryption keys should produce different ciphertext."""
        encryptor1 = CredentialEncryptor(encryption_key="key1")
        encryptor2 = CredentialEncryptor(encryption_key="key2")
        
        plaintext = "test_secret"
        
        encrypted1 = encryptor1.encrypt(plaintext)
        encrypted2 = encryptor2.encrypt(plaintext)
        
        assert encrypted1 != encrypted2
    
    def test_wrong_key_cannot_decrypt(self):
        """Decrypting with wrong key should fail."""
        encryptor1 = CredentialEncryptor(encryption_key="key1")
        encryptor2 = CredentialEncryptor(encryption_key="key2")
        
        plaintext = "test_secret"
        encrypted = encryptor1.encrypt(plaintext)
        
        with pytest.raises(ValueError, match="Decryption failed"):
            encryptor2.decrypt(encrypted)
    
    def test_hash_value_deterministic(self):
        """hash_value should be deterministic."""
        encryptor = CredentialEncryptor(encryption_key="test_key")
        
        value = "test_value"
        hash1 = encryptor.hash_value(value)
        hash2 = encryptor.hash_value(value)
        
        assert hash1 == hash2
    
    def test_hash_value_different_for_different_inputs(self):
        """hash_value should produce different hashes for different inputs."""
        encryptor = CredentialEncryptor(encryption_key="test_key")
        
        hash1 = encryptor.hash_value("value1")
        hash2 = encryptor.hash_value("value2")
        
        assert hash1 != hash2
    
    def test_rotate_key(self):
        """Key rotation should work correctly."""
        old_key = "old_key"
        new_key = "new_key"
        plaintext = "secret_value"
        
        # Encrypt with old key
        old_encryptor = CredentialEncryptor(encryption_key=old_key)
        encrypted_old = old_encryptor.encrypt(plaintext)
        
        # Rotate to new key
        rotated = old_encryptor.rotate_key(old_key, new_key, encrypted_old)
        
        # Decrypt with new key
        new_encryptor = CredentialEncryptor(encryption_key=new_key)
        decrypted = new_encryptor.decrypt(rotated)
        
        assert decrypted == plaintext


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_encrypt_credential(self):
        """encrypt_credential should work."""
        encrypted = encrypt_credential("test_secret")
        assert encrypted.startswith("enc:")
    
    def test_decrypt_credential(self):
        """decrypt_credential should work."""
        encrypted = encrypt_credential("test_secret")
        decrypted = decrypt_credential(encrypted)
        assert decrypted == "test_secret"
    
    def test_mask_credential(self):
        """mask_credential should work."""
        masked = mask_credential("my-secret-api-key")
        assert '*' in masked
        assert len(masked) == len("my-secret-api-key")
    
    def test_get_credential_encryptor_singleton(self):
        """get_credential_encryptor should return the same instance."""
        encryptor1 = get_credential_encryptor()
        encryptor2 = get_credential_encryptor()
        assert encryptor1 is encryptor2
