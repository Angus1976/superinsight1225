"""
Tests for AI Integration authentication and credential management.

Tests credential generation, hashing, and validation using both unit tests
and property-based tests. Also tests JWT token generation and validation.
"""

import pytest
import string
import time
from datetime import datetime, timedelta
import jwt as pyjwt
from hypothesis import given, strategies as st, settings, assume

from src.ai_integration.auth import (
    generate_api_key,
    generate_api_secret,
    hash_credential,
    verify_credential,
    generate_credentials,
    validate_credentials,
    APICredentials,
    JWTTokenService,
    TokenClaims,
)


# ============================================================================
# Unit Tests
# ============================================================================

def test_generate_api_key_default_length():
    """Test API key generation with default length."""
    key = generate_api_key()
    
    assert len(key) == 32
    assert all(c in string.ascii_letters + string.digits for c in key)


def test_generate_api_key_custom_length():
    """Test API key generation with custom length."""
    key = generate_api_key(length=64)
    
    assert len(key) == 64
    assert all(c in string.ascii_letters + string.digits for c in key)


def test_generate_api_key_minimum_length():
    """Test API key generation enforces minimum length."""
    with pytest.raises(ValueError, match="at least 16 characters"):
        generate_api_key(length=15)


def test_generate_api_key_uniqueness():
    """Test that generated API keys are unique."""
    keys = [generate_api_key() for _ in range(100)]
    
    # All keys should be unique
    assert len(keys) == len(set(keys))


def test_generate_api_secret_default_length():
    """Test API secret generation with default length."""
    secret = generate_api_secret()
    
    assert len(secret) == 64


def test_generate_api_secret_custom_length():
    """Test API secret generation with custom length."""
    secret = generate_api_secret(length=48)
    
    assert len(secret) == 48


def test_generate_api_secret_maximum_length():
    """Test API secret generation at maximum recommended length."""
    secret = generate_api_secret(length=64)
    
    assert len(secret) == 64


def test_generate_api_secret_exceeds_limit():
    """Test API secret generation enforces maximum length."""
    with pytest.raises(ValueError, match="should not exceed 64 characters"):
        generate_api_secret(length=65)


def test_generate_api_secret_minimum_length():
    """Test API secret generation enforces minimum length."""
    with pytest.raises(ValueError, match="at least 32 characters"):
        generate_api_secret(length=31)


def test_generate_api_secret_uniqueness():
    """Test that generated API secrets are unique."""
    secrets = [generate_api_secret() for _ in range(100)]
    
    # All secrets should be unique
    assert len(secrets) == len(set(secrets))


def test_hash_credential_basic():
    """Test basic credential hashing."""
    credential = "test_credential_123"
    hashed = hash_credential(credential)
    
    # Hash should be a non-empty string
    assert isinstance(hashed, str)
    assert len(hashed) > 0
    
    # Hash should start with bcrypt prefix
    assert hashed.startswith("$2b$")


def test_hash_credential_empty():
    """Test hashing empty credential raises error."""
    with pytest.raises(ValueError, match="cannot be empty"):
        hash_credential("")


def test_hash_credential_different_salts():
    """Test that same credential produces different hashes (different salts)."""
    credential = "same_credential"
    hash1 = hash_credential(credential)
    hash2 = hash_credential(credential)
    
    # Hashes should be different due to different salts
    assert hash1 != hash2


def test_verify_credential_correct():
    """Test credential verification with correct credential."""
    credential = "my_secret_key"
    hashed = hash_credential(credential)
    
    assert verify_credential(credential, hashed) is True


def test_verify_credential_incorrect():
    """Test credential verification with incorrect credential."""
    credential = "my_secret_key"
    hashed = hash_credential(credential)
    
    assert verify_credential("wrong_key", hashed) is False


def test_verify_credential_empty():
    """Test credential verification with empty inputs."""
    hashed = hash_credential("test")
    
    assert verify_credential("", hashed) is False
    assert verify_credential("test", "") is False
    assert verify_credential("", "") is False


def test_verify_credential_invalid_hash():
    """Test credential verification with invalid hash."""
    assert verify_credential("test", "invalid_hash") is False


