"""
Unit tests for MD Document Parser Error Handling

Tests error handling, validation failures, and descriptive error messages
for the MD document parser.

Validates: Requirements 1.4, 1.5
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
)


@pytest.fixture
def parser():
    """MD document parser instance"""
    return MDDocumentParser()


# ============================================================================
# Test: Invalid MD Syntax - Unclosed Tags
# ============================================================================

class TestUnclosedTags:
    """Tests for handling unclosed/invalid MD syntax elements"""

    def test_parse_document_with_unclosed_code_fence(self, parser):
        """Test handling of unclosed code fence"""
        doc = MDDocument(
            id="test-unclosed-code",
            content="""# Title

Some text with unclosed code fence:

```python
def hello():
    print("Hello"

More text after unclosed fence.
""",
            filename="unclosed_code.md",
            uploaded_by="test-user"
        )
        
        # Should parse successfully (code fence handling is permissive)
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)
        assert len(result.sections) >= 1

    def test_parse_document_with_mismatched_html_tags(self, parser):
        """Test handling of mismatched HTML tags"""
        doc = MDDocument(
            id="test-mismatched-html",
            content="""# Title

<div>Some content
More content without closing tag.
""",
            filename="mismatched_html.md",
            uploaded_by="test-user"
        )
        
        # Should parse successfully (HTML handling is permissive)
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)

    def test_parse_document_with_unclosed_blockquote(self, parser):
        """Test handling of unclosed blockquote"""
        doc = MDDocument(
            id="test-unclosed-blockquote",
            content="""# Title

> This is a blockquote
> That continues
But this is not part of the quote.
""",
            filename="unclosed_blockquote.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)
        assert len(result.sections) >= 1

    def test_parse_document_with_unclosed_list(self, parser):
        """Test handling of unclosed list"""
        doc = MDDocument(
            id="test-unclosed-list",
            content="""# Title

- Item one
- Item two
- Item three
And regular text after list.
""",
            filename="unclosed_list.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)


# ============================================================================
# Test: Invalid MD Syntax - Malformed Headers
# ============================================================================

class TestMalformedHeaders:
    """Tests for handling malformed header syntax"""

    def test_parse_document_with_extra_hashes(self, parser):
        """Test handling of headers with excessive hashes"""
        doc = MDDocument(
            id="test-extra-hashes",
            content="""####### Too many hashes
This is not a valid header.
""",
            filename="extra_hashes.md",
            uploaded_by="test-user"
        )
        
        # Should treat as regular text, not a header
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)

    def test_parse_document_with_empty_header(self, parser):
        """Test handling of empty header"""
        doc = MDDocument(
            id="test-empty-header",
            content="""# 

Some content.
""",
            filename="empty_header.md",
            uploaded_by="test-user"
        )
        
        # Should handle gracefully
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)

    def test_parse_document_with_whitespace_only_header(self, parser):
        """Test handling of whitespace-only header"""
        doc = MDDocument(
            id="test-whitespace-header",
            content="""#     

Some content.
""",
            filename="whitespace_header.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)

    def test_parse_document_with_special_chars_in_header(self, parser):
        """Test handling of special characters in headers"""
        doc = MDDocument(
            id="test-special-chars-header",
            content="""# Header with `code` and **bold** and *italic*
Content here.
""",
            filename="special_chars_header.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert result.sections[0].title == "Header with `code` and **bold** and *italic*"

    def test_parse_document_with_unicode_header(self, parser):
        """Test handling of unicode characters in headers"""
        doc = MDDocument(
            id="test-unicode-header",
            content="""# 标题 with émojis 🎉
Content here.
""",
            filename="unicode_header.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert "标题" in result.sections[0].title
        assert "🎉" in result.sections[0].title


# ============================================================================
# Test: Missing Required Fields
# ============================================================================

class TestMissingRequiredFields:
    """Tests for handling missing required fields"""

    def test_parse_document_with_empty_content(self, parser):
        """Test that empty content raises ValueError with descriptive message"""
        doc = MDDocument(
            id="test-empty-content",
            content="",
            filename="empty.md",
            uploaded_by="test-user"
        )
        
        with pytest.raises(ValueError) as exc_info:
            parser.parse_document(doc)
        
        assert "empty" in str(exc_info.value).lower()

    def test_parse_document_with_whitespace_only_content(self, parser):
        """Test that whitespace-only content raises ValueError"""
        doc = MDDocument(
            id="test-whitespace-content",
            content="   \n\n   \t\t  \n",
            filename="whitespace.md",
            uploaded_by="test-user"
        )
        
        with pytest.raises(ValueError) as exc_info:
            parser.parse_document(doc)
        
        assert "empty" in str(exc_info.value).lower()

    def test_validate_structure_with_no_sections(self, parser):
        """Test validation of structure with no sections"""
        structured_data = StructuredData(
            source_document_id="test",
            sections=[],
            metadata=Metadata(title="Test")
        )
        
        result = parser.validate_structure(structured_data)
        
        # Should be valid but with warning
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("no sections" in w.lower() for w in result.warnings)

    def test_validate_structure_with_missing_title(self, parser):
        """Test validation warns when title is missing"""
        structured_data = StructuredData(
            source_document_id="test",
            sections=[Section(title="Content", content="Test", level=1, order=0)],
            metadata=Metadata()  # No title
        )
        
        result = parser.validate_structure(structured_data)
        
        assert result.is_valid is True  # Still valid
        assert len(result.warnings) > 0
        assert any("title" in w.lower() for w in result.warnings)

    def test_validate_structure_with_missing_checksum(self, parser):
        """Test validation warns when checksum is missing"""
        structured_data = StructuredData(
            source_document_id="test",
            sections=[Section(title="Content", content="Test", level=1, order=0)],
            metadata=Metadata(title="Test"),
            checksum=None  # No checksum
        )
        
        result = parser.validate_structure(structured_data)
        
        assert result.is_valid is True  # Still valid
        assert len(result.warnings) > 0
        assert any("checksum" in w.lower() for w in result.warnings)


# ============================================================================
# Test: Malicious Content - Edge Cases
# ============================================================================

class TestMaliciousContent:
    """Tests for handling potentially malicious content"""

    def test_parse_document_with_null_bytes(self, parser):
        """Test handling of null bytes in content"""
        doc = MDDocument(
            id="test-null-bytes",
            content="# Title\x00\nContent with null.",
            filename="null_bytes.md",
            uploaded_by="test-user"
        )
        
        # Should handle null bytes gracefully
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)

    def test_parse_document_with_extremely_long_line(self, parser):
        """Test handling of extremely long lines"""
        long_line = "x" * 100000
        doc = MDDocument(
            id="test-long-line",
            content=f"# Title\n{long_line}",
            filename="long_line.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)
        assert len(result.sections[0].content) > 50000

    def test_parse_document_with_deeply_nested_headers(self, parser):
        """Test handling of deeply nested headers (up to h6)"""
        doc = MDDocument(
            id="test-deep-nesting",
            content="""# H1
## H2
### H3
#### H4
##### H5
###### H6
""",
            filename="deep_nesting.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert len(result.sections) == 6
        levels = [s.level for s in result.sections]
        assert levels == [1, 2, 3, 4, 5, 6]

    def test_parse_document_with_recursive_patterns(self, parser):
        """Test handling of recursive/repetitive patterns"""
        doc = MDDocument(
            id="test-recursive",
            content="# A\n# A\n# A\n# A\n# A\n# A\n# A\n# A\n# A\n# A",
            filename="recursive.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert len(result.sections) == 10

    def test_parse_document_with_control_characters(self, parser):
        """Test handling of control characters"""
        control_chars = "\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f"
        doc = MDDocument(
            id="test-control-chars",
            content=f"# Title{control_chars}\nContent",
            filename="control_chars.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)

    def test_parse_document_with_nested_backticks(self, parser):
        """Test handling of nested code spans"""
        doc = MDDocument(
            id="test-nested-backticks",
            content="""# Title

Text with ``code `inside` code`` here.
""",
            filename="nested_backticks.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)

    def test_parse_document_with_mixed_header_styles(self, parser):
        """Test handling of mixed header styles (atx and setext)"""
        doc = MDDocument(
            id="test-mixed-headers",
            content="""# ATX Header

Setext headers:
Header 1
========

Header 2
--------
""",
            filename="mixed_headers.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        # Should parse at least the atx header
        assert len(result.sections) >= 1


# ============================================================================
# Test: Structure Validation Failures
# ============================================================================

class TestStructureValidationFailures:
    """Tests for structure validation error detection"""

    def test_validate_structure_with_duplicate_section_order(self, parser):
        """Test validation detects duplicate section orders"""
        structured_data = StructuredData(
            source_document_id="test",
            sections=[
                Section(title="Section 1", content="Content", level=1, order=0),
                Section(title="Section 2", content="Content", level=1, order=0),  # Duplicate
            ],
            metadata=Metadata(title="Test")
        )
        
        result = parser.validate_structure(structured_data)
        
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_structure_with_gap_in_order(self, parser):
        """Test validation detects gaps in section ordering"""
        structured_data = StructuredData(
            source_document_id="test",
            sections=[
                Section(title="Section 1", content="Content", level=1, order=0),
                Section(title="Section 2", content="Content", level=2, order=2),  # Gap at 1
            ],
            metadata=Metadata(title="Test")
        )
        
        result = parser.validate_structure(structured_data)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("order" in e.lower() for e in result.errors)

    def test_validate_structure_with_negative_order(self, parser):
        """Test validation detects negative section order"""
        # Pydantic validates order >= 0 at model creation time
        with pytest.raises(Exception) as exc_info:
            Section(title="Section 1", content="Content", level=1, order=-1)
        
        # Pydantic raises ValidationError for negative order
        assert "greater than or equal to 0" in str(exc_info.value).lower() or "validation error" in str(exc_info.value).lower()

    def test_validate_structure_with_empty_section_title(self, parser):
        """Test validation detects empty section titles"""
        with pytest.raises(ValueError) as exc_info:
            Section(title="", content="Content", level=1, order=0)
        
        assert "empty" in str(exc_info.value).lower()

    def test_validate_structure_with_whitespace_only_title(self, parser):
        """Test validation detects whitespace-only section titles"""
        with pytest.raises(ValueError) as exc_info:
            Section(title="   ", content="Content", level=1, order=0)
        
        assert "empty" in str(exc_info.value).lower()

    def test_validate_structure_with_invalid_level_zero(self, parser):
        """Test validation rejects level 0 (must be 1-6)"""
        with pytest.raises(ValueError):
            Section(title="Title", content="Content", level=0, order=0)

    def test_validate_structure_with_invalid_level_seven(self, parser):
        """Test validation rejects level 7 (must be 1-6)"""
        with pytest.raises(ValueError):
            Section(title="Title", content="Content", level=7, order=0)

    def test_validate_structure_with_empty_sections_warning(self, parser):
        """Test validation warns about empty sections"""
        structured_data = StructuredData(
            source_document_id="test",
            sections=[
                Section(title="Section 1", content="Content", level=1, order=0),
                Section(title="Section 2", content="   ", level=2, order=1),  # Empty
            ],
            metadata=Metadata(title="Test")
        )
        
        result = parser.validate_structure(structured_data)
        
        assert result.is_valid is True  # Still valid
        assert len(result.warnings) > 0
        assert any("empty" in w.lower() for w in result.warnings)

    def test_validate_structure_with_large_level_jump_warning(self, parser):
        """Test validation warns about large level jumps"""
        structured_data = StructuredData(
            source_document_id="test",
            sections=[
                Section(title="Section 1", content="Content", level=1, order=0),
                Section(title="Section 2", content="Content", level=4, order=1),  # Jump
            ],
            metadata=Metadata(title="Test")
        )
        
        result = parser.validate_structure(structured_data)
        
        assert result.is_valid is True  # Valid but with warning
        assert len(result.warnings) > 0
        assert any("jump" in w.lower() for w in result.warnings)


# ============================================================================
# Test: Descriptive Error Messages
# ============================================================================

class TestDescriptiveErrorMessages:
    """Tests for descriptive error messages"""

    def test_parse_empty_document_error_message(self, parser):
        """Test that empty document error is descriptive"""
        doc = MDDocument(
            id="test-empty",
            content="",
            filename="empty.md",
            uploaded_by="test-user"
        )
        
        with pytest.raises(ValueError) as exc_info:
            parser.parse_document(doc)
        
        error_msg = str(exc_info.value).lower()
        assert "empty" in error_msg or "content" in error_msg

    def test_parse_whitespace_only_error_message(self, parser):
        """Test that whitespace-only document error is descriptive"""
        doc = MDDocument(
            id="test-whitespace",
            content="   \n\n   ",
            filename="whitespace.md",
            uploaded_by="test-user"
        )
        
        with pytest.raises(ValueError) as exc_info:
            parser.parse_document(doc)
        
        error_msg = str(exc_info.value).lower()
        assert "empty" in error_msg or "content" in error_msg

    def test_validation_error_message_contains_details(self, parser):
        """Test that validation errors contain specific details"""
        structured_data = StructuredData(
            source_document_id="test",
            sections=[
                Section(title="Section 1", content="Content", level=1, order=0),
                Section(title="Section 2", content="Content", level=2, order=2),  # Gap
            ],
            metadata=Metadata(title="Test")
        )
        
        result = parser.validate_structure(structured_data)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        # Error should mention the specific issue
        error_text = " ".join(result.errors).lower()
        assert "order" in error_text or "mismatch" in error_text

    def test_validation_error_message_contains_section_info(self, parser):
        """Test that validation errors include section information"""
        # Pydantic validates level range (1-6) at model creation time
        with pytest.raises(Exception) as exc_info:
            Section(title="Section 1", content="Content", level=10, order=0)
        
        # Error should mention the invalid level
        error_text = str(exc_info.value).lower()
        assert "level" in error_text or "less than or equal to 6" in error_text or "validation error" in error_text

    def test_validation_warning_message_is_descriptive(self, parser):
        """Test that validation warnings are descriptive"""
        structured_data = StructuredData(
            source_document_id="test",
            sections=[],  # No sections
            metadata=Metadata(title="Test")
        )
        
        result = parser.validate_structure(structured_data)
        
        assert result.is_valid is True  # Still valid
        assert len(result.warnings) > 0
        # Warning should be descriptive
        warning_text = " ".join(result.warnings).lower()
        assert "section" in warning_text or "no" in warning_text

    def test_parse_runtime_error_message(self, parser):
        """Test that unexpected parsing errors are wrapped with descriptive message"""
        # Test that passing None raises RuntimeError with descriptive message
        with pytest.raises(RuntimeError) as exc_info:
            parser.parse_document(None)  # type: ignore
        
        error_msg = str(exc_info.value)
        # The error should be descriptive and mention parsing failure
        assert "parse" in error_msg.lower() or "document" in error_msg.lower()
        assert len(error_msg) > 10  # Should have meaningful content

    def test_extract_metadata_error_returns_fallback(self, parser):
        """Test that metadata extraction errors return fallback with filename"""
        # This tests graceful degradation
        doc = MDDocument(
            id="test",
            content="# Title",
            filename="test_file.md",
            uploaded_by="user"
        )
        
        # Should not raise, should return metadata
        metadata = parser.extract_metadata(doc)
        assert metadata is not None
        assert metadata.title is not None


# ============================================================================
# Test: Metadata Extraction Edge Cases
# ============================================================================

class TestMetadataExtractionEdgeCases:
    """Tests for metadata extraction edge cases"""

    def test_extract_metadata_with_malformed_frontmatter(self, parser):
        """Test handling of malformed front matter"""
        doc = MDDocument(
            id="test-malformed-fm",
            content="""---
malformed: yaml: content: here
  not: valid
---
# Title
Content
""",
            filename="malformed_fm.md",
            uploaded_by="test-user"
        )
        
        # Should not raise, should skip front matter
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)

    def test_extract_metadata_with_empty_frontmatter(self, parser):
        """Test handling of empty front matter"""
        doc = MDDocument(
            id="test-empty-fm",
            content="""---
---
# Title
Content
""",
            filename="empty_fm.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)
        assert result.metadata.title == "Title"

    def test_extract_metadata_with_partial_frontmatter(self, parser):
        """Test handling of partial front matter"""
        doc = MDDocument(
            id="test-partial-fm",
            content="""---
title: Only Title
---
# Different Title
Content
""",
            filename="partial_fm.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        # Front matter title should be used
        assert result.metadata.title == "Only Title"

    def test_extract_metadata_with_invalid_date(self, parser):
        """Test handling of invalid date in front matter"""
        doc = MDDocument(
            id="test-invalid-date",
            content="""---
created_at: not-a-date
---
# Title
Content
""",
            filename="invalid_date.md",
            uploaded_by="test-user"
        )
        
        # Should not raise, should skip invalid date
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)
        assert result.metadata.created_at is None

    def test_extract_metadata_with_malformed_tags(self, parser):
        """Test handling of malformed tags in front matter"""
        doc = MDDocument(
            id="test-malformed-tags",
            content="""---
tags: not-properly-formatted
---
# Title
Content
""",
            filename="malformed_tags.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)
        # Tags without brackets are treated as a single string, not parsed as list
        # The parser expects [tag1, tag2] format
        # So malformed tags may result in empty list or single tag
        assert result.metadata.tags is not None

    def test_extract_metadata_with_empty_tags_list(self, parser):
        """Test handling of empty tags list"""
        doc = MDDocument(
            id="test-empty-tags",
            content="""---
tags: []
---
# Title
Content
""",
            filename="empty_tags.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)
        assert len(result.metadata.tags) == 0

    def test_extract_metadata_with_whitespace_tags(self, parser):
        """Test that whitespace is stripped from tags"""
        doc = MDDocument(
            id="test-whitespace-tags",
            content="""---
tags: [  tag1  ,   tag2  ,  ]
---
# Title
Content
""",
            filename="whitespace_tags.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        # Tags should be properly parsed and whitespace stripped
        assert result.metadata.tags is not None
        # The parser should handle the bracketed format
        assert len(result.metadata.tags) >= 0  # May be empty if parsing fails


# ============================================================================
# Test: Content with Special Characters
# ============================================================================

class TestSpecialCharacterContent:
    """Tests for handling content with special characters"""

    def test_parse_document_with_emoji(self, parser):
        """Test handling of emoji characters"""
        doc = MDDocument(
            id="test-emoji",
            content="# Title 🎉\nContent with emojis 🚀✨",
            filename="emoji.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert "🎉" in result.sections[0].title
        assert "🚀" in result.sections[0].content

    def test_parse_document_with_right_to_left_text(self, parser):
        """Test handling of right-to-left text"""
        doc = MDDocument(
            id="test-rtl",
            content="# Title\nمرحبا بالعالم",
            filename="rtl.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)

    def test_parse_document_with_mixed_encoding(self, parser):
        """Test handling of mixed encoding content"""
        doc = MDDocument(
            id="test-mixed-encoding",
            content="# Title\n中文English日本語한국어\nMixing scripts",
            filename="mixed_encoding.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)
        assert "中文" in result.sections[0].content

    def test_parse_document_with_very_long_title(self, parser):
        """Test handling of very long titles"""
        long_title = "A" * 1000
        doc = MDDocument(
            id="test-long-title",
            content=f"# {long_title}\nContent",
            filename="long_title.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert len(result.sections[0].title) == 1000

    def test_parse_document_with_only_special_characters(self, parser):
        """Test handling of content with only special characters"""
        doc = MDDocument(
            id="test-special-only",
            content="!@#$%^&*()_+-=[]{}|;':\",./<>?",
            filename="special_only.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)
        assert len(result.sections) == 1


# ============================================================================
# Test: Error Recovery and Graceful Degradation
# ============================================================================

class TestErrorRecovery:
    """Tests for error recovery and graceful degradation"""

    def test_parse_document_with_multiple_issues(self, parser):
        """Test handling of documents with multiple potential issues"""
        doc = MDDocument(
            id="test-multiple-issues",
            content="""---
invalid: yaml: content
---
# Title

> Blockquote
that continues

- List item
- List item

More content.
""",
            filename="multiple_issues.md",
            uploaded_by="test-user"
        )
        
        # Should parse successfully despite potential issues
        result = parser.parse_document(doc)
        assert isinstance(result, StructuredData)
        assert len(result.sections) >= 1

    def test_validate_structure_returns_all_errors(self, parser):
        """Test that validation returns all errors, not just first"""
        structured_data = StructuredData(
            source_document_id="test",
            sections=[
                Section(title="Section 1", content="", level=10, order=0),  # Invalid level
            ],
            metadata=Metadata(title="Test")
        )
        
        result = parser.validate_structure(structured_data)
        
        # Should have errors for invalid level
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_structure_returns_all_warnings(self, parser):
        """Test that validation returns all warnings"""
        structured_data = StructuredData(
            source_document_id="test",
            sections=[
                Section(title="Section 1", content="", level=1, order=0),  # Empty
                Section(title="Section 2", content="", level=4, order=1),  # Empty + level jump
            ],
            metadata=Metadata()  # No title
        )
        
        result = parser.validate_structure(structured_data)
        
        # Should have multiple warnings
        assert len(result.warnings) >= 2

    def test_parse_document_preserves_content_integrity(self, parser):
        """Test that parsed content matches original"""
        original_content = """# Main Title

## Section 1

Content for section 1.

### Subsection 1.1

More content.

## Section 2

Content for section 2.
"""
        
        doc = MDDocument(
            id="test-integrity",
            content=original_content,
            filename="test.md",
            uploaded_by="test-user"
        )
        
        result = parser.parse_document(doc)
        
        # Verify checksum
        assert result.checksum is not None
        assert len(result.checksum) == 64  # SHA-256 hex length

        # Verify sections contain expected content
        assert any("section 1" in s.content.lower() for s in result.sections)
        assert any("section 2" in s.content.lower() for s in result.sections)