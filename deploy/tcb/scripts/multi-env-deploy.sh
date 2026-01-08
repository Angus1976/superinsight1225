#!/bin/bash
# SuperInsight TCB Multi-Environment Deployment Script
# Supports development, staging, and production environments with blue-green deployment

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
TCB_CONFIG_DIR="${SCRIPT_DIR}/../config"
ENV_CONFIG_DIR="${SCRIPT_DIR}/../env"

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

# Default values
ENVIRONMENT=""
DEPLOYMENT_MODE="rolling"  # rolling, blue-green, canary
DRY_RUN=false
SKIP_TESTS=false
SKIP_HEALTH_CHECK=false
ROLLBACK_ON_FAILURE=true
BACKUP_BEFORE_DEPLOY=true
FORCE_DEPLOY=false

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

SuperInsight TCB Multi-Environment Deployment Script

OPTIONS:
    -e, --environment ENV       Target environment (development|staging|production)
    -m, --mode MODE            Deployment mode (rolling|blue-green|canary)
    -d, --dry-run              Perform a dry run without actual deployment
    -t, --skip-tests           Skip running tests before deployment
    -h, --skip-health-check    Skip health checks after deployment
    -n, --no-rollback          Don't rollback on deployment failure
    -b, --no-backup            Skip backup before deployment
    -f, --force                Force deployment even if validation fails
    --help                     Show this help message

EXAMPLES:
    # Deploy to development environment
    $0 -e development

    # Deploy to production with blue-green strategy
    $0 -e production -m blue-green

    # Dry run for staging deployment
    $0 -e staging --dry-run

    # Force deploy to production (skip validations)
    $0 -e production --force

ENVIRONMENT VARIABLES:
    TCB_SECRET_ID              Tencent Cloud Secret ID
    TCB_SECRET_KEY             Tencent Cloud Secret Key
    TCB_ENV_ID                 CloudBase Environment ID (optional, read from config)
    GITHUB_TOKEN               GitHub token for accessing private repos
    SLACK_WEBHOOK_URL          Slack webhook for notifications (optional)

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -m|--mode)
                DEPLOYMENT_MODE="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -t|--skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            -h|--skip-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            -n|--no-rollback)
                ROLLBACK_ON_FAILURE=false
                shift
                ;;
            -b|--no-backup)
                BACKUP_BEFORE_DEPLOY=false
                shift
                ;;
            -f|--force)
                FORCE_DEPLOY=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Validate environment
validate_environment() {
    local valid_envs=("development" "staging" "production")
    
    if [[ -z "$ENVIRONMENT" ]]; then
        log_error "Environment not specified. Use -e or --environment option."
        show_usage
        exit 1
    fi
    
    if [[ ! " ${valid_envs[@]} " =~ " ${ENVIRONMENT} " ]]; then
        log_error "Invalid environment: $ENVIRONMENT"
        log_error "Valid environments: ${valid_envs[*]}"
        exit 1
    fi
    
    log_info "Target environment: $ENVIRONMENT"
}

# Validate deployment mode
validate_deployment_mode() {
    local valid_modes=("rolling" "blue-green" "canary")
    
    if [[ ! " ${valid_modes[@]} " =~ " ${DEPLOYMENT_MODE} " ]]; then
        log_error "Invalid deployment mode: $DEPLOYMENT_MODE"
        log_error "Valid modes: ${valid_modes[*]}"
        exit 1
    fi
    
    log_info "Deployment mode: $DEPLOYMENT_MODE"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required tools
    local required_tools=("docker" "tcb" "kubectl" "jq" "curl")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool not found: $tool"
            exit 1
        fi
    done
    
    # Check TCB CLI authentication
    if ! tcb auth list &> /dev/null; then
        log_error "TCB CLI not authenticated. Please run 'tcb login' first."
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon not running or not accessible."
        exit 1
    fi
    
    # Check environment configuration file
    local env_file="${ENV_CONFIG_DIR}/${ENVIRONMENT}.env"
    if [[ ! -f "$env_file" ]]; then
        log_error "Environment configuration file not found: $env_file"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Load environment configuration
load_environment_config() {
    log_info "Loading environment configuration..."
    
    local env_file="${ENV_CONFIG_DIR}/${ENVIRONMENT}.env"
    
    # Source the environment file
    set -a  # Automatically export all variables
    source "$env_file"
    set +a
    
    # Validate required environment variables
    local required_vars=("TCB_ENV_ID" "TCB_REGION")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable not set: $var"
            exit 1
        fi
    done
    
    log_success "Environment configuration loaded"
    log_info "TCB Environment ID: $TCB_ENV_ID"
    log_info "TCB Region: $TCB_REGION"
}

# Run pre-deployment tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "Skipping tests as requested"
        return 0
    fi
    
    log_info "Running pre-deployment tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run unit tests
    if [[ -f "requirements.txt" ]]; then
        log_info "Running Python tests..."
        python -m pytest tests/ -v --tb=short || {
            log_error "Tests failed"
            return 1
        }
    fi
    
    # Run frontend tests if applicable
    if [[ -f "frontend/package.json" ]]; then
        log_info "Running frontend tests..."
        cd frontend
        npm test -- --run || {
            log_error "Frontend tests failed"
            return 1
        }
        cd "$PROJECT_ROOT"
    fi
    
    log_success "All tests passed"
}

