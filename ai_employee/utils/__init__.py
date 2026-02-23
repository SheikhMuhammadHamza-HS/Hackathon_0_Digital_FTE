"""Utility functions for AI Employee system.

Provides shared utilities including:
- File system monitoring
- Approval system
- Logging configuration
- Health monitoring
- Error recovery
- Process watchdog
- Common helper functions
"""

from .logging_config import get_logger, setup_logging
# Import file monitor lazily to avoid issues during tests
try:
    from .file_monitor import get_file_monitor
except ImportError:
    get_file_monitor = None
from .approval_system import get_approval_system
from .health_monitor import get_health_monitor, initialize_health_monitor, HealthStatus, HealthEvent
from .error_recovery import ErrorRecoveryService, ErrorCategory, ErrorSeverity
from .process_watchdog import get_process_watchdog, initialize_process_watchdog, ProcessWatchdog, ProcessStatus, RestartStrategy

__all__ = [
    "get_logger",
    "configure_logging",
    "get_file_monitor",
    "FileChangeType",
    "get_approval_system",
    "get_health_monitor",
    "initialize_health_monitor",
    "HealthStatus",
    "HealthEvent",
    "ErrorRecoveryService",
    "ErrorCategory",
    "ErrorSeverity",
    "get_process_watchdog",
    "initialize_process_watchdog",
    "ProcessWatchdog",
    "ProcessStatus",
    "RestartStrategy"
]