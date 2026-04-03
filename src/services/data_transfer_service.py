"""
Data Transfer Service for unified data transfer operations.

Implements the core service for transferring data from various sources
(structuring, augmentation, sync) to different target states (temp_stored,
in_sample_library, annotation_pending) with permission checks and approval workflow.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4
from sqlalchemy.orm import Session

from src.models.data_transfer import DataTransferRequest
from src.models.data_lifecycle import (
    TempDataModel, SampleModel, DataState, TransferAuditLogModel
)
from src.services.permission_service import PermissionService, UserRole
from src.services.approval_service import ApprovalService
from src.security.sensitive_data_validator import (
    SensitiveDataValidator,
    SensitiveDataDetectionResult
)
from src.sync.desensitization.models import SensitivityLevel


class User:
    """User model placeholder for type hints."""
    def __init__(self, id: str, role: UserRole):
        self.id = id
        self.role = role


class DataTransferService:
    """
    Unified data transfer service.
    
    Handles data transfer operations from various sources to different target states,
    with integrated permission checking and approval workflow support.
    """
    
    def __init__(self, db: Session, sensitive_data_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Data Transfer Service.
        
        Args:
            db: Database session
            sensitive_data_config: Optional configuration for sensitive data validation
        """
        self.db = db
        self.permission_service = PermissionService()
        self.approval_service = ApprovalService(db)
        self.sensitive_data_validator = SensitiveDataValidator(sensitive_data_config)
    
    async def transfer(
        self,
        request: DataTransferRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Execute data transfer with permission checks and approval workflow.
        
        Args:
            request: Data transfer request containing source, target, and records
            current_user: User performing the transfer
            
        Returns:
            Transfer result with success status, transferred IDs, and navigation URL
            or approval request details if approval is required
            
        Raises:
            ValueError: If source validation fails
            PermissionError: If user lacks required permissions
        """
        result = None
        error = None
        sensitive_data_result = None
        
        try:
            # 1. Check permission
            permission = self.permission_service.check_permission(
                user_role=current_user.role,
                target_state=request.target_state,
                record_count=len(request.records)
            )
            
            # 2. Validate for sensitive data
            sensitive_data_result = await self.sensitive_data_validator.validate_transfer_request(
                request
            )
            
            # 3. Check if sensitive data requires additional approval
            requires_approval = permission.requires_approval or sensitive_data_result.requires_additional_approval
            
            # 4. If approval required and not explicitly requested
            if requires_approval and not request.request_approval:
                approval = await self.approval_service.create_approval_request(
                    transfer_request=request,
                    requester_id=current_user.id,
                    requester_role=current_user.role
                )
                
                # Build approval response with sensitive data info
                result = {
                    "success": True,
                    "approval_required": True,
                    "approval_id": approval.id,
                    "message": "Transfer request submitted for approval",
                    "estimated_approval_time": "2-3 business days"
                }
                
                # Add sensitive data information if detected
                if sensitive_data_result.has_sensitive_data:
                    result["sensitive_data_detected"] = True
                    result["sensitivity_level"] = sensitive_data_result.sensitivity_level.value
                    result["recommendations"] = sensitive_data_result.recommendations
                
                # Log audit for approval submission with sensitive data info
                await self._log_audit(
                    request, 
                    current_user, 
                    result,
                    sensitive_data_result=sensitive_data_result
                )
                return result
            
            # 5. Validate source data
            await self._validate_source(request.source_type, request.source_id)
            
            # 6. Execute transfer
            result = await self._execute_transfer(request, current_user)
            
            # 7. Add sensitive data info to result
            if sensitive_data_result.has_sensitive_data:
                result["sensitive_data_detected"] = True
                result["sensitivity_level"] = sensitive_data_result.sensitivity_level.value
                result["recommendations"] = sensitive_data_result.recommendations
            
            # 8. Record audit log with sensitive data info
            await self._log_audit(
                request, 
                current_user, 
                result,
                sensitive_data_result=sensitive_data_result
            )
            
            return result
            
        except Exception as e:
            # Capture error for audit logging
            error = str(e)
            
            # Create error result for audit log
            error_result = {
                "success": False,
                "error": error,
                "source_type": request.source_type,
                "source_id": request.source_id,
                "target_state": request.target_state
            }
            
            # Log the failed operation with sensitive data info if available
            await self._log_audit(
                request, 
                current_user, 
                error_result, 
                error=error,
                sensitive_data_result=sensitive_data_result
            )
            
            # Re-raise the exception
            raise
    
    async def _validate_source(
        self,
        source_type: str,
        source_id: str
    ) -> None:
        """
        Validate that source data exists and is in valid state.
        
        Args:
            source_type: Type of data source
            source_id: ID of the source data
            
        Raises:
            ValueError: If source is invalid or not found
        """
        # Placeholder for source validation logic
        # In real implementation, would check:
        # - structuring: check structuring job exists and is completed
        # - augmentation: check enhancement job exists and is completed
        # - sync: check sync job exists and is completed
        
        if not source_id:
            raise ValueError(f"Invalid source_id: {source_id}")
        
        # TODO: Implement actual source validation based on source_type
        pass
    
    async def _execute_transfer(
        self,
        request: DataTransferRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Execute the actual transfer operation based on target state.
        
        Args:
            request: Data transfer request
            current_user: User performing the transfer
            
        Returns:
            Transfer result with success status and details
            
        Raises:
            ValueError: If target state is unsupported
        """
        if request.target_state == "temp_stored":
            return await self._transfer_to_temp_data(request, current_user)
        elif request.target_state == "in_sample_library":
            return await self._transfer_to_sample_library(request, current_user)
        elif request.target_state == "annotation_pending":
            return await self._transfer_to_annotation_pending(request, current_user)
        else:
            raise ValueError(f"Unsupported target state: {request.target_state}")
    
    async def _transfer_to_temp_data(
        self,
        request: DataTransferRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Transfer data to temporary storage with bulk insert optimization.
        
        Args:
            request: Data transfer request
            current_user: User performing the transfer
            
        Returns:
            Transfer result with lifecycle IDs and navigation URL
        """
        # Use bulk insert for better performance with large batches
        temp_data_list = []
        lifecycle_ids = []
        
        for record in request.records:
            record_id = uuid4()
            temp_data = TempDataModel(
                id=record_id,
                source_document_id=request.source_id,
                content=record.content,
                state=DataState.TEMP_STORED,
                uploaded_by=current_user.id,
                uploaded_at=datetime.utcnow(),
                metadata_={
                    "source_type": request.source_type,
                    "source_id": request.source_id,
                    "category": request.data_attributes.category,
                    "tags": request.data_attributes.tags,
                    "quality_score": request.data_attributes.quality_score,
                    "description": request.data_attributes.description,
                    **(record.metadata or {})
                }
            )
            temp_data_list.append(temp_data)
            lifecycle_ids.append(str(record_id))
        
        # Bulk insert all records at once
        self.db.bulk_save_objects(temp_data_list)
        self.db.flush()
        
        return {
            "success": True,
            "transferred_count": len(lifecycle_ids),
            "lifecycle_ids": lifecycle_ids,
            "target_state": "temp_stored",
            "message": f"Successfully transferred {len(lifecycle_ids)} records to temporary storage",
            "navigation_url": "/data-lifecycle/temp-data"
        }
    
    async def _transfer_to_sample_library(
        self,
        request: DataTransferRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Transfer data to sample library with bulk insert optimization.
        
        Args:
            request: Data transfer request
            current_user: User performing the transfer
            
        Returns:
            Transfer result with lifecycle IDs and navigation URL
        """
        # Use bulk insert for better performance with large batches
        sample_list = []
        lifecycle_ids = []
        quality_score = request.data_attributes.quality_score
        current_time = datetime.utcnow()
        
        for record in request.records:
            record_id = uuid4()
            sample = SampleModel(
                id=record_id,
                data_id=record.id,
                content=record.content,
                category=request.data_attributes.category,
                quality_overall=quality_score,
                quality_completeness=quality_score,
                quality_accuracy=quality_score,
                quality_consistency=quality_score,
                version=1,
                tags=request.data_attributes.tags,
                usage_count=0,
                metadata_={
                    "source_type": request.source_type,
                    "source_id": request.source_id,
                    "description": request.data_attributes.description,
                    "transferred_by": current_user.id,
                    "transferred_at": current_time.isoformat(),
                    **(record.metadata or {})
                },
                created_at=current_time,
                updated_at=current_time
            )
            sample_list.append(sample)
            lifecycle_ids.append(str(record_id))
        
        # Use add_all + flush so rows participate in the ORM session (bulk_save_objects
        # can leave subsequent queries in the same session unable to load by PK in tests).
        self.db.add_all(sample_list)
        self.db.flush()
        
        return {
            "success": True,
            "transferred_count": len(lifecycle_ids),
            "lifecycle_ids": lifecycle_ids,
            "target_state": "in_sample_library",
            "message": f"Successfully transferred {len(lifecycle_ids)} records to sample library",
            "navigation_url": "/data-lifecycle/sample-library"
        }
    
    async def _transfer_to_annotation_pending(
        self,
        request: DataTransferRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Transfer data to annotation pending state with bulk insert optimization.
        
        Args:
            request: Data transfer request
            current_user: User performing the transfer
            
        Returns:
            Transfer result with lifecycle IDs and navigation URL
        """
        # Use bulk insert for better performance with large batches
        temp_data_list = []
        lifecycle_ids = []
        current_time = datetime.utcnow()
        
        for record in request.records:
            record_id = uuid4()
            temp_data = TempDataModel(
                id=record_id,
                source_document_id=request.source_id,
                content=record.content,
                state=DataState.ANNOTATION_PENDING,
                uploaded_by=current_user.id,
                uploaded_at=current_time,
                metadata_={
                    "source_type": request.source_type,
                    "source_id": request.source_id,
                    "category": request.data_attributes.category,
                    "tags": request.data_attributes.tags,
                    "quality_score": request.data_attributes.quality_score,
                    "description": request.data_attributes.description,
                    "pending_annotation": True,
                    **(record.metadata or {})
                }
            )
            temp_data_list.append(temp_data)
            lifecycle_ids.append(str(record_id))
        
        # Bulk insert all records at once
        self.db.bulk_save_objects(temp_data_list)
        self.db.flush()
        
        return {
            "success": True,
            "transferred_count": len(lifecycle_ids),
            "lifecycle_ids": lifecycle_ids,
            "target_state": "annotation_pending",
            "message": f"Successfully transferred {len(lifecycle_ids)} records to annotation pending",
            "navigation_url": "/data-lifecycle/annotation-pending"
        }
    
    async def _log_audit(
        self,
        request: DataTransferRequest,
        current_user: User,
        result: Dict[str, Any],
        error: Optional[str] = None,
        sensitive_data_result: Optional[SensitiveDataDetectionResult] = None
    ) -> None:
        """
        Record audit log for transfer operation.
        
        Args:
            request: Data transfer request
            current_user: User who performed the transfer
            result: Transfer operation result
            error: Optional error message if operation failed
            sensitive_data_result: Optional sensitive data detection result
        """
        try:
            # Nested transaction so a failed audit insert does not invalidate the outer session
            # (which would lose an already-flushed transfer on SQLite).
            with self.db.begin_nested():
                # Determine success status
                success = result.get("success", False)
                error_message = error or result.get("error")

                # If approval required, still log as successful submission
                if result.get("approval_required"):
                    success = True

                # Create transfer-specific audit log
                audit_log = TransferAuditLogModel(
                    id=str(uuid4()),
                    user_id=current_user.id,
                    user_role=current_user.role.value,
                    operation="transfer",
                    source_type=request.source_type,
                    source_id=request.source_id,
                    target_state=request.target_state,
                    record_count=len(request.records),
                    success=success,
                    error_message=error_message,
                    created_at=datetime.utcnow()
                )

                # Add sensitive data information to audit log metadata if detected
                if sensitive_data_result and sensitive_data_result.has_sensitive_data:
                    if hasattr(audit_log, 'metadata_'):
                        audit_log.metadata_ = {
                            'sensitive_data_detected': True,
                            'sensitivity_level': sensitive_data_result.sensitivity_level.value,
                            'risk_score': sensitive_data_result.risk_score,
                            'detected_pattern_count': len(sensitive_data_result.detected_patterns),
                            'sensitive_field_count': len(sensitive_data_result.sensitive_fields),
                            'requires_additional_approval': sensitive_data_result.requires_additional_approval
                        }

                self.db.add(audit_log)
                self.db.flush()

            # Log sensitive data detection to application log
            if sensitive_data_result and sensitive_data_result.has_sensitive_data:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Sensitive data transfer detected: "
                    f"user={current_user.id}, "
                    f"level={sensitive_data_result.sensitivity_level.value}, "
                    f"risk_score={sensitive_data_result.risk_score:.2f}, "
                    f"patterns={len(sensitive_data_result.detected_patterns)}, "
                    f"requires_approval={sensitive_data_result.requires_additional_approval}"
                )
        except Exception as e:
            # Log error but don't fail the transfer
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create transfer audit log: {e}")
