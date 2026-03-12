"""
Unit tests for APIKeyService.

Tests validate API key creation, validation, lifecycle management,
and security features including hashing and expiration.
"""

import pytest
import hashlib
from datetime import datetime, timedelta
from uuid import uuid4

from src.sync.gateway.api_key_service import (
    APIKeyService,
    APIKeyConfig,
    APIKeyResponse
)
from src.sync.models import APIKeyModel, APIKeyStatus
from src.database.connection import db_manager


@pytest.fixture
def db_session():
    """Create a test database session."""
    with db_manager.get_session() as session:
        yield session


@pytest.fixture
def api_key_service(db_session):
    """Create APIKeyService instance with test session."""
    return APIKeyService(session=db_session)


class TestAPIKeyCreation:
    """Test cases for API key creation."""
    
    def test_create_key_basic(self, api_key_service, db_session):
        """Test creating a basic API key."""
        # Arrange
        config = APIKeyConfig(
            name="Test API Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True, "augmented_data": True},
            description="Test key for integration"
        )
        
        # Act
        response = api_key_service.create_key(config)
        
        # Assert
        assert response.id is not None
        assert response.name == "Test API Key"
        assert response.key_prefix.startswith("sk_")
        assert len(response.key_prefix) == 16
        assert response.raw_key is not None
        assert response.raw_key.startswith("sk_")
        assert len(response.raw_key) == 67  # sk_ + 64 hex chars
        assert response.scopes == {"annotations": True, "augmented_data": True}
        assert response.status == APIKeyStatus.ACTIVE
        assert response.total_calls == 0
        
        # Verify in database
        db_key = db_session.query(APIKeyModel).filter_by(id=response.id).first()
        assert db_key is not None
        assert db_key.name == "Test API Key"
        assert db_key.key_prefix == response.key_prefix
        assert db_key.key_hash is not None
        assert len(db_key.key_hash) == 64  # SHA-256 hex
    
    def test_create_key_with_expiration(self, api_key_service, db_session):
        """Test creating an API key with expiration."""
        # Arrange
        config = APIKeyConfig(
            name="Expiring Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True},
            expires_in_days=30
        )
        
        # Act
        response = api_key_service.create_key(config)
        
        # Assert
        assert response.expires_at is not None
        expected_expiry = datetime.utcnow() + timedelta(days=30)
        # Allow 1 second tolerance
        assert abs((response.expires_at - expected_expiry).total_seconds()) < 1
    
    def test_create_key_with_custom_rate_limits(self, api_key_service, db_session):
        """Test creating an API key with custom rate limits."""
        # Arrange
        config = APIKeyConfig(
            name="Custom Rate Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True},
            rate_limit_per_minute=100,
            rate_limit_per_day=5000
        )
        
        # Act
        response = api_key_service.create_key(config)
        
        # Assert
        assert response.rate_limit_per_minute == 100
        assert response.rate_limit_per_day == 5000
    
    def test_create_key_default_rate_limits(self, api_key_service, db_session):
        """Test creating an API key with default rate limits."""
        # Arrange
        config = APIKeyConfig(
            name="Default Rate Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        
        # Act
        response = api_key_service.create_key(config)
        
        # Assert
        assert response.rate_limit_per_minute == 60
        assert response.rate_limit_per_day == 10000
    
    def test_create_key_invalid_name(self, api_key_service):
        """Test creating an API key with invalid name."""
        # Arrange
        config = APIKeyConfig(
            name="",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="API key name is required"):
            api_key_service.create_key(config)
    
    def test_create_key_invalid_tenant(self, api_key_service):
        """Test creating an API key with invalid tenant."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="",
            scopes={"annotations": True}
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="Tenant ID is required"):
            api_key_service.create_key(config)
    
    def test_create_key_no_scopes(self, api_key_service):
        """Test creating an API key without scopes."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={}
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="At least one scope is required"):
            api_key_service.create_key(config)
    
    def test_create_key_unique_keys(self, api_key_service, db_session):
        """Test that each created key is unique."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        
        # Act
        response1 = api_key_service.create_key(config)
        response2 = api_key_service.create_key(config)
        
        # Assert
        assert response1.raw_key != response2.raw_key
        assert response1.key_prefix != response2.key_prefix
        assert response1.id != response2.id


class TestAPIKeyValidation:
    """Test cases for API key validation."""
    
    def test_validate_key_success(self, api_key_service, db_session):
        """Test validating a valid API key."""
        # Arrange
        config = APIKeyConfig(
            name="Valid Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        raw_key = response.raw_key
        
        # Act
        validated_key = api_key_service.validate_key(raw_key)
        
        # Assert
        assert validated_key is not None
        assert validated_key.id == response.id
        assert validated_key.status == APIKeyStatus.ACTIVE
    
    def test_validate_key_invalid_format(self, api_key_service):
        """Test validating a key with invalid format."""
        # Act
        validated_key = api_key_service.validate_key("invalid_key")
        
        # Assert
        assert validated_key is None
    
    def test_validate_key_wrong_prefix(self, api_key_service):
        """Test validating a key with wrong prefix."""
        # Act
        validated_key = api_key_service.validate_key("pk_1234567890abcdef")
        
        # Assert
        assert validated_key is None
    
    def test_validate_key_not_found(self, api_key_service):
        """Test validating a non-existent key."""
        # Arrange
        fake_key = "sk_" + "a" * 64
        
        # Act
        validated_key = api_key_service.validate_key(fake_key)
        
        # Assert
        assert validated_key is None
    
    def test_validate_key_disabled(self, api_key_service, db_session):
        """Test validating a disabled key."""
        # Arrange
        config = APIKeyConfig(
            name="Disabled Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        raw_key = response.raw_key
        
        # Disable the key
        api_key_service.disable_key(response.id, "test_tenant_001")
        
        # Act
        validated_key = api_key_service.validate_key(raw_key)
        
        # Assert
        assert validated_key is None
    
    def test_validate_key_revoked(self, api_key_service, db_session):
        """Test validating a revoked key."""
        # Arrange
        config = APIKeyConfig(
            name="Revoked Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        raw_key = response.raw_key
        
        # Revoke the key
        api_key_service.revoke_key(response.id, "test_tenant_001")
        
        # Act
        validated_key = api_key_service.validate_key(raw_key)
        
        # Assert
        assert validated_key is None
    
    def test_validate_key_expired(self, api_key_service, db_session):
        """Test validating an expired key."""
        # Arrange
        config = APIKeyConfig(
            name="Expired Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True},
            expires_in_days=-1  # Already expired
        )
        response = api_key_service.create_key(config)
        raw_key = response.raw_key
        
        # Act
        validated_key = api_key_service.validate_key(raw_key)
        
        # Assert
        assert validated_key is None


class TestAPIKeyLifecycle:
    """Test cases for API key lifecycle management."""
    
    def test_disable_key_success(self, api_key_service, db_session):
        """Test disabling an active key."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        
        # Act
        result = api_key_service.disable_key(response.id, "test_tenant_001")
        
        # Assert
        assert result is True
        db_key = db_session.query(APIKeyModel).filter_by(id=response.id).first()
        assert db_key.status == APIKeyStatus.DISABLED
    
    def test_enable_key_success(self, api_key_service, db_session):
        """Test enabling a disabled key."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        api_key_service.disable_key(response.id, "test_tenant_001")
        
        # Act
        result = api_key_service.enable_key(response.id, "test_tenant_001")
        
        # Assert
        assert result is True
        db_key = db_session.query(APIKeyModel).filter_by(id=response.id).first()
        assert db_key.status == APIKeyStatus.ACTIVE
    
    def test_revoke_key_success(self, api_key_service, db_session):
        """Test revoking a key."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        
        # Act
        result = api_key_service.revoke_key(response.id, "test_tenant_001")
        
        # Assert
        assert result is True
        db_key = db_session.query(APIKeyModel).filter_by(id=response.id).first()
        assert db_key.status == APIKeyStatus.REVOKED
    
    def test_cannot_enable_revoked_key(self, api_key_service, db_session):
        """Test that revoked keys cannot be enabled."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        api_key_service.revoke_key(response.id, "test_tenant_001")
        
        # Act
        result = api_key_service.enable_key(response.id, "test_tenant_001")
        
        # Assert
        assert result is False
        db_key = db_session.query(APIKeyModel).filter_by(id=response.id).first()
        assert db_key.status == APIKeyStatus.REVOKED
    
    def test_cannot_disable_revoked_key(self, api_key_service, db_session):
        """Test that revoked keys cannot be disabled."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        api_key_service.revoke_key(response.id, "test_tenant_001")
        
        # Act
        result = api_key_service.disable_key(response.id, "test_tenant_001")
        
        # Assert
        assert result is False
        db_key = db_session.query(APIKeyModel).filter_by(id=response.id).first()
        assert db_key.status == APIKeyStatus.REVOKED
    
    def test_lifecycle_wrong_tenant(self, api_key_service, db_session):
        """Test that lifecycle operations fail with wrong tenant."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        
        # Act & Assert
        assert api_key_service.disable_key(response.id, "wrong_tenant") is False
        assert api_key_service.enable_key(response.id, "wrong_tenant") is False
        assert api_key_service.revoke_key(response.id, "wrong_tenant") is False


class TestAPIKeyRetrieval:
    """Test cases for API key retrieval."""
    
    def test_get_key_success(self, api_key_service, db_session):
        """Test retrieving an API key."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        created = api_key_service.create_key(config)
        
        # Act
        retrieved = api_key_service.get_key(created.id, "test_tenant_001")
        
        # Assert
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.key_prefix == created.key_prefix
        assert retrieved.raw_key is None  # Never returned after creation
    
    def test_get_key_not_found(self, api_key_service):
        """Test retrieving a non-existent key."""
        # Act
        retrieved = api_key_service.get_key(uuid4(), "test_tenant_001")
        
        # Assert
        assert retrieved is None
    
    def test_get_key_wrong_tenant(self, api_key_service, db_session):
        """Test retrieving a key with wrong tenant."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        created = api_key_service.create_key(config)
        
        # Act
        retrieved = api_key_service.get_key(created.id, "wrong_tenant")
        
        # Assert
        assert retrieved is None
    
    def test_list_keys_success(self, api_key_service, db_session):
        """Test listing API keys for a tenant."""
        # Arrange
        tenant_id = "test_tenant_001"
        for i in range(3):
            config = APIKeyConfig(
                name=f"Test Key {i}",
                tenant_id=tenant_id,
                scopes={"annotations": True}
            )
            api_key_service.create_key(config)
        
        # Act
        keys = api_key_service.list_keys(tenant_id)
        
        # Assert
        assert len(keys) == 3
        assert all(key.raw_key is None for key in keys)
        assert all(key.key_prefix.startswith("sk_") for key in keys)
    
    def test_list_keys_with_status_filter(self, api_key_service, db_session):
        """Test listing API keys with status filter."""
        # Arrange
        tenant_id = "test_tenant_001"
        keys_created = []
        for i in range(3):
            config = APIKeyConfig(
                name=f"Test Key {i}",
                tenant_id=tenant_id,
                scopes={"annotations": True}
            )
            keys_created.append(api_key_service.create_key(config))
        
        # Disable one key
        api_key_service.disable_key(keys_created[0].id, tenant_id)
        
        # Act
        active_keys = api_key_service.list_keys(tenant_id, APIKeyStatus.ACTIVE)
        disabled_keys = api_key_service.list_keys(tenant_id, APIKeyStatus.DISABLED)
        
        # Assert
        assert len(active_keys) == 2
        assert len(disabled_keys) == 1
    
    def test_list_keys_empty(self, api_key_service):
        """Test listing keys for tenant with no keys."""
        # Act
        keys = api_key_service.list_keys("empty_tenant")
        
        # Assert
        assert len(keys) == 0


class TestAPIKeyUsageTracking:
    """Test cases for API key usage tracking."""
    
    def test_update_usage_increment_calls(self, api_key_service, db_session):
        """Test updating usage with call increment."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        
        # Act
        result = api_key_service.update_usage(response.id, increment_calls=True)
        
        # Assert
        assert result is True
        db_key = db_session.query(APIKeyModel).filter_by(id=response.id).first()
        assert db_key.total_calls == 1
        assert db_key.last_used_at is not None
    
    def test_update_usage_multiple_calls(self, api_key_service, db_session):
        """Test updating usage multiple times."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        
        # Act
        for _ in range(5):
            api_key_service.update_usage(response.id, increment_calls=True)
        
        # Assert
        db_key = db_session.query(APIKeyModel).filter_by(id=response.id).first()
        assert db_key.total_calls == 5
    
    def test_update_usage_without_increment(self, api_key_service, db_session):
        """Test updating usage without incrementing calls."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        response = api_key_service.create_key(config)
        
        # Act
        result = api_key_service.update_usage(response.id, increment_calls=False)
        
        # Assert
        assert result is True
        db_key = db_session.query(APIKeyModel).filter_by(id=response.id).first()
        assert db_key.total_calls == 0
        assert db_key.last_used_at is not None


class TestAPIKeySecurity:
    """Test cases for API key security features."""
    
    def test_key_hash_stored_not_raw(self, api_key_service, db_session):
        """Test that only hash is stored, not raw key."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        
        # Act
        response = api_key_service.create_key(config)
        
        # Assert
        db_key = db_session.query(APIKeyModel).filter_by(id=response.id).first()
        assert db_key.key_hash != response.raw_key
        assert len(db_key.key_hash) == 64  # SHA-256 hex
        
        # Verify hash matches
        expected_hash = hashlib.sha256(response.raw_key.encode()).hexdigest()
        assert db_key.key_hash == expected_hash
    
    def test_key_prefix_identification(self, api_key_service, db_session):
        """Test that key prefix allows identification."""
        # Arrange
        config = APIKeyConfig(
            name="Test Key",
            tenant_id="test_tenant_001",
            scopes={"annotations": True}
        )
        
        # Act
        response = api_key_service.create_key(config)
        
        # Assert
        db_key = db_session.query(APIKeyModel).filter_by(id=response.id).first()
        assert response.raw_key.startswith(db_key.key_prefix)
        assert len(db_key.key_prefix) == 16
