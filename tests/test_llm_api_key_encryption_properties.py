"""
Property-based tests for LLM Integration module - API Key Encryption Round-Trip.

Uses Hypothesis library for property testing with minimum 100 iterations.
Tests Property 4 from the LLM Integration design document.

Feature: llm-integration
Property: 4 - API Key Encryption Round-Trip
"""

import pytest
from typing import Optional
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.security.encryption import (
    AES256Encryption,
    EncryptionError,
    DecryptionError,
    encrypt,
    decrypt,
    generate_key
)


# ==================== Custom Strategies ====================

# Strategy for valid API keys (realistic API key formats)
# API keys typically contain alphanumeric characters, dashes, and underscores
# Length varies by provider: OpenAI (51 chars), Anthropic (108 chars), etc.
api_key_strategy = st.one_of(
    # OpenAI-style API keys (sk-...)
    st.builds(
        lambda suffix: f"sk-{suffix}",
        st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=48,
            max_size=48
        )
    ),
    # Anthropic-style API keys (sk-ant-...)
    st.builds(
        lambda suffix: f"sk-ant-{suffix}",
        st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-'),
            min_size=95,
            max_size=95
        )
    ),
    # Generic API keys (alphanumeric with dashes/underscores)
    st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
        min_size=16,
        max_size=128
    ),
    # UUID-style API keys
    st.uuids().map(str),
    # Base64-style API keys
    st.binary(min_size=16, max_size=64).map(lambda b: b.hex()),
)

# Strategy for encryption keys
encryption_key_strategy = st.one_of(
    # Generated keys (Base64 encoded 256-bit)
    st.just(generate_key()),
    # Password-derived keys
    st.text(min_size=8, max_size=64).filter(lambda x: len(x.strip()) >= 8),
)

# Strategy for Chinese LLM provider API keys
china_api_key_strategy = st.one_of(
    # Qwen/DashScope API keys
    st.builds(
        lambda suffix: f"sk-{suffix}",
        st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=32,
            max_size=32
        )
    ),
    # Zhipu API keys (typically longer)
    st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='.'),
        min_size=32,
        max_size=64
    ),
    # Baidu API keys
    st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N')),
        min_size=24,
        max_size=32
    ),
)


# ==================== Property 4: API Key Encryption Round-Trip ====================

class TestAPIKeyEncryptionRoundTrip:
    """
    Property 4: API Key Encryption Round-Trip
    
    For any API key string, storing it then retrieving it should produce 
    the original plaintext value, but the stored value in the database 
    should be encrypted and different from the plaintext.
    
    **Validates: Requirements 1.5, 9.1**
    
    Requirements:
    - 1.5: WHERE a provider requires API authentication, THE System SHALL 
           securely store and manage API keys using encryption
    - 9.1: WHEN storing API keys, THE System SHALL encrypt them using 
           AES-256 encryption
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        api_key=api_key_strategy,
        encryption_key=encryption_key_strategy
    )
    def test_property_4_encryption_roundtrip_preserves_api_key(
        self,
        api_key: str,
        encryption_key: str
    ):
        """
        Feature: llm-integration, Property 4: API Key Encryption Round-Trip
        
        For any API key string, encrypting then decrypting should return 
        the original API key value.
        
        **Validates: Requirements 1.5, 9.1**
        """
        # Skip empty or whitespace-only API keys
        assume(len(api_key.strip()) > 0)
        assume(len(encryption_key.strip()) >= 8)
        
        encryption = AES256Encryption()
        
        # Encrypt the API key (simulating storage)
        encrypted_api_key = encryption.encrypt(api_key, encryption_key)
        
        # Decrypt the API key (simulating retrieval)
        decrypted_api_key = encryption.decrypt(encrypted_api_key, encryption_key)
        
        # Property: Round-trip should preserve the original value
        assert decrypted_api_key == api_key, \
            f"Decrypted API key should match original. Got: {decrypted_api_key[:10]}..."
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        api_key=api_key_strategy,
        encryption_key=encryption_key_strategy
    )
    def test_property_4_encrypted_value_differs_from_plaintext(
        self,
        api_key: str,
        encryption_key: str
    ):
        """
        Feature: llm-integration, Property 4: API Key Encryption Round-Trip
        
        For any API key string, the encrypted (stored) value should be 
        different from the plaintext value.
        
        **Validates: Requirements 1.5, 9.1**
        """
        # Skip empty or whitespace-only API keys
        assume(len(api_key.strip()) > 0)
        assume(len(encryption_key.strip()) >= 8)
        
        encryption = AES256Encryption()
        
        # Encrypt the API key
        encrypted_api_key = encryption.encrypt(api_key, encryption_key)
        
        # Property: Encrypted value must be different from plaintext
        assert encrypted_api_key != api_key, \
            "Encrypted API key should differ from plaintext"
        
        # Additional check: encrypted value should be Base64 encoded
        # (AES256Encryption returns Base64 encoded ciphertext)
        import base64
        try:
            decoded = base64.b64decode(encrypted_api_key)
            assert len(decoded) > 0, "Encrypted value should be valid Base64"
        except Exception as e:
            pytest.fail(f"Encrypted value should be valid Base64: {e}")
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        api_key=api_key_strategy,
        encryption_key=encryption_key_strategy
    )
    def test_property_4_same_key_different_ciphertext(
        self,
        api_key: str,
        encryption_key: str
    ):
        """
        Feature: llm-integration, Property 4: API Key Encryption Round-Trip
        
        For any API key string, encrypting the same key twice should produce 
        different ciphertext (due to random nonce/IV), but both should decrypt 
        to the original value.
        
        **Validates: Requirements 1.5, 9.1**
        """
        # Skip empty or whitespace-only API keys
        assume(len(api_key.strip()) > 0)
        assume(len(encryption_key.strip()) >= 8)
        
        encryption = AES256Encryption()
        
        # Encrypt the same API key twice
        encrypted1 = encryption.encrypt(api_key, encryption_key)
        encrypted2 = encryption.encrypt(api_key, encryption_key)
        
        # Property: Different encryptions should produce different ciphertext
        # (due to random nonce in AES-GCM)
        assert encrypted1 != encrypted2, \
            "Same API key encrypted twice should produce different ciphertext"
        
        # Both should decrypt to the original value
        decrypted1 = encryption.decrypt(encrypted1, encryption_key)
        decrypted2 = encryption.decrypt(encrypted2, encryption_key)
        
        assert decrypted1 == api_key
        assert decrypted2 == api_key
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        api_key=china_api_key_strategy,
        encryption_key=encryption_key_strategy
    )
    def test_property_4_china_provider_api_keys(
        self,
        api_key: str,
        encryption_key: str
    ):
        """
        Feature: llm-integration, Property 4: API Key Encryption Round-Trip
        
        For any Chinese LLM provider API key (Qwen, Zhipu, Baidu, Hunyuan),
        encryption round-trip should preserve the original value.
        
        **Validates: Requirements 1.5, 9.1**
        """
        # Skip empty or whitespace-only API keys
        assume(len(api_key.strip()) > 0)
        assume(len(encryption_key.strip()) >= 8)
        
        encryption = AES256Encryption()
        
        # Encrypt
        encrypted = encryption.encrypt(api_key, encryption_key)
        
        # Verify encrypted differs from plaintext
        assert encrypted != api_key
        
        # Decrypt
        decrypted = encryption.decrypt(encrypted, encryption_key)
        
        # Verify round-trip
        assert decrypted == api_key
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        api_key=api_key_strategy,
        correct_key=encryption_key_strategy,
        wrong_key=encryption_key_strategy
    )
    def test_property_4_wrong_key_fails_decryption(
        self,
        api_key: str,
        correct_key: str,
        wrong_key: str
    ):
        """
        Feature: llm-integration, Property 4: API Key Encryption Round-Trip
        
        For any API key encrypted with one key, attempting to decrypt with 
        a different key should fail (security property).
        
        **Validates: Requirements 1.5, 9.1**
        """
        # Skip empty keys and ensure keys are different
        assume(len(api_key.strip()) > 0)
        assume(len(correct_key.strip()) >= 8)
        assume(len(wrong_key.strip()) >= 8)
        assume(correct_key != wrong_key)
        
        encryption = AES256Encryption()
        
        # Encrypt with correct key
        encrypted = encryption.encrypt(api_key, correct_key)
        
        # Attempt to decrypt with wrong key should fail
        with pytest.raises(DecryptionError):
            encryption.decrypt(encrypted, wrong_key)
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        api_key=st.text(min_size=1, max_size=500).filter(lambda x: len(x.strip()) > 0)
    )
    def test_property_4_encryption_with_master_key(self, api_key: str):
        """
        Feature: llm-integration, Property 4: API Key Encryption Round-Trip
        
        For any API key, encryption using the convenience functions (which use
        the master key) should preserve the original value on round-trip.
        
        **Validates: Requirements 1.5, 9.1**
        """
        import os
        
        # Set up a test master key
        test_master_key = "test_master_key_for_property_testing"
        original_key = os.environ.get("ENCRYPTION_MASTER_KEY")
        
        try:
            os.environ["ENCRYPTION_MASTER_KEY"] = test_master_key
            
            # Create a new encryption instance with the master key
            encryption = AES256Encryption(master_key=test_master_key)
            
            # Encrypt using master key (no explicit key parameter)
            encrypted = encryption.encrypt(api_key)
            
            # Verify encrypted differs from plaintext
            assert encrypted != api_key
            
            # Decrypt using master key
            decrypted = encryption.decrypt(encrypted)
            
            # Verify round-trip
            assert decrypted == api_key
            
        finally:
            # Restore original environment
            if original_key is not None:
                os.environ["ENCRYPTION_MASTER_KEY"] = original_key
            elif "ENCRYPTION_MASTER_KEY" in os.environ:
                del os.environ["ENCRYPTION_MASTER_KEY"]
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        api_key=api_key_strategy,
        password=st.text(min_size=8, max_size=32).filter(lambda x: len(x.strip()) >= 8)
    )
    def test_property_4_encryption_with_salt(
        self,
        api_key: str,
        password: str
    ):
        """
        Feature: llm-integration, Property 4: API Key Encryption Round-Trip
        
        For any API key, encryption with salt (password-based) should preserve 
        the original value on round-trip.
        
        **Validates: Requirements 1.5, 9.1**
        """
        assume(len(api_key.strip()) > 0)
        
        encryption = AES256Encryption()
        
        # Encrypt with salt
        encrypted = encryption.encrypt_with_salt(api_key, password)
        
        # Verify encrypted differs from plaintext
        assert encrypted != api_key
        
        # Decrypt with salt
        decrypted = encryption.decrypt_with_salt(encrypted, password)
        
        # Verify round-trip
        assert decrypted == api_key


# ==================== Additional Security Properties ====================

class TestAPIKeyEncryptionSecurity:
    """
    Additional security properties for API key encryption.
    
    **Validates: Requirements 1.5, 9.1**
    """
    
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        api_key1=api_key_strategy,
        api_key2=api_key_strategy,
        encryption_key=encryption_key_strategy
    )
    def test_different_api_keys_produce_different_ciphertext(
        self,
        api_key1: str,
        api_key2: str,
        encryption_key: str
    ):
        """
        Different API keys should produce different ciphertext when encrypted
        with the same key.
        
        **Validates: Requirements 1.5, 9.1**
        """
        assume(len(api_key1.strip()) > 0)
        assume(len(api_key2.strip()) > 0)
        assume(len(encryption_key.strip()) >= 8)
        assume(api_key1 != api_key2)
        
        encryption = AES256Encryption()
        
        encrypted1 = encryption.encrypt(api_key1, encryption_key)
        encrypted2 = encryption.encrypt(api_key2, encryption_key)
        
        # Different plaintexts should produce different ciphertexts
        assert encrypted1 != encrypted2
    
    def test_encryption_uses_aes_256(self):
        """
        Verify that the encryption service uses AES-256 (32-byte key).
        
        **Validates: Requirements 9.1**
        """
        # AES-256 requires a 256-bit (32-byte) key
        assert AES256Encryption.KEY_SIZE == 32, \
            "Encryption should use AES-256 (32-byte key)"
    
    def test_encryption_uses_gcm_mode(self):
        """
        Verify that the encryption service uses GCM mode for authenticated encryption.
        
        **Validates: Requirements 9.1**
        """
        # GCM mode uses a 96-bit (12-byte) nonce
        assert AES256Encryption.NONCE_SIZE == 12, \
            "Encryption should use GCM mode (12-byte nonce)"
    
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(api_key=api_key_strategy)
    def test_encrypted_length_appropriate(self, api_key: str):
        """
        Encrypted API key should have appropriate length (not excessively long).
        
        **Validates: Requirements 1.5, 9.1**
        """
        assume(len(api_key.strip()) > 0)
        
        encryption = AES256Encryption()
        key = generate_key()
        
        encrypted = encryption.encrypt(api_key, key)
        
        # Encrypted length should be reasonable:
        # Base64 encoding increases size by ~33%
        # Plus nonce (12 bytes) and auth tag (16 bytes)
        # So encrypted should be roughly: (len(api_key) + 28) * 4/3
        max_expected_length = (len(api_key.encode('utf-8')) + 28) * 2
        
        assert len(encrypted) <= max_expected_length, \
            f"Encrypted length {len(encrypted)} exceeds expected max {max_expected_length}"


# ==================== Edge Cases ====================

class TestAPIKeyEncryptionEdgeCases:
    """
    Edge case tests for API key encryption.
    
    **Validates: Requirements 1.5, 9.1**
    """
    
    def test_empty_api_key_raises_error(self):
        """Empty API key should raise an error."""
        encryption = AES256Encryption()
        key = generate_key()
        
        with pytest.raises(EncryptionError):
            encryption.encrypt("", key)
    
    def test_unicode_api_key_roundtrip(self):
        """
        API keys with unicode characters should round-trip correctly.
        
        **Validates: Requirements 1.5, 9.1**
        """
        encryption = AES256Encryption()
        key = generate_key()
        
        # API key with unicode (unlikely but should work)
        api_key = "sk-测试密钥-αβγ-🔑"
        
        encrypted = encryption.encrypt(api_key, key)
        assert encrypted != api_key
        
        decrypted = encryption.decrypt(encrypted, key)
        assert decrypted == api_key
    
    def test_very_long_api_key_roundtrip(self):
        """
        Very long API keys should round-trip correctly.
        
        **Validates: Requirements 1.5, 9.1**
        """
        encryption = AES256Encryption()
        key = generate_key()
        
        # Very long API key (1000 characters)
        api_key = "sk-" + "a" * 997
        
        encrypted = encryption.encrypt(api_key, key)
        assert encrypted != api_key
        
        decrypted = encryption.decrypt(encrypted, key)
        assert decrypted == api_key
    
    def test_special_characters_in_api_key(self):
        """
        API keys with special characters should round-trip correctly.
        
        **Validates: Requirements 1.5, 9.1**
        """
        encryption = AES256Encryption()
        key = generate_key()
        
        # API key with various special characters
        api_key = "sk-test_key-with.special+chars/and=more"
        
        encrypted = encryption.encrypt(api_key, key)
        assert encrypted != api_key
        
        decrypted = encryption.decrypt(encrypted, key)
        assert decrypted == api_key
    
    def test_tampered_ciphertext_fails_decryption(self):
        """
        Tampered ciphertext should fail decryption (integrity check).
        
        **Validates: Requirements 1.5, 9.1**
        """
        import base64
        
        encryption = AES256Encryption()
        key = generate_key()
        api_key = "sk-test-api-key-12345"
        
        encrypted = encryption.encrypt(api_key, key)
        
        # Tamper with the ciphertext
        encrypted_bytes = base64.b64decode(encrypted)
        tampered_bytes = bytearray(encrypted_bytes)
        tampered_bytes[len(tampered_bytes) // 2] ^= 0xFF  # Flip bits
        tampered = base64.b64encode(bytes(tampered_bytes)).decode('utf-8')
        
        # Decryption should fail due to authentication tag mismatch
        with pytest.raises(DecryptionError):
            encryption.decrypt(tampered, key)


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
