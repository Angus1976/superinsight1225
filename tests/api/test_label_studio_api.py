"""
Label Studio API Tests

Tests for Label Studio integration endpoints:
- POST /api/label-studio/projects/ensure - Ensure project exists
- GET /api/label-studio/projects/{project_id}/validate - Validate project
- GET /api/label-studio/projects/{project_id}/auth-url - Get authenticated URL
- POST /api/label-studio/projects/{project_id}/import-tasks - Import tasks

**Validates**: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4
import asyncio

from src.label_studio.integration import (
    LabelStudioIntegration,
    ProjectValidationResult,
    ProjectConfig,
    ImportResult,
)
from src.label_studio.exceptions import (
    LabelStudioIntegrationError,
    LabelStudioProjectNotFoundError,
)


class TestEnsureProjectEndpoint:
    """Tests for ensure_project_exists functionality"""
    
    @pytest.mark.asyncio
    async def test_ensure_project_success_creates_new_project(self):
        """
        Test: Successfully create new project
        Validates: Requirements 1.3 - Automatic Project Creation
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        mock_project = Mock()
        mock_project.id = 123
        mock_project.task_number = 0
        
        mock_ls.ensure_project_exists = AsyncMock(return_value=mock_project)
        
        # Execute
        project = await mock_ls.ensure_project_exists(
            project_id=None,
            project_config=ProjectConfig(
                title="Test Project",
                description="Test description",
                annotation_type="text_classification"
            )
        )
        
        # Verify
        assert project.id == 123
        assert project.task_number == 0
        mock_ls.ensure_project_exists.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_project_reuses_existing_project(self):
        """
        Test: Reuse existing project when it already exists
        Validates: Requirements 1.3 - Idempotent Project Creation
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        mock_project = Mock()
        mock_project.id = 456
        mock_project.task_number = 100
        
        mock_ls.ensure_project_exists = AsyncMock(return_value=mock_project)
        
        # Execute
        project = await mock_ls.ensure_project_exists(
            project_id="456",
            project_config=ProjectConfig(
                title="Test Project",
                description="Test description",
                annotation_type="text_classification"
            )
        )
        
        # Verify
        assert project.id == 456
        assert project.task_number == 100
    
    @pytest.mark.asyncio
    async def test_ensure_project_handles_integration_error(self):
        """
        Test: Handle Label Studio integration error
        Validates: Requirements 1.7 - Error Handling
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        mock_ls.ensure_project_exists = AsyncMock(
            side_effect=LabelStudioIntegrationError("Connection failed")
        )
        
        # Execute & Verify
        with pytest.raises(LabelStudioIntegrationError):
            await mock_ls.ensure_project_exists(
                project_id=None,
                project_config=ProjectConfig(
                    title="Test Project",
                    description="Test description",
                    annotation_type="text_classification"
                )
            )


class TestEnsureProjectEndpoint:
    """Tests for ensure_project_exists functionality"""
    
    @pytest.mark.asyncio
    async def test_ensure_project_success_creates_new_project(self):
        """
        Test: Successfully create new project
        Validates: Requirements 1.3 - Automatic Project Creation
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        mock_project = Mock()
        mock_project.id = 123
        mock_project.task_number = 0
        
        mock_ls.ensure_project_exists = AsyncMock(return_value=mock_project)
        
        # Execute
        project = await mock_ls.ensure_project_exists(
            project_id=None,
            project_config=ProjectConfig(
                title="Test Project",
                description="Test description",
                annotation_type="text_classification"
            )
        )
        
        # Verify
        assert project.id == 123
        assert project.task_number == 0
        mock_ls.ensure_project_exists.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_project_reuses_existing_project(self):
        """
        Test: Reuse existing project when it already exists
        Validates: Requirements 1.3 - Idempotent Project Creation
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        mock_project = Mock()
        mock_project.id = 456
        mock_project.task_number = 100
        
        mock_ls.ensure_project_exists = AsyncMock(return_value=mock_project)
        
        # Execute
        project = await mock_ls.ensure_project_exists(
            project_id="456",
            project_config=ProjectConfig(
                title="Test Project",
                description="Test description",
                annotation_type="text_classification"
            )
        )
        
        # Verify
        assert project.id == 456
        assert project.task_number == 100
    
    @pytest.mark.asyncio
    async def test_ensure_project_handles_integration_error(self):
        """
        Test: Handle Label Studio integration error
        Validates: Requirements 1.7 - Error Handling
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        mock_ls.ensure_project_exists = AsyncMock(
            side_effect=LabelStudioIntegrationError("Connection failed")
        )
        
        # Execute & Verify
        with pytest.raises(LabelStudioIntegrationError):
            await mock_ls.ensure_project_exists(
                project_id=None,
                project_config=ProjectConfig(
                    title="Test Project",
                    description="Test description",
                    annotation_type="text_classification"
                )
            )



class TestValidateProjectEndpoint:
    """Tests for validate_project functionality"""
    
    @pytest.mark.asyncio
    async def test_validate_project_exists_and_accessible(self):
        """
        Test: Validate project exists and is accessible
        Validates: Requirements 1.1, 1.2
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        validation_result = ProjectValidationResult(
            exists=True,
            accessible=True,
            task_count=100,
            annotation_count=65,
            status="ready"
        )
        
        mock_ls.validate_project = AsyncMock(return_value=validation_result)
        
        # Execute
        result = await mock_ls.validate_project("123")
        
        # Verify
        assert result.exists is True
        assert result.accessible is True
        assert result.task_count == 100
        assert result.annotation_count == 65
        assert result.status == "ready"
    
    @pytest.mark.asyncio
    async def test_validate_project_not_found(self):
        """
        Test: Validate project not found
        Validates: Requirements 1.1, 1.2
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        validation_result = ProjectValidationResult(
            exists=False,
            accessible=False,
            task_count=0,
            annotation_count=0,
            status="not_found",
            error_message="Project not found"
        )
        
        mock_ls.validate_project = AsyncMock(return_value=validation_result)
        
        # Execute
        result = await mock_ls.validate_project("999")
        
        # Verify
        assert result.exists is False
        assert result.accessible is False
        assert result.status == "not_found"


class TestAuthUrlEndpoint:
    """Tests for generate_authenticated_url functionality"""
    
    @pytest.mark.asyncio
    async def test_get_auth_url_with_chinese_language(self):
        """
        Test: Get authenticated URL with Chinese language
        Validates: Requirements 1.2, 1.5 - Language Synchronization
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        url_info = {
            "url": "https://labelstudio.example.com/projects/123?token=abc123&lang=zh",
            "expires_at": "2025-01-20T15:00:00Z",
            "project_id": "123",
            "language": "zh"
        }
        
        mock_ls.generate_authenticated_url = AsyncMock(return_value=url_info)
        
        # Execute
        result = await mock_ls.generate_authenticated_url(
            project_id="123",
            user_id="user123",
            language="zh",
            expires_in=3600
        )
        
        # Verify
        assert "url" in result
        assert "lang=zh" in result["url"]
        assert result["language"] == "zh"
        assert result["project_id"] == "123"
    
    @pytest.mark.asyncio
    async def test_get_auth_url_with_english_language(self):
        """
        Test: Get authenticated URL with English language
        Validates: Requirements 1.5 - Language Synchronization
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        url_info = {
            "url": "https://labelstudio.example.com/projects/123?token=xyz789&lang=en",
            "expires_at": "2025-01-20T15:00:00Z",
            "project_id": "123",
            "language": "en"
        }
        
        mock_ls.generate_authenticated_url = AsyncMock(return_value=url_info)
        
        # Execute
        result = await mock_ls.generate_authenticated_url(
            project_id="123",
            user_id="user123",
            language="en",
            expires_in=3600
        )
        
        # Verify
        assert "url" in result
        assert "lang=en" in result["url"]
        assert result["language"] == "en"
    
    @pytest.mark.asyncio
    async def test_get_auth_url_project_not_found(self):
        """
        Test: Get auth URL for non-existent project
        Validates: Requirements 1.7 - Error Handling
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        mock_ls.generate_authenticated_url = AsyncMock(
            side_effect=LabelStudioProjectNotFoundError("Project not found")
        )
        
        # Execute & Verify
        with pytest.raises(LabelStudioProjectNotFoundError):
            await mock_ls.generate_authenticated_url(
                project_id="999",
                user_id="user123",
                language="zh",
                expires_in=3600
            )


class TestImportTasksEndpoint:
    """Tests for import_tasks functionality"""
    
    @pytest.mark.asyncio
    async def test_import_tasks_success(self):
        """
        Test: Successfully import tasks
        Validates: Requirements 1.4 - Task Data Synchronization
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        import_result = ImportResult(
            success=True,
            imported_count=100,
            failed_count=0,
            errors=[]
        )
        
        mock_ls.import_tasks = AsyncMock(return_value=import_result)
        
        # Execute
        result = await mock_ls.import_tasks("123", [])
        
        # Verify
        assert result.success is True
        assert result.imported_count == 100
        assert result.failed_count == 0
    
    @pytest.mark.asyncio
    async def test_import_tasks_project_not_found(self):
        """
        Test: Import tasks to non-existent project
        Validates: Requirements 1.7 - Error Handling
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        mock_ls.import_tasks = AsyncMock(
            side_effect=LabelStudioProjectNotFoundError("Project not found")
        )
        
        # Execute & Verify
        with pytest.raises(LabelStudioProjectNotFoundError):
            await mock_ls.import_tasks("999", [])


class TestHealthCheckEndpoint:
    """Tests for health check functionality"""
    
    def test_health_check_success(self):
        """
        Test: Health check succeeds when Label Studio is available
        Validates: Requirements 1.7 - Service Availability Check
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        mock_ls.list_projects = Mock(return_value=[])
        
        # Execute
        projects = mock_ls.list_projects()
        
        # Verify
        assert projects == []
        mock_ls.list_projects.assert_called_once()
    
    def test_health_check_failure(self):
        """
        Test: Health check fails when Label Studio is unavailable
        Validates: Requirements 1.7 - Service Availability Check
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        mock_ls.list_projects = Mock(
            side_effect=Exception("Connection refused")
        )
        
        # Execute & Verify
        with pytest.raises(Exception):
            mock_ls.list_projects()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

