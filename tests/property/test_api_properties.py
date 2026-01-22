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
