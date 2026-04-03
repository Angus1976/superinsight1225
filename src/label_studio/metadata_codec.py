"""
Metadata Codec for Label Studio Enterprise Workspace.

This module provides encoding and decoding functionality for embedding
workspace metadata in Label Studio project descriptions.

Encoding Format:
    [SUPERINSIGHT_META:<base64-encoded-json>]<original-description>

Example:
    [SUPERINSIGHT_META:eyJ3b3Jrc3BhY2VfaWQiOiAiMTIzIn0=]研发部门项目描述

Metadata Structure:
    {
        "workspace_id": "uuid-string",
        "workspace_name": "研发部门",
        "created_by": "user-id",
        "created_at": "2026-01-29T10:00:00",
        "_version": "1.0"
    }
"""

import base64
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Constants
METADATA_PREFIX = "[SUPERINSIGHT_META:"
METADATA_SUFFIX = "]"
METADATA_VERSION = "1.0"

# Regex pattern to extract metadata from text
# Pattern: [SUPERINSIGHT_META:<base64>]<rest>
METADATA_PATTERN = re.compile(
    r'^\[SUPERINSIGHT_META:([A-Za-z0-9+/=]+)\](.*)$',
    re.DOTALL
)


@dataclass
class WorkspaceMetadata:
    """
    Workspace metadata structure for encoding/decoding.

    Attributes:
        workspace_id: UUID of the workspace
        workspace_name: Name of the workspace
        created_by: User ID who created the project
        created_at: ISO timestamp when metadata was created
        _version: Metadata format version (default: "1.0")
    """
    workspace_id: str
    workspace_name: str
    created_by: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    _version: str = METADATA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceMetadata":
        """Create metadata from dictionary."""
        return cls(
            workspace_id=data.get("workspace_id", ""),
            workspace_name=data.get("workspace_name", ""),
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            _version=data.get("_version", METADATA_VERSION)
        )


class MetadataCodecError(Exception):
    """Base exception for metadata codec errors."""
    pass


class MetadataDecodeError(MetadataCodecError):
    """Exception raised when metadata decoding fails."""
    pass


class MetadataEncodeError(MetadataCodecError):
    """Exception raised when metadata encoding fails."""
    pass


