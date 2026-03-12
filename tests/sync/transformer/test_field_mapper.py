"""
Unit tests for FieldMapper.

Tests field mapping, type conversion, and schema validation.
"""

import pytest
from src.sync.transformer.field_mapper import (
    FieldMapper,
    MappingRule,
    MappedData,
    ValidationError,
)


class TestFieldMapper:
    """Test FieldMapper functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = FieldMapper()

    def test_simple_field_mapping(self):
        """Test basic field name mapping."""
        data = {"name": "John", "age": 30}
        rules = [
            MappingRule(source_field="name", target_field="full_name"),
            MappingRule(source_field="age", target_field="years"),
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["full_name"] == "John"
        assert result.data["years"] == 30
        assert len(result.errors) == 0

    def test_type_conversion_string_to_int(self):
        """Test type conversion from string to int."""
        data = {"count": "42"}
        rules = [
            MappingRule(
                source_field="count",
                target_field="count",
                type_conversion="int"
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["count"] == 42
        assert isinstance(result.data["count"], int)

    def test_type_conversion_int_to_string(self):
        """Test type conversion from int to string."""
        data = {"id": 123}
        rules = [
            MappingRule(
                source_field="id",
                target_field="id_str",
                type_conversion="string"
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["id_str"] == "123"
        assert isinstance(result.data["id_str"], str)

    def test_type_conversion_string_to_float(self):
        """Test type conversion from string to float."""
        data = {"price": "19.99"}
        rules = [
            MappingRule(
                source_field="price",
                target_field="price",
                type_conversion="float"
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["price"] == 19.99
        assert isinstance(result.data["price"], float)

    def test_type_conversion_to_bool(self):
        """Test type conversion to boolean."""
        data = {"active": "true", "enabled": 1, "disabled": 0}
        rules = [
            MappingRule(source_field="active", target_field="active", type_conversion="bool"),
            MappingRule(source_field="enabled", target_field="enabled", type_conversion="bool"),
            MappingRule(source_field="disabled", target_field="disabled", type_conversion="bool"),
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["active"] is True
        assert result.data["enabled"] is True
        assert result.data["disabled"] is False

    def test_transform_uppercase(self):
        """Test uppercase transformation."""
        data = {"name": "john doe"}
        rules = [
            MappingRule(
                source_field="name",
                target_field="name",
                transform="uppercase"
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["name"] == "JOHN DOE"

    def test_transform_lowercase(self):
        """Test lowercase transformation."""
        data = {"email": "USER@EXAMPLE.COM"}
        rules = [
            MappingRule(
                source_field="email",
                target_field="email",
                transform="lowercase"
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["email"] == "user@example.com"

    def test_transform_trim(self):
        """Test trim transformation."""
        data = {"name": "  John Doe  "}
        rules = [
            MappingRule(
                source_field="name",
                target_field="name",
                transform="trim"
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["name"] == "John Doe"

    def test_nullable_field_with_null_value(self):
        """Test nullable field with null value."""
        data = {"name": None}
        rules = [
            MappingRule(
                source_field="name",
                target_field="name",
                nullable=True
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["name"] is None

    def test_non_nullable_field_with_null_value(self):
        """Test non-nullable field with null value."""
        data = {"name": None}
        rules = [
            MappingRule(
                source_field="name",
                target_field="name",
                nullable=False
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert not result.success
        assert len(result.errors) > 0
        assert "null but not nullable" in result.errors[0]

    def test_default_value_for_missing_field(self):
        """Test default value when field is missing."""
        data = {}
        rules = [
            MappingRule(
                source_field="status",
                target_field="status",
                default_value="active"
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["status"] == "active"

    def test_default_value_for_null_field(self):
        """Test default value when field is null."""
        data = {"status": None}
        rules = [
            MappingRule(
                source_field="status",
                target_field="status",
                nullable=False,
                default_value="inactive"
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["status"] == "inactive"

    def test_missing_required_field(self):
        """Test error when required field is missing."""
        data = {}
        rules = [
            MappingRule(
                source_field="required_field",
                target_field="required_field",
                nullable=False
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert not result.success
        assert len(result.errors) > 0
        assert "not found in source data" in result.errors[0]

    def test_invalid_type_conversion(self):
        """Test error on invalid type conversion."""
        data = {"value": "not_a_number"}
        rules = [
            MappingRule(
                source_field="value",
                target_field="value",
                type_conversion="int"
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert not result.success
        assert len(result.errors) > 0

    def test_dict_rules_conversion(self):
        """Test that dict rules are converted to MappingRule objects."""
        data = {"name": "John"}
        rules = [
            {
                "source_field": "name",
                "target_field": "full_name"
            }
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["full_name"] == "John"

    def test_combined_conversion_and_transform(self):
        """Test combining type conversion and transformation."""
        data = {"email": "  USER@EXAMPLE.COM  "}
        rules = [
            MappingRule(
                source_field="email",
                target_field="email",
                type_conversion="string",
                transform="lowercase"
            )
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        # Note: trim is not applied automatically, only the specified transform
        assert result.data["email"] == "  user@example.com  "


class TestFieldMapperValidation:
    """Test FieldMapper schema validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = FieldMapper()

    def test_validate_valid_mapping(self):
        """Test validation of valid mapping rules."""
        source_schema = {
            "name": {"type": "string", "nullable": True},
            "age": {"type": "int", "nullable": False},
        }
        target_schema = {
            "full_name": {"type": "string", "nullable": True},
            "years": {"type": "int", "nullable": False},
        }
        rules = [
            MappingRule(source_field="name", target_field="full_name"),
            MappingRule(source_field="age", target_field="years"),
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 0

    def test_validate_missing_source_field(self):
        """Test validation error for missing source field."""
        source_schema = {"name": "string"}
        target_schema = {"full_name": "string"}
        rules = [
            MappingRule(source_field="missing_field", target_field="full_name")
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 1
        assert errors[0].error_type == "missing_source_field"
        assert "missing_field" in errors[0].message

    def test_validate_missing_target_field(self):
        """Test validation error for missing target field."""
        source_schema = {"name": "string"}
        target_schema = {"full_name": "string"}
        rules = [
            MappingRule(source_field="name", target_field="missing_target")
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 1
        assert errors[0].error_type == "missing_target_field"
        assert "missing_target" in errors[0].message

    def test_validate_duplicate_target_mapping(self):
        """Test validation error for duplicate target field mapping."""
        source_schema = {"name": "string", "full_name": "string"}
        target_schema = {"target_name": "string"}
        rules = [
            MappingRule(source_field="name", target_field="target_name"),
            MappingRule(source_field="full_name", target_field="target_name"),
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 1
        assert errors[0].error_type == "duplicate_target_mapping"

    def test_validate_type_compatibility(self):
        """Test validation of type compatibility."""
        source_schema = {"count": "int"}
        target_schema = {"count": "int"}
        rules = [
            MappingRule(source_field="count", target_field="count")
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 0

    def test_validate_type_incompatibility(self):
        """Test validation error for incompatible types."""
        source_schema = {"active": "bool"}
        target_schema = {"count": "int"}
        rules = [
            MappingRule(source_field="active", target_field="count")
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 1
        assert errors[0].error_type == "type_mismatch"

    def test_validate_with_type_conversion(self):
        """Test validation with explicit type conversion."""
        source_schema = {"count": "string"}
        target_schema = {"count": "int"}
        rules = [
            MappingRule(
                source_field="count",
                target_field="count",
                type_conversion="int"
            )
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 0

    def test_validate_unsupported_conversion(self):
        """Test validation error for unsupported type conversion."""
        source_schema = {"value": "string"}
        target_schema = {"value": "string"}
        rules = [
            MappingRule(
                source_field="value",
                target_field="value",
                type_conversion="unsupported_type"
            )
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 1
        assert errors[0].error_type == "unsupported_conversion"

    def test_validate_nullable_mismatch(self):
        """Test validation error for nullable mismatch."""
        source_schema = {"name": {"type": "string", "nullable": True}}
        target_schema = {"name": {"type": "string", "nullable": False}}
        rules = [
            MappingRule(source_field="name", target_field="name")
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 1
        assert errors[0].error_type == "nullable_mismatch"

    def test_validate_nullable_mismatch_with_default(self):
        """Test validation passes when default value provided for nullable mismatch."""
        source_schema = {"name": {"type": "string", "nullable": True}}
        target_schema = {"name": {"type": "string", "nullable": False}}
        rules = [
            MappingRule(
                source_field="name",
                target_field="name",
                default_value="Unknown"
            )
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 0

    def test_validate_compatible_numeric_types(self):
        """Test validation of compatible numeric types."""
        source_schema = {"value": "int"}
        target_schema = {"value": "float"}
        rules = [
            MappingRule(source_field="value", target_field="value")
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 0

    def test_validate_string_accepts_any_type(self):
        """Test that string target type accepts any source type."""
        source_schema = {"value": "int"}
        target_schema = {"value": "string"}
        rules = [
            MappingRule(source_field="value", target_field="value")
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 0

    def test_validate_dict_rules(self):
        """Test validation with dict rules."""
        source_schema = {"name": "string"}
        target_schema = {"full_name": "string"}
        rules = [
            {"source_field": "name", "target_field": "full_name"}
        ]

        errors = self.mapper.validate_mapping(source_schema, target_schema, rules)

        assert len(errors) == 0


class TestFieldMapperEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = FieldMapper()

    def test_empty_data(self):
        """Test mapping with empty data."""
        data = {}
        rules = []

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data == {}

    def test_empty_rules(self):
        """Test mapping with empty rules."""
        data = {"name": "John"}
        rules = []

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data == {}

    def test_multiple_errors(self):
        """Test that multiple errors are collected."""
        data = {}
        rules = [
            MappingRule(source_field="field1", target_field="field1", nullable=False),
            MappingRule(source_field="field2", target_field="field2", nullable=False),
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert not result.success
        assert len(result.errors) == 2

    def test_partial_success(self):
        """Test that successful mappings are included even when some fail."""
        data = {"valid": "value"}
        rules = [
            MappingRule(source_field="valid", target_field="valid"),
            MappingRule(source_field="missing", target_field="missing", nullable=False),
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert not result.success
        assert result.data["valid"] == "value"
        assert len(result.errors) == 1

    def test_zero_and_empty_string_values(self):
        """Test handling of zero and empty string values."""
        data = {"count": 0, "name": ""}
        rules = [
            MappingRule(source_field="count", target_field="count"),
            MappingRule(source_field="name", target_field="name"),
        ]

        result = self.mapper.apply_mapping(data, rules)

        assert result.success
        assert result.data["count"] == 0
        assert result.data["name"] == ""
