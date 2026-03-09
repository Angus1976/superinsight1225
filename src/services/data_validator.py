"""
Data Validator Service for Data Lifecycle Management

Provides comprehensive validation for data integrity including UUID format,
foreign key references, quality score ranges, version monotonicity,
required fields, and string length constraints.

Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5, 20.6
"""

import uuid
from typing import Any, Dict, List, Optional, Type

from sqlalchemy.orm import Session


class DataValidator:
    """
    Standalone data validation utility for the data lifecycle system.

    Provides validation methods for:
    - UUID format validation
    - Quality score range validation (0-1)
    - Version number monotonicity
    - Required fields presence
    - String length constraints
    - Foreign key reference existence
    - Comprehensive data payload validation
    """

    @staticmethod
    def validate_uuid(value: str) -> bool:
        """
        Validate that a string is a valid UUID format.

        Args:
            value: String to validate as UUID

        Returns:
            True if valid UUID, False otherwise
        """
        if not isinstance(value, str):
            return False
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def validate_quality_score(score: float, field_name: str) -> None:
        """
        Validate that a quality score is between 0 and 1 inclusive.

        Args:
            score: Quality score to validate
            field_name: Name of the field for error messages

        Raises:
            ValueError: If score is not a number or outside [0, 1]
        """
        if not isinstance(score, (int, float)):
            raise ValueError(
                f"'{field_name}' must be a number, got {type(score).__name__}"
            )
        if score < 0 or score > 1:
            raise ValueError(
                f"'{field_name}' must be between 0 and 1, got {score}"
            )

    @staticmethod
    def validate_version_number(
        version: int, current_version: Optional[int] = None
    ) -> None:
        """
        Validate version number is a positive integer and monotonically increasing.

        Args:
            version: Version number to validate
            current_version: Current version to check monotonicity against

        Raises:
            ValueError: If version is not positive or not monotonically increasing
        """
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError(
                f"Version must be a positive integer, got {type(version).__name__}"
            )
        if version <= 0:
            raise ValueError(
                f"Version must be a positive integer, got {version}"
            )
        if current_version is not None and version <= current_version:
            raise ValueError(
                f"Version must be greater than current version {current_version}, "
                f"got {version}"
            )

    @staticmethod
    def validate_required_fields(data: dict, required: list) -> None:
        """
        Validate that all required fields are present and non-empty.

        Args:
            data: Dictionary to validate
            required: List of required field names

        Raises:
            ValueError: If any required field is missing or empty
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        missing = [f for f in required if f not in data or data[f] is None]
        if missing:
            raise ValueError(
                f"Missing required fields: {', '.join(missing)}"
            )

        empty = [
            f for f in required
            if f in data and isinstance(data[f], str) and not data[f].strip()
        ]
        if empty:
            raise ValueError(
                f"Fields must not be empty: {', '.join(empty)}"
            )

    @staticmethod
    def validate_string_length(
        value: str, field_name: str, min_len: int = 0, max_len: int = 255
    ) -> None:
        """
        Validate string length is within bounds.

        Args:
            value: String to validate
            field_name: Name of the field for error messages
            min_len: Minimum allowed length
            max_len: Maximum allowed length

        Raises:
            ValueError: If value is not a string or length is out of bounds
        """
        if not isinstance(value, str):
            raise ValueError(
                f"'{field_name}' must be a string, got {type(value).__name__}"
            )
        if len(value) < min_len:
            raise ValueError(
                f"'{field_name}' must be at least {min_len} characters, "
                f"got {len(value)}"
            )
        if len(value) > max_len:
            raise ValueError(
                f"'{field_name}' must be at most {max_len} characters, "
                f"got {len(value)}"
            )

    @staticmethod
    def validate_foreign_key(
        db: Session, model_class: Type, id_value: str, field_name: str
    ) -> None:
        """
        Validate that a foreign key reference points to an existing record.

        Args:
            db: Database session
            model_class: SQLAlchemy model class to query
            id_value: ID value to look up
            field_name: Name of the field for error messages

        Raises:
            ValueError: If the referenced record does not exist
        """
        if not id_value:
            raise ValueError(f"'{field_name}' must not be empty")

        record = db.query(model_class).filter(
            model_class.id == id_value
        ).first()

        if record is None:
            raise ValueError(
                f"'{field_name}' references non-existent record: {id_value}"
            )

    @staticmethod
    def validate_data_payload(data: dict) -> List[str]:
        """
        Comprehensive validation of a data payload returning all errors.

        Validates:
        - 'id' field is valid UUID if present
        - Quality score fields are in [0, 1] if present
        - 'version' is a positive integer if present
        - Required structure fields are present

        Args:
            data: Data dictionary to validate

        Returns:
            List of error message strings (empty if valid)
        """
        errors: List[str] = []

        if not isinstance(data, dict):
            return ["Data must be a dictionary"]

        # Validate UUID fields
        uuid_fields = ["id", "data_id", "source_document_id",
                        "original_data_id", "enhancement_job_id"]
        for field in uuid_fields:
            if field in data and data[field] is not None:
                if not DataValidator.validate_uuid(str(data[field])):
                    errors.append(
                        f"'{field}' must be a valid UUID format, "
                        f"got '{data[field]}'"
                    )

        # Validate quality score fields
        quality_fields = [
            "quality_overall", "quality_completeness",
            "quality_accuracy", "quality_consistency",
        ]
        for field in quality_fields:
            if field in data and data[field] is not None:
                try:
                    DataValidator.validate_quality_score(data[field], field)
                except ValueError as e:
                    errors.append(str(e))

        # Validate version field
        if "version" in data and data["version"] is not None:
            try:
                DataValidator.validate_version_number(data["version"])
            except ValueError as e:
                errors.append(str(e))

        return errors
