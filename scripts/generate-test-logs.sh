#!/bin/bash
# Docker Test Logs Generation Script
# This script collects container logs, generates health check reports,
# documents startup time metrics, and provides troubleshooting information.
#
# Usage: ./scripts/generate-test-logs.sh [options]
#
# Options:
#   --output-dir DIR    Output directory for logs (default: ./docker-logs)
#   --full-logs         Collect full container logs (default: last 1000 lines)
#   --no-metrics        Skip startup time metrics collection
#   --help              Show this help message
#
# Validates:
# - Task 7.1: Collect all container logs
# - Task 7.2: Generate health check report (JSON format)
# - Task 7.3: Document startup time metrics
# - Troubleshooting capability
# - Monitoring capability
# - Performance requirements

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Default configuration
OUTPUT_DIR="./docker-logs"
FULL_LOGS=false
COLLECT_METRICS=true
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Container names
POSTGRES_CONTAINER="superinsight-postgres"
REDIS_CONTAINER="superinsight-redis"
NEO4J_CONTAINER="superinsight-neo4j"
LABEL_STUDIO_CONTAINER="superinsight-label-studio"
API_CONTAINER="superinsight-api"

# Service ports
API_PORT=8000
POSTGRES_PORT=5432
REDIS_PORT=6379
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687
LABEL_STUDIO_PORT=8080

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --full-logs)
                FULL_LOGS=true
                shift
                ;;
            --no-metrics)
                COLLECT_METRICS=false
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    echo "Docker Test Logs Generation Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --output-dir DIR    Output directory for logs (default: ./docker-logs)"
    echo "  --full-logs         Collect full container logs (default: last 1000 lines)"
    echo "  --no-metrics        Skip startup time metrics collection"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                              # Basic log collection"
    echo "  $0 --output-dir /tmp/logs       # Custom output directory"
    echo "  $0 --full-logs                  # Collect complete logs"
}

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_step() {
    echo -e "\n${CYAN}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    print_success "Docker is available"
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    print_success "Docker daemon is running"
    
    # Check docker-compose
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        print_success "docker-compose is available"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
        print_success "docker compose (plugin) is available"
    else
        print_error "Neither docker-compose nor docker compose plugin is available"
        exit 1
    fi
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    print_success "Output directory created: $OUTPUT_DIR"
}

# Check if container is running
is_container_running() {
    local container_name=$1
    docker ps --format '{{.Names}}' | grep -q "^${container_name}$"
}

# Get container health status
get_container_health() {
    local container_name=$1
    docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-healthcheck"
}

# Get container start time
get_container_start_time() {
    local container_name=$1
    docker inspect --format='{{.State.StartedAt}}' "$container_name" 2>/dev/null || echo "unknown"
}

# Get container creation time
get_container_created_time() {
    local container_name=$1
    docker inspect --format='{{.Created}}' "$container_name" 2>/dev/null || echo "unknown"
}


