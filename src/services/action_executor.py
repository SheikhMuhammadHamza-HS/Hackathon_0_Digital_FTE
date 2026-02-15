import logging
from pathlib import Path

from ..utils.file_utils import read_file_head
from ..agents.email_sender import EmailSender
from ..agents.linkedin_poster import LinkedInPoster
from ..agents.x_poster import XPoster
from ..agents.whatsapp_sender import WhatsAppSender
from ..services.dashboard_updater import DashboardUpdater

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Dispatches a pending draft to the appropriate sender based on its ``Platform`` header.

    The dispatcher reads the first few lines of the draft to locate the ``Platform:``
    field. Supported platforms are ``email`` and ``linkedin``. Unknown platforms are
    logged as errors and the draft is moved to the ``FAILED`` folder.
    """

    def __init__(self):
        self.email_sender = EmailSender()
        self.linkedin_poster = LinkedInPoster()
        self.x_poster = XPoster()
        self.whatsapp_sender = WhatsAppSender()

    def _extract_platform(self, draft_path: Path) -> str:
        """Return the platform value from the draft header.

        The function reads the first 10 lines to avoid loading large files.
        """
        try:
            header = read_file_head(draft_path, lines=10)
            for line in header.splitlines():
                if line.lower().startswith("platform:"):
                    return line.split(":", 1)[1].strip().lower()
        except Exception as e:
            logger.error("Error reading platform header from %s: %s", draft_path, e)
        return ""

    def execute(self, draft_path: Path) -> bool:
        """Execute the appropriate action for the draft.

        Returns ``True`` if the action succeeded, ``False`` otherwise.
        """
        platform = self._extract_platform(draft_path)
        if platform == "email":
            logger.info("Executing EmailSender for %s", draft_path.name)
            result = self.email_sender.send_draft(draft_path)
            dashboard = DashboardUpdater()
            dashboard.append_entry("Email draft sent", "SUCCESS" if result else "FAILURE")
            return result
        elif platform == "linkedin":
            logger.info("Executing LinkedInPoster for %s", draft_path.name)
            result = self.linkedin_poster.post_draft(draft_path)
            dashboard = DashboardUpdater()
            dashboard.append_entry("LinkedIn draft posted", "SUCCESS" if result else "FAILURE")
            return result
        elif platform in ["x", "twitter"]:
            logger.info("Executing XPoster for %s", draft_path.name)
            result = self.x_poster.post_draft(draft_path)
            dashboard = DashboardUpdater()
            dashboard.append_entry("X/Twitter draft posted", "SUCCESS" if result else "FAILURE")
            return result
        elif platform == "whatsapp":
            logger.info("Executing WhatsAppSender for %s", draft_path.name)
            result = self.whatsapp_sender.send_draft(draft_path)
            dashboard = DashboardUpdater()
            dashboard.append_entry("WhatsApp draft sent", "SUCCESS" if result else "FAILURE")
            return result
        elif platform == "file_action":
            logger.info("Executing file_action (logging only) for %s", draft_path.name)
            dashboard = DashboardUpdater()
            dashboard.append_entry(f"Action executed: {draft_path.name}", "SUCCESS")
            return True
        else:
            logger.error("Unsupported or missing platform in draft %s", draft_path)
            return False
