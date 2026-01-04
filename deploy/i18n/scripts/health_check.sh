#!/bin/bash

# SuperInsight i18n Health Check Script
# Usage: ./health_check.sh [environment] [--detailed]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
ENVIRONMENT="${1:-staging}"
DETAILED_CHECK="${2:-}"
BASE_URL="http://localhost:8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Health check functions
check_service_status() {
    log_info "Checking service status..."
    
    cd "$DEPLOY_DIR"
    local compose_file="docker-compose.yml"
    local env_file=".env.$ENVIRONMENT"
    
    if [[ ! -f "$env_file" ]]; then
        log_warning "Environment file not found: $env_file"
        env_file=""
    fi
    
    # Check if services are running
    local services=(superinsight-api redis postgres nginx)
    local all_healthy=true
    
    for service in "${services[@]}"; do
        local status=$(docker-compose -f "$compose_file" ${env_file:+--env-file "$env_file"} ps -q "$service" 2>/dev/null || echo "")
        
        if [[ -n "$status" ]]; then
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$status" 2>/dev/null || echo "unknown")
            
            case "$health" in
                "healthy")
                    log_success "✓ $service is healthy"
                    ;;
                "unhealthy")
                    log_error "✗ $service is unhealthy"
                    all_healthy=false
                    ;;
                "starting")
                    log_warning "⚠ $service is starting"
                    ;;
                *)
                    log_warning "? $service status unknown"
                    ;;
            esac
        else
            log_error "✗ $service is not running"
            all_healthy=false
        fi
    done
    
    return $([ "$all_healthy" = true ] && echo 0 || echo 1)
}

check_api_health() {
    log_info "Checking API health..."
    
    local health_endpoint="$BASE_URL/health/i18n"
    local response
    local status_code
    
    # Check if API is responding
    if ! response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$health_endpoint" 2>/dev/null); then
        log_error "✗ API is not responding"
        return 1
    fi
    
    # Extract status code and body
    status_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    body=$(echo "$response" | sed 's/HTTPSTATUS:[0-9]*$//')
    
    if [[ "$status_code" == "200" ]]; then
        log_success "✓ API health check passed"
        
        if [[ "$DETAILED_CHECK" == "--detailed" ]]; then
            echo "Health response: $body" | jq . 2>/dev/null || echo "$body"
        fi
        
        return 0
    else
        log_error "✗ API health check failed (HTTP $status_code)"
        echo "Response: $body"
        return 1
    fi
}

check_i18n_functionality() {
    log_info "Checking i18n functionality..."
    
    local all_tests_passed=true
    
    # Test 1: Get supported languages
    log_info "Testing supported languages endpoint..."
    local response=$(curl -s "$BASE_URL/api/i18n/languages" 2>/dev/null || echo "")
    
    if echo "$response" | jq -e '.supported_languages | contains(["zh", "en"])' >/dev/null 2>&1; then
        log_success "✓ Supported languages endpoint works"
    else
        log_error "✗ Supported languages endpoint failed"
        all_tests_passed=false
    fi
    
    # Test 2: Get Chinese translations
    log_info "Testing Chinese translations..."
    local zh_response=$(curl -s "$BASE_URL/api/i18n/translations?language=zh" 2>/dev/null || echo "")
    
    if echo "$zh_response" | jq -e '.language == "zh" and .translations.login' >/dev/null 2>&1; then
        log_success "✓ Chinese translations available"
    else
        log_error "✗ Chinese translations failed"
        all_tests_passed=false
    fi
    
    # Test 3: Get English translations
    log_info "Testing English translations..."
    local en_response=$(curl -s "$BASE_URL/api/i18n/translations?language=en" 2>/dev/null || echo "")
    
    if echo "$en_response" | jq -e '.language == "en" and .translations.login' >/dev/null 2>&1; then
        log_success "✓ English translations available"
    else
        log_error "✗ English translations failed"
        all_tests_passed=false
    fi
    
    # Test 4: Language switching
    log_info "Testing language switching..."
    local switch_response=$(curl -s -X POST "$BASE_URL/api/settings/language" \
        -H "Content-Type: application/json" \
        -d '{"language": "en"}' 2>/dev/null || echo "")
    
    if echo "$switch_response" | jq -e '.current_language == "en"' >/dev/null 2>&1; then
        log_success "✓ Language switching works"
    else
        log_error "✗ Language switching failed"
        all_tests_passed=false
    fi
    
    # Test 5: Content-Language header
    log_info "Testing Content-Language header..."
    local header_check=$(curl -s -I "$BASE_URL/api/test?language=zh" 2>/dev/null | grep -i "content-language" || echo "")
    
    if echo "$header_check" | grep -q "zh"; then
        log_success "✓ Content-Language header present"
    else
        log_error "✗ Content-Language header missing"
        all_tests_passed=false
    fi
    
    return $([ "$all_tests_passed" = true ] && echo 0 || echo 1)
}

