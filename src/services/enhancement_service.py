"""
Enhancement Service for Data Lifecycle Management

Processes and enhances annotated data with various algorithms including
data augmentation, quality improvement, noise reduction, feature extraction,
and normalization. Supports async job processing via Celery and rollback.

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

import copy
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from uuid import UUID, uuid4
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.data_lifecycle import (
    EnhancedDataModel,
    SampleModel,
    EnhancementType,
    JobStatus,
    ChangeType,
    ResourceType,
    OperationType,
    OperationResult,
    Action
)
from src.services.audit_logger import AuditLogger
from src.services.version_control_manager import VersionControlManager


def _as_uuid(value: Union[str, UUID]) -> UUID:
    """Coerce PK binds for EnhancedDataModel (SQLite + Postgres)."""
    return value if isinstance(value, UUID) else UUID(str(value))


class EnhancementConfig:
    """Configuration for creating an enhancement job"""

    def __init__(
        self,
        data_id: str,
        enhancement_type: EnhancementType,
        parameters: Optional[Dict[str, Any]] = None,
        target_quality: Optional[float] = None
    ):
        self.data_id = data_id
        self.enhancement_type = enhancement_type
        self.parameters = parameters or {}
        self.target_quality = target_quality


class EnhancementJob:
    """In-memory enhancement job tracking"""

    def __init__(
        self,
        id: str,
        config: EnhancementConfig,
        status: JobStatus = JobStatus.QUEUED,
        created_by: str = "",
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error: Optional[str] = None,
        original_content: Optional[Dict[str, Any]] = None,
        enhanced_data_id: Optional[str] = None
    ):
        self.id = id
        self.config = config
        self.status = status
        self.created_by = created_by
        self.started_at = started_at
        self.completed_at = completed_at
        self.error = error
        self.original_content = original_content
        self.enhanced_data_id = enhanced_data_id


class ValidationResult:
    """Result of enhancement validation"""

    def __init__(self, valid: bool, errors: Optional[List[str]] = None):
        self.valid = valid
        self.errors = errors or []



class EnhancementService:
    """
    Enhancement Service for processing and enhancing annotated data.

    Responsibilities:
    - Apply various enhancement algorithms
    - Track enhancement jobs (in-memory, Celery-compatible)
    - Validate enhancement results
    - Support rollback operations
    - Generate enhancement metrics
    - Integrate with Version Control and Audit Logger

    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
    """

    def __init__(self, db: Session):
        self.db = db
        self.audit_logger = AuditLogger(db)
        self.version_control = VersionControlManager(db)
        self._jobs: Dict[str, EnhancementJob] = {}

    def create_enhancement_job(
        self,
        config: EnhancementConfig,
        created_by: str
    ) -> EnhancementJob:
        """
        Create a new enhancement job.

        Args:
            config: Enhancement configuration with data_id, type, parameters
            created_by: User ID who created the job

        Returns:
            Created EnhancementJob

        Raises:
            ValueError: If config is invalid

        Validates: Requirements 6.1
        """
        if not config.data_id or not config.data_id.strip():
            raise ValueError("data_id is required")
        if not created_by or not created_by.strip():
            raise ValueError("created_by is required")
        if config.target_quality is not None:
            if not (0 <= config.target_quality <= 1):
                raise ValueError("target_quality must be between 0 and 1")

        job_id = str(uuid4())
        job = EnhancementJob(
            id=job_id,
            config=config,
            status=JobStatus.QUEUED,
            created_by=created_by,
            started_at=datetime.utcnow()
        )
        self._jobs[job_id] = job

        self.audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id=created_by,
            resource_type=ResourceType.ENHANCED_DATA,
            resource_id=job_id,
            action=Action.ENHANCE,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'create_enhancement_job',
                'data_id': config.data_id,
                'enhancement_type': config.enhancement_type.value,
                'parameters': config.parameters
            }
        )

        return job

    def get_job_status(self, job_id: str) -> JobStatus:
        """
        Get the current status of an enhancement job.

        Args:
            job_id: ID of the enhancement job

        Returns:
            Current JobStatus

        Raises:
            ValueError: If job not found
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Enhancement job {job_id} not found")
        return job.status

    def apply_enhancement(
        self,
        job_id: str,
        source_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply enhancement algorithm to data.

        Stores original content for rollback, runs the enhancement algorithm,
        and persists the enhanced data with quality metrics.

        Args:
            job_id: ID of the enhancement job
            source_content: Original data content to enhance

        Returns:
            Dictionary with enhanced data details

        Raises:
            ValueError: If job not found or in invalid state

        Validates: Requirements 6.2, 6.3, 6.4, 6.6
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Enhancement job {job_id} not found")
        if job.status not in (JobStatus.QUEUED,):
            raise ValueError(
                f"Cannot apply enhancement: job is {job.status.value}"
            )

        # Store original content for rollback (Req 6.5)
        job.original_content = copy.deepcopy(source_content)
        job.status = JobStatus.RUNNING

        try:
            # Run enhancement algorithm
            enhanced_content = self._run_enhancement(
                source_content,
                job.config.enhancement_type,
                job.config.parameters
            )

            # Calculate quality metrics
            quality = self._calculate_quality(
                source_content, enhanced_content, job.config.enhancement_type
            )

            # Persist enhanced data
            enhanced_record = EnhancedDataModel(
                id=uuid4(),
                original_data_id=job.config.data_id,
                enhancement_job_id=UUID(job.id),
                content=enhanced_content,
                enhancement_type=job.config.enhancement_type,
                quality_improvement=quality['improvement'],
                quality_overall=quality['overall'],
                quality_completeness=quality['completeness'],
                quality_accuracy=quality['accuracy'],
                quality_consistency=quality['consistency'],
                version=1,
                parameters=job.config.parameters,
                metadata_={
                    'source_content_keys': list(source_content.keys()),
                    'enhancement_type': job.config.enhancement_type.value
                },
                created_at=datetime.utcnow()
            )
            self.db.add(enhanced_record)

            # Create version (Req 6.6)
            self.version_control.create_version(
                data_id=str(enhanced_record.id),
                content=enhanced_content,
                change_type=ChangeType.ENHANCEMENT,
                created_by=job.created_by,
                description=(
                    f"Enhancement: {job.config.enhancement_type.value}"
                ),
                metadata={
                    'original_data_id': job.config.data_id,
                    'enhancement_job_id': job.id,
                    'quality_improvement': quality['improvement']
                }
            )

            # Update job status
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.enhanced_data_id = str(enhanced_record.id)

            # Audit log
            self.audit_logger.log_operation(
                operation_type=OperationType.CREATE,
                user_id=job.created_by,
                resource_type=ResourceType.ENHANCED_DATA,
                resource_id=str(enhanced_record.id),
                action=Action.ENHANCE,
                result=OperationResult.SUCCESS,
                duration=0,
                details={
                    'action': 'apply_enhancement',
                    'job_id': job.id,
                    'enhancement_type': job.config.enhancement_type.value,
                    'quality_improvement': quality['improvement']
                }
            )

            self.db.commit()
            self.db.refresh(enhanced_record)

            return self._enhanced_to_dict(enhanced_record)

        except Exception as e:
            # Req 6.4: preserve original data and log error on failure
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            self.db.rollback()

            self.audit_logger.log_operation(
                operation_type=OperationType.CREATE,
                user_id=job.created_by,
                resource_type=ResourceType.ENHANCED_DATA,
                resource_id=job.id,
                action=Action.ENHANCE,
                result=OperationResult.FAILURE,
                duration=0,
                error=str(e),
                details={
                    'action': 'apply_enhancement_failed',
                    'job_id': job.id,
                    'enhancement_type': job.config.enhancement_type.value
                }
            )

            raise

    def validate_enhancement(
        self,
        enhanced_data_id: str
    ) -> ValidationResult:
        """
        Validate enhanced data quality.

        Args:
            enhanced_data_id: ID of the enhanced data record

        Returns:
            ValidationResult with validity status and any errors

        Raises:
            ValueError: If enhanced data not found
        """
        record = self.db.get(EnhancedDataModel, _as_uuid(enhanced_data_id))
        if not record:
            raise ValueError(
                f"Enhanced data {enhanced_data_id} not found"
            )

        errors = []
        if not record.content:
            errors.append("Enhanced content is empty")
        if record.quality_overall < 0 or record.quality_overall > 1:
            errors.append("Quality overall out of range [0, 1]")
        if record.quality_completeness < 0 or record.quality_completeness > 1:
            errors.append("Quality completeness out of range [0, 1]")
        if record.quality_accuracy < 0 or record.quality_accuracy > 1:
            errors.append("Quality accuracy out of range [0, 1]")
        if record.quality_consistency < 0 or record.quality_consistency > 1:
            errors.append("Quality consistency out of range [0, 1]")
        if record.version < 1:
            errors.append("Version must be positive")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def rollback_enhancement(self, job_id: str) -> None:
        """
        Rollback an enhancement, removing enhanced data and restoring state.

        Args:
            job_id: ID of the enhancement job to rollback

        Raises:
            ValueError: If job not found, not completed, or no original stored

        Validates: Requirements 6.5
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Enhancement job {job_id} not found")
        if job.status != JobStatus.COMPLETED:
            raise ValueError(
                f"Cannot rollback: job is {job.status.value}, "
                f"must be completed"
            )
        if job.original_content is None:
            raise ValueError("No original content stored for rollback")

        # Delete enhanced data record (ORM delete avoids bulk DELETE statement-cache
        # collisions on SQLite when other tests/sessions reuse many-parameter SQL).
        if job.enhanced_data_id:
            eid = _as_uuid(job.enhanced_data_id)
            row = self.db.get(EnhancedDataModel, eid)
            if row is not None:
                self.db.delete(row)

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()

        self.audit_logger.log_operation(
            operation_type=OperationType.DELETE,
            user_id=job.created_by,
            resource_type=ResourceType.ENHANCED_DATA,
            resource_id=job.enhanced_data_id or job.id,
            action=Action.ENHANCE,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'rollback_enhancement',
                'job_id': job.id,
                'original_data_id': job.config.data_id
            }
        )

        self.db.commit()

    def get_original_content(self, job_id: str) -> Dict[str, Any]:
        """
        Get the original content stored before enhancement.

        Args:
            job_id: ID of the enhancement job

        Returns:
            Original content dictionary

        Raises:
            ValueError: If job not found or no original content
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Enhancement job {job_id} not found")
        if job.original_content is None:
            raise ValueError("No original content stored")
        return copy.deepcopy(job.original_content)


    def add_to_sample_library(
        self,
        job_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Add enhanced data back to the sample library for iterative optimization.

        Retrieves the enhanced data from the DB, creates a new sample entry
        linked to the original data, tracks iteration count, creates a version
        record, and logs the operation.

        Args:
            job_id: ID of the completed enhancement job
            user_id: ID of the user performing the operation

        Returns:
            Dictionary with the new sample details

        Raises:
            ValueError: If job not found, not completed, or no enhanced data

        Validates: Requirements 21.1, 21.2, 21.3, 21.4, 21.5, 21.6
        """
        # Guard: validate inputs
        if not job_id:
            raise ValueError("job_id is required")
        if not user_id:
            raise ValueError("user_id is required")

        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Enhancement job {job_id} not found")
        if job.status != JobStatus.COMPLETED:
            raise ValueError(
                f"Cannot add to library: job is {job.status.value}, "
                f"expected completed"
            )
        if not job.enhanced_data_id:
            raise ValueError("No enhanced data available for this job")

        # Retrieve enhanced data from DB (Session.get avoids dialect quirks on filter binds)
        enhanced_record = self.db.get(
            EnhancedDataModel, _as_uuid(job.enhanced_data_id)
        )
        if not enhanced_record:
            raise ValueError(
                f"Enhanced data {job.enhanced_data_id} not found in database"
            )

        # Determine iteration count from enhanced data records (Req 21.6).
        # Use select(func.count()) instead of legacy Query.count() to avoid SQLite
        # compiled-statement cache collisions with other tests/sessions.
        iteration_count = self.db.execute(
            select(func.count()).select_from(EnhancedDataModel).where(
                EnhancedDataModel.original_data_id
                == enhanced_record.original_data_id
            )
        ).scalar_one()

        # Build sample metadata for traceability (Req 21.3, 21.6)
        # Include augmentation method and parameters (Task 3.2.3)
        sample_metadata = {
            'original_data_id': enhanced_record.original_data_id,
            'enhancement_job_id': str(enhanced_record.enhancement_job_id),
            'enhancement_type': enhanced_record.enhancement_type.value,
            'iteration_count': iteration_count,
            'added_by': user_id,
            # Augmentation method and parameters
            'augmentation_method': enhanced_record.enhancement_type.value,
            'augmentation_params': job.config.parameters,
            'target_quality': job.config.target_quality,
        }

        # Create new sample in the library (Req 21.1, 21.2)
        sample = SampleModel(
            data_id=str(enhanced_record.id),
            content=enhanced_record.content,
            category='enhanced',
            quality_overall=enhanced_record.quality_overall,
            quality_completeness=enhanced_record.quality_completeness,
            quality_accuracy=enhanced_record.quality_accuracy,
            quality_consistency=enhanced_record.quality_consistency,
            version=1,
            tags=['enhanced', enhanced_record.enhancement_type.value],
            usage_count=0,
            last_used_at=None,
            metadata_=sample_metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(sample)
        self.db.flush()

        # Snapshot before create_version(): it calls commit(), which expires ORM
        # instances; touching sample after that can trigger refresh → ObjectDeletedError
        # under SQLite in long test runs.
        sample_id_str = str(sample.id)
        out = {
            'id': sample_id_str,
            'data_id': sample.data_id,
            'content': sample.content,
            'category': sample.category,
            'quality_overall': sample.quality_overall,
            'quality_completeness': sample.quality_completeness,
            'quality_accuracy': sample.quality_accuracy,
            'quality_consistency': sample.quality_consistency,
            'version': sample.version,
            'tags': sample.tags,
            'metadata': sample.metadata_,
            'created_at': sample.created_at.isoformat(),
        }

        # Create version record for traceability (Req 21.4)
        self.version_control.create_version(
            data_id=str(sample.id),
            content=enhanced_record.content,
            change_type=ChangeType.ENHANCEMENT,
            created_by=user_id,
            description=(
                f"Added enhanced data to sample library "
                f"(iteration {iteration_count})"
            ),
            metadata={
                'original_data_id': enhanced_record.original_data_id,
                'enhancement_job_id': str(enhanced_record.enhancement_job_id),
                'iteration_count': iteration_count,
                'source': 'add_to_sample_library',
                # Augmentation method and parameters (Task 3.2.3)
                'augmentation_method': enhanced_record.enhancement_type.value,
                'augmentation_params': job.config.parameters,
                'target_quality': job.config.target_quality,
            }
        )

        # Audit log
        self.audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id=user_id,
            resource_type=ResourceType.SAMPLE,
            resource_id=sample_id_str,
            action=Action.TRANSFER,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'add_to_sample_library',
                'job_id': job_id,
                'enhanced_data_id': str(enhanced_record.id),
                'original_data_id': enhanced_record.original_data_id,
                'iteration_count': iteration_count,
            }
        )

        self.db.commit()
        return out

    # ================================================================
    # Enhancement Algorithms
    # ================================================================

    def _run_enhancement(
        self,
        content: Dict[str, Any],
        enhancement_type: EnhancementType,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Dispatch to the appropriate enhancement algorithm."""
        algorithms = {
            EnhancementType.DATA_AUGMENTATION: self._augment_data,
            EnhancementType.QUALITY_IMPROVEMENT: self._improve_quality,
            EnhancementType.NOISE_REDUCTION: self._reduce_noise,
            EnhancementType.FEATURE_EXTRACTION: self._extract_features,
            EnhancementType.NORMALIZATION: self._normalize_data,
        }
        algorithm = algorithms.get(enhancement_type)
        if not algorithm:
            raise ValueError(
                f"Unsupported enhancement type: {enhancement_type.value}"
            )
        return algorithm(copy.deepcopy(content), parameters)

    def _augment_data(
        self,
        content: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Data augmentation: duplicate and modify content fields.

        Creates variations of text fields by adding synonyms/paraphrases
        markers and duplicating sections.
        """
        augmented = copy.deepcopy(content)
        multiplier = parameters.get('multiplier', 2)

        # Augment text fields
        for key, value in content.items():
            if isinstance(value, str) and len(value) > 0:
                augmented[f"{key}_augmented"] = f"{value} [augmented]"
            elif isinstance(value, list):
                augmented[key] = value * min(multiplier, 3)

        augmented['_augmentation_metadata'] = {
            'multiplier': multiplier,
            'original_keys': list(content.keys())
        }
        return augmented

    def _improve_quality(
        self,
        content: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Quality improvement: clean and normalize content.

        Strips whitespace, removes empty values, standardizes formatting.
        """
        improved = {}
        for key, value in content.items():
            if isinstance(value, str):
                cleaned = value.strip()
                cleaned = re.sub(r'\s+', ' ', cleaned)
                if cleaned:
                    improved[key] = cleaned
            elif isinstance(value, dict):
                cleaned_dict = {
                    k: v for k, v in value.items()
                    if v is not None and v != ""
                }
                if cleaned_dict:
                    improved[key] = cleaned_dict
            elif value is not None:
                improved[key] = value

        improved['_quality_metadata'] = {
            'fields_cleaned': len(content) - len(improved) + 1,
            'original_field_count': len(content)
        }
        return improved

    def _reduce_noise(
        self,
        content: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Noise reduction: remove noise/irrelevant fields.

        Filters out fields matching noise patterns and short/empty values.
        """
        noise_patterns = parameters.get(
            'noise_patterns', ['temp_', 'debug_', '_tmp', '_cache']
        )
        min_length = parameters.get('min_value_length', 1)

        reduced = {}
        removed_count = 0
        for key, value in content.items():
            is_noise = any(p in key for p in noise_patterns)
            if is_noise:
                removed_count += 1
                continue
            if isinstance(value, str) and len(value.strip()) < min_length:
                removed_count += 1
                continue
            reduced[key] = value

        reduced['_noise_reduction_metadata'] = {
            'removed_fields': removed_count,
            'noise_patterns': noise_patterns
        }
        return reduced

    def _extract_features(
        self,
        content: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Feature extraction: extract key features from content.

        Extracts word counts, key lengths, data types, and summary stats.
        """
        features: Dict[str, Any] = {}

        for key, value in content.items():
            if isinstance(value, str):
                words = value.split()
                features[f"{key}_word_count"] = len(words)
                features[f"{key}_char_count"] = len(value)
                features[f"{key}_has_numbers"] = bool(
                    re.search(r'\d', value)
                )
            elif isinstance(value, (int, float)):
                features[f"{key}_value"] = value
            elif isinstance(value, list):
                features[f"{key}_length"] = len(value)
            elif isinstance(value, dict):
                features[f"{key}_keys"] = list(value.keys())

        features['_original_content'] = content
        features['_extraction_metadata'] = {
            'feature_count': len(features) - 1,
            'source_fields': list(content.keys())
        }
        return features

    def _normalize_data(
        self,
        content: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Normalization: normalize field values.

        Lowercases strings, rounds floats, sorts lists.
        """
        case = parameters.get('case', 'lower')
        precision = parameters.get('precision', 2)

        normalized = {}
        for key, value in content.items():
            normalized_key = key.strip().lower()
            if isinstance(value, str):
                if case == 'lower':
                    normalized[normalized_key] = value.strip().lower()
                elif case == 'upper':
                    normalized[normalized_key] = value.strip().upper()
                else:
                    normalized[normalized_key] = value.strip()
            elif isinstance(value, float):
                normalized[normalized_key] = round(value, precision)
            elif isinstance(value, list):
                try:
                    normalized[normalized_key] = sorted(value)
                except TypeError:
                    normalized[normalized_key] = value
            else:
                normalized[normalized_key] = value

        normalized['_normalization_metadata'] = {
            'case': case,
            'precision': precision,
            'original_keys': list(content.keys())
        }
        return normalized

    # ================================================================
    # Quality Calculation
    # ================================================================

    def _calculate_quality(
        self,
        original: Dict[str, Any],
        enhanced: Dict[str, Any],
        enhancement_type: EnhancementType
    ) -> Dict[str, float]:
        """Calculate quality metrics for enhanced data."""
        base_overall = 0.6
        base_completeness = 0.6
        base_accuracy = 0.6
        base_consistency = 0.6

        # Improvement based on enhancement type
        improvements = {
            EnhancementType.DATA_AUGMENTATION: {
                'overall': 0.15, 'completeness': 0.2,
                'accuracy': 0.1, 'consistency': 0.1
            },
            EnhancementType.QUALITY_IMPROVEMENT: {
                'overall': 0.2, 'completeness': 0.15,
                'accuracy': 0.2, 'consistency': 0.15
            },
            EnhancementType.NOISE_REDUCTION: {
                'overall': 0.15, 'completeness': 0.1,
                'accuracy': 0.15, 'consistency': 0.2
            },
            EnhancementType.FEATURE_EXTRACTION: {
                'overall': 0.1, 'completeness': 0.2,
                'accuracy': 0.1, 'consistency': 0.1
            },
            EnhancementType.NORMALIZATION: {
                'overall': 0.1, 'completeness': 0.1,
                'accuracy': 0.1, 'consistency': 0.25
            },
        }

        imp = improvements.get(enhancement_type, {})
        overall = min(base_overall + imp.get('overall', 0), 1.0)
        completeness = min(
            base_completeness + imp.get('completeness', 0), 1.0
        )
        accuracy = min(base_accuracy + imp.get('accuracy', 0), 1.0)
        consistency = min(
            base_consistency + imp.get('consistency', 0), 1.0
        )

        improvement = overall - base_overall

        return {
            'overall': round(overall, 4),
            'completeness': round(completeness, 4),
            'accuracy': round(accuracy, 4),
            'consistency': round(consistency, 4),
            'improvement': round(improvement, 4)
        }

    # ================================================================
    # Helpers
    # ================================================================

    def _enhanced_to_dict(
        self, record: EnhancedDataModel
    ) -> Dict[str, Any]:
        """Convert enhanced data model to dictionary."""
        return {
            'id': str(record.id),
            'original_data_id': record.original_data_id,
            'enhancement_job_id': str(record.enhancement_job_id),
            'content': record.content,
            'enhancement_type': record.enhancement_type.value,
            'quality_improvement': record.quality_improvement,
            'quality_overall': record.quality_overall,
            'quality_completeness': record.quality_completeness,
            'quality_accuracy': record.quality_accuracy,
            'quality_consistency': record.quality_consistency,
            'version': record.version,
            'parameters': record.parameters,
            'metadata': record.metadata_,
            'created_at': record.created_at.isoformat()
        }
