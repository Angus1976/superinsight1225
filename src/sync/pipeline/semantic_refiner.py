"""
Semantic Refiner for Data Sync Pipeline.

Uses LLM to analyze data business meaning and generate semantic enhancements.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional
import logging

from src.sync.pipeline.schemas import (
    RefineConfig,
    RefineRule,
    RefinementResult,
    DataDictionary,
    FieldDefinition,
    Entity,
    Relation,
)

logger = logging.getLogger(__name__)


class SemanticRefiner:
    """
    Semantic Refiner for AI-powered data enhancement.
    
    Features:
    - Field description generation
    - Data dictionary creation
    - Entity and relation extraction
    - Result caching
    - Custom refinement rules
    """
    
    def __init__(self, llm_service=None, cache=None):
        """
        Initialize the Semantic Refiner.
        
        Args:
            llm_service: LLM service for semantic analysis
            cache: Redis cache for caching results
        """
        self.llm = llm_service
        self.cache = cache
        self._memory_cache: Dict[str, RefinementResult] = {}
    
    async def refine(
        self,
        data: List[Dict[str, Any]],
        config: RefineConfig
    ) -> RefinementResult:
        """
        Execute semantic refinement on data.
        
        Args:
            data: Data to refine
            config: Refinement configuration
            
        Returns:
            RefinementResult with semantic enhancements
        """
        # Check cache
        cache_key = self.generate_cache_key(data, config)
        cached = await self._get_from_cache(cache_key)
        if cached:
            logger.info(f"Cache hit for refinement: {cache_key[:16]}...")
            return cached
        
        # Execute refinement
        result = await self._do_refine(data, config)
        
        # Cache result
        await self._save_to_cache(cache_key, result, config.cache_ttl)
        
        return result
    
    async def _do_refine(
        self,
        data: List[Dict[str, Any]],
        config: RefineConfig
    ) -> RefinementResult:
        """
        Perform the actual refinement.
        
        Args:
            data: Data to refine
            config: Refinement configuration
            
        Returns:
            RefinementResult
        """
        field_descriptions = {}
        data_dictionary = None
        entities = []
        relations = []
        enhanced_description = ""
        
        if not data:
            return RefinementResult(
                field_descriptions={},
                data_dictionary=None,
                entities=[],
                relations=[],
                enhanced_description="No data to refine"
            )
        
        # Generate field descriptions
        if config.generate_descriptions:
            field_descriptions = await self.generate_field_descriptions(data)
        
        # Generate data dictionary
        if config.generate_dictionary:
            data_dictionary = await self.generate_data_dictionary(data)
        
        # Extract entities
        if config.extract_entities:
            entities = await self.extract_entities(data)
        
        # Extract relations
        if config.extract_relations and entities:
            relations = await self.extract_relations(entities)
        
        # Apply custom rules
        if config.custom_rules:
            data = await self.apply_custom_rules(data, config.custom_rules)
        
        # Generate enhanced description
        enhanced_description = self._generate_enhanced_description(
            data, field_descriptions, entities
        )
        
        return RefinementResult(
            field_descriptions=field_descriptions,
            data_dictionary=data_dictionary,
            entities=entities,
            relations=relations,
            enhanced_description=enhanced_description
        )
    
    async def generate_field_descriptions(
        self,
        data: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generate descriptions for each field.
        
        Args:
            data: Data to analyze
            
        Returns:
            Dictionary mapping field names to descriptions
        """
        if not data:
            return {}
        
        # Get field names from first record
        sample = data[0]
        descriptions = {}
        
        for field_name, value in sample.items():
            # Analyze field based on name and sample values
            description = self._infer_field_description(
                field_name,
                [record.get(field_name) for record in data[:10]]
            )
            descriptions[field_name] = description
        
        # If LLM is available, enhance descriptions
        if self.llm:
            descriptions = await self._enhance_descriptions_with_llm(
                descriptions, data[:5]
            )
        
        return descriptions
    
    async def generate_data_dictionary(
        self,
        data: List[Dict[str, Any]]
    ) -> DataDictionary:
        """
        Generate a data dictionary.
        
        Args:
            data: Data to analyze
            
        Returns:
            DataDictionary with field definitions
        """
        if not data:
            return DataDictionary(
                fields=[],
                table_description="Empty dataset",
                business_context="No data available"
            )
        
        sample = data[0]
        fields = []
        
        for field_name in sample.keys():
            values = [record.get(field_name) for record in data[:100]]
            
            field_def = FieldDefinition(
                name=field_name,
                data_type=self._infer_data_type(values),
                description=self._infer_field_description(field_name, values),
                sample_values=values[:5],
                nullable=any(v is None for v in values),
                business_meaning=self._infer_business_meaning(field_name)
            )
            fields.append(field_def)
        
        return DataDictionary(
            fields=fields,
            table_description=self._generate_table_description(fields),
            business_context=self._infer_business_context(fields)
        )
    
    async def extract_entities(
        self,
        data: List[Dict[str, Any]]
    ) -> List[Entity]:
        """
        Extract entities from data.
        
        Args:
            data: Data to analyze
            
        Returns:
            List of extracted entities
        """
        if not data:
            return []
        
        entities = []
        sample = data[0]
        
        for field_name, value in sample.items():
            entity_type = self._infer_entity_type(field_name, value)
            if entity_type:
                entities.append(Entity(
                    name=field_name,
                    type=entity_type,
                    source_field=field_name,
                    confidence=0.8
                ))
        
        return entities
    
    async def extract_relations(
        self,
        entities: List[Entity]
    ) -> List[Relation]:
        """
        Extract relations between entities.
        
        Args:
            entities: List of entities
            
        Returns:
            List of relations
        """
        relations = []
        
        # Simple heuristic: look for ID fields that might reference other entities
        id_entities = [e for e in entities if e.type == "identifier"]
        other_entities = [e for e in entities if e.type != "identifier"]
        
        for id_entity in id_entities:
            for other in other_entities:
                # Check if ID field name suggests a relation
                if other.name.lower() in id_entity.name.lower():
                    relations.append(Relation(
                        source_entity=id_entity.name,
                        target_entity=other.name,
                        relation_type="references",
                        confidence=0.6
                    ))
        
        return relations
    
    async def apply_custom_rules(
        self,
        data: List[Dict[str, Any]],
        rules: List[RefineRule]
    ) -> List[Dict[str, Any]]:
        """
        Apply custom refinement rules to data.
        
        Args:
            data: Data to transform
            rules: List of custom rules
            
        Returns:
            Transformed data
        """
        import re
        
        for rule in rules:
            pattern = re.compile(rule.field_pattern)
            
            for record in data:
                for field_name in list(record.keys()):
                    if pattern.match(field_name):
                        # Apply transformation
                        record[field_name] = self._apply_transformation(
                            record[field_name],
                            rule.transformation,
                            rule.parameters
                        )
        
        return data
    
    def generate_cache_key(
        self,
        data: List[Dict[str, Any]],
        config: RefineConfig
    ) -> str:
        """
        Generate a cache key for the refinement request.
        
        Args:
            data: Data being refined
            config: Refinement configuration
            
        Returns:
            Cache key string
        """
        # Create a hash of data structure and config
        data_hash = hashlib.sha256(
            json.dumps(data[:10], sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        
        config_hash = hashlib.sha256(
            config.model_dump_json().encode()
        ).hexdigest()[:16]
        
        return f"refine:{data_hash}:{config_hash}"
    
    async def _get_from_cache(self, key: str) -> Optional[RefinementResult]:
        """Get result from cache."""
        if self.cache:
            cached = await self.cache.get(key)
            if cached:
                return RefinementResult.model_validate_json(cached)
        
        return self._memory_cache.get(key)
    
    async def _save_to_cache(
        self,
        key: str,
        result: RefinementResult,
        ttl: int
    ) -> None:
        """Save result to cache."""
        if self.cache:
            await self.cache.setex(key, ttl, result.model_dump_json())
        else:
            self._memory_cache[key] = result
    
    def _infer_field_description(
        self,
        field_name: str,
        values: List[Any]
    ) -> str:
        """Infer a description for a field based on name and values."""
        name_lower = field_name.lower()
        
        # Common field patterns
        if 'id' in name_lower:
            return f"Unique identifier for {field_name.replace('_id', '').replace('id', 'record')}"
        elif 'name' in name_lower:
            return f"Name or title field"
        elif 'date' in name_lower or 'time' in name_lower:
            return f"Date/time field for {field_name.replace('_', ' ')}"
        elif 'email' in name_lower:
            return "Email address"
        elif 'phone' in name_lower:
            return "Phone number"
        elif 'address' in name_lower:
            return "Physical or mailing address"
        elif 'price' in name_lower or 'amount' in name_lower or 'cost' in name_lower:
            return "Monetary value"
        elif 'count' in name_lower or 'quantity' in name_lower:
            return "Numeric count or quantity"
        elif 'status' in name_lower:
            return "Status indicator"
        elif 'type' in name_lower:
            return "Type or category classification"
        else:
            return f"Field containing {field_name.replace('_', ' ')} data"
    
    def _infer_data_type(self, values: List[Any]) -> str:
        """Infer the data type from sample values."""
        non_null = [v for v in values if v is not None]
        if not non_null:
            return "unknown"
        
        sample = non_null[0]
        if isinstance(sample, bool):
            return "boolean"
        elif isinstance(sample, int):
            return "integer"
        elif isinstance(sample, float):
            return "float"
        elif isinstance(sample, str):
            # Check for date patterns
            if any(c in sample for c in ['-', '/', ':']):
                return "datetime"
            return "string"
        elif isinstance(sample, list):
            return "array"
        elif isinstance(sample, dict):
            return "object"
        else:
            return "unknown"
    
    def _infer_business_meaning(self, field_name: str) -> str:
        """Infer business meaning from field name."""
        name_lower = field_name.lower()
        
        if 'customer' in name_lower or 'user' in name_lower:
            return "Customer/User related data"
        elif 'order' in name_lower:
            return "Order/Transaction related data"
        elif 'product' in name_lower:
            return "Product/Item related data"
        elif 'payment' in name_lower:
            return "Payment/Financial data"
        else:
            return "General business data"
    
    def _infer_entity_type(self, field_name: str, value: Any) -> Optional[str]:
        """Infer entity type from field name and value."""
        name_lower = field_name.lower()
        
        if 'id' in name_lower:
            return "identifier"
        elif 'name' in name_lower:
            return "name"
        elif 'email' in name_lower:
            return "email"
        elif 'date' in name_lower or 'time' in name_lower:
            return "datetime"
        elif isinstance(value, (int, float)):
            return "numeric"
        elif isinstance(value, str):
            return "text"
        
        return None
    
    def _generate_table_description(self, fields: List[FieldDefinition]) -> str:
        """Generate a description for the table."""
        field_names = [f.name for f in fields]
        return f"Table with {len(fields)} fields: {', '.join(field_names[:5])}{'...' if len(fields) > 5 else ''}"
    
    def _infer_business_context(self, fields: List[FieldDefinition]) -> str:
        """Infer business context from fields."""
        field_names = [f.name.lower() for f in fields]
        
        if any('customer' in n or 'user' in n for n in field_names):
            return "Customer/User management domain"
        elif any('order' in n or 'transaction' in n for n in field_names):
            return "Order/Transaction processing domain"
        elif any('product' in n or 'item' in n for n in field_names):
            return "Product/Inventory management domain"
        else:
            return "General business domain"
    
    def _generate_enhanced_description(
        self,
        data: List[Dict],
        field_descriptions: Dict[str, str],
        entities: List[Entity]
    ) -> str:
        """Generate an enhanced description of the data."""
        parts = [
            f"Dataset contains {len(data)} records",
            f"with {len(field_descriptions)} fields"
        ]
        
        if entities:
            entity_types = set(e.type for e in entities)
            parts.append(f"including {len(entities)} identified entities of types: {', '.join(entity_types)}")
        
        return ". ".join(parts) + "."
    
    def _apply_transformation(
        self,
        value: Any,
        transformation: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """Apply a transformation to a value."""
        if transformation == "uppercase":
            return str(value).upper() if value else value
        elif transformation == "lowercase":
            return str(value).lower() if value else value
        elif transformation == "trim":
            return str(value).strip() if value else value
        elif transformation == "prefix":
            prefix = parameters.get("prefix", "")
            return f"{prefix}{value}" if value else value
        elif transformation == "suffix":
            suffix = parameters.get("suffix", "")
            return f"{value}{suffix}" if value else value
        else:
            return value
    
    async def _enhance_descriptions_with_llm(
        self,
        descriptions: Dict[str, str],
        sample_data: List[Dict]
    ) -> Dict[str, str]:
        """Enhance descriptions using LLM."""
        # This would call the LLM service to improve descriptions
        # For now, return as-is
        return descriptions
    
    def clear_cache(self) -> None:
        """Clear the memory cache."""
        self._memory_cache.clear()
