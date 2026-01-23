"""Property-based tests for Ontology I18n Service.

This module tests the universal correctness properties of the i18n service:
- Property 9: Bilingual Definition Requirement
- Property 10: I18n Display Consistency

Requirements validated:
- 3.1: Bilingual definition requirement
- 3.2: I18n display consistency
- 3.3: Translation fallback mechanism
- 3.4: Translation export/import
- 3.5: Language-specific validation rule selection
"""

import pytest
import asyncio
import json
from hypothesis import given, strategies as st, settings
from uuid import uuid4
from src.collaboration.ontology_i18n_service import (
    OntologyI18nService,
    Language,
    TranslationStatus
)


# ============================================================================
# Property 9: Bilingual Definition Requirement
# ============================================================================

class TestBilingualDefinitionRequirement:
    """Test bilingual definition requirement.

    Property: Ontology elements must have definitions in both zh-CN and en-US
    for required fields (name, description, definition).

    Requirements: 3.1
    """

    @pytest.mark.asyncio
    async def test_bilingual_requirement_complete(self):
        """Test that elements with complete bilingual translations pass validation."""
        service = OntologyI18nService()

        element_id = uuid4()

        # Add zh-CN translations
        await service.add_translation(element_id, "entity_type", "name", Language.ZH_CN, "实体")
        await service.add_translation(element_id, "entity_type", "description", Language.ZH_CN, "这是一个实体")
        await service.add_translation(element_id, "entity_type", "definition", Language.ZH_CN, "实体的定义")

        # Add en-US translations
        await service.add_translation(element_id, "entity_type", "name", Language.EN_US, "Entity")
        await service.add_translation(element_id, "entity_type", "description", Language.EN_US, "This is an entity")
        await service.add_translation(element_id, "entity_type", "definition", Language.EN_US, "Definition of entity")

        # Check bilingual requirement
        is_bilingual = await service.check_bilingual_requirement(element_id)
        assert is_bilingual

    @pytest.mark.asyncio
    async def test_bilingual_requirement_incomplete(self):
        """Test that elements with incomplete translations fail validation."""
        service = OntologyI18nService()

        element_id = uuid4()

        # Only add zh-CN translations (missing en-US)
        await service.add_translation(element_id, "entity_type", "name", Language.ZH_CN, "实体")
        await service.add_translation(element_id, "entity_type", "description", Language.ZH_CN, "这是一个实体")
        await service.add_translation(element_id, "entity_type", "definition", Language.ZH_CN, "实体的定义")

        # Check bilingual requirement (should fail)
        is_bilingual = await service.check_bilingual_requirement(element_id)
        assert not is_bilingual

    @pytest.mark.asyncio
    async def test_missing_translations_detection(self):
        """Test detection of missing translations."""
        service = OntologyI18nService()

        element_id = uuid4()

        # Add only name and description in en-US (missing definition)
        await service.add_translation(element_id, "entity_type", "name", Language.EN_US, "Entity")
        await service.add_translation(element_id, "entity_type", "description", Language.EN_US, "Description")

        # Get missing translations
        missing = await service.get_missing_translations(element_id, Language.EN_US)

        assert "definition" in missing
        assert "name" not in missing
        assert "description" not in missing

    @pytest.mark.asyncio
    async def test_translation_coverage_calculation(self):
        """Test translation coverage percentage calculation."""
        service = OntologyI18nService()

        element_id = uuid4()

        # Add 2 out of 3 required translations
        await service.add_translation(element_id, "entity_type", "name", Language.EN_US, "Entity")
        await service.add_translation(element_id, "entity_type", "description", Language.EN_US, "Description")

        coverage = await service.get_translation_coverage(element_id, Language.EN_US)

        assert coverage.total_fields == 3
        assert coverage.translated_fields == 2
        assert coverage.missing_fields == 1
        assert coverage.coverage_percentage == pytest.approx(66.7, abs=0.1)
        assert "definition" in coverage.missing_field_names

    @pytest.mark.asyncio
    async def test_ontology_wide_coverage(self):
        """Test translation coverage for entire ontology."""
        service = OntologyI18nService()

        ontology_id = uuid4()
        element1_id = uuid4()
        element2_id = uuid4()

        # Element 1: Full coverage
        await service.add_translation(element1_id, "entity_type", "name", Language.EN_US, "Entity1")
        await service.add_translation(element1_id, "entity_type", "description", Language.EN_US, "Desc1")
        await service.add_translation(element1_id, "entity_type", "definition", Language.EN_US, "Def1")

        # Element 2: Partial coverage (2/3)
        await service.add_translation(element2_id, "entity_type", "name", Language.EN_US, "Entity2")
        await service.add_translation(element2_id, "entity_type", "description", Language.EN_US, "Desc2")

        # Get ontology coverage
        coverage = await service.get_ontology_coverage(
            ontology_id,
            Language.EN_US,
            [element1_id, element2_id]
        )

        # Total: 6 fields, translated: 5 fields
        assert coverage.total_fields == 6
        assert coverage.translated_fields == 5
        assert coverage.coverage_percentage == pytest.approx(83.3, abs=0.1)


