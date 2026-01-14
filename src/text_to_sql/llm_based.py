"""
LLM-based SQL Generation for Text-to-SQL Methods.

Implements SQL generation using Large Language Models with
validation, retry logic, and multiple framework support.
"""

import logging
import re
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from .schemas import (
    SQLGenerationResult,
    ValidationResult,
    MethodType,
)
from .schema_analyzer import DatabaseSchema

logger = logging.getLogger(__name__)


class LLMFramework(str, Enum):
    """Supported LLM frameworks."""
    LANGCHAIN = "langchain"
    SQLCODER = "sqlcoder"
    CUSTOM = "custom"
    OLLAMA = "ollama"


class SQLValidationError(Exception):
    """Exception for SQL validation errors."""
    pass


class LLMSQLGenerator:
    """
    LLM-based SQL Generator.
    
    Features:
    - Multiple LLM framework support (LangChain, SQLCoder, Ollama)
    - SQL syntax validation
    - Retry mechanism with error feedback
    - Prompt optimization for SQL generation
    """
    
    def __init__(
        self,
        llm_adapter: Optional[Any] = None,
        max_retries: int = 3,
        default_framework: LLMFramework = LLMFramework.OLLAMA
    ):
        """
        Initialize LLM SQL Generator.
        
        Args:
            llm_adapter: LLM adapter instance (optional, will use default)
            max_retries: Maximum retry attempts on failure
            default_framework: Default LLM framework to use
        """
        self._llm_adapter = llm_adapter
        self.max_retries = max_retries
        self.default_framework = default_framework
        
        # Statistics
        self._total_calls = 0
        self._successful_calls = 0
        self._retry_count = 0
    
    @property
    def llm_adapter(self):
        """Get LLM adapter, initializing if needed."""
        if self._llm_adapter is None:
            try:
                from .llm_adapter import get_llm_adapter
                self._llm_adapter = get_llm_adapter()
            except ImportError:
                logger.warning("LLM adapter not available")
        return self._llm_adapter
    
    async def generate(
        self,
        query: str,
        schema: Optional[DatabaseSchema] = None,
        framework: Optional[LLMFramework] = None,
        db_type: str = "postgresql"
    ) -> SQLGenerationResult:
        """
        Generate SQL from natural language using LLM.
        
        Args:
            query: Natural language query
            schema: Database schema for context
            framework: LLM framework to use
            db_type: Target database type
            
        Returns:
            SQLGenerationResult with generated SQL
        """
        start_time = time.time()
        self._total_calls += 1
        
        framework = framework or self.default_framework
        
        try:
            # Build prompt
            prompt = self.build_prompt(query, schema, db_type)
            
            # Generate SQL
            sql, confidence, model_used = await self._call_llm(prompt, framework)
            
            # Validate SQL
            validation = self.validate_sql(sql, db_type)
            
            if not validation.is_valid:
                # Retry with error feedback
                sql, confidence = await self._retry_with_feedback(
                    query, schema, db_type, framework, sql, validation.errors
                )
                validation = self.validate_sql(sql, db_type)
            
            execution_time = (time.time() - start_time) * 1000
            
            if validation.is_valid:
                self._successful_calls += 1
            
            return SQLGenerationResult(
                sql=sql,
                method_used="llm",
                confidence=confidence if validation.is_valid else confidence * 0.5,
                execution_time_ms=execution_time,
                formatted_sql=self._format_sql(sql),
                explanation=self._generate_explanation(query, sql),
                metadata={
                    "framework": framework.value,
                    "model_used": model_used,
                    "db_type": db_type,
                    "validation": {
                        "is_valid": validation.is_valid,
                        "errors": validation.errors,
                        "warnings": validation.warnings,
                    },
                    "retry_count": self._retry_count,
                },
            )
            
        except Exception as e:
            logger.error(f"LLM SQL generation failed: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return SQLGenerationResult(
                sql="",
                method_used="llm",
                confidence=0.0,
                execution_time_ms=execution_time,
                metadata={
                    "error": str(e),
                    "framework": framework.value if framework else "unknown",
                },
            )
    
    def build_prompt(
        self,
        query: str,
        schema: Optional[DatabaseSchema] = None,
        db_type: str = "postgresql"
    ) -> str:
        """
        Build optimized prompt for SQL generation.
        
        Args:
            query: Natural language query
            schema: Database schema
            db_type: Target database type
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # System instruction
        prompt_parts.append(f"""You are an expert SQL developer. Generate a valid {db_type.upper()} SQL query based on the user's natural language request.

