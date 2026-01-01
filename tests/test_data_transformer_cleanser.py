"""
Data Transformer and Cleanser Tests.

Tests for data transformation (field mapping, type conversion, value transforms)
and data cleansing (deduplication, validation, quality scoring).
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.sync.connectors.base import DataBatch, DataRecord
from src.sync.transformer.transformer import (
    TransformationType,
    TransformationRule,
    TransformResult,
    FieldMappingTransformer,
    TypeConversionTransformer,
    ValueTransformTransformer,
    EnrichmentTransformer,
    NormalizationTransformer,
    TransformationPipeline,
    DataTransformer,
)
from src.sync.transformer.cleanser import (
    CleansingType,
    CleansingRule,
    QualityScore,
    CleansingResult,
    DeduplicationEngine,
    ValidationEngine,
    DataCleanser,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_record():
    """Create a sample data record."""
    return DataRecord(
        id="rec_001",
        data={
            "name": "  John Doe  ",
            "email": "john@example.com",
            "age": "30",
            "phone": "123-456-7890",
            "status": "active",
            "score": 85.5
        },
        source="test",
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def sample_batch():
    """Create a sample data batch."""
    records = [
        DataRecord(
            id=f"rec_{i}",
            data={
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "value": i * 10
            },
            source="test",
            timestamp=datetime.utcnow()
        )
        for i in range(5)
    ]
    return DataBatch(
        batch_id="batch_001",
        records=records,
        source="test"
    )


# =============================================================================
# TransformationRule Tests
# =============================================================================

class TestTransformationRule:
    """Tests for TransformationRule."""

    def test_rule_creation(self):
        """Test basic rule creation."""
        rule = TransformationRule(
            name="test_rule",
            rule_type=TransformationType.FIELD_MAPPING,
            source_field="old_name",
            target_field="new_name"
        )

        assert rule.name == "test_rule"
        assert rule.rule_type == TransformationType.FIELD_MAPPING
        assert rule.enabled is True
        assert rule.priority == 0

    def test_rule_target_defaults_to_source(self):
        """Test that target_field defaults to source_field."""
        rule = TransformationRule(
            name="test_rule",
            rule_type=TransformationType.VALUE_TRANSFORM,
            source_field="name"
        )

        assert rule.target_field == "name"

    def test_rule_with_config(self):
        """Test rule with configuration."""
        rule = TransformationRule(
            name="type_convert",
            rule_type=TransformationType.TYPE_CONVERSION,
            source_field="age",
            config={"target_type": "int"}
        )

        assert rule.config["target_type"] == "int"


# =============================================================================
# FieldMappingTransformer Tests
# =============================================================================

class TestFieldMappingTransformer:
    """Tests for field mapping transformer."""

    def test_field_mapping(self, sample_record):
        """Test basic field mapping."""
        transformer = FieldMappingTransformer()
        rule = TransformationRule(
            name="map_name",
            rule_type=TransformationType.FIELD_MAPPING,
            source_field="name",
            target_field="full_name"
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["full_name"] == "  John Doe  "
        assert "name" in result.data  # Source kept by default

    def test_field_mapping_with_remove_source(self, sample_record):
        """Test field mapping with source removal."""
        transformer = FieldMappingTransformer()
        rule = TransformationRule(
            name="map_name",
            rule_type=TransformationType.FIELD_MAPPING,
            source_field="name",
            target_field="full_name",
            config={"remove_source": True}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["full_name"] == "  John Doe  "
        assert "name" not in result.data

    def test_field_mapping_missing_source(self, sample_record):
        """Test mapping when source field is missing."""
        transformer = FieldMappingTransformer()
        rule = TransformationRule(
            name="map_missing",
            rule_type=TransformationType.FIELD_MAPPING,
            source_field="nonexistent",
            target_field="target"
        )

        result = transformer.transform(sample_record, rule)

        assert result == sample_record
        assert "target" not in result.data


# =============================================================================
# TypeConversionTransformer Tests
# =============================================================================

class TestTypeConversionTransformer:
    """Tests for type conversion transformer."""

    def test_string_to_int_conversion(self, sample_record):
        """Test converting string to int."""
        transformer = TypeConversionTransformer()
        rule = TransformationRule(
            name="convert_age",
            rule_type=TransformationType.TYPE_CONVERSION,
            source_field="age",
            config={"target_type": "int"}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["age"] == 30
        assert isinstance(result.data["age"], int)

    def test_to_float_conversion(self, sample_record):
        """Test converting to float."""
        transformer = TypeConversionTransformer()
        rule = TransformationRule(
            name="convert_age",
            rule_type=TransformationType.TYPE_CONVERSION,
            source_field="age",
            config={"target_type": "float"}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["age"] == 30.0
        assert isinstance(result.data["age"], float)

    def test_to_bool_conversion(self):
        """Test converting to boolean."""
        record = DataRecord(
            id="test",
            data={"active": "true", "disabled": "false", "empty": ""},
            source="test",
            timestamp=datetime.utcnow()
        )
        transformer = TypeConversionTransformer()

        # True case
        rule = TransformationRule(
            name="convert",
            rule_type=TransformationType.TYPE_CONVERSION,
            source_field="active",
            config={"target_type": "bool"}
        )
        result = transformer.transform(record, rule)
        assert result.data["active"] is True

        # False case
        rule = TransformationRule(
            name="convert",
            rule_type=TransformationType.TYPE_CONVERSION,
            source_field="disabled",
            config={"target_type": "bool"}
        )
        result = transformer.transform(record, rule)
        assert result.data["disabled"] is False

    def test_conversion_error_skip(self, sample_record):
        """Test conversion error with skip handling."""
        sample_record.data["bad_number"] = "not_a_number"
        transformer = TypeConversionTransformer()
        rule = TransformationRule(
            name="convert",
            rule_type=TransformationType.TYPE_CONVERSION,
            source_field="bad_number",
            config={"target_type": "int"},
            error_handling="skip"
        )

        result = transformer.transform(sample_record, rule)

        # Original value kept
        assert result.data["bad_number"] == "not_a_number"

    def test_conversion_error_default(self, sample_record):
        """Test conversion error with default value."""
        sample_record.data["bad_number"] = "not_a_number"
        transformer = TypeConversionTransformer()
        rule = TransformationRule(
            name="convert",
            rule_type=TransformationType.TYPE_CONVERSION,
            source_field="bad_number",
            config={"target_type": "int", "default_value": 0},
            error_handling="default"
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["bad_number"] == 0

    def test_conversion_error_fail(self, sample_record):
        """Test conversion error with fail handling."""
        sample_record.data["bad_number"] = "not_a_number"
        transformer = TypeConversionTransformer()
        rule = TransformationRule(
            name="convert",
            rule_type=TransformationType.TYPE_CONVERSION,
            source_field="bad_number",
            config={"target_type": "int"},
            error_handling="fail"
        )

        with pytest.raises(ValueError):
            transformer.transform(sample_record, rule)


# =============================================================================
# ValueTransformTransformer Tests
# =============================================================================

class TestValueTransformTransformer:
    """Tests for value transformation."""

    def test_uppercase_transform(self, sample_record):
        """Test uppercase transformation."""
        transformer = ValueTransformTransformer()
        rule = TransformationRule(
            name="upper",
            rule_type=TransformationType.VALUE_TRANSFORM,
            source_field="name",
            config={"transform": "uppercase"}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["name"] == "  JOHN DOE  "

    def test_lowercase_transform(self, sample_record):
        """Test lowercase transformation."""
        sample_record.data["name"] = "JOHN DOE"
        transformer = ValueTransformTransformer()
        rule = TransformationRule(
            name="lower",
            rule_type=TransformationType.VALUE_TRANSFORM,
            source_field="name",
            config={"transform": "lowercase"}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["name"] == "john doe"

    def test_trim_transform(self, sample_record):
        """Test trim transformation."""
        transformer = ValueTransformTransformer()
        rule = TransformationRule(
            name="trim",
            rule_type=TransformationType.VALUE_TRANSFORM,
            source_field="name",
            config={"transform": "trim"}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["name"] == "John Doe"

    def test_replace_transform(self, sample_record):
        """Test replace transformation."""
        transformer = ValueTransformTransformer()
        rule = TransformationRule(
            name="replace",
            rule_type=TransformationType.VALUE_TRANSFORM,
            source_field="phone",
            config={"transform": "replace", "pattern": "-", "replacement": ""}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["phone"] == "1234567890"

    def test_regex_replace_transform(self, sample_record):
        """Test regex replace transformation."""
        transformer = ValueTransformTransformer()
        rule = TransformationRule(
            name="regex_replace",
            rule_type=TransformationType.VALUE_TRANSFORM,
            source_field="phone",
            config={"transform": "regex_replace", "pattern": r"\D", "replacement": ""}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["phone"] == "1234567890"

    def test_concat_transform(self, sample_record):
        """Test concat transformation."""
        sample_record.data["first_name"] = "John"
        sample_record.data["last_name"] = "Doe"
        transformer = ValueTransformTransformer()
        rule = TransformationRule(
            name="concat",
            rule_type=TransformationType.VALUE_TRANSFORM,
            source_field="name",
            target_field="full_name",
            config={
                "transform": "concat",
                "fields": ["first_name", "last_name"],
                "separator": " "
            }
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["full_name"] == "John Doe"

    def test_split_transform(self, sample_record):
        """Test split transformation."""
        sample_record.data["full_name"] = "John,Doe,Jr"
        transformer = ValueTransformTransformer()
        rule = TransformationRule(
            name="split",
            rule_type=TransformationType.VALUE_TRANSFORM,
            source_field="full_name",
            target_field="first_name",
            config={"transform": "split", "separator": ",", "index": 0}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["first_name"] == "John"

    def test_hash_transform(self, sample_record):
        """Test hash transformation."""
        transformer = ValueTransformTransformer()
        rule = TransformationRule(
            name="hash",
            rule_type=TransformationType.VALUE_TRANSFORM,
            source_field="email",
            target_field="email_hash",
            config={"transform": "hash", "algorithm": "sha256"}
        )

        result = transformer.transform(sample_record, rule)

        assert "email_hash" in result.data
        assert len(result.data["email_hash"]) == 64  # SHA256 hex length

    def test_mask_transform(self, sample_record):
        """Test mask transformation."""
        sample_record.data["credit_card"] = "1234567890123456"
        transformer = ValueTransformTransformer()
        rule = TransformationRule(
            name="mask",
            rule_type=TransformationType.VALUE_TRANSFORM,
            source_field="credit_card",
            config={
                "transform": "mask",
                "mask_char": "*",
                "visible_start": 4,
                "visible_end": 4
            }
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["credit_card"].startswith("1234")
        assert result.data["credit_card"].endswith("3456")
        assert "*" in result.data["credit_card"]


# =============================================================================
# EnrichmentTransformer Tests
# =============================================================================

class TestEnrichmentTransformer:
    """Tests for enrichment transformer."""

    def test_timestamp_enrichment(self, sample_record):
        """Test timestamp enrichment."""
        transformer = EnrichmentTransformer()
        rule = TransformationRule(
            name="add_timestamp",
            rule_type=TransformationType.ENRICHMENT,
            target_field="processed_at",
            config={"enrichment_type": "timestamp"}
        )

        result = transformer.transform(sample_record, rule)

        assert "processed_at" in result.data
        # Should be a valid ISO format timestamp
        datetime.fromisoformat(result.data["processed_at"])

    def test_uuid_enrichment(self, sample_record):
        """Test UUID enrichment."""
        transformer = EnrichmentTransformer()
        rule = TransformationRule(
            name="add_uuid",
            rule_type=TransformationType.ENRICHMENT,
            target_field="uuid",
            config={"enrichment_type": "uuid"}
        )

        result = transformer.transform(sample_record, rule)

        assert "uuid" in result.data
        # Should be a valid UUID format
        import re
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_pattern, result.data["uuid"], re.I)

    def test_constant_enrichment(self, sample_record):
        """Test constant enrichment."""
        transformer = EnrichmentTransformer()
        rule = TransformationRule(
            name="add_constant",
            rule_type=TransformationType.ENRICHMENT,
            target_field="source_system",
            config={"enrichment_type": "constant", "value": "CRM"}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["source_system"] == "CRM"

    def test_computed_enrichment(self, sample_record):
        """Test computed enrichment."""
        sample_record.data["price"] = 100
        sample_record.data["quantity"] = 5
        transformer = EnrichmentTransformer()
        rule = TransformationRule(
            name="compute_total",
            rule_type=TransformationType.ENRICHMENT,
            target_field="total",
            config={"enrichment_type": "computed", "expression": "price * quantity"}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["total"] == 500

    def test_lookup_enrichment(self, sample_record):
        """Test lookup enrichment."""
        transformer = EnrichmentTransformer()
        rule = TransformationRule(
            name="lookup_status",
            rule_type=TransformationType.ENRICHMENT,
            target_field="status_label",
            config={
                "enrichment_type": "lookup",
                "lookup_field": "status",
                "lookup_table": {
                    "active": "Active User",
                    "inactive": "Inactive User"
                },
                "default_value": "Unknown"
            }
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["status_label"] == "Active User"


# =============================================================================
# NormalizationTransformer Tests
# =============================================================================

class TestNormalizationTransformer:
    """Tests for normalization transformer."""

    def test_phone_normalization(self, sample_record):
        """Test phone number normalization."""
        sample_record.data["phone"] = "(123) 456-7890"
        transformer = NormalizationTransformer()
        rule = TransformationRule(
            name="normalize_phone",
            rule_type=TransformationType.NORMALIZATION,
            source_field="phone",
            config={"normalization_type": "phone", "country_code": "+1"}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["phone"] == "+11234567890"

    def test_email_normalization(self, sample_record):
        """Test email normalization."""
        sample_record.data["email"] = "  JOHN@EXAMPLE.COM  "
        transformer = NormalizationTransformer()
        rule = TransformationRule(
            name="normalize_email",
            rule_type=TransformationType.NORMALIZATION,
            source_field="email",
            config={"normalization_type": "email"}
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["email"] == "john@example.com"

    def test_date_normalization(self, sample_record):
        """Test date format normalization."""
        sample_record.data["date"] = "01/15/2024"
        transformer = NormalizationTransformer()
        rule = TransformationRule(
            name="normalize_date",
            rule_type=TransformationType.NORMALIZATION,
            source_field="date",
            config={
                "normalization_type": "date",
                "input_format": "%m/%d/%Y",
                "output_format": "%Y-%m-%d"
            }
        )

        result = transformer.transform(sample_record, rule)

        assert result.data["date"] == "2024-01-15"

    def test_boolean_normalization(self):
        """Test boolean normalization."""
        record = DataRecord(
            id="test",
            data={"active": "yes", "disabled": "no"},
            source="test",
            timestamp=datetime.utcnow()
        )
        transformer = NormalizationTransformer()
        rule = TransformationRule(
            name="normalize_bool",
            rule_type=TransformationType.NORMALIZATION,
            source_field="active",
            config={
                "normalization_type": "boolean",
                "true_values": ["yes", "y", "true", "1"]
            }
        )

        result = transformer.transform(record, rule)

        assert result.data["active"] is True

    def test_numeric_normalization(self):
        """Test numeric normalization."""
        record = DataRecord(
            id="test",
            data={"amount": "$1,234.56"},
            source="test",
            timestamp=datetime.utcnow()
        )
        transformer = NormalizationTransformer()
        rule = TransformationRule(
            name="normalize_numeric",
            rule_type=TransformationType.NORMALIZATION,
            source_field="amount",
            config={"normalization_type": "numeric"}
        )

        result = transformer.transform(record, rule)

        assert result.data["amount"] == 1234.56


# =============================================================================
# TransformationPipeline Tests
# =============================================================================

class TestTransformationPipeline:
    """Tests for transformation pipeline."""

    def test_pipeline_creation(self):
        """Test creating a pipeline with rules."""
        rules = [
            TransformationRule(
                name="trim",
                rule_type=TransformationType.VALUE_TRANSFORM,
                source_field="name",
                config={"transform": "trim"},
                priority=1
            ),
            TransformationRule(
                name="upper",
                rule_type=TransformationType.VALUE_TRANSFORM,
                source_field="name",
                config={"transform": "uppercase"},
                priority=2
            )
        ]
        pipeline = TransformationPipeline(rules)

        assert len(pipeline._rules) == 2
        # Should be sorted by priority (descending)
        assert pipeline._rules[0].name == "upper"

    def test_add_rule(self):
        """Test adding a rule to pipeline."""
        pipeline = TransformationPipeline()
        rule = TransformationRule(
            name="test",
            rule_type=TransformationType.FIELD_MAPPING,
            source_field="a",
            target_field="b"
        )

        pipeline.add_rule(rule)

        assert len(pipeline._rules) == 1

    def test_remove_rule(self):
        """Test removing a rule from pipeline."""
        rules = [
            TransformationRule(
                name="rule1",
                rule_type=TransformationType.FIELD_MAPPING,
                source_field="a",
                target_field="b"
            ),
            TransformationRule(
                name="rule2",
                rule_type=TransformationType.FIELD_MAPPING,
                source_field="c",
                target_field="d"
            )
        ]
        pipeline = TransformationPipeline(rules)

        result = pipeline.remove_rule("rule1")

        assert result is True
        assert len(pipeline._rules) == 1

    def test_transform_record(self, sample_record):
        """Test transforming a single record."""
        rules = [
            TransformationRule(
                name="trim",
                rule_type=TransformationType.VALUE_TRANSFORM,
                source_field="name",
                config={"transform": "trim"}
            ),
            TransformationRule(
                name="upper_email",
                rule_type=TransformationType.VALUE_TRANSFORM,
                source_field="email",
                config={"transform": "lowercase"}
            )
        ]
        pipeline = TransformationPipeline(rules)

        result = pipeline.transform_record(sample_record)

        assert result.data["name"] == "John Doe"
        assert result.data["email"] == "john@example.com"

    def test_transform_batch(self, sample_batch):
        """Test transforming a batch of records."""
        rules = [
            TransformationRule(
                name="add_source",
                rule_type=TransformationType.ENRICHMENT,
                target_field="source_system",
                config={"enrichment_type": "constant", "value": "batch_test"}
            )
        ]
        pipeline = TransformationPipeline(rules)

        result = pipeline.transform_batch(sample_batch)

        assert result.success is True
        assert result.records_transformed == 5
        for record in sample_batch.records:
            assert record.data["source_system"] == "batch_test"

    def test_disabled_rule_skipped(self, sample_record):
        """Test that disabled rules are skipped."""
        rules = [
            TransformationRule(
                name="disabled",
                rule_type=TransformationType.VALUE_TRANSFORM,
                source_field="name",
                config={"transform": "uppercase"},
                enabled=False
            )
        ]
        pipeline = TransformationPipeline(rules)

        result = pipeline.transform_record(sample_record)

        # Name should not be uppercased
        assert result.data["name"] == "  John Doe  "


# =============================================================================
# DataTransformer Tests
# =============================================================================

class TestDataTransformer:
    """Tests for DataTransformer service."""

    def test_create_pipeline(self):
        """Test creating a named pipeline."""
        transformer = DataTransformer()
        rules = [
            TransformationRule(
                name="test",
                rule_type=TransformationType.FIELD_MAPPING,
                source_field="a",
                target_field="b"
            )
        ]

        pipeline = transformer.create_pipeline("test_pipeline", rules)

        assert pipeline is not None
        assert transformer.get_pipeline("test_pipeline") is not None

    def test_transform_with_pipeline_name(self, sample_batch):
        """Test transforming with a named pipeline."""
        transformer = DataTransformer()
        rules = [
            TransformationRule(
                name="enrich",
                rule_type=TransformationType.ENRICHMENT,
                target_field="processed",
                config={"enrichment_type": "constant", "value": True}
            )
        ]
        transformer.create_pipeline("process", rules)

        result = transformer.transform(sample_batch, pipeline_name="process")

        assert result.success is True
        assert result.records_transformed == 5

    def test_transform_with_ad_hoc_rules(self, sample_batch):
        """Test transforming with ad-hoc rules."""
        transformer = DataTransformer()
        rules = [
            TransformationRule(
                name="convert",
                rule_type=TransformationType.TYPE_CONVERSION,
                source_field="value",
                config={"target_type": "float"}
            )
        ]

        result = transformer.transform(sample_batch, rules=rules)

        assert result.success is True

    def test_transform_no_pipeline_or_rules(self, sample_batch):
        """Test transforming without pipeline or rules."""
        transformer = DataTransformer()

        result = transformer.transform(sample_batch)

        assert result.success is True
        assert result.records_transformed == 5

    def test_transform_with_missing_pipeline(self, sample_batch):
        """Test that missing pipeline raises error."""
        transformer = DataTransformer()

        with pytest.raises(ValueError):
            transformer.transform(sample_batch, pipeline_name="nonexistent")


# =============================================================================
# DeduplicationEngine Tests
# =============================================================================

class TestDeduplicationEngine:
    """Tests for deduplication engine."""

    def test_compute_hash(self, sample_record):
        """Test computing record hash."""
        engine = DeduplicationEngine()

        hash1 = engine.compute_hash(sample_record)
        hash2 = engine.compute_hash(sample_record)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_compute_hash_with_fields(self, sample_record):
        """Test computing hash with specific fields."""
        engine = DeduplicationEngine()

        hash_all = engine.compute_hash(sample_record)
        hash_name = engine.compute_hash(sample_record, fields=["name"])

        assert hash_all != hash_name

    def test_is_duplicate_first_occurrence(self, sample_record):
        """Test that first occurrence is not a duplicate."""
        engine = DeduplicationEngine()

        is_dup, hash_val = engine.is_duplicate(sample_record)

        assert is_dup is False
        assert hash_val is not None

    def test_is_duplicate_second_occurrence(self, sample_record):
        """Test that second occurrence is a duplicate."""
        engine = DeduplicationEngine()

        engine.is_duplicate(sample_record)
        is_dup, hash_val = engine.is_duplicate(sample_record)

        assert is_dup is True

    def test_get_duplicate_count(self):
        """Test getting duplicate count."""
        engine = DeduplicationEngine()
        record1 = DataRecord(id="1", data={"a": 1}, source="test", timestamp=datetime.utcnow())
        record2 = DataRecord(id="2", data={"a": 1}, source="test", timestamp=datetime.utcnow())  # Dup
        record3 = DataRecord(id="3", data={"a": 2}, source="test", timestamp=datetime.utcnow())

        engine.is_duplicate(record1)
        engine.is_duplicate(record2)
        engine.is_duplicate(record3)

        assert engine.get_duplicate_count() == 1

    def test_reset(self, sample_record):
        """Test resetting dedup state."""
        engine = DeduplicationEngine()

        engine.is_duplicate(sample_record)
        engine.reset()
        is_dup, _ = engine.is_duplicate(sample_record)

        assert is_dup is False


# =============================================================================
# ValidationEngine Tests
# =============================================================================

class TestValidationEngine:
    """Tests for validation engine."""

    def test_validate_email(self):
        """Test email validation."""
        engine = ValidationEngine()

        valid, _ = engine.validate_field("test@example.com", "email")
        assert valid is True

        valid, error = engine.validate_field("invalid-email", "email")
        assert valid is False

    def test_validate_phone(self):
        """Test phone validation."""
        engine = ValidationEngine()

        valid, _ = engine.validate_field("123-456-7890", "phone")
        assert valid is True

        valid, _ = engine.validate_field("+1 (123) 456-7890", "phone")
        assert valid is True

    def test_validate_url(self):
        """Test URL validation."""
        engine = ValidationEngine()

        valid, _ = engine.validate_field("https://example.com", "url")
        assert valid is True

        valid, _ = engine.validate_field("not-a-url", "url")
        assert valid is False

    def test_validate_uuid(self):
        """Test UUID validation."""
        engine = ValidationEngine()

        valid, _ = engine.validate_field(str(uuid4()), "uuid")
        assert valid is True

        valid, _ = engine.validate_field("not-a-uuid", "uuid")
        assert valid is False

    def test_validate_date(self):
        """Test date validation."""
        engine = ValidationEngine()

        valid, _ = engine.validate_field("2024-01-15", "date")
        assert valid is True

        valid, _ = engine.validate_field("15/01/2024", "date")
        assert valid is False

    def test_validate_numeric(self):
        """Test numeric validation."""
        engine = ValidationEngine()

        valid, _ = engine.validate_field("123.45", "numeric")
        assert valid is True

        valid, _ = engine.validate_field("-123.45", "numeric")
        assert valid is True

        valid, _ = engine.validate_field("abc", "numeric")
        assert valid is False

    def test_validate_range(self):
        """Test range validation."""
        engine = ValidationEngine()

        valid, _ = engine.validate_field(50, "range", {"min": 0, "max": 100})
        assert valid is True

        valid, _ = engine.validate_field(150, "range", {"min": 0, "max": 100})
        assert valid is False

        valid, _ = engine.validate_field(-10, "range", {"min": 0})
        assert valid is False

    def test_validate_length(self):
        """Test length validation."""
        engine = ValidationEngine()

        valid, _ = engine.validate_field("hello", "length", {"min": 3, "max": 10})
        assert valid is True

        valid, _ = engine.validate_field("hi", "length", {"min": 3})
        assert valid is False

        valid, _ = engine.validate_field("hello world!", "length", {"max": 10})
        assert valid is False

    def test_validate_enum(self):
        """Test enum validation."""
        engine = ValidationEngine()

        valid, _ = engine.validate_field(
            "active",
            "enum",
            {"values": ["active", "inactive", "pending"]}
        )
        assert valid is True

        valid, _ = engine.validate_field(
            "deleted",
            "enum",
            {"values": ["active", "inactive", "pending"]}
        )
        assert valid is False

    def test_validate_regex(self):
        """Test regex validation."""
        engine = ValidationEngine()

        valid, _ = engine.validate_field("ABC123", "regex", {"pattern": r"^[A-Z]{3}\d{3}$"})
        assert valid is True

        valid, _ = engine.validate_field("abc123", "regex", {"pattern": r"^[A-Z]{3}\d{3}$"})
        assert valid is False

    def test_validate_required(self):
        """Test required validation."""
        engine = ValidationEngine()

        valid, _ = engine.validate_field("value", "required")
        assert valid is True

        valid, _ = engine.validate_field("", "required")
        assert valid is False

        valid, _ = engine.validate_field("   ", "required")
        assert valid is False

    def test_validate_null_handling(self):
        """Test null value handling."""
        engine = ValidationEngine()

        # Nullable by default
        valid, _ = engine.validate_field(None, "email")
        assert valid is True

        # Not nullable
        valid, _ = engine.validate_field(None, "email", {"nullable": False})
        assert valid is False


# =============================================================================
# DataCleanser Tests
# =============================================================================

class TestDataCleanser:
    """Tests for data cleanser."""

    def test_cleanse_with_deduplication(self):
        """Test cleansing with deduplication."""
        records = [
            DataRecord(id="1", data={"name": "John"}, source="test", timestamp=datetime.utcnow()),
            DataRecord(id="2", data={"name": "John"}, source="test", timestamp=datetime.utcnow()),
            DataRecord(id="3", data={"name": "Jane"}, source="test", timestamp=datetime.utcnow()),
        ]
        batch = DataBatch(batch_id="test", records=records, source="test")

        cleanser = DataCleanser()
        rules = [
            CleansingRule(
                name="dedup",
                rule_type=CleansingType.DEDUPLICATION,
                fields=["name"],
                action="skip"
            )
        ]

        result = cleanser.cleanse(batch, rules)

        assert result.success is True
        assert result.records_processed == 3
        assert result.duplicates_found == 1
        assert result.records_cleaned == 2
        assert len(batch.records) == 2

    def test_cleanse_with_validation(self):
        """Test cleansing with validation."""
        records = [
            DataRecord(
                id="1",
                data={"email": "valid@example.com"},
                source="test",
                timestamp=datetime.utcnow()
            ),
            DataRecord(
                id="2",
                data={"email": "invalid-email"},
                source="test",
                timestamp=datetime.utcnow()
            ),
        ]
        batch = DataBatch(batch_id="test", records=records, source="test")

        cleanser = DataCleanser()
        rules = [
            CleansingRule(
                name="validate_email",
                rule_type=CleansingType.VALIDATION,
                fields=["email"],
                config={"validation_type": "email"},
                action="skip"
            )
        ]

        result = cleanser.cleanse(batch, rules)

        assert result.invalid_records == 1
        assert result.records_cleaned == 1
        assert len(batch.records) == 1

    def test_cleanse_with_null_handling(self):
        """Test cleansing with null handling."""
        records = [
            DataRecord(
                id="1",
                data={"name": None, "email": "test@example.com"},
                source="test",
                timestamp=datetime.utcnow()
            ),
        ]
        batch = DataBatch(batch_id="test", records=records, source="test")

        cleanser = DataCleanser()
        rules = [
            CleansingRule(
                name="null_name",
                rule_type=CleansingType.NULL_HANDLING,
                fields=["name"],
                config={"null_action": "default", "default_value": "Unknown"}
            )
        ]

        result = cleanser.cleanse(batch, rules)

        assert batch.records[0].data["name"] == "Unknown"

    def test_cleanse_with_formatting(self):
        """Test cleansing with formatting."""
        records = [
            DataRecord(
                id="1",
                data={"name": "  JOHN DOE  "},
                source="test",
                timestamp=datetime.utcnow()
            ),
        ]
        batch = DataBatch(batch_id="test", records=records, source="test")

        cleanser = DataCleanser()
        rules = [
            CleansingRule(
                name="trim_name",
                rule_type=CleansingType.FORMATTING,
                fields=["name"],
                config={"format_type": "trim"}
            ),
            CleansingRule(
                name="lower_name",
                rule_type=CleansingType.FORMATTING,
                fields=["name"],
                config={"format_type": "lowercase"}
            )
        ]

        result = cleanser.cleanse(batch, rules)

        assert batch.records[0].data["name"] == "john doe"

    def test_deduplicate_convenience(self):
        """Test deduplicate convenience method."""
        records = [
            DataRecord(id="1", data={"name": "A", "value": 1}, source="test", timestamp=datetime.utcnow()),
            DataRecord(id="2", data={"name": "A", "value": 2}, source="test", timestamp=datetime.utcnow()),
            DataRecord(id="3", data={"name": "B", "value": 3}, source="test", timestamp=datetime.utcnow()),
        ]
        batch = DataBatch(batch_id="test", records=records, source="test")

        cleanser = DataCleanser()
        result = cleanser.deduplicate(batch, fields=["name"])

        assert result.duplicates_found == 1
        assert len(batch.records) == 2

    def test_validate_convenience(self):
        """Test validate convenience method."""
        records = [
            DataRecord(
                id="1",
                data={"age": 25, "email": "valid@example.com"},
                source="test",
                timestamp=datetime.utcnow()
            ),
            DataRecord(
                id="2",
                data={"age": 150, "email": "invalid"},
                source="test",
                timestamp=datetime.utcnow()
            ),
        ]
        batch = DataBatch(batch_id="test", records=records, source="test")

        cleanser = DataCleanser()
        result = cleanser.validate(batch, {
            "age": {"validation_type": "range", "min": 0, "max": 120, "action": "skip"},
            "email": {"validation_type": "email", "action": "skip"}
        })

        assert result.invalid_records >= 1

    def test_quality_score_calculation(self):
        """Test quality score calculation."""
        records = [
            DataRecord(
                id="1",
                data={"name": "John", "email": "john@example.com"},
                source="test",
                timestamp=datetime.utcnow()
            ),
            DataRecord(
                id="2",
                data={"name": "Jane", "email": None},  # Has null
                source="test",
                timestamp=datetime.utcnow()
            ),
        ]
        batch = DataBatch(batch_id="test", records=records, source="test")

        cleanser = DataCleanser()
        result = cleanser.cleanse(batch, [])

        assert result.quality_score is not None
        assert 0 <= result.quality_score.overall_score <= 1
        assert result.quality_score.completeness < 1  # Has null


class TestQualityScore:
    """Tests for quality score."""

    def test_quality_score_attributes(self):
        """Test quality score attributes."""
        score = QualityScore(
            overall_score=0.85,
            completeness=0.9,
            consistency=0.8,
            accuracy=0.85,
            validity=0.9,
            uniqueness=0.95
        )

        assert score.overall_score == 0.85
        assert score.completeness == 0.9


class TestCleansingResult:
    """Tests for cleansing result."""

    def test_cleansing_result_defaults(self):
        """Test cleansing result default values."""
        result = CleansingResult(success=True)

        assert result.records_processed == 0
        assert result.records_cleaned == 0
        assert result.duplicates_found == 0
        assert result.issues == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