# ============================================================================
# Property 10: I18n Display Consistency
# ============================================================================

class TestI18nDisplayConsistency:
    """Test i18n display consistency.

    Property: Translations must be consistent across all supported languages.
    Missing translations should fall back to default language with warning.

    Requirements: 3.2, 3.3, 5.5
    """

    @pytest.mark.asyncio
    async def test_translation_fallback_to_default(self):
        """Test that missing translations fall back to default language."""
        service = OntologyI18nService(default_language=Language.ZH_CN)

        element_id = uuid4()

        # Add only zh-CN translation (default language)
        await service.add_translation(element_id, "entity_type", "name", Language.ZH_CN, "实体")

        # Try to get en-US translation (should fall back to zh-CN)
        value = await service.get_translation(element_id, "name", Language.EN_US, fallback=True)

        assert value == "实体"

    @pytest.mark.asyncio
    async def test_no_fallback_returns_none(self):
        """Test that disabled fallback returns None for missing translations."""
        service = OntologyI18nService(default_language=Language.ZH_CN)

        element_id = uuid4()

        # Add only zh-CN translation
        await service.add_translation(element_id, "entity_type", "name", Language.ZH_CN, "实体")

        # Try to get en-US translation without fallback
        value = await service.get_translation(element_id, "name", Language.EN_US, fallback=False)

        assert value is None

    @pytest.mark.asyncio
    async def test_display_consistency_validation(self):
        """Test validation of display consistency across languages."""
        service = OntologyI18nService()

        element1_id = uuid4()
        element2_id = uuid4()

        # Element 1: Complete in both languages
        await service.add_translation(element1_id, "entity_type", "name", Language.ZH_CN, "实体1")
        await service.add_translation(element1_id, "entity_type", "name", Language.EN_US, "Entity1")

        # Element 2: zh-CN complete, en-US missing
        await service.add_translation(element2_id, "entity_type", "name", Language.ZH_CN, "实体2")
        await service.add_translation(element2_id, "entity_type", "description", Language.ZH_CN, "描述2")

        # Validate consistency
        inconsistencies = await service.validate_display_consistency(
            [element1_id, element2_id],
            Language.ZH_CN,
            Language.EN_US
        )

        # Should find inconsistencies in element2
        assert len(inconsistencies) > 0
        assert any(i["element_id"] == element2_id for i in inconsistencies)

    @pytest.mark.asyncio
    async def test_empty_translation_detection(self):
        """Test detection of empty translations."""
        service = OntologyI18nService()

        element_id = uuid4()

        # Add translation with empty value
        await service.add_translation(element_id, "entity_type", "name", Language.EN_US, "")
        await service.add_translation(element_id, "entity_type", "description", Language.EN_US, "Valid description")

        # Validate consistency
        inconsistencies = await service.validate_display_consistency(
            [element_id],
            Language.EN_US,
            Language.EN_US
        )

        # Should find empty translation
        empty_trans = [i for i in inconsistencies if i.get("type") == "empty_translation"]
        assert len(empty_trans) > 0