Rules:
1. Generate ONLY the SQL query, no explanations
2. Use proper {db_type.upper()} syntax
3. Only use SELECT statements (no INSERT, UPDATE, DELETE, DROP)
4. Use table and column names from the provided schema
5. Handle NULL values appropriately
6. Use appropriate JOINs when multiple tables are needed
""")
        
        # Schema context
        if schema and schema.tables:
            prompt_parts.append("\nDatabase Schema:")
            for table in schema.tables[:20]:  # Limit to 20 tables
                table_name = table.get("name", "unknown")
                columns = table.get("columns", [])
                col_strs = []
                for col in columns[:15]:  # Limit columns
                    col_name = col.get("name", "")
                    col_type = col.get("data_type", "")
                    pk = " [PK]" if col.get("is_primary_key") else ""
                    fk = f" [FK]" if col.get("is_foreign_key") else ""
                    col_strs.append(f"  - {col_name}: {col_type}{pk}{fk}")
                
                prompt_parts.append(f"\nTable: {table_name}")
                prompt_parts.append("\n".join(col_strs))
        
        # User query
        prompt_parts.append(f"\nUser Request: {query}")
        prompt_parts.append("\nSQL Query:")
        
        return "\n".join(prompt_parts)
    
    async def _call_llm(
        self,
        prompt: str,
        framework: LLMFramework
    ) -> Tuple[str, float, str]:
        """
        Call LLM to generate SQL.
        
        Returns:
            Tuple of (sql, confidence, model_used)
        """
        model_used = "unknown"
        confidence = 0.8
        
        if self.llm_adapter is None:
            # Fallback: return empty result
            return "", 0.0, "none"
        
        try:
            if framework == LLMFramework.OLLAMA:
                result = await self._call_ollama(prompt)
            elif framework == LLMFramework.LANGCHAIN:
                result = await self._call_langchain(prompt)
            elif framework == LLMFramework.SQLCODER:
                result = await self._call_sqlcoder(prompt)
            else:
                result = await self._call_custom(prompt)
            
            sql = result.get("sql", "")
            confidence = result.get("confidence", 0.8)
            model_used = result.get("model_used", "unknown")
            
            # Clean SQL
            sql = self._clean_sql(sql)
            
            return sql, confidence, model_used
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return "", 0.0, "error"
    
    async def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama for SQL generation."""
        try:
            if hasattr(self.llm_adapter, 'generate_sql_simple'):
                result = await self.llm_adapter.generate_sql_simple(prompt, "", "postgresql")
                return {
                    "sql": result.get("sql", ""),
                    "confidence": result.get("confidence", 0.8),
                    "model_used": result.get("model_used", "ollama"),
                }
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
        
        return {"sql": "", "confidence": 0.0, "model_used": "ollama"}
    
    async def _call_langchain(self, prompt: str) -> Dict[str, Any]:
        """Call LangChain for SQL generation."""
        # Placeholder for LangChain integration
        return await self._call_ollama(prompt)
    
    async def _call_sqlcoder(self, prompt: str) -> Dict[str, Any]:
        """Call SQLCoder for SQL generation."""
        # Placeholder for SQLCoder integration
        return await self._call_ollama(prompt)
    
    async def _call_custom(self, prompt: str) -> Dict[str, Any]:
        """Call custom LLM for SQL generation."""
        return await self._call_ollama(prompt)
    
    def _clean_sql(self, sql: str) -> str:
        """Clean and extract SQL from LLM response."""
        if not sql:
            return ""
        
        # Remove markdown code blocks
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        
        # Remove leading/trailing whitespace
        sql = sql.strip()
        
        # Extract first SQL statement if multiple
        if ";" in sql:
            statements = sql.split(";")
            for stmt in statements:
                stmt = stmt.strip()
                if stmt.upper().startswith("SELECT") or stmt.upper().startswith("WITH"):
                    sql = stmt
                    break
        
        return sql
    
    def validate_sql(self, sql: str, db_type: str = "postgresql") -> ValidationResult:
        """
        Validate SQL syntax and safety.
        
        Args:
            sql: SQL query to validate
            db_type: Database type for dialect-specific validation
            
        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []
        
        if not sql or not sql.strip():
            errors.append("SQL query is empty")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        sql_upper = sql.upper().strip()
        
        # Check for SELECT/WITH start
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            # Check for dangerous operations
            dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
            for op in dangerous:
                if sql_upper.startswith(op):
                    errors.append(f"Dangerous operation not allowed: {op}")
                    break
            else:
                errors.append("Query must start with SELECT or WITH")
        
        # Check for incomplete FROM clause
        if "FROM" in sql_upper:
            from_match = re.search(r'\bFROM\s*$', sql_upper)
            if from_match:
                errors.append("Incomplete FROM clause - missing table name")
            # Also check for FROM followed only by whitespace
            from_match2 = re.search(r'\bFROM\s+$', sql.strip(), re.IGNORECASE)
            if from_match2:
                errors.append("Incomplete FROM clause - missing table name")
        
        # Check for incomplete WHERE clause
        if re.search(r'\bWHERE\s*$', sql_upper):
            errors.append("Incomplete WHERE clause - missing condition")
        
        # Check balanced parentheses
        if sql.count("(") != sql.count(")"):
            errors.append("Unbalanced parentheses")
        
        # Check balanced quotes
        if sql.count("'") % 2 != 0:
            errors.append("Unclosed single quote")
        
        if sql.count('"') % 2 != 0:
            errors.append("Unclosed double quote")
        
        # Check for SQL injection patterns
        injection_patterns = [
            (r';\s*DROP', "Potential SQL injection: DROP after semicolon"),
            (r';\s*DELETE', "Potential SQL injection: DELETE after semicolon"),
            (r';\s*UPDATE', "Potential SQL injection: UPDATE after semicolon"),
            (r';\s*INSERT', "Potential SQL injection: INSERT after semicolon"),
        ]
        
        for pattern, message in injection_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                errors.append(message)
        
        # Performance warnings
        if "SELECT *" in sql_upper:
            warnings.append("Using SELECT * may impact performance")
        
        if "LIKE '%'" in sql_upper or re.search(r"LIKE\s+'%", sql, re.IGNORECASE):
            warnings.append("Leading wildcard in LIKE may prevent index usage")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    async def _retry_with_feedback(
        self,
        query: str,
        schema: Optional[DatabaseSchema],
        db_type: str,
        framework: LLMFramework,
        failed_sql: str,
        errors: List[str]
    ) -> Tuple[str, float]:
        """
        Retry SQL generation with error feedback.
        
        Returns:
            Tuple of (sql, confidence)
        """
        for attempt in range(self.max_retries):
            self._retry_count += 1
            
            # Build retry prompt with error feedback
            retry_prompt = self._build_retry_prompt(
                query, schema, db_type, failed_sql, errors
            )
            
            try:
                sql, confidence, _ = await self._call_llm(retry_prompt, framework)
                
                # Validate
                validation = self.validate_sql(sql, db_type)
                
                if validation.is_valid:
                    return sql, confidence * 0.9  # Slightly lower confidence for retry
                
                # Update for next retry
                failed_sql = sql
                errors = validation.errors
                
            except Exception as e:
                logger.warning(f"Retry {attempt + 1} failed: {e}")
        
        # Return last attempt even if invalid
        return failed_sql, 0.3
    
    def _build_retry_prompt(
        self,
        query: str,
        schema: Optional[DatabaseSchema],
        db_type: str,
        failed_sql: str,
        errors: List[str]
    ) -> str:
        """Build prompt for retry with error feedback."""
        base_prompt = self.build_prompt(query, schema, db_type)
        
        error_feedback = f"""

