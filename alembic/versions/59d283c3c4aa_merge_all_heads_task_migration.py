"""merge_all_heads_task_migration

Revision ID: 59d283c3c4aa
Revises: 013_ragas_eval, 020_add_extended_task_fields, merge_2026_01_16
Create Date: 2026-01-30 23:17:45.119139

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59d283c3c4aa'
down_revision: Union[str, Sequence[str], None] = ('013_ragas_eval', '020_add_extended_task_fields', 'merge_2026_01_16')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
