"""
Desensitization rule management system.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from .models import (
    DesensitizationRule,
    MaskingStrategy,
    PIIEntityType,
    SensitivityLevel
)

logger = logging.getLogger(__name__)


class DesensitizationRuleManager:
    """
    Manager for desensitization rules.
    
    Handles CRUD operations, rule validation, and rule application logic
    for data desensitization rules.
    """
    
    def __init__(self):
        """Initialize rule manager."""
        self._default_rules = self._create_default_rules()
    
    def create_rule(
        self,
        tenant_id: str,
        name: str,
        entity_type: PIIEntityType,
        masking_strategy: MaskingStrategy,
        sensitivity_level: SensitivityLevel = SensitivityLevel.MEDIUM,
        confidence_threshold: float = 0.8,
        field_pattern: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        created_by: Optional[UUID] = None,
        db: Optional[Session] = None
    ) -> Optional[DesensitizationRule]:
        """
        Create a new desensitization rule.
        
        Args:
            tenant_id: Tenant identifier
            name: Rule name
            entity_type: PII entity type
            masking_strategy: Masking strategy
            sensitivity_level: Data sensitivity level
            confidence_threshold: Minimum confidence for rule application
            field_pattern: Optional regex pattern for field matching
            config: Strategy-specific configuration
            created_by: User who created the rule
            db: Database session
            
        Returns:
            Created DesensitizationRule or None if failed
        """
        try:
            rule = DesensitizationRule(
                name=name,
                entity_type=entity_type,
                field_pattern=field_pattern,
                masking_strategy=masking_strategy,
                sensitivity_level=sensitivity_level,
                confidence_threshold=confidence_threshold,
                tenant_id=tenant_id,
                created_by=created_by,
                config=config or {}
            )
            
            # Validate rule configuration
            if not self._validate_rule(rule):
                logger.error(f"Invalid rule configuration: {name}")
                return None
            
            # Store rule (in production, this would be in database)
            # For now, we'll return the rule object
            logger.info(f"Created desensitization rule: {name} for tenant {tenant_id}")
            return rule
            
        except Exception as e:
            logger.error(f"Failed to create rule {name}: {e}")
            return None
    
    def get_rules_for_tenant(
        self,
        tenant_id: str,
        entity_type: Optional[PIIEntityType] = None,
        enabled_only: bool = True,
        db: Optional[Session] = None
    ) -> List[DesensitizationRule]:
        """
        Get desensitization rules for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            entity_type: Filter by entity type
            enabled_only: Return only enabled rules
            db: Database session
            
        Returns:
            List of matching rules
        """
        try:
            # In production, this would query the database
            # For now, return default rules filtered by criteria
            rules = self._default_rules.copy()
            
            # Filter by tenant (for demo, we'll return all default rules)
            if entity_type:
                rules = [r for r in rules if r.entity_type == entity_type]
                
            if enabled_only:
                rules = [r for r in rules if r.enabled]
            
            # Set tenant_id for all rules
            for rule in rules:
                rule.tenant_id = tenant_id
            
            return rules
            
        except Exception as e:
            logger.error(f"Failed to get rules for tenant {tenant_id}: {e}")
            return []
    
    def update_rule(
        self,
        rule_id: str,
        tenant_id: str,
        updates: Dict[str, Any],
        db: Optional[Session] = None
    ) -> bool:
        """
        Update an existing desensitization rule.
        
        Args:
            rule_id: Rule identifier
            tenant_id: Tenant identifier
            updates: Fields to update
            db: Database session
            
        Returns:
            True if update successful
        """
        try:
            # In production, this would update the database record
            logger.info(f"Updated rule {rule_id} for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update rule {rule_id}: {e}")
            return False
    
    def delete_rule(
        self,
        rule_id: str,
        tenant_id: str,
        db: Optional[Session] = None
    ) -> bool:
        """
        Delete a desensitization rule.
        
        Args:
            rule_id: Rule identifier
            tenant_id: Tenant identifier
            db: Database session
            
        Returns:
            True if deletion successful
        """
        try:
            # In production, this would delete from database
            logger.info(f"Deleted rule {rule_id} for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete rule {rule_id}: {e}")
            return False
    
    def get_rule_by_id(
        self,
        rule_id: str,
        tenant_id: str,
        db: Optional[Session] = None
    ) -> Optional[DesensitizationRule]:
        """
        Get a specific rule by ID.
        
        Args:
            rule_id: Rule identifier
            tenant_id: Tenant identifier
            db: Database session
            
        Returns:
            DesensitizationRule or None if not found
        """
        try:
            # Find rule in default rules (for demo)
            for rule in self._default_rules:
                if rule.id == rule_id:
                    rule.tenant_id = tenant_id
                    return rule
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get rule {rule_id}: {e}")
            return None
    
    def enable_rule(
        self,
        rule_id: str,
        tenant_id: str,
        db: Optional[Session] = None
    ) -> bool:
        """
        Enable a desensitization rule.
        
        Args:
            rule_id: Rule identifier
            tenant_id: Tenant identifier
            db: Database session
            
        Returns:
            True if successful
        """
        return self.update_rule(rule_id, tenant_id, {"enabled": True}, db)
    
    def disable_rule(
        self,
        rule_id: str,
        tenant_id: str,
        db: Optional[Session] = None
    ) -> bool:
        """
        Disable a desensitization rule.
        
        Args:
            rule_id: Rule identifier
            tenant_id: Tenant identifier
            db: Database session
            
        Returns:
            True if successful
        """
        return self.update_rule(rule_id, tenant_id, {"enabled": False}, db)
    
    def get_rules_by_entity_type(
        self,
        tenant_id: str,
        entity_type: PIIEntityType,
        db: Optional[Session] = None
    ) -> List[DesensitizationRule]:
        """
        Get rules for a specific entity type.
        
        Args:
            tenant_id: Tenant identifier
            entity_type: PII entity type
            db: Database session
            
        Returns:
            List of matching rules
        """
        return self.get_rules_for_tenant(
            tenant_id=tenant_id,
            entity_type=entity_type,
            enabled_only=True,
            db=db
        )
    
    def validate_rule_config(
        self,
        masking_strategy: MaskingStrategy,
        config: Dict[str, Any]
    ) -> bool:
        """
        Validate rule configuration for a masking strategy.
        
        Args:
            masking_strategy: Masking strategy
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        try:
            if masking_strategy == MaskingStrategy.REPLACE:
                return "replacement" in config
                
            elif masking_strategy == MaskingStrategy.MASK:
                return all(key in config for key in ["mask_char"])
                
            elif masking_strategy == MaskingStrategy.HASH:
                hash_type = config.get("hash_type", "sha256")
                return hash_type in ["md5", "sha256", "sha512"]
                
            elif masking_strategy == MaskingStrategy.ENCRYPT:
                return "key" in config and "algorithm" in config
                
            else:
                return True  # REDACT and KEEP don't need config
                
        except Exception as e:
            logger.error(f"Rule config validation failed: {e}")
            return False
    
    def _validate_rule(self, rule: DesensitizationRule) -> bool:
        """
        Validate a desensitization rule.
        
        Args:
            rule: Rule to validate
            
        Returns:
            True if rule is valid
        """
        try:
            # Check required fields
            if not rule.name or not rule.tenant_id:
                return False
            
            # Validate confidence threshold
            if not 0.0 <= rule.confidence_threshold <= 1.0:
                return False
            
            # Validate strategy configuration
            return self.validate_rule_config(rule.masking_strategy, rule.config)
            
        except Exception as e:
            logger.error(f"Rule validation failed: {e}")
            return False
    
    def _create_default_rules(self) -> List[DesensitizationRule]:
        """
        Create default desensitization rules.
        
        Returns:
            List of default rules
        """
        default_rules = [
            # Email addresses
            DesensitizationRule(
                name="Email Address Masking",
                entity_type=PIIEntityType.EMAIL_ADDRESS,
                masking_strategy=MaskingStrategy.MASK,
                sensitivity_level=SensitivityLevel.MEDIUM,
                confidence_threshold=0.8,
                config={
                    "mask_char": "*",
                    "chars_to_mask": -1,
                    "from_end": False
                }
            ),
            
            # Phone numbers
            DesensitizationRule(
                name="Phone Number Masking",
                entity_type=PIIEntityType.PHONE_NUMBER,
                masking_strategy=MaskingStrategy.MASK,
                sensitivity_level=SensitivityLevel.MEDIUM,
                confidence_threshold=0.8,
                config={
                    "mask_char": "*",
                    "chars_to_mask": 6,
                    "from_end": True
                }
            ),
            
            # Credit card numbers
            DesensitizationRule(
                name="Credit Card Redaction",
                entity_type=PIIEntityType.CREDIT_CARD,
                masking_strategy=MaskingStrategy.REDACT,
                sensitivity_level=SensitivityLevel.CRITICAL,
                confidence_threshold=0.9
            ),
            
            # Person names
            DesensitizationRule(
                name="Person Name Replacement",
                entity_type=PIIEntityType.PERSON,
                masking_strategy=MaskingStrategy.REPLACE,
                sensitivity_level=SensitivityLevel.HIGH,
                confidence_threshold=0.7,
                config={
                    "replacement": "[PERSON]"
                }
            ),
            
            # SSN
            DesensitizationRule(
                name="SSN Hash",
                entity_type=PIIEntityType.US_SSN,
                masking_strategy=MaskingStrategy.HASH,
                sensitivity_level=SensitivityLevel.CRITICAL,
                confidence_threshold=0.9,
                config={
                    "hash_type": "sha256",
                    "salt": "ssn_salt"
                }
            ),
            
            # IP addresses
            DesensitizationRule(
                name="IP Address Masking",
                entity_type=PIIEntityType.IP_ADDRESS,
                masking_strategy=MaskingStrategy.MASK,
                sensitivity_level=SensitivityLevel.LOW,
                confidence_threshold=0.8,
                config={
                    "mask_char": "X",
                    "chars_to_mask": 3,
                    "from_end": True
                }
            ),
            
            # Locations
            DesensitizationRule(
                name="Location Replacement",
                entity_type=PIIEntityType.LOCATION,
                masking_strategy=MaskingStrategy.REPLACE,
                sensitivity_level=SensitivityLevel.MEDIUM,
                confidence_threshold=0.7,
                config={
                    "replacement": "[LOCATION]"
                }
            )
        ]
        
        return default_rules
    
    def export_rules(
        self,
        tenant_id: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Export rules for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            db: Database session
            
        Returns:
            Dict containing exported rules
        """
        try:
            rules = self.get_rules_for_tenant(tenant_id, enabled_only=False, db=db)
            
            export_data = {
                "tenant_id": tenant_id,
                "export_timestamp": datetime.utcnow().isoformat(),
                "rules_count": len(rules),
                "rules": []
            }
            
            for rule in rules:
                rule_data = {
                    "id": rule.id,
                    "name": rule.name,
                    "entity_type": rule.entity_type.value,
                    "masking_strategy": rule.masking_strategy.value,
                    "sensitivity_level": rule.sensitivity_level.value,
                    "confidence_threshold": rule.confidence_threshold,
                    "field_pattern": rule.field_pattern,
                    "config": rule.config,
                    "enabled": rule.enabled,
                    "created_at": rule.created_at.isoformat(),
                    "updated_at": rule.updated_at.isoformat()
                }
                export_data["rules"].append(rule_data)
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export rules for tenant {tenant_id}: {e}")
            return {}
    
    def import_rules(
        self,
        tenant_id: str,
        import_data: Dict[str, Any],
        created_by: Optional[UUID] = None,
        db: Optional[Session] = None
    ) -> bool:
        """
        Import rules for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            import_data: Exported rules data
            created_by: User importing the rules
            db: Database session
            
        Returns:
            True if import successful
        """
        try:
            rules_data = import_data.get("rules", [])
            
            for rule_data in rules_data:
                rule = DesensitizationRule(
                    name=rule_data["name"],
                    entity_type=PIIEntityType(rule_data["entity_type"]),
                    field_pattern=rule_data.get("field_pattern"),
                    masking_strategy=MaskingStrategy(rule_data["masking_strategy"]),
                    sensitivity_level=SensitivityLevel(rule_data["sensitivity_level"]),
                    confidence_threshold=rule_data["confidence_threshold"],
                    config=rule_data.get("config", {}),
                    enabled=rule_data.get("enabled", True),
                    tenant_id=tenant_id,
                    created_by=created_by
                )
                
                # Validate and create rule
                if self._validate_rule(rule):
                    logger.info(f"Imported rule: {rule.name}")
                else:
                    logger.warning(f"Skipped invalid rule: {rule.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to import rules for tenant {tenant_id}: {e}")
            return False