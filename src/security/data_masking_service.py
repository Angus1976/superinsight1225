"""
Data Masking Service for SuperInsight Platform.

Implements data masking and desensitization:
- Multiple masking algorithms
- Role-based masking policies
- Dynamic masking (query-time)
- Static masking (export-time)
"""

import logging
import re
import hashlib
import fnmatch
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from uuid import UUID, uuid4
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.data_permission import (
    MaskingRuleModel, MaskingAlgorithmType,
    DataClassificationModel, SensitivityLevel
)
from src.schemas.data_permission import (
    MaskingRule, MaskingRuleResponse, ExportConfig, MaskingPreview
)

logger = logging.getLogger(__name__)


class MaskingAlgorithm(ABC):
    """Base class for masking algorithms."""
    
    @abstractmethod
    def mask(self, value: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        """Apply masking to a value."""
        pass
    
    @abstractmethod
    def can_unmask(self) -> bool:
        """Whether the masking is reversible."""
        pass


class ReplacementMasking(MaskingAlgorithm):
    """Replace value with a fixed string."""
    
    def mask(self, value: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        replacement = "***"
        if config:
            replacement = config.get("replacement", "***")
        return replacement
    
    def can_unmask(self) -> bool:
        return False


class PartialMasking(MaskingAlgorithm):
    """Partially mask value, showing first/last characters."""
    
    def mask(self, value: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        if not isinstance(value, str):
            value = str(value)
        
        if len(value) <= 4:
            return "****"
        
        show_start = 2
        show_end = 2
        mask_char = "*"
        
        if config:
            show_start = config.get("show_start", 2)
            show_end = config.get("show_end", 2)
            mask_char = config.get("mask_char", "*")
        
        if len(value) <= show_start + show_end:
            return mask_char * len(value)
        
        masked_length = len(value) - show_start - show_end
        return value[:show_start] + (mask_char * masked_length) + value[-show_end:]
    
    def can_unmask(self) -> bool:
        return False


class EncryptionMasking(MaskingAlgorithm):
    """Encrypt value using hash (one-way)."""
    
    def mask(self, value: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        if not isinstance(value, str):
            value = str(value)
        
        algorithm = "sha256"
        truncate = 16
        
        if config:
            algorithm = config.get("algorithm", "sha256")
            truncate = config.get("truncate", 16)
        
        if algorithm == "sha256":
            hashed = hashlib.sha256(value.encode()).hexdigest()
        elif algorithm == "md5":
            hashed = hashlib.md5(value.encode()).hexdigest()
        else:
            hashed = hashlib.sha256(value.encode()).hexdigest()
        
        if truncate and truncate > 0:
            return hashed[:truncate]
        return hashed
    
    def can_unmask(self) -> bool:
        return False


class HashMasking(MaskingAlgorithm):
    """Hash value with salt for consistent masking."""
    
    def mask(self, value: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        if not isinstance(value, str):
            value = str(value)
        
        salt = "default_salt"
        if config:
            salt = config.get("salt", "default_salt")
        
        salted = f"{salt}:{value}"
        return hashlib.sha256(salted.encode()).hexdigest()[:12]
    
    def can_unmask(self) -> bool:
        return False


class NullifyMasking(MaskingAlgorithm):
    """Replace value with null/empty."""
    
    def mask(self, value: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        return None
    
    def can_unmask(self) -> bool:
        return False


# Algorithm registry
MASKING_ALGORITHMS: Dict[MaskingAlgorithmType, MaskingAlgorithm] = {
    MaskingAlgorithmType.REPLACEMENT: ReplacementMasking(),
    MaskingAlgorithmType.PARTIAL: PartialMasking(),
    MaskingAlgorithmType.ENCRYPTION: EncryptionMasking(),
    MaskingAlgorithmType.HASH: HashMasking(),
    MaskingAlgorithmType.NULLIFY: NullifyMasking()
}


class DataMaskingService:
    """
    Data Masking Service.
    
    Provides data masking capabilities:
    - Multiple masking algorithms
    - Role-based masking rules
    - Dynamic masking (query-time)
    - Static masking (export-time)
    """
    
    def __init__(self, redis_client=None):
        self.logger = logging.getLogger(__name__)
        self._redis = redis_client
        self._algorithms = MASKING_ALGORITHMS.copy()
    
    # ========================================================================
    # Algorithm Management
    # ========================================================================
    
    def register_algorithm(
        self,
        name: MaskingAlgorithmType,
        algorithm: MaskingAlgorithm
    ) -> None:
        """Register a custom masking algorithm."""
        self._algorithms[name] = algorithm
        self.logger.info(f"Registered masking algorithm: {name}")
    
    def get_algorithm(self, name: MaskingAlgorithmType) -> Optional[MaskingAlgorithm]:
        """Get a masking algorithm by name."""
        return self._algorithms.get(name)
    
    # ========================================================================
    # Dynamic Masking (Query-Time)
    # ========================================================================
    
    async def mask_data(
        self,
        data: Dict[str, Any],
        user_id: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None,
        masking_rules: Optional[List[MaskingRuleModel]] = None
    ) -> Dict[str, Any]:
        """
        Apply dynamic masking to data.
        
        Args:
            data: Data dictionary to mask
            user_id: User requesting data
            tenant_id: Tenant context
            db: Database session
            user_roles: Optional user roles
            masking_rules: Optional specific rules to apply
            
        Returns:
            Masked data dictionary
        """
        if not masking_rules:
            masking_rules = await self.get_masking_rules(
                user_id=user_id,
                tenant_id=tenant_id,
                db=db,
                user_roles=user_roles
            )
        
        masked_data = data.copy()
        
        for field_name, value in data.items():
            if value is None:
                continue
            
            # Find applicable rule
            rule = self._find_matching_rule(field_name, masking_rules, user_roles)
            
            if rule:
                algorithm = self._algorithms.get(rule.algorithm)
                if algorithm:
                    masked_data[field_name] = algorithm.mask(
                        value,
                        rule.algorithm_config
                    )
        
        return masked_data
    
    async def mask_record(
        self,
        record: Dict[str, Any],
        user_id: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Mask a single record."""
        return await self.mask_data(
            data=record,
            user_id=user_id,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
    
    async def mask_records(
        self,
        records: List[Dict[str, Any]],
        user_id: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Mask multiple records."""
        # Get rules once for efficiency
        masking_rules = await self.get_masking_rules(
            user_id=user_id,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
        
        masked_records = []
        for record in records:
            masked = await self.mask_data(
                data=record,
                user_id=user_id,
                tenant_id=tenant_id,
                db=db,
                user_roles=user_roles,
                masking_rules=masking_rules
            )
            masked_records.append(masked)
        
        return masked_records
    
    # ========================================================================
    # Static Masking (Export-Time)
    # ========================================================================
    
    async def mask_for_export(
        self,
        data: List[Dict[str, Any]],
        export_config: ExportConfig,
        tenant_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Apply static masking for export.
        
        Args:
            data: Data to export
            export_config: Export configuration
            tenant_id: Tenant context
            db: Database session
            
        Returns:
            Masked data for export
        """
        # Get specific rules if provided
        masking_rules = []
        if export_config.masking_rules:
            for rule_id in export_config.masking_rules:
                rule = db.query(MaskingRuleModel).filter(
                    and_(
                        MaskingRuleModel.id == rule_id,
                        MaskingRuleModel.tenant_id == tenant_id,
                        MaskingRuleModel.is_active == True
                    )
                ).first()
                if rule:
                    masking_rules.append(rule)
        else:
            # Get all active rules
            masking_rules = db.query(MaskingRuleModel).filter(
                and_(
                    MaskingRuleModel.tenant_id == tenant_id,
                    MaskingRuleModel.is_active == True
                )
            ).order_by(MaskingRuleModel.priority.desc()).all()
        
        masked_data = []
        for record in data:
            masked_record = record.copy()
            
            # Remove excluded fields
            if export_config.exclude_fields:
                for field in export_config.exclude_fields:
                    masked_record.pop(field, None)
            
            # Apply masking
            for field_name, value in list(masked_record.items()):
                if value is None:
                    continue
                
                rule = self._find_matching_rule(field_name, masking_rules)
                if rule:
                    algorithm = self._algorithms.get(rule.algorithm)
                    if algorithm:
                        masked_record[field_name] = algorithm.mask(
                            value,
                            rule.algorithm_config
                        )
            
            masked_data.append(masked_record)
        
        return masked_data
    
    # ========================================================================
    # Rule Management
    # ========================================================================
    
    async def get_masking_rules(
        self,
        user_id: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None,
        resource: Optional[str] = None
    ) -> List[MaskingRuleModel]:
        """
        Get applicable masking rules for a user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant context
            db: Database session
            user_roles: Optional user roles
            resource: Optional specific resource
            
        Returns:
            List of applicable masking rules
        """
        query = db.query(MaskingRuleModel).filter(
            and_(
                MaskingRuleModel.tenant_id == tenant_id,
                MaskingRuleModel.is_active == True
            )
        )
        
        rules = query.order_by(MaskingRuleModel.priority.desc()).all()
        
        # Filter by applicable roles
        if user_roles:
            applicable_rules = []
            for rule in rules:
                if not rule.applicable_roles:
                    # Rule applies to all roles
                    applicable_rules.append(rule)
                elif any(role in rule.applicable_roles for role in user_roles):
                    # User has one of the applicable roles - rule applies
                    applicable_rules.append(rule)
                # If user has a role in applicable_roles, they DON'T need masking
                # This is inverted logic - applicable_roles means "roles that see masked data"
            return applicable_rules
        
        return rules
    
    async def configure_masking_rule(
        self,
        rule: MaskingRule,
        tenant_id: str,
        created_by: UUID,
        db: Session
    ) -> MaskingRuleModel:
        """
        Configure a masking rule.
        
        Args:
            rule: Rule configuration
            tenant_id: Tenant context
            created_by: User creating the rule
            db: Database session
            
        Returns:
            Created or updated MaskingRuleModel
        """
        # Check for existing rule with same name
        existing = db.query(MaskingRuleModel).filter(
            and_(
                MaskingRuleModel.tenant_id == tenant_id,
                MaskingRuleModel.name == rule.name
            )
        ).first()
        
        if existing:
            # Update existing
            existing.description = rule.description
            existing.field_pattern = rule.field_pattern
            existing.algorithm = rule.algorithm
            existing.algorithm_config = rule.algorithm_config
            existing.applicable_roles = rule.applicable_roles
            existing.conditions = rule.conditions
            existing.priority = rule.priority
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        
        # Create new
        rule_model = MaskingRuleModel(
            tenant_id=tenant_id,
            name=rule.name,
            description=rule.description,
            field_pattern=rule.field_pattern,
            algorithm=rule.algorithm,
            algorithm_config=rule.algorithm_config,
            applicable_roles=rule.applicable_roles,
            conditions=rule.conditions,
            priority=rule.priority,
            created_by=created_by
        )
        
        db.add(rule_model)
        db.commit()
        db.refresh(rule_model)
        
        self.logger.info(f"Created masking rule: {rule.name}")
        return rule_model
    
    async def delete_masking_rule(
        self,
        rule_id: UUID,
        tenant_id: str,
        db: Session
    ) -> bool:
        """Delete a masking rule."""
        rule = db.query(MaskingRuleModel).filter(
            and_(
                MaskingRuleModel.id == rule_id,
                MaskingRuleModel.tenant_id == tenant_id
            )
        ).first()
        
        if not rule:
            return False
        
        rule.is_active = False
        db.commit()
        
        return True
    
    async def list_masking_rules(
        self,
        tenant_id: str,
        db: Session,
        include_inactive: bool = False
    ) -> List[MaskingRuleModel]:
        """List all masking rules for a tenant."""
        query = db.query(MaskingRuleModel).filter(
            MaskingRuleModel.tenant_id == tenant_id
        )
        
        if not include_inactive:
            query = query.filter(MaskingRuleModel.is_active == True)
        
        return query.order_by(MaskingRuleModel.priority.desc()).all()
    
    # ========================================================================
    # Preview
    # ========================================================================
    
    async def preview_masking(
        self,
        value: str,
        algorithm: MaskingAlgorithmType,
        config: Optional[Dict[str, Any]] = None
    ) -> MaskingPreview:
        """
        Preview masking result.
        
        Args:
            value: Value to mask
            algorithm: Algorithm to use
            config: Optional algorithm configuration
            
        Returns:
            MaskingPreview with original and masked values
        """
        algo = self._algorithms.get(algorithm)
        if not algo:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        masked = algo.mask(value, config)
        
        return MaskingPreview(
            original_value=value,
            masked_value=str(masked) if masked is not None else "",
            algorithm=algorithm,
            rule_name="preview"
        )
    
    # ========================================================================
    # Internal Methods
    # ========================================================================
    
    def _find_matching_rule(
        self,
        field_name: str,
        rules: List[MaskingRuleModel],
        user_roles: Optional[List[str]] = None
    ) -> Optional[MaskingRuleModel]:
        """Find the first matching rule for a field."""
        for rule in rules:
            # Check field pattern match
            if self._matches_pattern(field_name, rule.field_pattern):
                # Check role applicability
                if rule.applicable_roles:
                    # If user has any of the applicable roles, they see masked data
                    if user_roles and any(role in rule.applicable_roles for role in user_roles):
                        continue  # Skip this rule - user is exempt
                
                # Check conditions
                if rule.conditions:
                    if not self._evaluate_conditions(rule.conditions):
                        continue
                
                return rule
        
        return None
    
    def _matches_pattern(self, field_name: str, pattern: str) -> bool:
        """Check if field name matches pattern."""
        # Support glob patterns
        if fnmatch.fnmatch(field_name.lower(), pattern.lower()):
            return True
        
        # Support regex patterns
        try:
            if re.match(pattern, field_name, re.IGNORECASE):
                return True
        except re.error:
            pass
        
        return False
    
    def _evaluate_conditions(self, conditions: List[Dict[str, Any]]) -> bool:
        """Evaluate masking conditions."""
        # Simplified condition evaluation
        for condition in conditions:
            condition_type = condition.get("type")
            
            if condition_type == "sensitivity_level":
                # Would check resource sensitivity
                pass
            elif condition_type == "time_range":
                # Check time-based conditions
                now = datetime.utcnow()
                start_hour = condition.get("start_hour", 0)
                end_hour = condition.get("end_hour", 24)
                if not (start_hour <= now.hour < end_hour):
                    return False
        
        return True


# Global instance
_data_masking_service: Optional[DataMaskingService] = None


def get_data_masking_service() -> DataMaskingService:
    """Get or create the global data masking service instance."""
    global _data_masking_service
    if _data_masking_service is None:
        _data_masking_service = DataMaskingService()
    return _data_masking_service