# Create backup before deployment
create_backup() {
    if [[ "$BACKUP_BEFORE_DEPLOY" == "false" ]]; then
        log_warning "Skipping backup as requested"
        return 0
    fi
    
    log_info "Creating backup before deployment..."
    
    local backup_script="${SCRIPT_DIR}/backup/backup-manager.sh"
    if [[ -f "$backup_script" ]]; then
        bash "$backup_script" --environment "$ENVIRONMENT" --type full || {
            log_error "Backup creation failed"
            return 1
        }
    else
        log_warning "Backup script not found, skipping backup"
    fi
    
    log_success "Backup created successfully"
}

# Build Docker image
build_docker_image() {
    log_info "Building Docker image..."
    
    local image_tag="superinsight:${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
    local dockerfile="${PROJECT_ROOT}/deploy/tcb/Dockerfile.fullstack"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would build image: $image_tag"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    docker build \
        -f "$dockerfile" \
        -t "$image_tag" \
        --build-arg ENVIRONMENT="$ENVIRONMENT" \
        --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --build-arg VCS_REF="$(git rev-parse HEAD)" \
        . || {
        log_error "Docker image build failed"
        return 1
    }
    
    # Tag as latest for the environment
    docker tag "$image_tag" "superinsight:${ENVIRONMENT}-latest"
    
    log_success "Docker image built: $image_tag"
    echo "$image_tag" > /tmp/superinsight_image_tag
}

# Deploy using rolling update strategy
deploy_rolling() {
    log_info "Deploying using rolling update strategy..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would perform rolling deployment to $ENVIRONMENT"
        return 0
    fi
    
    # Update TCB configuration
    tcb framework:deploy \
        --envId "$TCB_ENV_ID" \
        --mode "$ENVIRONMENT" \
        --strategy rolling || {
        log_error "Rolling deployment failed"
        return 1
    }
    
    log_success "Rolling deployment completed"
}

# Deploy using blue-green strategy
deploy_blue_green() {
    log_info "Deploying using blue-green strategy..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would perform blue-green deployment to $ENVIRONMENT"
        return 0
    fi
    
    # Get current active environment (blue or green)
    local current_env
    current_env=$(tcb hosting:detail --envId "$TCB_ENV_ID" | jq -r '.activeSlot // "blue"')
    
    # Determine target environment
    local target_env
    if [[ "$current_env" == "blue" ]]; then
        target_env="green"
    else
        target_env="blue"
    fi
    
    log_info "Current active slot: $current_env"
    log_info "Deploying to slot: $target_env"
    
    # Deploy to target environment
    tcb framework:deploy \
        --envId "$TCB_ENV_ID" \
        --mode "$ENVIRONMENT" \
        --slot "$target_env" || {
        log_error "Blue-green deployment to $target_env slot failed"
        return 1
    }
    
    # Wait for deployment to be ready
    log_info "Waiting for deployment to be ready..."
    sleep 30
    
    # Perform health check on target environment
    if ! perform_health_check "$target_env"; then
        log_error "Health check failed on $target_env slot"
        return 1
    fi
    
    # Switch traffic to target environment
    log_info "Switching traffic to $target_env slot..."
    tcb hosting:switch \
        --envId "$TCB_ENV_ID" \
        --slot "$target_env" || {
        log_error "Traffic switch failed"
        return 1
    }
    
    log_success "Blue-green deployment completed, traffic switched to $target_env"
}

# Deploy using canary strategy
deploy_canary() {
    log_info "Deploying using canary strategy..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would perform canary deployment to $ENVIRONMENT"
        return 0
    fi
    
    # Deploy canary version (10% traffic)
    tcb framework:deploy \
        --envId "$TCB_ENV_ID" \
        --mode "$ENVIRONMENT" \
        --strategy canary \
        --canary-weight 10 || {
        log_error "Canary deployment failed"
        return 1
    }
    
    log_info "Canary deployed with 10% traffic"
    
    # Wait and monitor
    log_info "Monitoring canary for 5 minutes..."
    sleep 300
    
    # Check canary health
    if perform_health_check "canary"; then
        log_info "Canary is healthy, promoting to 100%"
        tcb hosting:promote --envId "$TCB_ENV_ID" || {
            log_error "Canary promotion failed"
            return 1
        }
    else
        log_error "Canary health check failed, rolling back"
        tcb hosting:rollback --envId "$TCB_ENV_ID"
        return 1
    fi
    
    log_success "Canary deployment completed and promoted"
}

