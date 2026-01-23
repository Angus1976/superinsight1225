"""
Property-based tests for LLM Audit Logging module.

Uses Hypothesis library for property testing with minimum 100 iterations per property.
Tests the correctness properties defined in the LLM Integration design document:
- Property 24: Log Sanitization
- Property 26: Configuration Audit Logging
"""

import pytest
import asyncio
import re
from typing import Dict, Any, List, Optional
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from uuid import uuid4
from datetime import datetime

from src.ai.llm.log_sanitizer import (
    LogSanitizer,
    SanitizationPattern,
    SanitizationResult,
    get_sanitizer,
    sanitize_log,
    sanitize_for_audit,
)
from src.ai.llm.audit_service import (
    LLMAuditService,
    LLMAuditEntry,
    LLMConfigAction,
    get_llm_audit_service,
)


# ==================== Custom Strategies ====================

# Strategy for OpenAI-style API keys
openai_api_key_strategy = st.builds(
    lambda suffix: f"sk-{suffix}",
    st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=24, max_size=48)
)

# Strategy for generic API keys
generic_api_key_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
    min_size=16,
    max_size=64
)


# Strategy for email addresses
email_strategy = st.builds(
    lambda local, domain, tld: f"{local}@{domain}.{tld}",
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789._", min_size=1, max_size=20).filter(lambda x: x and not x.startswith('.') and not x.endswith('.')),
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=2, max_size=15),
    st.sampled_from(["com", "org", "net", "io", "cn", "edu"])
)

# Strategy for US phone numbers
us_phone_strategy = st.builds(
    lambda area, exchange, subscriber: f"{area}-{exchange}-{subscriber}",
    st.text(alphabet="0123456789", min_size=3, max_size=3),
    st.text(alphabet="0123456789", min_size=3, max_size=3),
    st.text(alphabet="0123456789", min_size=4, max_size=4)
)

# Strategy for credit card numbers (test patterns only)
credit_card_strategy = st.one_of(
    # Visa-like pattern
    st.builds(lambda n: f"4{''.join(n)}", st.lists(st.sampled_from("0123456789"), min_size=15, max_size=15)),
    # Mastercard-like pattern
    st.builds(lambda n: f"5{''.join(['1','2','3','4','5'][hash(str(n)) % 5])}{''.join(n)}", st.lists(st.sampled_from("0123456789"), min_size=14, max_size=14)),
)

# Strategy for passwords - exclude quotes and backslashes to avoid JSON format issues
password_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+[]{}|;:,.<>?",
    min_size=4, 
    max_size=32
).filter(lambda x: x.strip() and ' ' not in x)

# Strategy for tenant IDs
tenant_id_strategy = st.builds(lambda: str(uuid4()))

# Strategy for user IDs
user_id_strategy = st.builds(lambda: str(uuid4()))

# Strategy for provider IDs
provider_id_strategy = st.builds(lambda: str(uuid4()))

# Strategy for LLM config actions
action_strategy = st.sampled_from(list(LLMConfigAction))

# Strategy for IP addresses
ip_address_strategy = st.builds(
    lambda a, b, c, d: f"{a}.{b}.{c}.{d}",
    st.integers(min_value=1, max_value=255),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=1, max_value=254)
)

# Strategy for user agents
user_agent_strategy = st.sampled_from([
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "PostmanRuntime/7.29.0",
    "curl/7.79.1",
])


