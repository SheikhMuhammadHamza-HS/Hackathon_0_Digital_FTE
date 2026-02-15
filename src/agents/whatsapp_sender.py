import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ..config.settings import settings
from ..services.mcp_client import get_mcp_manager
from ..utils.security import is_safe_path

logger = logging.getLogger(__name__)

class WhatsAppSender:
    """Agent responsible for sending WhatsApp messages via MCP."""

    def __init__(self):
        self.mcp_manager = get_mcp_manager()
        # Fallback to mock if MCP server is not configured or fails
        self.use_mcp = True

    def send_draft(self, draft_path: Path) -> bool:
        """Send the WhatsApp draft file via MCP whatsapp-mcp server.

        Args:
            draft_path: Absolute path to a markdown draft in APPROVED_PATH

        Returns:
            True on success, False on failure
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
                logger.error("No recipient found in WhatsApp draft: %s", draft_path)
                return False

            # Try MCP first
            if self.use_mcp:
                return self._send_via_mcp(parsed)

            # Fallback to mock mode
            return self._send_mock(parsed)

        except Exception as e:
            logger.error("Failed to send WhatsApp draft %s: %s", draft_path, e)
            return False

    def _parse_draft(self, draft_path: Path) -> Dict[str, Any]:
        """Extract metadata and body from the markdown draft."""
        content = draft_path.read_text(encoding='utf-8')
        lines = content.splitlines()
        
        metadata = {
            'to': '',
            'body': '',
            'platform': 'whatsapp'
        }
        
        body_start_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('To:'):
                metadata['to'] = line.split(':', 1)[1].strip()
            elif line.startswith('Platform:'):
                metadata['platform'] = line.split(':', 1)[1].strip()
            elif line.strip() == '':
                body_start_idx = i + 1
                break
        
        metadata['body'] = '\n'.join(lines[body_start_idx:]).strip()
        return metadata

    def _send_via_mcp(self, parsed: dict) -> bool:
        """Send WhatsApp message using MCP whatsapp-mcp server."""
        try:
            client = self.mcp_manager.get_client('whatsapp-mcp')
            if not client:
                logger.warning("whatsapp-mcp client not available, falling back to mock mode")
                return self._send_mock(parsed)

            tool_name = 'send_message'
            args = {
                'to': parsed['to'],
                'body': parsed['body']
            }

            logger.info(f"Calling MCP tool {tool_name} for recipient {args['to']}")
            result = client.call_tool(tool_name, args)

            if result and not result.get('isError'):
                if 'content' in result:
                    logger.info("WhatsApp message sent via MCP: %s", result['content'][0]['text'])
                    return True
                else:
                    logger.error(f"MCP {tool_name} returned success but no content")
                    return True
            else:
                error_msg = result.get('content', [{}])[0].get('text', 'Unknown MCP error') if result else 'No result from MCP'
                logger.error(f"MCP {tool_name} failed: {error_msg}")
                return False

        except Exception as e:
            logger.error("Failed to send via WhatsApp MCP: %s", e)
            return False

    def _send_mock(self, parsed: dict) -> bool:
        """Mock sending WhatsApp message (for development/testing)."""
        logger.info("[MOCK] Sending WhatsApp message to %s", parsed['to'])
        logger.info("[MOCK] Body: %s", parsed['body'][:50] + "...")
        print(f"📱 [MOCK] WhatsApp sent to {parsed['to']}")
        return True
