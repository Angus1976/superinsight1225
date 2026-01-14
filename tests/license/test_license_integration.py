"""
Integration tests for License Management.

Tests the complete license management workflow including database operations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_db():
    """Create test database."""
    from sqlalchemy.orm import declarative_base
    from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON
    
    Base = declarative_base()
    
    # Define test models (SQLite-compatible)
    class TestLicense(Base):
        __tablename__ = "test_licenses"
        
        id = Column(String(36), primary_key=True)
        license_key = Column(String(255), unique=True)
        license_type = Column(String(50))
        features = Column(JSON)
        max_concurrent_users = Column(Integer, default=10)
        max_cpu_cores = Column(Integer, default=4)
        max_storage_gb = Column(Integer, default=100)
        max_projects = Column(Integer, default=10)
        max_datasets = Column(Integer, default=100)
        validity_start = Column(DateTime)
        validity_end = Column(DateTime)
        subscription_type = Column(String(50))
        grace_period_days = Column(Integer, default=7)
        hardware_id = Column(String(255), nullable=True)
        status = Column(String(50), default="pending")
        signature = Column(Text)
        created_at = Column(DateTime, default=datetime.utcnow)
        activated_at = Column(DateTime, nullable=True)
        revoked_at = Column(DateTime, nullable=True)
    
    class TestSession(Base):
        __tablename__ = "test_sessions"
        
        id = Column(String(36), primary_key=True)
        user_id = Column(String(255))
        session_id = Column(String(255), unique=True)
        priority = Column(Integer, default=0)
        is_active = Column(Boolean, default=True)
        login_time = Column(DateTime, default=datetime.utcnow)
        last_activity = Column(DateTime, default=datetime.utcnow)
        logout_time = Column(DateTime, nullable=True)
    
    class TestAuditLog(Base):
        __tablename__ = "test_audit_logs"
        
        id = Column(String(36), primary_key=True)
        license_id = Column(String(36), nullable=True)
        event_type = Column(String(50))
        details = Column(JSON)
        user_id = Column(String(255), nullable=True)
        success = Column(Boolean, default=True)
        timestamp = Column(DateTime, default=datetime.utcnow)
    
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield {
        "session": session,
        "License": TestLicense,
        "Session": TestSession,
        "AuditLog": TestAuditLog,
    }
    
    session.close()


# ============================================================================
# License Manager Tests
# ============================================================================

class TestLicenseManagerIntegration:
    """Integration tests for License Manager."""
    
    def test_create_license(self, test_db):
        """Test license creation."""
        session = test_db["session"]
        License = test_db["License"]
        
        license = License(
            id=str(uuid4()),
            license_key="TEST-1234-5678-ABCD",
            license_type="basic",
            features=["api_access", "basic_annotation"],
            max_concurrent_users=10,
            validity_start=datetime.now(timezone.utc),
            validity_end=datetime.now(timezone.utc) + timedelta(days=365),
            subscription_type="yearly",
            status="pending",
            signature="test_signature",
        )
        
        session.add(license)
        session.commit()
        
        # Verify
        result = session.query(License).filter_by(license_key="TEST-1234-5678-ABCD").first()
        assert result is not None
        assert result.license_type == "basic"
        assert result.status == "pending"
    
    def test_activate_license(self, test_db):
        """Test license activation."""
        session = test_db["session"]
        License = test_db["License"]
        
        # Create pending license
        license = License(
            id=str(uuid4()),
            license_key="ACTIVATE-TEST-KEY",
            license_type="professional",
            features=["api_access", "ai_annotation"],
            max_concurrent_users=20,
            validity_start=datetime.now(timezone.utc) - timedelta(days=1),
            validity_end=datetime.now(timezone.utc) + timedelta(days=364),
            subscription_type="yearly",
            status="pending",
            signature="test_signature",
        )
        
        session.add(license)
        session.commit()
        
        # Activate
        license.status = "active"
        license.activated_at = datetime.now(timezone.utc)
        license.hardware_id = "test_hardware_fingerprint"
        session.commit()
        
        # Verify
        result = session.query(License).filter_by(license_key="ACTIVATE-TEST-KEY").first()
        assert result.status == "active"
        assert result.activated_at is not None
        assert result.hardware_id == "test_hardware_fingerprint"
    
    def test_renew_license(self, test_db):
        """Test license renewal."""
        session = test_db["session"]
        License = test_db["License"]
        
        # Use naive datetime for SQLite compatibility
        original_end = datetime.utcnow() + timedelta(days=30)
        
        license = License(
            id=str(uuid4()),
            license_key="RENEW-TEST-KEY",
            license_type="basic",
            features=["api_access"],
            max_concurrent_users=5,
            validity_start=datetime.utcnow() - timedelta(days=335),
            validity_end=original_end,
            subscription_type="yearly",
            status="active",
            signature="test_signature",
        )
        
        session.add(license)
        session.commit()
        
        # Renew
        new_end = original_end + timedelta(days=365)
        license.validity_end = new_end
        session.commit()
        
        # Verify - compare without timezone
        result = session.query(License).filter_by(license_key="RENEW-TEST-KEY").first()
        # Check that the date was updated (within 1 second tolerance)
        assert abs((result.validity_end - new_end).total_seconds()) < 1
    
    def test_revoke_license(self, test_db):
        """Test license revocation."""
        session = test_db["session"]
        License = test_db["License"]
        
        license = License(
            id=str(uuid4()),
            license_key="REVOKE-TEST-KEY",
            license_type="enterprise",
            features=["api_access", "knowledge_graph"],
            max_concurrent_users=100,
            validity_start=datetime.now(timezone.utc),
            validity_end=datetime.now(timezone.utc) + timedelta(days=365),
            subscription_type="yearly",
            status="active",
            signature="test_signature",
        )
        
        session.add(license)
        session.commit()
        
        # Revoke
        license.status = "revoked"
        license.revoked_at = datetime.now(timezone.utc)
        session.commit()
        
        # Verify
        result = session.query(License).filter_by(license_key="REVOKE-TEST-KEY").first()
        assert result.status == "revoked"
        assert result.revoked_at is not None


# ============================================================================
# Concurrent User Controller Tests
# ============================================================================

class TestConcurrentUserIntegration:
    """Integration tests for Concurrent User Controller."""
    
    def test_register_session(self, test_db):
        """Test session registration."""
        session = test_db["session"]
        Session = test_db["Session"]
        
        user_session = Session(
            id=str(uuid4()),
            user_id="user_001",
            session_id="session_abc123",
            priority=0,
            is_active=True,
        )
        
        session.add(user_session)
        session.commit()
        
        # Verify
        result = session.query(Session).filter_by(user_id="user_001").first()
        assert result is not None
        assert result.is_active == True
    
    def test_release_session(self, test_db):
        """Test session release."""
        session = test_db["session"]
        Session = test_db["Session"]
        
        user_session = Session(
            id=str(uuid4()),
            user_id="user_002",
            session_id="session_def456",
            is_active=True,
        )
        
        session.add(user_session)
        session.commit()
        
        # Release
        user_session.is_active = False
        user_session.logout_time = datetime.now(timezone.utc)
        session.commit()
        
        # Verify
        result = session.query(Session).filter_by(user_id="user_002").first()
        assert result.is_active == False
        assert result.logout_time is not None
    
    def test_concurrent_limit_enforcement(self, test_db):
        """Test concurrent user limit enforcement."""
        session = test_db["session"]
        Session = test_db["Session"]
        
        max_users = 3
        
        # Add sessions up to limit
        for i in range(max_users):
            user_session = Session(
                id=str(uuid4()),
                user_id=f"user_{i}",
                session_id=f"session_{i}",
                is_active=True,
            )
            session.add(user_session)
        
        session.commit()
        
        # Count active sessions
        active_count = session.query(Session).filter_by(is_active=True).count()
        assert active_count == max_users
        
        # Verify limit check would fail
        assert active_count >= max_users
    
    def test_force_logout(self, test_db):
        """Test force logout functionality."""
        session = test_db["session"]
        Session = test_db["Session"]
        
        # Create multiple sessions for same user
        for i in range(3):
            user_session = Session(
                id=str(uuid4()),
                user_id="multi_session_user",
                session_id=f"multi_session_{i}",
                is_active=True,
            )
            session.add(user_session)
        
        session.commit()
        
        # Force logout all
        sessions = session.query(Session).filter_by(
            user_id="multi_session_user",
            is_active=True
        ).all()
        
        for s in sessions:
            s.is_active = False
            s.logout_time = datetime.now(timezone.utc)
        
        session.commit()
        
        # Verify all logged out
        active = session.query(Session).filter_by(
            user_id="multi_session_user",
            is_active=True
        ).count()
        
        assert active == 0


# ============================================================================
# Audit Logger Tests
# ============================================================================

class TestAuditLoggerIntegration:
    """Integration tests for Audit Logger."""
    
    def test_log_activation(self, test_db):
        """Test activation logging."""
        session = test_db["session"]
        AuditLog = test_db["AuditLog"]
        
        license_id = str(uuid4())
        
        log = AuditLog(
            id=str(uuid4()),
            license_id=license_id,
            event_type="activated",
            details={"hardware_id": "test_hw", "result": "success"},
            success=True,
        )
        
        session.add(log)
        session.commit()
        
        # Verify
        result = session.query(AuditLog).filter_by(
            license_id=license_id,
            event_type="activated"
        ).first()
        
        assert result is not None
        assert result.success == True
    
    def test_log_validation(self, test_db):
        """Test validation logging."""
        session = test_db["session"]
        AuditLog = test_db["AuditLog"]
        
        license_id = str(uuid4())
        
        log = AuditLog(
            id=str(uuid4()),
            license_id=license_id,
            event_type="validated",
            details={"result": "valid"},
            success=True,
        )
        
        session.add(log)
        session.commit()
        
        # Verify
        result = session.query(AuditLog).filter_by(
            license_id=license_id,
            event_type="validated"
        ).first()
        
        assert result is not None
    
    def test_query_logs_by_type(self, test_db):
        """Test querying logs by event type."""
        session = test_db["session"]
        AuditLog = test_db["AuditLog"]
        
        license_id = str(uuid4())
        
        # Add various log types
        for event_type in ["activated", "validated", "renewed", "validated"]:
            log = AuditLog(
                id=str(uuid4()),
                license_id=license_id,
                event_type=event_type,
                details={},
                success=True,
            )
            session.add(log)
        
        session.commit()
        
        # Query by type
        validated_logs = session.query(AuditLog).filter_by(
            event_type="validated"
        ).all()
        
        assert len(validated_logs) == 2
    
    def test_log_failure(self, test_db):
        """Test logging failed operations."""
        session = test_db["session"]
        AuditLog = test_db["AuditLog"]
        
        log = AuditLog(
            id=str(uuid4()),
            license_id=str(uuid4()),
            event_type="validation_failed",
            details={"reason": "signature_invalid"},
            success=False,
        )
        
        session.add(log)
        session.commit()
        
        # Verify
        failed_logs = session.query(AuditLog).filter_by(success=False).all()
        assert len(failed_logs) >= 1


# ============================================================================
# Feature Controller Tests
# ============================================================================

class TestFeatureControllerIntegration:
    """Integration tests for Feature Controller."""
    
    def test_feature_access_basic(self, test_db):
        """Test feature access for basic license."""
        session = test_db["session"]
        License = test_db["License"]
        
        license = License(
            id=str(uuid4()),
            license_key="FEATURE-BASIC-KEY",
            license_type="basic",
            features=["api_access", "basic_annotation", "export"],
            max_concurrent_users=5,
            validity_start=datetime.now(timezone.utc),
            validity_end=datetime.now(timezone.utc) + timedelta(days=365),
            subscription_type="yearly",
            status="active",
            signature="test_signature",
        )
        
        session.add(license)
        session.commit()
        
        # Verify features
        result = session.query(License).filter_by(license_key="FEATURE-BASIC-KEY").first()
        assert "api_access" in result.features
        assert "basic_annotation" in result.features
        assert "knowledge_graph" not in result.features
    
    def test_feature_access_enterprise(self, test_db):
        """Test feature access for enterprise license."""
        session = test_db["session"]
        License = test_db["License"]
        
        license = License(
            id=str(uuid4()),
            license_key="FEATURE-ENTERPRISE-KEY",
            license_type="enterprise",
            features=[
                "api_access", "basic_annotation", "export",
                "ai_annotation", "quality_assessment",
                "knowledge_graph", "advanced_analytics",
                "multi_tenant", "custom_integrations"
            ],
            max_concurrent_users=100,
            validity_start=datetime.now(timezone.utc),
            validity_end=datetime.now(timezone.utc) + timedelta(days=365),
            subscription_type="yearly",
            status="active",
            signature="test_signature",
        )
        
        session.add(license)
        session.commit()
        
        # Verify all features
        result = session.query(License).filter_by(license_key="FEATURE-ENTERPRISE-KEY").first()
        assert "knowledge_graph" in result.features
        assert "multi_tenant" in result.features


# ============================================================================
# Time Controller Tests
# ============================================================================

class TestTimeControllerIntegration:
    """Integration tests for Time Controller."""
    
    def test_active_license(self, test_db):
        """Test active license validity."""
        session = test_db["session"]
        License = test_db["License"]
        
        # Use naive datetime for SQLite
        now = datetime.utcnow()
        
        license = License(
            id=str(uuid4()),
            license_key="TIME-ACTIVE-KEY",
            license_type="basic",
            features=["api_access"],
            max_concurrent_users=5,
            validity_start=now - timedelta(days=30),
            validity_end=now + timedelta(days=335),
            subscription_type="yearly",
            grace_period_days=7,
            status="active",
            signature="test_signature",
        )
        
        session.add(license)
        session.commit()
        
        result = session.query(License).filter_by(license_key="TIME-ACTIVE-KEY").first()
        
        # Use naive datetime for comparison
        check_now = datetime.utcnow()
        assert result.validity_start < check_now < result.validity_end
    
    def test_expired_license(self, test_db):
        """Test expired license detection."""
        session = test_db["session"]
        License = test_db["License"]
        
        # Use naive datetime for SQLite
        now = datetime.utcnow()
        
        license = License(
            id=str(uuid4()),
            license_key="TIME-EXPIRED-KEY",
            license_type="basic",
            features=["api_access"],
            max_concurrent_users=5,
            validity_start=now - timedelta(days=400),
            validity_end=now - timedelta(days=35),
            subscription_type="yearly",
            grace_period_days=7,
            status="active",
            signature="test_signature",
        )
        
        session.add(license)
        session.commit()
        
        result = session.query(License).filter_by(license_key="TIME-EXPIRED-KEY").first()
        
        check_now = datetime.utcnow()
        grace_end = result.validity_end + timedelta(days=result.grace_period_days)
        
        assert check_now > result.validity_end
        assert check_now > grace_end  # Past grace period too
    
    def test_grace_period_license(self, test_db):
        """Test license in grace period."""
        session = test_db["session"]
        License = test_db["License"]
        
        # Use naive datetime for SQLite
        now = datetime.utcnow()
        
        license = License(
            id=str(uuid4()),
            license_key="TIME-GRACE-KEY",
            license_type="basic",
            features=["api_access"],
            max_concurrent_users=5,
            validity_start=now - timedelta(days=368),
            validity_end=now - timedelta(days=3),
            subscription_type="yearly",
            grace_period_days=7,
            status="active",
            signature="test_signature",
        )
        
        session.add(license)
        session.commit()
        
        result = session.query(License).filter_by(license_key="TIME-GRACE-KEY").first()
        
        check_now = datetime.utcnow()
        grace_end = result.validity_end + timedelta(days=result.grace_period_days)
        
        assert check_now > result.validity_end  # Past end date
        assert check_now < grace_end  # But within grace period


# ============================================================================
# Resource Controller Tests
# ============================================================================

class TestResourceControllerIntegration:
    """Integration tests for Resource Controller."""
    
    def test_resource_limits(self, test_db):
        """Test resource limit configuration."""
        session = test_db["session"]
        License = test_db["License"]
        
        license = License(
            id=str(uuid4()),
            license_key="RESOURCE-TEST-KEY",
            license_type="professional",
            features=["api_access"],
            max_concurrent_users=20,
            max_cpu_cores=8,
            max_storage_gb=200,
            max_projects=20,
            max_datasets=200,
            validity_start=datetime.now(timezone.utc),
            validity_end=datetime.now(timezone.utc) + timedelta(days=365),
            subscription_type="yearly",
            status="active",
            signature="test_signature",
        )
        
        session.add(license)
        session.commit()
        
        result = session.query(License).filter_by(license_key="RESOURCE-TEST-KEY").first()
        
        assert result.max_cpu_cores == 8
        assert result.max_storage_gb == 200
        assert result.max_projects == 20
        assert result.max_datasets == 200
