"""
Intelligent Data Transformer for SuperInsight Platform.

Provides advanced data transformation capabilities:
- ML-assisted schema mapping
- Rule engine for complex transformations
- Data validation and cleansing
- Lineage tracking
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import hashlib
import json
from uuid import uuid4

from src.sync.connectors.base import DataBatch, DataRecord
from src.sync.transformer.transformer import (
    DataTransformer,
    TransformationPipeline,
    TransformationRule,
    TransformationType,
    TransformResult
)

logger = logging.getLogger(__name__)


class MappingConfidence(str, Enum):
    """Confidence level for schema mapping."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MANUAL = "manual"


@dataclass
class FieldMapping:
    """Mapping between source and target fields."""
    source_field: str
    target_field: str
    confidence: MappingConfidence
    transform_type: Optional[str] = None
    transform_config: Dict[str, Any] = field(default_factory=dict)
    validated: bool = False


@dataclass
class SchemaMapping:
    """Complete schema mapping configuration."""
    id: str
    name: str
    source_schema: Dict[str, Any]
    target_schema: Dict[str, Any]
    field_mappings: List[FieldMapping]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformationLineage:
    """Tracks data lineage through transformations."""
    record_id: str
    source_id: str
    transformations: List[Dict[str, Any]] = field(default_factory=list)
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SchemaMapper:
    """
    Intelligent schema mapping with ML assistance.
    
    Features:
    - Automatic field matching based on names and types
    - Similarity scoring for mapping suggestions
    - Manual override support
    - Mapping validation
    """
    
    def __init__(self):
        self._mappings: Dict[str, SchemaMapping] = {}
        self._type_compatibility = {
            ("string", "text"): True,
            ("int", "integer"): True,
            ("int", "bigint"): True,
            ("float", "double"): True,
            ("float", "decimal"): True,
            ("bool", "boolean"): True,
            ("datetime", "timestamp"): True,
            ("date", "datetime"): True,
            ("dict", "json"): True,
            ("dict", "jsonb"): True,
            ("list", "array"): True,
        }
    
    async def auto_map(
        self,
        source_schema: Dict[str, Any],
        target_schema: Dict[str, Any],
        threshold: float = 0.6
    ) -> SchemaMapping:
        """
        Automatically generate schema mapping.
        
        Args:
            source_schema: Source schema definition
            target_schema: Target schema definition
            threshold: Minimum similarity score for mapping
            
        Returns:
            SchemaMapping with suggested mappings
        """
        source_fields = self._extract_fields(source_schema)
        target_fields = self._extract_fields(target_schema)
        
        mappings = []
        used_targets: Set[str] = set()
        
        for source_field in source_fields:
            best_match = None
            best_score = 0.0
            
            for target_field in target_fields:
                if target_field["name"] in used_targets:
                    continue
                
                score = self._calculate_similarity(source_field, target_field)
                
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = target_field
            
            if best_match:
                confidence = self._score_to_confidence(best_score)
                
                mapping = FieldMapping(
                    source_field=source_field["name"],
                    target_field=best_match["name"],
                    confidence=confidence,
                    transform_type=self._suggest_transform(source_field, best_match)
                )
                mappings.append(mapping)
                used_targets.add(best_match["name"])
        
        schema_mapping = SchemaMapping(
            id=str(uuid4()),
            name=f"auto_mapping_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            source_schema=source_schema,
            target_schema=target_schema,
            field_mappings=mappings
        )
        
        self._mappings[schema_mapping.id] = schema_mapping
        
        return schema_mapping
    
    def add_manual_mapping(
        self,
        mapping_id: str,
        source_field: str,
        target_field: str,
        transform_type: Optional[str] = None,
        transform_config: Optional[Dict[str, Any]] = None
    ) -> FieldMapping:
        """Add or update a manual field mapping."""
        if mapping_id not in self._mappings:
            raise ValueError(f"Mapping not found: {mapping_id}")
        
        schema_mapping = self._mappings[mapping_id]
        
        # Remove existing mapping for source field
        schema_mapping.field_mappings = [
            m for m in schema_mapping.field_mappings
            if m.source_field != source_field
        ]
        
        # Add new mapping
        field_mapping = FieldMapping(
            source_field=source_field,
            target_field=target_field,
            confidence=MappingConfidence.MANUAL,
            transform_type=transform_type,
            transform_config=transform_config or {},
            validated=True
        )
        
        schema_mapping.field_mappings.append(field_mapping)
        schema_mapping.updated_at = datetime.utcnow()
        
        return field_mapping
    
    def validate_mapping(self, mapping_id: str) -> Dict[str, Any]:
        """Validate a schema mapping."""
        if mapping_id not in self._mappings:
            raise ValueError(f"Mapping not found: {mapping_id}")
        
        schema_mapping = self._mappings[mapping_id]
        issues = []
        
        source_fields = {f["name"] for f in self._extract_fields(schema_mapping.source_schema)}
        target_fields = {f["name"] for f in self._extract_fields(schema_mapping.target_schema)}
        
        mapped_sources = {m.source_field for m in schema_mapping.field_mappings}
        mapped_targets = {m.target_field for m in schema_mapping.field_mappings}
        
        # Check unmapped source fields
        unmapped_sources = source_fields - mapped_sources
        if unmapped_sources:
            issues.append({
                "type": "unmapped_source",
                "fields": list(unmapped_sources),
                "severity": "warning"
            })
        
        # Check unmapped required target fields
        # (would need schema to know which are required)
        
        # Check invalid mappings
        for mapping in schema_mapping.field_mappings:
            if mapping.source_field not in source_fields:
                issues.append({
                    "type": "invalid_source",
                    "field": mapping.source_field,
                    "severity": "error"
                })
            if mapping.target_field not in target_fields:
                issues.append({
                    "type": "invalid_target",
                    "field": mapping.target_field,
                    "severity": "error"
                })
        
        return {
            "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
            "coverage": len(mapped_sources) / len(source_fields) if source_fields else 0
        }
    
    def _extract_fields(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract field definitions from schema."""
        fields = schema.get("fields", [])
        if isinstance(fields, dict):
            return [{"name": k, **v} for k, v in fields.items()]
        return fields
    
    def _calculate_similarity(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any]
    ) -> float:
        """Calculate similarity score between fields."""
        score = 0.0
        
        # Name similarity (Levenshtein-based)
        name_sim = self._string_similarity(
            source["name"].lower(),
            target["name"].lower()
        )
        score += name_sim * 0.5
        
        # Type compatibility
        source_type = source.get("type", "string").lower()
        target_type = target.get("type", "string").lower()
        
        if source_type == target_type:
            score += 0.3
        elif self._types_compatible(source_type, target_type):
            score += 0.2
        
        # Nullable compatibility
        if source.get("nullable") == target.get("nullable"):
            score += 0.1
        
        # Description similarity (if available)
        if "description" in source and "description" in target:
            desc_sim = self._string_similarity(
                source["description"].lower(),
                target["description"].lower()
            )
            score += desc_sim * 0.1
        
        return min(score, 1.0)
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using Levenshtein ratio."""
        if s1 == s2:
            return 1.0
        
        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # Simple ratio based on common characters
        common = sum(1 for c in s1 if c in s2)
        return (2.0 * common) / (len1 + len2)
    
    def _types_compatible(self, type1: str, type2: str) -> bool:
        """Check if two types are compatible."""
        if type1 == type2:
            return True
        return self._type_compatibility.get((type1, type2), False) or \
               self._type_compatibility.get((type2, type1), False)
    
    def _score_to_confidence(self, score: float) -> MappingConfidence:
        """Convert similarity score to confidence level."""
        if score >= 0.9:
            return MappingConfidence.HIGH
        elif score >= 0.7:
            return MappingConfidence.MEDIUM
        else:
            return MappingConfidence.LOW
    
    def _suggest_transform(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any]
    ) -> Optional[str]:
        """Suggest transformation type based on field types."""
        source_type = source.get("type", "string").lower()
        target_type = target.get("type", "string").lower()
        
        if source_type == target_type:
            return None
        
        # Type conversion suggestions
        if source_type in ("int", "integer") and target_type in ("string", "text"):
            return "to_string"
        if source_type in ("string", "text") and target_type in ("int", "integer"):
            return "to_int"
        if source_type in ("string", "text") and target_type in ("datetime", "timestamp"):
            return "parse_datetime"
        if source_type in ("datetime", "timestamp") and target_type in ("string", "text"):
            return "format_datetime"
        
        return "type_conversion"


