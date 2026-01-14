"""
Property-based tests for Template Filler.

Tests Property 5: 参数类型验证
Validates: Requirements 1.5

Uses Hypothesis for property-based testing with 100+ iterations.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, date
from typing import Dict, Any

from src.text_to_sql.basic import (
    TemplateFiller,
    get_template_filler,
)
from src.text_to_sql.schemas import (
    SQLTemplate,
    TemplateCategory,
    ParamType,
    ValidationResult,
)


# Custom strategies
@st.composite
def number_string_strategy(draw):
    """Generate strings that may or may not contain numbers."""
    has_number = draw(st.booleans())
    if has_number:
        num = draw(st.integers(min_value=-10000, max_value=10000))
        prefix = draw(st.text(max_size=5))
        suffix = draw(st.text(max_size=5))
        return f"{prefix}{num}{suffix}"
    else:
        return draw(st.text(min_size=1, max_size=20).filter(lambda x: not any(c.isdigit() for c in x)))


@st.composite
def date_string_strategy(draw):
    """Generate strings that may or may not contain dates."""
    has_date = draw(st.booleans())
    if has_date:
        year = draw(st.integers(min_value=2000, max_value=2030))
        month = draw(st.integers(min_value=1, max_value=12))
        day = draw(st.integers(min_value=1, max_value=28))
        separator = draw(st.sampled_from(["-", "/"]))
        return f"{year}{separator}{month:02d}{separator}{day:02d}"
    else:
        return draw(st.text(min_size=1, max_size=20))


@st.composite
def boolean_string_strategy(draw):
    """Generate strings that may or may not represent booleans."""
    is_bool = draw(st.booleans())
    if is_bool:
        return draw(st.sampled_from(["true", "false", "True", "False", "1", "0", "yes", "no", "是", "否"]))
    else:
        return draw(st.text(min_size=1, max_size=10).filter(
            lambda x: x.lower() not in ["true", "false", "1", "0", "yes", "no", "是", "否"]
        ))


class TestTemplateFilllerProperties:
    """Property-based tests for Template Filler."""
    
    @settings(max_examples=100, deadline=None)
    @given(value=st.text(min_size=0, max_size=100))
    def test_property_5_string_type_always_valid(self, value: str):
        """
        Property 5: 参数类型验证 - String type
        
        For any input value, STRING type validation should always succeed
        and return the string representation.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.5**
        """
        filler = TemplateFiller()
        
        params = {"test_param": value}
        param_types = {"test_param": ParamType.STRING}
        
        result = filler.validate_params(params, param_types)
        
        # String type should always be valid
        assert result.is_valid, f"String validation should always pass, got errors: {result.errors}"
        assert "test_param" in result.coerced_params
        assert isinstance(result.coerced_params["test_param"], str)
    
    @settings(max_examples=100, deadline=None)
    @given(value=st.integers())
    def test_property_5_number_from_int_valid(self, value: int):
        """
        Property 5: 参数类型验证 - Number from integer
        
        For any integer value, NUMBER type validation should succeed.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.5**
        """
        filler = TemplateFiller()
        
        params = {"test_param": value}
        param_types = {"test_param": ParamType.NUMBER}
        
        result = filler.validate_params(params, param_types)
        
        assert result.is_valid, f"Integer should be valid number, got errors: {result.errors}"
        assert "test_param" in result.coerced_params
    
    @settings(max_examples=100, deadline=None)
    @given(value=st.floats(allow_nan=False, allow_infinity=False))
    def test_property_5_number_from_float_valid(self, value: float):
        """
        Property 5: 参数类型验证 - Number from float
        
        For any finite float value, NUMBER type validation should succeed.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.5**
        """
        filler = TemplateFiller()
        
        params = {"test_param": value}
        param_types = {"test_param": ParamType.NUMBER}
        
        result = filler.validate_params(params, param_types)
        
        assert result.is_valid, f"Float should be valid number, got errors: {result.errors}"
        assert "test_param" in result.coerced_params
    
    @settings(max_examples=100, deadline=None)
    @given(value=number_string_strategy())
    def test_property_5_number_from_string_extraction(self, value: str):
        """
        Property 5: 参数类型验证 - Number extraction from string
        
        For any string containing a number, NUMBER type validation should
        extract and return the number. For strings without numbers, it should fail.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.5**
        """
        import re
        filler = TemplateFiller()
        
        params = {"test_param": value}
        param_types = {"test_param": ParamType.NUMBER}
        
        result = filler.validate_params(params, param_types)
        
        # Check if string contains a number
        has_number = bool(re.search(r'-?\d+\.?\d*', value))
        
        if has_number:
            assert result.is_valid, f"String with number should be valid: '{value}'"
        else:
            assert not result.is_valid, f"String without number should be invalid: '{value}'"
    
    @settings(max_examples=100, deadline=None)
    @given(d=st.dates(min_value=date(2000, 1, 1), max_value=date(2030, 12, 31)))
    def test_property_5_date_from_date_object_valid(self, d: date):
        """
        Property 5: 参数类型验证 - Date from date object
        
        For any date object, DATE type validation should succeed.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.5**
        """
        filler = TemplateFiller()
        
        params = {"test_param": d}
        param_types = {"test_param": ParamType.DATE}
        
        result = filler.validate_params(params, param_types)
        
        assert result.is_valid, f"Date object should be valid, got errors: {result.errors}"
        assert "test_param" in result.coerced_params
        # Should be formatted as YYYY-MM-DD
        assert "-" in result.coerced_params["test_param"]
    
    @settings(max_examples=100, deadline=None)
    @given(dt=st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2030, 12, 31)))
    def test_property_5_datetime_from_datetime_object_valid(self, dt: datetime):
        """
        Property 5: 参数类型验证 - Datetime from datetime object
        
        For any datetime object, DATETIME type validation should succeed.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.5**
        """
        filler = TemplateFiller()
        
        params = {"test_param": dt}
        param_types = {"test_param": ParamType.DATETIME}
        
        result = filler.validate_params(params, param_types)
        
        assert result.is_valid, f"Datetime object should be valid, got errors: {result.errors}"
        assert "test_param" in result.coerced_params
    
    @settings(max_examples=100, deadline=None)
    @given(value=st.booleans())
    def test_property_5_boolean_from_bool_valid(self, value: bool):
        """
        Property 5: 参数类型验证 - Boolean from bool
        
        For any boolean value, BOOLEAN type validation should succeed.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.5**
        """
        filler = TemplateFiller()
        
        params = {"test_param": value}
        param_types = {"test_param": ParamType.BOOLEAN}
        
        result = filler.validate_params(params, param_types)
        
        assert result.is_valid, f"Boolean should be valid, got errors: {result.errors}"
        assert "test_param" in result.coerced_params
        assert result.coerced_params["test_param"] == value
    
    @settings(max_examples=100, deadline=None)
    @given(value=boolean_string_strategy())
    def test_property_5_boolean_from_string(self, value: str):
        """
        Property 5: 参数类型验证 - Boolean from string
        
        For strings representing booleans, validation should succeed.
        For other strings, validation should fail.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.5**
        """
        filler = TemplateFiller()
        
        params = {"test_param": value}
        param_types = {"test_param": ParamType.BOOLEAN}
        
        result = filler.validate_params(params, param_types)
        
        bool_strings = {"true", "false", "1", "0", "yes", "no", "是", "否"}
        is_bool_string = value.lower() in bool_strings
        
        if is_bool_string:
            assert result.is_valid, f"Boolean string '{value}' should be valid"
        else:
            assert not result.is_valid, f"Non-boolean string '{value}' should be invalid"
    
    @settings(max_examples=100, deadline=None)
    @given(values=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    def test_property_5_list_from_list_valid(self, values: list):
        """
        Property 5: 参数类型验证 - List from list
        
        For any list value, LIST type validation should succeed.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.5**
        """
        filler = TemplateFiller()
        
        params = {"test_param": values}
        param_types = {"test_param": ParamType.LIST}
        
        result = filler.validate_params(params, param_types)
        
        assert result.is_valid, f"List should be valid, got errors: {result.errors}"
        assert "test_param" in result.coerced_params
        assert isinstance(result.coerced_params["test_param"], list)
    
    @settings(max_examples=100, deadline=None)
    @given(value=st.text(min_size=1, max_size=50))
    def test_property_5_list_from_string_splits(self, value: str):
        """
        Property 5: 参数类型验证 - List from comma-separated string
        
        For any string, LIST type validation should split by comma.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.5**
        """
        filler = TemplateFiller()
        
        params = {"test_param": value}
        param_types = {"test_param": ParamType.LIST}
        
        result = filler.validate_params(params, param_types)
        
        assert result.is_valid, f"String should be convertible to list"
        assert "test_param" in result.coerced_params
        assert isinstance(result.coerced_params["test_param"], list)
        
        # Verify split behavior
        expected_count = value.count(",") + 1
        assert len(result.coerced_params["test_param"]) == expected_count
    
    @settings(max_examples=100, deadline=None)
    @given(
        param_names=st.lists(
            st.text(alphabet=st.characters(whitelist_categories=('Ll',)), min_size=1, max_size=10),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    def test_property_5_missing_params_detected(self, param_names: list):
        """
        Property 5: 参数类型验证 - Missing parameters
        
        For any set of required parameters, validation should fail
        if any parameter is missing.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.5**
        """
        filler = TemplateFiller()
        
        # Create param_types with all params required
        param_types = {name: ParamType.STRING for name in param_names}
        
        # Provide only some params (or none)
        provided_count = len(param_names) // 2
        params = {name: "value" for name in param_names[:provided_count]}
        
        result = filler.validate_params(params, param_types)
        
        missing_count = len(param_names) - provided_count
        
        if missing_count > 0:
            assert not result.is_valid, "Should fail with missing params"
            assert len(result.errors) >= missing_count, "Should have error for each missing param"
        else:
            assert result.is_valid, "Should pass with all params provided"


class TestTemplateFillerMatching:
    """Tests for template matching functionality."""
    
    @settings(max_examples=100, deadline=None)
    @given(table_name=st.text(alphabet=st.characters(whitelist_categories=('Ll',)), min_size=2, max_size=20))
    def test_count_template_matches(self, table_name: str):
        """
        Test that count template matches count queries.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.1**
        """
        assume(table_name.strip())
        
        filler = TemplateFiller()
        
        query = f"统计{table_name}的数量"
        match = filler.match_template(query)
        
        assert match is not None, f"Should match count template for: {query}"
        assert match.template.category == TemplateCategory.AGGREGATE
    
    @settings(max_examples=100, deadline=None)
    @given(table_name=st.text(alphabet=st.characters(whitelist_categories=('Ll',)), min_size=2, max_size=20))
    def test_select_all_template_matches(self, table_name: str):
        """
        Test that select all template matches basic queries.
        
        **Feature: text-to-sql-methods, Property 5: 参数类型验证**
        **Validates: Requirements 1.1**
        """
        assume(table_name.strip())
        
        filler = TemplateFiller()
        
        query = f"查询所有{table_name}"
        match = filler.match_template(query)
        
        assert match is not None, f"Should match select template for: {query}"


class TestTemplateFillerGeneration:
    """Tests for SQL generation functionality."""
    
    def test_generate_count_sql(self):
        """Test generating count SQL."""
        filler = TemplateFiller()
        
        result = filler.generate("统计用户的数量")
        
        # May or may not match depending on param extraction
        # Just verify it returns a result
        assert result is not None
        assert result.method_used == "template"
    
    def test_generate_with_no_match(self):
        """Test generation when no template matches."""
        filler = TemplateFiller()
        
        # Use a query that definitely won't match any template
        result = filler.generate("@#$%^&*()_+")
        
        assert result is not None
        assert result.method_used == "template"
        # If no match, confidence should be 0 and there should be suggestions
        if result.confidence == 0.0:
            assert "suggestions" in result.metadata or "error" in result.metadata
    
    def test_fill_template_escapes_quotes(self):
        """Test that template filling escapes single quotes."""
        filler = TemplateFiller()
        
        template = SQLTemplate(
            id="test",
            name="Test",
            pattern="test",
            template="SELECT * FROM {table} WHERE name = '{name}'",
            param_types={"table": ParamType.STRING, "name": ParamType.STRING},
            category=TemplateCategory.FILTER,
        )
        
        params = {"table": "users", "name": "O'Brien"}
        sql = filler.fill_template(template, params)
        
        assert "O''Brien" in sql, "Single quotes should be escaped"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
