#!/bin/bash
set -e

# SuperInsight TCB Container Entrypoint Script
# Initializes all services and starts supervisor

echo "=========================================="
echo "SuperInsight Enterprise Container Starting"
echo "=========================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create necessary directories
log_info "Creating directories..."
mkdir -p /var/lib/postgresql/14/main \
         /var/lib/redis \
         /var/run/postgresql \
         /var/run/redis \
         /var/log/postgresql \
         /var/log/redis \
         /var/log/supervisor \
         /var/log/nginx \
         /app/uploads \
         /app/logs \
         /app/backups \
         /app/metrics \
         /app/label-studio-data

# Set permissions
log_info "Setting permissions..."
chown -R postgres:postgres /var/lib/postgresql /var/run/postgresql /var/log/postgresql
chmod 700 /var/lib/postgresql/14/main
chown -R redis:redis /var/lib/redis /var/run/redis /var/log/redis 2>/dev/null || true

# Initialize PostgreSQL if needed
if [ ! -f "/var/lib/postgresql/14/main/PG_VERSION" ]; then
    log_info "Initializing PostgreSQL database..."
    su - postgres -c "/usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/14/main --encoding=UTF-8 --lc-collate=C --lc-ctype=C"
    
    # Start PostgreSQL temporarily for setup
    log_info "Starting PostgreSQL for initial setup..."
    su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/14/main -l /var/log/postgresql/startup.log start"
    
    # Wait for PostgreSQL to be ready
    sleep 5
    
    # Create database and user
    log_info "Creating database and user..."
    su - postgres -c "psql -c \"CREATE USER ${POSTGRES_USER:-superinsight} WITH PASSWORD '${POSTGRES_PASSWORD:-superinsight_secure_pwd}' SUPERUSER;\""
    su - postgres -c "psql -c \"CREATE DATABASE ${POSTGRES_DB:-superinsight} OWNER ${POSTGRES_USER:-superinsight};\""
    
    # Run database migrations
    log_info "Running database migrations..."
    cd /app
    if [ -f "alembic.ini" ]; then
        DATABASE_URL="postgresql://${POSTGRES_USER:-superinsight}:${POSTGRES_PASSWORD:-superinsight_secure_pwd}@localhost:5432/${POSTGRES_DB:-superinsight}" \
        alembic upgrade head || log_warn "Alembic migrations failed or not configured"
    fi
    
    # Initialize application database
    log_info "Initializing application database..."
    DATABASE_URL="postgresql://${POSTGRES_USER:-superinsight}:${POSTGRES_PASSWORD:-superinsight_secure_pwd}@localhost:5432/${POSTGRES_DB:-superinsight}" \
    python -c "from src.database.connection import init_db; init_db()" 2>/dev/null || log_warn "Database initialization skipped"
    
    # Stop PostgreSQL (supervisor will start it)
    log_info "Stopping PostgreSQL temporary instance..."
    su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/14/main stop"
    sleep 2
fi

# Initialize Redis data directory
if [ ! -f "/var/lib/redis/dump.rdb" ]; then
    log_info "Initializing Redis data directory..."
    touch /var/lib/redis/.initialized
fi

# Set environment variables for services
export DATABASE_URL="postgresql://${POSTGRES_USER:-superinsight}:${POSTGRES_PASSWORD:-superinsight_secure_pwd}@localhost:5432/${POSTGRES_DB:-superinsight}"
export REDIS_URL="redis://localhost:6379/0"
export LABEL_STUDIO_URL="http://localhost:${LABEL_STUDIO_PORT:-8080}"

# Export for supervisor
export POSTGRES_USER="${POSTGRES_USER:-superinsight}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-superinsight_secure_pwd}"
export POSTGRES_DB="${POSTGRES_DB:-superinsight}"
export APP_PORT="${APP_PORT:-8000}"
export APP_WORKERS="${APP_WORKERS:-4}"
export LABEL_STUDIO_PORT="${LABEL_STUDIO_PORT:-8080}"
export SUPERVISOR_LOG_LEVEL="${SUPERVISOR_LOG_LEVEL:-info}"

log_info "Environment configured:"
log_info "  - DATABASE_URL: postgresql://***@localhost:5432/${POSTGRES_DB}"
log_info "  - REDIS_URL: redis://localhost:6379/0"
log_info "  - LABEL_STUDIO_URL: http://localhost:${LABEL_STUDIO_PORT}"
log_info "  - APP_PORT: ${APP_PORT}"
log_info "  - APP_WORKERS: ${APP_WORKERS}"

# Health check function
check_service() {
    local service=$1
    local port=$2
    local max_attempts=${3:-30}
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            log_info "$service is ready on port $port"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    log_error "$service failed to start on port $port"
    return 1
}

log_info "Starting services via Supervisor..."
echo "=========================================="

# Execute the main command (supervisord)
exec "$@"
