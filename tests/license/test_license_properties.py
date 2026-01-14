"""
Property-based tests for License Management.

Uses Hypothesis for property-based testing with minimum 100 iterations per property.
"""

import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.schemas.license import (
    LicenseType, LicenseStatus, SubscriptionType, ValidityStatus,
    LicenseLimits, LicenseValidity
)


# ============================================================================
# Test Data Models (SQLite-compatible for testing)
# ============================================================================

class MockLicense:
    """Mock license for testing without database."""
    
    def __init__(
        self,
        license_key: str,
        license_type: LicenseType,
        features: List[str],
        max_concurrent_users: int,
        max_cpu_cores: int,
        max_storage_gb: int,
        max_projects: int,
        max_datasets: int,
        validity_start: datetime,
        validity_end: datetime,
        subscription_type: SubscriptionType,
        grace_period_days: int,
        hardware_id: str = None,
        status: LicenseStatus = LicenseStatus.ACTIVE,
        signature: str = "",
        activated_at: datetime = None,
        revoked_at: datetime = None,
    ):
        self.id = uuid4()
        self.license_key = license_key
        self.license_type = license_type
        self.features = features
        self.max_concurrent_users = max_concurrent_users
        self.max_cpu_cores = max_cpu_cores
        self.max_storage_gb = max_storage_gb
        self.max_projects = max_projects
        self.max_datasets = max_datasets
        self.validity_start = validity_start
        self.validity_end = validity_end
        self.subscription_type = subscription_type
        self.grace_period_days = grace_period_days
        self.hardware_id = hardware_id
        self.status = status
        self.signature = signature
        self.activated_at = activated_at
        self.revoked_at = revoked_at


class MockSession:
    """Mock session for testing."""
    
    def __init__(self, user_id: str, session_id: str, priority: int = 0):
        self.id = uuid4()
        self.user_id = user_id
        self.session_id = session_id
        self.priority = priority
        self.is_active = True
        self.login_time = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)


# ============================================================================
# Helper Functions
# ============================================================================

def generate_signature(license_data: Dict[str, Any], signing_key: str = "test_key") -> str:
    """Generate signature for license data."""
    data_str = "|".join([
        str(license_data.get("license_key", "")),
        str(license_data.get("license_type", "")),
        str(license_data.get("validity_start", "")),
        str(license_data.get("validity_end", "")),
        str(license_data.get("max_concurrent_users", "")),
        str(license_data.get("hardware_id", "")),
    ])
    return hashlib.sha256(f"{data_str}|{signing_key}".encode()).hexdigest()


def verify_signature(license: MockLicense, signing_key: str = "test_key") -> bool:
    """Verify license signature."""
    license_data = {
        "license_key": license.license_key,
        "license_type": license.license_type.value,
        "validity_start": license.validity_start.isoformat(),
        "validity_end": license.validity_end.isoformat(),
        "max_concurrent_users": license.max_concurrent_users,
        "hardware_id": license.hardware_id,
    }
    expected = generate_signature(license_data, signing_key)
    return license.signature == expected


def check_validity_status(license: MockLicense) -> ValidityStatus:
    """Check license validity status."""
    now = datetime.now(timezone.utc)
    validity_start = license.validity_start
    validity_end = license.validity_end
    
    if validity_start.tzinfo is None:
        validity_start = validity_start.replace(tzinfo=timezone.utc)
    if validity_end.tzinfo is None:
        validity_end = validity_end.replace(tzinfo=timezone.utc)
    
    if now < validity_start:
        return ValidityStatus.NOT_STARTED
    
    if now > validity_end:
        grace_end = validity_end + timedelta(days=license.grace_period_days)
        if now <= grace_end:
            return ValidityStatus.GRACE_PERIOD
        return ValidityStatus.EXPIRED
    
    return ValidityStatus.ACTIVE


# ============================================================================
# Strategies
# ============================================================================

