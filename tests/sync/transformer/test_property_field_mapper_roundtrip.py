"""
Property-based tests for FieldMapper round-trip consistency.

Feature: bidirectional-sync-and-external-api
Property 1: 字段映射往返一致性

Tests that applying forward mapping then reverse mapping returns equivalent data.
Validates both field name mapping and type conversion round-trip consistency.
"""

import pytest
from hypothesis import given, strategies as st, settings
from src.sync.transformer.field_mapper import FieldMapper, MappingRule


# Strategy for generating valid field names
field_names = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=97, max_codepoint=122),
    min_size=1,
    max_size=20
).filter(lambda x: x and x[0].isalpha())


# Strategy for generating values that can round-trip through type conversions
@st.composite
def roundtrip_value_and_type(draw):
    """Generate a value and type that can round-trip consistently."""
    type_choice = draw(st.sampled_from([
        "string",
        "int",
        "float",
        "bool",
    ]))
    
    if type_choice == "string":
        value = draw(st.text(min_size=0, max_size=50))
        return value, type_choice
    elif type_choice == "int":
        value = draw(st.integers(min_value=-1000000, max_value=1000000))
        return value, type_choice
    elif type_choice == "float":
        value = draw(st.floats(
            min_value=-1000000.0,
            max_value=1000000.0,
            allow_nan=False,
            allow_infinity=False
        ))
        return value, type_choice
    elif type_choice == "bool":
        value = draw(st.booleans())
        return value, type_choice


@st.composite
def field_mapping_scenario(draw):
    """
    Generate a valid field mapping scenario with data and bidirectional rules.
    
    Returns:
        tuple: (data, forward_rules, reverse_rules, original_field_names)
    """
    # Generate 1-5 fields
    num_fields = draw(st.integers(min_value=1, max_value=5))
    
    # Generate unique field names for source and target
    source_fields = draw(st.lists(
        field_names,
        min_size=num_fields,
        max_size=num_fields,
        unique=True
    ))
    
    target_fields = draw(st.lists(
        field_names,
        min_size=num_fields,
        max_size=num_fields,
        unique=True
    ).filter(lambda x: set(x).isdisjoint(set(source_fields))))
    
    # Generate data and mapping rules
    data = {}
    forward_rules = []
    reverse_rules = []
    
    for source_field, target_field in zip(source_fields, target_fields):
        # Generate value and type
        value, value_type = draw(roundtrip_value_and_type())
        data[source_field] = value
        
        # Create forward mapping rule (source -> target)
        forward_rules.append(MappingRule(
            source_field=source_field,
            target_field=target_field,
            type_conversion=value_type,
            nullable=True
        ))
        
        # Create reverse mapping rule (target -> source)
        reverse_rules.append(MappingRule(
            source_field=target_field,
            target_field=source_field,
            type_conversion=value_type,
            nullable=True
        ))
    
    return data, forward_rules, reverse_rules, source_fields