# ============================================================================
# Translation Export/Import Tests
# ============================================================================

class TestTranslationExportImport:
    """Test translation export and import functionality.

    Requirements: 3.4
    """

    @pytest.mark.asyncio
    async def test_export_import_json_roundtrip(self):
        """Test JSON export/import round trip."""
        service = OntologyI18nService()

        ontology_id = uuid4()
        element_id = uuid4()

        # Add translations
        await service.add_translation(element_id, "entity_type", "name", Language.EN_US, "Entity")
        await service.add_translation(element_id, "entity_type", "description", Language.EN_US, "Description")

        # Export
        exported = await service.export_translations(ontology_id, Language.EN_US, format="json")

        # Verify export is valid JSON
        data = json.loads(exported)
        assert len(data) == 2
        assert any(item["field_name"] == "name" for item in data)
        assert any(item["field_name"] == "description" for item in data)

        # Clear translations
        service._translations.clear()

        # Import
        count = await service.import_translations(exported, format="json")

        assert count == 2

        # Verify imported translations
        name_value = await service.get_translation(element_id, "name", Language.EN_US, fallback=False)
        desc_value = await service.get_translation(element_id, "description", Language.EN_US, fallback=False)

        assert name_value == "Entity"
        assert desc_value == "Description"

    @pytest.mark.asyncio
    async def test_export_import_csv_roundtrip(self):
        """Test CSV export/import round trip."""
        service = OntologyI18nService()

        ontology_id = uuid4()
        element_id = uuid4()

        # Add translations
        await service.add_translation(element_id, "entity_type", "name", Language.ZH_CN, "实体")

        # Export
        exported = await service.export_translations(ontology_id, Language.ZH_CN, format="csv")

        # Verify export contains CSV header
        assert "element_id" in exported
        assert "field_name" in exported
        assert "实体" in exported

        # Clear translations
        service._translations.clear()

        # Import
        count = await service.import_translations(exported, format="csv")

        assert count == 1

        # Verify imported translation
        value = await service.get_translation(element_id, "name", Language.ZH_CN, fallback=False)
        assert value == "实体"

    @pytest.mark.asyncio
    async def test_batch_add_translations(self):
        """Test batch adding multiple translations."""
        service = OntologyI18nService()

        element_id = uuid4()

        translations = [
            {
                "element_id": element_id,
                "element_type": "entity_type",
                "field_name": "name",
                "language": Language.EN_US,
                "value": "Entity"
            },
            {
                "element_id": element_id,
                "element_type": "entity_type",
                "field_name": "description",
                "language": Language.EN_US,
                "value": "Description"
            },
            {
                "element_id": element_id,
                "element_type": "entity_type",
                "field_name": "definition",
                "language": Language.EN_US,
                "value": "Definition"
            }
        ]

        count = await service.batch_add_translations(translations)

        assert count == 3

        # Verify all added
        coverage = await service.get_translation_coverage(element_id, Language.EN_US)
        assert coverage.coverage_percentage == 100.0


# ============================================================================
# Translation Update Tests
# ============================================================================

