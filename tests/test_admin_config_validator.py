"""
Property-Based Tests for Config Validator.

Tests the configuration validation functionality using Hypothesis
for property-based testing.

**Feature: admin-configuration, Property 2: 数据库连接验证**
**Validates: Requirements 3.4, 3.7**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.admin.config_validator import ConfigValidator, get_config_validator
from src.admin.schemas import (
    ValidationResult,
    DatabaseType,
    LLMType,
    SyncMode,
    LLMConfigCreate,
    DBConfigCreate,
    SyncStrategyCreate,
)


# ========== Custom Strategies ==========

def valid_llm_config_strategy():
    """Strategy for generating valid LLM configurations."""
    return st.fixed_dictionaries({
        'name': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        'llm_type': st.sampled_from([t.value for t in LLMType]),
        'model_name': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'P'))),
        'api_endpoint': st.just("http://localhost:11434") | st.just("https://api.openai.com/v1"),
        'temperature': st.floats(min_value=0.0, max_value=2.0),
        'max_tokens': st.integers(min_value=1, max_value=128000),
        'timeout_seconds': st.integers(min_value=1, max_value=600),
    })


def valid_db_config_strategy():
    """Strategy for generating valid database configurations."""
    return st.fixed_dictionaries({
        'name': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        'db_type': st.sampled_from([t.value for t in DatabaseType]),
        'host': st.sampled_from(['localhost', '127.0.0.1', 'db.example.com']),
        'port': st.integers(min_value=1, max_value=65535),
        'database': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        'username': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        'password': st.text(min_size=0, max_size=50),
        'is_readonly': st.booleans(),
    })


def valid_sync_config_strategy():
    """Strategy for generating valid sync configurations."""
    return st.fixed_dictionaries({
        'db_config_id': st.uuids().map(str),
        'mode': st.sampled_from([m.value for m in SyncMode]),
        'batch_size': st.integers(min_value=1, max_value=100000),
        'enabled': st.booleans(),
    })


def invalid_temperature_strategy():
    """Strategy for generating invalid temperatures."""
    return st.one_of(
        st.floats(max_value=-0.1),
        st.floats(min_value=2.1)
    )


def invalid_port_strategy():
    """Strategy for generating invalid ports."""
    return st.one_of(
        st.integers(max_value=0),
        st.integers(min_value=65536)
    )


class TestConfigValidatorProperties:
    """Property-based tests for ConfigValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create a test validator."""
        return ConfigValidator()
    
    # ========== Property 2: Database connection validation ==========
    
    @given(valid_db_config_strategy())
    @settings(max_examples=100)
    def test_valid_db_config_passes_validation(self, config: dict):
        """
        **Feature: admin-configuration, Property 2: 数据库连接验证**
        **Validates: Requirements 3.4, 3.7**
        
        For any valid database configuration, validation should pass.
        """
        validator = ConfigValidator()
        result = validator.validate_db_config(config)
        
        assert result.is_valid, (
            f"Valid config should pass validation: errors={result.errors}"
        )
    
    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_empty_host_fails_validation(self, db_name: str):
        """
        **Feature: admin-configuration, Property 2: 数据库连接验证**
        **Validates: Requirements 3.4, 3.7**
        
        Database config with empty host should fail validation.
        """
        validator = ConfigValidator()
        config = {
            'name': db_name,
            'db_type': 'postgresql',
            'host': '',  # Empty host
            'port': 5432,
            'database': 'testdb',
            'username': 'user',
        }
        
        result = validator.validate_db_config(config)
        
        assert not result.is_valid, "Empty host should fail validation"
        assert any(e.field == 'host' for e in result.errors), (
            "Should have error for host field"
        )
    
    @given(invalid_port_strategy())
    @settings(max_examples=100)
    def test_invalid_port_fails_validation(self, port: int):
        """
        **Feature: admin-configuration, Property 2: 数据库连接验证**
        **Validates: Requirements 3.4, 3.7**
        
        Database config with invalid port should fail validation.
        """
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'db_type': 'postgresql',
            'host': 'localhost',
            'port': port,  # Invalid port
            'database': 'testdb',
            'username': 'user',
        }
        
        result = validator.validate_db_config(config)
        
        assert not result.is_valid, f"Invalid port {port} should fail validation"
        assert any(e.field == 'port' for e in result.errors), (
            "Should have error for port field"
        )
    
    # ========== LLM Config Validation Properties ==========
    
    @given(valid_llm_config_strategy())
    @settings(max_examples=100)
    def test_valid_llm_config_passes_validation(self, config: dict):
        """
        For any valid LLM configuration, validation should pass.
        """
        validator = ConfigValidator()
        result = validator.validate_llm_config(config)
        
        assert result.is_valid, (
            f"Valid LLM config should pass validation: errors={result.errors}"
        )
    
    @given(invalid_temperature_strategy())
    @settings(max_examples=100)
    def test_invalid_temperature_fails_validation(self, temperature: float):
        """
        LLM config with invalid temperature should fail validation.
        """
        assume(not (temperature != temperature))  # Skip NaN
        
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'llm_type': 'local_ollama',
            'model_name': 'llama2',
            'temperature': temperature,
        }
        
        result = validator.validate_llm_config(config)
        
        assert not result.is_valid, (
            f"Invalid temperature {temperature} should fail validation"
        )
        assert any(e.field == 'temperature' for e in result.errors), (
            "Should have error for temperature field"
        )
    
    @given(st.integers(max_value=0) | st.integers(min_value=128001))
    @settings(max_examples=100)
    def test_invalid_max_tokens_fails_validation(self, max_tokens: int):
        """
        LLM config with invalid max_tokens should fail validation.
        """
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'llm_type': 'local_ollama',
            'model_name': 'llama2',
            'max_tokens': max_tokens,
        }
        
        result = validator.validate_llm_config(config)
        
        assert not result.is_valid, (
            f"Invalid max_tokens {max_tokens} should fail validation"
        )
        assert any(e.field == 'max_tokens' for e in result.errors), (
            "Should have error for max_tokens field"
        )
    
    # ========== Sync Config Validation Properties ==========
    
    @given(valid_sync_config_strategy())
    @settings(max_examples=100)
    def test_valid_sync_config_passes_validation(self, config: dict):
        """
        For any valid sync configuration, validation should pass
        (unless incremental mode without incremental_field).
        """
        validator = ConfigValidator()
        
        # Add incremental_field if mode is incremental
        if config.get('mode') == 'incremental':
            config['incremental_field'] = 'updated_at'
        
        result = validator.validate_sync_config(config)
        
        assert result.is_valid, (
            f"Valid sync config should pass validation: errors={result.errors}"
        )
    
    @given(st.integers(max_value=0) | st.integers(min_value=100001))
    @settings(max_examples=100)
    def test_invalid_batch_size_fails_validation(self, batch_size: int):
        """
        Sync config with invalid batch_size should fail validation.
        """
        validator = ConfigValidator()
        config = {
            'db_config_id': 'test-id',
            'mode': 'full',
            'batch_size': batch_size,
        }
        
        result = validator.validate_sync_config(config)
        
        assert not result.is_valid, (
            f"Invalid batch_size {batch_size} should fail validation"
        )
        assert any(e.field == 'batch_size' for e in result.errors), (
            "Should have error for batch_size field"
        )
    
    def test_incremental_mode_requires_incremental_field(self):
        """
        Incremental sync mode should require incremental_field.
        """
        validator = ConfigValidator()
        config = {
            'db_config_id': 'test-id',
            'mode': 'incremental',
            # Missing incremental_field
        }
        
        result = validator.validate_sync_config(config)
        
        assert not result.is_valid, (
            "Incremental mode without incremental_field should fail"
        )
        assert any(e.field == 'incremental_field' for e in result.errors), (
            "Should have error for incremental_field"
        )
    
    # ========== Cron Validation Properties ==========
    
    @given(st.sampled_from([
        '* * * * *',
        '0 * * * *',
        '0 0 * * *',
        '0 0 1 * *',
        '0 0 * * 0',
        '*/5 * * * *',
        '0 */2 * * *',
    ]))
    @settings(max_examples=50)
    def test_valid_cron_passes_validation(self, cron: str):
        """
        Valid cron expressions should pass validation.
        """
        validator = ConfigValidator()
        config = {
            'db_config_id': 'test-id',
            'mode': 'full',
            'schedule': cron,
        }
        
        result = validator.validate_sync_config(config)
        
        # Should not have cron-related errors
        cron_errors = [e for e in result.errors if e.field == 'schedule']
        assert len(cron_errors) == 0, (
            f"Valid cron '{cron}' should not have errors: {cron_errors}"
        )
    
    @given(st.sampled_from([
        'invalid',
        '* * *',  # Too few fields
        '* * * * * *',  # Too many fields
        '60 * * * *',  # Invalid minute
        '* 24 * * *',  # Invalid hour
    ]))
    @settings(max_examples=50)
    def test_invalid_cron_fails_validation(self, cron: str):
        """
        Invalid cron expressions should fail validation.
        """
        validator = ConfigValidator()
        config = {
            'db_config_id': 'test-id',
            'mode': 'full',
            'schedule': cron,
        }
        
        result = validator.validate_sync_config(config)
        
        assert not result.is_valid, (
            f"Invalid cron '{cron}' should fail validation"
        )
        assert any(e.field == 'schedule' for e in result.errors), (
            f"Should have error for schedule field with cron '{cron}'"
        )


class TestConfigValidatorUnit:
    """Unit tests for ConfigValidator edge cases."""
    
    def test_validate_llm_config_empty_model_name(self):
        """Empty model name should fail validation."""
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'llm_type': 'local_ollama',
            'model_name': '',  # Empty
        }
        
        result = validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert any(e.field == 'model_name' for e in result.errors)
    
    def test_validate_llm_config_invalid_type(self):
        """Invalid LLM type should fail validation."""
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'llm_type': 'invalid_type',
            'model_name': 'model',
        }
        
        result = validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert any(e.field == 'llm_type' for e in result.errors)
    
    def test_validate_llm_config_invalid_url(self):
        """Invalid API endpoint URL should fail validation."""
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'llm_type': 'openai',
            'model_name': 'gpt-4',
            'api_endpoint': 'not-a-url',
        }
        
        result = validator.validate_llm_config(config)
        
        assert not result.is_valid
        assert any(e.field == 'api_endpoint' for e in result.errors)
    
    def test_validate_db_config_invalid_type(self):
        """Invalid database type should fail validation."""
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'db_type': 'invalid_db',
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'username': 'user',
        }
        
        result = validator.validate_db_config(config)
        
        assert not result.is_valid
        assert any(e.field == 'db_type' for e in result.errors)
    
    def test_validate_db_config_empty_database(self):
        """Empty database name should fail validation."""
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'db_type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': '',  # Empty
            'username': 'user',
        }
        
        result = validator.validate_db_config(config)
        
        assert not result.is_valid
        assert any(e.field == 'database' for e in result.errors)
    
    def test_validate_db_config_empty_username(self):
        """Empty username should fail validation."""
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'db_type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'username': '',  # Empty
        }
        
        result = validator.validate_db_config(config)
        
        assert not result.is_valid
        assert any(e.field == 'username' for e in result.errors)
    
    def test_validate_db_config_warns_no_password(self):
        """Missing password should generate warning."""
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'db_type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'username': 'user',
            # No password
        }
        
        result = validator.validate_db_config(config)
        
        assert result.is_valid  # Should still be valid
        assert len(result.warnings) > 0  # But should have warning
    
    def test_validate_db_config_warns_non_readonly(self):
        """Non-readonly connection should generate warning."""
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'db_type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'username': 'user',
            'password': 'pass',
            'is_readonly': False,
        }
        
        result = validator.validate_db_config(config)
        
        assert result.is_valid  # Should still be valid
        assert any('readonly' in w.lower() for w in result.warnings)
    
    def test_validate_sync_config_invalid_mode(self):
        """Invalid sync mode should fail validation."""
        validator = ConfigValidator()
        config = {
            'db_config_id': 'test-id',
            'mode': 'invalid_mode',
        }
        
        result = validator.validate_sync_config(config)
        
        assert not result.is_valid
        assert any(e.field == 'mode' for e in result.errors)
    
    def test_validate_sync_config_invalid_filter_condition(self):
        """Invalid filter condition should fail validation."""
        validator = ConfigValidator()
        config = {
            'db_config_id': 'test-id',
            'mode': 'full',
            'filter_conditions': [
                {'field': 'name'},  # Missing operator
            ],
        }
        
        result = validator.validate_sync_config(config)
        
        assert not result.is_valid
        assert any('filter_conditions' in e.field for e in result.errors)
    
    def test_get_config_validator_singleton(self):
        """get_config_validator should return the same instance."""
        validator1 = get_config_validator()
        validator2 = get_config_validator()
        
        assert validator1 is validator2


class TestConfigValidatorHostValidation:
    """Tests for host validation."""
    
    @pytest.mark.parametrize("host,expected_valid", [
        ("localhost", True),
        ("127.0.0.1", True),
        ("192.168.1.1", True),
        ("db.example.com", True),
        ("my-database.internal", True),
        ("", False),
        ("   ", False),
    ])
    def test_host_validation(self, host: str, expected_valid: bool):
        """Test various host formats."""
        validator = ConfigValidator()
        config = {
            'name': 'test',
            'db_type': 'postgresql',
            'host': host,
            'port': 5432,
            'database': 'testdb',
            'username': 'user',
        }
        
        result = validator.validate_db_config(config)
        
        if expected_valid:
            host_errors = [e for e in result.errors if e.field == 'host']
            assert len(host_errors) == 0, f"Host '{host}' should be valid"
        else:
            assert any(e.field == 'host' for e in result.errors), (
                f"Host '{host}' should be invalid"
            )