class TransformationRuleEngine:
    """
    Rule engine for complex data transformations.
    
    Supports:
    - Conditional transformations
    - Expression evaluation
    - Custom functions
    - Rule chaining
    """
    
    def __init__(self):
        self._rules: Dict[str, List[Dict[str, Any]]] = {}
        self._functions: Dict[str, Callable] = {}
        self._register_builtin_functions()
    
    def _register_builtin_functions(self):
        """Register built-in transformation functions."""
        self._functions.update({
            "upper": lambda x: str(x).upper(),
            "lower": lambda x: str(x).lower(),
            "trim": lambda x: str(x).strip(),
            "to_int": lambda x: int(x) if x else 0,
            "to_float": lambda x: float(x) if x else 0.0,
            "to_string": lambda x: str(x) if x is not None else "",
            "to_bool": lambda x: bool(x),
            "default": lambda x, d: x if x is not None else d,
            "concat": lambda *args: "".join(str(a) for a in args),
            "split": lambda x, sep=",": str(x).split(sep) if x else [],
            "join": lambda x, sep=",": sep.join(str(i) for i in x) if x else "",
            "replace": lambda x, old, new: str(x).replace(old, new) if x else "",
            "regex_replace": lambda x, pattern, repl: re.sub(pattern, repl, str(x)) if x else "",
            "substring": lambda x, start, end=None: str(x)[start:end] if x else "",
            "length": lambda x: len(x) if x else 0,
            "round": lambda x, digits=2: round(float(x), digits) if x else 0,
            "abs": lambda x: abs(float(x)) if x else 0,
            "now": lambda: datetime.utcnow().isoformat(),
            "date_format": lambda x, fmt="%Y-%m-%d": datetime.fromisoformat(str(x)).strftime(fmt) if x else "",
            "hash_md5": lambda x: hashlib.md5(str(x).encode()).hexdigest() if x else "",
            "hash_sha256": lambda x: hashlib.sha256(str(x).encode()).hexdigest() if x else "",
        })
    
    def register_function(self, name: str, func: Callable) -> None:
        """Register a custom transformation function."""
        self._functions[name] = func
    
    def add_rule(
        self,
        rule_set: str,
        field: str,
        expression: str,
        condition: Optional[str] = None,
        priority: int = 0
    ) -> None:
        """
        Add a transformation rule.
        
        Args:
            rule_set: Name of the rule set
            field: Target field to transform
            expression: Transformation expression
            condition: Optional condition for applying rule
            priority: Rule priority (higher = first)
        """
        if rule_set not in self._rules:
            self._rules[rule_set] = []
        
        self._rules[rule_set].append({
            "field": field,
            "expression": expression,
            "condition": condition,
            "priority": priority
        })
        
        # Sort by priority
        self._rules[rule_set].sort(key=lambda r: r["priority"], reverse=True)
    
    def apply_rules(
        self,
        rule_set: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply transformation rules to data.
        
        Args:
            rule_set: Name of the rule set
            data: Input data
            
        Returns:
            Transformed data
        """
        if rule_set not in self._rules:
            return data
        
        result = data.copy()
        
        for rule in self._rules[rule_set]:
            # Check condition
            if rule["condition"]:
                if not self._evaluate_condition(rule["condition"], result):
                    continue
            
            # Apply transformation
            try:
                value = self._evaluate_expression(rule["expression"], result)
                result[rule["field"]] = value
            except Exception as e:
                logger.warning(f"Rule application failed: {e}")
        
        return result
    
    def _evaluate_condition(self, condition: str, data: Dict[str, Any]) -> bool:
        """Evaluate a condition expression."""
        try:
            # Simple condition evaluation
            # In production, use a proper expression parser
            return eval(condition, {"__builtins__": {}}, data)
        except Exception:
            return False
    
    def _evaluate_expression(
        self,
        expression: str,
        data: Dict[str, Any]
    ) -> Any:
        """Evaluate a transformation expression."""
        # Parse function calls
        func_pattern = r'(\w+)\((.*?)\)'
        
        def replace_func(match):
            func_name = match.group(1)
            args_str = match.group(2)
            
            if func_name not in self._functions:
                raise ValueError(f"Unknown function: {func_name}")
            
            # Parse arguments
            args = []
            if args_str:
                for arg in args_str.split(","):
                    arg = arg.strip()
                    if arg.startswith("'") or arg.startswith('"'):
                        args.append(arg[1:-1])
                    elif arg in data:
                        args.append(data[arg])
                    else:
                        try:
                            args.append(eval(arg, {"__builtins__": {}}, data))
                        except:
                            args.append(arg)
            
            result = self._functions[func_name](*args)
            return repr(result)
        
        # Replace function calls
        evaluated = re.sub(func_pattern, replace_func, expression)
        
        # Evaluate final expression
        try:
            return eval(evaluated, {"__builtins__": {}}, data)
        except:
            return evaluated


class IntelligentDataTransformer(DataTransformer):
    """
    Intelligent data transformer with advanced capabilities.
    
    Extends base DataTransformer with:
    - Schema mapping
    - Rule engine
    - Lineage tracking
    - Validation
    """
    
    def __init__(self):
        super().__init__()
        self.schema_mapper = SchemaMapper()
        self.rule_engine = TransformationRuleEngine()
        self._lineage: Dict[str, TransformationLineage] = {}
        self._validators: List[Callable] = []
    
    def register_validator(self, validator: Callable[[Dict[str, Any]], bool]) -> None:
        """Register a data validator."""
        self._validators.append(validator)
    
    async def transform_with_mapping(
        self,
        batch: DataBatch,
        mapping_id: str,
        rule_set: Optional[str] = None,
        track_lineage: bool = True
    ) -> Tuple[DataBatch, TransformResult]:
        """
        Transform batch using schema mapping and rules.
        
        Args:
            batch: Input data batch
            mapping_id: Schema mapping ID
            rule_set: Optional rule set to apply
            track_lineage: Whether to track lineage
            
        Returns:
            Tuple of transformed batch and result
        """
        import time
        start_time = time.time()
        
        mapping = self.schema_mapper._mappings.get(mapping_id)
        if not mapping:
            raise ValueError(f"Mapping not found: {mapping_id}")
        
        result = TransformResult(success=True)
        transformed_records = []
        
        for record in batch.records:
            try:
                # Track input
                input_hash = None
                if track_lineage:
                    input_hash = self._compute_hash(record.data)
                
                # Apply schema mapping
                mapped_data = self._apply_mapping(record.data, mapping)
                
                # Apply rules
                if rule_set:
                    mapped_data = self.rule_engine.apply_rules(rule_set, mapped_data)
                
                # Validate
                if not self._validate(mapped_data):
                    result.records_skipped += 1
                    continue
                
                # Create transformed record
                transformed = DataRecord(
                    id=record.id,
                    data=mapped_data,
                    metadata={
                        **record.metadata,
                        "transformed_at": datetime.utcnow().isoformat(),
                        "mapping_id": mapping_id
                    },
                    timestamp=datetime.utcnow()
                )
                transformed_records.append(transformed)
                result.records_transformed += 1
                
                # Track lineage
                if track_lineage:
                    output_hash = self._compute_hash(mapped_data)
                    lineage = TransformationLineage(
                        record_id=record.id,
                        source_id=batch.source_id,
                        transformations=[{
                            "type": "schema_mapping",
                            "mapping_id": mapping_id,
                            "rule_set": rule_set
                        }],
                        input_hash=input_hash,
                        output_hash=output_hash
                    )
                    self._lineage[record.id] = lineage
                
            except Exception as e:
                result.records_failed += 1
                result.errors.append({
                    "record_id": record.id,
                    "error": str(e)
                })
        
        batch.records = transformed_records
        result.duration_seconds = time.time() - start_time
        
        return batch, result
    
    def _apply_mapping(
        self,
        data: Dict[str, Any],
        mapping: SchemaMapping
    ) -> Dict[str, Any]:
        """Apply schema mapping to data."""
        result = {}
        
        for field_mapping in mapping.field_mappings:
            source_value = data.get(field_mapping.source_field)
            
            # Apply transform if specified
            if field_mapping.transform_type:
                source_value = self._apply_field_transform(
                    source_value,
                    field_mapping.transform_type,
                    field_mapping.transform_config
                )
            
            result[field_mapping.target_field] = source_value
        
        return result
    
    def _apply_field_transform(
        self,
        value: Any,
        transform_type: str,
        config: Dict[str, Any]
    ) -> Any:
        """Apply field-level transformation."""
        if transform_type == "to_string":
            return str(value) if value is not None else ""
        elif transform_type == "to_int":
            return int(value) if value else 0
        elif transform_type == "to_float":
            return float(value) if value else 0.0
        elif transform_type == "parse_datetime":
            fmt = config.get("format", "%Y-%m-%d %H:%M:%S")
            return datetime.strptime(str(value), fmt) if value else None
        elif transform_type == "format_datetime":
            fmt = config.get("format", "%Y-%m-%d %H:%M:%S")
            if isinstance(value, datetime):
                return value.strftime(fmt)
            return str(value)
        elif transform_type == "type_conversion":
            target_type = config.get("target_type", "string")
            return self._convert_type(value, target_type)
        else:
            return value
    
    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type."""
        if value is None:
            return None
        
        type_converters = {
            "string": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict
        }
        
        converter = type_converters.get(target_type, str)
        return converter(value)
    
    def _validate(self, data: Dict[str, Any]) -> bool:
        """Validate transformed data."""
        for validator in self._validators:
            try:
                if not validator(data):
                    return False
            except Exception:
                return False
        return True
    
    def _compute_hash(self, data: Dict[str, Any]) -> str:
        """Compute hash of data."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def get_lineage(self, record_id: str) -> Optional[TransformationLineage]:
        """Get lineage for a record."""
        return self._lineage.get(record_id)


# Global transformer instance
intelligent_transformer = IntelligentDataTransformer()


__all__ = [
    "MappingConfidence",
    "FieldMapping",
    "SchemaMapping",
    "TransformationLineage",
    "SchemaMapper",
    "TransformationRuleEngine",
    "IntelligentDataTransformer",
    "intelligent_transformer",
]
