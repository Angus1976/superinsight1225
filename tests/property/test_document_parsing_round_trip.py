"""
Property-Based Tests for Document Parsing Round-Trip

Tests Property 1: Document Parsing Round-Trip

For any valid MD document, parsing it into structured data and then storing
and retrieving it should preserve the content and metadata.

**Validates: Requirements 1.1, 1.2, 1.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from sqlalchemy.orm import Session

from src.services.md_document_parser import (
    MDDocumentParser,
    MDDocument,
    StructuredData,
    Section,
    Metadata
)
from src.models.data_lifecycle import (
    TempDataModel,
    DataState
)
from tests.conftest import db_session


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating valid heading levels (1-6)
heading_level_strategy = st.integers(min_value=1, max_value=6)

# Strategy for generating section titles
section_title_strategy = st.text(
    min_size=1,
    max_size=100,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
        blacklist_characters='\n\r\t'
    )
).filter(lambda x: x.strip())

# Strategy for generating section content
section_content_strategy = st.text(
    min_size=0,
    max_size=500,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Po'),
        blacklist_characters='\r\t'
    )
)

# Strategy for generating metadata fields
metadata_title_strategy = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=200).filter(lambda x: x.strip())
)

metadata_author_strategy = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
)

metadata_tags_strategy = st.lists(
    st.text(min_size=1, max_size=30, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        min_codepoint=ord('a'),
        max_codepoint=ord('z')
    )),
    min_size=0,
    max_size=10
)

metadata_description_strategy = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=300)
)

metadata_language_strategy = st.one_of(
    st.none(),
    st.sampled_from(['en', 'zh', 'es', 'fr', 'de', 'ja'])
)

# Strategy for generating filenames
filename_strategy = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        min_codepoint=ord('a'),
        max_codepoint=ord('z')
    )
).map(lambda x: f"{x}.md")

# Strategy for generating user IDs
user_id_strategy = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        min_codepoint=ord('a'),
        max_codepoint=ord('z')
    )
)


# ============================================================================
# Helper Functions
# ============================================================================

def generate_md_document_with_frontmatter(
    title: Optional[str],
    author: Optional[str],
    tags: List[str],
    description: Optional[str],
    language: Optional[str],
    sections: List[tuple[int, str, str]]
) -> str:
    """
    Generate MD document with YAML front matter and sections.
    
    Args:
        title: Document title
        author: Document author
        tags: List of tags
        description: Document description
        language: Document language
        sections: List of (level, title, content) tuples
    
    Returns:
        MD document content as string
    """
    lines = []
    
    # Add front matter if any metadata exists
    if any([title, author, tags, description, language]):
        lines.append("---")
        if title:
            lines.append(f"title: {title}")
        if author:
            lines.append(f"author: {author}")
        if tags:
            tags_str = ", ".join(tags)
            lines.append(f"tags: [{tags_str}]")
        if description:
            lines.append(f"description: {description}")
        if language:
            lines.append(f"language: {language}")
        lines.append("---")
        lines.append("")
    
    # Add sections
    for level, section_title, content in sections:
        heading = "#" * level
        lines.append(f"{heading} {section_title}")
        lines.append("")
        if content:
            lines.append(content)
            lines.append("")
    
    return "\n".join(lines)


def compare_metadata(original: Metadata, retrieved: Metadata) -> bool:
    """
    Compare two Metadata objects for equality.
    
    Args:
        original: Original metadata
        retrieved: Retrieved metadata
    
    Returns:
        True if metadata matches, False otherwise
    """
    # Compare title
    if original.title != retrieved.title:
        return False
    
    # Compare author
    if original.author != retrieved.author:
        return False
    
    # Compare tags (order doesn't matter)
    if set(original.tags) != set(retrieved.tags):
        return False
    
    # Compare description
    if original.description != retrieved.description:
        return False
    
    # Compare language
    if original.language != retrieved.language:
        return False
    
    return True


def compare_sections(original: List[Section], retrieved: List[Section]) -> bool:
    """
    Compare two lists of Section objects for equality.
    
    Args:
        original: Original sections
        retrieved: Retrieved sections
    
    Returns:
        True if sections match, False otherwise
    """
    if len(original) != len(retrieved):
        return False
    
    for orig, retr in zip(original, retrieved):
        if orig.title != retr.title:
            return False
        if orig.content != retr.content:
            return False
        if orig.level != retr.level:
            return False
        if orig.order != retr.order:
            return False
    
    return True


# ============================================================================
# Property 1: Document Parsing Round-Trip
# **Validates: Requirements 1.1, 1.2, 1.3**
# ============================================================================

@pytest.mark.property
class TestDocumentParsingRoundTrip:
    """
    Property 1: Document Parsing Round-Trip
    
    For any valid MD document, parsing it into structured data and then
    storing and retrieving it should preserve the content and metadata.
    """
    
    @given(
        title=metadata_title_strategy,
        author=metadata_author_strategy,
        tags=metadata_tags_strategy,
        description=metadata_description_strategy,
        language=metadata_language_strategy,
        filename=filename_strategy,
        uploaded_by=user_id_strategy,
        sections=st.lists(
            st.tuples(
                heading_level_strategy,
                section_title_strategy,
                section_content_strategy
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_parse_store_retrieve_preserves_content(
        self,
        db_session: Session,
        title: Optional[str],
        author: Optional[str],
        tags: List[str],
        description: Optional[str],
        language: Optional[str],
        filename: str,
        uploaded_by: str,
        sections: List[tuple[int, str, str]]
    ):
        """
        Property: Parsing, storing, and retrieving preserves content and metadata.
        
        For any valid MD document:
        1. Parse it into structured data
        2. Store it in the temporary table
        3. Retrieve it from the database
        4. The retrieved content and metadata should match the original
        """
        # Generate MD document content
        md_content = generate_md_document_with_frontmatter(
            title=title,
            author=author,
            tags=tags,
            description=description,
            language=language,
            sections=sections
        )
        
        # Skip empty documents
        assume(md_content.strip())
        
        # Create MD document
        md_document = MDDocument(
            content=md_content,
            filename=filename,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow()
        )
        
        # Parse document
        parser = MDDocumentParser()
        try:
            structured_data = parser.parse_document(md_document)
        except ValueError:
            # Skip documents that fail parsing validation
            assume(False)
        
        # Validate structure
        validation_result = parser.validate_structure(structured_data)
        assume(validation_result.is_valid)
        
        # Store in temporary table
        temp_data = TempDataModel(
            id=uuid4(),
            source_document_id=structured_data.source_document_id,
            content={
                'sections': [s.model_dump() for s in structured_data.sections],
                'checksum': structured_data.checksum,
                'parsed_at': structured_data.parsed_at.isoformat()
            },
            state=DataState.TEMP_STORED,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            metadata_={
                'filename': filename,
                'title': structured_data.metadata.title,
                'author': structured_data.metadata.author,
                'tags': structured_data.metadata.tags,
                'description': structured_data.metadata.description,
                'language': structured_data.metadata.language,
                'sections_count': len(structured_data.sections)
            }
        )
        
        db_session.add(temp_data)
        db_session.commit()
        db_session.refresh(temp_data)
        
        # Retrieve from database
        retrieved_temp_data = db_session.query(TempDataModel).filter_by(
            id=temp_data.id
        ).first()
        
        assert retrieved_temp_data is not None, "Temp data should be retrievable"
        
        # Reconstruct structured data from retrieved content
        retrieved_sections = [
            Section(**section_dict)
            for section_dict in retrieved_temp_data.content['sections']
        ]
        
        retrieved_metadata = Metadata(
            title=retrieved_temp_data.metadata_.get('title'),
            author=retrieved_temp_data.metadata_.get('author'),
            tags=retrieved_temp_data.metadata_.get('tags', []),
            description=retrieved_temp_data.metadata_.get('description'),
            language=retrieved_temp_data.metadata_.get('language')
        )
        
        # Assert: Sections should be preserved
        assert compare_sections(structured_data.sections, retrieved_sections), (
            f"Sections should be preserved. "
            f"Original: {[(s.title, s.level, s.order) for s in structured_data.sections]}, "
            f"Retrieved: {[(s.title, s.level, s.order) for s in retrieved_sections]}"
        )
        
        # Assert: Metadata should be preserved
        assert compare_metadata(structured_data.metadata, retrieved_metadata), (
            f"Metadata should be preserved. "
            f"Original: title={structured_data.metadata.title}, "
            f"author={structured_data.metadata.author}, "
            f"tags={structured_data.metadata.tags}, "
            f"Retrieved: title={retrieved_metadata.title}, "
            f"author={retrieved_metadata.author}, "
            f"tags={retrieved_metadata.tags}"
        )
        
        # Assert: Checksum should be preserved
        assert retrieved_temp_data.content['checksum'] == structured_data.checksum, (
            f"Checksum should be preserved. "
            f"Original: {structured_data.checksum}, "
            f"Retrieved: {retrieved_temp_data.content['checksum']}"
        )
        
        # Assert: Source document ID should be preserved
        assert retrieved_temp_data.source_document_id == structured_data.source_document_id, (
            f"Source document ID should be preserved. "
            f"Original: {structured_data.source_document_id}, "
            f"Retrieved: {retrieved_temp_data.source_document_id}"
        )
    
    @given(
        filename=filename_strategy,
        uploaded_by=user_id_strategy,
        sections=st.lists(
            st.tuples(
                heading_level_strategy,
                section_title_strategy,
                section_content_strategy
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_parse_store_retrieve_preserves_section_order(
        self,
        db_session: Session,
        filename: str,
        uploaded_by: str,
        sections: List[tuple[int, str, str]]
    ):
        """
        Property: Section order is preserved through parse-store-retrieve cycle.
        
        The order of sections in the original document should be preserved
        after parsing, storing, and retrieving.
        """
        # Generate MD document without front matter
        md_content = generate_md_document_with_frontmatter(
            title=None,
            author=None,
            tags=[],
            description=None,
            language=None,
            sections=sections
        )
        
        assume(md_content.strip())
        
        # Create and parse document
        md_document = MDDocument(
            content=md_content,
            filename=filename,
            uploaded_by=uploaded_by
        )
        
        parser = MDDocumentParser()
        try:
            structured_data = parser.parse_document(md_document)
        except ValueError:
            assume(False)
        
        # Store in database
        temp_data = TempDataModel(
            id=uuid4(),
            source_document_id=structured_data.source_document_id,
            content={
                'sections': [s.model_dump() for s in structured_data.sections],
                'checksum': structured_data.checksum,
                'parsed_at': structured_data.parsed_at.isoformat()
            },
            state=DataState.TEMP_STORED,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            metadata_={}
        )
        
        db_session.add(temp_data)
        db_session.commit()
        db_session.refresh(temp_data)
        
        # Retrieve and reconstruct
        retrieved_temp_data = db_session.query(TempDataModel).filter_by(
            id=temp_data.id
        ).first()
        
        retrieved_sections = [
            Section(**section_dict)
            for section_dict in retrieved_temp_data.content['sections']
        ]
        
        # Assert: Section count should match
        assert len(retrieved_sections) == len(structured_data.sections), (
            f"Section count should be preserved. "
            f"Original: {len(structured_data.sections)}, "
            f"Retrieved: {len(retrieved_sections)}"
        )
        
        # Assert: Section order should be preserved
        for i, (orig, retr) in enumerate(zip(structured_data.sections, retrieved_sections)):
            assert orig.order == retr.order == i, (
                f"Section {i} order should be {i}. "
                f"Original: {orig.order}, Retrieved: {retr.order}"
            )
    
    @given(
        title=metadata_title_strategy,
        tags=metadata_tags_strategy,
        filename=filename_strategy,
        uploaded_by=user_id_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_parse_store_retrieve_preserves_metadata_tags(
        self,
        db_session: Session,
        title: Optional[str],
        tags: List[str],
        filename: str,
        uploaded_by: str
    ):
        """
        Property: Metadata tags are preserved (order-independent).
        
        Tags should be preserved through the parse-store-retrieve cycle,
        regardless of their order.
        """
        # Generate simple document with tags
        md_content = generate_md_document_with_frontmatter(
            title=title,
            author=None,
            tags=tags,
            description=None,
            language=None,
            sections=[(1, "Test Section", "Test content")]
        )
        
        assume(md_content.strip())
        
        # Create and parse document
        md_document = MDDocument(
            content=md_content,
            filename=filename,
            uploaded_by=uploaded_by
        )
        
        parser = MDDocumentParser()
        try:
            structured_data = parser.parse_document(md_document)
        except ValueError:
            assume(False)
        
        # Store in database
        temp_data = TempDataModel(
            id=uuid4(),
            source_document_id=structured_data.source_document_id,
            content={
                'sections': [s.model_dump() for s in structured_data.sections],
                'checksum': structured_data.checksum,
                'parsed_at': structured_data.parsed_at.isoformat()
            },
            state=DataState.TEMP_STORED,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            metadata_={
                'title': structured_data.metadata.title,
                'tags': structured_data.metadata.tags
            }
        )
        
        db_session.add(temp_data)
        db_session.commit()
        db_session.refresh(temp_data)
        
        # Retrieve
        retrieved_temp_data = db_session.query(TempDataModel).filter_by(
            id=temp_data.id
        ).first()
        
        retrieved_tags = retrieved_temp_data.metadata_.get('tags', [])
        
        # Assert: Tags should be preserved (order-independent)
        assert set(structured_data.metadata.tags) == set(retrieved_tags), (
            f"Tags should be preserved. "
            f"Original: {set(structured_data.metadata.tags)}, "
            f"Retrieved: {set(retrieved_tags)}"
        )
    
    def test_parse_store_retrieve_with_unicode_content(self, db_session: Session):
        """
        Property: Unicode content is preserved through parse-store-retrieve cycle.
        
        Documents with Unicode characters (Chinese, emoji, etc.) should be
        preserved correctly.
        """
        # Create document with Unicode content
        md_content = """---