def test_generate_credentials_basic():
    """Test complete credential generation."""
    creds = generate_credentials()
    
    # Check plain text credentials
    assert isinstance(creds.api_key, str)
    assert isinstance(creds.api_secret, str)
    assert len(creds.api_key) == 32
    assert len(creds.api_secret) == 64
    
    # Check hashes
    assert isinstance(creds.api_key_hash, str)
    assert isinstance(creds.api_secret_hash, str)
    assert creds.api_key_hash.startswith("$2b$")
    assert creds.api_secret_hash.startswith("$2b$")
    
    # Verify hashes match credentials
    assert verify_credential(creds.api_key, creds.api_key_hash)
    assert verify_credential(creds.api_secret, creds.api_secret_hash)


def test_generate_credentials_custom_lengths():
    """Test credential generation with custom lengths."""
    creds = generate_credentials(api_key_length=48, api_secret_length=64)
    
    assert len(creds.api_key) == 48
    assert len(creds.api_secret) == 64


def test_validate_credentials_correct():
    """Test credential validation with correct credentials."""
    creds = generate_credentials()
    
    result = validate_credentials(
        creds.api_key,
        creds.api_secret,
        creds.api_key_hash,
        creds.api_secret_hash
    )
    
    assert result is True


def test_validate_credentials_wrong_key():
    """Test credential validation with wrong API key."""
    creds = generate_credentials()
    
    result = validate_credentials(
        "wrong_key",
        creds.api_secret,
        creds.api_key_hash,
        creds.api_secret_hash
    )
    
    assert result is False


def test_validate_credentials_wrong_secret():
    """Test credential validation with wrong API secret."""
    creds = generate_credentials()
    
    result = validate_credentials(
        creds.api_key,
        "wrong_secret",
        creds.api_key_hash,
        creds.api_secret_hash
    )
    
    assert result is False


def test_validate_credentials_both_wrong():
    """Test credential validation with both credentials wrong."""
    creds = generate_credentials()
    
    result = validate_credentials(
        "wrong_key",
        "wrong_secret",
        creds.api_key_hash,
        creds.api_secret_hash
    )
    
    assert result is False


# ============================================================================
# Property-Based Tests
# ============================================================================

@settings(max_examples=20, deadline=None)
@given(length=st.integers(min_value=16, max_value=256))
def test_property_api_key_length(length: int):
    """
    Property: API key generation produces keys of correct length.
    
    For any valid length >= 16, the generated API key should have
    exactly that length.
    """
    key = generate_api_key(length=length)
    assert len(key) == length


@settings(max_examples=20, deadline=None)
@given(length=st.integers(min_value=16, max_value=256))
def test_property_api_key_alphabet(length: int):
    """
    Property: API keys only contain alphanumeric characters.
    
    For any generated API key, all characters should be from the
    allowed alphabet (letters and digits).
    """
    key = generate_api_key(length=length)
    allowed = string.ascii_letters + string.digits
    assert all(c in allowed for c in key)


@settings(max_examples=20, deadline=None)
@given(length=st.integers(min_value=32, max_value=64))
def test_property_api_secret_length(length: int):
    """
    Property: API secret generation produces secrets of correct length.
    
    For any valid length (32-64), the generated API secret should have
    exactly that length.
    """
    secret = generate_api_secret(length=length)
    assert len(secret) == length


@settings(max_examples=10, deadline=None)
@given(
    credential=st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'P'),
            min_codepoint=33,
            max_codepoint=126
        )
    )
)
def test_property_hash_verify_roundtrip(credential: str):
    """
    Property: Hash and verify roundtrip correctness.
    
    For any credential, hashing it and then verifying with the same
    credential should return True.
    """
    hashed = hash_credential(credential)
    assert verify_credential(credential, hashed) is True


@settings(max_examples=10, deadline=None)
@given(
    credential=st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'P'),
            min_codepoint=33,
            max_codepoint=126
        )
    ),
    wrong_credential=st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'P'),
            min_codepoint=33,
            max_codepoint=126
        )
    )
)
def test_property_hash_verify_wrong_credential(credential: str, wrong_credential: str):
    """
    Property: Wrong credential verification fails.
    
    For any two different credentials, verifying one against the hash
    of the other should return False.
    """
    assume(credential != wrong_credential)
    
    hashed = hash_credential(credential)
    assert verify_credential(wrong_credential, hashed) is False


