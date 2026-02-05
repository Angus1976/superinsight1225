#!/usr/bin/env python3
"""
SuperInsight Platform - Main Entry Point

This is the main entry point for the SuperInsight AI Data Governance and Annotation Platform.
It initializes and runs the FastAPI application with uvicorn.

Usage:
    python main.py                    # Run with default settings
    python main.py --host 0.0.0.0     # Run on all interfaces
    python main.py --port 8080        # Run on custom port
    python main.py --reload           # Run with auto-reload (development)
"""

import argparse
import logging
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

from src.config.settings import settings


def setup_logging():
    """Configure logging for the application."""
    log_level = logging.DEBUG if settings.app.debug else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SuperInsight AI Data Governance and Annotation Platform"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.app.debug,
        help="Enable auto-reload (default: based on debug setting)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("WORKERS", "1")),
        help="Number of worker processes (default: 1)"
    )
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Parse arguments
    args = parse_args()
    
    logger.info(f"Starting SuperInsight Platform v{settings.app.app_version}")
    logger.info(f"Environment: {'Development' if settings.app.debug else 'Production'}")
    logger.info(f"Host: {args.host}, Port: {args.port}")
    
    # Run the application
    uvicorn.run(
        "src.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level="debug" if settings.app.debug else "info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
