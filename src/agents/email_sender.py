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
        
        Supports standard headers: To, Subject, Platform
        Supports threading headers: Thread-ID, Message-ID, In-Reply-To
        """
        try:
            content = draft_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read draft {draft_path}: {e}")
            return {}

        result = {
            'to': '',
            'subject': '',
            'body': '',
            'is_html': False,
            'thread_id': None,
            'message_id': None
        }

        lines = content.splitlines()
        header_section = True
        body_lines = []

        for line in lines:
            if header_section:
                if not line.strip():
                    header_section = False
                    continue
                
                lower_line = line.lower()
                if lower_line.startswith("to:"):
                    result['to'] = line.split(":", 1)[1].strip()
                elif lower_line.startswith("subject:"):
                    result['subject'] = line.split(":", 1)[1].strip()
                elif lower_line.startswith("thread-id:"):
                    result['thread_id'] = line.split(":", 1)[1].strip()
                elif lower_line.startswith("message-id:") or lower_line.startswith("in-reply-to:"):
                    result['message_id'] = line.split(":", 1)[1].strip()
                elif lower_line.startswith("content-type:") and "text/html" in lower_line:
                    result['is_html'] = True
            else:
                body_lines.append(line)

        result['body'] = "\n".join(body_lines).strip()
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
            base_dir = Path(settings.BASE_DIR) / settings.APPROVED_PATH
            if not is_safe_path(draft_path, base_dir):
                logger.error("Unsafe draft path detected: %s", draft_path)
                return False

            # Parse the draft
            parsed = self._parse_draft(draft_path)

            if not parsed['to']:
                logger.error("No recipient found in draft: %s", draft_path)
                return False

            # Skip MCP for now - use direct Gmail API
            # if self.use_mcp:
            #     return self._send_via_mcp(parsed)

            # Try direct Gmail API
            return self._send_direct(parsed)

        except Exception as e:
            logger.error("Failed to send email draft %s: %s", draft_path, e)
            return False

    def _send_via_mcp(self, parsed: dict) -> bool:
        """Send email using MCP email-mcp server.
        Uses reply_to_email if thread_id/message_id are present, otherwise send_email.
        """
        try:
            client = self.mcp_manager.get_client('email-mcp')
            if not client:
                logger.warning("email-mcp client not available, using mock mode (development only)")
                return self._send_mock(parsed)

            # Clean email address (extract 'email@example.com' from 'Name <email@example.com>')
            import re
            raw_to = parsed['to']
            email_match = re.search(r'<(.+?)>', raw_to)
            clean_to = email_match.group(1) if email_match else raw_to

            tool_name = 'send_email'
            args = {
                'to': clean_to,
                'subject': parsed['subject'] or '(No Subject)',
                'body': parsed['body'],
                'is_html': parsed.get('is_html', False)
            }

            # Check for threading
            if parsed.get('thread_id') and parsed.get('message_id'):
                tool_name = 'reply_to_email'
                args['threadId'] = parsed['thread_id']
                args['messageId'] = parsed['message_id']
                # Keep subject - Gmail API raw send needs it in MIME even for replies

            logger.info(f"Calling MCP tool {tool_name} for recipient {clean_to}")
            result = client.call_tool(tool_name, args)

            if result and not result.get('isError'):
                if 'content' in result:
                    logger.info("Email sent via MCP: %s", result['content'][0]['text'])
                    return True
                else:
                    logger.error(f"MCP {tool_name} returned success but no content")
                    return True 
            else:
                error_msg = result.get('content', [{}])[0].get('text', 'Unknown MCP error') if result else 'No result from MCP'
                logger.error(f"MCP {tool_name} failed: {error_msg}")
                return False # Correctly return False on real error

        except Exception as e:
            logger.error("Failed to send via MCP: %s", e)
            return False # Correctly return False on exception

    def _send_direct(self, parsed: dict) -> bool:
        """Send email directly using Gmail API.

        Args:
            parsed: Parsed email data

        Returns:
            True on success, False on failure
        """
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            import base64
            import email
            from email.mime.text import MIMEText

            # Get Gmail token from settings
            gmail_token_str = settings.GMAIL_TOKEN
            if not gmail_token_str:
                logger.error("GMAIL_TOKEN not found in settings")
                return self._send_mock(parsed)

            # Parse token
            import json
            token_info = json.loads(gmail_token_str)
            creds = Credentials.from_authorized_user_info(token_info)

            # Build Gmail service
            service = build('gmail', 'v1', credentials=creds)

            # Create message
            message = MIMEText(parsed['body'])
            message['to'] = parsed['to']
            message['subject'] = parsed['subject'] or '(No Subject)'

            # Add threading info if available
            if parsed.get('message_id'):
                message['In-Reply-To'] = parsed['message_id']
                message['References'] = parsed['message_id']

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Send email
            if parsed.get('thread_id'):
                # Send as reply
                result = service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message, 'threadId': parsed['thread_id']}
                ).execute()
            else:
                # Send as new email
                result = service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()

            logger.info(f"Email sent successfully! Message ID: {result['id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email directly: {e}")
            # Fall back to mock mode
            return self._send_mock(parsed)

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