title: 测试文档
author: 张三
tags: [中文, 测试, Unicode]
---

# 介绍

这是一个包含中文内容的测试文档。

## 详细信息

包含表情符号: 😀 🎉 ✨

## 结论

测试完成。
"""
        
        md_document = MDDocument(
            content=md_content,
            filename="unicode_test.md",
            uploaded_by="test_user"
        )
        
        # Parse
        parser = MDDocumentParser()
        structured_data = parser.parse_document(md_document)
        
        # Store
        temp_data = TempDataModel(
            id=uuid4(),
            source_document_id=structured_data.source_document_id,
            content={
                'sections': [s.model_dump() for s in structured_data.sections],
                'checksum': structured_data.checksum,
                'parsed_at': structured_data.parsed_at.isoformat()
            },
            state=DataState.TEMP_STORED,
            uploaded_by="test_user",
            uploaded_at=datetime.utcnow(),
            metadata_={
                'title': structured_data.metadata.title,
                'author': structured_data.metadata.author,
                'tags': structured_data.metadata.tags
            }
        )
        
        db_session.add(temp_data)
        db_session.commit()
        db_session.refresh(temp_data)
        
        # Retrieve
        retrieved_temp_data = db_session.query(TempDataModel).filter_by(
            id=temp_data.id
        ).first()
        
        # Assert: Unicode metadata preserved
        assert retrieved_temp_data.metadata_['title'] == "测试文档"
        assert retrieved_temp_data.metadata_['author'] == "张三"
        assert "中文" in retrieved_temp_data.metadata_['tags']
        
        # Assert: Unicode section content preserved
        retrieved_sections = [
            Section(**s) for s in retrieved_temp_data.content['sections']
        ]
        
        assert retrieved_sections[0].title == "介绍"
        assert "中文内容" in retrieved_sections[0].content
        assert "😀" in retrieved_sections[1].content
    
    def test_parse_store_retrieve_with_code_blocks(self, db_session: Session):
        """
        Property: Code blocks are preserved through parse-store-retrieve cycle.
        
        Documents with code blocks should preserve the code content exactly.
        """
        md_content = """# Code Example

