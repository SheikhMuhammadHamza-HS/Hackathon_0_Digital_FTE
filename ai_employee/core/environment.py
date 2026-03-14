"""
Environment variable validation and loading for AI Employee system.

Provides comprehensive validation of required environment variables
and configuration loading with proper error handling.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """Validation rule for environment variables."""
    name: str
    required: bool = True
    default: Optional[str] = None
    validator: Optional[callable] = None
    description: str = ""
    example: str = ""


class EnvironmentValidationError(Exception):
    """Raised when environment validation fails."""
    pass


class EnvironmentManager:
    """Manages environment variable loading and validation."""

    def __init__(self, env_file: Optional[str] = None):
        """Initialize environment manager.

        Args:
            env_file: Optional path to .env file
        """
        self.env_file = env_file
        self.rules: Dict[str, ValidationRule] = {}
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default validation rules."""
        # System settings
        self.add_rule(ValidationRule(
            name="LOG_LEVEL",
            required=False,
            default="INFO",
            validator=self._validate_log_level,
            description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            example="INFO"
        ))

        self.add_rule(ValidationRule(
            name="ENVIRONMENT",
            required=False,
            default="development",
            validator=self._validate_environment,
            description="Application environment (development, staging, production)",
            example="development"
        ))

        self.add_rule(ValidationRule(
            name="DEBUG",
            required=False,
            default="false",
            validator=self._validate_boolean,
            description="Enable debug mode",
            example="false"
        ))

        # Platinum Tier Options
        self.add_rule(ValidationRule(
            name="PLATINUM_MODE",
            required=False,
            default="local",
            validator=self._validate_platinum_mode,
            description="Agent operating mode (local or cloud) for Platinum Dual Zone",
            example="cloud"
        ))

        # Security
        self.add_rule(ValidationRule(
            name="SECRET_KEY",
            required=True,
            validator=self._validate_secret_key,
            description="Application secret key (must be at least 32 characters)",
            example="your-secret-key-here-minimum-32-chars"
        ))

        self.add_rule(ValidationRule(
            name="JWT_SECRET_KEY",
            required=True,
            validator=self._validate_secret_key,
            description="JWT signing secret key",
            example="your-jwt-secret-key-here-minimum-32-chars"
        ))

        # API settings
        self.add_rule(ValidationRule(
            name="API_HOST",
            required=False,
            default="localhost",
            validator=self._validate_hostname,
            description="API server host",
            example="localhost"
        ))

        self.add_rule(ValidationRule(
            name="API_PORT",
            required=False,
            default="8000",
            validator=self._validate_port,
            description="API server port",
            example="8000"
        ))

        # Data retention
        self.add_rule(ValidationRule(
            name="DATA_RETENTION_DAYS",
            required=False,
            default="730",
            validator=self._validate_positive_integer,
            description="Data retention period in days",
            example="730"
        ))

        self.add_rule(ValidationRule(
            name="APPROVAL_TIMEOUT_HOURS",
            required=False,
            default="4",
            validator=self._validate_positive_integer,
            description="Approval timeout in hours",
            example="4"
        ))

        # Email settings
        self.add_rule(ValidationRule(
            name="EMAIL_HOST",
            required=False,
            validator=self._validate_hostname,
            description="Email server host",
            example="smtp.gmail.com"
        ))

        self.add_rule(ValidationRule(
            name="EMAIL_PORT",
            required=False,
            default="587",
            validator=self._validate_port,
            description="Email server port",
            example="587"
        ))

        self.add_rule(ValidationRule(
            name="EMAIL_USER",
            required=False,
            validator=self._validate_email,
            description="Email username",
            example="user@example.com"
        ))

        
        # Odoo settings
        self.add_rule(ValidationRule(
            name="ODOO_URL",
            required=False,
            validator=self._validate_url,
            description="Odoo server URL",
            example="http://localhost:8069"
        ))

        self.add_rule(ValidationRule(
            name="ODOO_DB",
            required=False,
            validator=self._validate_identifier,
            description="Odoo database name",
            example="your_database"
        ))

        # Monitoring settings
        self.add_rule(ValidationRule(
            name="HEALTH_CHECK_INTERVAL",
            required=False,
            default="60",
            validator=self._validate_positive_integer,
            description="Health check interval in seconds",
            example="60"
        ))

        self.add_rule(ValidationRule(
            name="CIRCUIT_BREAKER_THRESHOLD",
            required=False,
            default="5",
            validator=self._validate_positive_integer,
            description="Circuit breaker failure threshold",
            example="5"
        ))

        # Performance settings
        self.add_rule(ValidationRule(
            name="MAX_CONCURRENT_TASKS",
            required=False,
            default="10",
            validator=self._validate_positive_integer,
            description="Maximum concurrent tasks",
            example="10"
        ))

        self.add_rule(ValidationRule(
            name="TASK_TIMEOUT_SECONDS",
            required=False,
            default="300",
            validator=self._validate_positive_integer,
            description="Task timeout in seconds",
            example="300"
        ))

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule.

        Args:
            rule: Validation rule to add
        """
        self.rules[rule.name] = rule

    def get_rule(self, name: str) -> Optional[ValidationRule]:
        """Get a validation rule.

        Args:
            name: Rule name

        Returns:
            Validation rule or None if not found
        """
        return self.rules.get(name)

    def validate_environment(self, env_file: Optional[str] = None) -> Dict[str, Any]:
        """Validate environment variables.

        Args:
            env_file: Optional path to .env file

        Returns:
            Validated environment variables

        Raises:
            EnvironmentValidationError: If validation fails
        """
        # Load environment file if provided
        if env_file or self.env_file:
            self._load_env_file(env_file or self.env_file)

        errors = []
        validated_vars = {}

        # Validate each rule
        for name, rule in self.rules.items():
            try:
                value = self._validate_variable(name, rule)
                validated_vars[name] = value
            except EnvironmentValidationError as e:
                errors.append(str(e))

        # Report errors
        if errors:
            error_msg = "Environment validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise EnvironmentValidationError(error_msg)

        logger.info("Environment validation passed")
        return validated_vars

    def _load_env_file(self, env_file: str) -> None:
        """Load environment variables from file.

        Args:
            env_file: Path to .env file
        """
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file, override=True)
            logger.debug(f"Loaded environment variables from {env_file}")
        except ImportError:
            logger.warning("python-dotenv not installed, skipping .env file loading")
        except Exception as e:
            logger.error(f"Failed to load .env file {env_file}: {e}")

    def _validate_variable(self, name: str, rule: ValidationRule) -> Any:
        """Validate a single environment variable.

        Args:
            name: Variable name
            rule: Validation rule

        Returns:
            Validated value

        Raises:
            EnvironmentValidationError: If validation fails
        """
        value = os.getenv(name)

        # Check if required
        if rule.required and value is None:
            if rule.default is not None:
                value = rule.default
                os.environ[name] = value
            else:
                raise EnvironmentValidationError(f"{name}: Required environment variable is missing")

        # Use default if not set
        if value is None and rule.default is not None:
            value = rule.default
            os.environ[name] = value

        # Skip validation if still None
        if value is None:
            return None

        # Apply validator
        if rule.validator:
            try:
                return rule.validator(value)
            except Exception as e:
                raise EnvironmentValidationError(f"{name}: {e}")

        return value

    def _validate_log_level(self, value: str) -> str:
        """Validate log level.

        Args:
            value: Log level value

        Returns:
            Validated log level

        Raises:
            ValueError: If invalid log level
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        value = value.upper()

        if value not in valid_levels:
            raise ValueError(f"Must be one of: {', '.join(valid_levels)}")

        return value

    def _validate_environment(self, value: str) -> str:
        """Validate environment name.

        Args:
            value: Environment name

        Returns:
            Validated environment name

        Raises:
            ValueError: If invalid environment
        """
        valid_envs = ["development", "dev", "staging", "production", "prod", "test"]
        value = value.lower()

        if value not in valid_envs:
            raise ValueError(f"Must be one of: {', '.join(valid_envs)}")

        # Normalize environment names
        env_mapping = {
            "dev": "development",
            "prod": "production"
        }

        return env_mapping.get(value, value)

    def _validate_platinum_mode(self, value: str) -> str:
        """Validate platinum dual-zone mode.

        Args:
            value: Mode name

        Returns:
            Validated mode name

        Raises:
            ValueError: If invalid mode
        """
        valid_modes = ["local", "cloud"]
        value = value.lower()

        if value not in valid_modes:
            raise ValueError(f"Must be one of: {', '.join(valid_modes)}")

        return value

    def _validate_boolean(self, value: str) -> bool:
        """Validate boolean value.

        Args:
            value: Boolean string

        Returns:
            Boolean value

        Raises:
            ValueError: If invalid boolean
        """
        value = value.lower()

        if value in ["true", "1", "yes", "on"]:
            return True
        elif value in ["false", "0", "no", "off"]:
            return False
        else:
            raise ValueError("Must be true/false, 1/0, yes/no, or on/off")

    def _validate_secret_key(self, value: str) -> str:
        """Validate secret key.

        Args:
            value: Secret key

        Returns:
            Validated secret key

        Raises:
            ValueError: If invalid secret key
        """
        if len(value) < 32:
            raise ValueError("Must be at least 32 characters long")

        # Check for common weak patterns
        weak_patterns = [
            "secret", "password", "key", "test", "demo",
            "123", "abc", "default", "example"
        ]

        value_lower = value.lower()
        for pattern in weak_patterns:
            if pattern in value_lower:
                raise ValueError(f"Contains weak pattern: {pattern}")

        return value

    def _validate_hostname(self, value: str) -> str:
        """Validate hostname.

        Args:
            value: Hostname

        Returns:
            Validated hostname

        Raises:
            ValueError: If invalid hostname
        """
        if not value:
            raise ValueError("Cannot be empty")

        # Basic hostname validation
        if len(value) > 253:
            raise ValueError("Too long (max 253 characters)")

        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9.-]+$', value):
            raise ValueError("Contains invalid characters")

        # Check for invalid patterns
        if value.startswith('.') or value.endswith('.'):
            raise ValueError("Cannot start or end with dot")

        return value

    def _validate_port(self, value: str) -> int:
        """Validate port number.

        Args:
            value: Port string

        Returns:
            Validated port

        Raises:
            ValueError: If invalid port
        """
        try:
            port = int(value)
        except ValueError:
            raise ValueError("Must be a number")

        if not (1 <= port <= 65535):
            raise ValueError("Must be between 1 and 65535")

        return port

    def _validate_positive_integer(self, value: str) -> int:
        """Validate positive integer.

        Args:
            value: Integer string

        Returns:
            Validated integer

        Raises:
            ValueError: If invalid integer
        """
        try:
            integer = int(value)
        except ValueError:
            raise ValueError("Must be a number")

        if integer < 0:
            raise ValueError("Must be positive")

        return integer

    def _validate_email(self, value: str) -> str:
        """Validate email address.

        Args:
            value: Email address

        Returns:
            Validated email

        Raises:
            ValueError: If invalid email
        """
        if not value:
            raise ValueError("Cannot be empty")

        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(email_pattern, value):
            raise ValueError("Invalid email format")

        return value

    def _validate_url(self, value: str) -> str:
        """Validate URL.

        Args:
            value: URL string

        Returns:
            Validated URL

        Raises:
            ValueError: If invalid URL
        """
        if not value:
            raise ValueError("Cannot be empty")

        try:
            parsed = urlparse(value)
        except Exception:
            raise ValueError("Invalid URL format")

        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Must include scheme and host")

        if parsed.scheme not in ["http", "https"]:
            raise ValueError("Must use http or https scheme")

        return value

    def _validate_identifier(self, value: str) -> str:
        """Validate identifier (database name, etc.).

        Args:
            value: Identifier

        Returns:
            Validated identifier

        Raises:
            ValueError: If invalid identifier
        """
        if not value:
            raise ValueError("Cannot be empty")

        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise ValueError("Contains invalid characters (only letters, numbers, underscore, hyphen)")

        # Check length
        if len(value) > 63:
            raise ValueError("Too long (max 63 characters)")

        # Cannot start or end with underscore or hyphen
        if value.startswith(('_', '-')) or value.endswith(('_', '-')):
            raise ValueError("Cannot start or end with underscore or hyphen")

        return value

    def generate_env_template(self, output_path: Optional[str] = None) -> str:
        """Generate .env template file.

        Args:
            output_path: Optional output file path

        Returns:
            Template content
        """
        lines = [
            "# ============================================",
            "# AI Employee System Environment Configuration",
            "# ============================================",
            "",
            "# System Settings",
            f"LOG_LEVEL={self.rules['LOG_LEVEL'].default}",
            f"ENVIRONMENT={self.rules['ENVIRONMENT'].default}",
            f"DEBUG={self.rules['DEBUG'].default}",
            "",
            "# Security (REQUIRED - CHANGE IN PRODUCTION)",
            "SECRET_KEY=your-secret-key-here-minimum-32-characters",
            "JWT_SECRET_KEY=your-jwt-secret-key-here-minimum-32-characters",
            "",
            "# API Settings",
            f"API_HOST={self.rules['API_HOST'].default}",
            f"API_PORT={self.rules['API_PORT'].default}",
            "",
            "# Data Retention",
            f"DATA_RETENTION_DAYS={self.rules['DATA_RETENTION_DAYS'].default}",
            f"APPROVAL_TIMEOUT_HOURS={self.rules['APPROVAL_TIMEOUT_HOURS'].default}",
            "",
            "# Email Configuration",
            "EMAIL_HOST=smtp.gmail.com",
            "EMAIL_PORT=587",
            "EMAIL_USER=your_email@gmail.com",
            "EMAIL_PASSWORD=your_app_password",
            "EMAIL_FROM=AI Employee <noreply@yourcompany.com>",
            "",
            "# Odoo Configuration",
            "ODOO_URL=http://localhost:8069",
            "ODOO_DB=your_database",
            "ODOO_USERNAME=your_username",
            "ODOO_PASSWORD=your_password",
            "",
            "# Social Media APIs",
            "TWITTER_API_KEY=your_twitter_api_key",
            "TWITTER_API_SECRET=your_twitter_api_secret",
            "TWITTER_ACCESS_TOKEN=your_access_token",
            "TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret",
            "",
            "# Monitoring",
            f"HEALTH_CHECK_INTERVAL={self.rules['HEALTH_CHECK_INTERVAL'].default}",
            f"CIRCUIT_BREAKER_THRESHOLD={self.rules['CIRCUIT_BREAKER_THRESHOLD'].default}",
            "",
            "# Performance",
            f"MAX_CONCURRENT_TASKS={self.rules['MAX_CONCURRENT_TASKS'].default}",
            f"TASK_TIMEOUT_SECONDS={self.rules['TASK_TIMEOUT_SECONDS'].default}",
            ""
        ]

        content = "\n".join(lines)

        if output_path:
            Path(output_path).write_text(content, encoding='utf-8')
            logger.info(f"Generated .env template: {output_path}")

        return content

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation rules.

        Returns:
            Validation summary
        """
        required_vars = [name for name, rule in self.rules.items() if rule.required]
        optional_vars = [name for name, rule in self.rules.items() if not rule.required]

        return {
            'total_variables': len(self.rules),
            'required_variables': len(required_vars),
            'optional_variables': len(optional_vars),
            'required': required_vars,
            'optional': optional_vars
        }


# Global environment manager
env_manager = EnvironmentManager()


def validate_environment(env_file: Optional[str] = None) -> Dict[str, Any]:
    """Validate environment variables.

    Args:
        env_file: Optional path to .env file

    Returns:
        Validated environment variables

    Raises:
        EnvironmentValidationError: If validation fails
    """
    return env_manager.validate_environment(env_file)


def generate_env_template(output_path: Optional[str] = None) -> str:
    """Generate .env template file.

    Args:
        output_path: Optional output file path

    Returns:
        Template content
    """
    return env_manager.generate_env_template(output_path)