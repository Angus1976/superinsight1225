"""
SQL Builder Service for SuperInsight Platform Admin Configuration.

Provides visual SQL query building with:
- Database schema retrieval
- SQL query construction from configuration
- SQL validation
- Query execution with preview limits
- Query template management

**Feature: admin-configuration**
**Validates: Requirements 5.1, 5.4, 5.5, 5.6, 5.7**
"""

import logging
import re
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Union, Tuple
from uuid import uuid4

from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.schemas import (
    DatabaseType,
    ValidationResult,
    ValidationError,
    QueryConfig,
    QueryResult,
    QueryTemplateCreate,
    QueryTemplateResponse,
    DatabaseSchema,
    TableInfo,
    WhereCondition,
    OrderByClause,
)

logger = logging.getLogger(__name__)


class SQLBuilderService:
    """
    SQL Builder Service for visual query construction.
    
    Provides schema discovery, SQL generation, validation,
    and query execution capabilities.
    
    **Feature: admin-configuration**
    **Validates: Requirements 5.1, 5.4, 5.5, 5.6, 5.7**
    """
    
    # SQL keywords that should be uppercase
    SQL_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'LIKE',
        'BETWEEN', 'IS', 'NULL', 'ORDER', 'BY', 'ASC', 'DESC',
        'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'JOIN', 'LEFT', 'RIGHT',
        'INNER', 'OUTER', 'ON', 'AS', 'DISTINCT', 'COUNT', 'SUM',
        'AVG', 'MIN', 'MAX', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
    }
    
    # Valid SQL operators
    VALID_OPERATORS = {
        '=', '!=', '<>', '>', '<', '>=', '<=',
        'LIKE', 'NOT LIKE', 'ILIKE', 'NOT ILIKE',
        'IN', 'NOT IN', 'BETWEEN', 'NOT BETWEEN',
        'IS NULL', 'IS NOT NULL',
    }
    
    # Dangerous SQL patterns (for validation)
    DANGEROUS_PATTERNS = [
        r'\bDROP\b', r'\bDELETE\b', r'\bTRUNCATE\b', r'\bUPDATE\b',
        r'\bINSERT\b', r'\bALTER\b', r'\bCREATE\b', r'\bGRANT\b',
        r'\bREVOKE\b', r'--', r'/\*', r'\*/', r';.*SELECT',
    ]
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize the SQL builder service.
        
        Args:
            db: Optional async database session
        """
        self._db = db
        self._in_memory_templates: Dict[str, Dict[str, Any]] = {}
    
    @property
    def db(self) -> Optional[AsyncSession]:
        """Get the database session."""
        return self._db
    
    @db.setter
    def db(self, session: AsyncSession) -> None:
        """Set the database session."""
        self._db = session
    
    def build_sql(
        self,
        query_config: Union[QueryConfig, Dict[str, Any]],
        db_type: DatabaseType = DatabaseType.POSTGRESQL,
    ) -> str:
        """
        Build SQL query from configuration.
        
        Args:
            query_config: Query configuration
            db_type: Target database type
            
        Returns:
            Generated SQL query string
            
        **Feature: admin-configuration**
        **Validates: Requirements 5.4, 5.5**
        """
        # Convert to dict if needed
        if hasattr(query_config, 'model_dump'):
            config = query_config.model_dump()
        elif hasattr(query_config, 'dict'):
            config = query_config.dict()
        else:
            config = query_config
        
        # Build SELECT clause
        columns = config.get('columns', ['*'])
        if not columns:
            columns = ['*']
        select_clause = ', '.join(self._quote_identifier(c, db_type) if c != '*' else c for c in columns)
        
        # Build FROM clause
        tables = config.get('tables', [])
        if not tables:
            raise ValueError("At least one table is required")
        from_clause = ', '.join(self._quote_identifier(t, db_type) for t in tables)
        
        # Build WHERE clause
        where_conditions = config.get('where_conditions', [])
        where_clause = self._build_where_clause(where_conditions, db_type)
        
        # Build GROUP BY clause
        group_by = config.get('group_by', [])
        group_clause = ''
        if group_by:
            group_clause = 'GROUP BY ' + ', '.join(
                self._quote_identifier(g, db_type) for g in group_by
            )
        
        # Build ORDER BY clause
        order_by = config.get('order_by', [])
        order_clause = self._build_order_clause(order_by, db_type)
        
        # Build LIMIT/OFFSET clause
        limit = config.get('limit')
        offset = config.get('offset')
        limit_clause = self._build_limit_clause(limit, offset, db_type)
        
        # Assemble SQL
        sql_parts = [f"SELECT {select_clause}", f"FROM {from_clause}"]
        
        if where_clause:
            sql_parts.append(where_clause)
        if group_clause:
            sql_parts.append(group_clause)
        if order_clause:
            sql_parts.append(order_clause)
        if limit_clause:
            sql_parts.append(limit_clause)
        
        return '\n'.join(sql_parts)
    
    def validate_sql(
        self,
        sql: str,
        db_type: Union[DatabaseType, str] = DatabaseType.POSTGRESQL,
    ) -> ValidationResult:
        """
        Validate SQL query for safety and syntax.
        
        Args:
            sql: SQL query to validate
            db_type: Target database type
            
        Returns:
            ValidationResult with validation status
            
        **Feature: admin-configuration**
        **Validates: Requirements 5.5**
        """
        errors: List[ValidationError] = []
        warnings: List[str] = []
        
        if not sql or not sql.strip():
            errors.append(ValidationError(
                field="sql",
                message="SQL query cannot be empty",
                code="empty_sql"
            ))
            return ValidationResult(is_valid=False, errors=errors)
        
        sql_upper = sql.upper()
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                errors.append(ValidationError(
                    field="sql",
                    message=f"SQL contains potentially dangerous pattern: {pattern}",
                    code="dangerous_sql"
                ))
        
        # Check that it's a SELECT query
        if not sql_upper.strip().startswith('SELECT'):
            errors.append(ValidationError(
                field="sql",
                message="Only SELECT queries are allowed",
                code="non_select_query"
            ))
        
        # Check for basic syntax (has FROM clause)
        if 'FROM' not in sql_upper:
            errors.append(ValidationError(
                field="sql",
                message="SQL query must have a FROM clause",
                code="missing_from"
            ))
        
        # Check for balanced parentheses
        if sql.count('(') != sql.count(')'):
            errors.append(ValidationError(
                field="sql",
                message="Unbalanced parentheses in SQL query",
                code="unbalanced_parens"
            ))
        
        # Check for balanced quotes
        single_quotes = sql.count("'") - sql.count("\\'")
        if single_quotes % 2 != 0:
            errors.append(ValidationError(
                field="sql",
                message="Unbalanced single quotes in SQL query",
                code="unbalanced_quotes"
            ))
        
        # Warn about SELECT *
        if 'SELECT *' in sql_upper or 'SELECT  *' in sql_upper:
            warnings.append("Using SELECT * may impact performance; consider specifying columns")
        
        # Warn about missing LIMIT
        if 'LIMIT' not in sql_upper:
            warnings.append("Query has no LIMIT clause; consider adding one for large tables")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    async def execute_preview(
        self,
        sql: str,
        db_connection: Any,  # Database connection config or session
        limit: int = 100,
    ) -> QueryResult:
        """
        Execute SQL query with preview limit.
        
        Args:
            sql: SQL query to execute
            db_connection: Database connection
            limit: Maximum rows to return (default 100)
            
        Returns:
            QueryResult with execution results
            
        **Feature: admin-configuration**
        **Validates: Requirements 5.6**
        """
        # Validate SQL first
        validation = self.validate_sql(sql)
        if not validation.is_valid:
            raise ValueError(f"Invalid SQL: {validation.errors}")
        
        # Ensure limit is applied
        sql_with_limit = self._ensure_limit(sql, limit)
        
        start_time = time.time()
        
        try:
            if self._db is not None:
                result = await self._db.execute(text(sql_with_limit))
                rows = result.fetchall()
                columns = list(result.keys())
            else:
                # Mock execution for testing
                columns = ["id", "name", "value"]
                rows = [(1, "test", 100)]
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Convert rows to list of lists
            row_data = [list(row) for row in rows]
            
            return QueryResult(
                columns=columns,
                rows=row_data,
                row_count=len(row_data),
                execution_time_ms=execution_time_ms,
                truncated=len(row_data) >= limit,
            )
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise ValueError(f"Query execution failed: {e}")
    
    async def get_schema(
        self,
        db_connection: Any,
        db_type: DatabaseType = DatabaseType.POSTGRESQL,
    ) -> DatabaseSchema:
        """
        Get database schema information.
        
        Args:
            db_connection: Database connection
            db_type: Database type
            
        Returns:
            DatabaseSchema with table and view information
            
        **Feature: admin-configuration**
        **Validates: Requirements 5.1**
        """
        if self._db is None:
            # Return mock schema for testing
            return DatabaseSchema(
                tables=[
                    {
                        "name": "users",
                        "columns": [
                            {"name": "id", "type": "integer", "nullable": False},
                            {"name": "name", "type": "varchar", "nullable": False},
                            {"name": "email", "type": "varchar", "nullable": True},
                        ],
                    },
                    {
                        "name": "orders",
                        "columns": [
                            {"name": "id", "type": "integer", "nullable": False},
                            {"name": "user_id", "type": "integer", "nullable": False},
                            {"name": "total", "type": "decimal", "nullable": False},
                        ],
                    },
                ],
                views=[],
            )
        
        try:
            if db_type == DatabaseType.POSTGRESQL:
                return await self._get_postgresql_schema()
            elif db_type == DatabaseType.MYSQL:
                return await self._get_mysql_schema()
            else:
                return DatabaseSchema(tables=[], views=[])
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return DatabaseSchema(tables=[], views=[])
    
    async def save_template(
        self,
        template: QueryTemplateCreate,
        user_id: str,
        tenant_id: Optional[str] = None,
    ) -> QueryTemplateResponse:
        """
        Save a query template.
        
        Args:
            template: Template to save
            user_id: User creating the template
            tenant_id: Tenant ID for multi-tenant
            
        Returns:
            Saved QueryTemplateResponse
            
        **Feature: admin-configuration**
        **Validates: Requirements 5.7**
        """
        # Build SQL from config
        sql = self.build_sql(template.query_config)
        
        # Validate SQL
        validation = self.validate_sql(sql)
        if not validation.is_valid:
            raise ValueError(f"Invalid SQL in template: {validation.errors}")
        
        template_id = str(uuid4())
        now = datetime.utcnow()
        
        template_data = {
            "id": template_id,
            "name": template.name,
            "description": template.description,
            "query_config": template.query_config.model_dump() if hasattr(template.query_config, 'model_dump') else template.query_config,
            "sql": sql,
            "db_config_id": template.db_config_id,
            "created_by": user_id,
            "tenant_id": tenant_id,
            "created_at": now,
            "updated_at": now,
        }
        
        if self._db is not None:
            await self._save_template_to_db(template_data)
        else:
            self._in_memory_templates[template_id] = template_data
        
        return QueryTemplateResponse(
            id=template_id,
            name=template.name,
            description=template.description,
            query_config=template.query_config,
            sql=sql,
            db_config_id=template.db_config_id,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
    
    async def list_templates(
        self,
        db_config_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[QueryTemplateResponse]:
        """
        List query templates.
        
        Args:
            db_config_id: Filter by database config
            tenant_id: Filter by tenant
            
        Returns:
            List of QueryTemplateResponse
        """
        if self._db is not None:
            return await self._list_templates_from_db(db_config_id, tenant_id)
        else:
            templates = list(self._in_memory_templates.values())
            if db_config_id:
                templates = [t for t in templates if t.get("db_config_id") == db_config_id]
            if tenant_id:
                templates = [t for t in templates if t.get("tenant_id") == tenant_id]
            
            return [
                QueryTemplateResponse(
                    id=t["id"],
                    name=t["name"],
                    description=t.get("description"),
                    query_config=QueryConfig(**t["query_config"]),
                    sql=t["sql"],
                    db_config_id=t["db_config_id"],
                    created_by=t["created_by"],
                    created_at=t["created_at"],
                    updated_at=t["updated_at"],
                )
                for t in templates
            ]
    
    async def get_template(self, template_id: str) -> Optional[QueryTemplateResponse]:
        """Get a specific template by ID."""
        if self._db is not None:
            return await self._get_template_from_db(template_id)
        else:
            template = self._in_memory_templates.get(template_id)
            if template:
                return QueryTemplateResponse(
                    id=template["id"],
                    name=template["name"],
                    description=template.get("description"),
                    query_config=QueryConfig(**template["query_config"]),
                    sql=template["sql"],
                    db_config_id=template["db_config_id"],
                    created_by=template["created_by"],
                    created_at=template["created_at"],
                    updated_at=template["updated_at"],
                )
            return None
    
    async def delete_template(self, template_id: str) -> bool:
        """Delete a query template."""
        if self._db is not None:
            return await self._delete_template_from_db(template_id)
        else:
            if template_id in self._in_memory_templates:
                del self._in_memory_templates[template_id]
                return True
            return False
    
    def clear_in_memory_storage(self) -> None:
        """Clear in-memory storage (for testing)."""
        self._in_memory_templates.clear()
    
    # ========== Private helper methods ==========
    
    def _quote_identifier(self, identifier: str, db_type: DatabaseType) -> str:
        """Quote an identifier based on database type."""
        # Don't quote if it contains special chars (likely already formatted)
        if '.' in identifier or '(' in identifier or '*' in identifier:
            return identifier
        
        if db_type in (DatabaseType.POSTGRESQL, DatabaseType.SQLITE):
            return f'"{identifier}"'
        elif db_type == DatabaseType.MYSQL:
            return f'`{identifier}`'
        elif db_type == DatabaseType.SQLSERVER:
            return f'[{identifier}]'
        else:
            return f'"{identifier}"'
    
    def _build_where_clause(
        self,
        conditions: List[Union[WhereCondition, Dict[str, Any]]],
        db_type: DatabaseType,
    ) -> str:
        """Build WHERE clause from conditions."""
        if not conditions:
            return ''
        
        parts = []
        for i, cond in enumerate(conditions):
            if hasattr(cond, 'model_dump'):
                cond = cond.model_dump()
            elif hasattr(cond, 'dict'):
                cond = cond.dict()
            
            field = self._quote_identifier(cond['field'], db_type)
            operator = cond['operator'].upper()
            value = cond['value']
            logic = cond.get('logic', 'AND').upper()
            
            # Format value based on operator
            if operator in ('IS NULL', 'IS NOT NULL'):
                condition_str = f"{field} {operator}"
            elif operator in ('IN', 'NOT IN'):
                if isinstance(value, (list, tuple)):
                    formatted_values = ', '.join(self._format_value(v) for v in value)
                    condition_str = f"{field} {operator} ({formatted_values})"
                else:
                    condition_str = f"{field} {operator} ({self._format_value(value)})"
            elif operator == 'BETWEEN':
                if isinstance(value, (list, tuple)) and len(value) >= 2:
                    condition_str = f"{field} BETWEEN {self._format_value(value[0])} AND {self._format_value(value[1])}"
                else:
                    condition_str = f"{field} {operator} {self._format_value(value)}"
            else:
                condition_str = f"{field} {operator} {self._format_value(value)}"
            
            if i == 0:
                parts.append(condition_str)
            else:
                parts.append(f"{logic} {condition_str}")
        
        return 'WHERE ' + ' '.join(parts)
    
    def _build_order_clause(
        self,
        order_by: List[Union[OrderByClause, Dict[str, Any]]],
        db_type: DatabaseType,
    ) -> str:
        """Build ORDER BY clause."""
        if not order_by:
            return ''
        
        parts = []
        for order in order_by:
            if hasattr(order, 'model_dump'):
                order = order.model_dump()
            elif hasattr(order, 'dict'):
                order = order.dict()
            
            field = self._quote_identifier(order['field'], db_type)
            direction = order.get('direction', 'ASC').upper()
            parts.append(f"{field} {direction}")
        
        return 'ORDER BY ' + ', '.join(parts)
    
    def _build_limit_clause(
        self,
        limit: Optional[int],
        offset: Optional[int],
        db_type: DatabaseType,
    ) -> str:
        """Build LIMIT/OFFSET clause."""
        if limit is None and offset is None:
            return ''
        
        if db_type == DatabaseType.SQLSERVER:
            # SQL Server uses OFFSET...FETCH
            parts = []
            if offset:
                parts.append(f"OFFSET {offset} ROWS")
            if limit:
                if not offset:
                    parts.append("OFFSET 0 ROWS")
                parts.append(f"FETCH NEXT {limit} ROWS ONLY")
            return ' '.join(parts)
        else:
            # Standard LIMIT/OFFSET
            parts = []
            if limit:
                parts.append(f"LIMIT {limit}")
            if offset:
                parts.append(f"OFFSET {offset}")
            return ' '.join(parts)
    
    def _format_value(self, value: Any) -> str:
        """Format a value for SQL."""
        if value is None:
            return 'NULL'
        elif isinstance(value, bool):
            return 'TRUE' if value else 'FALSE'
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # Escape single quotes
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        else:
            return f"'{str(value)}'"
    
    def _ensure_limit(self, sql: str, limit: int) -> str:
        """Ensure SQL has a LIMIT clause."""
        sql_upper = sql.upper()
        if 'LIMIT' not in sql_upper:
            return f"{sql}\nLIMIT {limit}"
        return sql
    
    async def _get_postgresql_schema(self) -> DatabaseSchema:
        """Get PostgreSQL schema."""
        tables_query = """
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """
        
        result = await self._db.execute(text(tables_query))
        rows = result.fetchall()
        
        # Group by table
        tables_dict: Dict[str, List[Dict]] = {}
        for row in rows:
            table_name = row[0]
            if table_name not in tables_dict:
                tables_dict[table_name] = []
            tables_dict[table_name].append({
                "name": row[1],
                "type": row[2],
                "nullable": row[3] == 'YES',
            })
        
        tables = [
            {"name": name, "columns": columns}
            for name, columns in tables_dict.items()
        ]
        
        return DatabaseSchema(tables=tables, views=[])
    
    async def _get_mysql_schema(self) -> DatabaseSchema:
        """Get MySQL schema."""
        tables_query = """
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            ORDER BY table_name, ordinal_position
        """
        
        result = await self._db.execute(text(tables_query))
        rows = result.fetchall()
        
        tables_dict: Dict[str, List[Dict]] = {}
        for row in rows:
            table_name = row[0]
            if table_name not in tables_dict:
                tables_dict[table_name] = []
            tables_dict[table_name].append({
                "name": row[1],
                "type": row[2],
                "nullable": row[3] == 'YES',
            })
        
        tables = [
            {"name": name, "columns": columns}
            for name, columns in tables_dict.items()
        ]
        
        return DatabaseSchema(tables=tables, views=[])
    
    async def _save_template_to_db(self, template: Dict[str, Any]) -> None:
        """Save template to database."""
        from src.models.admin_config import QueryTemplate
        
        record = QueryTemplate(
            id=template["id"],
            tenant_id=template.get("tenant_id"),
            db_config_id=template["db_config_id"],
            name=template["name"],
            description=template.get("description"),
            query_config=template["query_config"],
            sql=template["sql"],
            created_by=template["created_by"],
        )
        
        self._db.add(record)
        await self._db.commit()
    
    async def _list_templates_from_db(
        self,
        db_config_id: Optional[str],
        tenant_id: Optional[str],
    ) -> List[QueryTemplateResponse]:
        """List templates from database."""
        from src.models.admin_config import QueryTemplate
        
        conditions = []
        if db_config_id:
            conditions.append(QueryTemplate.db_config_id == db_config_id)
        if tenant_id:
            conditions.append(QueryTemplate.tenant_id == tenant_id)
        
        query = select(QueryTemplate)
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self._db.execute(query)
        records = result.scalars().all()
        
        return [
            QueryTemplateResponse(
                id=str(r.id),
                name=r.name,
                description=r.description,
                query_config=QueryConfig(**r.query_config),
                sql=r.sql,
                db_config_id=str(r.db_config_id),
                created_by=str(r.created_by),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in records
        ]
    
    async def _get_template_from_db(self, template_id: str) -> Optional[QueryTemplateResponse]:
        """Get template from database."""
        from src.models.admin_config import QueryTemplate
        
        query = select(QueryTemplate).where(QueryTemplate.id == template_id)
        result = await self._db.execute(query)
        record = result.scalar_one_or_none()
        
        if record:
            return QueryTemplateResponse(
                id=str(record.id),
                name=record.name,
                description=record.description,
                query_config=QueryConfig(**record.query_config),
                sql=record.sql,
                db_config_id=str(record.db_config_id),
                created_by=str(record.created_by),
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        return None
    
    async def _delete_template_from_db(self, template_id: str) -> bool:
        """Delete template from database."""
        from src.models.admin_config import QueryTemplate
        from sqlalchemy import delete
        
        query = delete(QueryTemplate).where(QueryTemplate.id == template_id)
        result = await self._db.execute(query)
        await self._db.commit()
        
        return result.rowcount > 0


# Global service instance
_sql_builder_service: Optional[SQLBuilderService] = None


def get_sql_builder_service() -> SQLBuilderService:
    """Get the global SQL builder service instance."""
    global _sql_builder_service
    if _sql_builder_service is None:
        _sql_builder_service = SQLBuilderService()
    return _sql_builder_service
