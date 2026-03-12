"""
API Key Authentication Middleware for External API Access.

Provides X-API-Key header authentication, rate limiting per key,
and automatic API call logging for external API requests.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.sync.gateway.api_key_service import APIKeyService
from src.sync.gateway.rate_limiter import RateLimitResult
from src.sync.models import APIKeyModel, APICallLogModel
from src.database.connection import db_manager


logger = logging.getLogger(__name__)


class APIKeyRateLimiter:
    """
    Rate limiter for API keys with per-minute and per-day quotas.
    
    Extends the existing rate limiting infrastructure to support
    API key-specific quotas.
    """
    
    def __init__(self):
        """Initialize API key rate limiter."""
        # In-memory counters for per-minute limits
        self._minute_counters: Dict[UUID, Dict[str, Any]] = {}
        # In-memory counters for per-day limits
        self._day_counters: Dict[UUID, Dict[str, Any]] = {}
    
    def _get_current_minute_window(self) -> int:
        """Get current minute window timestamp."""
        return int(time.time() / 60) * 60
    
    def _get_current_day_window(self) -> int:
        """Get current day window timestamp."""
        return int(time.time() / 86400) * 86400
    
    async def check_rate_limit(
        self,
        api_key: APIKeyModel
    ) -> RateLimitResult:
        """
        Check rate limit for an API key.
        
        Args:
            api_key: The API key model with rate limit configuration
        
        Returns:
            RateLimitResult indicating if request is allowed
        """
        now = time.time()
        key_id = api_key.id
        
        # Check per-minute limit
        minute_window = self._get_current_minute_window()
        
        if key_id not in self._minute_counters:
            self._minute_counters[key_id] = {
                "window": minute_window,
                "count": 0
            }
        
        minute_state = self._minute_counters[key_id]
        
        # Reset if new window
        if minute_state["window"] != minute_window:
            minute_state["window"] = minute_window
            minute_state["count"] = 0
        
        # Check minute limit
        if minute_state["count"] >= api_key.rate_limit_per_minute:
            retry_after = int(minute_window + 60 - now)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=api_key.rate_limit_per_minute,
                reset_at=minute_window + 60,
                retry_after=retry_after,
                rule_name="api_key_per_minute"
            )
        
        # Check per-day limit
        day_window = self._get_current_day_window()
        
        if key_id not in self._day_counters:
            self._day_counters[key_id] = {
                "window": day_window,
                "count": 0
            }
        
        day_state = self._day_counters[key_id]
        
        # Reset if new window
        if day_state["window"] != day_window:
            day_state["window"] = day_window
            day_state["count"] = 0
        
        # Check day limit
        if day_state["count"] >= api_key.rate_limit_per_day:
            retry_after = int(day_window + 86400 - now)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=api_key.rate_limit_per_day,
                reset_at=day_window + 86400,
                retry_after=retry_after,
                rule_name="api_key_per_day"
            )
        
        # Increment counters
        minute_state["count"] += 1
        day_state["count"] += 1
        
        # Return success with remaining counts
        minute_remaining = api_key.rate_limit_per_minute - minute_state["count"]
        
        return RateLimitResult(
            allowed=True,
            remaining=minute_remaining,
            limit=api_key.rate_limit_per_minute,
            reset_at=minute_window + 60,
            retry_after=None,
            rule_name="api_key_per_minute"
        )
    
    async def cleanup(self) -> int:
        """
        Clean up expired rate limit state.
        
        Returns:
            Number of cleaned entries
        """
        now = time.time()
        current_minute = self._get_current_minute_window()
        current_day = self._get_current_day_window()
        cleaned = 0
        
        # Clean minute counters older than 2 minutes
        expired_minute_keys = [
            key for key, state in self._minute_counters.items()
            if state["window"] < current_minute - 120
        ]
        for key in expired_minute_keys:
            del self._minute_counters[key]
            cleaned += 1
        
        # Clean day counters older than 2 days
        expired_day_keys = [
            key for key, state in self._day_counters.items()
            if state["window"] < current_day - 172800
        ]
        for key in expired_day_keys:
            del self._day_counters[key]
            cleaned += 1
        
        return cleaned


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication on external API endpoints.
    
    Features:
    - X-API-Key header authentication
    - Per-key rate limiting (minute and daily quotas)
    - Automatic API call logging
    - Scope-based permission checking
    """
    
    HEADER_NAME = "X-API-Key"
    
    def __init__(
        self,
        app: ASGIApp,
        api_key_service: Optional[APIKeyService] = None,
        rate_limiter: Optional[APIKeyRateLimiter] = None,
        protected_paths: Optional[list[str]] = None
    ):
        """
        Initialize API key authentication middleware.
        
        Args:
            app: ASGI application
            api_key_service: API key service instance
            rate_limiter: API key rate limiter instance
            protected_paths: List of path prefixes that require API key auth
        """
        super().__init__(app)
        self.api_key_service = api_key_service or APIKeyService()
        self.rate_limiter = rate_limiter or APIKeyRateLimiter()
        self.protected_paths = protected_paths or ["/api/v1/external/"]
    
    def _is_protected_path(self, path: str) -> bool:
        """Check if path requires API key authentication."""
        return any(path.startswith(prefix) for prefix in self.protected_paths)
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers."""
        return request.headers.get(self.HEADER_NAME)
    
    async def _log_api_call(
        self,
        key_id: UUID,
        endpoint: str,
        status_code: int,
        response_time_ms: float
    ) -> None:
        """
        Log API call to database.
        
        Args:
            key_id: API key ID
            endpoint: Request endpoint
            status_code: Response status code
            response_time_ms: Response time in milliseconds
        """
        try:
            with db_manager.get_session() as session:
                log_entry = APICallLogModel(
                    key_id=key_id,
                    endpoint=endpoint,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    called_at=datetime.utcnow()
                )
                session.add(log_entry)
                session.commit()
                
                logger.debug(
                    f"Logged API call: key_id={key_id}, endpoint={endpoint}, "
                    f"status={status_code}, time={response_time_ms}ms"
                )
        except Exception as e:
            # Don't fail request if logging fails
            logger.error(f"Failed to log API call: {e}")
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request with API key authentication.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
        
        Returns:
            Response
        
        Raises:
            HTTPException: If authentication or rate limiting fails
        """
        path = str(request.url.path)
        
        # Skip non-protected paths
        if not self._is_protected_path(path):
            return await call_next(request)
        
        start_time = time.time()
        status_code = 200
        
        try:
            # Extract API key
            raw_key = self._extract_api_key(request)
            if not raw_key:
                logger.warning(f"Missing API key for protected path: {path}")
                status_code = 401
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "Authentication required",
                        "error_code": "MISSING_API_KEY",
                        "message": f"Missing {self.HEADER_NAME} header"
                    }
                )
            
            # Validate API key
            api_key = self.api_key_service.validate_key(raw_key)
            if not api_key:
                logger.warning(f"Invalid API key for path: {path}")
                status_code = 401
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "Authentication failed",
                        "error_code": "INVALID_API_KEY",
                        "message": "Invalid or expired API key"
                    }
                )
            
            # Check rate limits
            rate_limit_result = await self.rate_limiter.check_rate_limit(api_key)
            
            if not rate_limit_result.allowed:
                logger.warning(
                    f"Rate limit exceeded for API key {api_key.id}: "
                    f"rule={rate_limit_result.rule_name}"
                )
                
                # Log the rate-limited call
                response_time_ms = (time.time() - start_time) * 1000
                await self._log_api_call(
                    api_key.id,
                    path,
                    429,
                    response_time_ms
                )
                
                status_code = 429
                headers = {
                    "X-RateLimit-Limit": str(rate_limit_result.limit),
                    "X-RateLimit-Remaining": str(rate_limit_result.remaining),
                    "X-RateLimit-Reset": str(int(rate_limit_result.reset_at)),
                    "Retry-After": str(rate_limit_result.retry_after)
                }
                
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "retry_after": rate_limit_result.retry_after,
                        "limit": rate_limit_result.limit,
                        "window": rate_limit_result.rule_name
                    },
                    headers=headers
                )
            
            # Store API key in request state for downstream use
            request.state.api_key = api_key
            request.state.tenant_id = api_key.tenant_id
            
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
            # Add rate limit headers to response
            response.headers["X-RateLimit-Limit"] = str(rate_limit_result.limit)
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_result.remaining)
            response.headers["X-RateLimit-Reset"] = str(int(rate_limit_result.reset_at))
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            status_code = 500
            logger.error(f"Error processing API request: {e}")
            raise
        finally:
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Log API call if we have an API key
            if hasattr(request.state, "api_key"):
                await self._log_api_call(
                    request.state.api_key.id,
                    path,
                    status_code,
                    response_time_ms
                )
                
                # Update API key usage statistics
                try:
                    self.api_key_service.update_usage(request.state.api_key.id, increment_calls=True)
                except Exception as e:
                    logger.error(f"Failed to update API key usage: {e}")


# Global instances
api_key_rate_limiter = APIKeyRateLimiter()
