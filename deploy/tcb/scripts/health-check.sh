#!/bin/bash
# Enterprise Multi-Service Health Check Script
# Comprehensive health monitoring for PostgreSQL, Redis, FastAPI, and Label Studio

set -e

FASTAPI_PORT="${APP_PORT:-8000}"
LABEL_STUDIO_PORT="${LABEL_STUDIO_PORT:-8080}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
REDIS_PORT="${REDIS_PORT:-6379}"
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-10}"

# Exit codes
EXIT_HEALTHY=0
EXIT_UNHEALTHY=1
EXIT_WARNING=2

# Health check results
POSTGRES_HEALTHY=false
REDIS_HEALTHY=false
FASTAPI_HEALTHY=false
LABELSTUDIO_HEALTHY=false

log() {
    echo "[$(date -Iseconds)] [health-check] $1"
}

check_postgres() {
    log "Checking PostgreSQL health..."
    
    # Basic connectivity check
    if ! pg_isready -h localhost -p "$POSTGRES_PORT" -q -t "$HEALTH_CHECK_TIMEOUT"; then
        log "PostgreSQL: UNHEALTHY - Connection failed"
        return 1
    fi
    
    # Database query check
    if ! timeout "$HEALTH_CHECK_TIMEOUT" psql -h localhost -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" > /dev/null 2>&1; then
        log "PostgreSQL: UNHEALTHY - Query failed"
        return 1
    fi
    
    # Check active connections
    local connections=$(psql -h localhost -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
    if [ -z "$connections" ] || [ "$connections" -gt 90 ]; then
        log "PostgreSQL: WARNING - High connection count: $connections"
        return 2
    fi
    
    log "PostgreSQL: HEALTHY (connections: $connections)"
    POSTGRES_HEALTHY=true
    return 0
}

check_redis() {
    log "Checking Redis health..."
    
    # Basic connectivity check
    if ! timeout "$HEALTH_CHECK_TIMEOUT" nc -z localhost "$REDIS_PORT" 2>/dev/null; then
        log "Redis: UNHEALTHY - Connection failed"
        return 1
    fi
    
    # Redis ping check
    if ! timeout "$HEALTH_CHECK_TIMEOUT" redis-cli -p "$REDIS_PORT" ping > /dev/null 2>&1; then
        log "Redis: UNHEALTHY - Ping failed"
        return 1
    fi
    
    # Memory usage check
    local memory_info=$(redis-cli -p "$REDIS_PORT" info memory 2>/dev/null | grep "used_memory_human:")
    local used_memory=$(echo "$memory_info" | cut -d: -f2 | tr -d '\r')
    
    log "Redis: HEALTHY (memory: $used_memory)"
    REDIS_HEALTHY=true
    return 0
}

check_fastapi() {
    log "Checking FastAPI health..."
    
    # Health endpoint check
    local response_code=$(timeout "$HEALTH_CHECK_TIMEOUT" curl -s -o /dev/null -w "%{http_code}" "http://localhost:$FASTAPI_PORT/health" 2>/dev/null || echo "000")
    
    if [ "$response_code" != "200" ]; then
        # Try root endpoint as fallback
        response_code=$(timeout "$HEALTH_CHECK_TIMEOUT" curl -s -o /dev/null -w "%{http_code}" "http://localhost:$FASTAPI_PORT/" 2>/dev/null || echo "000")
        
        if [ "$response_code" != "200" ]; then
            log "FastAPI: UNHEALTHY - HTTP $response_code"
            return 1
        fi
    fi
    
    # Response time check
    local response_time=$(timeout "$HEALTH_CHECK_TIMEOUT" curl -s -o /dev/null -w "%{time_total}" "http://localhost:$FASTAPI_PORT/health" 2>/dev/null || echo "999")
    local response_time_ms=$(echo "$response_time * 1000" | bc -l 2>/dev/null | cut -d. -f1)
    
    if [ "$response_time_ms" -gt 5000 ]; then
        log "FastAPI: WARNING - Slow response: ${response_time_ms}ms"
        FASTAPI_HEALTHY=true
        return 2
    fi
    
    log "FastAPI: HEALTHY (response: ${response_time_ms}ms)"
    FASTAPI_HEALTHY=true
    return 0
}

check_label_studio() {
    log "Checking Label Studio health..."
    
    # Try health endpoint first
    local response_code=$(timeout "$HEALTH_CHECK_TIMEOUT" curl -s -o /dev/null -w "%{http_code}" "http://localhost:$LABEL_STUDIO_PORT/health" 2>/dev/null || echo "000")
    
    if [ "$response_code" != "200" ]; then
        # Try root endpoint as fallback
        response_code=$(timeout "$HEALTH_CHECK_TIMEOUT" curl -s -o /dev/null -w "%{http_code}" "http://localhost:$LABEL_STUDIO_PORT/" 2>/dev/null || echo "000")
        
        if [ "$response_code" != "200" ]; then
            log "Label Studio: UNHEALTHY - HTTP $response_code"
            return 1
        fi
    fi
    
    log "Label Studio: HEALTHY"
    LABELSTUDIO_HEALTHY=true
    return 0
}

check_system_resources() {
    log "Checking system resources..."
    
    # CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d',' -f1)
    if (( $(echo "$cpu_usage > 90" | bc -l) )); then
        log "SYSTEM: WARNING - High CPU usage: ${cpu_usage}%"
        return 2
    fi
    
    # Memory usage
    local memory_usage=$(free | grep '^Mem:' | awk '{printf "%.1f", $3/$2 * 100.0}')
    if (( $(echo "$memory_usage > 90" | bc -l) )); then
        log "SYSTEM: WARNING - High memory usage: ${memory_usage}%"
        return 2
    fi
    
    # Disk usage
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | cut -d'%' -f1)
    if [ "$disk_usage" -gt 90 ]; then
        log "SYSTEM: WARNING - High disk usage: ${disk_usage}%"
        return 2
    fi
    
    log "SYSTEM: HEALTHY (CPU: ${cpu_usage}%, Memory: ${memory_usage}%, Disk: ${disk_usage}%)"
    return 0
}

