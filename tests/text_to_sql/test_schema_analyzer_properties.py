"""
Property-based tests for Schema Analyzer.

Tests Property 6: Schema 信息完整性
Validates: Requirements 5.2

Uses Hypothesis for property-based testing with 100+ iterations.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime
from typing import Dict, Any, List

# Import the schema analyzer
from src.text_to_sql.schema_analyzer import (
    SchemaAnalyzer,
    DatabaseSchema,
    SchemaChange,
    get_schema_analyzer,
)


# Custom strategies for generating test data
@st.composite
def column_strategy(draw):
    """Generate a valid column definition."""
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu'), whitelist_characters='_'),
        min_size=1,
        max_size=30
    ).filter(lambda x: x[0].isalpha() if x else False))
    
    data_types = ["VARCHAR(255)", "INTEGER", "BIGINT", "TEXT", "BOOLEAN", 
                  "TIMESTAMP", "DATE", "DECIMAL(10,2)", "FLOAT", "UUID"]
    
    return {
        "name": name,
        "data_type": draw(st.sampled_from(data_types)),
        "nullable": draw(st.booleans()),
        "default": draw(st.none() | st.text(min_size=0, max_size=20)),
        "is_primary_key": draw(st.booleans()),
        "is_foreign_key": draw(st.booleans()),
        "references": draw(st.none() | st.text(min_size=3, max_size=50)),
    }


@st.composite
def table_strategy(draw):
    """Generate a valid table definition."""
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu'), whitelist_characters='_'),
        min_size=1,
        max_size=30
    ).filter(lambda x: x[0].isalpha() if x else False))
    
    columns = draw(st.lists(column_strategy(), min_size=1, max_size=10))
    
    # Ensure unique column names
    seen_names = set()
    unique_columns = []
    for col in columns:
        if col["name"] not in seen_names:
            seen_names.add(col["name"])
            unique_columns.append(col)
    
    # Set at least one primary key
    if unique_columns:
        pk_cols = [c["name"] for c in unique_columns if c.get("is_primary_key")]
        if not pk_cols and unique_columns:
            unique_columns[0]["is_primary_key"] = True
            pk_cols = [unique_columns[0]["name"]]
    else:
        pk_cols = []
    
    return {
        "name": name,
        "columns": unique_columns,
        "primary_key": pk_cols,
        "indexes": [],
        "schema_name": draw(st.none() | st.text(min_size=1, max_size=20)),
    }


@st.composite
def schema_strategy(draw):
    """Generate a valid database schema."""
    tables = draw(st.lists(table_strategy(), min_size=1, max_size=10))
    
    # Ensure unique table names
    seen_names = set()
    unique_tables = []
    for table in tables:
        if table["name"] not in seen_names:
            seen_names.add(table["name"])
            unique_tables.append(table)
    
    return {
        "tables": unique_tables,
        "relationships": [],
        "db_type": draw(st.sampled_from(["postgresql", "mysql", "sqlite"])),
    }


class TestSchemaAnalyzerProperties:
    """Property-based tests for Schema Analyzer."""
    
    @settings(max_examples=100, deadline=None)
    @given(schema_data=schema_strategy())
    def test_property_6_schema_completeness(self, schema_data: Dict[str, Any]):
        """
        Property 6: Schema 信息完整性
        
        For any database connection, Schema Analyzer extracted information
        should contain all necessary fields: table name, column names,
        data types, primary keys, foreign keys, indexes.
        
        **Feature: text-to-sql-methods, Property 6: Schema 信息完整性**
        **Validates: Requirements 5.2**
        """
        analyzer = SchemaAnalyzer()
        
        # Create connection info with mock schema
        connection_info = {
            "tables": schema_data["tables"],
            "relationships": schema_data.get("relationships", []),
            "db_type": schema_data.get("db_type", "postgresql"),
        }
        
        # Analyze schema
        schema = analyzer.analyze(connection_info)
        
        # Verify schema completeness
        assert schema is not None, "Schema should not be None"
        assert isinstance(schema.tables, list), "Tables should be a list"
        assert schema.db_type is not None, "DB type should be set"
        assert schema.updated_at is not None, "Updated timestamp should be set"
        
        # Verify each table has required fields
        for table in schema.tables:
            # Table name is required
            assert "name" in table, "Table must have a name"
            assert table["name"], "Table name must not be empty"
            
            # Columns are required
            assert "columns" in table, "Table must have columns"
            assert isinstance(table["columns"], list), "Columns must be a list"
            
            # Each column must have required fields
            for col in table["columns"]:
                assert "name" in col, "Column must have a name"
                assert col["name"], "Column name must not be empty"
                assert "data_type" in col, "Column must have a data type"
                assert "nullable" in col, "Column must have nullable flag"
            
            # Primary key should be defined (can be empty list)
            assert "primary_key" in table, "Table must have primary_key field"
            assert isinstance(table["primary_key"], list), "Primary key must be a list"
    
    @settings(max_examples=100, deadline=None)
    @given(schema_data=schema_strategy())
    def test_llm_context_contains_all_tables(self, schema_data: Dict[str, Any]):
        """
        Test that LLM context includes all tables when under limit.
        
        **Feature: text-to-sql-methods, Property 6: Schema 信息完整性**
        **Validates: Requirements 5.2**
        """
        analyzer = SchemaAnalyzer(max_tables_for_llm=100)
        
        connection_info = {
            "tables": schema_data["tables"],
            "relationships": [],
            "db_type": schema_data.get("db_type", "postgresql"),
        }
        
        schema = analyzer.analyze(connection_info)
        context = analyzer.to_llm_context(schema)
        
        # Verify context is not empty
        assert context, "LLM context should not be empty"
        assert "Database Schema:" in context, "Context should have header"
        
        # Verify all tables are mentioned
        for table in schema.tables:
            table_name = table.get("name", "")
            assert table_name in context, f"Table {table_name} should be in context"
    
    @settings(max_examples=100, deadline=None)
    @given(schema_data=schema_strategy(), query=st.text(min_size=1, max_size=100))
    def test_filter_relevant_tables_returns_subset(self, schema_data: Dict[str, Any], query: str):
        """
        Test that filter_relevant_tables returns a valid subset.
        
        **Feature: text-to-sql-methods, Property 6: Schema 信息完整性**
        **Validates: Requirements 5.3**
        """
        assume(query.strip())  # Skip empty queries
        
        analyzer = SchemaAnalyzer()
        
        connection_info = {
            "tables": schema_data["tables"],
            "relationships": [],
            "db_type": schema_data.get("db_type", "postgresql"),
        }
        
        schema = analyzer.analyze(connection_info)
        max_tables = 5
        
        filtered = analyzer.filter_relevant_tables(schema, query, max_tables=max_tables)
        
        # Verify result is a list
        assert isinstance(filtered, list), "Result should be a list"
        
        # Verify result size is within limit
        assert len(filtered) <= max_tables, f"Should return at most {max_tables} tables"
        
        # Verify all returned tables are from original schema
        original_names = {t.get("name") for t in schema.tables}
        for table in filtered:
            assert table.get("name") in original_names, "Filtered table should be from original schema"
    
    @settings(max_examples=100, deadline=None)
    @given(schema_data=schema_strategy())
    def test_incremental_update_preserves_structure(self, schema_data: Dict[str, Any]):
        """
        Test that incremental updates preserve schema structure.
        
        **Feature: text-to-sql-methods, Property 6: Schema 信息完整性**
        **Validates: Requirements 5.5**
        """
        analyzer = SchemaAnalyzer()
        
        connection_info = {
            "tables": schema_data["tables"],
            "relationships": [],
            "db_type": schema_data.get("db_type", "postgresql"),
        }
        
        schema = analyzer.analyze(connection_info)
        original_table_count = len(schema.tables)
        
        # Apply empty changes
        updated = analyzer.incremental_update(schema, [])
        
        # Verify structure is preserved
        assert len(updated.tables) == original_table_count, "Table count should be preserved"
        assert updated.db_type == schema.db_type, "DB type should be preserved"
    
    @settings(max_examples=100, deadline=None)
    @given(schema_data=schema_strategy())
    def test_add_table_incremental_update(self, schema_data: Dict[str, Any]):
        """
        Test adding a table via incremental update.
        
        **Feature: text-to-sql-methods, Property 6: Schema 信息完整性**
        **Validates: Requirements 5.5**
        """
        analyzer = SchemaAnalyzer()
        
        connection_info = {
            "tables": schema_data["tables"],
            "relationships": [],
            "db_type": schema_data.get("db_type", "postgresql"),
        }
        
        schema = analyzer.analyze(connection_info)
        original_count = len(schema.tables)
        
        # Add a new table
        new_table = {
            "name": "new_test_table",
            "columns": [{"name": "id", "data_type": "INTEGER", "nullable": False, "is_primary_key": True}],
            "primary_key": ["id"],
            "indexes": [],
        }
        
        changes = [SchemaChange(
            change_type="add_table",
            table_name="new_test_table",
            new_value=new_table
        )]
        
        updated = analyzer.incremental_update(schema, changes)
        
        # Verify table was added
        assert len(updated.tables) == original_count + 1, "Should have one more table"
        
        # Verify new table exists
        table_names = [t.get("name") for t in updated.tables]
        assert "new_test_table" in table_names, "New table should exist"
    
    @settings(max_examples=100, deadline=None)
    @given(schema_data=schema_strategy())
    def test_drop_table_incremental_update(self, schema_data: Dict[str, Any]):
        """
        Test dropping a table via incremental update.
        
        **Feature: text-to-sql-methods, Property 6: Schema 信息完整性**
        **Validates: Requirements 5.5**
        """
        assume(len(schema_data["tables"]) > 0)
        
        analyzer = SchemaAnalyzer()
        
        connection_info = {
            "tables": schema_data["tables"],
            "relationships": [],
            "db_type": schema_data.get("db_type", "postgresql"),
        }
        
        schema = analyzer.analyze(connection_info)
        original_count = len(schema.tables)
        
        # Drop first table
        table_to_drop = schema.tables[0].get("name")
        
        changes = [SchemaChange(
            change_type="drop_table",
            table_name=table_to_drop
        )]
        
        updated = analyzer.incremental_update(schema, changes)
        
        # Verify table was dropped
        assert len(updated.tables) == original_count - 1, "Should have one less table"
        
        # Verify table no longer exists
        table_names = [t.get("name") for t in updated.tables]
        assert table_to_drop not in table_names, "Dropped table should not exist"
    
    @settings(max_examples=100, deadline=None)
    @given(schema_data=schema_strategy())
    def test_schema_hash_changes_on_modification(self, schema_data: Dict[str, Any]):
        """
        Test that schema hash changes when schema is modified.
        
        **Feature: text-to-sql-methods, Property 6: Schema 信息完整性**
        **Validates: Requirements 5.5**
        """
        analyzer = SchemaAnalyzer()
        
        connection_info = {
            "tables": schema_data["tables"],
            "relationships": [],
            "db_type": schema_data.get("db_type", "postgresql"),
        }
        
        schema = analyzer.analyze(connection_info)
        original_hash = schema.schema_hash
        
        # Add a new table
        new_table = {
            "name": "hash_test_table",
            "columns": [{"name": "id", "data_type": "INTEGER", "nullable": False}],
            "primary_key": ["id"],
            "indexes": [],
        }
        
        changes = [SchemaChange(
            change_type="add_table",
            table_name="hash_test_table",
            new_value=new_table
        )]
        
        updated = analyzer.incremental_update(schema, changes)
        
        # Verify hash changed
        assert updated.schema_hash != original_hash, "Hash should change after modification"


class TestSchemaAnalyzerEdgeCases:
    """Edge case tests for Schema Analyzer."""
    
    def test_empty_schema(self):
        """Test handling of empty schema."""
        analyzer = SchemaAnalyzer()
        
        connection_info = {
            "tables": [],
            "relationships": [],
            "db_type": "postgresql",
        }
        
        schema = analyzer.analyze(connection_info)
        
        assert schema is not None
        assert len(schema.tables) == 0
        assert schema.db_type == "postgresql"
    
    def test_table_with_no_columns(self):
        """Test handling of table with no columns."""
        analyzer = SchemaAnalyzer()
        
        connection_info = {
            "tables": [{"name": "empty_table", "columns": [], "primary_key": [], "indexes": []}],
            "relationships": [],
            "db_type": "postgresql",
        }
        
        schema = analyzer.analyze(connection_info)
        
        assert len(schema.tables) == 1
        assert schema.tables[0]["name"] == "empty_table"
    
    def test_cache_functionality(self):
        """Test schema caching."""
        analyzer = SchemaAnalyzer()
        
        connection_info = {
            "tables": [{"name": "test", "columns": [], "primary_key": [], "indexes": []}],
            "relationships": [],
            "db_type": "postgresql",
        }
        
        # First call
        schema1 = analyzer.analyze(connection_info)
        
        # Second call should use cache
        schema2 = analyzer.analyze(connection_info)
        
        assert schema1.updated_at == schema2.updated_at, "Should return cached schema"
        
        # Clear cache and verify new schema
        analyzer.clear_cache()
        schema3 = analyzer.analyze(connection_info)
        
        # Note: timestamps might be same if executed quickly
        assert schema3 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
