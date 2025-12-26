"""
Data models for Knowledge Graph module.

Defines entities, relations, and graph schema structures.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Set
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator


class EntityType(str, Enum):
    """Entity types in the knowledge graph."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    TIME = "time"
    MONEY = "money"
    PERCENT = "percent"
    PRODUCT = "product"
    EVENT = "event"
    CONCEPT = "concept"
    DOCUMENT = "document"
    TASK = "task"
    ANNOTATION = "annotation"
    LABEL = "label"
    USER = "user"
    PROJECT = "project"
    CUSTOM = "custom"


class RelationType(str, Enum):
    """Relation types in the knowledge graph."""
    # General relations
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    HAS_PART = "has_part"
    INSTANCE_OF = "instance_of"
    SUBCLASS_OF = "subclass_of"

    # Temporal relations
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"

    # Spatial relations
    LOCATED_IN = "located_in"
    NEAR = "near"

    # Social relations
    WORKS_FOR = "works_for"
    KNOWS = "knows"
    COLLABORATES_WITH = "collaborates_with"

    # Action relations
    CREATED_BY = "created_by"
    MODIFIED_BY = "modified_by"
    ANNOTATED_BY = "annotated_by"
    REVIEWED_BY = "reviewed_by"
    ASSIGNED_TO = "assigned_to"

    # Data relations
    REFERENCES = "references"
    DERIVED_FROM = "derived_from"
    SIMILAR_TO = "similar_to"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"

    # Domain-specific
    BELONGS_TO_PROJECT = "belongs_to_project"
    HAS_LABEL = "has_label"
    HAS_ANNOTATION = "has_annotation"

    # Custom
    CUSTOM = "custom"