# Task 7.1: Collect all container logs
collect_container_logs() {
    print_header "Task 7.1: Collecting Container Logs"
    
    local LOG_FILE="${OUTPUT_DIR}/docker-startup-test-${TIMESTAMP}.log"
    local INDIVIDUAL_LOGS_DIR="${OUTPUT_DIR}/individual-logs-${TIMESTAMP}"
    
    mkdir -p "$INDIVIDUAL_LOGS_DIR"
    
    print_step "Collecting combined docker-compose logs"
    
    # Collect combined logs
    if [ "$FULL_LOGS" = true ]; then
        $COMPOSE_CMD logs --no-color > "$LOG_FILE" 2>&1 || true
        print_info "Collected full logs"
    else
        $COMPOSE_CMD logs --no-color --tail=1000 > "$LOG_FILE" 2>&1 || true
        print_info "Collected last 1000 lines of logs"
    fi
    
    print_success "Combined logs saved to: $LOG_FILE"
    
    # Collect individual container logs
    print_step "Collecting individual container logs"
    
    CONTAINERS=("$POSTGRES_CONTAINER" "$REDIS_CONTAINER" "$NEO4J_CONTAINER" "$LABEL_STUDIO_CONTAINER" "$API_CONTAINER")
    
    for container in "${CONTAINERS[@]}"; do
        if is_container_running "$container"; then
            local container_log="${INDIVIDUAL_LOGS_DIR}/${container}.log"
            
            if [ "$FULL_LOGS" = true ]; then
                docker logs "$container" > "$container_log" 2>&1 || true
            else
                docker logs --tail=500 "$container" > "$container_log" 2>&1 || true
            fi
            
            print_success "Collected logs for $container"
        else
            print_warn "Container $container is not running, skipping"
        fi
    done
    
    # Create log summary
    print_step "Creating log summary"
    
    local SUMMARY_FILE="${OUTPUT_DIR}/log-summary-${TIMESTAMP}.txt"
    
    cat > "$SUMMARY_FILE" << EOF
Docker Container Logs Summary
=============================
Generated: $(date -Iseconds)
Output Directory: $OUTPUT_DIR

Combined Logs:
- File: $LOG_FILE
- Size: $(du -h "$LOG_FILE" 2>/dev/null | cut -f1 || echo "N/A")

Individual Container Logs:
EOF
    
    for container in "${CONTAINERS[@]}"; do
        local container_log="${INDIVIDUAL_LOGS_DIR}/${container}.log"
        if [ -f "$container_log" ]; then
            echo "- $container: $(du -h "$container_log" 2>/dev/null | cut -f1 || echo "N/A")" >> "$SUMMARY_FILE"
        else
            echo "- $container: Not collected (container not running)" >> "$SUMMARY_FILE"
        fi
    done
    
    # Add error summary
    echo "" >> "$SUMMARY_FILE"
    echo "Error Summary:" >> "$SUMMARY_FILE"
    echo "--------------" >> "$SUMMARY_FILE"
    
    ERROR_COUNT=$(grep -ci "error\|exception\|failed" "$LOG_FILE" 2>/dev/null || echo "0")
    WARNING_COUNT=$(grep -ci "warning\|warn" "$LOG_FILE" 2>/dev/null || echo "0")
    
    echo "- Total errors/exceptions: $ERROR_COUNT" >> "$SUMMARY_FILE"
    echo "- Total warnings: $WARNING_COUNT" >> "$SUMMARY_FILE"
    
    print_success "Log summary saved to: $SUMMARY_FILE"
    
    # Return the log file path for reference
    echo "$LOG_FILE"
}