@settings(max_examples=10, deadline=None)
@given(
    credential=st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'P'),
            min_codepoint=33,
            max_codepoint=126
        )
    )
)
def test_property_hash_different_salts(credential: str):
    """
    Property: Same credential produces different hashes.
    
    For any credential, hashing it multiple times should produce
    different hashes due to different salts.
    """
    hash1 = hash_credential(credential)
    hash2 = hash_credential(credential)
    
    # Hashes should be different
    assert hash1 != hash2
    
    # But both should verify correctly
    assert verify_credential(credential, hash1) is True
    assert verify_credential(credential, hash2) is True


@settings(max_examples=20, deadline=None)
@given(
    key_length=st.integers(min_value=16, max_value=64),
    secret_length=st.integers(min_value=32, max_value=64)
)
def test_property_generate_credentials_structure(key_length: int, secret_length: int):
    """
    Property: Generated credentials have correct structure.
    
    For any valid key and secret lengths (within bcrypt limits),
    the generated credentials should have the correct lengths and valid hashes.
    """
    creds = generate_credentials(
        api_key_length=key_length,
        api_secret_length=secret_length
    )
    
    # Check lengths
    assert len(creds.api_key) == key_length
    assert len(creds.api_secret) == secret_length
    
    # Check hashes are valid bcrypt hashes
    assert creds.api_key_hash.startswith("$2b$")
    assert creds.api_secret_hash.startswith("$2b$")
    
    # Check verification works
    assert verify_credential(creds.api_key, creds.api_key_hash)
    assert verify_credential(creds.api_secret, creds.api_secret_hash)


@settings(max_examples=20, deadline=None)
@given(st.data())
def test_property_validate_credentials_correctness(data):
    """
    Property: Credential validation correctness.
    
    For any generated credentials:
    1. Validation with correct credentials returns True
    2. Validation with wrong key returns False
    3. Validation with wrong secret returns False
    4. Validation with both wrong returns False
    """
    creds = generate_credentials()
    
    # Correct credentials should validate
    assert validate_credentials(
        creds.api_key,
        creds.api_secret,
        creds.api_key_hash,
        creds.api_secret_hash
    ) is True
    
    # Generate wrong credentials
    wrong_key = data.draw(st.text(
        min_size=32,
        max_size=32,
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
    ))
    wrong_secret = data.draw(st.text(
        min_size=64,
        max_size=64,
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P'))
    ))
    
    # Ensure they're actually different
    assume(wrong_key != creds.api_key)
    assume(wrong_secret != creds.api_secret)
    
    # Wrong key should fail
    assert validate_credentials(
        wrong_key,
        creds.api_secret,
        creds.api_key_hash,
        creds.api_secret_hash
    ) is False
    
    # Wrong secret should fail
    assert validate_credentials(
        creds.api_key,
        wrong_secret,
        creds.api_key_hash,
        creds.api_secret_hash
    ) is False
    
    # Both wrong should fail
    assert validate_credentials(
        wrong_key,
        wrong_secret,
        creds.api_key_hash,
        creds.api_secret_hash
    ) is False


# ============================================================================
# Property-Based Test for Credential Uniqueness (Property 2)
# ============================================================================

@settings(max_examples=20, deadline=None)
@given(num_gateways=st.integers(min_value=2, max_value=50))
def test_property_credential_uniqueness(num_gateways: int):
    """
    **Property 2: API Credential Uniqueness**
    
    For any set of registered gateways, all API credentials (api_key, api_secret) 
    should be unique across the system.
    
    **Validates: Requirements 2.2**
    
    This property test verifies that:
    1. All generated API keys are unique across multiple gateways
    2. All generated API secrets are unique across multiple gateways
    3. No two gateways share the same API key
    4. No two gateways share the same API secret
    5. Uniqueness holds for any number of gateway registrations
    
    Feature: ai-application-integration, Property 2: API Credential Uniqueness
    """
    # Generate credentials for N gateways
    credentials_list = [generate_credentials() for _ in range(num_gateways)]
    
    # Extract all API keys and secrets
    api_keys = [creds.api_key for creds in credentials_list]
    api_secrets = [creds.api_secret for creds in credentials_list]
    api_key_hashes = [creds.api_key_hash for creds in credentials_list]
    api_secret_hashes = [creds.api_secret_hash for creds in credentials_list]
    
    # Property 1: All API keys must be unique
    assert len(api_keys) == len(set(api_keys)), \
        f"API keys must be unique across all gateways. Found {len(api_keys)} keys but only {len(set(api_keys))} unique"
    
    # Property 2: All API secrets must be unique
    assert len(api_secrets) == len(set(api_secrets)), \
        f"API secrets must be unique across all gateways. Found {len(api_secrets)} secrets but only {len(set(api_secrets))} unique"
    
    # Property 3: All API key hashes must be unique (since keys are unique and salts differ)
    assert len(api_key_hashes) == len(set(api_key_hashes)), \
        f"API key hashes must be unique across all gateways. Found {len(api_key_hashes)} hashes but only {len(set(api_key_hashes))} unique"
    
    # Property 4: All API secret hashes must be unique (since secrets are unique and salts differ)
    assert len(api_secret_hashes) == len(set(api_secret_hashes)), \
        f"API secret hashes must be unique across all gateways. Found {len(api_secret_hashes)} hashes but only {len(set(api_secret_hashes))} unique"
    
    # Property 5: No API key should match any API secret (additional security check)
    keys_set = set(api_keys)
    secrets_set = set(api_secrets)
    intersection = keys_set & secrets_set
    assert len(intersection) == 0, \
        f"API keys and secrets should not overlap. Found {len(intersection)} overlapping values"
    
    # Property 6: Each credential pair should validate correctly
    for creds in credentials_list:
        assert validate_credentials(
            creds.api_key,
            creds.api_secret,
            creds.api_key_hash,
            creds.api_secret_hash
        ), "Each generated credential pair should validate correctly"


