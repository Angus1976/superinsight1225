#!/bin/bash

# SuperInsight Full-Stack Setup Script
# This script automates the complete setup of the SuperInsight platform

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-superinsight_db}
DB_USER=${DB_USER:-superinsight}
DB_PASSWORD=${DB_PASSWORD:-password}

# Functions
print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║ $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"
}

print_step() {
    echo -e "${YELLOW}→ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed"
        return 1
    fi
    print_success "$1 is installed"
    return 0
}

# Main setup
main() {
    print_header "SuperInsight Full-Stack Setup"
    
    # Check prerequisites
    print_header "1. Checking Prerequisites"
    
    check_command "python3" || exit 1
    check_command "node" || exit 1
    check_command "npm" || exit 1
    check_command "psql" || exit 1
    
    # Check Python version
    print_step "Checking Python version..."
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    print_success "Python $PYTHON_VERSION"
    
    # Check Node version
    print_step "Checking Node version..."
    NODE_VERSION=$(node --version)
    print_success "Node $NODE_VERSION"
    
    # Setup backend
    print_header "2. Setting Up Backend"
    
    cd "$PROJECT_ROOT"
    
    # Create virtual environment
    print_step "Creating Python virtual environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    print_step "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
    
    # Install Python dependencies
    print_step "Installing Python dependencies..."
    pip install -q -r requirements.txt
    print_success "Python dependencies installed"
    
    # Setup database
    print_header "3. Setting Up Database"
    
    print_step "Checking PostgreSQL connection..."
    if pg_isready -h $DB_HOST -p $DB_PORT &> /dev/null; then
        print_success "PostgreSQL is running"
    else
        print_error "PostgreSQL is not running"
        echo "Please start PostgreSQL and try again"
        exit 1
    fi
    
    # Create database user and database
    print_step "Creating database user and database..."
    PGPASSWORD=postgres psql -h $DB_HOST -U postgres -tc "SELECT 1 FROM pg_user WHERE usename = '$DB_USER'" | grep -q 1 || \
    PGPASSWORD=postgres psql -h $DB_HOST -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    
    PGPASSWORD=postgres psql -h $DB_HOST -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    PGPASSWORD=postgres psql -h $DB_HOST -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    
    print_success "Database user and database created"
    
    # Run migrations
    print_step "Running database migrations..."
    alembic upgrade head
    print_success "Database migrations completed"
    
    # Initialize test data
    print_step "Initializing test data..."
    python init_test_accounts.py
    print_success "Test data initialized"
    
    # Setup frontend
    print_header "4. Setting Up Frontend"
    
    cd "$PROJECT_ROOT/frontend"
    
    # Install npm dependencies
    print_step "Installing npm dependencies..."
    npm install -q
    print_success "npm dependencies installed"
    
    # Create environment file
    print_step "Creating frontend environment file..."
    cat > .env.development << EOF
VITE_API_BASE_URL=http://localhost:$BACKEND_PORT
VITE_API_TIMEOUT=30000
VITE_ENABLE_MOCK=false
VITE_LOG_LEVEL=debug
EOF
    print_success "Frontend environment file created"
    
    # Create backend environment file
    print_header "5. Creating Backend Environment File"
    
    cd "$PROJECT_ROOT"
    
    if [ ! -f ".env" ]; then
        print_step "Creating backend environment file..."
        cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME
SQLALCHEMY_DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME

# JWT Configuration
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server Configuration
HOST=0.0.0.0
PORT=$BACKEND_PORT
DEBUG=True
ENVIRONMENT=development

# CORS Configuration
CORS_ORIGINS=["http://localhost:$FRONTEND_PORT","http://localhost:3000"]

# Redis Configuration (Optional)
REDIS_URL=redis://localhost:6379/0

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
EOF
        print_success "Backend environment file created"
    else
        print_success "Backend environment file already exists"
    fi
    
    # Summary
    print_header "Setup Complete!"
    
    echo -e "${GREEN}All components have been successfully set up!${NC}\n"
    
    echo "Next steps:"
    echo ""
    echo "1. Start the backend service:"
    echo -e "   ${YELLOW}python -m uvicorn src.app:app --host 0.0.0.0 --port $BACKEND_PORT --reload${NC}"
    echo ""
    echo "2. In a new terminal, start the frontend:"
    echo -e "   ${YELLOW}cd frontend && npm run dev${NC}"
    echo ""
    echo "3. Open your browser and visit:"
    echo -e "   ${YELLOW}http://localhost:$FRONTEND_PORT${NC}"
    echo ""
    echo "4. Login with test accounts:"
    echo -e "   ${YELLOW}Admin: admin@superinsight.com / Admin@123456${NC}"
    echo -e "   ${YELLOW}Analyst: analyst@superinsight.com / Analyst@123456${NC}"
    echo ""
    echo "5. Run integration tests:"
    echo -e "   ${YELLOW}python fullstack_integration_test.py${NC}"
    echo ""
    echo "For more information, see:"
    echo -e "   ${YELLOW}FULLSTACK_INTEGRATION_GUIDE.md${NC}"
    echo -e "   ${YELLOW}FRONTEND_TESTING_GUIDE.md${NC}"
    echo ""
}

# Run main function
main
