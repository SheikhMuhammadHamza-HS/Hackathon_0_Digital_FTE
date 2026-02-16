import logging
from .email_processor import EmailProcessor
from ..models.trigger_file import TriggerFile, TriggerStatus
from ..services.planner import Planner
from ..utils.handbook_loader import load_handbook
from ..services.draft_store import DraftStore
from ..config.logging_config import get_logger

logger = get_logger(__name__)

class WhatsAppProcessor(EmailProcessor):
    """Processes WhatsApp task trigger files and generates drafts via Gemini."""

    def process_trigger_file(self, trigger_file: TriggerFile) -> bool:
        """Generate a WhatsApp draft from a trigger file."""
        trigger_file.update_status(TriggerStatus.PROCESSING)

        try:
            handbook_text = load_handbook()
        except Exception as e:
            logger.error(f"Failed to load handbook: {e}")
            handbook_text = ""

        trigger_content = self._read_trigger_content(trigger_file)
        
        # Extract metadata (from_number, body)
        # WhatsApp trigger files are usually created with from_number as 'subject' equivalent
        subject, from_number, thread_id, message_id = self._extract_headers(trigger_content)
        
        logger.info("Generating Plan.md for WhatsApp drafting...")
        plan_context = {
            "sender": from_number,
            "platform": "whatsapp",
            "trigger_path": str(trigger_file.location)
        }
        
        plan, plan_path = self.planner.create_and_save_plan(
            task_type="whatsapp_draft",
            task_description=f"Draft a response to WhatsApp message from {from_number}",
            context=plan_context
        )

        prompt = (
            f"You are a smart Digital FTE Agent. Your goal is to draft a professional WhatsApp response.\n\n"
            "Instructions:\n"
            "1. ANALYZE the 'Original Message' below.\n"
            "2. DRAFT a response that is concise and suitable for WhatsApp (don't use too many formal email greetings).\n"
            "3. If the user sent a simple greeting, respond naturally.\n"
            "4. Use the 'Handbook' rules for capabilities or policy questions.\n"
            "5. SIGN OFF as 'Hamza Digital FTE' at the end.\n\n"
            f"Handbook:\n{handbook_text}\n\n"
            f"Original Message:\n{trigger_content}"
        )

        response = self._send_to_gemini_api(prompt)
        if not response:
            trigger_file.update_status(TriggerStatus.FAILED)
            return False

        draft_text = response.get('content', [{}])[0].get('text', '')
        
        try:
            store = DraftStore()
            store.save_draft(
                subject=f"WhatsApp Reply to {from_number}", 
                to_addr=from_number, 
                body=draft_text, 
                platform='whatsapp',
                thread_id=thread_id,
                message_id=message_id
            )
        except Exception as e:
            logger.error(f"Failed to save WhatsApp draft: {e}")
            trigger_file.update_status(TriggerStatus.FAILED)
            return False

        trigger_file.update_status(TriggerStatus.COMPLETED)
        return True
