"""
Property-based tests for Ontology Template Service.

Tests Properties from ontology-expert-collaboration specification:
- Property 5: Template Instantiation Completeness
- Property 41: Template Export/Import Round Trip
"""

import asyncio
import json
from typing import List
from uuid import UUID, uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume

# Import the module under test
import sys
sys.path.insert(0, str(__file__).replace("\\", "/").rsplit("/tests/", 1)[0] + "/src")

from collaboration.template_service import (
    TemplateService,
    OntologyTemplate,
    OntologyTemplateCreate,
    OntologyTemplateUpdate,
    InstantiatedOntology,
    TemplateCustomization,
    TemplateSearchFilter,
    TemplateExportFormat,
    TemplateCategory,
    TemplateStatus,
    EntityTypeDefinition,
    EntityAttribute,
    RelationTypeDefinition,
    ValidationRuleDefinition,
    DataType,
    RelationCardinality,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def template_category_strategy(draw) -> TemplateCategory:
    """Generate valid template category."""
    return draw(st.sampled_from(list(TemplateCategory)))


@st.composite
def data_type_strategy(draw) -> DataType:
    """Generate valid data type."""
    return draw(st.sampled_from(list(DataType)))


@st.composite
def cardinality_strategy(draw) -> RelationCardinality:
    """Generate valid relation cardinality."""
    return draw(st.sampled_from(list(RelationCardinality)))


@st.composite
def entity_attribute_strategy(draw) -> EntityAttribute:
    """Generate entity attribute."""
    return EntityAttribute(
        name=draw(st.from_regex(r"[a-z][a-z0-9_]{2,20}", fullmatch=True)),
        display_name=draw(st.text(min_size=1, max_size=50)),
        display_name_zh=draw(st.text(min_size=0, max_size=50)),
        data_type=draw(data_type_strategy()),
        required=draw(st.booleans()),
        unique=draw(st.booleans()),
        indexed=draw(st.booleans()),
        default_value=None,
        description=draw(st.text(min_size=0, max_size=100)),
    )


@st.composite
def entity_type_strategy(draw, name: str = None) -> EntityTypeDefinition:
    """Generate entity type definition."""
    if name is None:
        name = draw(st.from_regex(r"[A-Z][a-zA-Z0-9]{2,20}", fullmatch=True))

    attributes = draw(st.lists(
        entity_attribute_strategy(),
        min_size=0,
        max_size=5,
    ))

    # Ensure unique attribute names
    seen_names = set()
    unique_attrs = []
    for attr in attributes:
        if attr.name not in seen_names:
            seen_names.add(attr.name)
            unique_attrs.append(attr)

    return EntityTypeDefinition(
        name=name,
        display_name=draw(st.text(min_size=1, max_size=50)),
        display_name_zh=draw(st.text(min_size=0, max_size=50)),
        description=draw(st.text(min_size=0, max_size=100)),
        attributes=unique_attrs,
        parent_type=None,
        is_abstract=draw(st.booleans()),
        tags=draw(st.lists(st.text(min_size=1, max_size=20), max_size=3)),
    )


@st.composite
def relation_type_strategy(
    draw,
    source_type: str,
    target_type: str,
) -> RelationTypeDefinition:
    """Generate relation type definition."""
    return RelationTypeDefinition(
        name=draw(st.from_regex(r"[a-z][a-z0-9_]{2,20}", fullmatch=True)),
        display_name=draw(st.text(min_size=1, max_size=50)),
        display_name_zh=draw(st.text(min_size=0, max_size=50)),
        description=draw(st.text(min_size=0, max_size=100)),
        source_entity_type=source_type,
        target_entity_type=target_type,
        cardinality=draw(cardinality_strategy()),
        bidirectional=draw(st.booleans()),
        inverse_name=draw(st.one_of(
            st.none(),
            st.from_regex(r"[a-z][a-z0-9_]{2,20}", fullmatch=True),
        )),
    )


@st.composite
def validation_rule_strategy(draw, target_type: str) -> ValidationRuleDefinition:
    """Generate validation rule definition."""
    return ValidationRuleDefinition(
        name=draw(st.from_regex(r"[a-z][a-z0-9_]{2,20}", fullmatch=True)),
        description=draw(st.text(min_size=0, max_size=100)),
        target_type=target_type,
        rule_type=draw(st.sampled_from(["regex", "range", "enum", "custom"])),
        rule_expression=draw(st.text(min_size=1, max_size=100)),
        error_message=draw(st.text(min_size=0, max_size=100)),
        error_message_zh=draw(st.text(min_size=0, max_size=100)),
        severity=draw(st.sampled_from(["error", "warning", "info"])),
    )


@st.composite
def template_name_strategy(draw) -> str:
    """Generate unique template name."""
    unique_id = draw(st.integers(min_value=1, max_value=1000000))
    prefix = draw(st.sampled_from(["Template", "Ontology", "Model", "Schema"]))
    return f"{prefix}_{unique_id}"


@st.composite
def template_create_strategy(draw) -> OntologyTemplateCreate:
    """Generate template creation data."""
    # Generate entity types with unique names
    num_entities = draw(st.integers(min_value=1, max_value=5))
    entity_names = [f"Entity{i}" for i in range(num_entities)]
    entity_types = [
        draw(entity_type_strategy(name=name))
        for name in entity_names
    ]

    # Generate relation types between existing entities
    relation_types = []
    if len(entity_types) >= 2:
        num_relations = draw(st.integers(min_value=0, max_value=3))
        for i in range(num_relations):
            source = draw(st.sampled_from(entity_names))
            target = draw(st.sampled_from(entity_names))
            relation_types.append(draw(relation_type_strategy(source, target)))

    # Generate validation rules
    validation_rules = []
    if entity_types:
        num_rules = draw(st.integers(min_value=0, max_value=3))
        for i in range(num_rules):
            target = draw(st.sampled_from(entity_names + ["all"]))
            validation_rules.append(draw(validation_rule_strategy(target)))

    return OntologyTemplateCreate(
        name=draw(template_name_strategy()),
        display_name=draw(st.text(min_size=1, max_size=50)),
        display_name_zh=draw(st.text(min_size=0, max_size=50)),
        description=draw(st.text(min_size=0, max_size=200)),
        category=draw(template_category_strategy()),
        tags=draw(st.lists(st.text(min_size=1, max_size=20), max_size=5)),
        entity_types=entity_types,
        relation_types=relation_types,
        validation_rules=validation_rules,
    )


# =============================================================================
# Property 5: Template Instantiation Completeness
# =============================================================================

class TestTemplateInstantiationCompleteness:
    """
    Property 5: Template Instantiation Completeness

    Validates that:
    1. All entity types from template are instantiated
    2. All relation types from template are instantiated
    3. All validation rules from template are instantiated
    4. Instantiated elements have unique IDs
    """

    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        return TemplateService()

    @given(template_data=template_create_strategy())
    @settings(max_examples=30, deadline=None)
    def test_all_entity_types_instantiated(
        self,
        template_data: OntologyTemplateCreate,
    ):
        """Property: All entity types from template are instantiated."""
        service = TemplateService()

        async def run_test():
            # Create template
            template = await service.create_template(template_data)

            # Instantiate
            instance = await service.instantiate_template(
                template.id,
                f"Instance_{uuid4().hex[:8]}",
            )

            # Verify entity count matches
            assert len(instance.entity_types) == len(template.entity_types)

            # Verify entity names match
            template_names = {et.name for et in template.entity_types}
            instance_names = {et.name for et in instance.entity_types}
            assert template_names == instance_names

        asyncio.run(run_test())

    @given(template_data=template_create_strategy())
    @settings(max_examples=30, deadline=None)
    def test_all_relation_types_instantiated(
        self,
        template_data: OntologyTemplateCreate,
    ):
        """Property: All relation types from template are instantiated."""
        service = TemplateService()

        async def run_test():
            # Create template
            template = await service.create_template(template_data)

            # Instantiate
            instance = await service.instantiate_template(
                template.id,
                f"Instance_{uuid4().hex[:8]}",
            )

            # Verify relation count matches
            assert len(instance.relation_types) == len(template.relation_types)

            # Verify relation names match
            template_names = {rt.name for rt in template.relation_types}
            instance_names = {rt.name for rt in instance.relation_types}
            assert template_names == instance_names

        asyncio.run(run_test())

    @given(template_data=template_create_strategy())
    @settings(max_examples=30, deadline=None)
    def test_all_validation_rules_instantiated(
        self,
        template_data: OntologyTemplateCreate,
    ):
        """Property: All validation rules from template are instantiated."""
        service = TemplateService()

        async def run_test():
            # Create template
            template = await service.create_template(template_data)

            # Instantiate
            instance = await service.instantiate_template(
                template.id,
                f"Instance_{uuid4().hex[:8]}",
            )

            # Verify rule count matches
            assert len(instance.validation_rules) == len(template.validation_rules)

            # Verify rule names match
            template_names = {vr.name for vr in template.validation_rules}
            instance_names = {vr.name for vr in instance.validation_rules}
            assert template_names == instance_names

        asyncio.run(run_test())

    @given(template_data=template_create_strategy())
    @settings(max_examples=30, deadline=None)
    def test_instantiated_elements_have_unique_ids(
        self,
        template_data: OntologyTemplateCreate,
    ):
        """Property: Instantiated elements have unique IDs."""
        service = TemplateService()

        async def run_test():
            # Create template
            template = await service.create_template(template_data)

            # Instantiate twice
            instance1 = await service.instantiate_template(
                template.id,
                f"Instance1_{uuid4().hex[:8]}",
            )
            instance2 = await service.instantiate_template(
                template.id,
                f"Instance2_{uuid4().hex[:8]}",
            )

            # Collect all IDs from both instances
            ids1 = set()
            ids1.update(et.id for et in instance1.entity_types)
            ids1.update(rt.id for rt in instance1.relation_types)
            ids1.update(vr.id for vr in instance1.validation_rules)

            ids2 = set()
            ids2.update(et.id for et in instance2.entity_types)
            ids2.update(rt.id for rt in instance2.relation_types)
            ids2.update(vr.id for vr in instance2.validation_rules)

            # IDs should not overlap
            assert ids1.isdisjoint(ids2), "Instantiated elements share IDs"

        asyncio.run(run_test())


# =============================================================================
# Property 41: Template Export/Import Round Trip
# =============================================================================

class TestTemplateExportImportRoundTrip:
    """
    Property 41: Template Export/Import Round Trip

    Validates that:
    1. Exported template can be imported back
    2. Imported template has same content as original
    3. Both JSON and YAML formats work correctly
    """

    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        return TemplateService()

    @given(template_data=template_create_strategy())
    @settings(max_examples=30, deadline=None)
    def test_json_export_import_round_trip(
        self,
        template_data: OntologyTemplateCreate,
    ):
        """Property: JSON export/import preserves template content."""
        service = TemplateService()

        async def run_test():
            # Create template
            original = await service.create_template(template_data)

            # Export to JSON
            exported = await service.export_template(
                original.id,
                format=TemplateExportFormat.JSON,
            )

            # Import back (with different name to avoid conflict)
            import_data = json.loads(exported)
            import_data["name"] = f"Imported_{uuid4().hex[:8]}"
            imported_content = json.dumps(import_data)

            imported = await service.import_template(
                imported_content,
                format=TemplateExportFormat.JSON,
            )

            # Verify content matches
            assert len(imported.entity_types) == len(original.entity_types)
            assert len(imported.relation_types) == len(original.relation_types)
            assert len(imported.validation_rules) == len(original.validation_rules)

            # Verify entity type names match
            original_et_names = {et.name for et in original.entity_types}
            imported_et_names = {et.name for et in imported.entity_types}
            assert original_et_names == imported_et_names

        asyncio.run(run_test())

    @given(template_data=template_create_strategy())
    @settings(max_examples=20, deadline=None)
    def test_yaml_export_import_round_trip(
        self,
        template_data: OntologyTemplateCreate,
    ):
        """Property: YAML export/import preserves template content."""
        service = TemplateService()

        async def run_test():
            # Create template
            original = await service.create_template(template_data)

            # Export to YAML
            exported = await service.export_template(
                original.id,
                format=TemplateExportFormat.YAML,
            )

            # Parse and modify name
            import yaml
            import_data = yaml.safe_load(exported)
            import_data["name"] = f"Imported_{uuid4().hex[:8]}"
            imported_content = yaml.dump(import_data)

            # Import back
            imported = await service.import_template(
                imported_content,
                format=TemplateExportFormat.YAML,
            )

            # Verify content matches
            assert len(imported.entity_types) == len(original.entity_types)
            assert len(imported.relation_types) == len(original.relation_types)

        asyncio.run(run_test())

    @given(template_data=template_create_strategy())
    @settings(max_examples=20, deadline=None)
    def test_export_preserves_entity_attributes(
        self,
        template_data: OntologyTemplateCreate,
    ):
        """Property: Export preserves entity attributes."""
        service = TemplateService()

        async def run_test():
            # Create template
            original = await service.create_template(template_data)

            # Export to JSON
            exported = await service.export_template(
                original.id,
                format=TemplateExportFormat.JSON,
            )

            # Parse and verify attributes
            data = json.loads(exported)

            for i, et_data in enumerate(data["entity_types"]):
                original_et = original.entity_types[i]
                assert et_data["name"] == original_et.name
                assert len(et_data["attributes"]) == len(original_et.attributes)

                for j, attr_data in enumerate(et_data["attributes"]):
                    original_attr = original_et.attributes[j]
                    assert attr_data["name"] == original_attr.name
                    assert attr_data["data_type"] == original_attr.data_type.value
                    assert attr_data["required"] == original_attr.required

        asyncio.run(run_test())


# =============================================================================
# Additional Property Tests: Template Versioning
# =============================================================================

class TestTemplateVersioning:
    """
    Tests for template versioning functionality.
    """

    @given(template_data=template_create_strategy())
    @settings(max_examples=20, deadline=None)
    def test_new_version_increments_version_number(
        self,
        template_data: OntologyTemplateCreate,
    ):
        """Property: New version increments version number."""
        service = TemplateService()

        async def run_test():
            # Create original template
            original = await service.create_template(template_data)
            assert original.version == 1

            # Create new version
            new_version = await service.create_new_version(
                original.id,
                template_data,
            )

            assert new_version.version == 2
            assert new_version.parent_template_id == original.id
            assert original.id in new_version.lineage

        asyncio.run(run_test())

    @given(template_data=template_create_strategy())
    @settings(max_examples=20, deadline=None)
    def test_new_version_deprecates_old_version(
        self,
        template_data: OntologyTemplateCreate,
    ):
        """Property: New version marks old version as deprecated."""
        service = TemplateService()

        async def run_test():
            # Create original template
            original = await service.create_template(template_data)

            # Create new version
            await service.create_new_version(
                original.id,
                template_data,
            )

            # Get original again
            old_template = await service.get_template(original.id)
            assert old_template is not None
            assert old_template.status == TemplateStatus.DEPRECATED

        asyncio.run(run_test())


# =============================================================================
# Additional Property Tests: Template Customization
# =============================================================================

class TestTemplateCustomization:
    """
    Tests for template customization functionality.
    """

    @given(template_data=template_create_strategy())
    @settings(max_examples=20, deadline=None)
    def test_customization_adds_entity_types(
        self,
        template_data: OntologyTemplateCreate,
    ):
        """Property: Customization can add new entity types."""
        service = TemplateService()

        async def run_test():
            # Create template
            template = await service.create_template(template_data)

            # Create customization with new entity type
            new_entity = EntityTypeDefinition(
                name=f"NewEntity_{uuid4().hex[:8]}",
                display_name="New Entity",
            )

            customization = TemplateCustomization(
                add_entity_types=[new_entity],
            )

            # Instantiate with customization
            instance = await service.instantiate_template(
                template.id,
                f"Instance_{uuid4().hex[:8]}",
                customizations=customization,
            )

            # Verify new entity was added
            instance_names = {et.name for et in instance.entity_types}
            assert new_entity.name in instance_names
            assert len(instance.entity_types) == len(template.entity_types) + 1

        asyncio.run(run_test())

    @given(template_data=template_create_strategy())
    @settings(max_examples=20, deadline=None)
    def test_customization_removes_entity_types(
        self,
        template_data: OntologyTemplateCreate,
    ):
        """Property: Customization can remove entity types."""
        assume(len(template_data.entity_types) >= 2)

        service = TemplateService()

        async def run_test():
            # Create template
            template = await service.create_template(template_data)

            # Remove first entity type
            entity_to_remove = template.entity_types[0].name

            customization = TemplateCustomization(
                remove_entity_types=[entity_to_remove],
            )

            # Instantiate with customization
            instance = await service.instantiate_template(
                template.id,
                f"Instance_{uuid4().hex[:8]}",
                customizations=customization,
            )

            # Verify entity was removed
            instance_names = {et.name for et in instance.entity_types}
            assert entity_to_remove not in instance_names
            assert len(instance.entity_types) == len(template.entity_types) - 1

        asyncio.run(run_test())


# =============================================================================
# Additional Property Tests: Template Search
# =============================================================================

class TestTemplateSearch:
    """
    Tests for template search functionality.
    """

    @given(
        category=template_category_strategy(),
    )
    @settings(max_examples=20, deadline=None)
    def test_filter_by_category_returns_matching_templates(
        self,
        category: TemplateCategory,
    ):
        """Property: Filtering by category returns only matching templates."""
        service = TemplateService()

        async def run_test():
            # Create templates with specific category
            await service.create_template(OntologyTemplateCreate(
                name=f"Matching_{uuid4().hex[:8]}",
                entity_types=[EntityTypeDefinition(name="Entity1")],
                category=category,
            ))

            # Create template with different category
            other_categories = [c for c in TemplateCategory if c != category]
            if other_categories:
                await service.create_template(OntologyTemplateCreate(
                    name=f"Other_{uuid4().hex[:8]}",
                    entity_types=[EntityTypeDefinition(name="Entity2")],
                    category=other_categories[0],
                ))

            # Filter by category
            filter_params = TemplateSearchFilter(category=category)
            results = await service.list_templates(filter_params=filter_params)

            # All results should have matching category
            for template in results:
                assert template.category == category

        asyncio.run(run_test())


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
