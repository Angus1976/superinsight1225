"""merge_all_heads

Revision ID: 2f6b0cbeb30c
Revises: 001_add_multi_tenant_support, 002_optimize_tenant_indexes, add_business_logic_001, sync_001
Create Date: 2026-01-10 22:02:39.912346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f6b0cbeb30c'
down_revision: Union[str, Sequence[str], None] = ('001_add_multi_tenant_support', '002_optimize_tenant_indexes', 'add_business_logic_001', 'sync_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
