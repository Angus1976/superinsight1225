"""
Tests for API Registration Manager.

Tests the APIRegistrationManager class functionality including:
- Successful router registration
- Import error handling
- Exception handling
- Batch registration
- Registration report generation

Validates: Requirements 2.5 - 清晰的 API 注册规范
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from fastapi import FastAPI, APIRouter
from src.app import APIRegistrationManager, APIRouterConfig


class TestAPIRegistrationManager:
    """Test suite for APIRegistrationManager.
    
    Tests the core functionality of the API registration system including:
    - Single router registration with success and failure scenarios
    - Batch registration of multiple routers
    - Registration report generation
    - Error isolation (single failure doesn't affect others)
    """
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        return FastAPI()
    
    @pytest.fixture
    def logger(self):
        """Create a test logger."""
        return logging.getLogger("test_api_registration")
    
    @pytest.fixture
    def manager(self, app, logger):
        """Create an APIRegistrationManager instance."""
        return APIRegistrationManager(app, logger)
    
    def test_register_router_success(self, manager):
        """Test successful router registration.
        
        Validates: Requirements 2.5 - API 注册成功场景
        
        Tests that:
        - A valid module with a router can be registered
        - The module path is added to registered_apis list
        - The method returns True on success
        """
        # Test with a known existing module (src.api.extraction)
        result = manager.register_router(
            module_path="src.api.extraction",
            router_name="router",
            prefix="/api/v1/test-extraction",
            tags=["test"]
        )
        
        assert result is True, "Registration should succeed for valid module"
        assert "src.api.extraction" in manager.registered_apis, \
            "Module path should be in registered_apis list"
        assert len(manager.failed_apis) == 0, \
            "No failed APIs should be recorded on success"
    
    def test_register_router_import_error(self, manager):
        """Test handling of import errors.
        
        Validates: Requirements 3.2 - 单个 API 注册失败不应导致整个应用崩溃
        
        Tests that:
        - ImportError is handled gracefully when module doesn't exist
        - The method returns False on import failure
        - The failure is recorded in failed_apis list
        - No exception is raised when required=False
        """
        result = manager.register_router(
            module_path="src.api.nonexistent_module_xyz",
            router_name="router",
            prefix="/api/v1/test",
            tags=["test"],
            required=False
        )
        
        assert result is False, "Registration should fail for nonexistent module"
        assert any("nonexistent_module_xyz" in api[0] for api in manager.failed_apis), \
            "Failed module should be recorded in failed_apis"
        assert "src.api.nonexistent_module_xyz" not in manager.registered_apis, \
            "Failed module should not be in registered_apis"
    
    def test_register_router_import_error_required(self, manager):
        """Test that required=True raises ImportError for missing modules.
        
        Validates: Requirements 3.2 - 必需 API 失败时应抛出异常
        """
        with pytest.raises(ImportError):
            manager.register_router(
                module_path="src.api.nonexistent_required_module",
                router_name="router",
                prefix="/api/v1/test",
                tags=["test"],
                required=True
            )
    
    def test_register_router_exception(self, manager):
        """Test handling of general exceptions.
        
        Validates: Requirements 3.2 - 异常处理
        
        Tests that:
        - AttributeError is handled when router name doesn't exist in module
        - The method returns False on failure
        - The failure is recorded in failed_apis list
        """
        # Test with valid module but invalid router name
        result = manager.register_router(
            module_path="src.api.extraction",
            router_name="nonexistent_router_name",
            prefix="/api/v1/test",
            tags=["test"],
            required=False
        )
        
        assert result is False, "Registration should fail for invalid router name"
        assert len(manager.failed_apis) > 0, \
            "Failed registration should be recorded"
    
    def test_register_router_exception_required(self, manager):
        """Test that required=True raises exception for invalid router name.
        
        Validates: Requirements 3.2 - 必需 API 失败时应抛出异常
        """
        with pytest.raises(AttributeError):
            manager.register_router(
                module_path="src.api.extraction",
                router_name="nonexistent_router_name",
                prefix="/api/v1/test",
                tags=["test"],
                required=True
            )
    
    def test_register_batch(self, manager):
        """Test batch registration of multiple routers.
        
        Validates: Requirements 3.1 - 失败的 API 注册不应阻塞其他 API 的加载
        
        Tests that:
        - Multiple routers can be registered in batch
        - Success and failure counts are accurate
        - Single failure doesn't prevent other registrations
        """
        routers = [
            {
                "module_path": "src.api.extraction",
                "router_name": "router",
                "prefix": "/api/v1/batch-test1",
                "tags": ["batch-test"]
            },
            {
                "module_path": "src.api.nonexistent_batch_module",
                "router_name": "router",
                "prefix": "/api/v1/batch-test2",
                "tags": ["batch-test"],
                "required": False
            },
        ]
        
        success, failed = manager.register_batch(routers)
        
        assert success >= 1, "At least one router should succeed"
        assert failed >= 1, "At least one router should fail"
        assert success + failed == len(routers), \
            "Total should equal number of routers"
    
    def test_register_batch_empty_list(self, manager):
        """Test batch registration with empty list.
        
        Tests that:
        - Empty list is handled gracefully
        - Returns (0, 0) for empty input
        """
        success, failed = manager.register_batch([])
        
        assert success == 0, "Success count should be 0 for empty list"
        assert failed == 0, "Failed count should be 0 for empty list"
    
    def test_register_batch_missing_module_path(self, manager):
        """Test batch registration with missing module_path.
        
        Tests that:
        - Missing module_path is handled as a failure
        - Other routers are still processed
        """
        routers = [
            {
                # Missing module_path
                "router_name": "router",
                "prefix": "/api/v1/test"
            },
            {
                "module_path": "src.api.extraction",
                "router_name": "router",
                "prefix": "/api/v1/test2"
            }
        ]
        
        success, failed = manager.register_batch(routers)
        
        assert failed >= 1, "Missing module_path should count as failure"
        assert success >= 1, "Valid router should still succeed"
    
    def test_get_registration_report(self, manager):
        """Test registration report generation.
        
        Validates: Requirements 2.5 - 清晰的 API 注册状态
        
        Tests that:
        - Report contains all required fields
        - Counts are accurate
        - Status reflects registration state
        """
        # Register some routers first
        manager.register_router(
            module_path="src.api.extraction",
            router_name="router",
            prefix="/api/v1/report-test"
        )
        
        manager.register_router(
            module_path="src.api.nonexistent_report_module",
            router_name="router",
            prefix="/api/v1/report-test2",
            required=False
        )
        
        report = manager.get_registration_report()
        
        # Verify required fields exist
        assert "total" in report, "Report should contain 'total'"
        assert "successful" in report, "Report should contain 'successful'"
        assert "failed" in report, "Report should contain 'failed'"
        assert "status" in report, "Report should contain 'status'"
        assert "registered_apis" in report, "Report should contain 'registered_apis'"
        assert "failed_apis" in report, "Report should contain 'failed_apis'"
        assert "success_rate" in report, "Report should contain 'success_rate'"
        
        # Verify counts
        assert report["total"] == report["successful"] + report["failed"], \
            "Total should equal successful + failed"
        assert report["successful"] >= 1, "At least one should succeed"
        assert report["failed"] >= 1, "At least one should fail"
        
        # Verify status
        assert report["status"] in ["complete", "partial"], \
            "Status should be 'complete' or 'partial'"
    
    def test_get_registration_report_empty(self, manager):
        """Test registration report with no registrations.
        
        Tests that:
        - Report is valid even with no registrations
        - All counts are zero
        """
        report = manager.get_registration_report()
        
        assert report["total"] == 0, "Total should be 0"
        assert report["successful"] == 0, "Successful should be 0"
        assert report["failed"] == 0, "Failed should be 0"
        assert report["success_rate"] == 0.0, "Success rate should be 0.0"
    
    def test_is_registered(self, manager):
        """Test is_registered method.
        
        Tests that:
        - Returns True for registered modules
        - Returns False for unregistered modules
        """
        # Register a module
        manager.register_router(
            module_path="src.api.extraction",
            router_name="router",
            prefix="/api/v1/is-registered-test"
        )
        
        assert manager.is_registered("src.api.extraction") is True, \
            "Should return True for registered module"
        assert manager.is_registered("src.api.nonexistent") is False, \
            "Should return False for unregistered module"
    
    def test_get_registered_count(self, manager):
        """Test get_registered_count method.
        
        Tests that:
        - Count increases with successful registrations
        - Count doesn't increase with failed registrations
        """
        initial_count = manager.get_registered_count()
        
        # Register a valid module
        manager.register_router(
            module_path="src.api.extraction",
            router_name="router",
            prefix="/api/v1/count-test"
        )
        
        assert manager.get_registered_count() == initial_count + 1, \
            "Count should increase by 1"
        
        # Try to register invalid module
        manager.register_router(
            module_path="src.api.nonexistent_count_module",
            router_name="router",
            prefix="/api/v1/count-test2",
            required=False
        )
        
        assert manager.get_registered_count() == initial_count + 1, \
            "Count should not increase for failed registration"
    
    def test_get_failed_count(self, manager):
        """Test get_failed_count method.
        
        Tests that:
        - Count increases with failed registrations
        - Count doesn't increase with successful registrations
        """
        initial_count = manager.get_failed_count()
        
        # Try to register invalid module
        manager.register_router(
            module_path="src.api.nonexistent_failed_count_module",
            router_name="router",
            prefix="/api/v1/failed-count-test",
            required=False
        )
        
        assert manager.get_failed_count() == initial_count + 1, \
            "Failed count should increase by 1"
    
    def test_register_from_configs(self, manager):
        """Test register_from_configs method with APIRouterConfig objects.
        
        Validates: Requirements 2.5 - 使用配置对象注册
        
        Tests that:
        - APIRouterConfig objects can be used for registration
        - Success and failure counts are accurate
        """
        configs = [
            APIRouterConfig(
                module_path="src.api.extraction",
                router_name="router",
                prefix="/api/v1/config-test",
                tags=["config-test"],
                priority="high",
                description="Test config registration"
            ),
            APIRouterConfig(
                module_path="src.api.nonexistent_config_module",
                router_name="router",
                prefix="/api/v1/config-test2",
                tags=["config-test"],
                required=False,
                priority="low",
                description="Test failed config registration"
            ),
        ]
        
        success, failed = manager.register_from_configs(configs)
        
        assert success >= 1, "At least one config should succeed"
        assert failed >= 1, "At least one config should fail"
        assert success + failed == len(configs), \
            "Total should equal number of configs"


class TestAPIRouterConfig:
    """Test suite for APIRouterConfig Pydantic model.
    
    Tests the configuration model validation and defaults.
    """
    
    def test_config_defaults(self):
        """Test default values for APIRouterConfig.
        
        Tests that:
        - Default values are set correctly
        - Only module_path is required
        """
        config = APIRouterConfig(module_path="src.api.test")
        
        assert config.module_path == "src.api.test"
        assert config.router_name == "router"
        assert config.prefix is None
        assert config.tags is None
        assert config.required is False
        assert config.priority == "high"
        assert config.description == ""
    
    def test_config_with_all_fields(self):
        """Test APIRouterConfig with all fields specified.
        
        Tests that:
        - All fields can be set
        - Values are preserved correctly
        """
        config = APIRouterConfig(
            module_path="src.api.test",
            router_name="custom_router",
            prefix="/api/v1/custom",
            tags=["tag1", "tag2"],
            required=True,
            priority="medium",
            description="Custom description"
        )
        
        assert config.module_path == "src.api.test"
        assert config.router_name == "custom_router"
        assert config.prefix == "/api/v1/custom"
        assert config.tags == ["tag1", "tag2"]
        assert config.required is True
        assert config.priority == "medium"
        assert config.description == "Custom description"
    
    def test_config_model_dump(self):
        """Test that config can be converted to dict.
        
        Tests that:
        - model_dump() returns a valid dictionary
        - All fields are included
        """
        config = APIRouterConfig(
            module_path="src.api.test",
            prefix="/api/v1/test",
            tags=["test"]
        )
        
        config_dict = config.model_dump()
        
        assert isinstance(config_dict, dict)
        assert config_dict["module_path"] == "src.api.test"
        assert config_dict["prefix"] == "/api/v1/test"
        assert config_dict["tags"] == ["test"]


class TestAPIRegistrationErrorIsolation:
    """Test suite for error isolation in API registration.
    
    Validates: Requirements 3.1 - 单个 API 注册失败不应导致整个应用崩溃
    """
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        return FastAPI()
    
    @pytest.fixture
    def logger(self):
        """Create a test logger."""
        return logging.getLogger("test_error_isolation")
    
    @pytest.fixture
    def manager(self, app, logger):
        """Create an APIRegistrationManager instance."""
        return APIRegistrationManager(app, logger)
    
    def test_multiple_failures_dont_affect_success(self, manager):
        """Test that multiple failures don't prevent successful registrations.
        
        Tests that:
        - Multiple failed registrations are handled
        - Successful registrations still work
        - All failures are recorded
        """
        routers = [
            {"module_path": "src.api.nonexistent1", "prefix": "/api/v1/fail1"},
            {"module_path": "src.api.nonexistent2", "prefix": "/api/v1/fail2"},
            {"module_path": "src.api.extraction", "prefix": "/api/v1/success1"},
            {"module_path": "src.api.nonexistent3", "prefix": "/api/v1/fail3"},
        ]
        
        success, failed = manager.register_batch(routers)
        
        assert success >= 1, "At least one should succeed despite failures"
        assert failed >= 3, "All invalid modules should fail"
        assert len(manager.failed_apis) >= 3, "All failures should be recorded"
    
    def test_exception_in_one_doesnt_stop_batch(self, manager):
        """Test that exception in one registration doesn't stop the batch.
        
        Tests that:
        - Batch continues after individual failures
        - Final counts are accurate
        """
        # Create a mix of valid and invalid configurations
        routers = [
            {"module_path": "src.api.extraction", "prefix": "/api/v1/batch1"},
            {"module_path": "src.api.extraction", "router_name": "invalid_name", "prefix": "/api/v1/batch2"},
            {"module_path": "src.api.nonexistent", "prefix": "/api/v1/batch3"},
        ]
        
        success, failed = manager.register_batch(routers)
        
        # Verify batch completed
        assert success + failed == len(routers), \
            "All routers should be processed"


class TestHighPriorityAPIsConfig:
    """Test suite for HIGH_PRIORITY_APIS configuration.
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.4 - 高优先级 API 配置
    """
    
    def test_high_priority_apis_count(self):
        """Test that HIGH_PRIORITY_APIS has expected count.
        
        Tests that:
        - Configuration list has 12 high priority APIs
        """
        from src.app import HIGH_PRIORITY_APIS
        
        assert len(HIGH_PRIORITY_APIS) == 12, \
            "Should have 12 high priority APIs configured"
    
    def test_high_priority_apis_structure(self):
        """Test that all HIGH_PRIORITY_APIS have valid structure.
        
        Tests that:
        - All configs are APIRouterConfig instances
        - All have required fields
        """
        from src.app import HIGH_PRIORITY_APIS
        
        for config in HIGH_PRIORITY_APIS:
            assert isinstance(config, APIRouterConfig), \
                f"Config should be APIRouterConfig: {config}"
            assert config.module_path, \
                f"Config should have module_path: {config}"
            assert config.prefix, \
                f"Config should have prefix: {config}"
    
    def test_high_priority_apis_modules(self):
        """Test that HIGH_PRIORITY_APIS contains expected modules.
        
        Tests that:
        - License module APIs are included (3)
        - Quality module APIs are included (3)
        - Augmentation API is included (1)
        - Security module APIs are included (4)
        - Versioning API is included (1)
        """
        from src.app import HIGH_PRIORITY_APIS
        
        module_paths = [config.module_path for config in HIGH_PRIORITY_APIS]
        
        # License module (3)
        assert "src.api.license_router" in module_paths
        assert "src.api.usage_router" in module_paths
        assert "src.api.activation_router" in module_paths
        
        # Quality module (3)
        assert "src.api.quality_rules" in module_paths
        assert "src.api.quality_reports" in module_paths
        assert "src.api.quality_workflow" in module_paths
        
        # Augmentation (1)
        assert "src.api.augmentation" in module_paths
        
        # Security module (4)
        assert "src.api.sessions" in module_paths
        assert "src.api.sso" in module_paths
        assert "src.api.rbac" in module_paths
        assert "src.api.data_permission_router" in module_paths
        
        # Versioning (1)
        assert "src.api.versioning" in module_paths
    
    def test_high_priority_apis_prefixes(self):
        """Test that HIGH_PRIORITY_APIS have correct prefixes.
        
        Tests that:
        - All prefixes follow the /api/v1/ pattern
        - Prefixes are unique
        """
        from src.app import HIGH_PRIORITY_APIS
        
        prefixes = [config.prefix for config in HIGH_PRIORITY_APIS]
        
        # All should start with /api/v1/
        for prefix in prefixes:
            assert prefix.startswith("/api/v1/"), \
                f"Prefix should start with /api/v1/: {prefix}"
        
        # All should be unique
        assert len(prefixes) == len(set(prefixes)), \
            "All prefixes should be unique"
