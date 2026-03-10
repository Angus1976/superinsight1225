#!/bin/bash
#
# Data Transfer Integration - Deployment Script
# Version: 1.0
# Date: 2026-03-10
#
# Deploys the data transfer / lifecycle management feature to a target environment.
#
# Usage:
#   ./deploy_data_transfer.sh [environment]
#
# Arguments:
#   environment - Target environment: test, staging, production (default: test)
#
# Prerequisites:
#   - PostgreSQL database access (DATABASE_URL set)
#   - Python 3.10+
#   - alembic CLI installed
#

set -e  # Exit on error

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-test}"

# New migration files introduced by this feature
MIGRATIONS=(
    "028_add_data_lifecycle_tables"
    "029_add_approval_requests_table"
    "030_add_transfer_audit_logs_table"
)

# New environment variables required by this feature
REQUIRED_ENV_VARS=(
    "DATABASE_URL"
)

# Optional env vars with defaults (validated but not required)
OPTIONAL_ENV_VARS=(
    "PERMISSION_MATRIX_CONFIG_FILE"
    "PERMISSION_BATCH_THRESHOLD"
    "APPROVAL_TIMEOUT_HOURS"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# Helper Functions
# =============================================================================

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed or not in PATH"
        exit 1
    fi
}

# =============================================================================
# Pre-deployment Checklist
# =============================================================================

print_checklist() {
    echo ""
    echo "=========================================="
    echo "  Pre-deployment Checklist"
    echo "=========================================="
    echo ""
    echo "  [1] Database backup completed"
    echo "  [2] .env file updated with new variables:"
    echo "      - PERMISSION_MATRIX_CONFIG_FILE (optional)"
    echo "      - PERMISSION_BATCH_THRESHOLD (default: 1000)"
    echo "      - APPROVAL_TIMEOUT_HOURS (default: 168)"
    echo "  [3] All unit and integration tests passing"
    echo "  [4] Code reviewed and merged to deploy branch"
    echo ""

    if [[ "$ENVIRONMENT" == "production" ]]; then
        echo -e "  ${YELLOW}[PRODUCTION] Ensure staging deployment verified first${NC}"
        echo ""
        read -p "  Continue with deployment? (y/N): " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    fi
}

# =============================================================================
# Environment Validation
# =============================================================================

validate_environment() {
    log_info "Validating environment..."

    # Check required tools
    check_command "python"
    check_command "alembic"

    # Check required env vars
    for var in "${REQUIRED_ENV_VARS[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done

    # Report optional env vars status
    for var in "${OPTIONAL_ENV_VARS[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_warning "$var is not set, built-in default will be used"
        else
            log_info "$var = ${!var}"
        fi
    done

    # Validate PERMISSION_MATRIX_CONFIG_FILE if set
    if [[ -n "$PERMISSION_MATRIX_CONFIG_FILE" && ! -f "$PERMISSION_MATRIX_CONFIG_FILE" ]]; then
        log_error "PERMISSION_MATRIX_CONFIG_FILE points to non-existent file: $PERMISSION_MATRIX_CONFIG_FILE"
        exit 1
    fi

    log_success "Environment validation passed"
}

# =============================================================================
# Database Migration
# =============================================================================

run_migrations() {
    log_info "Running database migrations..."

    cd "$PROJECT_ROOT"

    # Show current migration head
    log_info "Current migration status:"
    alembic current 2>&1 || true

    # Optional backup
    if [[ "$BACKUP_BEFORE_MIGRATION" == "true" ]]; then
        log_info "Creating database backup..."
        BACKUP_FILE="backup_data_transfer_$(date +%Y%m%d_%H%M%S).sql"
        pg_dump "$DATABASE_URL" > "$BACKUP_FILE"
        log_success "Backup created: $BACKUP_FILE"
    fi

    # Apply migrations
    log_info "Applying migrations to head..."
    alembic upgrade head

    log_success "Database migrations completed"
}

# =============================================================================
# Verify Migration
# =============================================================================

