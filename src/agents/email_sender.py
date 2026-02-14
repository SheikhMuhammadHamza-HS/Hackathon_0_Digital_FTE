"""Email Sender using MCP Server architecture.

This module uses the email-mcp server to send emails instead of direct API calls.
"""

import logging
from pathlib import Path
from typing import Optional

from ..config import settings
from ..services.mcp_client import get_mcp_manager
from ..utils.security import is_safe_path

logger = logging.getLogger(__name__)


class EmailSender:
    """Sends email drafts via MCP email-mcp server.

    The implementation uses MCP (Model Context Protocol) to communicate with
    the email-mcp server, which handles the actual Gmail API interactions.

    Safety principles:
    * No hard-coded secrets – credentials are managed by the MCP server
    * Files are moved only within the project directory using is_safe_path
    * Falls back to mock mode if MCP server is unavailable
    """

    def __init__(self):
        """Initialize EmailSender with MCP client."""
        self.mcp_manager = get_mcp_manager()
        self.use_mcp = True

        # Check if MCP is available
        if not self.mcp_manager or not self.mcp_manager.clients:
            logger.warning("MCP configuration not found, will use mock mode")
            self.use_mcp = False

    def _parse_draft(self, draft_path: Path) -> dict:
        """Parse email draft file to extract headers and body.

        Args:
            draft_path: Path to the draft file

        Returns:
            Dictionary with 'to', 'subject', 'body', 'is_html' keys
        """
        content = draft_path.read_text(encoding="utf-8")

        result = {
            'to': '',
            'subject': 'No Subject',
            'body': '',
            'is_html': False
        }

        lines = content.splitlines()
        header_done = False

        for line in lines:
            if not header_done:
                if line.lower().startswith("to:"):
                    result['to'] = line.split(":", 1)[1].strip()
                elif line.lower().startswith("subject:"):
                    result['subject'] = line.split(":", 1)[1].strip()
                elif line.lower().startswith("content-type:"):
                    if 'text/html' in line.lower():
                        result['is_html'] = True
                elif not line.strip():
                    header_done = True
            else:
                result['body'] += line + '\n'

        # Clean up body
        result['body'] = result['body'].strip()

        return result

    def send_draft(self, draft_path: Path) -> bool:
        """Send the draft file via MCP email-mcp server.

        Args:
            draft_path: Absolute path to a markdown draft in APPROVED_PATH

        Returns:
            True on success (or mock success), False on failure
        """
        try:
            # Safety check
            base_dir = Path(settings.APPROVED_PATH)
            if not is_safe_path(draft_path, base_dir):
                logger.error("Unsafe draft path detected: %s", draft_path)
                return False

            # Parse the draft
            parsed = self._parse_draft(draft_path)

            if not parsed['to']:
                logger.error("No recipient found in draft: %s", draft_path)
                return False

            # Try MCP first
            if self.use_mcp:
                return self._send_via_mcp(parsed)

            # Fallback to mock mode
            return self._send_mock(parsed)

        except Exception as e:
            logger.error("Failed to send email draft %s: %s", draft_path, e)
            return False

    def _send_via_mcp(self, parsed: dict) -> bool:
        """Send email using MCP email-mcp server.

        Args:
            parsed: Parsed email data

        Returns:
            True on success, False on failure
        """
        try:
            client = self.mcp_manager.get_client('email-mcp')
            if not client:
                logger.warning("email-mcp client not available, falling back to mock mode")
                return self._send_mock(parsed)

            result = client.call_tool('send_email', {
                'to': parsed['to'],
                'subject': parsed['subject'],
                'body': parsed['body'],
                'is_html': parsed['is_html']
            })

            if result and 'content' in result:
                logger.info("Email sent via MCP: %s", result['content'][0]['text'])
                return True
            else:
                logger.error("MCP send_email returned unexpected result")
                return False

        except Exception as e:
            logger.error("Failed to send via MCP: %s", e)
            return False

    def _send_mock(self, parsed: dict) -> bool:
        """Mock send for development/testing without MCP.

        Args:
            parsed: Parsed email data

        Returns:
            True (mock success)
        """
        logger.info("MOCK MODE: Would send email to %s with subject '%s'",
                    parsed['to'], parsed['subject'])
        logger.debug("Email body preview: %s", parsed['body'][:200])
        return True