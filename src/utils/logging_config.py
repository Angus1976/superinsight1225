"""
Enhanced Logging Configuration for SuperInsight Platform.

Provides structured logging with consistent format, correlation ID support,
and configurable log levels for different modules.

Validates: Requirements 10.1, 10.2, 10.3, 10.4
"""

import json
import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from src.utils.correlation_middleware import CorrelationIdFilter, get_correlation_id


class StructuredLogFormatter(logging.Formatter):
    """
    Structured log formatter that outputs JSON-formatted log records.
    
    This formatter ensures consistent log format across all modules,
    including timestamp, level, module name, correlation ID, and message.
    
    Validates: Requirements 10.1, 10.2
    """
    
    # Standard fields that should always be present
    STANDARD_FIELDS = [
        "timestamp",
        "level",
        "logger",
        "module",
        "correlation_id",
        "message",
    ]
    
    def __init__(
        self,
        include_extra: bool = True,
        include_traceback: bool = True,
        json_output: bool = False
    ):
        """
        Initialize the formatter.
        
        Args:
            include_extra: Whether to include extra fields from log records
            include_traceback: Whether to include traceback for exceptions
            json_output: Whether to output as JSON (vs human-readable)
        """
        super().__init__()
        self.include_extra = include_extra
        self.include_traceback = include_traceback
        self.json_output = json_output
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log string
        """
        # Build the log data dictionary
        log_data = self._build_log_data(record)
        
        if self.json_output:
            return self._format_json(log_data)
        else:
            return self._format_human_readable(log_data, record)
    
    def _build_log_data(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Build the log data dictionary from a log record."""
        # Get correlation ID
        correlation_id = getattr(record, "correlation_id", None)
        if not correlation_id:
            correlation_id = get_correlation_id() or "-"
        
        # Build base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "correlation_id": correlation_id,
            "message": record.getMessage(),
        }
        
        # Add request_id if available
        request_id = getattr(record, "request_id", None)
        if request_id and request_id != "-":
            log_data["request_id"] = request_id
        
        # Add exception info if present
        if record.exc_info and self.include_traceback:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self._format_traceback(record.exc_info) if record.exc_info[2] else None,
            }
        
        # Add extra fields
        if self.include_extra:
            extra_fields = self._extract_extra_fields(record)
            if extra_fields:
                log_data["extra"] = extra_fields
        
        return log_data
    
    def _extract_extra_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract extra fields from the log record."""
        # Standard LogRecord attributes to exclude
        standard_attrs = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "correlation_id", "request_id", "message", "taskName"
        }
        
        extra = {}
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                # Try to serialize the value
                try:
                    json.dumps(value)
                    extra[key] = value
                except (TypeError, ValueError):
                    extra[key] = str(value)
        
        return extra
    
    def _format_traceback(self, exc_info) -> str:
        """Format exception traceback."""
        if exc_info[2]:
            return "".join(traceback.format_exception(*exc_info))
        return ""
    
    def _format_json(self, log_data: Dict[str, Any]) -> str:
        """Format log data as JSON."""
        try:
            return json.dumps(log_data, ensure_ascii=False, default=str)
        except Exception:
            # Fallback to basic format if JSON serialization fails
            return json.dumps({
                "timestamp": log_data.get("timestamp"),
                "level": log_data.get("level"),
                "message": str(log_data.get("message")),
                "error": "Failed to serialize log data"
            })
    
    def _format_human_readable(self, log_data: Dict[str, Any], record: logging.LogRecord) -> str:
        """Format log data as human-readable string."""
        # Format: [TIMESTAMP] LEVEL [CORRELATION_ID] MODULE:FUNCTION:LINE - MESSAGE
        parts = [
            f"[{log_data['timestamp']}]",
            f"{log_data['level']:8s}",
            f"[{log_data['correlation_id']}]",
            f"{log_data['logger']}:{log_data['function']}:{log_data['line']}",
            "-",
            log_data["message"],
        ]
        
        result = " ".join(parts)
        
        # Add extra fields if present
        if "extra" in log_data and log_data["extra"]:
            extra_str = " ".join(f"{k}={v}" for k, v in log_data["extra"].items())
            result += f" | {extra_str}"
        
        # Add exception info if present
        if "exception" in log_data and log_data["exception"].get("traceback"):
            result += f"\n{log_data['exception']['traceback']}"
        
        return result


class LoggingConfig:
    """
    Logging configuration manager for the SuperInsight platform.
    
    Provides methods to configure logging with structured format,
    correlation ID support, and configurable log levels.
    
    Validates: Requirements 10.1, 10.2, 10.3, 10.4
    """
    
    # Default log levels for different modules
    DEFAULT_LOG_LEVELS = {
        "root": "INFO",
        "src": "INFO",
        "src.api": "INFO",
        "src.database": "WARNING",
        "src.security": "INFO",
        "src.system": "INFO",
        "uvicorn": "INFO",
        "uvicorn.access": "WARNING",
        "sqlalchemy": "WARNING",
        "sqlalchemy.engine": "WARNING",
        "httpx": "WARNING",
        "httpcore": "WARNING",
    }
    
    def __init__(
        self,
        log_level: str = "INFO",
        json_output: bool = False,
        log_file: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        include_traceback: bool = True
    ):
        """
        Initialize logging configuration.
        
        Args:
            log_level: Default log level
            json_output: Whether to output logs as JSON
            log_file: Optional log file path
            max_file_size: Maximum log file size before rotation
            backup_count: Number of backup files to keep
            include_traceback: Whether to include tracebacks in logs
        """
        self.log_level = log_level.upper()
        self.json_output = json_output
        self.log_file = log_file
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.include_traceback = include_traceback
        
        # Create formatter
        self.formatter = StructuredLogFormatter(
            include_extra=True,
            include_traceback=include_traceback,
            json_output=json_output
        )
        
        # Create correlation ID filter
        self.correlation_filter = CorrelationIdFilter()
    
    def configure(self) -> None:
        """
        Configure logging for the application.
        
        This method sets up:
        - Root logger with structured formatter
        - Console handler
        - Optional file handler with rotation
        - Correlation ID filter
        - Module-specific log levels
        """
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Allow all levels, handlers will filter
        
        # Remove existing handlers
        root_logger.handlers.clear()
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level))
        console_handler.setFormatter(self.formatter)
        console_handler.addFilter(self.correlation_filter)
        root_logger.addHandler(console_handler)
        
        # Add file handler if configured
        if self.log_file:
            self._add_file_handler(root_logger)
        
        # Configure module-specific log levels
        self._configure_module_levels()
        
        logging.info(
            "Logging configured",
            extra={
                "log_level": self.log_level,
                "json_output": self.json_output,
                "log_file": self.log_file,
            }
        )
    
    def _add_file_handler(self, logger: logging.Logger) -> None:
        """Add rotating file handler to logger."""
        # Ensure log directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(self.formatter)
        file_handler.addFilter(self.correlation_filter)
        logger.addHandler(file_handler)
    
    def _configure_module_levels(self) -> None:
        """Configure log levels for specific modules."""
        for module, level in self.DEFAULT_LOG_LEVELS.items():
            logger = logging.getLogger(module)
            logger.setLevel(getattr(logging, level))
    
    def set_module_level(self, module: str, level: str) -> None:
        """
        Set log level for a specific module.
        
        Args:
            module: Module name (e.g., "src.api")
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        logger = logging.getLogger(module)
        logger.setLevel(getattr(logging, level.upper()))
    
    def get_module_level(self, module: str) -> str:
        """
        Get log level for a specific module.
        
        Args:
            module: Module name
            
        Returns:
            Log level name
        """
        logger = logging.getLogger(module)
        return logging.getLevelName(logger.level)