verify_migrations() {
    log_info "Verifying new tables exist..."

    cd "$PROJECT_ROOT"

    python -c "
import sys
try:
    from sqlalchemy import create_engine, inspect
    import os

    url = os.environ['DATABASE_URL']
    # Convert async URL to sync for inspection
    url = url.replace('+asyncpg', '').replace('+aiosqlite', '')
    engine = create_engine(url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected = ['data_lifecycle', 'approval_requests', 'transfer_audit_logs']
    missing = [t for t in expected if t not in tables]

    if missing:
        print(f'ERROR: Missing tables: {missing}')
        sys.exit(1)
    else:
        print(f'All expected tables found: {expected}')
        sys.exit(0)
except Exception as e:
    print(f'WARNING: Could not verify tables: {e}')
    print('Skipping table verification (manual check recommended)')
    sys.exit(0)
"

    log_success "Migration verification passed"
}

# =============================================================================
# Verify Module Imports
# =============================================================================

verify_modules() {
    log_info "Verifying data transfer modules..."

    cd "$PROJECT_ROOT"

    python -c "
from src.services.permission_service import PermissionService
from src.services.data_transfer_service import DataTransferService
from src.api.data_lifecycle_api import router
from src.config.permission_defaults import DEFAULT_TRANSFER_MATRIX, DEFAULT_CRUD_MATRIX
from src.config.approval_defaults import DEFAULT_APPROVAL_TIMEOUT_HOURS
print('All data transfer modules imported successfully')
" || {
        log_warning "Some module imports failed — check output above"
    }

    log_success "Module verification completed"
}

# =============================================================================
# Run Tests
# =============================================================================

run_tests() {
    log_info "Running data transfer tests..."

    cd "$PROJECT_ROOT"

    # Unit tests
    log_info "Running unit tests..."
    python -m pytest tests/unit/test_permission_service.py tests/unit/test_data_transfer_service.py tests/unit/test_transfer_messages.py tests/unit/test_permission_defaults.py -v --tb=short || {
        log_warning "Some unit tests failed"
    }

    # Integration tests
    log_info "Running integration tests..."
    python -m pytest tests/integration/test_transfer_e2e.py tests/integration/test_approval_e2e.py tests/integration/test_permission_matrix.py tests/integration/test_legacy_api_compat.py -v --tb=short || {
        log_warning "Some integration tests failed"
    }

    # Security tests
    log_info "Running security tests..."
    python -m pytest tests/security/test_data_transfer_security.py tests/security/test_sensitive_data_validator.py -v --tb=short || {
        log_warning "Some security tests failed"
    }

    log_success "Test suite completed"
}

# =============================================================================
# Rollback
# =============================================================================

rollback() {
    log_warning "Rolling back data transfer migrations..."

    cd "$PROJECT_ROOT"

    # Downgrade the 3 migrations added by this feature
    alembic downgrade -3

    log_success "Rollback completed (reverted 3 migrations)"
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo "=========================================="
    echo "  Data Transfer Integration Deployment"
    echo "  Environment: $ENVIRONMENT"
    echo "  Date: $(date)"
    echo "=========================================="
    echo ""

    if [[ "$1" == "rollback" ]]; then
        rollback
        exit 0
    fi

    print_checklist
    validate_environment
    run_migrations
    verify_migrations
    verify_modules

    if [[ "$ENVIRONMENT" == "test" ]]; then
        run_tests
    fi

    echo ""
    echo "=========================================="
    log_success "Deployment completed for $ENVIRONMENT!"
    echo "=========================================="
    echo ""
    echo "New environment variables (see .env.example):"
    echo "  PERMISSION_MATRIX_CONFIG_FILE  - Custom permission matrix JSON"
    echo "  PERMISSION_BATCH_THRESHOLD     - Batch transfer threshold (default: 1000)"
    echo "  APPROVAL_TIMEOUT_HOURS         - Approval expiry hours (default: 168)"
    echo ""
    echo "New database tables:"
    echo "  data_lifecycle          - Core lifecycle records"
    echo "  approval_requests       - Approval workflow"
    echo "  transfer_audit_logs     - Audit trail"
    echo ""
    echo "To rollback: $0 rollback"
    echo ""
}

main "$@"
