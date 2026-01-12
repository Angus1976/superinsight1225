"""
TCB Centralized Log Management.

Provides centralized logging for TCB deployments with JSON formatting,
log aggregation, and cloud log integration.
"""

import asyncio
import logging
import json
import time
import sys
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from datetime import datetime
from pathlib import Path
import traceback

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """A log entry."""
    timestamp: float
    level: LogLevel
    message: str
    service: str
    logger_name: str
    extra: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None


@dataclass
class TCBLoggerConfig:
    """Configuration for TCB logger."""
    service_name: str = "superinsight"
    log_level: str = "INFO"
    enable_json_format: bool = True
    enable_console_output: bool = True
    enable_file_output: bool = True
    log_file_path: str = "/app/logs/superinsight.log"
    max_log_file_size_mb: int = 100
    max_log_files: int = 10
    enable_cloud_push: bool = True
    buffer_size: int = 1000
    flush_interval: float = 5.0


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def __init__(self, service_name: str = "superinsight"):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "service": self.service_name,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "tenant_id"):
            log_data["tenant_id"] = record.tenant_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info[0] else None
            }
        
        return json.dumps(log_data, ensure_ascii=False)


class TCBLogHandler(logging.Handler):
    """Custom log handler for TCB cloud logging."""
    
    def __init__(self, config: 'TCBLoggerConfig', log_manager: 'TCBLogManager'):
        super().__init__()
        self.config = config
        self.log_manager = log_manager
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record."""
        try:
            entry = LogEntry(
                timestamp=record.created,
                level=LogLevel[record.levelname],
                message=record.getMessage(),
                service=self.config.service_name,
                logger_name=record.name,
                extra=getattr(record, "extra_data", {}),
                exception=self._format_exception(record) if record.exc_info else None,
                request_id=getattr(record, "request_id", None),
                user_id=getattr(record, "user_id", None),
                tenant_id=getattr(record, "tenant_id", None)
            )
            self.log_manager.add_log_entry(entry)
        except Exception:
            self.handleError(record)
    
    def _format_exception(self, record: logging.LogRecord) -> str:
        """Format exception info."""
        if record.exc_info:
            return "".join(traceback.format_exception(*record.exc_info))
        return ""


class TCBLogManager:
    """
    Centralized log manager for TCB deployments.
    
    Features:
    - JSON structured logging
    - Log aggregation and buffering
    - Cloud log integration
    - Log rotation
    - Log search and filtering
    """
    
    def __init__(self, config: Optional[TCBLoggerConfig] = None):
        self.config = config or TCBLoggerConfig()
        self.log_buffer: deque = deque(maxlen=self.config.buffer_size)
        self.log_counts: Dict[str, int] = {level.value: 0 for level in LogLevel}
        self._is_running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._handlers: List[logging.Handler] = []
        
        logger.info("TCBLogManager initialized")
    
    def setup_logging(self):
        """Setup logging configuration."""
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.log_level))
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        if self.config.enable_console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            if self.config.enable_json_format:
                console_handler.setFormatter(JSONFormatter(self.config.service_name))
            else:
                console_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
            root_logger.addHandler(console_handler)
            self._handlers.append(console_handler)
        
        # File handler
        if self.config.enable_file_output:
            try:
                log_path = Path(self.config.log_file_path)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    self.config.log_file_path,
                    maxBytes=self.config.max_log_file_size_mb * 1024 * 1024,
                    backupCount=self.config.max_log_files
                )
                if self.config.enable_json_format:
                    file_handler.setFormatter(JSONFormatter(self.config.service_name))
                else:
                    file_handler.setFormatter(logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    ))
                root_logger.addHandler(file_handler)
                self._handlers.append(file_handler)
            except Exception as e:
                logger.error(f"Failed to setup file handler: {e}")
        
        # TCB cloud handler
        if self.config.enable_cloud_push:
            tcb_handler = TCBLogHandler(self.config, self)
            tcb_handler.setLevel(getattr(logging, self.config.log_level))
            root_logger.addHandler(tcb_handler)
            self._handlers.append(tcb_handler)
        
        logger.info(f"Logging configured with level: {self.config.log_level}")
    
    def add_log_entry(self, entry: LogEntry):
        """Add a log entry to the buffer."""
        self.log_buffer.append(entry)
        self.log_counts[entry.level.value] += 1
    
    async def start(self):
        """Start the log manager."""
        if self._is_running:
            return
        
        self._is_running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("TCBLogManager started")
    
    async def stop(self):
        """Stop the log manager."""
        self._is_running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self._flush_to_cloud()
        
        logger.info("TCBLogManager stopped")
    
    async def _flush_loop(self):
        """Background loop for flushing logs to cloud."""
        while self._is_running:
            try:
                await asyncio.sleep(self.config.flush_interval)
                await self._flush_to_cloud()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in log flush loop: {e}")
    
    async def _flush_to_cloud(self):
        """Flush buffered logs to cloud."""
        if not self.config.enable_cloud_push:
            return
        
        if not self.log_buffer:
            return
        
        # Get logs to flush
        logs_to_flush = list(self.log_buffer)
        self.log_buffer.clear()
        
        # In production, this would push to TCB cloud logging
        # For now, we just track that logs were flushed
        logger.debug(f"Flushed {len(logs_to_flush)} logs to cloud")
    
    def get_recent_logs(
        self,
        limit: int = 100,
        level: Optional[LogLevel] = None,
        service: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get recent logs with optional filtering."""
        logs = list(self.log_buffer)
        
        # Apply filters
        if level:
            logs = [l for l in logs if l.level == level]
        if service:
            logs = [l for l in logs if l.service == service]
        if start_time:
            logs = [l for l in logs if l.timestamp >= start_time]
        if end_time:
            logs = [l for l in logs if l.timestamp <= end_time]
        
        # Return most recent
        logs = logs[-limit:]
        
        return [
            {
                "timestamp": l.timestamp,
                "level": l.level.value,
                "message": l.message,
                "service": l.service,
                "logger": l.logger_name,
                "extra": l.extra,
                "exception": l.exception,
                "request_id": l.request_id,
                "user_id": l.user_id,
                "tenant_id": l.tenant_id
            }
            for l in logs
        ]
    
    def search_logs(
        self,
        query: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search logs by message content."""
        logs = list(self.log_buffer)
        query_lower = query.lower()
        
        matching = [
            l for l in logs
            if query_lower in l.message.lower()
        ]
        
        return [
            {
                "timestamp": l.timestamp,
                "level": l.level.value,
                "message": l.message,
                "service": l.service,
                "logger": l.logger_name
            }
            for l in matching[-limit:]
        ]
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get logging statistics."""
        return {
            "buffer_size": len(self.log_buffer),
            "max_buffer_size": self.config.buffer_size,
            "counts_by_level": self.log_counts.copy(),
            "total_logs": sum(self.log_counts.values()),
            "is_running": self._is_running,
            "log_level": self.config.log_level,
            "json_format_enabled": self.config.enable_json_format,
            "cloud_push_enabled": self.config.enable_cloud_push
        }
    
    def clear_buffer(self):
        """Clear the log buffer."""
        self.log_buffer.clear()
        logger.info("Log buffer cleared")


# Context logger for request tracking
class ContextLogger:
    """Logger with context support for request tracking."""
    
    def __init__(self, logger_name: str):
        self._logger = logging.getLogger(logger_name)
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """Set context values."""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear context."""
        self._context.clear()
    
    def _log(self, level: int, message: str, *args, **kwargs):
        """Log with context."""
        extra = kwargs.pop("extra", {})
        extra.update(self._context)
        
        # Create log record with extra data
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "(unknown file)",
            0,
            message,
            args,
            None,
            extra=extra
        )
        
        # Add extra data as attribute
        record.extra_data = extra
        for key, value in self._context.items():
            setattr(record, key, value)
        
        self._logger.handle(record)
    
    def debug(self, message: str, *args, **kwargs):
        self._log(logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        self._log(logging.INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        self._log(logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        self._log(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        self._log(logging.CRITICAL, message, *args, **kwargs)


# Global log manager
tcb_log_manager: Optional[TCBLogManager] = None


def initialize_tcb_logging(
    config: Optional[TCBLoggerConfig] = None
) -> TCBLogManager:
    """Initialize the global TCB log manager."""
    global tcb_log_manager
    tcb_log_manager = TCBLogManager(config)
    tcb_log_manager.setup_logging()
    return tcb_log_manager


def get_tcb_log_manager() -> Optional[TCBLogManager]:
    """Get the global TCB log manager."""
    return tcb_log_manager


def get_context_logger(name: str) -> ContextLogger:
    """Get a context-aware logger."""
    return ContextLogger(name)
