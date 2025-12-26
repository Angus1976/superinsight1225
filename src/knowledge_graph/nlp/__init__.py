"""
NLP module for Knowledge Graph.

Provides text processing, entity extraction, and relation extraction.
"""

from .text_processor import TextProcessor, get_text_processor
from .entity_extractor import EntityExtractor, get_entity_extractor
from .relation_extractor import RelationExtractor, get_relation_extractor

__all__ = [
    "TextProcessor",
    "get_text_processor",
    "EntityExtractor",
    "get_entity_extractor",
    "RelationExtractor",
    "get_relation_extractor",
]
