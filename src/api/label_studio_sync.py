"""
Label Studio Synchronization Service

Handles automatic synchronization between SuperInsight tasks and Label Studio projects.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from src.label_studio.integration import (
    LabelStudioIntegration,
    ProjectConfig,
    label_studio_integration
)
from src.label_studio.exceptions import (
    LabelStudioIntegrationError,
    LabelStudioAuthenticationError
)

logger = logging.getLogger(__name__)


class LabelStudioSyncService:
    """Service for synchronizing tasks with Label Studio"""
    
    def __init__(self, integration: Optional[LabelStudioIntegration] = None):
        """
        Initialize sync service.
        
        Args:
            integration: Optional LabelStudioIntegration instance.
                        If not provided, uses global instance.
        """
        self.integration = integration or label_studio_integration
    
    async def create_project_for_task(
        self,
        task_id: str,
        task_name: str,
        task_description: Optional[str],
        annotation_type: str
    ) -> Dict[str, Any]:
        """
        Create a Label Studio project for a task.
        
        Args:
            task_id: SuperInsight task ID
            task_name: Task name
            task_description: Task description
            annotation_type: Type of annotation (text_classification, ner, etc.)
            
        Returns:
            Dict containing:
                - success: bool
                - project_id: str (if successful)
                - project_url: str (if successful)
                - error: str (if failed)
                - sync_status: str (synced, failed)
                - synced_at: str (ISO datetime)
        """
        try:
            logger.info(f"Creating Label Studio project for task {task_id}")
            
            # Prepare project configuration
            project_config = ProjectConfig(
                title=f"{task_name} (Task: {task_id})",
                description=task_description or f"Annotation project for task {task_id}",
                annotation_type=annotation_type
            )
            
            # Create project in Label Studio
            project = await self.integration.create_project(project_config)
            
            project_url = f"{self.integration.base_url}/projects/{project.id}"
            
            logger.info(
                f"Successfully created Label Studio project {project.id} "
                f"for task {task_id}"
            )
            
            return {
                "success": True,
                "project_id": str(project.id),
                "project_url": project_url,
                "sync_status": "synced",
                "synced_at": datetime.utcnow().isoformat() + "Z",
                "error": None
            }
            
        except LabelStudioAuthenticationError as e:
            error_msg = f"Authentication failed: {str(e)}"
            logger.error(f"Failed to create project for task {task_id}: {error_msg}")
            return {
                "success": False,
                "project_id": None,
                "project_url": None,
                "sync_status": "failed",
                "synced_at": datetime.utcnow().isoformat() + "Z",
                "error": error_msg
            }
            
        except LabelStudioIntegrationError as e:
            error_msg = f"Integration error: {str(e)}"
            logger.error(f"Failed to create project for task {task_id}: {error_msg}")
            return {
                "success": False,
                "project_id": None,
                "project_url": None,
                "sync_status": "failed",
                "synced_at": datetime.utcnow().isoformat() + "Z",
                "error": error_msg
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to create project for task {task_id}: {error_msg}")
            return {
                "success": False,
                "project_id": None,
                "project_url": None,
                "sync_status": "failed",
                "synced_at": datetime.utcnow().isoformat() + "Z",
                "error": error_msg
            }
    
    async def validate_project(self, project_id: str) -> Dict[str, Any]:
        """
        Validate that a Label Studio project exists and is accessible.
        
        Args:
            project_id: Label Studio project ID
            
        Returns:
            Dict containing validation result
        """
        try:
            result = await self.integration.validate_project(project_id)
            return result.to_dict()
        except Exception as e:
            logger.error(f"Error validating project {project_id}: {str(e)}")
            return {
                "exists": False,
                "accessible": False,
                "task_count": 0,
                "annotation_count": 0,
                "status": "error",
                "error_message": str(e)
            }
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test Label Studio connection and authentication.
        
        Returns:
            Dict containing:
                - connected: bool
                - authenticated: bool
                - auth_method: str (jwt or api_token)
                - base_url: str
                - error: str (if failed)
        """
        try:
            # Test connection
            connected = await self.integration.test_connection()
            
            if connected:
                return {
                    "connected": True,
                    "authenticated": True,
                    "auth_method": self.integration.auth_method,
                    "base_url": self.integration.base_url,
                    "error": None
                }
            else:
                return {
                    "connected": False,
                    "authenticated": False,
                    "auth_method": self.integration.auth_method,
                    "base_url": self.integration.base_url,
                    "error": "Connection test failed"
                }
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Connection test failed: {error_msg}")
            return {
                "connected": False,
                "authenticated": False,
                "auth_method": self.integration.auth_method,
                "base_url": self.integration.base_url,
                "error": error_msg
            }


# Global sync service instance
label_studio_sync_service = LabelStudioSyncService()
