#!/bin/bash
# SuperInsight TCB Enterprise Container Entrypoint
# Initializes services and starts Supervisor with enterprise features

set -e

echo "=== SuperInsight TCB Enterprise Container Starting ==="
echo "Timestamp: $(date -Iseconds)"
echo "Version: 2.0.0"

# Function to log messages
log() {
    echo "[$(date -Iseconds)] [entrypoint] $1"
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log "ERROR: Entrypoint must run as root for initialization"
        exit 1
    fi
}

# Enterprise security initialization
init_security() {
    log "Initializing enterprise security features..."
    
    # Configure fail2ban if enabled
    if [ "$FAIL2BAN_ENABLED" = "true" ]; then
        log "Starting fail2ban service..."
        service fail2ban start || log "WARNING: Failed to start fail2ban"
    fi
    
    # Set secure file permissions
    chmod 600 /etc/postgresql/14/main/postgresql.conf
    chmod 600 /etc/redis/redis.conf
    chmod 700 /app/backups
    chmod 750 /app/metrics
    
    log "Security initialization completed"
}

# Enterprise monitoring initialization
init_monitoring() {
    log "Initializing enterprise monitoring..."
    
    # Create monitoring directories
    mkdir -p /app/metrics /app/logs
    chown superinsight:superinsight /app/metrics /app/logs
    
    # Initialize metrics collection
    if [ "$ENABLE_METRICS" = "true" ]; then
        log "Metrics collection enabled"
        touch /app/logs/metrics-collector.log
        chown superinsight:superinsight /app/logs/metrics-collector.log
    fi
    
    log "Monitoring initialization completed"
}

# Enterprise backup initialization
init_backup() {
    log "Initializing enterprise backup system..."
    
    if [ "$ENABLE_BACKUP" = "true" ]; then
        # Create backup directories
        mkdir -p /app/backups
        chown superinsight:superinsight /app/backups
        
        # Initialize backup logs
        touch /app/logs/backup-manager.log /app/logs/backup-scheduler.log
        chown superinsight:superinsight /app/logs/backup-*.log
        
        log "Backup system initialized"
    else
        log "Backup system disabled"
    fi
}

# Create required directories if they don't exist
create_directories() {
    log "Creating required directories..."
    
    mkdir -p \
        /var/lib/postgresql/14/main \
        /var/lib/redis \
        /var/log/supervisor \
        /var/run/supervisor \
        /run/postgresql \
        /var/run/redis \
        /app/uploads \
        /app/logs \
        /app/label-studio-data \
        /app/metrics \
        /app/backups
}

# Set correct ownership and permissions
set_permissions() {
    log "Setting directory permissions..."
    
    chown -R postgres:postgres /var/lib/postgresql /run/postgresql
    chown -R redis:redis /var/lib/redis /var/run/redis
    chown -R superinsight:superinsight /app/uploads /app/logs /app/label-studio-data /app/metrics /app/backups
    
    # Set secure permissions
    chmod 700 /var/lib/postgresql/14/main
    chmod 755 /var/lib/redis
    chmod 750 /app/backups
    chmod 755 /app/metrics
}

# Initialize PostgreSQL if not already initialized
init_postgresql() {
    if [ ! -f "/var/lib/postgresql/14/main/PG_VERSION" ]; then
        log "Initializing PostgreSQL database cluster..."
        /app/scripts/init-postgres.sh
    else
        log "PostgreSQL already initialized"
    fi
    
    # Configure PostgreSQL authentication
    log "Configuring PostgreSQL authentication..."
    cp /etc/postgresql/14/main/pg_hba.conf /var/lib/postgresql/14/main/pg_hba.conf 2>/dev/null || true
    chown postgres:postgres /var/lib/postgresql/14/main/pg_hba.conf 2>/dev/null || true
}

# Start PostgreSQL temporarily for database setup
start_temp_postgresql() {
    log "Starting PostgreSQL for initialization..."
    su - postgres -c "/usr/lib/postgresql/14/bin/pg_ctl -D /var/lib/postgresql/14/main -l /var/log/supervisor/postgres_init.log start" || true
    
    # Wait for PostgreSQL to be ready
    log "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if su - postgres -c "pg_isready -q"; then
            log "PostgreSQL is ready"
            return 0
        fi
        sleep 1
    done
    
    log "ERROR: PostgreSQL failed to start within 30 seconds"
    return 1
}

# Create databases and users
setup_databases() {
    log "Creating databases and users..."
    
    # Create application user
    su - postgres -c "psql -c \"SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER}'\" | grep -q 1 || psql -c \"CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}' SUPERUSER;\""
    
    # Create application database
    su - postgres -c "psql -c \"SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'\" | grep -q 1 || psql -c \"CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};\""
    
    # Create Label Studio database
    su - postgres -c "psql -c \"SELECT 1 FROM pg_database WHERE datname='label_studio'\" | grep -q 1 || psql -c \"CREATE DATABASE label_studio OWNER ${POSTGRES_USER};\""
    
    log "Database setup completed"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    /app/scripts/init-db.sh || log "Warning: Database migrations failed or already applied"
}

# Stop temporary PostgreSQL
stop_temp_postgresql() {
    log "Stopping temporary PostgreSQL..."
    su - postgres -c "/usr/lib/postgresql/14/bin/pg_ctl -D /var/lib/postgresql/14/main stop -m fast" || true
    sleep 2
}

# Validate system health before starting services
validate_system() {
    log "Validating system configuration..."
    
    # Check required files
    local required_files=(
        "/etc/supervisor/supervisord.conf"
        "/etc/postgresql/14/main/postgresql.conf"
        "/etc/redis/redis.conf"
        "/app/scripts/health-check.sh"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log "ERROR: Required file missing: $file"
            exit 1
        fi
    done
    
    # Check required directories
    local required_dirs=(
        "/var/lib/postgresql/14/main"
        "/var/lib/redis"
        "/app/logs"
        "/app/backups"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            log "ERROR: Required directory missing: $dir"
            exit 1
        fi
    done
    
    log "System validation completed"
}

# Main initialization sequence
main() {
    check_root
    
    log "=== Enterprise Initialization Starting ==="
    
    create_directories
    set_permissions
    init_security
    init_monitoring
    init_backup
    init_postgresql
    
    start_temp_postgresql
    setup_databases
    run_migrations
    stop_temp_postgresql
    
    validate_system
    
    log "=== Enterprise Initialization Complete ==="
    log "Starting Supervisor with enterprise monitoring..."
    
    # Switch to supervisor user and execute the main command
    exec "$@"
}

# Run main initialization
main "$@"
