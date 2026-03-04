"""Add LLM application binding tables

Revision ID: 009_llm_app_binding
Revises: ai_annotation_001
Create Date: 2026-03-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '009_llm_app_binding'
down_revision = 'ai_annotation_001'
branch_labels = None
depends_on = None


def upgrade():
    # Create llm_applications table
    op.create_table(
        'llm_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('llm_usage_pattern', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()'), onupdate=datetime.utcnow),
    )
    
    # Create index on code
    op.create_index('idx_llm_applications_code', 'llm_applications', ['code'], unique=True)
    
    # Insert initial application data
    op.execute("""
        INSERT INTO llm_applications (code, name, description, llm_usage_pattern) VALUES
        ('structuring', 'Data Structuring', 'Schema inference and entity extraction from unstructured data', 'High-frequency, low-latency requests for real-time data processing'),
        ('knowledge_graph', 'Knowledge Graph', 'Knowledge graph construction and entity/relation extraction', 'Medium-frequency, high-quality extraction for graph building'),
        ('ai_assistant', 'AI Assistant', 'Intelligent assistant services for user interactions', 'High-frequency, conversational interactions with context awareness'),
        ('semantic_analysis', 'Semantic Analysis', 'Semantic analysis and text understanding services', 'Medium-frequency, analytical processing for deep understanding'),
        ('rag_agent', 'RAG Agent', 'Retrieval-augmented generation for context-aware responses', 'High-frequency, context-aware generation with retrieval'),
        ('text_to_sql', 'Text to SQL', 'Natural language to SQL query conversion', 'Medium-frequency, precise translation for database queries')
    """)
    
    # Add tenant_id column to llm_configurations if not exists
    # Check if column exists first
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('llm_configurations')]
    
    if 'tenant_id' not in columns:
        op.add_column('llm_configurations', 
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True)
        )
        op.create_foreign_key(
            'fk_llm_configurations_tenant',
            'llm_configurations', 'tenants',
            ['tenant_id'], ['id'],
            ondelete='CASCADE'
        )
    
    if 'provider' not in columns:
        op.add_column('llm_configurations',
            sa.Column('provider', sa.String(50), nullable=True)
        )
        # Set default provider for existing records
        op.execute("UPDATE llm_configurations SET provider = 'openai' WHERE provider IS NULL")
        # Make it non-nullable after setting defaults
        op.alter_column('llm_configurations', 'provider', nullable=False)
    
    # Create llm_application_bindings table
    op.create_table(
        'llm_application_bindings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('llm_config_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('priority', sa.Integer, nullable=False),
        sa.Column('max_retries', sa.Integer, nullable=False, server_default=sa.text('3')),
        sa.Column('timeout_seconds', sa.Integer, nullable=False, server_default=sa.text('30')),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()'), onupdate=datetime.utcnow),
        sa.ForeignKeyConstraint(['llm_config_id'], ['llm_configurations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['llm_applications.id'], ondelete='CASCADE'),
    )
    
    # Create unique constraint on application_id + priority
    op.create_unique_constraint('uq_app_priority', 'llm_application_bindings', ['application_id', 'priority'])
    
    # Create check constraints
    op.create_check_constraint(
        'ck_priority_range',
        'llm_application_bindings',
        'priority >= 1 AND priority <= 99'
    )
    op.create_check_constraint(
        'ck_max_retries_range',
        'llm_application_bindings',
        'max_retries >= 0 AND max_retries <= 10'
    )
    op.create_check_constraint(
        'ck_timeout_positive',
        'llm_application_bindings',
        'timeout_seconds > 0'
    )
    
    # Create indexes
    op.create_index('idx_bindings_app_priority', 'llm_application_bindings', ['application_id', 'priority'])
    op.create_index('idx_bindings_active', 'llm_application_bindings', ['is_active'])
    
    # Create index on llm_configurations for tenant queries
    if 'idx_llm_configs_tenant_active' not in [idx['name'] for idx in inspector.get_indexes('llm_configurations')]:
        op.create_index('idx_llm_configs_tenant_active', 'llm_configurations', ['tenant_id', 'is_active'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_bindings_active', 'llm_application_bindings')
    op.drop_index('idx_bindings_app_priority', 'llm_application_bindings')
    
    # Drop llm_application_bindings table
    op.drop_table('llm_application_bindings')
    
    # Drop llm_applications table
    op.drop_index('idx_llm_applications_code', 'llm_applications')
    op.drop_table('llm_applications')
    
    # Remove added columns from llm_configurations (optional, commented out to preserve data)
    # op.drop_constraint('fk_llm_configurations_tenant', 'llm_configurations', type_='foreignkey')
    # op.drop_column('llm_configurations', 'tenant_id')
    # op.drop_column('llm_configurations', 'provider')
    # op.drop_index('idx_llm_configs_tenant_active', 'llm_configurations')