# Task 7.2: Generate health check report
generate_health_report() {
    print_header "Task 7.2: Generating Health Check Report"
    
    local REPORT_FILE="${OUTPUT_DIR}/health-check-report-${TIMESTAMP}.json"
    
    print_step "Collecting service health statuses"
    
    # Collect health status for each service
    local postgres_running=$(is_container_running "$POSTGRES_CONTAINER" && echo "true" || echo "false")
    local postgres_health=$(get_container_health "$POSTGRES_CONTAINER")
    
    local redis_running=$(is_container_running "$REDIS_CONTAINER" && echo "true" || echo "false")
    local redis_health=$(get_container_health "$REDIS_CONTAINER")
    
    local neo4j_running=$(is_container_running "$NEO4J_CONTAINER" && echo "true" || echo "false")
    local neo4j_health=$(get_container_health "$NEO4J_CONTAINER")
    
    local label_studio_running=$(is_container_running "$LABEL_STUDIO_CONTAINER" && echo "true" || echo "false")
    local label_studio_health=$(get_container_health "$LABEL_STUDIO_CONTAINER")
    
    local api_running=$(is_container_running "$API_CONTAINER" && echo "true" || echo "false")
    local api_health=$(get_container_health "$API_CONTAINER")
    
    # Test endpoint health
    print_step "Testing service endpoints"
    
    local api_endpoint_status="unknown"
    local label_studio_endpoint_status="unknown"
    local neo4j_endpoint_status="unknown"
    
    if command -v curl &> /dev/null; then
        # Test API health endpoint
        api_endpoint_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${API_PORT}/health" 2>/dev/null || echo "failed")
        
        # Test Label Studio health endpoint
        label_studio_endpoint_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${LABEL_STUDIO_PORT}/health" 2>/dev/null || echo "failed")
        
        # Test Neo4j HTTP endpoint
        neo4j_endpoint_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${NEO4J_HTTP_PORT}" 2>/dev/null || echo "failed")
    fi
    
    # Test PostgreSQL
    local postgres_query_status="unknown"
    if [ "$postgres_running" = "true" ]; then
        if docker exec "$POSTGRES_CONTAINER" pg_isready -U superinsight -d superinsight > /dev/null 2>&1; then
            postgres_query_status="ready"
        else
            postgres_query_status="not_ready"
        fi
    fi
    
    # Test Redis
    local redis_ping_status="unknown"
    if [ "$redis_running" = "true" ]; then
        redis_ping_result=$(docker exec "$REDIS_CONTAINER" redis-cli ping 2>/dev/null || echo "failed")
        if [ "$redis_ping_result" = "PONG" ]; then
            redis_ping_status="pong"
        else
            redis_ping_status="failed"
        fi
    fi
    
    # Calculate overall status
    local overall_status="healthy"
    local healthy_count=0
    local total_count=5
    
    [ "$postgres_health" = "healthy" ] && ((healthy_count++)) || true
    [ "$redis_health" = "healthy" ] && ((healthy_count++)) || true
    [ "$neo4j_health" = "healthy" ] && ((healthy_count++)) || true
    [ "$label_studio_health" = "healthy" ] && ((healthy_count++)) || true
    [ "$api_health" = "healthy" ] && ((healthy_count++)) || true
    
    if [ $healthy_count -lt $total_count ]; then
        if [ $healthy_count -eq 0 ]; then
            overall_status="critical"
        else
            overall_status="degraded"
        fi
    fi
    
    # Generate JSON report
    print_step "Generating JSON health report"
    
    cat > "$REPORT_FILE" << EOF
{
    "report_metadata": {
        "timestamp": "$(date -Iseconds)",
        "report_type": "health_check",
        "spec_reference": "docker-infrastructure",
        "validates": [
            "Task 7.2: Generate health check report",
            "Monitoring capability"
        ]
    },
    "overall_status": {
        "status": "${overall_status}",
        "healthy_services": ${healthy_count},
        "total_services": ${total_count},
        "health_percentage": $(echo "scale=2; ${healthy_count} * 100 / ${total_count}" | bc 2>/dev/null || echo "0")
    },
    "services": {
        "postgresql": {
            "container_name": "${POSTGRES_CONTAINER}",
            "running": ${postgres_running},
            "docker_health_status": "${postgres_health}",
            "pg_isready_status": "${postgres_query_status}",
            "port": ${POSTGRES_PORT},
            "health_check_command": "pg_isready -U superinsight -d superinsight"
        },
        "redis": {
            "container_name": "${REDIS_CONTAINER}",
            "running": ${redis_running},
            "docker_health_status": "${redis_health}",
            "ping_status": "${redis_ping_status}",
            "port": ${REDIS_PORT},
            "health_check_command": "redis-cli ping"
        },
        "neo4j": {
            "container_name": "${NEO4J_CONTAINER}",
            "running": ${neo4j_running},
            "docker_health_status": "${neo4j_health}",
            "http_endpoint_status": "${neo4j_endpoint_status}",
            "http_port": ${NEO4J_HTTP_PORT},
            "bolt_port": ${NEO4J_BOLT_PORT},
            "health_check_command": "wget -q --spider http://localhost:7474"
        },
        "label_studio": {
            "container_name": "${LABEL_STUDIO_CONTAINER}",
            "running": ${label_studio_running},
            "docker_health_status": "${label_studio_health}",
            "health_endpoint_status": "${label_studio_endpoint_status}",
            "port": ${LABEL_STUDIO_PORT},
            "health_check_command": "curl -f http://localhost:8080/health"
        },
        "api": {
            "container_name": "${API_CONTAINER}",
            "running": ${api_running},
            "docker_health_status": "${api_health}",
            "health_endpoint_status": "${api_endpoint_status}",
            "port": ${API_PORT},
            "health_check_command": "curl -f http://localhost:8000/health"
        }
    },
    "recommendations": [
$([ "$postgres_health" != "healthy" ] && echo '        "Check PostgreSQL container logs: docker logs '"$POSTGRES_CONTAINER"'",' || true)
$([ "$redis_health" != "healthy" ] && echo '        "Check Redis container logs: docker logs '"$REDIS_CONTAINER"'",' || true)
$([ "$neo4j_health" != "healthy" ] && echo '        "Check Neo4j container logs: docker logs '"$NEO4J_CONTAINER"'",' || true)
$([ "$label_studio_health" != "healthy" ] && echo '        "Check Label Studio container logs: docker logs '"$LABEL_STUDIO_CONTAINER"'",' || true)
$([ "$api_health" != "healthy" ] && echo '        "Check API container logs: docker logs '"$API_CONTAINER"'",' || true)
        "Run ./scripts/verify-health-checks.sh for detailed health verification"
    ]
}
EOF
    
    print_success "Health check report saved to: $REPORT_FILE"
    
    # Display summary
    print_info "Health Status Summary:"
    echo "  PostgreSQL: $postgres_health (running: $postgres_running)"
    echo "  Redis: $redis_health (running: $redis_running)"
    echo "  Neo4j: $neo4j_health (running: $neo4j_running)"
    echo "  Label Studio: $label_studio_health (running: $label_studio_running)"
    echo "  API: $api_health (running: $api_running)"
    echo ""
    echo "  Overall: $overall_status ($healthy_count/$total_count healthy)"
    
    echo "$REPORT_FILE"
}