# ==================== Property 24: Log Sanitization ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(api_key=openai_api_key_strategy)
def test_property_24_openai_api_key_sanitization(api_key: str):
    """
    Feature: llm-integration, Property 24: Log Sanitization
    
    For any log entry containing an OpenAI-style API key (sk-...), 
    the log should not contain the API key after sanitization.
    
    **Validates: Requirements 9.2**
    
    This test generates 100+ random OpenAI-style API keys and verifies
    that they are properly redacted from log entries.
    """
    sanitizer = LogSanitizer()
    
    # Create a log entry containing the API key
    log_entry = f"Making request with API key: {api_key}"
    
    # Sanitize the log entry
    result = sanitizer.sanitize_string(log_entry)
    
    # Verify the API key is not in the sanitized output
    assert api_key not in result.sanitized, \
        f"API key should be redacted from log: {result.sanitized}"
    
    # Verify a redaction marker is present
    assert "[REDACTED" in result.sanitized, \
        f"Redaction marker should be present: {result.sanitized}"
    
    # Verify patterns were matched
    assert len(result.patterns_matched) > 0, \
        "At least one pattern should be matched"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    key_name=st.sampled_from(["api_key", "apikey", "api-key", "API_KEY"]),
    key_value=generic_api_key_strategy
)
def test_property_24_generic_api_key_param_sanitization(key_name: str, key_value: str):
    """
    Feature: llm-integration, Property 24: Log Sanitization
    
    For any log entry containing an API key parameter (api_key=...), 
    the log should not contain the API key value after sanitization.
    
    **Validates: Requirements 9.2**
    """
    sanitizer = LogSanitizer()
    
    # Create log entries with various formats
    log_formats = [
        f"{key_name}={key_value}",
        f"{key_name}: {key_value}",
        f'"{key_name}": "{key_value}"',
    ]
    
    for log_entry in log_formats:
        result = sanitizer.sanitize_string(log_entry)
        
        # Verify the key value is not in the sanitized output
        assert key_value not in result.sanitized, \
            f"API key value should be redacted from: {log_entry}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(password=password_strategy)
def test_property_24_password_sanitization(password: str):
    """
    Feature: llm-integration, Property 24: Log Sanitization
    
    For any log entry containing a password field, the password value
    should not appear in the sanitized output.
    
    **Validates: Requirements 9.2**
    """
    sanitizer = LogSanitizer()
    
    # Create log entries with password
    log_formats = [
        f"password={password}",
        f"password: {password}",
        f'"password": "{password}"',
    ]
    
    for log_entry in log_formats:
        result = sanitizer.sanitize_string(log_entry)
        
        # Verify the password is not in the sanitized output
        assert password not in result.sanitized, \
            f"Password should be redacted from: {log_entry}"
        
        # Verify redaction marker is present
        assert "[REDACTED" in result.sanitized, \
            f"Redaction marker should be present: {result.sanitized}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(email=email_strategy)
def test_property_24_email_sanitization(email: str):
    """
    Feature: llm-integration, Property 24: Log Sanitization
    
    For any log entry containing an email address, the email should
    not appear in the sanitized output.
    
    **Validates: Requirements 9.2**
    """
    sanitizer = LogSanitizer()
    
    # Create a log entry containing the email
    log_entry = f"User email: {email}"
    
    # Sanitize the log entry
    result = sanitizer.sanitize_string(log_entry)
    
    # Verify the email is not in the sanitized output
    assert email not in result.sanitized, \
        f"Email should be redacted from log: {result.sanitized}"
    
    # Verify redaction marker is present
    assert "[REDACTED_EMAIL]" in result.sanitized, \
        f"Email redaction marker should be present: {result.sanitized}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(phone=us_phone_strategy)
