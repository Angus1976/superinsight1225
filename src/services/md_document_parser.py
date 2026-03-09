"""
MD Document Parser Service

Parses Markdown documents and converts them into structured data format
with metadata extraction and validation.

Implements the IStructureParser interface from the design document.
"""

import hashlib
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class Section(BaseModel):
    """Represents a section in the structured document"""
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    level: int = Field(..., ge=1, le=6, description="Heading level (1-6)")
    order: int = Field(..., ge=0, description="Section order in document")
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Section title cannot be empty")
        return v.strip()


class Metadata(BaseModel):
    """Document metadata extracted from MD document"""
    title: Optional[str] = Field(None, description="Document title")
    author: Optional[str] = Field(None, description="Document author")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    created_at: Optional[datetime] = Field(None, description="Creation date")
    description: Optional[str] = Field(None, description="Document description")
    language: Optional[str] = Field(None, description="Document language")
    
    @field_validator('tags')
    @classmethod
    def tags_not_empty_strings(cls, v: List[str]) -> List[str]:
        return [tag.strip() for tag in v if tag and tag.strip()]


class StructuredData(BaseModel):
    """Structured representation of parsed MD document"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_document_id: str = Field(..., description="Original document ID")
    sections: List[Section] = Field(default_factory=list)
    metadata: Metadata = Field(default_factory=Metadata)
    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    checksum: Optional[str] = Field(None, description="Content checksum for integrity")


class ValidationResult(BaseModel):
    """Result of structure validation"""
    is_valid: bool = Field(..., description="Whether structure is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class MDDocument(BaseModel):
    """Input MD document"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = Field(..., description="Raw MD content")
    filename: str = Field(..., description="Original filename")
    uploaded_by: str = Field(..., description="User who uploaded")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# MD Document Parser
# ============================================================================

