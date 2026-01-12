"""
Enhanced Audit Decorators for SuperInsight Platform.

Provides comprehensive audit logging decorators that can be easily applied
to API endpoints to ensure complete audit coverage.
"""

import functools
import inspect
from typing import Optional, Callable, Any, Dict, List
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session

from src.security.audit_service import EnhancedAuditService
from src.security.models import AuditAction, UserModel
from src.security.controller import SecurityController
from src.database.connection import get_db_session
import logging

logger = logging.getLogger(__name__)


class AuditDecorators:
    """
    Collection of audit decorators for comprehensive operation logging.
    """
    
    def __init__(self):
        self.audit_service = EnhancedAuditService()
        self.security_controller = SecurityController()
    
    def audit_all_operations(
        self,
        resource_type: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource_id_param: Optional[str] = None,
        include_request_body: bool = True,
        include_response_body: bool = False
    ):
        """
        Comprehensive audit decorator that logs all operations.
        
        Args:
            resource_type: Type of resource being accessed
            action: Specific action being performed
            resource_id_param: Parameter name containing resource ID
            include_request_body: Whether to include request body in audit
            include_response_body: Whether to include response body in audit
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract function signature information
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                # Extract common dependencies
                request = bound_args.arguments.get('request')
                current_user = bound_args.arguments.get('current_user')
                db = bound_args.arguments.get('db')
                
                # Auto-detect resource type and action if not provided
                detected_resource_type = resource_type or self._detect_resource_type(func.__name__)
                detected_action = action or self._detect_action(func.__name__, request)
                
                # Extract resource ID
                resource_id = None
                if resource_id_param and resource_id_param in bound_args.arguments:
                    resource_id = str(bound_args.arguments[resource_id_param])
                
                # Prepare audit details
                audit_details = {
                    "function_name": func.__name__,
                    "module": func.__module__,
                    "parameters": self._sanitize_parameters(bound_args.arguments),
                    "timestamp": self._get_timestamp()
                }
                
                # Add request information if available
                if request:
                    audit_details.update({
                        "request_method": request.method,
                        "request_path": request.url.path,
                        "query_params": dict(request.query_params),
                        "client_ip": self._get_client_ip(request),
                        "user_agent": request.headers.get("user-agent", "")
                    })
                    
                    # Include request body if requested
                    if include_request_body and request.method in ["POST", "PUT", "PATCH"]:
                        try:
                            body = await request.body()
                            if body:
                                audit_details["request_body"] = self._sanitize_body(body)
                        except Exception as e:
                            audit_details["request_body_error"] = str(e)
                
                # Execute the function
                start_time = self._get_timestamp()
                try:
                    result = await func(*args, **kwargs)
                    
                    # Calculate execution time
                    end_time = self._get_timestamp()
                    execution_time = (end_time - start_time).total_seconds()
                    
                    # Add success information
                    audit_details.update({
                        "status": "success",
                        "execution_time": execution_time,
                        "end_timestamp": end_time
                    })
                    
                    # Include response body if requested
                    if include_response_body and result:
                        audit_details["response_body"] = self._sanitize_response(result)
                    
                    # Log successful operation
                    if current_user and db:
                        await self.audit_service.log_enhanced_audit_event(
                            user_id=current_user.id,
                            tenant_id=current_user.tenant_id,
                            action=detected_action,
                            resource_type=detected_resource_type,
                            resource_id=resource_id,
                            ip_address=audit_details.get("client_ip"),
                            user_agent=audit_details.get("user_agent"),
                            details=audit_details,
                            db=db
                        )
                    
                    return result
                    
                except Exception as e:
                    # Calculate execution time for failed operations
                    end_time = self._get_timestamp()
                    execution_time = (end_time - start_time).total_seconds()
                    
                    # Add failure information
                    audit_details.update({
                        "status": "error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "execution_time": execution_time,
                        "end_timestamp": end_time
                    })
                    
                    # Log failed operation
                    if current_user and db:
                        await self.audit_service.log_enhanced_audit_event(
                            user_id=current_user.id,
                            tenant_id=current_user.tenant_id,
                            action=detected_action,
                            resource_type=detected_resource_type,
                            resource_id=resource_id,
                            ip_address=audit_details.get("client_ip"),
                            user_agent=audit_details.get("user_agent"),
                            details=audit_details,
                            db=db
                        )
                    
                    # Re-raise the exception
                    raise
            
            return wrapper
        return decorator
    
    def audit_sensitive_operation(
        self,
        resource_type: str,
        action: AuditAction,
        risk_level: str = "high",
        require_approval: bool = False
    ):
        """
        Audit decorator for sensitive operations with enhanced security.
        
        Args:
            resource_type: Type of resource being accessed
            action: Action being performed
            risk_level: Risk level of the operation
            require_approval: Whether operation requires approval
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract dependencies
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                current_user = bound_args.arguments.get('current_user')
                db = bound_args.arguments.get('db')
                request = bound_args.arguments.get('request')
                
                if not current_user or not db:
                    raise HTTPException(
                        status_code=500,
                        detail="Missing authentication dependencies for sensitive operation"
                    )
                
                # Enhanced audit details for sensitive operations
                audit_details = {
                    "operation_type": "sensitive",
                    "risk_level": risk_level,
                    "function_name": func.__name__,
                    "module": func.__module__,
                    "require_approval": require_approval,
                    "user_role": current_user.role.value,
                    "timestamp": self._get_timestamp()
                }
                
                # Add request context
                if request:
                    audit_details.update({
                        "request_method": request.method,
                        "request_path": request.url.path,
                        "client_ip": self._get_client_ip(request),
                        "user_agent": request.headers.get("user-agent", "")
                    })
                
                # Check if approval is required
                if require_approval:
                    # In a real implementation, this would check an approval system
                    audit_details["approval_status"] = "auto_approved"
                
                # Execute the function with enhanced monitoring
                try:
                    result = await func(*args, **kwargs)
                    
                    audit_details["status"] = "success"
                    
                    # Log sensitive operation
                    await self.audit_service.log_enhanced_audit_event(
                        user_id=current_user.id,
                        tenant_id=current_user.tenant_id,
                        action=action,
                        resource_type=resource_type,
                        ip_address=audit_details.get("client_ip"),
                        user_agent=audit_details.get("user_agent"),
                        details=audit_details,
                        db=db
                    )
                    
                    return result
                    
                except Exception as e:
                    audit_details.update({
                        "status": "error",
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                    
                    # Log failed sensitive operation
                    await self.audit_service.log_enhanced_audit_event(
                        user_id=current_user.id,
                        tenant_id=current_user.tenant_id,
                        action=action,
                        resource_type=resource_type,
                        ip_address=audit_details.get("client_ip"),
                        user_agent=audit_details.get("user_agent"),
                        details=audit_details,
                        db=db
                    )
                    
                    raise
            
            return wrapper
        return decorator
    
    def audit_data_access(
        self,
        data_type: str,
        access_level: str = "read",
        track_volume: bool = True
    ):
        """
        Audit decorator specifically for data access operations.
        
        Args:
            data_type: Type of data being accessed
            access_level: Level of access (read, write, delete)
            track_volume: Whether to track data volume
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                current_user = bound_args.arguments.get('current_user')
                db = bound_args.arguments.get('db')
                request = bound_args.arguments.get('request')
                
                # Prepare data access audit details
                audit_details = {
                    "access_type": "data_access",
                    "data_type": data_type,
                    "access_level": access_level,
                    "function_name": func.__name__,
                    "timestamp": self._get_timestamp()
                }
                
                # Execute function and track data volume
                try:
                    result = await func(*args, **kwargs)
                    
                    # Track data volume if requested
                    if track_volume and result:
                        volume_info = self._calculate_data_volume(result)
                        audit_details.update(volume_info)
                    
                    audit_details["status"] = "success"
                    
                    # Log data access
                    if current_user and db:
                        action = AuditAction.READ if access_level == "read" else AuditAction.UPDATE
                        
                        await self.audit_service.log_enhanced_audit_event(
                            user_id=current_user.id,
                            tenant_id=current_user.tenant_id,
                            action=action,
                            resource_type=data_type,
                            ip_address=self._get_client_ip(request) if request else None,
                            user_agent=request.headers.get("user-agent") if request else None,
                            details=audit_details,
                            db=db
                        )
                    
                    return result
                    
                except Exception as e:
                    audit_details.update({
                        "status": "error",
                        "error": str(e)
                    })
                    
                    # Log failed data access
                    if current_user and db:
                        await self.audit_service.log_enhanced_audit_event(
                            user_id=current_user.id,
                            tenant_id=current_user.tenant_id,
                            action=AuditAction.READ,
                            resource_type=data_type,
                            ip_address=self._get_client_ip(request) if request else None,
                            user_agent=request.headers.get("user-agent") if request else None,
                            details=audit_details,
                            db=db
                        )
                    
                    raise
            
            return wrapper
        return decorator
    
    def _detect_resource_type(self, function_name: str) -> str:
        """Auto-detect resource type from function name."""
        
        # Common patterns in function names
        if "user" in function_name.lower():
            return "user"
        elif "audit" in function_name.lower():
            return "audit_log"
        elif "security" in function_name.lower():
            return "security"
        elif "billing" in function_name.lower():
            return "billing"
        elif "quality" in function_name.lower():
            return "quality"
        elif "export" in function_name.lower():
            return "export"
        elif "admin" in function_name.lower():
            return "admin"
        else:
            return "system"
    
    def _detect_action(self, function_name: str, request: Optional[Request]) -> AuditAction:
        """Auto-detect action from function name and request method."""
        
        function_lower = function_name.lower()
        
        # Check function name patterns first
        if any(word in function_lower for word in ["create", "add", "insert", "post"]):
            return AuditAction.CREATE
        elif any(word in function_lower for word in ["update", "modify", "edit", "put", "patch"]):
            return AuditAction.UPDATE
        elif any(word in function_lower for word in ["delete", "remove", "destroy"]):
            return AuditAction.DELETE
        elif any(word in function_lower for word in ["export", "download"]):
            return AuditAction.EXPORT
        elif any(word in function_lower for word in ["import", "upload"]):
            return AuditAction.IMPORT
        elif any(word in function_lower for word in ["login", "authenticate"]):
            return AuditAction.LOGIN
        elif any(word in function_lower for word in ["logout", "signout"]):
            return AuditAction.LOGOUT
        
        # Fallback to HTTP method
        if request:
            method_mapping = {
                "POST": AuditAction.CREATE,
                "PUT": AuditAction.UPDATE,
                "PATCH": AuditAction.UPDATE,
                "DELETE": AuditAction.DELETE,
                "GET": AuditAction.READ
            }
            return method_mapping.get(request.method, AuditAction.READ)
        
        return AuditAction.READ
    
    def _sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize function parameters for audit logging."""
        
        sanitized = {}
        sensitive_keys = {"password", "secret", "token", "key", "credential"}
        
        for key, value in parameters.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif value is None:
                sanitized[key] = None
            else:
                sanitized[key] = f"<{type(value).__name__}>"
        
        return sanitized
    
    def _sanitize_body(self, body: bytes) -> Dict[str, Any]:
        """Sanitize request body for audit logging."""
        
        try:
            import json
            
            # Try to parse as JSON
            body_str = body.decode("utf-8")
            body_data = json.loads(body_str)
            
            # Sanitize sensitive fields
            return self._sanitize_dict(body_data)
            
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Return truncated string if not JSON
            return {
                "raw_body": body.decode("utf-8", errors="ignore")[:500],
                "size": len(body)
            }
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary data."""
        
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        sensitive_keys = {"password", "secret", "token", "key", "credential"}
        
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value[:10]  # Limit list size
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_response(self, response: Any) -> Dict[str, Any]:
        """Sanitize response data for audit logging."""
        
        if hasattr(response, 'dict'):
            # Pydantic model
            return self._sanitize_dict(response.dict())
        elif isinstance(response, dict):
            return self._sanitize_dict(response)
        elif isinstance(response, list):
            return {
                "type": "list",
                "count": len(response),
                "sample": response[:3] if response else []
            }
        else:
            return {
                "type": type(response).__name__,
                "value": str(response)[:200]
            }
    
    def _calculate_data_volume(self, data: Any) -> Dict[str, Any]:
        """Calculate data volume metrics."""
        
        volume_info = {}
        
        if isinstance(data, list):
            volume_info["record_count"] = len(data)
            volume_info["data_type"] = "list"
        elif isinstance(data, dict):
            volume_info["field_count"] = len(data)
            volume_info["data_type"] = "dict"
        elif isinstance(data, str):
            volume_info["character_count"] = len(data)
            volume_info["data_type"] = "string"
        
        # Estimate size in bytes
        try:
            import sys
            volume_info["estimated_size_bytes"] = sys.getsizeof(data)
        except:
            pass
        
        return volume_info
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        if not request:
            return "unknown"
        
        # Check forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _get_timestamp(self):
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow()


# Global audit decorators instance
audit_decorators = AuditDecorators()

# Convenience decorators
audit_all = audit_decorators.audit_all_operations
audit_sensitive = audit_decorators.audit_sensitive_operation
audit_data = audit_decorators.audit_data_access