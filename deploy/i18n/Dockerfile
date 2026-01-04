# Multi-stage build for SuperInsight i18n-enabled application
FROM python:3.9-slim as builder

# Set build arguments
ARG BUILD_ENV=production
ARG I18N_VERSION=1.0.0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY main.py .

# Create non-root user
RUN groupadd -r superinsight && useradd -r -g superinsight superinsight

# Production stage
FROM python:3.9-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    I18N_DEFAULT_LANGUAGE=zh \
    I18N_SUPPORTED_LANGUAGES=zh,en \
    I18N_CACHE_ENABLED=true \
    I18N_LOG_LEVEL=INFO

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application user and directories
RUN groupadd -r superinsight && useradd -r -g superinsight superinsight
RUN mkdir -p /app/logs /app/cache /app/config && \
    chown -R superinsight:superinsight /app

# Copy from builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder --chown=superinsight:superinsight /app /app

# Copy deployment-specific configuration
COPY deploy/i18n/config/ /app/config/
COPY deploy/i18n/scripts/ /app/scripts/

# Set working directory
WORKDIR /app

# Create health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8000/health/i18n || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh && \
    chown superinsight:superinsight /app/healthcheck.sh

# Switch to non-root user
USER superinsight

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Default command
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Development stage
FROM production as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-asyncio \
    hypothesis \
    black \
    flake8 \
    mypy

# Install debugging tools
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    strace \
    && rm -rf /var/lib/apt/lists/*

# Set development environment variables
ENV I18N_DEBUG_MODE=true \
    I18N_LOG_LEVEL=DEBUG \
    I18N_VALIDATION_ENABLED=true

# Switch back to application user
USER superinsight

# Development command with hot reload
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Testing stage
FROM development as testing

# Switch to root for test setup
USER root

# Copy test files
COPY tests/ /app/tests/
COPY pytest.ini /app/
COPY .coveragerc /app/

# Set test environment variables
ENV I18N_TESTING=true \
    I18N_CACHE_ENABLED=false \
    I18N_LOG_LEVEL=WARNING

# Switch back to application user
USER superinsight

# Test command
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=src/i18n", "--cov-report=html", "--cov-report=term"]