"""
Ontology Template Service (本体模板服务)

Provides template management, instantiation, customization, and export/import
functionality for ontology collaboration workflows.

Implements Task 4 from ontology-expert-collaboration specification.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
import yaml


# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class TemplateCategory(str, Enum):
    """Template category (模板分类)"""
    # Industry categories
    FINANCE = "finance"  # 金融
    HEALTHCARE = "healthcare"  # 医疗
    MANUFACTURING = "manufacturing"  # 制造
    RETAIL = "retail"  # 零售
    LOGISTICS = "logistics"  # 物流
    ENERGY = "energy"  # 能源
    GOVERNMENT = "government"  # 政府

    # Technical categories
    GENERAL = "general"  # 通用
    DATA_GOVERNANCE = "data_governance"  # 数据治理
    KNOWLEDGE_GRAPH = "knowledge_graph"  # 知识图谱

    # Compliance categories
    COMPLIANCE = "compliance"  # 合规
    DATA_SECURITY = "data_security"  # 数据安全
    PRIVACY = "privacy"  # 隐私保护


class TemplateStatus(str, Enum):
    """Template status (模板状态)"""
    DRAFT = "draft"  # 草稿
    PUBLISHED = "published"  # 已发布
    DEPRECATED = "deprecated"  # 已废弃
    ARCHIVED = "archived"  # 已归档


class DataType(str, Enum):
    """Data type for entity attributes (实体属性数据类型)"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    ARRAY = "array"
    REFERENCE = "reference"


class RelationCardinality(str, Enum):
    """Relation cardinality (关系基数)"""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


# =============================================================================
# Data Models (Pydantic)
# =============================================================================

class EntityAttribute(BaseModel):
    """Entity attribute definition (实体属性定义)"""
    name: str = Field(..., min_length=1)
    display_name: str = Field(default="")
    display_name_zh: str = Field(default="")
    data_type: DataType = DataType.STRING
    required: bool = False
    unique: bool = False
    indexed: bool = False
    default_value: Optional[Any] = None
    description: str = ""
    validation_rules: List[str] = Field(default_factory=list)


class EntityTypeDefinition(BaseModel):
    """Entity type definition (实体类型定义)"""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1)
    display_name: str = Field(default="")
    display_name_zh: str = Field(default="")
    description: str = ""
    attributes: List[EntityAttribute] = Field(default_factory=list)
    parent_type: Optional[str] = None  # For inheritance
    is_abstract: bool = False
    tags: List[str] = Field(default_factory=list)


class RelationTypeDefinition(BaseModel):
    """Relation type definition (关系类型定义)"""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1)
    display_name: str = Field(default="")
    display_name_zh: str = Field(default="")
    description: str = ""
    source_entity_type: str
    target_entity_type: str
    cardinality: RelationCardinality = RelationCardinality.MANY_TO_MANY
    attributes: List[EntityAttribute] = Field(default_factory=list)
    bidirectional: bool = False
    inverse_name: Optional[str] = None


class ValidationRuleDefinition(BaseModel):
    """Validation rule definition (验证规则定义)"""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1)
    description: str = ""
    target_type: str  # Entity type or 'all'
    rule_type: str  # 'regex', 'range', 'enum', 'custom'
    rule_expression: str
    error_message: str = ""
    error_message_zh: str = ""
    severity: str = "error"  # 'error', 'warning', 'info'


class OntologyTemplateCreate(BaseModel):
    """Create ontology template request (创建本体模板请求)"""
    name: str = Field(..., min_length=1, max_length=200)
    display_name: str = Field(default="")
    display_name_zh: str = Field(default="")
    description: str = ""
    category: TemplateCategory = TemplateCategory.GENERAL
    tags: List[str] = Field(default_factory=list)
    entity_types: List[EntityTypeDefinition] = Field(default_factory=list)
    relation_types: List[RelationTypeDefinition] = Field(default_factory=list)
    validation_rules: List[ValidationRuleDefinition] = Field(default_factory=list)