class MetadataCodec:
    """
    Encoder/decoder for workspace metadata in project descriptions.

    This class provides methods to embed workspace metadata into Label Studio
    project descriptions and extract it back, preserving the original text.

    Thread-safe: All methods are stateless and can be called from multiple threads.

    Example Usage:
        codec = MetadataCodec()

        # Encode metadata into description
        metadata = WorkspaceMetadata(
            workspace_id="123",
            workspace_name="研发部门",
            created_by="user-456"
        )
        encoded = codec.encode("项目描述", metadata)
        # Result: "[SUPERINSIGHT_META:eyJ3b3Jrc3BhY2VfaWQiOi...=]项目描述"

        # Decode metadata from description
        original_text, decoded_metadata = codec.decode(encoded)
        # original_text: "项目描述"
        # decoded_metadata: WorkspaceMetadata(...)

        # Check if text has metadata
        has_meta = codec.has_metadata(encoded)  # True
    """

    def encode(
        self,
        original_text: str,
        metadata: WorkspaceMetadata
    ) -> str:
        """
        Encode metadata into text.

        Embeds workspace metadata as a Base64-encoded JSON prefix into the
        original text.

        Args:
            original_text: Original text to prepend metadata to (can be empty)
            metadata: WorkspaceMetadata object to encode

        Returns:
            Encoded text with metadata prefix

        Raises:
            MetadataEncodeError: If encoding fails

        Example:
            >>> codec = MetadataCodec()
            >>> meta = WorkspaceMetadata("ws-1", "Dev", "user-1")
            >>> result = codec.encode("Description", meta)
            >>> result.startswith("[SUPERINSIGHT_META:")
            True
        """
        try:
            # Convert metadata to JSON string (ensure UTF-8 for Chinese support)
            metadata_dict = metadata.to_dict()
            json_str = json.dumps(metadata_dict, ensure_ascii=False, separators=(',', ':'))

            # Base64 encode the JSON string
            # Use UTF-8 encoding to support Chinese characters
            json_bytes = json_str.encode('utf-8')
            base64_str = base64.b64encode(json_bytes).decode('ascii')

            # Construct the encoded text
            encoded_text = f"{METADATA_PREFIX}{base64_str}{METADATA_SUFFIX}{original_text or ''}"

            logger.debug(f"Encoded metadata for workspace '{metadata.workspace_name}'")
            return encoded_text

        except Exception as e:
            logger.error(f"Failed to encode metadata: {e}")
            raise MetadataEncodeError(f"Failed to encode metadata: {e}") from e

    def decode(
        self,
        encoded_text: str
    ) -> Tuple[str, Optional[WorkspaceMetadata]]:
        """
        Decode metadata from text.

        Extracts workspace metadata from the text prefix and returns the
        original text along with the decoded metadata.

        Args:
            encoded_text: Text that may contain metadata prefix

        Returns:
            Tuple of (original_text, metadata):
            - original_text: The text without the metadata prefix
            - metadata: WorkspaceMetadata object if found, None otherwise

        Raises:
            MetadataDecodeError: If metadata is present but corrupted

        Example:
            >>> codec = MetadataCodec()
            >>> text, meta = codec.decode("[SUPERINSIGHT_META:eyJ3b3...=]Desc")
            >>> text
            'Desc'
            >>> meta.workspace_id
            'ws-1'
        """
        if not encoded_text:
            return "", None

        # Check if text starts with metadata prefix
        match = METADATA_PATTERN.match(encoded_text)

        if not match:
            # Text looks like it might contain our prefix but does not match the
            # full pattern (e.g. corrupted Base64 block). Treat this as
            # corrupted metadata rather than plain text so callers can surface
            # a decoding error, while ``try_decode`` will safely swallow it.
            if encoded_text.startswith(METADATA_PREFIX):
                raise MetadataDecodeError("Corrupted metadata: invalid prefix format")
            # No metadata prefix found, return original text
            return encoded_text, None

        try:
            # Extract Base64 string and original text
            base64_str = match.group(1)
            original_text = match.group(2)

            # Decode Base64 to JSON bytes
            json_bytes = base64.b64decode(base64_str)

            # Decode JSON bytes to string (UTF-8 for Chinese support)
            json_str = json_bytes.decode('utf-8')

            # Parse JSON to dictionary
            metadata_dict = json.loads(json_str)

            # Create WorkspaceMetadata object
            metadata = WorkspaceMetadata.from_dict(metadata_dict)

            logger.debug(f"Decoded metadata for workspace '{metadata.workspace_name}'")
            return original_text, metadata

        except (base64.binascii.Error, json.JSONDecodeError) as e:
            logger.warning(f"Failed to decode metadata (corrupted data): {e}")
            raise MetadataDecodeError(f"Corrupted metadata: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error decoding metadata: {e}")
            raise MetadataDecodeError(f"Failed to decode metadata: {e}") from e

    def has_metadata(self, text: str) -> bool:
        """
        Check if text contains metadata prefix.

        This is a lightweight check that doesn't validate the metadata content,
        only checks if the metadata format is present.

        Args:
            text: Text to check for metadata prefix

        Returns:
            True if text contains valid metadata prefix format, False otherwise

        Example:
            >>> codec = MetadataCodec()
            >>> codec.has_metadata("[SUPERINSIGHT_META:abc=]text")
            True
            >>> codec.has_metadata("plain text")
            False
        """
        if not text:
            return False

        return text.startswith(METADATA_PREFIX) and METADATA_PATTERN.match(text) is not None

    def encode_dict(
        self,
        original_text: str,
        metadata_dict: Dict[str, Any]
    ) -> str:
        """
        Encode metadata dictionary into text.

        Convenience method that accepts a dictionary instead of WorkspaceMetadata.

        Args:
            original_text: Original text to prepend metadata to
            metadata_dict: Dictionary containing metadata fields

        Returns:
            Encoded text with metadata prefix

        Raises:
            MetadataEncodeError: If encoding fails
        """
        metadata = WorkspaceMetadata.from_dict(metadata_dict)
        return self.encode(original_text, metadata)

    def decode_to_dict(
        self,
        encoded_text: str
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Decode metadata from text and return as dictionary.

        Convenience method that returns metadata as a dictionary instead of
        WorkspaceMetadata object.

        Args:
            encoded_text: Text that may contain metadata prefix

        Returns:
            Tuple of (original_text, metadata_dict):
            - original_text: The text without the metadata prefix
            - metadata_dict: Dictionary if metadata found, None otherwise

        Raises:
            MetadataDecodeError: If metadata is present but corrupted
        """
        original_text, metadata = self.decode(encoded_text)

        if metadata is None:
            return original_text, None

        return original_text, metadata.to_dict()

    def try_decode(
        self,
        encoded_text: str
    ) -> Tuple[str, Optional[WorkspaceMetadata]]:
        """
        Safely decode metadata from text, returning None on any error.

        Unlike decode(), this method never raises exceptions. If metadata
        is corrupted or cannot be decoded, it returns the original text
        with None metadata.

        Args:
            encoded_text: Text that may contain metadata prefix

        Returns:
            Tuple of (text, metadata) where metadata is None if not found or corrupted

        Example:
            >>> codec = MetadataCodec()
            >>> # Corrupted metadata
            >>> text, meta = codec.try_decode("[SUPERINSIGHT_META:!!!]text")
            >>> text
            '[SUPERINSIGHT_META:!!!]text'
            >>> meta is None
            True
        """
        try:
            return self.decode(encoded_text)
        except MetadataDecodeError:
            logger.warning(f"Could not decode metadata, returning original text")
            return encoded_text, None


# Singleton instance for convenience
_codec_instance: Optional[MetadataCodec] = None


def get_metadata_codec() -> MetadataCodec:
    """
    Get the singleton MetadataCodec instance.

    Returns:
        MetadataCodec singleton instance

    Example:
        codec = get_metadata_codec()
        encoded = codec.encode("text", metadata)
    """
    global _codec_instance
    if _codec_instance is None:
        _codec_instance = MetadataCodec()
    return _codec_instance


# Convenience functions for quick access
def encode_metadata(
    original_text: str,
    workspace_id: str,
    workspace_name: str,
    created_by: str,
    created_at: Optional[str] = None
) -> str:
    """
    Convenience function to encode metadata into text.

    Args:
        original_text: Original description text
        workspace_id: Workspace UUID
        workspace_name: Workspace name
        created_by: User ID who created the project
        created_at: Optional ISO timestamp (default: current time)

    Returns:
        Encoded text with metadata prefix
    """
    metadata = WorkspaceMetadata(
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        created_by=created_by,
        created_at=created_at or datetime.utcnow().isoformat()
    )
    return get_metadata_codec().encode(original_text, metadata)


def decode_metadata(
    encoded_text: str
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Convenience function to decode metadata from text.

    Args:
        encoded_text: Text that may contain metadata prefix

    Returns:
        Tuple of (original_text, metadata_dict)
    """
    return get_metadata_codec().decode_to_dict(encoded_text)


def has_metadata(text: str) -> bool:
    """
    Convenience function to check if text has metadata.

    Args:
        text: Text to check

    Returns:
        True if metadata prefix is present
    """
    return get_metadata_codec().has_metadata(text)
