"""Add security and audit tables

Revision ID: security_001
Revises: d01fd5049733
Create Date: 2024-12-21 10:00:00.000000

Legacy migration: ``users`` / ``audit_logs`` etc. are created by ``000_core_tables``
and newer security migrations. Kept as no-op for revision graph continuity.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'security_001'
down_revision = 'd01fd5049733'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
