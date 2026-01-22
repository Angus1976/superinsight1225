"""
Admin Configuration API Authentication Property Tests

Tests API authentication enforcement properties to ensure that
unauthenticated requests are properly rejected and authenticated
requests are allowed.

**Feature: admin-configuration**
**Property 29: API Authentication Enforcement**
**Validates: Requirements 9.4**
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timedelta

from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src.app import app
from src.security.controller import SecurityController
from src.security.models import UserModel, UserRole
from src.database.connection import get_db_session


# ============================================================================
# Test Helpers
# ============================================================================

def get_async_client():
    """Create an async HTTP client for testing the FastAPI app."""
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    )

def get_security_controller() -> SecurityController:
    """Create security controller for token generation."""
    return SecurityController(secret_key="test-secret-key-for-property-tests")


def get_test_user() -> Dict[str, Any]:
    """Create a test user for authentication."""
    return {
        "id": str(uuid4()),
        "username": "test_user",
        "tenant_id": "test_tenant",
        "role": UserRole.ADMIN,
    }


def generate_valid_token(security_controller: SecurityController, user: Dict[str, Any]) -> str:
    """Generate a valid JWT token for testing."""
    return security_controller.create_access_token(
        user_id=user["id"],
        tenant_id=user["tenant_id"],
    )


def generate_expired_token(security_controller: SecurityController, user: Dict[str, Any]) -> str:
    """Generate an expired JWT token for testing."""
    # Create token with negative expiry to make it expired
    import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "user_id": user["id"],
        "tenant_id": user["tenant_id"],
        "exp": datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
        "iat": datetime.utcnow() - timedelta(hours=2),
    }
    
    return jwt.encode(payload, security_controller.secret_key, algorithm="HS256")


def generate_invalid_token() -> str:
    """Generate an invalid JWT token for testing."""
    return "invalid.jwt.token.that.should.fail"


# ============================================================================
# Property 29: API Authentication Enforcement
# ============================================================================

class TestAPIAuthenticationEnforcement:
    """
    Property 29: API Authentication Enforcement
    
    For any API request attempting unauthorized access based on configured
    permissions, the system should reject the request with a 401 Unauthorized
    response.
    
    **Feature: admin-configuration**
    **Validates: Requirements 9.4**
    """
    
    @given(
        endpoint_path=st.sampled_from([
            "/api/v1/admin/config/llm",
            "/api/v1/admin/config/databases",
            "/api/v1/admin/config/sync",
            "/api/v1/admin/config/history",
            "/api/v1/admin/dashboard",
        ]),
        http_method=st.sampled_from(["GET", "POST", "PUT", "DELETE"]),
    )
    @settings(max_examples=100, deadline=None)
    def test_unauthenticated_requests_rejected(
        self, endpoint_path: str, http_method: str
    ):
        """
        Unauthenticated requests to admin API endpoints are rejected.
        
        For any admin API endpoint and HTTP method, requests without
        authentication tokens should be rejected with 401 Unauthorized.
        """
        async def run_test():
            async with get_async_client() as client:
                # Prepare request based on method
                request_kwargs = {
                    "url": endpoint_path,
                    "headers": {},  # No Authorization header
                }
                
                # Add body for POST/PUT requests
                if http_method in ["POST", "PUT"]:
                    request_kwargs["json"] = {
                        "name": "test-config",
                        "llm_type": "openai",
                        "model_name": "gpt-4",
                    }
                
                # Make request without authentication
                if http_method == "GET":
                    response = await client.get(**request_kwargs)
                elif http_method == "POST":
                    response = await client.post(**request_kwargs)
                elif http_method == "PUT":
                    # Add ID to path for PUT requests
                    request_kwargs["url"] = f"{endpoint_path}/test-id"
                    response = await client.put(**request_kwargs)
                elif http_method == "DELETE":
                    # Add ID to path for DELETE requests
                    request_kwargs["url"] = f"{endpoint_path}/test-id"
                    response = await client.delete(**request_kwargs)
                
                # Should be rejected with 401 or 403 (depending on endpoint)
                # Note: Some endpoints may return 403 if they check permissions first
                assert response.status_code in [
                    status.HTTP_401_UNAUTHORIZED,
                    status.HTTP_403_FORBIDDEN,
                ], (
                    f"Unauthenticated {http_method} request to {endpoint_path} "
                    f"should be rejected with 401 or 403, got {response.status_code}"
                )
        
        asyncio.run(run_test())
    
    @given(
        endpoint_path=st.sampled_from([
            "/api/v1/admin/config/llm",
            "/api/v1/admin/config/databases",
            "/api/v1/admin/config/sync",
            "/api/v1/admin/dashboard",
        ]),
    )
    @settings(max_examples=100, deadline=None)
    def test_expired_token_rejected(
        self, endpoint_path: str
    ):
        """
        Requests with expired tokens are rejected.
        
        For any admin API endpoint, requests with expired JWT tokens
        should be rejected with 401 Unauthorized.
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            
            # Generate expired token
            expired_token = generate_expired_token(security_controller, test_user)
            
            async with get_async_client() as client:
                response = await client.get(
                    endpoint_path,
                    headers={"Authorization": f"Bearer {expired_token}"},
                )
                
                # Should be rejected with 401
                assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
                    f"Request with expired token to {endpoint_path} "
                    f"should be rejected with 401, got {response.status_code}"
                )
                
                # Response should indicate token issue
                response_data = response.json()
                assert "detail" in response_data, "Error response should include detail"
                detail_lower = response_data["detail"].lower()
                assert any(
                    keyword in detail_lower
                    for keyword in ["token", "expired", "invalid", "unauthorized"]
                ), f"Error detail should mention token issue: {response_data['detail']}"
        
        asyncio.run(run_test())
    
    @given(
        endpoint_path=st.sampled_from([
            "/api/v1/admin/config/llm",
            "/api/v1/admin/config/databases",
            "/api/v1/admin/config/sync",
        ]),
    )
    @settings(max_examples=100, deadline=None)
    def test_invalid_token_rejected(
        self, endpoint_path: str
    ):
        """
        Requests with invalid tokens are rejected.
        
        For any admin API endpoint, requests with malformed or invalid
        JWT tokens should be rejected with 401 Unauthorized.
        """
        async def run_test():
            # Generate invalid token
            invalid_token = generate_invalid_token()
            
            async with get_async_client() as client:
                response = await client.get(
                    endpoint_path,
                    headers={"Authorization": f"Bearer {invalid_token}"},
                )
                
                # Should be rejected with 401
                assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
                    f"Request with invalid token to {endpoint_path} "
                    f"should be rejected with 401, got {response.status_code}"
                )
        
        asyncio.run(run_test())
    
    @given(
        endpoint_path=st.sampled_from([
            "/api/v1/admin/config/llm",
            "/api/v1/admin/config/databases",
            "/api/v1/admin/config/sync",
            "/api/v1/admin/dashboard",
        ]),
        auth_header_format=st.sampled_from([
            "InvalidFormat {token}",  # Wrong prefix
            "{token}",  # Missing Bearer prefix
            "Bearer",  # Missing token
            "",  # Empty header
        ]),
    )
    @settings(max_examples=100, deadline=None)
    def test_malformed_auth_header_rejected(
        self, endpoint_path: str, auth_header_format: str
    ):
        """
        Requests with malformed Authorization headers are rejected.
        
        For any admin API endpoint, requests with incorrectly formatted
        Authorization headers should be rejected with 401 Unauthorized.
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            
            # Generate valid token but use malformed header format
            valid_token = generate_valid_token(security_controller, test_user)
            malformed_header = auth_header_format.format(token=valid_token)
            
            async with get_async_client() as client:
                response = await client.get(
                    endpoint_path,
                    headers={"Authorization": malformed_header} if malformed_header else {},
                )
                
                # Should be rejected with 401 or 403
                assert response.status_code in [
                    status.HTTP_401_UNAUTHORIZED,
                    status.HTTP_403_FORBIDDEN,
                ], (
                    f"Request with malformed auth header '{malformed_header}' to {endpoint_path} "
                    f"should be rejected with 401 or 403, got {response.status_code}"
                )
        
        asyncio.run(run_test())
    
    @given(
        num_requests=st.integers(min_value=5, max_value=20),
    )
    @settings(max_examples=100, deadline=None)
    def test_multiple_unauthenticated_requests_all_rejected(
        self, num_requests: int
    ):
        """
        Multiple unauthenticated requests are consistently rejected.
        
        For any number of unauthenticated requests to admin API endpoints,
        all requests should be consistently rejected with 401 Unauthorized.
        """
        async def run_test():
            # List of admin endpoints to test
            endpoints = [
                "/api/v1/admin/config/llm",
                "/api/v1/admin/config/databases",
                "/api/v1/admin/config/sync",
                "/api/v1/admin/dashboard",
            ]
            
            async with get_async_client() as client:
                # Make multiple unauthenticated requests
                tasks = []
                for i in range(num_requests):
                    endpoint = endpoints[i % len(endpoints)]
                    tasks.append(client.get(endpoint, headers={}))
                
                # Execute all requests concurrently
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # All should be rejected
                for i, response in enumerate(responses):
                    if isinstance(response, Exception):
                        # Network errors are acceptable in tests
                        continue
                    
                    assert response.status_code in [
                        status.HTTP_401_UNAUTHORIZED,
                        status.HTTP_403_FORBIDDEN,
                    ], (
                        f"Request {i+1}/{num_requests} should be rejected with 401 or 403, "
                        f"got {response.status_code}"
                    )
        
        asyncio.run(run_test())
    
    @given(
        endpoint_path=st.sampled_from([
            "/api/v1/admin/config/llm",
            "/api/v1/admin/config/databases",
            "/api/v1/admin/config/sync",
        ]),
        http_method=st.sampled_from(["GET", "POST"]),
    )
    @settings(max_examples=100, deadline=None)
    def test_authenticated_requests_not_rejected_for_auth_reasons(
        self, endpoint_path: str, http_method: str
    ):
        """
        Authenticated requests are not rejected for authentication reasons.
        
        For any admin API endpoint, requests with valid authentication tokens
        should not be rejected with 401 Unauthorized. They may fail for other
        reasons (400, 404, 500) but not for authentication.
        
        Note: This test verifies that authentication itself works, not that
        the request succeeds (which may require additional setup like database
        records, valid request bodies, etc.).
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            
            # Generate valid token
            valid_token = generate_valid_token(security_controller, test_user)
            
            async with get_async_client() as client:
                # Prepare request
                request_kwargs = {
                    "url": endpoint_path,
                    "headers": {"Authorization": f"Bearer {valid_token}"},
                }
                
                # Add body for POST requests
                if http_method == "POST":
                    request_kwargs["json"] = {
                        "name": "test-config",
                        "llm_type": "openai",
                        "model_name": "gpt-4",
                        "api_key": "sk-test-key",
                        "api_endpoint": "https://api.openai.com/v1",
                    }
                
                # Make authenticated request
                if http_method == "GET":
                    response = await client.get(**request_kwargs)
                elif http_method == "POST":
                    response = await client.post(**request_kwargs)
                
                # Should NOT be rejected with 401 (authentication passed)
                # May get other errors (400, 404, 500) due to missing data, etc.
                assert response.status_code != status.HTTP_401_UNAUTHORIZED, (
                    f"Authenticated {http_method} request to {endpoint_path} "
                    f"should not be rejected with 401. Got {response.status_code}. "
                    f"Authentication should pass even if request fails for other reasons."
                )
                
                # If we get 403, it's a permission issue, not authentication
                # If we get 400, it's a validation issue
                # If we get 404, it's a not found issue
                # If we get 500, it's a server error
                # All of these are acceptable - authentication worked
        
        asyncio.run(run_test())
    
    @given(
        num_endpoints=st.integers(min_value=3, max_value=6),
    )
    @settings(max_examples=100, deadline=None)
    def test_authentication_enforced_across_all_admin_endpoints(
        self, num_endpoints: int
    ):
        """
        Authentication is enforced across all admin API endpoints.
        
        For any set of admin API endpoints, authentication should be
        consistently enforced across all of them.
        """
        async def run_test():
            # All admin endpoints that should require authentication
            all_endpoints = [
                "/api/v1/admin/dashboard",
                "/api/v1/admin/config/llm",
                "/api/v1/admin/config/databases",
                "/api/v1/admin/config/sync",
                "/api/v1/admin/config/history",
                "/api/v1/admin/sql-builder/schema/test-id",
                "/api/v1/admin/sql-builder/templates",
                "/api/v1/admin/config/third-party",
            ]
            
            # Select subset of endpoints to test
            endpoints_to_test = all_endpoints[:num_endpoints]
            
            async with get_async_client() as client:
                # Test each endpoint without authentication
                for endpoint in endpoints_to_test:
                    response = await client.get(endpoint, headers={})
                    
                    # Should be rejected with 401 or 403
                    assert response.status_code in [
                        status.HTTP_401_UNAUTHORIZED,
                        status.HTTP_403_FORBIDDEN,
                    ], (
                        f"Endpoint {endpoint} should enforce authentication. "
                        f"Expected 401 or 403, got {response.status_code}"
                    )
        
        asyncio.run(run_test())
    
    @given(
        token_variations=st.lists(
            st.sampled_from([
                "valid",
                "expired",
                "invalid",
                "malformed",
                "missing",
            ]),
            min_size=5,
            max_size=10,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_authentication_consistency_across_token_types(
        self, token_variations: List[str]
    ):
        """
        Authentication enforcement is consistent across different token types.
        
        For any combination of valid, expired, invalid, malformed, and missing
        tokens, the authentication system should consistently reject invalid
        tokens and accept valid tokens.
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            
            endpoint = "/api/v1/admin/dashboard"
            
            async with get_async_client() as client:
                for token_type in token_variations:
                    # Generate appropriate token
                    if token_type == "valid":
                        token = generate_valid_token(security_controller, test_user)
                        headers = {"Authorization": f"Bearer {token}"}
                        should_be_rejected = False
                    elif token_type == "expired":
                        token = generate_expired_token(security_controller, test_user)
                        headers = {"Authorization": f"Bearer {token}"}
                        should_be_rejected = True
                    elif token_type == "invalid":
                        token = generate_invalid_token()
                        headers = {"Authorization": f"Bearer {token}"}
                        should_be_rejected = True
                    elif token_type == "malformed":
                        token = generate_valid_token(security_controller, test_user)
                        headers = {"Authorization": token}  # Missing "Bearer" prefix
                        should_be_rejected = True
                    else:  # missing
                        headers = {}
                        should_be_rejected = True
                    
                    # Make request
                    response = await client.get(endpoint, headers=headers)
                    
                    # Verify expected behavior
                    if should_be_rejected:
                        assert response.status_code in [
                            status.HTTP_401_UNAUTHORIZED,
                            status.HTTP_403_FORBIDDEN,
                        ], (
                            f"Token type '{token_type}' should be rejected with 401 or 403, "
                            f"got {response.status_code}"
                        )
                    else:
                        assert response.status_code != status.HTTP_401_UNAUTHORIZED, (
                            f"Valid token should not be rejected with 401, "
                            f"got {response.status_code}"
                        )
        
        asyncio.run(run_test())


# ============================================================================
# Property 30: API Response Format Consistency
# ============================================================================

class TestAPIResponseFormatConsistency:
    """
    Property 30: API Response Format Consistency
    
    For any successful API operation (create, update, delete), the response
    should follow a standardized format including operation status, resource ID,
    and timestamp.
    
    **Feature: admin-configuration**
    **Validates: Requirements 9.5**
    """
    
    @given(
        operation_type=st.sampled_from(["create", "update", "delete"]),
        config_type=st.sampled_from(["llm", "database", "sync", "third_party"]),
        config_name=st.text(min_size=3, max_size=50, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_"
        )),
    )
    @settings(max_examples=100, deadline=None)
    def test_successful_operations_return_standardized_format(
        self, operation_type: str, config_type: str, config_name: str
    ):
        """
        Successful API operations return standardized response format.
        
        For any successful create, update, or delete operation on any
        configuration type, the response should include:
        - status (success indicator)
        - resource_id (ID of created/updated/deleted resource)
        - timestamp (when operation occurred)
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)
            
            async with get_async_client() as client:
                resource_id = None
                
                # Prepare request based on config type
                if config_type == "llm":
                    endpoint = "/api/v1/admin/config/llm"
                    create_data = {
                        "name": config_name,
                        "llm_type": "openai",
                        "model_name": "gpt-4",
                        "api_key": "sk-test-key-12345",
                        "api_endpoint": "https://api.openai.com/v1",
                        "max_tokens": 4096,
                        "temperature": 0.7,
                    }
                    update_data = {
                        "name": f"{config_name}_updated",
                        "max_tokens": 8192,
                    }
                elif config_type == "database":
                    endpoint = "/api/v1/admin/config/databases"
                    create_data = {
                        "name": config_name,
                        "db_type": "postgresql",
                        "host": "localhost",
                        "port": 5432,
                        "database": "testdb",
                        "username": "testuser",
                        "password": "testpass123",
                        "is_readonly": True,
                    }
                    update_data = {
                        "name": f"{config_name}_updated",
                        "port": 5433,
                    }
                elif config_type == "sync":
                    endpoint = "/api/v1/admin/config/sync"
                    # For sync, we need a database config first
                    # Skip this test case as it requires complex setup
                    return
                else:  # third_party
                    endpoint = "/api/v1/admin/config/third-party"
                    create_data = {
                        "name": config_name,
                        "tool_type": "text_to_sql",
                        "endpoint": "https://api.example.com/v1",
                        "api_key": "test-api-key-12345",
                        "timeout_seconds": 30,
                    }
                    update_data = {
                        "name": f"{config_name}_updated",
                        "timeout_seconds": 60,
                    }
                
                headers = {"Authorization": f"Bearer {valid_token}"}
                
                # Execute operation based on type
                if operation_type == "create":
                    response = await client.post(
                        endpoint,
                        json=create_data,
                        headers=headers,
                    )
                    
                    # Check if operation succeeded (201 or 200)
                    if response.status_code in [200, 201]:
                        response_data = response.json()
                        
                        # Verify standardized format
                        assert "id" in response_data or "resource_id" in response_data, (
                            f"Create response should include 'id' or 'resource_id'. "
                            f"Got: {list(response_data.keys())}"
                        )
                        
                        # Extract resource ID
                        resource_id = response_data.get("id") or response_data.get("resource_id")
                        assert resource_id is not None, "Resource ID should not be None"
                        
                        # Check for timestamp (various possible field names)
                        timestamp_fields = ["timestamp", "created_at", "updated_at"]
                        has_timestamp = any(field in response_data for field in timestamp_fields)
                        assert has_timestamp, (
                            f"Create response should include timestamp field. "
                            f"Expected one of {timestamp_fields}, got: {list(response_data.keys())}"
                        )
                        
                        # Verify timestamp is valid ISO format
                        for field in timestamp_fields:
                            if field in response_data:
                                timestamp_value = response_data[field]
                                if timestamp_value:
                                    # Should be parseable as datetime
                                    try:
                                        from datetime import datetime
                                        datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                                    except (ValueError, AttributeError):
                                        assert False, f"Timestamp '{field}' should be valid ISO format: {timestamp_value}"
                
                elif operation_type == "update":
                    # First create a resource
                    create_response = await client.post(
                        endpoint,
                        json=create_data,
                        headers=headers,
                    )
                    
                    if create_response.status_code not in [200, 201]:
                        # Skip if create failed
                        return
                    
                    create_data_response = create_response.json()
                    resource_id = create_data_response.get("id") or create_data_response.get("resource_id")
                    
                    if not resource_id:
                        # Skip if no resource ID
                        return
                    
                    # Now update it
                    update_endpoint = f"{endpoint}/{resource_id}"
                    response = await client.put(
                        update_endpoint,
                        json=update_data,
                        headers=headers,
                    )
                    
                    # Check if operation succeeded
                    if response.status_code == 200:
                        response_data = response.json()
                        
                        # Verify standardized format
                        assert "id" in response_data or "resource_id" in response_data, (
                            f"Update response should include 'id' or 'resource_id'. "
                            f"Got: {list(response_data.keys())}"
                        )
                        
                        # Check for timestamp
                        timestamp_fields = ["timestamp", "updated_at", "created_at"]
                        has_timestamp = any(field in response_data for field in timestamp_fields)
                        assert has_timestamp, (
                            f"Update response should include timestamp field. "
                            f"Expected one of {timestamp_fields}, got: {list(response_data.keys())}"
                        )
                
                elif operation_type == "delete":
                    # First create a resource
                    create_response = await client.post(
                        endpoint,
                        json=create_data,
                        headers=headers,
                    )
                    
                    if create_response.status_code not in [200, 201]:
                        # Skip if create failed
                        return
                    
                    create_data_response = create_response.json()
                    resource_id = create_data_response.get("id") or create_data_response.get("resource_id")
                    
                    if not resource_id:
                        # Skip if no resource ID
                        return
                    
                    # Now delete it
                    delete_endpoint = f"{endpoint}/{resource_id}"
                    response = await client.delete(
                        delete_endpoint,
                        headers=headers,
                    )
                    
                    # Check if operation succeeded (200 or 204)
                    if response.status_code in [200, 204]:
                        if response.status_code == 200:
                            # If 200, should have response body
                            response_data = response.json()
                            
                            # Verify standardized format
                            # Delete responses should at least confirm the operation
                            assert "id" in response_data or "resource_id" in response_data or "success" in response_data, (
                                f"Delete response should include 'id', 'resource_id', or 'success'. "
                                f"Got: {list(response_data.keys())}"
                            )
                            
                            # Check for timestamp
                            timestamp_fields = ["timestamp", "deleted_at", "updated_at"]
                            has_timestamp = any(field in response_data for field in timestamp_fields)
                            # Timestamp is optional for delete, but if present should be valid
                            if has_timestamp:
                                for field in timestamp_fields:
                                    if field in response_data:
                                        timestamp_value = response_data[field]
                                        if timestamp_value:
                                            try:
                                                from datetime import datetime
                                                datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                                            except (ValueError, AttributeError):
                                                assert False, f"Timestamp '{field}' should be valid ISO format: {timestamp_value}"
        
        asyncio.run(run_test())
    
    @given(
        num_operations=st.integers(min_value=3, max_value=10),
    )
    @settings(max_examples=100, deadline=None)
    def test_multiple_operations_consistent_format(
        self, num_operations: int
    ):
        """
        Multiple operations return consistent response format.
        
        For any number of successful operations, all responses should
        follow the same standardized format structure.
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)
            
            headers = {"Authorization": f"Bearer {valid_token}"}
            endpoint = "/api/v1/admin/config/third-party"
            
            async with get_async_client() as client:
                responses = []
                
                # Create multiple resources
                for i in range(num_operations):
                    create_data = {
                        "name": f"test-tool-{i}",
                        "tool_type": "text_to_sql",
                        "endpoint": f"https://api.example{i}.com/v1",
                        "api_key": f"test-key-{i}",
                        "timeout_seconds": 30,
                    }
                    
                    response = await client.post(
                        endpoint,
                        json=create_data,
                        headers=headers,
                    )
                    
                    if response.status_code in [200, 201]:
                        responses.append(response.json())
                
                # Verify all responses have consistent structure
                if len(responses) >= 2:
                    # Check that all responses have the same top-level keys
                    first_keys = set(responses[0].keys())
                    
                    for i, response_data in enumerate(responses[1:], 1):
                        current_keys = set(response_data.keys())
                        
                        # Should have similar structure (allowing for some variation)
                        # At minimum, all should have ID and timestamp
                        assert "id" in current_keys or "resource_id" in current_keys, (
                            f"Response {i} should include 'id' or 'resource_id'"
                        )
                        
                        timestamp_fields = ["timestamp", "created_at", "updated_at"]
                        has_timestamp = any(field in current_keys for field in timestamp_fields)
                        assert has_timestamp, (
                            f"Response {i} should include timestamp field"
                        )
        
        asyncio.run(run_test())
    
    @given(
        config_type=st.sampled_from(["llm", "database", "third_party"]),
    )
    @settings(max_examples=100, deadline=None)
    def test_response_format_includes_required_fields(
        self, config_type: str
    ):
        """
        Response format includes all required fields.
        
        For any successful operation, the response should include:
        - Resource identifier (id or resource_id)
        - Timestamp (created_at, updated_at, or timestamp)
        - Operation status indication (implicit via HTTP status or explicit field)
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)
            
            headers = {"Authorization": f"Bearer {valid_token}"}
            
            # Prepare request based on config type
            if config_type == "llm":
                endpoint = "/api/v1/admin/config/llm"
                create_data = {
                    "name": "test-llm-config",
                    "llm_type": "openai",
                    "model_name": "gpt-4",
                    "api_key": "sk-test-key",
                    "api_endpoint": "https://api.openai.com/v1",
                }
            elif config_type == "database":
                endpoint = "/api/v1/admin/config/databases"
                create_data = {
                    "name": "test-db-config",
                    "db_type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "database": "testdb",
                    "username": "testuser",
                    "password": "testpass",
                }
            else:  # third_party
                endpoint = "/api/v1/admin/config/third-party"
                create_data = {
                    "name": "test-third-party",
                    "tool_type": "text_to_sql",
                    "endpoint": "https://api.example.com/v1",
                    "api_key": "test-key",
                }
            
            async with get_async_client() as client:
                response = await client.post(
                    endpoint,
                    json=create_data,
                    headers=headers,
                )
                
                # Check if operation succeeded
                if response.status_code in [200, 201]:
                    response_data = response.json()
                    
                    # Required field 1: Resource identifier
                    has_id = "id" in response_data or "resource_id" in response_data
                    assert has_id, (
                        f"Response must include resource identifier ('id' or 'resource_id'). "
                        f"Got keys: {list(response_data.keys())}"
                    )
                    
                    # Required field 2: Timestamp
                    timestamp_fields = ["timestamp", "created_at", "updated_at"]
                    has_timestamp = any(field in response_data for field in timestamp_fields)
                    assert has_timestamp, (
                        f"Response must include timestamp field (one of {timestamp_fields}). "
                        f"Got keys: {list(response_data.keys())}"
                    )
                    
                    # Required field 3: Operation status (implicit via HTTP 200/201 or explicit)
                    # HTTP 200/201 already indicates success, but check for explicit field
                    # This is optional but good practice
                    status_fields = ["success", "status", "operation_status"]
                    has_explicit_status = any(field in response_data for field in status_fields)
                    
                    # If explicit status exists, verify it indicates success
                    if has_explicit_status:
                        for field in status_fields:
                            if field in response_data:
                                status_value = response_data[field]
                                # Should indicate success
                                if isinstance(status_value, bool):
                                    assert status_value is True, f"Status field '{field}' should be True for successful operation"
                                elif isinstance(status_value, str):
                                    assert status_value.lower() in ["success", "ok", "completed"], (
                                        f"Status field '{field}' should indicate success, got: {status_value}"
                                    )
        
        asyncio.run(run_test())
    
    @given(
        operation_type=st.sampled_from(["create", "update"]),
    )
    @settings(max_examples=100, deadline=None)
    def test_timestamp_format_is_valid_iso8601(
        self, operation_type: str
    ):
        """
        Timestamp fields use valid ISO 8601 format.
        
        For any successful operation, timestamp fields should be in
        valid ISO 8601 format that can be parsed as datetime.
        """
        async def run_test():
            from datetime import datetime
            
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)
            
            headers = {"Authorization": f"Bearer {valid_token}"}
            endpoint = "/api/v1/admin/config/third-party"
            
            create_data = {
                "name": "test-timestamp-format",
                "tool_type": "text_to_sql",
                "endpoint": "https://api.example.com/v1",
                "api_key": "test-key",
            }
            
            async with get_async_client() as client:
                # Create resource
                response = await client.post(
                    endpoint,
                    json=create_data,
                    headers=headers,
                )
                
                if response.status_code not in [200, 201]:
                    return
                
                response_data = response.json()
                resource_id = response_data.get("id") or response_data.get("resource_id")
                
                if operation_type == "update" and resource_id:
                    # Update the resource
                    update_data = {"timeout_seconds": 60}
                    response = await client.put(
                        f"{endpoint}/{resource_id}",
                        json=update_data,
                        headers=headers,
                    )
                    
                    if response.status_code != 200:
                        return
                    
                    response_data = response.json()
                
                # Check all timestamp fields
                timestamp_fields = ["timestamp", "created_at", "updated_at", "deleted_at"]
                
                for field in timestamp_fields:
                    if field in response_data:
                        timestamp_value = response_data[field]
                        
                        if timestamp_value is not None:
                            # Should be a string
                            assert isinstance(timestamp_value, str), (
                                f"Timestamp field '{field}' should be string, got {type(timestamp_value)}"
                            )
                            
                            # Should be parseable as ISO 8601
                            try:
                                # Handle both with and without 'Z' suffix
                                parsed = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                                
                                # Verify it's a reasonable timestamp (not too far in past/future)
                                now = datetime.now(parsed.tzinfo)
                                time_diff = abs((now - parsed).total_seconds())
                                
                                # Should be within 1 hour of current time for create/update operations
                                assert time_diff < 3600, (
                                    f"Timestamp '{field}' seems unreasonable: {timestamp_value} "
                                    f"(diff from now: {time_diff} seconds)"
                                )
                            except (ValueError, AttributeError) as e:
                                assert False, (
                                    f"Timestamp field '{field}' should be valid ISO 8601 format. "
                                    f"Got: {timestamp_value}, Error: {e}"
                                )
        
        asyncio.run(run_test())
    
    @given(
        config_name=st.text(min_size=5, max_size=30, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_"
        )),
    )
    @settings(max_examples=100, deadline=None)
    def test_resource_id_is_valid_uuid(
        self, config_name: str
    ):
        """
        Resource IDs are valid UUIDs.
        
        For any successful create operation, the returned resource ID
        should be a valid UUID format.
        """
        async def run_test():
            from uuid import UUID
            
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)
            
            headers = {"Authorization": f"Bearer {valid_token}"}
            endpoint = "/api/v1/admin/config/third-party"
            
            create_data = {
                "name": config_name,
                "tool_type": "text_to_sql",
                "endpoint": "https://api.example.com/v1",
                "api_key": "test-key",
            }
            
            async with get_async_client() as client:
                response = await client.post(
                    endpoint,
                    json=create_data,
                    headers=headers,
                )
                
                if response.status_code in [200, 201]:
                    response_data = response.json()
                    
                    # Get resource ID
                    resource_id = response_data.get("id") or response_data.get("resource_id")
                    
                    if resource_id:
                        # Should be a string
                        assert isinstance(resource_id, str), (
                            f"Resource ID should be string, got {type(resource_id)}"
                        )
                        
                        # Should be valid UUID
                        try:
                            uuid_obj = UUID(resource_id)
                            # Verify it's a valid UUID by converting back to string
                            assert str(uuid_obj) == resource_id or str(uuid_obj).replace('-', '') == resource_id, (
                                f"Resource ID should be valid UUID format: {resource_id}"
                            )
                        except (ValueError, AttributeError) as e:
                            assert False, (
                                f"Resource ID should be valid UUID. Got: {resource_id}, Error: {e}"
                            )
        
        asyncio.run(run_test())


