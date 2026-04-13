"""Create initial database schema with documents, tasks, billing_records, and quality_issues tables

Revision ID: d01fd5049733
Revises: 000_core_tables
Create Date: 2025-12-21 00:05:27.354393

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd01fd5049733'
down_revision: Union[str, Sequence[str], None] = '000_core_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Legacy root — superseded by ``000_core_tables``. No-op for new installs."""
    pass


def downgrade() -> None:
    """No-op: legacy DDL not recreated."""
    pass
