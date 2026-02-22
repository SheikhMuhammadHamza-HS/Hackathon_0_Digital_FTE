"""
Centralized logging configuration for AI Employee system.

Provides structured logging with appropriate handlers, formatters,
and log rotation for production use.
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import structlog
from datetime import datetime

from ai_employee.core.config import get_config


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }

    def format(self, record):
        """Format log record with colors."""
        if hasattr(record, 'no_color') and record.no_color:
            return super().format(record)

        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Add color to levelname
        record.levelname = f"{color}{record.levelname}{reset}"

        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            }:
                log_entry[key] = value

        import json
        return json.dumps(log_entry)


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_json: bool = None
) -> None:
    """Setup centralized logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        enable_console: Enable console logging
        enable_json: Enable JSON formatting (auto-detected based on environment)
    """
    config = get_config()

    # Determine settings
    if log_level is None:
        log_level = config.log_level

    if enable_json is None:
        enable_json = config.environment == 'production'

    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Setup console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))

        if enable_json:
            console_formatter = JSONFormatter()
        else:
            console_formatter = ColoredFormatter(
                fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Setup file handler with rotation
    if log_file:
        # Use rotating file handler for log rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))

        # Always use JSON format for files
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Setup specific loggers
    _setup_specific_loggers()

    # Configure structlog
    _setup_structlog(enable_json)

    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, JSON: {enable_json}, Console: {enable_console}")


def _setup_specific_loggers() -> None:
    """Setup logging levels for specific loggers."""
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)


def _setup_structlog(enable_json: bool) -> None:
    """Configure structlog for structured logging.

    Args:
        enable_json: Whether to use JSON formatting
    """
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if enable_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def setup_file_logging(
    base_path: Optional[Path] = None,
    retention_days: Optional[int] = None
) -> Dict[str, str]:
    """Setup file-based logging with multiple log files.

    Args:
        base_path: Base path for log files
        retention_days: Number of days to retain logs

    Returns:
        Dictionary mapping log types to file paths
    """
    config = get_config()

    if base_path is None:
        base_path = config.paths.logs_path

    if retention_days is None:
        retention_days = config.data_retention_days

    # Ensure logs directory exists
    base_path.mkdir(parents=True, exist_ok=True)

    # Define log files
    log_files = {
        'application': base_path / 'ai_employee.log',
        'errors': base_path / 'errors.log',
        'business': base_path / 'business.log',
        'external': base_path / 'external.log',
        'security': base_path / 'security.log',
        'performance': base_path / 'performance.log',
    }

    # Setup specific loggers for different types
    _setup_type_specific_loggers(log_files)

    return {k: str(v) for k, v in log_files.items()}


def _setup_type_specific_loggers(log_files: Dict[str, Path]) -> None:
    """Setup type-specific loggers with their own files.

    Args:
        log_files: Dictionary of log file paths
    """
    config = get_config()

    # Error logger - only ERROR and CRITICAL
    error_logger = logging.getLogger('ai_employee.errors')
    error_logger.setLevel(logging.ERROR)

    error_handler = logging.handlers.RotatingFileHandler(
        log_files['errors'],
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setFormatter(JSONFormatter())
    error_logger.addHandler(error_handler)
    error_logger.propagate = True

    # Business operations logger
    business_logger = logging.getLogger('ai_employee.business')
    business_logger.setLevel(logging.INFO)

    business_handler = logging.handlers.RotatingFileHandler(
        log_files['business'],
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10,
        encoding='utf-8'
    )
    business_handler.setFormatter(JSONFormatter())
    business_logger.addHandler(business_handler)
    business_logger.propagate = False  # Don't duplicate to main log

    # External API logger
    external_logger = logging.getLogger('ai_employee.external')
    external_logger.setLevel(logging.INFO)

    external_handler = logging.handlers.RotatingFileHandler(
        log_files['external'],
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=5,
        encoding='utf-8'
    )
    external_handler.setFormatter(JSONFormatter())
    external_logger.addHandler(external_handler)
    external_logger.propagate = False

    # Security logger
    security_logger = logging.getLogger('ai_employee.security')
    security_logger.setLevel(logging.INFO)

    security_handler = logging.handlers.RotatingFileHandler(
        log_files['security'],
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,  # Keep more security logs
        encoding='utf-8'
    )
    security_handler.setFormatter(JSONFormatter())
    security_logger.addHandler(security_handler)
    security_logger.propagate = False

    # Performance logger
    performance_logger = logging.getLogger('ai_employee.performance')
    performance_logger.setLevel(logging.INFO)

    performance_handler = logging.handlers.RotatingFileHandler(
        log_files['performance'],
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=3,
        encoding='utf-8'
    )
    performance_handler.setFormatter(JSONFormatter())
    performance_logger.addHandler(performance_handler)
    performance_logger.propagate = False


class BusinessLogger:
    """Logger for business operations with audit trail."""

    def __init__(self):
        self.logger = logging.getLogger('ai_employee.business')

    def log_invoice_created(self, invoice_id: str, client_id: str, amount: float) -> None:
        """Log invoice creation for audit trail."""
        self.logger.info(
            "invoice_created",
            extra={
                'action': 'invoice_created',
                'invoice_id': invoice_id,
                'client_id': client_id,
                'amount': amount,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

    def log_payment_processed(self, payment_id: str, invoice_id: str, amount: float) -> None:
        """Log payment processing for audit trail."""
        self.logger.info(
            "payment_processed",
            extra={
                'action': 'payment_processed',
                'payment_id': payment_id,
                'invoice_id': invoice_id,
                'amount': amount,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

    def log_approval_requested(self, item_type: str, item_id: str, amount: Optional[float] = None) -> None:
        """Log approval request."""
        self.logger.info(
            "approval_requested",
            extra={
                'action': 'approval_requested',
                'item_type': item_type,
                'item_id': item_id,
                'amount': amount,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

    def log_approval_decision(self, item_type: str, item_id: str, approved: bool, user: str) -> None:
        """Log approval decision."""
        self.logger.info(
            "approval_decision",
            extra={
                'action': 'approval_decision',
                'item_type': item_type,
                'item_id': item_id,
                'approved': approved,
                'user': user,
                'timestamp': datetime.utcnow().isoformat()
            }
        )


class SecurityLogger:
    """Logger for security events."""

    def __init__(self):
        self.logger = logging.getLogger('ai_employee.security')

    def log_authentication_attempt(self, user: str, success: bool, ip_address: str) -> None:
        """Log authentication attempt."""
        level = logging.INFO if success else logging.WARNING
        self.logger.log(
            level,
            "authentication_attempt",
            extra={
                'event': 'authentication',
                'user': user,
                'success': success,
                'ip_address': ip_address,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

    def log_access_denied(self, resource: str, user: str, reason: str) -> None:
        """Log access denied event."""
        self.logger.warning(
            "access_denied",
            extra={
                'event': 'access_denied',
                'resource': resource,
                'user': user,
                'reason': reason,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

    def log_security_violation(self, violation_type: str, details: Dict[str, Any]) -> None:
        """Log security violation."""
        self.logger.error(
            "security_violation",
            extra={
                'event': 'security_violation',
                'violation_type': violation_type,
                'details': details,
                'timestamp': datetime.utcnow().isoformat()
            }
        )


# Global logger instances
business_logger = BusinessLogger()
security_logger = SecurityLogger()