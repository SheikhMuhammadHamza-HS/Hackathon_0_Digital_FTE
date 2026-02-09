import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv(dotenv_path=BASE_DIR / ".env.example")

class Settings:
    """Configuration loaded from environment variables."""

    def __init__(self):
        # API keys (required for some agents)
        self.CLAUDE_CODE_API_KEY: str = os.getenv("CLAUDE_CODE_API_KEY", "")
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

        # Directory and file paths
        self.INBOX_PATH: str = os.getenv("INBOX_PATH", "./Inbox")
        self.NEEDS_ACTION_PATH: str = os.getenv("NEEDS_ACTION_PATH", "./Needs_Action")
        self.DONE_PATH: str = os.getenv("DONE_PATH", "./Done")
        self.FAILED_PATH: str = os.getenv("FAILED_PATH", "./Failed")
        self.PENDING_APPROVAL_PATH: str = os.getenv("PENDING_APPROVAL_PATH", "./Pending_Approval")
        self.APPROVED_PATH: str = os.getenv("APPROVED_PATH", "./Approved")
        self.LOGS_PATH: str = os.getenv("LOGS_PATH", "./Logs")
        self.DASHBOARD_PATH: str = os.getenv("DASHBOARD_PATH", "./Dashboard.md")
        self.COMPANY_HANDBOOK_PATH: str = os.getenv("COMPANY_HANDBOOK_PATH", "./Company_Handbook.md")
        self.AGENT_STATE_PATH: str = os.getenv("AGENT_STATE_PATH", "./agent_state.json")

        # Operational limits
        self.FILE_SIZE_LIMIT: int = int(os.getenv("FILE_SIZE_LIMIT", "10485760"))  # 10 MiB
        self.MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
        self.FILE_DETECTION_LATENCY: float = float(os.getenv("FILE_DETECTION_LATENCY", "5.0"))

    def validate(self) -> list:
        """Validate configuration values.
        Returns a list of error strings; empty list means valid.
        """
        errors = []
        path_attrs = [
            "INBOX_PATH",
            "NEEDS_ACTION_PATH",
            "DONE_PATH",
            "PENDING_APPROVAL_PATH",
            "APPROVED_PATH",
            "LOGS_PATH",
            "DASHBOARD_PATH",
            "COMPANY_HANDBOOK_PATH",
        ]
        for attr in path_attrs:
            val = getattr(self, attr, None)
            if not isinstance(val, (str, Path)) or not str(val).strip():
                errors.append(f"{attr} must be a non‑empty string or path")
            elif attr.endswith("_PATH") and attr not in ["DASHBOARD_PATH", "COMPANY_HANDBOOK_PATH"]:
                 # Ensure base paths are valid strings (tests might pass Paths)
                 pass

        # API key requirement (satisfies test_cli_commands and Claude's requirement)
        if not self.CLAUDE_CODE_API_KEY and not self.GEMINI_API_KEY:
            errors.append("CLAUDE_CODE_API_KEY is required")
            errors.append("GEMINI_API_KEY is required")
        
        return errors

# Global settings instance
settings = Settings()

# Module-level attributes for easier access/testing
CLAUDE_CODE_API_KEY = settings.CLAUDE_CODE_API_KEY
GEMINI_API_KEY = settings.GEMINI_API_KEY
INBOX_PATH = settings.INBOX_PATH
NEEDS_ACTION_PATH = settings.NEEDS_ACTION_PATH
DONE_PATH = settings.DONE_PATH
PENDING_APPROVAL_PATH = settings.PENDING_APPROVAL_PATH
APPROVED_PATH = settings.APPROVED_PATH
LOGS_PATH = settings.LOGS_PATH
DASHBOARD_PATH = settings.DASHBOARD_PATH
COMPANY_HANDBOOK_PATH = settings.COMPANY_HANDBOOK_PATH
FILE_SIZE_LIMIT = settings.FILE_SIZE_LIMIT
MAX_RETRY_ATTEMPTS = settings.MAX_RETRY_ATTEMPTS
FILE_DETECTION_LATENCY = settings.FILE_DETECTION_LATENCY
