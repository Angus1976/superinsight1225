"""
Test for LLMHealthStatus migration structure.

This test verifies that the migration file is correctly structured
and matches the model definition.
"""

import pytest
import importlib.util
import sys
from pathlib import Path

# Load the migration module dynamically since it starts with a number
migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "016_add_llm_health_status_table.py"
spec = importlib.util.spec_from_file_location("migration_module", migration_path)
migration = importlib.util.module_from_spec(spec)
sys.modules["migration_module"] = migration
spec.loader.exec_module(migration)


def test_migration_has_required_attributes():
    """Test that migration has all required attributes."""
    assert hasattr(migration, 'revision')
    assert hasattr(migration, 'down_revision')
    assert hasattr(migration, 'upgrade')
    assert hasattr(migration, 'downgrade')


def test_migration_revision_id():
    """Test that migration has correct revision ID."""
    assert migration.revision == '016_add_llm_health_status'


def test_migration_down_revision():
    """Test that migration has correct down revision."""
    assert migration.down_revision == '015_add_optimization_indexes'


def test_upgrade_function_exists():
    """Test that upgrade function is callable."""
    assert callable(migration.upgrade)


def test_downgrade_function_exists():
    """Test that downgrade function is callable."""
    assert callable(migration.downgrade)


def test_migration_docstring():
    """Test that migration has descriptive docstring."""
    assert migration.__doc__ is not None
    assert 'LLMHealthStatus' in migration.__doc__
    assert 'health monitoring' in migration.__doc__.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
