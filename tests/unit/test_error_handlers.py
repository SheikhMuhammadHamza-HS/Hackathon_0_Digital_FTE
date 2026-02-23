"""Unit tests for error handlers."""

import pytest
from datetime import datetime
from ai_employee.utils.error_handlers import (
    AIEmployeeError,
    ConfigurationError,
    IntegrationError,
    ValidationError,
    PermissionError,
    BusinessRuleError,
    ErrorHandler,
    ErrorSeverity,
    ErrorCategory,
    get_error_message
)


class TestAIEmployeeError:
    """Test AIEmployeeError base class."""

    def test_basic_error_creation(self):
        """Test basic error creation."""
        error = AIEmployeeError("Test message")
        assert error.message == "Test message"
        assert error.category == ErrorCategory.SYSTEM
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.user_message is not None
        assert error.suggestions == []
        assert isinstance(error.timestamp, datetime)

    def test_error_with_custom_properties(self):
        """Test error with custom properties."""
        error = AIEmployeeError(
            message="Custom error",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            user_message="Custom user message",
            details={"field": "test"},
            suggestions=["Try again"]
        )
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.LOW
        assert error.user_message == "Custom user message"
        assert error.details == {"field": "test"}
        assert error.suggestions == ["Try again"]

    def test_error_to_dict(self):
        """Test error serialization to dictionary."""
        error = AIEmployeeError(
            message="Test error",
            category=ErrorCategory.INTEGRATION,
            severity=ErrorSeverity.HIGH,
            details={"service": "test"},
            suggestions=["Check service"]
        )
        error_dict = error.to_dict()

        assert error_dict["error"] == "AIEmployeeError"
        assert error_dict["message"] == "Test error"
        assert error_dict["category"] == "integration"
        assert error_dict["severity"] == "high"
        assert error_dict["details"] == {"service": "test"}
        assert error_dict["suggestions"] == ["Check service"]
        assert "timestamp" in error_dict


class TestSpecificErrors:
    """Test specific error types."""

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError(
            "Missing config",
            missing_keys=["API_KEY", "SECRET"]
        )
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.details["missing_keys"] == ["API_KEY", "SECRET"]
        assert "Missing configuration keys" in error.suggestions[0]

    def test_integration_error(self):
        """Test IntegrationError."""
        error = IntegrationError(
            "API call failed",
            service="Twitter",
            status_code=429,
            response_body="Rate limit exceeded"
        )
        assert error.category == ErrorCategory.INTEGRATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.details["service"] == "Twitter"
        assert error.details["status_code"] == 429
        assert "Twitter API credentials" in error.suggestions[0]

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError(
            "Invalid email format",
            field="email",
            value="invalid-email"
        )
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.details["field"] == "email"
        assert error.details["value"] == "invalid-email"
        assert "email field" in error.suggestions[0]

    def test_permission_error(self):
        """Test PermissionError."""
        error = PermissionError(
            "Cannot read file",
            resource="/vault/data.json"
        )
        assert error.category == ErrorCategory.PERMISSION
        assert error.severity == ErrorSeverity.HIGH
        assert error.details["resource"] == "/vault/data.json"
        assert "/vault/data.json" in error.suggestions[0]

    def test_business_rule_error(self):
        """Test BusinessRuleError."""
        error = BusinessRuleError(
            "Invoice amount exceeds limit",
            rule="MAX_INVOICE_AMOUNT"
        )
        assert error.category == ErrorCategory.BUSINESS
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.details["rule"] == "MAX_INVOICE_AMOUNT"
        assert "MAX_INVOICE_AMOUNT" in error.suggestions[0]


class TestErrorHandler:
    """Test ErrorHandler utility class."""

    def test_handle_database_error_connection(self):
        """Test database connection error handling."""
        error = Exception("Connection refused")
        handled = ErrorHandler.handle_database_error(error)

        assert isinstance(handled, IntegrationError)
        assert handled.category == ErrorCategory.INTEGRATION
        assert "Database connection failed" in handled.message

    def test_handle_database_error_permission(self):
        """Test database permission error handling."""
        error = Exception("Permission denied for database")
        handled = ErrorHandler.handle_database_error(error)

        assert isinstance(handled, PermissionError)
        assert handled.category == ErrorCategory.PERMISSION
        assert "Database permission error" in handled.message

    def test_handle_file_error_permission(self):
        """Test file permission error handling."""
        error = Exception("Permission denied: /vault/test.txt")
        handled = ErrorHandler.handle_file_error(error, "/vault/test.txt")

        assert isinstance(handled, PermissionError)
        assert handled.category == ErrorCategory.PERMISSION
        assert "/vault/test.txt" in handled.suggestions[0]

    def test_handle_file_error_not_found(self):
        """Test file not found error handling."""
        error = Exception("No such file or directory: /vault/missing.txt")
        handled = ErrorHandler.handle_file_error(error, "/vault/missing.txt")

        assert isinstance(handled, ValidationError)
        assert handled.category == ErrorCategory.VALIDATION
        assert handled.details["field"] == "file_path"

    def test_handle_file_error_disk_full(self):
        """Test disk full error handling."""
        error = Exception("No space left on device")
        handled = ErrorHandler.handle_file_error(error, "/vault/data.txt")

        assert handled.category == ErrorCategory.SYSTEM
        assert handled.severity == ErrorSeverity.CRITICAL
        assert "Free up disk space" in handled.suggestions[0]

    def test_handle_api_error_auth(self):
        """Test API authentication error handling."""
        error = Exception("Unauthorized")
        handled = ErrorHandler.handle_api_error(error, "Twitter API", 401)

        assert isinstance(handled, IntegrationError)
        assert handled.category == ErrorCategory.INTEGRATION
        assert "Authentication failed" in handled.message
        assert handled.details["status_code"] == 401

    def test_handle_api_error_rate_limit(self):
        """Test API rate limit error handling."""
        error = Exception("Too many requests")
        handled = ErrorHandler.handle_api_error(error, "Facebook API", 429)

        assert isinstance(handled, IntegrationError)
        assert "Rate limit exceeded" in handled.message
        assert "rate limit" in handled.suggestions[0]

    def test_handle_api_error_server_error(self):
        """Test API server error handling."""
        error = Exception("Internal server error")
        handled = ErrorHandler.handle_api_error(error, "LinkedIn API", 500)

        assert isinstance(handled, IntegrationError)
        assert "Server error" in handled.message
        assert handled.details["status_code"] == 500


class TestErrorMessages:
    """Test predefined error messages."""

    def test_get_error_message_existing(self):
        """Test getting existing error message."""
        error_info = get_error_message("odoo_connection")
        assert "user_message" in error_info
        assert "suggestions" in error_info
        assert "Odoo" in error_info["user_message"]

    def test_get_error_message_nonexistent(self):
        """Test getting non-existent error message."""
        error_info = get_error_message("nonexistent_error")
        assert "user_message" in error_info
        assert "suggestions" in error_info
        assert "An error occurred" in error_info["user_message"]


class TestErrorCategories:
    """Test error categories enum."""

    def test_all_categories_exist(self):
        """Test all expected categories exist."""
        expected_categories = {
            "configuration",
            "integration",
            "validation",
            "permission",
            "network",
            "data",
            "system",
            "business"
        }

        actual_categories = {cat.value for cat in ErrorCategory}
        assert actual_categories == expected_categories


class TestErrorSeverity:
    """Test error severity enum."""

    def test_all_severity_levels_exist(self):
        """Test all expected severity levels exist."""
        expected_severities = {"low", "medium", "high", "critical"}
        actual_severities = {sev.value for sev in ErrorSeverity}
        assert actual_severities == expected_severities