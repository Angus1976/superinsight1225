"""
Concurrent User Controller for SuperInsight Platform.

Manages concurrent user sessions and enforces user limits.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.license import ConcurrentSessionModel, LicenseModel, LicenseStatus
from src.schemas.license import (
    ConcurrentCheckResult, UserSession, RegisterSessionRequest
)


class ConcurrentUserController:
    """
    Concurrent User Controller.
    
    Manages user sessions and enforces concurrent user limits.
    """
    
    # Session timeout in minutes
    SESSION_TIMEOUT_MINUTES = 30
    
    def __init__(
        self,
        db: AsyncSession,
        max_users: Optional[int] = None
    ):
        """
        Initialize Concurrent User Controller.
        
        Args:
            db: Database session
            max_users: Override max concurrent users (for testing)
        """
        self.db = db
        self._max_users_override = max_users
    
    async def _get_max_users(self) -> int:
        """Get maximum concurrent users from active license."""
        if self._max_users_override is not None:
            return self._max_users_override
        
        result = await self.db.execute(
            select(LicenseModel)
            .where(LicenseModel.status == LicenseStatus.ACTIVE)
            .order_by(LicenseModel.activated_at.desc())
            .limit(1)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return 0  # No license, no users allowed
        
        return license_model.max_concurrent_users
    
    async def _cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        timeout = datetime.now(timezone.utc) - timedelta(
            minutes=self.SESSION_TIMEOUT_MINUTES
        )
        
        result = await self.db.execute(
            update(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.is_active == True)
            .where(ConcurrentSessionModel.last_activity < timeout)
            .values(is_active=False, logout_time=datetime.now(timezone.utc))
        )
        
        await self.db.commit()
        return result.rowcount
    
    async def get_current_user_count(self) -> int:
        """Get current active user count."""
        # Clean up expired sessions first
        await self._cleanup_expired_sessions()
        
        result = await self.db.execute(
            select(func.count(ConcurrentSessionModel.id))
            .where(ConcurrentSessionModel.is_active == True)
        )
        return result.scalar() or 0
    
    async def check_concurrent_limit(
        self,
        user_id: str
    ) -> ConcurrentCheckResult:
        """
        Check if user can log in based on concurrent limits.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Check result with allowed status
        """
        max_users = await self._get_max_users()
        
        if max_users == 0:
            return ConcurrentCheckResult(
                allowed=False,
                reason="No valid license found",
                current=0,
                max=0
            )
        
        # Check if user already has an active session
        result = await self.db.execute(
            select(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.user_id == user_id)
            .where(ConcurrentSessionModel.is_active == True)
        )
        existing_session = result.scalar_one_or_none()
        
        if existing_session:
            # User already logged in, allow
            return ConcurrentCheckResult(
                allowed=True,
                current=await self.get_current_user_count(),
                max=max_users
            )
        
        # Check current count
        current_count = await self.get_current_user_count()
        
        if current_count >= max_users:
            return ConcurrentCheckResult(
                allowed=False,
                reason=f"Concurrent user limit reached ({current_count}/{max_users})",
                current=current_count,
                max=max_users
            )
        
        return ConcurrentCheckResult(
            allowed=True,
            current=current_count,
            max=max_users
        )
    
    async def register_user_session(
        self,
        request: RegisterSessionRequest
    ) -> Optional[UserSession]:
        """
        Register a new user session.
        
        Args:
            request: Session registration request
            
        Returns:
            Created session or None if limit reached
        """
        # Check limit first
        check_result = await self.check_concurrent_limit(request.user_id)
        
        if not check_result.allowed:
            return None
        
        # Check for existing session
        result = await self.db.execute(
            select(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.user_id == request.user_id)
            .where(ConcurrentSessionModel.is_active == True)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing session
            existing.last_activity = datetime.now(timezone.utc)
            existing.session_id = request.session_id
            if request.ip_address:
                existing.ip_address = request.ip_address
            if request.user_agent:
                existing.user_agent = request.user_agent
            
            await self.db.commit()
            await self.db.refresh(existing)
            
            return self._to_session(existing)
        
        # Create new session
        session = ConcurrentSessionModel(
            id=uuid4(),
            user_id=request.user_id,
            session_id=request.session_id,
            priority=request.priority,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            is_active=True,
            login_time=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        return self._to_session(session)
    
    async def release_user_session(
        self,
        user_id: str,
        session_id: str
    ) -> bool:
        """
        Release a user session.
        
        Args:
            user_id: User ID
            session_id: Session ID
            
        Returns:
            True if session was released
        """
        result = await self.db.execute(
            select(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.user_id == user_id)
            .where(ConcurrentSessionModel.session_id == session_id)
            .where(ConcurrentSessionModel.is_active == True)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return False
        
        session.is_active = False
        session.logout_time = datetime.now(timezone.utc)
        
        await self.db.commit()
        return True
    
    async def update_session_activity(
        self,
        user_id: str,
        session_id: str
    ) -> bool:
        """
        Update session last activity time.
        
        Args:
            user_id: User ID
            session_id: Session ID
            
        Returns:
            True if session was updated
        """
        result = await self.db.execute(
            update(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.user_id == user_id)
            .where(ConcurrentSessionModel.session_id == session_id)
            .where(ConcurrentSessionModel.is_active == True)
            .values(last_activity=datetime.now(timezone.utc))
        )
        
        await self.db.commit()
        return result.rowcount > 0
    
    async def get_active_sessions(self) -> List[UserSession]:
        """Get all active sessions."""
        await self._cleanup_expired_sessions()
        
        result = await self.db.execute(
            select(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.is_active == True)
            .order_by(ConcurrentSessionModel.login_time.desc())
        )
        sessions = result.scalars().all()
        
        return [self._to_session(s) for s in sessions]
    
    async def get_user_sessions(self, user_id: str) -> List[UserSession]:
        """Get all sessions for a user."""
        result = await self.db.execute(
            select(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.user_id == user_id)
            .where(ConcurrentSessionModel.is_active == True)
        )
        sessions = result.scalars().all()
        
        return [self._to_session(s) for s in sessions]
    
    async def force_logout_user(
        self,
        user_id: str,
        reason: str
    ) -> int:
        """
        Force logout all sessions for a user.
        
        Args:
            user_id: User ID to logout
            reason: Reason for forced logout
            
        Returns:
            Number of sessions terminated
        """
        result = await self.db.execute(
            update(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.user_id == user_id)
            .where(ConcurrentSessionModel.is_active == True)
            .values(
                is_active=False,
                logout_time=datetime.now(timezone.utc)
            )
        )
        
        await self.db.commit()
        return result.rowcount
    
    async def force_logout_session(
        self,
        session_id: str,
        reason: str
    ) -> bool:
        """
        Force logout a specific session.
        
        Args:
            session_id: Session ID to logout
            reason: Reason for forced logout
            
        Returns:
            True if session was terminated
        """
        result = await self.db.execute(
            update(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.session_id == session_id)
            .where(ConcurrentSessionModel.is_active == True)
            .values(
                is_active=False,
                logout_time=datetime.now(timezone.utc)
            )
        )
        
        await self.db.commit()
        return result.rowcount > 0
    
    async def get_session_by_priority(
        self,
        min_priority: int = 0
    ) -> List[UserSession]:
        """Get sessions with priority >= min_priority."""
        result = await self.db.execute(
            select(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.is_active == True)
            .where(ConcurrentSessionModel.priority >= min_priority)
            .order_by(ConcurrentSessionModel.priority.desc())
        )
        sessions = result.scalars().all()
        
        return [self._to_session(s) for s in sessions]
    
    async def evict_lowest_priority_session(self) -> Optional[UserSession]:
        """
        Evict the lowest priority session.
        
        Returns:
            Evicted session or None if no sessions
        """
        result = await self.db.execute(
            select(ConcurrentSessionModel)
            .where(ConcurrentSessionModel.is_active == True)
            .order_by(ConcurrentSessionModel.priority.asc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return None
        
        session.is_active = False
        session.logout_time = datetime.now(timezone.utc)
        
        await self.db.commit()
        
        return self._to_session(session)
    
    def _to_session(self, model: ConcurrentSessionModel) -> UserSession:
        """Convert model to schema."""
        return UserSession(
            id=model.id,
            user_id=model.user_id,
            session_id=model.session_id,
            priority=model.priority,
            login_time=model.login_time,
            last_activity=model.last_activity,
            ip_address=model.ip_address,
            is_active=model.is_active,
        )
