"""
Admin Configuration Encryption Property Tests

Tests encryption round-trip properties for configuration data.

Validates: Requirements 1.4, 1.7, 2.5
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

# Import the encryption service
from src.admin.credential_encryptor import CredentialEncryptor


# ============================================================================
# Property 1: Configuration Round-Trip with Encryption
# ============================================================================

class TestConfigurationEncryptionRoundTrip:
    """
    Property 1: Configuration Round-Trip with Encryption
    
    For any valid configuration (LLM, database, or sync strategy), saving the 
    configuration and then retrieving it should return equivalent data, and all 
    sensitive fields (API keys, passwords, secrets) should be encrypted in 
    storage (not plaintext).
    
    **Validates: Requirements 1.4, 1.7, 2.5**
    """
    
    @given(
        plaintext=st.text(min_size=1, max_size=1000),
        encryption_key=st.text(min_size=8, max_size=64)
    )
    @settings(max_examples=100, deadline=None)
    def test_encrypt_decrypt_roundtrip(self, plaintext: str, encryption_key: str):
        """
        Encrypted data can be decrypted to original value.
        
        For any plaintext credential and encryption key, encrypting and then
        decrypting should return the original plaintext value.
        """
        # Skip empty or whitespace-only strings
        assume(len(plaintext.strip()) > 0)
        assume(len(encryption_key.strip()) >= 8)
        
        # Create encryptor with specific key
        encryptor = CredentialEncryptor(encryption_key=encryption_key)
        
        # Encrypt the plaintext
        ciphertext = encryptor.encrypt(plaintext)
        
        # Verify encrypted data is not plaintext
        assert ciphertext != plaintext, "Ciphertext should not equal plaintext"
        assert encryptor.is_encrypted(ciphertext), "Value should be marked as encrypted"
        
        # Decrypt the ciphertext
        decrypted = encryptor.decrypt(ciphertext)
        
        # Verify decrypted value equals original plaintext
        assert decrypted == plaintext, "Decrypted value should equal original plaintext"
    
    @given(
        api_key=st.text(min_size=20, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            min_codepoint=33,
            max_codepoint=126
        )),
        password=st.text(min_size=8, max_size=64, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P'),
            min_codepoint=33,
            max_codepoint=126
        ))
    )
    @settings(max_examples=100, deadline=None)
    def test_sensitive_fields_encrypted_in_storage(self, api_key: str, password: str):
        """
        Verify encrypted data is not plaintext in storage.
        
        For any sensitive credential (API key, password), the encrypted value
        should not contain the plaintext and should be identifiable as encrypted.
        """
        assume(len(api_key.strip()) >= 20)
        assume(len(password.strip()) >= 8)
        
        encryptor = CredentialEncryptor()
        
        # Encrypt API key
        encrypted_api_key = encryptor.encrypt(api_key)
        
        # Verify API key is not in plaintext in encrypted value
        assert api_key not in encrypted_api_key, "Plaintext API key should not appear in ciphertext"
        assert encrypted_api_key.startswith(CredentialEncryptor.ENCRYPTED_PREFIX), \
            "Encrypted value should have encryption prefix"
        
        # Encrypt password
        encrypted_password = encryptor.encrypt(password)
        
        # Verify password is not in plaintext in encrypted value
        assert password not in encrypted_password, "Plaintext password should not appear in ciphertext"
        assert encrypted_password.startswith(CredentialEncryptor.ENCRYPTED_PREFIX), \
            "Encrypted value should have encryption prefix"
        
        # Verify both can be decrypted correctly
        assert encryptor.decrypt(encrypted_api_key) == api_key
        assert encryptor.decrypt(encrypted_password) == password
    
    @given(
        credential=st.text(min_size=10, max_size=200),
        key1=st.text(min_size=8, max_size=32),
        key2=st.text(min_size=8, max_size=32)
    )
    @settings(max_examples=50, deadline=None)
    def test_different_keys_produce_different_ciphertext(
        self, 
        credential: str, 
        key1: str, 
        key2: str
    ):
        """
        Different encryption keys should produce different ciphertext.
        
        For any credential encrypted with two different keys, the resulting
        ciphertext should be different, but both should decrypt correctly
        with their respective keys.
        """
        assume(len(credential.strip()) >= 10)
        assume(len(key1.strip()) >= 8)
        assume(len(key2.strip()) >= 8)
        assume(key1 != key2)  # Ensure keys are different
        
        # Create two encryptors with different keys
        encryptor1 = CredentialEncryptor(encryption_key=key1)
        encryptor2 = CredentialEncryptor(encryption_key=key2)
        
        # Encrypt with both keys
        ciphertext1 = encryptor1.encrypt(credential)
        ciphertext2 = encryptor2.encrypt(credential)
        
        # Verify ciphertexts are different
        assert ciphertext1 != ciphertext2, \
            "Different keys should produce different ciphertext"
        
        # Verify each decrypts correctly with its own key
        assert encryptor1.decrypt(ciphertext1) == credential
        assert encryptor2.decrypt(ciphertext2) == credential
        
        # Verify cross-decryption fails
        with pytest.raises(ValueError):
            encryptor1.decrypt(ciphertext2)
        
        with pytest.raises(ValueError):
            encryptor2.decrypt(ciphertext1)
    
    @given(
        plaintext=st.text(min_size=1, max_size=500)
    )
    @settings(max_examples=100, deadline=None)
    def test_same_plaintext_different_ciphertext_each_time(self, plaintext: str):
        """
        Same plaintext encrypted multiple times should produce different ciphertext.
        
        Due to random nonce/IV, encrypting the same plaintext multiple times
        should produce different ciphertext values, but all should decrypt
        to the same plaintext.
        """
        assume(len(plaintext.strip()) > 0)
        
        encryptor = CredentialEncryptor()
        
        # Encrypt the same plaintext multiple times
        ciphertext1 = encryptor.encrypt(plaintext)
        ciphertext2 = encryptor.encrypt(plaintext)
        ciphertext3 = encryptor.encrypt(plaintext)
        
        # Verify all ciphertexts are different (due to random nonce)
        assert ciphertext1 != ciphertext2, "Multiple encryptions should produce different ciphertext"
        assert ciphertext2 != ciphertext3, "Multiple encryptions should produce different ciphertext"
        assert ciphertext1 != ciphertext3, "Multiple encryptions should produce different ciphertext"
        
        # Verify all decrypt to the same plaintext
        assert encryptor.decrypt(ciphertext1) == plaintext
        assert encryptor.decrypt(ciphertext2) == plaintext
        assert encryptor.decrypt(ciphertext3) == plaintext
    
    def test_empty_value_raises_error(self):
        """
        Encrypting empty or None values should raise an error.
        
        The encryption service should reject empty values to prevent
        storing invalid encrypted data.
        """
        encryptor = CredentialEncryptor()
        
        # Empty string should raise error
        with pytest.raises(ValueError, match="Cannot encrypt empty or None value"):
            encryptor.encrypt("")
        
        # None should raise error
        with pytest.raises(ValueError, match="Cannot encrypt empty or None value"):
            encryptor.encrypt(None)
    
    def test_invalid_ciphertext_raises_error(self):
        """
        Decrypting invalid ciphertext should raise an error.
        
        The encryption service should detect and reject invalid or
        corrupted ciphertext.
        """
        encryptor = CredentialEncryptor()
        
        # Invalid base64
        with pytest.raises(ValueError):
            encryptor.decrypt("invalid_ciphertext_!@#$%")
        
        # Valid base64 but invalid Fernet token
        with pytest.raises(ValueError):
            encryptor.decrypt("enc:YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo=")
    
    @given(
        credential=st.text(min_size=10, max_size=100)
    )
    @settings(max_examples=50, deadline=None)
    def test_double_encryption_prevention(self, credential: str):
        """
        Encrypting already encrypted data should not double-encrypt.
        
        The encryption service should detect already encrypted values
        and return them unchanged to prevent double encryption.
        """
        assume(len(credential.strip()) >= 10)
        
        encryptor = CredentialEncryptor()
        
        # First encryption
        encrypted_once = encryptor.encrypt(credential)
        
        # Attempt to encrypt again
        encrypted_twice = encryptor.encrypt(encrypted_once)
        
        # Should return the same value (not double-encrypted)
        assert encrypted_once == encrypted_twice, \
            "Already encrypted value should not be encrypted again"
        
        # Should still decrypt to original plaintext
        assert encryptor.decrypt(encrypted_twice) == credential
    
    @given(
        credential=st.text(min_size=10, max_size=100)
    )
    @settings(max_examples=50, deadline=None)
    def test_encrypt_if_needed_idempotent(self, credential: str):
        """
        encrypt_if_needed should be idempotent.
        
        Calling encrypt_if_needed multiple times should produce the same
        result after the first encryption.
        """
        assume(len(credential.strip()) >= 10)
        
        encryptor = CredentialEncryptor()
        
        # First call encrypts
        result1 = encryptor.encrypt_if_needed(credential)
        assert encryptor.is_encrypted(result1)
        
        # Second call should return same encrypted value
        result2 = encryptor.encrypt_if_needed(result1)
        assert result1 == result2
        
        # Third call should still return same value
        result3 = encryptor.encrypt_if_needed(result2)
        assert result1 == result3
        
        # All should decrypt to original
        assert encryptor.decrypt(result1) == credential
        assert encryptor.decrypt(result2) == credential
        assert encryptor.decrypt(result3) == credential
    
    @given(
        credential=st.text(min_size=10, max_size=100)
    )
    @settings(max_examples=50, deadline=None)
    def test_decrypt_if_needed_handles_both_encrypted_and_plain(self, credential: str):
        """
        decrypt_if_needed should handle both encrypted and plaintext values.
        
        For plaintext input, it should return unchanged. For encrypted input,
        it should decrypt.
        """
        assume(len(credential.strip()) >= 10)
        
        encryptor = CredentialEncryptor()
        
        # Plaintext should be returned unchanged
        result_plain = encryptor.decrypt_if_needed(credential)
        assert result_plain == credential
        
        # Encrypted value should be decrypted
        encrypted = encryptor.encrypt(credential)
        result_encrypted = encryptor.decrypt_if_needed(encrypted)
        assert result_encrypted == credential
    
    @given(
        credential=st.text(min_size=10, max_size=100),
        visible_chars=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_masking_preserves_length_information(self, credential: str, visible_chars: int):
        """
        Masking should preserve length information while hiding content.
        
        The masked value should have the same length as the original and
        should show only the specified number of characters at start and end.
        """
        assume(len(credential.strip()) >= 10)
        
        encryptor = CredentialEncryptor()
        
        # Mask the credential
        masked = encryptor.mask(credential, visible_chars=visible_chars)
        
        # Verify length is preserved
        assert len(masked) == len(credential), \
            "Masked value should have same length as original"
        
        # Verify masking pattern
        if len(credential) > visible_chars * 2:
            # Should show first and last visible_chars characters
            assert masked.startswith(credential[:visible_chars]), \
                "Masked value should show first N characters"
            assert masked.endswith(credential[-visible_chars:]), \
                "Masked value should show last N characters"
            assert '*' in masked, "Masked value should contain asterisks"
        else:
            # Short values should be fully masked
            assert all(c == '*' for c in masked), \
                "Short values should be fully masked"
    
    @given(
        old_key=st.text(min_size=8, max_size=32),
        new_key=st.text(min_size=8, max_size=32),
        credential=st.text(min_size=10, max_size=100)
    )
    @settings(max_examples=30, deadline=None)
    def test_key_rotation_preserves_plaintext(
        self, 
        old_key: str, 
        new_key: str, 
        credential: str
    ):
        """
        Key rotation should preserve the plaintext value.
        
        Rotating encryption keys should allow the same plaintext to be
        recovered using the new key.
        """
        assume(len(old_key.strip()) >= 8)
        assume(len(new_key.strip()) >= 8)
        assume(len(credential.strip()) >= 10)
        assume(old_key != new_key)
        
        # Create encryptor with old key
        old_encryptor = CredentialEncryptor(encryption_key=old_key)
        
        # Encrypt with old key
        encrypted_with_old = old_encryptor.encrypt(credential)
        
        # Rotate to new key
        rotated = old_encryptor.rotate_key(old_key, new_key, encrypted_with_old)
        
        # Create encryptor with new key
        new_encryptor = CredentialEncryptor(encryption_key=new_key)
        
        # Decrypt with new key should return original plaintext
        decrypted = new_encryptor.decrypt(rotated)
        assert decrypted == credential, \
            "Key rotation should preserve plaintext value"
        
        # Old key should no longer work
        with pytest.raises(ValueError):
            old_encryptor.decrypt(rotated)


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
