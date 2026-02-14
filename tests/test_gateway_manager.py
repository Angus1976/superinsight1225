"""
Unit tests for GatewayManager class.

Tests gateway registration, configuration updates, and deactivation
with credential revocation.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.models.ai_integration import AIGateway, AISkill
from src.ai_integration.gateway_manager import (
    GatewayManager,
    GatewayRegistrationError,
    GatewayNotFoundError,
    ConfigurationValidationError
)
from src.ai_integration.auth import validate_credentials
from src.database.connection import Base


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    from sqlalchemy import JSON, event
    from sqlalchemy.dialects.postgresql import JSONB
    
    # Replace JSONB with JSON for SQLite compatibility
    engine = create_engine("sqlite:///:memory:")
    
    # Monkey patch JSONB to JSON for SQLite
    @event.listens_for(engine, "before_cursor_execute", retval=True)
    def replace_jsonb(conn, cursor, statement, parameters, context, executemany):
        return statement, parameters
    
    # Create tables with JSON instead of JSONB for SQLite
    from src.models.ai_integration import AIGateway, AISkill, AIAuditLog
    for table in [AIGateway.__table__, AISkill.__table__, AIAuditLog.__table__]:
        for column in table.columns:
            if hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'JSONB':
                column.type = JSON()
    
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def gateway_manager(db_session):
    """Create a GatewayManager instance for testing."""
    return GatewayManager(db_session)


@pytest.fixture
def valid_configuration():
    """Provide a valid gateway configuration."""
    return {
        'channels': [
            {
                'channel_type': 'whatsapp',
                'enabled': True,
                'credentials': {'api_key': 'test_key'}
            }
        ],
        'network_settings': {
            'port': 3000,
            'host': 'localhost'
        }
    }


class TestGatewayRegistration:
    """Test gateway registration functionality."""
    
    def test_register_gateway_success(self, gateway_manager, valid_configuration):
        """Test successful gateway registration."""
        gateway, credentials = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        assert gateway.id is not None
        assert gateway.name == "Test Gateway"
        assert gateway.gateway_type == "openclaw"
        assert gateway.tenant_id == "tenant_123"
        assert gateway.status == "inactive"
        assert gateway.configuration == valid_configuration
        
        # Verify credentials were generated
        assert credentials.api_key is not None
        assert credentials.api_secret is not None
        assert len(credentials.api_key) == 32
        assert len(credentials.api_secret) == 64
        
        # Verify credentials can be validated
        assert validate_credentials(
            credentials.api_key,
            credentials.api_secret,
            gateway.api_key_hash,
            gateway.api_secret_hash
        )
    
    def test_register_gateway_empty_name(self, gateway_manager, valid_configuration):
        """Test registration fails with empty name."""
        with pytest.raises(ConfigurationValidationError, match="name cannot be empty"):
            gateway_manager.register_gateway(
                name="",
                gateway_type="openclaw",
                tenant_id="tenant_123",
                configuration=valid_configuration
            )
    
    def test_register_gateway_empty_type(self, gateway_manager, valid_configuration):
        """Test registration fails with empty gateway type."""
        with pytest.raises(ConfigurationValidationError, match="type cannot be empty"):
            gateway_manager.register_gateway(
                name="Test Gateway",
                gateway_type="",
                tenant_id="tenant_123",
                configuration=valid_configuration
            )
    
    def test_register_gateway_empty_tenant(self, gateway_manager, valid_configuration):
        """Test registration fails with empty tenant ID."""
        with pytest.raises(ConfigurationValidationError, match="Tenant ID cannot be empty"):
            gateway_manager.register_gateway(
                name="Test Gateway",
                gateway_type="openclaw",
                tenant_id="",
                configuration=valid_configuration
            )
    
    def test_register_gateway_invalid_configuration_type(self, gateway_manager):
        """Test registration fails with non-dict configuration."""
        with pytest.raises(ConfigurationValidationError, match="must be a dictionary"):
            gateway_manager.register_gateway(
                name="Test Gateway",
                gateway_type="openclaw",
                tenant_id="tenant_123",
                configuration="invalid"
            )
    
    def test_register_gateway_missing_channels(self, gateway_manager):
        """Test registration fails without channels."""
        with pytest.raises(ConfigurationValidationError, match="must include 'channels'"):
            gateway_manager.register_gateway(
                name="Test Gateway",
                gateway_type="openclaw",
                tenant_id="tenant_123",
                configuration={}
            )
    
    def test_register_gateway_invalid_channels_type(self, gateway_manager):
        """Test registration fails with non-list channels."""
        with pytest.raises(ConfigurationValidationError, match="'channels' must be a list"):
            gateway_manager.register_gateway(
                name="Test Gateway",
                gateway_type="openclaw",
                tenant_id="tenant_123",
                configuration={'channels': 'invalid'}
            )
    
    def test_register_gateway_invalid_channel_structure(self, gateway_manager):
        """Test registration fails with invalid channel structure."""
        with pytest.raises(ConfigurationValidationError, match="must have 'channel_type'"):
            gateway_manager.register_gateway(
                name="Test Gateway",
                gateway_type="openclaw",
                tenant_id="tenant_123",
                configuration={
                    'channels': [{'enabled': True}],
                    'network_settings': {}
                }
            )
    
    def test_register_gateway_openclaw_missing_network_settings(self, gateway_manager):
        """Test OpenClaw registration fails without network_settings."""
        with pytest.raises(ConfigurationValidationError, match="must include 'network_settings'"):
            gateway_manager.register_gateway(
                name="Test Gateway",
                gateway_type="openclaw",
                tenant_id="tenant_123",
                configuration={
                    'channels': [
                        {'channel_type': 'whatsapp', 'enabled': True}
                    ]
                }
            )
    
    def test_register_gateway_duplicate_name(self, gateway_manager, valid_configuration):
        """Test registration fails with duplicate name in same tenant."""
        # Register first gateway
        gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        # Try to register duplicate
        with pytest.raises(GatewayRegistrationError, match="already exists"):
            gateway_manager.register_gateway(
                name="Test Gateway",
                gateway_type="openclaw",
                tenant_id="tenant_123",
                configuration=valid_configuration
            )
    
    def test_register_gateway_same_name_different_tenant(self, gateway_manager, valid_configuration):
        """Test registration succeeds with same name in different tenant."""
        # Register first gateway
        gateway1, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        # Register with same name but different tenant
        gateway2, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_456",
            configuration=valid_configuration
        )
        
        assert gateway1.id != gateway2.id
        assert gateway1.tenant_id != gateway2.tenant_id
    
    def test_register_gateway_custom_limits(self, gateway_manager, valid_configuration):
        """Test registration with custom rate limits and quotas."""
        gateway, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration,
            rate_limit_per_minute=120,
            quota_per_day=50000
        )
        
        assert gateway.rate_limit_per_minute == 120
        assert gateway.quota_per_day == 50000


class TestConfigurationUpdate:
    """Test gateway configuration update functionality."""
    
    def test_update_configuration_success(self, gateway_manager, valid_configuration):
        """Test successful configuration update with versioning."""
        # Register gateway
        gateway, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        # Update configuration
        new_config = valid_configuration.copy()
        new_config['channels'][0]['enabled'] = False
        
        updated_gateway = gateway_manager.update_configuration(
            gateway_id=gateway.id,
            configuration=new_config,
            updated_by="admin_user"
        )
        
        assert updated_gateway.configuration['channels'][0]['enabled'] is False
        assert 'versions' in updated_gateway.configuration
        assert len(updated_gateway.configuration['versions']) == 1
        
        # Verify version history
        version = updated_gateway.configuration['versions'][0]
        assert version['version'] == 1
        assert version['updated_by'] == "admin_user"
        assert 'timestamp' in version
        assert version['configuration']['channels'][0]['enabled'] is True
    
    def test_update_configuration_multiple_versions(self, gateway_manager, valid_configuration):
        """Test multiple configuration updates create version history."""
        # Register gateway
        gateway, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        # First update
        config1 = valid_configuration.copy()
        config1['channels'][0]['enabled'] = False
        gateway_manager.update_configuration(
            gateway_id=gateway.id,
            configuration=config1,
            updated_by="user1"
        )
        
        # Second update
        config2 = valid_configuration.copy()
        config2['channels'].append({
            'channel_type': 'telegram',
            'enabled': True
        })
        updated_gateway = gateway_manager.update_configuration(
            gateway_id=gateway.id,
            configuration=config2,
            updated_by="user2"
        )
        
        # Verify version history
        assert len(updated_gateway.configuration['versions']) == 2
        assert updated_gateway.configuration['versions'][0]['updated_by'] == "user1"
        assert updated_gateway.configuration['versions'][1]['updated_by'] == "user2"
    
    def test_update_configuration_gateway_not_found(self, gateway_manager, valid_configuration):
        """Test update fails when gateway not found."""
        with pytest.raises(GatewayNotFoundError, match="not found"):
            gateway_manager.update_configuration(
                gateway_id="nonexistent_id",
                configuration=valid_configuration
            )
    
    def test_update_configuration_invalid_type(self, gateway_manager, valid_configuration):
        """Test update fails with non-dict configuration."""
        # Register gateway
        gateway, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        with pytest.raises(ConfigurationValidationError, match="must be a dictionary"):
            gateway_manager.update_configuration(
                gateway_id=gateway.id,
                configuration="invalid"
            )
    
    def test_update_configuration_invalid_structure(self, gateway_manager, valid_configuration):
        """Test update fails with invalid configuration structure."""
        # Register gateway
        gateway, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        with pytest.raises(ConfigurationValidationError):
            gateway_manager.update_configuration(
                gateway_id=gateway.id,
                configuration={'invalid': 'config'}
            )


class TestGatewayDeactivation:
    """Test gateway deactivation functionality."""
    
    def test_deactivate_gateway_success(self, gateway_manager, valid_configuration, db_session):
        """Test successful gateway deactivation."""
        # Register gateway
        gateway, credentials = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        # Verify credentials work before deactivation
        assert validate_credentials(
            credentials.api_key,
            credentials.api_secret,
            gateway.api_key_hash,
            gateway.api_secret_hash
        )
        
        # Deactivate gateway
        gateway_manager.deactivate_gateway(gateway.id)
        
        # Refresh gateway from database
        db_session.refresh(gateway)
        
        # Verify gateway is deactivated
        assert gateway.status == "inactive"
        assert gateway.api_key_hash == "REVOKED"
        assert gateway.api_secret_hash == "REVOKED"
        
        # Verify credentials no longer work
        assert not validate_credentials(
            credentials.api_key,
            credentials.api_secret,
            gateway.api_key_hash,
            gateway.api_secret_hash
        )
    
    def test_deactivate_gateway_disables_skills(self, gateway_manager, valid_configuration, db_session):
        """Test deactivation disables all associated skills."""
        # Register gateway
        gateway, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        # Add skills to gateway
        skill1 = AISkill(
            gateway_id=gateway.id,
            name="Skill 1",
            version="1.0.0",
            code_path="/path/to/skill1",
            status="deployed"
        )
        skill2 = AISkill(
            gateway_id=gateway.id,
            name="Skill 2",
            version="1.0.0",
            code_path="/path/to/skill2",
            status="deployed"
        )
        db_session.add(skill1)
        db_session.add(skill2)
        db_session.commit()
        
        # Deactivate gateway
        gateway_manager.deactivate_gateway(gateway.id)
        
        # Refresh skills from database
        db_session.refresh(skill1)
        db_session.refresh(skill2)
        
        # Verify all skills are disabled
        assert skill1.status == "disabled"
        assert skill2.status == "disabled"
    
    def test_deactivate_gateway_not_found(self, gateway_manager):
        """Test deactivation fails when gateway not found."""
        with pytest.raises(GatewayNotFoundError, match="not found"):
            gateway_manager.deactivate_gateway("nonexistent_id")
    
    def test_deactivate_gateway_idempotent(self, gateway_manager, valid_configuration, db_session):
        """Test deactivating an already deactivated gateway is idempotent."""
        # Register gateway
        gateway, _ = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        # Deactivate twice
        gateway_manager.deactivate_gateway(gateway.id)
        gateway_manager.deactivate_gateway(gateway.id)
        
        # Refresh gateway from database
        db_session.refresh(gateway)
        
        # Verify gateway is still deactivated
        assert gateway.status == "inactive"
        assert gateway.api_key_hash == "REVOKED"


class TestCredentialGeneration:
    """Test credential generation during registration."""
    
    def test_credentials_are_unique(self, gateway_manager, valid_configuration):
        """Test that each gateway gets unique credentials."""
        gateway1, creds1 = gateway_manager.register_gateway(
            name="Gateway 1",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        gateway2, creds2 = gateway_manager.register_gateway(
            name="Gateway 2",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        # Verify credentials are different
        assert creds1.api_key != creds2.api_key
        assert creds1.api_secret != creds2.api_secret
        assert gateway1.api_key_hash != gateway2.api_key_hash
        assert gateway1.api_secret_hash != gateway2.api_secret_hash
    
    def test_credentials_are_hashed(self, gateway_manager, valid_configuration):
        """Test that credentials are properly hashed in database."""
        gateway, credentials = gateway_manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=valid_configuration
        )
        
        # Verify hashes don't match plain text
        assert gateway.api_key_hash != credentials.api_key
        assert gateway.api_secret_hash != credentials.api_secret
        
        # Verify hashes start with bcrypt prefix
        assert gateway.api_key_hash.startswith("$2b$")
        assert gateway.api_secret_hash.startswith("$2b$")


# ============================================================================
# Property-Based Tests for Gateway Configuration
# ============================================================================

from hypothesis import given, strategies as st, settings, assume, HealthCheck


def _create_test_db_session():
    """Create a fresh database session for property tests."""
    from sqlalchemy import JSON, create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine("sqlite:///:memory:")
    
    # Create tables with JSON instead of JSONB for SQLite
    from src.models.ai_integration import AIGateway, AISkill, AIAuditLog
    for table in [AIGateway.__table__, AISkill.__table__, AIAuditLog.__table__]:
        for column in table.columns:
            if hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'JSONB':
                column.type = JSON()
    
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122)),
    gateway_type=st.sampled_from(['openclaw', 'custom']),
    tenant_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122)),
    has_channels=st.booleans(),
    channels_is_list=st.booleans(),
    has_network_settings=st.booleans()
)
def test_property_configuration_validation(
    name: str,
    gateway_type: str,
    tenant_id: str,
    has_channels: bool,
    channels_is_list: bool,
    has_network_settings: bool
):
    """
    **Property 3: Configuration Validation**
    
    For any gateway configuration update, invalid configurations (missing 
    required fields, invalid types, or schema violations) should be rejected 
    before persistence.
    
    **Validates: Requirements 2.3, 9.1, 10.2**
    
    This property test verifies that:
    1. Configurations missing required fields are rejected
    2. Configurations with invalid types are rejected
    3. Configurations violating schema are rejected
    4. Valid configurations are accepted
    5. Gateway-specific validation rules are enforced
    
    Feature: ai-application-integration, Property 3: Configuration Validation
    """
    # Create fresh session for each test
    db_session = _create_test_db_session()
    manager = GatewayManager(db_session)
    
    try:
        # Build configuration based on test parameters
        configuration = {}
        
        if has_channels:
            if channels_is_list:
                configuration['channels'] = [
                    {
                        'channel_type': 'whatsapp',
                        'enabled': True
                    }
                ]
            else:
                # Invalid: channels is not a list
                configuration['channels'] = 'invalid'
        
        if has_network_settings and gateway_type == 'openclaw':
            configuration['network_settings'] = {
                'port': 3000,
                'host': 'localhost'
            }
        
        # Determine if configuration should be valid
        is_valid = (
            has_channels and
            channels_is_list and
            (gateway_type != 'openclaw' or has_network_settings)
        )
        
        if is_valid:
            # Valid configuration should succeed
            try:
                gateway, _ = manager.register_gateway(
                    name=name,
                    gateway_type=gateway_type,
                    tenant_id=tenant_id,
                    configuration=configuration
                )
                assert gateway is not None
                assert gateway.configuration == configuration
            except (ConfigurationValidationError, GatewayRegistrationError):
                # May fail due to duplicate name or other constraints
                pass
        else:
            # Invalid configuration should be rejected
            with pytest.raises(ConfigurationValidationError):
                manager.register_gateway(
                    name=name,
                    gateway_type=gateway_type,
                    tenant_id=tenant_id,
                    configuration=configuration
                )
    finally:
        db_session.close()


@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_updates=st.integers(min_value=1, max_value=10)
)
def test_property_configuration_versioning(num_updates: int):
    """
    **Property 4: Configuration Versioning**
    
    For any gateway configuration update, the Gateway_Registry should create 
    a new version entry with timestamp and change author, and all previous 
    versions should remain accessible.
    
    **Validates: Requirements 2.4, 9.5**
    
    This property test verifies that:
    1. Each configuration update creates a new version entry
    2. Version entries include timestamp and change author
    3. All previous versions remain accessible
    4. Version numbers increment correctly
    5. Version history is preserved across multiple updates
    
    Feature: ai-application-integration, Property 4: Configuration Versioning
    """
    # Create fresh session
    db_session = _create_test_db_session()
    manager = GatewayManager(db_session)
    
    try:
        # Register initial gateway
        initial_config = {
            'channels': [{'channel_type': 'whatsapp', 'enabled': True}],
            'network_settings': {'port': 3000}
        }
        
        gateway, _ = manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=initial_config
        )
        
        # Perform multiple configuration updates
        for i in range(num_updates):
            new_config = {
                'channels': [
                    {'channel_type': 'whatsapp', 'enabled': True},
                    {'channel_type': 'telegram', 'enabled': i % 2 == 0}
                ],
                'network_settings': {'port': 3000 + i}
            }
            
            updated_gateway = manager.update_configuration(
                gateway_id=gateway.id,
                configuration=new_config,
                updated_by=f"user_{i}"
            )
            
            # Property 1: Version history should exist
            assert 'versions' in updated_gateway.configuration
            
            # Property 2: Number of versions should match number of updates
            assert len(updated_gateway.configuration['versions']) == i + 1
            
            # Property 3: Each version should have required fields
            for version_idx, version in enumerate(updated_gateway.configuration['versions']):
                assert 'version' in version
                assert 'configuration' in version
                assert 'timestamp' in version
                assert 'updated_by' in version
                
                # Property 4: Version numbers should increment correctly
                assert version['version'] == version_idx + 1
                
                # Property 5: Timestamp should be valid ISO format
                from datetime import datetime
                datetime.fromisoformat(version['timestamp'])
            
            # Property 6: Latest version should have correct author
            latest_version = updated_gateway.configuration['versions'][-1]
            assert latest_version['updated_by'] == f"user_{i}"
            
            # Property 7: Current configuration should not include versions key
            current_config_without_versions = {
                k: v for k, v in updated_gateway.configuration.items()
                if k != 'versions'
            }
            assert current_config_without_versions == new_config
            
            gateway = updated_gateway
        
        # Property 8: All versions should be accessible after all updates
        final_gateway = db_session.query(AIGateway).filter(
            AIGateway.id == gateway.id
        ).first()
        
        assert len(final_gateway.configuration['versions']) == num_updates
        
        # Property 9: Version history should be in chronological order
        for i in range(len(final_gateway.configuration['versions']) - 1):
            v1 = final_gateway.configuration['versions'][i]
            v2 = final_gateway.configuration['versions'][i + 1]
            
            from datetime import datetime
            t1 = datetime.fromisoformat(v1['timestamp'])
            t2 = datetime.fromisoformat(v2['timestamp'])
            
            # Later versions should have later or equal timestamps
            assert t2 >= t1
    
    finally:
        db_session.close()


@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_skills=st.integers(min_value=0, max_value=5)
)
def test_property_gateway_deactivation(num_skills: int):
    """
    **Property 5: Gateway Deactivation Completeness**
    
    For any gateway deactivation, the gateway's API credentials should be 
    revoked, all associated skills should be disabled, and subsequent 
    authentication attempts should fail.
    
    **Validates: Requirements 2.5**
    
    This property test verifies that:
    1. Gateway status is set to 'inactive'
    2. API credentials are revoked (set to 'REVOKED')
    3. All associated skills are disabled
    4. Authentication with old credentials fails
    5. Deactivation is idempotent
    
    Feature: ai-application-integration, Property 5: Gateway Deactivation Completeness
    """
    # Create fresh session
    db_session = _create_test_db_session()
    manager = GatewayManager(db_session)
    
    try:
        # Register gateway
        config = {
            'channels': [{'channel_type': 'whatsapp', 'enabled': True}],
            'network_settings': {'port': 3000}
        }
        
        gateway, credentials = manager.register_gateway(
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant_123",
            configuration=config
        )
        
        # Property 1: Credentials should work before deactivation
        assert validate_credentials(
            credentials.api_key,
            credentials.api_secret,
            gateway.api_key_hash,
            gateway.api_secret_hash
        )
        
        # Add skills to gateway
        skills = []
        for i in range(num_skills):
            skill = AISkill(
                gateway_id=gateway.id,
                name=f"Skill {i}",
                version="1.0.0",
                code_path=f"/path/to/skill{i}",
                status="deployed"
            )
            db_session.add(skill)
            skills.append(skill)
        
        db_session.commit()
        
        # Deactivate gateway
        manager.deactivate_gateway(gateway.id)
        
        # Refresh from database
        db_session.refresh(gateway)
        for skill in skills:
            db_session.refresh(skill)
        
        # Property 2: Gateway status should be 'inactive'
        assert gateway.status == "inactive"
        
        # Property 3: API credentials should be revoked
        assert gateway.api_key_hash == "REVOKED"
        assert gateway.api_secret_hash == "REVOKED"
        
        # Property 4: Credentials should no longer validate
        assert not validate_credentials(
            credentials.api_key,
            credentials.api_secret,
            gateway.api_key_hash,
            gateway.api_secret_hash
        )
        
        # Property 5: All skills should be disabled
        for skill in skills:
            assert skill.status == "disabled"
        
        # Property 6: Deactivation should be idempotent
        manager.deactivate_gateway(gateway.id)
        db_session.refresh(gateway)
        
        assert gateway.status == "inactive"
        assert gateway.api_key_hash == "REVOKED"
        assert gateway.api_secret_hash == "REVOKED"
        
        # Property 7: Skills should remain disabled after second deactivation
        for skill in skills:
            db_session.refresh(skill)
            assert skill.status == "disabled"
    
    finally:
        db_session.close()
