"""Add audit integrity support

Revision ID: 007_add_audit_integrity_support
Revises: 006_add_sensitivity_policies
Create Date: 2026-01-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_add_audit_integrity_support'
down_revision = '006_add_sensitivity_policies'
branch_labels = None
depends_on = None


def upgrade():
    """Add audit integrity support to existing audit_logs table."""
    
    # The integrity information is already stored in the JSONB details field
    # This migration adds indexes and constraints to optimize integrity queries
    
    # Add index for integrity data queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_integrity_exists 
        ON audit_logs USING GIN ((details->'integrity')) 
        WHERE details ? 'integrity'
    """)
    
    # Add index for integrity hash queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_integrity_hash 
        ON audit_logs USING BTREE ((details->'integrity'->>'hash')) 
        WHERE details->'integrity'->>'hash' IS NOT NULL
    """)
    
    # Add index for integrity timestamp queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_integrity_timestamp 
        ON audit_logs USING BTREE ((details->'integrity'->>'timestamp')) 
        WHERE details->'integrity'->>'timestamp' IS NOT NULL
    """)
    
    # Create audit integrity statistics view
    op.execute("""
        CREATE OR REPLACE VIEW audit_integrity_stats AS
        SELECT 
            tenant_id,
            COUNT(*) as total_logs,
            COUNT(CASE WHEN details ? 'integrity' THEN 1 END) as protected_logs,
            COUNT(CASE WHEN details ? 'integrity' THEN NULL ELSE 1 END) as unprotected_logs,
            ROUND(
                (COUNT(CASE WHEN details ? 'integrity' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 
                2
            ) as protection_rate_percent,
            MIN(timestamp) as earliest_log,
            MAX(timestamp) as latest_log,
            MAX(CASE WHEN details ? 'integrity' THEN timestamp END) as latest_protected_log
        FROM audit_logs 
        GROUP BY tenant_id
    """)
    
    # Create function to validate integrity data structure
    op.execute("""
        CREATE OR REPLACE FUNCTION validate_audit_integrity(integrity_data JSONB)
        RETURNS BOOLEAN AS $$
        BEGIN
            -- Check required fields
            IF NOT (integrity_data ? 'hash' AND 
                   integrity_data ? 'signature' AND 
                   integrity_data ? 'algorithm' AND 
                   integrity_data ? 'signature_algorithm' AND 
                   integrity_data ? 'timestamp') THEN
                RETURN FALSE;
            END IF;
            
            -- Check hash format (should be 64 character hex string for SHA256)
            IF LENGTH(integrity_data->>'hash') != 64 OR 
               NOT (integrity_data->>'hash' ~ '^[a-f0-9]{64}$') THEN
                RETURN FALSE;
            END IF;
            
            -- Check algorithm
            IF integrity_data->>'algorithm' != 'sha256' THEN
                RETURN FALSE;
            END IF;
            
            -- Check signature algorithm
            IF integrity_data->>'signature_algorithm' != 'RSA-PSS-SHA256' THEN
                RETURN FALSE;
            END IF;
            
            -- Check timestamp format
            BEGIN
                PERFORM (integrity_data->>'timestamp')::timestamp;
            EXCEPTION WHEN OTHERS THEN
                RETURN FALSE;
            END;
            
            RETURN TRUE;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
    """)
    
    # Add check constraint for integrity data validation
    op.execute("""
        ALTER TABLE audit_logs 
        ADD CONSTRAINT check_audit_integrity_format 
        CHECK (
            details->'integrity' IS NULL OR 
            validate_audit_integrity(details->'integrity')
        )
    """)
    
    # Create audit integrity violation detection function
    op.execute("""
        CREATE OR REPLACE FUNCTION detect_audit_integrity_violations(
            p_tenant_id TEXT,
            p_days INTEGER DEFAULT 30
        )
        RETURNS TABLE(
            log_id UUID,
            violation_type TEXT,
            description TEXT,
            severity TEXT,
            detected_at TIMESTAMP
        ) AS $$
        DECLARE
            start_date TIMESTAMP;
        BEGIN
            start_date := NOW() - (p_days || ' days')::INTERVAL;
            
            -- Missing integrity data
            RETURN QUERY
            SELECT 
                al.id,
                'missing_integrity_data'::TEXT,
                'Audit log missing integrity protection'::TEXT,
                'medium'::TEXT,
                NOW()
            FROM audit_logs al
            WHERE al.tenant_id = p_tenant_id
              AND al.timestamp >= start_date
              AND NOT (al.details ? 'integrity');
            
            -- Invalid integrity data format
            RETURN QUERY
            SELECT 
                al.id,
                'invalid_integrity_format'::TEXT,
                'Audit log has invalid integrity data format'::TEXT,
                'high'::TEXT,
                NOW()
            FROM audit_logs al
            WHERE al.tenant_id = p_tenant_id
              AND al.timestamp >= start_date
              AND al.details ? 'integrity'
              AND NOT validate_audit_integrity(al.details->'integrity');
            
            -- Suspicious time gaps (more than 2 hours between consecutive logs during business hours)
            RETURN QUERY
            WITH consecutive_logs AS (
                SELECT 
                    id,
                    timestamp,
                    LAG(timestamp) OVER (ORDER BY timestamp) as prev_timestamp
                FROM audit_logs
                WHERE tenant_id = p_tenant_id
                  AND timestamp >= start_date
                ORDER BY timestamp
            )
            SELECT 
                cl.id,
                'suspicious_time_gap'::TEXT,
                'Suspicious gap of ' || EXTRACT(EPOCH FROM (cl.timestamp - cl.prev_timestamp))/3600 || ' hours between audit logs'::TEXT,
                'medium'::TEXT,
                NOW()
            FROM consecutive_logs cl
            WHERE cl.prev_timestamp IS NOT NULL
              AND EXTRACT(EPOCH FROM (cl.timestamp - cl.prev_timestamp)) > 7200  -- 2 hours
              AND EXTRACT(HOUR FROM cl.timestamp) BETWEEN 8 AND 18  -- Business hours
              AND EXTRACT(DOW FROM cl.timestamp) BETWEEN 1 AND 5;   -- Weekdays
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create audit integrity summary function
    op.execute("""
        CREATE OR REPLACE FUNCTION get_audit_integrity_summary(
            p_tenant_id TEXT,
            p_days INTEGER DEFAULT 30
        )
        RETURNS JSONB AS $$
        DECLARE
            result JSONB;
            start_date TIMESTAMP;
            total_logs INTEGER;
            protected_logs INTEGER;
            violation_count INTEGER;
        BEGIN
            start_date := NOW() - (p_days || ' days')::INTERVAL;
            
            -- Get basic statistics
            SELECT COUNT(*) INTO total_logs
            FROM audit_logs
            WHERE tenant_id = p_tenant_id AND timestamp >= start_date;
            
            SELECT COUNT(*) INTO protected_logs
            FROM audit_logs
            WHERE tenant_id = p_tenant_id 
              AND timestamp >= start_date
              AND details ? 'integrity';
            
            -- Get violation count
            SELECT COUNT(*) INTO violation_count
            FROM detect_audit_integrity_violations(p_tenant_id, p_days);
            
            -- Build result
            result := jsonb_build_object(
                'tenant_id', p_tenant_id,
                'analysis_period_days', p_days,
                'total_logs', total_logs,
                'protected_logs', protected_logs,
                'unprotected_logs', total_logs - protected_logs,
                'protection_rate_percent', 
                    CASE WHEN total_logs > 0 
                         THEN ROUND((protected_logs::numeric / total_logs::numeric) * 100, 2)
                         ELSE 0 
                    END,
                'integrity_violations', violation_count,
                'integrity_status', 
                    CASE 
                        WHEN violation_count = 0 AND protected_logs::numeric / NULLIF(total_logs, 0) >= 0.95 THEN 'excellent'
                        WHEN violation_count <= 5 AND protected_logs::numeric / NULLIF(total_logs, 0) >= 0.80 THEN 'good'
                        WHEN violation_count <= 20 AND protected_logs::numeric / NULLIF(total_logs, 0) >= 0.60 THEN 'fair'
                        ELSE 'poor'
                    END,
                'generated_at', NOW()
            );
            
            RETURN result;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade():
    """Remove audit integrity support."""
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS get_audit_integrity_summary(TEXT, INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS detect_audit_integrity_violations(TEXT, INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS validate_audit_integrity(JSONB)")
    
    # Drop view
    op.execute("DROP VIEW IF EXISTS audit_integrity_stats")
    
    # Drop constraint
    op.execute("ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS check_audit_integrity_format")
    
    # Drop indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_audit_logs_integrity_timestamp")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_audit_logs_integrity_hash")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_audit_logs_integrity_exists")