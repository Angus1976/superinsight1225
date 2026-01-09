"""
Authentication API endpoints for SuperInsight Platform.
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.controller import SecurityController
from src.security.models import UserModel, UserRole, AuditAction

logger = logging.getLogger(__name__)

# Initialize security controller
security_controller = SecurityController()

# Security scheme
security = HTTPBearer()

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response models
class LoginRequest(BaseModel):
    username: str
    password: str
    tenant_id: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    role: str
    tenant_id: str
    is_active: bool
    last_login: Optional[datetime]


# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
) -> UserModel:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = security_controller.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# Authentication endpoints
@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db_session)
):
    """Authenticate user and return access token."""
    try:
        # Authenticate user
        user = security_controller.authenticate_user(
            username=request.username,
            password=request.password,
            db=db
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check tenant_id if provided
        if request.tenant_id and user.tenant_id != request.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid tenant",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token = security_controller.create_access_token(
            user_id=str(user.id),
            tenant_id=user.tenant_id
        )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Log successful login
        security_controller.log_user_action(
            user_id=user.id,
            tenant_id=user.tenant_id,
            action=AuditAction.LOGIN,
            resource_type="auth",
            resource_id=str(user.id),
            details={"username": user.username},
            db=db
        )
        
        return LoginResponse(
            access_token=access_token,
            user={
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "tenant_id": user.tenant_id,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
async def logout(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Logout user (invalidate token on client side)."""
    try:
        # Log logout event
        security_controller.log_user_action(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action=AuditAction.LOGOUT,
            resource_type="auth",
            resource_id=str(current_user.id),
            details={"username": current_user.username},
            db=db
        )
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserModel = Depends(get_current_user)
):
    """Get current user information."""
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        tenant_id=current_user.tenant_id,
        is_active=current_user.is_active,
        last_login=current_user.last_login
    )


@router.get("/tenants")
async def get_tenants():
    """Get available tenants for login."""
    # For now, return a default tenant
    # In a real implementation, this would query the database
    return [
        {
            "id": "default_tenant",
            "name": "Default Tenant",
            "logo": None
        }
    ]