check_performance() {
    log_info "Checking performance..."
    
    local endpoint="$BASE_URL/api/i18n/translations?language=en"
    local total_time=0
    local requests=10
    
    for i in $(seq 1 $requests); do
        local start_time=$(date +%s%N)
        curl -s "$endpoint" >/dev/null 2>&1
        local end_time=$(date +%s%N)
        
        local request_time=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds
        total_time=$((total_time + request_time))
    done
    
    local avg_time=$((total_time / requests))
    
    if [[ $avg_time -lt 100 ]]; then
        log_success "✓ Performance good (avg: ${avg_time}ms)"
    elif [[ $avg_time -lt 500 ]]; then
        log_warning "⚠ Performance acceptable (avg: ${avg_time}ms)"
    else
        log_error "✗ Performance poor (avg: ${avg_time}ms)"
        return 1
    fi
    
    return 0
}

check_cache_functionality() {
    log_info "Checking cache functionality..."
    
    # Check Redis connection
    local redis_container=$(docker ps --filter "name=redis" --format "{{.Names}}" | head -n1)
    
    if [[ -n "$redis_container" ]]; then
        if docker exec "$redis_container" redis-cli ping >/dev/null 2>&1; then
            log_success "✓ Redis cache is accessible"
        else
            log_error "✗ Redis cache is not responding"
            return 1
        fi
    else
        log_warning "⚠ Redis container not found"
        return 1
    fi
    
    # Test cache performance (first request should be slower, second should be faster)
    local endpoint="$BASE_URL/api/i18n/translations?language=en"
    
    # Clear cache first
    docker exec "$redis_container" redis-cli flushdb >/dev/null 2>&1 || true
    
    # First request (cache miss)
    local start1=$(date +%s%N)
    curl -s "$endpoint" >/dev/null 2>&1
    local end1=$(date +%s%N)
    local time1=$(( (end1 - start1) / 1000000 ))
    
    # Second request (cache hit)
    local start2=$(date +%s%N)
    curl -s "$endpoint" >/dev/null 2>&1
    local end2=$(date +%s%N)
    local time2=$(( (end2 - start2) / 1000000 ))
    
    if [[ $time2 -lt $time1 ]]; then
        log_success "✓ Cache is working (${time1}ms -> ${time2}ms)"
    else
        log_warning "⚠ Cache performance unclear (${time1}ms -> ${time2}ms)"
    fi
    
    return 0
}

check_database_connectivity() {
    log_info "Checking database connectivity..."
    
    local postgres_container=$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -n1)
    
    if [[ -n "$postgres_container" ]]; then
        if docker exec "$postgres_container" pg_isready -U superinsight >/dev/null 2>&1; then
            log_success "✓ Database is accessible"
        else
            log_error "✗ Database is not responding"
            return 1
        fi
    else
        log_error "✗ PostgreSQL container not found"
        return 1
    fi
    
    return 0
}

check_monitoring() {
    log_info "Checking monitoring services..."
    
    # Check Prometheus
    if curl -s "http://localhost:9090/-/healthy" >/dev/null 2>&1; then
        log_success "✓ Prometheus is healthy"
    else
        log_warning "⚠ Prometheus is not accessible"
    fi
    
    # Check Grafana
    if curl -s "http://localhost:3000/api/health" >/dev/null 2>&1; then
        log_success "✓ Grafana is healthy"
    else
        log_warning "⚠ Grafana is not accessible"
    fi
}

generate_health_report() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local report_file="$DEPLOY_DIR/health_reports/health_report_$(date +%Y%m%d_%H%M%S).json"
    
    mkdir -p "$(dirname "$report_file")"
    
    cat > "$report_file" << EOF
{
  "timestamp": "$timestamp",
  "environment": "$ENVIRONMENT",
  "checks": {
    "service_status": $(check_service_status >/dev/null 2>&1 && echo "true" || echo "false"),
    "api_health": $(check_api_health >/dev/null 2>&1 && echo "true" || echo "false"),
    "i18n_functionality": $(check_i18n_functionality >/dev/null 2>&1 && echo "true" || echo "false"),
    "performance": $(check_performance >/dev/null 2>&1 && echo "true" || echo "false"),
    "cache": $(check_cache_functionality >/dev/null 2>&1 && echo "true" || echo "false"),
    "database": $(check_database_connectivity >/dev/null 2>&1 && echo "true" || echo "false")
  }
}
EOF
    
    log_info "Health report saved: $report_file"
}

# Main health check function
main() {
    log_info "Starting SuperInsight i18n health check..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Base URL: $BASE_URL"
    
    local overall_health=true
    
    # Core health checks
    check_service_status || overall_health=false
    check_api_health || overall_health=false
    check_i18n_functionality || overall_health=false
    
    # Additional checks for detailed mode
    if [[ "$DETAILED_CHECK" == "--detailed" ]]; then
        log_info "Running detailed health checks..."
        check_performance || overall_health=false
        check_cache_functionality || overall_health=false
        check_database_connectivity || overall_health=false
        check_monitoring || overall_health=false
        
        # Generate report
        generate_health_report
    fi
    
    # Summary
    echo ""
    if [[ "$overall_health" == "true" ]]; then
        log_success "Overall health: HEALTHY ✓"
        exit 0
    else
        log_error "Overall health: UNHEALTHY ✗"
        exit 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi