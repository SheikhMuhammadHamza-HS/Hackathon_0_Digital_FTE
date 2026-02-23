"""
Configuration utilities for AI Employee system
Provides backward compatibility for backup and other utilities
"""

import os
from pathlib import Path
from typing import Optional

class Config:
    """
    Simple configuration class for backward compatibility
    """

    def __init__(self):
        # Database configuration
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", "ai_employee/database/ai_employee.db")

        # Backup configuration
        self.BACKUP_DIRECTORY = os.getenv("BACKUP_DIRECTORY", "backups")

        # Configuration files
        self.CONFIG_PATH = os.getenv("CONFIG_PATH", "config.yaml")

        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

        # Security
        self.SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")

        # API settings
        self.API_HOST = os.getenv("API_HOST", "localhost")
        self.API_PORT = int(os.getenv("API_PORT", "8000"))

        # Environment
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

        # Data retention
        self.DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "730"))

        # Performance
        self.MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "10"))
        self.TASK_TIMEOUT_SECONDS = int(os.getenv("TASK_TIMEOUT_SECONDS", "300"))

        # Backup settings
        self.BACKUP_ENCRYPTION_ENABLED = os.getenv("BACKUP_ENCRYPTION_ENABLED", "true").lower() == "true"
        self.BACKUP_COMPRESSION_LEVEL = int(os.getenv("BACKUP_COMPRESSION_LEVEL", "6"))
        self.BACKUP_MAX_SIZE_GB = int(os.getenv("BACKUP_MAX_SIZE_GB", "10"))

        # Retention policies
        self.BACKUP_RETENTION_DAILY = int(os.getenv("BACKUP_RETENTION_DAILY", "7"))
        self.BACKUP_RETENTION_WEEKLY = int(os.getenv("BACKUP_RETENTION_WEEKLY", "28"))
        self.BACKUP_RETENTION_MONTHLY = int(os.getenv("BACKUP_RETENTION_MONTHLY", "365"))

        # Auto backup
        self.AUTO_BACKUP_ENABLED = os.getenv("AUTO_BACKUP_ENABLED", "true").lower() == "true"
        self.BACKUP_SCHEDULE_DAILY = os.getenv("BACKUP_SCHEDULE_DAILY", "0 2 * * *")
        self.BACKUP_SCHEDULE_WEEKLY = os.getenv("BACKUP_SCHEDULE_WEEKLY", "0 3 * * 0")
        self.BACKUP_SCHEDULE_MONTHLY = os.getenv("BACKUP_SCHEDULE_MONTHLY", "0 4 1 * *")

        # Paths
        self.VAULT_PATH = os.getenv("VAULT_PATH", "ai_employee/vault")
        self.LOGS_PATH = os.getenv("LOGS_PATH", "logs")
        self.MEDIA_PATH = os.getenv("MEDIA_PATH", "ai_employee/media")

    def ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            Path(self.BACKUP_DIRECTORY),
            Path(self.VAULT_PATH),
            Path(self.LOGS_PATH),
            Path(self.MEDIA_PATH),
            Path(self.DATABASE_PATH).parent
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT.lower() == "development"

# Global config instance
config = Config()