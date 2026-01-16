"""
Comprehensive Audit Middleware for SuperInsight Platform.

Automatically logs all user operations and API requests for complete audit trail.
Implements enterprise-level audit logging with risk assessment and real-time monitoring.
"""

import json
import time
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
import logging

from src.security.audit_service import EnhancedAuditService, RiskLevel
from src.security.models import AuditAction, UserModel
from src.security.controller import SecurityController
from src.database.connection import db_manager


logger = logging.getLogger(__name__)


class ComprehensiveAuditMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive audit middleware that logs ALL user operations.
    
    Features:
    - Automatic audit logging for all API requests
    - Risk assessment and threat detection
    - Real-time monitoring and alerting
    - Performance tracking
    - Sensitive data detection
    - Multi-tenant audit isolation
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.audit_service = EnhancedAuditService()
        self.security_controller = SecurityController()
        
        # Excluded paths that don't need audit logging
        self.excluded_paths = {
            "/health",
            "/health/live", 
            "/health/ready",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/favicon.ico"
        }
        
        # Sensitive endpoints that require special attention
        self.sensitive_endpoints = {
            "/api/security/",
            "/api/audit/",
            "/api/admin/",
            "/api/billing/",
            "/api/desensitization/",
            "/api/compliance/"
        }
        
        # Action mapping for HTTP methods
        self.method_to_action = {
            "GET": AuditAction.READ,
            "POST": AuditAction.CREATE,
            "PUT": AuditAction.UPDATE,
            "PATCH": AuditAction.UPDATE,
            "DELETE": AuditAction.DELETE
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with comprehensive audit logging."""
        
        # Skip excluded paths
        if self._should_skip_audit(request):
            return await call_next(request)
        
        # Start request tracking
        start_time = time.time()
        request_id = f"req_{int(start_time * 1000000)}"
        
        # Extract request information
        request_info = await self._extract_request_info(request)
        
        # Get user context if available
        user_context = await self._get_user_context(request)
        
        # Execute the request
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Extract response information
            response_info = await self._extract_response_info(response, response_time)
            
            # Log the audit event
            await self._log_audit_event(
                request_id=request_id,
                request_info=request_info,
                response_info=response_info,
                user_context=user_context,
                success=True
            )
            
            return response
            
        except Exception as e:
            # Calculate response time for failed requests
            response_time = time.time() - start_time
            
            # Log failed request
            await self._log_audit_event(
                request_id=request_id,
                request_info=request_info,
                response_info={
                    "status_code": 500,
                    "error": str(e),
                    "response_time": response_time
                },
                user_context=user_context,
                success=False
            )
            
            # Re-raise the exception
            raise
    
    def _should_skip_audit(self, request: Request) -> bool:
        """Determine if request should be skipped from audit logging."""
        path = request.url.path
        
        # Skip excluded paths
        if path in self.excluded_paths:
            return True
        
        # Skip static files
        if path.startswith("/static/") or path.endswith((".css", ".js", ".png", ".jpg", ".ico")):
            return True
        
        return False
    
    async def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """Extract comprehensive request information."""
        
        # Basic request info
        info = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Extract request body for POST/PUT/PATCH requests
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Read body content
                body = await request.body()
                if body:
                    # Try to parse as JSON
                    try:
                        info["body"] = json.loads(body.decode())
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Store as string if not JSON
                        info["body"] = body.decode("utf-8", errors="ignore")[:1000]  # Limit size
                        
                    # Check for sensitive data in body
                    info["contains_sensitive_data"] = self._detect_sensitive_data(body)
            except Exception as e:
                logger.warning(f"Failed to extract request body: {e}")
                info["body_error"] = str(e)
        
        # Determine resource type and action
        info["resource_type"] = self._extract_resource_type(request.url.path)
        info["action"] = self.method_to_action.get(request.method, AuditAction.READ)
        
        # Check if this is a sensitive endpoint
        info["is_sensitive_endpoint"] = any(
            request.url.path.startswith(sensitive) 
            for sensitive in self.sensitive_endpoints
        )
        
        return info
    
    async def _extract_response_info(self, response: Response, response_time: float) -> Dict[str, Any]:
        """Extract response information."""
        
        info = {
            "status_code": response.status_code,
            "response_time": response_time,
            "headers": dict(response.headers),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Extract response body for analysis (limited size)
        if hasattr(response, 'body') and response.body:
            try:
                body_content = response.body
                if isinstance(body_content, bytes):
                    body_str = body_content.decode("utf-8", errors="ignore")[:1000]
                    info["body_preview"] = body_str
                    info["contains_sensitive_data"] = self._detect_sensitive_data(body_content)
            except Exception as e:
                logger.warning(f"Failed to extract response body: {e}")
        
        # Determine success/failure
        info["success"] = 200 <= response.status_code < 400
        
        return info
    
    async def _get_user_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract user context from request if available."""
        
        try:
            # Try to get authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            # Extract token
            token = auth_header.split(" ")[1]
            
            # Verify token
            payload = self.security_controller.verify_token(token)
            if not payload:
                return None
            
            # Get user from database
            with db_manager.get_session() as db:
                user = self.security_controller.get_user_by_id(payload["user_id"], db)
                if not user:
                    return None
                
                return {
                    "user_id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "role": user.role.value,
                    "tenant_id": user.tenant_id,
                    "is_active": user.is_active
                }
        
        except Exception as e:
            logger.debug(f"Failed to extract user context: {e}")
            return None
    
    async def _log_audit_event(
        self,
        request_id: str,
        request_info: Dict[str, Any],
        response_info: Dict[str, Any],
        user_context: Optional[Dict[str, Any]],
        success: bool
    ):
        """Log comprehensive audit event."""
        
        try:
            with db_manager.get_session() as db:
                # Prepare audit details
                audit_details = {
                    "request_id": request_id,
                    "request": {
                        "method": request_info["method"],
                        "path": request_info["path"],
                        "query_params": request_info["query_params"],
                        "user_agent": request_info["user_agent"],
                        "contains_sensitive_data": request_info.get("contains_sensitive_data", False),
                        "is_sensitive_endpoint": request_info.get("is_sensitive_endpoint", False)
                    },
                    "response": {
                        "status_code": response_info["status_code"],
                        "response_time": response_info["response_time"],
                        "success": success
                    },
                    "performance": {
                        "response_time_ms": response_info["response_time"] * 1000,
                        "slow_request": response_info["response_time"] > 5.0  # 5 second threshold
                    }
                }
                
                # Add request body info if available (sanitized)
                if "body" in request_info:
                    audit_details["request"]["has_body"] = True
                    audit_details["request"]["body_size"] = len(str(request_info["body"]))
                    
                    # Only include body for non-sensitive endpoints and if not too large
                    if (not request_info.get("is_sensitive_endpoint", False) and 
                        not request_info.get("contains_sensitive_data", False) and
                        audit_details["request"]["body_size"] < 1000):
                        audit_details["request"]["body_preview"] = request_info["body"]
                
                # Use enhanced audit service for logging
                await self.audit_service.log_enhanced_audit_event(
                    user_id=UUID(user_context["user_id"]) if user_context else None,
                    tenant_id=user_context["tenant_id"] if user_context else "system",
                    action=request_info["action"],
                    resource_type=request_info["resource_type"],
                    resource_id=self._extract_resource_id(request_info["path"]),
                    ip_address=request_info["client_ip"],
                    user_agent=request_info["user_agent"],
                    details=audit_details,
                    db=db
                )
                
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _extract_resource_type(self, path: str) -> str:
        """Extract resource type from URL path."""
        
        # Remove leading slash and split path
        path_parts = path.strip("/").split("/")
        
        if len(path_parts) < 2:
            return "system"
        
        # Skip 'api' prefix if present
        if path_parts[0] == "api":
            path_parts = path_parts[1:]
        
        if not path_parts:
            return "system"
        
        # Map common resource types
        resource_mapping = {
            "security": "security",
            "audit": "audit_log",
            "admin": "admin",
            "users": "user",
            "billing": "billing",
            "quality": "quality",
            "extraction": "extraction",
            "enhancement": "enhancement",
            "export": "export",
            "desensitization": "desensitization",
            "compliance": "compliance",
            "monitoring": "monitoring",
            "alerts": "alert",
            "notifications": "notification"
        }
        
        return resource_mapping.get(path_parts[0], path_parts[0])
    
    def _extract_resource_id(self, path: str) -> Optional[str]:
        """Extract resource ID from URL path if present."""
        
        path_parts = path.strip("/").split("/")
        
        # Look for UUID-like patterns or numeric IDs
        for part in path_parts:
            # Check for UUID pattern
            if len(part) == 36 and part.count("-") == 4:
                return part
            
            # Check for numeric ID
            if part.isdigit():
                return part
        
        return None
    
    def _detect_sensitive_data(self, content: bytes) -> bool:
        """Detect if content contains sensitive data patterns."""
        
        if not content:
            return False
        
        try:
            # Convert to string for pattern matching
            text = content.decode("utf-8", errors="ignore").lower()
            
            # Common sensitive data patterns
            sensitive_patterns = [
                "password",
                "secret",
                "token",
                "key",
                "credential",
                "ssn",
                "social security",
                "credit card",
                "bank account",
                "phone",
                "email",
                "address"
            ]
            
            # Check for patterns
            for pattern in sensitive_patterns:
                if pattern in text:
                    return True
            
            # Check for common data formats
            import re
            
            # Email pattern
            if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
                return True
            
            # Phone pattern
            if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text):
                return True
            
            # Credit card pattern (basic)
            if re.search(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', text):
                return True
            
            return False
            
        except Exception:
            return False


class AuditEventCollector:
    """
    Collects and batches audit events for performance optimization.
    """
    
    def __init__(self, batch_size: int = 100, flush_interval: int = 30):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.event_queue: List[Dict[str, Any]] = []
        self.last_flush = time.time()
        self.audit_service = EnhancedAuditService()
        
    async def add_event(self, event: Dict[str, Any]):
        """Add event to collection queue."""
        self.event_queue.append(event)
        
        # Check if we need to flush
        if (len(self.event_queue) >= self.batch_size or 
            time.time() - self.last_flush > self.flush_interval):
            await self.flush_events()
    
    async def flush_events(self):
        """Flush collected events to database."""
        if not self.event_queue:
            return
        
        try:
            with db_manager.get_session() as db:
                # Use bulk logging for performance
                success = self.audit_service.log_bulk_actions(self.event_queue, db)
                
                if success:
                    logger.info(f"Flushed {len(self.event_queue)} audit events")
                    self.event_queue.clear()
                    self.last_flush = time.time()
                else:
                    logger.error("Failed to flush audit events")
                    
        except Exception as e:
            logger.error(f"Error flushing audit events: {e}")


# Global audit event collector
audit_collector = AuditEventCollector()


class AuditConfiguration:
    """
    Configuration for audit middleware.
    """
    
    def __init__(self):
        self.enabled = True
        self.log_request_body = True
        self.log_response_body = False
        self.max_body_size = 10000  # 10KB
        self.excluded_paths = set()
        self.sensitive_endpoints = set()
        self.performance_threshold = 5.0  # seconds
        
    def add_excluded_path(self, path: str):
        """Add path to exclusion list."""
        self.excluded_paths.add(path)
    
    def add_sensitive_endpoint(self, endpoint: str):
        """Add endpoint to sensitive list."""
        self.sensitive_endpoints.add(endpoint)


# Global audit configuration
audit_config = AuditConfiguration()