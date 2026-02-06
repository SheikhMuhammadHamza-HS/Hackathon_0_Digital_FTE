import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings loaded from environment variables."""

    # API Configuration
    CLAUDE_CODE_API_KEY: str = os.getenv("CLAUDE_CODE_API_KEY", "")  # Kept for backward compatibility
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")  # New Gemini API key

    # Directory Configuration
    INBOX_PATH: Path = Path(os.getenv("INBOX_PATH", "./Inbox"))
    NEEDS_ACTION_PATH: Path = Path(os.getenv("NEEDS_ACTION_PATH", "./Needs_Action"))
    DONE_PATH: Path = Path(os.getenv("DONE_PATH", "./Done"))
    LOGS_PATH: Path = Path(os.getenv("LOGS_PATH", "./Logs"))
    DASHBOARD_PATH: Path = Path(os.getenv("DASHBOARD_PATH", "./Dashboard.md"))
    COMPANY_HANDBOOK_PATH: Path = Path(os.getenv("COMPANY_HANDBOOK_PATH", "./Company_Handbook.md"))

    # File Processing Configuration
    FILE_SIZE_LIMIT: int = int(os.getenv("FILE_SIZE_LIMIT", "10485760"))  # 10MB default
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))

    # Performance Configuration
    FILE_DETECTION_LATENCY: float = 5.0  # 5 seconds default detection latency

    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration settings and return list of errors."""
        errors = []

        # Check if at least one API key is provided for AI processing
        # The agent can still monitor files without an API key, but won't be able to process them
        if not cls.CLAUDE_CODE_API_KEY and not cls.GEMINI_API_KEY:
            # We'll log this as a warning rather than an error to allow basic file monitoring
            pass  # Allow operation without API key for monitoring-only mode

        # Validate directory paths exist or can be created
        dirs_to_check = [
            cls.INBOX_PATH,
            cls.NEEDS_ACTION_PATH,
            cls.DONE_PATH,
            cls.LOGS_PATH
        ]

        for dir_path in dirs_to_check:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create/access directory {dir_path}: {str(e)}")

        # Validate file size limit is positive
        if cls.FILE_SIZE_LIMIT <= 0:
            errors.append("FILE_SIZE_LIMIT must be greater than 0")

        # Validate retry attempts is non-negative
        if cls.MAX_RETRY_ATTEMPTS < 0:
            errors.append("MAX_RETRY_ATTEMPTS must be non-negative")

        return errors

# Global settings instance
settings = Settings()