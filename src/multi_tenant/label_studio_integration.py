"""
Label Studio integration for multi-tenant workspace management.

This module provides integration between the multi-tenant system and Label Studio,
managing organizations, projects, and user synchronization.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
import requests
from sqlalchemy.orm import Session

from src.multi_tenant.services import TenantManager, WorkspaceManager, UserWorkspaceManager
from src.database.multi_tenant_models import TenantModel, WorkspaceModel, WorkspaceRole
from src.config import settings

logger = logging.getLogger(__name__)


class LabelStudioIntegrationService:
    """Service for integrating multi-tenant workspaces with Label Studio."""
    
    def __init__(self, session: Session):
        self.session = session
        self.base_url = getattr(settings, 'LABEL_STUDIO_URL', 'http://localhost:8080')
        self.api_token = getattr(settings, 'LABEL_STUDIO_API_TOKEN', '')
        self.headers = {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    def create_tenant_organization(self, tenant_id: str) -> Optional[str]:
        """
        Create a Label Studio organization for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Organization ID if successful, None otherwise
        """
        try:
            tenant_manager = TenantManager(self.session)
            tenant = tenant_manager.get_tenant(tenant_id)
            
            if not tenant:
                logger.error(f"Tenant {tenant_id} not found")
                return None
            
            # Check if organization already exists
            if tenant.label_studio_org_id:
                return tenant.label_studio_org_id
            
            # Create organization in Label Studio
            org_data = {
                'title': tenant.display_name,
                'description': tenant.description or f'Organization for tenant {tenant_id}',
                'contact_info': tenant.billing_email or '',
            }
            
            response = requests.post(
                f'{self.base_url}/api/organizations/',
                json=org_data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 201:
                org_info = response.json()
                org_id = str(org_info['id'])
                
                # Update tenant with organization ID
                tenant_manager.update_tenant(tenant_id, label_studio_org_id=org_id)
                
                logger.info(f"Created Label Studio organization {org_id} for tenant {tenant_id}")
                return org_id
            else:
                logger.error(f"Failed to create Label Studio organization: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating Label Studio organization for tenant {tenant_id}: {e}")
            return None
    
    def create_workspace_project(self, workspace_id: UUID) -> Optional[str]:
        """
        Create a Label Studio project for a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            Project ID if successful, None otherwise
        """
        try:
            workspace_manager = WorkspaceManager(self.session)
            workspace = workspace_manager.get_workspace(workspace_id)
            
            if not workspace:
                logger.error(f"Workspace {workspace_id} not found")
                return None
            
            # Check if project already exists
            if workspace.label_studio_project_id:
                return workspace.label_studio_project_id
            
            # Ensure tenant organization exists
            org_id = self.create_tenant_organization(workspace.tenant_id)
            if not org_id:
                logger.error(f"Failed to create/get organization for tenant {workspace.tenant_id}")
                return None
            
            # Create project in Label Studio
            project_data = {
                'title': workspace.display_name,
                'description': workspace.description or f'Project for workspace {workspace.name}',
                'organization': int(org_id),
                'label_config': self._get_default_label_config(),
                'expert_instruction': 'Please annotate the data according to the project guidelines.',
                'show_instruction': True,
                'show_skip_button': True,
                'enable_empty_annotation': False,
            }
            
            # Add workspace-specific configuration
            if workspace.configuration:
                if 'label_config' in workspace.configuration:
                    project_data['label_config'] = workspace.configuration['label_config']
                if 'expert_instruction' in workspace.configuration:
                    project_data['expert_instruction'] = workspace.configuration['expert_instruction']
            
            response = requests.post(
                f'{self.base_url}/api/projects/',
                json=project_data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 201:
                project_info = response.json()
                project_id = str(project_info['id'])
                
                # Update workspace with project ID
                workspace_manager.update_workspace(workspace_id, label_studio_project_id=project_id)
                
                logger.info(f"Created Label Studio project {project_id} for workspace {workspace_id}")
                return project_id
            else:
                logger.error(f"Failed to create Label Studio project: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating Label Studio project for workspace {workspace_id}: {e}")
            return None
    
    def sync_workspace_users(self, workspace_id: UUID) -> bool:
        """
        Synchronize workspace users to Label Studio project.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            workspace_manager = WorkspaceManager(self.session)
            user_workspace_manager = UserWorkspaceManager(self.session)
            
            workspace = workspace_manager.get_workspace(workspace_id)
            if not workspace or not workspace.label_studio_project_id:
                logger.error(f"Workspace {workspace_id} not found or no Label Studio project")
                return False
            
            # Get workspace users
            user_associations = user_workspace_manager.get_workspace_users(workspace_id)
            
            # Get current project members from Label Studio
            response = requests.get(
                f'{self.base_url}/api/projects/{workspace.label_studio_project_id}/members/',
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get Label Studio project members: {response.text}")
                return False
            
            current_members = response.json()
            current_member_emails = {member['user']['email'] for member in current_members}
            
            # Add new users to project
            for association in user_associations:
                user_email = association.user.email
                if user_email not in current_member_emails:
                    self._add_user_to_project(
                        workspace.label_studio_project_id,
                        user_email,
                        association.role
                    )
            
            logger.info(f"Synchronized {len(user_associations)} users to Label Studio project {workspace.label_studio_project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error synchronizing users for workspace {workspace_id}: {e}")
            return False
    
    def _add_user_to_project(self, project_id: str, user_email: str, role: WorkspaceRole) -> bool:
        """
        Add a user to a Label Studio project.
        
        Args:
            project_id: Label Studio project ID
            user_email: User email
            role: Workspace role
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Map workspace roles to Label Studio roles
            role_mapping = {
                WorkspaceRole.VIEWER: 'Reviewer',
                WorkspaceRole.ANNOTATOR: 'Annotator',
                WorkspaceRole.REVIEWER: 'Reviewer',
                WorkspaceRole.ADMIN: 'Manager'
            }
            
            ls_role = role_mapping.get(role, 'Annotator')
            
            # First, try to get or create the user
            user_data = {
                'email': user_email,
                'first_name': user_email.split('@')[0],
                'last_name': '',
            }
            
            # Try to create user (will fail if exists, which is fine)
            requests.post(
                f'{self.base_url}/api/users/',
                json=user_data,
                headers=self.headers,
                timeout=30
            )
            
            # Add user to project
            member_data = {
                'user': user_email,
                'role': ls_role
            }
            
            response = requests.post(
                f'{self.base_url}/api/projects/{project_id}/members/',
                json=member_data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Added user {user_email} to Label Studio project {project_id} with role {ls_role}")
                return True
            else:
                logger.warning(f"Failed to add user to Label Studio project: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding user {user_email} to project {project_id}: {e}")
            return False
    
    def update_project_configuration(self, workspace_id: UUID, configuration: Dict[str, Any]) -> bool:
        """
        Update Label Studio project configuration from workspace settings.
        
        Args:
            workspace_id: Workspace ID
            configuration: New configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            workspace_manager = WorkspaceManager(self.session)
            workspace = workspace_manager.get_workspace(workspace_id)
            
            if not workspace or not workspace.label_studio_project_id:
                logger.error(f"Workspace {workspace_id} not found or no Label Studio project")
                return False
            
            # Prepare update data
            update_data = {}
            
            if 'label_config' in configuration:
                update_data['label_config'] = configuration['label_config']
            
            if 'expert_instruction' in configuration:
                update_data['expert_instruction'] = configuration['expert_instruction']
            
            if 'title' in configuration:
                update_data['title'] = configuration['title']
            
            if 'description' in configuration:
                update_data['description'] = configuration['description']
            
            if not update_data:
                return True  # Nothing to update
            
            # Update project in Label Studio
            response = requests.patch(
                f'{self.base_url}/api/projects/{workspace.label_studio_project_id}/',
                json=update_data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Updated Label Studio project {workspace.label_studio_project_id} configuration")
                return True
            else:
                logger.error(f"Failed to update Label Studio project: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating project configuration for workspace {workspace_id}: {e}")
            return False
    
    def archive_workspace_project(self, workspace_id: UUID) -> bool:
        """
        Archive a Label Studio project when workspace is archived.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            workspace_manager = WorkspaceManager(self.session)
            workspace = workspace_manager.get_workspace(workspace_id)
            
            if not workspace or not workspace.label_studio_project_id:
                return True  # Nothing to archive
            
            # Archive project in Label Studio (set to inactive)
            update_data = {
                'is_published': False,
                'description': f"[ARCHIVED] {workspace.description or workspace.display_name}"
            }
            
            response = requests.patch(
                f'{self.base_url}/api/projects/{workspace.label_studio_project_id}/',
                json=update_data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Archived Label Studio project {workspace.label_studio_project_id}")
                return True
            else:
                logger.warning(f"Failed to archive Label Studio project: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error archiving project for workspace {workspace_id}: {e}")
            return False
    
    def _get_default_label_config(self) -> str:
        """
        Get default Label Studio configuration.
        
        Returns:
            Default label configuration XML
        """
        return '''
        <View>
          <Text name="text" value="$text"/>
          <Choices name="sentiment" toName="text">
            <Choice value="positive"/>
            <Choice value="negative"/>
            <Choice value="neutral"/>
          </Choices>
        </View>
        '''
    
    def test_connection(self) -> bool:
        """
        Test connection to Label Studio.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = requests.get(
                f'{self.base_url}/api/version/',
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                version_info = response.json()
                logger.info(f"Connected to Label Studio version: {version_info.get('version', 'unknown')}")
                return True
            else:
                logger.error(f"Failed to connect to Label Studio: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error testing Label Studio connection: {e}")
            return False
    
    def get_project_stats(self, workspace_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get Label Studio project statistics for a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            Project statistics or None if error
        """
        try:
            workspace_manager = WorkspaceManager(self.session)
            workspace = workspace_manager.get_workspace(workspace_id)
            
            if not workspace or not workspace.label_studio_project_id:
                return None
            
            response = requests.get(
                f'{self.base_url}/api/projects/{workspace.label_studio_project_id}/',
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                project_info = response.json()
                return {
                    'project_id': project_info['id'],
                    'title': project_info['title'],
                    'total_annotations': project_info.get('total_annotations_number', 0),
                    'total_predictions': project_info.get('total_predictions_number', 0),
                    'task_number': project_info.get('task_number', 0),
                    'finished_task_number': project_info.get('finished_task_number', 0),
                    'skipped_annotations_number': project_info.get('skipped_annotations_number', 0),
                    'ground_truth_number': project_info.get('ground_truth_number', 0),
                    'created_at': project_info.get('created_at'),
                    'updated_at': project_info.get('updated_at')
                }
            else:
                logger.error(f"Failed to get Label Studio project stats: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting project stats for workspace {workspace_id}: {e}")
            return None