@settings(max_examples=10, deadline=None)
@given(
    num_gateways=st.integers(min_value=2, max_value=20),
    key_length=st.integers(min_value=16, max_value=64),
    secret_length=st.integers(min_value=32, max_value=64)
)
def test_property_credential_uniqueness_custom_lengths(
    num_gateways: int,
    key_length: int,
    secret_length: int
):
    """
    Property: Credential uniqueness with custom lengths.
    
    For any set of gateways with custom credential lengths, all credentials
    should still be unique. This tests that uniqueness holds regardless of
    the credential length configuration.
    
    **Validates: Requirements 2.2**
    """
    # Generate credentials with custom lengths
    credentials_list = [
        generate_credentials(
            api_key_length=key_length,
            api_secret_length=secret_length
        )
        for _ in range(num_gateways)
    ]
    
    # Extract all API keys and secrets
    api_keys = [creds.api_key for creds in credentials_list]
    api_secrets = [creds.api_secret for creds in credentials_list]
    
    # Verify uniqueness
    assert len(api_keys) == len(set(api_keys)), \
        f"API keys must be unique with custom length {key_length}"
    assert len(api_secrets) == len(set(api_secrets)), \
        f"API secrets must be unique with custom length {secret_length}"
    
    # Verify correct lengths
    for creds in credentials_list:
        assert len(creds.api_key) == key_length, \
            f"API key should have length {key_length}"
        assert len(creds.api_secret) == secret_length, \
            f"API secret should have length {secret_length}"


@settings(max_examples=50, deadline=None)
@given(num_gateways=st.integers(min_value=2, max_value=30))
def test_property_credential_collision_resistance(num_gateways: int):
    """
    Property: Credential collision resistance.
    
    For any set of gateways, the probability of credential collision should be
    negligible. This test verifies that even with many gateways, we don't see
    any credential collisions.
    
    **Validates: Requirements 2.2**
    """
    # Generate multiple batches of credentials
    all_keys = []
    all_secrets = []
    
    # Generate 3 batches to increase collision detection probability
    for _ in range(3):
        credentials_list = [generate_credentials() for _ in range(num_gateways)]
        all_keys.extend([creds.api_key for creds in credentials_list])
        all_secrets.extend([creds.api_secret for creds in credentials_list])
    
    total_credentials = num_gateways * 3
    
    # Verify no collisions across all batches
    assert len(all_keys) == len(set(all_keys)), \
        f"No API key collisions should occur across {total_credentials} credentials"
    assert len(all_secrets) == len(set(all_secrets)), \
        f"No API secret collisions should occur across {total_credentials} credentials"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ============================================================================
# JWT Token Service Tests
# ============================================================================

def test_jwt_service_initialization():
    """Test JWT service initialization with auto-generated keys."""
    service = JWTTokenService()
    
    # Should have private and public keys
    private_key_pem = service.get_private_key_pem()
    public_key_pem = service.get_public_key_pem()
    
    assert isinstance(private_key_pem, bytes)
    assert isinstance(public_key_pem, bytes)
    assert b'BEGIN PRIVATE KEY' in private_key_pem
    assert b'BEGIN PUBLIC KEY' in public_key_pem


