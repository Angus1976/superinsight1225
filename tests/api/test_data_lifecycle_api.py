"""
Tests for Data Lifecycle API endpoints.

Tests the POST /api/data-lifecycle/transfer endpoint with various scenarios:
- Successful transfers to different target states
- Permission checks and approval workflows
- Internationalization (i18n) support
- Error handling and validation
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.api.data_lifecycle_api import (
    transfer_data,
    get_message,
    parse_accept_language
)
from src.models.data_transfer import (
    DataTransferRequest,
    DataAttributes,
    TransferRecord
)
from src.api.auth_simple import SimpleUser
from src.services.permission_service import UserRole


# Test fixtures
@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def admin_user():
    """Create admin user for testing."""
    user = Mock(spec=SimpleUser)
    user.id = "admin-123"
    user.is_superuser = True
    user.email = "admin@test.com"
    user.username = "admin"
    user.name = "Admin User"
    user.is_active = True
    return user


@pytest.fixture
def data_analyst_user():
    """Create data analyst user for testing."""
    user = Mock(spec=SimpleUser)
    user.id = "analyst-456"
    user.is_superuser = False
    user.email = "analyst@test.com"
    user.username = "analyst"
    user.name = "Analyst User"
    user.is_active = True
    return user


@pytest.fixture
def regular_user():
    """Create regular user for testing."""
    user = Mock(spec=SimpleUser)
    user.id = "user-789"
    user.is_superuser = False
    user.email = "user@test.com"
    user.username = "user"
    user.name = "Regular User"
    user.is_active = True
    return user


@pytest.fixture
def sample_transfer_request():
    """Create sample transfer request."""
    return DataTransferRequest(
        source_type="structuring",
        source_id="job-123",
        target_state="temp_stored",
        data_attributes=DataAttributes(
            category="test_category",
            tags=["test", "sample"],
            quality_score=0.9,
            description="Test transfer"
        ),
        records=[
            TransferRecord(
                id="record-1",
                content={"field1": "value1", "field2": "value2"},
                metadata={"source": "test"}
            ),
            TransferRecord(
                id="record-2",
                content={"field1": "value3", "field2": "value4"},
                metadata={"source": "test"}
            )
        ]
    )


# Test i18n helper functions
class TestI18nHelpers:
    """Test internationalization helper functions."""
    
    def test_parse_accept_language_english(self):
        """Test parsing English Accept-Language header."""
        assert parse_accept_language("en-US") == "en"
        assert parse_accept_language("en") == "en"
        assert parse_accept_language("en-GB,en;q=0.9") == "en"
    
    def test_parse_accept_language_chinese(self):
        """Test parsing Chinese Accept-Language header."""
        assert parse_accept_language("zh-CN") == "zh"
        assert parse_accept_language("zh") == "zh"
        assert parse_accept_language("zh-TW,zh;q=0.9") == "zh"
    
    def test_parse_accept_language_default(self):
        """Test default language when header is missing."""
        assert parse_accept_language(None) == "zh"
        assert parse_accept_language("") == "zh"
    
    def test_get_message_chinese(self):
        """Test getting Chinese messages."""
        msg = get_message("success", "zh", count=5, state="临时存储")
        assert "成功转存" in msg
        assert "5" in msg
        assert "临时存储" in msg
    
    def test_get_message_english(self):
        """Test getting English messages."""
        msg = get_message("success", "en", count=5, state="temporary storage")
        assert "Successfully transferred" in msg
        assert "5" in msg
        assert "temporary storage" in msg
    
    def test_get_message_nested_key(self):
        """Test getting nested message keys."""
        assert get_message("states.temp_stored", "zh") == "临时存储"
        assert get_message("states.temp_stored", "en") == "temporary storage"
        assert get_message("states.in_sample_library", "zh") == "样本库"
        assert get_message("states.in_sample_library", "en") == "sample library"


# Test successful transfers
class TestSuccessfulTransfers:
    """Test successful transfer scenarios."""
    
    @pytest.mark.asyncio
    async def test_transfer_to_temp_storage_admin(
        self,
        mock_db,
        admin_user,
        sample_transfer_request
    ):
        """Test admin user transferring to temporary storage."""
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            # Setup mock service
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(return_value={
                "success": True,
                "transferred_count": 2,
                "lifecycle_ids": ["id-1", "id-2"],
                "target_state": "temp_stored",
                "message": "Success",
                "navigation_url": "/data-lifecycle/temp-data"
            })
            
            # Execute transfer
            result = await transfer_data(
                request=sample_transfer_request,
                db=mock_db,
                current_user=admin_user,
                accept_language="zh-CN"
            )
            
            # Verify result
            assert result["success"] is True
            assert result["transferred_count"] == 2
            assert len(result["lifecycle_ids"]) == 2
            assert result["target_state"] == "temp_stored"
            assert "成功转存" in result["message"]
            
            # Verify service was called correctly
            mock_service.transfer.assert_called_once()
            call_args = mock_service.transfer.call_args
            assert call_args[0][0] == sample_transfer_request
            assert call_args[0][1].id == admin_user.id
            assert call_args[0][1].role == UserRole.ADMIN
    
    @pytest.mark.asyncio
    async def test_transfer_to_sample_library_admin(
        self,
        mock_db,
        admin_user,
        sample_transfer_request
    ):
        """Test admin user transferring to sample library."""
        sample_transfer_request.target_state = "in_sample_library"
        
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(return_value={
                "success": True,
                "transferred_count": 2,
                "lifecycle_ids": ["id-1", "id-2"],
                "target_state": "in_sample_library",
                "message": "Success",
                "navigation_url": "/data-lifecycle/sample-library"
            })
            
            result = await transfer_data(
                request=sample_transfer_request,
                db=mock_db,
                current_user=admin_user,
                accept_language="en-US"
            )
            
            assert result["success"] is True
            assert result["target_state"] == "in_sample_library"
            assert "Successfully transferred" in result["message"]
            assert "sample library" in result["message"]
    
    @pytest.mark.asyncio
    async def test_transfer_with_english_locale(
        self,
        mock_db,
        admin_user,
        sample_transfer_request
    ):
        """Test transfer with English locale."""
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(return_value={
                "success": True,
                "transferred_count": 2,
                "lifecycle_ids": ["id-1", "id-2"],
                "target_state": "temp_stored",
                "message": "Success",
                "navigation_url": "/data-lifecycle/temp-data"
            })
            
            result = await transfer_data(
                request=sample_transfer_request,
                db=mock_db,
                current_user=admin_user,
                accept_language="en-US"
            )
            
            assert "Successfully transferred" in result["message"]
            assert "temporary storage" in result["message"]


# Test approval workflow
class TestApprovalWorkflow:
    """Test approval workflow scenarios."""
    
    @pytest.mark.asyncio
    async def test_transfer_requires_approval(
        self,
        mock_db,
        data_analyst_user,
        sample_transfer_request
    ):
        """Test transfer that requires approval."""
        sample_transfer_request.target_state = "in_sample_library"
        
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(return_value={
                "success": True,
                "approval_required": True,
                "approval_id": "approval-123",
                "message": "Transfer request submitted for approval",
                "estimated_approval_time": "2-3 business days"
            })
            
            result = await transfer_data(
                request=sample_transfer_request,
                db=mock_db,
                current_user=data_analyst_user,
                accept_language="zh-CN"
            )
            
            assert result["success"] is True
            assert result["approval_required"] is True
            assert result["approval_id"] == "approval-123"
            assert "等待审批" in result["message"]
    
    @pytest.mark.asyncio
    async def test_approval_message_english(
        self,
        mock_db,
        data_analyst_user,
        sample_transfer_request
    ):
        """Test approval message in English."""
        sample_transfer_request.target_state = "in_sample_library"
        
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(return_value={
                "success": True,
                "approval_required": True,
                "approval_id": "approval-123",
                "message": "Transfer request submitted for approval",
                "estimated_approval_time": "2-3 business days"
            })
            
            result = await transfer_data(
                request=sample_transfer_request,
                db=mock_db,
                current_user=data_analyst_user,
                accept_language="en-US"
            )
            
            assert "submitted for approval" in result["message"]


# Test error handling
class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_invalid_source_error(
        self,
        mock_db,
        admin_user,
        sample_transfer_request
    ):
        """Test handling of invalid source error."""
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(
                side_effect=ValueError("Source not found")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await transfer_data(
                    request=sample_transfer_request,
                    db=mock_db,
                    current_user=admin_user,
                    accept_language="zh-CN"
                )
            
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["error_code"] == "INVALID_SOURCE"
            assert "源数据不存在" in exc_info.value.detail["message"]
    
    @pytest.mark.asyncio
    async def test_permission_denied_error(
        self,
        mock_db,
        regular_user,
        sample_transfer_request
    ):
        """Test handling of permission denied error."""
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(
                side_effect=PermissionError("No permission")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await transfer_data(
                    request=sample_transfer_request,
                    db=mock_db,
                    current_user=regular_user,
                    accept_language="en-US"
                )
            
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error_code"] == "PERMISSION_DENIED"
            assert "permission" in exc_info.value.detail["message"].lower()
    
    @pytest.mark.asyncio
    async def test_internal_server_error(
        self,
        mock_db,
        admin_user,
        sample_transfer_request
    ):
        """Test handling of internal server error."""
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await transfer_data(
                    request=sample_transfer_request,
                    db=mock_db,
                    current_user=admin_user,
                    accept_language="zh-CN"
                )
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail["error_code"] == "INTERNAL_ERROR"
            assert "内部服务器错误" in exc_info.value.detail["message"]


# Test user role mapping
class TestUserRoleMapping:
    """Test user role mapping to service layer."""
    
    @pytest.mark.asyncio
    async def test_superuser_maps_to_admin(
        self,
        mock_db,
        sample_transfer_request
    ):
        """Test superuser is correctly mapped to ADMIN role."""
        admin = Mock(spec=SimpleUser)
        admin.id = "admin-123"
        admin.is_superuser = True
        admin.email = "admin@test.com"
        admin.username = "admin"
        admin.name = "Admin"
        admin.is_active = True
        
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(return_value={
                "success": True,
                "transferred_count": 2,
                "lifecycle_ids": ["id-1", "id-2"],
                "target_state": "temp_stored",
                "message": "Success",
                "navigation_url": "/data-lifecycle/temp-data"
            })
            
            await transfer_data(
                request=sample_transfer_request,
                db=mock_db,
                current_user=admin,
                accept_language="zh-CN"
            )
            
            call_args = mock_service.transfer.call_args
            assert call_args[0][1].role == UserRole.ADMIN
    
    @pytest.mark.asyncio
    async def test_regular_user_maps_to_user_role(
        self,
        mock_db,
        sample_transfer_request
    ):
        """Test regular user is correctly mapped to USER role."""
        user = Mock(spec=SimpleUser)
        user.id = "user-123"
        user.is_superuser = False
        user.email = "user@test.com"
        user.username = "user"
        user.name = "User"
        user.is_active = True
        
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(return_value={
                "success": True,
                "transferred_count": 2,
                "lifecycle_ids": ["id-1", "id-2"],
                "target_state": "temp_stored",
                "message": "Success",
                "navigation_url": "/data-lifecycle/temp-data"
            })
            
            await transfer_data(
                request=sample_transfer_request,
                db=mock_db,
                current_user=user,
                accept_language="zh-CN"
            )
            
            call_args = mock_service.transfer.call_args
            assert call_args[0][1].role == UserRole.USER


# Test request validation
class TestRequestValidation:
    """Test request validation scenarios."""
    
    @pytest.mark.asyncio
    async def test_empty_records_list(
        self,
        mock_db,
        admin_user
    ):
        """Test validation fails with empty records list."""
        # This should be caught by Pydantic validation before reaching the endpoint
        with pytest.raises(Exception):
            DataTransferRequest(
                source_type="structuring",
                source_id="job-123",
                target_state="temp_stored",
                data_attributes=DataAttributes(
                    category="test",
                    tags=[],
                    quality_score=0.8
                ),
                records=[]  # Empty list should fail validation
            )
    
    @pytest.mark.asyncio
    async def test_invalid_quality_score(
        self,
        mock_db,
        admin_user
    ):
        """Test validation fails with invalid quality score."""
        with pytest.raises(Exception):
            DataTransferRequest(
                source_type="structuring",
                source_id="job-123",
                target_state="temp_stored",
                data_attributes=DataAttributes(
                    category="test",
                    tags=[],
                    quality_score=1.5  # Invalid: > 1.0
                ),
                records=[
                    TransferRecord(
                        id="record-1",
                        content={"field": "value"}
                    )
                ]
            )



# Test batch transfer endpoint
class TestBatchTransfer:
    """Test batch transfer endpoint scenarios."""
    
    @pytest.mark.asyncio
    async def test_batch_transfer_success_admin(
        self,
        mock_db,
        admin_user
    ):
        """Test successful batch transfer by admin user."""
        requests = [
            DataTransferRequest(
                source_type="structuring",
                source_id="job-1",
                target_state="temp_stored",
                data_attributes=DataAttributes(
                    category="category1",
                    tags=["tag1"],
                    quality_score=0.9
                ),
                records=[
                    TransferRecord(
                        id="record-1",
                        content={"field": "value1"}
                    )
                ]
            ),
            DataTransferRequest(
                source_type="augmentation",
                source_id="job-2",
                target_state="in_sample_library",
                data_attributes=DataAttributes(
                    category="category2",
                    tags=["tag2"],
                    quality_score=0.95
                ),
                records=[
                    TransferRecord(
                        id="record-2",
                        content={"field": "value2"}
                    )
                ]
            )
        ]
        
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(side_effect=[
                {
                    "success": True,
                    "transferred_count": 1,
                    "lifecycle_ids": ["id-1"],
                    "target_state": "temp_stored",
                    "message": "Success",
                    "navigation_url": "/data-lifecycle/temp-data"
                },
                {
                    "success": True,
                    "transferred_count": 1,
                    "lifecycle_ids": ["id-2"],
                    "target_state": "in_sample_library",
                    "message": "Success",
                    "navigation_url": "/data-lifecycle/sample-library"
                }
            ])
            
            from src.api.data_lifecycle_api import batch_transfer_data
            
            result = await batch_transfer_data(
                requests=requests,
                db=mock_db,
                current_user=admin_user,
                accept_language="zh-CN"
            )
            
            assert result["success"] is True
            assert result["total_transfers"] == 2
            assert result["successful_transfers"] == 2
            assert result["failed_transfers"] == 0
            assert len(result["results"]) == 2
            
            # Check first result
            assert result["results"][0]["success"] is True
            assert result["results"][0]["index"] == 0
            assert result["results"][0]["source_id"] == "job-1"
            assert "成功转存" in result["results"][0]["message"]
            
            # Check second result
            assert result["results"][1]["success"] is True
            assert result["results"][1]["index"] == 1
            assert result["results"][1]["source_id"] == "job-2"
    
    @pytest.mark.asyncio
    async def test_batch_transfer_partial_failure(
        self,
        mock_db,
        admin_user
    ):
        """Test batch transfer with some failures."""
        requests = [
            DataTransferRequest(
                source_type="structuring",
                source_id="job-1",
                target_state="temp_stored",
                data_attributes=DataAttributes(
                    category="category1",
                    tags=["tag1"],
                    quality_score=0.9
                ),
                records=[
                    TransferRecord(
                        id="record-1",
                        content={"field": "value1"}
                    )
                ]
            ),
            DataTransferRequest(
                source_type="augmentation",
                source_id="job-2",
                target_state="in_sample_library",
                data_attributes=DataAttributes(
                    category="category2",
                    tags=["tag2"],
                    quality_score=0.95
                ),
                records=[
                    TransferRecord(
                        id="record-2",
                        content={"field": "value2"}
                    )
                ]
            ),
            DataTransferRequest(
                source_type="sync",
                source_id="job-3",
                target_state="temp_stored",
                data_attributes=DataAttributes(
                    category="category3",
                    tags=["tag3"],
                    quality_score=0.85
                ),
                records=[
                    TransferRecord(
                        id="record-3",
                        content={"field": "value3"}
                    )
                ]
            )
        ]
        
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(side_effect=[
                {
                    "success": True,
                    "transferred_count": 1,
                    "lifecycle_ids": ["id-1"],
                    "target_state": "temp_stored",
                    "message": "Success",
                    "navigation_url": "/data-lifecycle/temp-data"
                },
                ValueError("Source not found"),
                {
                    "success": True,
                    "transferred_count": 1,
                    "lifecycle_ids": ["id-3"],
                    "target_state": "temp_stored",
                    "message": "Success",
                    "navigation_url": "/data-lifecycle/temp-data"
                }
            ])
            
            from src.api.data_lifecycle_api import batch_transfer_data
            
            result = await batch_transfer_data(
                requests=requests,
                db=mock_db,
                current_user=admin_user,
                accept_language="en-US"
            )
            
            assert result["success"] is True
            assert result["total_transfers"] == 3
            assert result["successful_transfers"] == 2
            assert result["failed_transfers"] == 1
            assert len(result["results"]) == 3
            
            # Check successful transfers
            assert result["results"][0]["success"] is True
            assert result["results"][2]["success"] is True
            
            # Check failed transfer
            assert result["results"][1]["success"] is False
            assert result["results"][1]["error_code"] == "INVALID_SOURCE"
            assert "not found" in result["results"][1]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_batch_transfer_permission_denied_non_admin(
        self,
        mock_db,
        regular_user
    ):
        """Test batch transfer denied for non-admin user."""
        requests = [
            DataTransferRequest(
                source_type="structuring",
                source_id="job-1",
                target_state="temp_stored",
                data_attributes=DataAttributes(
                    category="category1",
                    tags=["tag1"],
                    quality_score=0.9
                ),
                records=[
                    TransferRecord(
                        id="record-1",
                        content={"field": "value1"}
                    )
                ]
            )
        ]
        
        from src.api.data_lifecycle_api import batch_transfer_data
        
        with pytest.raises(HTTPException) as exc_info:
            await batch_transfer_data(
                requests=requests,
                db=mock_db,
                current_user=regular_user,
                accept_language="zh-CN"
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "PERMISSION_DENIED"
        assert "没有权限" in exc_info.value.detail["message"]
    
    @pytest.mark.asyncio
    async def test_batch_transfer_english_messages(
        self,
        mock_db,
        admin_user
    ):
        """Test batch transfer with English messages."""
        requests = [
            DataTransferRequest(
                source_type="structuring",
                source_id="job-1",
                target_state="temp_stored",
                data_attributes=DataAttributes(
                    category="category1",
                    tags=["tag1"],
                    quality_score=0.9
                ),
                records=[
                    TransferRecord(
                        id="record-1",
                        content={"field": "value1"}
                    )
                ]
            )
        ]
        
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(return_value={
                "success": True,
                "transferred_count": 1,
                "lifecycle_ids": ["id-1"],
                "target_state": "temp_stored",
                "message": "Success",
                "navigation_url": "/data-lifecycle/temp-data"
            })
            
            from src.api.data_lifecycle_api import batch_transfer_data
            
            result = await batch_transfer_data(
                requests=requests,
                db=mock_db,
                current_user=admin_user,
                accept_language="en-US"
            )
            
            assert "Successfully transferred" in result["results"][0]["message"]
            assert "temporary storage" in result["results"][0]["message"]
    
    @pytest.mark.asyncio
    async def test_batch_transfer_all_failures(
        self,
        mock_db,
        admin_user
    ):
        """Test batch transfer where all transfers fail."""
        requests = [
            DataTransferRequest(
                source_type="structuring",
                source_id="job-1",
                target_state="temp_stored",
                data_attributes=DataAttributes(
                    category="category1",
                    tags=["tag1"],
                    quality_score=0.9
                ),
                records=[
                    TransferRecord(
                        id="record-1",
                        content={"field": "value1"}
                    )
                ]
            ),
            DataTransferRequest(
                source_type="augmentation",
                source_id="job-2",
                target_state="in_sample_library",
                data_attributes=DataAttributes(
                    category="category2",
                    tags=["tag2"],
                    quality_score=0.95
                ),
                records=[
                    TransferRecord(
                        id="record-2",
                        content={"field": "value2"}
                    )
                ]
            )
        ]
        
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(side_effect=[
                ValueError("Source 1 not found"),
                PermissionError("No permission for source 2")
            ])
            
            from src.api.data_lifecycle_api import batch_transfer_data
            
            result = await batch_transfer_data(
                requests=requests,
                db=mock_db,
                current_user=admin_user,
                accept_language="zh-CN"
            )
            
            assert result["success"] is True
            assert result["total_transfers"] == 2
            assert result["successful_transfers"] == 0
            assert result["failed_transfers"] == 2
            
            # Check both failures
            assert result["results"][0]["success"] is False
            assert result["results"][0]["error_code"] == "INVALID_SOURCE"
            assert result["results"][1]["success"] is False
            assert result["results"][1]["error_code"] == "PERMISSION_DENIED"
    
    @pytest.mark.asyncio
    async def test_batch_transfer_with_approval_required(
        self,
        mock_db,
        admin_user
    ):
        """Test batch transfer where some transfers require approval."""
        requests = [
            DataTransferRequest(
                source_type="structuring",
                source_id="job-1",
                target_state="temp_stored",
                data_attributes=DataAttributes(
                    category="category1",
                    tags=["tag1"],
                    quality_score=0.9
                ),
                records=[
                    TransferRecord(
                        id="record-1",
                        content={"field": "value1"}
                    )
                ]
            ),
            DataTransferRequest(
                source_type="augmentation",
                source_id="job-2",
                target_state="in_sample_library",
                data_attributes=DataAttributes(
                    category="category2",
                    tags=["tag2"],
                    quality_score=0.95
                ),
                records=[
                    TransferRecord(
                        id="record-2",
                        content={"field": "value2"}
                    )
                ],
                request_approval=False
            )
        ]
        
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(side_effect=[
                {
                    "success": True,
                    "transferred_count": 1,
                    "lifecycle_ids": ["id-1"],
                    "target_state": "temp_stored",
                    "message": "Success",
                    "navigation_url": "/data-lifecycle/temp-data"
                },
                {
                    "success": True,
                    "approval_required": True,
                    "approval_id": "approval-123",
                    "message": "Transfer request submitted for approval",
                    "estimated_approval_time": "2-3 business days"
                }
            ])
            
            from src.api.data_lifecycle_api import batch_transfer_data
            
            result = await batch_transfer_data(
                requests=requests,
                db=mock_db,
                current_user=admin_user,
                accept_language="zh-CN"
            )
            
            assert result["success"] is True
            assert result["total_transfers"] == 2
            assert result["successful_transfers"] == 2
            assert result["failed_transfers"] == 0
            
            # Check first result (direct transfer)
            assert result["results"][0]["success"] is True
            assert "approval_required" not in result["results"][0]
            
            # Check second result (approval required)
            assert result["results"][1]["success"] is True
            assert result["results"][1]["approval_required"] is True
            assert result["results"][1]["approval_id"] == "approval-123"
            assert "等待审批" in result["results"][1]["message"]
    
    @pytest.mark.asyncio
    async def test_batch_transfer_empty_list(
        self,
        mock_db,
        admin_user
    ):
        """Test batch transfer with empty request list."""
        from src.api.data_lifecycle_api import batch_transfer_data
        
        result = await batch_transfer_data(
            requests=[],
            db=mock_db,
            current_user=admin_user,
            accept_language="zh-CN"
        )
        
        assert result["success"] is True
        assert result["total_transfers"] == 0
        assert result["successful_transfers"] == 0
        assert result["failed_transfers"] == 0
        assert len(result["results"]) == 0
    
    @pytest.mark.asyncio
    async def test_batch_transfer_internal_error_handling(
        self,
        mock_db,
        admin_user
    ):
        """Test batch transfer handles internal errors gracefully."""
        requests = [
            DataTransferRequest(
                source_type="structuring",
                source_id="job-1",
                target_state="temp_stored",
                data_attributes=DataAttributes(
                    category="category1",
                    tags=["tag1"],
                    quality_score=0.9
                ),
                records=[
                    TransferRecord(
                        id="record-1",
                        content={"field": "value1"}
                    )
                ]
            )
        ]
        
        with patch('src.api.data_lifecycle_api.DataTransferService') as MockService:
            mock_service = MockService.return_value
            mock_service.transfer = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            
            from src.api.data_lifecycle_api import batch_transfer_data
            
            result = await batch_transfer_data(
                requests=requests,
                db=mock_db,
                current_user=admin_user,
                accept_language="en-US"
            )
            
            assert result["success"] is True
            assert result["total_transfers"] == 1
            assert result["successful_transfers"] == 0
            assert result["failed_transfers"] == 1
            
            # Check error details
            assert result["results"][0]["success"] is False
            assert result["results"][0]["error_code"] == "INTERNAL_ERROR"
            assert "internal" in result["results"][0]["message"].lower()


# Tests for GET /api/data-lifecycle/approvals endpoint

@pytest.mark.asyncio
async def test_list_approvals_admin_can_see_all(mock_db, admin_user):
    """Test that admin users can see all approval requests."""
    from src.api.data_lifecycle_api import list_approvals
    from src.models.approval import ApprovalRequest, ApprovalStatus
    from datetime import datetime, timedelta
    
    # Mock approval service
    mock_approvals = [
        ApprovalRequest(
            id="approval-1",
            transfer_request=DataTransferRequest(
                source_type="structuring",
                source_id="job-1",
                target_state="in_sample_library",
                data_attributes=DataAttributes(
                    category="test",
                    tags=["test"],
                    quality_score=0.9
                ),
                records=[
                    TransferRecord(
                        id="rec-1",
                        content={"data": "test"},
                        metadata={}
                    )
                ]
            ),
            requester_id="user-123",
            requester_role="user",
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        ),
        ApprovalRequest(
            id="approval-2",
            transfer_request=DataTransferRequest(
                source_type="augmentation",
                source_id="job-2",
                target_state="annotation_pending",
                data_attributes=DataAttributes(
                    category="test2",
                    tags=["test2"],
                    quality_score=0.8
                ),
                records=[
                    TransferRecord(
                        id="rec-2",
                        content={"data": "test2"},
                        metadata={}
                    )
                ]
            ),
            requester_id="user-456",
            requester_role="data_analyst",
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
    ]
    
    with patch('src.services.approval_service.ApprovalService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_pending_approvals.return_value = mock_approvals
        
        result = await list_approvals(
            status=None,
            user_id=None,
            limit=50,
            offset=0,
            db=mock_db,
            current_user=admin_user,
            accept_language="en-US"
        )
        
        assert result["success"] is True
        assert len(result["approvals"]) == 2
        assert result["approvals"][0]["id"] == "approval-1"
        assert result["approvals"][1]["id"] == "approval-2"
        assert result["limit"] == 50
        assert result["offset"] == 0


@pytest.mark.asyncio
async def test_list_approvals_regular_user_only_sees_own(mock_db, regular_user):
    """Test that regular users can only see their own approval requests."""
    from src.api.data_lifecycle_api import list_approvals
    from src.models.approval import ApprovalRequest, ApprovalStatus
    from datetime import datetime, timedelta
    
    mock_approvals = [
        ApprovalRequest(
            id="approval-1",
            transfer_request=DataTransferRequest(
                source_type="structuring",
                source_id="job-1",
                target_state="in_sample_library",
                data_attributes=DataAttributes(
                    category="test",
                    tags=["test"],
                    quality_score=0.9
                ),
                records=[
                    TransferRecord(
                        id="rec-1",
                        content={"data": "test"},
                        metadata={}
                    )
                ]
            ),
            requester_id="user-789",
            requester_role="user",
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
    ]
    
    with patch('src.services.approval_service.ApprovalService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_user_approval_requests.return_value = mock_approvals
        
        result = await list_approvals(
            status=None,
            user_id=None,
            limit=50,
            offset=0,
            db=mock_db,
            current_user=regular_user,
            accept_language="en-US"
        )
        
        assert result["success"] is True
        assert len(result["approvals"]) == 1
        assert result["approvals"][0]["requester_id"] == "user-789"
        
        # Verify the service was called with the current user's ID
        mock_service.get_user_approval_requests.assert_called_once()
        call_args = mock_service.get_user_approval_requests.call_args
        assert call_args[1]["user_id"] == "user-789"


@pytest.mark.asyncio
async def test_list_approvals_regular_user_cannot_query_others(mock_db, regular_user):
    """Test that regular users cannot query other users' approval requests."""
    from src.api.data_lifecycle_api import list_approvals
    
    with pytest.raises(HTTPException) as exc_info:
        await list_approvals(
            status=None,
            user_id="other-user-123",  # Trying to query another user
            limit=50,
            offset=0,
            db=mock_db,
            current_user=regular_user,
            accept_language="en-US"
        )
    
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error_code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_list_approvals_filter_by_status(mock_db, admin_user):
    """Test filtering approvals by status."""
    from src.api.data_lifecycle_api import list_approvals
    from src.models.approval import ApprovalRequest, ApprovalStatus
    from datetime import datetime, timedelta
    
    mock_approvals = [
        ApprovalRequest(
            id="approval-1",
            transfer_request=DataTransferRequest(
                source_type="structuring",
                source_id="job-1",
                target_state="in_sample_library",
                data_attributes=DataAttributes(
                    category="test",
                    tags=["test"],
                    quality_score=0.9
                ),
                records=[
                    TransferRecord(
                        id="rec-1",
                        content={"data": "test"},
                        metadata={}
                    )
                ]
            ),
            requester_id="user-123",
            requester_role="user",
            status=ApprovalStatus.APPROVED,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            approver_id="admin-123",
            approved_at=datetime.utcnow()
        )
    ]
    
    with patch('src.services.approval_service.ApprovalService') as MockService:
        mock_service = MockService.return_value
        
        # Mock the database query for non-pending statuses
        with patch.object(mock_db, 'execute') as mock_execute:
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                (
                    "approval-1",
                    '{"source_type": "structuring", "source_id": "job-1", "target_state": "in_sample_library", "data_attributes": {"category": "test", "tags": ["test"], "quality_score": 0.9}, "records": [{"id": "rec-1", "content": {"data": "test"}, "metadata": {}}]}',
                    "user-123",
                    "user",
                    "approved",
                    datetime.utcnow(),
                    datetime.utcnow() + timedelta(days=7),
                    "admin-123",
                    datetime.utcnow(),
                    None
                )
            ]
            mock_execute.return_value = mock_result
            
            result = await list_approvals(
                status="approved",
                user_id=None,
                limit=50,
                offset=0,
                db=mock_db,
                current_user=admin_user,
                accept_language="en-US"
            )
            
            assert result["success"] is True
            assert len(result["approvals"]) == 1
            assert result["approvals"][0]["status"] == "approved"


@pytest.mark.asyncio
async def test_list_approvals_invalid_status(mock_db, admin_user):
    """Test that invalid status parameter returns 400 error."""
    from src.api.data_lifecycle_api import list_approvals
    
    with pytest.raises(HTTPException) as exc_info:
        await list_approvals(
            status="invalid_status",
            user_id=None,
            limit=50,
            offset=0,
            db=mock_db,
            current_user=admin_user,
            accept_language="en-US"
        )
    
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "INVALID_STATUS"


@pytest.mark.asyncio
async def test_list_approvals_pagination(mock_db, admin_user):
    """Test pagination parameters."""
    from src.api.data_lifecycle_api import list_approvals
    from src.models.approval import ApprovalRequest, ApprovalStatus
    from datetime import datetime, timedelta
    
    # Create 50 mock approvals
    mock_approvals = []
    for i in range(50):
        mock_approvals.append(
            ApprovalRequest(
                id=f"approval-{i}",
                transfer_request=DataTransferRequest(
                    source_type="structuring",
                    source_id=f"job-{i}",
                    target_state="in_sample_library",
                    data_attributes=DataAttributes(
                        category="test",
                        tags=["test"],
                        quality_score=0.9
                    ),
                    records=[
                        TransferRecord(
                            id=f"rec-{i}",
                            content={"data": f"test{i}"},
                            metadata={}
                        )
                    ]
                ),
                requester_id=f"user-{i}",
                requester_role="user",
                status=ApprovalStatus.PENDING,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
        )
    
    with patch('src.services.approval_service.ApprovalService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_pending_approvals.return_value = mock_approvals
        
        result = await list_approvals(
            status=None,
            user_id=None,
            limit=50,
            offset=0,
            db=mock_db,
            current_user=admin_user,
            accept_language="en-US"
        )
        
        assert result["success"] is True
        assert len(result["approvals"]) == 50
        assert result["limit"] == 50
        assert result["offset"] == 0
        assert result["has_more"] is True


@pytest.mark.asyncio
async def test_list_approvals_limit_max_100(mock_db, admin_user):
    """Test that limit is capped at 100."""
    from src.api.data_lifecycle_api import list_approvals
    
    with patch('src.services.approval_service.ApprovalService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_pending_approvals.return_value = []
        
        result = await list_approvals(
            status=None,
            user_id=None,
            limit=200,  # Request more than max
            offset=0,
            db=mock_db,
            current_user=admin_user,
            accept_language="en-US"
        )
        
        # Verify limit was capped at 100
        assert result["limit"] == 100


@pytest.mark.asyncio
async def test_list_approvals_i18n_support(mock_db, admin_user):
    """Test that the endpoint respects Accept-Language header."""
    from src.api.data_lifecycle_api import list_approvals
    
    with patch('src.services.approval_service.ApprovalService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_pending_approvals.return_value = []
        
        # Test with Chinese
        result_zh = await list_approvals(
            status=None,
            user_id=None,
            limit=50,
            offset=0,
            db=mock_db,
            current_user=admin_user,
            accept_language="zh-CN"
        )
        
        assert result_zh["success"] is True
        
        # Test with English
        result_en = await list_approvals(
            status=None,
            user_id=None,
            limit=50,
            offset=0,
            db=mock_db,
            current_user=admin_user,
            accept_language="en-US"
        )
        
        assert result_en["success"] is True


@pytest.mark.asyncio
async def test_list_approvals_admin_filter_by_user(mock_db, admin_user):
    """Test that admin can filter approvals by specific user."""
    from src.api.data_lifecycle_api import list_approvals
    from src.models.approval import ApprovalRequest, ApprovalStatus
    from datetime import datetime, timedelta
    
    mock_approvals = [
        ApprovalRequest(
            id="approval-1",
            transfer_request=DataTransferRequest(
                source_type="structuring",
                source_id="job-1",
                target_state="in_sample_library",
                data_attributes=DataAttributes(
                    category="test",
                    tags=["test"],
                    quality_score=0.9
                ),
                records=[
                    TransferRecord(
                        id="rec-1",
                        content={"data": "test"},
                        metadata={}
                    )
                ]
            ),
            requester_id="specific-user-123",
            requester_role="user",
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
    ]
    
    with patch('src.services.approval_service.ApprovalService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_user_approval_requests.return_value = mock_approvals
        
        result = await list_approvals(
            status=None,
            user_id="specific-user-123",
            limit=50,
            offset=0,
            db=mock_db,
            current_user=admin_user,
            accept_language="en-US"
        )
        
        assert result["success"] is True
        assert len(result["approvals"]) == 1
        assert result["approvals"][0]["requester_id"] == "specific-user-123"
        
        # Verify the service was called with the specified user_id
        mock_service.get_user_approval_requests.assert_called_once()
        call_args = mock_service.get_user_approval_requests.call_args
        assert call_args[1]["user_id"] == "specific-user-123"



# Test approval endpoint
class TestApprovalEndpoint:
    """Test POST /api/data-lifecycle/approvals/{id}/approve endpoint."""
    
    @pytest.fixture
    def data_manager_user(self):
        """Create data manager user for testing."""
        user = Mock(spec=SimpleUser)
        user.id = "manager-999"
        user.is_superuser = False
        user.email = "manager@test.com"
        user.username = "manager"
        user.name = "Data Manager"
        user.is_active = True
        # In real implementation, this would have a role field
        # For now, we'll mock the role check in the test
        return user
    
    @pytest.mark.asyncio
    async def test_approve_request_as_admin(self, mock_db, admin_user):
        """Test admin user approving a request."""
        from src.api.data_lifecycle_api import approve_transfer
        from src.models.approval import ApprovalRequest, ApprovalStatus
        from datetime import datetime, timedelta
        
        approval_id = "approval-123"
        
        with patch('src.services.approval_service.ApprovalService') as MockService:
            # Setup mock approval
            mock_approval = Mock(spec=ApprovalRequest)
            mock_approval.id = approval_id
            mock_approval.status = ApprovalStatus.APPROVED
            mock_approval.approver_id = admin_user.id
            mock_approval.approved_at = datetime.utcnow()
            mock_approval.comment = "Looks good"
            
            mock_service = MockService.return_value
            mock_service.approve_request = AsyncMock(return_value=mock_approval)
            
            # Execute approval
            result = await approve_transfer(
                approval_id=approval_id,
                approved=True,
                comment="Looks good",
                db=mock_db,
                current_user=admin_user,
                accept_language="zh-CN"
            )
            
            # Verify result
            assert result["success"] is True
            assert result["approval"]["id"] == approval_id
            assert result["approval"]["status"] == "approved"
            assert result["approval"]["approver_id"] == admin_user.id
            assert result["approval"]["comment"] == "Looks good"
            assert "已批准" in result["message"]
            
            # Verify service was called correctly
            mock_service.approve_request.assert_called_once_with(
                approval_id=approval_id,
                approver_id=admin_user.id,
                approver_role=UserRole.ADMIN,
                approved=True,
                comment="Looks good"
            )
    
    @pytest.mark.asyncio
    async def test_reject_request_as_admin(self, mock_db, admin_user):
        """Test admin user rejecting a request."""
        from src.api.data_lifecycle_api import approve_transfer
        from src.models.approval import ApprovalRequest, ApprovalStatus
        from datetime import datetime
        
        approval_id = "approval-456"
        
        with patch('src.services.approval_service.ApprovalService') as MockService:
            mock_approval = Mock(spec=ApprovalRequest)
            mock_approval.id = approval_id
            mock_approval.status = ApprovalStatus.REJECTED
            mock_approval.approver_id = admin_user.id
            mock_approval.approved_at = datetime.utcnow()
            mock_approval.comment = "Insufficient quality"
            
            mock_service = MockService.return_value
            mock_service.approve_request = AsyncMock(return_value=mock_approval)
            
            result = await approve_transfer(
                approval_id=approval_id,
                approved=False,
                comment="Insufficient quality",
                db=mock_db,
                current_user=admin_user,
                accept_language="en-US"
            )
            
            assert result["success"] is True
            assert result["approval"]["status"] == "rejected"
            assert "rejected successfully" in result["message"]
    
    @pytest.mark.asyncio
    async def test_approve_without_comment(self, mock_db, admin_user):
        """Test approving without a comment."""
        from src.api.data_lifecycle_api import approve_transfer
        from src.models.approval import ApprovalRequest, ApprovalStatus
        from datetime import datetime
        
        approval_id = "approval-789"
        
        with patch('src.services.approval_service.ApprovalService') as MockService:
            mock_approval = Mock(spec=ApprovalRequest)
            mock_approval.id = approval_id
            mock_approval.status = ApprovalStatus.APPROVED
            mock_approval.approver_id = admin_user.id
            mock_approval.approved_at = datetime.utcnow()
            mock_approval.comment = None
            
            mock_service = MockService.return_value
            mock_service.approve_request = AsyncMock(return_value=mock_approval)
            
            result = await approve_transfer(
                approval_id=approval_id,
                approved=True,
                comment=None,
                db=mock_db,
                current_user=admin_user,
                accept_language="zh-CN"
            )
            
            assert result["success"] is True
            assert result["approval"]["comment"] is None
    
    @pytest.mark.asyncio
    async def test_regular_user_cannot_approve(self, mock_db, regular_user):
        """Test regular user cannot approve requests."""
        from src.api.data_lifecycle_api import approve_transfer
        
        approval_id = "approval-999"
        
        with pytest.raises(HTTPException) as exc_info:
            await approve_transfer(
                approval_id=approval_id,
                approved=True,
                comment="Test",
                db=mock_db,
                current_user=regular_user,
                accept_language="zh-CN"
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "PERMISSION_DENIED"
        assert "没有权限" in exc_info.value.detail["message"]
    
    @pytest.mark.asyncio
    async def test_data_analyst_cannot_approve(self, mock_db, data_analyst_user):
        """Test data analyst cannot approve requests."""
        from src.api.data_lifecycle_api import approve_transfer
        
        approval_id = "approval-888"
        
        with pytest.raises(HTTPException) as exc_info:
            await approve_transfer(
                approval_id=approval_id,
                approved=True,
                comment="Test",
                db=mock_db,
                current_user=data_analyst_user,
                accept_language="en-US"
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "PERMISSION_DENIED"
        assert "don't have permission" in exc_info.value.detail["message"]
    
    @pytest.mark.asyncio
    async def test_approval_not_found(self, mock_db, admin_user):
        """Test approving non-existent approval request."""
        from src.api.data_lifecycle_api import approve_transfer
        
        approval_id = "nonexistent-approval"
        
        with patch('src.services.approval_service.ApprovalService') as MockService:
            mock_service = MockService.return_value
            mock_service.approve_request = AsyncMock(
                side_effect=ValueError(f"Approval request {approval_id} not found")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await approve_transfer(
                    approval_id=approval_id,
                    approved=True,
                    comment="Test",
                    db=mock_db,
                    current_user=admin_user,
                    accept_language="zh-CN"
                )
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail["error_code"] == "APPROVAL_NOT_FOUND"
            assert approval_id in exc_info.value.detail["message"]
    
    @pytest.mark.asyncio
    async def test_approval_expired(self, mock_db, admin_user):
        """Test approving expired approval request."""
        from src.api.data_lifecycle_api import approve_transfer
        
        approval_id = "expired-approval"
        
        with patch('src.services.approval_service.ApprovalService') as MockService:
            mock_service = MockService.return_value
            mock_service.approve_request = AsyncMock(
                side_effect=ValueError("Approval request has expired")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await approve_transfer(
                    approval_id=approval_id,
                    approved=True,
                    comment="Test",
                    db=mock_db,
                    current_user=admin_user,
                    accept_language="zh-CN"
                )
            
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["error_code"] == "APPROVAL_EXPIRED"
            assert "已过期" in exc_info.value.detail["message"]
    
    @pytest.mark.asyncio
    async def test_approval_already_processed(self, mock_db, admin_user):
        """Test approving already processed approval request."""
        from src.api.data_lifecycle_api import approve_transfer
        
        approval_id = "processed-approval"
        
        with patch('src.services.approval_service.ApprovalService') as MockService:
            mock_service = MockService.return_value
            mock_service.approve_request = AsyncMock(
                side_effect=ValueError("Approval request is already approved")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await approve_transfer(
                    approval_id=approval_id,
                    approved=True,
                    comment="Test",
                    db=mock_db,
                    current_user=admin_user,
                    accept_language="en-US"
                )
            
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail["error_code"] == "INVALID_APPROVAL"
    
    @pytest.mark.asyncio
    async def test_approval_internal_error(self, mock_db, admin_user):
        """Test internal error during approval."""
        from src.api.data_lifecycle_api import approve_transfer
        
        approval_id = "error-approval"
        
        with patch('src.services.approval_service.ApprovalService') as MockService:
            mock_service = MockService.return_value
            mock_service.approve_request = AsyncMock(
                side_effect=Exception("Database connection error")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await approve_transfer(
                    approval_id=approval_id,
                    approved=True,
                    comment="Test",
                    db=mock_db,
                    current_user=admin_user,
                    accept_language="zh-CN"
                )
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail["error_code"] == "INTERNAL_ERROR"
            assert "内部服务器错误" in exc_info.value.detail["message"]
    
    @pytest.mark.asyncio
    async def test_approval_permission_error_from_service(self, mock_db, admin_user):
        """Test permission error raised by service layer."""
        from src.api.data_lifecycle_api import approve_transfer
        
        approval_id = "permission-error-approval"
        
        with patch('src.services.approval_service.ApprovalService') as MockService:
            mock_service = MockService.return_value
            mock_service.approve_request = AsyncMock(
                side_effect=PermissionError("User cannot approve requests")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await approve_transfer(
                    approval_id=approval_id,
                    approved=True,
                    comment="Test",
                    db=mock_db,
                    current_user=admin_user,
                    accept_language="en-US"
                )
            
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error_code"] == "PERMISSION_DENIED"
    
    @pytest.mark.asyncio
    async def test_approve_with_chinese_locale(self, mock_db, admin_user):
        """Test approval with Chinese locale."""
        from src.api.data_lifecycle_api import approve_transfer
        from src.models.approval import ApprovalRequest, ApprovalStatus
        from datetime import datetime
        
        approval_id = "approval-zh"
        
        with patch('src.services.approval_service.ApprovalService') as MockService:
            mock_approval = Mock(spec=ApprovalRequest)
            mock_approval.id = approval_id
            mock_approval.status = ApprovalStatus.APPROVED
            mock_approval.approver_id = admin_user.id
            mock_approval.approved_at = datetime.utcnow()
            mock_approval.comment = "测试评论"
            
            mock_service = MockService.return_value
            mock_service.approve_request = AsyncMock(return_value=mock_approval)
            
            result = await approve_transfer(
                approval_id=approval_id,
                approved=True,
                comment="测试评论",
                db=mock_db,
                current_user=admin_user,
                accept_language="zh-CN"
            )
            
            assert result["success"] is True
            assert "已批准" in result["message"]
    
    @pytest.mark.asyncio
    async def test_reject_with_english_locale(self, mock_db, admin_user):
        """Test rejection with English locale."""
        from src.api.data_lifecycle_api import approve_transfer
        from src.models.approval import ApprovalRequest, ApprovalStatus
        from datetime import datetime
        
        approval_id = "approval-en"
        
        with patch('src.services.approval_service.ApprovalService') as MockService:
            mock_approval = Mock(spec=ApprovalRequest)
            mock_approval.id = approval_id
            mock_approval.status = ApprovalStatus.REJECTED
            mock_approval.approver_id = admin_user.id
            mock_approval.approved_at = datetime.utcnow()
            mock_approval.comment = "Test comment"
            
            mock_service = MockService.return_value
            mock_service.approve_request = AsyncMock(return_value=mock_approval)
            
            result = await approve_transfer(
                approval_id=approval_id,
                approved=False,
                comment="Test comment",
                db=mock_db,
                current_user=admin_user,
                accept_language="en-US"
            )
            
            assert result["success"] is True
            assert "rejected successfully" in result["message"]


# Test permissions check endpoint
class TestPermissionsCheckEndpoint:
    """Test GET /api/data-lifecycle/permissions/check endpoint."""
    
    @pytest.mark.asyncio
    async def test_check_permissions_admin_temp_stored(self, admin_user):
        """Test admin checking permissions for temp_stored."""
        from src.api.data_lifecycle_api import check_permissions
        
        result = await check_permissions(
            source_type="structuring",
            target_state="temp_stored",
            operation="transfer",
            current_user=admin_user,
            accept_language="zh-CN"
        )
        
        assert result["allowed"] is True
        assert result["requires_approval"] is False
        assert result["user_role"] == "admin"
        assert "reason" not in result or result.get("reason") is None
    
    @pytest.mark.asyncio
    async def test_check_permissions_admin_sample_library(self, admin_user):
        """Test admin checking permissions for sample library."""
        from src.api.data_lifecycle_api import check_permissions
        
        result = await check_permissions(
            source_type="augmentation",
            target_state="in_sample_library",
            operation="transfer",
            current_user=admin_user,
            accept_language="en-US"
        )
        
        assert result["allowed"] is True
        assert result["requires_approval"] is False
        assert result["user_role"] == "admin"
    
    @pytest.mark.asyncio
    async def test_check_permissions_regular_user_temp_stored(self, regular_user):
        """Test regular user checking permissions for temp_stored."""
        from src.api.data_lifecycle_api import check_permissions
        
        result = await check_permissions(
            source_type="structuring",
            target_state="temp_stored",
            operation="transfer",
            current_user=regular_user,
            accept_language="zh-CN"
        )
        
        assert result["allowed"] is True
        assert result["requires_approval"] is False
        assert result["user_role"] == "user"
    
    @pytest.mark.asyncio
    async def test_check_permissions_regular_user_sample_library_requires_approval(
        self,
        regular_user
    ):
        """Test regular user checking permissions for sample library (requires approval)."""
        from src.api.data_lifecycle_api import check_permissions
        
        result = await check_permissions(
            source_type="augmentation",
            target_state="in_sample_library",
            operation="transfer",
            current_user=regular_user,
            accept_language="zh-CN"
        )
        
        assert result["allowed"] is True
        assert result["requires_approval"] is True
        assert result["user_role"] == "user"
        assert "reason" in result
        assert "等待审批" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_check_permissions_regular_user_sample_library_english(
        self,
        regular_user
    ):
        """Test regular user checking permissions with English locale."""
        from src.api.data_lifecycle_api import check_permissions
        
        result = await check_permissions(
            source_type="augmentation",
            target_state="in_sample_library",
            operation="transfer",
            current_user=regular_user,
            accept_language="en-US"
        )
        
        assert result["allowed"] is True
        assert result["requires_approval"] is True
        assert result["user_role"] == "user"
        assert "reason" in result
        assert "approval" in result["reason"].lower()
    
    @pytest.mark.asyncio
    async def test_check_permissions_batch_transfer_admin(self, admin_user):
        """Test admin checking batch transfer permissions."""
        from src.api.data_lifecycle_api import check_permissions
        
        result = await check_permissions(
            source_type="sync",
            target_state="temp_stored",
            operation="batch_transfer",
            current_user=admin_user,
            accept_language="zh-CN"
        )
        
        assert result["allowed"] is True
        assert result["requires_approval"] is False
        assert result["user_role"] == "admin"
    
    @pytest.mark.asyncio
    async def test_check_permissions_batch_transfer_regular_user_denied(
        self,
        regular_user
    ):
        """Test regular user checking batch transfer permissions (denied)."""
        from src.api.data_lifecycle_api import check_permissions
        
        result = await check_permissions(
            source_type="sync",
            target_state="temp_stored",
            operation="batch_transfer",
            current_user=regular_user,
            accept_language="zh-CN"
        )
        
        assert result["allowed"] is False
        assert result["requires_approval"] is False
        assert result["user_role"] == "user"
        assert "reason" in result
    
    @pytest.mark.asyncio
    async def test_check_permissions_annotation_pending_regular_user(
        self,
        regular_user
    ):
        """Test regular user checking permissions for annotation_pending."""
        from src.api.data_lifecycle_api import check_permissions
        
        result = await check_permissions(
            source_type="annotation",
            target_state="annotation_pending",
            operation="transfer",
            current_user=regular_user,
            accept_language="zh-CN"
        )
        
        assert result["allowed"] is True
        assert result["requires_approval"] is True
        assert result["user_role"] == "user"
    
    @pytest.mark.asyncio
    async def test_check_permissions_invalid_source_type(self, admin_user):
        """Test permissions check with invalid source_type."""
        from src.api.data_lifecycle_api import check_permissions
        
        with pytest.raises(HTTPException) as exc_info:
            await check_permissions(
                source_type="invalid_source",
                target_state="temp_stored",
                operation="transfer",
                current_user=admin_user,
                accept_language="zh-CN"
            )
        
        assert exc_info.value.status_code == 400
        assert "INVALID_SOURCE_TYPE" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_check_permissions_invalid_target_state(self, admin_user):
        """Test permissions check with invalid target_state."""
        from src.api.data_lifecycle_api import check_permissions
        
        with pytest.raises(HTTPException) as exc_info:
            await check_permissions(
                source_type="structuring",
                target_state="invalid_state",
                operation="transfer",
                current_user=admin_user,
                accept_language="zh-CN"
            )
        
        assert exc_info.value.status_code == 400
        assert "INVALID_TARGET_STATE" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_check_permissions_invalid_operation(self, admin_user):
        """Test permissions check with invalid operation."""
        from src.api.data_lifecycle_api import check_permissions
        
        with pytest.raises(HTTPException) as exc_info:
            await check_permissions(
                source_type="structuring",
                target_state="temp_stored",
                operation="invalid_operation",
                current_user=admin_user,
                accept_language="zh-CN"
            )
        
        assert exc_info.value.status_code == 400
        assert "INVALID_OPERATION" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_check_permissions_all_source_types(self, admin_user):
        """Test permissions check with all valid source types."""
        from src.api.data_lifecycle_api import check_permissions
        
        source_types = [
            "structuring",
            "augmentation",
            "sync",
            "annotation",
            "ai_assistant",
            "manual"
        ]
        
        for source_type in source_types:
            result = await check_permissions(
                source_type=source_type,
                target_state="temp_stored",
                operation="transfer",
                current_user=admin_user,
                accept_language="zh-CN"
            )
            
            assert result["allowed"] is True
            assert result["user_role"] == "admin"
    
    @pytest.mark.asyncio
    async def test_check_permissions_all_target_states(self, admin_user):
        """Test permissions check with all valid target states."""
        from src.api.data_lifecycle_api import check_permissions
        
        target_states = ["temp_stored", "in_sample_library", "annotation_pending"]
        
        for target_state in target_states:
            result = await check_permissions(
                source_type="structuring",
                target_state=target_state,
                operation="transfer",
                current_user=admin_user,
                accept_language="zh-CN"
            )
            
            assert result["allowed"] is True
            assert result["user_role"] == "admin"
    
    @pytest.mark.asyncio
    async def test_check_permissions_default_operation(self, admin_user):
        """Test permissions check with default operation parameter."""
        from src.api.data_lifecycle_api import check_permissions
        
        # Test that operation defaults to "transfer"
        result = await check_permissions(
            source_type="structuring",
            target_state="temp_stored",
            current_user=admin_user,
            accept_language="zh-CN"
        )
        
        assert result["allowed"] is True
        assert result["user_role"] == "admin"
    
    @pytest.mark.asyncio
    async def test_check_permissions_data_analyst_user(self, data_analyst_user):
        """Test data analyst checking various permissions."""
        from src.api.data_lifecycle_api import check_permissions
        
        # Temp stored - should be allowed without approval
        result = await check_permissions(
            source_type="structuring",
            target_state="temp_stored",
            operation="transfer",
            current_user=data_analyst_user,
            accept_language="zh-CN"
        )
        
        assert result["allowed"] is True
        assert result["requires_approval"] is False
        assert result["user_role"] == "user"  # Non-superuser defaults to USER role
    
    @pytest.mark.asyncio
    async def test_check_permissions_response_structure(self, admin_user):
        """Test that response has correct structure."""
        from src.api.data_lifecycle_api import check_permissions
        
        result = await check_permissions(
            source_type="structuring",
            target_state="temp_stored",
            operation="transfer",
            current_user=admin_user,
            accept_language="zh-CN"
        )
        
        # Check required fields
        assert "allowed" in result
        assert "requires_approval" in result
        assert "user_role" in result
        
        # Check types
        assert isinstance(result["allowed"], bool)
        assert isinstance(result["requires_approval"], bool)
        assert isinstance(result["user_role"], str)
    
    @pytest.mark.asyncio
    async def test_check_permissions_with_service_error(self, admin_user):
        """Test permissions check when service raises an error."""
        from src.api.data_lifecycle_api import check_permissions
        
        with patch('src.services.permission_service.PermissionService') as MockService:
            mock_service = MockService.return_value
            mock_service.check_permission.side_effect = Exception("Service error")
            
            with pytest.raises(HTTPException) as exc_info:
                await check_permissions(
                    source_type="structuring",
                    target_state="temp_stored",
                    operation="transfer",
                    current_user=admin_user,
                    accept_language="zh-CN"
                )
            
            assert exc_info.value.status_code == 500
            assert "INTERNAL_ERROR" in str(exc_info.value.detail)
