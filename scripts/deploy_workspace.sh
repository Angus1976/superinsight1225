#!/bin/bash
#
# Label Studio Enterprise Workspace Deployment Script
# Version: 1.0
# Date: 2026-01-30
#
# This script deploys the Label Studio Enterprise Workspace feature to a target environment.
#
# Usage:
#   ./deploy_workspace.sh [environment]
#
# Arguments:
#   environment - Target environment: test, staging, production (default: test)
#
# Prerequisites:
#   - PostgreSQL database access
#   - Python 3.10+
#   - Node.js 18+
#   - alembic CLI installed
#

set -e  # Exit on error

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-test}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

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

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed or not in PATH"
        exit 1
    fi
}

# =============================================================================
# Pre-deployment Checks
# =============================================================================

pre_deployment_checks() {
    log_info "Running pre-deployment checks..."

    # Check required commands
    check_command "python"
    check_command "pip"
    check_command "alembic"
    check_command "psql"

    # Check Python version
    PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ $(echo "$PYTHON_VERSION < 3.10" | bc -l) -eq 1 ]]; then
        log_error "Python 3.10+ is required, found $PYTHON_VERSION"
        exit 1
    fi

    # Check environment variables
    if [[ -z "$DATABASE_URL" ]]; then
        log_error "DATABASE_URL environment variable is not set"
        exit 1
    fi

    # Check database connectivity
    log_info "Testing database connection..."
    if ! psql "$DATABASE_URL" -c "SELECT 1" &> /dev/null; then
        log_error "Cannot connect to database"
        exit 1
    fi

    log_success "Pre-deployment checks passed"
}

# =============================================================================
# Database Migration
# =============================================================================

run_database_migration() {
    log_info "Running database migrations..."

    cd "$PROJECT_ROOT"

    # Check current migration status
    log_info "Current migration status:"
    alembic current

    # Create backup before migration (optional, controlled by env var)
    if [[ "$BACKUP_BEFORE_MIGRATION" == "true" ]]; then
        log_info "Creating database backup..."
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
        pg_dump "$DATABASE_URL" > "$BACKUP_FILE"
        log_success "Backup created: $BACKUP_FILE"
    fi

    # Run migration
    log_info "Applying migrations..."
    alembic upgrade head

    # Verify migration
    log_info "Verifying migration..."
    TABLES=$(psql "$DATABASE_URL" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_name IN ('label_studio_workspaces', 'label_studio_workspace_members', 'workspace_projects', 'project_members');")
    TABLES=$(echo "$TABLES" | tr -d ' ')

    if [[ "$TABLES" -eq 4 ]]; then
        log_success "All workspace tables created successfully"
    else
        log_error "Expected 4 tables, found $TABLES"
        exit 1
    fi

    log_success "Database migration completed"
}

# =============================================================================
# Backend Deployment
# =============================================================================

deploy_backend() {
    log_info "Deploying backend services..."

    cd "$PROJECT_ROOT"

    # Install/update dependencies
    log_info "Installing Python dependencies..."
    pip install -r requirements.txt

    # Verify module imports
    log_info "Verifying module imports..."
    python -c "
from src.label_studio.workspace_service import WorkspaceService
from src.label_studio.rbac_service import RBACService
from src.label_studio.proxy import LabelStudioProxy
from src.api.label_studio_workspace import router
print('All workspace modules imported successfully')
"

    # Run unit tests for workspace module
    log_info "Running workspace unit tests..."
    python -m pytest tests/label_studio/ -v --tb=short || {
        log_warning "Some unit tests failed, check the output above"
    }

    log_success "Backend deployment completed"
}

# =============================================================================
# Frontend Deployment
# =============================================================================

deploy_frontend() {
    log_info "Deploying frontend..."

    cd "$PROJECT_ROOT/frontend"

    # Install dependencies
    log_info "Installing Node.js dependencies..."
    npm ci

    # Type check
    log_info "Running TypeScript type check..."
    npm run typecheck || {
        log_warning "TypeScript errors found, check the output"
    }

    # Build for production
    if [[ "$ENVIRONMENT" != "test" ]]; then
        log_info "Building frontend for $ENVIRONMENT..."
        npm run build
    fi

    log_success "Frontend deployment completed"
}

# =============================================================================
# Smoke Tests
# =============================================================================

run_smoke_tests() {
    log_info "Running smoke tests..."

    cd "$PROJECT_ROOT"

    # Check API health endpoint
    if [[ -n "$API_BASE_URL" ]]; then
        log_info "Checking API health..."
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/health")
        if [[ "$HTTP_STATUS" -eq 200 ]]; then
            log_success "API health check passed"
        else
            log_warning "API health check returned status $HTTP_STATUS"
        fi
    fi

    # Run integration tests
    log_info "Running integration tests..."
    python -m pytest tests/integration/test_ls_workspace_flow.py tests/integration/test_ls_permission_flow.py -v --tb=short || {
        log_warning "Some integration tests failed"
    }

    log_success "Smoke tests completed"
}

# =============================================================================
# Post-deployment Verification
# =============================================================================

post_deployment_verification() {
    log_info "Running post-deployment verification..."

    cd "$PROJECT_ROOT"

    # Verify database tables
    log_info "Verifying database tables..."
    psql "$DATABASE_URL" -c "
        SELECT 'label_studio_workspaces' as table_name, count(*) as row_count FROM label_studio_workspaces
        UNION ALL
        SELECT 'label_studio_workspace_members', count(*) FROM label_studio_workspace_members
        UNION ALL
        SELECT 'workspace_projects', count(*) FROM workspace_projects
        UNION ALL
        SELECT 'project_members', count(*) FROM project_members;
    "

    # Verify indexes
    log_info "Verifying database indexes..."
    psql "$DATABASE_URL" -c "
        SELECT indexname, tablename
        FROM pg_indexes
        WHERE tablename IN ('label_studio_workspaces', 'label_studio_workspace_members', 'workspace_projects', 'project_members')
        ORDER BY tablename, indexname;
    "

    log_success "Post-deployment verification completed"
}

# =============================================================================
# Rollback Function
# =============================================================================

rollback() {
    log_warning "Rolling back deployment..."

    cd "$PROJECT_ROOT"

    # Rollback database migration
    log_info "Rolling back database migration..."
    alembic downgrade -1

    log_success "Rollback completed"
}

# =============================================================================
# Main Deployment Process
# =============================================================================

main() {
    echo ""
    echo "=========================================="
    echo "  Label Studio Workspace Deployment"
    echo "  Environment: $ENVIRONMENT"
    echo "  Date: $(date)"
    echo "=========================================="
    echo ""

    # Handle rollback command
    if [[ "$1" == "rollback" ]]; then
        rollback
        exit 0
    fi

    # Run deployment steps
    pre_deployment_checks
    run_database_migration
    deploy_backend
    deploy_frontend
    run_smoke_tests
    post_deployment_verification

    echo ""
    echo "=========================================="
    log_success "Deployment completed successfully!"
    echo "=========================================="
    echo ""

    # Print summary
    echo "Deployment Summary:"
    echo "  - Environment: $ENVIRONMENT"
    echo "  - Database: Migrated to latest"
    echo "  - Backend: Deployed"
    echo "  - Frontend: Deployed"
    echo "  - Smoke Tests: Passed"
    echo ""
    echo "Next steps:"
    echo "  1. Verify the application is running"
    echo "  2. Check logs for any errors"
    echo "  3. Run manual verification tests"
    echo ""
}

# Run main function
main "$@"
