"""Add API key and call log tables

Revision ID: 033_add_api_key_and_call_log_tables
Revises: 032_extend_sync_models_for_bidirectional_sync
Create Date: 2026-03-16 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '033_add_api_key_and_call_log_tables'
down_revision = '032_extend_sync_models_for_bidirectional_sync'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create api_keys and api_call_logs tables."""
    
    # Create APIKeyStatus enum
    op.execute("""
        CREATE TYPE apikeystatustype AS ENUM ('active', 'disabled', 'revoked')
    """)
    
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('key_prefix', sa.String(16), nullable=False),
        sa.Column('key_hash', sa.String(128), nullable=False, unique=True),
        sa.Column('scopes', JSONB, nullable=False, server_default='{}'),
        sa.Column('rate_limit_per_minute', sa.Integer, nullable=False, server_default='60'),
        sa.Column('rate_limit_per_day', sa.Integer, nullable=False, server_default='10000'),
        sa.Column('status', sa.Enum('active', 'disabled', 'revoked', name='apikeystatustype'), 
                  nullable=False, server_default='active'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_calls', sa.BigInteger, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=True),
    )
    
    # Create indexes for api_keys
    op.create_index('idx_api_keys_tenant_status', 'api_keys', ['tenant_id', 'status'])
    op.create_index('idx_api_keys_key_hash', 'api_keys', ['key_hash'])
    
    # Create api_call_logs table
    op.create_table(
        'api_call_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('key_id', UUID(as_uuid=True), nullable=False),
        sa.Column('endpoint', sa.String(200), nullable=False),
        sa.Column('status_code', sa.Integer, nullable=False),
        sa.Column('response_time_ms', sa.Float, nullable=False),
        sa.Column('called_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['key_id'], ['api_keys.id'], name='fk_api_call_logs_key_id'),
    )
    
    # Create indexes for api_call_logs
    op.create_index('idx_api_call_logs_key_id', 'api_call_logs', ['key_id'])
    op.create_index('idx_api_call_logs_key_time', 'api_call_logs', ['key_id', 'called_at'])
    op.create_index('idx_api_call_logs_endpoint', 'api_call_logs', ['endpoint'])
    op.create_index('idx_api_call_logs_called_at', 'api_call_logs', ['called_at'])


def downgrade() -> None:
    """Drop api_keys and api_call_logs tables."""
    
    # Drop indexes for api_call_logs
    op.drop_index('idx_api_call_logs_endpoint', 'api_call_logs')
    op.drop_index('idx_api_call_logs_key_time', 'api_call_logs')
    op.drop_index('idx_api_call_logs_called_at', 'api_call_logs')
    op.drop_index('idx_api_call_logs_key_id', 'api_call_logs')
    
    # Drop api_call_logs table
    op.drop_table('api_call_logs')
    
    # Drop indexes for api_keys
    op.drop_index('idx_api_keys_key_hash', 'api_keys')
    op.drop_index('idx_api_keys_tenant_status', 'api_keys')
    
    # Drop api_keys table
    op.drop_table('api_keys')
    
    # Drop enum type
    op.execute('DROP TYPE apikeystatustype')