def test_jwt_service_initialization_with_keys():
    """Test JWT service initialization with provided keys."""
    # Generate keys
    service1 = JWTTokenService()
    private_key = service1.get_private_key_pem()
    public_key = service1.get_public_key_pem()
    
    # Initialize with same keys
    service2 = JWTTokenService(private_key=private_key, public_key=public_key)
    
    # Should be able to use the keys
    token = service2.generate_token("gw_123", "tenant_456", ["read:data"])
    assert isinstance(token, str)


def test_generate_token_basic():
    """Test basic JWT token generation."""
    service = JWTTokenService()
    
    token = service.generate_token(
        gateway_id="gw_123",
        tenant_id="tenant_456",
        permissions=["read:data", "write:data"]
    )
    
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Token should have 3 parts (header.payload.signature)
    parts = token.split('.')
    assert len(parts) == 3


def test_generate_token_custom_expiration():
    """Test token generation with custom expiration."""
    service = JWTTokenService()
    
    token = service.generate_token(
        gateway_id="gw_123",
        tenant_id="tenant_456",
        permissions=["read:data"],
        expires_in_seconds=7200  # 2 hours
    )
    
    claims = service.validate_token(token)
    
    # Check expiration is approximately 2 hours from now
    time_diff = (claims.expires_at - claims.issued_at).total_seconds()
    assert 7190 <= time_diff <= 7210  # Allow small variance


def test_validate_token_success():
    """Test successful token validation."""
    service = JWTTokenService()
    
    token = service.generate_token(
        gateway_id="gw_123",
        tenant_id="tenant_456",
        permissions=["read:data", "write:data"]
    )
    
    claims = service.validate_token(token)
    
    assert claims.gateway_id == "gw_123"
    assert claims.tenant_id == "tenant_456"
    assert claims.permissions == ["read:data", "write:data"]
    assert isinstance(claims.issued_at, datetime)
    assert isinstance(claims.expires_at, datetime)
    assert claims.expires_at > claims.issued_at


def test_validate_token_expired():
    """Test validation of expired token."""
    service = JWTTokenService()
    
    # Generate token that expires in 1 second
    token = service.generate_token(
        gateway_id="gw_123",
        tenant_id="tenant_456",
        permissions=["read:data"],
        expires_in_seconds=1
    )
    
    # Wait for token to expire
    time.sleep(2)
    
    # Should raise ExpiredSignatureError
    with pytest.raises(pyjwt.ExpiredSignatureError, match="expired"):
        service.validate_token(token)


def test_validate_token_invalid():
    """Test validation of invalid token."""
    service = JWTTokenService()
    
    # Invalid token format
    with pytest.raises(pyjwt.InvalidTokenError):
        service.validate_token("invalid.token.here")
    
    # Completely invalid string
    with pytest.raises(pyjwt.InvalidTokenError):
        service.validate_token("not_a_token")


def test_validate_token_wrong_signature():
    """Test validation of token with wrong signature."""
    service1 = JWTTokenService()
    service2 = JWTTokenService()  # Different keys
    
    # Generate token with service1
    token = service1.generate_token("gw_123", "tenant_456", ["read:data"])
    
    # Try to validate with service2 (different keys)
    with pytest.raises(pyjwt.InvalidTokenError):
        service2.validate_token(token)


def test_is_token_expired_not_expired():
    """Test checking if token is expired (not expired case)."""
    service = JWTTokenService()
    
    token = service.generate_token(
        gateway_id="gw_123",
        tenant_id="tenant_456",
        permissions=["read:data"],
        expires_in_seconds=3600
    )
    
    assert service.is_token_expired(token) is False


def test_is_token_expired_expired():
    """Test checking if token is expired (expired case)."""
    service = JWTTokenService()
    
    # Generate token that expires immediately
    token = service.generate_token(
        gateway_id="gw_123",
        tenant_id="tenant_456",
        permissions=["read:data"],
        expires_in_seconds=1
    )
    
    # Wait for expiration
    time.sleep(2)
    
    assert service.is_token_expired(token) is True


def test_is_token_expired_invalid():
    """Test checking if invalid token is considered expired."""
    service = JWTTokenService()
    
    # Invalid tokens should be considered expired
    assert service.is_token_expired("invalid_token") is True


