"""
Tests for AI Integration models.

Tests the basic functionality of AIGateway, AISkill, and AIAuditLog models.
Includes property-based tests for gateway registration completeness.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any

from src.models.ai_integration import AIGateway, AISkill, AIAuditLog


def test_ai_gateway_creation():
    """Test AIGateway model creation."""
    gateway = AIGateway(
        id=str(uuid4()),
        name="Test Gateway",
        gateway_type="openclaw",
        tenant_id=str(uuid4()),
        status="active",
        configuration={"channels": ["whatsapp"]},
        api_key_hash="hashed_key",
        api_secret_hash="hashed_secret",
        rate_limit_per_minute=100,
        quota_per_day=50000
    )
    
    assert gateway.name == "Test Gateway"
    assert gateway.gateway_type == "openclaw"
    assert gateway.status == "active"
    assert gateway.configuration == {"channels": ["whatsapp"]}
    assert gateway.rate_limit_per_minute == 100
    assert gateway.quota_per_day == 50000


def test_ai_skill_creation():
    """Test AISkill model creation."""
    gateway_id = str(uuid4())
    skill = AISkill(
        id=str(uuid4()),
        gateway_id=gateway_id,
        name="SuperInsight Skill",
        version="1.0.0",
        code_path="/skills/superinsight",
        configuration={"timeout": 30},
        dependencies=["axios", "dotenv"],
        status="deployed"
    )
    
    assert skill.name == "SuperInsight Skill"
    assert skill.version == "1.0.0"
    assert skill.gateway_id == gateway_id
    assert skill.status == "deployed"
    assert skill.dependencies == ["axios", "dotenv"]


def test_ai_audit_log_creation():
    """Test AIAuditLog model creation."""
    gateway_id = str(uuid4())
    tenant_id = str(uuid4())
    
    audit_log = AIAuditLog(
        id=str(uuid4()),
        gateway_id=gateway_id,
        tenant_id=tenant_id,
        event_type="data_access",
        resource="/api/v1/data/query",
        action="GET",
        event_metadata={"query": "dataset_id=123"},
        user_identifier="user@example.com",
        channel="whatsapp",
        success=True,
        signature="hmac_signature_here"
    )
    
    assert audit_log.gateway_id == gateway_id
    assert audit_log.tenant_id == tenant_id
    assert audit_log.event_type == "data_access"
    assert audit_log.resource == "/api/v1/data/query"
    assert audit_log.action == "GET"
    assert audit_log.success is True
    assert audit_log.event_metadata == {"query": "dataset_id=123"}


def test_ai_gateway_default_values():
    """Test AIGateway accepts minimal required fields."""
    gateway = AIGateway(
        id=str(uuid4()),
        name="Default Gateway",
        gateway_type="custom",
        tenant_id=str(uuid4()),
        api_key_hash="hash1",
        api_secret_hash="hash2"
    )
    
    # Verify required fields are set
    assert gateway.name == "Default Gateway"
    assert gateway.gateway_type == "custom"
    assert gateway.api_key_hash == "hash1"
    assert gateway.api_secret_hash == "hash2"


def test_ai_skill_default_values():
    """Test AISkill accepts minimal required fields."""
    skill = AISkill(
        id=str(uuid4()),
        gateway_id=str(uuid4()),
        name="Test Skill",
        version="1.0.0",
        code_path="/skills/test"
    )
    
    # Verify required fields are set
    assert skill.name == "Test Skill"
    assert skill.version == "1.0.0"
    assert skill.code_path == "/skills/test"


def test_ai_audit_log_default_values():
    """Test AIAuditLog accepts minimal required fields."""
    audit_log = AIAuditLog(
        id=str(uuid4()),
        gateway_id=str(uuid4()),
        tenant_id=str(uuid4()),
        event_type="test_event",
        resource="/test",
        action="TEST",
        signature="sig"
    )
    
    # Verify required fields are set
    assert audit_log.event_type == "test_event"
    assert audit_log.resource == "/test"
    assert audit_log.action == "TEST"
    assert audit_log.signature == "sig"
    # Optional fields should be None
    assert audit_log.user_identifier is None
    assert audit_log.channel is None
    assert audit_log.error_message is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ============================================================================
# Property-Based Tests
# ============================================================================

# Strategy for generating valid gateway types
gateway_types = st.sampled_from(["openclaw", "custom", "langchain", "autogen"])

# Strategy for generating valid gateway status
gateway_statuses = st.sampled_from(["active", "inactive", "error", "pending"])

# Strategy for generating valid configuration dictionaries
@st.composite
def gateway_configuration(draw):
    """Generate valid gateway configuration."""
    channels = draw(st.lists(
        st.sampled_from(["whatsapp", "telegram", "slack", "discord", "wechat"]),
        min_size=0,
        max_size=5,
        unique=True
    ))
    
    config = {
        "channels": channels,
    }
    
    # Optionally add more configuration fields
    if draw(st.booleans()):
        config["timeout"] = draw(st.integers(min_value=10, max_value=300))
    
    if draw(st.booleans()):
        config["max_retries"] = draw(st.integers(min_value=1, max_value=10))
    
    if draw(st.booleans()):
        config["custom_settings"] = draw(st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
            st.text(min_size=1, max_size=50),
            min_size=0,
            max_size=5
        ))
    
    return config


@st.composite
def valid_gateway_data(draw):
    """Generate valid gateway registration data."""
    return {
        "id": str(uuid4()),
        "name": draw(st.text(min_size=1, max_size=255, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')))),
        "gateway_type": draw(gateway_types),
        "tenant_id": str(uuid4()),
        "status": draw(gateway_statuses),
        "configuration": draw(gateway_configuration()),
        "api_key_hash": draw(st.text(min_size=32, max_size=255, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        "api_secret_hash": draw(st.text(min_size=32, max_size=255, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        "rate_limit_per_minute": draw(st.integers(min_value=1, max_value=10000)),
        "quota_per_day": draw(st.integers(min_value=100, max_value=1000000)),
    }


@settings(max_examples=20, deadline=None)
@given(gateway_data=valid_gateway_data())
def test_property_gateway_registration_completeness(gateway_data: Dict[str, Any]):
    """
    **Property 1: Gateway Registration Completeness**
    
    For any gateway registration request with valid parameters, all required 
    metadata fields (name, type, version, channels, configuration, tenant_id) 
    should be stored in the Gateway_Registry and retrievable.
    
    **Validates: Requirements 2.1**
    
    This property test verifies that:
    1. All required fields are stored correctly
    2. All optional fields are stored correctly
    3. Configuration (including channels) is preserved
    4. All fields are retrievable after creation
    """
    # Create gateway with generated data
    gateway = AIGateway(**gateway_data)
    
    # Verify all required fields are stored and retrievable
    assert gateway.id == gateway_data["id"], "Gateway ID should match input"
    assert gateway.name == gateway_data["name"], "Gateway name should match input"
    assert gateway.gateway_type == gateway_data["gateway_type"], "Gateway type should match input"
    assert gateway.tenant_id == gateway_data["tenant_id"], "Tenant ID should match input"
    assert gateway.status == gateway_data["status"], "Gateway status should match input"
    
    # Verify configuration is stored correctly
    assert gateway.configuration == gateway_data["configuration"], "Configuration should match input"
    
    # Verify channels are stored in configuration
    if "channels" in gateway_data["configuration"]:
        assert "channels" in gateway.configuration, "Channels should be in configuration"
        assert gateway.configuration["channels"] == gateway_data["configuration"]["channels"], \
            "Channels should match input"
    
    # Verify credentials are stored
    assert gateway.api_key_hash == gateway_data["api_key_hash"], "API key hash should match input"
    assert gateway.api_secret_hash == gateway_data["api_secret_hash"], "API secret hash should match input"
    
    # Verify rate limits and quotas are stored
    assert gateway.rate_limit_per_minute == gateway_data["rate_limit_per_minute"], \
        "Rate limit should match input"
    assert gateway.quota_per_day == gateway_data["quota_per_day"], \
        "Quota should match input"
    
    # Verify all fields are non-null for required fields
    assert gateway.id is not None, "Gateway ID should not be None"
    assert gateway.name is not None, "Gateway name should not be None"
    assert gateway.gateway_type is not None, "Gateway type should not be None"
    assert gateway.tenant_id is not None, "Tenant ID should not be None"
    assert gateway.status is not None, "Gateway status should not be None"
    assert gateway.configuration is not None, "Configuration should not be None"
    assert gateway.api_key_hash is not None, "API key hash should not be None"
    assert gateway.api_secret_hash is not None, "API secret hash should not be None"
    assert gateway.rate_limit_per_minute is not None, "Rate limit should not be None"
    assert gateway.quota_per_day is not None, "Quota should not be None"


@settings(max_examples=10, deadline=None)
@given(
    gateway_data1=valid_gateway_data(),
    gateway_data2=valid_gateway_data()
)
def test_property_gateway_registration_independence(gateway_data1: Dict[str, Any], gateway_data2: Dict[str, Any]):
    """
    Property: Gateway Registration Independence
    
    For any two gateway registration requests with different IDs, the gateways
    should be stored independently without affecting each other.
    
    This property test verifies that:
    1. Multiple gateways can be created independently
    2. Each gateway maintains its own data
    3. Creating one gateway doesn't affect another
    """
    # Ensure different IDs
    assume(gateway_data1["id"] != gateway_data2["id"])
    
    # Create two gateways
    gateway1 = AIGateway(**gateway_data1)
    gateway2 = AIGateway(**gateway_data2)
    
    # Verify they are independent
    assert gateway1.id != gateway2.id, "Gateway IDs should be different"
    assert gateway1.name == gateway_data1["name"], "Gateway 1 name should match its input"
    assert gateway2.name == gateway_data2["name"], "Gateway 2 name should match its input"
    assert gateway1.tenant_id == gateway_data1["tenant_id"], "Gateway 1 tenant should match its input"
    assert gateway2.tenant_id == gateway_data2["tenant_id"], "Gateway 2 tenant should match its input"
    assert gateway1.configuration == gateway_data1["configuration"], "Gateway 1 config should match its input"
    assert gateway2.configuration == gateway_data2["configuration"], "Gateway 2 config should match its input"


@settings(max_examples=10, deadline=None)
@given(gateway_data=valid_gateway_data())
def test_property_gateway_configuration_preservation(gateway_data: Dict[str, Any]):
    """
    Property: Gateway Configuration Preservation
    
    For any gateway registration with configuration data, the configuration
    should be preserved exactly as provided, including nested structures.
    
    This property test verifies that:
    1. Configuration is stored as-is
    2. Nested structures are preserved
    3. All configuration keys and values are retrievable
    """
    gateway = AIGateway(**gateway_data)
    
    # Verify configuration is preserved exactly
    assert gateway.configuration == gateway_data["configuration"], \
        "Configuration should be preserved exactly"
    
    # Verify all configuration keys are present
    for key in gateway_data["configuration"].keys():
        assert key in gateway.configuration, f"Configuration key '{key}' should be present"
        assert gateway.configuration[key] == gateway_data["configuration"][key], \
            f"Configuration value for '{key}' should match input"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