def test_property_24_phone_sanitization(phone: str):
    """
    Feature: llm-integration, Property 24: Log Sanitization
    
    For any log entry containing a phone number, the phone number should
    not appear in the sanitized output.
    
    **Validates: Requirements 9.2**
    """
    sanitizer = LogSanitizer()
    
    # Create a log entry containing the phone number
    log_entry = f"Contact phone: {phone}"
    
    # Sanitize the log entry
    result = sanitizer.sanitize_string(log_entry)
    
    # Verify the phone number is not in the sanitized output
    assert phone not in result.sanitized, \
        f"Phone number should be redacted from log: {result.sanitized}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    sensitive_key=st.sampled_from([
        "api_key", "secret_key", "password", "token", "authorization",
        "openai_api_key", "azure_api_key", "qwen_api_key", "zhipu_api_key"
    ]),
    sensitive_value=generic_api_key_strategy
)
def test_property_24_dict_sensitive_key_sanitization(sensitive_key: str, sensitive_value: str):
    """
    Feature: llm-integration, Property 24: Log Sanitization
    
    For any dictionary log entry with sensitive keys (api_key, password, etc.),
    the sensitive values should not appear in the sanitized output.
    
    **Validates: Requirements 9.2**
    """
    sanitizer = LogSanitizer()
    
    # Create a dictionary with sensitive data
    log_dict = {
        "operation": "test",
        sensitive_key: sensitive_value,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Sanitize the dictionary
    result = sanitizer.sanitize_dict(log_dict)
    
    # Verify the sensitive value is not in the sanitized output
    assert sensitive_value not in str(result.sanitized), \
        f"Sensitive value should be redacted from dict"
    
    # Verify the key still exists but value is redacted
    assert sensitive_key in result.sanitized, \
        f"Key should still exist in sanitized dict"
    assert result.sanitized[sensitive_key] == "[REDACTED]", \
        f"Value should be redacted marker"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    api_key=openai_api_key_strategy,
    email=email_strategy,
    password=password_strategy
)
def test_property_24_multiple_sensitive_data_sanitization(
    api_key: str,
    email: str,
    password: str
):
    """
    Feature: llm-integration, Property 24: Log Sanitization
    
    For any log entry containing multiple types of sensitive data,
    all sensitive data should be redacted.
    
    **Validates: Requirements 9.2**
    """
    sanitizer = LogSanitizer()
    
    # Create a log entry with multiple sensitive items
    log_entry = f"User {email} with API key {api_key} and password={password}"
    
    # Sanitize the log entry
    result = sanitizer.sanitize_string(log_entry)
    
    # Verify none of the sensitive data is in the output
    assert api_key not in result.sanitized, "API key should be redacted"
    assert email not in result.sanitized, "Email should be redacted"
    assert password not in result.sanitized, "Password should be redacted"
    
    # Verify multiple patterns were matched
    assert result.redaction_count >= 3, \
        f"At least 3 redactions should occur, got {result.redaction_count}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    nested_key=generic_api_key_strategy,
    nested_email=email_strategy
)
def test_property_24_nested_dict_sanitization(nested_key: str, nested_email: str):
    """
    Feature: llm-integration, Property 24: Log Sanitization
    
    For any nested dictionary log entry, sensitive data at any depth
    should be redacted.
    
    **Validates: Requirements 9.2**
    """
    sanitizer = LogSanitizer()
    
    # Create a nested dictionary with sensitive data
    log_dict = {
        "operation": "test",
        "config": {
            "api_key": nested_key,
            "user": {
                "email": nested_email,
                "name": "Test User"
            }
        }
    }
    
    # Sanitize the dictionary
    result = sanitizer.sanitize_dict(log_dict, recursive=True)
    
    # Verify nested sensitive data is redacted
    assert nested_key not in str(result.sanitized), \
        "Nested API key should be redacted"
    
    # Verify the nested structure is preserved
    assert "config" in result.sanitized
    assert "api_key" in result.sanitized["config"]
    assert result.sanitized["config"]["api_key"] == "[REDACTED]"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    safe_text=st.text(min_size=1, max_size=100).filter(
        lambda x: not any(c in x for c in ['@', 'sk-', 'password', 'api_key'])
    )
)
def test_property_24_safe_data_preservation(safe_text: str):
    """
    Feature: llm-integration, Property 24: Log Sanitization
    
    For any log entry without sensitive data, the content should be
    preserved unchanged.
    
    **Validates: Requirements 9.2**
    """
    sanitizer = LogSanitizer()
    
    # Create a log entry without sensitive data
    log_entry = f"Normal log message: {safe_text}"
    
    # Sanitize the log entry
    result = sanitizer.sanitize_string(log_entry)
    
    # Verify the safe text is preserved
    assert safe_text in result.sanitized, \
        f"Safe text should be preserved: {result.sanitized}"
    
    # Verify no redactions occurred
    assert result.redaction_count == 0, \
        f"No redactions should occur for safe data"


