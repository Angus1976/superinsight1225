#!/bin/bash

# Login Testing Startup Script
# This script starts all services needed for login testing

set -e

echo "================================"
echo "SuperInsight Login Testing Setup"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
echo -e "${BLUE}[1/5]${NC} Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${YELLOW}Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Start Docker services
echo -e "${BLUE}[2/5]${NC} Starting Docker services..."
docker-compose -f docker-compose.local.yml up -d
echo -e "${GREEN}✓ Docker services started${NC}"
echo ""

# Wait for services to be healthy
echo -e "${BLUE}[3/5]${NC} Waiting for services to be healthy..."
sleep 5
docker-compose -f docker-compose.local.yml ps
echo -e "${GREEN}✓ Services are running${NC}"
echo ""

# Create test users
echo -e "${BLUE}[4/5]${NC} Creating test users..."
python create_test_users_for_login.py
echo -e "${GREEN}✓ Test users created${NC}"
echo ""

# Start backend
echo -e "${BLUE}[5/5]${NC} Starting backend API server..."
echo -e "${YELLOW}Backend will start in a new terminal window${NC}"
echo ""

# Check OS and open terminal accordingly
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && python main.py"'
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    gnome-terminal -- bash -c "cd $(pwd) && python main.py; exec bash"
else
    # Windows or other
    echo -e "${YELLOW}Please manually start the backend with: python main.py${NC}"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Next steps:"
echo "1. Wait for backend to start (check terminal window)"
echo "2. Start frontend: cd frontend && npm run dev"
echo "3. Open browser: http://localhost:5173/login"
echo ""
echo "Test Credentials:"
echo "  Admin:     admin_user / Admin@123456"
echo "  Business:  business_expert / Business@123456"
echo "  Technical: technical_expert / Technical@123456"
echo "  Contractor: contractor / Contractor@123456"
echo "  Viewer:    viewer / Viewer@123456"
echo ""
echo "Documentation: LOGIN_TESTING_GUIDE.md"
echo "Test Suite: pytest test_login_comprehensive.py -v"
echo ""
