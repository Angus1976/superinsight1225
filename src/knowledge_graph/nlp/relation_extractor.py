"""
Relation Extractor for Knowledge Graph.

Provides relation extraction between entities using pattern matching and dependency parsing.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass

from ..core.models import EntityType, RelationType, ExtractedEntity, ExtractedRelation
from .text_processor import TextProcessor, get_text_processor
from .entity_extractor import EntityExtractor, get_entity_extractor

logger = logging.getLogger(__name__)

# spaCy for dependency parsing
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


@dataclass
class RelationPattern:
    """Pattern for relation extraction."""
    source_types: List[EntityType]
    target_types: List[EntityType]
    relation_type: RelationType
    patterns: List[str]  # Regex patterns with {source} and {target} placeholders
    confidence: float = 0.8


class RelationExtractor:
    """
    Relation extractor using pattern matching and dependency parsing.

    Extracts relations between entities based on predefined patterns
    and syntactic analysis.
    """

    # Default relation patterns (Chinese)
    DEFAULT_PATTERNS = [
        # Organization relations
        RelationPattern(
            source_types=[EntityType.PERSON],
            target_types=[EntityType.ORGANIZATION],
            relation_type=RelationType.WORKS_FOR,
            patterns=[
                r'{source}.*?(在|就职于|供职于|工作于|任职于|服务于){target}',
                r'{source}.*?是{target}(的)?(员工|职员|成员|雇员)',
                r'{target}(的)?(员工|职员|成员|雇员){source}',
            ],
            confidence=0.85,
        ),
        RelationPattern(
            source_types=[EntityType.PERSON],
            target_types=[EntityType.ORGANIZATION],
            relation_type=RelationType.CREATED_BY,
            patterns=[
                r'{source}.*?(创办|创立|创建|成立|创始){target}',
                r'{target}.*?(由|被){source}(创办|创立|创建|成立)',
            ],
            confidence=0.85,
        ),
        # Location relations
        RelationPattern(
            source_types=[EntityType.ORGANIZATION, EntityType.PERSON],
            target_types=[EntityType.LOCATION],
            relation_type=RelationType.LOCATED_IN,
            patterns=[
                r'{source}.*?(位于|坐落于|在|地址在|总部在|设在){target}',
                r'{target}.*?(有|包括|包含){source}',
            ],
            confidence=0.8,
        ),
        RelationPattern(
            source_types=[EntityType.LOCATION],
            target_types=[EntityType.LOCATION],
            relation_type=RelationType.PART_OF,
            patterns=[
                r'{source}.*?(属于|隶属于|是.*的一部分|位于){target}',
                r'{target}(包括|包含|辖区内有){source}',
            ],
            confidence=0.75,
        ),
        # Social relations
        RelationPattern(
            source_types=[EntityType.PERSON],
            target_types=[EntityType.PERSON],
            relation_type=RelationType.KNOWS,
            patterns=[
                r'{source}.*?(认识|了解|知道|与.*相识){target}',
                r'{source}(和|与|跟){target}(是)?(朋友|同事|同学|熟人)',
            ],
            confidence=0.7,
        ),
        RelationPattern(
            source_types=[EntityType.PERSON],
            target_types=[EntityType.PERSON],
            relation_type=RelationType.COLLABORATES_WITH,
            patterns=[
                r'{source}.*?(与|和|跟){target}(合作|协作|共事|配合)',
                r'{source}.*?{target}.*?(共同|一起|联合|合力)(完成|开发|创建|制作)',
            ],
            confidence=0.75,
        ),
        # Temporal relations
        RelationPattern(
            source_types=[EntityType.EVENT],
            target_types=[EntityType.DATE, EntityType.TIME],
            relation_type=RelationType.DURING,
            patterns=[
                r'{source}.*?(于|在|发生于|举行于){target}',
                r'{target}.*?(举行|发生|进行){source}',
            ],
            confidence=0.85,
        ),
        # Document/task relations
        RelationPattern(
            source_types=[EntityType.DOCUMENT, EntityType.TASK],
            target_types=[EntityType.PROJECT],
            relation_type=RelationType.BELONGS_TO_PROJECT,
            patterns=[
                r'{source}.*?(属于|归属于|隶属于){target}(项目)?',
                r'{target}(项目)?.*?(包含|包括|有){source}',
            ],
            confidence=0.8,
        ),
        RelationPattern(
            source_types=[EntityType.DOCUMENT, EntityType.TASK],
            target_types=[EntityType.PERSON],
            relation_type=RelationType.CREATED_BY,
            patterns=[
                r'{source}.*?(由|被){target}(创建|创作|编写|制作)',
                r'{target}.*?(创建|创作|编写|制作)(了)?{source}',
            ],
            confidence=0.8,
        ),
        # Reference relations
        RelationPattern(
            source_types=[EntityType.DOCUMENT],
            target_types=[EntityType.DOCUMENT],
            relation_type=RelationType.REFERENCES,
            patterns=[
                r'{source}.*?(引用|参考|参见|见|详见){target}',
                r'{source}.*?(基于|根据|依据){target}',
            ],
            confidence=0.75,
        ),
        # Similarity and derivation
        RelationPattern(
            source_types=[EntityType.CONCEPT, EntityType.PRODUCT],
            target_types=[EntityType.CONCEPT, EntityType.PRODUCT],
            relation_type=RelationType.SIMILAR_TO,
            patterns=[
                r'{source}.*?(类似于|类似|像|相似于|相似|如同){target}',
                r'{source}(和|与){target}(相似|类似|相近)',
            ],
            confidence=0.7,
        ),
        RelationPattern(
            source_types=[EntityType.CONCEPT, EntityType.PRODUCT, EntityType.DOCUMENT],
            target_types=[EntityType.CONCEPT, EntityType.PRODUCT, EntityType.DOCUMENT],
            relation_type=RelationType.DERIVED_FROM,
            patterns=[
                r'{source}.*?(源自|来自|派生自|基于|衍生自){target}',
                r'{source}.*?(是|为){target}(的)?(变体|衍生品|派生物|发展)',
            ],
            confidence=0.75,
        ),
    ]

    def __init__(
        self,
        patterns: Optional[List[RelationPattern]] = None,
        use_dependency_parsing: bool = True,
        confidence_threshold: float = 0.6,
        max_distance: int = 100,
    ):
        """
        Initialize RelationExtractor.

        Args:
            patterns: Custom relation patterns
            use_dependency_parsing: Whether to use spaCy dependency parsing
            confidence_threshold: Minimum confidence threshold
            max_distance: Maximum character distance between entities
        """
        self.patterns = patterns or self.DEFAULT_PATTERNS
        self.use_dependency_parsing = use_dependency_parsing
        self.confidence_threshold = confidence_threshold
        self.max_distance = max_distance

        self._nlp = None
        self._entity_extractor: Optional[EntityExtractor] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the extractor."""
        if self._initialized:
            return

        # Get entity extractor
        self._entity_extractor = get_entity_extractor()

        # Load spaCy model for dependency parsing
        if self.use_dependency_parsing and SPACY_AVAILABLE:
            try:
                self._nlp = spacy.load("zh_core_web_sm")
                logger.info("Loaded spaCy model for dependency parsing")
            except OSError:
                logger.warning("spaCy model not found, using pattern-based extraction only")
                self._nlp = None

        self._initialized = True
        logger.info("RelationExtractor initialized")

    def extract(
        self,
        text: str,
        entities: Optional[List[ExtractedEntity]] = None,
        relation_types: Optional[List[RelationType]] = None,
    ) -> List[ExtractedRelation]:
        """
        Extract relations from text.

        Args:
            text: Input text
            entities: Pre-extracted entities (will extract if not provided)
            relation_types: Filter to specific relation types

        Returns:
            List of extracted relations
        """
        if not self._initialized:
            self.initialize()

        if not text or not text.strip():
            return []

        # Extract entities if not provided
        if entities is None:
            entities = self._entity_extractor.extract(text)

        if len(entities) < 2:
            # Need at least 2 entities to form a relation
            return []

        relations = []

        # Pattern-based extraction
        pattern_relations = self._extract_with_patterns(text, entities)
        relations.extend(pattern_relations)

        # Dependency parsing extraction
        if self.use_dependency_parsing and self._nlp is not None:
            dep_relations = self._extract_with_dependency(text, entities)
            relations = self._merge_relations(relations, dep_relations)

        # Proximity-based extraction (fallback)
        if not relations:
            proximity_relations = self._extract_by_proximity(text, entities)
            relations.extend(proximity_relations)

        # Filter by relation types
        if relation_types:
            relations = [r for r in relations if r.relation_type in relation_types]

        # Filter by confidence
        relations = [r for r in relations if r.confidence >= self.confidence_threshold]

        # Remove duplicates
        relations = self._deduplicate_relations(relations)

        return relations

    def extract_batch(
        self,
        texts: List[str],
        entities_list: Optional[List[List[ExtractedEntity]]] = None,
    ) -> List[List[ExtractedRelation]]:
        """
        Extract relations from multiple texts.

        Args:
            texts: List of input texts
            entities_list: Pre-extracted entities for each text

        Returns:
            List of relation lists for each text
        """
        if entities_list is None:
            entities_list = [None] * len(texts)

        return [
            self.extract(text, entities)
            for text, entities in zip(texts, entities_list)
        ]

    def _extract_with_patterns(
        self,
        text: str,
        entities: List[ExtractedEntity],
    ) -> List[ExtractedRelation]:
        """Extract relations using pattern matching."""
        relations = []

        # Group entities by type
        entities_by_type: Dict[EntityType, List[ExtractedEntity]] = {}
        for entity in entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity)

        # Try each pattern
        for pattern_def in self.patterns:
            # Get candidate source entities
            source_entities = []
            for source_type in pattern_def.source_types:
                source_entities.extend(entities_by_type.get(source_type, []))

            # Get candidate target entities
            target_entities = []
            for target_type in pattern_def.target_types:
                target_entities.extend(entities_by_type.get(target_type, []))

            # Try each source-target pair
            for source in source_entities:
                for target in target_entities:
                    if source.text == target.text:
                        continue

                    # Check distance
                    distance = abs(source.start_char - target.start_char)
                    if distance > self.max_distance:
                        continue

                    # Try each pattern
                    for pattern_str in pattern_def.patterns:
                        # Build regex with entity placeholders
                        regex_pattern = pattern_str.replace(
                            '{source}', re.escape(source.text)
                        ).replace(
                            '{target}', re.escape(target.text)
                        )

                        try:
                            if re.search(regex_pattern, text):
                                # Extract evidence text
                                min_pos = min(source.start_char, target.start_char)
                                max_pos = max(source.end_char, target.end_char)
                                evidence = text[max(0, min_pos-10):min(len(text), max_pos+10)]

                                relations.append(ExtractedRelation(
                                    source_entity=source,
                                    target_entity=target,
                                    relation_type=pattern_def.relation_type,
                                    confidence=pattern_def.confidence,
                                    evidence=evidence,
                                    metadata={
                                        "source": "pattern",
                                        "pattern": pattern_str,
                                    },
                                ))
                                break  # Found a match, no need to try other patterns
                        except re.error as e:
                            logger.warning(f"Invalid regex pattern: {e}")

        return relations

    def _extract_with_dependency(
        self,
        text: str,
        entities: List[ExtractedEntity],
    ) -> List[ExtractedRelation]:
        """Extract relations using dependency parsing."""
        relations = []

        try:
            doc = self._nlp(text)

            # Map entity positions to spacy tokens
            entity_token_map: Dict[int, ExtractedEntity] = {}
            for entity in entities:
                for token in doc:
                    if token.idx >= entity.start_char and token.idx < entity.end_char:
                        entity_token_map[token.i] = entity
                        break

            # Analyze dependencies
            for token in doc:
                if token.i in entity_token_map:
                    source_entity = entity_token_map[token.i]

                    # Check head token
                    if token.head.i in entity_token_map and token.head.i != token.i:
                        target_entity = entity_token_map[token.head.i]

                        # Infer relation type from dependency
                        relation_type = self._dep_to_relation(token.dep_)
                        if relation_type:
                            relations.append(ExtractedRelation(
                                source_entity=source_entity,
                                target_entity=target_entity,
                                relation_type=relation_type,
                                confidence=0.7,
                                evidence=token.sent.text if token.sent else text,
                                metadata={
                                    "source": "dependency",
                                    "dep_label": token.dep_,
                                },
                            ))

        except Exception as e:
            logger.error(f"Dependency parsing failed: {e}")

        return relations

    def _extract_by_proximity(
        self,
        text: str,
        entities: List[ExtractedEntity],
    ) -> List[ExtractedRelation]:
        """Extract relations based on entity proximity."""
        relations = []

        # Sort entities by position
        sorted_entities = sorted(entities, key=lambda e: e.start_char)

        # Check adjacent entity pairs
        for i in range(len(sorted_entities) - 1):
            source = sorted_entities[i]
            target = sorted_entities[i + 1]

            # Check distance
            distance = target.start_char - source.end_char
            if distance > self.max_distance:
                continue

            # Get text between entities
            between_text = text[source.end_char:target.start_char].strip()

            # Infer relation from context
            relation_type = self._infer_relation_from_context(
                source, target, between_text
            )

            if relation_type:
                relations.append(ExtractedRelation(
                    source_entity=source,
                    target_entity=target,
                    relation_type=relation_type,
                    confidence=0.5,  # Lower confidence for proximity-based
                    evidence=text[source.start_char:target.end_char],
                    metadata={
                        "source": "proximity",
                        "distance": distance,
                    },
                ))

        return relations

    def _dep_to_relation(self, dep_label: str) -> Optional[RelationType]:
        """Map dependency label to relation type."""
        dep_relation_map = {
            "nsubj": RelationType.CREATED_BY,
            "dobj": RelationType.RELATED_TO,
            "pobj": RelationType.RELATED_TO,
            "nmod": RelationType.PART_OF,
            "compound": RelationType.PART_OF,
            "appos": RelationType.RELATED_TO,
            "conj": RelationType.RELATED_TO,
        }
        return dep_relation_map.get(dep_label)

    def _infer_relation_from_context(
        self,
        source: ExtractedEntity,
        target: ExtractedEntity,
        between_text: str,
    ) -> Optional[RelationType]:
        """Infer relation type from context between entities."""
        between_lower = between_text.lower()

        # Check for common relation indicators
        if any(kw in between_lower for kw in ["的", "之"]):
            if source.entity_type == EntityType.PERSON and target.entity_type == EntityType.ORGANIZATION:
                return RelationType.WORKS_FOR
            return RelationType.PART_OF

        if any(kw in between_lower for kw in ["在", "于", "位于"]):
            if target.entity_type == EntityType.LOCATION:
                return RelationType.LOCATED_IN

        if any(kw in between_lower for kw in ["和", "与", "跟"]):
            if source.entity_type == target.entity_type:
                return RelationType.RELATED_TO

        return RelationType.RELATED_TO  # Default fallback

    def _merge_relations(
        self,
        existing: List[ExtractedRelation],
        new: List[ExtractedRelation],
    ) -> List[ExtractedRelation]:
        """Merge relation lists, avoiding duplicates."""
        merged = list(existing)
        existing_keys = {
            (r.source_entity.text, r.target_entity.text, r.relation_type)
            for r in existing
        }

        for relation in new:
            key = (relation.source_entity.text, relation.target_entity.text, relation.relation_type)
            if key not in existing_keys:
                merged.append(relation)
                existing_keys.add(key)

        return merged

    def _deduplicate_relations(
        self,
        relations: List[ExtractedRelation],
    ) -> List[ExtractedRelation]:
        """Remove duplicate relations, keeping highest confidence."""
        seen: Dict[tuple, ExtractedRelation] = {}

        for relation in relations:
            key = (
                relation.source_entity.text,
                relation.target_entity.text,
                relation.relation_type,
            )

            if key not in seen or relation.confidence > seen[key].confidence:
                seen[key] = relation

        return list(seen.values())

    def add_pattern(self, pattern: RelationPattern) -> None:
        """Add a custom extraction pattern."""
        self.patterns.append(pattern)

    def get_relation_statistics(self, relations: List[ExtractedRelation]) -> Dict[str, Any]:
        """Get statistics about extracted relations."""
        by_type = {}
        by_source = {}
        confidence_sum = 0.0

        for relation in relations:
            # Count by type
            type_name = relation.relation_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

            # Count by source
            source = relation.metadata.get("source", "unknown")
            by_source[source] = by_source.get(source, 0) + 1

            # Sum confidence
            confidence_sum += relation.confidence

        return {
            "total_count": len(relations),
            "by_type": by_type,
            "by_source": by_source,
            "avg_confidence": confidence_sum / len(relations) if relations else 0.0,
        }


# Global instance
_relation_extractor: Optional[RelationExtractor] = None


def get_relation_extractor() -> RelationExtractor:
    """Get or create global RelationExtractor instance."""
    global _relation_extractor

    if _relation_extractor is None:
        from src.config.settings import settings

        _relation_extractor = RelationExtractor(
            confidence_threshold=settings.knowledge_graph.relation_confidence_threshold,
        )
        _relation_extractor.initialize()

    return _relation_extractor
