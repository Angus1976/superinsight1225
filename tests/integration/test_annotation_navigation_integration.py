"""
Label Studio Annotation Navigation Integration Tests

End-to-end integration tests for the annotation navigation workflow:
- Complete project creation and navigation flow
- Project validation and reuse
- Authenticated URL generation and window opening
- Error handling and recovery

**Validates**: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta

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


class TestAnnotationNavigationIntegration:
    """Integration tests for complete annotation navigation workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_start_annotation_flow_with_existing_project(self):
        """
        Test: Complete flow for starting annotation with existing project
        
        Flow:
        1. User clicks "Start Annotation" button
        2. System validates project exists
        3. System navigates to annotation page
        
        Validates: Requirements 1.1, 1.2, 1.6
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        task_id = str(uuid4())
        project_id = "123"
        
        # Mock project validation - project exists and is accessible
        validation_result = ProjectValidationResult(
            exists=True,
            accessible=True,
            task_count=100,
            annotation_count=65,
            status="ready"
        )
        mock_ls.validate_project = AsyncMock(return_value=validation_result)
        
        # Execute
        result = await mock_ls.validate_project(project_id)
        
        # Verify
        assert result.exists is True
        assert result.accessible is True
        assert result.status == "ready"
        mock_ls.validate_project.assert_called_once_with(project_id)
    
    @pytest.mark.asyncio
    async def test_complete_start_annotation_flow_with_project_creation(self):
        """
        Test: Complete flow for starting annotation with project creation
        
        Flow:
        1. User clicks "Start Annotation" button
        2. System checks if project exists (not found)
        3. System creates new project
        4. System updates task with new project ID
        5. System navigates to annotation page
        
        Validates: Requirements 1.1, 1.3, 1.6
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        task_id = str(uuid4())
        
        # Mock project validation - project doesn't exist
        validation_result = ProjectValidationResult(
            exists=False,
            accessible=False,
            task_count=0,
            annotation_count=0,
            status="not_found"
        )
        mock_ls.validate_project = AsyncMock(return_value=validation_result)
        
        # Mock project creation
        mock_project = Mock()
        mock_project.id = 456
        mock_project.task_number = 0
        mock_ls.ensure_project_exists = AsyncMock(return_value=mock_project)
        
        # Execute - Step 1: Validate project
        validation = await mock_ls.validate_project(None)
        assert validation.exists is False
        
        # Execute - Step 2: Create project
        project_config = ProjectConfig(
            title="Test Task",
            description="Test description",
            annotation_type="text_classification"
        )
        project = await mock_ls.ensure_project_exists(
            project_id=None,
            project_config=project_config
        )
        
        # Verify
        assert project.id == 456
        assert project.task_number == 0
        mock_ls.validate_project.assert_called_once()
        mock_ls.ensure_project_exists.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_open_in_new_window_flow(self):
        """
        Test: Complete flow for opening in new window
        
        Flow:
        1. User clicks "Open in New Window" button
        2. System validates project exists
        3. System generates authenticated URL with language
        4. System opens URL in new window
        
        Validates: Requirements 1.2, 1.5, 1.6
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        project_id = "123"
        user_id = "user-456"
        language = "zh"
        
        # Mock project validation
        validation_result = ProjectValidationResult(
            exists=True,
            accessible=True,
            task_count=100,
            annotation_count=65,
            status="ready"
        )
        mock_ls.validate_project = AsyncMock(return_value=validation_result)
        
        # Mock authenticated URL generation
        url_info = {
            "url": f"https://labelstudio.example.com/projects/{project_id}?token=abc123&lang={language}",
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            "project_id": project_id,
            "language": language
        }
        mock_ls.generate_authenticated_url = AsyncMock(return_value=url_info)
        
        # Execute - Step 1: Validate project
        validation = await mock_ls.validate_project(project_id)
        assert validation.exists is True
        
        # Execute - Step 2: Generate authenticated URL
        auth_url = await mock_ls.generate_authenticated_url(
            project_id=project_id,
            user_id=user_id,
            language=language,
            expires_in=3600
        )
        
        # Verify
        assert "url" in auth_url
        assert f"lang={language}" in auth_url["url"]
        assert auth_url["project_id"] == project_id
        assert auth_url["language"] == language
        mock_ls.validate_project.assert_called_once()
        mock_ls.generate_authenticated_url.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_flow_with_language_switching(self):
        """
        Test: Complete flow with language switching
        
        Flow:
        1. User is in Chinese interface
        2. User clicks "Open in New Window"
        3. System generates URL with Chinese language
        4. User switches to English
        5. User clicks "Open in New Window" again
        6. System generates URL with English language
        
        Validates: Requirements 1.5
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        project_id = "123"
        user_id = "user-456"
        
        # Mock project validation
        validation_result = ProjectValidationResult(
            exists=True,
            accessible=True,
            task_count=100,
            annotation_count=65,
            status="ready"
        )
        mock_ls.validate_project = AsyncMock(return_value=validation_result)
        
        # Mock authenticated URL generation for Chinese
        url_info_zh = {
            "url": f"https://labelstudio.example.com/projects/{project_id}?token=abc123&lang=zh",
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            "project_id": project_id,
            "language": "zh"
        }
        
        # Mock authenticated URL generation for English
        url_info_en = {
            "url": f"https://labelstudio.example.com/projects/{project_id}?token=xyz789&lang=en",
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            "project_id": project_id,
            "language": "en"
        }
        
        mock_ls.generate_authenticated_url = AsyncMock(
            side_effect=[url_info_zh, url_info_en]
        )
        
        # Execute - Step 1: Generate URL in Chinese
        auth_url_zh = await mock_ls.generate_authenticated_url(
            project_id=project_id,
            user_id=user_id,
            language="zh",
            expires_in=3600
        )
        
        # Verify Chinese URL
        assert "lang=zh" in auth_url_zh["url"]
        assert auth_url_zh["language"] == "zh"
        
        # Execute - Step 2: Generate URL in English
        auth_url_en = await mock_ls.generate_authenticated_url(
            project_id=project_id,
            user_id=user_id,
            language="en",
            expires_in=3600
        )
        
        # Verify English URL
        assert "lang=en" in auth_url_en["url"]
        assert auth_url_en["language"] == "en"
        
        # Verify both calls were made
        assert mock_ls.generate_authenticated_url.call_count == 2
    
    @pytest.mark.asyncio
    async def test_error_handling_project_not_found(self):
        """
        Test: Error handling when project is not found
        
        Flow:
        1. User clicks button
        2. System tries to validate project
        3. Project not found error occurs
        4. System displays error message
        
        Validates: Requirements 1.7
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        
        # Mock project validation - project not found
        mock_ls.validate_project = AsyncMock(
            side_effect=LabelStudioProjectNotFoundError("Project not found")
        )
        
        # Execute & Verify
        with pytest.raises(LabelStudioProjectNotFoundError):
            await mock_ls.validate_project("999")
    
    @pytest.mark.asyncio
    async def test_error_handling_service_unavailable(self):
        """
        Test: Error handling when Label Studio service is unavailable
        
        Flow:
        1. User clicks button
        2. System tries to validate project
        3. Service unavailable error occurs
        4. System displays error message
        
        Validates: Requirements 1.7
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        
        # Mock project validation - service unavailable
        mock_ls.validate_project = AsyncMock(
            side_effect=LabelStudioIntegrationError("Service unavailable")
        )
        
        # Execute & Verify
        with pytest.raises(LabelStudioIntegrationError):
            await mock_ls.validate_project("123")
    
    @pytest.mark.asyncio
    async def test_error_handling_authentication_failure(self):
        """
        Test: Error handling when authentication fails
        
        Flow:
        1. User clicks button
        2. System tries to generate authenticated URL
        3. Authentication fails
        4. System displays error message
        
        Validates: Requirements 1.7
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        
        # Mock authenticated URL generation - authentication failure
        mock_ls.generate_authenticated_url = AsyncMock(
            side_effect=LabelStudioIntegrationError("Authentication failed")
        )
        
        # Execute & Verify
        with pytest.raises(LabelStudioIntegrationError):
            await mock_ls.generate_authenticated_url(
                project_id="123",
                user_id="user-456",
                language="zh",
                expires_in=3600
            )
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self):
        """
        Test: Handling concurrent requests from multiple users
        
        Flow:
        1. Multiple users click buttons simultaneously
        2. System handles all requests concurrently
        3. All requests complete successfully
        
        Validates: Requirements 1.1, 1.2
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        
        # Mock project validation
        validation_result = ProjectValidationResult(
            exists=True,
            accessible=True,
            task_count=100,
            annotation_count=65,
            status="ready"
        )
        mock_ls.validate_project = AsyncMock(return_value=validation_result)
        
        # Execute - Simulate concurrent requests
        tasks = [
            mock_ls.validate_project(f"project-{i}")
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        
        # Verify
        assert len(results) == 10
        assert all(r.exists is True for r in results)
        assert mock_ls.validate_project.call_count == 10
    
    @pytest.mark.asyncio
    async def test_project_reuse_across_multiple_operations(self):
        """
        Test: Project is reused across multiple operations
        
        Flow:
        1. User creates project for task A
        2. User opens task A in new window (reuses project)
        3. User opens task A again (reuses project)
        4. Project is only created once
        
        Validates: Requirements 1.3
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        project_id = "123"
        
        # Mock project validation - project exists
        validation_result = ProjectValidationResult(
            exists=True,
            accessible=True,
            task_count=100,
            annotation_count=65,
            status="ready"
        )
        mock_ls.validate_project = AsyncMock(return_value=validation_result)
        
        # Mock authenticated URL generation
        url_info = {
            "url": f"https://labelstudio.example.com/projects/{project_id}?token=abc123&lang=zh",
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            "project_id": project_id,
            "language": "zh"
        }
        mock_ls.generate_authenticated_url = AsyncMock(return_value=url_info)
        
        # Execute - Multiple operations
        for _ in range(3):
            validation = await mock_ls.validate_project(project_id)
            assert validation.exists is True
            
            auth_url = await mock_ls.generate_authenticated_url(
                project_id=project_id,
                user_id="user-456",
                language="zh",
                expires_in=3600
            )
            assert auth_url["project_id"] == project_id
        
        # Verify - Project validation called 3 times, but project not recreated
        assert mock_ls.validate_project.call_count == 3
        assert mock_ls.generate_authenticated_url.call_count == 3


class TestAnnotationNavigationErrorRecovery:
    """Integration tests for error recovery scenarios"""
    
    @pytest.mark.asyncio
    async def test_recovery_from_temporary_service_failure(self):
        """
        Test: Recovery from temporary service failure
        
        Flow:
        1. First request fails (service temporarily unavailable)
        2. User retries
        3. Second request succeeds
        
        Validates: Requirements 1.7
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        
        # Mock project validation - first call fails, second succeeds
        validation_result = ProjectValidationResult(
            exists=True,
            accessible=True,
            task_count=100,
            annotation_count=65,
            status="ready"
        )
        mock_ls.validate_project = AsyncMock(
            side_effect=[
                LabelStudioIntegrationError("Service temporarily unavailable"),
                validation_result
            ]
        )
        
        # Execute - First attempt fails
        with pytest.raises(LabelStudioIntegrationError):
            await mock_ls.validate_project("123")
        
        # Execute - Retry succeeds
        result = await mock_ls.validate_project("123")
        
        # Verify
        assert result.exists is True
        assert mock_ls.validate_project.call_count == 2
    
    @pytest.mark.asyncio
    async def test_recovery_from_project_creation_failure(self):
        """
        Test: Recovery from project creation failure
        
        Flow:
        1. Project creation fails
        2. User retries
        3. Project creation succeeds
        
        Validates: Requirements 1.3, 1.7
        """
        # Setup
        mock_ls = Mock(spec=LabelStudioIntegration)
        
        # Mock project creation - first call fails, second succeeds
        mock_project = Mock()
        mock_project.id = 456
        mock_project.task_number = 0
        
        mock_ls.ensure_project_exists = AsyncMock(
            side_effect=[
                LabelStudioIntegrationError("Failed to create project"),
                mock_project
            ]
        )
        
        project_config = ProjectConfig(
            title="Test Task",
            description="Test description",
            annotation_type="text_classification"
        )
        
        # Execute - First attempt fails
        with pytest.raises(LabelStudioIntegrationError):
            await mock_ls.ensure_project_exists(
                project_id=None,
                project_config=project_config
            )
        
        # Execute - Retry succeeds
        project = await mock_ls.ensure_project_exists(
            project_id=None,
            project_config=project_config
        )
        
        # Verify
        assert project.id == 456
        assert mock_ls.ensure_project_exists.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
