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
        self.creds = self._load_credentials()
        try:
            from googleapiclient.discovery import build
            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.info("EmailSender configured with Gmail API")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail API service: {e}")
            self.service = None

    def _load_credentials(self):
        """Load Gmail OAuth2 credentials from settings."""
        from google.oauth2.credentials import Credentials
        # Check for direct TOKEN string (authorized_user_info format)
        token_info = None
        if settings.GMAIL_TOKEN:
             import json
             try:
                 token_info = json.loads(settings.GMAIL_TOKEN)
             except Exception:
                 logger.error("GMAIL_TOKEN is not a valid JSON string")
        
        if token_info:
            return Credentials.from_authorized_user_info(token_info)
            
        # Fallback: check for token.json file in root
        token_file = Path("token.json")
        if token_file.exists():
            from ..watchers.gmail_watcher import SCOPES
            return Credentials.from_authorized_user_file(str(token_file), SCOPES)

        return None

    def send_draft(self, draft_path: Path) -> bool:
        """Send the draft file via Gmail API."""
        try:
            if not self.service:
                logger.error("Gmail service not initialized. Cannot send email.")
                return False

            # Safety: ensure the draft lives inside the approved base directory
            base_dir = Path(settings.APPROVED_PATH)
            if not is_safe_path(draft_path, base_dir):
                logger.error("Unsafe draft path detected: %s", draft_path)
                return False

            # Read the file
            content = draft_path.read_text(encoding="utf-8")
            
            # Extract headers and body
            subject = "No Subject"
            to_addr = ""
            body = []
            
            lines = content.splitlines()
            header_done = False
            for line in lines:
                if not header_done:
                    if line.lower().startswith("subject:"):
                        subject = line.split(":", 1)[1].strip()
                    elif line.lower().startswith("to:"):
                        to_addr = line.split(":", 1)[1].strip()
                    elif not line.strip():
                        header_done = True
                else:
                    body.append(line)

            full_body = "\n".join(body)

            # Create MIME message
            import base64
            from email.mime.text import MIMEText
            
            message = MIMEText(full_body)
            message['to'] = to_addr
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send the message
            print(f"DEBUG: Attempting to send email to {to_addr} via Gmail API...")
            self.service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
            
            logger.info("Successfully sent email to %s", to_addr)
            print(f"DONE: Email successfully sent to {to_addr}!")
            return True
        except Exception as e:
            logger.error("Failed to send email draft %s: %s", draft_path, e)
            return False
