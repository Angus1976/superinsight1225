"""
Property-based tests for API Response and Permission Enforcement.

Tests validate API response pagination correctness and permission scope enforcement
using hypothesis for comprehensive coverage.

Feature: bidirectional-sync-and-external-api
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings, HealthCheck
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, HTTPException
from starlette.datastructures import Headers

from src.sync.gateway.external_data_router import (
    router,
    get_annotations,
    get_augmented_data,
    get_quality_reports,
    get_experiments,
    PaginatedResponse,
    PaginationMeta
)
from src.sync.models import APIKeyModel, APIKeyStatus


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating valid page numbers
page_strategy = st.integers(min_value=1, max_value=100)

# Strategy for generating valid page sizes
page_size_strategy = st.integers(min_value=1, max_value=1000)

# Strategy for generating tenant IDs
tenant_ids = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122),
    min_size=5,
    max_size=30
)

# Strategy for generating API endpoints
endpoint_strategy = st.sampled_from([
    '/api/v1/external/annotations',
    '/api/v1/external/augmented-data',
    '/api/v1/external/quality-reports',
    '/api/v1/external/experiments'
])

# Strategy for generating scopes with at least one True value
scopes_strategy = st.dictionaries(
    keys=st.sampled_from(['annotations', 'augmented_data', 'quality_reports', 'experiments']),
    values=st.booleans(),
    min_size=1,
    max_size=4
).filter(lambda d: any(d.values()))


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_api_key(tenant_id: str, scopes: dict) -> APIKeyModel:
    """Create a mock API key with specified scopes."""
    mock_api_key = Mock(spec=APIKeyModel)
    mock_api_key.id = uuid4()
    mock_api_key.tenant_id = tenant_id
    mock_api_key.name = "Test API Key"
    mock_api_key.scopes = scopes
    mock_api_key.rate_limit_per_minute = 1000
    mock_api_key.rate_limit_per_day = 100000
    mock_api_key.status = APIKeyStatus.ACTIVE
    return mock_api_key


def create_mock_request(tenant_id: str, api_key: APIKeyModel, endpoint: str) -> Request:
    """Create a mock FastAPI request with API key in state."""
    request = Mock(spec=Request)
    request.url.path = endpoint
    request.headers = Headers({"X-API-Key": "sk_test_key"})
    request.state = Mock()
    request.state.api_key = api_key
    request.state.tenant_id = tenant_id
    return request


# ============================================================================
# Property 14: API Response Pagination Correctness
# ============================================================================

class TestProperty14_APIPaginationCorrectness:
    """
    Feature: bidirectional-sync-and-external-api, Property 14: API 响应分页正确性
    
    **Validates: Requirements 5.3, 5.4**
    
    For any 带有 page 和 page_size 参数的 API 请求，响应应为 JSON 格式，
    包含 total、page、page_size、items 字段，且 items 长度不超过 page_size
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        tenant_id=tenant_ids,
        page=page_strategy,
        page_size=page_size_strategy,
        total_items=st.integers(min_value=0, max_value=500)
    )
    @pytest.mark.asyncio
    async def test_pagination_response_structure(
        self,
        tenant_id,
        page,
        page_size,
        total_items
    ):
        """Property: Paginated responses contain all required fields with correct structure."""
        # Arrange - Create mock API key with all scopes
        scopes = {
            'annotations': True,
            'augmented_data': True,
            'quality_reports': True,
            'experiments': True
        }
        api_key = create_mock_api_key(tenant_id, scopes)
        request = create_mock_request(tenant_id, api_key, '/api/v1/external/annotations')
        
        # Mock database session and query results
        mock_items = []
        for i in range(min(total_items, page_size)):
            mock_item = Mock()
            mock_item.id = uuid4()
            mock_item.name = f"Item {i}"
            mock_item.description = f"Description {i}"
            mock_item.annotation_type = Mock(value="text")
            mock_item.status = Mock(value="completed")
            mock_item.created_by = tenant_id
            mock_item.created_at = datetime.utcnow()
            mock_item.progress_total = 100
            mock_item.progress_completed = 100
            mock_item.annotations = {}
            mock_item.metadata_ = {}
            mock_items.append(mock_item)
        
        # Calculate expected pagination metadata
        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
        expected_items_count = min(page_size, max(0, total_items - (page - 1) * page_size))
        
        # Mock the database session and query
        with patch('src.sync.gateway.external_data_router.db_manager') as mock_db_manager:
            mock_session = Mock()
            mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
            
            # Mock the query execution
            mock_query_result = Mock()
            mock_query_result.scalars.return_value.all.return_value = mock_items[:expected_items_count]
            mock_session.execute.side_effect = [
                Mock(scalar=Mock(return_value=total_items)),  # Count query
                mock_query_result  # Items query
            ]
            
            # Act
            response = await get_annotations(
                request=request,
                page=page,
                page_size=page_size,
                sort_by=None,
                fields=None
            )
        
        # Assert - Response has correct structure
        assert isinstance(response, PaginatedResponse), \
            "Response must be a PaginatedResponse"
        
        # Assert - Response contains items field
        assert hasattr(response, 'items'), \
            "Response must contain 'items' field"
        assert isinstance(response.items, list), \
            "'items' must be a list"
        
        # Assert - Response contains meta field
        assert hasattr(response, 'meta'), \
            "Response must contain 'meta' field"
        assert isinstance(response.meta, PaginationMeta), \
            "'meta' must be a PaginationMeta object"
        
        # Assert - Meta contains all required fields
        assert hasattr(response.meta, 'total'), \
            "Meta must contain 'total' field"
        assert hasattr(response.meta, 'page'), \
            "Meta must contain 'page' field"
        assert hasattr(response.meta, 'page_size'), \
            "Meta must contain 'page_size' field"
        assert hasattr(response.meta, 'total_pages'), \
            "Meta must contain 'total_pages' field"
        
        # Assert - Meta values are correct
        assert response.meta.total == total_items, \
            f"Meta.total must equal {total_items}"
        assert response.meta.page == page, \
            f"Meta.page must equal {page}"
        assert response.meta.page_size == page_size, \
            f"Meta.page_size must equal {page_size}"
        assert response.meta.total_pages == total_pages, \
            f"Meta.total_pages must equal {total_pages}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        tenant_id=tenant_ids,
        page=page_strategy,
        page_size=page_size_strategy,
        total_items=st.integers(min_value=0, max_value=500)
    )
    @pytest.mark.asyncio
    async def test_items_length_not_exceeds_page_size(
        self,
        tenant_id,
        page,
        page_size,
        total_items
    ):
        """Property: Items length never exceeds page_size."""
        # Arrange
        scopes = {'annotations': True}
        api_key = create_mock_api_key(tenant_id, scopes)
        request = create_mock_request(tenant_id, api_key, '/api/v1/external/annotations')
        
        # Calculate expected items count
        offset = (page - 1) * page_size
        expected_items_count = min(page_size, max(0, total_items - offset))
        
        # Mock database items
        mock_items = []
        for i in range(expected_items_count):
            mock_item = Mock()
            mock_item.id = uuid4()
            mock_item.name = f"Item {i}"
            mock_item.description = f"Description {i}"
            mock_item.annotation_type = Mock(value="text")
            mock_item.status = Mock(value="completed")
            mock_item.created_by = tenant_id
            mock_item.created_at = datetime.utcnow()
            mock_item.progress_total = 100
            mock_item.progress_completed = 100
            mock_item.annotations = {}
            mock_item.metadata_ = {}
            mock_items.append(mock_item)
        
        # Mock the database session
        with patch('src.sync.gateway.external_data_router.db_manager') as mock_db_manager:
            mock_session = Mock()
            mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
            
            mock_query_result = Mock()
            mock_query_result.scalars.return_value.all.return_value = mock_items
            mock_session.execute.side_effect = [
                Mock(scalar=Mock(return_value=total_items)),
                mock_query_result
            ]
            
            # Act
            response = await get_annotations(
                request=request,
                page=page,
                page_size=page_size,
                sort_by=None,
                fields=None
            )
        
        # Assert - Items length does not exceed page_size
        assert len(response.items) <= page_size, \
            f"Items length ({len(response.items)}) must not exceed page_size ({page_size})"
        
        # Assert - Items length matches expected count
        assert len(response.items) == expected_items_count, \
            f"Items length must equal expected count {expected_items_count}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        page=page_strategy,
        page_size=page_size_strategy,
        endpoint=endpoint_strategy
    )
    @pytest.mark.asyncio
    async def test_all_endpoints_return_paginated_response(
        self,
        page,
        page_size,
        endpoint
    ):
        """Property: All external API endpoints return properly paginated responses."""
        # Use a valid UUID for tenant_id to avoid conversion errors
        tenant_id = str(uuid4())
        
        # Arrange - Map endpoints to scopes and handler functions
        endpoint_config = {
            '/api/v1/external/annotations': ('annotations', get_annotations),
            '/api/v1/external/augmented-data': ('augmented_data', get_augmented_data),
            '/api/v1/external/quality-reports': ('quality_reports', get_quality_reports),
            '/api/v1/external/experiments': ('experiments', get_experiments)
        }
        
        scope, handler = endpoint_config[endpoint]
        scopes = {scope: True}
        api_key = create_mock_api_key(tenant_id, scopes)
        request = create_mock_request(tenant_id, api_key, endpoint)
        
        # Mock empty result set for simplicity
        total_items = 0
        
        # Mock the database session
        with patch('src.sync.gateway.external_data_router.db_manager') as mock_db_manager:
            mock_session = Mock()
            mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
            
            mock_query_result = Mock()
            mock_query_result.scalars.return_value.all.return_value = []
            mock_session.execute.side_effect = [
                Mock(scalar=Mock(return_value=total_items)),
                mock_query_result
            ]
            
            # Act
            response = await handler(
                request=request,
                page=page,
                page_size=page_size,
                sort_by=None,
                fields=None
            )
        
        # Assert - Response is properly structured
        assert isinstance(response, PaginatedResponse), \
            f"Endpoint {endpoint} must return PaginatedResponse"
        assert hasattr(response, 'items'), \
            f"Endpoint {endpoint} response must have 'items'"
        assert hasattr(response, 'meta'), \
            f"Endpoint {endpoint} response must have 'meta'"
        assert isinstance(response.meta, PaginationMeta), \
            f"Endpoint {endpoint} meta must be PaginationMeta"
        assert len(response.items) <= page_size, \
            f"Endpoint {endpoint} items length must not exceed page_size"
    
    @settings(max_examples=100, deadline=None)
    @given(
        tenant_id=tenant_ids,
        page_size=page_size_strategy,
        total_items=st.integers(min_value=1, max_value=500)
    )
    @pytest.mark.asyncio
    async def test_pagination_consistency_across_pages(
        self,
        tenant_id,
        page_size,
        total_items
    ):
        """Property: Sum of items across all pages equals total items."""
        # Arrange
        scopes = {'annotations': True}
        api_key = create_mock_api_key(tenant_id, scopes)
        
        total_pages = (total_items + page_size - 1) // page_size
        total_fetched = 0
        
        # Act - Fetch all pages
        for page in range(1, total_pages + 1):
            request = create_mock_request(tenant_id, api_key, '/api/v1/external/annotations')
            
            # Calculate items for this page
            offset = (page - 1) * page_size
            items_on_page = min(page_size, total_items - offset)
            
            # Mock database items for this page
            mock_items = []
            for i in range(items_on_page):
                mock_item = Mock()
                mock_item.id = uuid4()
                mock_item.name = f"Item {offset + i}"
                mock_item.description = f"Description {offset + i}"
                mock_item.annotation_type = Mock(value="text")
                mock_item.status = Mock(value="completed")
                mock_item.created_by = tenant_id
                mock_item.created_at = datetime.utcnow()
                mock_item.progress_total = 100
                mock_item.progress_completed = 100
                mock_item.annotations = {}
                mock_item.metadata_ = {}
                mock_items.append(mock_item)
            
            with patch('src.sync.gateway.external_data_router.db_manager') as mock_db_manager:
                mock_session = Mock()
                mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
                
                mock_query_result = Mock()
                mock_query_result.scalars.return_value.all.return_value = mock_items
                mock_session.execute.side_effect = [
                    Mock(scalar=Mock(return_value=total_items)),
                    mock_query_result
                ]
                
                response = await get_annotations(
                    request=request,
                    page=page,
                    page_size=page_size,
                    sort_by=None,
                    fields=None
                )
            
            total_fetched += len(response.items)
        
        # Assert - Total fetched equals total items
        assert total_fetched == total_items, \
            f"Sum of items across all pages ({total_fetched}) must equal total items ({total_items})"


# ============================================================================
# Property 15: Permission Scope Enforcement
# ============================================================================

class TestProperty15_PermissionScopeEnforcement:
    """
    Feature: bidirectional-sync-and-external-api, Property 15: 权限范围强制执行
    
    **Validates: Requirements 5.5**
    
    For any 具有限定 scopes 的 API 密钥，请求超出其 scopes 的数据端点应返回 403 状态码
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        allowed_scopes=scopes_strategy
    )
    @pytest.mark.asyncio
    async def test_scope_permission_enforced(
        self,
        allowed_scopes
    ):
        """Property: API requests outside key's scopes return 403."""
        # Use a valid UUID for tenant_id to avoid conversion errors
        tenant_id = str(uuid4())
        
        # Arrange - Map scopes to endpoints
        scope_to_endpoint = {
            'annotations': ('/api/v1/external/annotations', get_annotations),
            'augmented_data': ('/api/v1/external/augmented-data', get_augmented_data),
            'quality_reports': ('/api/v1/external/quality-reports', get_quality_reports),
            'experiments': ('/api/v1/external/experiments', get_experiments)
        }
        
        # Create API key with limited scopes
        api_key = create_mock_api_key(tenant_id, allowed_scopes)
        
        # Test each endpoint
        for scope, (endpoint, handler) in scope_to_endpoint.items():
            request = create_mock_request(tenant_id, api_key, endpoint)
            
            if allowed_scopes.get(scope, False):
                # Scope is allowed - should succeed (or at least not return 403)
                # Mock successful database access
                with patch('src.sync.gateway.external_data_router.db_manager') as mock_db_manager:
                    mock_session = Mock()
                    mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
                    
                    mock_query_result = Mock()
                    mock_query_result.scalars.return_value.all.return_value = []
                    mock_session.execute.side_effect = [
                        Mock(scalar=Mock(return_value=0)),
                        mock_query_result
                    ]
                    
                    # Should not raise 403
                    response = await handler(
                        request=request,
                        page=1,
                        page_size=50,
                        sort_by=None,
                        fields=None
                    )
                    assert isinstance(response, PaginatedResponse), \
                        f"Allowed scope {scope} should return successful response"
            else:
                # Scope is not allowed - should return 403
                with pytest.raises(HTTPException) as exc_info:
                    await handler(
                        request=request,
                        page=1,
                        page_size=50,
                        sort_by=None,
                        fields=None
                    )
                
                assert exc_info.value.status_code == 403, \
                    f"Request to {endpoint} without {scope} scope must return 403"
                assert "INSUFFICIENT_SCOPE" in str(exc_info.value.detail), \
                    "Error detail must indicate insufficient scope"
    
    @settings(max_examples=100, deadline=None)
    @given(
        endpoint=endpoint_strategy
    )
    @pytest.mark.asyncio
    async def test_no_scopes_denies_all_access(
        self,
        endpoint
    ):
        """Property: API key with no scopes is denied access to all endpoints."""
        # Use a valid UUID for tenant_id to avoid conversion errors
        tenant_id = str(uuid4())
        
        # Arrange - Create API key with all scopes set to False
        scopes = {
            'annotations': False,
            'augmented_data': False,
            'quality_reports': False,
            'experiments': False
        }
        api_key = create_mock_api_key(tenant_id, scopes)
        request = create_mock_request(tenant_id, api_key, endpoint)
        
        # Map endpoints to handlers
        endpoint_handlers = {
            '/api/v1/external/annotations': get_annotations,
            '/api/v1/external/augmented-data': get_augmented_data,
            '/api/v1/external/quality-reports': get_quality_reports,
            '/api/v1/external/experiments': get_experiments
        }
        
        handler = endpoint_handlers[endpoint]
        
        # Act & Assert - Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await handler(
                request=request,
                page=1,
                page_size=50,
                sort_by=None,
                fields=None
            )
        
        assert exc_info.value.status_code == 403, \
            "API key with no scopes must be denied access (403)"
        assert "INSUFFICIENT_SCOPE" in str(exc_info.value.detail), \
            "Error must indicate insufficient scope"
    
    @pytest.mark.asyncio
    async def test_all_scopes_allows_all_access(
        self
    ):
        """Property: API key with all scopes can access all endpoints."""
        # Use a valid UUID for tenant_id to avoid conversion errors
        tenant_id = str(uuid4())
        
        # Arrange - Create API key with all scopes enabled
        scopes = {
            'annotations': True,
            'augmented_data': True,
            'quality_reports': True,
            'experiments': True
        }
        api_key = create_mock_api_key(tenant_id, scopes)
        
        # Test all endpoints
        endpoints = [
            ('/api/v1/external/annotations', get_annotations),
            ('/api/v1/external/augmented-data', get_augmented_data),
            ('/api/v1/external/quality-reports', get_quality_reports),
            ('/api/v1/external/experiments', get_experiments)
        ]
        
        for endpoint, handler in endpoints:
            request = create_mock_request(tenant_id, api_key, endpoint)
            
            # Mock successful database access
            with patch('src.sync.gateway.external_data_router.db_manager') as mock_db_manager:
                mock_session = Mock()
                mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
                
                mock_query_result = Mock()
                mock_query_result.scalars.return_value.all.return_value = []
                mock_session.execute.side_effect = [
                    Mock(scalar=Mock(return_value=0)),
                    mock_query_result
                ]
                
                # Act - Should not raise exception
                response = await handler(
                    request=request,
                    page=1,
                    page_size=50,
                    sort_by=None,
                    fields=None
                )
                
                # Assert - Successful response
                assert isinstance(response, PaginatedResponse), \
                    f"API key with all scopes should access {endpoint}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        allowed_scopes=scopes_strategy
    )
    @pytest.mark.asyncio
    async def test_403_error_includes_scope_information(
        self,
        allowed_scopes
    ):
        """Property: 403 errors include information about required and available scopes."""
        # Use a valid UUID for tenant_id to avoid conversion errors
        tenant_id = str(uuid4())
        
        # Arrange - Find a scope that is not allowed
        all_scopes = ['annotations', 'augmented_data', 'quality_reports', 'experiments']
        denied_scopes = [s for s in all_scopes if not allowed_scopes.get(s, False)]
        
        if not denied_scopes:
            # All scopes are allowed, skip this test
            return
        
        denied_scope = denied_scopes[0]
        
        # Map scope to endpoint
        scope_to_endpoint = {
            'annotations': ('/api/v1/external/annotations', get_annotations),
            'augmented_data': ('/api/v1/external/augmented-data', get_augmented_data),
            'quality_reports': ('/api/v1/external/quality-reports', get_quality_reports),
            'experiments': ('/api/v1/external/experiments', get_experiments)
        }
        
        endpoint, handler = scope_to_endpoint[denied_scope]
        api_key = create_mock_api_key(tenant_id, allowed_scopes)
        request = create_mock_request(tenant_id, api_key, endpoint)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await handler(
                request=request,
                page=1,
                page_size=50,
                sort_by=None,
                fields=None
            )
        
        # Assert - Error contains scope information
        assert exc_info.value.status_code == 403
        error_detail = exc_info.value.detail
        
        assert isinstance(error_detail, dict), \
            "Error detail must be a dictionary"
        assert "required_scope" in error_detail, \
            "Error must include required_scope"
        assert "available_scopes" in error_detail, \
            "Error must include available_scopes"
        assert error_detail["required_scope"] == denied_scope, \
            f"Required scope must be {denied_scope}"
        
        # Available scopes should only include enabled scopes
        available = error_detail["available_scopes"]
        assert isinstance(available, list), \
            "Available scopes must be a list"
        for scope in available:
            assert allowed_scopes.get(scope, False), \
                f"Available scopes should only include enabled scopes, found {scope}"
