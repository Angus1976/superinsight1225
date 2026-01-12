"""
Automatic Desensitization Middleware

Middleware that automatically detects and masks sensitive data in
API requests and responses in real-time.
"""

import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.security.auto_desensitization_service import AutoDesensitizationService
from src.security.controller import SecurityController
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)


class AutoDesensitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic sensitive data detection and masking.
    
    Intercepts API requests and responses to automatically detect
    and mask sensitive data based on tenant policies.
    """
    
    def __init__(
        self,
        app,
        enabled: bool = True,
        mask_requests: bool = True,
        mask_responses: bool = True,
        excluded_paths: Optional[List[str]] = None,
        max_content_size: int = 10 * 1024 * 1024  # 10MB
    ):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI application
            enabled: Whether middleware is enabled
            mask_requests: Whether to mask request data
            mask_responses: Whether to mask response data
            excluded_paths: Paths to exclude from processing
            max_content_size: Maximum content size to process
        """
        super().__init__(app)
        self.enabled = enabled
        self.mask_requests = mask_requests
        self.mask_responses = mask_responses
        self.excluded_paths = excluded_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/static",
            "/favicon.ico"
        ]
        self.max_content_size = max_content_size
        
        # Initialize desensitization service
        self.desensitization_service = AutoDesensitizationService()
        
        # Performance tracking
        self.processing_stats = {
            "total_requests": 0,
            "processed_requests": 0,
            "skipped_requests": 0,
            "error_count": 0,
            "total_processing_time": 0.0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and response for sensitive data.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response
        """
        start_time = time.time()
        self.processing_stats["total_requests"] += 1
        
        # Check if middleware is enabled
        if not self.enabled:
            return await call_next(request)
        
        # Check if path should be excluded
        if self._should_exclude_path(request.url.path):
            self.processing_stats["skipped_requests"] += 1
            return await call_next(request)
        
        try:
            # Get user context
            user_context = await self._get_user_context(request)
            if not user_context:
                # No user context, skip processing
                return await call_next(request)
            
            # Process request if enabled
            if self.mask_requests:
                request = await self._process_request(request, user_context)
            
            # Call next middleware/handler
            response = await call_next(request)
            
            # Process response if enabled
            if self.mask_responses:
                response = await self._process_response(response, user_context)
            
            self.processing_stats["processed_requests"] += 1
            
        except Exception as e:
            logger.error(f"Auto-desensitization middleware error: {e}")
            self.processing_stats["error_count"] += 1
            
            # Continue with original request/response on error
            response = await call_next(request)
        
        finally:
            processing_time = time.time() - start_time
            self.processing_stats["total_processing_time"] += processing_time
        
        return response
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from processing."""
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return True
        return False
    
    async def _get_user_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract user context from request."""
        try:
            # Extract JWT token from Authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header.split(" ")[1]
            
            # Initialize security controller and verify token
            security_controller = SecurityController()
            payload = security_controller.verify_token(token)
            
            if not payload:
                return None
            
            # Get database session and user
            db = next(get_db_session())
            try:
                user = security_controller.get_user_by_id(payload["user_id"], db)
                if user and user.is_active:
                    return {
                        "user_id": str(user.id),
                        "tenant_id": str(user.tenant_id),
                        "username": user.username,
                        "roles": [user.role.value] if hasattr(user, 'role') else []
                    }
            finally:
                db.close()
                
        except Exception as e:
            logger.debug(f"Could not extract user context: {e}")
        
        return None
    
    async def _process_request(
        self,
        request: Request,
        user_context: Dict[str, Any]
    ) -> Request:
        """
        Process request for sensitive data.
        
        Args:
            request: HTTP request
            user_context: User context information
            
        Returns:
            Processed request
        """
        try:
            # Check content size
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_content_size:
                logger.warning(f"Request too large for processing: {content_length} bytes")
                return request
            
            # Read request body
            body = await request.body()
            if not body:
                return request
            
            # Parse JSON body if applicable
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    json_data = json.loads(body.decode("utf-8"))
                    
                    # Process JSON data for sensitive information
                    result = await self.desensitization_service.detect_and_mask_automatically(
                        data=json_data,
                        tenant_id=user_context["tenant_id"],
                        user_id=user_context["user_id"],
                        context={
                            "request_path": request.url.path,
                            "request_method": request.method,
                            "content_type": content_type
                        },
                        operation_type="api_request"
                    )
                    
                    if result["success"] and result["entities_detected"]:
                        # Replace request body with masked data
                        masked_json = json.dumps(result["masked_data"])
                        request._body = masked_json.encode("utf-8")
                        
                        # Update content-length header
                        request.headers.__dict__["_list"] = [
                            (name, value) if name != b"content-length" 
                            else (name, str(len(masked_json)).encode())
                            for name, value in request.headers.raw
                        ]
                        
                        logger.info(
                            f"Masked {len(result['entities_detected'])} entities in request "
                            f"for user {user_context['user_id']}"
                        )
                    
                except json.JSONDecodeError:
                    logger.debug("Request body is not valid JSON, skipping processing")
                except Exception as e:
                    logger.error(f"Request processing error: {e}")
            
            elif "text/" in content_type or "application/xml" in content_type:
                # Process text/XML content
                text_data = body.decode("utf-8")
                
                result = await self.desensitization_service.detect_and_mask_automatically(
                    data=text_data,
                    tenant_id=user_context["tenant_id"],
                    user_id=user_context["user_id"],
                    context={
                        "request_path": request.url.path,
                        "request_method": request.method,
                        "content_type": content_type
                    },
                    operation_type="api_request"
                )
                
                if result["success"] and result["entities_detected"]:
                    # Replace request body with masked text
                    masked_text = result["masked_data"]
                    request._body = masked_text.encode("utf-8")
                    
                    # Update content-length header
                    request.headers.__dict__["_list"] = [
                        (name, value) if name != b"content-length" 
                        else (name, str(len(masked_text)).encode())
                        for name, value in request.headers.raw
                    ]
                    
                    logger.info(
                        f"Masked {len(result['entities_detected'])} entities in text request "
                        f"for user {user_context['user_id']}"
                    )
            
        except Exception as e:
            logger.error(f"Request processing failed: {e}")
        
        return request
    
    async def _process_response(
        self,
        response: Response,
        user_context: Dict[str, Any]
    ) -> Response:
        """
        Process response for sensitive data.
        
        Args:
            response: HTTP response
            user_context: User context information
            
        Returns:
            Processed response
        """
        try:
            # Only process successful responses with content
            if response.status_code >= 400:
                return response
            
            # Check if response has body
            if not hasattr(response, 'body') or not response.body:
                return response
            
            # Check content size
            if len(response.body) > self.max_content_size:
                logger.warning(f"Response too large for processing: {len(response.body)} bytes")
                return response
            
            # Get content type
            content_type = response.headers.get("content-type", "")
            
            if "application/json" in content_type:
                try:
                    # Parse JSON response
                    json_data = json.loads(response.body.decode("utf-8"))
                    
                    # Process JSON data for sensitive information
                    result = await self.desensitization_service.detect_and_mask_automatically(
                        data=json_data,
                        tenant_id=user_context["tenant_id"],
                        user_id=user_context["user_id"],
                        context={
                            "response_status": response.status_code,
                            "content_type": content_type
                        },
                        operation_type="api_response"
                    )
                    
                    if result["success"] and result["entities_detected"]:
                        # Create new response with masked data
                        masked_response = JSONResponse(
                            content=result["masked_data"],
                            status_code=response.status_code,
                            headers=dict(response.headers)
                        )
                        
                        # Add desensitization metadata header
                        masked_response.headers["X-Desensitization-Applied"] = "true"
                        masked_response.headers["X-Entities-Masked"] = str(len(result["entities_detected"]))
                        
                        logger.info(
                            f"Masked {len(result['entities_detected'])} entities in response "
                            f"for user {user_context['user_id']}"
                        )
                        
                        return masked_response
                    
                except json.JSONDecodeError:
                    logger.debug("Response body is not valid JSON, skipping processing")
                except Exception as e:
                    logger.error(f"Response JSON processing error: {e}")
            
            elif "text/" in content_type or "application/xml" in content_type:
                # Process text/XML response
                text_data = response.body.decode("utf-8")
                
                result = await self.desensitization_service.detect_and_mask_automatically(
                    data=text_data,
                    tenant_id=user_context["tenant_id"],
                    user_id=user_context["user_id"],
                    context={
                        "response_status": response.status_code,
                        "content_type": content_type
                    },
                    operation_type="api_response"
                )
                
                if result["success"] and result["entities_detected"]:
                    # Create new response with masked text
                    masked_response = Response(
                        content=result["masked_data"],
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=content_type
                    )
                    
                    # Add desensitization metadata headers
                    masked_response.headers["X-Desensitization-Applied"] = "true"
                    masked_response.headers["X-Entities-Masked"] = str(len(result["entities_detected"]))
                    
                    logger.info(
                        f"Masked {len(result['entities_detected'])} entities in text response "
                        f"for user {user_context['user_id']}"
                    )
                    
                    return masked_response
            
        except Exception as e:
            logger.error(f"Response processing failed: {e}")
        
        return response
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get middleware processing statistics."""
        total_requests = self.processing_stats["total_requests"]
        
        return {
            "enabled": self.enabled,
            "total_requests": total_requests,
            "processed_requests": self.processing_stats["processed_requests"],
            "skipped_requests": self.processing_stats["skipped_requests"],
            "error_count": self.processing_stats["error_count"],
            "processing_rate": (
                self.processing_stats["processed_requests"] / total_requests
                if total_requests > 0 else 0.0
            ),
            "average_processing_time": (
                self.processing_stats["total_processing_time"] / total_requests
                if total_requests > 0 else 0.0
            ),
            "configuration": {
                "mask_requests": self.mask_requests,
                "mask_responses": self.mask_responses,
                "max_content_size": self.max_content_size,
                "excluded_paths": self.excluded_paths
            }
        }
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self.processing_stats = {
            "total_requests": 0,
            "processed_requests": 0,
            "skipped_requests": 0,
            "error_count": 0,
            "total_processing_time": 0.0
        }
    
    def update_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update middleware configuration.
        
        Args:
            config: Configuration updates
            
        Returns:
            Dict containing update result
        """
        try:
            valid_keys = {
                "enabled",
                "mask_requests",
                "mask_responses",
                "excluded_paths",
                "max_content_size"
            }
            
            invalid_keys = set(config.keys()) - valid_keys
            if invalid_keys:
                return {
                    "success": False,
                    "error": f"Invalid configuration keys: {invalid_keys}"
                }
            
            # Apply configuration updates
            for key, value in config.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            return {
                "success": True,
                "message": "Configuration updated successfully",
                "applied_config": config
            }
            
        except Exception as e:
            logger.error(f"Configuration update failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class StreamingDesensitizationMiddleware:
    """
    Middleware for streaming data desensitization.
    
    Handles real-time desensitization of streaming data
    such as WebSocket messages or Server-Sent Events.
    """
    
    def __init__(self, desensitization_service: AutoDesensitizationService):
        """Initialize streaming middleware."""
        self.desensitization_service = desensitization_service
        self.active_streams = {}
        
    async def process_stream_message(
        self,
        message: Any,
        stream_id: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process streaming message for sensitive data.
        
        Args:
            message: Stream message
            stream_id: Stream identifier
            user_context: User context information
            
        Returns:
            Dict containing processed message and metadata
        """
        try:
            result = await self.desensitization_service.detect_and_mask_automatically(
                data=message,
                tenant_id=user_context["tenant_id"],
                user_id=user_context["user_id"],
                context={
                    "stream_id": stream_id,
                    "message_type": type(message).__name__
                },
                operation_type="stream_message"
            )
            
            # Track stream statistics
            if stream_id not in self.active_streams:
                self.active_streams[stream_id] = {
                    "messages_processed": 0,
                    "entities_detected": 0,
                    "start_time": time.time()
                }
            
            stream_stats = self.active_streams[stream_id]
            stream_stats["messages_processed"] += 1
            stream_stats["entities_detected"] += len(result.get("entities_detected", []))
            
            return {
                "success": result["success"],
                "original_message": message,
                "masked_message": result["masked_data"],
                "entities_detected": result.get("entities_detected", []),
                "stream_id": stream_id,
                "processing_time_ms": result.get("processing_time_ms", 0)
            }
            
        except Exception as e:
            logger.error(f"Stream message processing failed for stream {stream_id}: {e}")
            return {
                "success": False,
                "original_message": message,
                "masked_message": message,
                "entities_detected": [],
                "stream_id": stream_id,
                "error": str(e)
            }
    
    def get_stream_statistics(self, stream_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for streams."""
        if stream_id:
            return self.active_streams.get(stream_id, {})
        
        return {
            "active_streams": len(self.active_streams),
            "total_messages": sum(s["messages_processed"] for s in self.active_streams.values()),
            "total_entities": sum(s["entities_detected"] for s in self.active_streams.values()),
            "streams": self.active_streams
        }
    
    def close_stream(self, stream_id: str) -> None:
        """Close and cleanup stream."""
        if stream_id in self.active_streams:
            del self.active_streams[stream_id]