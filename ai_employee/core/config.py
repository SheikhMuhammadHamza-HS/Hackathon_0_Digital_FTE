"""
Configuration management for AI Employee system.

Handles loading, validation, and access to configuration settings
from environment variables and configuration files.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600


@dataclass
class EmailConfig:
    """Email service configuration."""
    host: str
    port: int
    user: str
    password: str
    from_email: str
    use_tls: bool = True
    timeout: int = 30


@dataclass
class OdooConfig:
    """Odoo ERP configuration."""
    url: str
    database: str
    username: str
    password: str
    timeout: int = 30
    max_retries: int = 3


@dataclass
class SocialMediaConfig:
    """Social media API configuration."""
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None
    twitter_bearer_token: Optional[str] = None

    facebook_page_id: Optional[str] = None
    facebook_access_token: Optional[str] = None
    facebook_app_id: Optional[str] = None
    facebook_app_secret: Optional[str] = None

    instagram_user_id: Optional[str] = None
    instagram_access_token: Optional[str] = None
    instagram_client_id: Optional[str] = None
    instagram_client_secret: Optional[str] = None

    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    linkedin_access_token: Optional[str] = None
    linkedin_company_id: Optional[str] = None


@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str
    jwt_secret_key: str
    jwt_expiration_hours: int = 24
    api_key_header: str = "X-API-Key"


@dataclass
class MonitoringConfig:
    """Monitoring and health check configuration."""
    health_check_interval: int = 60
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 300
    max_retry_attempts: int = 3
    retry_backoff_factor: float = 2.0
    metrics_enabled: bool = True
    metrics_port: int = 9090


@dataclass
class PerformanceConfig:
    """Performance and limits configuration."""
    max_concurrent_tasks: int = 10
    task_timeout_seconds: int = 300
    max_file_size_mb: int = 10
    rate_limit_requests_per_minute: int = 100


@dataclass
class PathsConfig:
    """File system paths configuration."""
    vault_path: Path
    inbox_path: Path
    needs_action_path: Path
    pending_approval_path: Path
    approved_path: Path
    rejected_path: Path
    done_path: Path
    logs_path: Path
    reports_path: Path
    archive_path: Path


@dataclass
class AppConfig:
    """Main application configuration."""
    # System settings
    log_level: str = "INFO"
    environment: str = "development"
    debug: bool = False
    api_host: str = "localhost"
    api_port: int = 8000

    # Data retention
    data_retention_days: int = 730
    temp_file_retention_days: int = 7
    approval_timeout_hours: int = 4

    # Sub-configurations
    email: Optional[EmailConfig] = None
    odoo: Optional[OdooConfig] = None
    social_media: SocialMediaConfig = field(default_factory=SocialMediaConfig)
    security: Optional[SecurityConfig] = None
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    paths: Optional[PathsConfig] = None


class ConfigManager:
    """Manages application configuration loading and validation."""

    def __init__(self, env_file: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            env_file: Optional path to .env file
        """
        self.env_file = env_file or ".env"
        self._config: Optional[AppConfig] = None

    def load_config(self) -> AppConfig:
        """Load and validate configuration from environment.

        Returns:
            Validated application configuration

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        if self._config is not None:
            return self._config

        # Load environment variables
        load_dotenv(self.env_file)

        # Validate required fields
        self._validate_required_fields()

        # Build configuration
        self._config = self._build_config()

        logger.info(f"Configuration loaded successfully for environment: {self._config.environment}")
        return self._config

    def _validate_required_fields(self) -> None:
        """Validate required environment variables are present.

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = [
            "SECRET_KEY",
            "JWT_SECRET_KEY",
        ]

        missing_fields = []
        for field in required_fields:
            if not os.getenv(field):
                missing_fields.append(field)

        if missing_fields:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")

    def _build_config(self) -> AppConfig:
        """Build configuration object from environment variables.

        Returns:
            Application configuration
        """
        # System settings
        config = AppConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            api_host=os.getenv("API_HOST", "localhost"),
            api_port=int(os.getenv("API_PORT", "8000")),
            data_retention_days=int(os.getenv("DATA_RETENTION_DAYS", "730")),
            temp_file_retention_days=int(os.getenv("TEMP_FILE_RETENTION_DAYS", "7")),
            approval_timeout_hours=int(os.getenv("APPROVAL_TIMEOUT_HOURS", "4")),
        )

        # Email configuration
        if os.getenv("EMAIL_HOST"):
            config.email = EmailConfig(
                host=os.getenv("EMAIL_HOST"),
                port=int(os.getenv("EMAIL_PORT", "587")),
                user=os.getenv("EMAIL_USER"),
                password=os.getenv("EMAIL_PASSWORD"),
                from_email=os.getenv("EMAIL_FROM"),
                use_tls=os.getenv("EMAIL_USE_TLS", "true").lower() == "true",
                timeout=int(os.getenv("EMAIL_TIMEOUT", "30")),
            )

        # Odoo configuration
        if os.getenv("ODOO_URL"):
            config.odoo = OdooConfig(
                url=os.getenv("ODOO_URL"),
                database=os.getenv("ODOO_DB"),
                username=os.getenv("ODOO_USERNAME"),
                password=os.getenv("ODOO_PASSWORD"),
                timeout=int(os.getenv("ODOO_TIMEOUT", "30")),
                max_retries=int(os.getenv("ODOO_MAX_RETRIES", "3")),
            )

        # Social media configuration
        config.social_media = SocialMediaConfig(
            twitter_api_key=os.getenv("TWITTER_API_KEY"),
            twitter_api_secret=os.getenv("TWITTER_API_SECRET"),
            twitter_access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            twitter_access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
            twitter_bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            facebook_page_id=os.getenv("FACEBOOK_PAGE_ID"),
            facebook_access_token=os.getenv("FACEBOOK_ACCESS_TOKEN"),
            facebook_app_id=os.getenv("FACEBOOK_APP_ID"),
            facebook_app_secret=os.getenv("FACEBOOK_APP_SECRET"),
            instagram_user_id=os.getenv("INSTAGRAM_USER_ID"),
            instagram_access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN"),
            instagram_client_id=os.getenv("INSTAGRAM_CLIENT_ID"),
            instagram_client_secret=os.getenv("INSTAGRAM_CLIENT_SECRET"),
            linkedin_client_id=os.getenv("LINKEDIN_CLIENT_ID"),
            linkedin_client_secret=os.getenv("LINKEDIN_CLIENT_SECRET"),
            linkedin_access_token=os.getenv("LINKEDIN_ACCESS_TOKEN"),
            linkedin_company_id=os.getenv("LINKEDIN_COMPANY_ID"),
        )

        # Security configuration
        config.security = SecurityConfig(
            secret_key=os.getenv("SECRET_KEY"),
            jwt_secret_key=os.getenv("JWT_SECRET_KEY"),
            jwt_expiration_hours=int(os.getenv("JWT_EXPIRATION_HOURS", "24")),
            api_key_header=os.getenv("API_KEY_HEADER", "X-API-Key"),
        )

        # Monitoring configuration
        config.monitoring = MonitoringConfig(
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "60")),
            circuit_breaker_threshold=int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5")),
            circuit_breaker_timeout=int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "300")),
            max_retry_attempts=int(os.getenv("MAX_RETRY_ATTEMPTS", "3")),
            retry_backoff_factor=float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0")),
            metrics_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            metrics_port=int(os.getenv("METRICS_PORT", "9090")),
        )

        # Performance configuration
        config.performance = PerformanceConfig(
            max_concurrent_tasks=int(os.getenv("MAX_CONCURRENT_TASKS", "10")),
            task_timeout_seconds=int(os.getenv("TASK_TIMEOUT_SECONDS", "300")),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "10")),
            rate_limit_requests_per_minute=int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100")),
        )

        # Paths configuration
        vault_path = Path(os.getenv("VAULT_PATH", "/Vault"))
        config.paths = PathsConfig(
            vault_path=vault_path,
            inbox_path=vault_path / "Inbox",
            needs_action_path=vault_path / "Needs_Action",
            pending_approval_path=vault_path / "Pending_Approval",
            approved_path=vault_path / "Approved",
            rejected_path=vault_path / "Rejected",
            done_path=vault_path / "Done",
            logs_path=vault_path / "Logs",
            reports_path=vault_path / "Reports",
            archive_path=vault_path / "Archive",
        )

        return config

    def get_config(self) -> AppConfig:
        """Get current configuration.

        Returns:
            Application configuration
        """
        if self._config is None:
            return self.load_config()
        return self._config

    def reload_config(self) -> AppConfig:
        """Reload configuration from environment.

        Returns:
            Reloaded application configuration
        """
        self._config = None
        return self.load_config()


# Global configuration instance
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """Get application configuration.

    Returns:
        Application configuration
    """
    return config_manager.get_config()


def reload_config() -> AppConfig:
    """Reload application configuration.

    Returns:
        Reloaded application configuration
    """
    return config_manager.reload_config()