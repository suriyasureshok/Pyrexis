"""
utils/logging.py

Production-grade logging utilities with structured formatting.

This module provides:
- Structured logging with JSON support
- Context-aware logging (job_id, correlation_id)
- Multiple output formats (text, JSON)
- Rotating file handlers
- Thread-safe logging

Usage:
    # Basic setup
    setup_logging(level="INFO")
    
    # With file rotation
    setup_logging(level="DEBUG", log_file="pyrexis.log", max_bytes=10*1024*1024, backup_count=5)
    
    # Context logging
    with log_context(job_id="task-1", correlation_id="abc-123"):
        logger.info("Processing job")
"""

import logging
import sys
import json
import threading
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
from datetime import datetime
from contextlib import contextmanager


# Thread-local storage for context
_context = threading.local()


class ContextFilter(logging.Filter):
    """
    Inject context variables into log records.

    Adds job_id, correlation_id, and other context to each log record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        # Get context from thread-local storage
        context = getattr(_context, 'data', {})
        
        # Add context fields to record
        record.job_id = context.get('job_id', '-')
        record.correlation_id = context.get('correlation_id', '-')
        record.user_id = context.get('user_id', '-')
        
        return True


class JSONFormatter(logging.Formatter):
    """
    Format log records as JSON.

    Useful for structured logging systems (ELK, Splunk, CloudWatch).
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'thread': record.threadName,
            'process': record.process,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add context fields
        if hasattr(record, 'job_id') and record.job_id != '-':
            log_data['job_id'] = record.job_id
        if hasattr(record, 'correlation_id') and record.correlation_id != '-':
            log_data['correlation_id'] = record.correlation_id
        if hasattr(record, 'user_id') and record.user_id != '-':
            log_data['user_id'] = record.user_id

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Format log records with colors for terminal output.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
            record.levelname = colored_levelname

        # Format with parent formatter
        formatted = super().format(record)
        
        # Reset levelname for next use
        record.levelname = levelname
        
        return formatted


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_type: str = "text",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    enable_colors: bool = True,
) -> None:
    """
    Setup production-grade logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file path for log output. If provided, uses RotatingFileHandler.
        format_type: Output format - "text" or "json".
        max_bytes: Maximum bytes per log file before rotation (default: 10MB).
        backup_count: Number of backup files to keep (default: 5).
        enable_colors: Enable colored output for console (default: True).

    Example:
        # Basic console logging
        setup_logging(level="INFO")

        # File logging with rotation
        setup_logging(level="DEBUG", log_file="pyrexis.log", max_bytes=50*1024*1024, backup_count=10)

        # JSON logging for production
        setup_logging(level="INFO", log_file="pyrexis.json", format_type="json")
    """
    # Convert level string to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear existing handlers
    logger.handlers.clear()

    # Add context filter
    context_filter = ContextFilter()
    logger.addFilter(context_filter)

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if format_type == "json":
        console_formatter = JSONFormatter()
    else:
        # Text format with context fields
        if enable_colors and sys.stdout.isatty():
            console_formatter = ColoredFormatter(
                fmt="[%(asctime)s] [%(levelname)s] [%(threadName)s:%(process)d] "
                    "[job=%(job_id)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            console_formatter = logging.Formatter(
                fmt="[%(asctime)s] [%(levelname)s] [%(threadName)s:%(process)d] "
                    "[job=%(job_id)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Setup file handler with rotation if log_file specified
    if log_file:
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        file_handler.setLevel(log_level)

        if format_type == "json":
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                fmt="[%(asctime)s] [%(levelname)s] [%(threadName)s:%(process)d] "
                    "[job=%(job_id)s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


@contextmanager
def log_context(**kwargs: Any):
    """
    Context manager for adding context to log records.

    Args:
        **kwargs: Context key-value pairs (job_id, correlation_id, user_id, etc.)

    Example:
        with log_context(job_id="task-1", correlation_id="abc-123"):
            logger.info("Processing job")  # Will include job_id and correlation_id
    """
    # Get or create context dict
    if not hasattr(_context, 'data'):
        _context.data = {}

    # Save previous context
    previous_context = _context.data.copy()

    # Update context with new values
    _context.data.update(kwargs)

    try:
        yield
    finally:
        # Restore previous context
        _context.data = previous_context


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Logger instance.

    Example:
        logger = get_logger(__name__)
        logger.info("Starting process")
    """
    return logging.getLogger(name)


# Create module logger
logger = get_logger(__name__)

