"""
Unit tests for Data Validator Service

Tests UUID validation, quality score ranges, version monotonicity,
required fields, string length, foreign key references, and
comprehensive data payload validation.
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from src.services.data_validator import DataValidator


# ============================================================================
# Test: validate_uuid
# ============================================================================

class TestValidateUuid:
    """Tests for UUID format validation"""

    def test_valid_uuid4(self):
        assert DataValidator.validate_uuid(str(uuid4())) is True

    def test_valid_uuid_with_hyphens(self):
        assert DataValidator.validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True

    def test_valid_uuid_uppercase(self):
        assert DataValidator.validate_uuid("550E8400-E29B-41D4-A716-446655440000") is True

    def test_invalid_uuid_random_string(self):
        assert DataValidator.validate_uuid("not-a-uuid") is False

    def test_invalid_uuid_empty_string(self):
        assert DataValidator.validate_uuid("") is False

    def test_invalid_uuid_none(self):
        assert DataValidator.validate_uuid(None) is False

    def test_invalid_uuid_integer(self):
        assert DataValidator.validate_uuid(12345) is False

    def test_invalid_uuid_partial(self):
        assert DataValidator.validate_uuid("550e8400-e29b-41d4") is False


# ============================================================================
# Test: validate_quality_score
# ============================================================================

class TestValidateQualityScore:
    """Tests for quality score range validation (0-1)"""

    def test_valid_score_zero(self):
        DataValidator.validate_quality_score(0.0, "quality_overall")

    def test_valid_score_one(self):
        DataValidator.validate_quality_score(1.0, "quality_overall")

    def test_valid_score_mid(self):
        DataValidator.validate_quality_score(0.5, "quality_accuracy")

    def test_valid_score_integer_zero(self):
        DataValidator.validate_quality_score(0, "quality_overall")

    def test_valid_score_integer_one(self):
        DataValidator.validate_quality_score(1, "quality_overall")

    def test_invalid_score_negative(self):
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            DataValidator.validate_quality_score(-0.1, "quality_overall")

    def test_invalid_score_above_one(self):
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            DataValidator.validate_quality_score(1.1, "quality_completeness")

    def test_invalid_score_string(self):
        with pytest.raises(ValueError, match="must be a number"):
            DataValidator.validate_quality_score("0.5", "quality_overall")

    def test_invalid_score_none(self):
        with pytest.raises(ValueError, match="must be a number"):
            DataValidator.validate_quality_score(None, "quality_overall")

    def test_error_includes_field_name(self):
        with pytest.raises(ValueError, match="quality_accuracy"):
            DataValidator.validate_quality_score(2.0, "quality_accuracy")


# ============================================================================
# Test: validate_version_number
# ============================================================================

class TestValidateVersionNumber:
    """Tests for version number validation and monotonicity"""

    def test_valid_version_one(self):
        DataValidator.validate_version_number(1)

    def test_valid_version_large(self):
        DataValidator.validate_version_number(999)

    def test_valid_version_monotonic(self):
        DataValidator.validate_version_number(3, current_version=2)

    def test_invalid_version_zero(self):
        with pytest.raises(ValueError, match="positive integer"):
            DataValidator.validate_version_number(0)

    def test_invalid_version_negative(self):
        with pytest.raises(ValueError, match="positive integer"):
            DataValidator.validate_version_number(-1)

    def test_invalid_version_float(self):
        with pytest.raises(ValueError, match="positive integer"):
            DataValidator.validate_version_number(1.5)

    def test_invalid_version_string(self):
        with pytest.raises(ValueError, match="positive integer"):
            DataValidator.validate_version_number("1")

    def test_invalid_version_bool(self):
        with pytest.raises(ValueError, match="positive integer"):
            DataValidator.validate_version_number(True)

    def test_invalid_version_not_monotonic_equal(self):
        with pytest.raises(ValueError, match="greater than current version"):
            DataValidator.validate_version_number(2, current_version=2)

    def test_invalid_version_not_monotonic_less(self):
        with pytest.raises(ValueError, match="greater than current version 5"):
            DataValidator.validate_version_number(3, current_version=5)


# ============================================================================
# Test: validate_required_fields
# ============================================================================

class TestValidateRequiredFields:
    """Tests for required fields validation"""

    def test_all_fields_present(self):
        data = {"name": "test", "category": "A"}
        DataValidator.validate_required_fields(data, ["name", "category"])

    def test_missing_field(self):
        data = {"name": "test"}
        with pytest.raises(ValueError, match="Missing required fields: category"):
            DataValidator.validate_required_fields(data, ["name", "category"])

    def test_multiple_missing_fields(self):
        with pytest.raises(ValueError, match="Missing required fields"):
            DataValidator.validate_required_fields({}, ["name", "category"])

    def test_none_value_treated_as_missing(self):
        data = {"name": None}
        with pytest.raises(ValueError, match="Missing required fields: name"):
            DataValidator.validate_required_fields(data, ["name"])

    def test_empty_string_treated_as_empty(self):
        data = {"name": "  "}
        with pytest.raises(ValueError, match="Fields must not be empty: name"):
            DataValidator.validate_required_fields(data, ["name"])

    def test_non_dict_input(self):
        with pytest.raises(ValueError, match="Data must be a dictionary"):
            DataValidator.validate_required_fields("not a dict", ["name"])

    def test_empty_required_list(self):
        DataValidator.validate_required_fields({"a": 1}, [])


# ============================================================================
# Test: validate_string_length
# ============================================================================

class TestValidateStringLength:
    """Tests for string length validation"""

    def test_valid_length(self):
        DataValidator.validate_string_length("hello", "name", min_len=1, max_len=10)

    def test_exact_min_length(self):
        DataValidator.validate_string_length("ab", "name", min_len=2, max_len=10)

    def test_exact_max_length(self):
        DataValidator.validate_string_length("abcde", "name", min_len=1, max_len=5)

    def test_too_short(self):
        with pytest.raises(ValueError, match="at least 3 characters"):
            DataValidator.validate_string_length("ab", "name", min_len=3, max_len=10)

    def test_too_long(self):
        with pytest.raises(ValueError, match="at most 5 characters"):
            DataValidator.validate_string_length("abcdef", "name", min_len=1, max_len=5)

    def test_not_a_string(self):
        with pytest.raises(ValueError, match="must be a string"):
            DataValidator.validate_string_length(123, "name", min_len=1, max_len=10)

    def test_error_includes_field_name(self):
        with pytest.raises(ValueError, match="'title'"):
            DataValidator.validate_string_length("", "title", min_len=1, max_len=10)


# ============================================================================
# Test: validate_foreign_key
# ============================================================================

class TestValidateForeignKey:
    """Tests for foreign key reference validation"""

    def _make_mock_db(self, record_exists: bool):
        """Helper to create a mock db session with chained query."""
        mock_db = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = MagicMock() if record_exists else None
        mock_db.query.return_value.filter.return_value = mock_filter
        return mock_db

    def test_existing_record(self):
        mock_db = self._make_mock_db(record_exists=True)
        mock_model = MagicMock()

        DataValidator.validate_foreign_key(
            mock_db, mock_model, str(uuid4()), "sample_id"
        )
        mock_db.query.assert_called_once_with(mock_model)

    def test_non_existent_record(self):
        mock_db = self._make_mock_db(record_exists=False)
        mock_model = MagicMock()

        test_id = str(uuid4())
        with pytest.raises(ValueError, match="references non-existent record"):
            DataValidator.validate_foreign_key(
                mock_db, mock_model, test_id, "sample_id"
            )

    def test_empty_id_value(self):
        mock_db = MagicMock()
        with pytest.raises(ValueError, match="must not be empty"):
            DataValidator.validate_foreign_key(mock_db, MagicMock, "", "sample_id")


# ============================================================================
# Test: validate_data_payload
# ============================================================================

class TestValidateDataPayload:
    """Tests for comprehensive data payload validation"""

    def test_valid_payload(self):
        data = {
            "id": str(uuid4()),
            "quality_overall": 0.8,
            "quality_completeness": 0.9,
            "quality_accuracy": 0.7,
            "quality_consistency": 0.85,
            "version": 1,
        }
        errors = DataValidator.validate_data_payload(data)
        assert errors == []

    def test_invalid_uuid(self):
        data = {"id": "not-a-uuid"}
        errors = DataValidator.validate_data_payload(data)
        assert len(errors) == 1
        assert "valid UUID format" in errors[0]

    def test_invalid_quality_score(self):
        data = {"quality_overall": 1.5}
        errors = DataValidator.validate_data_payload(data)
        assert len(errors) == 1
        assert "between 0 and 1" in errors[0]

    def test_invalid_version(self):
        data = {"version": -1}
        errors = DataValidator.validate_data_payload(data)
        assert len(errors) == 1
        assert "positive integer" in errors[0]

    def test_multiple_errors(self):
        data = {
            "id": "bad-uuid",
            "quality_overall": 2.0,
            "version": 0,
        }
        errors = DataValidator.validate_data_payload(data)
        assert len(errors) == 3

    def test_non_dict_input(self):
        errors = DataValidator.validate_data_payload("not a dict")
        assert errors == ["Data must be a dictionary"]

    def test_empty_dict(self):
        errors = DataValidator.validate_data_payload({})
        assert errors == []

    def test_none_values_skipped(self):
        data = {"id": None, "quality_overall": None, "version": None}
        errors = DataValidator.validate_data_payload(data)
        assert errors == []

    def test_multiple_uuid_fields(self):
        data = {
            "id": "bad",
            "data_id": "also-bad",
            "original_data_id": str(uuid4()),  # valid
        }
        errors = DataValidator.validate_data_payload(data)
        assert len(errors) == 2

    def test_multiple_quality_fields_invalid(self):
        data = {
            "quality_overall": -0.1,
            "quality_completeness": 1.5,
            "quality_accuracy": 0.5,  # valid
            "quality_consistency": "bad",
        }
        errors = DataValidator.validate_data_payload(data)
        assert len(errors) == 3
