"""Audit storage optimization with partitioning

Revision ID: 005_audit_storage_optimization
Revises: 004_extend_audit_tables
Create Date: 2026-01-10 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime, timedelta

# revision identifiers, used by Alembic.
revision = '005_audit_storage_optimization'
down_revision = '004_extend_audit_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade to optimized audit storage with partitioning."""
    
    # Check if we're using PostgreSQL (partitioning is PostgreSQL-specific)
    bind = op.get_bind()
    try:
        if 'postgresql' not in str(bind.engine.url).lower():
            print("Skipping partitioning setup - PostgreSQL required")
            return
    except AttributeError:
        # Fallback check
        if 'postgresql' not in str(bind).lower():
            print("Skipping partitioning setup - PostgreSQL required")
            return
    
    # Convert existing audit_logs table to partitioned table
    op.execute("""
        -- Create new partitioned audit_logs table
        CREATE TABLE audit_logs_partitioned (
            id UUID DEFAULT gen_random_uuid(),
            user_id UUID,
            tenant_id VARCHAR(100) NOT NULL,
            action auditaction NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            resource_id VARCHAR(255),
            ip_address INET,
            user_agent TEXT,
            details JSONB DEFAULT '{}',
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp);
    """)
    
    # Create indexes on the partitioned table
    op.execute("""
        CREATE INDEX idx_audit_logs_partitioned_tenant_timestamp 
        ON audit_logs_partitioned (tenant_id, timestamp);
        
        CREATE INDEX idx_audit_logs_partitioned_user_action 
        ON audit_logs_partitioned (user_id, action);
        
        CREATE INDEX idx_audit_logs_partitioned_resource 
        ON audit_logs_partitioned (resource_type, resource_id);
        
        CREATE INDEX idx_audit_logs_partitioned_ip_address 
        ON audit_logs_partitioned (ip_address);
    """)
    
    # Create initial monthly partitions (current month + next 11 months)
    current_date = datetime.now()
    for i in range(12):
        partition_date = current_date + timedelta(days=30 * i)
        partition_name = f"audit_logs_{partition_date.strftime('%Y_%m')}"
        
        # Calculate partition bounds
        start_date = partition_date.replace(day=1)
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
        
        op.execute(f"""
            CREATE TABLE {partition_name} PARTITION OF audit_logs_partitioned
            FOR VALUES FROM ('{start_date.isoformat()}') TO ('{end_date.isoformat()}');
            
            CREATE INDEX idx_{partition_name}_tenant_timestamp 
            ON {partition_name} (tenant_id, timestamp);
            
            CREATE INDEX idx_{partition_name}_user_action 
            ON {partition_name} (user_id, action);
            
            CREATE INDEX idx_{partition_name}_resource 
            ON {partition_name} (resource_type, resource_id);
        """)
    
    # Migrate existing data from old table to partitioned table
    op.execute("""
        INSERT INTO audit_logs_partitioned 
        SELECT * FROM audit_logs;
    """)
    
    # Rename tables to complete the migration
    op.execute("ALTER TABLE audit_logs RENAME TO audit_logs_old;")
    op.execute("ALTER TABLE audit_logs_partitioned RENAME TO audit_logs;")
    
    # Create audit log archival tracking table
    op.create_table(
        'audit_log_archives',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('archive_filename', sa.String(255), nullable=False),
        sa.Column('archive_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('logs_archived', sa.Integer, nullable=False),
        sa.Column('archive_size_bytes', sa.BigInteger, nullable=True),
        sa.Column('compression_ratio', sa.Float, nullable=True),
        sa.Column('storage_location', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('metadata', postgresql.JSONB, default={})
    )
    
    # Create indexes for archive tracking
    op.create_index('idx_audit_archives_tenant_date', 'audit_log_archives', ['tenant_id', 'archive_date'])
    op.create_index('idx_audit_archives_filename', 'audit_log_archives', ['archive_filename'])
    
    # Create audit storage statistics table
    op.create_table(
        'audit_storage_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('stat_date', sa.Date, nullable=False),
        sa.Column('total_logs', sa.BigInteger, nullable=False, default=0),
        sa.Column('logs_archived', sa.BigInteger, nullable=False, default=0),
        sa.Column('logs_deleted', sa.BigInteger, nullable=False, default=0),
        sa.Column('storage_size_mb', sa.Float, nullable=True),
        sa.Column('compression_ratio', sa.Float, nullable=True),
        sa.Column('batch_operations', sa.Integer, nullable=False, default=0),
        sa.Column('avg_batch_time_ms', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create unique constraint and indexes for storage stats
    op.create_index('idx_audit_storage_stats_tenant_date', 'audit_storage_stats', ['tenant_id', 'stat_date'], unique=True)
    
    # Create function for automatic partition creation
    op.execute("""
        CREATE OR REPLACE FUNCTION create_monthly_audit_partition(partition_date DATE)
        RETURNS TEXT AS $$
        DECLARE
            partition_name TEXT;
            start_date DATE;
            end_date DATE;
        BEGIN
            -- Calculate partition name and bounds
            partition_name := 'audit_logs_' || to_char(partition_date, 'YYYY_MM');
            start_date := date_trunc('month', partition_date)::DATE;
            end_date := (date_trunc('month', partition_date) + interval '1 month')::DATE;
            
            -- Check if partition already exists
            IF EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = partition_name
            ) THEN
                RETURN 'Partition ' || partition_name || ' already exists';
            END IF;
            
            -- Create partition
            EXECUTE format('
                CREATE TABLE %I PARTITION OF audit_logs
                FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
            
            -- Create indexes
            EXECUTE format('
                CREATE INDEX idx_%I_tenant_timestamp ON %I (tenant_id, timestamp)',
                partition_name, partition_name
            );
            
            EXECUTE format('
                CREATE INDEX idx_%I_user_action ON %I (user_id, action)',
                partition_name, partition_name
            );
            
            EXECUTE format('
                CREATE INDEX idx_%I_resource ON %I (resource_type, resource_id)',
                partition_name, partition_name
            );
            
            RETURN 'Created partition ' || partition_name;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create function for automatic old partition cleanup
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_old_audit_partitions(retention_months INTEGER DEFAULT 84)
        RETURNS TEXT AS $$
        DECLARE
            partition_record RECORD;
            cutoff_date DATE;
            result_text TEXT := '';
        BEGIN
            -- Calculate cutoff date (default 7 years = 84 months)
            cutoff_date := (date_trunc('month', CURRENT_DATE) - (retention_months || ' months')::INTERVAL)::DATE;
            
            -- Find old partitions to drop
            FOR partition_record IN
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE tablename ~ '^audit_logs_\d{4}_\d{2}$'
                AND tablename < 'audit_logs_' || to_char(cutoff_date, 'YYYY_MM')
            LOOP
                -- Drop the partition
                EXECUTE format('DROP TABLE IF EXISTS %I.%I', 
                    partition_record.schemaname, partition_record.tablename);
                
                result_text := result_text || 'Dropped partition ' || partition_record.tablename || '; ';
            END LOOP;
            
            IF result_text = '' THEN
                RETURN 'No old partitions found to cleanup';
            ELSE
                RETURN result_text;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade():
    """Downgrade from optimized audit storage."""
    
    bind = op.get_bind()
    if 'postgresql' not in str(bind.url).lower():
        print("Skipping partitioning downgrade - PostgreSQL required")
        return
    
    # Drop partition management functions
    op.execute("DROP FUNCTION IF EXISTS create_monthly_audit_partition(DATE);")
    op.execute("DROP FUNCTION IF EXISTS cleanup_old_audit_partitions(INTEGER);")
    
    # Drop storage tracking tables
    op.drop_table('audit_storage_stats')
    op.drop_table('audit_log_archives')
    
    # Restore original audit_logs table structure
    op.execute("""
        -- Create new non-partitioned table
        CREATE TABLE audit_logs_restored (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id),
            tenant_id VARCHAR(100) NOT NULL,
            action auditaction NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            resource_id VARCHAR(255),
            ip_address INET,
            user_agent TEXT,
            details JSONB DEFAULT '{}',
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    
    # Migrate data back from partitioned table
    op.execute("""
        INSERT INTO audit_logs_restored 
        SELECT * FROM audit_logs;
    """)
    
    # Drop partitioned table and all partitions
    op.execute("DROP TABLE audit_logs CASCADE;")
    
    # Restore original table name
    op.execute("ALTER TABLE audit_logs_restored RENAME TO audit_logs;")
    
    # Recreate original indexes
    op.create_index('idx_audit_logs_tenant_timestamp', 'audit_logs', ['tenant_id', 'timestamp'])
    op.create_index('idx_audit_logs_user_action', 'audit_logs', ['user_id', 'action'])
    
    # Drop old backup table if it exists
    op.execute("DROP TABLE IF EXISTS audit_logs_old;")