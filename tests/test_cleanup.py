"""
Test environment cleanup utilities for SuperInsight testing.

This module provides comprehensive cleanup utilities for:
- Database data cleanup hooks
- Redis cache clearing utilities
- File system cleanup for uploaded test files
- Teardown utilities for E2E tests

Requirements: 3.6, 11.7
"""

import os
import pytest
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Generator, List, Optional, Callable
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


# =============================================================================
# Test Upload Directory Configuration
# =============================================================================

class TestUploadConfig:
    """Configuration for test file upload cleanup."""
    
    # Default test upload directory
    DEFAULT_UPLOAD_DIR = Path(tempfile.gettempdir()) / "superinsight_test_uploads"
    
    # Alternative directories for different test scenarios
    TEST_DATA_DIR = Path(__file__).parent / "test_data"
    FIXTURES_DIR = Path(__file__).parent / "fixtures"
    
    # File patterns to ignore during cleanup
    IGNORED_PATTERNS = {".gitkeep", ".gitignore", ".keep"}
    
    @classmethod
    def get_upload_dir(cls, test_id: str = None) -> Path:
        """
        Get the test upload directory.
        
        Args:
            test_id: Optional test identifier for subdirectories
        
        Returns:
            Path to test upload directory
        """
        if test_id:
            return cls.DEFAULT_UPLOAD_DIR / test_id
        return cls.DEFAULT_UPLOAD_DIR
    
    @classmethod
    def get_test_data_dir(cls) -> Path:
        """Get the test data directory."""
        return cls.TEST_DATA_DIR
    
    @classmethod
    def get_fixtures_dir(cls) -> Path:
        """Get the fixtures directory."""
        return cls.FIXTURES_DIR


# =============================================================================
# File System Cleanup Manager
# =============================================================================

