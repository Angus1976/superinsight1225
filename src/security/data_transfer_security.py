"""
Security Middleware for Data Transfer Operations

Implements security checks to prevent privilege escalation attacks and
unauthorized access to data transfer operations.
"""

import logging
from typing import Any, Dict

from src.models.data_transfer import DataTransferRequest
from src.services.permission_service import UserRole


logger = logging.getLogger(__name__)


class SecurityException(Exception):
    """Exception raised when a security violation is detected."""
    pass


class DataTransferSecurityMiddleware:
    """
    Security middleware for data transfer operations.
    
    Prevents privilege escalation attacks by:
    - Detecting attempts to bypass permission checks (e.g., force_approve flags)
    - Validating user roles haven't been tampered with in requests
    - Checking for suspicious request patterns
    - Raising SecurityException for detected attacks
    """
    
    # List of forbidden fields that should never appear in transfer requests
    FORBIDDEN_FIELDS = {
        'force_approve',
        'bypass_permission',
        'skip_approval',
        'override_role',
        'admin_override',
        'force_admin',
        'bypass_check',
        'skip_validation'
    }
    
    # List of protected metadata fields that users shouldn't be able to set
    PROTECTED_METADATA_FIELDS = {
        'approved_by',
        'approved_at',
        'system_approved',
        'internal_transfer',
        'bypass_audit',
        'skip_log'
    }
    
    async def verify_no_privilege_escalation(
        self,
        request: DataTransferRequest,
        current_user_id: str,
        current_user_role: UserRole
    ) -> None:
        """
        Verify that the request doesn't contain privilege escalation attempts.
        
        Args:
            request: Data transfer request to validate
            current_user_id: ID of the current authenticated user
            current_user_role: Role of the current authenticated user
            
        Raises:
            SecurityException: If privilege escalation attempt is detected
        """
        # Check for forbidden fields in request
        self._check_forbidden_fields(request)
        
        # Check for role tampering in request data
        self._check_role_tampering(request, current_user_role)
        
        # Check for protected metadata manipulation
        self._check_protected_metadata(request)
        
        # Check for suspicious approval bypass attempts
        self._check_approval_bypass(request)
        
        # Log security check passed
        logger.debug(
            f"Security check passed for user {current_user_id} "
            f"with role {current_user_role.value}"
        )
    
    def _check_forbidden_fields(self, request: DataTransferRequest) -> None:
        """
        Check if request contains any forbidden fields that could bypass security.
        
        Note: Pydantic models prevent adding fields that don't exist in the schema,
        so this check is primarily for documentation and defense-in-depth.
        In practice, Pydantic will reject requests with forbidden fields before
        they reach this middleware.
        
        Args:
            request: Data transfer request to validate
            
        Raises:
            SecurityException: If forbidden fields are detected
        """
        # Convert request to dict to check all fields
        request_dict = request.dict()
        
        # Check top-level fields
        for field in self.FORBIDDEN_FIELDS:
            if field in request_dict:
                logger.error(
                    f"Privilege escalation attempt detected: "
                    f"forbidden field '{field}' in request"
                )
                raise SecurityException(
                    f"Privilege escalation attempt detected: "
                    f"field '{field}' is not allowed in transfer requests"
                )
        
        # Check if any forbidden fields are in data_attributes
        if hasattr(request, 'data_attributes') and request.data_attributes:
            attrs_dict = request.data_attributes.dict()
            for field in self.FORBIDDEN_FIELDS:
                if field in attrs_dict:
                    logger.error(
                        f"Privilege escalation attempt detected: "
                        f"forbidden field '{field}' in data_attributes"
                    )
                    raise SecurityException(
                        f"Privilege escalation attempt detected: "
                        f"field '{field}' is not allowed in data attributes"
                    )
    
    def _check_role_tampering(
        self,
        request: DataTransferRequest,
        current_user_role: UserRole
    ) -> None:
        """
        Check if request attempts to tamper with user role.
        
        Note: Pydantic models prevent adding fields that don't exist in the schema,
        so this check is primarily for documentation and defense-in-depth.
        
        Args:
            request: Data transfer request to validate
            current_user_role: Actual role of the current user
            
        Raises:
            SecurityException: If role tampering is detected
        """
        request_dict = request.dict()
        
        # Check for user_role field in request
        if 'user_role' in request_dict:
            claimed_role = request_dict['user_role']
            
            # If claimed role differs from actual role, it's tampering
            if isinstance(claimed_role, str):
                try:
                    claimed_role_enum = UserRole(claimed_role)
                    if claimed_role_enum != current_user_role:
                        logger.error(
                            f"Role tampering detected: "
                            f"claimed role '{claimed_role}' differs from "
                            f"actual role '{current_user_role.value}'"
                        )
                        raise SecurityException(
                            "Role tampering detected: user role in request "
                            "does not match authenticated user role"
                        )
                except ValueError:
                    logger.error(f"Invalid role value in request: {claimed_role}")
                    raise SecurityException(
                        f"Invalid role value in request: {claimed_role}"
                    )
        
        # Check for role in data_attributes
        if hasattr(request, 'data_attributes') and request.data_attributes:
            attrs_dict = request.data_attributes.dict()
            if 'user_role' in attrs_dict or 'role' in attrs_dict:
                logger.error(
                    "Role tampering attempt detected in data_attributes"
                )
                raise SecurityException(
                    "Role information is not allowed in data attributes"
                )
    
    def _check_protected_metadata(self, request: DataTransferRequest) -> None:
        """
        Check if request attempts to set protected metadata fields.
        
        Args:
            request: Data transfer request to validate
            
        Raises:
            SecurityException: If protected metadata manipulation is detected
        """
        # Check each record's metadata
        for idx, record in enumerate(request.records):
            if record.metadata:
                for field in self.PROTECTED_METADATA_FIELDS:
                    if field in record.metadata:
                        logger.error(
                            f"Protected metadata manipulation detected: "
                            f"field '{field}' in record {idx} metadata"
                        )
                        raise SecurityException(
                            f"Protected metadata field '{field}' cannot be set "
                            f"by users (record index: {idx})"
                        )
    
    def _check_approval_bypass(self, request: DataTransferRequest) -> None:
        """
        Check for suspicious patterns that might indicate approval bypass attempts.
        
        Args:
            request: Data transfer request to validate
            
        Raises:
            SecurityException: If approval bypass attempt is detected
        """
        # Check if request_approval is being manipulated suspiciously
        # Note: request_approval=True is legitimate (user explicitly requesting approval)
        # but we check for patterns that suggest trying to bypass approval
        
        # Check for suspicious metadata patterns
        for idx, record in enumerate(request.records):
            if record.metadata:
                # Check for metadata that suggests trying to mark as pre-approved
                suspicious_patterns = [
                    'pre_approved',
                    'auto_approved',
                    'approved',
                    'no_approval_needed',
                    'approval_skipped'
                ]
                
                for pattern in suspicious_patterns:
                    if pattern in record.metadata:
                        logger.warning(
                            f"Suspicious approval-related metadata detected: "
                            f"'{pattern}' in record {idx}"
                        )
                        # This is a warning, not necessarily an attack
                        # but we remove the suspicious field
                        del record.metadata[pattern]
                        logger.info(
                            f"Removed suspicious metadata field '{pattern}' "
                            f"from record {idx}"
                        )
    
    async def validate_request_integrity(
        self,
        request: DataTransferRequest
    ) -> None:
        """
        Validate the overall integrity of the transfer request.
        
        Args:
            request: Data transfer request to validate
            
        Raises:
            SecurityException: If request integrity issues are detected
        """
        # Validate source_type is legitimate
        valid_source_types = [
            'structuring',
            'augmentation',
            'sync',
            'annotation',
            'ai_assistant',
            'manual'
        ]
        
        if request.source_type not in valid_source_types:
            logger.error(f"Invalid source_type: {request.source_type}")
            raise SecurityException(
                f"Invalid source_type: {request.source_type}. "
                f"Must be one of: {', '.join(valid_source_types)}"
            )
        
        # Validate target_state is legitimate
        valid_target_states = [
            'temp_stored',
            'in_sample_library',
            'annotation_pending'
        ]
        
        if request.target_state not in valid_target_states:
            logger.error(f"Invalid target_state: {request.target_state}")
            raise SecurityException(
                f"Invalid target_state: {request.target_state}. "
                f"Must be one of: {', '.join(valid_target_states)}"
            )
        
        # Validate records list is not empty
        if not request.records or len(request.records) == 0:
            logger.error("Transfer request contains no records")
            raise SecurityException(
                "Transfer request must contain at least one record"
            )
        
        # Validate record count is reasonable (prevent DoS)
        max_records = 10000
        if len(request.records) > max_records:
            logger.error(
                f"Transfer request contains too many records: "
                f"{len(request.records)} > {max_records}"
            )
            raise SecurityException(
                f"Transfer request contains too many records. "
                f"Maximum allowed: {max_records}"
            )
    
    async def log_security_event(
        self,
        event_type: str,
        user_id: str,
        user_role: UserRole,
        details: Dict[str, Any]
    ) -> None:
        """
        Log security-related events for audit purposes.
        
        Args:
            event_type: Type of security event (e.g., "privilege_escalation_blocked")
            user_id: ID of the user involved
            user_role: Role of the user involved
            details: Additional details about the security event
        """
        logger.warning(
            f"SECURITY EVENT: {event_type} | "
            f"User: {user_id} | "
            f"Role: {user_role.value} | "
            f"Details: {details}"
        )
        
        # In production, this should also write to a dedicated security audit log
        # or send alerts to security monitoring systems
