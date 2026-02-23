"""Comprehensive error handlers with user-friendly messages."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification."""
    CONFIGURATION = "configuration"
    INTEGRATION = "integration"
    VALIDATION = "validation"
    PERMISSION = "permission"
    NETWORK = "network"
    DATA = "data"
    SYSTEM = "system"
    BUSINESS = "business"


class AIEmployeeError(Exception):
    """Base exception for AI Employee system."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.user_message = user_message or self._generate_user_message()
        self.details = details or {}
        self.suggestions = suggestions or []
        self.timestamp = datetime.now()

    def _generate_user_message(self) -> str:
        """Generate user-friendly error message."""
        category_messages = {
            ErrorCategory.CONFIGURATION: (
                "There's a configuration issue. Please check your settings "
                "in the .env file and ensure all required values are provided."
            ),
            ErrorCategory.INTEGRATION: (
                "Having trouble connecting to an external service. "
                "Please check your internet connection and API credentials."
            ),
            ErrorCategory.VALIDATION: (
                "The provided data is not valid. Please check the input "
                "format and required fields."
            ),
            ErrorCategory.PERMISSION: (
                "Permission denied. Please check file permissions and "
                "ensure the application has access to required resources."
            ),
            ErrorCategory.NETWORK: (
                "Network connection issue. Please check your internet "
                "connection and try again."
            ),
            ErrorCategory.DATA: (
                "Data processing error. The system encountered an issue "
                "while processing the data. Please try again or contact support."
            ),
            ErrorCategory.SYSTEM: (
                "System error occurred. Please try again or contact "
                "support if the issue persists."
            ),
            ErrorCategory.BUSINESS: (
                "Business rule violation. The operation cannot be completed "
                "due to business constraints."
            )
        }
        return category_messages.get(self.category, "An error occurred. Please try again.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "suggestions": self.suggestions
        }


class ConfigurationError(AIEmployeeError):
    """Configuration-related errors."""

    def __init__(self, message: str, missing_keys: Optional[List[str]] = None):
        suggestions = [
            "Check your .env file in the ai_employee directory",
            "Ensure all required environment variables are set",
            "Refer to the quickstart guide for proper configuration"
        ]
        if missing_keys:
            suggestions.insert(0, f"Missing configuration keys: {', '.join(missing_keys)}")

        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            details={"missing_keys": missing_keys} if missing_keys else None,
            suggestions=suggestions
        )


class IntegrationError(AIEmployeeError):
    """External service integration errors."""

    def __init__(
        self,
        message: str,
        service: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None
    ):
        suggestions = [
            f"Check {service} API credentials and permissions",
            "Verify API rate limits and quotas",
            "Ensure the service is accessible from your network",
            "Check service status page for outages"
        ]

        super().__init__(
            message=message,
            category=ErrorCategory.INTEGRATION,
            severity=ErrorSeverity.HIGH,
            details={
                "service": service,
                "status_code": status_code,
                "response_body": response_body
            },
            suggestions=suggestions
        )


class ValidationError(AIEmployeeError):
    """Data validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        suggestions = [
            "Check the input data format",
            "Ensure all required fields are provided",
            "Validate data against the API schema"
        ]

        if field:
            suggestions.insert(0, f"Check the '{field}' field value")

        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            details={"field": field, "value": str(value) if value is not None else None},
            suggestions=suggestions
        )


class PermissionError(AIEmployeeError):
    """Permission-related errors."""

    def __init__(self, message: str, resource: Optional[str] = None):
        suggestions = [
            "Check file and directory permissions",
            "Run the application with appropriate privileges",
            "Ensure the Vault directory structure exists"
        ]

        if resource:
            suggestions.insert(0, f"Check permissions for: {resource}")

        super().__init__(
            message=message,
            category=ErrorCategory.PERMISSION,
            severity=ErrorSeverity.HIGH,
            details={"resource": resource},
            suggestions=suggestions
        )


class BusinessRuleError(AIEmployeeError):
    """Business rule violation errors."""

    def __init__(self, message: str, rule: Optional[str] = None):
        suggestions = [
            "Review business rules and constraints",
            "Contact administrator for rule clarification",
            "Check if approval is required for this operation"
        ]

        if rule:
            suggestions.insert(0, f"Business rule violated: {rule}")

        super().__init__(
            message=message,
            category=ErrorCategory.BUSINESS,
            severity=ErrorSeverity.MEDIUM,
            details={"rule": rule},
            suggestions=suggestions
        )