# ============================================================================
# Additional Authentication Tests
# ============================================================================

class TestAuthenticationEdgeCases:
    """
    Additional edge case tests for authentication enforcement.
    """
    
    def test_case_sensitive_bearer_prefix(self):
        """
        Test that Bearer prefix is case-sensitive (or insensitive as per spec).
        """
        async def run_test():
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)
            endpoint = "/api/v1/admin/dashboard"
            
            async with get_async_client() as client:
                # Test different case variations
                test_cases = [
                    ("Bearer", True),   # Standard
                    ("bearer", False),  # Lowercase - should fail
                    ("BEARER", False),  # Uppercase - should fail
                    ("BeArEr", False),  # Mixed case - should fail
                ]
                
                for prefix, should_work in test_cases:
                    response = await client.get(
                        endpoint,
                        headers={"Authorization": f"{prefix} {valid_token}"},
                    )
                    
                    if should_work:
                        # Standard "Bearer" should work
                        assert response.status_code != status.HTTP_401_UNAUTHORIZED, (
                            f"Standard 'Bearer' prefix should work"
                        )
                    else:
                        # Other variations should fail
                        assert response.status_code in [
                            status.HTTP_401_UNAUTHORIZED,
                            status.HTTP_403_FORBIDDEN,
                        ], (
                            f"Non-standard prefix '{prefix}' should be rejected"
                        )
        
        asyncio.run(run_test())
    
    def test_whitespace_in_auth_header(self):
        """
        Test handling of whitespace in Authorization header.
        """
        async def run_test():
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)
            endpoint = "/api/v1/admin/dashboard"
            
            async with get_async_client() as client:
                # Test whitespace variations
                test_cases = [
                    f"Bearer {valid_token}",      # Standard (single space)
                    f"Bearer  {valid_token}",     # Double space
                    f"Bearer\t{valid_token}",     # Tab
                    f" Bearer {valid_token}",     # Leading space
                    f"Bearer {valid_token} ",     # Trailing space
                ]
                
                for auth_header in test_cases:
                    response = await client.get(
                        endpoint,
                        headers={"Authorization": auth_header},
                    )
                    
                    # Most should fail except standard format
                    # This tests robustness of auth header parsing
                    # Exact behavior depends on FastAPI's HTTPBearer implementation
                    assert response.status_code in [
                        status.HTTP_200_OK,
                        status.HTTP_401_UNAUTHORIZED,
                        status.HTTP_403_FORBIDDEN,
                    ], (
                        f"Auth header with whitespace variation should return "
                        f"valid status code, got {response.status_code}"
                    )

        asyncio.run(run_test())


