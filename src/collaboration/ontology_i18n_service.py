"""Ontology I18n Service for multi-language support.

This module provides internationalization support for ontology elements:
- Translation management for ontology elements
- Multi-language support (zh-CN, en-US, extensible)
- Translation fallback mechanism
- Translation export/import
- Language-specific validation rule selection

Requirements:
- 3.1: Bilingual definition requirement (zh-CN, en-US)
- 3.2: I18n display consistency
- 3.3: Translation fallback mechanism
- 3.4: Translation export/import
- 3.5: Language-specific validation rule selection
"""

import asyncio
import json
import csv
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
from io import StringIO


class Language(str, Enum):
    """Supported languages."""
    ZH_CN = "zh-CN"
    EN_US = "en-US"
    ZH_TW = "zh-TW"
    JA_JP = "ja-JP"
    KO_KR = "ko-KR"


class TranslationStatus(str, Enum):
    """Translation status."""
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"
    NEEDS_REVIEW = "needs_review"


@dataclass
class Translation:
    """Translation for an ontology element field."""
    translation_id: UUID = field(default_factory=uuid4)
    element_id: UUID = field(default_factory=uuid4)
    element_type: str = ""  # "entity_type", "relation_type", "attribute"
    field_name: str = ""  # "name", "description", "definition"
    language: Language = Language.ZH_CN
    value: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None
    status: TranslationStatus = TranslationStatus.COMPLETE


@dataclass
class TranslationCoverage:
    """Translation coverage statistics for an element or ontology."""
    element_id: Optional[UUID] = None
    ontology_id: Optional[UUID] = None
    language: Language = Language.EN_US
    total_fields: int = 0
    translated_fields: int = 0
    missing_fields: int = 0
    coverage_percentage: float = 0.0
    missing_field_names: List[str] = field(default_factory=list)


@dataclass
class OntologyElement:
    """Ontology element with translations."""
    element_id: UUID = field(default_factory=uuid4)
    element_type: str = ""
    fields: Dict[str, Any] = field(default_factory=dict)  # Base language fields
    translations: Dict[Language, Dict[str, str]] = field(default_factory=dict)


