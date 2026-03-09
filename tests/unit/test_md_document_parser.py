"""
Unit tests for MD Document Parser Service

Tests the parsing, validation, and metadata extraction functionality
of the MD document parser.
"""

import pytest
from datetime import datetime
from src.services.md_document_parser import (
    MDDocumentParser,
    MDDocument,
    StructuredData,
    Section,
    Metadata,
    ValidationResult,
    parse_md_document,
    validate_structured_data,
    extract_md_metadata
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def simple_md_document():
    """Simple MD document with basic structure"""
    content = """# Introduction

This is the introduction section.

## Background

Some background information here.

### Details

More detailed information.

## Conclusion

Final thoughts.
"""
    return MDDocument(
        id="test-doc-1",
        content=content,
        filename="test.md",
        uploaded_by="test-user",
        uploaded_at=datetime.utcnow()
    )


@pytest.fixture
def md_document_with_frontmatter():
    """MD document with YAML front matter"""
    content = """---
title: Test Document
author: John Doe
tags: [test, markdown, parser]
created_at: 2024-01-15
description: A test document for parser
language: en
---

# Main Content

This is the main content of the document.

## Section 1

Content for section 1.

## Section 2

Content for section 2.
"""
    return MDDocument(
        id="test-doc-2",
        content=content,
        filename="test_with_meta.md",
        uploaded_by="test-user",
        uploaded_at=datetime.utcnow()
    )


@pytest.fixture
def empty_md_document():
    """Empty MD document"""
    return MDDocument(
        id="test-doc-3",
        content="",
        filename="empty.md",
        uploaded_by="test-user",
        uploaded_at=datetime.utcnow()
    )


@pytest.fixture
def md_document_no_headings():
    """MD document without headings"""
    content = """This is a document with no headings.
Just plain text content.
Multiple lines of text.
"""
    return MDDocument(
        id="test-doc-4",
        content=content,
        filename="no_headings.md",
        uploaded_by="test-user",
        uploaded_at=datetime.utcnow()
    )


@pytest.fixture
def parser():
    """MD document parser instance"""
    return MDDocumentParser()


# ============================================================================
# Test parseDocument Method
# ============================================================================

def test_parse_simple_document(parser, simple_md_document):
    """Test parsing a simple MD document"""
    result = parser.parse_document(simple_md_document)
    
    assert isinstance(result, StructuredData)
    assert result.source_document_id == "test-doc-1"
    assert len(result.sections) == 4  # Introduction, Background, Details, Conclusion
    assert result.checksum is not None
    assert result.parsed_at is not None


def test_parse_document_sections_structure(parser, simple_md_document):
    """Test that sections are parsed correctly"""
    result = parser.parse_document(simple_md_document)
    
    # Check first section
    assert result.sections[0].title == "Introduction"
    assert result.sections[0].level == 1
    assert result.sections[0].order == 0
    assert "introduction section" in result.sections[0].content.lower()
    
    # Check second section
    assert result.sections[1].title == "Background"
    assert result.sections[1].level == 2
    assert result.sections[1].order == 1
    
    # Check nested section
    assert result.sections[2].title == "Details"
    assert result.sections[2].level == 3
    assert result.sections[2].order == 2


def test_parse_document_with_frontmatter(parser, md_document_with_frontmatter):
    """Test parsing document with YAML front matter"""
    result = parser.parse_document(md_document_with_frontmatter)
    
    # Check metadata extraction
    assert result.metadata.title == "Test Document"
    assert result.metadata.author == "John Doe"
    assert "test" in result.metadata.tags
    assert "markdown" in result.metadata.tags
    assert "parser" in result.metadata.tags
    assert result.metadata.description == "A test document for parser"
    assert result.metadata.language == "en"
    
    # Check sections (should not include front matter)
    assert len(result.sections) == 3  # Main Content, Section 1, Section 2
    assert result.sections[0].title == "Main Content"


def test_parse_document_no_headings(parser, md_document_no_headings):
    """Test parsing document without headings"""
    result = parser.parse_document(md_document_no_headings)
    
    # Should create one section with default title
    assert len(result.sections) == 1
    assert result.sections[0].title == "Content"
    assert result.sections[0].level == 1
    assert "plain text content" in result.sections[0].content.lower()


def test_parse_empty_document_raises_error(parser, empty_md_document):
    """Test that parsing empty document raises ValueError"""
    with pytest.raises(ValueError, match="Document content cannot be empty"):
        parser.parse_document(empty_md_document)


def test_parse_document_checksum_consistency(parser, simple_md_document):
    """Test that checksum is consistent for same content"""
    result1 = parser.parse_document(simple_md_document)
    result2 = parser.parse_document(simple_md_document)
    
    assert result1.checksum == result2.checksum


# ============================================================================
# Test validateStructure Method
# ============================================================================

def test_validate_valid_structure(parser, simple_md_document):
    """Test validation of valid structure"""
    structured_data = parser.parse_document(simple_md_document)
    result = parser.validate_structure(structured_data)
    
    assert isinstance(result, ValidationResult)
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_validate_structure_with_warnings(parser):
    """Test validation with warnings (empty sections)"""
    structured_data = StructuredData(
        source_document_id="test",
        sections=[
            Section(title="Section 1", content="Content", level=1, order=0),
            Section(title="Section 2", content="", level=2, order=1),  # Empty
        ],
        metadata=Metadata(title="Test")
    )
    
    result = parser.validate_structure(structured_data)
    
    assert result.is_valid is True  # Still valid, just warnings
    assert len(result.warnings) > 0
    assert any("empty" in w.lower() for w in result.warnings)


def test_validate_structure_invalid_order(parser):
    """Test validation with invalid section ordering"""
    structured_data = StructuredData(
        source_document_id="test",
        sections=[
            Section(title="Section 1", content="Content", level=1, order=0),
            Section(title="Section 2", content="Content", level=2, order=2),  # Skip order 1
        ],
        metadata=Metadata(title="Test")
    )
    
    result = parser.validate_structure(structured_data)
    
    assert result.is_valid is False
    assert len(result.errors) > 0
    assert any("order mismatch" in e.lower() for e in result.errors)


def test_validate_structure_invalid_heading_level(parser):
    """Test that Pydantic validates heading level at model creation time"""
    # Pydantic validates level range (1-6) at model creation
    # This test verifies that invalid levels are caught early
    with pytest.raises(ValueError):
        Section(title="Section 1", content="Content", level=7, order=0)


def test_validate_structure_level_jump_warning(parser):
    """Test validation warns about large heading level jumps"""
    structured_data = StructuredData(
        source_document_id="test",
        sections=[
            Section(title="Section 1", content="Content", level=1, order=0),
            Section(title="Section 2", content="Content", level=4, order=1),  # Jump from 1 to 4
        ],
        metadata=Metadata(title="Test")
    )
    
    result = parser.validate_structure(structured_data)
    
    assert result.is_valid is True  # Valid but with warning
    assert len(result.warnings) > 0
    assert any("jumps from level" in w.lower() for w in result.warnings)


def test_validate_structure_no_sections_warning(parser):
    """Test validation warns when no sections"""
    structured_data = StructuredData(
        source_document_id="test",
        sections=[],
        metadata=Metadata(title="Test")
    )
    
    result = parser.validate_structure(structured_data)
    
    assert result.is_valid is True  # Valid but with warning
    assert len(result.warnings) > 0
    assert any("no sections" in w.lower() for w in result.warnings)


# ============================================================================
# Test extractMetadata Method
# ============================================================================

def test_extract_metadata_from_frontmatter(parser, md_document_with_frontmatter):
    """Test metadata extraction from front matter"""
    metadata = parser.extract_metadata(md_document_with_frontmatter)
    
    assert metadata.title == "Test Document"
    assert metadata.author == "John Doe"
    assert len(metadata.tags) == 3
    assert "test" in metadata.tags
    assert metadata.description == "A test document for parser"


def test_extract_metadata_from_content(parser, simple_md_document):
    """Test metadata extraction from content (no front matter)"""
    metadata = parser.extract_metadata(simple_md_document)
    
    # Should extract title from first h1
    assert metadata.title == "Introduction"


def test_extract_metadata_fallback_to_filename(parser):
    """Test metadata falls back to filename when no title found"""
    doc = MDDocument(
        id="test",
        content="Just plain text, no headings",
        filename="my_document.md",
        uploaded_by="user"
    )
    
    metadata = parser.extract_metadata(doc)
    
    assert metadata.title == "my_document"  # Filename without extension


def test_extract_metadata_with_hashtags(parser):
    """Test extraction of hashtags as tags"""
    doc = MDDocument(
        id="test",
        content="# Title\n\nSome content with #tag1 and #tag2 hashtags.",
        filename="test.md",
        uploaded_by="user"
    )
    
    metadata = parser.extract_metadata(doc)
    
    assert "tag1" in metadata.tags
    assert "tag2" in metadata.tags


def test_extract_metadata_with_author_pattern(parser):
    """Test extraction of author from content patterns"""
    doc = MDDocument(
        id="test",
        content="# Title\n\nAuthor: Jane Smith\n\nContent here.",
        filename="test.md",
        uploaded_by="user"
    )
    
    metadata = parser.extract_metadata(doc)
    
    assert metadata.author == "Jane Smith"


# ============================================================================
# Test Convenience Functions
# ============================================================================

def test_parse_md_document_convenience_function(simple_md_document):
    """Test convenience function for parsing"""
    result = parse_md_document(simple_md_document)
    
    assert isinstance(result, StructuredData)
    assert len(result.sections) > 0


def test_validate_structured_data_convenience_function(parser, simple_md_document):
    """Test convenience function for validation"""
    structured_data = parser.parse_document(simple_md_document)
    result = validate_structured_data(structured_data)
    
    assert isinstance(result, ValidationResult)
    assert result.is_valid is True


def test_extract_md_metadata_convenience_function(simple_md_document):
    """Test convenience function for metadata extraction"""
    metadata = extract_md_metadata(simple_md_document)
    
    assert isinstance(metadata, Metadata)
    assert metadata.title is not None


# ============================================================================
# Test Error Handling
# ============================================================================

def test_parse_document_handles_malformed_frontmatter(parser):
    """Test parser handles malformed front matter gracefully"""
    doc = MDDocument(
        id="test",
        content="---\nmalformed: yaml: content\n---\n# Title\nContent",
        filename="test.md",
        uploaded_by="user"
    )
    
    # Should not raise, just skip malformed front matter
    result = parser.parse_document(doc)
    assert isinstance(result, StructuredData)


def test_parse_document_handles_unicode(parser):
    """Test parser handles Unicode content"""
    doc = MDDocument(
        id="test",
        content="# 标题\n\n这是中文内容。\n\n## 子标题\n\n更多内容。",
        filename="chinese.md",
        uploaded_by="user"
    )
    
    result = parser.parse_document(doc)
    
    assert result.sections[0].title == "标题"
    assert "中文内容" in result.sections[0].content


def test_parse_document_handles_special_characters(parser):
    """Test parser handles special characters in headings"""
    doc = MDDocument(
        id="test",
        content="# Title with *emphasis* and `code`\n\nContent here.",
        filename="test.md",
        uploaded_by="user"
    )
    
    result = parser.parse_document(doc)
    
    assert "*emphasis*" in result.sections[0].title
    assert "`code`" in result.sections[0].title


# ============================================================================
# Test Section Model Validation
# ============================================================================

def test_section_title_cannot_be_empty():
    """Test Section model validates title is not empty"""
    with pytest.raises(ValueError, match="Section title cannot be empty"):
        Section(title="", content="Content", level=1, order=0)


def test_section_title_strips_whitespace():
    """Test Section model strips whitespace from title"""
    section = Section(title="  Title  ", content="Content", level=1, order=0)
    assert section.title == "Title"


def test_section_level_must_be_valid():
    """Test Section model validates level range"""
    with pytest.raises(ValueError):
        Section(title="Title", content="Content", level=0, order=0)
    
    with pytest.raises(ValueError):
        Section(title="Title", content="Content", level=7, order=0)


# ============================================================================
# Test Metadata Model Validation
# ============================================================================

def test_metadata_tags_filters_empty_strings():
    """Test Metadata model filters out empty tag strings"""
    metadata = Metadata(tags=["tag1", "", "  ", "tag2"])
    assert len(metadata.tags) == 2
    assert "tag1" in metadata.tags
    assert "tag2" in metadata.tags


def test_metadata_tags_strips_whitespace():
    """Test Metadata model strips whitespace from tags"""
    metadata = Metadata(tags=["  tag1  ", "tag2  "])
    assert "tag1" in metadata.tags
    assert "tag2" in metadata.tags


# ============================================================================
# Test Edge Cases
# ============================================================================

def test_parse_document_with_only_whitespace(parser):
    """Test parsing document with only whitespace"""
    doc = MDDocument(
        id="test",
        content="   \n\n   \t\t   \n",
        filename="whitespace.md",
        uploaded_by="user"
    )
    
    with pytest.raises(ValueError, match="Document content cannot be empty"):
        parser.parse_document(doc)


def test_parse_document_with_multiple_h1_headings(parser):
    """Test parsing document with multiple h1 headings"""
    doc = MDDocument(
        id="test",
        content="# First Title\n\nContent 1\n\n# Second Title\n\nContent 2",
        filename="test.md",
        uploaded_by="user"
    )
    
    result = parser.parse_document(doc)
    
    assert len(result.sections) == 2
    assert result.sections[0].title == "First Title"
    assert result.sections[1].title == "Second Title"


def test_parse_document_with_code_blocks(parser):
    """Test parsing document with code blocks"""
    doc = MDDocument(
        id="test",
        content="""# Title

Some text.

```python
def hello():
    print("Hello")
```

More text.
""",
        filename="test.md",
        uploaded_by="user"
    )
    
    result = parser.parse_document(doc)
    
    assert "```python" in result.sections[0].content
    assert "def hello()" in result.sections[0].content


def test_checksum_changes_with_content(parser):
    """Test that checksum changes when content changes"""
    doc1 = MDDocument(
        id="test",
        content="# Title\n\nContent 1",
        filename="test.md",
        uploaded_by="user"
    )
    
    doc2 = MDDocument(
        id="test",
        content="# Title\n\nContent 2",  # Different content
        filename="test.md",
        uploaded_by="user"
    )
    
    result1 = parser.parse_document(doc1)
    result2 = parser.parse_document(doc2)
    
    assert result1.checksum != result2.checksum
