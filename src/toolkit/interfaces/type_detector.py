"""
TypeDetector interface — detects file type, structure, encoding, and schema.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from src.toolkit.models.enums import DataStructure, Encoding, FileType


class TypeDetector(ABC):
    """
    Interface for detecting data type characteristics.

    Implementations identify file type, internal structure,
    character encoding, and schema of data sources.
    """

    @abstractmethod
    async def detect_file_type(self, data_source: Any) -> FileType:
        """
        Detect the file type of a data source.

        Args:
            data_source: The data source to inspect.

        Returns:
            The detected FileType.
        """
        ...

    @abstractmethod
    async def detect_data_structure(self, content: bytes) -> DataStructure:
        """
        Detect the internal data structure from raw content.

        Args:
            content: Raw byte content to analyze.

        Returns:
            The detected DataStructure type.
        """
        ...

    @abstractmethod
    async def detect_encoding(self, content: bytes) -> Encoding:
        """
        Detect the character encoding of raw content.

        Args:
            content: Raw byte content to analyze.

        Returns:
            The detected Encoding.
        """
        ...

    @abstractmethod
    async def detect_schema(self, structured_data: Any) -> Dict[str, str]:
        """
        Detect the schema of structured data.

        Args:
            structured_data: Parsed structured data (e.g. DataFrame, dict).

        Returns:
            A mapping of field names to their detected types.
        """
        ...