class Entity(BaseModel):
    """Entity node in the knowledge graph."""

    id: UUID = Field(default_factory=uuid4, description="Entity unique ID")
    entity_type: EntityType = Field(..., description="Entity type")
    name: str = Field(..., min_length=1, description="Entity name")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity properties")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    description: Optional[str] = Field(None, description="Entity description")

    # Provenance
    source: Optional[str] = Field(None, description="Source of this entity")
    source_id: Optional[str] = Field(None, description="ID in source system")

    # Quality metrics
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    verified: bool = Field(default=False, description="Whether manually verified")

    # Multi-tenancy
    tenant_id: Optional[str] = Field(None, description="Tenant ID")

    # Audit
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Update time")
    created_by: Optional[str] = Field(None, description="Creator ID")
    updated_by: Optional[str] = Field(None, description="Updater ID")
    version: int = Field(default=1, ge=1, description="Version number")
    is_active: bool = Field(default=True, description="Whether entity is active")

    def update(self, **kwargs) -> None:
        """Update entity fields."""
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ('id', 'created_at', 'created_by'):
                setattr(self, key, value)
        self.updated_at = datetime.now()
        self.version += 1

    def add_alias(self, alias: str) -> None:
        """Add an alias if not exists."""
        if alias and alias not in self.aliases:
            self.aliases.append(alias)
            self.updated_at = datetime.now()

    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j compatible properties."""
        props = {
            "id": str(self.id),
            "entity_type": self.entity_type.value,
            "name": self.name,
            "confidence": self.confidence,
            "verified": self.verified,
            "is_active": self.is_active,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if self.description:
            props["description"] = self.description
        if self.source:
            props["source"] = self.source
        if self.source_id:
            props["source_id"] = self.source_id
        if self.tenant_id:
            props["tenant_id"] = self.tenant_id
        if self.aliases:
            props["aliases"] = self.aliases
        # Flatten properties into prefixed keys
        for key, value in self.properties.items():
            if isinstance(value, (str, int, float, bool)):
                props[f"prop_{key}"] = value
        return props


class Relation(BaseModel):
    """Relation edge in the knowledge graph."""

    id: UUID = Field(default_factory=uuid4, description="Relation unique ID")
    source_id: UUID = Field(..., description="Source entity ID")
    target_id: UUID = Field(..., description="Target entity ID")
    relation_type: RelationType = Field(..., description="Relation type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Relation properties")

    # Quality metrics
    weight: float = Field(default=1.0, ge=0.0, description="Relation weight/strength")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    verified: bool = Field(default=False, description="Whether manually verified")

    # Temporal validity
    valid_from: Optional[datetime] = Field(None, description="Valid from time")
    valid_to: Optional[datetime] = Field(None, description="Valid to time")

    # Provenance
    source: Optional[str] = Field(None, description="Source of this relation")
    evidence: Optional[str] = Field(None, description="Evidence text")

    # Multi-tenancy
    tenant_id: Optional[str] = Field(None, description="Tenant ID")

    # Audit
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Update time")
    created_by: Optional[str] = Field(None, description="Creator ID")
    version: int = Field(default=1, ge=1, description="Version number")
    is_active: bool = Field(default=True, description="Whether relation is active")

    def update(self, **kwargs) -> None:
        """Update relation fields."""
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ('id', 'source_id', 'target_id', 'created_at', 'created_by'):
                setattr(self, key, value)
        self.updated_at = datetime.now()
        self.version += 1

    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j compatible properties."""
        props = {
            "id": str(self.id),
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "confidence": self.confidence,
            "verified": self.verified,
            "is_active": self.is_active,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if self.source:
            props["source"] = self.source
        if self.evidence:
            props["evidence"] = self.evidence
        if self.tenant_id:
            props["tenant_id"] = self.tenant_id
        if self.valid_from:
            props["valid_from"] = self.valid_from.isoformat()
        if self.valid_to:
            props["valid_to"] = self.valid_to.isoformat()
        # Flatten properties
        for key, value in self.properties.items():
            if isinstance(value, (str, int, float, bool)):
                props[f"prop_{key}"] = value
        return props


class ExtractedEntity(BaseModel):
    """Entity extracted from text by NLP."""

    text: str = Field(..., description="Original text span")
    entity_type: EntityType = Field(..., description="Entity type")
    start_char: int = Field(..., ge=0, description="Start character position")
    end_char: int = Field(..., ge=0, description="End character position")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")
    normalized_name: Optional[str] = Field(None, description="Normalized entity name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('end_char')
    @classmethod
    def end_after_start(cls, v, info):
        if 'start_char' in info.data and v <= info.data['start_char']:
            raise ValueError('end_char must be greater than start_char')
        return v

    def to_entity(self, source: str = "nlp_extraction") -> Entity:
        """Convert to Entity model."""
        return Entity(
            entity_type=self.entity_type,
            name=self.normalized_name or self.text,
            properties={
                "original_text": self.text,
                "start_char": self.start_char,
                "end_char": self.end_char,
                **self.metadata
            },
            confidence=self.confidence,
            source=source,
        )


class ExtractedRelation(BaseModel):
    """Relation extracted from text by NLP."""

    source_entity: ExtractedEntity = Field(..., description="Source entity")
    target_entity: ExtractedEntity = Field(..., description="Target entity")
    relation_type: RelationType = Field(..., description="Relation type")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")
    evidence: Optional[str] = Field(None, description="Evidence text span")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def to_relation(self, source_id: UUID, target_id: UUID, source: str = "nlp_extraction") -> Relation:
        """Convert to Relation model."""
        return Relation(
            source_id=source_id,
            target_id=target_id,
            relation_type=self.relation_type,
            confidence=self.confidence,
            evidence=self.evidence,
            source=source,
            properties=self.metadata,
        )


class GraphSchema(BaseModel):
    """Schema definition for the knowledge graph."""

    name: str = Field(..., description="Schema name")
    description: Optional[str] = Field(None, description="Schema description")
    version: str = Field(default="1.0.0", description="Schema version")

    # Entity type definitions
    entity_types: List[EntityType] = Field(
        default_factory=lambda: list(EntityType),
        description="Allowed entity types"
    )

    # Relation type definitions
    relation_types: List[RelationType] = Field(
        default_factory=lambda: list(RelationType),
        description="Allowed relation types"
    )

    # Constraints
    entity_constraints: Dict[EntityType, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Constraints for entity types"
    )

    relation_constraints: Dict[RelationType, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Constraints for relation types"
    )

    # Allowed relation patterns (source_type, relation_type, target_type)
    allowed_patterns: List[tuple] = Field(
        default_factory=list,
        description="Allowed (source_type, relation_type, target_type) patterns"
    )

    def validate_entity(self, entity: Entity) -> bool:
        """Validate entity against schema."""
        if entity.entity_type not in self.entity_types:
            return False
        if entity.entity_type in self.entity_constraints:
            constraints = self.entity_constraints[entity.entity_type]
            # Check required properties
            if "required_properties" in constraints:
                for prop in constraints["required_properties"]:
                    if prop not in entity.properties:
                        return False
        return True

    def validate_relation(self, relation: Relation,
                         source_entity: Entity,
                         target_entity: Entity) -> bool:
        """Validate relation against schema."""
        if relation.relation_type not in self.relation_types:
            return False

        # Check allowed patterns
        if self.allowed_patterns:
            pattern = (source_entity.entity_type, relation.relation_type, target_entity.entity_type)
            if pattern not in self.allowed_patterns:
                return False

        return True


class GraphStatistics(BaseModel):
    """Statistics about the knowledge graph."""

    total_entities: int = Field(default=0, description="Total number of entities")
    total_relations: int = Field(default=0, description="Total number of relations")
    entities_by_type: Dict[str, int] = Field(default_factory=dict, description="Entity counts by type")
    relations_by_type: Dict[str, int] = Field(default_factory=dict, description="Relation counts by type")
    avg_degree: float = Field(default=0.0, description="Average node degree")
    density: float = Field(default=0.0, description="Graph density")
    connected_components: int = Field(default=0, description="Number of connected components")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last statistics update")


class GraphQueryResult(BaseModel):
    """Result of a graph query."""

    entities: List[Entity] = Field(default_factory=list, description="Matching entities")
    relations: List[Relation] = Field(default_factory=list, description="Matching relations")
    paths: List[List[Dict[str, Any]]] = Field(default_factory=list, description="Path results")
    total_count: int = Field(default=0, description="Total matching count")
    query: str = Field(default="", description="Original query")
    query_time_ms: float = Field(default=0.0, description="Query time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EntityCreateRequest(BaseModel):
    """Request model for creating an entity."""

    entity_type: EntityType = Field(..., description="Entity type")
    name: str = Field(..., min_length=1, description="Entity name")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity properties")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    description: Optional[str] = Field(None, description="Entity description")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    source: Optional[str] = Field(None, description="Source of this entity")


class RelationCreateRequest(BaseModel):
    """Request model for creating a relation."""

    source_id: UUID = Field(..., description="Source entity ID")
    target_id: UUID = Field(..., description="Target entity ID")
    relation_type: RelationType = Field(..., description="Relation type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Relation properties")
    weight: float = Field(default=1.0, ge=0.0, description="Relation weight")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    evidence: Optional[str] = Field(None, description="Evidence text")


class TextExtractionRequest(BaseModel):
    """Request model for extracting entities and relations from text."""

    text: str = Field(..., min_length=1, description="Text to process")
    extract_entities: bool = Field(default=True, description="Whether to extract entities")
    extract_relations: bool = Field(default=True, description="Whether to extract relations")
    entity_types: Optional[List[EntityType]] = Field(None, description="Entity types to extract")
    relation_types: Optional[List[RelationType]] = Field(None, description="Relation types to extract")
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")
    save_to_graph: bool = Field(default=False, description="Whether to save to graph database")


class TextExtractionResponse(BaseModel):
    """Response model for text extraction."""

    entities: List[ExtractedEntity] = Field(default_factory=list, description="Extracted entities")
    relations: List[ExtractedRelation] = Field(default_factory=list, description="Extracted relations")
    text_length: int = Field(default=0, description="Original text length")
    processing_time_ms: float = Field(default=0.0, description="Processing time in milliseconds")
    saved_entity_ids: List[UUID] = Field(default_factory=list, description="IDs of saved entities")
    saved_relation_ids: List[UUID] = Field(default_factory=list, description="IDs of saved relations")
