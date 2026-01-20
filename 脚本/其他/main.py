"""
SuperInsight Platform Main Application Entry Point
"""
import logging
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Initialize logging first
from src.system.logging_config import setup_logging, get_logger

# Setup logging before importing other modules
setup_logging()

from src.config.settings import settings
from src.system.integration import system_manager
from src.system.service_registry import service_registry

logger = get_logger(__name__, service_name="main")


async def initialize_system():
    """Initialize the complete system."""
    logger.info(f"Initializing {settings.app.app_name} v{settings.app.app_version}")
    
    try:
        # Initialize service registry
        from src.system.service_registry import initialize_service_registry
        await initialize_service_registry()
        
        logger.info("Service registry initialized")
        logger.info("System initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        return False


def main():
    """Main application entry point"""
    import asyncio
    
    async def async_main():
        success = await initialize_system()
        if not success:
            return False
        
        logger.info("SuperInsight Platform initialized successfully")
        logger.info("Use 'python -m uvicorn src.app:app --reload' to start the web server")
        return True
    
    # Run async initialization
    success = asyncio.run(async_main())
    return success


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)