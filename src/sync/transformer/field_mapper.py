"""
Field Mapper for Bidirectional Sync.

Handles field name mapping and type conversion between source and target databases.
Validates mapping rules against schemas before execution.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class MappingRule:
    """Field mapping rule."""
    source_field: str
    target_field: str
    type_conversion: Optional[str] = None  # e.g., "string", "int", "float", "bool", "datetime"
    default_value: Any = None
    nullable: bool = True
    transform: Optional[str] = None  # e.g., "uppercase", "lowercase", "trim"


@dataclass
class MappedData:
    """Result of field mapping operation."""
    data: Dict[str, Any]
    success: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class ValidationError:
    """Mapping validation error."""
    field: str
    error_type: str
    message: str


class FieldMapper:
    """
    Field Mapper for bidirectional sync.
    
    Handles:
    - Field name mapping between source and target
    - Type conversion
    - Schema validation
    """

    TYPE_CONVERTERS = {
        "string": str,
        "str": str,
        "int": int,
        "integer": int,
        "float": float,
        "double": float,
        "bool": lambda x: bool(x) if x not in ("false", "False", "0", "", None) else False,
        "boolean": lambda x: bool(x) if x not in ("false", "False", "0", "", None) else False,
        "datetime": lambda x: x,  # Simplified for now, can be enhanced
        "date": lambda x: x,
        "json": lambda x: x if isinstance(x, (dict, list)) else __import__("json").loads(str(x)),
    }

    def apply_mapping(
        self,
        data: Dict[str, Any],
        rules: List[Union[MappingRule, Dict[str, Any]]]
    ) -> MappedData:
        """
        Apply field mapping rules to data.
        
        Args:
            data: Source data dictionary
            rules: List of mapping rules (MappingRule objects or dicts)
            
        Returns:
            MappedData with transformed data and any errors
        """
        mapped_data = {}
        errors = []
        
        # Convert dict rules to MappingRule objects
        mapping_rules = []
        for rule in rules:
            if isinstance(rule, dict):
                mapping_rules.append(MappingRule(**rule))
            else:
                mapping_rules.append(rule)
        
        for rule in mapping_rules:
            try:
                # Get source value
                if rule.source_field not in data:
                    if not rule.nullable and rule.default_value is None:
                        errors.append(
                            f"Required field '{rule.source_field}' not found in source data"
                        )
                        continue
                    value = rule.default_value
                else:
                    value = data[rule.source_field]
                
                # Handle null values
                if value is None:
                    if not rule.nullable:
                        if rule.default_value is not None:
                            value = rule.default_value
                        else:
                            errors.append(
                                f"Field '{rule.source_field}' is null but not nullable"
                            )
                            continue
                    else:
                        # Nullable field with None value
                        mapped_data[rule.target_field] = None
                        continue
                
                # Apply type conversion
                if rule.type_conversion:
                    value = self._convert_type(value, rule.type_conversion)
                
                # Apply transformation
                if rule.transform:
                    value = self._apply_transform(value, rule.transform)
                
                mapped_data[rule.target_field] = value
                
            except Exception as e:
                errors.append(
                    f"Error mapping field '{rule.source_field}' to '{rule.target_field}': {str(e)}"
                )
                logger.warning(
                    f"Field mapping error: {rule.source_field} -> {rule.target_field}: {e}"
                )
        
        return MappedData(
            data=mapped_data,
            success=len(errors) == 0,
            errors=errors
        )
    
    def validate_mapping(
        self,
        source_schema: Dict[str, Any],
        target_schema: Dict[str, Any],
        rules: List[Union[MappingRule, Dict[str, Any]]]
    ) -> List[ValidationError]:
        """
        Validate mapping rules against source and target schemas.
        
        Args:
            source_schema: Source schema definition (field_name -> type_info)
            target_schema: Target schema definition (field_name -> type_info)
            rules: List of mapping rules to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Convert dict rules to MappingRule objects
        mapping_rules = []
        for rule in rules:
            if isinstance(rule, dict):
                mapping_rules.append(MappingRule(**rule))
            else:
                mapping_rules.append(rule)
        
        # Track which target fields are mapped
        mapped_target_fields = set()
        
        for rule in mapping_rules:
            # Validate source field exists
            if rule.source_field not in source_schema:
                errors.append(ValidationError(
                    field=rule.source_field,
                    error_type="missing_source_field",
                    message=f"Source field '{rule.source_field}' not found in source schema"
                ))
                continue
            
            # Validate target field exists
            if rule.target_field not in target_schema:
                errors.append(ValidationError(
                    field=rule.target_field,
                    error_type="missing_target_field",
                    message=f"Target field '{rule.target_field}' not found in target schema"
                ))
                continue
            
            # Check for duplicate target mappings
            if rule.target_field in mapped_target_fields:
                errors.append(ValidationError(
                    field=rule.target_field,
                    error_type="duplicate_target_mapping",
                    message=f"Target field '{rule.target_field}' is mapped multiple times"
                ))
            mapped_target_fields.add(rule.target_field)
            
            # Validate type compatibility
            source_type = self._normalize_type(source_schema[rule.source_field])
            target_type = self._normalize_type(target_schema[rule.target_field])
            
            if rule.type_conversion:
                # Check if conversion is supported
                if rule.type_conversion not in self.TYPE_CONVERTERS:
                    errors.append(ValidationError(
                        field=rule.source_field,
                        error_type="unsupported_conversion",
                        message=f"Unsupported type conversion: '{rule.type_conversion}'"
                    ))
                else:
                    # Validate conversion target matches target schema
                    converted_type = self._normalize_type(rule.type_conversion)
                    if not self._types_compatible(converted_type, target_type):
                        errors.append(ValidationError(
                            field=rule.target_field,
                            error_type="type_mismatch",
                            message=(
                                f"Converted type '{converted_type}' incompatible with "
                                f"target type '{target_type}'"
                            )
                        ))
            else:
                # No conversion - check direct compatibility
                if not self._types_compatible(source_type, target_type):
                    errors.append(ValidationError(
                        field=rule.target_field,
                        error_type="type_mismatch",
                        message=(
                            f"Source type '{source_type}' incompatible with "
                            f"target type '{target_type}' (no conversion specified)"
                        )
                    ))
            
            # Validate nullable constraints
            source_nullable = self._is_nullable(source_schema[rule.source_field])
            target_nullable = self._is_nullable(target_schema[rule.target_field])
            
            if source_nullable and not target_nullable and not rule.default_value:
                errors.append(ValidationError(
                    field=rule.target_field,
                    error_type="nullable_mismatch",
                    message=(
                        f"Source field '{rule.source_field}' is nullable but "
                        f"target field '{rule.target_field}' is not (no default value provided)"
                    )
                ))
        
        return errors
    
    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type."""
        if value is None:
            return None
        
        converter = self.TYPE_CONVERTERS.get(target_type.lower())
        if not converter:
            raise ValueError(f"Unsupported type conversion: {target_type}")
        
        try:
            return converter(value)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Failed to convert value '{value}' to type '{target_type}': {e}"
            )
    
    def _apply_transform(self, value: Any, transform: str) -> Any:
        """Apply transformation to value."""
        if value is None:
            return None
        
        str_value = str(value)
        
        if transform == "uppercase":
            return str_value.upper()
        elif transform == "lowercase":
            return str_value.lower()
        elif transform == "trim":
            return str_value.strip()
        elif transform == "titlecase":
            return str_value.title()
        else:
            logger.warning(f"Unknown transform: {transform}")
            return value
    
    def _normalize_type(self, type_info: Any) -> str:
        """Normalize type information to standard type name."""
        if isinstance(type_info, dict):
            type_name = type_info.get("type", "string")
        else:
            type_name = str(type_info)
        
        # Normalize common type names
        type_name = type_name.lower()
        type_map = {
            "varchar": "string",
            "char": "string",
            "text": "string",
            "integer": "int",
            "bigint": "int",
            "smallint": "int",
            "double": "float",
            "decimal": "float",
            "numeric": "float",
            "boolean": "bool",
            "timestamp": "datetime",
            "timestamptz": "datetime",
        }
        
        return type_map.get(type_name, type_name)
    
    def _types_compatible(self, source_type: str, target_type: str) -> bool:
        """Check if source and target types are compatible."""
        # Exact match
        if source_type == target_type:
            return True
        
        # Compatible type groups
        numeric_types = {"int", "float", "double", "decimal", "numeric"}
        string_types = {"string", "str", "text", "varchar", "char"}
        bool_types = {"bool", "boolean"}
        datetime_types = {"datetime", "timestamp", "date"}
        
        if source_type in numeric_types and target_type in numeric_types:
            return True
        if source_type in string_types and target_type in string_types:
            return True
        if source_type in bool_types and target_type in bool_types:
            return True
        if source_type in datetime_types and target_type in datetime_types:
            return True
        
        # String can accept most types (implicit conversion)
        if target_type in string_types:
            return True
        
        return False
    
    def _is_nullable(self, field_info: Any) -> bool:
        """Check if field is nullable."""
        if isinstance(field_info, dict):
            return field_info.get("nullable", True)
        return True


# Global field mapper instance
field_mapper = FieldMapper()