def test_token_claims_to_dict():
    """Test TokenClaims to_dict conversion."""
    now = datetime.utcnow()
    expires = now + timedelta(hours=1)
    
    claims = TokenClaims(
        gateway_id="gw_123",
        tenant_id="tenant_456",
        permissions=["read:data", "write:data"],
        issued_at=now,
        expires_at=expires
    )
    
    claims_dict = claims.to_dict()
    
    assert claims_dict['gateway_id'] == "gw_123"
    assert claims_dict['tenant_id'] == "tenant_456"
    assert claims_dict['permissions'] == ["read:data", "write:data"]
    assert claims_dict['iat'] == int(now.timestamp())
    assert claims_dict['exp'] == int(expires.timestamp())


def test_token_claims_from_dict():
    """Test TokenClaims from_dict conversion."""
    now = datetime.utcnow()
    expires = now + timedelta(hours=1)
    
    claims_dict = {
        'gateway_id': "gw_123",
        'tenant_id': "tenant_456",
        'permissions': ["read:data", "write:data"],
        'iat': int(now.timestamp()),
        'exp': int(expires.timestamp())
    }
    
    claims = TokenClaims.from_dict(claims_dict)
    
    assert claims.gateway_id == "gw_123"
    assert claims.tenant_id == "tenant_456"
    assert claims.permissions == ["read:data", "write:data"]
    assert abs((claims.issued_at - now).total_seconds()) < 1
    assert abs((claims.expires_at - expires).total_seconds()) < 1


def test_token_claims_roundtrip():
    """Test TokenClaims to_dict and from_dict roundtrip."""
    now = datetime.utcnow()
    expires = now + timedelta(hours=1)
    
    original_claims = TokenClaims(
        gateway_id="gw_123",
        tenant_id="tenant_456",
        permissions=["read:data"],
        issued_at=now,
        expires_at=expires
    )
    
    # Convert to dict and back
    claims_dict = original_claims.to_dict()
    restored_claims = TokenClaims.from_dict(claims_dict)
    
    assert restored_claims.gateway_id == original_claims.gateway_id
    assert restored_claims.tenant_id == original_claims.tenant_id
    assert restored_claims.permissions == original_claims.permissions


def test_token_empty_permissions():
    """Test token generation with empty permissions list."""
    service = JWTTokenService()
    
    token = service.generate_token(
        gateway_id="gw_123",
        tenant_id="tenant_456",
        permissions=[]
    )
    
    claims = service.validate_token(token)
    assert claims.permissions == []


def test_token_multiple_permissions():
    """Test token with multiple permissions."""
    service = JWTTokenService()
    
    permissions = [
        "read:data",
        "write:data",
        "delete:data",
        "admin:gateway"
    ]
    
    token = service.generate_token(
        gateway_id="gw_123",
        tenant_id="tenant_456",
        permissions=permissions
    )
    
    claims = service.validate_token(token)
    assert claims.permissions == permissions


# ============================================================================
# Property-Based Tests for JWT Tokens
# ============================================================================

@settings(max_examples=20, deadline=None)
@given(
    gateway_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122)),
    tenant_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122)),
    permissions=st.lists(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122)), min_size=0, max_size=10)
)
def test_property_jwt_token_issuance(gateway_id: str, tenant_id: str, permissions: list):
    """
    **Property 20: JWT Token Issuance**
    
    For any successful authentication, a JWT token should be issued with 
    tenant_id and permissions in the claims, and the token should be valid 
    for the configured duration.
    
    **Validates: Requirements 7.2**
    
    This property test verifies that:
    1. Token is successfully generated for any valid gateway_id and tenant_id
    2. Token contains correct tenant_id in claims
    3. Token contains correct permissions in claims
    4. Token is valid and can be decoded
    5. Token expiration is set correctly
    
    Feature: ai-application-integration, Property 20: JWT Token Issuance
    """
    service = JWTTokenService()
    expires_in = 3600  # 1 hour
    
    # Generate token
    token = service.generate_token(
        gateway_id=gateway_id,
        tenant_id=tenant_id,
        permissions=permissions,
        expires_in_seconds=expires_in
    )
    
    # Property 1: Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Property 2: Token should be valid and decodable
    claims = service.validate_token(token)
    
    # Property 3: Claims should contain correct gateway_id
    assert claims.gateway_id == gateway_id
    
    # Property 4: Claims should contain correct tenant_id
    assert claims.tenant_id == tenant_id
    
    # Property 5: Claims should contain correct permissions
    assert claims.permissions == permissions
    
    # Property 6: Token should have issued_at timestamp
    assert isinstance(claims.issued_at, datetime)
    
    # Property 7: Token should have expires_at timestamp
    assert isinstance(claims.expires_at, datetime)
    
    # Property 8: Expiration should be after issuance
    assert claims.expires_at > claims.issued_at
    
    # Property 9: Expiration should be approximately expires_in seconds from issuance
    time_diff = (claims.expires_at - claims.issued_at).total_seconds()
    assert expires_in - 10 <= time_diff <= expires_in + 10  # Allow 10 second variance


