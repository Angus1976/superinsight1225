#!/bin/bash

# SuperInsight i18n Deployment Script
# Usage: ./deploy.sh [environment] [version]
# Example: ./deploy.sh production v1.0.0

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_DIR="$PROJECT_ROOT/deploy/i18n"

# Default values
ENVIRONMENT="${1:-staging}"
VERSION="${2:-latest}"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"
ENV_FILE="$DEPLOY_DIR/.env.$ENVIRONMENT"

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

# Validation functions
validate_environment() {
    case "$ENVIRONMENT" in
        development|staging|production)
            log_info "Deploying to $ENVIRONMENT environment"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_error "Valid environments: development, staging, production"
            exit 1
            ;;
    esac
}

validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check if environment file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning "Environment file not found: $ENV_FILE"
        log_info "Creating default environment file..."
        create_env_file
    fi
    
    log_success "Prerequisites validated"
}

create_env_file() {
    cat > "$ENV_FILE" << EOF
# SuperInsight i18n Environment Configuration
# Environment: $ENVIRONMENT
# Generated: $(date)

# Application Settings
ENVIRONMENT=$ENVIRONMENT
VERSION=$VERSION
DEBUG_MODE=false

# I18n Configuration
I18N_DEFAULT_LANGUAGE=zh
I18N_SUPPORTED_LANGUAGES=zh,en
I18N_FALLBACK_LANGUAGE=zh

# Cache Configuration
I18N_CACHE_ENABLED=true
I18N_CACHE_TTL=300
I18N_CACHE_MAX_SIZE=1000
I18N_CACHE_BACKEND=redis

# Redis Configuration
I18N_REDIS_HOST=redis
I18N_REDIS_PORT=6379
I18N_REDIS_DB=0
I18N_REDIS_PASSWORD=

# Database Configuration
DATABASE_URL=postgresql://superinsight:password@postgres:5432/superinsight

# Logging Configuration
I18N_LOG_LEVEL=INFO
I18N_LOG_MISSING_KEYS=true
I18N_LOG_LANGUAGE_CHANGES=false

# Security Configuration
I18N_API_RATE_LIMIT=100
I18N_API_TIMEOUT=30

# Monitoring Configuration
I18N_METRICS_ENABLED=true
I18N_HEALTH_CHECK_ENABLED=true

# Feature Flags
I18N_VALIDATION_ENABLED=true
I18N_STRICT_MODE=false
EOF
    
    log_success "Environment file created: $ENV_FILE"
}

backup_current_deployment() {
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_info "Creating backup of current deployment..."
        
        BACKUP_DIR="$DEPLOY_DIR/backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Backup database
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
            pg_dump -U superinsight superinsight > "$BACKUP_DIR/database.sql" || true
        
        # Backup configuration
        cp -r "$DEPLOY_DIR/config" "$BACKUP_DIR/" || true
        
        # Backup logs
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs > "$BACKUP_DIR/logs.txt" || true
        
        log_success "Backup created: $BACKUP_DIR"
    fi
}

build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Build main application image
    docker build \
        --target production \
        --build-arg BUILD_ENV="$ENVIRONMENT" \
        --build-arg I18N_VERSION="$VERSION" \
        -t "superinsight/api:$VERSION" \
        -f "$DEPLOY_DIR/Dockerfile" \
        .
    
    # Tag as latest for the environment
    docker tag "superinsight/api:$VERSION" "superinsight/api:$ENVIRONMENT-latest"
    
    log_success "Docker images built successfully"
}

run_pre_deployment_tests() {
    log_info "Running pre-deployment tests..."
    
    # Build test image
    docker build \
        --target testing \
        --build-arg BUILD_ENV="testing" \
        -t "superinsight/api:test" \
        -f "$DEPLOY_DIR/Dockerfile" \
        "$PROJECT_ROOT"
    
    # Run tests
    docker run --rm \
        -e I18N_TESTING=true \
        -e I18N_LOG_LEVEL=WARNING \
        "superinsight/api:test" \
        python -m pytest tests/unit/test_i18n* -v --tb=short
    
    log_success "Pre-deployment tests passed"
}

deploy_services() {
    log_info "Deploying services..."
    
    cd "$DEPLOY_DIR"
    
    # Pull latest images for external services
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull redis postgres nginx
    
    # Start services
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    
    log_success "Services deployed"
}