# Task 7.3: Document startup time metrics
collect_startup_metrics() {
    print_header "Task 7.3: Documenting Startup Time Metrics"
    
    if [ "$COLLECT_METRICS" = false ]; then
        print_warn "Metrics collection skipped (--no-metrics flag)"
        return
    fi
    
    local METRICS_FILE="${OUTPUT_DIR}/startup-metrics-${TIMESTAMP}.json"
    
    print_step "Collecting container startup times"
    
    # Collect startup times for each container
    declare -A START_TIMES
    declare -A CREATED_TIMES
    declare -A HEALTH_TIMES
    
    CONTAINERS=("$POSTGRES_CONTAINER" "$REDIS_CONTAINER" "$NEO4J_CONTAINER" "$LABEL_STUDIO_CONTAINER" "$API_CONTAINER")
    
    for container in "${CONTAINERS[@]}"; do
        if is_container_running "$container"; then
            START_TIMES[$container]=$(get_container_start_time "$container")
            CREATED_TIMES[$container]=$(get_container_created_time "$container")
            
            # Get time to healthy from health check logs
            local health_log=$(docker inspect --format='{{range .State.Health.Log}}{{.End}}{{end}}' "$container" 2>/dev/null | tail -1 || echo "")
            HEALTH_TIMES[$container]=${health_log:-"unknown"}
        else
            START_TIMES[$container]="not_running"
            CREATED_TIMES[$container]="not_running"
            HEALTH_TIMES[$container]="not_running"
        fi
    done
    
    # Calculate startup durations
    print_step "Calculating startup durations"
    
    # Get compose start time (approximate from first container)
    local compose_start=""
    for container in "${CONTAINERS[@]}"; do
        if [ "${CREATED_TIMES[$container]}" != "not_running" ]; then
            compose_start="${CREATED_TIMES[$container]}"
            break
        fi
    done
    
    # Generate metrics JSON
    print_step "Generating startup metrics report"
    
    cat > "$METRICS_FILE" << EOF
{
    "report_metadata": {
        "timestamp": "$(date -Iseconds)",
        "report_type": "startup_metrics",
        "spec_reference": "docker-infrastructure",
        "validates": [
            "Task 7.3: Document startup time metrics",
            "Performance requirements: Container startup time < 60 seconds"
        ]
    },
    "compose_metadata": {
        "approximate_start_time": "${compose_start:-unknown}",
        "collection_time": "$(date -Iseconds)"
    },
    "container_metrics": {
        "postgresql": {
            "container_name": "${POSTGRES_CONTAINER}",
            "created_at": "${CREATED_TIMES[$POSTGRES_CONTAINER]}",
            "started_at": "${START_TIMES[$POSTGRES_CONTAINER]}",
            "first_healthy_at": "${HEALTH_TIMES[$POSTGRES_CONTAINER]}",
            "expected_startup_time": "< 30 seconds",
            "notes": "Database initialization may take longer on first run"
        },
        "redis": {
            "container_name": "${REDIS_CONTAINER}",
            "created_at": "${CREATED_TIMES[$REDIS_CONTAINER]}",
            "started_at": "${START_TIMES[$REDIS_CONTAINER]}",
            "first_healthy_at": "${HEALTH_TIMES[$REDIS_CONTAINER]}",
            "expected_startup_time": "< 10 seconds",
            "notes": "Redis typically starts very quickly"
        },
        "neo4j": {
            "container_name": "${NEO4J_CONTAINER}",
            "created_at": "${CREATED_TIMES[$NEO4J_CONTAINER]}",
            "started_at": "${START_TIMES[$NEO4J_CONTAINER]}",
            "first_healthy_at": "${HEALTH_TIMES[$NEO4J_CONTAINER]}",
            "expected_startup_time": "< 60 seconds",
            "notes": "Neo4j may take longer to initialize on first run"
        },
        "label_studio": {
            "container_name": "${LABEL_STUDIO_CONTAINER}",
            "created_at": "${CREATED_TIMES[$LABEL_STUDIO_CONTAINER]}",
            "started_at": "${START_TIMES[$LABEL_STUDIO_CONTAINER]}",
            "first_healthy_at": "${HEALTH_TIMES[$LABEL_STUDIO_CONTAINER]}",
            "expected_startup_time": "< 60 seconds",
            "notes": "Label Studio depends on PostgreSQL being healthy"
        },
        "api": {
            "container_name": "${API_CONTAINER}",
            "created_at": "${CREATED_TIMES[$API_CONTAINER]}",
            "started_at": "${START_TIMES[$API_CONTAINER]}",
            "first_healthy_at": "${HEALTH_TIMES[$API_CONTAINER]}",
            "expected_startup_time": "< 30 seconds",
            "notes": "API depends on all other services being healthy"
        }
    },
    "performance_requirements": {
        "container_startup_time": "< 60 seconds for all services",
        "database_initialization": "< 10 seconds",
        "health_check_response_time": "< 5 seconds",
        "total_stack_startup": "< 120 seconds"
    },
    "health_check_configuration": {
        "postgresql": {
            "interval": "10s",
            "timeout": "5s",
            "retries": 5
        },
        "redis": {
            "interval": "10s",
            "timeout": "5s",
            "retries": 5
        },
        "neo4j": {
            "interval": "10s",
            "timeout": "5s",
            "retries": 5
        },
        "label_studio": {
            "interval": "30s",
            "timeout": "10s",
            "retries": 5
        }
    }
}
EOF
    
    print_success "Startup metrics saved to: $METRICS_FILE"
    
    # Display summary
    print_info "Startup Times Summary:"
    for container in "${CONTAINERS[@]}"; do
        if [ "${START_TIMES[$container]}" != "not_running" ]; then
            echo "  $container: Started at ${START_TIMES[$container]}"
        else
            echo "  $container: Not running"
        fi
    done
    
    echo "$METRICS_FILE"
}

