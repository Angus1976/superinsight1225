"""
Tests for TCB Logger.
"""

import pytest
import logging
import tempfile
import os
import json

from src.deployment.tcb_logger import (
    TCBLogManager,
    TCBLoggerConfig,
    LogEntry,
    LogLevel,
    JSONFormatter,
    ContextLogger,
    initialize_tcb_logging,
    get_tcb_log_manager,
    get_context_logger
)


class TestTCBLoggerConfig:
    """Tests for TCBLoggerConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = TCBLoggerConfig()
        
        assert config.service_name == "superinsight"
        assert config.log_level == "INFO"
        assert config.enable_json_format is True
        assert config.enable_console_output is True
        assert config.enable_file_output is True
        assert config.buffer_size == 1000
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = TCBLoggerConfig(
            service_name="custom-service",
            log_level="DEBUG",
            enable_json_format=False,
            buffer_size=500
        )
        
        assert config.service_name == "custom-service"
        assert config.log_level == "DEBUG"
        assert config.enable_json_format is False
        assert config.buffer_size == 500


class TestLogLevel:
    """Tests for LogLevel enum."""
    
    def test_log_levels(self):
        """Test log level values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"


class TestLogEntry:
    """Tests for LogEntry."""
    
    def test_entry_creation(self):
        """Test log entry creation."""
        entry = LogEntry(
            timestamp=1234567890.0,
            level=LogLevel.INFO,
            message="Test message",
            service="test-service",
            logger_name="test.logger"
        )
        
        assert entry.timestamp == 1234567890.0
        assert entry.level == LogLevel.INFO
        assert entry.message == "Test message"
        assert entry.service == "test-service"
        assert entry.logger_name == "test.logger"
    
    def test_entry_with_extra(self):
        """Test log entry with extra data."""
        entry = LogEntry(
            timestamp=1234567890.0,
            level=LogLevel.ERROR,
            message="Error occurred",
            service="test-service",
            logger_name="test.logger",
            extra={"key": "value"},
            exception="Traceback...",
            request_id="req-123",
            user_id="user-456",
            tenant_id="tenant-789"
        )
        
        assert entry.extra == {"key": "value"}
        assert entry.exception == "Traceback..."
        assert entry.request_id == "req-123"
        assert entry.user_id == "user-456"
        assert entry.tenant_id == "tenant-789"


class TestJSONFormatter:
    """Tests for JSONFormatter."""
    
    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = JSONFormatter("test-service")
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["service"] == "test-service"
        assert data["logger"] == "test.logger"
    
    def test_format_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = JSONFormatter("test-service")
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.request_id = "req-123"
        record.user_id = "user-456"
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["request_id"] == "req-123"
        assert data["user_id"] == "user-456"


