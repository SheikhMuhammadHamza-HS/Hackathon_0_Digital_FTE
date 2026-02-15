import os
import logging
import base64
from pathlib import Path
from typing import List
from datetime import datetime

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from ..config.settings import settings
from ..utils.file_utils import ensure_directory_exists
from ..utils.security import is_safe_path
from ..agents.email_processor import EmailProcessor
from ..models.trigger_file import TriggerFile

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

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
        self.needs_action_path = Path(settings.NEEDS_ACTION_PATH)
        ensure_directory_exists(self.needs_action_path)
        self.email_processor = EmailProcessor()
        logger.info("GmailWatcher initialized (Polled every %s sec)", self.poll_interval)

    def _load_credentials(self) -> Credentials:
        """Load Gmail OAuth2 credentials from settings."""
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
            return Credentials.from_authorized_user_file(str(token_file), SCOPES)

        raise RuntimeError(
            "Gmail credentials not found. Set GMAIL_TOKEN env var or create token.json. "
            "See .clade/gmail-automation/SKILL.md for setup instructions."
        )

    def poll_unread(self, max_results: int = 5) -> List[Path]:
        """Fetch unread messages (up to max_results) and create .md tasks in Needs_Action."""
        try:
            results = self.service.users().messages().list(userId='me', q='is:unread', maxResults=max_results).execute()
            messages = results.get('messages', [])
            created_files = []
            
            for msg in messages:
                msg_id = msg['id']
                # Get message metadata and body
                msg_obj = self.service.users().messages().get(userId='me', id=msg_id).execute()
                payload = msg_obj.get('payload', {})
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
                date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
                
                thread_id = msg['threadId']
                
                # Extract full snippet or body if available
                snippet = msg_obj.get('snippet', '')
                
                # Prepare markdown content with YAML frontmatter
                timestamp = datetime.now().isoformat()
                content = f"""---
type: email
id: "{msg_id}"
thread_id: "{thread_id}"
message_id: "{msg_id}"
from: "{sender}"
subject: "{subject}"
received_at: "{date_str}"
detected_at: "{timestamp}"
status: pending
---
## Email Content
{snippet}

## Threading Info
Thread-ID: {thread_id}
Message-ID: {msg_id}

## Actions Required
- [ ] Draft a reply
- [ ] Archive email
"""
                file_path = self.needs_action_path / f"GMAIL_{msg_id}.md"
                
                # Safety: ensure the file stays within needs_action_path
                if not is_safe_path(str(file_path), str(self.needs_action_path)):
                    logger.warning("Unsafe path blocked for message %s", msg_id)
                    continue
                    
                file_path.write_text(content, encoding='utf-8')
                created_files.append(file_path)
                
                # Mark as read (optional - PDF says mark once processed, but here we detect)
                # To avoid re-detecting, we must mark as read or track seen IDs
                self.service.users().messages().modify(
                    userId='me', 
                    id=msg_id, 
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                
                logger.info("Created Gmail task: %s", file_path.name)
                
                # Trigger processing for the new Gmail task
                try:
                    from ..models.trigger_file import TriggerStatus
                    trigger_file = TriggerFile(
                        id=msg_id,
                        filename=file_path.name,
                        type="email",
                        source_path=str(file_path),
                        status=TriggerStatus.PENDING,
                        timestamp=datetime.now(),
                        location=str(file_path)
                    )
                    self.email_processor.process_trigger_file(trigger_file)
                except Exception as pe:
                    logger.error("Failed to process Gmail task %s: %s", msg_id, pe)
                
            return created_files
        except Exception as e:
            logger.error("Gmail poll failed: %s", e)
            return []

    def start(self):
        """Blocking loop for polling."""
        import time
        logger.info("Gmail watcher started.")
        while True:
            try:
                self.poll_unread()
            except Exception as e:
                logger.error("Watcher loop error: %s", e)
            time.sleep(self.poll_interval)