class TestFieldMapperRoundtripProperty:
    """Property-based tests for field mapping round-trip consistency."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = FieldMapper()
    
    # Feature: bidirectional-sync-and-external-api, Property 1: 字段映射往返一致性
    @settings(max_examples=100, deadline=None)
    @given(scenario=field_mapping_scenario())
    def test_field_mapping_roundtrip_consistency(self, scenario):
        """
        Property: For any valid field mapping rules and input data,
        applying forward mapping then reverse mapping should return
        data equivalent to the original (both field names and types restored).
        
        Validates: Requirements 1.3
        """
        data, forward_rules, reverse_rules, original_fields = scenario
        
        # Apply forward mapping (source -> target)
        forward_result = self.mapper.apply_mapping(data, forward_rules)
        
        # Forward mapping should succeed
        assert forward_result.success, f"Forward mapping failed: {forward_result.errors}"
        
        # Apply reverse mapping (target -> source)
        reverse_result = self.mapper.apply_mapping(forward_result.data, reverse_rules)
        
        # Reverse mapping should succeed
        assert reverse_result.success, f"Reverse mapping failed: {reverse_result.errors}"
        
        # Check that all original fields are restored
        for field in original_fields:
            assert field in reverse_result.data, f"Field '{field}' not restored after round-trip"
        
        # Check that values are equivalent after round-trip
        for field in original_fields:
            original_value = data[field]
            restored_value = reverse_result.data[field]
            
            # Handle type-specific equivalence checks
            if isinstance(original_value, float):
                # For floats, check approximate equality due to potential precision loss
                assert abs(original_value - restored_value) < 1e-6, (
                    f"Field '{field}': float value not preserved. "
                    f"Original: {original_value}, Restored: {restored_value}"
                )
            elif isinstance(original_value, bool):
                # Booleans should be exactly equal
                assert original_value == restored_value, (
                    f"Field '{field}': bool value not preserved. "
                    f"Original: {original_value}, Restored: {restored_value}"
                )
            elif isinstance(original_value, int):
                # Integers should be exactly equal
                assert original_value == restored_value, (
                    f"Field '{field}': int value not preserved. "
                    f"Original: {original_value}, Restored: {restored_value}"
                )
            elif isinstance(original_value, str):
                # Strings should be exactly equal
                assert original_value == restored_value, (
                    f"Field '{field}': string value not preserved. "
                    f"Original: {original_value!r}, Restored: {restored_value!r}"
                )
            else:
                # For other types, use equality
                assert original_value == restored_value, (
                    f"Field '{field}': value not preserved. "
                    f"Original: {original_value}, Restored: {restored_value}"
                )
            
            # Check that types are preserved
            assert type(original_value) == type(restored_value), (
                f"Field '{field}': type not preserved. "
                f"Original type: {type(original_value)}, Restored type: {type(restored_value)}"
            )
    
    # Feature: bidirectional-sync-and-external-api, Property 1: 字段映射往返一致性
    @settings(max_examples=100, deadline=None)
    @given(
        value=st.one_of(
            st.integers(min_value=-1000000, max_value=1000000),
            st.floats(min_value=-1000000.0, max_value=1000000.0, allow_nan=False, allow_infinity=False),
            st.text(min_size=0, max_size=100),
            st.booleans()
        )
    )
    def test_type_conversion_roundtrip_consistency(self, value):
        """
        Property: For any value, converting to a type and back should preserve
        the value (within type-specific equivalence).
        
        Validates: Requirements 1.3
        """
        # Determine the original type
        if isinstance(value, bool):
            # Must check bool before int since bool is a subclass of int
            original_type = "bool"
        elif isinstance(value, int):
            original_type = "int"
        elif isinstance(value, float):
            original_type = "float"
        elif isinstance(value, str):
            original_type = "string"
        else:
            pytest.skip(f"Unsupported type: {type(value)}")
        
        data = {"field": value}
        
        # Create forward and reverse rules with the same type
        forward_rules = [MappingRule(
            source_field="field",
            target_field="mapped_field",
            type_conversion=original_type,
            nullable=True
        )]
        
        reverse_rules = [MappingRule(
            source_field="mapped_field",
            target_field="field",
            type_conversion=original_type,
            nullable=True
        )]
        
        # Apply forward mapping
        forward_result = self.mapper.apply_mapping(data, forward_rules)
        assert forward_result.success, f"Forward mapping failed: {forward_result.errors}"
        
        # Apply reverse mapping
        reverse_result = self.mapper.apply_mapping(forward_result.data, reverse_rules)
        assert reverse_result.success, f"Reverse mapping failed: {reverse_result.errors}"
        
        # Check value preservation
        restored_value = reverse_result.data["field"]
        
        if isinstance(value, float):
            assert abs(value - restored_value) < 1e-6, (
                f"Float value not preserved: {value} != {restored_value}"
            )
        else:
            assert value == restored_value, (
                f"Value not preserved: {value} != {restored_value}"
            )
        
        # Check type preservation
        assert type(value) == type(restored_value), (
            f"Type not preserved: {type(value)} != {type(restored_value)}"
        )
    
    # Feature: bidirectional-sync-and-external-api, Property 1: 字段映射往返一致性
    @settings(max_examples=100, deadline=None)
    @given(
        num_fields=st.integers(min_value=1, max_value=10),
        data=st.data()
    )
    def test_multiple_fields_roundtrip_independence(self, num_fields, data):
        """
        Property: Round-trip mapping of multiple fields should be independent -
        each field's value should be preserved regardless of other fields.
        
        Validates: Requirements 1.3
        """
        # Generate unique field names
        source_fields = [f"src_field_{i}" for i in range(num_fields)]
        target_fields = [f"tgt_field_{i}" for i in range(num_fields)]
        
        # Generate random values for each field
        field_data = {}
        forward_rules = []
        reverse_rules = []
        
        for i, (src, tgt) in enumerate(zip(source_fields, target_fields)):
            # Generate a random value and type
            value, value_type = data.draw(roundtrip_value_and_type())
            field_data[src] = value
            
            forward_rules.append(MappingRule(
                source_field=src,
                target_field=tgt,
                type_conversion=value_type,
                nullable=True
            ))
            
            reverse_rules.append(MappingRule(
                source_field=tgt,
                target_field=src,
                type_conversion=value_type,
                nullable=True
            ))
        
        # Apply forward mapping
        forward_result = self.mapper.apply_mapping(field_data, forward_rules)
        assert forward_result.success, f"Forward mapping failed: {forward_result.errors}"
        
        # Apply reverse mapping
        reverse_result = self.mapper.apply_mapping(forward_result.data, reverse_rules)
        assert reverse_result.success, f"Reverse mapping failed: {reverse_result.errors}"
        
        # Verify each field independently
        for src in source_fields:
            original = field_data[src]
            restored = reverse_result.data[src]
            
            if isinstance(original, float):
                assert abs(original - restored) < 1e-6, (
                    f"Field '{src}' not preserved: {original} != {restored}"
                )
            else:
                assert original == restored, (
                    f"Field '{src}' not preserved: {original} != {restored}"
                )
            
            assert type(original) == type(restored), (
                f"Field '{src}' type not preserved: {type(original)} != {type(restored)}"
            )
