#!/bin/bash
# SuperInsight TCB Environment Switcher and Rollback Manager
# Provides environment switching and rollback capabilities

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
ENVIRONMENT=""
ACTION=""
TARGET_VERSION=""
FORCE=false
DRY_RUN=false

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] ACTION

SuperInsight TCB Environment Switcher and Rollback Manager

ACTIONS:
    switch          Switch between blue/green environments
    rollback        Rollback to previous version
    list-versions   List available versions for rollback
    status          Show current deployment status
    promote         Promote canary deployment to full traffic

OPTIONS:
    -e, --environment ENV    Target environment (development|staging|production)
    -v, --version VERSION    Target version for rollback
    -f, --force             Force action without confirmation
    -d, --dry-run           Show what would be done without executing
    --help                  Show this help message

EXAMPLES:
    # Switch blue/green environments
    $0 -e production switch

    # Rollback to specific version
    $0 -e production rollback -v v1.2.3

    # List available versions
    $0 -e production list-versions

    # Check deployment status
    $0 -e production status

    # Promote canary deployment
    $0 -e production promote

EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -v|--version)
                TARGET_VERSION="$2"
                shift 2
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            switch|rollback|list-versions|status|promote)
                ACTION="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

validate_inputs() {
    if [[ -z "$ACTION" ]]; then
        log_error "Action not specified"
        show_usage
        exit 1
    fi
    
    if [[ -z "$ENVIRONMENT" ]]; then
        log_error "Environment not specified"
        show_usage
        exit 1
    fi
    
    local valid_envs=("development" "staging" "production")
    if [[ ! " ${valid_envs[@]} " =~ " ${ENVIRONMENT} " ]]; then
        log_error "Invalid environment: $ENVIRONMENT"
        exit 1
    fi
}

load_environment_config() {
    local env_file="${SCRIPT_DIR}/../env/${ENVIRONMENT}.env"
    if [[ ! -f "$env_file" ]]; then
        log_error "Environment configuration not found: $env_file"
        exit 1
    fi
    
    set -a
    source "$env_file"
    set +a
    
    if [[ -z "${TCB_ENV_ID:-}" ]]; then
        log_error "TCB_ENV_ID not set in environment configuration"
        exit 1
    fi
}

check_tcb_auth() {
    if ! tcb auth list &> /dev/null; then
        log_error "TCB CLI not authenticated. Please run 'tcb login' first."
        exit 1
    fi
}

get_deployment_status() {
    log_info "Getting deployment status for environment: $ENVIRONMENT"
    
    local status_json
    status_json=$(tcb hosting:detail --envId "$TCB_ENV_ID" --output json 2>/dev/null || echo "{}")
    
    if [[ "$status_json" == "{}" ]]; then
        log_error "Failed to get deployment status"
        return 1
    fi
    
    echo "$status_json"
}

show_status() {
    log_info "Deployment Status for $ENVIRONMENT"
    echo "=================================="
    
    local status_json
    status_json=$(get_deployment_status)
    
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    # Parse and display status
    local active_slot current_version blue_version green_version
    active_slot=$(echo "$status_json" | jq -r '.activeSlot // "unknown"')
    current_version=$(echo "$status_json" | jq -r '.version // "unknown"')
    blue_version=$(echo "$status_json" | jq -r '.slots.blue.version // "none"')
    green_version=$(echo "$status_json" | jq -r '.slots.green.version // "none"')
    
    echo "Environment ID: $TCB_ENV_ID"
    echo "Active Slot: $active_slot"
    echo "Current Version: $current_version"
    echo ""
    echo "Slot Status:"
    echo "  Blue:  $blue_version"
    echo "  Green: $green_version"
    echo ""
    
    # Show traffic distribution if canary is active
    local canary_weight
    canary_weight=$(echo "$status_json" | jq -r '.canaryWeight // 0')
    if [[ "$canary_weight" -gt 0 ]]; then
        echo "Canary Deployment Active:"
        echo "  Canary Traffic: ${canary_weight}%"
        echo "  Stable Traffic: $((100 - canary_weight))%"
    fi
}

list_versions() {
    log_info "Available versions for rollback:"
    echo "================================"
    
    # Get deployment history
    local history_json
    history_json=$(tcb hosting:history --envId "$TCB_ENV_ID" --output json 2>/dev/null || echo "[]")
    
    if [[ "$history_json" == "[]" ]]; then
        log_warning "No deployment history found"
        return 0
    fi
    
    # Display versions with timestamps
    echo "$history_json" | jq -r '.[] | "\(.version) - \(.deployedAt) - \(.status)"' | head -10
    
    echo ""
    log_info "Use -v VERSION to rollback to a specific version"
}

