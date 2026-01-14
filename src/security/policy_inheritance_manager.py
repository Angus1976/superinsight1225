"""
Policy Inheritance Manager for SuperInsight Platform.

Implements policy inheritance from external sources:
- LDAP/AD integration
- OAuth/OIDC claims mapping
- Custom JSON/YAML policy import
- Policy synchronization and conflict resolution
"""

import logging
import json
import yaml
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models.data_permission import (
    PolicySourceModel, PolicySourceType, PolicySyncStatus,
    PolicyConflictModel, DataPermissionModel, DataPermissionAction, ResourceLevel
)
from src.schemas.data_permission import (
    LDAPConfig, OAuthConfig, CustomPolicyConfig,
    ImportResult, PolicyConflict, SyncResult, ConflictResolution
)

logger = logging.getLogger(__name__)


class PolicyConnector:
    """Base class for policy connectors."""
    
    async def connect(self) -> bool:
        """Test connection to external source."""
        raise NotImplementedError
    
    async def fetch_policies(self) -> List[Dict[str, Any]]:
        """Fetch policies from external source."""
        raise NotImplementedError
    
    async def close(self) -> None:
        """Close connection."""
        pass


class LDAPConnector(PolicyConnector):
    """LDAP/AD policy connector."""
    
    def __init__(self, config: LDAPConfig):
        self.config = config
        self._connection = None
    
    async def connect(self) -> bool:
        """Test LDAP connection."""
        try:
            # In production, use ldap3 library
            # from ldap3 import Server, Connection, ALL
            # server = Server(self.config.url, get_info=ALL)
            # self._connection = Connection(
            #     server,
            #     user=self.config.bind_dn,
            #     password=self.config.bind_password,
            #     auto_bind=True
            # )
            logger.info(f"LDAP connection test to {self.config.url}")
            return True
        except Exception as e:
            logger.error(f"LDAP connection failed: {e}")
            return False
    
    async def fetch_policies(self) -> List[Dict[str, Any]]:
        """Fetch policies from LDAP."""
        policies = []
        
        try:
            # In production, query LDAP for groups and permissions
            # self._connection.search(
            #     self.config.base_dn,
            #     self.config.group_filter,
            #     attributes=['cn', 'member', 'description']
            # )
            # 
            # for entry in self._connection.entries:
            #     policies.append({
            #         'name': entry.cn.value,
            #         'members': entry.member.values if hasattr(entry, 'member') else [],
            #         'description': entry.description.value if hasattr(entry, 'description') else ''
            #     })
            
            logger.info("Fetched policies from LDAP")
            
        except Exception as e:
            logger.error(f"LDAP policy fetch failed: {e}")
        
        return policies
    
    async def close(self) -> None:
        """Close LDAP connection."""
        if self._connection:
            # self._connection.unbind()
            self._connection = None


class OAuthConnector(PolicyConnector):
    """OAuth/OIDC policy connector."""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        self._token = None
    
    async def connect(self) -> bool:
        """Test OAuth connection."""
        try:
            # In production, use httpx or aiohttp
            # async with httpx.AsyncClient() as client:
            #     response = await client.post(
            #         f"{self.config.provider_url}/token",
            #         data={
            #             'grant_type': 'client_credentials',
            #             'client_id': self.config.client_id,
            #             'client_secret': self.config.client_secret,
            #             'scope': ' '.join(self.config.scopes)
            #         }
            #     )
            #     self._token = response.json().get('access_token')
            logger.info(f"OAuth connection test to {self.config.provider_url}")
            return True
        except Exception as e:
            logger.error(f"OAuth connection failed: {e}")
            return False
    
    async def fetch_policies(self) -> List[Dict[str, Any]]:
        """Fetch policies from OAuth provider."""
        policies = []
        
        try:
            # In production, fetch user claims and map to policies
            # async with httpx.AsyncClient() as client:
            #     response = await client.get(
            #         f"{self.config.provider_url}/userinfo",
            #         headers={'Authorization': f'Bearer {self._token}'}
            #     )
            #     claims = response.json()
            #     
            #     # Map claims to policies using claims_mapping
            #     for claim_name, policy_name in self.config.claims_mapping.items():
            #         if claim_name in claims:
            #             policies.append({
            #                 'name': policy_name,
            #                 'claim': claim_name,
            #                 'value': claims[claim_name]
            #             })
            
            logger.info("Fetched policies from OAuth provider")
            
        except Exception as e:
            logger.error(f"OAuth policy fetch failed: {e}")
        
        return policies


