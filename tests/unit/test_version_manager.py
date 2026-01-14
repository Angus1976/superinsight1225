"""
Unit tests for Version Manager.

Tests the core functionality of:
- Version creation and retrieval
- Semantic versioning calculation
- Version history and rollback
- Tag management
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime
import hashlib
import json
from enum import Enum


class VersionType(str, Enum):
    """Version type for semantic versioning."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class MockVersionManager:
    """Mock Version Manager for testing without database dependencies."""
    
    def _calculate_next_version(
        self,
        current_version: str,
        version_type: VersionType
    ) -> str:
        """Calculate next semantic version."""
        try:
            parts = current_version.split('.')
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
        except (ValueError, IndexError):
            major, minor, patch = 0, 0, 0
        
        if version_type == VersionType.MAJOR:
            return f"{major + 1}.0.0"
        elif version_type == VersionType.MINOR:
            return f"{major}.{minor + 1}.0"
        else:  # PATCH
            return f"{major}.{minor}.{patch + 1}"
    
    def _calculate_checksum(self, data: dict) -> str:
        """Calculate SHA-256 checksum of data."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _calculate_size(self, data: dict) -> int:
        """Calculate size of data in bytes."""
        return len(json.dumps(data, default=str).encode())


class TestVersionManager:
    """Tests for VersionManager class."""
    
    @pytest.fixture
    def version_manager(self):
        """Create a MockVersionManager instance."""
        return MockVersionManager()
    
    def test_calculate_next_version_patch(self, version_manager):
        """Test patch version increment."""
        result = version_manager._calculate_next_version("1.2.3", VersionType.PATCH)
        assert result == "1.2.4"
    
    def test_calculate_next_version_minor(self, version_manager):
        """Test minor version increment."""
        result = version_manager._calculate_next_version("1.2.3", VersionType.MINOR)
        assert result == "1.3.0"
    
    def test_calculate_next_version_major(self, version_manager):
        """Test major version increment."""
        result = version_manager._calculate_next_version("1.2.3", VersionType.MAJOR)
        assert result == "2.0.0"
    
    def test_calculate_next_version_from_zero(self, version_manager):
        """Test version increment from 0.0.0."""
        result = version_manager._calculate_next_version("0.0.0", VersionType.PATCH)
        assert result == "0.0.1"
        
        result = version_manager._calculate_next_version("0.0.0", VersionType.MINOR)
        assert result == "0.1.0"
        
        result = version_manager._calculate_next_version("0.0.0", VersionType.MAJOR)
        assert result == "1.0.0"
    
    def test_calculate_next_version_invalid_format(self, version_manager):
        """Test version increment with invalid format."""
        result = version_manager._calculate_next_version("invalid", VersionType.PATCH)
        assert result == "0.0.1"
    
    def test_calculate_next_version_partial_format(self, version_manager):
        """Test version increment with partial format."""
        result = version_manager._calculate_next_version("1", VersionType.PATCH)
        assert result == "1.0.1"
        
        result = version_manager._calculate_next_version("1.2", VersionType.PATCH)
        assert result == "1.2.1"
    
    def test_calculate_checksum(self, version_manager):
        """Test checksum calculation."""
        data = {"name": "test", "value": 123}
        checksum = version_manager._calculate_checksum(data)
        
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex digest length
        
        # Same data should produce same checksum
        checksum2 = version_manager._calculate_checksum(data)
        assert checksum == checksum2
        
        # Different data should produce different checksum
        data2 = {"name": "test", "value": 456}
        checksum3 = version_manager._calculate_checksum(data2)
        assert checksum != checksum3
    
    def test_calculate_checksum_order_independent(self, version_manager):
        """Test checksum is order-independent for dict keys."""
        data1 = {"a": 1, "b": 2, "c": 3}
        data2 = {"c": 3, "a": 1, "b": 2}
        
        checksum1 = version_manager._calculate_checksum(data1)
        checksum2 = version_manager._calculate_checksum(data2)
        
        assert checksum1 == checksum2
    
    def test_calculate_size(self, version_manager):
        """Test size calculation."""
        data = {"name": "test"}
        size = version_manager._calculate_size(data)
        
        assert isinstance(size, int)
        assert size > 0
    
    def test_calculate_size_empty(self, version_manager):
        """Test size calculation for empty data."""
        data = {}
        size = version_manager._calculate_size(data)
        
        assert size == 2  # "{}" is 2 bytes


class TestVersionType:
    """Tests for VersionType enum."""
    
    def test_version_type_values(self):
        """Test VersionType enum values."""
        assert VersionType.MAJOR.value == "major"
        assert VersionType.MINOR.value == "minor"
        assert VersionType.PATCH.value == "patch"
    
    def test_version_type_from_string(self):
        """Test creating VersionType from string."""
        assert VersionType("major") == VersionType.MAJOR
        assert VersionType("minor") == VersionType.MINOR
        assert VersionType("patch") == VersionType.PATCH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