# ==================== Property 26: Configuration Audit Logging ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    user_id=user_id_strategy,
    tenant_id=tenant_id_strategy,
    provider_id=provider_id_strategy,
    api_key=openai_api_key_strategy
)
def test_property_26_create_audit_logging(
    user_id: str,
    tenant_id: str,
    provider_id: str,
    api_key: str
):
    """
    Feature: llm-integration, Property 26: Configuration Audit Logging
    
    For any provider configuration create operation, an audit log entry
    should be created with user ID, timestamp, and change details.
    
    **Validates: Requirements 9.4**
    """
    audit_service = LLMAuditService()
    audit_service.clear_audit_logs()
    
    # Create a configuration
    config_data = {
        "name": "Test Provider",
        "type": "openai",
        "api_key": api_key,
        "model": "gpt-4"
    }
    
    # Log the creation using asyncio.run() for proper event loop handling
    entry = asyncio.run(
        audit_service.log_config_create(
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            config_data=config_data
        )
    )
    
    # Verify audit entry was created
    assert entry is not None, "Audit entry should be created"
    assert entry.action == LLMConfigAction.CREATE, "Action should be CREATE"
    assert entry.user_id == user_id, "User ID should match"
    assert entry.tenant_id == tenant_id, "Tenant ID should match"
    assert entry.provider_id == provider_id, "Provider ID should match"
    assert entry.timestamp is not None, "Timestamp should be set"
    
    # Verify change details are present
    assert "operation" in entry.change_details, "Operation should be in details"
    assert entry.change_details["operation"] == "create"
    
    # Verify API key is NOT in the audit log (sanitized)
    assert api_key not in str(entry.change_details), \
        "API key should be sanitized from audit log"
    
    # Verify the entry is in the audit logs
    logs = audit_service.get_audit_logs(tenant_id=tenant_id)
    assert len(logs) == 1, "One audit log should exist"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    user_id=user_id_strategy,
    tenant_id=tenant_id_strategy,
    provider_id=provider_id_strategy,
    old_api_key=openai_api_key_strategy,
    new_api_key=openai_api_key_strategy
)
def test_property_26_update_audit_logging(
    user_id: str,
    tenant_id: str,
    provider_id: str,
    old_api_key: str,
    new_api_key: str
):
    """
    Feature: llm-integration, Property 26: Configuration Audit Logging
    
    For any provider configuration update operation, an audit log entry
    should be created with user ID, timestamp, and change details showing
    what changed.
    
    **Validates: Requirements 9.4**
    """
    audit_service = LLMAuditService()
    audit_service.clear_audit_logs()
    
    # Old and new configurations
    old_config = {
        "name": "Test Provider",
        "type": "openai",
        "api_key": old_api_key,
        "model": "gpt-3.5-turbo"
    }
    
    new_config = {
        "name": "Test Provider Updated",
        "type": "openai",
        "api_key": new_api_key,
        "model": "gpt-4"
    }
    
    # Log the update using asyncio.run() for proper event loop handling
    entry = asyncio.run(
        audit_service.log_config_update(
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            old_config=old_config,
            new_config=new_config
        )
    )
    
    # Verify audit entry was created
    assert entry is not None, "Audit entry should be created"
    assert entry.action == LLMConfigAction.UPDATE, "Action should be UPDATE"
    assert entry.user_id == user_id, "User ID should match"
    assert entry.timestamp is not None, "Timestamp should be set"
    
    # Verify change details include changes
    assert "changes" in entry.change_details, "Changes should be in details"
    
    # Verify API keys are NOT in the audit log (sanitized)
    assert old_api_key not in str(entry.change_details), \
        "Old API key should be sanitized"
    assert new_api_key not in str(entry.change_details), \
        "New API key should be sanitized"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    user_id=user_id_strategy,
    tenant_id=tenant_id_strategy,
    provider_id=provider_id_strategy,
    api_key=openai_api_key_strategy
)
def test_property_26_delete_audit_logging(
    user_id: str,
    tenant_id: str,
    provider_id: str,
    api_key: str
):
    """
    Feature: llm-integration, Property 26: Configuration Audit Logging
    
    For any provider configuration delete operation, an audit log entry
    should be created with user ID, timestamp, and details of what was deleted.
    
    **Validates: Requirements 9.4**
    """
    audit_service = LLMAuditService()
    audit_service.clear_audit_logs()
    
    # Configuration being deleted
    config_data = {
        "name": "Test Provider",
        "type": "openai",
        "api_key": api_key,
        "model": "gpt-4"
    }
    
    # Log the deletion using asyncio.run() for proper event loop handling
    entry = asyncio.run(
        audit_service.log_config_delete(
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            config_data=config_data
        )
    )
    
    # Verify audit entry was created
    assert entry is not None, "Audit entry should be created"
    assert entry.action == LLMConfigAction.DELETE, "Action should be DELETE"
    assert entry.user_id == user_id, "User ID should match"
    assert entry.tenant_id == tenant_id, "Tenant ID should match"
    assert entry.provider_id == provider_id, "Provider ID should match"
    assert entry.timestamp is not None, "Timestamp should be set"
    
    # Verify change details are present
    assert "operation" in entry.change_details, "Operation should be in details"
    assert entry.change_details["operation"] == "delete"
    
    # Verify API key is NOT in the audit log (sanitized)
    assert api_key not in str(entry.change_details), \
        "API key should be sanitized from audit log"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    action=action_strategy,
    user_id=user_id_strategy,
    tenant_id=tenant_id_strategy,
    provider_id=provider_id_strategy
)
def test_property_26_audit_entry_completeness(
    action: LLMConfigAction,
    user_id: str,
    tenant_id: str,
    provider_id: str
):
    """
    Feature: llm-integration, Property 26: Configuration Audit Logging
    
    For any configuration change, the audit entry should contain all
    required fields: user_id, tenant_id, provider_id, timestamp, action.
    
    **Validates: Requirements 9.4**
    """
    # Create an audit entry directly
    entry = LLMAuditEntry(
        action=action,
        user_id=user_id,
        tenant_id=tenant_id,
        provider_id=provider_id,
        change_details={"test": "data"}
    )
    
    # Verify all required fields are present
    assert entry.action == action, "Action should be set"
    assert entry.user_id == user_id, "User ID should be set"
    assert entry.tenant_id == tenant_id, "Tenant ID should be set"
    assert entry.provider_id == provider_id, "Provider ID should be set"
    assert entry.timestamp is not None, "Timestamp should be auto-set"
    assert isinstance(entry.timestamp, datetime), "Timestamp should be datetime"
    
    # Verify to_dict produces complete output
    entry_dict = entry.to_dict()
    assert "action" in entry_dict
    assert "user_id" in entry_dict
    assert "tenant_id" in entry_dict
    assert "provider_id" in entry_dict
    assert "timestamp" in entry_dict
    assert "change_details" in entry_dict


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    user_id=user_id_strategy,
    tenant_id=tenant_id_strategy,
    provider_id=provider_id_strategy,
    ip_address=ip_address_strategy,
    user_agent=user_agent_strategy
)
def test_property_26_audit_metadata_capture(
    user_id: str,
    tenant_id: str,
    provider_id: str,
    ip_address: str,
    user_agent: str
):
    """
    Feature: llm-integration, Property 26: Configuration Audit Logging
    
    For any configuration change, the audit entry should capture
    request metadata including IP address and user agent.
    
    **Validates: Requirements 9.4**
    """
    audit_service = LLMAuditService()
    audit_service.clear_audit_logs()
    
    # Log a creation with metadata using asyncio.run() for proper event loop handling
    entry = asyncio.run(
        audit_service.log_config_create(
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            config_data={"name": "Test"},
            ip_address=ip_address,
            user_agent=user_agent
        )
    )
    
    # Verify metadata is captured
    assert entry.ip_address == ip_address, "IP address should be captured"
    assert entry.user_agent == user_agent, "User agent should be captured"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    tenant_id=tenant_id_strategy,
    num_operations=st.integers(min_value=1, max_value=10)
)
def test_property_26_audit_log_ordering(tenant_id: str, num_operations: int):
    """
    Feature: llm-integration, Property 26: Configuration Audit Logging
    
    For any sequence of configuration changes, audit logs should be
    retrievable and ordered by timestamp.
    
    **Validates: Requirements 9.4**
    """
    audit_service = LLMAuditService()
    audit_service.clear_audit_logs()
    
    # Perform multiple operations using asyncio.run() for proper event loop handling
    for i in range(num_operations):
        asyncio.run(
            audit_service.log_config_create(
                user_id=str(uuid4()),
                tenant_id=tenant_id,
                provider_id=str(uuid4()),
                config_data={"name": f"Provider {i}"}
            )
        )
    
    # Retrieve logs
    logs = audit_service.get_audit_logs(tenant_id=tenant_id)
    
    # Verify all operations are logged
    assert len(logs) == num_operations, \
        f"All {num_operations} operations should be logged"
    
    # Verify logs are ordered by timestamp
    for i in range(1, len(logs)):
        assert logs[i-1].timestamp <= logs[i].timestamp, \
            "Logs should be ordered by timestamp"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    user_id=user_id_strategy,
    tenant_id=tenant_id_strategy,
    provider_id=provider_id_strategy,
    success=st.booleans(),
    error_message=st.one_of(st.none(), st.text(min_size=1, max_size=100))
)
def test_property_26_connection_test_audit_logging(
    user_id: str,
    tenant_id: str,
    provider_id: str,
    success: bool,
    error_message: Optional[str]
):
    """
    Feature: llm-integration, Property 26: Configuration Audit Logging
    
    For any connection test operation, an audit log entry should be
    created with the test result.
    
    **Validates: Requirements 9.4**
    """
    audit_service = LLMAuditService()
    audit_service.clear_audit_logs()
    
    # Log a connection test using asyncio.run() for proper event loop handling
    entry = asyncio.run(
        audit_service.log_connection_test(
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            success=success,
            error_message=error_message if not success else None
        )
    )
    
    # Verify audit entry was created
    assert entry is not None, "Audit entry should be created"
    assert entry.action == LLMConfigAction.TEST_CONNECTION, \
        "Action should be TEST_CONNECTION"
    
    # Verify test result is in details
    assert "success" in entry.change_details
    assert entry.change_details["success"] == success


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    tenant_id=tenant_id_strategy,
    provider_id=provider_id_strategy,
    action=action_strategy
)
def test_property_26_audit_log_filtering(
    tenant_id: str,
    provider_id: str,
    action: LLMConfigAction
):
    """
    Feature: llm-integration, Property 26: Configuration Audit Logging
    
    Audit logs should be filterable by tenant_id, provider_id, and action.
    
    **Validates: Requirements 9.4**
    """
    audit_service = LLMAuditService()
    audit_service.clear_audit_logs()
    
    # Create entries with different attributes
    other_tenant = str(uuid4())
    other_provider = str(uuid4())
    
    # Log entries for target tenant/provider using asyncio.run() for proper event loop handling
    asyncio.run(
        audit_service.log_config_create(
            user_id=str(uuid4()),
            tenant_id=tenant_id,
            provider_id=provider_id,
            config_data={"name": "Target"}
        )
    )
    
    # Log entries for other tenant
    asyncio.run(
        audit_service.log_config_create(
            user_id=str(uuid4()),
            tenant_id=other_tenant,
            provider_id=other_provider,
            config_data={"name": "Other"}
        )
    )
    
    # Filter by tenant
    tenant_logs = audit_service.get_audit_logs(tenant_id=tenant_id)
    assert all(log.tenant_id == tenant_id for log in tenant_logs), \
        "All logs should match tenant filter"
    
    # Filter by provider
    provider_logs = audit_service.get_audit_logs(provider_id=provider_id)
    assert all(log.provider_id == provider_id for log in provider_logs), \
        "All logs should match provider filter"