# Global logging configuration instance
_logging_config: Optional[LoggingConfig] = None


def configure_logging(
    log_level: str = "INFO",
    json_output: bool = False,
    log_file: Optional[str] = None,
    **kwargs
) -> LoggingConfig:
    """
    Configure logging for the application.
    
    Args:
        log_level: Default log level
        json_output: Whether to output logs as JSON
        log_file: Optional log file path
        **kwargs: Additional configuration options
        
    Returns:
        LoggingConfig instance
    """
    global _logging_config
    
    _logging_config = LoggingConfig(
        log_level=log_level,
        json_output=json_output,
        log_file=log_file,
        **kwargs
    )
    _logging_config.configure()
    
    return _logging_config


def get_logging_config() -> Optional[LoggingConfig]:
    """
    Get the current logging configuration.
    
    Returns:
        LoggingConfig instance or None if not configured
    """
    return _logging_config


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    This is a convenience function that ensures the logger
    has the correlation ID filter applied.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # Ensure correlation filter is applied
    has_filter = any(
        isinstance(f, CorrelationIdFilter) for f in logger.filters
    )
    if not has_filter:
        logger.addFilter(CorrelationIdFilter())
    
    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context
) -> None:
    """
    Log a message with additional context.
    
    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        **context: Additional context to include in the log
    """
    logger.log(level, message, extra=context)


def log_error_with_traceback(
    logger: logging.Logger,
    message: str,
    exception: Optional[Exception] = None,
    **context
) -> None:
    """
    Log an error with full traceback and context.
    
    Validates: Requirements 10.3
    
    Args:
        logger: Logger instance
        message: Error message
        exception: Optional exception to include
        **context: Additional context to include
    """
    if exception:
        context["exception_type"] = type(exception).__name__
        context["exception_message"] = str(exception)
        context["traceback"] = traceback.format_exc()
    
    logger.error(message, extra=context, exc_info=exception is not None)
