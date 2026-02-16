import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from .email_processor import EmailProcessor
from ..models.trigger_file import TriggerFile, TriggerStatus
from ..services.planner import Planner
from ..utils.handbook_loader import load_handbook
from ..services.draft_store import DraftStore
from ..config.logging_config import get_logger
from ..config.settings import settings

logger = get_logger(__name__)


class WhatsAppProcessor(EmailProcessor):
    """Processes WhatsApp task trigger files and generates contextual responses via Gemini.

    This processor:
    1. Parses WhatsApp message metadata from task files
    2. Generates contextual AI responses using Gemini
    3. Considers message tone, urgency, and sender context
    4. Creates properly formatted drafts in Pending_Approval
    """

    def __init__(self):
        """Initialize the WhatsApp processor with Gemini configuration."""
        super().__init__()
        self.platform = "whatsapp"

    def process_trigger_file(self, trigger_file: TriggerFile) -> bool:
        """Generate a WhatsApp draft response from a trigger file.

        Args:
            trigger_file: The trigger file containing WhatsApp message data

        Returns:
            True if processing succeeded, False otherwise
        """
        trigger_file.update_status(TriggerStatus.PROCESSING)

        try:
            # Load handbook for guidance
            try:
                handbook_text = load_handbook()
            except Exception as e:
                logger.error(f"Failed to load handbook: {e}")
                handbook_text = ""

            # Read and parse the trigger content
            trigger_content = self._read_trigger_content(trigger_file)

            # Extract WhatsApp-specific metadata
            metadata = self._extract_whatsapp_metadata(trigger_content)
            sender = metadata.get('sender', 'Unknown')
            msg_text = metadata.get('message_text', '')
            received_at = metadata.get('received_at', '')
            original_hash = metadata.get('hash', '')

            logger.info(f"Processing WhatsApp message from: {sender}")

            # Generate Plan.md for tracking
            plan_context = {
                "sender": sender,
                "platform": "whatsapp",
                "trigger_path": str(trigger_file.location),
                "message_preview": msg_text[:100] + "..." if len(msg_text) > 100 else msg_text
            }

            plan, plan_path = self.planner.create_and_save_plan(
                task_type="whatsapp_draft",
                task_description=f"Draft a WhatsApp response to message from {sender}",
                context=plan_context
            )
            logger.info(f"Plan created: {plan_path}")

            # Analyze message for tone and urgency
            tone_analysis = self._analyze_message_tone(msg_text)

            # Build optimized prompt for Gemini
            prompt = self._build_whatsapp_prompt(
                sender=sender,
                message_text=msg_text,
                received_at=received_at,
                tone_analysis=tone_analysis,
                handbook_text=handbook_text
            )

            # Send to Gemini API
            response = self._send_to_gemini_api(prompt)
            if not response:
                logger.error("No response received from Gemini API")
                trigger_file.update_status(TriggerStatus.FAILED)
                return False

            # Extract draft text from response
            draft_text = response.get('content', [{}])[0].get('text', '')

            if not draft_text or len(draft_text.strip()) < 10:
                logger.error("Generated draft is too short or empty")
                trigger_file.update_status(TriggerStatus.FAILED)
                return False

            # Clean up the draft (remove any markdown code blocks if present)
            draft_text = self._clean_draft_text(draft_text)

            # Save the draft to Pending_Approval
            try:
                store = DraftStore()
                draft_path = store.save_draft(
                    subject=f"WhatsApp Reply to {sender}",
                    to_addr=sender,
                    body=draft_text,
                    platform='whatsapp',
                    thread_id=original_hash,
                    message_id=metadata.get('id', '')
                )
                logger.info(f"WhatsApp draft saved to: {draft_path}")
            except Exception as e:
                logger.error(f"Failed to save WhatsApp draft: {e}")
                trigger_file.update_status(TriggerStatus.FAILED)
                return False

            trigger_file.update_status(TriggerStatus.COMPLETED)
            return True

        except Exception as e:
            logger.error(f"Error processing WhatsApp trigger file: {e}")
            trigger_file.update_status(TriggerStatus.FAILED)
            return False

    def _extract_whatsapp_metadata(self, content: str) -> Dict[str, Any]:
        """Extract WhatsApp-specific metadata from task file content.

        Args:
            content: The raw content of the task file

        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {
            'id': '',
            'sender': 'Unknown',
            'hash': '',
            'received_at': '',
            'detected_at': '',
            'message_text': ''
        }

        # Extract YAML frontmatter
        if content.startswith('---'):
            try:
                import yaml
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    if frontmatter:
                        metadata['id'] = frontmatter.get('id', '')
                        metadata['sender'] = frontmatter.get('sender', 'Unknown')
                        metadata['hash'] = frontmatter.get('hash', '')
                        metadata['received_at'] = frontmatter.get('received_at', '')
                        metadata['detected_at'] = frontmatter.get('detected_at', '')

                    # Extract message text from body (after second ---)
                    body_content = parts[2]
                    # Find the message content section
                    if '### Message Content' in body_content:
                        msg_section = body_content.split('### Message Content')[1]
                        # Get text until next section or end
                        if '---' in msg_section:
                            msg_section = msg_section.split('---')[0]
                        metadata['message_text'] = msg_section.strip()
                    else:
                        # Fallback: extract everything after frontmatter
                        metadata['message_text'] = body_content.strip()
            except Exception as e:
                logger.warning(f"Failed to parse YAML frontmatter: {e}")

        # If no frontmatter or parsing failed, try line-by-line extraction
        if metadata['sender'] == 'Unknown':
            for line in content.split('\n'):
                if line.lower().startswith('sender:'):
                    metadata['sender'] = line.split(':', 1)[1].strip().strip('"')
                elif line.lower().startswith('from:'):
                    metadata['sender'] = line.split(':', 1)[1].strip().strip('"')

        return metadata

    def _analyze_message_tone(self, message_text: str) -> Dict[str, Any]:
        """Analyze the tone and urgency of the incoming message.

        Args:
            message_text: The message content to analyze

        Returns:
            Dictionary with tone analysis results
        """
        text_lower = message_text.lower()

        # Urgency indicators
        urgent_keywords = ['urgent', 'asap', 'immediately', 'emergency', 'quick', 'fast', 'hurry']
        is_urgent = any(kw in text_lower for kw in urgent_keywords)

        # Question detection
        has_question = '?' in message_text or any(
            kw in text_lower for kw in ['what', 'when', 'where', 'why', 'how', 'who', 'can you', 'could you']
        )

        # Greeting detection
        greeting_patterns = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']
        is_greeting = any(text_lower.strip().startswith(g) for g in greeting_patterns)

        # Sentiment indicators
        positive_words = ['thanks', 'thank you', 'great', 'awesome', 'good', 'love', 'happy']
        negative_words = ['bad', 'issue', 'problem', 'error', 'fail', 'wrong', 'angry', 'upset']

        positive_count = sum(1 for w in positive_words if w in text_lower)
        negative_count = sum(1 for w in negative_words if w in text_lower)

        if negative_count > positive_count:
            sentiment = 'negative'
        elif positive_count > negative_count:
            sentiment = 'positive'
        else:
            sentiment = 'neutral'

        return {
            'is_urgent': is_urgent,
            'has_question': has_question,
            'is_greeting': is_greeting,
            'sentiment': sentiment,
            'length_category': 'short' if len(message_text) < 50 else ('medium' if len(message_text) < 200 else 'long')
        }

    def _build_whatsapp_prompt(
        self,
        sender: str,
        message_text: str,
        received_at: str,
        tone_analysis: Dict[str, Any],
        handbook_text: str
    ) -> str:
        """Build an optimized prompt for WhatsApp response generation.

        Args:
            sender: The sender's name/number
            message_text: The original message content
            received_at: Timestamp when message was received
            tone_analysis: Tone analysis results
            handbook_text: Company handbook content

        Returns:
            Formatted prompt string for Gemini
        """
        # Build tone guidance
        tone_guidance = []
        if tone_analysis['is_urgent']:
            tone_guidance.append("- The message appears URGENT - respond promptly and prioritize action items")
        if tone_analysis['has_question']:
            tone_guidance.append("- The sender asked a question - ensure you directly answer it")
        if tone_analysis['is_greeting']:
            tone_guidance.append("- This is a greeting/conversation starter - be warm and friendly")
        if tone_analysis['sentiment'] == 'negative':
            tone_guidance.append("- The sender may be frustrated - be empathetic and solution-focused")
        elif tone_analysis['sentiment'] == 'positive':
            tone_guidance.append("- The sender seems positive - match their enthusiasm")

        tone_section = '\n'.join(tone_guidance) if tone_guidance else "- Keep the tone professional yet conversational"

        prompt = f"""You are Hamza Digital FTE, a smart AI assistant handling WhatsApp communications.