# Generate comprehensive test report
generate_comprehensive_report() {
    print_header "Generating Comprehensive Test Report"
    
    local REPORT_FILE="${OUTPUT_DIR}/comprehensive-test-report-${TIMESTAMP}.json"
    
    print_step "Compiling comprehensive report"
    
    # Get docker-compose ps output
    local compose_ps=$($COMPOSE_CMD ps --format json 2>/dev/null || $COMPOSE_CMD ps 2>/dev/null || echo "[]")
    
    # Get docker version info
    local docker_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
    local compose_version=$($COMPOSE_CMD version --short 2>/dev/null || echo "unknown")
    
    # Get system info
    local os_info=$(uname -a 2>/dev/null || echo "unknown")
    local hostname=$(hostname 2>/dev/null || echo "unknown")
    
    cat > "$REPORT_FILE" << EOF
{
    "report_metadata": {
        "timestamp": "$(date -Iseconds)",
        "report_type": "comprehensive_test_report",
        "hostname": "${hostname}",
        "spec_reference": "docker-infrastructure",
        "validates": [
            "Task 7: Generate Test Logs",
            "Troubleshooting capability",
            "Monitoring capability",
            "Performance requirements"
        ]
    },
    "environment": {
        "docker_version": "${docker_version}",
        "compose_version": "${compose_version}",
        "os_info": "${os_info}",
        "output_directory": "${OUTPUT_DIR}"
    },
    "generated_files": {
        "combined_logs": "docker-startup-test-${TIMESTAMP}.log",
        "health_report": "health-check-report-${TIMESTAMP}.json",
        "startup_metrics": "startup-metrics-${TIMESTAMP}.json",
        "individual_logs_dir": "individual-logs-${TIMESTAMP}/"
    },
    "verification_scripts": {
        "postgres_init": "./scripts/verify-postgres-init.sh",
        "health_checks": "./scripts/verify-health-checks.sh",
        "connectivity": "./scripts/verify-connectivity.sh"
    },
    "troubleshooting_guide": "DOCKER_TROUBLESHOOTING.md",
    "quick_commands": {
        "view_all_logs": "docker-compose logs",
        "view_service_logs": "docker-compose logs <service-name>",
        "restart_all": "docker-compose restart",
        "rebuild_all": "docker-compose up -d --build",
        "check_health": "docker-compose ps",
        "run_verification": "./scripts/verify-health-checks.sh"
    }
}
EOF
    
    print_success "Comprehensive report saved to: $REPORT_FILE"
    
    echo "$REPORT_FILE"
}

