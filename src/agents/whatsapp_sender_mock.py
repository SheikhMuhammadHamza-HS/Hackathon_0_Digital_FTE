"""
Mock WhatsApp Sender - Simulates sending messages for testing.

No browser automation, no API calls - just logs what would be sent.
For production, replace with real MCP sender.
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from ..config.settings import settings
from ..utils.file_utils import ensure_directory_exists

logger = logging.getLogger(__name__)


class WhatsAppSenderMock:
    """Mock WhatsApp sender for testing the flow without real sends."""

    def __init__(self):
        self.sent_log_path = Path(settings.LOGS_PATH) / "mock_sent_messages.log"
        ensure_directory_exists(self.sent_log_path.parent)

    def send_draft(self, draft_path: Path) -> bool:
        """Simulate sending a WhatsApp draft.

        Args:
            draft_path: Path to approved draft file

        Returns:
            True (simulated success)
        """
        try:
            # Parse the draft
            parsed = self._parse_draft(draft_path)

            recipient = parsed.get('to', 'Unknown')
            message = parsed.get('body', '')

            # Validate
            if not recipient or recipient == 'Unknown':
                logger.error("❌ No recipient found in draft")
                return False

            if not message:
                logger.error("❌ No message body found")
                return False

            # Simulate sending
            logger.info("=" * 60)
            logger.info("MOCK WHATSAPP SEND")
            logger.info("=" * 60)
            logger.info(f"To: {recipient}")
            logger.info(f"Message ({len(message)} chars):")
            logger.info(f"  {message[:100]}{'...' if len(message) > 100 else ''}")
            logger.info("=" * 60)
            logger.info("SUCCESS: Message sent (MOCK MODE)")
            logger.info("=" * 60)

            # Log to file
            self._log_sent_message(recipient, message)

            return True

        except Exception as e:
            logger.error(f"❌ Mock send failed: {e}")
            return False

    def _parse_draft(self, draft_path: Path) -> Dict[str, Any]:
        """Parse draft file for recipient and message."""
        content = draft_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        metadata = {
            'to': '',
            'body': '',
            'platform': 'whatsapp'
        }

        # Parse headers
        in_body = False
        body_lines = []

        for line in lines:
            stripped = line.strip()

            # Skip frontmatter markers
            if stripped == '---':
                continue

            # Parse headers
            if not in_body:
                if stripped.lower().startswith('to:'):
                    metadata['to'] = stripped.split(':', 1)[1].strip()
                elif stripped.lower().startswith('platform:'):
                    metadata['platform'] = stripped.split(':', 1)[1].strip()
                elif stripped == '':
                    in_body = True
                elif stripped.startswith('#'):
                    in_body = True
                    body_lines.append(line)
            else:
                body_lines.append(line)

        # Extract body (remove markdown formatting)
        body = '\n'.join(body_lines).strip()

        # Remove "Response to..." header if present
        if body.startswith('## Response to'):
            body = '\n'.join(body.split('\n')[2:]).strip()

        # Remove separator lines
        body = body.replace('---', '').strip()

        metadata['body'] = body

        return metadata

    def _log_sent_message(self, recipient: str, message: str):
        """Log sent message to file."""
        timestamp = datetime.now().isoformat()
        log_entry = f"""
{'='*60}
Time: {timestamp}
To: {recipient}
Message: {message[:200]}{'...' if len(message) > 200 else ''}
Status: MOCK_SEND_SUCCESS
{'='*60}
"""
        with open(self.sent_log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

        logger.debug(f"Logged mock send to {self.sent_log_path}")