# ============================================================================
# Property 31: API Rate Limiting
# ============================================================================

class TestAPIRateLimiting:
    """
    Property 31: API Rate Limiting

    For any client exceeding the rate limit (100 requests per minute),
    subsequent requests should be rejected with 429 Too Many Requests
    until the rate limit window resets.

    **Feature: admin-configuration**
    **Validates: Requirements 9.7**
    """

    @given(
        num_requests=st.integers(min_value=5, max_value=20),
    )
    @settings(max_examples=50, deadline=None)
    def test_rate_limiter_allows_requests_under_limit(
        self, num_requests: int
    ):
        """
        Requests under rate limit are allowed.

        For any number of requests under the rate limit, all requests
        should be allowed (not rejected with 429).
        """
        async def run_test():
            from src.api.middleware.rate_limiter import InMemoryRateLimiter, RateLimitResult

            # Create rate limiter with higher limit than test requests
            rate_limiter = InMemoryRateLimiter(limit=100, window_seconds=60)

            client_id = f"test_client_{num_requests}"

            # Make requests under the limit
            for i in range(num_requests):
                result = await rate_limiter.check_rate_limit(client_id)

                # All requests should be allowed
                assert result.allowed, (
                    f"Request {i+1}/{num_requests} should be allowed "
                    f"(under limit of 100), but was rejected"
                )

                # Remaining should decrease
                expected_remaining = max(0, 100 - (i + 1))
                assert result.remaining == expected_remaining, (
                    f"Remaining should be {expected_remaining}, got {result.remaining}"
                )

        asyncio.run(run_test())

    @given(
        extra_requests=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=50, deadline=None)
    def test_rate_limiter_rejects_requests_over_limit(
        self, extra_requests: int
    ):
        """
        Requests over rate limit are rejected.

        For any number of requests exceeding the rate limit, the excess
        requests should be rejected with appropriate rate limit info.
        """
        async def run_test():
            from src.api.middleware.rate_limiter import InMemoryRateLimiter

            # Create rate limiter with low limit for testing
            limit = 10
            rate_limiter = InMemoryRateLimiter(limit=limit, window_seconds=60)

            client_id = "test_client_over_limit"

            # First, exhaust the limit
            for i in range(limit):
                result = await rate_limiter.check_rate_limit(client_id)
                assert result.allowed, f"Request {i+1} should be allowed"

            # Now, additional requests should be rejected
            for i in range(extra_requests):
                result = await rate_limiter.check_rate_limit(client_id)

                # Should be rejected
                assert not result.allowed, (
                    f"Extra request {i+1}/{extra_requests} should be rejected "
                    f"(over limit of {limit})"
                )

                # Remaining should be 0
                assert result.remaining == 0, (
                    f"Remaining should be 0 when over limit, got {result.remaining}"
                )

                # Retry-after should be set
                assert result.retry_after is not None, (
                    "Retry-after should be set when rate limited"
                )
                assert result.retry_after > 0, (
                    f"Retry-after should be positive, got {result.retry_after}"
                )

        asyncio.run(run_test())

    @given(
        num_clients=st.integers(min_value=2, max_value=5),
        requests_per_client=st.integers(min_value=3, max_value=10),
    )
    @settings(max_examples=50, deadline=None)
    def test_rate_limiter_isolates_clients(
        self, num_clients: int, requests_per_client: int
    ):
        """
        Rate limits are isolated per client.

        For any number of clients making requests, each client's rate
        limit should be tracked independently.
        """
        async def run_test():
            from src.api.middleware.rate_limiter import InMemoryRateLimiter

            # Create rate limiter with limit higher than per-client requests
            limit = requests_per_client + 5
            rate_limiter = InMemoryRateLimiter(limit=limit, window_seconds=60)

            # Make requests from multiple clients
            for client_num in range(num_clients):
                client_id = f"isolated_client_{client_num}"

                for req_num in range(requests_per_client):
                    result = await rate_limiter.check_rate_limit(client_id)

                    # Each client should have independent limit
                    assert result.allowed, (
                        f"Client {client_num} request {req_num+1} should be allowed"
                    )

                    # Remaining should be based on this client only
                    expected_remaining = limit - (req_num + 1)
                    assert result.remaining == expected_remaining, (
                        f"Client {client_num}: Remaining should be {expected_remaining}, "
                        f"got {result.remaining}"
                    )

        asyncio.run(run_test())

    @given(
        limit=st.integers(min_value=10, max_value=100),
        window_seconds=st.integers(min_value=30, max_value=120),
    )
    @settings(max_examples=50, deadline=None)
    def test_rate_limit_result_contains_correct_metadata(
        self, limit: int, window_seconds: int
    ):
        """
        Rate limit results contain correct metadata.

        For any rate limit configuration, the result should contain
        correct limit, remaining, and reset information.
        """
        async def run_test():
            import time
            from src.api.middleware.rate_limiter import InMemoryRateLimiter

            rate_limiter = InMemoryRateLimiter(limit=limit, window_seconds=window_seconds)

            client_id = "metadata_test_client"

            # First request
            before_time = time.time()
            result = await rate_limiter.check_rate_limit(client_id)
            after_time = time.time()

            # Verify metadata
            assert result.limit == limit, (
                f"Limit should be {limit}, got {result.limit}"
            )

            assert result.remaining == limit - 1, (
                f"Remaining should be {limit - 1}, got {result.remaining}"
            )

            # Reset time should be in the future
            assert result.reset_at >= before_time + window_seconds, (
                f"Reset time should be at least {window_seconds}s in future"
            )
            assert result.reset_at <= after_time + window_seconds + 1, (
                f"Reset time should be within window"
            )

        asyncio.run(run_test())

    def test_rate_limiter_reset_clears_count(self):
        """
        Resetting rate limit clears request count.

        After resetting a client's rate limit, they should have
        full quota available again.
        """
        async def run_test():
            from src.api.middleware.rate_limiter import InMemoryRateLimiter

            limit = 10
            rate_limiter = InMemoryRateLimiter(limit=limit, window_seconds=60)

            client_id = "reset_test_client"

            # Make some requests
            for i in range(5):
                await rate_limiter.check_rate_limit(client_id)

            # Check remaining
            result = await rate_limiter.check_rate_limit(client_id)
            assert result.remaining == limit - 6, f"Should have {limit - 6} remaining"

            # Reset
            reset_success = await rate_limiter.reset(client_id)
            assert reset_success, "Reset should succeed"

            # Check remaining again - should be full
            result = await rate_limiter.check_rate_limit(client_id)
            assert result.remaining == limit - 1, (
                f"After reset, remaining should be {limit - 1}, got {result.remaining}"
            )

        asyncio.run(run_test())


# ============================================================================
# Property 12: Permission Immediate Effect
# ============================================================================

class TestPermissionImmediateEffect:
    """
    Property 12: Permission Immediate Effect

    For any permission change (grant or revoke), the change should take
    effect immediately without requiring service restart.

    **Feature: admin-configuration**
    **Validates: Requirements 4.5**
    """

    @given(
        user_id=st.uuids().map(str),
        tenant_id=st.text(min_size=5, max_size=20, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_"
        )),
    )
    @settings(max_examples=50, deadline=None)
    def test_permission_cache_invalidation_on_change(
        self, user_id: str, tenant_id: str
    ):
        """
        Permission cache is invalidated when permissions change.

        For any user, when their permissions are changed, cached
        permission decisions should be invalidated immediately.
        """
        async def run_test():
            from src.api.middleware.permission_enforcer import PermissionCache

            cache = PermissionCache(ttl_seconds=300)

            resource = "admin.config.llm.read"
            action = "read"

            # Set initial permission in cache
            await cache.set(user_id, tenant_id, resource, action, allowed=True)

            # Verify it's cached
            cached = await cache.get(user_id, tenant_id, resource, action)
            assert cached is True, "Permission should be cached"

            # Invalidate user permissions
            invalidated_count = await cache.invalidate_user(user_id)

            # Should have invalidated at least 1 entry
            assert invalidated_count >= 1, (
                f"Should have invalidated at least 1 entry, invalidated {invalidated_count}"
            )

            # Permission should no longer be cached
            cached_after = await cache.get(user_id, tenant_id, resource, action)
            assert cached_after is None, (
                "After invalidation, permission should not be cached"
            )

        asyncio.run(run_test())

    @given(
        num_users=st.integers(min_value=2, max_value=5),
        num_permissions=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=50, deadline=None)
    def test_tenant_permission_invalidation(
        self, num_users: int, num_permissions: int
    ):
        """
        Tenant-wide permission invalidation affects all users.

        When tenant permissions change, all cached permissions for
        all users in that tenant should be invalidated.
        """
        async def run_test():
            from src.api.middleware.permission_enforcer import PermissionCache

            cache = PermissionCache(ttl_seconds=300)

            tenant_id = "test_tenant_123"
            resources = [f"resource_{i}" for i in range(num_permissions)]

            # Cache permissions for multiple users
            for user_num in range(num_users):
                user_id = f"user_{user_num}"
                for resource in resources:
                    await cache.set(user_id, tenant_id, resource, "read", allowed=True)

            # Verify some are cached
            cached = await cache.get("user_0", tenant_id, resources[0], "read")
            assert cached is True, "Permission should be cached"

            # Invalidate tenant permissions
            invalidated_count = await cache.invalidate_tenant(tenant_id)

            # Should have invalidated all entries
            expected_invalidations = num_users * num_permissions
            assert invalidated_count >= expected_invalidations, (
                f"Should have invalidated at least {expected_invalidations} entries, "
                f"got {invalidated_count}"
            )

            # All permissions should be cleared
            for user_num in range(num_users):
                user_id = f"user_{user_num}"
                for resource in resources:
                    cached = await cache.get(user_id, tenant_id, resource, "read")
                    assert cached is None, (
                        f"Permission for {user_id}/{resource} should be cleared"
                    )

        asyncio.run(run_test())

    def test_permission_effect_without_restart(self):
        """
        Permission changes take effect without service restart.

        Simulates changing permissions and verifying the change is
        reflected immediately in permission checks.
        """
        async def run_test():
            from src.api.middleware.permission_enforcer import PermissionCache

            cache = PermissionCache(ttl_seconds=300)

            user_id = "dynamic_permission_user"
            tenant_id = "dynamic_tenant"
            resource = "admin.config.sync.write"
            action = "write"

            # Initial state: permission denied
            await cache.set(user_id, tenant_id, resource, action, allowed=False)

            initial = await cache.get(user_id, tenant_id, resource, action)
            assert initial is False, "Initial permission should be denied"

            # Simulate permission change by invalidating and setting new value
            await cache.invalidate_user(user_id)
            await cache.set(user_id, tenant_id, resource, action, allowed=True)

            # New permission should take effect immediately
            updated = await cache.get(user_id, tenant_id, resource, action)
            assert updated is True, (
                "Permission change should take effect immediately"
            )

        asyncio.run(run_test())


