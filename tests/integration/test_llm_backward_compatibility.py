"""
Integration test for LLM Application Binding backward compatibility.

This module tests that the upgraded _load_cloud_config() function maintains
backward compatibility with existing code:
- Works with database bindings when present
- Falls back to environment variables when no bindings exist
- Prioritizes database over environment variables when both exist
- Requires zero code changes in existing modules (SchemaInferrer, EntityExtractor)

Validates: Requirements 7.1, 7.4, 7.5, 7.8
"""

import asyncio
import os
import pytest
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select

from src.ai.llm_schemas import CloudConfig
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding
from src.services.structuring_pipeline import _load_cloud_config
from src.ai.schema_inferrer import SchemaInferrer
from src.ai.entity_extractor import EntityExtractor


@pytest.fixture
def setup_database_bindings(db_session):
    """
    Create test database bindings for the structuring application.
    
    Sets up:
    - LLMApplication for "structuring"
    - LLMConfiguration with encrypted API key
    - LLMApplicationBinding with priority 1
    """
    from src.ai.encryption_service import get_encryption_service
    
    encryption = get_encryption_service()
    
    # Create application
    app = LLMApplication(
        id=uuid4(),
        code="structuring",
        name="Data Structuring",
        description="Schema inference and entity extraction",
        llm_usage_pattern="High-frequency, low-latency",
        is_active=True
    )
    db_session.add(app)
    db_session.flush()
    
    # Create LLM configuration (without foreign key fields to avoid schema issues)
    api_key_encrypted = encryption.encrypt("test-database-api-key")
    config = LLMConfiguration(
        id=uuid4(),
        name="Test Database Config",
        default_method="openai",
        is_active=True,
        tenant_id=None,  # No tenant for test
        created_by=None,  # No user for test
        updated_by=None,  # No user for test
        config_data={
            "provider": "openai",
            "api_key_encrypted": api_key_encrypted,
            "base_url": "https://api.database.example.com/v1",
            "model_name": "gpt-4-database"
        }
    )
    db_session.add(config)
    db_session.flush()
    
    # Create binding
    binding = LLMApplicationBinding(
        id=uuid4(),
        llm_config_id=config.id,
        application_id=app.id,
        priority=1,
        max_retries=3,
        timeout_seconds=30,
        is_active=True
    )
    db_session.add(binding)
    db_session.commit()
    
    return {
        "application": app,
        "config": config,
        "binding": binding
    }