Here's some Python code:

```python
def hello_world():
    print("Hello, World!")
    return 42
```

And some JSON:

```json
{
  "key": "value",
  "number": 123
}
```
"""
        
        md_document = MDDocument(
            content=md_content,
            filename="code_test.md",
            uploaded_by="test_user"
        )
        
        # Parse
        parser = MDDocumentParser()
        structured_data = parser.parse_document(md_document)
        
        # Store
        temp_data = TempDataModel(
            id=uuid4(),
            source_document_id=structured_data.source_document_id,
            content={
                'sections': [s.model_dump() for s in structured_data.sections],
                'checksum': structured_data.checksum,
                'parsed_at': structured_data.parsed_at.isoformat()
            },
            state=DataState.TEMP_STORED,
            uploaded_by="test_user",
            uploaded_at=datetime.utcnow(),
            metadata_={}
        )
        
        db_session.add(temp_data)
        db_session.commit()
        db_session.refresh(temp_data)
        
        # Retrieve
        retrieved_temp_data = db_session.query(TempDataModel).filter_by(
            id=temp_data.id
        ).first()
        
        retrieved_sections = [
            Section(**s) for s in retrieved_temp_data.content['sections']
        ]
        
        # Assert: Code blocks preserved
        assert "```python" in retrieved_sections[0].content
        assert "def hello_world():" in retrieved_sections[0].content
        assert "```json" in retrieved_sections[0].content
        assert '"key": "value"' in retrieved_sections[0].content
