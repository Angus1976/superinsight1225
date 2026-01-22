"""Add LLMHealthStatus table for provider health monitoring

Revision ID: 016_add_llm_health_status
Revises: 015_add_optimization_indexes
Create Date: 2026-01-19

This migration adds the llm_health_status table for tracking LLM provider health:
- Monitors health status of LLM providers with automatic health checks
- Tracks consecutive failures and last error messages
- Provides indexes for efficient health monitoring queries
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '016_add_llm_health_status'
down_revision: Union[str, Sequence[str], None] = '015_add_optimization_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create llm_health_status table."""
    
    # Create llm_health_status table
    op.create_table(
        'llm_health_status',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('provider_id', UUID(as_uuid=True), sa.ForeignKey('llm_configurations.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('is_healthy', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('last_check_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('last_error', sa.String(500), nullable=True),
        sa.Column('consecutive_failures', sa.Integer, nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for health monitoring queries
    op.create_index('ix_llm_health_provider', 'llm_health_status', ['provider_id'])
    op.create_index('ix_llm_health_status', 'llm_health_status', ['is_healthy'])
    op.create_index('ix_llm_health_last_check', 'llm_health_status', ['last_check_at'])


def downgrade() -> None:
    """Drop llm_health_status table."""
    
    # Drop indexes and table
    op.drop_index('ix_llm_health_last_check', table_name='llm_health_status')
    op.drop_index('ix_llm_health_status', table_name='llm_health_status')
    op.drop_index('ix_llm_health_provider', table_name='llm_health_status')
    op.drop_table('llm_health_status')
