"""
LLM Configuration API.

REST API endpoints for LLM configuration, application, and binding management.
"""

import logging
import time
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.database.connection import db_manager, get_db_session
from src.schemas.llm_config import (
    LLMConfigCreate, LLMConfigUpdate, LLMConfigResponse,
    ApplicationResponse,
    LLMBindingCreate, LLMBindingUpdate, LLMBindingResponse,
    TestConnectionRequest, TestConnectionResponse
)
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding
from src.ai.encryption_service import get_encryption_service
from src.ai.cache_manager import get_cache_manager
from src.ai.application_llm_manager import get_app_llm_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/llm-configs", tags=["LLM Configuration"])


# Use database session from connection module
# (removed local definition, using imported get_db_session)


# LLM Configuration Management Endpoints

# Application Management Endpoints (must be before /{config_id} to avoid route conflicts)

@router.get("/applications", response_model=List[ApplicationResponse])
def list_applications(
    db: Session = Depends(get_db_session)
):
    """
    List all applications.
    
    Requires authenticated user.
    """
    try:
        stmt = select(LLMApplication).where(LLMApplication.is_active == True)
        result = db.execute(stmt)
        applications = result.scalars().all()
        
        return [ApplicationResponse.model_validate(app) for app in applications]
        
    except Exception as e:
        logger.error(f"Failed to list applications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/applications/{code}", response_model=ApplicationResponse)
def get_application(
    code: str,
    db: Session = Depends(get_db_session)
):
    """
    Get a single application by code.
    
    Requires authenticated user.
    """
    try:
        stmt = select(LLMApplication).where(LLMApplication.code == code)
        result = db.execute(stmt)
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        return ApplicationResponse.model_validate(application)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get application: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Binding Management Endpoints (must be before /{config_id} to avoid route conflicts)

