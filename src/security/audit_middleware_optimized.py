"""
Performance-Optimized Audit Middleware.

Replaces the existing audit middleware with a high-performance version
that achieves < 50ms audit logging latency.
"""

import time
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from src.security.audit_performance_integration import (
    audit_performance_manager,
    log_audit_fast
)
from src.security.models import AuditAction
from src.security.controller import SecurityController

logger = logging.getLogger(__name__)


class OptimizedAuditMiddleware(BaseHTTPMiddleware):
    """
    Performance-optimized audit middleware with < 50ms latency target.
    
    Features:
    - Minimal request processing overhead
    - Asynchronous audit logging
    - Automatic performance monitoring
    - Graceful degradation on performance issues
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.security_controller = SecurityController()
        
        # Excluded paths (minimal set for performance)
        self.excluded_paths = {
            "/health", "/health/live", "/health/ready",
            "/metrics", "/docs", "/openapi.json", "/favicon.ico"
        }
        
        # Action mapping
        self.method_to_action = {
            "GET": AuditAction.READ,
            "POST": AuditAction.CREATE,
            "PUT": AuditAction.UPDATE,
            "PATCH": AuditAction.UPDATE,
            "DELETE": AuditAction.DELETE
        }
        
        # Performance tracking
        self.request_count = 0
        self.total_audit_time = 0.0
        self.failed_audits = 0
    
    async def dispatch(self, request: Request, call_next):
        """Process request with optimized audit logging."""
        
        # Quick exclusion check
        if self._should_skip_audit(request):
            return await call_next(request)
        
        # Start request processing
        request_start = time.perf_counter()
        request_id = f"req_{int(request_start * 1000000)}"
        
        # Extract minimal request info for performance
        request_info = self._extract_minimal_request_info(request)
        
        # Get user context (cached for performance)
        user_context = await self._get_user_context_fast(request)
        
        # Execute the request
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.perf_counter() - request_start
            
            # Log audit event asynchronously for minimal latency impact
            asyncio.create_task(
                self._log_audit_async(
                    request_id=request_id,
                    request_info=request_info,
                    user_context=user_context,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=True
                )
            )
            
            return response
            
        except Exception as e:
            # Calculate response time for failed requests
            response_time = time.perf_counter() - request_start
            
            # Log failed request asynchronously
            asyncio.create_task(
                self._log_audit_async(
                    request_id=request_id,
                    request_info=request_info,
                    user_context=user_context,
                    response_status=500,
                    response_time=response_time,
                    success=False,
                    error=str(e)
                )
            )
            
            raise
    
    def _should_skip_audit(self, request: Request) -> bool:
        """Fast path exclusion check."""
        path = request.url.path
        
        # Quick exclusion checks
        if path in self.excluded_paths:
            return True
        
        # Skip static files (fast check)
        if path.startswith("/static/") or "." in path.split("/")[-1]:
            return True
        
        return False
    
    def _extract_minimal_request_info(self, request: Request) -> Dict[str, Any]:
        """Extract minimal request information for performance."""
        
        return {
            "method": request.method,
            "path": request.url.path,
            "client_ip": self._get_client_ip_fast(request),
            "user_agent": request.headers.get("user-agent", "")[:200],  # Truncate for performance
            "resource_type": self._extract_resource_type_fast(request.url.path),
            "action": self.method_to_action.get(request.method, AuditAction.READ),
            "timestamp": datetime.utcnow()
        }
    
    def _get_client_ip_fast(self, request: Request) -> str:
        """Fast client IP extraction."""
        # Check most common headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        return request.client.host if request.client else "unknown"
    
    def _extract_resource_type_fast(self, path: str) -> str:
        """Fast resource type extraction."""
        # Simple path-based resource type extraction
        path_parts = path.strip("/").split("/")
        
        if len(path_parts) >= 2 and path_parts[0] == "api":
            return path_parts[1]
        elif len(path_parts) >= 1:
            return path_parts[0]
        
        return "system"
    
    async def _get_user_context_fast(self, request: Request) -> Optional[Dict[str, Any]]:
        """Fast user context extraction with minimal overhead."""
        
        try:
            # Quick auth header check
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            # Extract and verify token (this could be cached for better performance)
            token = auth_header.split(" ")[1]
            payload = self.security_controller.verify_token(token)
            
            if not payload:
                return None
            
            # Return minimal user context for performance
            return {
                "user_id": payload.get("user_id"),
                "tenant_id": payload.get("tenant_id", "unknown"),
                "role": payload.get("role", "unknown")
            }
            
        except Exception:
            # Fail silently for performance
            return None
    
    async def _log_audit_async(
        self,
        request_id: str,
        request_info: Dict[str, Any],
        user_context: Optional[Dict[str, Any]],
        response_status: int,
        response_time: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Log audit event asynchronously with performance optimization."""
        
        audit_start = time.perf_counter()
        
        try:
            # Prepare minimal audit details for performance
            details = {
                "request_id": request_id,
                "method": request_info["method"],
                "path": request_info["path"],
                "status_code": response_status,
                "response_time_ms": response_time * 1000,
                "success": success
            }
            
            # Add error info if present
            if error:
                details["error"] = error[:500]  # Truncate for performance
            
            # Log using performance-optimized service
            result = await log_audit_fast(
                user_id=UUID(user_context["user_id"]) if user_context and user_context.get("user_id") else None,
                tenant_id=user_context["tenant_id"] if user_context else "system",
                action=request_info["action"],
                resource_type=request_info["resource_type"],
                ip_address=request_info["client_ip"],
                user_agent=request_info["user_agent"],
                details=details
            )
            
            # Track performance metrics
            audit_time = time.perf_counter() - audit_start
            self._update_performance_metrics(audit_time, result.get('status') == 'success')
            
            # Log performance warnings if needed
            if result.get('latency_ms', 0) > 50.0:
                logger.warning(
                    f"Audit logging latency {result.get('latency_ms', 0):.2f}ms exceeds 50ms target"
                )
            
        except Exception as e:
            audit_time = time.perf_counter() - audit_start
            self._update_performance_metrics(audit_time, False)
            
            logger.error(f"Async audit logging failed: {e}")
    
    def _update_performance_metrics(self, audit_time: float, success: bool):
        """Update internal performance metrics."""
        
        self.request_count += 1
        self.total_audit_time += audit_time
        
        if not success:
            self.failed_audits += 1
        
        # Log performance summary periodically
        if self.request_count % 1000 == 0:
            avg_audit_time = (self.total_audit_time / self.request_count) * 1000  # Convert to ms
            failure_rate = self.failed_audits / self.request_count
            
            logger.info(
                f"Audit middleware performance: {self.request_count} requests, "
                f"avg audit time: {avg_audit_time:.2f}ms, "
                f"failure rate: {failure_rate:.2%}"
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get middleware performance statistics."""
        
        if self.request_count == 0:
            return {"status": "no_data"}
        
        avg_audit_time_ms = (self.total_audit_time / self.request_count) * 1000
        failure_rate = self.failed_audits / self.request_count
        
        return {
            "total_requests": self.request_count,
            "average_audit_time_ms": avg_audit_time_ms,
            "failure_rate": failure_rate,
            "total_failed_audits": self.failed_audits,
            "performance_grade": (
                "excellent" if avg_audit_time_ms < 10.0 else
                "good" if avg_audit_time_ms < 25.0 else
                "acceptable" if avg_audit_time_ms < 50.0 else
                "poor"
            )
        }


class AuditMiddlewareManager:
    """
    Manages the optimized audit middleware lifecycle.
    """
    
    def __init__(self):
        self.middleware_instance: Optional[OptimizedAuditMiddleware] = None
        self.started = False
    
    async def initialize(self):
        """Initialize the audit middleware manager."""
        
        if not self.started:
            # Start the audit performance manager
            await audit_performance_manager.start()
            self.started = True
            
            logger.info("Audit middleware manager initialized")
    
    async def shutdown(self):
        """Shutdown the audit middleware manager."""
        
        if self.started:
            # Stop the audit performance manager
            await audit_performance_manager.stop()
            self.started = False
            
            logger.info("Audit middleware manager shutdown")
    
    def create_middleware(self, app):
        """Create optimized audit middleware instance."""
        
        self.middleware_instance = OptimizedAuditMiddleware(app)
        return self.middleware_instance
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        
        report = {
            "manager_status": {
                "started": self.started,
                "middleware_created": self.middleware_instance is not None
            }
        }
        
        # Add middleware stats if available
        if self.middleware_instance:
            report["middleware_stats"] = self.middleware_instance.get_performance_stats()
        
        # Add audit manager stats
        report["audit_manager_stats"] = audit_performance_manager.get_performance_summary()
        
        return report


# Global middleware manager
audit_middleware_manager = AuditMiddlewareManager()


# FastAPI integration helper
def add_optimized_audit_middleware(app):
    """
    Add optimized audit middleware to FastAPI application.
    
    Usage:
        from src.security.audit_middleware_optimized import add_optimized_audit_middleware
        
        app = FastAPI()
        add_optimized_audit_middleware(app)
    """
    
    # Create and add the middleware
    middleware = audit_middleware_manager.create_middleware(app)
    app.add_middleware(OptimizedAuditMiddleware)
    
    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_audit_middleware():
        await audit_middleware_manager.initialize()
    
    @app.on_event("shutdown")
    async def shutdown_audit_middleware():
        await audit_middleware_manager.shutdown()
    
    logger.info("Optimized audit middleware added to FastAPI application")
    
    return middleware


# Performance monitoring endpoint helper
def add_audit_performance_endpoints(app):
    """
    Add audit performance monitoring endpoints.
    
    Adds endpoints:
    - GET /audit/performance/stats - Get performance statistics
    - POST /audit/performance/test - Run performance test
    """
    
    from fastapi import APIRouter
    
    router = APIRouter(prefix="/audit/performance", tags=["audit-performance"])
    
    @router.get("/stats")
    async def get_audit_performance_stats():
        """Get audit performance statistics."""
        return audit_middleware_manager.get_performance_report()
    
    @router.post("/test")
    async def run_audit_performance_test(num_logs: int = 100):
        """Run audit performance test."""
        return await audit_performance_manager.run_performance_test(num_logs)
    
    @router.get("/health")
    async def get_audit_health():
        """Get audit system health status."""
        stats = audit_performance_manager.get_performance_summary()
        
        health_status = "healthy"
        if stats.get('status') == 'no_data':
            health_status = "unknown"
        elif stats.get('service_health', {}).get('health_status') == 'degraded':
            health_status = "degraded"
        
        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "details": stats
        }
    
    app.include_router(router)
    logger.info("Audit performance endpoints added to FastAPI application")