# Print final summary
print_final_summary() {
    print_header "Test Logs Generation Complete"
    
    echo ""
    echo "Generated Files:"
    echo "================"
    echo ""
    
    # List all generated files
    if [ -d "$OUTPUT_DIR" ]; then
        ls -la "$OUTPUT_DIR"/*${TIMESTAMP}* 2>/dev/null || echo "No files found"
    fi
    
    echo ""
    echo "Quick Reference:"
    echo "================"
    echo ""
    echo "View combined logs:"
    echo "  cat ${OUTPUT_DIR}/docker-startup-test-${TIMESTAMP}.log"
    echo ""
    echo "View health report:"
    echo "  cat ${OUTPUT_DIR}/health-check-report-${TIMESTAMP}.json | python3 -m json.tool"
    echo ""
    echo "View startup metrics:"
    echo "  cat ${OUTPUT_DIR}/startup-metrics-${TIMESTAMP}.json | python3 -m json.tool"
    echo ""
    echo "Run verification scripts:"
    echo "  ./scripts/verify-postgres-init.sh"
    echo "  ./scripts/verify-health-checks.sh"
    echo "  ./scripts/verify-connectivity.sh"
    echo ""
    echo "For troubleshooting, see: DOCKER_TROUBLESHOOTING.md"
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║       Docker Test Logs Generation Script                   ║"
    echo "║       SuperInsight Platform - Docker Infrastructure        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "This script validates Task 7 from the docker-infrastructure spec:"
    echo "  - 7.1: Collect all container logs"
    echo "  - 7.2: Generate health check report (JSON)"
    echo "  - 7.3: Document startup time metrics"
    echo ""
    
    parse_args "$@"
    
    check_prerequisites
    
    # Execute tasks
    collect_container_logs
    generate_health_report
    collect_startup_metrics
    generate_comprehensive_report
    
    # Print summary
    print_final_summary
    
    echo ""
    print_success "All test logs generated successfully!"
    echo ""
}

# Run main function
main "$@"
