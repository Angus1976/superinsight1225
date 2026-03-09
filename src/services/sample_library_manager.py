"""
Sample Library Manager Service for Data Lifecycle Management

Manages the sample library storage and retrieval with search, filtering,
and usage tracking capabilities.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from src.models.data_lifecycle import SampleModel, ChangeType


class SearchCriteria:
    """Search criteria for sample library queries"""
    def __init__(
        self,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        quality_min: Optional[float] = None,
        quality_max: Optional[float] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ):
        self.tags = tags or []
        self.category = category
        self.quality_min = quality_min
        self.quality_max = quality_max
        self.date_from = date_from
        self.date_to = date_to
        self.limit = limit
        self.offset = offset


class SampleLibraryManager:
    """
    Sample Library Manager for managing approved data samples.
    
    Responsibilities:
    - Store approved samples
    - Provide search and filtering capabilities
    - Manage sample metadata
    - Support tagging and categorization
    - Track usage count and last used timestamp
    
    Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
    """
    
    def __init__(self, db: Session, version_control_manager=None):
        """
        Initialize the Sample Library Manager.
        
        Args:
            db: Database session
            version_control_manager: Optional VersionControlManager instance for version tracking
        """
        self.db = db
        self.version_control_manager = version_control_manager
    
    def add_sample(
        self,
        data_id: str,
        content: Dict[str, Any],
        category: str,
        quality_overall: float = 0.8,
        quality_completeness: float = 0.8,
        quality_accuracy: float = 0.8,
        quality_consistency: float = 0.8,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SampleModel:
        """
        Add a new sample to the library.
        
        Args:
            data_id: ID of the source data
            content: Sample content (structured data)
            category: Sample category
            quality_overall: Overall quality score (0-1)
            quality_completeness: Completeness quality score (0-1)
            quality_accuracy: Accuracy quality score (0-1)
            quality_consistency: Consistency quality score (0-1)
            tags: List of tags for categorization
            metadata: Additional metadata
        
        Returns:
            Created SampleModel instance
        
        Raises:
            ValueError: If quality scores are out of range or required fields missing
        
        Validates: Requirements 4.1, 4.5
        """
        # Validate quality scores
        for score_name, score_value in [
            ('quality_overall', quality_overall),
            ('quality_completeness', quality_completeness),
            ('quality_accuracy', quality_accuracy),
            ('quality_consistency', quality_consistency)
        ]:
            if not (0 <= score_value <= 1):
                raise ValueError(
                    f"{score_name} must be between 0 and 1, got {score_value}"
                )
        
        # Validate required fields
        if not data_id:
            raise ValueError("data_id is required")
        if not content:
            raise ValueError("content is required")
        if not category:
            raise ValueError("category is required")
        
        # Create sample
        sample = SampleModel(
            data_id=data_id,
            content=content,
            category=category,
            quality_overall=quality_overall,
            quality_completeness=quality_completeness,
            quality_accuracy=quality_accuracy,
            quality_consistency=quality_consistency,
            version=1,
            tags=tags or [],
            usage_count=0,
            last_used_at=None,
            metadata_=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(sample)
        self.db.commit()
        self.db.refresh(sample)
        
        return sample
    
    def get_sample(self, sample_id: str) -> Optional[SampleModel]:
        """
        Get a specific sample by ID.
        
        Args:
            sample_id: UUID of the sample
        
        Returns:
            SampleModel instance or None if not found
        
        Validates: Requirements 4.1
        """
        try:
            sample_uuid = UUID(sample_id)
        except (ValueError, AttributeError):
            return None
        
        return self.db.query(SampleModel).filter(
            SampleModel.id == sample_uuid
        ).first()
    
    def search_samples(
        self,
        criteria: SearchCriteria
    ) -> tuple[List[SampleModel], int]:
        """
        Search samples with filters and pagination.
        
        Args:
            criteria: SearchCriteria object with filter parameters
        
        Returns:
            Tuple of (list of matching samples, total count)
        
        Validates: Requirements 4.2, 4.3
        """
        # Build query
        query = self.db.query(SampleModel)
        
        # Apply filters
        filters = []
        
        # Category filter
        if criteria.category:
            filters.append(SampleModel.category == criteria.category)
        
        # Quality score range filter
        if criteria.quality_min is not None:
            filters.append(SampleModel.quality_overall >= criteria.quality_min)
        if criteria.quality_max is not None:
            filters.append(SampleModel.quality_overall <= criteria.quality_max)
        
        # Date range filter
        if criteria.date_from:
            filters.append(SampleModel.created_at >= criteria.date_from)
        if criteria.date_to:
            filters.append(SampleModel.created_at <= criteria.date_to)
        
        # Tags filter (sample must have ALL specified tags)
        if criteria.tags:
            for tag in criteria.tags:
                # PostgreSQL JSON array contains operator
                filters.append(
                    func.jsonb_exists(
                        func.cast(SampleModel.tags, type_=func.JSONB),
                        tag
                    )
                )
        
        # Apply all filters
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        query = query.order_by(SampleModel.created_at.desc())
        query = query.limit(criteria.limit).offset(criteria.offset)
        
        # Execute query
        samples = query.all()
        
        return samples, total_count
    
    def update_sample(
        self,
        sample_id: str,
        updates: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> SampleModel:
        """
        Update a sample's metadata or tags.
        
        Args:
            sample_id: UUID of the sample
            updates: Dictionary of fields to update
            updated_by: User ID performing the update (required for version control)
        
        Returns:
            Updated SampleModel instance
        
        Raises:
            ValueError: If sample not found or invalid updates
        
        Validates: Requirements 4.5, 4.6
        """
        sample = self.get_sample(sample_id)
        if not sample:
            raise ValueError(f"Sample {sample_id} not found")
        
        # Allowed update fields
        allowed_fields = {
            'category', 'tags', 'metadata_',
            'quality_overall', 'quality_completeness',
            'quality_accuracy', 'quality_consistency'
        }
        
        # Capture old content for version control
        old_content = {
            'data_id': sample.data_id,
            'content': sample.content,
            'category': sample.category,
            'tags': sample.tags,
            'metadata': sample.metadata_,
            'quality_overall': sample.quality_overall,
            'quality_completeness': sample.quality_completeness,
            'quality_accuracy': sample.quality_accuracy,
            'quality_consistency': sample.quality_consistency
        }
        
        # Apply updates
        for field, value in updates.items():
            if field not in allowed_fields:
                raise ValueError(f"Field '{field}' cannot be updated")
            
            # Validate quality scores if being updated
            if field.startswith('quality_') and not (0 <= value <= 1):
                raise ValueError(
                    f"{field} must be between 0 and 1, got {value}"
                )
            
            setattr(sample, field, value)
        
        sample.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(sample)
        
        # Create version snapshot if version control is enabled
        if self.version_control_manager and updated_by:
            new_content = {
                'data_id': sample.data_id,
                'content': sample.content,
                'category': sample.category,
                'tags': sample.tags,
                'metadata': sample.metadata_,
                'quality_overall': sample.quality_overall,
                'quality_completeness': sample.quality_completeness,
                'quality_accuracy': sample.quality_accuracy,
                'quality_consistency': sample.quality_consistency
            }
            
            self.version_control_manager.create_version(
                data_id=sample.data_id,
                content=new_content,
                change_type=ChangeType.CORRECTION,
                created_by=updated_by,
                description=f"Sample updated: {', '.join(updates.keys())}",
                metadata={
                    'sample_id': str(sample.id),
                    'updated_fields': list(updates.keys()),
                    'old_values': {k: old_content.get(k) for k in updates.keys()}
                }
            )
        
        return sample
    
    def delete_sample(self, sample_id: str) -> None:
        """
        Delete a sample from the library.
        
        Args:
            sample_id: UUID of the sample
        
        Raises:
            ValueError: If sample not found
        
        Validates: Requirements 4.1
        """
        sample = self.get_sample(sample_id)
        if not sample:
            raise ValueError(f"Sample {sample_id} not found")
        
        self.db.delete(sample)
        self.db.commit()
    
    def get_samples_by_tag(self, tags: List[str]) -> List[SampleModel]:
        """
        Get samples that have ALL specified tags.
        
        Args:
            tags: List of tags to search for
        
        Returns:
            List of matching SampleModel instances
        
        Validates: Requirements 4.5
        """
        if not tags:
            return []
        
        # Build query with tag filters
        query = self.db.query(SampleModel)
        
        for tag in tags:
            query = query.filter(
                func.jsonb_exists(
                    func.cast(SampleModel.tags, type_=func.JSONB),
                    tag
                )
            )
        
        return query.order_by(SampleModel.created_at.desc()).all()
    
    def track_usage(self, sample_id: str) -> None:
        """
        Track sample usage by incrementing usage count and updating last used timestamp.
        
        Args:
            sample_id: UUID of the sample
        
        Raises:
            ValueError: If sample not found
        
        Validates: Requirements 4.4
        """
        sample = self.get_sample(sample_id)
        if not sample:
            raise ValueError(f"Sample {sample_id} not found")
        
        sample.usage_count += 1
        sample.last_used_at = datetime.utcnow()
        sample.updated_at = datetime.utcnow()
        
        self.db.commit()
