"""
Simple Authentication API for SuperInsight Platform.

Provides basic login functionality for testing and development.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.orm import Session
import jwt
import bcrypt

from src.database.connection import get_db_session
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# JWT configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Request/Response models
class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str]
    name: Optional[str]
    is_active: bool
    is_superuser: bool


class SimpleUser:
    """Simple user object for dependency injection."""
    def __init__(self, user_id: str, email: str, username: Optional[str], name: Optional[str], is_active: bool, is_superuser: bool):
        self.id = user_id
        self.email = email
        self.username = username
        self.name = name
        self.is_active = is_active
        self.is_superuser = is_superuser
        self.tenant_id = "system"  # Default tenant


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db_session)
):
    """Authenticate user and return access token."""
    try:
        # Query user from database
        result = db.execute(text(
            "SELECT id, email, username, name, password_hash, is_active, is_superuser FROM users WHERE email = :email"
        ), {"email": request.email})
        
        user_row = result.fetchone()
        
        if not user_row:
            logger.warning(f"Login attempt for non-existent user: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id, email, username, name, password_hash, is_active, is_superuser = user_row
        
        if not is_active:
            logger.warning(f"Login attempt for inactive user: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not verify_password(request.password, password_hash):
            logger.warning(f"Failed login attempt for user: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": str(user_id), "email": email}
        )
        
        # Update last login
        db.execute(text(
            "UPDATE users SET last_login_at = :now WHERE id = :user_id"
        ), {"now": datetime.utcnow(), "user_id": user_id})
        db.commit()
        
        logger.info(f"Successful login for user: {email}")
        
        return LoginResponse(
            access_token=access_token,
            user={
                "id": str(user_id),
                "email": email,
                "username": username,
                "name": name,
                "is_active": is_active,
                "is_superuser": is_superuser
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


@router.get("/me", response_model=UserResponse)
def get_current_user_endpoint(
    db: Session = Depends(get_db_session),
    token: str = None
):
    """Get current authenticated user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = db.execute(text(
        "SELECT id, email, username, name, is_active, is_superuser FROM users WHERE id = :user_id"
    ), {"user_id": user_id})
    
    user_row = result.fetchone()
    
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id, email, username, name, is_active, is_superuser = user_row
    
    return UserResponse(
        id=str(user_id),
        email=email,
        username=username,
        name=name,
        is_active=is_active,
        is_superuser=is_superuser
    )


async def get_current_user(
    db: Session = Depends(get_db_session),
    authorization: Optional[str] = Header(None)
) -> SimpleUser:
    """Dependency to get current authenticated user from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = db.execute(text(
        "SELECT id, email, username, name, is_active, is_superuser FROM users WHERE id = :user_id"
    ), {"user_id": user_id})
    
    user_row = result.fetchone()
    
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id, email, username, name, is_active, is_superuser = user_row
    
    return SimpleUser(
        user_id=str(user_id),
        email=email,
        username=username,
        name=name,
        is_active=is_active,
        is_superuser=is_superuser
    )
