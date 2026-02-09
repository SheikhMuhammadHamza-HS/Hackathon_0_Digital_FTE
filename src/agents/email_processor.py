import time
import json
from pathlib import Path

import google.generativeai as genai

from ..config import settings
from ..models.trigger_file import TriggerFile, TriggerStatus
from ..exceptions import ClaudeCodeIntegrationException
from ..config.logging_config import get_logger

from ..utils.handbook_loader import load_handbook

logger = get_logger(__name__)


class EmailProcessor:
    """Processes email‑task trigger files and generates drafts via Gemini.

    The processor reads the trigger file, loads the company handbook for guidance,
    sends a combined prompt to the Gemini model (or falls back to a mock response),
    and updates the trigger status accordingly.
    """

    def __init__(self):
        """Initialize the processor and configure Gemini if an API key is present."""
        # Prefer Gemini key, fall back to Claude key for compatibility
        self.api_key = settings.GEMINI_API_KEY or settings.CLAUDE_CODE_API_KEY
        if self.api_key and not self.api_key.startswith("your_"):
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("Gemini model configured for EmailProcessor")
        else:
            logger.warning("No valid API key – EmailProcessor will use mock responses")
            self.model = None

    def process_trigger_file(self, trigger_file: TriggerFile) -> bool:
        """Generate an email draft from a trigger file.

        The method:
        1. Marks the trigger as PROCESSING.
        2. Loads the company handbook for contextual guidance.
        3. Sends a prompt to Gemini (or mock) and receives a response.
        4. Updates the trigger status to COMPLETED.
        5. Returns ``True`` on success, ``False`` on failure.
        """
        # Update status to indicate work has started
        trigger_file.update_status(TriggerStatus.PROCESSING)

        # Load handbook – if this fails we continue with an empty string so the draft can still be generated
        try:
            handbook_text = load_handbook()
        except Exception as e:
            logger.error(f"Failed to load handbook: {e}")
            handbook_text = ""

        # Read the raw trigger content
        trigger_content = self._read_trigger_content(trigger_file)

        # Build a concise prompt for Gemini
        prompt = (
            "Generate an email draft based on the following trigger content, "
            "taking into account the company handbook guidance.\n\n"
            f"Handbook:\n{handbook_text}\n\n"
            f"Trigger Content:\n{trigger_content}"
        )

        # Send to Gemini (or mock) and handle the response
        response = self._send_to_gemini_api(prompt)
        if not response:
            logger.error("No response received from Gemini/mock")
            trigger_file.update_status(TriggerStatus.FAILED)
            return False

        # Log the first 200 characters of the draft
        draft_text = response.get('content', [{}])[0].get('text', '')
        logger.info(f"Email draft generated (truncated): {draft_text[:200]}")

        # Extract Subject and To from trigger content (fallback defaults)
        subject, to_addr = self._extract_headers(trigger_content)
        # Persist the draft using DraftStore
        try:
            from ..services.draft_store import DraftStore
            store = DraftStore()
            store.save_draft(subject=subject, to_addr=to_addr, body=draft_text, platform='email')
        except Exception as e:
            logger.error(f"Failed to save draft file: {e}")
            trigger_file.update_status(TriggerStatus.FAILED)
            return False

        # Mark the trigger as completed
        trigger_file.update_status(TriggerStatus.COMPLETED)
        return True

    def _extract_headers(self, content: str) -> tuple[str, str]:
        """Very simple header extraction from trigger content.

        Looks for lines starting with ``Subject:`` and ``To:`` (case‑insensitive).
        If not found, returns placeholder values.
        """
        subject = "No Subject"
        to_addr = "unknown@example.com"
        for line in content.splitlines():
            if line.lower().startswith('subject:'):
                subject = line.split(':', 1)[1].strip()
            elif line.lower().startswith('to:'):
                to_addr = line.split(':', 1)[1].strip()
        return subject, to_addr

    def _read_trigger_content(self, trigger_file: TriggerFile) -> str:
        """Read the full text of a trigger file."""
        try:
            with open(trigger_file.location, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ClaudeCodeIntegrationException(
                f"Error reading trigger file {trigger_file.location}: {str(e)}"
            )

    def _send_to_gemini_api(self, content: str) -> dict:
        """Send a prompt to Gemini and return a simplified response dict.

        The real Gemini call returns a complex object; we normalise it to the shape used
        throughout the codebase ( ``id``, ``content`` list, ``model`` etc.). If the model
        is not configured we return a mock response.
        """
        try:
            start = time.time()
            if self.model:
                response = self.model.generate_content(content)
                response_data = {
                    "id": "gemini_response_id",
                    "content": [{"type": "text", "text": response.text or "Draft generated"}],
                    "role": "assistant",
                    "model": "Gemini 2.5 Flash",
                    "stop_reason": getattr(response, 'stop_reason', 'end_turn'),
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": getattr(getattr(response, 'usage_metadata', None), 'prompt_token_count', 0),
                        "output_tokens": getattr(getattr(response, 'usage_metadata', None), 'candidates_token_count', 0)
                    }
                }
            else:
                # Mock path – simulate a short latency
                time.sleep(0.2)
                response_data = {
                    "id": "mock_response_id",
                    "content": [{"type": "text", "text": "Mock email draft generated (no API key)"}],
                    "role": "assistant",
                    "model": "Mock",
                    "stop_reason": "end_turn",
                    "stop_sequence": None,
                    "usage": {"input_tokens": 100, "output_tokens": 20}
                }
            elapsed = time.time() - start
            logger.info(f"Gemini call took {elapsed:.2f}s")
            return response_data
        except Exception as e:
            raise ClaudeCodeIntegrationException(f"Error communicating with Gemini API: {str(e)}")
