"""
Session Management API Router for SuperInsight Platform.

Provides REST API endpoints for user session management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

import redis
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from src.database.connection import get_db_session
from src.security.session_manager import SessionManager, Session


router = APIRouter(prefix="/api/v1/sessions", tags=["Session Management"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class SessionResponse(BaseModel):
    """Session response."""
    id: str
    user_id: str
    ip_address: str
    user_agent: Optional[str]
    created_at: datetime
    last_activity: datetime
    expires_at: Optional[datetime]
    metadata: Optional[Dict[str, Any]]


class SessionListResponse(BaseModel):
    """Session list response."""
    sessions: List[SessionResponse]
    total: int


class CreateSessionRequest(BaseModel):
    """Create session request."""
    user_id: str = Field(..., description="User ID")
    ip_address: str = Field(..., description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    timeout: Optional[int] = Field(None, ge=60, le=86400, description="Session timeout in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional session metadata")


class SessionConfigRequest(BaseModel):
    """Session configuration request."""
    default_timeout: Optional[int] = Field(None, ge=60, le=86400, description="Default timeout in seconds")
    max_concurrent_sessions: Optional[int] = Field(None, ge=1, le=100, description="Max concurrent sessions per user")


class SessionConfigResponse(BaseModel):
    """Session configuration response."""
    default_timeout: int
    max_concurrent_sessions: int


class SessionStatisticsResponse(BaseModel):
    """Session statistics response."""
    total_active_sessions: int
    total_users_with_sessions: int
    top_users_by_sessions: Dict[str, int]
    configuration: SessionConfigResponse


class ForceLogoutResponse(BaseModel):
    """Force logout response."""
    success: bool
    sessions_destroyed: int
    user_id: str


class ExtendSessionRequest(BaseModel):
    """Extend session request."""
    additional_seconds: int = Field(..., ge=60, le=86400, description="Additional seconds to add")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    from src.config.settings import settings
    return redis.Redis.from_url(settings.redis.redis_url)


def get_session_manager(
    redis_client: redis.Redis = Depends(get_redis_client),
    db: DBSession = Depends(get_db_session)
) -> SessionManager:
    """Get session manager instance."""
    from src.security.audit_logger import AuditLogger
    
    audit_logger = AuditLogger(db)
    return SessionManager(redis_client, audit_logger)


# ============================================================================
# Session CRUD Endpoints
# ============================================================================

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Create a new user session.
    
    Creates a session with optional custom timeout and metadata.
    Enforces concurrent session limits.
    """
    try:
        session = await session_manager.create_session(
            user_id=request.user_id,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            timeout=request.timeout,
            metadata=request.metadata
        )
        
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            created_at=session.created_at,
            last_activity=session.last_activity,
            expires_at=session.expires_at,
            metadata=session.metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    List active sessions.
    
    If user_id is provided, returns sessions for that user only.
    Otherwise returns all active sessions (admin function).
    """
    try:
        if user_id:
            sessions = await session_manager.get_user_sessions(user_id)
        else:
            sessions = await session_manager.get_active_sessions(limit=limit)
        
        session_responses = [
            SessionResponse(
                id=s.id,
                user_id=s.user_id,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                created_at=s.created_at,
                last_activity=s.last_activity,
                expires_at=s.expires_at,
                metadata=s.metadata
            )
            for s in sessions
        ]
        
        return SessionListResponse(
            sessions=session_responses,
            total=len(session_responses)
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Get a specific session.
    
    Also validates and refreshes the session.
    """
    try:
        session = await session_manager.validate_session(session_id)
        
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or expired")
        
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            created_at=session.created_at,
            last_activity=session.last_activity,
            expires_at=session.expires_at,
            metadata=session.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def destroy_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Destroy a session.
    
    Immediately invalidates the session.
    """
    try:
        success = await session_manager.destroy_session(session_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.post("/force-logout/{user_id}", response_model=ForceLogoutResponse)
async def force_logout_user(
    user_id: str,
    admin_user_id: str = Query(..., description="Admin user ID performing the action"),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Force logout all sessions for a user.
    
    Destroys all active sessions for the specified user.
    Requires admin privileges.
    """
    try:
        destroyed_count = await session_manager.force_logout(user_id)
        
        return ForceLogoutResponse(
            success=True,
            sessions_destroyed=destroyed_count,
            user_id=user_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{session_id}/extend", response_model=SessionResponse)
async def extend_session(
    session_id: str,
    request: ExtendSessionRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Extend session timeout.
    
    Adds additional time to the session's expiration.
    """
    try:
        success = await session_manager.extend_session(
            session_id=session_id,
            additional_seconds=request.additional_seconds
        )
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
        # Get updated session
        session = await session_manager.validate_session(session_id)
        
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            created_at=session.created_at,
            last_activity=session.last_activity,
            expires_at=session.expires_at,
            metadata=session.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{session_id}/validate", response_model=SessionResponse)
async def validate_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Validate a session.
    
    Checks if session is valid and refreshes last activity time.
    """
    try:
        session = await session_manager.validate_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalid or expired"
            )
        
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            created_at=session.created_at,
            last_activity=session.last_activity,
            expires_at=session.expires_at,
            metadata=session.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Session Configuration Endpoints
# ============================================================================

@router.get("/config/current", response_model=SessionConfigResponse)
async def get_session_config(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Get current session configuration.
    """
    return SessionConfigResponse(
        default_timeout=session_manager.default_timeout,
        max_concurrent_sessions=session_manager.max_concurrent_sessions
    )


@router.put("/config", response_model=SessionConfigResponse)
async def update_session_config(
    request: SessionConfigRequest,
    admin_user_id: str = Query(..., description="Admin user ID making the change"),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Update session configuration.
    
    Requires admin privileges.
    """
    try:
        if request.default_timeout is not None:
            await session_manager.configure_timeout(request.default_timeout)
        
        if request.max_concurrent_sessions is not None:
            await session_manager.configure_max_concurrent(request.max_concurrent_sessions)
        
        # Log the configuration change
        await session_manager.audit_logger.log(
            event_type="session_config_updated",
            user_id=admin_user_id,
            resource="session_config",
            action="update",
            result=True,
            details={
                "default_timeout": session_manager.default_timeout,
                "max_concurrent_sessions": session_manager.max_concurrent_sessions
            }
        )
        
        return SessionConfigResponse(
            default_timeout=session_manager.default_timeout,
            max_concurrent_sessions=session_manager.max_concurrent_sessions
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Session Statistics Endpoints
# ============================================================================

@router.get("/stats/overview", response_model=SessionStatisticsResponse)
async def get_session_statistics(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Get session statistics.
    
    Returns overview of active sessions and configuration.
    """
    try:
        stats = await session_manager.get_session_statistics()
        
        return SessionStatisticsResponse(
            total_active_sessions=stats["total_active_sessions"],
            total_users_with_sessions=stats["total_users_with_sessions"],
            top_users_by_sessions=stats["top_users_by_sessions"],
            configuration=SessionConfigResponse(
                default_timeout=stats["configuration"]["default_timeout"],
                max_concurrent_sessions=stats["configuration"]["max_concurrent_sessions"]
            )
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_expired_sessions(
    admin_user_id: str = Query(..., description="Admin user ID performing the action"),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Clean up expired sessions.
    
    Removes all expired sessions from the system.
    Requires admin privileges.
    """
    try:
        cleaned_count = await session_manager.cleanup_expired_sessions()
        
        # Log the cleanup
        await session_manager.audit_logger.log(
            event_type="session_cleanup",
            user_id=admin_user_id,
            resource="sessions",
            action="cleanup",
            result=True,
            details={"cleaned_count": cleaned_count}
        )
        
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "performed_by": admin_user_id,
            "performed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# User Session Endpoints
# ============================================================================

@router.get("/users/{user_id}", response_model=SessionListResponse)
async def get_user_sessions(
    user_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Get all sessions for a specific user.
    """
    try:
        sessions = await session_manager.get_user_sessions(user_id)
        
        session_responses = [
            SessionResponse(
                id=s.id,
                user_id=s.user_id,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                created_at=s.created_at,
                last_activity=s.last_activity,
                expires_at=s.expires_at,
                metadata=s.metadata
            )
            for s in sessions
        ]
        
        return SessionListResponse(
            sessions=session_responses,
            total=len(session_responses)
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def destroy_user_sessions(
    user_id: str,
    admin_user_id: str = Query(..., description="Admin user ID performing the action"),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Destroy all sessions for a user.
    
    Same as force_logout but returns no content.
    """
    try:
        await session_manager.force_logout(user_id)
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
