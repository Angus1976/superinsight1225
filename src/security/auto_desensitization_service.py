"""
Automatic Sensitive Data Detection and Desensitization Service

Provides real-time automatic detection and masking of sensitive data
across the SuperInsight platform with audit integration.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.audit_service import AuditService
from src.sync.desensitization import (
    PresidioEngine,
    DesensitizationRuleManager,
    DataClassifier,
    PIIEntityType,
    MaskingStrategy,
    SensitivityLevel
)
from src.desensitization.validator import DesensitizationValidator
from src.quality.desensitization_monitor import DesensitizationQualityMonitor
from src.alerts.desensitization_alerts import DesensitizationAlertManager

logger = logging.getLogger(__name__)


class AutoDesensitizationService:
    """
    Automatic sensitive data detection and desensitization service.
    
    Provides real-time detection and masking of sensitive data with
    audit logging, quality monitoring, and alert management.
    """
    
    def __init__(self):
        """Initialize the auto-desensitization service."""
        self.presidio_engine = PresidioEngine()
        self.rule_manager = DesensitizationRuleManager()
        self.data_classifier = DataClassifier(self.presidio_engine)
        self.validator = DesensitizationValidator()
        self.quality_monitor = DesensitizationQualityMonitor()
        self.alert_manager = DesensitizationAlertManager()
        self.audit_service = AuditService()
        
        # Configuration
        self.auto_detection_enabled = True
        self.real_time_masking_enabled = True
        self.quality_validation_enabled = True
        self.alert_on_high_risk = True
        
        # Performance settings
        self.batch_size = 100
        self.max_concurrent_operations = 10
        self.detection_timeout_seconds = 30
        
        # Cache for rules and policies
        self._rule_cache = {}
        self._policy_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
    async def detect_and_mask_automatically(
        self,
        data: Union[str, Dict[str, Any], List[Any]],
        tenant_id: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        operation_type: str = "data_processing"
    ) -> Dict[str, Any]:
        """
        Automatically detect and mask sensitive data.
        
        Args:
            data: Data to process (text, dict, or list)
            tenant_id: Tenant identifier
            user_id: User identifier
            context: Additional context information
            operation_type: Type of operation (for audit)
            
        Returns:
            Dict containing masked data and processing metadata
        """
        start_time = datetime.utcnow()
        operation_id = str(uuid4())
        
        try:
            # Log operation start
            await self.audit_service.log_event(
                event_type="data_desensitization_start",
                user_id=user_id,
                resource="sensitive_data",
                action="auto_detect_mask",
                details={
                    "operation_id": operation_id,
                    "operation_type": operation_type,
                    "data_type": type(data).__name__,
                    "tenant_id": tenant_id
                }
            )
            
            # Get active rules for tenant
            rules = await self._get_active_rules(tenant_id)
            if not rules:
                logger.warning(f"No active desensitization rules found for tenant {tenant_id}")
                return {
                    "success": True,
                    "original_data": data,
                    "masked_data": data,
                    "entities_detected": [],
                    "rules_applied": [],
                    "processing_time_ms": 0,
                    "operation_id": operation_id
                }
            
            # Process data based on type
            if isinstance(data, str):
                result = await self._process_text_data(data, rules, tenant_id, user_id, operation_id)
            elif isinstance(data, dict):
                result = await self._process_dict_data(data, rules, tenant_id, user_id, operation_id)
            elif isinstance(data, list):
                result = await self._process_list_data(data, rules, tenant_id, user_id, operation_id)
            else:
                raise ValueError(f"Unsupported data type: {type(data)}")
            
            # Validate desensitization quality if enabled
            if self.quality_validation_enabled and result["success"]:
                validation_result = await self._validate_desensitization_quality(
                    result, tenant_id, operation_id
                )
                result["validation"] = validation_result
            
            # Monitor quality metrics
            await self.quality_monitor.record_operation(
                tenant_id=tenant_id,
                operation_id=operation_id,
                operation_type=operation_type,
                entities_detected=len(result.get("entities_detected", [])),
                rules_applied=len(result.get("rules_applied", [])),
                processing_time_ms=result.get("processing_time_ms", 0),
                success=result["success"]
            )
            
            # Check for high-risk scenarios and send alerts
            if self.alert_on_high_risk:
                await self._check_and_send_alerts(result, tenant_id, user_id, operation_id)
            
            # Log operation completion
            await self.audit_service.log_event(
                event_type="data_desensitization_complete",
                user_id=user_id,
                resource="sensitive_data",
                action="auto_detect_mask",
                details={
                    "operation_id": operation_id,
                    "entities_detected": len(result.get("entities_detected", [])),
                    "rules_applied": result.get("rules_applied", []),
                    "processing_time_ms": result.get("processing_time_ms", 0),
                    "success": result["success"]
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Auto-desensitization failed for operation {operation_id}: {e}")
            
            # Log error
            await self.audit_service.log_event(
                event_type="data_desensitization_error",
                user_id=user_id,
                resource="sensitive_data",
                action="auto_detect_mask",
                details={
                    "operation_id": operation_id,
                    "error": str(e),
                    "processing_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
                }
            )
            
            # Send error alert
            await self.alert_manager.send_error_alert(
                tenant_id=tenant_id,
                operation_id=operation_id,
                error_message=str(e),
                context=context
            )
            
            return {
                "success": False,
                "original_data": data,
                "masked_data": data,
                "entities_detected": [],
                "rules_applied": [],
                "processing_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                "operation_id": operation_id,
                "error": str(e)
            }
    
    async def _process_text_data(
        self,
        text: str,
        rules: List[Any],
        tenant_id: str,
        user_id: str,
        operation_id: str
    ) -> Dict[str, Any]:
        """Process text data for sensitive information."""
        start_time = datetime.utcnow()
        
        # Detect PII entities
        entities = self.presidio_engine.detect_pii(
            text=text,
            entities=[rule.entity_type.value for rule in rules],
            score_threshold=min(rule.confidence_threshold for rule in rules)
        )
        
        # Apply desensitization rules
        desensitization_result = self.presidio_engine.anonymize_text(
            text=text,
            rules=rules,
            entities=entities
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "success": desensitization_result.success,
            "original_data": text,
            "masked_data": desensitization_result.anonymized_text,
            "entities_detected": [
                {
                    "entity_type": entity.entity_type.value,
                    "start": entity.start,
                    "end": entity.end,
                    "score": entity.score,
                    "text": entity.text
                }
                for entity in desensitization_result.entities_found
            ],
            "rules_applied": desensitization_result.rules_applied,
            "processing_time_ms": processing_time,
            "operation_id": operation_id,
            "errors": desensitization_result.errors
        }
    
    async def _process_dict_data(
        self,
        data_dict: Dict[str, Any],
        rules: List[Any],
        tenant_id: str,
        user_id: str,
        operation_id: str
    ) -> Dict[str, Any]:
        """Process dictionary data for sensitive information."""
        start_time = datetime.utcnow()
        
        masked_dict = {}
        all_entities = []
        all_rules_applied = set()
        all_errors = []
        
        # Process each field in the dictionary
        for field_name, field_value in data_dict.items():
            if isinstance(field_value, str) and field_value.strip():
                # Check if field matches any rule patterns
                applicable_rules = [
                    rule for rule in rules
                    if not rule.field_pattern or 
                    self._field_matches_pattern(field_name, rule.field_pattern)
                ]
                
                if applicable_rules:
                    # Process the field value
                    field_result = await self._process_text_data(
                        field_value, applicable_rules, tenant_id, user_id, operation_id
                    )
                    
                    masked_dict[field_name] = field_result["masked_data"]
                    all_entities.extend(field_result["entities_detected"])
                    all_rules_applied.update(field_result["rules_applied"])
                    all_errors.extend(field_result.get("errors", []))
                else:
                    # No applicable rules, keep original value
                    masked_dict[field_name] = field_value
            else:
                # Non-string or empty value, keep as is
                masked_dict[field_name] = field_value
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "success": len(all_errors) == 0,
            "original_data": data_dict,
            "masked_data": masked_dict,
            "entities_detected": all_entities,
            "rules_applied": list(all_rules_applied),
            "processing_time_ms": processing_time,
            "operation_id": operation_id,
            "errors": all_errors
        }
    
    async def _process_list_data(
        self,
        data_list: List[Any],
        rules: List[Any],
        tenant_id: str,
        user_id: str,
        operation_id: str
    ) -> Dict[str, Any]:
        """Process list data for sensitive information."""
        start_time = datetime.utcnow()
        
        masked_list = []
        all_entities = []
        all_rules_applied = set()
        all_errors = []
        
        # Process items in batches for performance
        for i in range(0, len(data_list), self.batch_size):
            batch = data_list[i:i + self.batch_size]
            batch_tasks = []
            
            for item in batch:
                if isinstance(item, str):
                    task = self._process_text_data(item, rules, tenant_id, user_id, operation_id)
                elif isinstance(item, dict):
                    task = self._process_dict_data(item, rules, tenant_id, user_id, operation_id)
                else:
                    # Non-processable item, keep as is
                    task = asyncio.create_task(asyncio.sleep(0, result={
                        "success": True,
                        "original_data": item,
                        "masked_data": item,
                        "entities_detected": [],
                        "rules_applied": [],
                        "processing_time_ms": 0,
                        "operation_id": operation_id,
                        "errors": []
                    }))
                
                batch_tasks.append(task)
            
            # Process batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    all_errors.append(str(result))
                    masked_list.append(None)  # Placeholder for failed item
                else:
                    masked_list.append(result["masked_data"])
                    all_entities.extend(result["entities_detected"])
                    all_rules_applied.update(result["rules_applied"])
                    all_errors.extend(result.get("errors", []))
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "success": len(all_errors) == 0,
            "original_data": data_list,
            "masked_data": masked_list,
            "entities_detected": all_entities,
            "rules_applied": list(all_rules_applied),
            "processing_time_ms": processing_time,
            "operation_id": operation_id,
            "errors": all_errors
        }
    
    def _field_matches_pattern(self, field_name: str, pattern: str) -> bool:
        """Check if field name matches the given pattern."""
        import re
        try:
            return bool(re.search(pattern, field_name, re.IGNORECASE))
        except re.error:
            # Invalid regex pattern, fall back to simple string matching
            return pattern.lower() in field_name.lower()
    
    async def _get_active_rules(self, tenant_id: str) -> List[Any]:
        """Get active desensitization rules for tenant with caching."""
        cache_key = f"rules_{tenant_id}"
        
        # Check cache first
        if cache_key in self._rule_cache:
            cached_data = self._rule_cache[cache_key]
            if (datetime.utcnow() - cached_data["timestamp"]).total_seconds() < self._cache_ttl:
                return cached_data["rules"]
        
        # Fetch from database
        async with get_db_session() as db:
            rules = self.rule_manager.get_rules_for_tenant(
                tenant_id=tenant_id,
                enabled_only=True,
                db=db
            )
        
        # Cache the results
        self._rule_cache[cache_key] = {
            "rules": rules,
            "timestamp": datetime.utcnow()
        }
        
        return rules
    
    async def _validate_desensitization_quality(
        self,
        result: Dict[str, Any],
        tenant_id: str,
        operation_id: str
    ) -> Dict[str, Any]:
        """Validate the quality of desensitization."""
        try:
            validation_result = await self.validator.validate_desensitization(
                original_text=str(result["original_data"]),
                masked_text=str(result["masked_data"]),
                detected_entities=result["entities_detected"]
            )
            
            return {
                "is_valid": validation_result.is_valid,
                "completeness_score": validation_result.completeness_score,
                "accuracy_score": validation_result.accuracy_score,
                "issues": validation_result.issues,
                "recommendations": validation_result.recommendations
            }
            
        except Exception as e:
            logger.error(f"Quality validation failed for operation {operation_id}: {e}")
            return {
                "is_valid": False,
                "completeness_score": 0.0,
                "accuracy_score": 0.0,
                "issues": [f"Validation error: {str(e)}"],
                "recommendations": ["Review validation configuration"]
            }
    
    async def _check_and_send_alerts(
        self,
        result: Dict[str, Any],
        tenant_id: str,
        user_id: str,
        operation_id: str
    ) -> None:
        """Check for high-risk scenarios and send alerts."""
        try:
            # Check for high number of sensitive entities
            entities_count = len(result.get("entities_detected", []))
            if entities_count > 50:  # Configurable threshold
                await self.alert_manager.send_high_volume_alert(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    operation_id=operation_id,
                    entities_count=entities_count
                )
            
            # Check for validation failures
            validation = result.get("validation", {})
            if not validation.get("is_valid", True):
                await self.alert_manager.send_quality_alert(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    operation_id=operation_id,
                    validation_issues=validation.get("issues", [])
                )
            
            # Check for processing errors
            errors = result.get("errors", [])
            if errors:
                await self.alert_manager.send_processing_alert(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    operation_id=operation_id,
                    errors=errors
                )
                
        except Exception as e:
            logger.error(f"Alert checking failed for operation {operation_id}: {e}")
    
    async def bulk_detect_and_mask(
        self,
        data_items: List[Any],
        tenant_id: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Bulk process multiple data items for sensitive information.
        
        Args:
            data_items: List of data items to process
            tenant_id: Tenant identifier
            user_id: User identifier
            context: Additional context information
            
        Returns:
            Dict containing bulk processing results
        """
        start_time = datetime.utcnow()
        bulk_operation_id = str(uuid4())
        
        try:
            # Log bulk operation start
            await self.audit_service.log_event(
                event_type="bulk_desensitization_start",
                user_id=user_id,
                resource="sensitive_data",
                action="bulk_detect_mask",
                details={
                    "bulk_operation_id": bulk_operation_id,
                    "items_count": len(data_items),
                    "tenant_id": tenant_id
                }
            )
            
            # Process items in parallel batches
            results = []
            total_entities = 0
            total_rules_applied = set()
            total_errors = []
            
            for i in range(0, len(data_items), self.batch_size):
                batch = data_items[i:i + self.batch_size]
                batch_tasks = []
                
                for item in batch:
                    task = self.detect_and_mask_automatically(
                        data=item,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        context=context,
                        operation_type="bulk_processing"
                    )
                    batch_tasks.append(task)
                
                # Limit concurrent operations
                semaphore = asyncio.Semaphore(self.max_concurrent_operations)
                
                async def process_with_semaphore(task):
                    async with semaphore:
                        return await task
                
                batch_results = await asyncio.gather(
                    *[process_with_semaphore(task) for task in batch_tasks],
                    return_exceptions=True
                )
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        total_errors.append(str(result))
                        results.append({
                            "success": False,
                            "error": str(result)
                        })
                    else:
                        results.append(result)
                        total_entities += len(result.get("entities_detected", []))
                        total_rules_applied.update(result.get("rules_applied", []))
                        total_errors.extend(result.get("errors", []))
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            success_count = sum(1 for r in results if r.get("success", False))
            
            # Log bulk operation completion
            await self.audit_service.log_event(
                event_type="bulk_desensitization_complete",
                user_id=user_id,
                resource="sensitive_data",
                action="bulk_detect_mask",
                details={
                    "bulk_operation_id": bulk_operation_id,
                    "items_processed": len(results),
                    "success_count": success_count,
                    "total_entities": total_entities,
                    "total_rules_applied": len(total_rules_applied),
                    "processing_time_ms": processing_time
                }
            )
            
            return {
                "success": len(total_errors) == 0,
                "bulk_operation_id": bulk_operation_id,
                "items_processed": len(results),
                "success_count": success_count,
                "failure_count": len(results) - success_count,
                "total_entities_detected": total_entities,
                "total_rules_applied": list(total_rules_applied),
                "processing_time_ms": processing_time,
                "results": results,
                "errors": total_errors
            }
            
        except Exception as e:
            logger.error(f"Bulk desensitization failed for operation {bulk_operation_id}: {e}")
            
            # Log error
            await self.audit_service.log_event(
                event_type="bulk_desensitization_error",
                user_id=user_id,
                resource="sensitive_data",
                action="bulk_detect_mask",
                details={
                    "bulk_operation_id": bulk_operation_id,
                    "error": str(e),
                    "processing_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
                }
            )
            
            return {
                "success": False,
                "bulk_operation_id": bulk_operation_id,
                "items_processed": 0,
                "success_count": 0,
                "failure_count": len(data_items),
                "total_entities_detected": 0,
                "total_rules_applied": [],
                "processing_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                "results": [],
                "errors": [str(e)]
            }
    
    async def configure_auto_detection(
        self,
        tenant_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Configure automatic detection settings for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            config: Configuration settings
            
        Returns:
            Dict containing configuration result
        """
        try:
            # Validate configuration
            valid_keys = {
                "auto_detection_enabled",
                "real_time_masking_enabled", 
                "quality_validation_enabled",
                "alert_on_high_risk",
                "batch_size",
                "max_concurrent_operations",
                "detection_timeout_seconds"
            }
            
            invalid_keys = set(config.keys()) - valid_keys
            if invalid_keys:
                return {
                    "success": False,
                    "error": f"Invalid configuration keys: {invalid_keys}"
                }
            
            # Apply configuration
            for key, value in config.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            # Cache configuration for tenant
            self._policy_cache[f"config_{tenant_id}"] = {
                "config": config,
                "timestamp": datetime.utcnow()
            }
            
            return {
                "success": True,
                "message": "Configuration updated successfully",
                "applied_config": config
            }
            
        except Exception as e:
            logger.error(f"Configuration update failed for tenant {tenant_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_detection_statistics(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get detection and masking statistics for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Dict containing statistics
        """
        try:
            return await self.quality_monitor.get_tenant_statistics(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date
            )
            
        except Exception as e:
            logger.error(f"Failed to get statistics for tenant {tenant_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }