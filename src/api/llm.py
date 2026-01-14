"""
LLM API Routes for SuperInsight platform.

Provides REST API endpoints for LLM operations including generation, embedding,
configuration management, and health checks.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

try:
    from src.ai.llm_schemas import (
        LLMConfig, LLMMethod, GenerateOptions, LLMResponse, EmbeddingResponse,
        LLMError, LLMErrorCode, HealthStatus, MethodInfo, ValidationResult,
        GenerateRequest, EmbedRequest, mask_api_key
    )
    from src.ai.llm_switcher import get_initialized_switcher, LLMSwitcher
    from src.ai.llm_config_manager import get_config_manager, LLMConfigManager
    from src.security.auth import get_current_user, get_current_admin_user
    from src.models.user import User
except ImportError:
    from ai.llm_schemas import (
        LLMConfig, LLMMethod, GenerateOptions, LLMResponse, EmbeddingResponse,
        LLMError, LLMErrorCode, HealthStatus, MethodInfo, ValidationResult,
        GenerateRequest, EmbedRequest, mask_api_key
    )
    from ai.llm_switcher import get_initialized_switcher, LLMSwitcher
    from ai.llm_config_manager import get_config_manager, LLMConfigManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/llm", tags=["LLM"])


# ==================== Response Models ====================

class GenerateResponse(BaseModel):
    """Response model for text generation."""
    success: bool = True
    data: LLMResponse


class EmbedResponse(BaseModel):
    """Response model for embedding."""
    success: bool = True
    data: EmbeddingResponse


class ConfigResponse(BaseModel):
    """Response model for configuration."""
    success: bool = True
    data: LLMConfig


class HealthResponse(BaseModel):
    """Response model for health check."""
    success: bool = True
    data: Dict[str, HealthStatus]


class MethodsResponse(BaseModel):
    """Response model for methods list."""
    success: bool = True
    data: List[MethodInfo]


class TestConnectionResponse(BaseModel):
    """Response model for connection test."""
    success: bool = True
    data: HealthStatus


class ErrorResponse(BaseModel):
    """Response model for errors."""
    success: bool = False
    error: Dict[str, Any]


# ==================== Dependencies ====================

async def get_switcher(tenant_id: Optional[str] = None) -> LLMSwitcher:
    """Get initialized LLM switcher."""
    return await get_initialized_switcher(tenant_id)


def get_manager() -> LLMConfigManager:
    """Get config manager."""
    return get_config_manager()


# ==================== Generation Endpoints ====================

@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Generate text using LLM",
    description="Generate text response using the configured LLM provider."
)
async def generate(
    request: GenerateRequest,
    switcher: LLMSwitcher = Depends(get_switcher),
):
    """
    Generate text using the specified or default LLM method.
    
    - **prompt**: Input text prompt
    - **options**: Generation options (max_tokens, temperature, etc.)
    - **method**: Override default method (optional)
    - **model**: Override default model (optional)
    - **system_prompt**: System prompt for chat models (optional)
    """
    try:
        response = await switcher.generate(
            prompt=request.prompt,
            options=request.options,
            method=request.method,
            model=request.model,
            system_prompt=request.system_prompt,
        )
        return GenerateResponse(data=response)
        
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code.value,
                "message": e.message,
                "provider": e.provider,
                "suggestions": e.suggestions,
                "retry_after": e.retry_after,
            }
        )
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": str(e)}
        )


@router.post(
    "/stream",
    summary="Stream text generation",
    description="Stream text generation response using Server-Sent Events."
)
async def stream_generate(
    request: GenerateRequest,
    switcher: LLMSwitcher = Depends(get_switcher),
):
    """
    Stream text generation using Server-Sent Events.
    
    Returns a stream of text chunks as they are generated.
    """
    async def generate_stream():
        try:
            async for chunk in switcher.stream_generate(
                prompt=request.prompt,
                options=request.options,
                method=request.method,
                model=request.model,
                system_prompt=request.system_prompt,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post(
    "/embed",
    response_model=EmbedResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Generate text embedding",
    description="Generate embedding vector for the input text."
)
async def embed(
    request: EmbedRequest,
    switcher: LLMSwitcher = Depends(get_switcher),
):
    """
    Generate text embedding using the specified or default method.
    
    - **text**: Input text to embed
    - **method**: Override default method (optional)
    - **model**: Override default model (optional)
    """
    try:
        response = await switcher.embed(
            text=request.text,
            method=request.method,
            model=request.model,
        )
        return EmbedResponse(data=response)
        
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code.value,
                "message": e.message,
                "provider": e.provider,
            }
        )
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": str(e)}
        )


# ==================== Configuration Endpoints ====================

@router.get(
    "/config",
    response_model=ConfigResponse,
    summary="Get LLM configuration",
    description="Get current LLM configuration with masked API keys."
)
async def get_config(
    tenant_id: Optional[str] = Query(None, description="Tenant ID"),
    manager: LLMConfigManager = Depends(get_manager),
):
    """
    Get current LLM configuration.
    
    API keys are masked for security.
    """
    try:
        config = await manager.get_config(tenant_id, mask_keys=True)
        return ConfigResponse(data=config)
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "CONFIG_ERROR", "message": str(e)}
        )


@router.put(
    "/config",
    response_model=ConfigResponse,
    summary="Update LLM configuration",
    description="Update LLM configuration (admin only)."
)
async def update_config(
    config: LLMConfig,
    tenant_id: Optional[str] = Query(None, description="Tenant ID"),
    manager: LLMConfigManager = Depends(get_manager),
):
    """
    Update LLM configuration.
    
    Requires admin privileges.
    """
    try:
        # Validate configuration
        validation = await manager.validate_config(config)
        if not validation.valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_CONFIG",
                    "message": "Configuration validation failed",
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                }
            )
        
        # Save configuration
        saved_config = await manager.save_config(config, tenant_id)
        
        # Return masked config
        masked_config = await manager.get_config(tenant_id, mask_keys=True)
        return ConfigResponse(data=masked_config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "CONFIG_ERROR", "message": str(e)}
        )


@router.post(
    "/config/validate",
    response_model=ValidationResult,
    summary="Validate LLM configuration",
    description="Validate LLM configuration without saving."
)
async def validate_config(
    config: LLMConfig,
    manager: LLMConfigManager = Depends(get_manager),
):
    """
    Validate LLM configuration.
    
    Returns validation result with errors and warnings.
    """
    try:
        return await manager.validate_config(config)
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "VALIDATION_ERROR", "message": str(e)}
        )


@router.post(
    "/config/test",
    response_model=TestConnectionResponse,
    summary="Test LLM connection",
    description="Test connection to a specific LLM provider."
)
async def test_connection(
    method: LLMMethod = Body(..., embed=True, description="LLM method to test"),
    switcher: LLMSwitcher = Depends(get_switcher),
):
    """
    Test connection to a specific LLM provider.
    
    Returns health status with latency information.
    """
    try:
        status_result = await switcher.test_connection(method)
        return TestConnectionResponse(data=status_result)
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return TestConnectionResponse(
            success=False,
            data=HealthStatus(
                method=method,
                available=False,
                error=str(e)
            )
        )


# ==================== Health & Status Endpoints ====================

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check LLM health",
    description="Check health status of all configured LLM providers."
)
async def health_check(
    method: Optional[LLMMethod] = Query(None, description="Specific method to check"),
    switcher: LLMSwitcher = Depends(get_switcher),
):
    """
    Check health of LLM providers.
    
    Returns health status for all or specific providers.
    """
    try:
        results = await switcher.health_check(method)
        # Convert dict keys to strings for JSON serialization
        data = {m.value: s for m, s in results.items()}
        return HealthResponse(data=data)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "HEALTH_CHECK_ERROR", "message": str(e)}
        )


@router.get(
    "/methods",
    response_model=MethodsResponse,
    summary="List available methods",
    description="List all available LLM methods with their status."
)
async def list_methods(
    switcher: LLMSwitcher = Depends(get_switcher),
):
    """
    List all available LLM methods.
    
    Returns method information including enabled status and available models.
    """
    try:
        methods = switcher.list_available_methods()
        return MethodsResponse(data=methods)
    except Exception as e:
        logger.error(f"Failed to list methods: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "LIST_ERROR", "message": str(e)}
        )


@router.get(
    "/current-method",
    summary="Get current method",
    description="Get the current default LLM method."
)
async def get_current_method(
    switcher: LLMSwitcher = Depends(get_switcher),
):
    """Get the current default LLM method."""
    return {
        "success": True,
        "data": {
            "method": switcher.get_current_method().value
        }
    }


@router.post(
    "/switch-method",
    summary="Switch default method",
    description="Switch the default LLM method."
)
async def switch_method(
    method: LLMMethod = Body(..., embed=True, description="New default method"),
    switcher: LLMSwitcher = Depends(get_switcher),
):
    """
    Switch the default LLM method.
    
    The method must be enabled in the configuration.
    """
    try:
        switcher.switch_method(method)
        return {
            "success": True,
            "data": {
                "method": method.value,
                "message": f"Switched to {method.value}"
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_METHOD", "message": str(e)}
        )


# ==================== Model Management Endpoints ====================

@router.get(
    "/models",
    summary="List available models",
    description="List available models for a specific method."
)
async def list_models(
    method: Optional[LLMMethod] = Query(None, description="LLM method"),
    switcher: LLMSwitcher = Depends(get_switcher),
):
    """
    List available models for a method.
    
    If no method specified, returns models for the current method.
    """
    try:
        methods_info = switcher.list_available_methods()
        
        if method:
            for info in methods_info:
                if info.method == method:
                    return {
                        "success": True,
                        "data": {
                            "method": method.value,
                            "models": info.models
                        }
                    }
            return {
                "success": True,
                "data": {
                    "method": method.value,
                    "models": []
                }
            }
        
        # Return all models grouped by method
        all_models = {}
        for info in methods_info:
            if info.models:
                all_models[info.method.value] = info.models
        
        return {
            "success": True,
            "data": all_models
        }
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "LIST_ERROR", "message": str(e)}
        )


# ==================== Hot Reload Endpoint ====================

@router.post(
    "/reload",
    summary="Hot reload configuration",
    description="Force reload LLM configuration from database."
)
async def hot_reload(
    tenant_id: Optional[str] = Query(None, description="Tenant ID"),
    manager: LLMConfigManager = Depends(get_manager),
):
    """
    Force reload LLM configuration.
    
    Useful after external configuration changes.
    """
    try:
        config = await manager.hot_reload(tenant_id)
        masked_config = await manager.get_config(tenant_id, mask_keys=True)
        return {
            "success": True,
            "data": {
                "message": "Configuration reloaded",
                "config": masked_config.model_dump()
            }
        }
    except Exception as e:
        logger.error(f"Hot reload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "RELOAD_ERROR", "message": str(e)}
        )