generate_health_report() {
    local timestamp=$(date -Iseconds)
    local overall_status="HEALTHY"
    
    # Determine overall status
    if [ "$POSTGRES_HEALTHY" = false ] || [ "$REDIS_HEALTHY" = false ] || [ "$FASTAPI_HEALTHY" = false ]; then
        overall_status="UNHEALTHY"
    elif [ "$LABELSTUDIO_HEALTHY" = false ]; then
        overall_status="WARNING"
    fi
    
    # Generate JSON report
    cat > /app/metrics/health_report.json << EOF
{
    "timestamp": "$timestamp",
    "overall_status": "$overall_status",
    "services": {
        "postgresql": {
            "status": $([ "$POSTGRES_HEALTHY" = true ] && echo '"healthy"' || echo '"unhealthy"'),
            "port": $POSTGRES_PORT
        },
        "redis": {
            "status": $([ "$REDIS_HEALTHY" = true ] && echo '"healthy"' || echo '"unhealthy"'),
            "port": $REDIS_PORT
        },
        "fastapi": {
            "status": $([ "$FASTAPI_HEALTHY" = true ] && echo '"healthy"' || echo '"unhealthy"'),
            "port": $FASTAPI_PORT
        },
        "label_studio": {
            "status": $([ "$LABELSTUDIO_HEALTHY" = true ] && echo '"healthy"' || echo '"unhealthy"'),
            "port": $LABEL_STUDIO_PORT
        }
    }
}
EOF
}

# Main health check
main() {
    local exit_code=$EXIT_HEALTHY
    local warning_count=0
    
    log "Starting comprehensive health check..."
    
    # Check all services
    check_postgres || { 
        case $? in
            1) exit_code=$EXIT_UNHEALTHY ;;
            2) ((warning_count++)) ;;
        esac
    }
    
    check_redis || {
        case $? in
            1) exit_code=$EXIT_UNHEALTHY ;;
            2) ((warning_count++)) ;;
        esac
    }
    
    check_fastapi || {
        case $? in
            1) exit_code=$EXIT_UNHEALTHY ;;
            2) ((warning_count++)) ;;
        esac
    }
    
    check_label_studio || {
        case $? in
            1) 
                # Label Studio failure is not critical for overall health
                log "Label Studio: Non-critical service failure"
                ((warning_count++))
                ;;
            2) ((warning_count++)) ;;
        esac
    }
    
    check_system_resources || {
        case $? in
            2) ((warning_count++)) ;;
        esac
    }
    
    # Generate health report
    generate_health_report
    
    # Determine final exit code
    if [ $exit_code -eq $EXIT_UNHEALTHY ]; then
        log "Overall status: UNHEALTHY"
        exit $EXIT_UNHEALTHY
    elif [ $warning_count -gt 0 ]; then
        log "Overall status: WARNING ($warning_count warnings)"
        # For Docker health check, warnings are still considered healthy
        exit $EXIT_HEALTHY
    else
        log "Overall status: HEALTHY"
        exit $EXIT_HEALTHY
    fi
}

# Allow checking individual services
case "${1:-all}" in
    postgres)
        check_postgres
        ;;
    redis)
        check_redis
        ;;
    fastapi)
        check_fastapi
        ;;
    label-studio)
        check_label_studio
        ;;
    system)
        check_system_resources
        ;;
    all|"")
        main
        ;;
    *)
        log "Usage: $0 [postgres|redis|fastapi|label-studio|system|all]"
        exit 1
        ;;
esac