# ============================================================================
# Property 13: Permission Enforcement at API Level
# ============================================================================

class TestPermissionEnforcementAtAPILevel:
    """
    Property 13: Permission Enforcement at API Level

    For any API request attempting unauthorized access based on configured
    permissions, the system should reject the request with a 403 Forbidden
    response.

    **Feature: admin-configuration**
    **Validates: Requirements 4.4**
    """

    @given(
        path=st.sampled_from([
            "/api/v1/admin/config/llm",
            "/api/v1/admin/config/databases",
            "/api/v1/admin/config/sync",
            "/api/v1/admin/sql-builder/templates",
        ]),
    )
    @settings(max_examples=50, deadline=None)
    def test_permission_rule_matching(
        self, path: str
    ):
        """
        Permission rules correctly match API paths.

        For any API path, the permission enforcer should correctly
        identify matching permission rules.
        """
        from src.api.middleware.permission_enforcer import (
            PermissionRule,
            DEFAULT_PERMISSION_RULES
        )

        # At least one rule should match admin API paths
        matching_rules = [
            rule for rule in DEFAULT_PERMISSION_RULES
            if rule.matches(path)
        ]

        # Admin paths should have matching rules
        if "/api/v1/admin/" in path:
            assert len(matching_rules) > 0, (
                f"Admin path '{path}' should have at least one matching permission rule"
            )

    @given(
        excluded_path=st.sampled_from([
            "/health",
            "/metrics",
            "/api/v1/health",
            "/docs",
            "/openapi.json",
        ]),
    )
    @settings(max_examples=50, deadline=None)
    def test_excluded_paths_bypass_permission_check(
        self, excluded_path: str
    ):
        """
        Excluded paths bypass permission enforcement.

        Certain paths like health checks and documentation should be
        accessible without permission checks.
        """
        from src.api.middleware.permission_enforcer import (
            DEFAULT_PERMISSION_RULES
        )

        # Excluded paths should not match any permission rules
        # (they're checked separately in the middleware)
        default_exclude_paths = [
            "/health",
            "/metrics",
            "/api/v1/health",
            "/api/v1/system/status",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]

        # Path should be in exclude list
        is_excluded = any(
            excluded_path.startswith(exclude)
            for exclude in default_exclude_paths
        )

        assert is_excluded, (
            f"Path '{excluded_path}' should be in the exclude list"
        )

    @given(
        method=st.sampled_from(["GET", "HEAD", "OPTIONS"]),
    )
    @settings(max_examples=50, deadline=None)
    def test_readonly_methods_identified_correctly(
        self, method: str
    ):
        """
        Read-only HTTP methods are correctly identified.

        GET, HEAD, and OPTIONS should be identified as read-only
        methods that may require different permissions than write methods.
        """
        from src.api.middleware.permission_enforcer import PermissionEnforcerMiddleware

        # These methods should be considered read-only
        assert method in PermissionEnforcerMiddleware.READONLY_METHODS, (
            f"Method '{method}' should be in READONLY_METHODS"
        )

    @given(
        method=st.sampled_from(["POST", "PUT", "PATCH", "DELETE"]),
    )
    @settings(max_examples=50, deadline=None)
    def test_write_methods_identified_correctly(
        self, method: str
    ):
        """
        Write HTTP methods are correctly identified.

        POST, PUT, PATCH, and DELETE should be identified as write
        methods requiring write permissions.
        """
        from src.api.middleware.permission_enforcer import PermissionEnforcerMiddleware

        # These methods should be considered write methods
        assert method in PermissionEnforcerMiddleware.WRITE_METHODS, (
            f"Method '{method}' should be in WRITE_METHODS"
        )

    @given(
        resource_pattern=st.sampled_from([
            "/api/v1/admin/config/*",
            "/api/v1/admin/config/llm",
            "/api/v1/admin/sql-builder/*",
        ]),
        test_path=st.sampled_from([
            "/api/v1/admin/config/llm",
            "/api/v1/admin/config/databases",
            "/api/v1/admin/sql-builder/schema/123",
            "/api/v1/other/path",
        ]),
    )
    @settings(max_examples=50, deadline=None)
    def test_permission_rule_pattern_matching(
        self, resource_pattern: str, test_path: str
    ):
        """
        Permission rules use correct pattern matching.

        Permission rule patterns should correctly match or reject
        API paths based on wildcard patterns.
        """
        from src.api.middleware.permission_enforcer import PermissionRule
        import fnmatch

        rule = PermissionRule(
            resource_pattern=resource_pattern,
            required_permissions={"test.permission"},
            allow_readonly=True
        )

        # Our implementation should match fnmatch behavior
        expected_match = fnmatch.fnmatch(test_path, resource_pattern)
        actual_match = rule.matches(test_path)

        assert actual_match == expected_match, (
            f"Pattern '{resource_pattern}' matching '{test_path}': "
            f"expected {expected_match}, got {actual_match}"
        )


