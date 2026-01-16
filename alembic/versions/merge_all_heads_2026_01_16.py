"""Merge all heads into single head

Revision ID: merge_2026_01_16
Revises: 006_add_rbac_tables, 007_add_audit_integrity_support, 012_add_admin_config, 20260113_security, 20260113_mtw, sync_pipeline_001, text_to_sql_001, cf61a2f229a1
Create Date: 2026-01-16

This migration merges all existing heads into a single head.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_2026_01_16'
down_revision: Union[str, Sequence[str], None] = (
    '000_core_tables',
    '006_add_rbac_tables',
    '007_add_audit_integrity_support', 
    '012_add_admin_config',
    '20260113_security',
    '20260113_mtw',
    'sync_pipeline_001',
    'text_to_sql_001',
    'cf61a2f229a1',
    'version_lineage_002'
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge migration - no schema changes."""
    pass


def downgrade() -> None:
    """Merge migration - no schema changes."""
    pass