Previous attempt failed with errors:
{chr(10).join(f'- {e}' for e in errors)}

Failed SQL:
{failed_sql}

Please fix the errors and generate a valid SQL query.
SQL Query:"""
        
        return base_prompt + error_feedback
    
    def _format_sql(self, sql: str) -> str:
        """Format SQL for readability."""
        if not sql:
            return ""
        
        # Uppercase keywords
        keywords = [
            "SELECT", "FROM", "WHERE", "JOIN", "LEFT JOIN", "RIGHT JOIN",
            "INNER JOIN", "OUTER JOIN", "ON", "AND", "OR", "ORDER BY",
            "GROUP BY", "HAVING", "LIMIT", "OFFSET", "WITH", "AS",
            "UNION", "INTERSECT", "EXCEPT", "DISTINCT", "COUNT", "SUM",
            "AVG", "MAX", "MIN", "CASE", "WHEN", "THEN", "ELSE", "END",
            "IN", "NOT", "NULL", "IS", "LIKE", "BETWEEN", "EXISTS"
        ]
        
        formatted = sql
        for kw in keywords:
            pattern = rf'\b{kw}\b'
            formatted = re.sub(pattern, kw, formatted, flags=re.IGNORECASE)
        
        # Add newlines before major clauses
        major_clauses = ["FROM", "WHERE", "JOIN", "LEFT JOIN", "RIGHT JOIN",
                        "ORDER BY", "GROUP BY", "HAVING", "LIMIT"]
        for clause in major_clauses:
            formatted = re.sub(rf'\s+{clause}\b', f'\n{clause}', formatted, flags=re.IGNORECASE)
        
        return formatted.strip()
    
    def _generate_explanation(self, query: str, sql: str) -> str:
        """Generate natural language explanation of the SQL."""
        if not sql:
            return ""
        
        explanation_parts = []
        sql_upper = sql.upper()
        
        # Detect query type
        if "COUNT(" in sql_upper:
            explanation_parts.append("统计数量")
        elif "SUM(" in sql_upper:
            explanation_parts.append("计算总和")
        elif "AVG(" in sql_upper:
            explanation_parts.append("计算平均值")
        elif "MAX(" in sql_upper:
            explanation_parts.append("查找最大值")
        elif "MIN(" in sql_upper:
            explanation_parts.append("查找最小值")
        else:
            explanation_parts.append("查询数据")
        
        # Detect joins
        if "JOIN" in sql_upper:
            explanation_parts.append("关联多表")
        
        # Detect filters
        if "WHERE" in sql_upper:
            explanation_parts.append("带条件筛选")
        
        # Detect grouping
        if "GROUP BY" in sql_upper:
            explanation_parts.append("分组统计")
        
        # Detect ordering
        if "ORDER BY" in sql_upper:
            if "DESC" in sql_upper:
                explanation_parts.append("降序排列")
            else:
                explanation_parts.append("升序排列")
        
        return "，".join(explanation_parts)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return {
            "total_calls": self._total_calls,
            "successful_calls": self._successful_calls,
            "success_rate": self._successful_calls / max(1, self._total_calls),
            "total_retries": self._retry_count,
        }


# Global instance
_llm_sql_generator: Optional[LLMSQLGenerator] = None


def get_llm_sql_generator() -> LLMSQLGenerator:
    """Get or create global LLMSQLGenerator instance."""
    global _llm_sql_generator
    if _llm_sql_generator is None:
        _llm_sql_generator = LLMSQLGenerator()
    return _llm_sql_generator