confirm_action() {
    local message="$1"
    
    if [[ "$FORCE" == "true" ]]; then
        return 0
    fi
    
    echo -n "$message (y/N): "
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            log_info "Action cancelled"
            exit 0
            ;;
    esac
}

switch_environment() {
    log_info "Switching blue/green environments..."
    
    local status_json
    status_json=$(get_deployment_status)
    
    local current_slot target_slot
    current_slot=$(echo "$status_json" | jq -r '.activeSlot // "blue"')
    
    if [[ "$current_slot" == "blue" ]]; then
        target_slot="green"
    else
        target_slot="blue"
    fi
    
    log_info "Current active slot: $current_slot"
    log_info "Target slot: $target_slot"
    
    # Check if target slot has a deployment
    local target_version
    target_version=$(echo "$status_json" | jq -r ".slots.${target_slot}.version // \"none\"")
    
    if [[ "$target_version" == "none" ]]; then
        log_error "Target slot ($target_slot) has no deployment"
        log_error "Deploy to the target slot first before switching"
        exit 1
    fi
    
    confirm_action "Switch traffic from $current_slot to $target_slot (version: $target_version)?"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would switch traffic to $target_slot"
        return 0
    fi
    
    # Perform the switch
    tcb hosting:switch --envId "$TCB_ENV_ID" --slot "$target_slot" || {
        log_error "Failed to switch environments"
        return 1
    }
    
    log_success "Successfully switched to $target_slot slot"
    
    # Verify the switch
    sleep 10
    local new_status
    new_status=$(get_deployment_status)
    local new_active_slot
    new_active_slot=$(echo "$new_status" | jq -r '.activeSlot')
    
    if [[ "$new_active_slot" == "$target_slot" ]]; then
        log_success "Switch verified: $target_slot is now active"
    else
        log_warning "Switch verification failed: expected $target_slot, got $new_active_slot"
    fi
}

rollback_deployment() {
    log_info "Rolling back deployment..."
    
    if [[ -n "$TARGET_VERSION" ]]; then
        log_info "Rolling back to version: $TARGET_VERSION"
        confirm_action "Rollback to version $TARGET_VERSION?"
    else
        log_info "Rolling back to previous version"
        confirm_action "Rollback to previous version?"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would rollback deployment"
        if [[ -n "$TARGET_VERSION" ]]; then
            log_info "[DRY RUN] Target version: $TARGET_VERSION"
        fi
        return 0
    fi
    
    # Perform rollback
    local rollback_cmd="tcb hosting:rollback --envId $TCB_ENV_ID"
    if [[ -n "$TARGET_VERSION" ]]; then
        rollback_cmd="$rollback_cmd --version $TARGET_VERSION"
    fi
    
    eval "$rollback_cmd" || {
        log_error "Rollback failed"
        return 1
    }
    
    log_success "Rollback completed successfully"
    
    # Show new status
    echo ""
    show_status
}

promote_canary() {
    log_info "Promoting canary deployment..."
    
    local status_json
    status_json=$(get_deployment_status)
    
    local canary_weight
    canary_weight=$(echo "$status_json" | jq -r '.canaryWeight // 0')
    
    if [[ "$canary_weight" -eq 0 ]]; then
        log_error "No active canary deployment found"
        exit 1
    fi
    
    log_info "Current canary traffic: ${canary_weight}%"
    confirm_action "Promote canary to 100% traffic?"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would promote canary to 100%"
        return 0
    fi
    
    # Promote canary
    tcb hosting:promote --envId "$TCB_ENV_ID" || {
        log_error "Canary promotion failed"
        return 1
    }
    
    log_success "Canary promoted to 100% traffic"
    
    # Show new status
    echo ""
    show_status
}

main() {
    parse_args "$@"
    validate_inputs
    load_environment_config
    check_tcb_auth
    
    case "$ACTION" in
        "status")
            show_status
            ;;
        "list-versions")
            list_versions
            ;;
        "switch")
            switch_environment
            ;;
        "rollback")
            rollback_deployment
            ;;
        "promote")
            promote_canary
            ;;
        *)
            log_error "Unknown action: $ACTION"
            show_usage
            exit 1
            ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi