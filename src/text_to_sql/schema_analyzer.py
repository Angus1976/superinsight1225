"""
Schema Analyzer for Text-to-SQL Methods.

Enhanced schema analysis with LLM-friendly context generation,
intelligent table filtering, and incremental updates.
"""

import logging
import re
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Column information for schema analysis."""
    name: str
    data_type: str
    nullable: bool = True
    default: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    references: Optional[str] = None  # table.column
    description: Optional[str] = None
    sample_values: List[Any] = field(default_factory=list)


@dataclass
class IndexInfo:
    """Index information for schema analysis."""
    name: str
    columns: List[str]
    is_unique: bool = False
    is_primary: bool = False


@dataclass
class TableInfo:
    """Table information for schema analysis."""
    name: str
    columns: List[ColumnInfo]
    primary_key: List[str] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    row_count: Optional[int] = None
    schema_name: Optional[str] = None
    description: Optional[str] = None
    
    def get_column(self, name: str) -> Optional[ColumnInfo]:
        """Get column by name."""
        for col in self.columns:
            if col.name.lower() == name.lower():
                return col
        return None


@dataclass
class Relationship:
    """Relationship between tables."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    relationship_type: str = "foreign_key"  # foreign_key, inferred


class DatabaseSchema(BaseModel):
    """Complete database schema representation."""
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    db_type: Optional[str] = None
    schema_hash: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class SchemaChange(BaseModel):
    """Schema change for incremental updates."""
    change_type: str  # add_table, drop_table, add_column, drop_column, modify_column
    table_name: str
    column_name: Optional[str] = None
    new_value: Optional[Dict[str, Any]] = None
    old_value: Optional[Dict[str, Any]] = None