class OntologyTemplateUpdate(BaseModel):
    """Update ontology template request (更新本体模板请求)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    display_name: Optional[str] = None
    display_name_zh: Optional[str] = None
    description: Optional[str] = None
    category: Optional[TemplateCategory] = None
    tags: Optional[List[str]] = None
    status: Optional[TemplateStatus] = None


class OntologyTemplate(BaseModel):
    """Ontology template (本体模板)"""
    id: UUID = Field(default_factory=uuid4)
    name: str
    display_name: str = ""
    display_name_zh: str = ""
    description: str = ""
    version: int = 1
    category: TemplateCategory = TemplateCategory.GENERAL
    tags: List[str] = Field(default_factory=list)
    status: TemplateStatus = TemplateStatus.DRAFT

    # Template content
    entity_types: List[EntityTypeDefinition] = Field(default_factory=list)
    relation_types: List[RelationTypeDefinition] = Field(default_factory=list)
    validation_rules: List[ValidationRuleDefinition] = Field(default_factory=list)

    # Lineage tracking
    parent_template_id: Optional[UUID] = None
    lineage: List[UUID] = Field(default_factory=list)

    # Metadata
    author_id: Optional[UUID] = None
    author_name: str = ""
    usage_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InstantiatedOntology(BaseModel):
    """Instantiated ontology from template (从模板实例化的本体)"""
    id: UUID = Field(default_factory=uuid4)
    name: str
    template_id: UUID
    template_version: int
    project_id: Optional[UUID] = None

    # Instantiated content with unique IDs
    entity_types: List[EntityTypeDefinition] = Field(default_factory=list)
    relation_types: List[RelationTypeDefinition] = Field(default_factory=list)
    validation_rules: List[ValidationRuleDefinition] = Field(default_factory=list)

    # Customizations applied
    customizations: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TemplateCustomization(BaseModel):
    """Template customization request (模板定制请求)"""
    add_entity_types: List[EntityTypeDefinition] = Field(default_factory=list)
    remove_entity_types: List[str] = Field(default_factory=list)  # By name
    modify_entity_types: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    add_relation_types: List[RelationTypeDefinition] = Field(default_factory=list)
    remove_relation_types: List[str] = Field(default_factory=list)  # By name
    modify_relation_types: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    add_validation_rules: List[ValidationRuleDefinition] = Field(default_factory=list)
    remove_validation_rules: List[str] = Field(default_factory=list)  # By name


class TemplateSearchFilter(BaseModel):
    """Template search filter (模板搜索过滤器)"""
    category: Optional[TemplateCategory] = None
    tags: Optional[List[str]] = None
    status: Optional[TemplateStatus] = None
    author_id: Optional[UUID] = None
    min_version: Optional[int] = None


class TemplateExportFormat(str, Enum):
    """Template export format (模板导出格式)"""
    JSON = "json"
    YAML = "yaml"


# =============================================================================
# Template Service
# =============================================================================

class TemplateService:
    """
    Ontology Template Service (本体模板服务)

    Provides template management, instantiation, customization, and
    export/import functionality for ontology collaboration workflows.

    Features:
    - Template CRUD operations
    - Template versioning
    - Template lineage tracking
    - Template instantiation
    - Template customization with validation
    - Template export/import (JSON/YAML)
    - Template search and filtering
    """

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        cache_ttl_seconds: int = 3600,  # 1 hour
    ):
        """
        Initialize TemplateService.

        Args:
            redis_client: Optional Redis client for caching
            cache_ttl_seconds: Cache TTL in seconds (default 1 hour)
        """
        self._lock = asyncio.Lock()
        self._templates: Dict[UUID, OntologyTemplate] = {}
        self._name_index: Dict[str, UUID] = {}
        self._instantiated: Dict[UUID, InstantiatedOntology] = {}
        self._redis = redis_client
        self._cache_ttl = cache_ttl_seconds

        logger.info("TemplateService initialized")

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def create_template(
        self,
        data: OntologyTemplateCreate,
        author_id: Optional[UUID] = None,
        author_name: str = "",
    ) -> OntologyTemplate:
        """
        Create a new ontology template.

        Args:
            data: Template creation data
            author_id: Author's UUID
            author_name: Author's name

        Returns:
            Created template

        Raises:
            ValueError: If template name already exists
        """
        async with self._lock:
            # Check name uniqueness
            if data.name.lower() in self._name_index:
                raise ValueError(f"Template with name '{data.name}' already exists")

            # Create template
            template = OntologyTemplate(
                name=data.name,
                display_name=data.display_name or data.name,
                display_name_zh=data.display_name_zh,
                description=data.description,
                category=data.category,
                tags=data.tags,
                entity_types=data.entity_types,
                relation_types=data.relation_types,
                validation_rules=data.validation_rules,
                author_id=author_id,
                author_name=author_name,
            )

            # Store
            self._templates[template.id] = template
            self._name_index[template.name.lower()] = template.id

            logger.info(f"Created template: {template.id} ({template.name})")
            return template

    async def get_template(self, template_id: UUID) -> Optional[OntologyTemplate]:
        """
        Get template by ID.

        Args:
            template_id: Template UUID

        Returns:
            Template or None if not found
        """
        return self._templates.get(template_id)

    async def get_template_by_name(self, name: str) -> Optional[OntologyTemplate]:
        """
        Get template by name.

        Args:
            name: Template name

        Returns:
            Template or None if not found
        """
        template_id = self._name_index.get(name.lower())
        if template_id:
            return self._templates.get(template_id)
        return None

    async def update_template(
        self,
        template_id: UUID,
        data: OntologyTemplateUpdate,
    ) -> Optional[OntologyTemplate]:
        """
        Update template metadata (not content).

        Args:
            template_id: Template UUID
            data: Update data

        Returns:
            Updated template or None if not found
        """
        async with self._lock:
            template = self._templates.get(template_id)
            if not template:
                return None

            # Handle name change
            old_name = template.name.lower()
            update_data = data.model_dump(exclude_unset=True)

            if "name" in update_data:
                new_name = update_data["name"].lower()
                if new_name != old_name and new_name in self._name_index:
                    raise ValueError(f"Template name '{update_data['name']}' already exists")

                # Update name index
                del self._name_index[old_name]
                self._name_index[new_name] = template_id

            # Update fields
            for field_name, value in update_data.items():
                if value is not None:
                    setattr(template, field_name, value)

            template.updated_at = datetime.utcnow()

            # Store
            self._templates[template_id] = template

            logger.info(f"Updated template: {template_id}")
            return template

    async def delete_template(self, template_id: UUID) -> bool:
        """
        Delete template (soft delete - archive).

        Args:
            template_id: Template UUID

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            template = self._templates.get(template_id)
            if not template:
                return False

            # Soft delete - change status to archived
            template.status = TemplateStatus.ARCHIVED
            template.updated_at = datetime.utcnow()
            self._templates[template_id] = template

            # Remove from name index
            if template.name.lower() in self._name_index:
                del self._name_index[template.name.lower()]

            logger.info(f"Archived template: {template_id}")
            return True

    async def list_templates(
        self,
        filter_params: Optional[TemplateSearchFilter] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OntologyTemplate]:
        """
        List templates with optional filtering.

        Args:
            filter_params: Optional search filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of templates
        """
        templates = [
            t for t in self._templates.values()
            if t.status != TemplateStatus.ARCHIVED
        ]

        # Apply filters
        if filter_params:
            templates = self._apply_filters(templates, filter_params)

        # Sort by usage count (most popular first)
        templates.sort(key=lambda x: x.usage_count, reverse=True)

        return templates[skip:skip + limit]

    def _apply_filters(
        self,
        templates: List[OntologyTemplate],
        filter_params: TemplateSearchFilter,
    ) -> List[OntologyTemplate]:
        """Apply search filters to template list."""
        filtered = templates

        if filter_params.category:
            filtered = [t for t in filtered if t.category == filter_params.category]

        if filter_params.tags:
            filter_set = set(filter_params.tags)
            filtered = [
                t for t in filtered
                if filter_set.intersection(set(t.tags))
            ]

        if filter_params.status:
            filtered = [t for t in filtered if t.status == filter_params.status]

        if filter_params.author_id:
            filtered = [t for t in filtered if t.author_id == filter_params.author_id]

        if filter_params.min_version is not None:
            filtered = [t for t in filtered if t.version >= filter_params.min_version]

        return filtered

    # =========================================================================
    # Versioning
    # =========================================================================

    async def create_new_version(
        self,
        template_id: UUID,
        data: OntologyTemplateCreate,
        author_id: Optional[UUID] = None,
        author_name: str = "",
    ) -> OntologyTemplate:
        """
        Create a new version of an existing template.

        Args:
            template_id: Original template UUID
            data: New version data
            author_id: Author's UUID
            author_name: Author's name

        Returns:
            New template version

        Raises:
            ValueError: If original template not found
        """
        async with self._lock:
            original = self._templates.get(template_id)
            if not original:
                raise ValueError(f"Template {template_id} not found")

            # Create new version
            new_template = OntologyTemplate(
                name=f"{original.name}_v{original.version + 1}",
                display_name=data.display_name or original.display_name,
                display_name_zh=data.display_name_zh or original.display_name_zh,
                description=data.description or original.description,
                category=data.category or original.category,
                tags=data.tags or original.tags,
                entity_types=data.entity_types,
                relation_types=data.relation_types,
                validation_rules=data.validation_rules,
                version=original.version + 1,
                parent_template_id=template_id,
                lineage=original.lineage + [original.id],
                author_id=author_id,
                author_name=author_name,
            )

            # Store
            self._templates[new_template.id] = new_template
            self._name_index[new_template.name.lower()] = new_template.id

            # Deprecate old version
            original.status = TemplateStatus.DEPRECATED
            original.updated_at = datetime.utcnow()
            self._templates[template_id] = original

            logger.info(
                f"Created new version: {new_template.id} (v{new_template.version}) "
                f"from {template_id}"
            )
            return new_template

    async def get_template_versions(
        self,
        template_id: UUID,
    ) -> List[OntologyTemplate]:
        """
        Get all versions of a template (by lineage).

        Args:
            template_id: Any version's template UUID

        Returns:
            List of all versions sorted by version number
        """
        template = self._templates.get(template_id)
        if not template:
            return []

        # Collect all related templates
        all_ids = set(template.lineage) | {template_id}

        # Find all templates with this ID in their lineage
        for t in self._templates.values():
            if template_id in t.lineage:
                all_ids.add(t.id)
                all_ids.update(t.lineage)

        # Get templates and sort by version
        versions = [
            self._templates[tid]
            for tid in all_ids
            if tid in self._templates
        ]
        versions.sort(key=lambda x: x.version)

        return versions

    # =========================================================================
    # Instantiation
    # =========================================================================

    async def instantiate_template(
        self,
        template_id: UUID,
        instance_name: str,
        project_id: Optional[UUID] = None,
        customizations: Optional[TemplateCustomization] = None,
    ) -> InstantiatedOntology:
        """
        Instantiate a template to create a new ontology.

        Args:
            template_id: Template UUID
            instance_name: Name for the instantiated ontology
            project_id: Optional project UUID
            customizations: Optional customizations to apply

        Returns:
            Instantiated ontology

        Raises:
            ValueError: If template not found
        """
        async with self._lock:
            template = self._templates.get(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")

            # Generate unique IDs for all elements
            entity_types = [
                EntityTypeDefinition(
                    id=uuid4(),
                    name=et.name,
                    display_name=et.display_name,
                    display_name_zh=et.display_name_zh,
                    description=et.description,
                    attributes=et.attributes,
                    parent_type=et.parent_type,
                    is_abstract=et.is_abstract,
                    tags=et.tags,
                )
                for et in template.entity_types
            ]

            relation_types = [
                RelationTypeDefinition(
                    id=uuid4(),
                    name=rt.name,
                    display_name=rt.display_name,
                    display_name_zh=rt.display_name_zh,
                    description=rt.description,
                    source_entity_type=rt.source_entity_type,
                    target_entity_type=rt.target_entity_type,
                    cardinality=rt.cardinality,
                    attributes=rt.attributes,
                    bidirectional=rt.bidirectional,
                    inverse_name=rt.inverse_name,
                )
                for rt in template.relation_types
            ]

            validation_rules = [
                ValidationRuleDefinition(
                    id=uuid4(),
                    name=vr.name,
                    description=vr.description,
                    target_type=vr.target_type,
                    rule_type=vr.rule_type,
                    rule_expression=vr.rule_expression,
                    error_message=vr.error_message,
                    error_message_zh=vr.error_message_zh,
                    severity=vr.severity,
                )
                for vr in template.validation_rules
            ]

            # Create instantiated ontology
            instance = InstantiatedOntology(
                name=instance_name,
                template_id=template_id,
                template_version=template.version,
                project_id=project_id,
                entity_types=entity_types,
                relation_types=relation_types,
                validation_rules=validation_rules,
            )

            # Apply customizations if provided
            if customizations:
                instance = await self._apply_customizations(instance, customizations)

            # Store
            self._instantiated[instance.id] = instance

            # Increment template usage count
            template.usage_count += 1
            template.updated_at = datetime.utcnow()
            self._templates[template_id] = template

            logger.info(
                f"Instantiated template {template_id} as ontology {instance.id} "
                f"({instance_name})"
            )
            return instance

    async def _apply_customizations(
        self,
        instance: InstantiatedOntology,
        customizations: TemplateCustomization,
    ) -> InstantiatedOntology:
        """Apply customizations to an instantiated ontology."""
        # Track customizations
        custom_log: Dict[str, Any] = {}

        # Add entity types
        if customizations.add_entity_types:
            for et in customizations.add_entity_types:
                # Validate no name conflict
                existing_names = {e.name for e in instance.entity_types}
                if et.name in existing_names:
                    raise ValueError(f"Entity type '{et.name}' already exists")
                instance.entity_types.append(et)
            custom_log["added_entity_types"] = [
                et.name for et in customizations.add_entity_types
            ]

        # Remove entity types
        if customizations.remove_entity_types:
            remove_set = set(customizations.remove_entity_types)
            instance.entity_types = [
                et for et in instance.entity_types
                if et.name not in remove_set
            ]
            custom_log["removed_entity_types"] = customizations.remove_entity_types

        # Modify entity types
        if customizations.modify_entity_types:
            for name, modifications in customizations.modify_entity_types.items():
                for et in instance.entity_types:
                    if et.name == name:
                        for field_name, value in modifications.items():
                            if hasattr(et, field_name):
                                setattr(et, field_name, value)
                        break
            custom_log["modified_entity_types"] = list(
                customizations.modify_entity_types.keys()
            )

        # Add relation types
        if customizations.add_relation_types:
            for rt in customizations.add_relation_types:
                # Validate source and target exist
                entity_names = {e.name for e in instance.entity_types}
                if rt.source_entity_type not in entity_names:
                    raise ValueError(
                        f"Source entity type '{rt.source_entity_type}' not found"
                    )
                if rt.target_entity_type not in entity_names:
                    raise ValueError(
                        f"Target entity type '{rt.target_entity_type}' not found"
                    )
                instance.relation_types.append(rt)
            custom_log["added_relation_types"] = [
                rt.name for rt in customizations.add_relation_types
            ]

        # Remove relation types
        if customizations.remove_relation_types:
            remove_set = set(customizations.remove_relation_types)
            instance.relation_types = [
                rt for rt in instance.relation_types
                if rt.name not in remove_set
            ]
            custom_log["removed_relation_types"] = customizations.remove_relation_types

        # Modify relation types
        if customizations.modify_relation_types:
            for name, modifications in customizations.modify_relation_types.items():
                for rt in instance.relation_types:
                    if rt.name == name:
                        for field_name, value in modifications.items():
                            if hasattr(rt, field_name):
                                setattr(rt, field_name, value)
                        break
            custom_log["modified_relation_types"] = list(
                customizations.modify_relation_types.keys()
            )

        # Add validation rules
        if customizations.add_validation_rules:
            instance.validation_rules.extend(customizations.add_validation_rules)
            custom_log["added_validation_rules"] = [
                vr.name for vr in customizations.add_validation_rules
            ]

        # Remove validation rules
        if customizations.remove_validation_rules:
            remove_set = set(customizations.remove_validation_rules)
            instance.validation_rules = [
                vr for vr in instance.validation_rules
                if vr.name not in remove_set
            ]
            custom_log["removed_validation_rules"] = customizations.remove_validation_rules

        # Store customization log
        instance.customizations = custom_log
        instance.updated_at = datetime.utcnow()

        return instance

    # =========================================================================
    # Export/Import
    # =========================================================================

    async def export_template(
        self,
        template_id: UUID,
        format: TemplateExportFormat = TemplateExportFormat.JSON,
    ) -> str:
        """
        Export template to JSON or YAML format.

        Args:
            template_id: Template UUID
            format: Export format (JSON or YAML)

        Returns:
            Serialized template string

        Raises:
            ValueError: If template not found
        """
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Prepare export data
        export_data = {
            "name": template.name,
            "display_name": template.display_name,
            "display_name_zh": template.display_name_zh,
            "description": template.description,
            "version": template.version,
            "category": template.category.value,
            "tags": template.tags,
            "entity_types": [
                {
                    "name": et.name,
                    "display_name": et.display_name,
                    "display_name_zh": et.display_name_zh,
                    "description": et.description,
                    "attributes": [
                        {
                            "name": attr.name,
                            "display_name": attr.display_name,
                            "display_name_zh": attr.display_name_zh,
                            "data_type": attr.data_type.value,
                            "required": attr.required,
                            "unique": attr.unique,
                            "indexed": attr.indexed,
                            "default_value": attr.default_value,
                            "description": attr.description,
                            "validation_rules": attr.validation_rules,
                        }
                        for attr in et.attributes
                    ],
                    "parent_type": et.parent_type,
                    "is_abstract": et.is_abstract,
                    "tags": et.tags,
                }
                for et in template.entity_types
            ],
            "relation_types": [
                {
                    "name": rt.name,
                    "display_name": rt.display_name,
                    "display_name_zh": rt.display_name_zh,
                    "description": rt.description,
                    "source_entity_type": rt.source_entity_type,
                    "target_entity_type": rt.target_entity_type,
                    "cardinality": rt.cardinality.value,
                    "attributes": [
                        {
                            "name": attr.name,
                            "display_name": attr.display_name,
                            "display_name_zh": attr.display_name_zh,
                            "data_type": attr.data_type.value,
                            "required": attr.required,
                        }
                        for attr in rt.attributes
                    ],
                    "bidirectional": rt.bidirectional,
                    "inverse_name": rt.inverse_name,
                }
                for rt in template.relation_types
            ],
            "validation_rules": [
                {
                    "name": vr.name,
                    "description": vr.description,
                    "target_type": vr.target_type,
                    "rule_type": vr.rule_type,
                    "rule_expression": vr.rule_expression,
                    "error_message": vr.error_message,
                    "error_message_zh": vr.error_message_zh,
                    "severity": vr.severity,
                }
                for vr in template.validation_rules
            ],
            "exported_at": datetime.utcnow().isoformat(),
            "export_version": "1.0",
        }

        if format == TemplateExportFormat.JSON:
            return json.dumps(export_data, indent=2, ensure_ascii=False)
        else:
            return yaml.dump(export_data, allow_unicode=True, default_flow_style=False)

    async def import_template(
        self,
        content: str,
        format: TemplateExportFormat = TemplateExportFormat.JSON,
        author_id: Optional[UUID] = None,
        author_name: str = "",
    ) -> OntologyTemplate:
        """
        Import template from JSON or YAML format.

        Args:
            content: Serialized template string
            format: Import format (JSON or YAML)
            author_id: Importer's UUID
            author_name: Importer's name

        Returns:
            Imported template

        Raises:
            ValueError: If content is invalid
        """
        # Parse content
        try:
            if format == TemplateExportFormat.JSON:
                data = json.loads(content)
            else:
                data = yaml.safe_load(content)
        except Exception as e:
            raise ValueError(f"Failed to parse template content: {e}")

        # Validate required fields
        required_fields = ["name", "entity_types"]
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing required field: {field_name}")

        # Convert to model format
        entity_types = [
            EntityTypeDefinition(
                name=et["name"],
                display_name=et.get("display_name", ""),
                display_name_zh=et.get("display_name_zh", ""),
                description=et.get("description", ""),
                attributes=[
                    EntityAttribute(
                        name=attr["name"],
                        display_name=attr.get("display_name", ""),
                        display_name_zh=attr.get("display_name_zh", ""),
                        data_type=DataType(attr.get("data_type", "string")),
                        required=attr.get("required", False),
                        unique=attr.get("unique", False),
                        indexed=attr.get("indexed", False),
                        default_value=attr.get("default_value"),
                        description=attr.get("description", ""),
                        validation_rules=attr.get("validation_rules", []),
                    )
                    for attr in et.get("attributes", [])
                ],
                parent_type=et.get("parent_type"),
                is_abstract=et.get("is_abstract", False),
                tags=et.get("tags", []),
            )
            for et in data["entity_types"]
        ]

        relation_types = [
            RelationTypeDefinition(
                name=rt["name"],
                display_name=rt.get("display_name", ""),
                display_name_zh=rt.get("display_name_zh", ""),
                description=rt.get("description", ""),
                source_entity_type=rt["source_entity_type"],
                target_entity_type=rt["target_entity_type"],
                cardinality=RelationCardinality(
                    rt.get("cardinality", "many_to_many")
                ),
                attributes=[
                    EntityAttribute(
                        name=attr["name"],
                        display_name=attr.get("display_name", ""),
                        display_name_zh=attr.get("display_name_zh", ""),
                        data_type=DataType(attr.get("data_type", "string")),
                        required=attr.get("required", False),
                    )
                    for attr in rt.get("attributes", [])
                ],
                bidirectional=rt.get("bidirectional", False),
                inverse_name=rt.get("inverse_name"),
            )
            for rt in data.get("relation_types", [])
        ]

        validation_rules = [
            ValidationRuleDefinition(
                name=vr["name"],
                description=vr.get("description", ""),
                target_type=vr["target_type"],
                rule_type=vr["rule_type"],
                rule_expression=vr["rule_expression"],
                error_message=vr.get("error_message", ""),
                error_message_zh=vr.get("error_message_zh", ""),
                severity=vr.get("severity", "error"),
            )
            for vr in data.get("validation_rules", [])
        ]

        # Create template
        create_data = OntologyTemplateCreate(
            name=data["name"],
            display_name=data.get("display_name", ""),
            display_name_zh=data.get("display_name_zh", ""),
            description=data.get("description", ""),
            category=TemplateCategory(data.get("category", "general")),
            tags=data.get("tags", []),
            entity_types=entity_types,
            relation_types=relation_types,
            validation_rules=validation_rules,
        )

        return await self.create_template(
            create_data,
            author_id=author_id,
            author_name=author_name,
        )

    # =========================================================================
    # Search
    # =========================================================================

    async def search_templates(
        self,
        query: str,
        filter_params: Optional[TemplateSearchFilter] = None,
        limit: int = 20,
    ) -> List[OntologyTemplate]:
        """
        Search templates by name, description, or tags.

        Args:
            query: Search query string
            filter_params: Optional additional filters
            limit: Maximum results

        Returns:
            List of matching templates
        """
        query_lower = query.lower()
        results: List[OntologyTemplate] = []

        for template in self._templates.values():
            if template.status == TemplateStatus.ARCHIVED:
                continue

            # Search in name, description, tags
            if (
                query_lower in template.name.lower() or
                query_lower in template.display_name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)
            ):
                results.append(template)

        # Apply additional filters
        if filter_params:
            results = self._apply_filters(results, filter_params)

        # Sort by usage count
        results.sort(key=lambda x: x.usage_count, reverse=True)

        return results[:limit]

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_template_statistics(self) -> Dict[str, Any]:
        """
        Get overall template statistics.

        Returns:
            Dictionary with various statistics
        """
        total = len(self._templates)
        if total == 0:
            return {
                "total_templates": 0,
                "published_templates": 0,
                "category_distribution": {},
                "total_instantiations": 0,
                "average_entity_types": 0,
            }

        published = sum(
            1 for t in self._templates.values()
            if t.status == TemplateStatus.PUBLISHED
        )

        # Category distribution
        cat_dist: Dict[str, int] = {}
        for template in self._templates.values():
            cat_dist[template.category.value] = cat_dist.get(
                template.category.value, 0
            ) + 1

        # Total instantiations
        total_instantiations = sum(
            t.usage_count for t in self._templates.values()
        )

        # Average entity types per template
        total_entity_types = sum(
            len(t.entity_types) for t in self._templates.values()
        )
        avg_entity_types = total_entity_types / total if total > 0 else 0

        return {
            "total_templates": total,
            "published_templates": published,
            "category_distribution": cat_dist,
            "total_instantiations": total_instantiations,
            "average_entity_types": avg_entity_types,
        }

    async def get_popular_templates(
        self,
        category: Optional[TemplateCategory] = None,
        limit: int = 10,
    ) -> List[OntologyTemplate]:
        """
        Get most popular templates by usage count.

        Args:
            category: Optional filter by category
            limit: Maximum results

        Returns:
            List of popular templates
        """
        templates = [
            t for t in self._templates.values()
            if t.status == TemplateStatus.PUBLISHED
        ]

        if category:
            templates = [t for t in templates if t.category == category]

        # Sort by usage count
        templates.sort(key=lambda x: x.usage_count, reverse=True)

        return templates[:limit]
