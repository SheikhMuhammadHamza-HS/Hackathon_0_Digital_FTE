import json
import os
from datetime import datetime
from pathlib import Path

class AuditLogger:
    """Simple audit logger that writes JSON entries to a daily log file.

    Log files are stored under ``/Vault/Logs`` with the name ``YYYY-MM-DD.json``.
    """

    def __init__(self, base_dir: str = "./Vault/Logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _log_path(self) -> Path:
        """Return the path for today's log file."""
        today = datetime.utcnow().date().isoformat()
        return self.base_dir / f"{today}.json"

    def log(self, event: str, data: dict | None = None) -> bool:
        """Append an audit entry.

        Args:
            event: Short string describing the event.
            data: Optional dictionary with additional details.
        Returns:
            ``True`` if the entry was written successfully.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "data": data or {},
        }
        try:
            log_file = self._log_path()
            # Write each entry as a separate JSON line (ndjson) for easy streaming
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            return True
        except Exception as e:
            # In production you might route this to a fallback logger;
            # here we simply signal failure.
            print(f"Audit log write failed: {e}")
            return False

# Convenience singleton for the application
audit_logger = AuditLogger()