class ErrorHandler:
    """Centralized error handler for the AI Employee system."""

    @staticmethod
    def handle_database_error(error: Exception) -> AIEmployeeError:
        """Handle database-related errors."""
        if "connection" in str(error).lower():
            return IntegrationError(
                message=f"Database connection failed: {str(error)}",
                service="Database",
                suggestions=[
                    "Check database server is running",
                    "Verify connection string and credentials",
                    "Check network connectivity to database"
                ]
            )
        elif "permission" in str(error).lower():
            return PermissionError(
                message=f"Database permission error: {str(error)}",
                resource="Database",
                suggestions=[
                    "Check database user permissions",
                    "Verify user has access to required tables",
                    "Check database connection credentials"
                ]
            )
        else:
            return AIEmployeeError(
                message=f"Database error: {str(error)}",
                category=ErrorCategory.DATA,
                severity=ErrorSeverity.HIGH
            )

    @staticmethod
    def handle_file_error(error: Exception, filepath: str) -> AIEmployeeError:
        """Handle file-related errors."""
        error_str = str(error).lower()

        if "permission denied" in error_str or "access denied" in error_str:
            return PermissionError(
                message=f"File access error: {str(error)}",
                resource=filepath,
                suggestions=[
                    f"Check permissions for: {filepath}",
                    "Ensure the Vault directory exists",
                    "Run with appropriate file system permissions"
                ]
            )
        elif "not found" in error_str or "no such file" in error_str:
            return ValidationError(
                message=f"File not found: {str(error)}",
                field="file_path",
                value=filepath,
                suggestions=[
                    f"Check if the file exists: {filepath}",
                    "Verify the file path is correct",
                    "Create missing directories if needed"
                ]
            )
        elif "disk full" in error_str or "no space left" in error_str:
            return AIEmployeeError(
                message=f"Disk space error: {str(error)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                suggestions=[
                    "Free up disk space",
                    "Archive old files",
                    "Expand storage capacity"
                ]
            )
        else:
            return AIEmployeeError(
                message=f"File error: {str(error)}",
                category=ErrorCategory.SYSTEM,
                details={"filepath": filepath}
            )

    @staticmethod
    def handle_api_error(error: Exception, endpoint: str, status_code: Optional[int] = None) -> AIEmployeeError:
        """Handle API-related errors."""
        if status_code == 401:
            return IntegrationError(
                message=f"Authentication failed for {endpoint}: {str(error)}",
                service=endpoint,
                status_code=status_code,
                suggestions=[
                    "Check API credentials and tokens",
                    "Refresh authentication tokens",
                    "Verify API key permissions"
                ]
            )
        elif status_code == 429:
            return IntegrationError(
                message=f"Rate limit exceeded for {endpoint}: {str(error)}",
                service=endpoint,
                status_code=status_code,
                suggestions=[
                    "Wait before making more requests",
                    "Check API rate limits",
                    "Implement request throttling"
                ]
            )
        elif status_code and status_code >= 500:
            return IntegrationError(
                message=f"Server error from {endpoint}: {str(error)}",
                service=endpoint,
                status_code=status_code,
                suggestions=[
                    "Check service status page",
                    "Try again later",
                    "Contact service provider if issue persists"
                ]
            )
        else:
            return IntegrationError(
                message=f"API error for {endpoint}: {str(error)}",
                service=endpoint,
                status_code=status_code
            )

    @staticmethod
    def log_error(error: AIEmployeeError, context: Optional[Dict[str, Any]] = None):
        """Log error with context."""
        log_data = {
            "error": error.to_dict(),
            "context": context or {}
        }

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {error.message}", extra=log_data)
        else:
            logger.info(f"Low severity error: {error.message}", extra=log_data)


# Common error messages and suggestions
ERROR_MESSAGES = {
    "odoo_connection": {
        "user_message": "Cannot connect to Odoo accounting system. Please check your Odoo configuration.",
        "suggestions": [
            "Verify Odoo server is running at the specified URL",
            "Check database name and credentials in .env file",
            "Ensure Odoo user has API permissions",
            "Test connection manually: curl http://your-odoo-url:8069"
        ]
    },
    "email_config": {
        "user_message": "Email configuration is invalid. Cannot send notifications.",
        "suggestions": [
            "Check SMTP server settings in .env file",
            "Verify email and password are correct",
            "Use app-specific password for Gmail",
            "Test SMTP connection manually"
        ]
    },
    "social_media_auth": {
        "user_message": "Social media authentication failed. Please check API credentials.",
        "suggestions": [
            "Verify API keys and secrets for each platform",
            "Check callback URLs in platform developer console",
            "Ensure tokens are not expired",
            "Re-authenticate with platforms if needed"
        ]
    },
    "vault_structure": {
        "user_message": "Vault directory structure is missing or incomplete.",
        "suggestions": [
            "Create Vault directory in your home folder",
            "Ensure all subdirectories exist (Inbox, Needs_Action, etc.)",
            "Check file permissions for Vault directory",
            "Run: mkdir -p ~/Vault/{Inbox,Needs_Action,Done,Logs,Pending_Approval}"
        ]
    },
    "data_retention": {
        "user_message": "Data retention policy violation. Cannot perform operation.",
        "suggestions": [
            "Check data retention settings in configuration",
            "Ensure data is not older than retention period",
            "Archive old data before attempting operation",
            "Contact administrator for policy exceptions"
        ]
    }
}


def get_error_message(error_type: str) -> Dict[str, Any]:
    """Get predefined error message and suggestions."""
    return ERROR_MESSAGES.get(error_type, {
        "user_message": "An error occurred. Please try again or contact support.",
        "suggestions": [
            "Check system logs for more details",
            "Try the operation again",
            "Contact support if issue persists"
        ]
    })