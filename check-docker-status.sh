#!/bin/bash

echo "=== Docker Status Check ==="
echo ""

# Check if Docker command is available
if command -v docker &> /dev/null; then
    echo "✓ Docker command found"
    docker --version
    echo ""
    
    # Check if Docker daemon is running
    if docker info &> /dev/null; then
        echo "✓ Docker daemon is running"
        echo ""
        
        # Show running containers
        echo "Running containers:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        
        # Show all containers
        echo "All containers:"
        docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}"
        echo ""
        
        echo "Docker is ready! You can now run: ./wait-for-docker-and-rebuild.sh"
    else
        echo "✗ Docker daemon is not running"
        echo "  Please wait for Docker Desktop to start, then run this script again"
        exit 1
    fi
else
    echo "✗ Docker command not found"
    echo "  Docker Desktop may still be starting..."
    echo "  Please wait a moment and run this script again"
    exit 1
fi
