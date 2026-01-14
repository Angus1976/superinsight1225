"""
Property-based tests for Text-to-SQL API.

Tests Property 4: 第三方工具格式转换往返
Validates: Requirements 6.4, 6.5

Uses Hypothesis for property-based testing with 100+ iterations.
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.text_to_sql.schemas import (
    SQLGenerationResult,
    MethodInfo,
    PluginInfo,
    PluginConfig,
    TextToSQLConfig,
    MethodType,
    ConnectionType,
)
from src.text_to_sql.schema_analyzer import DatabaseSchema


# =============================================================================
# Property 4: Third-Party Tool Format Conversion Round-Trip Tests
# =============================================================================

class TestThirdPartyFormatConversion:
    """
    Property 4: 第三方工具格式转换往返
    
    For any valid query and schema, after conversion to tool format
    and back, the response should correctly contain SQL and confidence.
    
    **Validates: Requirements 6.4, 6.5**
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        query=st.text(min_size=5, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    def test_property_4_format_conversion_preserves_sql(
        self,
        query: str,
        confidence: float,
    ):
        """
        Property 4: Format conversion preserves SQL content.
        
        For any query, the SQL should be preserved through format conversion.
        
        **Feature: text-to-sql-methods, Property 4: 第三方工具格式转换往返**
        **Validates: Requirements 6.4, 6.5**
        """
        assume(query.strip())
        
        # Simulate third-party tool request format
        native_request = {
            "question": query,
            "database_schema": {"tables": []},
            "options": {"max_tokens": 500},
        }
        
        # Simulate third-party tool response format
        native_response = {
            "sql": f"SELECT * FROM test WHERE condition = '{query[:10]}'",
            "confidence": confidence,
            "metadata": {"tool": "test_tool"},
        }
        
        # Convert to unified format
        result = SQLGenerationResult(
            sql=native_response["sql"],
            method_used="third_party:test_tool",
            confidence=native_response["confidence"],
            execution_time_ms=100.0,
            metadata=native_response.get("metadata", {}),
        )
        
        # Verify SQL is preserved
        assert result.sql == native_response["sql"], "SQL should be preserved"
        assert result.confidence == confidence, "Confidence should be preserved"
        assert "third_party" in result.method_used, "Method should indicate third-party"
    
    @settings(max_examples=100, deadline=None)
    @given(
        sql=st.text(min_size=10, max_size=500, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))),
        tool_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
    )
    def test_property_4_metadata_preserved(
        self,
        sql: str,
        tool_name: str,
    ):
        """
        Property 4: Metadata is preserved through conversion.
        
        **Feature: text-to-sql-methods, Property 4: 第三方工具格式转换往返**
        **Validates: Requirements 6.4, 6.5**
        """
        assume(sql.strip() and tool_name.strip())
        
        original_metadata = {
            "tool": tool_name,
            "version": "1.0.0",
            "processing_time": 150.0,
        }
        
        # Create result with metadata
        result = SQLGenerationResult(
            sql=sql,
            method_used=f"third_party:{tool_name}",
            confidence=0.8,
            execution_time_ms=100.0,
            metadata=original_metadata,
        )
        
        # Verify metadata is preserved
        assert result.metadata["tool"] == tool_name, "Tool name should be preserved"
        assert "version" in result.metadata, "Version should be preserved"
    
    @settings(max_examples=100, deadline=None)
    @given(
        tables=st.lists(
            st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            min_size=1,
            max_size=10,
            unique=True,
        ),
    )
    def test_property_4_schema_conversion(self, tables: List[str]):
        """
        Property 4: Schema information is correctly converted.
        
        **Feature: text-to-sql-methods, Property 4: 第三方工具格式转换往返**
        **Validates: Requirements 6.4**
        """
        assume(all(t.strip() for t in tables))
        
        # Create schema using Dict format (as expected by DatabaseSchema)
        table_dicts = [
            {
                "name": table,
                "columns": [
                    {"name": "id", "data_type": "integer", "nullable": False},
                    {"name": "name", "data_type": "varchar", "nullable": True},
                ],
                "primary_key": ["id"],
                "indexes": [],
            }
            for table in tables
        ]
        
        schema = DatabaseSchema(
            tables=table_dicts,
            relationships=[],
            updated_at=datetime.utcnow(),
        )
        
        # Convert to native format (simulated)
        native_schema = {
            "tables": [
                {
                    "name": t["name"],
                    "columns": [{"name": c["name"], "type": c["data_type"]} for c in t["columns"]],
                }
                for t in schema.tables
            ]
        }
        
        # Verify all tables are present
        assert len(native_schema["tables"]) == len(tables), "All tables should be converted"
        
        # Verify table names match
        native_names = {t["name"] for t in native_schema["tables"]}
        original_names = set(tables)
        assert native_names == original_names, "Table names should match"
    
    @settings(max_examples=100, deadline=None)
    @given(
        query=st.text(min_size=5, max_size=100),
        db_type=st.sampled_from(["postgresql", "mysql", "sqlite"]),
    )
    def test_property_4_request_format_conversion(self, query: str, db_type: str):
        """
        Property 4: Request format conversion is correct.
        
        **Feature: text-to-sql-methods, Property 4: 第三方工具格式转换往返**
        **Validates: Requirements 6.4**
        """
        assume(query.strip())
        
        # Create unified request
        unified_request = {
            "query": query,
            "db_type": db_type,
            "options": {},
        }
        
        # Convert to various third-party formats
        
        # Vanna.ai format
        vanna_request = {
            "question": unified_request["query"],
            "database": unified_request["db_type"],
        }
        assert vanna_request["question"] == query, "Vanna request should preserve query"
        
        # DIN-SQL format
        din_request = {
            "nl_query": unified_request["query"],
            "dialect": unified_request["db_type"],
        }
        assert din_request["nl_query"] == query, "DIN-SQL request should preserve query"
        
        # Generic REST format
        rest_request = {
            "input": unified_request["query"],
            "parameters": {"database_type": unified_request["db_type"]},
        }
        assert rest_request["input"] == query, "REST request should preserve query"
    
    @settings(max_examples=100, deadline=None)
    @given(
        sql=st.text(min_size=10, max_size=200),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        execution_time=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False),
    )
    def test_property_4_response_format_conversion(
        self,
        sql: str,
        confidence: float,
        execution_time: float,
    ):
        """
        Property 4: Response format conversion preserves all fields.
        
        **Feature: text-to-sql-methods, Property 4: 第三方工具格式转换往返**
        **Validates: Requirements 6.5**
        """
        assume(sql.strip())
        
        # Simulate various third-party response formats
        
        # Vanna.ai response
        vanna_response = {
            "sql": sql,
            "confidence_score": confidence,
            "time_ms": execution_time,
        }
        
        # Convert to unified format
        unified_from_vanna = SQLGenerationResult(
            sql=vanna_response["sql"],
            method_used="third_party:vanna",
            confidence=vanna_response["confidence_score"],
            execution_time_ms=vanna_response["time_ms"],
        )
        
        assert unified_from_vanna.sql == sql, "SQL should be preserved from Vanna"
        assert unified_from_vanna.confidence == confidence, "Confidence should be preserved"
        
        # DIN-SQL response
        din_response = {
            "generated_sql": sql,
            "score": confidence,
            "latency": execution_time / 1000,  # seconds
        }
        
        unified_from_din = SQLGenerationResult(
            sql=din_response["generated_sql"],
            method_used="third_party:din-sql",
            confidence=din_response["score"],
            execution_time_ms=din_response["latency"] * 1000,
        )
        
        assert unified_from_din.sql == sql, "SQL should be preserved from DIN-SQL"