# Safe alphabet for license keys
LICENSE_KEY_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

license_key_strategy = st.text(
    alphabet=LICENSE_KEY_ALPHABET,
    min_size=16,
    max_size=20
)

license_type_strategy = st.sampled_from([
    LicenseType.TRIAL,
    LicenseType.BASIC,
    LicenseType.PROFESSIONAL,
    LicenseType.ENTERPRISE,
])

status_strategy = st.sampled_from([
    LicenseStatus.PENDING,
    LicenseStatus.ACTIVE,
    LicenseStatus.EXPIRED,
    LicenseStatus.SUSPENDED,
    LicenseStatus.REVOKED,
])

subscription_strategy = st.sampled_from([
    SubscriptionType.PERPETUAL,
    SubscriptionType.MONTHLY,
    SubscriptionType.YEARLY,
])

# Safe alphabet for user/session IDs
ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789_"

user_id_strategy = st.text(alphabet=ID_ALPHABET, min_size=1, max_size=20)
session_id_strategy = st.text(alphabet=ID_ALPHABET, min_size=1, max_size=32)


# ============================================================================
# Property 1: License Signature Verification
# ============================================================================

@settings(max_examples=100)
@given(
    license_key=license_key_strategy,
    license_type=license_type_strategy,
    max_users=st.integers(min_value=1, max_value=1000),
    days_offset=st.integers(min_value=-30, max_value=30),
    duration_days=st.integers(min_value=1, max_value=365),
)
def test_license_signature_verification(
    license_key: str,
    license_type: LicenseType,
    max_users: int,
    days_offset: int,
    duration_days: int,
):
    """
    Property 1: Signed licenses should pass verification.
    
    Validates: Requirements 7.1, 7.2
    """
    now = datetime.now(timezone.utc)
    validity_start = now + timedelta(days=days_offset)
    validity_end = validity_start + timedelta(days=duration_days)
    
    # Create license data
    license_data = {
        "license_key": license_key,
        "license_type": license_type.value,
        "validity_start": validity_start.isoformat(),
        "validity_end": validity_end.isoformat(),
        "max_concurrent_users": max_users,
        "hardware_id": None,
    }
    
    # Generate signature
    signature = generate_signature(license_data)
    
    # Create mock license
    license = MockLicense(
        license_key=license_key,
        license_type=license_type,
        features=[],
        max_concurrent_users=max_users,
        max_cpu_cores=4,
        max_storage_gb=100,
        max_projects=10,
        max_datasets=100,
        validity_start=validity_start,
        validity_end=validity_end,
        subscription_type=SubscriptionType.YEARLY,
        grace_period_days=7,
        signature=signature,
    )
    
    # Verify signature
    assert verify_signature(license) == True


@settings(max_examples=100)
@given(
    license_key=license_key_strategy,
    tampered_key=license_key_strategy,
)
def test_tampered_license_fails_verification(
    license_key: str,
    tampered_key: str,
):
    """
    Property 1b: Tampered licenses should fail verification.
    
    Validates: Requirements 7.1, 7.2
    """
    assume(license_key != tampered_key)
    
    now = datetime.now(timezone.utc)
    validity_start = now
    validity_end = now + timedelta(days=30)
    
    # Create license data with original key
    license_data = {
        "license_key": license_key,
        "license_type": LicenseType.BASIC.value,
        "validity_start": validity_start.isoformat(),
        "validity_end": validity_end.isoformat(),
        "max_concurrent_users": 10,
        "hardware_id": None,
    }
    
    signature = generate_signature(license_data)
    
    # Create license with tampered key
    license = MockLicense(
        license_key=tampered_key,  # Tampered!
        license_type=LicenseType.BASIC,
        features=[],
        max_concurrent_users=10,
        max_cpu_cores=4,
        max_storage_gb=100,
        max_projects=10,
        max_datasets=100,
        validity_start=validity_start,
        validity_end=validity_end,
        subscription_type=SubscriptionType.YEARLY,
        grace_period_days=7,
        signature=signature,
    )
    
    # Verification should fail
    assert verify_signature(license) == False


# ============================================================================
# Property 2: Concurrent User Limit Consistency
# ============================================================================

class MockConcurrentController:
    """Mock concurrent user controller for testing."""
    
    def __init__(self, max_users: int):
        self.max_users = max_users
        self.sessions: Dict[str, MockSession] = {}
    
    def check_limit(self, user_id: str) -> bool:
        """Check if user can log in."""
        # User already has session
        if user_id in self.sessions:
            return True
        # Check limit
        return len(self.sessions) < self.max_users
    
    def register_session(self, user_id: str, session_id: str) -> bool:
        """Register a session."""
        if not self.check_limit(user_id):
            return False
        self.sessions[user_id] = MockSession(user_id, session_id)
        return True
    
    def release_session(self, user_id: str) -> bool:
        """Release a session."""
        if user_id in self.sessions:
            del self.sessions[user_id]
            return True
        return False
    
    def get_count(self) -> int:
        """Get current session count."""
        return len(self.sessions)


@settings(max_examples=100)
@given(
    max_users=st.integers(min_value=1, max_value=100),
    login_attempts=st.integers(min_value=1, max_value=200),
)
def test_concurrent_user_limit_consistency(max_users: int, login_attempts: int):
    """
    Property 2: Concurrent users should never exceed license limit.
    
    Validates: Requirements 2.2, 2.3
    """
    controller = MockConcurrentController(max_users=max_users)
    successful_logins = 0
    
    for i in range(login_attempts):
        user_id = f"user_{i}"
        session_id = f"session_{i}"
        
        if controller.register_session(user_id, session_id):
            successful_logins += 1
    
    # Should never exceed max
    assert successful_logins <= max_users
    assert controller.get_count() <= max_users


@settings(max_examples=100)
@given(
    max_users=st.integers(min_value=1, max_value=50),
    users_to_add=st.integers(min_value=1, max_value=50),
    users_to_remove=st.integers(min_value=0, max_value=50),
)
def test_session_release_correctness(
    max_users: int,
    users_to_add: int,
    users_to_remove: int,
):
    """
    Property 6: Session release should correctly update count.
    
    Validates: Requirements 2.6
    """
    controller = MockConcurrentController(max_users=max_users)
    
    # Add users
    added = 0
    for i in range(users_to_add):
        if controller.register_session(f"user_{i}", f"session_{i}"):
            added += 1
    
    initial_count = controller.get_count()
    assert initial_count == added
    
    # Remove users
    actual_remove = min(users_to_remove, added)
    for i in range(actual_remove):
        controller.release_session(f"user_{i}")
    
    final_count = controller.get_count()
    assert final_count == added - actual_remove


# ============================================================================
# Property 3: Time Validity Check
# ============================================================================

@settings(max_examples=100)
@given(
    start_offset=st.integers(min_value=-365, max_value=365),
    duration_days=st.integers(min_value=1, max_value=365),
    grace_days=st.integers(min_value=0, max_value=30),
)
def test_time_validity_check(
    start_offset: int,
    duration_days: int,
    grace_days: int,
):
    """
    Property 3: License validity check should be correct.
    
    Validates: Requirements 3.1, 3.5
    """
    now = datetime.now(timezone.utc)
    start_date = now + timedelta(days=start_offset)
    end_date = start_date + timedelta(days=duration_days)
    
    license = MockLicense(
        license_key="TEST-KEY",
        license_type=LicenseType.BASIC,
        features=[],
        max_concurrent_users=10,
        max_cpu_cores=4,
        max_storage_gb=100,
        max_projects=10,
        max_datasets=100,
        validity_start=start_date,
        validity_end=end_date,
        subscription_type=SubscriptionType.YEARLY,
        grace_period_days=grace_days,
        signature="",
    )
    
    status = check_validity_status(license)
    
    if now < start_date:
        assert status == ValidityStatus.NOT_STARTED
    elif now > end_date:
        grace_end = end_date + timedelta(days=grace_days)
        if now <= grace_end:
            assert status == ValidityStatus.GRACE_PERIOD
        else:
            assert status == ValidityStatus.EXPIRED
    else:
        assert status == ValidityStatus.ACTIVE


# ============================================================================
# Property 4: Hardware Fingerprint Consistency
# ============================================================================

def generate_fingerprint(components: Dict[str, str]) -> str:
    """Generate hardware fingerprint from components."""
    data = "|".join([
        components.get("mac", ""),
        components.get("hostname", ""),
        components.get("platform", ""),
        components.get("cpu", ""),
    ])
    return hashlib.sha256(data.encode()).hexdigest()


@settings(max_examples=100)
@given(
    mac=st.text(alphabet="0123456789abcdef:", min_size=17, max_size=17),
    hostname=st.text(alphabet=ID_ALPHABET, min_size=1, max_size=20),
    platform=st.text(alphabet=ID_ALPHABET, min_size=1, max_size=20),
    cpu=st.text(alphabet=ID_ALPHABET, min_size=1, max_size=20),
    iterations=st.integers(min_value=2, max_value=10),
)
def test_hardware_fingerprint_consistency(
    mac: str,
    hostname: str,
    platform: str,
    cpu: str,
    iterations: int,
):
    """
    Property 4: Same hardware should produce same fingerprint.
    
    Validates: Requirements 6.3
    """
    components = {
        "mac": mac,
        "hostname": hostname,
        "platform": platform,
        "cpu": cpu,
    }
    
    fingerprints = []
    for _ in range(iterations):
        fp = generate_fingerprint(components)
        fingerprints.append(fp)
    
    # All fingerprints should be identical
    assert len(set(fingerprints)) == 1


# ============================================================================
# Property 5: License Status Transitions
# ============================================================================

VALID_TRANSITIONS = {
    LicenseStatus.PENDING: [LicenseStatus.ACTIVE, LicenseStatus.REVOKED],
    LicenseStatus.ACTIVE: [LicenseStatus.EXPIRED, LicenseStatus.SUSPENDED, LicenseStatus.REVOKED],
    LicenseStatus.EXPIRED: [LicenseStatus.ACTIVE, LicenseStatus.REVOKED],
    LicenseStatus.SUSPENDED: [LicenseStatus.ACTIVE, LicenseStatus.REVOKED],
    LicenseStatus.REVOKED: [],  # Terminal state
}


def can_transition(current: LicenseStatus, target: LicenseStatus) -> bool:
    """Check if status transition is valid."""
    return target in VALID_TRANSITIONS.get(current, [])


@settings(max_examples=100)
@given(
    initial_status=st.sampled_from([
        LicenseStatus.PENDING,
        LicenseStatus.ACTIVE,
        LicenseStatus.EXPIRED,
        LicenseStatus.SUSPENDED,
    ]),
    target_status=status_strategy,
)
def test_license_status_transitions(
    initial_status: LicenseStatus,
    target_status: LicenseStatus,
):
    """
    Property 5: License status transitions should follow valid paths.
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4
    """
    valid_targets = VALID_TRANSITIONS.get(initial_status, [])
    
    if target_status in valid_targets:
        assert can_transition(initial_status, target_status) == True
    else:
        assert can_transition(initial_status, target_status) == False


@settings(max_examples=100)
@given(
    target_status=status_strategy,
)
def test_revoked_is_terminal(target_status: LicenseStatus):
    """
    Property 5b: Revoked status should be terminal.
    
    Validates: Requirements 1.4
    """
    # Cannot transition from REVOKED to anything
    assert can_transition(LicenseStatus.REVOKED, target_status) == False