class MDDocumentParser:
    """
    Parser for Markdown documents.
    
    Converts MD format documents into structured sections with metadata extraction.
    Handles parsing errors gracefully and validates structure integrity.
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
    """
    
    # Regex patterns for parsing
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    METADATA_BLOCK_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n',
        re.DOTALL | re.MULTILINE
    )
    METADATA_LINE_PATTERN = re.compile(r'^(\w+):\s*(.+)$')
    TAG_PATTERN = re.compile(r'\[([^\]]+)\]')
    
    def __init__(self):
        """Initialize the MD document parser"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def parse_document(self, document: MDDocument) -> StructuredData:
        """
        Parse MD document into structured data.
        
        Args:
            document: MDDocument to parse
        
        Returns:
            StructuredData with sections and metadata
        
        Raises:
            ValueError: If document content is empty or invalid
            RuntimeError: If parsing fails unexpectedly
        
        Validates: Requirements 1.1, 1.2, 1.3
        """
        try:
            self.logger.info(
                f"Parsing MD document: {document.filename} "
                f"(uploaded by {document.uploaded_by})"
            )
            
            # Validate input
            if not document.content or not document.content.strip():
                raise ValueError("Document content cannot be empty")
            
            content = document.content
            
            # Extract metadata from front matter (if present)
            metadata, content_without_metadata = self._extract_metadata_from_frontmatter(
                content
            )
            
            # If no front matter, try to extract from first heading and content
            if not metadata.title:
                metadata = self._extract_metadata_from_content(content_without_metadata)
            
            # Parse sections
            sections = self._parse_sections(content_without_metadata)
            
            # Calculate checksum for integrity
            checksum = self._calculate_checksum(document.content)
            
            # Create structured data
            structured_data = StructuredData(
                source_document_id=document.id,
                sections=sections,
                metadata=metadata,
                parsed_at=datetime.utcnow(),
                checksum=checksum
            )
            
            self.logger.info(
                f"Successfully parsed document: {len(sections)} sections, "
                f"title='{metadata.title}'"
            )
            
            return structured_data
            
        except ValueError as e:
            self.logger.error(f"Validation error parsing document: {e}")
            raise
        except Exception as e:
            self.logger.exception(f"Unexpected error parsing document: {e}")
            raise RuntimeError(f"Failed to parse document: {e}") from e
    
    def validate_structure(self, data: StructuredData) -> ValidationResult:
        """
        Validate the structure integrity of parsed data.
        
        Args:
            data: StructuredData to validate
        
        Returns:
            ValidationResult with validation status and messages
        
        Validates: Requirements 1.5
        """
        errors = []
        warnings = []
        
        try:
            # Check if sections exist
            if not data.sections:
                warnings.append("Document has no sections")
            
            # Validate section ordering
            expected_order = 0
            for section in data.sections:
                if section.order != expected_order:
                    errors.append(
                        f"Section order mismatch: expected {expected_order}, "
                        f"got {section.order}"
                    )
                expected_order += 1
            
            # Validate heading levels
            prev_level = 0
            for i, section in enumerate(data.sections):
                # Check for valid level range
                if section.level < 1 or section.level > 6:
                    errors.append(
                        f"Section {i} has invalid heading level: {section.level}"
                    )
                
                # Warn about large level jumps (e.g., h1 -> h4)
                if prev_level > 0 and section.level > prev_level + 1:
                    warnings.append(
                        f"Section {i} jumps from level {prev_level} to {section.level}"
                    )
                
                prev_level = section.level
            
            # Check for empty sections
            empty_sections = [
                i for i, s in enumerate(data.sections)
                if not s.content or not s.content.strip()
            ]
            if empty_sections:
                warnings.append(
                    f"Found {len(empty_sections)} empty sections: {empty_sections}"
                )
            
            # Validate metadata
            if not data.metadata.title:
                warnings.append("Document has no title in metadata")
            
            # Check checksum
            if not data.checksum:
                warnings.append("Document has no checksum for integrity verification")
            
            is_valid = len(errors) == 0
            
            if is_valid:
                self.logger.info(
                    f"Structure validation passed with {len(warnings)} warnings"
                )
            else:
                self.logger.warning(
                    f"Structure validation failed with {len(errors)} errors"
                )
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.exception(f"Error during validation: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {e}"],
                warnings=warnings
            )
    
    def extract_metadata(self, document: MDDocument) -> Metadata:
        """
        Extract metadata from MD document.
        
        Args:
            document: MDDocument to extract metadata from
        
        Returns:
            Metadata object with extracted information
        
        Validates: Requirements 1.2
        """
        try:
            self.logger.info(f"Extracting metadata from: {document.filename}")
            
            # Try front matter first
            metadata, _ = self._extract_metadata_from_frontmatter(document.content)
            
            # If no front matter, extract from content
            if not metadata.title:
                metadata = self._extract_metadata_from_content(document.content)
            
            # Add filename-based fallbacks
            if not metadata.title:
                # Use filename without extension as title
                metadata.title = document.filename.rsplit('.', 1)[0]
            
            self.logger.info(
                f"Extracted metadata: title='{metadata.title}', "
                f"author='{metadata.author}', tags={metadata.tags}"
            )
            
            return metadata
            
        except Exception as e:
            self.logger.exception(f"Error extracting metadata: {e}")
            # Return minimal metadata on error
            return Metadata(title=document.filename)
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _extract_metadata_from_frontmatter(
        self,
        content: str
    ) -> tuple[Metadata, str]:
        """
        Extract metadata from YAML front matter.
        
        Front matter format:
        ---
        title: Document Title
        author: Author Name
        tags: [tag1, tag2, tag3]
        created_at: 2024-01-01
        description: Document description
        language: en
        ---
        
        Returns:
            Tuple of (Metadata, content_without_frontmatter)
        """
        match = self.METADATA_BLOCK_PATTERN.match(content)
        
        if not match:
            return Metadata(), content
        
        frontmatter = match.group(1)
        content_without_frontmatter = content[match.end():]
        
        metadata_dict: Dict[str, Any] = {}
        
        for line in frontmatter.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            meta_match = self.METADATA_LINE_PATTERN.match(line)
            if meta_match:
                key = meta_match.group(1).lower()
                value = meta_match.group(2).strip()
                
                # Parse tags
                if key == 'tags':
                    # Handle both [tag1, tag2] and tag1, tag2 formats
                    value = value.strip('[]')
                    tags = [t.strip().strip('"\'') for t in value.split(',')]
                    metadata_dict['tags'] = [t for t in tags if t]
                
                # Parse date
                elif key == 'created_at':
                    try:
                        metadata_dict['created_at'] = datetime.fromisoformat(
                            value.replace('Z', '+00:00')
                        )
                    except ValueError:
                        self.logger.warning(f"Invalid date format: {value}")
                
                # Other fields
                else:
                    metadata_dict[key] = value
        
        return Metadata(**metadata_dict), content_without_frontmatter
    
    def _extract_metadata_from_content(self, content: str) -> Metadata:
        """
        Extract metadata from document content.
        
        Heuristics:
        - First h1 heading is the title
        - Look for "Author:", "By:", etc. patterns
        - Extract hashtags as tags
        """
        metadata_dict: Dict[str, Any] = {}
        
        # Extract title from first h1
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            metadata_dict['title'] = h1_match.group(1).strip()
        
        # Look for author patterns
        author_patterns = [
            r'(?:Author|By|Written by):\s*(.+)$',
            r'(?:作者|撰写)[:：]\s*(.+)$'
        ]
        for pattern in author_patterns:
            author_match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            if author_match:
                metadata_dict['author'] = author_match.group(1).strip()
                break
        
        # Extract hashtags as tags
        hashtags = re.findall(r'#(\w+)', content)
        if hashtags:
            metadata_dict['tags'] = list(set(hashtags))
        
        return Metadata(**metadata_dict)
    
    def _parse_sections(self, content: str) -> List[Section]:
        """
        Parse content into sections based on headings.
        
        Args:
            content: MD content to parse
        
        Returns:
            List of Section objects
        """
        sections = []
        
        # Find all headings
        headings = list(self.HEADING_PATTERN.finditer(content))
        
        if not headings:
            # No headings found, treat entire content as one section
            if content.strip():
                sections.append(Section(
                    title="Content",
                    content=content.strip(),
                    level=1,
                    order=0
                ))
            return sections
        
        # Process each heading and its content
        for i, heading_match in enumerate(headings):
            # Extract heading info
            level = len(heading_match.group(1))  # Number of # characters
            title = heading_match.group(2).strip()
            
            # Extract content between this heading and the next
            start_pos = heading_match.end()
            if i < len(headings) - 1:
                end_pos = headings[i + 1].start()
            else:
                end_pos = len(content)
            
            section_content = content[start_pos:end_pos].strip()
            
            sections.append(Section(
                title=title,
                content=section_content,
                level=level,
                order=i
            ))
        
        return sections
    
    def _calculate_checksum(self, content: str) -> str:
        """
        Calculate SHA-256 checksum of content.
        
        Args:
            content: Content to checksum
        
        Returns:
            Hex string of checksum
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


# ============================================================================
# Convenience Functions
# ============================================================================

def parse_md_document(document: MDDocument) -> StructuredData:
    """
    Convenience function to parse an MD document.
    
    Args:
        document: MDDocument to parse
    
    Returns:
        StructuredData with parsed content
    """
    parser = MDDocumentParser()
    return parser.parse_document(document)


def validate_structured_data(data: StructuredData) -> ValidationResult:
    """
    Convenience function to validate structured data.
    
    Args:
        data: StructuredData to validate
    
    Returns:
        ValidationResult with validation status
    """
    parser = MDDocumentParser()
    return parser.validate_structure(data)


def extract_md_metadata(document: MDDocument) -> Metadata:
    """
    Convenience function to extract metadata from MD document.
    
    Args:
        document: MDDocument to extract metadata from
    
    Returns:
        Metadata object
    """
    parser = MDDocumentParser()
    return parser.extract_metadata(document)