class OntologyI18nService:
    """Service for managing ontology translations."""

    def __init__(self, default_language: Language = Language.ZH_CN):
        """Initialize i18n service.

        Args:
            default_language: Default language for fallback
        """
        self._translations: Dict[UUID, List[Translation]] = {}  # element_id -> [Translation]
        self._elements: Dict[UUID, OntologyElement] = {}  # element_id -> OntologyElement
        self._lock = asyncio.Lock()
        self._default_language = default_language

        # Required fields for bilingual definition
        self._required_bilingual_fields = {"name", "description", "definition"}

    async def add_translation(
        self,
        element_id: UUID,
        element_type: str,
        field_name: str,
        language: Language,
        value: str,
        created_by: Optional[UUID] = None
    ) -> Translation:
        """Add or update a translation for an ontology element field.

        Args:
            element_id: Element ID
            element_type: Type of element
            field_name: Field name to translate
            language: Target language
            value: Translation value
            created_by: User creating the translation

        Returns:
            Created or updated translation
        """
        async with self._lock:
            translation = Translation(
                element_id=element_id,
                element_type=element_type,
                field_name=field_name,
                language=language,
                value=value,
                created_by=created_by
            )

            if element_id not in self._translations:
                self._translations[element_id] = []

            # Check if translation exists, update if so
            existing = next(
                (t for t in self._translations[element_id]
                 if t.field_name == field_name and t.language == language),
                None
            )

            if existing:
                existing.value = value
                existing.updated_at = datetime.utcnow()
                existing.status = TranslationStatus.COMPLETE
                return existing
            else:
                self._translations[element_id].append(translation)
                return translation

    async def get_translation(
        self,
        element_id: UUID,
        field_name: str,
        language: Language,
        fallback: bool = True
    ) -> Optional[str]:
        """Get translation for an element field.

        Args:
            element_id: Element ID
            field_name: Field name
            language: Target language
            fallback: Whether to fall back to default language if translation missing

        Returns:
            Translation value or None
        """
        async with self._lock:
            translations = self._translations.get(element_id, [])

            # Try to find exact language match
            translation = next(
                (t for t in translations
                 if t.field_name == field_name and t.language == language),
                None
            )

            if translation:
                return translation.value

            # Fallback to default language if enabled
            if fallback and language != self._default_language:
                default_translation = next(
                    (t for t in translations
                     if t.field_name == field_name and t.language == self._default_language),
                    None
                )
                if default_translation:
                    return default_translation.value

            return None

    async def check_bilingual_requirement(
        self,
        element_id: UUID,
        required_languages: Optional[Set[Language]] = None
    ) -> bool:
        """Check if an element meets bilingual definition requirement.

        Args:
            element_id: Element ID
            required_languages: Languages required (default: zh-CN, en-US)

        Returns:
            True if all required fields are translated to all required languages
        """
        if required_languages is None:
            required_languages = {Language.ZH_CN, Language.EN_US}

        async with self._lock:
            translations = self._translations.get(element_id, [])

            for language in required_languages:
                for field_name in self._required_bilingual_fields:
                    has_translation = any(
                        t.field_name == field_name and t.language == language
                        for t in translations
                    )
                    if not has_translation:
                        return False

            return True

    async def get_missing_translations(
        self,
        element_id: UUID,
        language: Language
    ) -> List[str]:
        """Get list of missing translations for an element.

        Args:
            element_id: Element ID
            language: Target language

        Returns:
            List of field names missing translations
        """
        async with self._lock:
            translations = self._translations.get(element_id, [])
            translated_fields = {
                t.field_name for t in translations if t.language == language
            }

            missing = []
            for field_name in self._required_bilingual_fields:
                if field_name not in translated_fields:
                    missing.append(field_name)

            return missing

    async def get_translation_coverage(
        self,
        element_id: UUID,
        language: Language
    ) -> TranslationCoverage:
        """Get translation coverage statistics for an element.

        Args:
            element_id: Element ID
            language: Target language

        Returns:
            Translation coverage statistics
        """
        async with self._lock:
            translations = self._translations.get(element_id, [])
            translated_fields = {
                t.field_name for t in translations
                if t.language == language and t.status == TranslationStatus.COMPLETE
            }

            total = len(self._required_bilingual_fields)
            translated = len(translated_fields & self._required_bilingual_fields)
            missing = total - translated

            missing_field_names = list(self._required_bilingual_fields - translated_fields)

            return TranslationCoverage(
                element_id=element_id,
                language=language,
                total_fields=total,
                translated_fields=translated,
                missing_fields=missing,
                coverage_percentage=round((translated / total) * 100, 1) if total > 0 else 0.0,
                missing_field_names=missing_field_names
            )

    async def export_translations(
        self,
        ontology_id: UUID,
        language: Language,
        format: str = "json"
    ) -> str:
        """Export translations for an ontology.

        Args:
            ontology_id: Ontology ID
            language: Language to export
            format: Export format ("json" or "csv")

        Returns:
            Exported data as string
        """
        async with self._lock:
            # Collect all translations for this language
            export_data = []

            for element_id, translations in self._translations.items():
                for translation in translations:
                    if translation.language == language:
                        export_data.append({
                            "element_id": str(element_id),
                            "element_type": translation.element_type,
                            "field_name": translation.field_name,
                            "language": translation.language.value,
                            "value": translation.value,
                            "status": translation.status.value,
                            "updated_at": translation.updated_at.isoformat()
                        })

            if format == "json":
                return json.dumps(export_data, indent=2, ensure_ascii=False)
            elif format == "csv":
                output = StringIO()
                if export_data:
                    writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
                    writer.writeheader()
                    writer.writerows(export_data)
                return output.getvalue()
            else:
                raise ValueError(f"Unsupported format: {format}")

    async def import_translations(
        self,
        data: str,
        format: str = "json",
        created_by: Optional[UUID] = None
    ) -> int:
        """Import translations from exported data.

        Args:
            data: Imported data string
            format: Import format ("json" or "csv")
            created_by: User importing the translations

        Returns:
            Number of translations imported
        """
        async with self._lock:
            count = 0

            if format == "json":
                import_data = json.loads(data)
            elif format == "csv":
                reader = csv.DictReader(StringIO(data))
                import_data = list(reader)
            else:
                raise ValueError(f"Unsupported format: {format}")

            for item in import_data:
                element_id = UUID(item["element_id"])
                element_type = item["element_type"]
                field_name = item["field_name"]
                language = Language(item["language"])
                value = item["value"]

                await self.add_translation(
                    element_id=element_id,
                    element_type=element_type,
                    field_name=field_name,
                    language=language,
                    value=value,
                    created_by=created_by
                )
                count += 1

            return count

    async def batch_add_translations(
        self,
        translations: List[Dict[str, Any]],
        created_by: Optional[UUID] = None
    ) -> int:
        """Batch add multiple translations.

        Args:
            translations: List of translation dicts
            created_by: User creating the translations

        Returns:
            Number of translations added
        """
        count = 0
        for trans_data in translations:
            await self.add_translation(
                element_id=trans_data["element_id"],
                element_type=trans_data["element_type"],
                field_name=trans_data["field_name"],
                language=trans_data["language"],
                value=trans_data["value"],
                created_by=created_by
            )
            count += 1

        return count

    async def get_element_translations(
        self,
        element_id: UUID,
        language: Optional[Language] = None
    ) -> Dict[str, str]:
        """Get all translations for an element.

        Args:
            element_id: Element ID
            language: Optional language filter

        Returns:
            Dictionary mapping field names to translated values
        """
        async with self._lock:
            translations = self._translations.get(element_id, [])

            if language:
                translations = [t for t in translations if t.language == language]

            return {t.field_name: t.value for t in translations}

    async def get_ontology_coverage(
        self,
        ontology_id: UUID,
        language: Language,
        element_ids: List[UUID]
    ) -> TranslationCoverage:
        """Get translation coverage for an entire ontology.

        Args:
            ontology_id: Ontology ID
            language: Target language
            element_ids: List of element IDs in the ontology

        Returns:
            Aggregated translation coverage
        """
        async with self._lock:
            total_fields = 0
            translated_fields = 0

            for element_id in element_ids:
                coverage = await self.get_translation_coverage(element_id, language)
                total_fields += coverage.total_fields
                translated_fields += coverage.translated_fields

            missing_fields = total_fields - translated_fields

            return TranslationCoverage(
                ontology_id=ontology_id,
                language=language,
                total_fields=total_fields,
                translated_fields=translated_fields,
                missing_fields=missing_fields,
                coverage_percentage=round((translated_fields / total_fields) * 100, 1) if total_fields > 0 else 0.0
            )

    async def mark_needs_review(
        self,
        element_id: UUID,
        field_name: str,
        language: Language
    ) -> bool:
        """Mark a translation as needing review.

        Args:
            element_id: Element ID
            field_name: Field name
            language: Language

        Returns:
            True if successful
        """
        async with self._lock:
            translations = self._translations.get(element_id, [])
            translation = next(
                (t for t in translations
                 if t.field_name == field_name and t.language == language),
                None
            )

            if translation:
                translation.status = TranslationStatus.NEEDS_REVIEW
                translation.updated_at = datetime.utcnow()
                return True

            return False

    async def get_translations_needing_review(
        self,
        language: Optional[Language] = None
    ) -> List[Translation]:
        """Get all translations that need review.

        Args:
            language: Optional language filter

        Returns:
            List of translations needing review
        """
        async with self._lock:
            needing_review = []

            for translations in self._translations.values():
                for translation in translations:
                    if translation.status == TranslationStatus.NEEDS_REVIEW:
                        if language is None or translation.language == language:
                            needing_review.append(translation)

            return needing_review

    def get_supported_languages(self) -> List[Language]:
        """Get list of supported languages.

        Returns:
            List of supported languages
        """
        return list(Language)

    async def validate_display_consistency(
        self,
        element_ids: List[UUID],
        primary_language: Language,
        secondary_language: Language
    ) -> List[Dict[str, Any]]:
        """Validate that translations are consistent across languages.

        Args:
            element_ids: List of element IDs to validate
            primary_language: Primary language
            secondary_language: Secondary language

        Returns:
            List of inconsistencies found
        """
        inconsistencies = []

        async with self._lock:
            for element_id in element_ids:
                primary_trans = await self.get_element_translations(element_id, primary_language)
                secondary_trans = await self.get_element_translations(element_id, secondary_language)

                # Check for fields in primary but missing in secondary
                missing_in_secondary = set(primary_trans.keys()) - set(secondary_trans.keys())
                if missing_in_secondary:
                    inconsistencies.append({
                        "element_id": element_id,
                        "type": "missing_translation",
                        "language": secondary_language.value,
                        "fields": list(missing_in_secondary)
                    })

                # Check for empty values in secondary
                for field, value in secondary_trans.items():
                    if not value or value.strip() == "":
                        inconsistencies.append({
                            "element_id": element_id,
                            "type": "empty_translation",
                            "language": secondary_language.value,
                            "field": field
                        })

        return inconsistencies