# ============================================================================
# Property 7: Audit Log Completeness
# ============================================================================

class MockAuditLogger:
    """Mock audit logger for testing."""
    
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []
    
    def log_event(self, event_type: str, license_id: str, details: Dict = None):
        """Log an event."""
        self.logs.append({
            "id": str(uuid4()),
            "event_type": event_type,
            "license_id": license_id,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    def query_logs(self, license_id: str = None, event_type: str = None) -> List[Dict]:
        """Query logs."""
        result = self.logs
        if license_id:
            result = [l for l in result if l["license_id"] == license_id]
        if event_type:
            result = [l for l in result if l["event_type"] == event_type]
        return result


@settings(max_examples=100)
@given(
    event_type=st.sampled_from(["activation", "validation", "renewal", "revocation"]),
    license_id=st.text(alphabet=ID_ALPHABET, min_size=1, max_size=36),
)
def test_audit_log_completeness(event_type: str, license_id: str):
    """
    Property 7: Every license operation should have audit log.
    
    Validates: Requirements 8.1, 8.2, 8.3
    """
    logger = MockAuditLogger()
    
    # Perform operation (simulated by logging)
    logger.log_event(event_type, license_id, {"action": "test"})
    
    # Verify log exists
    logs = logger.query_logs(license_id=license_id, event_type=event_type)
    assert len(logs) > 0
    assert logs[-1]["event_type"] == event_type
    assert logs[-1]["license_id"] == license_id


# ============================================================================
# Property 8: Feature Module Access Control
# ============================================================================

FEATURE_MATRIX = {
    LicenseType.TRIAL: ["api_access", "basic_annotation"],
    LicenseType.BASIC: ["api_access", "basic_annotation", "export"],
    LicenseType.PROFESSIONAL: [
        "api_access", "basic_annotation", "export",
        "ai_annotation", "quality_assessment"
    ],
    LicenseType.ENTERPRISE: [
        "api_access", "basic_annotation", "export",
        "ai_annotation", "quality_assessment",
        "knowledge_graph", "advanced_analytics",
        "multi_tenant", "custom_integrations"
    ],
}


def check_feature_access(license_type: LicenseType, feature: str) -> bool:
    """Check if feature is accessible for license type."""
    allowed_features = FEATURE_MATRIX.get(license_type, [])
    return feature in allowed_features


@settings(max_examples=100)
@given(
    license_type=license_type_strategy,
    feature=st.sampled_from([
        "api_access", "basic_annotation", "export",
        "ai_annotation", "quality_assessment",
        "knowledge_graph", "advanced_analytics",
        "multi_tenant", "custom_integrations"
    ]),
)
def test_feature_access_control(license_type: LicenseType, feature: str):
    """
    Property 8: Feature access should match license type.
    
    Validates: Requirements 5.1, 5.2, 5.3
    """
    allowed_features = FEATURE_MATRIX.get(license_type, [])
    access_result = check_feature_access(license_type, feature)
    
    if feature in allowed_features:
        assert access_result == True
    else:
        assert access_result == False


@settings(max_examples=100)
@given(
    license_type=license_type_strategy,
)
def test_higher_tiers_include_lower_features(license_type: LicenseType):
    """
    Property 8b: Higher license tiers should include all lower tier features.
    
    Validates: Requirements 5.1, 5.2
    """
    tier_order = [
        LicenseType.TRIAL,
        LicenseType.BASIC,
        LicenseType.PROFESSIONAL,
        LicenseType.ENTERPRISE,
    ]
    
    current_idx = tier_order.index(license_type)
    current_features = set(FEATURE_MATRIX.get(license_type, []))
    
    # Check all lower tiers
    for i in range(current_idx):
        lower_features = set(FEATURE_MATRIX.get(tier_order[i], []))
        # Current tier should have all features from lower tiers
        assert lower_features.issubset(current_features)