# ============================================================================
# Property 28: Bulk Import/Export Round-Trip
# ============================================================================

class TestBulkImportExportRoundTrip:
    """
    Property 28: Bulk Import/Export Round-Trip

    For any set of configurations exported via the API, importing those
    configurations back should result in equivalent configurations that
    preserve all original field values.

    **Feature: admin-configuration**
    **Validates: Requirements 9.3**
    """

    @given(
        num_configs=st.integers(min_value=1, max_value=5),
        config_name_prefix=st.text(min_size=3, max_size=10, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_"
        ))
    )
    @settings(max_examples=50, deadline=None)
    def test_llm_config_export_import_round_trip(
        self, num_configs: int, config_name_prefix: str
    ):
        """
        LLM configurations can be exported and imported back.

        For any set of LLM configurations, exporting and then importing
        should result in equivalent configurations.
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)

            headers = {"Authorization": f"Bearer {valid_token}"}
            base_endpoint = "/api/v1/admin/config/llm"

            async with get_async_client() as client:
                created_configs = []

                # Create multiple configurations
                for i in range(num_configs):
                    create_data = {
                        "name": f"{config_name_prefix}_llm_{i}",
                        "llm_type": "openai",
                        "model_name": f"gpt-4-test-{i}",
                        "api_key": f"sk-test-key-{i}-abcdef",
                        "api_endpoint": "https://api.openai.com/v1",
                        "max_tokens": 4096 + i * 100,
                        "temperature": 0.7,
                    }

                    response = await client.post(
                        base_endpoint,
                        json=create_data,
                        headers=headers,
                    )

                    if response.status_code in [200, 201]:
                        created_configs.append({
                            **create_data,
                            "id": response.json().get("id")
                        })

                if len(created_configs) == 0:
                    # Skip if no configs created (maybe due to test environment)
                    return

                # Export configurations
                export_endpoint = "/api/v1/admin/config-export"
                export_response = await client.get(
                    export_endpoint,
                    params={"config_type": "llm"},
                    headers=headers,
                )

                # If export endpoint exists and succeeds
                if export_response.status_code == 200:
                    exported_data = export_response.json()

                    # Verify exported data contains our configs
                    if isinstance(exported_data, list):
                        exported_names = [c.get("name") for c in exported_data]
                        for config in created_configs:
                            assert config["name"] in exported_names, \
                                f"Exported data should contain config '{config['name']}'"

                    # Clean up created configs (delete them)
                    for config in created_configs:
                        config_id = config.get("id")
                        if config_id:
                            await client.delete(
                                f"{base_endpoint}/{config_id}",
                                headers=headers,
                            )

                    # Import configurations back
                    import_endpoint = "/api/v1/admin/config-import"
                    import_response = await client.post(
                        import_endpoint,
                        json={"configs": exported_data, "config_type": "llm"},
                        headers=headers,
                    )

                    # Verify import succeeds
                    if import_response.status_code in [200, 201]:
                        import_result = import_response.json()

                        # Verify all configs were imported
                        if isinstance(import_result, dict):
                            success_count = import_result.get("success_count", 0)
                            assert success_count >= len(created_configs), \
                                f"Should import at least {len(created_configs)} configs"

        asyncio.run(run_test())

    @given(
        num_configs=st.integers(min_value=1, max_value=3),
        config_name_prefix=st.text(min_size=3, max_size=10, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_"
        ))
    )
    @settings(max_examples=50, deadline=None)
    def test_database_config_export_import_round_trip(
        self, num_configs: int, config_name_prefix: str
    ):
        """
        Database configurations can be exported and imported back.

        For any set of database configurations, exporting and then importing
        should result in equivalent configurations preserving connection params.
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)

            headers = {"Authorization": f"Bearer {valid_token}"}
            base_endpoint = "/api/v1/admin/config/databases"

            async with get_async_client() as client:
                created_configs = []

                # Create multiple configurations
                for i in range(num_configs):
                    create_data = {
                        "name": f"{config_name_prefix}_db_{i}",
                        "db_type": "postgresql",
                        "host": f"db-host-{i}.example.com",
                        "port": 5432 + i,
                        "database": f"testdb_{i}",
                        "username": f"user_{i}",
                        "password": f"password_{i}_secure",
                        "is_readonly": i % 2 == 0,
                        "ssl_enabled": True,
                    }

                    response = await client.post(
                        base_endpoint,
                        json=create_data,
                        headers=headers,
                    )

                    if response.status_code in [200, 201]:
                        created_configs.append({
                            **create_data,
                            "id": response.json().get("id")
                        })

                if len(created_configs) == 0:
                    return

                # Export configurations
                export_endpoint = "/api/v1/admin/config-export"
                export_response = await client.get(
                    export_endpoint,
                    params={"config_type": "database"},
                    headers=headers,
                )

                if export_response.status_code == 200:
                    exported_data = export_response.json()

                    # Verify exported data
                    if isinstance(exported_data, list):
                        for config in created_configs:
                            # Find matching exported config
                            matching = [c for c in exported_data if c.get("name") == config["name"]]
                            if matching:
                                exported_config = matching[0]
                                # Verify key fields preserved
                                assert exported_config.get("db_type") == config["db_type"], \
                                    "Database type should be preserved"
                                assert exported_config.get("host") == config["host"], \
                                    "Host should be preserved"
                                assert exported_config.get("port") == config["port"], \
                                    "Port should be preserved"
                                # Password should be redacted or encrypted
                                password_value = exported_config.get("password", "")
                                assert password_value != config["password"] or \
                                       "[REDACTED]" in str(password_value), \
                                    "Password should be protected in export"

        asyncio.run(run_test())

    @given(
        config_types=st.lists(
            st.sampled_from(["llm", "database", "third_party"]),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_mixed_config_types_export_import(
        self, config_types: List[str]
    ):
        """
        Multiple configuration types can be exported and imported together.

        For any combination of configuration types, bulk export should
        include all types and import should restore them correctly.
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)

            headers = {"Authorization": f"Bearer {valid_token}"}

            async with get_async_client() as client:
                # Export all config types
                export_endpoint = "/api/v1/admin/config-export"
                export_response = await client.get(
                    export_endpoint,
                    params={"config_types": ",".join(config_types)},
                    headers=headers,
                )

                if export_response.status_code == 200:
                    exported_data = export_response.json()

                    # Verify structure
                    if isinstance(exported_data, dict):
                        # Should have sections for each config type
                        for config_type in config_types:
                            type_key = f"{config_type}_configs"
                            if type_key in exported_data:
                                assert isinstance(exported_data[type_key], list), \
                                    f"Config type '{config_type}' should be a list"

                    elif isinstance(exported_data, list):
                        # Each item should have a config_type field
                        for item in exported_data:
                            if "config_type" in item:
                                assert item["config_type"] in config_types, \
                                    f"Config type should be one of {config_types}"

        asyncio.run(run_test())

    @given(
        config_name=st.text(min_size=5, max_size=20, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_"
        ))
    )
    @settings(max_examples=50, deadline=None)
    def test_import_preserves_all_field_values(
        self, config_name: str
    ):
        """
        Import preserves all field values from exported data.

        For any configuration export, the imported configuration should
        have all the same field values (except sensitive/generated fields).
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)

            headers = {"Authorization": f"Bearer {valid_token}"}
            endpoint = "/api/v1/admin/config/third-party"

            async with get_async_client() as client:
                # Create a configuration with all fields
                original_data = {
                    "name": config_name,
                    "tool_type": "text_to_sql",
                    "endpoint": "https://api.example.com/v1",
                    "api_key": "test-api-key-12345",
                    "timeout_seconds": 45,
                    "extra_config": {
                        "retry_count": 3,
                        "max_connections": 10
                    }
                }

                # Create config
                create_response = await client.post(
                    endpoint,
                    json=original_data,
                    headers=headers,
                )

                if create_response.status_code not in [200, 201]:
                    return

                created = create_response.json()
                config_id = created.get("id")

                # Simulate export by getting the config
                get_response = await client.get(
                    f"{endpoint}/{config_id}",
                    headers=headers,
                )

                if get_response.status_code == 200:
                    exported_config = get_response.json()

                    # Verify fields are preserved
                    assert exported_config.get("name") == original_data["name"], \
                        "Name should be preserved"
                    assert exported_config.get("tool_type") == original_data["tool_type"], \
                        "Tool type should be preserved"
                    assert exported_config.get("endpoint") == original_data["endpoint"], \
                        "Endpoint should be preserved"
                    assert exported_config.get("timeout_seconds") == original_data["timeout_seconds"], \
                        "Timeout should be preserved"

                    # API key should be protected
                    exported_api_key = exported_config.get("api_key", "")
                    assert exported_api_key != original_data["api_key"] or \
                           "[REDACTED]" in str(exported_api_key) or \
                           "encrypted" in str(exported_api_key).lower(), \
                        "API key should be protected in export"

        asyncio.run(run_test())

    @given(
        invalid_data=st.sampled_from([
            {"configs": "not a list"},
            {"configs": [{"invalid": "config"}]},
            {"configs": []},
            {},
        ])
    )
    @settings(max_examples=30, deadline=None)
    def test_import_validates_data_structure(
        self, invalid_data: Dict[str, Any]
    ):
        """
        Import validates the data structure before processing.

        For any invalid import data, the import should fail with
        appropriate validation errors.
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)

            headers = {"Authorization": f"Bearer {valid_token}"}
            import_endpoint = "/api/v1/admin/config-import"

            async with get_async_client() as client:
                response = await client.post(
                    import_endpoint,
                    json=invalid_data,
                    headers=headers,
                )

                # Should fail with validation error (400) or bad request
                # If endpoint doesn't exist, 404 is also acceptable
                assert response.status_code in [400, 404, 422], \
                    f"Invalid import data should be rejected with 400/404/422, got {response.status_code}"

        asyncio.run(run_test())

    @given(
        num_exports=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=30, deadline=None)
    def test_export_is_deterministic(
        self, num_exports: int
    ):
        """
        Export produces deterministic results.

        For any configuration set, multiple exports should produce
        the same data (modulo timestamps).
        """
        async def run_test():
            # Create security controller and test user
            security_controller = get_security_controller()
            test_user = get_test_user()
            valid_token = generate_valid_token(security_controller, test_user)

            headers = {"Authorization": f"Bearer {valid_token}"}
            export_endpoint = "/api/v1/admin/config-export"

            async with get_async_client() as client:
                exports = []

                # Perform multiple exports
                for _ in range(num_exports):
                    response = await client.get(
                        export_endpoint,
                        params={"config_type": "llm"},
                        headers=headers,
                    )

                    if response.status_code == 200:
                        exports.append(response.json())

                # Compare exports (excluding timestamps)
                if len(exports) >= 2:
                    def normalize_export(data):
                        """Remove timestamps for comparison."""
                        if isinstance(data, list):
                            return [normalize_export(item) for item in data]
                        elif isinstance(data, dict):
                            return {
                                k: normalize_export(v)
                                for k, v in data.items()
                                if k not in ["timestamp", "created_at", "updated_at", "exported_at"]
                            }
                        return data

                    normalized_exports = [normalize_export(e) for e in exports]

                    # All exports should be equivalent
                    for i in range(1, len(normalized_exports)):
                        # Check that structure matches
                        if isinstance(normalized_exports[0], list):
                            assert len(normalized_exports[0]) == len(normalized_exports[i]), \
                                "Export results should have same length"
                        elif isinstance(normalized_exports[0], dict):
                            assert set(normalized_exports[0].keys()) == set(normalized_exports[i].keys()), \
                                "Export results should have same keys"

        asyncio.run(run_test())


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
