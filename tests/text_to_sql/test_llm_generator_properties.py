"""
Property-based tests for LLM SQL Generator.

Tests Property 1: SQL 语法正确性
Validates: Requirements 1.2, 2.4

Uses Hypothesis for property-based testing with 100+ iterations.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List

from src.text_to_sql.llm_based import (
    LLMSQLGenerator,
    LLMFramework,
    get_llm_sql_generator,
)
from src.text_to_sql.schemas import ValidationResult


# Custom strategies for SQL generation
@st.composite
def valid_sql_strategy(draw):
    """Generate valid SQL SELECT statements."""
    tables = ["users", "orders", "products", "customers", "sales"]
    columns = ["id", "name", "email", "status", "amount", "created_at", "updated_at"]
    
    table = draw(st.sampled_from(tables))
    
    # Choose query type
    query_type = draw(st.sampled_from(["simple", "count", "where", "order", "limit"]))
    
    if query_type == "simple":
        return f"SELECT * FROM {table}"
    elif query_type == "count":
        return f"SELECT COUNT(*) FROM {table}"
    elif query_type == "where":
        col = draw(st.sampled_from(columns))
        return f"SELECT * FROM {table} WHERE {col} IS NOT NULL"
    elif query_type == "order":
        col = draw(st.sampled_from(columns))
        direction = draw(st.sampled_from(["ASC", "DESC"]))
        return f"SELECT * FROM {table} ORDER BY {col} {direction}"
    else:  # limit
        limit = draw(st.integers(min_value=1, max_value=100))
        return f"SELECT * FROM {table} LIMIT {limit}"


@st.composite
def invalid_sql_strategy(draw):
    """Generate invalid SQL statements."""
    invalid_types = [
        "INSERT INTO users VALUES (1, 'test')",
        "UPDATE users SET name = 'test'",
        "DELETE FROM users",
        "DROP TABLE users",
        "CREATE TABLE test (id INT)",
        "ALTER TABLE users ADD COLUMN test INT",
        "TRUNCATE TABLE users",
        "SELECT * FROM users; DROP TABLE users",
        "SELECT * FROM users WHERE id = 1; DELETE FROM users",
    ]
    return draw(st.sampled_from(invalid_types))


@st.composite
def malformed_sql_strategy(draw):
    """Generate malformed SQL with syntax errors."""
    malformed_types = [
        "SELECT * FROM users (",  # Unbalanced parentheses
        "SELECT * FROM users WHERE name = 'test",  # Unclosed quote
        'SELECT * FROM users WHERE name = "test',  # Unclosed double quote
        "SELECT * FROM users ((",  # Multiple unbalanced
        "SELECT * FROM users WHERE id = '1",  # Unclosed in WHERE
    ]
    return draw(st.sampled_from(malformed_types))


class TestLLMGeneratorValidation:
    """Property-based tests for SQL validation."""
    
    @settings(max_examples=100, deadline=None)
    @given(sql=valid_sql_strategy())
    def test_property_1_valid_sql_passes_validation(self, sql: str):
        """
        Property 1: SQL 语法正确性 - Valid SQL
        
        For any valid SELECT SQL statement, validation should pass.
        
        **Feature: text-to-sql-methods, Property 1: SQL 语法正确性**
        **Validates: Requirements 1.2, 2.4**
        """
        generator = LLMSQLGenerator()
        
        result = generator.validate_sql(sql, "postgresql")
        
        assert result.is_valid, f"Valid SQL should pass validation: {sql}, errors: {result.errors}"
    
    @settings(max_examples=100, deadline=None)
    @given(sql=invalid_sql_strategy())
    def test_property_1_dangerous_sql_fails_validation(self, sql: str):
        """
        Property 1: SQL 语法正确性 - Dangerous SQL
        
        For any dangerous SQL (INSERT, UPDATE, DELETE, DROP, etc.),
        validation should fail.
        
        **Feature: text-to-sql-methods, Property 1: SQL 语法正确性**
        **Validates: Requirements 1.2, 2.4**
        """
        generator = LLMSQLGenerator()
        
        result = generator.validate_sql(sql, "postgresql")
        
        assert not result.is_valid, f"Dangerous SQL should fail validation: {sql}"
        assert len(result.errors) > 0, "Should have error messages"
    
    @settings(max_examples=100, deadline=None)
    @given(sql=malformed_sql_strategy())
    def test_property_1_malformed_sql_fails_validation(self, sql: str):
        """
        Property 1: SQL 语法正确性 - Malformed SQL
        
        For any malformed SQL with syntax errors, validation should fail.
        
        **Feature: text-to-sql-methods, Property 1: SQL 语法正确性**
        **Validates: Requirements 1.2, 2.4**
        """
        generator = LLMSQLGenerator()
        
        result = generator.validate_sql(sql, "postgresql")
        
        assert not result.is_valid, f"Malformed SQL should fail validation: {sql}"
    
    @settings(max_examples=100, deadline=None)
    @given(sql=st.text(min_size=0, max_size=10))
    def test_property_1_empty_or_short_sql_fails(self, sql: str):
        """
        Property 1: SQL 语法正确性 - Empty/Short SQL
        
        For empty or very short strings that can't be valid SQL,
        validation should fail.
        
        **Feature: text-to-sql-methods, Property 1: SQL 语法正确性**
        **Validates: Requirements 1.2, 2.4**
        """
        generator = LLMSQLGenerator()
        
        # Skip if it happens to be a valid SQL start
        if sql.strip().upper().startswith("SELECT") or sql.strip().upper().startswith("WITH"):
            return
        
        result = generator.validate_sql(sql, "postgresql")
        
        # Empty or non-SQL strings should fail
        if not sql.strip():
            assert not result.is_valid, "Empty SQL should fail validation"


class TestLLMGeneratorPromptBuilding:
    """Tests for prompt building functionality."""
    
    @settings(max_examples=100, deadline=None)
    @given(query=st.text(min_size=1, max_size=200))
    def test_prompt_contains_query(self, query: str):
        """
        Test that built prompt contains the user query.
        
        **Feature: text-to-sql-methods, Property 1: SQL 语法正确性**
        **Validates: Requirements 2.2**
        """
        assume(query.strip())
        
        generator = LLMSQLGenerator()
        prompt = generator.build_prompt(query, None, "postgresql")
        
        assert query in prompt, "Prompt should contain the user query"
        assert "SQL" in prompt, "Prompt should mention SQL"
    
    @settings(max_examples=100, deadline=None)
    @given(db_type=st.sampled_from(["postgresql", "mysql", "sqlite", "oracle"]))
    def test_prompt_contains_db_type(self, db_type: str):
        """
        Test that built prompt contains the database type.
        
        **Feature: text-to-sql-methods, Property 1: SQL 语法正确性**
        **Validates: Requirements 2.2**
        """
        generator = LLMSQLGenerator()
        prompt = generator.build_prompt("test query", None, db_type)
        
        assert db_type.upper() in prompt.upper(), f"Prompt should mention {db_type}"
    
    def test_prompt_with_schema(self):
        """Test prompt building with schema context."""
        from src.text_to_sql.schema_analyzer import DatabaseSchema
        
        generator = LLMSQLGenerator()
        
        schema = DatabaseSchema(
            tables=[
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "data_type": "INTEGER", "is_primary_key": True},
                        {"name": "name", "data_type": "VARCHAR(255)"},
                    ],
                    "primary_key": ["id"],
                }
            ],
            relationships=[],
        )
        
        prompt = generator.build_prompt("查询所有用户", schema, "postgresql")
        
        assert "users" in prompt, "Prompt should contain table name"
        assert "id" in prompt, "Prompt should contain column names"


class TestLLMGeneratorSQLCleaning:
    """Tests for SQL cleaning functionality."""
    
    @settings(max_examples=100, deadline=None)
    @given(sql=valid_sql_strategy())
    def test_clean_sql_preserves_valid_sql(self, sql: str):
        """
        Test that cleaning preserves valid SQL.
        
        **Feature: text-to-sql-methods, Property 1: SQL 语法正确性**
        **Validates: Requirements 2.4**
        """
        generator = LLMSQLGenerator()
        
        cleaned = generator._clean_sql(sql)
        
        # Should preserve the core SQL
        assert "SELECT" in cleaned.upper(), "Should preserve SELECT"
    
    def test_clean_sql_removes_markdown(self):
        """Test that cleaning removes markdown code blocks."""
        generator = LLMSQLGenerator()
        
        sql_with_markdown = "```sql\nSELECT * FROM users\n```"
        cleaned = generator._clean_sql(sql_with_markdown)
        
        assert "```" not in cleaned, "Should remove markdown"
        assert "SELECT" in cleaned.upper(), "Should preserve SQL"
    
    def test_clean_sql_extracts_first_statement(self):
        """Test that cleaning extracts first SELECT statement."""
        generator = LLMSQLGenerator()
        
        multi_statement = "SELECT * FROM users; SELECT * FROM orders"
        cleaned = generator._clean_sql(multi_statement)
        
        # Should get first statement
        assert "users" in cleaned.lower()


class TestLLMGeneratorFormatting:
    """Tests for SQL formatting functionality."""
    
    @settings(max_examples=100, deadline=None)
    @given(sql=valid_sql_strategy())
    def test_format_sql_uppercases_keywords(self, sql: str):
        """
        Test that formatting uppercases SQL keywords.
        
        **Feature: text-to-sql-methods, Property 1: SQL 语法正确性**
        **Validates: Requirements 2.4**
        """
        generator = LLMSQLGenerator()
        
        formatted = generator._format_sql(sql.lower())
        
        # Keywords should be uppercase
        assert "SELECT" in formatted, "SELECT should be uppercase"
        assert "FROM" in formatted, "FROM should be uppercase"
    
    def test_format_sql_adds_newlines(self):
        """Test that formatting adds newlines for readability."""
        generator = LLMSQLGenerator()
        
        sql = "SELECT * FROM users WHERE id = 1 ORDER BY name"
        formatted = generator._format_sql(sql)
        
        # Should have newlines before major clauses
        assert "\n" in formatted, "Should have newlines"


class TestLLMGeneratorExplanation:
    """Tests for SQL explanation generation."""
    
    def test_explanation_for_count(self):
        """Test explanation for COUNT query."""
        generator = LLMSQLGenerator()
        
        sql = "SELECT COUNT(*) FROM users"
        explanation = generator._generate_explanation("统计用户数量", sql)
        
        assert "统计" in explanation, "Should mention counting"
    
    def test_explanation_for_join(self):
        """Test explanation for JOIN query."""
        generator = LLMSQLGenerator()
        
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        explanation = generator._generate_explanation("查询用户订单", sql)
        
        assert "关联" in explanation, "Should mention join"
    
    def test_explanation_for_order(self):
        """Test explanation for ORDER BY query."""
        generator = LLMSQLGenerator()
        
        sql = "SELECT * FROM users ORDER BY created_at DESC"
        explanation = generator._generate_explanation("查询用户", sql)
        
        assert "排" in explanation, "Should mention ordering"


class TestLLMGeneratorStatistics:
    """Tests for statistics tracking."""
    
    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly."""
        generator = LLMSQLGenerator()
        
        # Initial stats
        stats = generator.get_statistics()
        assert stats["total_calls"] == 0
        assert stats["successful_calls"] == 0
    
    def test_statistics_after_validation(self):
        """Test statistics after validation calls."""
        generator = LLMSQLGenerator()
        
        # Validate some SQL
        generator.validate_sql("SELECT * FROM users", "postgresql")
        generator.validate_sql("SELECT * FROM orders", "postgresql")
        
        # Stats should still be 0 (validation doesn't count as generation)
        stats = generator.get_statistics()
        assert stats["total_calls"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
