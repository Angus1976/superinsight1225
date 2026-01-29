"""
Unit tests for Label Studio Metadata Codec.

Tests the encoding and decoding of workspace metadata in project descriptions.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.label_studio.metadata_codec import (
    MetadataCodec,
    WorkspaceMetadata,
    MetadataDecodeError,
    MetadataEncodeError,
    get_metadata_codec,
    encode_metadata,
    decode_metadata,
    has_metadata,
    METADATA_PREFIX,
    METADATA_SUFFIX,
    METADATA_VERSION,
)


class TestWorkspaceMetadata:
    """Tests for WorkspaceMetadata dataclass."""

    def test_create_metadata(self):
        """Test creating WorkspaceMetadata with required fields."""
        metadata = WorkspaceMetadata(
            workspace_id="ws-123",
            workspace_name="研发部门",
            created_by="user-456"
        )

        assert metadata.workspace_id == "ws-123"
        assert metadata.workspace_name == "研发部门"
        assert metadata.created_by == "user-456"
        assert metadata._version == METADATA_VERSION
        assert metadata.created_at is not None

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = WorkspaceMetadata(
            workspace_id="ws-123",
            workspace_name="Test Workspace",
            created_by="user-456",
            created_at="2026-01-29T10:00:00"
        )

        result = metadata.to_dict()

        assert result["workspace_id"] == "ws-123"
        assert result["workspace_name"] == "Test Workspace"
        assert result["created_by"] == "user-456"
        assert result["created_at"] == "2026-01-29T10:00:00"
        assert result["_version"] == METADATA_VERSION

    def test_metadata_from_dict(self):
        """Test creating metadata from dictionary."""
        data = {
            "workspace_id": "ws-789",
            "workspace_name": "数据团队",
            "created_by": "user-abc",
            "created_at": "2026-01-29T12:00:00",
            "_version": "1.0"
        }

        metadata = WorkspaceMetadata.from_dict(data)

        assert metadata.workspace_id == "ws-789"
        assert metadata.workspace_name == "数据团队"
        assert metadata.created_by == "user-abc"
        assert metadata.created_at == "2026-01-29T12:00:00"

    def test_metadata_from_dict_with_missing_fields(self):
        """Test creating metadata from dictionary with missing optional fields."""
        data = {
            "workspace_id": "ws-minimal",
            "workspace_name": "Minimal",
            "created_by": "user-min"
        }

        metadata = WorkspaceMetadata.from_dict(data)

        assert metadata.workspace_id == "ws-minimal"
        assert metadata.workspace_name == "Minimal"
        assert metadata._version == METADATA_VERSION


class TestMetadataCodec:
    """Tests for MetadataCodec class."""

    @pytest.fixture
    def codec(self):
        """Create a MetadataCodec instance."""
        return MetadataCodec()

    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata for testing."""
        return WorkspaceMetadata(
            workspace_id=str(uuid4()),
            workspace_name="测试工作空间",
            created_by="test-user",
            created_at="2026-01-29T10:00:00"
        )

    # ========== Encode Tests ==========

    def test_encode_basic(self, codec, sample_metadata):
        """Test basic encoding of metadata."""
        original_text = "This is a project description"
        encoded = codec.encode(original_text, sample_metadata)

        assert encoded.startswith(METADATA_PREFIX)
        assert METADATA_SUFFIX in encoded
        assert original_text in encoded

    def test_encode_empty_text(self, codec, sample_metadata):
        """Test encoding with empty original text."""
        encoded = codec.encode("", sample_metadata)

        assert encoded.startswith(METADATA_PREFIX)
        assert encoded.endswith(METADATA_SUFFIX)

    def test_encode_chinese_text(self, codec, sample_metadata):
        """Test encoding with Chinese characters in original text."""
        original_text = "这是一个中文项目描述"
        encoded = codec.encode(original_text, sample_metadata)

        assert original_text in encoded
        assert encoded.startswith(METADATA_PREFIX)

    def test_encode_chinese_metadata(self, codec):
        """Test encoding with Chinese characters in metadata."""
        metadata = WorkspaceMetadata(
            workspace_id="ws-cn",
            workspace_name="研发部门工作空间",
            created_by="张三"
        )
        original_text = "项目描述"
        encoded = codec.encode(original_text, metadata)

        # Verify encoding succeeded
        assert encoded.startswith(METADATA_PREFIX)

        # Verify we can decode it back
        decoded_text, decoded_meta = codec.decode(encoded)
        assert decoded_text == original_text
        assert decoded_meta.workspace_name == "研发部门工作空间"
        assert decoded_meta.created_by == "张三"

    def test_encode_special_characters(self, codec, sample_metadata):
        """Test encoding with special characters in text."""
        original_text = "Description with special chars: <>&\"'[]{}()=+-*/"
        encoded = codec.encode(original_text, sample_metadata)

        decoded_text, _ = codec.decode(encoded)
        assert decoded_text == original_text

    def test_encode_multiline_text(self, codec, sample_metadata):
        """Test encoding with multiline text."""
        original_text = """Line 1
Line 2
Line 3"""
        encoded = codec.encode(original_text, sample_metadata)

        decoded_text, _ = codec.decode(encoded)
        assert decoded_text == original_text

    # ========== Decode Tests ==========

    def test_decode_basic(self, codec, sample_metadata):
        """Test basic decoding of metadata."""
        original_text = "Original description"
        encoded = codec.encode(original_text, sample_metadata)

        decoded_text, decoded_meta = codec.decode(encoded)

        assert decoded_text == original_text
        assert decoded_meta.workspace_id == sample_metadata.workspace_id
        assert decoded_meta.workspace_name == sample_metadata.workspace_name
        assert decoded_meta.created_by == sample_metadata.created_by

    def test_decode_no_metadata(self, codec):
        """Test decoding text without metadata prefix."""
        plain_text = "This is plain text without metadata"

        decoded_text, decoded_meta = codec.decode(plain_text)

        assert decoded_text == plain_text
        assert decoded_meta is None

    def test_decode_empty_text(self, codec):
        """Test decoding empty text."""
        decoded_text, decoded_meta = codec.decode("")

        assert decoded_text == ""
        assert decoded_meta is None

    def test_decode_none_returns_empty(self, codec):
        """Test decoding None returns empty string."""
        decoded_text, decoded_meta = codec.decode(None)

        assert decoded_text == ""
        assert decoded_meta is None

    def test_decode_corrupted_base64(self, codec):
        """Test decoding corrupted Base64 raises error."""
        corrupted = "[SUPERINSIGHT_META:!!!invalid!!!]Some text"

        with pytest.raises(MetadataDecodeError):
            codec.decode(corrupted)

    def test_decode_corrupted_json(self, codec):
        """Test decoding valid Base64 but invalid JSON raises error."""
        import base64
        invalid_json = base64.b64encode(b"not valid json").decode()
        corrupted = f"[SUPERINSIGHT_META:{invalid_json}]Some text"

        with pytest.raises(MetadataDecodeError):
            codec.decode(corrupted)

    def test_try_decode_corrupted(self, codec):
        """Test try_decode returns original text on corrupted data."""
        corrupted = "[SUPERINSIGHT_META:!!!invalid!!!]Some text"

        decoded_text, decoded_meta = codec.try_decode(corrupted)

        # Should return original text without raising
        assert decoded_text == corrupted
        assert decoded_meta is None

    # ========== has_metadata Tests ==========

    def test_has_metadata_true(self, codec, sample_metadata):
        """Test has_metadata returns True for encoded text."""
        encoded = codec.encode("Test", sample_metadata)

        assert codec.has_metadata(encoded) is True

    def test_has_metadata_false_plain_text(self, codec):
        """Test has_metadata returns False for plain text."""
        assert codec.has_metadata("Plain text") is False

    def test_has_metadata_false_empty(self, codec):
        """Test has_metadata returns False for empty text."""
        assert codec.has_metadata("") is False

    def test_has_metadata_false_none(self, codec):
        """Test has_metadata returns False for None."""
        assert codec.has_metadata(None) is False

    def test_has_metadata_partial_prefix(self, codec):
        """Test has_metadata returns False for partial prefix."""
        assert codec.has_metadata("[SUPERINSIGHT_META:") is False
        assert codec.has_metadata("[SUPERINSIGHT_") is False

    # ========== Roundtrip Tests ==========

    def test_encode_decode_roundtrip(self, codec, sample_metadata):
        """Test encoding and decoding produces same result."""
        original_text = "Complete roundtrip test"

        encoded = codec.encode(original_text, sample_metadata)
        decoded_text, decoded_meta = codec.decode(encoded)

        assert decoded_text == original_text
        assert decoded_meta.workspace_id == sample_metadata.workspace_id
        assert decoded_meta.workspace_name == sample_metadata.workspace_name

    def test_encode_decode_unicode_roundtrip(self, codec):
        """Test roundtrip with various Unicode characters."""
        metadata = WorkspaceMetadata(
            workspace_id="ws-unicode",
            workspace_name="工作空间 🚀",
            created_by="用户"
        )
        original_text = "描述 with émoji 🎉 and ñ and 日本語"

        encoded = codec.encode(original_text, metadata)
        decoded_text, decoded_meta = codec.decode(encoded)

        assert decoded_text == original_text
        assert decoded_meta.workspace_name == "工作空间 🚀"

    # ========== Convenience Method Tests ==========

    def test_encode_dict(self, codec):
        """Test encode_dict convenience method."""
        metadata_dict = {
            "workspace_id": "ws-dict",
            "workspace_name": "Dict Workspace",
            "created_by": "user-dict"
        }
        original_text = "Text"

        encoded = codec.encode_dict(original_text, metadata_dict)

        assert codec.has_metadata(encoded)
        decoded_text, decoded_meta = codec.decode(encoded)
        assert decoded_text == original_text
        assert decoded_meta.workspace_id == "ws-dict"

    def test_decode_to_dict(self, codec, sample_metadata):
        """Test decode_to_dict convenience method."""
        encoded = codec.encode("Text", sample_metadata)

        decoded_text, decoded_dict = codec.decode_to_dict(encoded)

        assert decoded_text == "Text"
        assert isinstance(decoded_dict, dict)
        assert decoded_dict["workspace_id"] == sample_metadata.workspace_id


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_metadata_codec_singleton(self):
        """Test get_metadata_codec returns same instance."""
        codec1 = get_metadata_codec()
        codec2 = get_metadata_codec()

        assert codec1 is codec2

    def test_encode_metadata_function(self):
        """Test encode_metadata convenience function."""
        encoded = encode_metadata(
            original_text="Description",
            workspace_id="ws-func",
            workspace_name="Func Workspace",
            created_by="user-func"
        )

        assert METADATA_PREFIX in encoded
        assert "Description" in encoded

    def test_decode_metadata_function(self):
        """Test decode_metadata convenience function."""
        encoded = encode_metadata(
            original_text="Test",
            workspace_id="ws-decode",
            workspace_name="Decode Test",
            created_by="user-test"
        )

        decoded_text, decoded_dict = decode_metadata(encoded)

        assert decoded_text == "Test"
        assert decoded_dict["workspace_id"] == "ws-decode"

    def test_has_metadata_function(self):
        """Test has_metadata convenience function."""
        encoded = encode_metadata(
            original_text="",
            workspace_id="ws",
            workspace_name="WS",
            created_by="u"
        )

        assert has_metadata(encoded) is True
        assert has_metadata("plain text") is False


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def codec(self):
        return MetadataCodec()

    def test_very_long_description(self, codec):
        """Test encoding/decoding very long descriptions."""
        metadata = WorkspaceMetadata("ws", "WS", "user")
        original_text = "A" * 10000  # 10,000 character description

        encoded = codec.encode(original_text, metadata)
        decoded_text, _ = codec.decode(encoded)

        assert decoded_text == original_text

    def test_metadata_with_special_json_chars(self, codec):
        """Test metadata with special JSON characters."""
        metadata = WorkspaceMetadata(
            workspace_id="ws-special",
            workspace_name='Name with "quotes" and \\backslash',
            created_by="user"
        )

        encoded = codec.encode("Text", metadata)
        _, decoded_meta = codec.decode(encoded)

        assert decoded_meta.workspace_name == 'Name with "quotes" and \\backslash'

    def test_text_that_looks_like_prefix(self, codec):
        """Test text that partially matches prefix pattern."""
        metadata = WorkspaceMetadata("ws", "WS", "user")
        original_text = "[SUPERINSIGHT something else"

        encoded = codec.encode(original_text, metadata)
        decoded_text, _ = codec.decode(encoded)

        assert decoded_text == original_text

    def test_nested_metadata_pattern(self, codec):
        """Test text containing another metadata pattern."""
        metadata = WorkspaceMetadata("ws", "WS", "user")
        original_text = "[SUPERINSIGHT_META:fake]inner text"

        encoded = codec.encode(original_text, metadata)
        decoded_text, decoded_meta = codec.decode(encoded)

        assert decoded_text == original_text
        assert decoded_meta.workspace_id == "ws"

    def test_whitespace_only_description(self, codec):
        """Test encoding whitespace-only description."""
        metadata = WorkspaceMetadata("ws", "WS", "user")
        original_text = "   \n\t  "

        encoded = codec.encode(original_text, metadata)
        decoded_text, _ = codec.decode(encoded)

        assert decoded_text == original_text

    def test_version_preserved(self, codec):
        """Test that version is preserved through encoding/decoding."""
        metadata = WorkspaceMetadata(
            workspace_id="ws",
            workspace_name="WS",
            created_by="user",
            _version="2.0"  # Custom version
        )

        encoded = codec.encode("Text", metadata)
        _, decoded_meta = codec.decode(encoded)

        assert decoded_meta._version == "2.0"


class TestPerformance:
    """Basic performance tests."""

    @pytest.fixture
    def codec(self):
        return MetadataCodec()

    def test_encode_performance(self, codec):
        """Test that encoding is reasonably fast."""
        import time
        metadata = WorkspaceMetadata("ws", "WS", "user")
        text = "Sample text" * 100

        start = time.time()
        for _ in range(1000):
            codec.encode(text, metadata)
        elapsed = time.time() - start

        # Should complete 1000 encodings in under 1 second
        assert elapsed < 1.0, f"Encoding took {elapsed}s for 1000 iterations"

    def test_decode_performance(self, codec):
        """Test that decoding is reasonably fast."""
        import time
        metadata = WorkspaceMetadata("ws", "WS", "user")
        encoded = codec.encode("Sample text" * 100, metadata)

        start = time.time()
        for _ in range(1000):
            codec.decode(encoded)
        elapsed = time.time() - start

        # Should complete 1000 decodings in under 1 second
        assert elapsed < 1.0, f"Decoding took {elapsed}s for 1000 iterations"
