"""
Field-level Access Control for sensitive data protection.

Provides fine-grained field access control with masking, hashing, and
conditional access based on user roles and permissions.
"""

import logging
import hashlib
import re
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from dataclasses import dataclass

from src.database.connection import get_db_session
from .models import (
    FieldPermissionModel, FieldAccessLevel, DataAccessAuditModel,
    AuditEventType
)
from .permission_manager import PermissionManager
from .tenant_isolation import tenant_context

logger = logging.getLogger(__name__)


@dataclass
class FieldAccessResult:
    """Result of field access check."""
    allowed: bool
    access_level: FieldAccessLevel
    masked_value: Optional[Any] = None
    reason: str = ""


class FieldAccessController:
    """
    Field-level access control service.
    
    Provides fine-grained control over field access with masking,
    hashing, and conditional access policies.
    """
    
    def __init__(self, permission_manager: Optional[PermissionManager] = None):
        self.permission_manager = permission_manager or PermissionManager()
        
        # Default masking patterns
        self.masking_patterns = {
            "email": self._mask_email,
            "phone": self._mask_phone,
            "ssn": self._mask_ssn,
            "credit_card": self._mask_credit_card,
            "partial": self._mask_partial,
            "full": self._mask_full,
            "hash": self._hash_value
        }
    
    def check_field_access(
        self,
        user_id: UUID,
        tenant_id: str,
        table_name: str,
        field_name: str,
        field_value: Any,
        context: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> FieldAccessResult:
        """
        Check field access and apply appropriate masking.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            table_name: Table name
            field_name: Field name
            field_value: Original field value
            context: Additional context for access decision
            db: Database session
            
        Returns:
            FieldAccessResult with access decision and masked value
        """
        if db is None:
            db = next(get_db_session())
        
        try:
            # Get field permission
            field_permission = self._get_field_permission(
                user_id, tenant_id, table_name, field_name, db
            )
            
            if not field_permission:
                # Default to full access if no specific permission
                return FieldAccessResult(
                    allowed=True,
                    access_level=FieldAccessLevel.FULL,
                    masked_value=field_value,
                    reason="No specific field permission - default access"
                )
            
            # Check access level
            access_level = field_permission.access_level
            
            if access_level == FieldAccessLevel.DENIED:
                self._log_field_access(
                    user_id, tenant_id, table_name, field_name,
                    access_level, False, context, db
                )
                return FieldAccessResult(
                    allowed=False,
                    access_level=access_level,
                    reason="Field access denied"
                )
            
            # Apply masking based on access level
            masked_value = self._apply_masking(
                field_value, access_level, field_permission.masking_config
            )
            
            # Log field access
            self._log_field_access(
                user_id, tenant_id, table_name, field_name,
                access_level, True, context, db
            )
            
            return FieldAccessResult(
                allowed=True,
                access_level=access_level,
                masked_value=masked_value,
                reason=f"Field access granted with {access_level.value} level"
            )
            
        except Exception as e:
            logger.error(f"Error checking field access: {e}")
            return FieldAccessResult(
                allowed=False,
                access_level=FieldAccessLevel.DENIED,
                reason=f"Field access check failed: {str(e)}"
            )
    
    def filter_record_fields(
        self,
        user_id: UUID,
        tenant_id: str,
        table_name: str,
        record_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Filter record fields based on user permissions.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            table_name: Table name
            record_data: Original record data
            context: Additional context
            db: Database session
            
        Returns:
            Filtered record data with appropriate masking
        """
        if db is None:
            db = next(get_db_session())
        
        filtered_data = {}
        
        for field_name, field_value in record_data.items():
            access_result = self.check_field_access(
                user_id, tenant_id, table_name, field_name,
                field_value, context, db
            )
            
            if access_result.allowed:
                filtered_data[field_name] = access_result.masked_value
            # Denied fields are simply omitted from the result
        
        return filtered_data
    
    def filter_query_results(
        self,
        user_id: UUID,
        tenant_id: str,
        table_name: str,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter query results based on field permissions.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            table_name: Table name
            results: List of record dictionaries
            context: Additional context
            db: Database session
            
        Returns:
            Filtered results with appropriate field masking
        """
        filtered_results = []
        
        for record in results:
            filtered_record = self.filter_record_fields(
                user_id, tenant_id, table_name, record, context, db
            )
            filtered_results.append(filtered_record)
        
        return filtered_results
    
    def get_accessible_fields(
        self,
        user_id: UUID,
        tenant_id: str,
        table_name: str,
        db: Optional[Session] = None
    ) -> Dict[str, FieldAccessLevel]:
        """
        Get all accessible fields for user on table.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            table_name: Table name
            db: Database session
            
        Returns:
            Dictionary mapping field names to access levels
        """
        if db is None:
            db = next(get_db_session())
        
        # Get user's role IDs
        user_role_ids = self._get_user_role_ids(user_id, tenant_id, db)
        
        # Get field permissions for user and roles
        field_permissions = db.query(FieldPermissionModel).filter(
            and_(
                FieldPermissionModel.tenant_id == tenant_id,
                FieldPermissionModel.table_name == table_name,
                or_(
                    FieldPermissionModel.user_id == user_id,
                    FieldPermissionModel.role_id.in_(user_role_ids)
                )
            )
        ).all()
        
        accessible_fields = {}
        
        for perm in field_permissions:
            field_name = perm.field_name
            access_level = perm.access_level
            
            # User-specific permissions override role permissions
            if perm.user_id == user_id:
                accessible_fields[field_name] = access_level
            elif field_name not in accessible_fields:
                accessible_fields[field_name] = access_level
        
        return accessible_fields
    
    def set_field_masking_rule(
        self,
        tenant_id: str,
        table_name: str,
        field_name: str,
        masking_type: str,
        masking_config: Optional[Dict[str, Any]] = None,
        role_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        db: Optional[Session] = None
    ) -> bool:
        """
        Set field masking rule.
        
        Args:
            tenant_id: Tenant ID
            table_name: Table name
            field_name: Field name
            masking_type: Type of masking (email, phone, partial, etc.)
            masking_config: Additional masking configuration
            role_id: Role ID (if role-based)
            user_id: User ID (if user-specific)
            created_by: User who created the rule
            db: Database session
            
        Returns:
            True if rule set successfully
        """
        if db is None:
            db = next(get_db_session())
        
        # Determine access level based on masking type
        if masking_type == "deny":
            access_level = FieldAccessLevel.DENIED
        elif masking_type == "hash":
            access_level = FieldAccessLevel.HASHED
        elif masking_type in ["email", "phone", "ssn", "credit_card", "partial", "full"]:
            access_level = FieldAccessLevel.MASKED
        else:
            access_level = FieldAccessLevel.FULL
        
        # Prepare masking config
        config = masking_config or {}
        config["masking_type"] = masking_type
        
        try:
            # Check if rule already exists
            existing = db.query(FieldPermissionModel).filter(
                and_(
                    FieldPermissionModel.tenant_id == tenant_id,
                    FieldPermissionModel.table_name == table_name,
                    FieldPermissionModel.field_name == field_name,
                    FieldPermissionModel.role_id == role_id if role_id else True,
                    FieldPermissionModel.user_id == user_id if user_id else True
                )
            ).first()
            
            if existing:
                # Update existing rule
                existing.access_level = access_level
                existing.masking_config = config
            else:
                # Create new rule
                field_permission = FieldPermissionModel(
                    tenant_id=tenant_id,
                    table_name=table_name,
                    field_name=field_name,
                    role_id=role_id,
                    user_id=user_id,
                    access_level=access_level,
                    masking_config=config,
                    created_by=created_by
                )
                db.add(field_permission)
            
            db.commit()
            logger.info(f"Field masking rule set: {table_name}.{field_name} -> {masking_type}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error setting field masking rule: {e}")
            return False
    
    def _get_field_permission(
        self,
        user_id: UUID,
        tenant_id: str,
        table_name: str,
        field_name: str,
        db: Session
    ) -> Optional[FieldPermissionModel]:
        """Get field permission for user (user-specific takes precedence over role-based)."""
        
        # First check user-specific permission
        user_permission = db.query(FieldPermissionModel).filter(
            and_(
                FieldPermissionModel.tenant_id == tenant_id,
                FieldPermissionModel.table_name == table_name,
                FieldPermissionModel.field_name == field_name,
                FieldPermissionModel.user_id == user_id
            )
        ).first()
        
        if user_permission:
            return user_permission
        
        # Then check role-based permissions
        user_role_ids = self._get_user_role_ids(user_id, tenant_id, db)
        
        role_permission = db.query(FieldPermissionModel).filter(
            and_(
                FieldPermissionModel.tenant_id == tenant_id,
                FieldPermissionModel.table_name == table_name,
                FieldPermissionModel.field_name == field_name,
                FieldPermissionModel.role_id.in_(user_role_ids)
            )
        ).first()
        
        return role_permission
    
    def _get_user_role_ids(self, user_id: UUID, tenant_id: str, db: Session) -> List[UUID]:
        """Get role IDs for user."""
        from .models import UserRoleModel
        from datetime import datetime
        
        user_roles = db.query(UserRoleModel).filter(
            and_(
                UserRoleModel.user_id == user_id,
                UserRoleModel.tenant_id == tenant_id,
                UserRoleModel.is_active == True,
                or_(
                    UserRoleModel.valid_until.is_(None),
                    UserRoleModel.valid_until > datetime.utcnow()
                )
            )
        ).all()
        
        return [ur.role_id for ur in user_roles]
    
    def _apply_masking(
        self,
        value: Any,
        access_level: FieldAccessLevel,
        masking_config: Dict[str, Any]
    ) -> Any:
        """Apply masking based on access level and configuration."""
        
        if value is None:
            return None
        
        if access_level == FieldAccessLevel.FULL:
            return value
        
        if access_level == FieldAccessLevel.DENIED:
            return None
        
        # Convert to string for masking
        str_value = str(value)
        
        if access_level == FieldAccessLevel.HASHED:
            return self._hash_value(str_value)
        
        if access_level == FieldAccessLevel.MASKED:
            masking_type = masking_config.get("masking_type", "partial")
            
            if masking_type in self.masking_patterns:
                return self.masking_patterns[masking_type](str_value, masking_config)
            else:
                # Default to partial masking
                return self._mask_partial(str_value, masking_config)
        
        return value
    
    def _mask_email(self, email: str, config: Dict[str, Any]) -> str:
        """Mask email address."""
        if "@" not in email:
            return self._mask_partial(email, config)
        
        local, domain = email.split("@", 1)
        
        if len(local) <= 2:
            masked_local = "*" * len(local)
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"
    
    def _mask_phone(self, phone: str, config: Dict[str, Any]) -> str:
        """Mask phone number."""
        # Remove non-digits
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) < 4:
            return "*" * len(phone)
        
        # Keep last 4 digits
        masked_digits = "*" * (len(digits) - 4) + digits[-4:]
        
        # Preserve original format
        result = phone
        digit_index = 0
        for i, char in enumerate(phone):
            if char.isdigit():
                if digit_index < len(masked_digits):
                    result = result[:i] + masked_digits[digit_index] + result[i+1:]
                    digit_index += 1
        
        return result
    
    def _mask_ssn(self, ssn: str, config: Dict[str, Any]) -> str:
        """Mask SSN."""
        # Remove non-digits
        digits = re.sub(r'\D', '', ssn)
        
        if len(digits) != 9:
            return self._mask_partial(ssn, config)
        
        # Show only last 4 digits
        return "***-**-" + digits[-4:]
    
    def _mask_credit_card(self, cc: str, config: Dict[str, Any]) -> str:
        """Mask credit card number."""
        # Remove non-digits
        digits = re.sub(r'\D', '', cc)
        
        if len(digits) < 8:
            return "*" * len(cc)
        
        # Show first 4 and last 4 digits
        masked = digits[:4] + "*" * (len(digits) - 8) + digits[-4:]
        
        # Add spacing every 4 digits
        return " ".join([masked[i:i+4] for i in range(0, len(masked), 4)])
    
    def _mask_partial(self, value: str, config: Dict[str, Any]) -> str:
        """Partial masking - show first and last characters."""
        if len(value) <= 2:
            return "*" * len(value)
        
        show_chars = config.get("show_chars", 1)
        mask_char = config.get("mask_char", "*")
        
        if len(value) <= 2 * show_chars:
            return mask_char * len(value)
        
        return (
            value[:show_chars] +
            mask_char * (len(value) - 2 * show_chars) +
            value[-show_chars:]
        )
    
    def _mask_full(self, value: str, config: Dict[str, Any]) -> str:
        """Full masking - replace entire value."""
        mask_char = config.get("mask_char", "*")
        return mask_char * len(value)
    
    def _hash_value(self, value: str, config: Dict[str, Any] = None) -> str:
        """Hash value using SHA-256."""
        return hashlib.sha256(value.encode()).hexdigest()[:16]  # First 16 chars
    
    def _log_field_access(
        self,
        user_id: UUID,
        tenant_id: str,
        table_name: str,
        field_name: str,
        access_level: FieldAccessLevel,
        granted: bool,
        context: Optional[Dict[str, Any]],
        db: Session
    ) -> None:
        """Log field access for audit purposes."""
        try:
            audit_log = DataAccessAuditModel(
                tenant_id=tenant_id,
                user_id=user_id,
                event_type=AuditEventType.FIELD_ACCESS,
                table_name=table_name,
                field_names=[field_name],
                permission_granted=granted,
                request_context=context or {},
                response_context={
                    "access_level": access_level.value,
                    "field_name": field_name
                }
            )
            
            db.add(audit_log)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging field access: {e}")
            db.rollback()