"""
Custom exceptions for the Minimum Viable Agent.
"""


class AgentException(Exception):
    """Base exception for agent-related errors."""
    pass


class FileProcessingException(AgentException):
    """Raised when there's an error during file processing."""
    pass


class FileSizeLimitException(FileProcessingException):
    """Raised when a file exceeds the size limit."""
    pass


class UnsupportedFileTypeException(FileProcessingException):
    """Raised when a file type is not supported."""
    pass


class TriggerCreationException(AgentException):
    """Raised when there's an error creating a trigger file."""
    pass


class ConfigurationException(AgentException):
    """Raised when there's an error with configuration."""
    pass


class SecurityException(AgentException):
    """Raised when there's a security-related error."""
    pass


class ClaudeCodeIntegrationException(AgentException):
    """Raised when there's an error integrating with Claude Code."""
    pass


class DashboardException(AgentException):
    """Raised when there's an error updating the dashboard."""
    pass


class FileMoveException(AgentException):
    """Raised when there's an error moving a file."""
    pass


class FileSystemException(AgentException):
    """Raised when there's a general filesystem error."""
    pass