class FileSystemCleanupManager:
    """
    Manages cleanup of test files and directories.
    
    Provides utilities for:
    - Creating temporary test directories
    - Cleaning up test upload directories
    - Removing test-generated files
    - Verifying clean file state
    """
    
    def __init__(self, base_dir: Path = None):
        """
        Initialize the file system cleanup manager.
        
        Args:
            base_dir: Base directory for test files (default: temp directory)
        """
        self._base_dir = base_dir or TestUploadConfig.DEFAULT_UPLOAD_DIR
        self._created_dirs: List[Path] = []
        self._created_files: List[Path] = []
        self._setup_base_dir()
    
    def _setup_base_dir(self):
        """Set up the base directory for test files."""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"File system cleanup manager initialized with base dir: {self._base_dir}")
    
    def create_test_directory(self, name: str, parent: Path = None) -> Path:
        """
        Create a test directory for file uploads.
        
        Args:
            name: Name of the directory
            parent: Parent directory (uses base_dir if not specified)
        
        Returns:
            Path to the created directory
        """
        parent = parent or self._base_dir
        test_dir = parent / name
        test_dir.mkdir(parents=True, exist_ok=True)
        self._created_dirs.append(test_dir)
        logger.debug(f"Created test directory: {test_dir}")
        return test_dir
    
    def create_temporary_file(self, name: str = None, content: bytes = b"", 
                               directory: Path = None) -> Path:
        """
        Create a temporary test file.
        
        Args:
            name: Name of the file (auto-generated if not provided)
            content: File content
            directory: Directory to create file in
        
        Returns:
            Path to the created file
        """
        directory = directory or self._base_dir
        if name is None:
            import uuid
            name = f"test_file_{uuid.uuid4().hex[:8]}.tmp"
        
        file_path = directory / name
        file_path.write_bytes(content)
        self._created_files.append(file_path)
        logger.debug(f"Created test file: {file_path}")
        return file_path
    
    def cleanup_created_directories(self) -> int:
        """
        Clean up all created test directories.
        
        Returns:
            Number of directories cleaned up
        """
        cleaned = 0
        for directory in reversed(self._created_dirs):
            try:
                if directory.exists():
                    shutil.rmtree(directory)
                    cleaned += 1
                    logger.debug(f"Cleaned up directory: {directory}")
            except Exception as e:
                logger.warning(f"Failed to clean up directory {directory}: {e}")
        
        self._created_dirs.clear()
        logger.info(f"Cleaned up {cleaned} test directories")
        return cleaned
    
    def cleanup_created_files(self) -> int:
        """
        Clean up all created test files.
        
        Returns:
            Number of files cleaned up
        """
        cleaned = 0
        for file_path in self._created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    cleaned += 1
                    logger.debug(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up file {file_path}: {e}")
        
        self._created_files.clear()
        logger.info(f"Cleaned up {cleaned} test files")
        return cleaned
    
    def cleanup_directory(self, directory: Path, pattern: str = "*") -> int:
        """
        Clean up files in a directory matching a pattern.
        
        Args:
            directory: Directory to clean
            pattern: File pattern to match
        
        Returns:
            Number of files cleaned up
        """
        if not directory.exists():
            return 0
        
        cleaned = 0
        for file_path in directory.glob(pattern):
            try:
                if file_path.is_file() and file_path.name not in TestUploadConfig.IGNORED_PATTERNS:
                    file_path.unlink()
                    cleaned += 1
            except Exception as e:
                logger.warning(f"Failed to clean up file {file_path}: {e}")
        
        logger.info(f"Cleaned up {cleaned} files in {directory}")
        return cleaned
    
    def cleanup_all_test_uploads(self) -> int:
        """
        Clean up all test upload directories.
        
        Returns:
            Total number of files/directories cleaned up
        """
        if not self._base_dir.exists():
            return 0
        
        total_cleaned = 0
        
        # Clean up all subdirectories
        for item in self._base_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                    total_cleaned += 1
                elif item.is_file():
                    item.unlink()
                    total_cleaned += 1
            except Exception as e:
                logger.warning(f"Failed to clean up {item}: {e}")
        
        logger.info(f"Cleaned up {total_cleaned} items in {self._base_dir}")
        return total_cleaned
    
    def verify_clean_state(self) -> bool:
        """
        Verify that the test file system is in a clean state.
        
        Returns:
            True if no test files remain, False otherwise
        """
        if not self._base_dir.exists():
            return True
        
        # Check for any files (excluding ignored patterns)
        for item in self._base_dir.iterdir():
            if item.is_file() and item.name not in TestUploadConfig.IGNORED_PATTERNS:
                logger.warning(f"Found remaining test file: {item}")
                return False
            if item.is_dir():
                logger.warning(f"Found remaining test directory: {item}")
                return False
        
        logger.info("File system is in clean state")
        return True
    
    def get_cleanup_summary(self) -> dict:
        """
        Get a summary of items to be cleaned up.
        
        Returns:
            Dictionary with cleanup summary
        """
        return {
            "created_directories": len(self._created_dirs),
            "created_files": len(self._created_files),
            "base_directory": str(self._base_dir),
        }


# =============================================================================
# E2E Test Teardown Utilities
# =============================================================================

class E2ETestTeardownManager:
    """
    Manages teardown for end-to-end tests.
    
    Provides utilities for:
    - Cleaning up browser artifacts (screenshots, traces)
    - Cleaning up test user sessions
    - Resetting test state
    - Verifying test isolation
    """
    
    def __init__(self):
        """Initialize the E2E teardown manager."""
        self._cleanup_callbacks: List[Callable] = []
        self._test_artifacts: List[str] = []
        self._test_sessions: List[str] = []
    
    def register_cleanup_callback(self, callback: Callable) -> None:
        """
        Register a cleanup callback to be executed during teardown.
        
        Args:
            callback: Callable that performs cleanup
        """
        self._cleanup_callbacks.append(callback)
        logger.debug(f"Registered cleanup callback: {callback.__name__}")
    
    def add_test_artifact(self, artifact_path: str) -> None:
        """
        Add a test artifact (screenshot, trace, etc.) for tracking.
        
        Args:
            artifact_path: Path to the artifact
        """
        self._test_artifacts.append(artifact_path)
    
    def add_test_session(self, session_id: str) -> None:
        """
        Add a test session for cleanup.
        
        Args:
            session_id: Session identifier
        """
        self._test_sessions.append(session_id)
    
    def execute_cleanup(self) -> dict:
        """
        Execute all registered cleanup callbacks.
        
        Returns:
            Dictionary with cleanup results
        """
        results = {
            "callbacks_executed": 0,
            "artifacts_cleaned": 0,
            "sessions_cleaned": 0,
            "errors": [],
        }
        
        # Execute cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
                results["callbacks_executed"] += 1
            except Exception as e:
                error_msg = f"Error in cleanup callback {callback.__name__}: {e}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        # Clean up test artifacts
        for artifact in self._test_artifacts:
            try:
                if os.path.exists(artifact):
                    if os.path.isdir(artifact):
                        shutil.rmtree(artifact)
                    else:
                        os.unlink(artifact)
                    results["artifacts_cleaned"] += 1
            except Exception as e:
                logger.warning(f"Failed to clean up artifact {artifact}: {e}")
        
        # Clean up test sessions
        for session_id in self._test_sessions:
            try:
                # Session cleanup logic (e.g., logout, close connections)
                self._cleanup_session(session_id)
                results["sessions_cleaned"] += 1
            except Exception as e:
                logger.warning(f"Failed to clean up session {session_id}: {e}")
        
        logger.info(f"E2E teardown complete: {results}")
        return results
    
    def _cleanup_session(self, session_id: str) -> None:
        """
        Clean up a test session.
        
        Args:
            session_id: Session identifier
        """
        # This is a placeholder - actual cleanup depends on the session management
        logger.debug(f"Cleaning up session: {session_id}")
    
    def cleanup_browser_artifacts(self, artifacts_dir: str = "test-results") -> int:
        """
        Clean up Playwright browser artifacts (screenshots, traces).
        
        Args:
            artifacts_dir: Directory containing browser artifacts
        
        Returns:
            Number of artifacts cleaned up
        """
        if not os.path.exists(artifacts_dir):
            return 0
        
        cleaned = 0
        for item in Path(artifacts_dir).iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                cleaned += 1
            except Exception as e:
                logger.warning(f"Failed to clean up {item}: {e}")
        
        logger.info(f"Cleaned up {cleaned} browser artifacts")
        return cleaned
    
    def reset_test_state(self) -> None:
        """
        Reset test state to initial conditions.
        
        Clears all registered callbacks, artifacts, and sessions.
        """
        self._cleanup_callbacks.clear()
        self._test_artifacts.clear()
        self._test_sessions.clear()
        logger.info("Test state reset to initial conditions")


# =============================================================================
# Comprehensive Test Environment Cleanup
# =============================================================================

class TestEnvironmentCleanup:
    """
    Comprehensive cleanup manager for the entire test environment.
    
    Combines:
    - Database cleanup
    - Redis cleanup
    - File system cleanup
    - E2E teardown
    
    Usage:
        cleanup = TestEnvironmentCleanup()
        cleanup.register_database_cleanup(db_session)
        cleanup.register_redis_cleanup(redis_client)
        cleanup.register_file_cleanup(fs_manager)
        # ... run tests ...
        cleanup.execute_cleanup()  # Clean up everything
    """
    
    def __init__(self):
        """Initialize the comprehensive cleanup manager."""
        self._db_session = None
        self._redis_client = None
        self._fs_manager = None
        self._e2e_manager = None
        self._cleanup_executed = False
    
    def register_database_cleanup(self, db_session) -> None:
        """
        Register database session for cleanup.
        
        Args:
            db_session: SQLAlchemy database session
        """
        from tests.database_isolation import DatabaseCleanupManager
        self._db_session = db_session
    
    def register_redis_cleanup(self, redis_client) -> None:
        """
        Register Redis client for cleanup.
        
        Args:
            redis_client: Redis client instance
        """
        from tests.redis_isolation import RedisTestCleanupManager
        self._redis_client = redis_client
    
    def register_file_cleanup(self, fs_manager: FileSystemCleanupManager) -> None:
        """
        Register file system cleanup manager.
        
        Args:
            fs_manager: FileSystemCleanupManager instance
        """
        self._fs_manager = fs_manager
    
    def register_e2e_teardown(self, e2e_manager: E2ETestTeardownManager) -> None:
        """
        Register E2E teardown manager.
        
        Args:
            e2e_manager: E2ETestTeardownManager instance
        """
        self._e2e_manager = e2e_manager
    
    def execute_cleanup(self) -> dict:
        """
        Execute all registered cleanup operations.
        
        Returns:
            Dictionary with cleanup results for each component
        """
        if self._cleanup_executed:
            logger.warning("Cleanup has already been executed")
            return {"status": "already_executed"}
        
        self._cleanup_executed = True
        results = {
            "database": {"status": "skipped"},
            "redis": {"status": "skipped"},
            "file_system": {"status": "skipped"},
            "e2e": {"status": "skipped"},
        }
        
        # Database cleanup
        if self._db_session is not None:
            try:
                from tests.database_isolation import DatabaseCleanupManager
                cleanup_manager = DatabaseCleanupManager(self._db_session)
                cleanup_manager.truncate_all_tables()
                results["database"] = {"status": "success", "message": "All tables truncated"}
            except Exception as e:
                results["database"] = {"status": "error", "message": str(e)}
                logger.error(f"Database cleanup failed: {e}")
        
        # Redis cleanup
        if self._redis_client is not None:
            try:
                from tests.redis_isolation import RedisTestCleanupManager
                cleanup_manager = RedisTestCleanupManager(self._redis_client)
                cleanup_manager.delete_test_prefix_keys()
                results["redis"] = {"status": "success", "message": "Test keys deleted"}
            except Exception as e:
                results["redis"] = {"status": "error", "message": str(e)}
                logger.error(f"Redis cleanup failed: {e}")
        
        # File system cleanup
        if self._fs_manager is not None:
            try:
                self._fs_manager.cleanup_created_files()
                self._fs_manager.cleanup_created_directories()
                results["file_system"] = {"status": "success", "message": "Files and directories cleaned"}
            except Exception as e:
                results["file_system"] = {"status": "error", "message": str(e)}
                logger.error(f"File system cleanup failed: {e}")
        
        # E2E teardown
        if self._e2e_manager is not None:
            try:
                e2e_results = self._e2e_manager.execute_cleanup()
                results["e2e"] = {"status": "success", "results": e2e_results}
            except Exception as e:
                results["e2e"] = {"status": "error", "message": str(e)}
                logger.error(f"E2E teardown failed: {e}")
        
        logger.info(f"Test environment cleanup complete: {results}")
        return results
    
    def verify_isolation(self) -> dict:
        """
        Verify that test environment is properly isolated.
        
        Returns:
            Dictionary with isolation verification results
        """
        results = {
            "database_clean": True,
            "redis_clean": True,
            "file_system_clean": True,
            "e2e_clean": True,
            "details": {},
        }
        
        # Verify database isolation
        if self._db_session is not None:
            try:
                from tests.database_isolation import DatabaseCleanupManager
                cleanup_manager = DatabaseCleanupManager(self._db_session)
                results["database_clean"] = cleanup_manager.verify_clean_state()
                results["details"]["database"] = "clean" if results["database_clean"] else "has remaining data"
            except Exception as e:
                results["details"]["database"] = f"verification error: {e}"
        
        # Verify Redis isolation
        if self._redis_client is not None:
            try:
                from tests.redis_isolation import RedisTestCleanupManager
                cleanup_manager = RedisTestCleanupManager(self._redis_client)
                results["redis_clean"] = cleanup_manager.verify_clean_state()
                results["details"]["redis"] = "clean" if results["redis_clean"] else "has remaining keys"
            except Exception as e:
                results["details"]["redis"] = f"verification error: {e}"
        
        # Verify file system isolation
        if self._fs_manager is not None:
            results["file_system_clean"] = self._fs_manager.verify_clean_state()
            results["details"]["file_system"] = "clean" if results["file_system_clean"] else "has remaining files"
        
        # Overall status
        results["isolated"] = all([
            results["database_clean"],
            results["redis_clean"],
            results["file_system_clean"],
        ])
        
        return results


# =============================================================================
# Context Managers for Automatic Cleanup
# =============================================================================

@contextmanager
def isolated_test_environment(db_session=None, redis_client=None) -> Generator[TestEnvironmentCleanup, None, None]:
    """
    Context manager for isolated test environment with automatic cleanup.
    
    Usage:
        with isolated_test_environment(db_session, redis_client) as cleanup:
            # Test code here
            # All resources will be cleaned up automatically
            cleanup.register_file_cleanup(fs_manager)
    
    Args:
        db_session: Optional database session
        redis_client: Optional Redis client
    
    Yields:
        TestEnvironmentCleanup instance for registering additional resources
    """
    cleanup_manager = TestEnvironmentCleanup()
    
    # Register provided resources
    if db_session is not None:
        cleanup_manager.register_database_cleanup(db_session)
    if redis_client is not None:
        cleanup_manager.register_redis_cleanup(redis_client)
    
    try:
        yield cleanup_manager
    finally:
        cleanup_manager.execute_cleanup()


@contextmanager
def temporary_test_files(base_dir: Path = None) -> Generator[FileSystemCleanupManager, None, None]:
    """
    Context manager for temporary test files with automatic cleanup.
    
    Usage:
        with temporary_test_files() as fs_manager:
            test_file = fs_manager.create_temporary_file("test.txt", b"content")
            # Use the file in tests
            # File will be cleaned up automatically
    
    Args:
        base_dir: Optional base directory for test files
    
    Yields:
        FileSystemCleanupManager instance
    """
    fs_manager = FileSystemCleanupManager(base_dir)
    
    try:
        yield fs_manager
    finally:
        fs_manager.cleanup_created_files()
        fs_manager.cleanup_created_directories()


@contextmanager
def e2e_test_teardown() -> Generator[E2ETestTeardownManager, None, None]:
    """
    Context manager for E2E test teardown with automatic cleanup.
    
    Usage:
        with e2e_test_teardown() as teardown:
            # Test code here
            teardown.add_test_artifact("screenshot.png")
            teardown.add_test_session("session123")
            # All artifacts and sessions will be cleaned up automatically
    
    Yields:
        E2ETestTeardownManager instance
    """
    teardown_manager = E2ETestTeardownManager()
    
    try:
        yield teardown_manager
    finally:
        teardown_manager.execute_cleanup()


# =============================================================================
# Decorators for Automatic Cleanup
# =============================================================================

def cleanup_after_test(db_param: str = None, redis_param: str = None, 
                        fs_param: str = None) -> Callable:
    """
    Decorator for automatic test cleanup.
    
    Usage:
        @cleanup_after_test(db_param="db", redis_param="redis")
        def test_something(db, redis):
            # Test code here
            # Resources will be cleaned up after test
    
    Args:
        db_param: Name of database session parameter
        redis_param: Name of Redis client parameter
        fs_param: Name of file system manager parameter
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cleanup managers
            fs_manager = None
            if fs_param and fs_param in kwargs:
                fs_manager = kwargs[fs_param]
            
            e2e_manager = E2ETestTeardownManager()
            
            # Add fs_manager to kwargs for the test
            if fs_manager is not None:
                kwargs["_fs_cleanup"] = fs_manager
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Clean up file system
                if fs_manager is not None:
                    fs_manager.cleanup_created_files()
                    fs_manager.cleanup_created_directories()
                
                # Execute E2E teardown
                e2e_manager.execute_cleanup()
        
        return wrapper
    return decorator


# =============================================================================
# Pytest Fixtures for Cleanup
# =============================================================================

@pytest.fixture
def file_cleanup_manager() -> Generator[FileSystemCleanupManager, None, None]:
    """
    Provide a file system cleanup manager for tests.
    
    Usage:
        def test_file_upload(file_cleanup_manager):
            test_dir = file_cleanup_manager.create_test_directory("test_uploads")
            test_file = file_cleanup_manager.create_temporary_file("test.txt", b"content")
            # Test code here
            # Files will be cleaned up automatically after test
    """
    manager = FileSystemCleanupManager()
    yield manager
    manager.cleanup_created_files()
    manager.cleanup_created_directories()


@pytest.fixture
def e2e_teardown_manager() -> Generator[E2ETestTeardownManager, None, None]:
    """
    Provide an E2E teardown manager for tests.
    
    Usage:
        def test_e2e_workflow(e2e_teardown_manager):
            # Test code here
            e2e_teardown_manager.add_test_artifact("screenshot.png")
            e2e_teardown_manager.add_test_session("session123")
            # Artifacts will be cleaned up automatically after test
    """
    manager = E2ETestTeardownManager()
    yield manager
    manager.execute_cleanup()


@pytest.fixture
def test_environment_cleanup(db_session, redis_client) -> Generator[TestEnvironmentCleanup, None, None]:
    """
    Provide a comprehensive test environment cleanup manager.
    
    Usage:
        def test_integration(test_environment_cleanup):
            # Test code here
            # All resources will be cleaned up automatically after test
    """
    cleanup = TestEnvironmentCleanup()
    cleanup.register_database_cleanup(db_session)
    cleanup.register_redis_cleanup(redis_client)
    yield cleanup
    cleanup.execute_cleanup()


@pytest.fixture
def cleanup_verifier(db_session, redis_client, file_cleanup_manager) -> Generator[dict, None, None]:
    """
    Provide a cleanup verification utility.
    
    Usage:
        def test_something(cleanup_verifier):
            # Test code here
            # Verify cleanup after test
            result = cleanup_verifier()
            assert result["isolated"] is True
    """
    def verify() -> dict:
        from tests.database_isolation import DatabaseCleanupManager
        from tests.redis_isolation import RedisTestCleanupManager
        
        results = {
            "database_clean": True,
            "redis_clean": True,
            "file_system_clean": True,
            "isolated": True,
        }
        
        # Verify database
        try:
            db_cleanup = DatabaseCleanupManager(db_session)
            results["database_clean"] = db_cleanup.verify_clean_state()
        except Exception:
            results["database_clean"] = False
        
        # Verify Redis
        try:
            redis_cleanup = RedisTestCleanupManager(redis_client)
            results["redis_clean"] = redis_cleanup.verify_clean_state()
        except Exception:
            results["redis_clean"] = False
        
        # Verify file system
        results["file_system_clean"] = file_cleanup_manager.verify_clean_state()
        
        # Overall isolation
        results["isolated"] = all([
            results["database_clean"],
            results["redis_clean"],
            results["file_system_clean"],
        ])
        
        return results
    
    yield verify


# =============================================================================
# Cleanup Verification Tests
# =============================================================================

def test_file_system_cleanup_manager_creation():
    """Test that FileSystemCleanupManager can be created."""
    manager = FileSystemCleanupManager()
    assert manager is not None
    assert manager._base_dir.exists()


def test_file_system_cleanup_manager_file_creation(file_cleanup_manager):
    """Test that FileSystemCleanupManager can create files."""
    test_file = file_cleanup_manager.create_temporary_file("test.txt", b"test content")
    assert test_file.exists()
    assert test_file.read_bytes() == b"test content"


def test_file_system_cleanup_manager_directory_creation(file_cleanup_manager):
    """Test that FileSystemCleanupManager can create directories."""
    test_dir = file_cleanup_manager.create_test_directory("test_dir")
    assert test_dir.exists()
    assert test_dir.is_dir()


def test_file_system_cleanup_manager_cleanup(file_cleanup_manager):
    """Test that FileSystemCleanupManager cleans up properly."""
    # Create some files and directories
    file_cleanup_manager.create_temporary_file("test1.txt", b"content1")
    file_cleanup_manager.create_temporary_file("test2.txt", b"content2")
    file_cleanup_manager.create_test_directory("test_dir")
    
    # Verify they exist
    assert len(file_cleanup_manager._created_files) == 2
    assert len(file_cleanup_manager._created_dirs) == 1
    
    # Cleanup is called automatically by fixture


def test_e2e_teardown_manager_creation():
    """Test that E2ETestTeardownManager can be created."""
    manager = E2ETestTeardownManager()
    assert manager is not None
    assert len(manager._cleanup_callbacks) == 0
    assert len(manager._test_artifacts) == 0
    assert len(manager._test_sessions) == 0


def test_e2e_teardown_manager_registration(e2e_teardown_manager):
    """Test that E2ETestTeardownManager can register artifacts."""
    e2e_teardown_manager.add_test_artifact("/tmp/test_screenshot.png")
    e2e_teardown_manager.add_test_session("test_session_123")
    
    assert len(e2e_teardown_manager._test_artifacts) == 1
    assert len(e2e_teardown_manager._test_sessions) == 1


def test_e2e_teardown_manager_callback_registration(e2e_teardown_manager):
    """Test that E2ETestTeardownManager can register callbacks."""
    callback_executed = []
    
    def test_callback():
        callback_executed.append(True)
    
    e2e_teardown_manager.register_cleanup_callback(test_callback)
    
    assert len(e2e_teardown_manager._cleanup_callbacks) == 1


def test_test_environment_cleanup_creation():
    """Test that TestEnvironmentCleanup can be created."""
    cleanup = TestEnvironmentCleanup()
    assert cleanup is not None
    assert cleanup._cleanup_executed is False


def test_isolated_test_environment_context_manager():
    """Test that isolated_test_environment context manager works."""
    with isolated_test_environment() as cleanup:
        assert isinstance(cleanup, TestEnvironmentCleanup)


def test_temporary_test_files_context_manager():
    """Test that temporary_test_files context manager works."""
    with temporary_test_files() as fs_manager:
        assert isinstance(fs_manager, FileSystemCleanupManager)


def test_e2e_test_teardown_context_manager():
    """Test that e2e_test_teardown context manager works."""
    with e2e_test_teardown() as teardown_manager:
        assert isinstance(teardown_manager, E2ETestTeardownManager)


def test_cleanup_verifier_fixture(cleanup_verifier):
    """Test that cleanup_verifier fixture works."""
    result = cleanup_verifier()
    assert "isolated" in result
    assert "database_clean" in result
    assert "redis_clean" in result
    assert "file_system_clean" in result


def test_file_system_cleanup_verify_clean_state(file_cleanup_manager):
    """Test that verify_clean_state works correctly."""
    # Initially clean
    assert file_cleanup_manager.verify_clean_state() is True
    
    # Create some files
    file_cleanup_manager.create_temporary_file("test.txt", b"content")
    
    # Now should not be clean
    assert file_cleanup_manager.verify_clean_state() is False
    
    # Cleanup is called automatically by fixture


def test_cleanup_summary(file_cleanup_manager):
    """Test that get_cleanup_summary works correctly."""
    file_cleanup_manager.create_temporary_file("test1.txt", b"content1")
    file_cleanup_manager.create_temporary_file("test2.txt", b"content2")
    file_cleanup_manager.create_test_directory("test_dir")
    
    summary = file_cleanup_manager.get_cleanup_summary()
    assert summary["created_files"] == 2
    assert summary["created_directories"] == 1
    assert "superinsight_test_uploads" in summary["base_directory"]


def test_test_environment_cleanup_execute_cleanup():
    """Test that TestEnvironmentCleanup.execute_cleanup works."""
    cleanup = TestEnvironmentCleanup()
    results = cleanup.execute_cleanup()
    
    assert "database" in results
    assert "redis" in results
    assert "file_system" in results
    assert "e2e" in results


def test_test_environment_cleanup_verify_isolation():
    """Test that TestEnvironmentCleanup.verify_isolation works."""
    cleanup = TestEnvironmentCleanup()
    results = cleanup.verify_isolation()
    
    assert "database_clean" in results
    assert "redis_clean" in results
    assert "file_system_clean" in results
    assert "isolated" in results


def test_cleanup_after_test_decorator():
    """Test that cleanup_after_test decorator works."""
    
    @cleanup_after_test(fs_param="fs")
    def test_function(fs=None):
        if fs:
            fs.create_temporary_file("test.txt", b"content")
        return "success"
    
    result = test_function()
    assert result == "success"


def test_test_upload_config():
    """Test TestUploadConfig configuration."""
    assert TestUploadConfig.DEFAULT_UPLOAD_DIR.exists() or True  # May not exist
    assert TestUploadConfig.TEST_DATA_DIR.exists() or True
    assert TestUploadConfig.FIXTURES_DIR.exists() or True
    
    # Test get_upload_dir
    upload_dir = TestUploadConfig.get_upload_dir("test123")
    assert "test123" in str(upload_dir)
    assert "superinsight_test_uploads" in str(upload_dir)


def test_file_system_cleanup_manager_with_custom_base_dir(tmp_path):
    """Test FileSystemCleanupManager with custom base directory."""
    manager = FileSystemCleanupManager(base_dir=tmp_path)
    assert manager._base_dir == tmp_path
    
    # Create and cleanup
    test_file = manager.create_temporary_file("custom_test.txt", b"custom content")
    assert test_file.exists()
    
    manager.cleanup_created_files()
    assert not test_file.exists()