# ==================== Combined Property Tests ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    api_key=openai_api_key_strategy,
    email=email_strategy,
    password=password_strategy,
    user_id=user_id_strategy,
    tenant_id=tenant_id_strategy,
    provider_id=provider_id_strategy
)
def test_property_24_26_combined_sanitization_and_audit(
    api_key: str,
    email: str,
    password: str,
    user_id: str,
    tenant_id: str,
    provider_id: str
):
    """
    Feature: llm-integration, Properties 24 & 26: Combined Test
    
    For any configuration change containing sensitive data, the audit log
    should be created AND all sensitive data should be sanitized.
    
    **Validates: Requirements 9.2, 9.4**
    """
    audit_service = LLMAuditService()
    audit_service.clear_audit_logs()
    
    # Create a configuration with multiple sensitive fields
    config_data = {
        "name": "Test Provider",
        "type": "openai",
        "api_key": api_key,
        "admin_email": email,
        "password": password,
        "model": "gpt-4"
    }
    
    # Log the creation using asyncio.run() for proper event loop handling
    entry = asyncio.run(
        audit_service.log_config_create(
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            config_data=config_data
        )
    )
    
    # Verify audit entry was created (Property 26)
    assert entry is not None, "Audit entry should be created"
    assert entry.action == LLMConfigAction.CREATE
    assert entry.user_id == user_id
    assert entry.tenant_id == tenant_id
    assert entry.timestamp is not None
    
    # Verify all sensitive data is sanitized (Property 24)
    # Check the actual config values, not just string presence
    new_config = entry.change_details.get("new_config", {})
    assert new_config.get("api_key") == "[REDACTED]", "API key should be sanitized"
    assert new_config.get("password") == "[REDACTED]", "Password should be sanitized"
    
    # Verify the audit log is retrievable
    logs = audit_service.get_audit_logs(tenant_id=tenant_id)
    assert len(logs) == 1
