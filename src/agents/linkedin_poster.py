"""LinkedIn Poster using MCP Server architecture.

This module uses the linkedin-mcp server to post LinkedIn content instead of
direct API calls.
"""

import logging
from pathlib import Path

from ..config import settings
from ..services.mcp_client import get_mcp_manager
from ..utils.security import is_safe_path

logger = logging.getLogger(__name__)


class LinkedInPoster:
    """Posts LinkedIn drafts via MCP linkedin-mcp server.

    The implementation uses MCP (Model Context Protocol) to communicate with
    the linkedin-mcp server, which handles the actual LinkedIn API interactions.

    Safety principles:
    * No hard-coded secrets – credentials are managed by the MCP server
    * Files are moved only within the project directory using is_safe_path
    * Falls back to mock mode if MCP server is unavailable
    """

    def __init__(self):
        """Initialize LinkedInPoster with MCP client."""
        self.mcp_manager = get_mcp_manager()
        self.use_mcp = True

        # Check if MCP is available
        if not self.mcp_manager or not self.mcp_manager.clients:
            logger.warning("MCP configuration not found, will use mock mode")
            self.use_mcp = False

    def _parse_draft(self, draft_path: Path) -> dict:
        """Parse LinkedIn draft file to extract post content and visibility.

        Args:
            draft_path: Path to the draft file

        Returns:
            Dictionary with 'text' and 'visibility' keys
        """
        content = draft_path.read_text(encoding="utf-8")

        result = {
            'text': '',
            'visibility': 'PUBLIC'
        }

        lines = content.splitlines()
        header_done = False

        for line in lines:
            if not header_done:
                if line.lower().startswith("visibility:"):
                    result['visibility'] = line.split(":", 1)[1].strip().upper()
                elif not line.strip():
                    header_done = True
            else:
                result['text'] += line + '\n'

        # Clean up text
        result['text'] = result['text'].strip()

        return result

    def post_draft(self, draft_path: Path) -> bool:
        """Post the LinkedIn draft via MCP linkedin-mcp server.

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

            if not parsed['text']:
                logger.error("No content found in LinkedIn draft: %s", draft_path)
                return False

            # Try MCP first
            if self.use_mcp:
                return self._post_via_mcp(parsed)

            # Fallback to mock mode
            return self._post_mock(parsed)

        except Exception as e:
            logger.error("Failed to post LinkedIn draft %s: %s", draft_path, e)
            return False

    def _post_via_mcp(self, parsed: dict) -> bool:
        """Post LinkedIn content using MCP linkedin-mcp server.

        Args:
            parsed: Parsed LinkedIn post data

        Returns:
            True on success, False on failure
        """
        try:
            client = self.mcp_manager.get_client('linkedin-mcp')
            if not client:
                logger.warning("linkedin-mcp client not available, falling back to mock mode")
                return self._post_mock(parsed)

            result = client.call_tool('create_post', {
                'text': parsed['text'],
                'visibility': parsed['visibility']
            })

            if result and 'content' in result:
                logger.info("LinkedIn post created via MCP: %s", result['content'][0]['text'])
                return True
            else:
                logger.error("MCP create_post returned unexpected result")
                return False

        except Exception as e:
            logger.error("Failed to post via MCP: %s", e)
            return False

    def _post_mock(self, parsed: dict) -> bool:
        """Mock post for development/testing without MCP.

        Args:
            parsed: Parsed LinkedIn post data

        Returns:
            True (mock success)
        """
        logger.info("MOCK MODE: Would post to LinkedIn with visibility %s",
                    parsed['visibility'])
        logger.debug("Post content preview: %s", parsed['text'][:200])
        return True