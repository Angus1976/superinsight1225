#!/bin/bash

# SuperInsight Platform - Startup Script

set -e

echo "================================================================================"
echo "SuperInsight Platform - Starting Services"
echo "================================================================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "✅ .env file created. Please update with your configuration."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo ""
echo "Starting services with Docker Compose..."
echo ""

# Start all services
docker-compose up -d

echo ""
echo "Waiting for services to be healthy..."
echo ""

# Wait for PostgreSQL
echo -n "Waiting for PostgreSQL..."
until docker-compose exec -T postgres pg_isready -U superinsight > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo " ✅"

# Wait for Redis
echo -n "Waiting for Redis..."
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo " ✅"

# Run database migrations
echo ""
echo "Running database migrations..."
docker-compose exec -T app alembic upgrade head
echo "✅ Migrations complete"

echo ""
echo "================================================================================"
echo "✅ SuperInsight Platform is running!"
echo "================================================================================"
echo ""
echo "Services:"
echo "  - Application:     http://localhost:8000"
echo "  - API Docs:        http://localhost:8000/docs"
echo "  - Health Check:    http://localhost:8000/health"
echo "  - Label Studio:    http://localhost:8080"
echo "  - Argilla:         http://localhost:6900"
echo "  - Prometheus:      http://localhost:9090"
echo "  - Grafana:         http://localhost:3001"
echo ""
echo "Logs:"
echo "  docker-compose logs -f app"
echo ""
echo "Stop:"
echo "  docker-compose down"
echo ""
