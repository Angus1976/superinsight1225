"""
Property-Based Tests for Token Expiration

Tests Property 36: Token Expiration

**Validates: Requirements 24.5**

For any authentication token, using an expired token should result in
authentication failure. JWT tokens have configurable expiration and
expired tokens are rejected.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from src.services.security_service import JWTManager, TokenPayload


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for user IDs (non-empty strings)
user_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=50,
)

# Strategy for roles lists
role_strategy = st.lists(
    st.sampled_from(["admin", "reviewer", "annotator", "viewer", "editor"]),
    min_size=0,
    max_size=4,
    unique=True,
)

# Strategy for positive expiry seconds (valid tokens)
positive_expiry_strategy = st.integers(min_value=60, max_value=86400)

# Strategy for negative expiry seconds (already-expired tokens)
negative_expiry_strategy = st.integers(min_value=-86400, max_value=-1)


# ============================================================================
# Property 36: Token Expiration
# **Validates: Requirements 24.5**
# ============================================================================


@pytest.mark.property
class TestTokenExpiration:
    """
    Property 36: Token Expiration

    Verifies that JWT tokens have configurable expiration, expired tokens
    are rejected, expires_at > issued_at for valid tokens, is_token_expired
    is consistent with validate_token, and decoded tokens preserve user data.
    """

    # ------------------------------------------------------------------ #
    # Sub-property 1: Valid tokens are accepted immediately after creation
    # ------------------------------------------------------------------ #

    @given(
        user_id=user_id_strategy,
        roles=role_strategy,
        expiry_seconds=positive_expiry_strategy,
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_valid_token_accepted_immediately(
        self, user_id: str, roles: list, expiry_seconds: int
    ):
        """
        For any token created with positive expiry_seconds,
        validate_token succeeds immediately after creation.

        **Validates: Requirements 24.5**
        """
        manager = JWTManager()
        token = manager.create_token(
            user_id=user_id, roles=roles, expiry_seconds=expiry_seconds
        )

        payload = manager.validate_token(token)

        assert isinstance(payload, TokenPayload), (
            f"Expected TokenPayload, got {type(payload)}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 2: Expired tokens are always rejected
    # ------------------------------------------------------------------ #

    @given(
        user_id=user_id_strategy,
        roles=role_strategy,
        expiry_seconds=negative_expiry_strategy,
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_expired_token_always_rejected(
        self, user_id: str, roles: list, expiry_seconds: int
    ):
        """
        For any token created with negative expiry_seconds (already expired),
        validate_token always raises ValueError.

        **Validates: Requirements 24.5**
        """
        manager = JWTManager()
        token = manager.create_token(
            user_id=user_id, roles=roles, expiry_seconds=expiry_seconds
        )

        with pytest.raises(ValueError):
            manager.validate_token(token)

    # ------------------------------------------------------------------ #
    # Sub-property 3: expires_at is always greater than issued_at
    # ------------------------------------------------------------------ #

    @given(
        user_id=user_id_strategy,
        roles=role_strategy,
        expiry_seconds=positive_expiry_strategy,
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_expires_at_greater_than_issued_at(
        self, user_id: str, roles: list, expiry_seconds: int
    ):
        """
        For any valid token, the expires_at field is always greater
        than issued_at.

        **Validates: Requirements 24.5**
        """
        manager = JWTManager()
        token = manager.create_token(
            user_id=user_id, roles=roles, expiry_seconds=expiry_seconds
        )

        payload = manager.validate_token(token)

        assert payload.expires_at > payload.issued_at, (
            f"expires_at ({payload.expires_at}) should be greater than "
            f"issued_at ({payload.issued_at})"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 4: is_token_expired consistent with validate_token
    # ------------------------------------------------------------------ #

    @given(
        user_id=user_id_strategy,
        roles=role_strategy,
        expiry_seconds=positive_expiry_strategy,
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_is_expired_consistent_with_validate(
        self, user_id: str, roles: list, expiry_seconds: int
    ):
        """
        For any token, is_token_expired returns consistent results
        with validate_token: if validate succeeds, is_expired is False.

        **Validates: Requirements 24.5**
        """
        manager = JWTManager()
        token = manager.create_token(
            user_id=user_id, roles=roles, expiry_seconds=expiry_seconds
        )

        is_expired = manager.is_token_expired(token)
        validate_succeeded = True
        try:
            manager.validate_token(token)
        except ValueError:
            validate_succeeded = False

        assert is_expired != validate_succeeded, (
            f"is_token_expired={is_expired} inconsistent with "
            f"validate_token success={validate_succeeded}"
        )

    # ------------------------------------------------------------------ #
    # Sub-property 5: Decoded token preserves user_id and roles
    # ------------------------------------------------------------------ #

    @given(
        user_id=user_id_strategy,
        roles=role_strategy,
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_decoded_token_preserves_user_data(
        self, user_id: str, roles: list,
    ):
        """
        For any user_id and roles, the decoded token always contains
        the same user_id and roles.

        **Validates: Requirements 24.5**
        """
        manager = JWTManager()
        token = manager.create_token(user_id=user_id, roles=roles)

        payload = manager.validate_token(token)

        assert payload.user_id == user_id, (
            f"user_id mismatch: expected {user_id!r}, got {payload.user_id!r}"
        )
        assert payload.roles == roles, (
            f"roles mismatch: expected {roles!r}, got {payload.roles!r}"
        )
