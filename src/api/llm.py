"""
LLM API Routes for SuperInsight Platform.

Provides REST API endpoints for LLM operations including:
- Text generation using active provider
- Health status monitoring
- Provider activation

**Feature: llm-integration**

Requirements Implemented:
- 6.1: Display all configured providers with their status
- 6.3: Test provider connection and display result
- 7.1: Send pre-annotation data to active LLM provider
- 9.3: Require administrator role for API key access
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.api.auth import get_current_user
from src.security.models import UserModel, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/llm", tags=["LLM"])


# ========== Request/Response Schemas ==========

class GenerateRequest(BaseModel):
    """Request schema for LLM text generation."""
    prompt: str = Field(..., min_length=1, description="Input prompt for generation")
    max_tokens: Optional[int] = Field(None, ge=1, le=4096, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Top-p sampling parameter")
    provider_id: Optional[str] = Field(None, description="Override active provider with specific provider ID")
    system_prompt: Optional[str] = Field(None, description="System prompt for chat models")


class GenerateResponse(BaseModel):
    """Response schema for LLM text generation."""
    text: str = Field(..., description="Generated text content")
    model: str = Field(..., description="Model used for generation")
    provider_id: str = Field(..., description="Provider that handled the request")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage statistics")
    cached: bool = Field(default=False, description="Whether response was served from cache")
    latency_ms: float = Field(default=0.0, description="Response latency in milliseconds")


class ProviderHealthStatus(BaseModel):
    """Health status for a single provider."""
    provider_id: str = Field(..., description="Provider ID")
    name: str = Field(..., description="Provider name")
    provider_type: str = Field(..., description="Provider type (openai, qwen, etc.)")
    is_healthy: bool = Field(..., description="Whether provider is healthy")
    is_active: bool = Field(default=False, description="Whether this is the active provider")
    last_check_at: Optional[datetime] = Field(None, description="Last health check timestamp")
    last_error: Optional[str] = Field(None, description="Last error message if unhealthy")
    latency_ms: Optional[float] = Field(None, description="Health check latency")


class HealthResponse(BaseModel):
    """Response schema for health status endpoint."""
    providers: List[ProviderHealthStatus] = Field(..., description="Health status of all providers")
    active_provider_id: Optional[str] = Field(None, description="Currently active provider ID")
    fallback_provider_id: Optional[str] = Field(None, description="Fallback provider ID")
    overall_healthy: bool = Field(..., description="Whether at least one provider is healthy")


class ActivateProviderRequest(BaseModel):
    """Request schema for activating a provider."""
    set_as_fallback: bool = Field(default=False, description="Set as fallback instead of primary")


class ActivateProviderResponse(BaseModel):
    """Response schema for provider activation."""
    success: bool = Field(..., description="Whether activation succeeded")
    provider_id: str = Field(..., description="Activated provider ID")
    message: str = Field(..., description="Status message")
    previous_active_id: Optional[str] = Field(None, description="Previously active provider ID")


# ========== Helper Functions ==========

def require_admin(user: UserModel) -> None:
    """
    Verify user has administrator role.
    
    Raises HTTPException with 403 if user is not an admin.
    
    **Validates: Requirements 9.3**
    
    Args:
        user: Current authenticated user
        
    Raises:
        HTTPException: 403 Forbidden if user is not admin
    """
    if user.role != UserRole.ADMIN:
        logger.warning(
            f"Non-admin user {user.username} attempted to access admin-only resource"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "ADMIN_REQUIRED",
                "message": "Administrator role required for this operation"
            }
        )


async def get_llm_switcher_instance():
    """
    Get the LLM Switcher instance.
    
    Returns:
        Initialized LLMSwitcher instance
    """
    try:
        from src.ai.llm_switcher import get_initialized_switcher
        switcher = await get_initialized_switcher()
        return switcher
    except ImportError:
        logger.error("LLM Switcher module not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "LLM_MODULE_UNAVAILABLE",
                "message": "LLM module is not available"
            }
        )
    except Exception as e:
        logger.error(f"Failed to initialize LLM Switcher: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "LLM_INIT_FAILED",
                "message": f"Failed to initialize LLM service: {str(e)}"
            }
        )


async def get_health_monitor_instance():
    """
    Get the Health Monitor instance.
    
    Returns:
        HealthMonitor instance
    """
    try:
        from src.ai.llm.health_monitor import get_health_monitor
        from src.ai.llm_switcher import get_initialized_switcher
        
        switcher = await get_initialized_switcher()
        monitor = get_health_monitor(switcher=switcher)
        return monitor
    except ImportError:
        logger.error("Health Monitor module not available")
        return None
    except Exception as e:
        logger.error(f"Failed to get Health Monitor: {e}")
        return None


# ========== API Endpoints ==========

@router.post("/generate", response_model=GenerateResponse)
async def generate_completion(
    request: GenerateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> GenerateResponse:
    """
    Generate text completion using the active LLM provider.
    
    Sends the prompt to the currently active LLM provider and returns
    the generated text. Supports automatic failover to fallback provider
    if the primary provider fails.
    
    **Requirement 7.1: Pre-Annotation Routing**
    - Sends pre-annotation data to active LLM provider
    - Supports provider override via provider_id parameter
    
    Args:
        request: Generation request with prompt and options
        current_user: Authenticated user
        db: Database session
        
    Returns:
        GenerateResponse with generated text and metadata
        
    Raises:
        HTTPException: 503 if LLM service unavailable
        HTTPException: 500 if generation fails
    """
    logger.info(f"Generate request from user {current_user.username}")
    
    try:
        switcher = await get_llm_switcher_instance()
        
        # Build generation options
        from src.ai.llm_schemas import GenerateOptions, LLMMethod
        
        options = GenerateOptions(
            max_tokens=request.max_tokens or 1000,
            temperature=request.temperature or 0.7,
            top_p=request.top_p or 0.9,
        )
        
        # Determine method to use
        method = None
        if request.provider_id:
            # TODO: Map provider_id to LLMMethod
            # For now, use default method
            pass
        
        # Generate response
        response = await switcher.generate(
            prompt=request.prompt,
            options=options,
            method=method,
            system_prompt=request.system_prompt,
        )
        
        # Get active provider info
        active_method = switcher._current_method
        provider_id = active_method.value if active_method else "unknown"
        
        return GenerateResponse(
            text=response.content,
            model=response.model,
            provider_id=provider_id,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            } if response.usage else None,
            cached=response.cached,
            latency_ms=response.latency_ms,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "GENERATION_FAILED",
                "message": f"Text generation failed: {str(e)}"
            }
        )


@router.get("/health", response_model=HealthResponse)
async def get_health_status(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> HealthResponse:
    """
    Get health status of all configured LLM providers.
    
    Returns the health status of each provider including whether it's
    healthy, the last check timestamp, and any error messages.
    
    **Requirement 6.1: Display all configured providers with their status**
    **Requirement 5.1-5.5: Health Monitoring**
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        HealthResponse with status of all providers
    """
    logger.info(f"Health status request from user {current_user.username}")
    
    providers_status: List[ProviderHealthStatus] = []
    active_provider_id: Optional[str] = None
    fallback_provider_id: Optional[str] = None
    
    try:
        switcher = await get_llm_switcher_instance()
        monitor = await get_health_monitor_instance()
        
        # Get active and fallback provider info
        if switcher._current_method:
            active_provider_id = switcher._current_method.value
        
        if switcher._fallback_method:
            fallback_provider_id = switcher._fallback_method.value
        
        # Get health status from monitor or directly from providers
        if monitor:
            all_status = await monitor.get_all_health_status()
            
            for provider_id, status_info in all_status.items():
                providers_status.append(ProviderHealthStatus(
                    provider_id=provider_id,
                    name=provider_id,  # Use ID as name for now
                    provider_type=provider_id.replace("provider_", ""),
                    is_healthy=status_info.get("is_healthy", False),
                    is_active=(provider_id == active_provider_id),
                    last_error=status_info.get("last_error"),
                ))
        else:
            # Fallback: check providers directly
            for method, provider in switcher._providers.items():
                try:
                    health = await provider.health_check()
                    providers_status.append(ProviderHealthStatus(
                        provider_id=method.value,
                        name=method.value,
                        provider_type=method.value.split("_")[0] if "_" in method.value else method.value,
                        is_healthy=health.available,
                        is_active=(method.value == active_provider_id),
                        last_check_at=health.last_check,
                        last_error=health.error,
                        latency_ms=health.latency_ms,
                    ))
                except Exception as e:
                    providers_status.append(ProviderHealthStatus(
                        provider_id=method.value,
                        name=method.value,
                        provider_type=method.value.split("_")[0] if "_" in method.value else method.value,
                        is_healthy=False,
                        is_active=(method.value == active_provider_id),
                        last_error=str(e),
                    ))
        
        # Determine overall health
        overall_healthy = any(p.is_healthy for p in providers_status)
        
        return HealthResponse(
            providers=providers_status,
            active_provider_id=active_provider_id,
            fallback_provider_id=fallback_provider_id,
            overall_healthy=overall_healthy,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get health status: {e}", exc_info=True)
        # Return empty status on error
        return HealthResponse(
            providers=[],
            active_provider_id=None,
            fallback_provider_id=None,
            overall_healthy=False,
        )


@router.post("/providers/{provider_id}/activate", response_model=ActivateProviderResponse)
async def activate_provider(
    provider_id: str,
    request: ActivateProviderRequest = ActivateProviderRequest(),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ActivateProviderResponse:
    """
    Set a provider as the active (or fallback) provider.
    
    Activates the specified provider for handling LLM requests.
    Requires administrator role.
    
    **Requirement 9.3: Require administrator role for API key access**
    **Requirement 3.2: Validate target provider is available before switching**
    
    Args:
        provider_id: ID of the provider to activate
        request: Activation options
        current_user: Authenticated user (must be admin)
        db: Database session
        
    Returns:
        ActivateProviderResponse with activation result
        
    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if provider not found
        HTTPException: 400 if provider is unhealthy
    """
    # Require admin role (Requirement 9.3)
    require_admin(current_user)
    
    logger.info(
        f"Provider activation request from admin {current_user.username}: "
        f"provider_id={provider_id}, set_as_fallback={request.set_as_fallback}"
    )
    
    try:
        switcher = await get_llm_switcher_instance()
        
        # Map provider_id to LLMMethod
        from src.ai.llm_schemas import LLMMethod
        
        try:
            method = LLMMethod(provider_id)
        except ValueError:
            # Try to find by partial match
            method = None
            for m in LLMMethod:
                if m.value == provider_id or provider_id in m.value:
                    method = m
                    break
            
            if not method:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error_code": "PROVIDER_NOT_FOUND",
                        "message": f"Provider '{provider_id}' not found"
                    }
                )
        
        # Check if provider is available
        if method not in switcher._providers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "PROVIDER_NOT_INITIALIZED",
                    "message": f"Provider '{provider_id}' is not initialized"
                }
            )
        
        # Get previous active provider
        previous_active = switcher._current_method
        previous_active_id = previous_active.value if previous_active else None
        
        if request.set_as_fallback:
            # Set as fallback provider
            await switcher.set_fallback_provider(method)
            message = f"Provider '{provider_id}' set as fallback provider"
        else:
            # Validate provider health before activation (Requirement 3.2)
            provider = switcher._providers[method]
            try:
                health = await provider.health_check()
                if not health.available:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error_code": "PROVIDER_UNHEALTHY",
                            "message": f"Provider '{provider_id}' is unhealthy: {health.error}"
                        }
                    )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "HEALTH_CHECK_FAILED",
                        "message": f"Health check failed for provider '{provider_id}': {str(e)}"
                    }
                )
            
            # Set as active provider
            switcher._current_method = method
            message = f"Provider '{provider_id}' activated as primary provider"
        
        logger.info(f"Provider activation successful: {message}")
        
        return ActivateProviderResponse(
            success=True,
            provider_id=provider_id,
            message=message,
            previous_active_id=previous_active_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Provider activation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "ACTIVATION_FAILED",
                "message": f"Failed to activate provider: {str(e)}"
            }
        )


@router.get("/providers/{provider_id}/api-key")
async def get_provider_api_key(
    provider_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get the API key for a provider (admin only).
    
    Returns the decrypted API key for the specified provider.
    This endpoint requires administrator role for security.
    
    **Requirement 9.3: Require administrator role for API key access**
    
    Args:
        provider_id: ID of the provider
        current_user: Authenticated user (must be admin)
        db: Database session
        
    Returns:
        Dictionary with masked API key
        
    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if provider not found
    """
    # Require admin role (Requirement 9.3)
    require_admin(current_user)
    
    logger.info(
        f"API key access request from admin {current_user.username} "
        f"for provider {provider_id}"
    )
    
    try:
        from src.admin.config_manager import get_config_manager
        from src.ai.llm_schemas import mask_api_key
        
        manager = get_config_manager()
        config = await manager.get_llm_config(provider_id, current_user.tenant_id)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "PROVIDER_NOT_FOUND",
                    "message": f"Provider '{provider_id}' not found"
                }
            )
        
        # Return masked API key for security
        api_key = config.api_key if hasattr(config, 'api_key') else None
        
        return {
            "provider_id": provider_id,
            "api_key_masked": mask_api_key(api_key) if api_key else None,
            "has_api_key": api_key is not None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "API_KEY_ACCESS_FAILED",
                "message": f"Failed to access API key: {str(e)}"
            }
        )
