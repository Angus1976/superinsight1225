#!/bin/bash
# SuperInsight TCB Deployment Script
# Deploys the full-stack container to Tencent Cloud Base

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKERFILE="deploy/tcb/Dockerfile.fullstack"
IMAGE_NAME="superinsight-enterprise"
VERSION="${VERSION:-$(date +%Y%m%d%H%M%S)}"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env.tcb" ]; then
    source "$PROJECT_ROOT/.env.tcb"
    log_info "Loaded TCB environment from .env.tcb"
elif [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
    log_info "Loaded environment from .env"
fi

# Validate required environment variables
validate_env() {
    local missing=()
    
    [ -z "$TCB_ENV_ID" ] && missing+=("TCB_ENV_ID")
    [ -z "$TCB_SECRET_ID" ] && missing+=("TCB_SECRET_ID")
    [ -z "$TCB_SECRET_KEY" ] && missing+=("TCB_SECRET_KEY")
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required environment variables: ${missing[*]}"
        log_info "Please set these in .env.tcb or export them"
        exit 1
    fi
    
    log_info "Environment validation passed"
}

# Build Docker image
build_image() {
    log_step "Building Docker image..."
    
    cd "$PROJECT_ROOT"
    
    docker build \
        -f "$DOCKERFILE" \
        -t "$IMAGE_NAME:$VERSION" \
        -t "$IMAGE_NAME:latest" \
        --build-arg VERSION="$VERSION" \
        --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        .
    
    log_info "Image built: $IMAGE_NAME:$VERSION"
}

# Run tests before deployment
run_tests() {
    log_step "Running pre-deployment tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run unit tests
    python -m pytest tests/deployment/ -v --tb=short || {
        log_warn "Some deployment tests failed, continuing..."
    }
    
    log_info "Pre-deployment tests completed"
}

# Push image to TCB registry
push_image() {
    log_step "Pushing image to TCB registry..."
    
    local registry="ccr.ccs.tencentyun.com"
    local full_image="$registry/$TCB_ENV_ID/$IMAGE_NAME:$VERSION"
    
    # Login to TCB registry
    echo "$TCB_SECRET_KEY" | docker login --username="$TCB_SECRET_ID" --password-stdin "$registry"
    
    # Tag and push
    docker tag "$IMAGE_NAME:$VERSION" "$full_image"
    docker push "$full_image"
    
    log_info "Image pushed: $full_image"
    echo "$full_image"
}

# Deploy to TCB Cloud Run
deploy_to_tcb() {
    local image_url="$1"
    
    log_step "Deploying to TCB Cloud Run..."
    
    # Install TCB CLI if not present
    if ! command -v tcb &> /dev/null; then
        log_info "Installing TCB CLI..."
        npm install -g @cloudbase/cli
    fi
    
    # Login to TCB
    tcb login --apiKeyId "$TCB_SECRET_ID" --apiKey "$TCB_SECRET_KEY"
    
    # Deploy using cloudbaserc.json
    cd "$PROJECT_ROOT"
    tcb framework deploy --mode container
    
    log_info "Deployment initiated"
}

# Verify deployment
verify_deployment() {
    log_step "Verifying deployment..."
    
    local max_attempts=30
    local attempt=0
    local health_url="https://$IMAGE_NAME.$TCB_ENV_ID.${TCB_REGION:-ap-shanghai}.tcb.qcloud.la/health"
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "$health_url" > /dev/null 2>&1; then
            log_info "Deployment verified - service is healthy"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log_info "Waiting for service to be ready... ($attempt/$max_attempts)"
        sleep 10
    done
    
    log_error "Deployment verification failed"
    return 1
}

# Rollback deployment
rollback() {
    log_step "Rolling back deployment..."
    
    # Get previous version
    local prev_version=$(tcb service list --envId "$TCB_ENV_ID" --json | jq -r '.[0].previousVersion')
    
    if [ -n "$prev_version" ] && [ "$prev_version" != "null" ]; then
        tcb service rollback --envId "$TCB_ENV_ID" --serviceName "$IMAGE_NAME" --version "$prev_version"
        log_info "Rolled back to version: $prev_version"
    else
        log_error "No previous version found for rollback"
        return 1
    fi
}

# Main deployment flow
main() {
    echo "=========================================="
    echo "SuperInsight TCB Deployment"
    echo "Version: $VERSION"
    echo "=========================================="
    
    case "${1:-deploy}" in
        deploy)
            validate_env
            run_tests
            build_image
            local image_url=$(push_image)
            deploy_to_tcb "$image_url"
            verify_deployment
            ;;
        build)
            build_image
            ;;
        push)
            validate_env
            push_image
            ;;
        verify)
            validate_env
            verify_deployment
            ;;
        rollback)
            validate_env
            rollback
            ;;
        *)
            echo "Usage: $0 {deploy|build|push|verify|rollback}"
            exit 1
            ;;
    esac
    
    log_info "Operation completed successfully"
}

main "$@"
