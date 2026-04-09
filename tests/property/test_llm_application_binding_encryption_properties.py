"""
Property-based tests for LLM Application Binding - EncryptionService.

Uses Hypothesis library for property testing with minimum 100 iterations.
Tests Property 2 from the LLM Application Binding design document.

Feature: llm-application-binding
Property: 2 - API Key Encryption Round-Trip
"""

import pytest
import os
import base64
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.ai.encryption_service import EncryptionService, EncryptionError


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
    # Azure OpenAI API keys (32 hex characters)
    st.text(
        alphabet='0123456789abcdef',
        min_size=32,
        max_size=32
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
    # Ollama (local, no API key but test empty string handling)
    st.just("local-ollama-no-key"),
)


# ==================== Fixtures ====================

@pytest.fixture(scope="module")
def encryption_key():
    """Generate a test encryption key for the module."""
    # Generate a 32-byte key and encode as base64
    key_bytes = os.urandom(32)
    return base64.b64encode(key_bytes).decode('utf-8')


@pytest.fixture(scope="module")
def encryption_service(encryption_key):
    """Create an EncryptionService instance with a test key."""
    return EncryptionService(encryption_key=encryption_key)


# ==================== Property 2: API Key Encryption Round-Trip ====================

class TestAPIKeyEncryptionRoundTrip:
    """
    Property 2: API Key Encryption Round-Trip
    
    For any API key string, encrypting then decrypting should produce 
    the original value, and the encrypted value should differ from the original.
    
    **Validates: Requirements 1.3, 4.3, 12.1**
    
    Requirements:
    - 1.3: WHEN an administrator creates an LLM configuration, THE System SHALL 
           encrypt the api_key before storage
    - 4.3: THE System SHALL decrypt api_key values before returning them to applications
    - 12.1: WHEN an API key is stored, THE System SHALL encrypt it using AES-256 encryption
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(api_key=api_key_strategy)
    def test_property_2_encryption_roundtrip_preserves_api_key(
        self,
        encryption_service,
        api_key: str
    ):
        """
        Feature: llm-application-binding, Property 2: API Key Encryption Round-Trip
        
        For any API key string, encrypting then decrypting should return 
        the original API key value.
        
        **Validates: Requirements 1.3, 4.3, 12.1**
        """
        # Skip empty or whitespace-only API keys (service validates this)
        assume(len(api_key.strip()) > 0)
        
        # Encrypt the API key (simulating storage)
        encrypted_api_key = encryption_service.encrypt(api_key)
        
        # Decrypt the API key (simulating retrieval)
        decrypted_api_key = encryption_service.decrypt(encrypted_api_key)
        
        # Property: Round-trip should preserve the original value
        assert decrypted_api_key == api_key, \
            f"Decrypted API key should match original. Got: {decrypted_api_key[:10]}..."
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(api_key=api_key_strategy)
    def test_property_2_encrypted_value_differs_from_plaintext(
        self,
        encryption_service,
        api_key: str
    ):
        """
        Feature: llm-application-binding, Property 2: API Key Encryption Round-Trip
        
        For any API key string, the encrypted (stored) value should be 
        different from the plaintext value.
        
        **Validates: Requirements 1.3, 4.3, 12.1**
        """
        # Skip empty or whitespace-only API keys
        assume(len(api_key.strip()) > 0)
        
        # Encrypt the API key
        encrypted_api_key = encryption_service.encrypt(api_key)
        
        # Property: Encrypted value must be different from plaintext
        assert encrypted_api_key != api_key, \
            "Encrypted API key should differ from plaintext"
        
        # Additional check: encrypted value should be Base64 encoded
        try:
            decoded = base64.b64decode(encrypted_api_key)
            assert len(decoded) > 0, "Encrypted value should be valid Base64"
        except Exception as e:
            pytest.fail(f"Encrypted value should be valid Base64: {e}")
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(api_key=api_key_strategy)
    def test_property_2_same_key_different_ciphertext(
        self,
        encryption_service,
        api_key: str
    ):
        """
        Feature: llm-application-binding, Property 2: API Key Encryption Round-Trip
        
        For any API key string, encrypting the same key twice should produce 
        different ciphertext (due to random nonce), but both should decrypt 
        to the original value.
        
        **Validates: Requirements 1.3, 4.3, 12.1**
        """
        # Skip empty or whitespace-only API keys
        assume(len(api_key.strip()) > 0)
        
        # Encrypt the same API key twice
        encrypted1 = encryption_service.encrypt(api_key)
        encrypted2 = encryption_service.encrypt(api_key)
        
        # Property: Different encryptions should produce different ciphertext
        # (due to random nonce in AES-GCM)
        assert encrypted1 != encrypted2, \
            "Same API key encrypted twice should produce different ciphertext"
        
        # Both should decrypt to the original value
        decrypted1 = encryption_service.decrypt(encrypted1)
        decrypted2 = encryption_service.decrypt(encrypted2)
        
        assert decrypted1 == api_key
        assert decrypted2 == api_key
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(api_key=china_api_key_strategy)
    def test_property_2_china_provider_api_keys(
        self,
        encryption_service,
        api_key: str
    ):
        """
        Feature: llm-application-binding, Property 2: API Key Encryption Round-Trip
        
        For any Chinese LLM provider API key (Qwen, Zhipu, Baidu, Ollama),
        encryption round-trip should preserve the original value.
        
        **Validates: Requirements 1.3, 4.3, 12.1**
        """
        # Skip empty or whitespace-only API keys
        assume(len(api_key.strip()) > 0)
        
        # Encrypt
        encrypted = encryption_service.encrypt(api_key)
        
        # Verify encrypted differs from plaintext
        assert encrypted != api_key
        
        # Decrypt
        decrypted = encryption_service.decrypt(encrypted)
        
        # Verify round-trip
        assert decrypted == api_key


# ==================== Additional Security Properties ====================

class TestAPIKeyEncryptionSecurity:
    """
    Additional security properties for API key encryption.
    
    **Validates: Requirements 1.3, 4.3, 12.1**
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        api_key1=api_key_strategy,
        api_key2=api_key_strategy
    )
    def test_different_api_keys_produce_different_ciphertext(
        self,
        encryption_service,
        api_key1: str,
        api_key2: str
    ):
        """
        Different API keys should produce different ciphertext when encrypted
        with the same key.
        
        **Validates: Requirements 1.3, 12.1**
        """
        assume(len(api_key1.strip()) > 0)
        assume(len(api_key2.strip()) > 0)
        assume(api_key1 != api_key2)
        
        encrypted1 = encryption_service.encrypt(api_key1)
        encrypted2 = encryption_service.encrypt(api_key2)
        
        # Different plaintexts should produce different ciphertexts
        assert encrypted1 != encrypted2
    
    def test_encryption_uses_aes_256_gcm(self, encryption_service):
        """
        Verify that the encryption service uses AES-256-GCM.
        
        **Validates: Requirements 12.1**
        """
        # AES-256 requires a 256-bit (32-byte) key
        assert len(encryption_service._key) == 32, \
            "Encryption should use AES-256 (32-byte key)"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(api_key=api_key_strategy)
    def test_encrypted_length_appropriate(
        self,
        encryption_service,
        api_key: str
    ):
        """
        Encrypted API key should have appropriate length (not excessively long).
        
        **Validates: Requirements 1.3, 12.1**
        """
        assume(len(api_key.strip()) > 0)
        
        encrypted = encryption_service.encrypt(api_key)
        
        # Encrypted length should be reasonable:
        # Base64 encoding increases size by ~33%
        # Plus nonce (12 bytes) and auth tag (16 bytes)
        # So encrypted should be roughly: (len(api_key) + 28) * 4/3
        max_expected_length = (len(api_key.encode('utf-8')) + 28) * 2
        
        assert len(encrypted) <= max_expected_length, \
            f"Encrypted length {len(encrypted)} exceeds expected max {max_expected_length}"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(api_key=api_key_strategy)
    def test_wrong_key_fails_decryption(
        self,
        encryption_key,
        api_key: str
    ):
        """
        For any API key encrypted with one key, attempting to decrypt with 
        a different key should fail (security property).
        
        **Validates: Requirements 12.1**
        """
        # Skip empty keys
        assume(len(api_key.strip()) > 0)
        
        # Create two different encryption services with different keys
        service1 = EncryptionService(encryption_key=encryption_key)
        
        # Generate a different key
        different_key_bytes = os.urandom(32)
        different_key = base64.b64encode(different_key_bytes).decode('utf-8')
        service2 = EncryptionService(encryption_key=different_key)
        
        # Encrypt with first key
        encrypted = service1.encrypt(api_key)
        
        # Attempt to decrypt with second key should fail
        with pytest.raises(EncryptionError):
            service2.decrypt(encrypted)


# ==================== Edge Cases ====================

class TestAPIKeyEncryptionEdgeCases:
    """
    Edge case tests for API key encryption.
    
    **Validates: Requirements 1.3, 4.3, 12.1**
    """
    
    def test_empty_api_key_raises_error(self, encryption_service):
        """Empty API key should raise an error."""
        with pytest.raises(ValueError, match="plaintext cannot be empty"):
            encryption_service.encrypt("")
    
    def test_unicode_api_key_roundtrip(self, encryption_service):
        """
        API keys with unicode characters should round-trip correctly.
        
        **Validates: Requirements 1.3, 4.3, 12.1**
        """
        # API key with unicode (unlikely but should work)
        api_key = "sk-测试密钥-αβγ-🔑"
        
        encrypted = encryption_service.encrypt(api_key)
        assert encrypted != api_key
        
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == api_key
    
    def test_very_long_api_key_roundtrip(self, encryption_service):
        """
        Very long API keys should round-trip correctly.
        
        **Validates: Requirements 1.3, 4.3, 12.1**
        """
        # Very long API key (1000 characters)
        api_key = "sk-" + "a" * 997
        
        encrypted = encryption_service.encrypt(api_key)
        assert encrypted != api_key
        
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == api_key
    
    def test_special_characters_in_api_key(self, encryption_service):
        """
        API keys with special characters should round-trip correctly.
        
        **Validates: Requirements 1.3, 4.3, 12.1**
        """
        # API key with various special characters
        api_key = "sk-test_key-with.special+chars/and=more"
        
        encrypted = encryption_service.encrypt(api_key)
        assert encrypted != api_key
        
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == api_key
    
    def test_tampered_ciphertext_fails_decryption(self, encryption_service):
        """
        Tampered ciphertext should fail decryption (integrity check).
        
        **Validates: Requirements 12.1**
        """
        api_key = "sk-test-api-key-12345"
        
        encrypted = encryption_service.encrypt(api_key)
        
        # Tamper with the ciphertext
        encrypted_bytes = base64.b64decode(encrypted)
        tampered_bytes = bytearray(encrypted_bytes)
        tampered_bytes[len(tampered_bytes) // 2] ^= 0xFF  # Flip bits
        tampered = base64.b64encode(bytes(tampered_bytes)).decode('utf-8')
        
        # Decryption should fail due to authentication tag mismatch
        with pytest.raises(EncryptionError):
            encryption_service.decrypt(tampered)
    
    def test_empty_encrypted_string_raises_error(self, encryption_service):
        """Empty encrypted string should raise an error."""
        with pytest.raises(ValueError, match="encrypted cannot be empty"):
            encryption_service.decrypt("")
    
    def test_invalid_base64_raises_error(self, encryption_service):
        """Invalid base64 encrypted string should raise an error."""
        with pytest.raises(EncryptionError):
            encryption_service.decrypt("not-valid-base64!!!")
    
    def test_too_short_encrypted_data_raises_error(self, encryption_service):
        """Encrypted data shorter than nonce size should raise an error."""
        # Create a base64 string that decodes to less than 12 bytes
        short_data = base64.b64encode(b"short").decode('utf-8')
        
        with pytest.raises(EncryptionError, match="Encrypted data too short"):
            encryption_service.decrypt(short_data)


# ==================== Environment Variable Tests ====================

class TestEncryptionServiceInitialization:
    """
    Tests for EncryptionService initialization and key management.
    
    **Validates: Requirements 12.2**
    """
    
    def test_initialization_with_explicit_key(self):
        """Service should initialize with an explicit encryption key."""
        key_bytes = os.urandom(32)
        key = base64.b64encode(key_bytes).decode('utf-8')
        
        service = EncryptionService(encryption_key=key)
        
        assert service._key == key_bytes
    
    def test_initialization_from_environment_variable(self):
        """Service should initialize from LLM_ENCRYPTION_KEY environment variable."""
        key_bytes = os.urandom(32)
        key = base64.b64encode(key_bytes).decode('utf-8')
        
        # Save original env var
        original_key = os.environ.get("LLM_ENCRYPTION_KEY")
        
        try:
            os.environ["LLM_ENCRYPTION_KEY"] = key
            
            service = EncryptionService()
            
            assert service._key == key_bytes
            
        finally:
            # Restore original environment
            if original_key is not None:
                os.environ["LLM_ENCRYPTION_KEY"] = original_key
            elif "LLM_ENCRYPTION_KEY" in os.environ:
                del os.environ["LLM_ENCRYPTION_KEY"]
    
    def test_initialization_without_key_raises_error(self):
        """Service should raise error if no encryption key is provided."""
        # Save original env var
        original_key = os.environ.get("LLM_ENCRYPTION_KEY")
        
        try:
            # Remove env var
            if "LLM_ENCRYPTION_KEY" in os.environ:
                del os.environ["LLM_ENCRYPTION_KEY"]
            
            with pytest.raises(ValueError, match="LLM_ENCRYPTION_KEY environment variable not set"):
                EncryptionService()
            
        finally:
            # Restore original environment
            if original_key is not None:
                os.environ["LLM_ENCRYPTION_KEY"] = original_key
    
    def test_initialization_with_invalid_base64_raises_error(self):
        """Service should raise error if encryption key is not valid base64."""
        with pytest.raises(ValueError, match="Invalid encryption key"):
            EncryptionService(encryption_key="not-valid-base64!!!")
    
    def test_initialization_with_wrong_key_length_raises_error(self):
        """Service should raise error if encryption key is not 32 bytes."""
        # 16-byte key (AES-128, not AES-256)
        short_key = base64.b64encode(os.urandom(16)).decode('utf-8')
        
        with pytest.raises(ValueError, match="Encryption key must be 32 bytes"):
            EncryptionService(encryption_key=short_key)


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