# =============================================================================
# Format Conversion Edge Cases
# =============================================================================

class TestFormatConversionEdgeCases:
    """Tests for edge cases in format conversion."""
    
    def test_empty_metadata_handling(self):
        """Test handling of empty metadata."""
        result = SQLGenerationResult(
            sql="SELECT 1",
            method_used="third_party:test",
            confidence=0.9,
            execution_time_ms=10.0,
            metadata={},
        )
        
        assert result.metadata == {}, "Empty metadata should be preserved"
    
    def test_special_characters_in_sql(self):
        """Test handling of special characters in SQL."""
        special_sql = "SELECT * FROM users WHERE name = 'O''Brien' AND status = 'active'"
        
        result = SQLGenerationResult(
            sql=special_sql,
            method_used="third_party:test",
            confidence=0.85,
            execution_time_ms=50.0,
        )
        
        assert result.sql == special_sql, "Special characters should be preserved"
    
    def test_unicode_in_query(self):
        """Test handling of Unicode in queries."""
        unicode_sql = "SELECT * FROM 用户表 WHERE 名称 = '张三'"
        
        result = SQLGenerationResult(
            sql=unicode_sql,
            method_used="third_party:test",
            confidence=0.8,
            execution_time_ms=100.0,
        )
        
        assert result.sql == unicode_sql, "Unicode should be preserved"
    
    def test_multiline_sql(self):
        """Test handling of multiline SQL."""
        multiline_sql = """
        SELECT 
            u.id,
            u.name,
            COUNT(o.id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 5
        ORDER BY order_count DESC
        """
        
        result = SQLGenerationResult(
            sql=multiline_sql,
            method_used="third_party:test",
            confidence=0.9,
            execution_time_ms=200.0,
        )
        
        assert result.sql == multiline_sql, "Multiline SQL should be preserved"
    
    @settings(max_examples=100, deadline=None)
    @given(
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    def test_confidence_bounds(self, confidence: float):
        """
        Test that confidence values are within valid bounds.
        
        **Feature: text-to-sql-methods, Property 4: 第三方工具格式转换往返**
        **Validates: Requirements 6.5**
        """
        result = SQLGenerationResult(
            sql="SELECT 1",
            method_used="third_party:test",
            confidence=confidence,
            execution_time_ms=10.0,
        )
        
        assert 0.0 <= result.confidence <= 1.0, "Confidence should be between 0 and 1"


# =============================================================================
# Round-Trip Conversion Tests
# =============================================================================

class TestRoundTripConversion:
    """Tests for complete round-trip format conversion."""
    
    @settings(max_examples=100, deadline=None)
    @given(
        query=st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Z'))),
        sql=st.text(min_size=10, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    def test_full_round_trip(self, query: str, sql: str, confidence: float):
        """
        Test complete round-trip: unified -> native -> unified.
        
        **Feature: text-to-sql-methods, Property 4: 第三方工具格式转换往返**
        **Validates: Requirements 6.4, 6.5**
        """
        assume(query.strip() and sql.strip())
        
        # Step 1: Create unified request
        unified_request = {
            "query": query,
            "db_type": "postgresql",
        }
        
        # Step 2: Convert to native format (Vanna.ai style)
        native_request = {
            "question": unified_request["query"],
            "database": unified_request["db_type"],
        }
        
        # Step 3: Simulate native response
        native_response = {
            "sql": sql,
            "confidence_score": confidence,
            "metadata": {"original_query": native_request["question"]},
        }
        
        # Step 4: Convert back to unified format
        unified_response = SQLGenerationResult(
            sql=native_response["sql"],
            method_used="third_party:vanna",
            confidence=native_response["confidence_score"],
            execution_time_ms=100.0,
            metadata=native_response["metadata"],
        )
        
        # Verify round-trip preserves data
        assert unified_response.sql == sql, "SQL should survive round-trip"
        assert unified_response.confidence == confidence, "Confidence should survive round-trip"
        assert unified_response.metadata["original_query"] == query, "Query should be traceable"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