class TestTCBLogManager:
    """Tests for TCBLogManager."""
    
    def test_initialization(self):
        """Test log manager initialization."""
        manager = TCBLogManager()
        
        assert manager.config.service_name == "superinsight"
        assert len(manager.log_buffer) == 0
        assert manager._is_running is False
    
    def test_initialization_with_config(self):
        """Test initialization with custom config."""
        config = TCBLoggerConfig(service_name="custom", log_level="DEBUG")
        manager = TCBLogManager(config)
        
        assert manager.config.service_name == "custom"
        assert manager.config.log_level == "DEBUG"
    
    def test_add_log_entry(self):
        """Test adding a log entry."""
        manager = TCBLogManager()
        
        entry = LogEntry(
            timestamp=1234567890.0,
            level=LogLevel.INFO,
            message="Test message",
            service="test",
            logger_name="test.logger"
        )
        
        manager.add_log_entry(entry)
        
        assert len(manager.log_buffer) == 1
        assert manager.log_counts["INFO"] == 1
    
    def test_get_recent_logs(self):
        """Test getting recent logs."""
        manager = TCBLogManager()
        
        for i in range(5):
            entry = LogEntry(
                timestamp=1234567890.0 + i,
                level=LogLevel.INFO,
                message=f"Message {i}",
                service="test",
                logger_name="test.logger"
            )
            manager.add_log_entry(entry)
        
        logs = manager.get_recent_logs(limit=3)
        
        assert len(logs) == 3
    
    def test_get_recent_logs_with_level_filter(self):
        """Test getting recent logs with level filter."""
        manager = TCBLogManager()
        
        manager.add_log_entry(LogEntry(
            timestamp=1.0, level=LogLevel.INFO, message="Info",
            service="test", logger_name="test"
        ))
        manager.add_log_entry(LogEntry(
            timestamp=2.0, level=LogLevel.ERROR, message="Error",
            service="test", logger_name="test"
        ))
        
        logs = manager.get_recent_logs(level=LogLevel.ERROR)
        
        assert len(logs) == 1
        assert logs[0]["level"] == "ERROR"
    
    def test_search_logs(self):
        """Test searching logs."""
        manager = TCBLogManager()
        
        manager.add_log_entry(LogEntry(
            timestamp=1.0, level=LogLevel.INFO, message="User logged in",
            service="test", logger_name="test"
        ))
        manager.add_log_entry(LogEntry(
            timestamp=2.0, level=LogLevel.INFO, message="User logged out",
            service="test", logger_name="test"
        ))
        manager.add_log_entry(LogEntry(
            timestamp=3.0, level=LogLevel.ERROR, message="Database error",
            service="test", logger_name="test"
        ))
        
        results = manager.search_logs("logged")
        
        assert len(results) == 2
    
    def test_get_log_statistics(self):
        """Test getting log statistics."""
        manager = TCBLogManager()
        
        manager.add_log_entry(LogEntry(
            timestamp=1.0, level=LogLevel.INFO, message="Info",
            service="test", logger_name="test"
        ))
        manager.add_log_entry(LogEntry(
            timestamp=2.0, level=LogLevel.ERROR, message="Error",
            service="test", logger_name="test"
        ))
        
        stats = manager.get_log_statistics()
        
        assert stats["buffer_size"] == 2
        assert stats["counts_by_level"]["INFO"] == 1
        assert stats["counts_by_level"]["ERROR"] == 1
        assert stats["total_logs"] == 2
    
    def test_clear_buffer(self):
        """Test clearing the log buffer."""
        manager = TCBLogManager()
        
        manager.add_log_entry(LogEntry(
            timestamp=1.0, level=LogLevel.INFO, message="Test",
            service="test", logger_name="test"
        ))
        
        assert len(manager.log_buffer) == 1
        
        manager.clear_buffer()
        
        assert len(manager.log_buffer) == 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the manager."""
        config = TCBLoggerConfig(
            enable_file_output=False,
            enable_cloud_push=False
        )
        manager = TCBLogManager(config)
        
        await manager.start()
        assert manager._is_running is True
        
        await manager.stop()
        assert manager._is_running is False


class TestContextLogger:
    """Tests for ContextLogger."""
    
    def test_context_logger_creation(self):
        """Test creating a context logger."""
        ctx_logger = ContextLogger("test.context")
        
        assert ctx_logger._logger is not None
    
    def test_set_context(self):
        """Test setting context."""
        ctx_logger = ContextLogger("test.context")
        
        ctx_logger.set_context(request_id="req-123", user_id="user-456")
        
        assert ctx_logger._context["request_id"] == "req-123"
        assert ctx_logger._context["user_id"] == "user-456"
    
    def test_clear_context(self):
        """Test clearing context."""
        ctx_logger = ContextLogger("test.context")
        
        ctx_logger.set_context(request_id="req-123")
        ctx_logger.clear_context()
        
        assert len(ctx_logger._context) == 0


class TestGlobalLogManager:
    """Tests for global log manager functions."""
    
    def test_initialize_and_get(self):
        """Test initializing and getting global manager."""
        config = TCBLoggerConfig(
            enable_file_output=False,
            enable_console_output=False,
            enable_cloud_push=False
        )
        manager = initialize_tcb_logging(config)
        
        assert manager is not None
        assert get_tcb_log_manager() is manager
    
    def test_get_context_logger(self):
        """Test getting a context logger."""
        ctx_logger = get_context_logger("test.module")
        
        assert isinstance(ctx_logger, ContextLogger)
