import threading
import os
from pathlib import Path
from datetime import datetime
import json

from ..config import settings
from ..utils.file_utils import ensure_directory_exists

import logging

logger = logging.getLogger(__name__)

_lock = threading.Lock()


class DashboardUpdater:
    """Append entries to the Dashboard markdown file in a thread‑safe, efficient way.

    Each entry is written as a markdown table row with three columns:
    Time | Task | Status

    When the file exceeds ``MAX_SIZE_BYTES`` it is rotated: the current file is renamed
    with a timestamp suffix and a new empty dashboard file is created.
    """

    MAX_SIZE_BYTES = 1 * 1024 * 1024  # 1 MiB – rotate before it gets large

    def __init__(self, dashboard_path: str | Path = None):
        self.dashboard_path = Path(dashboard_path) if dashboard_path else Path(settings.DASHBOARD_PATH)
        ensure_directory_exists(self.dashboard_path.parent)
        # Ensure the file exists and has a header
        if not self.dashboard_path.exists():
            self._initialize_file()

    def _initialize_file(self):
        header = "| Time | Task | Status |\n|---|---|---|\n"
        with open(self.dashboard_path, "w", encoding="utf-8") as f:
            f.write(header)
        logger.info("Dashboard initialized at %s", self.dashboard_path)

    def _rotate_if_necessary(self):
        try:
            if self.dashboard_path.stat().st_size >= self.MAX_SIZE_BYTES:
                timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                archive_name = self.dashboard_path.with_name(f"Dashboard_{timestamp}.md")
                self.dashboard_path.rename(archive_name)
                logger.info("Dashboard rotated to %s", archive_name)
                self._initialize_file()
        except Exception as e:
            logger.error("Failed to rotate dashboard: %s", e)

    def append_entry(self, task: str, status: str):
        """Append a single row to the dashboard.

        Parameters
        ----------
        task: str
            Human‑readable description of the task (e.g., "Email draft sent").
        status: str
            Outcome status, typically "SUCCESS" or "FAILURE".
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
        row = f"| {timestamp} | {task} | {status} |\n"
        with _lock:
            try:
                self._rotate_if_necessary()
                with open(self.dashboard_path, "a", encoding="utf-8") as f:
                    f.write(row)
                    f.flush()
                    os.fsync(f.fileno())
                logger.info("Dashboard entry added: %s", row.strip())
            except Exception as e:
                logger.error("Failed to append to dashboard: %s", e)