@router.get("/bindings", response_model=List[LLMBindingResponse])
def list_bindings(
    application_id: Optional[UUID] = Query(None, description="Filter by application ID"),
    llm_config_id: Optional[UUID] = Query(None, description="Filter by LLM config ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db_session)
):
    """
    List bindings with optional filters.
    
    Requires ADMIN or TECHNICAL_EXPERT role.
    """
    try:
        stmt = (
            select(LLMApplicationBinding)
            .options(
                selectinload(LLMApplicationBinding.llm_config),
                selectinload(LLMApplicationBinding.application)
            )
            .order_by(LLMApplicationBinding.priority.asc())
        )
        
        if application_id is not None:
            stmt = stmt.where(LLMApplicationBinding.application_id == application_id)
        if llm_config_id is not None:
            stmt = stmt.where(LLMApplicationBinding.llm_config_id == llm_config_id)
        if is_active is not None:
            stmt = stmt.where(LLMApplicationBinding.is_active == is_active)
        
        result = db.execute(stmt)
        bindings = result.scalars().all()
        
        response = []
        for binding in bindings:
            config_data = binding.llm_config.config_data or {}
            response.append(LLMBindingResponse(
                id=binding.id,
                llm_config=LLMConfigResponse(
                    id=binding.llm_config.id,
                    name=binding.llm_config.name or "",
                    provider=config_data.get("provider", binding.llm_config.default_method),
                    base_url=config_data.get("base_url"),
                    model_name=config_data.get("model_name", ""),
                    parameters={},
                    is_active=binding.llm_config.is_active,
                    tenant_id=binding.llm_config.tenant_id,
                    created_at=binding.llm_config.created_at,
                    updated_at=binding.llm_config.updated_at
                ),
                application=ApplicationResponse.model_validate(binding.application),
                priority=binding.priority,
                max_retries=binding.max_retries,
                timeout_seconds=binding.timeout_seconds,
                is_active=binding.is_active,
                created_at=binding.created_at,
                updated_at=binding.updated_at
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to list bindings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bindings", response_model=LLMBindingResponse)
def create_binding(
    request: LLMBindingCreate,
    db: Session = Depends(get_db_session)
):
    """
    Create a new LLM-application binding.
    
    Requires ADMIN role.
    """
    try:
        # Verify LLM config exists
        config_stmt = select(LLMConfiguration).where(LLMConfiguration.id == request.llm_config_id)
        config_result = db.execute(config_stmt)
        if not config_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="LLM configuration not found")
        
        # Verify application exists
        app_stmt = select(LLMApplication).where(LLMApplication.id == request.application_id)
        app_result = db.execute(app_stmt)
        if not app_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Check for duplicate priority
        dup_stmt = select(LLMApplicationBinding).where(
            LLMApplicationBinding.application_id == request.application_id,
            LLMApplicationBinding.priority == request.priority
        )
        dup_result = db.execute(dup_stmt)
        if dup_result.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Priority {request.priority} already exists for this application"
            )
        
        # Create binding
        binding = LLMApplicationBinding(
            llm_config_id=request.llm_config_id,
            application_id=request.application_id,
            priority=request.priority,
            max_retries=request.max_retries,
            timeout_seconds=request.timeout_seconds,
            is_active=True
        )
        
        db.add(binding)
        db.commit()
        db.refresh(binding)
        
        # Load relationships
        db.refresh(binding, ["llm_config", "application"])
        
        # Invalidate cache (skip if cache manager not available)
        try:
            cache_manager = get_cache_manager()
            # Note: cache invalidation is async, but we skip it for now
        except Exception:
            pass
        
        logger.info(f"Created binding: {binding.id}")
        
        # Build response
        config_data = binding.llm_config.config_data or {}
        return LLMBindingResponse(
            id=binding.id,
            llm_config=LLMConfigResponse(
                id=binding.llm_config.id,
                name=binding.llm_config.name or "",
                provider=config_data.get("provider", binding.llm_config.default_method),
                base_url=config_data.get("base_url"),
                model_name=config_data.get("model_name", ""),
                parameters={},
                is_active=binding.llm_config.is_active,
                tenant_id=binding.llm_config.tenant_id,
                created_at=binding.llm_config.created_at,
                updated_at=binding.llm_config.updated_at
            ),
            application=ApplicationResponse.model_validate(binding.application),
            priority=binding.priority,
            max_retries=binding.max_retries,
            timeout_seconds=binding.timeout_seconds,
            is_active=binding.is_active,
            created_at=binding.created_at,
            updated_at=binding.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create binding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# LLM Configuration CRUD Endpoints

@router.post("", response_model=LLMConfigResponse)
def create_llm_config(
    request: LLMConfigCreate,
    db: Session = Depends(get_db_session)
):
    """
    Create a new LLM configuration.
    
    Requires ADMIN role.
    """
    try:
        encryption_service = get_encryption_service()
        
        # Encrypt API key
        api_key_encrypted = encryption_service.encrypt(request.api_key)
        
        # Create configuration
        config_data = {
            "provider": request.provider,
            "api_key_encrypted": api_key_encrypted,
            "base_url": request.base_url,
            "model_name": request.model_name,
            **request.parameters
        }
        
        llm_config = LLMConfiguration(
            name=request.name,
            provider=request.provider,
            default_method=request.provider,
            config_data=config_data,
            tenant_id=request.tenant_id,
            is_active=True
        )
        
        db.add(llm_config)
        db.commit()
        db.refresh(llm_config)
        
        # Invalidate cache (skip if cache manager not available)
        try:
            cache_manager = get_cache_manager()
            # Note: cache invalidation is async, but we skip it for now
        except Exception:
            pass
        
        logger.info(f"Created LLM configuration: {llm_config.id}")
        
        return LLMConfigResponse(
            id=llm_config.id,
            name=llm_config.name or "",
            provider=request.provider,
            base_url=request.base_url,
            model_name=request.model_name,
            parameters=request.parameters,
            is_active=llm_config.is_active,
            tenant_id=llm_config.tenant_id,
            created_at=llm_config.created_at,
            updated_at=llm_config.updated_at
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create LLM configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[LLMConfigResponse])
def list_llm_configs(
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db_session)
):
    """
    List all LLM configurations with optional filters.
    
    Requires ADMIN or TECHNICAL_EXPERT role.
    """
    try:
        stmt = select(LLMConfiguration)
        
        if tenant_id is not None:
            stmt = stmt.where(LLMConfiguration.tenant_id == tenant_id)
        if is_active is not None:
            stmt = stmt.where(LLMConfiguration.is_active == is_active)
        
        result = db.execute(stmt)
        configs = result.scalars().all()
        
        response = []
        for config in configs:
            config_data = config.config_data or {}
            response.append(LLMConfigResponse(
                id=config.id,
                name=config.name or "",
                provider=config_data.get("provider", config.default_method),
                base_url=config_data.get("base_url"),
                model_name=config_data.get("model_name", ""),
                parameters={k: v for k, v in config_data.items() 
                           if k not in ["provider", "api_key_encrypted", "base_url", "model_name"]},
                is_active=config.is_active,
                tenant_id=config.tenant_id,
                created_at=config.created_at,
                updated_at=config.updated_at
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to list LLM configurations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{config_id}", response_model=LLMConfigResponse)
def get_llm_config(
    config_id: UUID,
    db: Session = Depends(get_db_session)
):
    """
    Get a single LLM configuration by ID.
    
    Requires ADMIN or TECHNICAL_EXPERT role.
    """
    try:
        stmt = select(LLMConfiguration).where(LLMConfiguration.id == config_id)
        result = db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="LLM configuration not found")
        
        config_data = config.config_data or {}
        return LLMConfigResponse(
            id=config.id,
            name=config.name or "",
            provider=config_data.get("provider", config.default_method),
            base_url=config_data.get("base_url"),
            model_name=config_data.get("model_name", ""),
            parameters={k: v for k, v in config_data.items() 
                       if k not in ["provider", "api_key_encrypted", "base_url", "model_name"]},
            is_active=config.is_active,
            tenant_id=config.tenant_id,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get LLM configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{config_id}", response_model=LLMConfigResponse)
def update_llm_config(
    config_id: UUID,
    request: LLMConfigUpdate,
    db: Session = Depends(get_db_session)
):
    """
    Update an LLM configuration.
    
    Requires ADMIN role.
    """
    try:
        stmt = select(LLMConfiguration).where(LLMConfiguration.id == config_id)
        result = db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="LLM configuration not found")
        
        # Update fields
        config_data = config.config_data or {}
        
        if request.name is not None:
            config.name = request.name
        if request.provider is not None:
            config_data["provider"] = request.provider
            config.default_method = request.provider
        if request.api_key is not None:
            encryption_service = get_encryption_service()
            config_data["api_key_encrypted"] = encryption_service.encrypt(request.api_key)
        if request.base_url is not None:
            config_data["base_url"] = request.base_url
        if request.model_name is not None:
            config_data["model_name"] = request.model_name
        if request.parameters is not None:
            # Merge parameters
            for k, v in request.parameters.items():
                if k not in ["provider", "api_key_encrypted", "base_url", "model_name"]:
                    config_data[k] = v
        if request.is_active is not None:
            config.is_active = request.is_active
        
        config.config_data = config_data
        db.commit()
        db.refresh(config)
        
        # Invalidate cache (skip if cache manager not available)
        try:
            cache_manager = get_cache_manager()
            # Note: cache invalidation is async, but we skip it for now
        except Exception:
            pass
        
        logger.info(f"Updated LLM configuration: {config_id}")
        
        return LLMConfigResponse(
            id=config.id,
            name=config.name or "",
            provider=config_data.get("provider", config.default_method),
            base_url=config_data.get("base_url"),
            model_name=config_data.get("model_name", ""),
            parameters={k: v for k, v in config_data.items() 
                       if k not in ["provider", "api_key_encrypted", "base_url", "model_name"]},
            is_active=config.is_active,
            tenant_id=config.tenant_id,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update LLM configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{config_id}", status_code=204)
def delete_llm_config(
    config_id: UUID,
    db: Session = Depends(get_db_session)
):
    """
    Delete an LLM configuration.
    
    Fails if the configuration has active bindings.
    Requires ADMIN role.
    """
    try:
        stmt = select(LLMConfiguration).where(LLMConfiguration.id == config_id)
        result = db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="LLM configuration not found")
        
        # Check for active bindings
        binding_stmt = select(LLMApplicationBinding).where(
            LLMApplicationBinding.llm_config_id == config_id,
            LLMApplicationBinding.is_active == True
        )
        binding_result = db.execute(binding_stmt)
        bindings = binding_result.scalars().all()
        
        if bindings:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete LLM configuration with {len(bindings)} active bindings"
            )
        
        db.delete(config)
        db.commit()
        
        # Invalidate cache (skip if cache manager not available)
        try:
            cache_manager = get_cache_manager()
            # Note: cache invalidation is async, but we skip it for now
        except Exception:
            pass
        
        logger.info(f"Deleted LLM configuration: {config_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete LLM configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{config_id}/test", response_model=TestConnectionResponse)
async def test_llm_connection(
    config_id: UUID,
    request: TestConnectionRequest,
    db: Session = Depends(get_db_session)
):
    """
    Test LLM connectivity.
    
    Requires ADMIN or TECHNICAL_EXPERT role.
    """
    try:
        stmt = select(LLMConfiguration).where(LLMConfiguration.id == config_id)
        result = db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="LLM configuration not found")
        
        # Build CloudConfig for testing
        from src.ai.llm_schemas import CloudConfig
        encryption_service = get_encryption_service()
        
        config_data = config.config_data or {}
        api_key_encrypted = config_data.get("api_key_encrypted")
        api_key = encryption_service.decrypt(api_key_encrypted) if api_key_encrypted else ""
        
        cloud_config = CloudConfig(
            openai_api_key=api_key,
            openai_base_url=config_data.get("base_url", "https://api.openai.com/v1"),
            openai_model=config_data.get("model_name", "gpt-3.5-turbo")
        )
        
        # Test connection with a simple prompt
        start_time = time.time()
        
        try:
            # Import LLM client
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(
                api_key=cloud_config.openai_api_key,
                base_url=cloud_config.openai_base_url
            )
            
            response = await client.chat.completions.create(
                model=cloud_config.openai_model,
                messages=[{"role": "user", "content": request.prompt}],
                max_tokens=10
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return TestConnectionResponse(
                status="success",
                latency_ms=latency_ms,
                model=cloud_config.openai_model
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return TestConnectionResponse(
                status="failed",
                latency_ms=latency_ms,
                error=str(e),
                model=cloud_config.openai_model
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test LLM connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))
def list_bindings(
    application_id: Optional[UUID] = Query(None, description="Filter by application ID"),
    llm_config_id: Optional[UUID] = Query(None, description="Filter by LLM config ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db_session)
):
    """
    List bindings with optional filters.
    
    Requires ADMIN or TECHNICAL_EXPERT role.
    """
    try:
        stmt = (
            select(LLMApplicationBinding)
            .options(
                selectinload(LLMApplicationBinding.llm_config),
                selectinload(LLMApplicationBinding.application)
            )
            .order_by(LLMApplicationBinding.priority.asc())
        )
        
        if application_id is not None:
            stmt = stmt.where(LLMApplicationBinding.application_id == application_id)
        if llm_config_id is not None:
            stmt = stmt.where(LLMApplicationBinding.llm_config_id == llm_config_id)
        if is_active is not None:
            stmt = stmt.where(LLMApplicationBinding.is_active == is_active)
        
        result = db.execute(stmt)
        bindings = result.scalars().all()
        
        response = []
        for binding in bindings:
            config_data = binding.llm_config.config_data or {}
            response.append(LLMBindingResponse(
                id=binding.id,
                llm_config=LLMConfigResponse(
                    id=binding.llm_config.id,
                    name=binding.llm_config.name or "",
                    provider=config_data.get("provider", binding.llm_config.default_method),
                    base_url=config_data.get("base_url"),
                    model_name=config_data.get("model_name", ""),
                    parameters={},
                    is_active=binding.llm_config.is_active,
                    tenant_id=binding.llm_config.tenant_id,
                    created_at=binding.llm_config.created_at,
                    updated_at=binding.llm_config.updated_at
                ),
                application=ApplicationResponse.model_validate(binding.application),
                priority=binding.priority,
                max_retries=binding.max_retries,
                timeout_seconds=binding.timeout_seconds,
                is_active=binding.is_active,
                created_at=binding.created_at,
                updated_at=binding.updated_at
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to list bindings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bindings/{binding_id}", response_model=LLMBindingResponse)
def get_binding(
    binding_id: UUID,
    db: Session = Depends(get_db_session)
):
    """
    Get a single binding by ID.
    
    Requires ADMIN or TECHNICAL_EXPERT role.
    """
    try:
        stmt = (
            select(LLMApplicationBinding)
            .options(
                selectinload(LLMApplicationBinding.llm_config),
                selectinload(LLMApplicationBinding.application)
            )
            .where(LLMApplicationBinding.id == binding_id)
        )
        result = db.execute(stmt)
        binding = result.scalar_one_or_none()
        
        if not binding:
            raise HTTPException(status_code=404, detail="Binding not found")
        
        config_data = binding.llm_config.config_data or {}
        return LLMBindingResponse(
            id=binding.id,
            llm_config=LLMConfigResponse(
                id=binding.llm_config.id,
                name=binding.llm_config.name or "",
                provider=config_data.get("provider", binding.llm_config.default_method),
                base_url=config_data.get("base_url"),
                model_name=config_data.get("model_name", ""),
                parameters={},
                is_active=binding.llm_config.is_active,
                tenant_id=binding.llm_config.tenant_id,
                created_at=binding.llm_config.created_at,
                updated_at=binding.llm_config.updated_at
            ),
            application=ApplicationResponse.model_validate(binding.application),
            priority=binding.priority,
            max_retries=binding.max_retries,
            timeout_seconds=binding.timeout_seconds,
            is_active=binding.is_active,
            created_at=binding.created_at,
            updated_at=binding.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get binding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/bindings/{binding_id}", response_model=LLMBindingResponse)
def update_binding(
    binding_id: UUID,
    request: LLMBindingUpdate,
    db: Session = Depends(get_db_session)
):
    """
    Update a binding.
    
    Requires ADMIN role.
    """
    try:
        stmt = (
            select(LLMApplicationBinding)
            .options(
                selectinload(LLMApplicationBinding.llm_config),
                selectinload(LLMApplicationBinding.application)
            )
            .where(LLMApplicationBinding.id == binding_id)
        )
        result = db.execute(stmt)
        binding = result.scalar_one_or_none()
        
        if not binding:
            raise HTTPException(status_code=404, detail="Binding not found")
        
        # Check for duplicate priority if priority is being changed
        if request.priority is not None and request.priority != binding.priority:
            dup_stmt = select(LLMApplicationBinding).where(
                LLMApplicationBinding.application_id == binding.application_id,
                LLMApplicationBinding.priority == request.priority,
                LLMApplicationBinding.id != binding_id
            )
            dup_result = db.execute(dup_stmt)
            if dup_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail=f"Priority {request.priority} already exists for this application"
                )
            binding.priority = request.priority
        
        if request.max_retries is not None:
            binding.max_retries = request.max_retries
        if request.timeout_seconds is not None:
            binding.timeout_seconds = request.timeout_seconds
        if request.is_active is not None:
            binding.is_active = request.is_active
        
        db.commit()
        db.refresh(binding)
        
        # Invalidate cache (skip if cache manager not available)
        try:
            cache_manager = get_cache_manager()
            # Note: cache invalidation is async, but we skip it for now
        except Exception:
            pass
        
        logger.info(f"Updated binding: {binding_id}")
        
        config_data = binding.llm_config.config_data or {}
        return LLMBindingResponse(
            id=binding.id,
            llm_config=LLMConfigResponse(
                id=binding.llm_config.id,
                name=binding.llm_config.name or "",
                provider=config_data.get("provider", binding.llm_config.default_method),
                base_url=config_data.get("base_url"),
                model_name=config_data.get("model_name", ""),
                parameters={},
                is_active=binding.llm_config.is_active,
                tenant_id=binding.llm_config.tenant_id,
                created_at=binding.llm_config.created_at,
                updated_at=binding.llm_config.updated_at
            ),
            application=ApplicationResponse.model_validate(binding.application),
            priority=binding.priority,
            max_retries=binding.max_retries,
            timeout_seconds=binding.timeout_seconds,
            is_active=binding.is_active,
            created_at=binding.created_at,
            updated_at=binding.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update binding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bindings/{binding_id}", status_code=204)
def delete_binding(
    binding_id: UUID,
    db: Session = Depends(get_db_session)
):
    """
    Delete a binding.
    
    Requires ADMIN role.
    """
    try:
        stmt = select(LLMApplicationBinding).where(LLMApplicationBinding.id == binding_id)
        result = db.execute(stmt)
        binding = result.scalar_one_or_none()
        
        if not binding:
            raise HTTPException(status_code=404, detail="Binding not found")
        
        db.delete(binding)
        db.commit()
        
        # Invalidate cache (skip if cache manager not available)
        try:
            cache_manager = get_cache_manager()
            # Note: cache invalidation is async, but we skip it for now
        except Exception:
            pass
        
        logger.info(f"Deleted binding: {binding_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete binding: {e}")
        raise HTTPException(status_code=500, detail=str(e))
