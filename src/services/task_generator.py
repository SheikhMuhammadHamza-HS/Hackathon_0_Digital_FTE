import hashlib
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from ..config.settings import settings
from ..utils.file_utils import ensure_directory_exists
from ..services.dashboard_updater import DashboardUpdater

logger = logging.getLogger(__name__)

class TaskGenerator:
    """Generates task files in the ``Needs_Action`` folder.

    The generator creates a JSON file containing metadata about the source
    file (hash, timestamp, original path). Duplicate detection is performed
    by comparing the SHA‑256 hash of the file's contents with hashes of
    previously generated tasks.
    """

    def __init__(self):
        self.needs_action_path = Path(settings.NEEDS_ACTION_PATH)
        ensure_directory_exists(self.needs_action_path)

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        """Return a SHA‑256 hex digest of the file's contents."""
        hasher = hashlib.sha256()
        with file_path.open('rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _existing_hashes(self):
        """Yield hashes of all existing task files in ``Needs_Action``.

        Task files are expected to be JSON objects with a ``file_hash`` key.
        """
        for task_file in self.needs_action_path.glob('*.json'):
            try:
                data = json.loads(task_file.read_text())
                if 'file_hash' in data:
                    yield data['file_hash']
            except Exception as e:
                logger.warning("Failed to read task file %s: %s", task_file, e)

    def is_duplicate(self, file_path: Path) -> bool:
        """Check whether a file has already been turned into a task.

        Returns ``True`` if the file's hash matches any existing task hash.
        """
        file_hash = self._hash_file(file_path)
        return file_hash in set(self._existing_hashes())

    def create_task(self, source_path: Path) -> Path:
        """Create a task file for ``source_path``.

        The generated file is a JSON document named ``<timestamp>_<hash>.json``
        placed in ``NEEDS_ACTION_PATH``.
        """
        if not source_path.is_file():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        file_hash = self._hash_file(source_path)
        if self.is_duplicate(source_path):
            logger.info("Duplicate task detected for %s; skipping creation", source_path)
            return None

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        task_filename = f"{timestamp}_{file_hash[:8]}.json"
        task_path = self.needs_action_path / task_filename

        task_data = {
            "source_path": str(source_path),
            "created_at": timestamp,
            "file_hash": file_hash,
            "status": "pending"
        }
        task_path.write_text(json.dumps(task_data, indent=2))
        logger.info("Created task file %s for source %s", task_path, source_path)
        try:
            dashboard = DashboardUpdater()
            dashboard.append_entry(f"Task Created: {source_path.name}", "SUCCESS")
        except Exception as e:
            logger.warning(f"Failed to update dashboard: {e}")
        return task_path