class SchemaAnalyzer:
    """
    Database Schema Analyzer for Text-to-SQL.
    
    Features:
    - Comprehensive schema extraction
    - LLM-friendly context generation
    - Intelligent table filtering
    - Incremental schema updates
    - Relevance scoring for queries
    """
    
    def __init__(self, max_tables_for_llm: int = 50):
        """
        Initialize Schema Analyzer.
        
        Args:
            max_tables_for_llm: Maximum tables to include in LLM context
        """
        self.max_tables_for_llm = max_tables_for_llm
        self._schema_cache: Dict[str, DatabaseSchema] = {}
        self._table_embeddings: Dict[str, Dict[str, List[float]]] = {}
        
        # Common business term mappings
        self._business_terms = {
            "用户": ["user", "users", "account", "accounts", "member", "members"],
            "订单": ["order", "orders", "purchase", "purchases"],
            "产品": ["product", "products", "item", "items", "goods"],
            "客户": ["customer", "customers", "client", "clients"],
            "销售": ["sale", "sales", "revenue"],
            "金额": ["amount", "price", "cost", "total", "sum"],
            "数量": ["quantity", "qty", "count", "number"],
            "日期": ["date", "day", "created_at", "updated_at"],
            "时间": ["time", "datetime", "timestamp"],
            "状态": ["status", "state", "condition"],
        }
    
    def analyze(self, connection_info: Dict[str, Any]) -> DatabaseSchema:
        """
        Analyze database schema from connection info.
        
        Args:
            connection_info: Database connection information
            
        Returns:
            DatabaseSchema with complete schema information
        """
        cache_key = self._get_cache_key(connection_info)
        
        if cache_key in self._schema_cache:
            cached = self._schema_cache[cache_key]
            # Return cached if less than 1 hour old
            if (datetime.utcnow() - cached.updated_at).total_seconds() < 3600:
                return cached
        
        tables = []
        relationships = []
        
        # Extract schema based on connection type
        if "tables" in connection_info:
            # Mock/test mode with provided schema
            tables = connection_info["tables"]
            relationships = connection_info.get("relationships", [])
        else:
            # Real database connection
            tables, relationships = self._extract_from_database(connection_info)
        
        # Build schema object
        schema = DatabaseSchema(
            tables=tables,
            relationships=relationships,
            updated_at=datetime.utcnow(),
            db_type=connection_info.get("db_type", "postgresql"),
            schema_hash=self._compute_schema_hash(tables)
        )
        
        # Cache result
        self._schema_cache[cache_key] = schema
        
        return schema
    
    def _extract_from_database(self, connection_info: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
        """Extract schema from actual database connection."""
        tables = []
        relationships = []
        
        try:
            from sqlalchemy import create_engine, inspect
            
            connection_string = connection_info.get("connection_string", "")
            if not connection_string:
                return tables, relationships
            
            engine = create_engine(connection_string, pool_pre_ping=True)
            inspector = inspect(engine)
            
            schema_name = connection_info.get("schema_name")
            table_names = inspector.get_table_names(schema=schema_name)
            
            for table_name in table_names:
                table_info = self._extract_table_info(inspector, table_name, schema_name)
                if table_info:
                    tables.append(table_info)
                    
                    # Extract relationships from foreign keys
                    fks = inspector.get_foreign_keys(table_name, schema=schema_name)
                    for fk in fks:
                        for i, col in enumerate(fk.get("constrained_columns", [])):
                            ref_cols = fk.get("referred_columns", [])
                            if i < len(ref_cols):
                                relationships.append({
                                    "from_table": table_name,
                                    "from_column": col,
                                    "to_table": fk.get("referred_table", ""),
                                    "to_column": ref_cols[i],
                                    "relationship_type": "foreign_key"
                                })
            
            engine.dispose()
            
        except Exception as e:
            logger.error(f"Failed to extract schema from database: {e}")
        
        return tables, relationships
    
    def _extract_table_info(self, inspector, table_name: str, schema_name: Optional[str]) -> Optional[Dict]:
        """Extract information for a single table."""
        try:
            columns = []
            pk_constraint = inspector.get_pk_constraint(table_name, schema=schema_name)
            pk_columns = set(pk_constraint.get("constrained_columns", []))
            
            fk_info = inspector.get_foreign_keys(table_name, schema=schema_name)
            fk_map = {}
            for fk in fk_info:
                for i, col in enumerate(fk.get("constrained_columns", [])):
                    ref_table = fk.get("referred_table", "")
                    ref_cols = fk.get("referred_columns", [])
                    if i < len(ref_cols):
                        fk_map[col] = f"{ref_table}.{ref_cols[i]}"
            
            for col in inspector.get_columns(table_name, schema=schema_name):
                columns.append({
                    "name": col["name"],
                    "data_type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": str(col.get("default")) if col.get("default") else None,
                    "is_primary_key": col["name"] in pk_columns,
                    "is_foreign_key": col["name"] in fk_map,
                    "references": fk_map.get(col["name"]),
                })
            
            # Get indexes
            indexes = []
            for idx in inspector.get_indexes(table_name, schema=schema_name):
                indexes.append({
                    "name": idx.get("name", ""),
                    "columns": idx.get("column_names", []),
                    "is_unique": idx.get("unique", False),
                })
            
            return {
                "name": table_name,
                "columns": columns,
                "primary_key": list(pk_columns),
                "indexes": indexes,
                "schema_name": schema_name,
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract table {table_name}: {e}")
            return None
    
    def to_llm_context(self, schema: DatabaseSchema, max_tables: Optional[int] = None) -> str:
        """
        Generate LLM-friendly schema description.
        
        Args:
            schema: Database schema to describe
            max_tables: Maximum tables to include (default: self.max_tables_for_llm)
            
        Returns:
            String description suitable for LLM prompt
        """
        max_tables = max_tables or self.max_tables_for_llm
        tables = schema.tables[:max_tables] if len(schema.tables) > max_tables else schema.tables
        
        lines = ["Database Schema:"]
        lines.append(f"Database Type: {schema.db_type or 'Unknown'}")
        lines.append(f"Total Tables: {len(schema.tables)}")
        
        if len(schema.tables) > max_tables:
            lines.append(f"(Showing {max_tables} most relevant tables)")
        
        lines.append("")
        
        for table in tables:
            table_name = table.get("name", "unknown")
            lines.append(f"Table: {table_name}")
            
            columns = table.get("columns", [])
            for col in columns:
                col_name = col.get("name", "")
                col_type = col.get("data_type", "")
                nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
                pk = " [PK]" if col.get("is_primary_key") else ""
                fk = f" [FK -> {col.get('references')}]" if col.get("is_foreign_key") else ""
                
                lines.append(f"  - {col_name}: {col_type} {nullable}{pk}{fk}")
            
            # Add primary key info
            pk_cols = table.get("primary_key", [])
            if pk_cols:
                lines.append(f"  Primary Key: ({', '.join(pk_cols)})")
            
            lines.append("")
        
        # Add relationships
        if schema.relationships:
            lines.append("Relationships:")
            for rel in schema.relationships:
                from_table = rel.get("from_table", "")
                from_col = rel.get("from_column", "")
                to_table = rel.get("to_table", "")
                to_col = rel.get("to_column", "")
                lines.append(f"  {from_table}.{from_col} -> {to_table}.{to_col}")
        
        return "\n".join(lines)
    
    def filter_relevant_tables(
        self,
        schema: DatabaseSchema,
        query: str,
        max_tables: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Filter tables relevant to the query.
        
        Args:
            schema: Database schema
            query: Natural language query
            max_tables: Maximum tables to return
            
        Returns:
            List of relevant tables sorted by relevance
        """
        if len(schema.tables) <= max_tables:
            return schema.tables
        
        # Score each table
        scored_tables = []
        query_lower = query.lower()
        query_terms = set(re.findall(r'\w+', query_lower))
        
        # Expand query terms with business term mappings
        expanded_terms = set(query_terms)
        for term in query_terms:
            for chinese, english_list in self._business_terms.items():
                if term == chinese or term in english_list:
                    expanded_terms.update(english_list)
                    expanded_terms.add(chinese)
        
        for table in schema.tables:
            score = self._calculate_relevance_score(table, expanded_terms, query_lower)
            scored_tables.append((score, table))
        
        # Sort by score descending
        scored_tables.sort(key=lambda x: x[0], reverse=True)
        
        # Return top tables
        return [t[1] for t in scored_tables[:max_tables]]
    
    def _calculate_relevance_score(
        self,
        table: Dict[str, Any],
        query_terms: Set[str],
        query_lower: str
    ) -> float:
        """Calculate relevance score for a table."""
        score = 0.0
        table_name = table.get("name", "").lower()
        
        # Direct table name match
        if table_name in query_lower:
            score += 10.0
        
        # Partial table name match
        for term in query_terms:
            if term in table_name or table_name in term:
                score += 5.0
        
        # Column name matches
        columns = table.get("columns", [])
        for col in columns:
            col_name = col.get("name", "").lower()
            if col_name in query_lower:
                score += 3.0
            for term in query_terms:
                if term in col_name or col_name in term:
                    score += 1.0
        
        # Boost for tables with foreign keys (likely important)
        fk_count = sum(1 for col in columns if col.get("is_foreign_key"))
        score += fk_count * 0.5
        
        return score
    
    def incremental_update(
        self,
        schema: DatabaseSchema,
        changes: List[SchemaChange]
    ) -> DatabaseSchema:
        """
        Apply incremental updates to schema.
        
        Args:
            schema: Current schema
            changes: List of schema changes
            
        Returns:
            Updated schema
        """
        tables = list(schema.tables)
        relationships = list(schema.relationships)
        
        for change in changes:
            if change.change_type == "add_table":
                if change.new_value:
                    tables.append(change.new_value)
                    
            elif change.change_type == "drop_table":
                tables = [t for t in tables if t.get("name") != change.table_name]
                relationships = [
                    r for r in relationships
                    if r.get("from_table") != change.table_name
                    and r.get("to_table") != change.table_name
                ]
                
            elif change.change_type == "add_column":
                for table in tables:
                    if table.get("name") == change.table_name and change.new_value:
                        table.setdefault("columns", []).append(change.new_value)
                        break
                        
            elif change.change_type == "drop_column":
                for table in tables:
                    if table.get("name") == change.table_name:
                        table["columns"] = [
                            c for c in table.get("columns", [])
                            if c.get("name") != change.column_name
                        ]
                        break
                        
            elif change.change_type == "modify_column":
                for table in tables:
                    if table.get("name") == change.table_name:
                        for i, col in enumerate(table.get("columns", [])):
                            if col.get("name") == change.column_name and change.new_value:
                                table["columns"][i] = change.new_value
                                break
                        break
        
        return DatabaseSchema(
            tables=tables,
            relationships=relationships,
            updated_at=datetime.utcnow(),
            db_type=schema.db_type,
            schema_hash=self._compute_schema_hash(tables)
        )
    
    def _get_cache_key(self, connection_info: Dict[str, Any]) -> str:
        """Generate cache key from connection info."""
        key_data = str(sorted(connection_info.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _compute_schema_hash(self, tables: List[Dict]) -> str:
        """Compute hash of schema for change detection."""
        import json
        schema_str = json.dumps(tables, sort_keys=True, default=str)
        return hashlib.sha256(schema_str.encode()).hexdigest()[:16]
    
    def clear_cache(self) -> None:
        """Clear schema cache."""
        self._schema_cache.clear()
        self._table_embeddings.clear()


# Global instance
_schema_analyzer: Optional[SchemaAnalyzer] = None


def get_schema_analyzer() -> SchemaAnalyzer:
    """Get or create global SchemaAnalyzer instance."""
    global _schema_analyzer
    if _schema_analyzer is None:
        _schema_analyzer = SchemaAnalyzer()
    return _schema_analyzer
