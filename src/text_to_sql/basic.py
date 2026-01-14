"""
Template-based SQL Generation for Text-to-SQL Methods.

Implements template matching and parameter filling for common SQL patterns.
"""

import logging
import re
import os
import json
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .schemas import (
    SQLGenerationResult,
    SQLTemplate,
    TemplateMatch,
    ValidationResult,
    TemplateCategory,
    ParamType,
    MethodType,
)
from .schema_analyzer import DatabaseSchema

logger = logging.getLogger(__name__)


class TemplateFiller:
    """
    SQL Template Filler for template-based SQL generation.
    
    Features:
    - Pattern matching for natural language queries
    - Parameter extraction and validation
    - Type coercion for parameters
    - Fallback suggestions when no match found
    """
    
    def __init__(self, templates_path: Optional[str] = None):
        """
        Initialize Template Filler.
        
        Args:
            templates_path: Path to templates directory or file
        """
        self.templates: List[SQLTemplate] = []
        self._load_default_templates()
        
        if templates_path:
            self._load_templates_from_path(templates_path)
    
    def _load_default_templates(self) -> None:
        """Load default SQL templates."""
        default_templates = [
            # Aggregate templates
            SQLTemplate(
                id="aggregate_count",
                name="统计数量",
                pattern=r"(?:统计|查询|获取|计算)(.+?)的(?:数量|总数|个数|条数)",
                template="SELECT COUNT(*) AS count FROM {table}",
                param_types={"table": ParamType.STRING},
                category=TemplateCategory.AGGREGATE,
                description="Count records in a table",
                examples=["统计用户的数量", "查询订单的总数"],
                priority=10,
            ),
            SQLTemplate(
                id="aggregate_count_where",
                name="条件统计数量",
                pattern=r"(?:统计|查询|获取)(.+?)(?:中|里)?(.+?)的(?:数量|总数|个数)",
                template="SELECT COUNT(*) AS count FROM {table} WHERE {condition}",
                param_types={"table": ParamType.STRING, "condition": ParamType.STRING},
                category=TemplateCategory.AGGREGATE,
                description="Count records with condition",
                examples=["统计订单中已完成的数量"],
                priority=9,
            ),
            SQLTemplate(
                id="aggregate_sum",
                name="求和",
                pattern=r"(?:计算|求|统计)(.+?)的(?:总|合计)?(.+?)(?:和|总和|总额)?",
                template="SELECT SUM({column}) AS total FROM {table}",
                param_types={"table": ParamType.STRING, "column": ParamType.STRING},
                category=TemplateCategory.AGGREGATE,
                description="Sum a column",
                examples=["计算订单的总金额", "求销售的总额"],
                priority=8,
            ),
            SQLTemplate(
                id="aggregate_avg",
                name="平均值",
                pattern=r"(?:计算|求|统计)(.+?)的平均(.+)",
                template="SELECT AVG({column}) AS average FROM {table}",
                param_types={"table": ParamType.STRING, "column": ParamType.STRING},
                category=TemplateCategory.AGGREGATE,
                description="Calculate average",
                examples=["计算订单的平均金额"],
                priority=8,
            ),
            SQLTemplate(
                id="aggregate_max",
                name="最大值",
                pattern=r"(?:查询|获取|找出)(.+?)(?:中|的)?最(?:大|高)的?(.+)",
                template="SELECT MAX({column}) AS max_value FROM {table}",
                param_types={"table": ParamType.STRING, "column": ParamType.STRING},
                category=TemplateCategory.AGGREGATE,
                description="Find maximum value",
                examples=["查询订单中最大的金额"],
                priority=8,
            ),
            SQLTemplate(
                id="aggregate_min",
                name="最小值",
                pattern=r"(?:查询|获取|找出)(.+?)(?:中|的)?最(?:小|低)的?(.+)",
                template="SELECT MIN({column}) AS min_value FROM {table}",
                param_types={"table": ParamType.STRING, "column": ParamType.STRING},
                category=TemplateCategory.AGGREGATE,
                description="Find minimum value",
                examples=["查询订单中最小的金额"],
                priority=8,
            ),
            
            # Filter templates
            SQLTemplate(
                id="filter_by_date_range",
                name="按日期范围筛选",
                pattern=r"(?:查询|获取|筛选)(.+?)从(.+?)到(.+?)的(?:数据|记录)?",
                template="SELECT * FROM {table} WHERE {date_column} BETWEEN '{start_date}' AND '{end_date}'",
                param_types={
                    "table": ParamType.STRING,
                    "date_column": ParamType.STRING,
                    "start_date": ParamType.DATE,
                    "end_date": ParamType.DATE,
                },
                category=TemplateCategory.FILTER,
                description="Filter by date range",
                examples=["查询订单从2024-01-01到2024-12-31的数据"],
                priority=7,
            ),
            SQLTemplate(
                id="filter_by_status",
                name="按状态筛选",
                pattern=r"(?:查询|获取|筛选)(?:所有)?(.+?)(?:为|是|状态为?)(.+?)的(.+)",
                template="SELECT * FROM {table} WHERE {status_column} = '{status_value}'",
                param_types={
                    "table": ParamType.STRING,
                    "status_column": ParamType.STRING,
                    "status_value": ParamType.STRING,
                },
                category=TemplateCategory.FILTER,
                description="Filter by status",
                examples=["查询状态为已完成的订单"],
                priority=6,
            ),
            SQLTemplate(
                id="filter_by_value",
                name="按值筛选",
                pattern=r"(?:查询|获取|筛选)(.+?)(?:大于|小于|等于)(.+?)的(.+)",
                template="SELECT * FROM {table} WHERE {column} {operator} {value}",
                param_types={
                    "table": ParamType.STRING,
                    "column": ParamType.STRING,
                    "operator": ParamType.STRING,
                    "value": ParamType.NUMBER,
                },
                category=TemplateCategory.FILTER,
                description="Filter by numeric value",
                examples=["查询金额大于1000的订单"],
                priority=6,
            ),
            
            # Sort templates
            SQLTemplate(
                id="sort_desc",
                name="降序排序",
                pattern=r"(?:查询|获取|列出)(.+?)(?:按|根据)(.+?)(?:降序|从高到低|倒序)(?:排序|排列)?",
                template="SELECT * FROM {table} ORDER BY {column} DESC",
                param_types={"table": ParamType.STRING, "column": ParamType.STRING},
                category=TemplateCategory.SORT,
                description="Sort descending",
                examples=["查询订单按金额降序排序"],
                priority=5,
            ),
            SQLTemplate(
                id="sort_asc",
                name="升序排序",
                pattern=r"(?:查询|获取|列出)(.+?)(?:按|根据)(.+?)(?:升序|从低到高|正序)(?:排序|排列)?",
                template="SELECT * FROM {table} ORDER BY {column} ASC",
                param_types={"table": ParamType.STRING, "column": ParamType.STRING},
                category=TemplateCategory.SORT,
                description="Sort ascending",
                examples=["查询订单按日期升序排序"],
                priority=5,
            ),
            SQLTemplate(
                id="top_n",
                name="前N条记录",
                pattern=r"(?:查询|获取|列出)(?:前)?(\d+)(?:条|个|名)?(.+)",
                template="SELECT * FROM {table} LIMIT {limit}",
                param_types={"table": ParamType.STRING, "limit": ParamType.NUMBER},
                category=TemplateCategory.SORT,
                description="Get top N records",
                examples=["查询前10条订单", "获取前5个用户"],
                priority=5,
            ),
            
            # Group templates
            SQLTemplate(
                id="group_count",
                name="分组统计",
                pattern=r"(?:按|根据)(.+?)(?:分组)?统计(.+?)的(?:数量|个数)",
                template="SELECT {group_column}, COUNT(*) AS count FROM {table} GROUP BY {group_column}",
                param_types={"table": ParamType.STRING, "group_column": ParamType.STRING},
                category=TemplateCategory.GROUP,
                description="Group and count",
                examples=["按状态分组统计订单的数量"],
                priority=7,
            ),
            SQLTemplate(
                id="group_sum",
                name="分组求和",
                pattern=r"(?:按|根据)(.+?)(?:分组)?(?:统计|计算)(.+?)的(?:总|合计)?(.+)",
                template="SELECT {group_column}, SUM({sum_column}) AS total FROM {table} GROUP BY {group_column}",
                param_types={
                    "table": ParamType.STRING,
                    "group_column": ParamType.STRING,
                    "sum_column": ParamType.STRING,
                },
                category=TemplateCategory.GROUP,
                description="Group and sum",
                examples=["按类别分组统计销售的总金额"],
                priority=7,
            ),
            
            # Join templates
            SQLTemplate(
                id="join_two_tables",
                name="两表关联",
                pattern=r"(?:查询|获取)(.+?)(?:和|与)(.+?)(?:关联|连接)的(?:数据|记录)?",
                template="SELECT * FROM {table1} JOIN {table2} ON {table1}.{join_column1} = {table2}.{join_column2}",
                param_types={
                    "table1": ParamType.STRING,
                    "table2": ParamType.STRING,
                    "join_column1": ParamType.STRING,
                    "join_column2": ParamType.STRING,
                },
                category=TemplateCategory.JOIN,
                description="Join two tables",
                examples=["查询订单和用户关联的数据"],
                priority=6,
            ),
            
            # Simple select
            SQLTemplate(
                id="select_all",
                name="查询所有",
                pattern=r"(?:查询|获取|列出|显示)(?:所有)?(.+?)(?:的数据|的记录|表)?$",
                template="SELECT * FROM {table}",
                param_types={"table": ParamType.STRING},
                category=TemplateCategory.FILTER,
                description="Select all from table",
                examples=["查询所有用户", "列出订单表"],
                priority=1,
            ),
        ]
        
        self.templates.extend(default_templates)
        # Sort by priority (higher first)
        self.templates.sort(key=lambda t: t.priority, reverse=True)
    
    def _load_templates_from_path(self, path: str) -> None:
        """Load templates from file or directory."""
        path_obj = Path(path)
        
        if path_obj.is_file():
            self._load_templates_from_file(path_obj)
        elif path_obj.is_dir():
            for file_path in path_obj.glob("*.json"):
                self._load_templates_from_file(file_path)
            for file_path in path_obj.glob("*.yaml"):
                self._load_templates_from_file(file_path)
    
    def _load_templates_from_file(self, file_path: Path) -> None:
        """Load templates from a single file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if file_path.suffix == ".json":
                    data = json.load(f)
                elif file_path.suffix in [".yaml", ".yml"]:
                    import yaml
                    data = yaml.safe_load(f)
                else:
                    return
            
            templates = data.get("templates", [])
            for t in templates:
                template = SQLTemplate(
                    id=t.get("id", ""),
                    name=t.get("name", ""),
                    pattern=t.get("pattern", ""),
                    template=t.get("template", ""),
                    param_types={k: ParamType(v) for k, v in t.get("param_types", {}).items()},
                    category=TemplateCategory(t.get("category", "filter")),
                    description=t.get("description"),
                    examples=t.get("examples", []),
                    priority=t.get("priority", 0),
                    enabled=t.get("enabled", True),
                )
                self.templates.append(template)
            
            # Re-sort by priority
            self.templates.sort(key=lambda t: t.priority, reverse=True)
            logger.info(f"Loaded {len(templates)} templates from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load templates from {file_path}: {e}")
    
    def match_template(self, query: str) -> Optional[TemplateMatch]:
        """
        Match query to a template.
        
        Args:
            query: Natural language query
            
        Returns:
            TemplateMatch if found, None otherwise
        """
        query = query.strip()
        
        for template in self.templates:
            if not template.enabled:
                continue
            
            try:
                match = re.search(template.pattern, query, re.IGNORECASE)
                if match:
                    # Extract groups
                    groups = {f"group_{i}": g for i, g in enumerate(match.groups())}
                    
                    # Calculate match score based on coverage
                    match_length = match.end() - match.start()
                    match_score = match_length / len(query) if query else 0.0
                    
                    return TemplateMatch(
                        template=template,
                        params={},  # Will be filled by extract_params
                        match_score=min(1.0, match_score + 0.5),  # Boost score
                        groups=groups,
                    )
            except re.error as e:
                logger.warning(f"Invalid regex pattern in template {template.id}: {e}")
        
        return None
    
    def extract_params(
        self,
        query: str,
        template: SQLTemplate,
        schema: Optional[DatabaseSchema] = None
    ) -> Dict[str, Any]:
        """
        Extract parameters from query for template.
        
        Args:
            query: Natural language query
            template: Matched template
            schema: Optional database schema for validation
            
        Returns:
            Dictionary of extracted parameters
        """
        params = {}
        
        try:
            match = re.search(template.pattern, query, re.IGNORECASE)
            if not match:
                return params
            
            groups = match.groups()
            param_names = list(template.param_types.keys())
            
            # Map groups to parameters
            for i, group in enumerate(groups):
                if i < len(param_names):
                    param_name = param_names[i]
                    params[param_name] = self._clean_param(group)
            
            # Try to infer missing parameters from schema
            if schema and "table" in template.param_types and "table" not in params:
                # Try to find table name in query
                for table in schema.tables:
                    table_name = table.get("name", "")
                    if table_name.lower() in query.lower():
                        params["table"] = table_name
                        break
            
        except Exception as e:
            logger.error(f"Failed to extract params: {e}")
        
        return params
    
    def _clean_param(self, value: str) -> str:
        """Clean extracted parameter value."""
        if not value:
            return ""
        
        # Remove common suffixes/prefixes
        value = value.strip()
        value = re.sub(r"^(的|中|里|表|数据|记录)", "", value)
        value = re.sub(r"(的|中|里|表|数据|记录)$", "", value)
        
        return value.strip()
    
    def fill_template(self, template: SQLTemplate, params: Dict[str, Any]) -> str:
        """
        Fill template with parameters.
        
        Args:
            template: SQL template
            params: Parameter values
            
        Returns:
            Filled SQL query
        """
        sql = template.template
        
        for param_name, param_value in params.items():
            placeholder = "{" + param_name + "}"
            if placeholder in sql:
                # Escape single quotes in string values
                if isinstance(param_value, str):
                    param_value = param_value.replace("'", "''")
                sql = sql.replace(placeholder, str(param_value))
        
        return sql
    
    def validate_params(
        self,
        params: Dict[str, Any],
        param_types: Dict[str, ParamType]
    ) -> ValidationResult:
        """
        Validate parameter types.
        
        Args:
            params: Parameter values
            param_types: Expected parameter types
            
        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []
        coerced_params = {}
        
        for param_name, expected_type in param_types.items():
            if param_name not in params:
                errors.append(f"Missing required parameter: {param_name}")
                continue
            
            value = params[param_name]
            coerced_value, error = self._coerce_type(value, expected_type)
            
            if error:
                errors.append(f"Parameter '{param_name}': {error}")
            else:
                coerced_params[param_name] = coerced_value
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            coerced_params=coerced_params,
        )
    
    def _coerce_type(self, value: Any, expected_type: ParamType) -> Tuple[Any, Optional[str]]:
        """
        Coerce value to expected type.
        
        Returns:
            Tuple of (coerced_value, error_message)
        """
        try:
            if expected_type == ParamType.STRING:
                return str(value), None
                
            elif expected_type == ParamType.NUMBER:
                # Try to extract number from string
                if isinstance(value, str):
                    numbers = re.findall(r'-?\d+\.?\d*', value)
                    if numbers:
                        num_str = numbers[0]
                        if '.' in num_str:
                            return float(num_str), None
                        return int(num_str), None
                    return None, f"Cannot convert '{value}' to number"
                return float(value), None
                
            elif expected_type == ParamType.DATE:
                if isinstance(value, (date, datetime)):
                    return value.strftime("%Y-%m-%d"), None
                # Try to parse date string
                date_patterns = [
                    r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
                    r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                ]
                for pattern in date_patterns:
                    match = re.search(pattern, str(value))
                    if match:
                        return match.group(1).replace("/", "-"), None
                return str(value), None
                
            elif expected_type == ParamType.DATETIME:
                if isinstance(value, datetime):
                    return value.strftime("%Y-%m-%d %H:%M:%S"), None
                return str(value), None
                
            elif expected_type == ParamType.BOOLEAN:
                if isinstance(value, bool):
                    return value, None
                value_lower = str(value).lower()
                if value_lower in ["true", "1", "yes", "是"]:
                    return True, None
                if value_lower in ["false", "0", "no", "否"]:
                    return False, None
                return None, f"Cannot convert '{value}' to boolean"
                
            elif expected_type == ParamType.LIST:
                if isinstance(value, list):
                    return value, None
                # Try to split by comma
                return [v.strip() for v in str(value).split(",")], None
                
            else:
                return str(value), None
                
        except Exception as e:
            return None, str(e)
    
    def generate(
        self,
        query: str,
        schema: Optional[DatabaseSchema] = None
    ) -> SQLGenerationResult:
        """
        Generate SQL from natural language query using templates.
        
        Args:
            query: Natural language query
            schema: Optional database schema
            
        Returns:
            SQLGenerationResult
        """
        import time
        start_time = time.time()
        
        # Try to match template
        match = self.match_template(query)
        
        if not match:
            # No template matched
            execution_time = (time.time() - start_time) * 1000
            return SQLGenerationResult(
                sql="",
                method_used="template",
                confidence=0.0,
                execution_time_ms=execution_time,
                metadata={
                    "error": "No matching template found",
                    "suggestions": self._get_fallback_suggestions(query),
                },
            )
        
        # Extract parameters
        params = self.extract_params(query, match.template, schema)
        
        # Validate parameters
        validation = self.validate_params(params, match.template.param_types)
        
        if not validation.is_valid:
            execution_time = (time.time() - start_time) * 1000
            return SQLGenerationResult(
                sql="",
                method_used="template",
                confidence=0.0,
                execution_time_ms=execution_time,
                template_id=match.template.id,
                metadata={
                    "error": "Parameter validation failed",
                    "validation_errors": validation.errors,
                    "extracted_params": params,
                },
            )
        
        # Fill template
        sql = self.fill_template(match.template, validation.coerced_params)
        
        execution_time = (time.time() - start_time) * 1000
        
        return SQLGenerationResult(
            sql=sql,
            method_used="template",
            confidence=match.match_score,
            execution_time_ms=execution_time,
            template_id=match.template.id,
            metadata={
                "template_name": match.template.name,
                "template_category": match.template.category.value,
                "extracted_params": validation.coerced_params,
            },
        )
    
    def _get_fallback_suggestions(self, query: str) -> List[str]:
        """Get suggestions when no template matches."""
        suggestions = []
        
        # Suggest similar templates based on keywords
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ["统计", "数量", "count", "总数"]):
            suggestions.append("尝试: '统计[表名]的数量'")
        if any(kw in query_lower for kw in ["求和", "总", "sum", "合计"]):
            suggestions.append("尝试: '计算[表名]的总[列名]'")
        if any(kw in query_lower for kw in ["排序", "order", "sort"]):
            suggestions.append("尝试: '查询[表名]按[列名]降序排序'")
        if any(kw in query_lower for kw in ["分组", "group"]):
            suggestions.append("尝试: '按[列名]分组统计[表名]的数量'")
        
        if not suggestions:
            suggestions.append("尝试使用更具体的查询模式，如 '统计用户的数量' 或 '查询订单按金额降序排序'")
        
        return suggestions
    
    def add_template(self, template: SQLTemplate) -> None:
        """Add a new template."""
        self.templates.append(template)
        self.templates.sort(key=lambda t: t.priority, reverse=True)
    
    def remove_template(self, template_id: str) -> bool:
        """Remove a template by ID."""
        for i, t in enumerate(self.templates):
            if t.id == template_id:
                del self.templates[i]
                return True
        return False
    
    def get_template(self, template_id: str) -> Optional[SQLTemplate]:
        """Get template by ID."""
        for t in self.templates:
            if t.id == template_id:
                return t
        return None
    
    def list_templates(self, category: Optional[TemplateCategory] = None) -> List[SQLTemplate]:
        """List all templates, optionally filtered by category."""
        if category:
            return [t for t in self.templates if t.category == category]
        return list(self.templates)


# Global instance
_template_filler: Optional[TemplateFiller] = None


def get_template_filler() -> TemplateFiller:
    """Get or create global TemplateFiller instance."""
    global _template_filler
    if _template_filler is None:
        _template_filler = TemplateFiller()
    return _template_filler