# Perform deployment based on strategy
perform_deployment() {
    log_info "Starting deployment to $ENVIRONMENT environment..."
    
    case "$DEPLOYMENT_MODE" in
        "rolling")
            deploy_rolling
            ;;
        "blue-green")
            deploy_blue_green
            ;;
        "canary")
            deploy_canary
            ;;
        *)
            log_error "Unknown deployment mode: $DEPLOYMENT_MODE"
            return 1
            ;;
    esac
}

# Perform health check
perform_health_check() {
    local slot="${1:-}"
    
    if [[ "$SKIP_HEALTH_CHECK" == "true" ]]; then
        log_warning "Skipping health check as requested"
        return 0
    fi
    
    log_info "Performing health check..."
    
    # Get service URL
    local service_url
    if [[ -n "$slot" ]]; then
        service_url=$(tcb hosting:detail --envId "$TCB_ENV_ID" --slot "$slot" | jq -r '.url')
    else
        service_url=$(tcb hosting:detail --envId "$TCB_ENV_ID" | jq -r '.url')
    fi
    
    if [[ -z "$service_url" || "$service_url" == "null" ]]; then
        log_error "Could not get service URL"
        return 1
    fi
    
    log_info "Health check URL: ${service_url}/health"
    
    # Retry health check up to 10 times
    local max_attempts=10
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log_info "Health check attempt $attempt/$max_attempts"
        
        if curl -sf "${service_url}/health" -o /dev/null; then
            log_success "Health check passed"
            return 0
        fi
        
        if [[ $attempt -lt $max_attempts ]]; then
            log_warning "Health check failed, retrying in 30 seconds..."
            sleep 30
        fi
        
        ((attempt++))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Rollback on failure
rollback_deployment() {
    if [[ "$ROLLBACK_ON_FAILURE" == "false" ]]; then
        log_warning "Rollback disabled, manual intervention required"
        return 0
    fi
    
    log_warning "Rolling back deployment due to failure..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would rollback deployment"
        return 0
    fi
    
    tcb framework:rollback --envId "$TCB_ENV_ID" || {
        log_error "Rollback failed, manual intervention required"
        return 1
    }
    
    log_success "Rollback completed"
}

# Send notification
send_notification() {
    local status="$1"
    local message="$2"
    
    if [[ -z "${SLACK_WEBHOOK_URL:-}" ]]; then
        return 0
    fi
    
    local color
    case "$status" in
        "success") color="good" ;;
        "failure") color="danger" ;;
        *) color="warning" ;;
    esac
    
    local payload=$(cat << EOF
{
    "attachments": [
        {
            "color": "$color",
            "title": "SuperInsight Deployment $status",
            "fields": [
                {
                    "title": "Environment",
                    "value": "$ENVIRONMENT",
                    "short": true
                },
                {
                    "title": "Mode",
                    "value": "$DEPLOYMENT_MODE",
                    "short": true
                },
                {
                    "title": "Message",
                    "value": "$message",
                    "short": false
                }
            ],
            "ts": $(date +%s)
        }
    ]
}
EOF
    )
    
    curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK_URL" &> /dev/null || true
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f /tmp/superinsight_image_tag
}

# Main deployment function
main() {
    # Set up cleanup trap
    trap cleanup EXIT
    
    log_info "Starting SuperInsight TCB deployment..."
    log_info "Timestamp: $(date)"
    
    # Parse arguments and validate
    parse_args "$@"
    validate_environment
    validate_deployment_mode
    
    # Check prerequisites
    check_prerequisites
    load_environment_config
    
    # Pre-deployment steps
    if ! run_tests; then
        if [[ "$FORCE_DEPLOY" == "false" ]]; then
            log_error "Tests failed, aborting deployment"
            send_notification "failure" "Tests failed"
            exit 1
        else
            log_warning "Tests failed but force deploy enabled, continuing..."
        fi
    fi
    
    create_backup
    build_docker_image
    
    # Perform deployment
    if perform_deployment; then
        if perform_health_check; then
            log_success "Deployment completed successfully!"
            send_notification "success" "Deployment completed successfully"
        else
            log_error "Health check failed after deployment"
            rollback_deployment
            send_notification "failure" "Health check failed, rolled back"
            exit 1
        fi
    else
        log_error "Deployment failed"
        rollback_deployment
        send_notification "failure" "Deployment failed, rolled back"
        exit 1
    fi
    
    log_success "SuperInsight deployment to $ENVIRONMENT completed successfully!"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi