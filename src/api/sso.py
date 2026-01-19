"""
SSO API Router for SuperInsight Platform.

Provides REST API endpoints for Single Sign-On management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.sso.provider import SSOProvider
from src.security.sso.base import (
    SSOConfigurationError, SSOAuthenticationError, ProviderNotFoundError
)
from src.models.security import SSOProtocol


router = APIRouter(prefix="/api/v1/sso", tags=["SSO"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class SSOProviderConfig(BaseModel):
    """SSO provider configuration."""
    # Common fields
    entity_id: Optional[str] = Field(None, description="Entity ID (SAML)")
    idp_metadata_url: Optional[str] = Field(None, description="IdP metadata URL (SAML)")
    idp_sso_url: Optional[str] = Field(None, description="IdP SSO URL (SAML)")
    idp_certificate: Optional[str] = Field(None, description="IdP certificate (SAML)")
    
    # OAuth2/OIDC fields
    client_id: Optional[str] = Field(None, description="OAuth2/OIDC client ID")
    client_secret: Optional[str] = Field(None, description="OAuth2/OIDC client secret")
    authorization_url: Optional[str] = Field(None, description="Authorization URL")
    token_url: Optional[str] = Field(None, description="Token URL")
    userinfo_url: Optional[str] = Field(None, description="User info URL")
    scopes: Optional[List[str]] = Field(None, description="OAuth2 scopes")
    
    # LDAP fields
    server_url: Optional[str] = Field(None, description="LDAP server URL")
    bind_dn: Optional[str] = Field(None, description="LDAP bind DN")
    bind_password: Optional[str] = Field(None, description="LDAP bind password")
    base_dn: Optional[str] = Field(None, description="LDAP base DN")
    user_search_filter: Optional[str] = Field(None, description="LDAP user search filter")


class CreateSSOProviderRequest(BaseModel):
    """Create SSO provider request."""
    name: str = Field(..., min_length=1, max_length=100, description="Provider name")
    protocol: str = Field(..., description="Protocol: saml, oauth2, oidc, ldap")
    config: SSOProviderConfig = Field(..., description="Provider configuration")
    enabled: bool = Field(True, description="Whether provider is enabled")


class UpdateSSOProviderRequest(BaseModel):
    """Update SSO provider request."""
    config: Optional[SSOProviderConfig] = Field(None, description="Provider configuration")
    enabled: Optional[bool] = Field(None, description="Whether provider is enabled")


class SSOProviderResponse(BaseModel):
    """SSO provider response."""
    id: str
    name: str
    protocol: str
    enabled: bool
    created_at: datetime
    updated_at: Optional[datetime]


class SSOLoginInitResponse(BaseModel):
    """SSO login initiation response."""
    redirect_url: str
    state: Optional[str]
    provider_name: str


class SSOCallbackRequest(BaseModel):
    """SSO callback request."""
    code: Optional[str] = Field(None, description="Authorization code (OAuth2/OIDC)")
    state: Optional[str] = Field(None, description="State parameter")
    saml_response: Optional[str] = Field(None, description="SAML response")
    error: Optional[str] = Field(None, description="Error from provider")
    error_description: Optional[str] = Field(None, description="Error description")


class SSOLoginResponse(BaseModel):
    """SSO login response."""
    success: bool
    session_id: Optional[str]
    user_id: Optional[str]
    email: Optional[str]
    error: Optional[str]


class SSOLogoutRequest(BaseModel):
    """SSO logout request."""
    provider_name: Optional[str] = Field(None, description="SSO provider name")
    session_id: Optional[str] = Field(None, description="Session ID")


class SSOLogoutResponse(BaseModel):
    """SSO logout response."""
    success: bool
    redirect_url: Optional[str]
    error: Optional[str]


class SSOTestResponse(BaseModel):
    """SSO test response."""
    success: bool
    message: Optional[str]
    error: Optional[str]
    details: Optional[Dict[str, Any]]


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_sso_provider(db: Session = Depends(get_db_session)) -> SSOProvider:
    """Get SSO provider instance."""
    provider = SSOProvider(db)
    await provider.load_providers()
    return provider


# ============================================================================
# SSO Provider Management Endpoints
# ============================================================================

@router.post("/providers", response_model=SSOProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_sso_provider(
    request: CreateSSOProviderRequest,
    sso_provider: SSOProvider = Depends(get_sso_provider)
):
    """
    Configure a new SSO provider.
    
    Supports SAML 2.0, OAuth 2.0, OIDC, and LDAP/AD protocols.
    """
    try:
        # Map protocol string to enum
        protocol_map = {
            "saml": SSOProtocol.SAML,
            "oauth2": SSOProtocol.OAUTH2,
            "oidc": SSOProtocol.OIDC,
            "ldap": SSOProtocol.LDAP
        }
        
        protocol = protocol_map.get(request.protocol.lower())
        if not protocol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid protocol: {request.protocol}. Supported: saml, oauth2, oidc, ldap"
            )
        
        # Convert config to dict
        config_dict = request.config.model_dump(exclude_none=True)
        
        provider = await sso_provider.configure_provider(
            name=request.name,
            protocol=protocol,
            config=config_dict,
            enabled=request.enabled
        )
        
        return SSOProviderResponse(
            id=str(provider.id),
            name=provider.name,
            protocol=provider.protocol.value,
            enabled=provider.enabled,
            created_at=provider.created_at,
            updated_at=provider.updated_at
        )
        
    except SSOConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/providers", response_model=List[SSOProviderResponse])
async def list_sso_providers(
    enabled_only: bool = Query(False, description="Only return enabled providers"),
    sso_provider: SSOProvider = Depends(get_sso_provider)
):
    """
    List all SSO providers.
    """
    try:
        providers = await sso_provider.list_providers(enabled_only=enabled_only)
        
        return [
            SSOProviderResponse(
                id=str(p.id),
                name=p.name,
                protocol=p.protocol.value,
                enabled=p.enabled,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in providers
        ]
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/providers/{provider_name}", response_model=SSOProviderResponse)
async def get_sso_provider_details(
    provider_name: str,
    sso_provider: SSOProvider = Depends(get_sso_provider)
):
    """
    Get SSO provider details.
    """
    try:
        provider = await sso_provider.get_provider(provider_name)
        
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        
        return SSOProviderResponse(
            id=str(provider.id),
            name=provider.name,
            protocol=provider.protocol.value,
            enabled=provider.enabled,
            created_at=provider.created_at,
            updated_at=provider.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/providers/{provider_name}", response_model=SSOProviderResponse)
async def update_sso_provider(
    provider_name: str,
    request: UpdateSSOProviderRequest,
    sso_provider: SSOProvider = Depends(get_sso_provider)
):
    """
    Update SSO provider configuration.
    """
    try:
        provider = await sso_provider.get_provider(provider_name)
        
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        
        # Update configuration
        config_dict = provider.config
        if request.config:
            config_dict.update(request.config.model_dump(exclude_none=True))
        
        enabled = request.enabled if request.enabled is not None else provider.enabled
        
        updated_provider = await sso_provider.configure_provider(
            name=provider_name,
            protocol=provider.protocol,
            config=config_dict,
            enabled=enabled
        )
        
        return SSOProviderResponse(
            id=str(updated_provider.id),
            name=updated_provider.name,
            protocol=updated_provider.protocol.value,
            enabled=updated_provider.enabled,
            created_at=updated_provider.created_at,
            updated_at=updated_provider.updated_at
        )
        
    except HTTPException:
        raise
    except SSOConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/providers/{provider_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sso_provider(
    provider_name: str,
    sso_provider: SSOProvider = Depends(get_sso_provider)
):
    """
    Delete/disable SSO provider.
    """
    try:
        success = await sso_provider.disable_provider(provider_name)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# SSO Login/Logout Endpoints
# ============================================================================

@router.get("/login/{provider_name}", response_model=SSOLoginInitResponse)
async def initiate_sso_login(
    provider_name: str,
    redirect_uri: str = Query(..., description="URI to redirect after authentication"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    sso_provider: SSOProvider = Depends(get_sso_provider)
):
    """
    Initiate SSO login flow.
    
    Returns a redirect URL to the identity provider.
    """
    try:
        result = await sso_provider.initiate_login(
            provider_name=provider_name,
            redirect_uri=redirect_uri,
            state=state
        )
        
        return SSOLoginInitResponse(
            redirect_url=result.redirect_url,
            state=result.state,
            provider_name=provider_name
        )
        
    except ProviderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    except SSOAuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/callback/{provider_name}", response_model=SSOLoginResponse)
async def handle_sso_callback(
    provider_name: str,
    request: Request,
    callback_data: Optional[SSOCallbackRequest] = None,
    sso_provider: SSOProvider = Depends(get_sso_provider)
):
    """
    Handle SSO callback from identity provider.
    
    Processes the authentication response and creates a local session.
    """
    try:
        # Build callback data from request
        if callback_data:
            data = callback_data.model_dump(exclude_none=True)
        else:
            # Try to get from query params or form data
            data = dict(request.query_params)
            if not data:
                form = await request.form()
                data = dict(form)
        
        # Check for errors from provider
        if data.get("error"):
            return SSOLoginResponse(
                success=False,
                error=data.get("error"),
            )
        
        result = await sso_provider.handle_callback(
            provider_name=provider_name,
            callback_data=data
        )
        
        if result.success:
            return SSOLoginResponse(
                success=True,
                session_id=result.session_id,
                user_id=str(result.user_info.sso_id) if result.user_info else None,
                email=result.user_info.email if result.user_info else None
            )
        else:
            return SSOLoginResponse(
                success=False,
                error=result.error
            )
        
    except ProviderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    except SSOAuthenticationError as e:
        return SSOLoginResponse(success=False, error=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/logout", response_model=SSOLogoutResponse)
async def sso_logout(
    request: SSOLogoutRequest,
    current_user_id: str = Query(..., description="Current user ID"),
    sso_provider: SSOProvider = Depends(get_sso_provider)
):
    """
    Initiate SSO logout (Single Logout).
    """
    try:
        if request.provider_name:
            result = await sso_provider.initiate_logout(
                provider_name=request.provider_name,
                user_id=current_user_id,
                session_id=request.session_id
            )
            
            return SSOLogoutResponse(
                success=result.success,
                redirect_url=result.redirect_url,
                error=result.error
            )
        else:
            # Local logout only
            return SSOLogoutResponse(success=True)
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# SSO Testing Endpoints
# ============================================================================

@router.post("/providers/{provider_name}/test", response_model=SSOTestResponse)
async def test_sso_provider(
    provider_name: str,
    sso_provider: SSOProvider = Depends(get_sso_provider)
):
    """
    Test SSO provider configuration.
    """
    try:
        result = await sso_provider.test_provider(provider_name)
        
        return SSOTestResponse(
            success=result.get("success", False),
            message=result.get("message"),
            error=result.get("error"),
            details=result.get("details")
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/providers/{provider_name}/enable", response_model=SSOProviderResponse)
async def enable_sso_provider(
    provider_name: str,
    sso_provider: SSOProvider = Depends(get_sso_provider)
):
    """
    Enable SSO provider.
    """
    try:
        success = await sso_provider.enable_provider(provider_name)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        
        provider = await sso_provider.get_provider(provider_name)
        
        return SSOProviderResponse(
            id=str(provider.id),
            name=provider.name,
            protocol=provider.protocol.value,
            enabled=provider.enabled,
            created_at=provider.created_at,
            updated_at=provider.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/providers/{provider_name}/disable", response_model=SSOProviderResponse)
async def disable_sso_provider(
    provider_name: str,
    sso_provider: SSOProvider = Depends(get_sso_provider)
):
    """
    Disable SSO provider.
    """
    try:
        success = await sso_provider.disable_provider(provider_name)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        
        provider = await sso_provider.get_provider(provider_name)
        
        return SSOProviderResponse(
            id=str(provider.id),
            name=provider.name,
            protocol=provider.protocol.value,
            enabled=provider.enabled,
            created_at=provider.created_at,
            updated_at=provider.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