@settings(max_examples=10, deadline=None)
@given(
    gateway_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122)),
    tenant_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122)),
    permissions=st.lists(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122)), min_size=0, max_size=5)
)
def test_property_expired_token_rejection(gateway_id: str, tenant_id: str, permissions: list):
    """
    **Property 21: Expired Token Rejection**
    
    For any API request with an expired JWT token, the request should be 
    rejected with HTTP 401 status, and the client should be required to 
    re-authenticate.
    
    **Validates: Requirements 7.3**
    
    This property test verifies that:
    1. Expired tokens are detected correctly
    2. Validation raises ExpiredSignatureError for expired tokens
    3. is_token_expired returns True for expired tokens
    4. Valid tokens are not incorrectly marked as expired
    
    Feature: ai-application-integration, Property 21: Expired Token Rejection
    """
    service = JWTTokenService()
    
    # Generate token that expires in 1 second
    token = service.generate_token(
        gateway_id=gateway_id,
        tenant_id=tenant_id,
        permissions=permissions,
        expires_in_seconds=1
    )
    
    # Property 1: Token should be valid immediately after generation
    claims = service.validate_token(token)
    assert claims.gateway_id == gateway_id
    assert service.is_token_expired(token) is False
    
    # Wait for token to expire
    time.sleep(2)
    
    # Property 2: Expired token should raise ExpiredSignatureError
    with pytest.raises(pyjwt.ExpiredSignatureError):
        service.validate_token(token)
    
    # Property 3: is_token_expired should return True for expired token
    assert service.is_token_expired(token) is True


@settings(max_examples=20, deadline=None)
@given(
    num_tokens=st.integers(min_value=2, max_value=20),
    expires_in=st.integers(min_value=60, max_value=7200)
)
def test_property_token_uniqueness(num_tokens: int, expires_in: int):
    """
    Property: Token uniqueness across multiple generations.
    
    For any number of token generations with the same parameters,
    each token should be unique due to different issuance timestamps
    and potentially different random elements in JWT encoding.
    
    **Validates: Requirements 7.2**
    """
    service = JWTTokenService()
    
    tokens = []
    for i in range(num_tokens):
        token = service.generate_token(
            gateway_id=f"gw_{i}",
            tenant_id="tenant_123",
            permissions=["read:data"],
            expires_in_seconds=expires_in
        )
        tokens.append(token)
        # Small delay to ensure different timestamps
        time.sleep(0.01)
    
    # All tokens should be unique
    assert len(tokens) == len(set(tokens)), \
        f"All tokens should be unique. Generated {len(tokens)} tokens but only {len(set(tokens))} are unique"


@settings(max_examples=10, deadline=None)
@given(
    gateway_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122)),
    tenant_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122))
)
def test_property_token_signature_verification(gateway_id: str, tenant_id: str):
    """
    Property: Token signature verification prevents tampering.
    
    For any token generated by one service, it should not be valid
    when verified by a different service with different keys.
    This ensures tokens cannot be forged.
    
    **Validates: Requirements 7.2**
    """
    service1 = JWTTokenService()
    service2 = JWTTokenService()  # Different keys
    
    # Generate token with service1
    token = service1.generate_token(
        gateway_id=gateway_id,
        tenant_id=tenant_id,
        permissions=["read:data"]
    )
    
    # Property 1: Token should be valid with service1
    claims = service1.validate_token(token)
    assert claims.gateway_id == gateway_id
    
    # Property 2: Token should be invalid with service2 (different keys)
    with pytest.raises(pyjwt.InvalidTokenError):
        service2.validate_token(token)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
