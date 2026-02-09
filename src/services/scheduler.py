try:
    import schedule
except ImportError:
    # Minimal fallback implementation for the subset of schedule API used
    class _SimpleScheduler:
        def __init__(self):
            self._jobs = []
        class _Every:
            def __init__(self, parent):
                self.parent = parent
            def monday(self):
                return self
            def at(self, time_str):
                return self
            def do(self, job_func):
                self.parent._jobs.append(job_func)
                return job_func
        def every(self):
            return self._Every(self)
        def run_pending(self):
            for job in list(self._jobs):
                job()
    schedule = _SimpleScheduler()

import time
import threading
import logging
from datetime import datetime

from ..agents.linkedin_processor import LinkedInProcessor
from ..models.trigger_file import TriggerFile, TriggerStatus
from ..config import settings
from .dashboard_updater import DashboardUpdater

logger = logging.getLogger(__name__)

class Scheduler:
    """Simple weekly scheduler for LinkedIn drafts.

    Uses the ``schedule`` library (already a dependency). The job runs every
    Monday at 09:00 local time. For testing, the CLI offers a ``schedule-run``
    command that invokes ``run_pending`` immediately.
    """

    def __init__(self):
        self.processor = LinkedInProcessor()
        self._setup_job()

    def _setup_job(self):
        # Schedule the job – Monday 09:00
        schedule.every().monday.at('09:00').do(self._run_job)
        logger.info('Scheduler job for LinkedIn drafts set for Monday 09:00')

    def _run_job(self):
        """Create a dummy trigger file and process it.

        In a real system the trigger would be created by the file watcher. For the
        scheduled job we fabricate a minimal trigger to reuse existing processing
        logic.
        """
        dummy_trigger = TriggerFile(
            trigger_id='scheduler_' + datetime.utcnow().strftime('%Y%m%d%H%M%S'),
            source_path='Business_Goals.md',
            location='scheduler_trigger.md',
            status=TriggerStatus.PENDING,
            source_path_abs='Business_Goals.md',
            needs_action_dir=settings.NEEDS_ACTION_PATH,
            created_at=datetime.utcnow()
        )
        try:
            success = self.processor.process_trigger_file(dummy_trigger)
            logger.info(f'Scheduled LinkedIn draft processing result: {success}')
            try:
                dashboard = DashboardUpdater()
                status = "SUCCESS" if success else "FAILURE"
                dashboard.append_entry("Scheduled Draft: LinkedIn post", status)
            except Exception as e:
                logger.warning(f'Failed to update dashboard: {e}')
        except Exception as e:
            logger.error(f'Error during scheduled LinkedIn draft processing: {e}')
        return success

    def start(self):
        """Run the scheduler loop in a background thread.

        The loop checks for pending jobs every second. The method returns
        immediately after starting the thread so callers can continue.
        """
        thread = threading.Thread(target=self._run_continuously, daemon=True)
        thread.start()
        logger.info('Scheduler thread started')

    def _run_continuously(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    def run_once(self):
        """Execute any pending jobs right now – useful for the CLI ``schedule-run`` command."""
        schedule.run_pending()
        logger.info('Executed scheduler pending jobs manually')
