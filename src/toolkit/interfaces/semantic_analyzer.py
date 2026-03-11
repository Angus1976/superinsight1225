"""
SemanticAnalyzer interface — extracts semantic meaning from data.
"""

from abc import ABC, abstractmethod
from typing import Any, List

from src.toolkit.models.enums import Domain, Language, SemanticType


class SemanticAnalyzer(ABC):
    """
    Interface for semantic analysis of data content.

    Implementations detect language, domain, extract entities,
    and infer semantic types for structured columns.
    """

    @abstractmethod
    async def detect_language(self, text_data: str) -> Language:
        """
        Detect the primary language of text content.

        Args:
            text_data: Text content to analyze.

        Returns:
            The detected Language.
        """
        ...

    @abstractmethod
    async def detect_domain(self, content: Any) -> Domain:
        """
        Detect the content domain (e.g. finance, medical, legal).

        Args:
            content: Content to classify.

        Returns:
            The detected Domain.
        """
        ...

    @abstractmethod
    async def extract_entities(self, text_data: str) -> List[str]:
        """
        Extract named entities from text content.

        Args:
            text_data: Text content to analyze.

        Returns:
            A list of extracted entity strings.
        """
        ...

    @abstractmethod
    async def infer_semantic_type(self, column: Any) -> SemanticType:
        """
        Infer the semantic type of a data column.

        Args:
            column: Column data (e.g. list of values or Series).

        Returns:
            The inferred SemanticType.
        """
        ...