wait_for_services() {
    log_info "Waiting for services to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "Health check attempt $attempt/$max_attempts"
        
        # Check API health
        if curl -f -s "http://localhost:8000/health/i18n" > /dev/null 2>&1; then
            log_success "API is healthy"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Services failed to become healthy within timeout"
            show_service_logs
            exit 1
        fi
        
        sleep 10
        ((attempt++))
    done
}

run_post_deployment_tests() {
    log_info "Running post-deployment tests..."
    
    # Test API endpoints
    test_api_endpoint() {
        local endpoint="$1"
        local expected_status="$2"
        
        local status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000$endpoint")
        
        if [[ "$status" == "$expected_status" ]]; then
            log_success "✓ $endpoint returned $status"
        else
            log_error "✗ $endpoint returned $status, expected $expected_status"
            return 1
        fi
    }
    
    # Test i18n endpoints
    test_api_endpoint "/health/i18n" "200"
    test_api_endpoint "/api/settings/language" "200"
    test_api_endpoint "/api/i18n/languages" "200"
    test_api_endpoint "/api/i18n/translations?language=zh" "200"
    test_api_endpoint "/api/i18n/translations?language=en" "200"
    
    # Test language switching
    log_info "Testing language switching..."
    
    local response=$(curl -s -X POST "http://localhost:8000/api/settings/language" \
        -H "Content-Type: application/json" \
        -d '{"language": "en"}')
    
    if echo "$response" | grep -q '"current_language": "en"'; then
        log_success "✓ Language switching works"
    else
        log_error "✗ Language switching failed"
        return 1
    fi
    
    log_success "Post-deployment tests passed"
}

show_service_logs() {
    log_info "Showing service logs..."
    
    cd "$DEPLOY_DIR"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=50
}

show_deployment_info() {
    log_info "Deployment Information:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Version: $VERSION"
    echo "  API URL: http://localhost:8000"
    echo "  Health Check: http://localhost:8000/health/i18n"
    echo "  Monitoring: http://localhost:3000 (Grafana)"
    echo "  Metrics: http://localhost:9090 (Prometheus)"
    echo ""
    
    log_info "Service Status:"
    cd "$DEPLOY_DIR"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
}

cleanup_old_images() {
    log_info "Cleaning up old Docker images..."
    
    # Remove old images (keep last 3 versions)
    docker images "superinsight/api" --format "table {{.Tag}}\t{{.ID}}" | \
        grep -v "latest\|$VERSION" | \
        tail -n +4 | \
        awk '{print $2}' | \
        xargs -r docker rmi || true
    
    # Remove dangling images
    docker image prune -f || true
    
    log_success "Cleanup completed"
}

rollback_deployment() {
    log_error "Deployment failed. Rolling back..."
    
    cd "$DEPLOY_DIR"
    
    # Stop current services
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down || true
    
    # Restore from backup if available
    local latest_backup=$(ls -1t "$DEPLOY_DIR/backups/" 2>/dev/null | head -n1)
    
    if [[ -n "$latest_backup" && "$ENVIRONMENT" == "production" ]]; then
        log_info "Restoring from backup: $latest_backup"
        
        # Restore database
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d postgres
        sleep 10
        
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
            psql -U superinsight -d superinsight < "$DEPLOY_DIR/backups/$latest_backup/database.sql" || true
    fi
    
    log_error "Rollback completed. Please check the logs and try again."
    exit 1
}

# Main deployment function
main() {
    log_info "Starting SuperInsight i18n deployment..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Version: $VERSION"
    
    # Set up error handling
    trap rollback_deployment ERR
    
    # Validation
    validate_environment
    validate_prerequisites
    
    # Pre-deployment
    if [[ "$ENVIRONMENT" == "production" ]]; then
        backup_current_deployment
    fi
    
    # Build and test
    build_images
    
    if [[ "$ENVIRONMENT" != "development" ]]; then
        run_pre_deployment_tests
    fi
    
    # Deploy
    deploy_services
    wait_for_services
    
    # Post-deployment
    run_post_deployment_tests
    show_deployment_info
    
    # Cleanup
    cleanup_old_images
    
    log_success "Deployment completed successfully!"
    
    # Remove error trap
    trap - ERR
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi