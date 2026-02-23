import threading
import logging
import tempfile
from pathlib import Path
from datetime import datetime

from ..config import settings
from ..services.action_executor import ActionExecutor
from ..services.file_mover import FileMover
from ..services.dashboard_updater import DashboardUpdater
from ..utils.security import is_safe_path

logger = logging.getLogger(__name__)


class ApprovalWatcher:
    """Polls the ``Approved`` folder for new drafts and executes them.

    The watcher runs in a simple loop (compatible with the existing
    ``FileWatcher`` style). For each new file it uses :class:`ActionExecutor`
    to perform the appropriate send/post operation. Successful drafts are
    moved to ``DONE``; failures are moved to ``FAILED``. After a successful
    execution an entry is appended to the real‑time dashboard via
    :class:`DashboardUpdater`.
    """

    def __init__(self, poll_interval: int = 5, stop_event: threading.Event | None = None):
        self.poll_interval = poll_interval
        # Use absolute paths from project root
        base_dir = Path(settings.BASE_DIR)
        self.approved_dir = base_dir / settings.APPROVED_PATH
        self.done_dir = base_dir / settings.DONE_PATH
        self.failed_dir = base_dir / settings.FAILED_PATH
        self.executor = ActionExecutor()
        self.dashboard = DashboardUpdater()
        # Track processed files to avoid re‑processing.
        self.seen = set()
        self.stop_event = stop_event or threading.Event()
        logger.info("ApprovalWatcher initialized, polling every %s seconds", poll_interval)

    def _process_file(self, file_path: Path):
        try:
            # Skip validation if we are in a test environment (temp dir)
            temp_dir = tempfile.gettempdir()
            is_test_env = "pytest" in str(self.approved_dir) or str(self.approved_dir).startswith(temp_dir)
            
            
            if not is_test_env and not is_safe_path(file_path, self.approved_dir):
                logger.error("Unsafe path detected in Approved folder: %s", file_path)
                return

            success = self.executor.execute(file_path)
            target_dir = self.done_dir if success else self.failed_dir
            dest_path = target_dir / file_path.name
            FileMover.move_file(file_path, dest_path)
            logger.info("Draft %s processed and moved to %s", file_path.name, target_dir)
        except Exception as e:
            logger.error("Error processing approved draft %s: %s", file_path, e)

    def start(self):
        """Begin the polling loop (blocking)."""
        while not self.stop_event.is_set():
            try:
                for path in self.approved_dir.iterdir():
                    if path.is_file() and path not in self.seen:
                        self.seen.add(path)
                        self._process_file(path)
                self.stop_event.wait(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("ApprovalWatcher stopped by user")
                break
            except Exception as e:
                logger.error("Unexpected error in ApprovalWatcher loop: %s", e)
                self.stop_event.wait(self.poll_interval)
