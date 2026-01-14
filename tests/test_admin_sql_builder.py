"""
Property-Based Tests for SQL Builder Service.

Tests the SQL query building functionality using Hypothesis
for property-based testing.

**Feature: admin-configuration**
**Property 3: SQL 构建正确性**
**Validates: Requirements 5.4, 5.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from uuid import uuid4

from src.admin.sql_builder import SQLBuilderService, get_sql_builder_service
from src.admin.schemas import (
    DatabaseType,
    QueryConfig,
    WhereCondition,
    OrderByClause,
    QueryTemplateCreate,
)


# ========== Custom Strategies ==========

def table_name_strategy():
    """Strategy for generating valid table names."""
    return st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(whitelist_categories=('L',), whitelist_characters='_')
    ).filter(lambda x: x[0].isalpha())


def column_name_strategy():
    """Strategy for generating valid column names."""
    return st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_')
    ).filter(lambda x: x and x[0].isalpha())


def simple_query_config_strategy():
    """Strategy for generating simple query configurations."""
    return st.builds(
        QueryConfig,
        tables=st.lists(table_name_strategy(), min_size=1, max_size=3),
        columns=st.lists(column_name_strategy(), min_size=1, max_size=5),
        limit=st.integers(min_value=1, max_value=1000) | st.none(),
    )


def where_condition_strategy():
    """Strategy for generating WHERE conditions."""
    return st.builds(
        WhereCondition,
        field=column_name_strategy(),
        operator=st.sampled_from(['=', '!=', '>', '<', '>=', '<=', 'LIKE']),
        value=st.one_of(
            st.integers(min_value=0, max_value=1000),
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        ),
        logic=st.sampled_from(['AND', 'OR']),
    )


def order_by_strategy():
    """Strategy for generating ORDER BY clauses."""
    return st.builds(
        OrderByClause,
        field=column_name_strategy(),
        direction=st.sampled_from(['ASC', 'DESC']),
    )


class TestSQLBuilderProperties:
    """Property-based tests for SQLBuilderService."""
    
    @pytest.fixture
    def builder(self):
        """Create a fresh builder for each test."""
        builder = SQLBuilderService()
        builder.clear_in_memory_storage()
        return builder
    
    # ========== Property 3: SQL 构建正确性 ==========
    
    @given(config=simple_query_config_strategy())
    @settings(max_examples=100)
    def test_built_sql_is_valid_select(self, config: QueryConfig):
        """
        **Feature: admin-configuration, Property 3: SQL 构建正确性**
        **Validates: Requirements 5.4, 5.5**
        
        For any valid query configuration, the generated SQL should
        be a valid SELECT statement.
        """
        builder = SQLBuilderService()
        
        sql = builder.build_sql(config)
        
        # Should start with SELECT
        assert sql.upper().startswith('SELECT'), "SQL should start with SELECT"
        
        # Should contain FROM
        assert 'FROM' in sql.upper(), "SQL should contain FROM"
        
        # Should pass validation
        validation = builder.validate_sql(sql)
        assert validation.is_valid, f"Generated SQL should be valid: {validation.errors}"
    
    @given(
        tables=st.lists(table_name_strategy(), min_size=1, max_size=2),
        columns=st.lists(column_name_strategy(), min_size=1, max_size=3),
    )
    @settings(max_examples=100)
    def test_sql_contains_specified_tables_and_columns(
        self,
        tables: list,
        columns: list,
    ):
        """
        **Feature: admin-configuration, Property 3: SQL 构建正确性**
        **Validates: Requirements 5.4**
        
        Generated SQL should contain the specified tables and columns.
        """
        builder = SQLBuilderService()
        
        config = QueryConfig(tables=tables, columns=columns)
        sql = builder.build_sql(config)
        
        # All tables should be in FROM clause
        for table in tables:
            assert table in sql, f"Table {table} should be in SQL"
        
        # All columns should be in SELECT clause
        for column in columns:
            assert column in sql, f"Column {column} should be in SQL"
    
    @given(
        tables=st.lists(table_name_strategy(), min_size=1, max_size=1),
        conditions=st.lists(where_condition_strategy(), min_size=1, max_size=3),
    )
    @settings(max_examples=50)
    def test_sql_includes_where_conditions(
        self,
        tables: list,
        conditions: list,
    ):
        """
        **Feature: admin-configuration, Property 3: SQL 构建正确性**
        **Validates: Requirements 5.4**
        
        Generated SQL should include WHERE clause when conditions are specified.
        """
        builder = SQLBuilderService()
        
        config = QueryConfig(
            tables=tables,
            columns=["*"],
            where_conditions=conditions,
        )
        sql = builder.build_sql(config)
        
        # Should have WHERE clause
        assert 'WHERE' in sql.upper(), "SQL should have WHERE clause"
        
        # All condition fields should be present
        for cond in conditions:
            assert cond.field in sql, f"Condition field {cond.field} should be in SQL"
    
    @given(
        tables=st.lists(table_name_strategy(), min_size=1, max_size=1),
        order_by=st.lists(order_by_strategy(), min_size=1, max_size=2),
    )
    @settings(max_examples=50)
    def test_sql_includes_order_by(
        self,
        tables: list,
        order_by: list,
    ):
        """
        Generated SQL should include ORDER BY clause when specified.
        """
        builder = SQLBuilderService()
        
        config = QueryConfig(
            tables=tables,
            columns=["*"],
            order_by=order_by,
        )
        sql = builder.build_sql(config)
        
        # Should have ORDER BY clause
        assert 'ORDER BY' in sql.upper(), "SQL should have ORDER BY clause"
        
        # All order fields should be present
        for order in order_by:
            assert order.field in sql, f"Order field {order.field} should be in SQL"
    
    @given(
        tables=st.lists(table_name_strategy(), min_size=1, max_size=1),
        limit=st.integers(min_value=1, max_value=10000),
    )
    @settings(max_examples=50)
    def test_sql_includes_limit(self, tables: list, limit: int):
        """
        Generated SQL should include LIMIT clause when specified.
        """
        builder = SQLBuilderService()
        
        config = QueryConfig(
            tables=tables,
            columns=["*"],
            limit=limit,
        )
        sql = builder.build_sql(config)
        
        # Should have LIMIT clause
        assert 'LIMIT' in sql.upper(), "SQL should have LIMIT clause"
        assert str(limit) in sql, f"Limit value {limit} should be in SQL"


class TestSQLBuilderValidation:
    """Tests for SQL validation."""
    
    @pytest.fixture
    def builder(self):
        """Create a fresh builder for each test."""
        return SQLBuilderService()
    
    def test_validate_valid_select(self, builder):
        """Valid SELECT should pass validation."""
        sql = "SELECT id, name FROM users WHERE id = 1"
        result = builder.validate_sql(sql)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_empty_sql(self, builder):
        """Empty SQL should fail validation."""
        result = builder.validate_sql("")
        
        assert not result.is_valid
        assert any(e.code == "empty_sql" for e in result.errors)
    
    def test_validate_non_select(self, builder):
        """Non-SELECT queries should fail validation."""
        result = builder.validate_sql("UPDATE users SET name = 'test'")
        
        assert not result.is_valid
        assert any(e.code == "non_select_query" for e in result.errors)
    
    @pytest.mark.parametrize("dangerous_sql", [
        "SELECT * FROM users; DROP TABLE users",
        "SELECT * FROM users WHERE name = 'test' -- comment",
        "SELECT * FROM users /* comment */",
    ])
    def test_validate_dangerous_sql(self, builder, dangerous_sql):
        """Dangerous SQL patterns should fail validation."""
        result = builder.validate_sql(dangerous_sql)
        
        assert not result.is_valid
        assert any(e.code == "dangerous_sql" for e in result.errors)
    
    def test_validate_missing_from(self, builder):
        """SQL without FROM should fail validation."""
        result = builder.validate_sql("SELECT 1 + 1")
        
        assert not result.is_valid
        assert any(e.code == "missing_from" for e in result.errors)
    
    def test_validate_unbalanced_parens(self, builder):
        """SQL with unbalanced parentheses should fail."""
        result = builder.validate_sql("SELECT * FROM users WHERE (id = 1")
        
        assert not result.is_valid
        assert any(e.code == "unbalanced_parens" for e in result.errors)
    
    def test_validate_warns_select_star(self, builder):
        """SELECT * should generate warning."""
        result = builder.validate_sql("SELECT * FROM users LIMIT 10")
        
        assert result.is_valid  # Still valid
        assert any("SELECT *" in w for w in result.warnings)
    
    def test_validate_warns_no_limit(self, builder):
        """Missing LIMIT should generate warning."""
        result = builder.validate_sql("SELECT id FROM users")
        
        assert result.is_valid  # Still valid
        assert any("LIMIT" in w for w in result.warnings)


class TestSQLBuilderBuild:
    """Tests for SQL building."""
    
    @pytest.fixture
    def builder(self):
        """Create a fresh builder for each test."""
        return SQLBuilderService()
    
    def test_build_simple_select(self, builder):
        """Build simple SELECT query."""
        config = QueryConfig(
            tables=["users"],
            columns=["id", "name"],
        )
        
        sql = builder.build_sql(config)
        
        assert "SELECT" in sql
        assert "id" in sql
        assert "name" in sql
        assert "FROM" in sql
        assert "users" in sql
    
    def test_build_select_star(self, builder):
        """Build SELECT * query."""
        config = QueryConfig(
            tables=["users"],
            columns=["*"],
        )
        
        sql = builder.build_sql(config)
        
        assert "SELECT *" in sql or "SELECT  *" in sql
    
    def test_build_with_where(self, builder):
        """Build query with WHERE clause."""
        config = QueryConfig(
            tables=["users"],
            columns=["*"],
            where_conditions=[
                WhereCondition(field="id", operator="=", value=1),
            ],
        )
        
        sql = builder.build_sql(config)
        
        assert "WHERE" in sql
        assert "id" in sql
        assert "= 1" in sql
    
    def test_build_with_multiple_conditions(self, builder):
        """Build query with multiple WHERE conditions."""
        config = QueryConfig(
            tables=["users"],
            columns=["*"],
            where_conditions=[
                WhereCondition(field="id", operator=">", value=10, logic="AND"),
                WhereCondition(field="name", operator="LIKE", value="%test%", logic="AND"),
            ],
        )
        
        sql = builder.build_sql(config)
        
        assert "WHERE" in sql
        assert "AND" in sql
    
    def test_build_with_order_by(self, builder):
        """Build query with ORDER BY."""
        config = QueryConfig(
            tables=["users"],
            columns=["*"],
            order_by=[
                OrderByClause(field="name", direction="ASC"),
            ],
        )
        
        sql = builder.build_sql(config)
        
        assert "ORDER BY" in sql
        assert "ASC" in sql
    
    def test_build_with_limit_offset(self, builder):
        """Build query with LIMIT and OFFSET."""
        config = QueryConfig(
            tables=["users"],
            columns=["*"],
            limit=10,
            offset=20,
        )
        
        sql = builder.build_sql(config)
        
        assert "LIMIT 10" in sql
        assert "OFFSET 20" in sql
    
    def test_build_with_group_by(self, builder):
        """Build query with GROUP BY."""
        config = QueryConfig(
            tables=["orders"],
            columns=["user_id", "COUNT(*)"],
            group_by=["user_id"],
        )
        
        sql = builder.build_sql(config)
        
        assert "GROUP BY" in sql
        assert "user_id" in sql
    
    def test_build_no_tables_raises_error(self, builder):
        """Building without tables should raise error."""
        # Pydantic validates min_length=1 for tables, so we test with dict
        config = {
            "tables": [],
            "columns": ["*"],
        }
        
        with pytest.raises(ValueError) as exc_info:
            builder.build_sql(config)
        
        assert "table" in str(exc_info.value).lower()


class TestSQLBuilderTemplates:
    """Tests for query template management."""
    
    @pytest.fixture
    def builder(self):
        """Create a fresh builder for each test."""
        builder = SQLBuilderService()
        builder.clear_in_memory_storage()
        return builder
    
    @pytest.mark.asyncio
    async def test_save_and_get_template(self, builder):
        """Should save and retrieve template."""
        template = QueryTemplateCreate(
            name="Test Template",
            description="A test template",
            query_config=QueryConfig(
                tables=["users"],
                columns=["id", "name"],
            ),
            db_config_id=str(uuid4()),
        )
        
        saved = await builder.save_template(
            template=template,
            user_id="user-1",
        )
        
        assert saved.id is not None
        assert saved.name == "Test Template"
        assert saved.sql is not None
        assert "SELECT" in saved.sql
        
        # Retrieve
        retrieved = await builder.get_template(saved.id)
        assert retrieved is not None
        assert retrieved.id == saved.id
    
    @pytest.mark.asyncio
    async def test_list_templates(self, builder):
        """Should list templates."""
        db_config_id = str(uuid4())
        
        for i in range(3):
            template = QueryTemplateCreate(
                name=f"Template {i}",
                query_config=QueryConfig(tables=["users"], columns=["*"]),
                db_config_id=db_config_id,
            )
            await builder.save_template(template=template, user_id="user-1")
        
        templates = await builder.list_templates(db_config_id=db_config_id)
        
        assert len(templates) == 3
    
    @pytest.mark.asyncio
    async def test_delete_template(self, builder):
        """Should delete template."""
        template = QueryTemplateCreate(
            name="To Delete",
            query_config=QueryConfig(tables=["users"], columns=["*"]),
            db_config_id=str(uuid4()),
        )
        
        saved = await builder.save_template(template=template, user_id="user-1")
        
        result = await builder.delete_template(saved.id)
        assert result is True
        
        retrieved = await builder.get_template(saved.id)
        assert retrieved is None


class TestSQLBuilderSingleton:
    """Tests for singleton behavior."""
    
    def test_get_sql_builder_service_singleton(self):
        """get_sql_builder_service should return the same instance."""
        service1 = get_sql_builder_service()
        service2 = get_sql_builder_service()
        
        assert service1 is service2
