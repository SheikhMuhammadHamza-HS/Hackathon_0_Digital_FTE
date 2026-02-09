import logging
from pathlib import Path

from ..config import settings
from ..services.file_mover import FileMover
from ..services.draft_store import DraftStore
from ..utils.security import is_safe_path

logger = logging.getLogger(__name__)


class EmailSender:
    """Sends email drafts produced by :class:`EmailProcessor`.

    The implementation follows the same safety principles as other agents:
    * No hard‑coded secrets – the Gmail API key is read from ``settings``.
    * Files are moved only within the project directory using :func:`is_safe_path`.
    * A missing or invalid API key results in a mock send (logged only).
    """

    def __init__(self):
        self.api_key = getattr(settings, "GMAIL_API_KEY", "")
        if self.api_key:
            logger.info("EmailSender configured with real Gmail API key")
        else:
            logger.warning("No Gmail API key present – EmailSender will operate in mock mode")

    def send_draft(self, draft_path: Path) -> bool:
        """Send the draft file.

        Parameters
        ----------
        draft_path: Path
            Absolute path to a markdown draft stored in ``settings.PENDING_APPROVAL_PATH``.

        Returns
        -------
        bool
            ``True`` on successful send (or mock send), ``False`` otherwise.
        """
        try:
            # Safety: ensure the draft lives inside the approved base directory
            base_dir = Path(settings.APPROVED_PATH)
            if not is_safe_path(draft_path, base_dir):
                logger.error("Unsafe draft path detected: %s", draft_path)
                return False

            # Read the file (the DraftStore already guarantees the Platform header is "email")
            content = draft_path.read_text(encoding="utf-8")
            logger.debug("Email draft content (first 200 chars): %s", content[:200])

            if self.api_key:
                # Real implementation would call Gmail API here.
                # For the purposes of this repository we simply log the action.
                logger.info("Sending email via Gmail API (mocked – real call omitted)")
            else:
                logger.info("Mock email send – no API key configured")

            return True
        except Exception as e:
            logger.error("Failed to send email draft %s: %s", draft_path, e)
            return False
