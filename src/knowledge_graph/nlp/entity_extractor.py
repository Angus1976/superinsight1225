"""
Entity Extractor for Knowledge Graph.

Provides named entity recognition using spaCy and rule-based matching.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime

from ..core.models import EntityType, ExtractedEntity
from .text_processor import TextProcessor, get_text_processor, Token

logger = logging.getLogger(__name__)

# spaCy for NER
try:
    import spacy
    from spacy.tokens import Doc, Span
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not installed. Install with: pip install spacy")


class EntityExtractor:
    """
    Entity extractor using spaCy and rule-based matching.

    Supports Chinese named entity recognition for persons, organizations,
    locations, dates, and custom entity types.
    """

    # spaCy entity type to EntityType mapping
    SPACY_ENTITY_MAPPING = {
        "PERSON": EntityType.PERSON,
        "PER": EntityType.PERSON,
        "ORG": EntityType.ORGANIZATION,
        "GPE": EntityType.LOCATION,
        "LOC": EntityType.LOCATION,
        "DATE": EntityType.DATE,
        "TIME": EntityType.TIME,
        "MONEY": EntityType.MONEY,
        "PERCENT": EntityType.PERCENT,
        "PRODUCT": EntityType.PRODUCT,
        "EVENT": EntityType.EVENT,
        "WORK_OF_ART": EntityType.CONCEPT,
        "LAW": EntityType.CONCEPT,
        "LANGUAGE": EntityType.CONCEPT,
        "NORP": EntityType.CONCEPT,  # Nationalities, religious, political groups
        "FAC": EntityType.LOCATION,  # Facilities
        "CARDINAL": EntityType.CUSTOM,
        "ORDINAL": EntityType.CUSTOM,
        "QUANTITY": EntityType.CUSTOM,
    }

    # Common patterns for rule-based extraction
    PATTERNS = {
        EntityType.DATE: [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{4}/\d{2}/\d{2}',
            r'\d{1,2}月\d{1,2}日',
            r'今天|昨天|明天|前天|后天',
            r'本周|上周|下周|本月|上月|下月',
            r'今年|去年|明年|前年',
        ],
        EntityType.TIME: [
            r'\d{1,2}:\d{2}(:\d{2})?',
            r'\d{1,2}点(\d{1,2}分)?',
            r'上午|下午|晚上|早上|中午|凌晨',
        ],
        EntityType.MONEY: [
            r'[\d,]+\.?\d*\s*(元|万元|亿元|美元|人民币|RMB|USD|CNY)',
            r'\$[\d,]+\.?\d*',
            r'¥[\d,]+\.?\d*',
        ],
        EntityType.PERCENT: [
            r'\d+\.?\d*%',
            r'百分之\d+\.?\d*',
        ],
    }

    def __init__(
        self,
        spacy_model: str = "zh_core_web_sm",
        use_rule_based: bool = True,
        confidence_threshold: float = 0.7,
        custom_patterns: Optional[Dict[EntityType, List[str]]] = None,
    ):
        """
        Initialize EntityExtractor.

        Args:
            spacy_model: Name of the spaCy model to use
            use_rule_based: Whether to use rule-based extraction as fallback
            confidence_threshold: Minimum confidence threshold
            custom_patterns: Additional regex patterns for extraction
        """
        self.spacy_model = spacy_model
        self.use_rule_based = use_rule_based
        self.confidence_threshold = confidence_threshold
        self.custom_patterns = custom_patterns or {}

        self._nlp = None
        self._text_processor: Optional[TextProcessor] = None
        self._initialized = False

        # Combine default and custom patterns
        self._patterns = {**self.PATTERNS, **self.custom_patterns}

    def initialize(self) -> None:
        """Initialize the extractor."""
        if self._initialized:
            return

        # Initialize text processor
        self._text_processor = get_text_processor()

        # Load spaCy model
        if SPACY_AVAILABLE:
            try:
                self._nlp = spacy.load(self.spacy_model)
                logger.info(f"Loaded spaCy model: {self.spacy_model}")
            except OSError:
                logger.warning(f"spaCy model '{self.spacy_model}' not found. "
                             f"Install with: python -m spacy download {self.spacy_model}")
                self._nlp = None
        else:
            logger.warning("spaCy not available, using rule-based extraction only")

        self._initialized = True
        logger.info("EntityExtractor initialized")

    def extract(self, text: str, entity_types: Optional[List[EntityType]] = None) -> List[ExtractedEntity]:
        """
        Extract entities from text.

        Args:
            text: Input text
            entity_types: Filter to specific entity types

        Returns:
            List of extracted entities
        """
        if not self._initialized:
            self.initialize()

        if not text or not text.strip():
            return []

        entities = []

        # Use spaCy if available
        if self._nlp is not None:
            spacy_entities = self._extract_with_spacy(text)
            entities.extend(spacy_entities)

        # Use rule-based extraction
        if self.use_rule_based:
            rule_entities = self._extract_with_rules(text)
            # Merge with existing, avoiding duplicates
            entities = self._merge_entities(entities, rule_entities)

        # Extract from POS tags (nouns as potential entities)
        if self._text_processor:
            pos_entities = self._extract_from_pos(text)
            entities = self._merge_entities(entities, pos_entities)

        # Filter by entity types if specified
        if entity_types:
            entities = [e for e in entities if e.entity_type in entity_types]

        # Filter by confidence
        entities = [e for e in entities if e.confidence >= self.confidence_threshold]

        # Sort by position
        entities.sort(key=lambda e: e.start_char)

        # Deduplicate overlapping entities
        entities = self._remove_overlapping(entities)

        return entities

    def extract_batch(self, texts: List[str], entity_types: Optional[List[EntityType]] = None) -> List[List[ExtractedEntity]]:
        """
        Extract entities from multiple texts.

        Args:
            texts: List of input texts
            entity_types: Filter to specific entity types

        Returns:
            List of entity lists for each text
        """
        return [self.extract(text, entity_types) for text in texts]

    def _extract_with_spacy(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using spaCy NER."""
        entities = []

        try:
            doc = self._nlp(text)

            for ent in doc.ents:
                entity_type = self.SPACY_ENTITY_MAPPING.get(ent.label_, EntityType.CUSTOM)

                entities.append(ExtractedEntity(
                    text=ent.text,
                    entity_type=entity_type,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    confidence=0.85,  # spaCy default confidence
                    normalized_name=ent.text.strip(),
                    metadata={
                        "source": "spacy",
                        "label": ent.label_,
                    },
                ))
        except Exception as e:
            logger.error(f"spaCy extraction failed: {e}")

        return entities

    def _extract_with_rules(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using regex patterns."""
        entities = []

        for entity_type, patterns in self._patterns.items():
            for pattern in patterns:
                try:
                    for match in re.finditer(pattern, text):
                        entities.append(ExtractedEntity(
                            text=match.group(),
                            entity_type=entity_type,
                            start_char=match.start(),
                            end_char=match.end(),
                            confidence=0.9,  # High confidence for regex matches
                            normalized_name=match.group().strip(),
                            metadata={
                                "source": "rule",
                                "pattern": pattern,
                            },
                        ))
                except re.error as e:
                    logger.error(f"Invalid regex pattern '{pattern}': {e}")

        return entities

    def _extract_from_pos(self, text: str) -> List[ExtractedEntity]:
        """Extract potential entities from POS tags."""
        entities = []

        processed = self._text_processor.process(text)

        # Look for proper nouns and named entities
        for token in processed.tokens:
            if token.pos == "PROPN" and len(token.text) >= 2:
                # Proper noun - likely a named entity
                entity_type = self._infer_entity_type(token.text)

                entities.append(ExtractedEntity(
                    text=token.text,
                    entity_type=entity_type,
                    start_char=token.start,
                    end_char=token.end,
                    confidence=0.6,  # Lower confidence for POS-based
                    normalized_name=token.text.strip(),
                    metadata={
                        "source": "pos",
                        "pos_tag": token.pos,
                    },
                ))

        # Look for noun phrases
        noun_phrases = self._text_processor.get_noun_phrases(processed.tokens)
        for phrase in noun_phrases:
            # Find phrase position
            start = text.find(phrase)
            if start >= 0:
                entity_type = self._infer_entity_type(phrase)
                entities.append(ExtractedEntity(
                    text=phrase,
                    entity_type=entity_type,
                    start_char=start,
                    end_char=start + len(phrase),
                    confidence=0.5,  # Even lower for noun phrases
                    normalized_name=phrase.strip(),
                    metadata={
                        "source": "noun_phrase",
                    },
                ))

        return entities

    def _infer_entity_type(self, text: str) -> EntityType:
        """
        Infer entity type from text content.

        Args:
            text: Entity text

        Returns:
            Inferred EntityType
        """
        # Organization indicators
        org_suffixes = ["公司", "集团", "银行", "企业", "机构", "组织", "协会", "委员会", "部门", "学院", "大学", "医院"]
        if any(text.endswith(suffix) for suffix in org_suffixes):
            return EntityType.ORGANIZATION

        # Location indicators
        loc_suffixes = ["省", "市", "县", "区", "镇", "村", "街道", "路", "国", "洲"]
        if any(text.endswith(suffix) for suffix in loc_suffixes):
            return EntityType.LOCATION

        # Product indicators
        product_patterns = ["产品", "系统", "软件", "平台", "服务", "版本"]
        if any(p in text for p in product_patterns):
            return EntityType.PRODUCT

        # Default to concept
        return EntityType.CONCEPT

    def _merge_entities(self, existing: List[ExtractedEntity], new: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """
        Merge two entity lists, avoiding duplicates.

        Args:
            existing: Existing entities
            new: New entities to merge

        Returns:
            Merged entity list
        """
        merged = list(existing)
        existing_spans = {(e.start_char, e.end_char, e.text) for e in existing}

        for entity in new:
            key = (entity.start_char, entity.end_char, entity.text)
            if key not in existing_spans:
                merged.append(entity)
                existing_spans.add(key)

        return merged

    def _remove_overlapping(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """
        Remove overlapping entities, keeping higher confidence ones.

        Args:
            entities: List of entities (should be sorted by start position)

        Returns:
            Non-overlapping entities
        """
        if not entities:
            return []

        # Sort by confidence descending, then by length descending
        sorted_entities = sorted(entities, key=lambda e: (-e.confidence, -(e.end_char - e.start_char)))

        result = []
        used_ranges: List[Tuple[int, int]] = []

        for entity in sorted_entities:
            # Check if overlaps with any used range
            overlaps = False
            for start, end in used_ranges:
                if not (entity.end_char <= start or entity.start_char >= end):
                    overlaps = True
                    break

            if not overlaps:
                result.append(entity)
                used_ranges.append((entity.start_char, entity.end_char))

        # Re-sort by position
        result.sort(key=lambda e: e.start_char)

        return result

    def add_pattern(self, entity_type: EntityType, pattern: str) -> None:
        """
        Add a custom extraction pattern.

        Args:
            entity_type: Entity type for this pattern
            pattern: Regex pattern
        """
        if entity_type not in self._patterns:
            self._patterns[entity_type] = []
        self._patterns[entity_type].append(pattern)

    def get_entity_statistics(self, entities: List[ExtractedEntity]) -> Dict[str, Any]:
        """
        Get statistics about extracted entities.

        Args:
            entities: List of extracted entities

        Returns:
            Statistics dictionary
        """
        by_type = {}
        by_source = {}
        confidence_sum = 0.0

        for entity in entities:
            # Count by type
            type_name = entity.entity_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

            # Count by source
            source = entity.metadata.get("source", "unknown")
            by_source[source] = by_source.get(source, 0) + 1

            # Sum confidence
            confidence_sum += entity.confidence

        return {
            "total_count": len(entities),
            "by_type": by_type,
            "by_source": by_source,
            "avg_confidence": confidence_sum / len(entities) if entities else 0.0,
            "unique_texts": len(set(e.text for e in entities)),
        }


# Global instance
_entity_extractor: Optional[EntityExtractor] = None


def get_entity_extractor() -> EntityExtractor:
    """Get or create global EntityExtractor instance."""
    global _entity_extractor

    if _entity_extractor is None:
        from src.config.settings import settings

        _entity_extractor = EntityExtractor(
            spacy_model=settings.knowledge_graph.spacy_model,
            confidence_threshold=settings.knowledge_graph.entity_confidence_threshold,
        )
        _entity_extractor.initialize()

    return _entity_extractor
