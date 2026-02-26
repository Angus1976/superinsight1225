"""Merge structuring and task migration heads

Revision ID: 023_merge_heads
Revises: 022_add_structuring, 59d283c3c4aa
Create Date: 2026-02-26
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '023_merge_heads'
down_revision: Union[str, Sequence[str], None] = ('022_add_structuring', '59d283c3c4aa')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
