import time
from pathlib import Path

import google.generativeai as genai

from ..config import settings
from ..models.trigger_file import TriggerFile, TriggerStatus
from ..exceptions import ClaudeCodeIntegrationException
from ..config.logging_config import get_logger

from ..utils.goals_reader import get_metrics, get_rules
from ..services.draft_store import DraftStore

logger = get_logger(__name__)


class LinkedInProcessor:
    """Generates LinkedIn post drafts based on Business_Goals.

    Uses the same mock‑fallback pattern as :class:`EmailProcessor`. Drafts are
    persisted via :class:`DraftStore` into the ``Pending_Approval`` folder.
    """

    def __init__(self):
        """Configure Gemini (or mock) using the shared GEMINI_API_KEY."""
        self.api_key = settings.GEMINI_API_KEY or settings.CLAUDE_CODE_API_KEY
        if self.api_key and not self.api_key.startswith('your_'):
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info('Gemini model configured for LinkedInProcessor')
        else:
            logger.warning('No valid API key – LinkedInProcessor will use mock responses')
            self.model = None

        self.draft_store = DraftStore()

    def process_trigger_file(self, trigger_file: TriggerFile) -> bool:
        """Generate a LinkedIn draft from a trigger file.

        The flow mirrors ``EmailProcessor.process_trigger_file`` but draws its
        context from the ``Business_Goals.md`` sections.
        """
        trigger_file.update_status(TriggerStatus.PROCESSING)

        # Load Business Goals sections – fall back to empty strings on error
        try:
            metrics = get_metrics()
            rules = get_rules()
        except Exception as e:
            logger.error(f'Failed to load Business_Goals sections: {e}')
            metrics = ''
            rules = ''

        trigger_content = self._read_trigger_content(trigger_file)

        prompt = (
            "Generate a concise LinkedIn post draft using the following information.\n\n"
            f"Metrics:\n{metrics}\n\n"
            f"Rules:\n{rules}\n\n"
            f"Trigger Content:\n{trigger_content}"
        )

        response = self._send_to_gemini_api(prompt)
        if not response:
            logger.error('No response from Gemini/mock for LinkedIn draft')
            trigger_file.update_status(TriggerStatus.FAILED)
            return False

        draft_text = response.get('content', [{}])[0].get('text', '')
        logger.info(f'LinkedIn draft generated (truncated): {draft_text[:200]}')

        # For LinkedIn we don't have a real recipient; use placeholder values
        subject = 'LinkedIn Draft'
        to_addr = 'linkedin'
        try:
            self.draft_store.save_draft(subject=subject, to_addr=to_addr, body=draft_text, platform='linkedin')
        except Exception as e:
            logger.error(f'Failed to persist LinkedIn draft: {e}')
            trigger_file.update_status(TriggerStatus.FAILED)
            return False

        trigger_file.update_status(TriggerStatus.COMPLETED)
        return True

    def _read_trigger_content(self, trigger_file: TriggerFile) -> str:
        try:
            with open(trigger_file.location, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ClaudeCodeIntegrationException(
                f'Error reading trigger file {trigger_file.location}: {e}'
            )

    def _send_to_gemini_api(self, content: str) -> dict:
        try:
            start = time.time()
            if self.model:
                resp = self.model.generate_content(content)
                data = {
                    'id': 'gemini_response_id',
                    'content': [{'type': 'text', 'text': resp.text or 'Draft generated'}],
                    'role': 'assistant',
                    'model': 'Gemini 2.5 Flash',
                    'stop_reason': getattr(resp, 'stop_reason', 'end_turn'),
                    'stop_sequence': None,
                    'usage': {
                        'input_tokens': getattr(getattr(resp, 'usage_metadata', None), 'prompt_token_count', 0),
                        'output_tokens': getattr(getattr(resp, 'usage_metadata', None), 'candidates_token_count', 0)
                    }
                }
            else:
                time.sleep(0.2)
                data = {
                    'id': 'mock_response_id',
                    'content': [{'type': 'text', 'text': 'Mock LinkedIn draft (no API key)'}],
                    'role': 'assistant',
                    'model': 'Mock',
                    'stop_reason': 'end_turn',
                    'stop_sequence': None,
                    'usage': {'input_tokens': 100, 'output_tokens': 20}
                }
            logger.info(f'Gemini call took {time.time() - start:.2f}s')
            return data
        except Exception as e:
            raise ClaudeCodeIntegrationException(f'Error communicating with Gemini API: {e}')
