"""
License Middleware for SuperInsight Platform.

Validates license and enforces access control on API requests.
"""

from datetime import datetime, timezone
from typing import Optional, List, Callable, Set
import logging

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.license.license_validator import LicenseValidator
from src.license.time_controller import TimeController
from src.license.feature_controller import FeatureController
from src.schemas.license import ValidityStatus


logger = logging.getLogger(__name__)


class LicenseMiddleware(BaseHTTPMiddleware):
    """
    License validation middleware.
    
    Validates license on each request and enforces access control.
    """
    
    # Routes that don't require license validation
    DEFAULT_WHITELIST = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/activation/activate",
        "/api/v1/activation/offline/request",
        "/api/v1/activation/offline/activate",
        "/api/v1/activation/fingerprint",
        "/api/v1/license/status",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
    }
    
    # Route prefixes that don't require license validation
    DEFAULT_WHITELIST_PREFIXES = {
        "/static/",
        "/assets/",
    }
    
    # Feature to route mapping
    FEATURE_ROUTES = {
        "ai_annotation": ["/api/v1/ai/", "/api/v1/annotation/ai/"],
        "knowledge_graph": ["/api/v1/knowledge/", "/api/v1/graph/"],
        "advanced_analytics": ["/api/v1/analytics/advanced/", "/api/v1/reports/advanced/"],
        "export": ["/api/v1/export/"],
        "multi_tenant": ["/api/v1/tenants/"],
        "quality_assessment": ["/api/v1/quality/"],
    }
    
    def __init__(
        self,
        app,
        validator: Optional[LicenseValidator] = None,
        time_controller: Optional[TimeController] = None,
        whitelist: Optional[Set[str]] = None,
        whitelist_prefixes: Optional[Set[str]] = None,
        enabled: bool = True,
    ):
        """
        Initialize License Middleware.
        
        Args:
            app: FastAPI application
            validator: License validator instance
            time_controller: Time controller instance
            whitelist: Additional routes to whitelist
            whitelist_prefixes: Additional route prefixes to whitelist
            enabled: Whether middleware is enabled
        """
        super().__init__(app)
        self.validator = validator or LicenseValidator()
        self.time_controller = time_controller or TimeController()
        self.whitelist = self.DEFAULT_WHITELIST.copy()
        self.whitelist_prefixes = self.DEFAULT_WHITELIST_PREFIXES.copy()
        self.enabled = enabled
        
        if whitelist:
            self.whitelist.update(whitelist)
        if whitelist_prefixes:
            self.whitelist_prefixes.update(whitelist_prefixes)
    
    def _is_whitelisted(self, path: str) -> bool:
        """Check if path is whitelisted."""
        if path in self.whitelist:
            return True
        
        for prefix in self.whitelist_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _get_required_feature(self, path: str) -> Optional[str]:
        """Get required feature for a path."""
        for feature, routes in self.FEATURE_ROUTES.items():
            for route in routes:
                if path.startswith(route):
                    return feature
        return None
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request through middleware."""
        # Skip if disabled
        if not self.enabled:
            return await call_next(request)
        
        path = request.url.path
        
        # Skip whitelisted routes
        if self._is_whitelisted(path):
            return await call_next(request)
        
        # Get license from app state (should be set during startup)
        license_model = getattr(request.app.state, "current_license", None)
        
        if not license_model:
            # Try to get from database
            # This is a fallback - ideally license should be cached in app state
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "detail": "No valid license found",
                    "code": "LICENSE_REQUIRED"
                }
            )
        
        # Validate license
        validation = self.validator.validate_license_sync(license_model)
        
        if not validation.valid:
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "detail": validation.reason or "License validation failed",
                    "code": "LICENSE_INVALID"
                }
            )
        
        # Check validity status
        validity = self.time_controller.check_license_validity(license_model)
        
        if validity.status == ValidityStatus.EXPIRED:
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "detail": "License has expired",
                    "code": "LICENSE_EXPIRED"
                }
            )
        
        if validity.status == ValidityStatus.NOT_STARTED:
            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "detail": f"License validity starts in {validity.days_until_start} days",
                    "code": "LICENSE_NOT_STARTED"
                }
            )
        
        # Check feature access
        required_feature = self._get_required_feature(path)
        if required_feature:
            if required_feature not in license_model.features:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": f"Feature '{required_feature}' is not available in your license",
                        "code": "FEATURE_NOT_LICENSED",
                        "feature": required_feature
                    }
                )
        
        # Check grace period restrictions
        if validity.status == ValidityStatus.GRACE_PERIOD:
            restrictions = self.time_controller.get_expiry_restrictions(license_model)
            
            # Apply restrictions
            if "export_disabled" in restrictions and path.startswith("/api/v1/export/"):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "Export is disabled during grace period",
                        "code": "GRACE_PERIOD_RESTRICTION"
                    }
                )
            
            if "ai_features_disabled" in restrictions and path.startswith("/api/v1/ai/"):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "AI features are disabled during grace period",
                        "code": "GRACE_PERIOD_RESTRICTION"
                    }
                )
        
        # Add license info to request state
        request.state.license = license_model
        request.state.license_validity = validity
        
        # Add warning headers if applicable
        response = await call_next(request)
        
        if validity.status == ValidityStatus.GRACE_PERIOD:
            response.headers["X-License-Warning"] = f"License expired, {validity.grace_days_remaining} grace days remaining"
        elif validity.days_remaining and validity.days_remaining <= 30:
            response.headers["X-License-Warning"] = f"License expires in {validity.days_remaining} days"
        
        return response


class ConcurrentUserMiddleware(BaseHTTPMiddleware):
    """
    Concurrent user tracking middleware.
    
    Tracks user sessions and enforces concurrent user limits.
    """
    
    # Routes that don't require session tracking
    EXCLUDED_ROUTES = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    def __init__(
        self,
        app,
        enabled: bool = True,
    ):
        """
        Initialize Concurrent User Middleware.
        
        Args:
            app: FastAPI application
            enabled: Whether middleware is enabled
        """
        super().__init__(app)
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request through middleware."""
        if not self.enabled:
            return await call_next(request)
        
        path = request.url.path
        
        # Skip excluded routes
        if path in self.EXCLUDED_ROUTES:
            return await call_next(request)
        
        # Get user from request (should be set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        session_id = request.headers.get("X-Session-ID")
        
        if user_id and session_id:
            # Update session activity
            controller = getattr(request.app.state, "concurrent_controller", None)
            if controller:
                await controller.update_session_activity(user_id, session_id)
        
        return await call_next(request)


def create_license_middleware(
    validator: Optional[LicenseValidator] = None,
    time_controller: Optional[TimeController] = None,
    whitelist: Optional[Set[str]] = None,
    enabled: bool = True,
) -> Callable:
    """
    Create license middleware factory.
    
    Args:
        validator: License validator instance
        time_controller: Time controller instance
        whitelist: Additional routes to whitelist
        enabled: Whether middleware is enabled
        
    Returns:
        Middleware factory function
    """
    def middleware_factory(app):
        return LicenseMiddleware(
            app,
            validator=validator,
            time_controller=time_controller,
            whitelist=whitelist,
            enabled=enabled,
        )
    
    return middleware_factory
