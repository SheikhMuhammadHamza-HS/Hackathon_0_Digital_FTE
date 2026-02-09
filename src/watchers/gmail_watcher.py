import os
import logging
import base64
from pathlib import Path
from typing import List

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from ..config.settings import settings
from ..utils.file_utils import ensure_directory_exists
from ..utils.security import is_safe_path

logger = logging.getLogger(__name__)

class GmailWatcher:
    """Watches a Gmail inbox for unread messages and creates task files.

    This watcher polls the Gmail API at a configurable interval (default 60 seconds).
    For each unread message it creates a plain‑text file in the ``INBOX_PATH`` directory.
    The file name format is ``{message_id}.eml`` and the content is the raw email
    message (decoded from base64). After processing, the message is marked as read.
    """

    def __init__(self, poll_interval: int = 60):
        self.poll_interval = poll_interval
        self.creds = self._load_credentials()
        self.service = build('gmail', 'v1', credentials=self.creds)
        self.inbox_path = Path(settings.INBOX_PATH)
        ensure_directory_exists(self.inbox_path)
        logger.info("GmailWatcher initialized with poll interval %s seconds", self.poll_interval)

    def _load_credentials(self) -> Credentials:
        """Load Gmail OAuth2 credentials from environment variables.

        Expected env vars:
          - ``GMAIL_TOKEN`` – JSON string of the token
          - ``GMAIL_REFRESH_TOKEN`` – Refresh token (optional)
          - ``GMAIL_CLIENT_ID`` and ``GMAIL_CLIENT_SECRET`` – OAuth client info
        """
        token_json = os.getenv('GMAIL_TOKEN')
        if not token_json:
            raise RuntimeError('GMAIL_TOKEN environment variable not set')
        # In a real implementation we would parse the JSON and construct Credentials.
        # For this stub we assume the token JSON can be passed directly.
        return Credentials.from_authorized_user_info(info=eval(token_json))

    def poll_unread(self) -> List[Path]:
        """Fetch unread messages, write them to the inbox directory, and mark them read.

        Returns a list of ``Path`` objects pointing to the created files.
        """
        results = self.service.users().messages().list(userId='me', q='is:unread').execute()
        messages = results.get('messages', [])
        created_files = []
        for msg in messages:
            msg_id = msg['id']
            msg_detail = self.service.users().messages().get(userId='me', id=msg_id, format='raw').execute()
            raw_data = base64.urlsafe_b64decode(msg_detail['raw'])
            file_path = self.inbox_path / f"{msg_id}.eml"
            # Safety: ensure the file stays within INBOX_PATH
            if not is_safe_path(file_path, self.inbox_path):
                logger.warning("Unsafe path generated for message %s", msg_id)
                continue
            file_path.write_bytes(raw_data)
            created_files.append(file_path)
            # Mark as read
            self.service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
            logger.info("Processed Gmail message %s into %s", msg_id, file_path)
        return created_files

    def start(self):
        """Continuously poll Gmail at the configured interval.

        This method blocks; it can be run in a separate thread or process.
        """
        import time
        logger.info("Starting Gmail watcher loop")
        while True:
            try:
                self.poll_unread()
            except Exception as e:
                logger.error("Error while polling Gmail: %s", e)
            time.sleep(self.poll_interval)