## TASK
Draft a contextual WhatsApp response to the message below.

## ORIGINAL MESSAGE
From: {sender}
Received: {received_at}
Content:
{message_text}

## TONE ANALYSIS
{tone_section}
Message length: {tone_analysis['length_category']}

## RESPONSE GUIDELINES
1. **Be Concise**: WhatsApp messages should be brief and to-the-point (2-4 sentences ideal)
2. **Conversational Tone**: Less formal than email, more like texting a colleague
3. **Direct Answer**: If they asked something specific, answer it clearly first
4. **Contextual Awareness**:
   - For greetings: Respond warmly, ask how you can help
   - For questions: Answer directly, offer follow-up if needed
   - For urgent requests: Acknowledge urgency, provide timeline
   - For complaints/issues: Show empathy, explain next steps
5. **Professional but Friendly**: Use casual language but maintain professionalism
6. **No Over-Explaining**: Don't write paragraphs when a sentence suffices
7. **Action Items**: If follow-up is needed, clearly state what you'll do

## COMPANY HANDBOOK REFERENCE
{handbook_text if handbook_text else "No specific handbook guidelines available."}

## OUTPUT FORMAT
Write ONLY the response message text. Do NOT include:
- Headers or labels
- Quotation marks around the message
- Signatures (sign off naturally as part of the message)
- Meta-commentary about being an AI

The response should feel natural and human, as if typed quickly on a phone."""

        return prompt

    def _clean_draft_text(self, draft_text: str) -> str:
        """Clean up the generated draft text.

        Args:
            draft_text: Raw text from Gemini

        Returns:
            Cleaned text ready for sending
        """
        # Remove markdown code blocks if present
        if draft_text.startswith('```') and draft_text.endswith('```'):
            lines = draft_text.split('\n')
            # Remove first and last lines (code block markers)
            if len(lines) > 2:
                draft_text = '\n'.join(lines[1:-1])

        # Remove common prefixes that Gemini might add
        prefixes_to_remove = [
            'Response:',
            'Reply:',
            'WhatsApp Response:',
            'Draft:',
        ]
        for prefix in prefixes_to_remove:
            if draft_text.startswith(prefix):
                draft_text = draft_text[len(prefix):].strip()

        # Clean up excessive whitespace
        draft_text = re.sub(r'\n{3,}', '\n\n', draft_text)

        return draft_text.strip()
