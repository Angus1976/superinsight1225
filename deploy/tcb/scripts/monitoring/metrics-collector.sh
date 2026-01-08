#!/bin/bash
# Enterprise Metrics Collection Script
# Collects system and application metrics for monitoring

set -e

METRICS_DIR="/app/metrics"
TIMESTAMP=$(date -Iseconds)
LOG_FILE="/app/logs/metrics-collector.log"

log() {
    echo "[$(date -Iseconds)] [metrics-collector] $1" | tee -a "$LOG_FILE"
}

collect_system_metrics() {
    log "Collecting system metrics..."
    
    # CPU usage
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    
    # Memory usage
    MEMORY_INFO=$(free -m | grep '^Mem:')
    MEMORY_TOTAL=$(echo $MEMORY_INFO | awk '{print $2}')
    MEMORY_USED=$(echo $MEMORY_INFO | awk '{print $3}')
    MEMORY_USAGE=$(echo "scale=2; $MEMORY_USED * 100 / $MEMORY_TOTAL" | bc -l)
    
    # Disk usage
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | cut -d'%' -f1)
    
    # Network stats
    NETWORK_RX=$(cat /proc/net/dev | grep eth0 | awk '{print $2}')
    NETWORK_TX=$(cat /proc/net/dev | grep eth0 | awk '{print $10}')
    
    # Write system metrics
    cat > "$METRICS_DIR/system_metrics.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "cpu_usage_percent": $CPU_USAGE,
    "memory_usage_percent": $MEMORY_USAGE,
    "memory_total_mb": $MEMORY_TOTAL,
    "memory_used_mb": $MEMORY_USED,
    "disk_usage_percent": $DISK_USAGE,
    "network_rx_bytes": $NETWORK_RX,
    "network_tx_bytes": $NETWORK_TX
}
EOF
}

collect_postgres_metrics() {
    log "Collecting PostgreSQL metrics..."
    
    if pg_isready -q; then
        # Connection count
        CONNECTIONS=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
        
        # Database size
        DB_SIZE=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT pg_size_pretty(pg_database_size('$POSTGRES_DB'));" 2>/dev/null | xargs)
        
        # Transaction stats
        TXN_STATS=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT xact_commit, xact_rollback FROM pg_stat_database WHERE datname='$POSTGRES_DB';" 2>/dev/null)
        
        cat > "$METRICS_DIR/postgres_metrics.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "active_connections": $CONNECTIONS,
    "database_size": "$DB_SIZE",
    "transactions_committed": $(echo $TXN_STATS | awk '{print $1}'),
    "transactions_rolled_back": $(echo $TXN_STATS | awk '{print $2}'),
    "status": "healthy"
}
EOF
    else
        cat > "$METRICS_DIR/postgres_metrics.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "status": "unhealthy"
}
EOF
    fi
}

collect_redis_metrics() {
    log "Collecting Redis metrics..."
    
    if nc -z localhost "$REDIS_PORT" 2>/dev/null; then
        # Redis info
        REDIS_INFO=$(redis-cli info memory 2>/dev/null)
        USED_MEMORY=$(echo "$REDIS_INFO" | grep "used_memory:" | cut -d: -f2 | tr -d '\r')
        MAX_MEMORY=$(echo "$REDIS_INFO" | grep "maxmemory:" | cut -d: -f2 | tr -d '\r')
        
        # Connected clients
        CLIENTS=$(redis-cli info clients 2>/dev/null | grep "connected_clients:" | cut -d: -f2 | tr -d '\r')
        
        cat > "$METRICS_DIR/redis_metrics.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "used_memory_bytes": $USED_MEMORY,
    "max_memory_bytes": $MAX_MEMORY,
    "connected_clients": $CLIENTS,
    "status": "healthy"
}
EOF
    else
        cat > "$METRICS_DIR/redis_metrics.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "status": "unhealthy"
}
EOF
    fi
}

collect_application_metrics() {
    log "Collecting application metrics..."
    
    # FastAPI health
    if curl -sf "http://localhost:$APP_PORT/health" > /dev/null 2>&1; then
        FASTAPI_STATUS="healthy"
    else
        FASTAPI_STATUS="unhealthy"
    fi
    
    # Label Studio health
    if curl -sf "http://localhost:$LABEL_STUDIO_PORT/" > /dev/null 2>&1; then
        LABELSTUDIO_STATUS="healthy"
    else
        LABELSTUDIO_STATUS="unhealthy"
    fi
    
    cat > "$METRICS_DIR/application_metrics.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "fastapi_status": "$FASTAPI_STATUS",
    "label_studio_status": "$LABELSTUDIO_STATUS"
}
EOF
}

main() {
    # Create metrics directory if it doesn't exist
    mkdir -p "$METRICS_DIR"
    
    log "Starting metrics collection..."
    
    collect_system_metrics
    collect_postgres_metrics
    collect_redis_metrics
    collect_application_metrics
    
    log "Metrics collection completed"
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi