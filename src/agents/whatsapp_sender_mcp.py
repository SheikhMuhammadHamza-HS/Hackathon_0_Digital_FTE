"""
Real WhatsApp Sender using MCP WhatsApp Business API.

Uses the official Meta WhatsApp Business API via MCP server.
No browser automation - direct API calls.

Required env vars:
- WHATSAPP_PHONE_NUMBER_ID
- WHATSAPP_ACCESS_TOKEN
"""
import logging
import json
import subprocess
from pathlib import Path
from typing import Dict, Any

from ..config.settings import settings

logger = logging.getLogger(__name__)


class WhatsAppSenderMCP:
    """Real WhatsApp sender using MCP WhatsApp Business API."""

    def __init__(self):
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID or ""
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN or ""
        self.mcp_server_path = Path(__file__).parent.parent.parent / "mcp-servers" / "whatsapp-mcp"

    def send_draft(self, draft_path: Path) -> bool:
        """Send WhatsApp message using real API.

        Args:
            draft_path: Path to approved draft file

        Returns:
            True if sent successfully
        """
        try:
            # Check credentials
            if not self.phone_number_id or not self.access_token:
                logger.error("Missing WhatsApp credentials in .env file")
                logger.error("Required: WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN")
                return False

            # Parse the draft
            parsed = self._parse_draft(draft_path)
            recipient = parsed.get('to', '')
            message = parsed.get('body', '')

            if not recipient:
                logger.error("No recipient found in draft")
                return False

            if not message:
                logger.error("No message body found")
                return False

            # Format recipient (remove + and spaces for API)
            recipient_clean = recipient.replace('+', '').replace(' ', '')

            logger.info("=" * 60)
            logger.info("REAL WHATSAPP SEND via API")
            logger.info("=" * 60)
            logger.info(f"To: {recipient}")
            logger.info(f"Message: {message[:100]}{'...' if len(message) > 100 else ''}")
            logger.info("=" * 60)

            # Send via MCP server
            result = self._send_via_mcp(recipient_clean, message)

            if result:
                logger.info("SUCCESS: WhatsApp message sent!")
                logger.info(f"Recipient: {recipient}")
                logger.info(f"Message ID: {result.get('messages', [{}])[0].get('id', 'N/A')}")
            else:
                logger.error("FAILED: Could not send WhatsApp message")

            logger.info("=" * 60)
            return result is not None

        except Exception as e:
            logger.error(f"Error sending WhatsApp: {e}")
            import traceback
            logger.error(traceback.format_exc())
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

        # Parse YAML frontmatter
        in_frontmatter = False
        frontmatter_end = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            if stripped == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    frontmatter_end = i
                    break
            elif in_frontmatter and ':' in stripped:
                key, value = stripped.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                if key == 'to':
                    metadata['to'] = value

        # Extract body (after frontmatter)
        body_lines = []
        in_body = False

        for line in lines[frontmatter_end + 1:]:
            stripped = line.strip()

            # Skip markdown headers
            if stripped.startswith('## Response'):
                continue
            if stripped == '---':
                in_body = False
                continue
            if stripped.startswith('**To Approve'):
                break

            if stripped or in_body:
                body_lines.append(line)
                in_body = True

        # Clean up body
        body = '\n'.join(body_lines).strip()
        # Remove markdown
        body = body.replace('---', '').strip()

        metadata['body'] = body

        return metadata

    def _send_via_mcp(self, to: str, body: str) -> Dict[str, Any]:
        """Send message via MCP WhatsApp server using direct API call."""
        import requests

        api_version = "v21.0"
        url = f"https://graph.facebook.com/{api_version}/{self.phone_number_id}/messages"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": body
            }
        }

        try:
            logger.info(f"Sending API request to Meta WhatsApp...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                logger.info(f"API Response: Success")
                return result
            else:
                logger.error(f"API Error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for WhatsApp API."""
        # Remove all non-numeric characters
        cleaned = ''.join(c for c in phone if c.isdigit())

        # If no country code, add default (Pakistan: 92)
        if len(cleaned) == 10:  # e.g., 3001234567
            cleaned = "92" + cleaned

        return cleaned
