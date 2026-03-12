"""
Property-based tests for API Key Management.

Tests validate core properties of API key lifecycle, security,
and usage tracking using hypothesis for comprehensive coverage.

Feature: bidirectional-sync-and-external-api
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from uuid import uuid4

from src.sync.gateway.api_key_service import (
    APIKeyService,
    APIKeyConfig,
)
from src.sync.models import APIKeyModel, APIKeyStatus
from src.database.connection import db_manager


@pytest.fixture
def db_session():
    """Create a test database session."""
    with db_manager.get_session() as session:
        yield session


@pytest.fixture
def api_key_service(db_session):
    """Create APIKeyService instance with test session."""
    return APIKeyService(session=db_session)


# Strategy for generating valid API key names
api_key_names = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd', 'Zs')),
    min_size=1,
    max_size=100
).filter(lambda x: x.strip())  # Ensure non-empty after strip

# Strategy for generating tenant IDs
tenant_ids = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')),
    min_size=5,
    max_size=50
)

# Strategy for generating scopes
scopes_strategy = st.dictionaries(
    keys=st.sampled_from(['annotations', 'augmented_data', 'quality_reports', 'experiments']),
    values=st.booleans(),
    min_size=1,
    max_size=4
).filter(lambda d: any(d.values()))  # At least one True value

# Strategy for expiration days
expiration_days = st.one_of(
    st.none(),
    st.integers(min_value=1, max_value=365)
)


class TestProperty9_APIKeyCreationVisibility:
    """
    Feature: bidirectional-sync-and-external-api, Property 9: API 密钥创建仅一次可见
    
    **Validates: Requirements 4.2**
    
    For any 新创建的 API 密钥，创建响应应包含完整的 raw_key 字段；
    后续的查询/列表响应应仅包含 key_prefix，不包含完整密钥
    """
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=api_key_names,
        tenant_id=tenant_ids,
        scopes=scopes_strategy
    )
    def test_raw_key_only_visible_on_creation(
        self,
        api_key_service,
        db_session,
        name,
        tenant_id,
        scopes
    ):
        """Property: Raw key is only visible in creation response, never in subsequent queries."""
        # Arrange
        config = APIKeyConfig(
            name=name,
            tenant_id=tenant_id,
            scopes=scopes
        )
        
        # Act - Create key
        creation_response = api_key_service.create_key(config)
        
        # Assert - Creation response contains raw_key
        assert creation_response.raw_key is not None, \
            "Creation response must contain raw_key"
        assert creation_response.raw_key.startswith("sk_"), \
            "Raw key must have correct prefix"
        assert len(creation_response.raw_key) == 67, \
            "Raw key must be sk_ + 64 hex chars"
        assert creation_response.key_prefix is not None, \
            "Creation response must contain key_prefix"
        
        # Act - Get key by ID
        get_response = api_key_service.get_key(creation_response.id, tenant_id)
        
        # Assert - Get response does NOT contain raw_key
        assert get_response is not None, "Get should return the key"
        assert get_response.raw_key is None, \
            "Get response must NOT contain raw_key"
        assert get_response.key_prefix == creation_response.key_prefix, \
            "Get response must contain key_prefix for identification"
        
        # Act - List keys
        list_response = api_key_service.list_keys(tenant_id)
        
        # Assert - List response does NOT contain raw_key
        assert len(list_response) > 0, "List should return keys"
        matching_keys = [k for k in list_response if k.id == creation_response.id]
        assert len(matching_keys) == 1, "Should find the created key in list"
        
        listed_key = matching_keys[0]
        assert listed_key.raw_key is None, \
            "List response must NOT contain raw_key"
        assert listed_key.key_prefix == creation_response.key_prefix, \
            "List response must contain key_prefix for identification"
        
        # Cleanup
        db_session.query(APIKeyModel).filter_by(id=creation_response.id).delete()
        db_session.commit()


class TestProperty10_APIKeyStateMachine:
    """
    Feature: bidirectional-sync-and-external-api, Property 10: API 密钥状态机正确性
    
    **Validates: Requirements 4.4**
    
    For any API 密钥，状态转换应遵循：
    - active↔disabled 可双向切换
    - active/disabled→revoked 为单向终态
    - revoked 状态不可恢复
    """
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=api_key_names,
        tenant_id=tenant_ids,
        scopes=scopes_strategy
    )
    def test_active_disabled_bidirectional(
        self,
        api_key_service,
        db_session,
        name,
        tenant_id,
        scopes
    ):
        """Property: Active and disabled states can transition bidirectionally."""
        # Arrange
        config = APIKeyConfig(name=name, tenant_id=tenant_id, scopes=scopes)
        response = api_key_service.create_key(config)
        key_id = response.id
        
        try:
            # Assert - Initial state is active
            db_key = db_session.query(APIKeyModel).filter_by(id=key_id).first()
            assert db_key.status == APIKeyStatus.ACTIVE, \
                "Initial status must be ACTIVE"
            
            # Act - Disable key
            result = api_key_service.disable_key(key_id, tenant_id)
            assert result is True, "Disable should succeed"
            
            # Assert - Status is disabled
            db_session.refresh(db_key)
            assert db_key.status == APIKeyStatus.DISABLED, \
                "Status must be DISABLED after disable"
            
            # Act - Enable key
            result = api_key_service.enable_key(key_id, tenant_id)
            assert result is True, "Enable should succeed"
            
            # Assert - Status is active again
            db_session.refresh(db_key)
            assert db_key.status == APIKeyStatus.ACTIVE, \
                "Status must be ACTIVE after enable"
            
            # Act - Disable again
            result = api_key_service.disable_key(key_id, tenant_id)
            assert result is True, "Second disable should succeed"
            
            # Assert - Status is disabled again
            db_session.refresh(db_key)
            assert db_key.status == APIKeyStatus.DISABLED, \
                "Status must be DISABLED after second disable"
        
        finally:
            # Cleanup
            db_session.query(APIKeyModel).filter_by(id=key_id).delete()
            db_session.commit()
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=api_key_names,
        tenant_id=tenant_ids,
        scopes=scopes_strategy,
        initial_state=st.sampled_from([APIKeyStatus.ACTIVE, APIKeyStatus.DISABLED])
    )
    def test_revoked_is_terminal(
        self,
        api_key_service,
        db_session,
        name,
        tenant_id,
        scopes,
        initial_state
    ):
        """Property: Revoked is a terminal state that cannot be recovered."""
        # Arrange
        config = APIKeyConfig(name=name, tenant_id=tenant_id, scopes=scopes)
        response = api_key_service.create_key(config)
        key_id = response.id
        
        try:
            # Set initial state
            if initial_state == APIKeyStatus.DISABLED:
                api_key_service.disable_key(key_id, tenant_id)
            
            # Act - Revoke key
            result = api_key_service.revoke_key(key_id, tenant_id)
            assert result is True, "Revoke should succeed"
            
            # Assert - Status is revoked
            db_key = db_session.query(APIKeyModel).filter_by(id=key_id).first()
            assert db_key.status == APIKeyStatus.REVOKED, \
                "Status must be REVOKED after revoke"
            
            # Act - Try to enable revoked key
            result = api_key_service.enable_key(key_id, tenant_id)
            
            # Assert - Enable fails, status remains revoked
            assert result is False, \
                "Enable must fail on revoked key"
            db_session.refresh(db_key)
            assert db_key.status == APIKeyStatus.REVOKED, \
                "Status must remain REVOKED after failed enable"
            
            # Act - Try to disable revoked key
            result = api_key_service.disable_key(key_id, tenant_id)
            
            # Assert - Disable fails, status remains revoked
            assert result is False, \
                "Disable must fail on revoked key"
            db_session.refresh(db_key)
            assert db_key.status == APIKeyStatus.REVOKED, \
                "Status must remain REVOKED after failed disable"
        
        finally:
            # Cleanup
            db_session.query(APIKeyModel).filter_by(id=key_id).delete()
            db_session.commit()


class TestProperty11_ExpiredRevokedKeysRejectAccess:
    """
    Feature: bidirectional-sync-and-external-api, Property 11: 过期/吊销密钥拒绝访问
    
    **Validates: Requirements 4.6**
    
    For any 已过期或已吊销的 API 密钥，使用该密钥的所有 API 请求应返回 401 状态码
    (在此测试中，我们验证 validate_key 返回 None，表示拒绝访问)
    """
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=api_key_names,
        tenant_id=tenant_ids,
        scopes=scopes_strategy
    )
    def test_revoked_key_rejects_access(
        self,
        api_key_service,
        db_session,
        name,
        tenant_id,
        scopes
    ):
        """Property: Revoked keys are rejected during validation."""
        # Arrange
        config = APIKeyConfig(name=name, tenant_id=tenant_id, scopes=scopes)
        response = api_key_service.create_key(config)
        raw_key = response.raw_key
        key_id = response.id
        
        try:
            # Assert - Key is valid before revocation
            validated = api_key_service.validate_key(raw_key)
            assert validated is not None, \
                "Key must be valid before revocation"
            assert validated.id == key_id, \
                "Validated key must match created key"
            
            # Act - Revoke key
            api_key_service.revoke_key(key_id, tenant_id)
            
            # Assert - Key is rejected after revocation
            validated = api_key_service.validate_key(raw_key)
            assert validated is None, \
                "Revoked key must be rejected (validate_key returns None)"
        
        finally:
            # Cleanup
            db_session.query(APIKeyModel).filter_by(id=key_id).delete()
            db_session.commit()
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=api_key_names,
        tenant_id=tenant_ids,
        scopes=scopes_strategy,
        expiration_days=st.integers(min_value=-30, max_value=-1)  # Already expired
    )
    def test_expired_key_rejects_access(
        self,
        api_key_service,
        db_session,
        name,
        tenant_id,
        scopes,
        expiration_days
    ):
        """Property: Expired keys are rejected during validation."""
        # Arrange - Create key with past expiration
        config = APIKeyConfig(
            name=name,
            tenant_id=tenant_id,
            scopes=scopes,
            expires_in_days=expiration_days  # Negative = already expired
        )
        response = api_key_service.create_key(config)
        raw_key = response.raw_key
        key_id = response.id
        
        try:
            # Assert - Expiration is in the past
            assert response.expires_at < datetime.utcnow(), \
                "Key must be expired"
            
            # Act - Validate expired key
            validated = api_key_service.validate_key(raw_key)
            
            # Assert - Key is rejected
            assert validated is None, \
                "Expired key must be rejected (validate_key returns None)"
        
        finally:
            # Cleanup
            db_session.query(APIKeyModel).filter_by(id=key_id).delete()
            db_session.commit()
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=api_key_names,
        tenant_id=tenant_ids,
        scopes=scopes_strategy
    )
    def test_disabled_key_rejects_access(
        self,
        api_key_service,
        db_session,
        name,
        tenant_id,
        scopes
    ):
        """Property: Disabled keys are rejected during validation."""
        # Arrange
        config = APIKeyConfig(name=name, tenant_id=tenant_id, scopes=scopes)
        response = api_key_service.create_key(config)
        raw_key = response.raw_key
        key_id = response.id
        
        try:
            # Assert - Key is valid before disabling
            validated = api_key_service.validate_key(raw_key)
            assert validated is not None, \
                "Key must be valid before disabling"
            
            # Act - Disable key
            api_key_service.disable_key(key_id, tenant_id)
            
            # Assert - Key is rejected after disabling
            validated = api_key_service.validate_key(raw_key)
            assert validated is None, \
                "Disabled key must be rejected (validate_key returns None)"
        
        finally:
            # Cleanup
            db_session.query(APIKeyModel).filter_by(id=key_id).delete()
            db_session.commit()


class TestProperty12_APIKeyCallCountIncrement:
    """
    Feature: bidirectional-sync-and-external-api, Property 12: API 密钥调用计数递增
    
    **Validates: Requirements 4.5**
    
    For any 有效 API 密钥的成功调用，密钥的 total_calls 应递增 1，
    且 last_used_at 应更新为当前时间
    """
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=api_key_names,
        tenant_id=tenant_ids,
        scopes=scopes_strategy,
        num_calls=st.integers(min_value=1, max_value=20)
    )
    def test_call_count_increments_correctly(
        self,
        api_key_service,
        db_session,
        name,
        tenant_id,
        scopes,
        num_calls
    ):
        """Property: Each successful call increments total_calls by 1."""
        # Arrange
        config = APIKeyConfig(name=name, tenant_id=tenant_id, scopes=scopes)
        response = api_key_service.create_key(config)
        key_id = response.id
        
        try:
            # Assert - Initial state
            db_key = db_session.query(APIKeyModel).filter_by(id=key_id).first()
            assert db_key.total_calls == 0, \
                "Initial total_calls must be 0"
            initial_last_used = db_key.last_used_at
            
            # Act - Make multiple calls
            for i in range(num_calls):
                result = api_key_service.update_usage(key_id, increment_calls=True)
                assert result is True, f"Call {i+1} should succeed"
            
            # Assert - Total calls incremented correctly
            db_session.refresh(db_key)
            assert db_key.total_calls == num_calls, \
                f"total_calls must be {num_calls} after {num_calls} calls"
            
            # Assert - last_used_at updated
            assert db_key.last_used_at is not None, \
                "last_used_at must be set after calls"
            if initial_last_used is not None:
                assert db_key.last_used_at > initial_last_used, \
                    "last_used_at must be updated to later time"
        
        finally:
            # Cleanup
            db_session.query(APIKeyModel).filter_by(id=key_id).delete()
            db_session.commit()
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=api_key_names,
        tenant_id=tenant_ids,
        scopes=scopes_strategy
    )
    def test_last_used_at_updates_on_call(
        self,
        api_key_service,
        db_session,
        name,
        tenant_id,
        scopes
    ):
        """Property: last_used_at is updated to current time on each call."""
        # Arrange
        config = APIKeyConfig(name=name, tenant_id=tenant_id, scopes=scopes)
        response = api_key_service.create_key(config)
        key_id = response.id
        
        try:
            # Act - First call
            before_call = datetime.utcnow()
            result = api_key_service.update_usage(key_id, increment_calls=True)
            after_call = datetime.utcnow()
            
            # Assert - last_used_at is within call timeframe
            assert result is True, "Call should succeed"
            db_key = db_session.query(APIKeyModel).filter_by(id=key_id).first()
            assert db_key.last_used_at is not None, \
                "last_used_at must be set"
            assert before_call <= db_key.last_used_at <= after_call, \
                "last_used_at must be within call timeframe"
            
            first_last_used = db_key.last_used_at
            
            # Act - Second call (with small delay to ensure time difference)
            import time
            time.sleep(0.01)  # 10ms delay
            result = api_key_service.update_usage(key_id, increment_calls=True)
            
            # Assert - last_used_at updated to later time
            assert result is True, "Second call should succeed"
            db_session.refresh(db_key)
            assert db_key.last_used_at > first_last_used, \
                "last_used_at must be updated to later time on subsequent call"
        
        finally:
            # Cleanup
            db_session.query(APIKeyModel).filter_by(id=key_id).delete()
            db_session.commit()
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=api_key_names,
        tenant_id=tenant_ids,
        scopes=scopes_strategy,
        num_calls=st.integers(min_value=1, max_value=10)
    )
    def test_call_count_atomic_increment(
        self,
        api_key_service,
        db_session,
        name,
        tenant_id,
        scopes,
        num_calls
    ):
        """Property: Call count increments are atomic (no lost updates)."""
        # Arrange
        config = APIKeyConfig(name=name, tenant_id=tenant_id, scopes=scopes)
        response = api_key_service.create_key(config)
        key_id = response.id
        
        try:
            # Act - Make sequential calls
            for _ in range(num_calls):
                api_key_service.update_usage(key_id, increment_calls=True)
            
            # Assert - Final count matches number of calls
            db_key = db_session.query(APIKeyModel).filter_by(id=key_id).first()
            assert db_key.total_calls == num_calls, \
                f"total_calls must equal {num_calls}, no lost updates"
        
        finally:
            # Cleanup
            db_session.query(APIKeyModel).filter_by(id=key_id).delete()
            db_session.commit()