@pytest.mark.asyncio
class TestBackwardCompatibility:
    """Test backward compatibility of _load_cloud_config()."""
    
    async def test_with_database_bindings_present(self, db_session, setup_database_bindings):
        """
        Test that _load_cloud_config() loads from database when bindings exist.
        
        Validates: Requirements 7.1, 7.5
        """
        # Clear environment variables to ensure database is used
        with patch.dict(os.environ, {}, clear=True):
            # Load config
            config = await _load_cloud_config(tenant_id=None, application_code="structuring")
            
            # Verify config loaded from database
            assert config is not None
            assert isinstance(config, CloudConfig)
            assert config.openai_api_key == "test-database-api-key"
            assert config.openai_base_url == "https://api.database.example.com/v1"
            assert config.openai_model == "gpt-4-database"
    
    async def test_with_only_environment_variables(self, db_session):
        """
        Test that _load_cloud_config() falls back to environment variables
        when no database bindings exist.
        
        Validates: Requirements 7.1, 7.4
        """
        # Set environment variables
        env_vars = {
            "OPENAI_API_KEY": "test-env-api-key",
            "OPENAI_BASE_URL": "https://api.env.example.com/v1",
            "OPENAI_MODEL": "gpt-3.5-env"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Load config (no bindings exist for this application)
            config = await _load_cloud_config(tenant_id=None, application_code="nonexistent_app")
            
            # Verify config loaded from environment
            assert config is not None
            assert isinstance(config, CloudConfig)
            assert config.openai_api_key == "test-env-api-key"
            assert config.openai_base_url == "https://api.env.example.com/v1"
            assert config.openai_model == "gpt-3.5-env"
    
    async def test_database_wins_over_environment(self, db_session, setup_database_bindings):
        """
        Test that database bindings take priority over environment variables
        when both exist.
        
        Validates: Requirements 7.5
        """
        # Set environment variables
        env_vars = {
            "OPENAI_API_KEY": "test-env-api-key",
            "OPENAI_BASE_URL": "https://api.env.example.com/v1",
            "OPENAI_MODEL": "gpt-3.5-env"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Load config
            config = await _load_cloud_config(tenant_id=None, application_code="structuring")
            
            # Verify database config is used, not environment
            assert config is not None
            assert config.openai_api_key == "test-database-api-key"
            assert config.openai_base_url == "https://api.database.example.com/v1"
            assert config.openai_model == "gpt-4-database"
            
            # Verify environment variables were NOT used
            assert config.openai_api_key != "test-env-api-key"
            assert config.openai_base_url != "https://api.env.example.com/v1"
    
    async def test_function_signature_unchanged(self):
        """
        Test that _load_cloud_config() maintains its original function signature
        for backward compatibility.
        
        Validates: Requirements 7.6, 7.8
        """
        import inspect
        
        # Get function signature
        sig = inspect.signature(_load_cloud_config)
        params = list(sig.parameters.keys())
        
        # Verify parameters
        assert "tenant_id" in params
        assert "application_code" in params
        
        # Verify defaults
        assert sig.parameters["tenant_id"].default is None
        assert sig.parameters["application_code"].default == "structuring"
        
        # Verify it's an async function
        assert asyncio.iscoroutinefunction(_load_cloud_config)


@pytest.mark.asyncio
class TestZeroCodeChanges:
    """
    Test that existing modules work without code changes.
    
    Validates: Requirements 7.8
    """
    
    async def test_schema_inferrer_works_without_changes(self, db_session, setup_database_bindings):
        """
        Test that SchemaInferrer works with the upgraded _load_cloud_config()
        without any code changes.
        
        Validates: Requirements 7.8
        """
        # Load config using the upgraded function
        config = await _load_cloud_config(tenant_id=None, application_code="structuring")
        
        # Create SchemaInferrer with the config (no code changes needed)
        inferrer = SchemaInferrer(config)
        
        # Verify SchemaInferrer was created successfully
        assert inferrer is not None
        assert inferrer.cloud_config == config
        assert inferrer.cloud_config.openai_api_key == "test-database-api-key"
    
    async def test_entity_extractor_works_without_changes(self, db_session, setup_database_bindings):
        """
        Test that EntityExtractor works with the upgraded _load_cloud_config()
        without any code changes.
        
        Validates: Requirements 7.8
        """
        # Load config using the upgraded function
        config = await _load_cloud_config(tenant_id=None, application_code="structuring")
        
        # Create EntityExtractor with the config (no code changes needed)
        extractor = EntityExtractor(config)
        
        # Verify EntityExtractor was created successfully
        assert extractor is not None
        assert extractor.cloud_config == config
        assert extractor.cloud_config.openai_api_key == "test-database-api-key"
    
    async def test_existing_code_pattern_still_works(self, db_session):
        """
        Test that the existing code pattern (loading config and passing to modules)
        still works exactly as before.
        
        Validates: Requirements 7.8
        """
        # Set environment variables (simulating existing deployment)
        env_vars = {
            "OPENAI_API_KEY": "existing-deployment-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "OPENAI_MODEL": "gpt-3.5-turbo"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Existing code pattern (unchanged)
            config = await _load_cloud_config()
            inferrer = SchemaInferrer(config)
            extractor = EntityExtractor(config)
            
            # Verify everything works
            assert config.openai_api_key == "existing-deployment-key"
            assert inferrer.cloud_config == config
            assert extractor.cloud_config == config


@pytest.mark.asyncio
class TestGradualMigration:
    """
    Test gradual migration scenario where some applications use database
    bindings while others continue using environment variables.
    
    Validates: Requirements 7.7
    """
    
    async def test_mixed_configuration_sources(self, db_session, setup_database_bindings):
        """
        Test that applications can use different configuration sources
        during gradual migration.
        
        Validates: Requirements 7.7
        """
        env_vars = {
            "OPENAI_API_KEY": "env-fallback-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "OPENAI_MODEL": "gpt-3.5-turbo"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Application with database binding
            config_with_db = await _load_cloud_config(
                tenant_id=None,
                application_code="structuring"
            )
            
            # Application without database binding (uses env vars)
            config_with_env = await _load_cloud_config(
                tenant_id=None,
                application_code="knowledge_graph"
            )
            
            # Verify different sources
            assert config_with_db.openai_api_key == "test-database-api-key"
            assert config_with_db.openai_base_url == "https://api.database.example.com/v1"
            
            assert config_with_env.openai_api_key == "env-fallback-key"
            assert config_with_env.openai_base_url == "https://api.openai.com/v1"
    
    async def test_application_can_be_migrated_independently(self, db_session):
        """
        Test that applications can be migrated to database configuration
        independently without affecting others.
        
        Validates: Requirements 7.7
        """
        from src.ai.encryption_service import get_encryption_service
        
        encryption = get_encryption_service()
        
        # Create application and binding for knowledge_graph
        app = LLMApplication(
            id=uuid4(),
            code="knowledge_graph",
            name="Knowledge Graph",
            description="Knowledge graph construction",
            is_active=True
        )
        db_session.add(app)
        db_session.flush()
        
        api_key_encrypted = encryption.encrypt("kg-database-key")
        config = LLMConfiguration(
            id=uuid4(),
            name="KG Config",
            default_method="openai",
            is_active=True,
            tenant_id=None,
            created_by=None,
            updated_by=None,
            config_data={
                "provider": "openai",
                "api_key_encrypted": api_key_encrypted,
                "base_url": "https://api.kg.example.com/v1",
                "model_name": "gpt-4-kg"
            }
        )
        db_session.add(config)
        db_session.flush()
        
        binding = LLMApplicationBinding(
            id=uuid4(),
            llm_config_id=config.id,
            application_id=app.id,
            priority=1,
            max_retries=3,
            timeout_seconds=30,
            is_active=True
        )
        db_session.add(binding)
        db_session.commit()
        
        # Set environment variables
        env_vars = {
            "OPENAI_API_KEY": "env-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "OPENAI_MODEL": "gpt-3.5-turbo"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # knowledge_graph now uses database
            kg_config = await _load_cloud_config(
                tenant_id=None,
                application_code="knowledge_graph"
            )
            
            # Other apps still use environment
            other_config = await _load_cloud_config(
                tenant_id=None,
                application_code="ai_assistant"
            )
            
            # Verify independent configuration
            assert kg_config.openai_api_key == "kg-database-key"
            assert other_config.openai_api_key == "env-key"


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling in backward compatibility scenarios."""
    
    async def test_missing_both_database_and_env(self, db_session):
        """
        Test that appropriate error is raised when neither database
        nor environment configuration is available.
        
        Validates: Requirements 7.1
        """
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="No LLM configuration found"):
                await _load_cloud_config(
                    tenant_id=None,
                    application_code="nonexistent_app"
                )
    
    async def test_database_error_falls_back_to_env(self, db_session):
        """
        Test that database errors trigger fallback to environment variables.
        
        Validates: Requirements 7.1
        """
        env_vars = {
            "OPENAI_API_KEY": "fallback-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "OPENAI_MODEL": "gpt-3.5-turbo"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Simulate database error by using invalid session
            with patch("src.services.structuring_pipeline.db_manager.get_async_session") as mock_session:
                mock_session.side_effect = Exception("Database connection failed")
                
                # Should fall back to environment variables
                config = await _load_cloud_config(
                    tenant_id=None,
                    application_code="structuring"
                )
                
                assert config.openai_api_key == "fallback-key"
