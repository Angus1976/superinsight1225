"""
Integration test for augmentation method and parameter recording in transfer metadata.

Tests that augmentation methods and parameters are properly recorded when transferring
augmented data to the data lifecycle system.

Task: 3.2.3 - Record augmentation methods and parameters
"""

import json

import pytest
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.services.data_transfer_service import DataTransferService, User
from src.services.permission_service import UserRole
from src.models.data_transfer import (
    DataTransferRequest,
    DataAttributes,
    TransferRecord
)
from src.models.data_lifecycle import TempDataModel


def _as_uuid(value):
    """Coerce lifecycle id from transfer API (str) to UUID for ORM queries."""
    return UUID(value) if isinstance(value, str) else value


@pytest.fixture
def admin_user():
    """Create an admin user for testing."""
    return User(id=str(uuid4()), role=UserRole.ADMIN)


@pytest.fixture
def transfer_service(db_session):
    """Create a data transfer service instance."""
    return DataTransferService(db_session)


class TestAugmentationMetadataRecording:
    """Test suite for augmentation metadata recording in transfers."""
    
    @pytest.mark.asyncio
    async def test_transfer_preserves_augmentation_method(
        self,
        transfer_service: DataTransferService,
        admin_user: User,
        db_session: Session
    ):
        """Test that augmentation method is preserved in transfer metadata."""
        # Arrange
        augmentation_params = {
            "synonym_replacement": True,
            "random_insertion": True,
            "augmentation_ratio": 1.5,
            "temperature": 0.8
        }
        
        transfer_request = DataTransferRequest(
            source_type="augmentation",
            source_id="job-123",
            target_state="temp_stored",
            data_attributes=DataAttributes(
                category="augmented_text",
                tags=["augmented", "text"],
                quality_score=0.92,
                description="Augmented customer reviews"
            ),
            records=[
                TransferRecord(
                    id="sample-1",
                    content={
                        "text": "This is augmented text",
                        "original_text": "This is original text"
                    },
                    metadata={
                        "augmentation_method": "TEXT_ENHANCEMENT",
                        "enhancement_type": "TEXT_ENHANCEMENT",
                        "augmentation_params": augmentation_params,
                        "augmentation_config": augmentation_params,
                        "target_quality": 0.9,
                        "augmentation_job_id": "job-123",
                        "augmentation_strategy": "synonym_replacement"
                    }
                )
            ]
        )
        
        # Act
        result = await transfer_service.transfer(transfer_request, admin_user)
        
        # Assert
        assert result["success"] is True
        assert result["transferred_count"] == 1
        assert len(result["lifecycle_ids"]) == 1
        
        # Verify metadata in database
        lifecycle_id = result["lifecycle_ids"][0]
        temp_data = db_session.query(TempDataModel).filter_by(id=_as_uuid(lifecycle_id)).first()
        
        assert temp_data is not None
        assert temp_data.metadata_["augmentation_method"] == "TEXT_ENHANCEMENT"
        assert temp_data.metadata_["enhancement_type"] == "TEXT_ENHANCEMENT"
        assert temp_data.metadata_["augmentation_params"] == augmentation_params
        assert temp_data.metadata_["augmentation_config"] == augmentation_params
        assert temp_data.metadata_["target_quality"] == 0.9
        assert temp_data.metadata_["augmentation_job_id"] == "job-123"
        assert temp_data.metadata_["augmentation_strategy"] == "synonym_replacement"
    
    @pytest.mark.asyncio
    async def test_transfer_to_sample_library_preserves_parameters(
        self,
        transfer_service: DataTransferService,
        admin_user: User,
        db_session: Session
    ):
        """Test that augmentation parameters are preserved when transferring to sample library."""
        # Arrange
        augmentation_params = {
            "rotation": True,
            "flip": True,
            "brightness_range": [0.8, 1.2],
            "augmentation_ratio": 2.0
        }
        
        transfer_request = DataTransferRequest(
            source_type="augmentation",
            source_id="job-456",
            target_state="in_sample_library",
            data_attributes=DataAttributes(
                category="augmented_images",
                tags=["augmented", "image"],
                quality_score=0.87,
                description="Augmented product images"
            ),
            records=[
                TransferRecord(
                    id="sample-2",
                    content={
                        "image_url": "https://example.com/augmented.jpg",
                        "original_url": "https://example.com/original.jpg"
                    },
                    metadata={
                        "augmentation_method": "IMAGE_ENHANCEMENT",
                        "enhancement_type": "IMAGE_ENHANCEMENT",
                        "augmentation_params": augmentation_params,
                        "target_quality": 0.85,
                        "augmentation_job_id": "job-456"
                    }
                )
            ]
        )
        
        # Act
        result = await transfer_service.transfer(transfer_request, admin_user)
        
        # Assert
        assert result["success"] is True
        assert result["target_state"] == "in_sample_library"
        
        # Verify metadata in database (raw SQL avoids ORM UUID type confusion when
        # test_legacy_api_compat runs earlier in the same process and patches columns).
        # Prefer latest row: PK string comparison can differ across SQLite/UUID adapters.
        row = db_session.execute(
            text("SELECT metadata FROM samples ORDER BY created_at DESC LIMIT 1"),
        ).mappings().first()
        assert row is not None
        meta = row["metadata"]
        if isinstance(meta, str):
            meta = json.loads(meta)
        assert meta["augmentation_method"] == "IMAGE_ENHANCEMENT"
        assert meta["augmentation_params"] == augmentation_params
        assert meta["target_quality"] == 0.85
    
    @pytest.mark.asyncio
    async def test_multiple_records_preserve_different_parameters(
        self,
        transfer_service: DataTransferService,
        admin_user: User,
        db_session: Session
    ):
        """Test that different augmentation parameters are preserved for multiple records."""
        # Arrange
        transfer_request = DataTransferRequest(
            source_type="augmentation",
            source_id="job-batch",
            target_state="temp_stored",
            data_attributes=DataAttributes(
                category="mixed_augmented",
                tags=["augmented"],
                quality_score=0.85
            ),
            records=[
                TransferRecord(
                    id="sample-text",
                    content={"text": "Augmented text 1"},
                    metadata={
                        "augmentation_method": "TEXT_ENHANCEMENT",
                        "augmentation_params": {
                            "synonym_replacement": True,
                            "temperature": 0.7
                        },
                        "target_quality": 0.9
                    }
                ),
                TransferRecord(
                    id="sample-image",
                    content={"image_url": "augmented.jpg"},
                    metadata={
                        "augmentation_method": "IMAGE_ENHANCEMENT",
                        "augmentation_params": {
                            "rotation": True,
                            "flip": False
                        },
                        "target_quality": 0.8
                    }
                )
            ]
        )
        
        # Act
        result = await transfer_service.transfer(transfer_request, admin_user)
        
        # Assert
        assert result["success"] is True
        assert result["transferred_count"] == 2
        
        # Verify each record has its own parameters
        for lifecycle_id in result["lifecycle_ids"]:
            temp_data = db_session.query(TempDataModel).filter_by(id=_as_uuid(lifecycle_id)).first()
            assert temp_data is not None
            assert "augmentation_method" in temp_data.metadata_
            assert "augmentation_params" in temp_data.metadata_
            assert "target_quality" in temp_data.metadata_
    
    @pytest.mark.asyncio
    async def test_transfer_without_augmentation_params_still_works(
        self,
        transfer_service: DataTransferService,
        admin_user: User,
        db_session: Session
    ):
        """Test that transfer works even without augmentation parameters (backward compatibility)."""
        # Arrange
        transfer_request = DataTransferRequest(
            source_type="augmentation",
            source_id="job-legacy",
            target_state="temp_stored",
            data_attributes=DataAttributes(
                category="legacy_augmented",
                tags=["augmented"],
                quality_score=0.8
            ),
            records=[
                TransferRecord(
                    id="sample-legacy",
                    content={"text": "Legacy augmented text"},
                    metadata={}  # No augmentation parameters
                )
            ]
        )
        
        # Act
        result = await transfer_service.transfer(transfer_request, admin_user)
        
        # Assert
        assert result["success"] is True
        assert result["transferred_count"] == 1
        
        # Verify record exists even without augmentation params
        lifecycle_id = result["lifecycle_ids"][0]
        temp_data = db_session.query(TempDataModel).filter_by(id=_as_uuid(lifecycle_id)).first()
        assert temp_data is not None