class TestTranslationUpdate:
    """Test translation update functionality."""

    @pytest.mark.asyncio
    async def test_update_existing_translation(self):
        """Test updating an existing translation."""
        service = OntologyI18nService()

        element_id = uuid4()

        # Add initial translation
        trans1 = await service.add_translation(
            element_id, "entity_type", "name", Language.EN_US, "Original Name"
        )

        # Update translation
        trans2 = await service.add_translation(
            element_id, "entity_type", "name", Language.EN_US, "Updated Name"
        )

        # Should be the same translation object (updated)
        assert trans1.translation_id == trans2.translation_id
        assert trans2.value == "Updated Name"

        # Verify value is updated
        value = await service.get_translation(element_id, "name", Language.EN_US)
        assert value == "Updated Name"

    @pytest.mark.asyncio
    async def test_mark_needs_review(self):
        """Test marking translation as needing review."""
        service = OntologyI18nService()

        element_id = uuid4()

        # Add translation
        await service.add_translation(element_id, "entity_type", "name", Language.EN_US, "Entity")

        # Mark as needs review
        success = await service.mark_needs_review(element_id, "name", Language.EN_US)
        assert success

        # Get translations needing review
        needing_review = await service.get_translations_needing_review(Language.EN_US)

        assert len(needing_review) == 1
        assert needing_review[0].element_id == element_id
        assert needing_review[0].field_name == "name"
        assert needing_review[0].status == TranslationStatus.NEEDS_REVIEW


# ============================================================================
# Supported Languages Tests
# ============================================================================

class TestSupportedLanguages:
    """Test supported languages functionality."""

    def test_get_supported_languages(self):
        """Test getting list of supported languages."""
        service = OntologyI18nService()

        languages = service.get_supported_languages()

        assert Language.ZH_CN in languages
        assert Language.EN_US in languages
        assert len(languages) >= 2

    @pytest.mark.asyncio
    async def test_multiple_language_support(self):
        """Test support for multiple languages beyond zh-CN and en-US."""
        service = OntologyI18nService()

        element_id = uuid4()

        # Add translations in multiple languages
        await service.add_translation(element_id, "entity_type", "name", Language.ZH_CN, "实体")
        await service.add_translation(element_id, "entity_type", "name", Language.EN_US, "Entity")
        await service.add_translation(element_id, "entity_type", "name", Language.ZH_TW, "實體")
        await service.add_translation(element_id, "entity_type", "name", Language.JA_JP, "エンティティ")

        # Verify all translations
        zh_cn = await service.get_translation(element_id, "name", Language.ZH_CN, fallback=False)
        en_us = await service.get_translation(element_id, "name", Language.EN_US, fallback=False)
        zh_tw = await service.get_translation(element_id, "name", Language.ZH_TW, fallback=False)
        ja_jp = await service.get_translation(element_id, "name", Language.JA_JP, fallback=False)

        assert zh_cn == "实体"
        assert en_us == "Entity"
        assert zh_tw == "實體"
        assert ja_jp == "エンティティ"


# ============================================================================
# Get Element Translations Tests
# ============================================================================

class TestGetElementTranslations:
    """Test getting all translations for an element."""

    @pytest.mark.asyncio
    async def test_get_all_element_translations(self):
        """Test getting all translations for an element."""
        service = OntologyI18nService()

        element_id = uuid4()

        # Add multiple translations
        await service.add_translation(element_id, "entity_type", "name", Language.EN_US, "Entity")
        await service.add_translation(element_id, "entity_type", "description", Language.EN_US, "Description")
        await service.add_translation(element_id, "entity_type", "definition", Language.EN_US, "Definition")

        # Get all translations
        translations = await service.get_element_translations(element_id, Language.EN_US)

        assert len(translations) == 3
        assert translations["name"] == "Entity"
        assert translations["description"] == "Description"
        assert translations["definition"] == "Definition"

    @pytest.mark.asyncio
    async def test_get_element_translations_multiple_languages(self):
        """Test getting translations in specific language."""
        service = OntologyI18nService()

        element_id = uuid4()

        # Add translations in two languages
        await service.add_translation(element_id, "entity_type", "name", Language.ZH_CN, "实体")
        await service.add_translation(element_id, "entity_type", "name", Language.EN_US, "Entity")

        # Get only zh-CN
        zh_translations = await service.get_element_translations(element_id, Language.ZH_CN)
        assert zh_translations["name"] == "实体"

        # Get only en-US
        en_translations = await service.get_element_translations(element_id, Language.EN_US)
        assert en_translations["name"] == "Entity"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
