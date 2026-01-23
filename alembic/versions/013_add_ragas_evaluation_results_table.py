"""Add ragas_evaluation_results table

Revision ID: 013_ragas_eval
Revises: 012_add_admin_configuration_tables
Create Date: 2026-01-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013_ragas_eval'
down_revision = None  # Will be set during migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ragas_evaluation_results table."""
    # Check if we're using PostgreSQL or SQLite
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    
    if is_postgresql:
        # PostgreSQL with JSONB support
        op.create_table(
            'ragas_evaluation_results',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('task_id', sa.String(100), nullable=True, index=True),
            sa.Column('annotation_ids', postgresql.JSONB(), nullable=False, server_default='[]'),
            sa.Column('metrics', postgresql.JSONB(), nullable=False, server_default='{}'),
            sa.Column('scores', postgresql.JSONB(), nullable=False, server_default='{}'),
            sa.Column('overall_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
            sa.Column('metadata', postgresql.JSONB(), nullable=True),
        )
        
        # Create additional indexes for common queries
        op.create_index(
            'ix_ragas_evaluation_results_task_created',
            'ragas_evaluation_results',
            ['task_id', 'created_at']
        )
        
        op.create_index(
            'ix_ragas_evaluation_results_overall_score',
            'ragas_evaluation_results',
            ['overall_score']
        )
    else:
        # SQLite with JSON support
        op.create_table(
            'ragas_evaluation_results',
            sa.Column('id', sa.String(100), primary_key=True),
            sa.Column('task_id', sa.String(100), nullable=True, index=True),
            sa.Column('annotation_ids', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('metrics', sa.JSON(), nullable=False, server_default='{}'),
            sa.Column('scores', sa.JSON(), nullable=False, server_default='{}'),
            sa.Column('overall_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
            sa.Column('metadata', sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    """Drop ragas_evaluation_results table."""
    # Drop indexes first (PostgreSQL only)
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    
    if is_postgresql:
        op.drop_index('ix_ragas_evaluation_results_overall_score', table_name='ragas_evaluation_results')
        op.drop_index('ix_ragas_evaluation_results_task_created', table_name='ragas_evaluation_results')
    
    op.drop_table('ragas_evaluation_results')