class PolicyInheritanceManager:
    """
    Policy Inheritance Manager.
    
    Manages policy import from external sources:
    - LDAP/AD
    - OAuth/OIDC
    - Custom JSON/YAML files
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._connectors: Dict[str, PolicyConnector] = {}
    
    # ========================================================================
    # LDAP Policy Import
    # ========================================================================
    
    async def import_ldap_policies(
        self,
        ldap_config: LDAPConfig,
        tenant_id: str,
        created_by: UUID,
        db: Session
    ) -> ImportResult:
        """
        Import policies from LDAP/AD.
        
        Args:
            ldap_config: LDAP connection configuration
            tenant_id: Tenant context
            created_by: User performing import
            db: Database session
            
        Returns:
            ImportResult with import statistics
        """
        connector = LDAPConnector(ldap_config)
        
        try:
            # Test connection
            if not await connector.connect():
                return ImportResult(
                    success=False,
                    imported_count=0,
                    errors=["Failed to connect to LDAP server"]
                )
            
            # Create or update policy source
            source = await self._get_or_create_source(
                name=f"ldap_{ldap_config.url}",
                source_type=PolicySourceType.LDAP,
                config=ldap_config.model_dump(),
                tenant_id=tenant_id,
                created_by=created_by,
                db=db
            )
            
            # Fetch policies
            policies = await connector.fetch_policies()
            
            # Import policies
            result = await self._import_policies(
                policies=policies,
                source_id=source.id,
                tenant_id=tenant_id,
                created_by=created_by,
                attribute_mapping=ldap_config.attribute_mapping,
                db=db
            )
            
            # Update source status
            source.last_sync_at = datetime.utcnow()
            source.last_sync_status = PolicySyncStatus.SUCCESS if result.success else PolicySyncStatus.FAILED
            db.commit()
            
            return result
            
        except Exception as e:
            self.logger.error(f"LDAP import failed: {e}")
            return ImportResult(
                success=False,
                imported_count=0,
                errors=[str(e)]
            )
        finally:
            await connector.close()
    
    # ========================================================================
    # OAuth/OIDC Policy Import
    # ========================================================================
    
    async def import_oauth_claims(
        self,
        oauth_config: OAuthConfig,
        tenant_id: str,
        created_by: UUID,
        db: Session
    ) -> ImportResult:
        """
        Import policies from OAuth/OIDC claims.
        
        Args:
            oauth_config: OAuth configuration
            tenant_id: Tenant context
            created_by: User performing import
            db: Database session
            
        Returns:
            ImportResult with import statistics
        """
        connector = OAuthConnector(oauth_config)
        
        try:
            # Test connection
            if not await connector.connect():
                return ImportResult(
                    success=False,
                    imported_count=0,
                    errors=["Failed to connect to OAuth provider"]
                )
            
            # Create or update policy source
            source = await self._get_or_create_source(
                name=f"oauth_{oauth_config.provider_url}",
                source_type=PolicySourceType.OAUTH,
                config={
                    "provider_url": oauth_config.provider_url,
                    "client_id": oauth_config.client_id,
                    "scopes": oauth_config.scopes,
                    "claims_mapping": oauth_config.claims_mapping
                },
                tenant_id=tenant_id,
                created_by=created_by,
                db=db
            )
            
            # Fetch policies
            policies = await connector.fetch_policies()
            
            # Import policies
            result = await self._import_policies(
                policies=policies,
                source_id=source.id,
                tenant_id=tenant_id,
                created_by=created_by,
                attribute_mapping=oauth_config.claims_mapping,
                db=db
            )
            
            # Update source status
            source.last_sync_at = datetime.utcnow()
            source.last_sync_status = PolicySyncStatus.SUCCESS if result.success else PolicySyncStatus.FAILED
            db.commit()
            
            return result
            
        except Exception as e:
            self.logger.error(f"OAuth import failed: {e}")
            return ImportResult(
                success=False,
                imported_count=0,
                errors=[str(e)]
            )
    
    # ========================================================================
    # Custom Policy Import
    # ========================================================================
    
    async def import_custom_policies(
        self,
        policy_file: Union[str, Dict],
        format: str,
        tenant_id: str,
        created_by: UUID,
        db: Session,
        source_name: Optional[str] = None
    ) -> ImportResult:
        """
        Import custom JSON/YAML policies.
        
        Args:
            policy_file: Policy content (string or dict)
            format: Format type ("json" or "yaml")
            tenant_id: Tenant context
            created_by: User performing import
            db: Database session
            source_name: Optional source name
            
        Returns:
            ImportResult with import statistics
        """
        try:
            # Parse policy content
            if isinstance(policy_file, str):
                if format.lower() == "yaml":
                    policies = yaml.safe_load(policy_file)
                else:
                    policies = json.loads(policy_file)
            else:
                policies = policy_file
            
            # Ensure policies is a list
            if isinstance(policies, dict):
                if "policies" in policies:
                    policies = policies["policies"]
                else:
                    policies = [policies]
            
            # Create policy source
            source_type = PolicySourceType.CUSTOM_YAML if format.lower() == "yaml" else PolicySourceType.CUSTOM_JSON
            source = await self._get_or_create_source(
                name=source_name or f"custom_{format}_{datetime.utcnow().isoformat()}",
                source_type=source_type,
                config={"format": format, "policy_count": len(policies)},
                tenant_id=tenant_id,
                created_by=created_by,
                db=db
            )
            
            # Import policies
            result = await self._import_policies(
                policies=policies,
                source_id=source.id,
                tenant_id=tenant_id,
                created_by=created_by,
                db=db
            )
            
            # Update source status
            source.last_sync_at = datetime.utcnow()
            source.last_sync_status = PolicySyncStatus.SUCCESS if result.success else PolicySyncStatus.FAILED
            db.commit()
            
            return result
            
        except json.JSONDecodeError as e:
            return ImportResult(
                success=False,
                imported_count=0,
                errors=[f"Invalid JSON format: {e}"]
            )
        except yaml.YAMLError as e:
            return ImportResult(
                success=False,
                imported_count=0,
                errors=[f"Invalid YAML format: {e}"]
            )
        except Exception as e:
            self.logger.error(f"Custom policy import failed: {e}")
            return ImportResult(
                success=False,
                imported_count=0,
                errors=[str(e)]
            )
    
    # ========================================================================
    # Policy Synchronization
    # ========================================================================
    
    async def schedule_sync(
        self,
        source_id: UUID,
        cron_expression: str,
        tenant_id: str,
        db: Session
    ) -> bool:
        """
        Configure scheduled sync for a policy source.
        
        Args:
            source_id: Policy source ID
            cron_expression: Cron expression for schedule
            tenant_id: Tenant context
            db: Database session
            
        Returns:
            True if schedule was set
        """
        source = db.query(PolicySourceModel).filter(
            and_(
                PolicySourceModel.id == source_id,
                PolicySourceModel.tenant_id == tenant_id
            )
        ).first()
        
        if not source:
            return False
        
        source.sync_schedule = cron_expression
        db.commit()
        
        self.logger.info(f"Scheduled sync for source {source_id}: {cron_expression}")
        return True
    
    async def sync_policies(
        self,
        source_id: UUID,
        tenant_id: str,
        db: Session
    ) -> SyncResult:
        """
        Synchronize policies from an external source.
        
        Args:
            source_id: Policy source ID
            tenant_id: Tenant context
            db: Database session
            
        Returns:
            SyncResult with sync statistics
        """
        source = db.query(PolicySourceModel).filter(
            and_(
                PolicySourceModel.id == source_id,
                PolicySourceModel.tenant_id == tenant_id
            )
        ).first()
        
        if not source:
            return SyncResult(
                success=False,
                source_id=source_id,
                synced_at=datetime.utcnow(),
                errors=["Source not found"]
            )
        
        try:
            # Update status
            source.last_sync_status = PolicySyncStatus.SYNCING
            db.commit()
            
            # Perform sync based on source type
            if source.source_type == PolicySourceType.LDAP:
                config = LDAPConfig(**source.config)
                result = await self.import_ldap_policies(
                    ldap_config=config,
                    tenant_id=tenant_id,
                    created_by=source.created_by,
                    db=db
                )
            elif source.source_type in [PolicySourceType.OAUTH, PolicySourceType.OIDC]:
                config = OAuthConfig(**source.config)
                result = await self.import_oauth_claims(
                    oauth_config=config,
                    tenant_id=tenant_id,
                    created_by=source.created_by,
                    db=db
                )
            else:
                return SyncResult(
                    success=False,
                    source_id=source_id,
                    synced_at=datetime.utcnow(),
                    errors=["Custom sources cannot be synced automatically"]
                )
            
            return SyncResult(
                success=result.success,
                source_id=source_id,
                synced_at=datetime.utcnow(),
                added_count=result.imported_count,
                updated_count=result.updated_count,
                errors=result.errors
            )
            
        except Exception as e:
            self.logger.error(f"Policy sync failed: {e}")
            source.last_sync_status = PolicySyncStatus.FAILED
            source.last_sync_error = str(e)
            db.commit()
            
            return SyncResult(
                success=False,
                source_id=source_id,
                synced_at=datetime.utcnow(),
                errors=[str(e)]
            )
    
    # ========================================================================
    # Conflict Detection and Resolution
    # ========================================================================
    
    async def detect_conflicts(
        self,
        new_policies: List[Dict[str, Any]],
        tenant_id: str,
        db: Session
    ) -> List[PolicyConflict]:
        """
        Detect conflicts between new and existing policies.
        
        Args:
            new_policies: List of new policies to check
            tenant_id: Tenant context
            db: Database session
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        for policy in new_policies:
            # Check for duplicate permissions
            existing = db.query(DataPermissionModel).filter(
                and_(
                    DataPermissionModel.tenant_id == tenant_id,
                    DataPermissionModel.resource_type == policy.get("resource_type"),
                    DataPermissionModel.resource_id == policy.get("resource_id"),
                    DataPermissionModel.action == policy.get("action"),
                    DataPermissionModel.is_active == True
                )
            ).first()
            
            if existing:
                conflict = PolicyConflict(
                    id=uuid4(),
                    conflict_type="duplicate",
                    description=f"Permission already exists for {policy.get('resource_type')}:{policy.get('resource_id')}",
                    existing_policy={
                        "id": str(existing.id),
                        "resource_type": existing.resource_type,
                        "resource_id": existing.resource_id,
                        "action": existing.action.value if existing.action else None
                    },
                    new_policy=policy,
                    suggested_resolution="keep_existing"
                )
                conflicts.append(conflict)
        
        return conflicts
    
    async def resolve_conflict(
        self,
        conflict_id: UUID,
        resolution: ConflictResolution,
        tenant_id: str,
        db: Session
    ) -> bool:
        """
        Resolve a policy conflict.
        
        Args:
            conflict_id: Conflict ID
            resolution: Resolution strategy
            tenant_id: Tenant context
            db: Database session
            
        Returns:
            True if conflict was resolved
        """
        conflict = db.query(PolicyConflictModel).filter(
            and_(
                PolicyConflictModel.id == conflict_id,
                PolicyConflictModel.tenant_id == tenant_id,
                PolicyConflictModel.resolved == False
            )
        ).first()
        
        if not conflict:
            return False
        
        try:
            if resolution.resolution == "keep_existing":
                # Just mark as resolved
                pass
            elif resolution.resolution == "use_new":
                # Deactivate existing and create new
                existing_id = conflict.existing_policy.get("id")
                if existing_id:
                    existing = db.query(DataPermissionModel).filter(
                        DataPermissionModel.id == UUID(existing_id)
                    ).first()
                    if existing:
                        existing.is_active = False
                
                # Create new permission from conflict.new_policy
                await self._create_permission_from_policy(
                    policy=conflict.new_policy,
                    tenant_id=tenant_id,
                    db=db
                )
            elif resolution.resolution == "merge":
                # Merge policies based on merge_config
                if resolution.merge_config:
                    await self._merge_policies(
                        existing=conflict.existing_policy,
                        new=conflict.new_policy,
                        merge_config=resolution.merge_config,
                        tenant_id=tenant_id,
                        db=db
                    )
            
            conflict.resolved = True
            conflict.resolution = resolution.resolution
            conflict.resolved_at = datetime.utcnow()
            db.commit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Conflict resolution failed: {e}")
            db.rollback()
            return False
    
    # ========================================================================
    # Internal Methods
    # ========================================================================
    
    async def _get_or_create_source(
        self,
        name: str,
        source_type: PolicySourceType,
        config: Dict[str, Any],
        tenant_id: str,
        created_by: UUID,
        db: Session
    ) -> PolicySourceModel:
        """Get or create a policy source."""
        source = db.query(PolicySourceModel).filter(
            and_(
                PolicySourceModel.tenant_id == tenant_id,
                PolicySourceModel.name == name
            )
        ).first()
        
        if source:
            source.config = config
            source.updated_at = datetime.utcnow()
        else:
            source = PolicySourceModel(
                tenant_id=tenant_id,
                name=name,
                source_type=source_type,
                config=config,
                created_by=created_by
            )
            db.add(source)
        
        db.commit()
        db.refresh(source)
        return source
    
    async def _import_policies(
        self,
        policies: List[Dict[str, Any]],
        source_id: UUID,
        tenant_id: str,
        created_by: UUID,
        db: Session,
        attribute_mapping: Optional[Dict[str, str]] = None
    ) -> ImportResult:
        """Import policies into the database."""
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        conflicts = []
        errors = []
        
        for policy in policies:
            try:
                # Map attributes if mapping provided
                if attribute_mapping:
                    policy = self._apply_attribute_mapping(policy, attribute_mapping)
                
                # Check for conflicts
                policy_conflicts = await self.detect_conflicts([policy], tenant_id, db)
                if policy_conflicts:
                    conflicts.extend(policy_conflicts)
                    skipped_count += 1
                    continue
                
                # Create permission
                await self._create_permission_from_policy(
                    policy=policy,
                    tenant_id=tenant_id,
                    created_by=created_by,
                    db=db
                )
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Failed to import policy: {e}")
        
        return ImportResult(
            success=len(errors) == 0,
            imported_count=imported_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            conflicts=conflicts,
            errors=errors
        )
    
    def _apply_attribute_mapping(
        self,
        policy: Dict[str, Any],
        mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Apply attribute mapping to policy."""
        mapped = {}
        for key, value in policy.items():
            mapped_key = mapping.get(key, key)
            mapped[mapped_key] = value
        return mapped
    
    async def _create_permission_from_policy(
        self,
        policy: Dict[str, Any],
        tenant_id: str,
        db: Session,
        created_by: Optional[UUID] = None
    ) -> DataPermissionModel:
        """Create a permission from policy dict."""
        # Determine resource level
        resource_level = ResourceLevel.DATASET
        if policy.get("resource_level"):
            resource_level = ResourceLevel(policy["resource_level"])
        elif policy.get("field_name"):
            resource_level = ResourceLevel.FIELD
        elif policy.get("record_id"):
            resource_level = ResourceLevel.RECORD
        
        # Parse action
        action = DataPermissionAction.READ
        if policy.get("action"):
            action = DataPermissionAction(policy["action"])
        
        permission = DataPermissionModel(
            tenant_id=tenant_id,
            resource_level=resource_level,
            resource_type=policy.get("resource_type", "dataset"),
            resource_id=policy.get("resource_id", "*"),
            field_name=policy.get("field_name"),
            user_id=UUID(policy["user_id"]) if policy.get("user_id") else None,
            role_id=UUID(policy["role_id"]) if policy.get("role_id") else None,
            action=action,
            conditions=policy.get("conditions"),
            tags=policy.get("tags"),
            granted_by=created_by or UUID("00000000-0000-0000-0000-000000000000")
        )
        
        db.add(permission)
        db.commit()
        db.refresh(permission)
        
        return permission
    
    async def _merge_policies(
        self,
        existing: Dict[str, Any],
        new: Dict[str, Any],
        merge_config: Dict[str, Any],
        tenant_id: str,
        db: Session
    ) -> None:
        """Merge two policies based on merge configuration."""
        # Implementation depends on merge strategy
        # For now, just update conditions
        existing_id = existing.get("id")
        if existing_id:
            perm = db.query(DataPermissionModel).filter(
                DataPermissionModel.id == UUID(existing_id)
            ).first()
            
            if perm and merge_config.get("merge_conditions"):
                existing_conditions = perm.conditions or {}
                new_conditions = new.get("conditions", {})
                perm.conditions = {**existing_conditions, **new_conditions}
                db.commit()


# Global instance
_policy_inheritance_manager: Optional[PolicyInheritanceManager] = None


def get_policy_inheritance_manager() -> PolicyInheritanceManager:
    """Get or create the global policy inheritance manager instance."""
    global _policy_inheritance_manager
    if _policy_inheritance_manager is None:
        _policy_inheritance_manager = PolicyInheritanceManager()
    return _policy_inheritance_manager
