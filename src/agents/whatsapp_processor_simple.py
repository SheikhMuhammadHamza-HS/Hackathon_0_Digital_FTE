"""
Simplified WhatsApp Processor - Creates plans and drafts from incoming messages.

Flow:
1. Read WhatsApp task from Needs_Action
2. Create Plan.md in Plans/ folder
3. Create draft response in Pending_Approval/
"""
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from ..config.settings import settings
from ..config import settings as settings_module
from ..utils.file_utils import ensure_directory_exists

logger = logging.getLogger(__name__)


class WhatsAppProcessorSimple:
    """Simple WhatsApp processor that creates plans and drafts."""

    def __init__(self):
        # Get base dir from settings module
        self.base_dir = Path(settings_module.BASE_DIR)
        self.plans_dir = self.base_dir / "Plans"
        self.pending_dir = Path(settings.PENDING_APPROVAL_PATH)
        ensure_directory_exists(self.plans_dir)
        ensure_directory_exists(self.pending_dir)

    def process_task(self, task_path: Path) -> bool:
        """Process a WhatsApp task file.

        Args:
            task_path: Path to task file in Needs_Action

        Returns:
            True if successful
        """
        try:
            # Parse the incoming message
            metadata = self._parse_task(task_path)

            # Create plan
            plan_path = self._create_plan(metadata)

            # Create draft response
            draft_path = self._create_draft(metadata)

            logger.info(f"✅ Processed {task_path.name}")
            logger.info(f"   Plan: {plan_path.name}")
            logger.info(f"   Draft: {draft_path.name}")

            return True

        except Exception as e:
            logger.error(f"Failed to process {task_path}: {e}")
            return False

    def _parse_task(self, task_path: Path) -> Dict[str, Any]:
        """Parse WhatsApp task file."""
        content = task_path.read_text(encoding='utf-8')

        # Extract metadata
        metadata = {
            'sender': '',
            'message': '',
            'timestamp': datetime.now().isoformat(),
            'task_id': task_path.stem
        }

        # Parse YAML frontmatter if present
        lines = content.split('\n')
        in_frontmatter = False
        body_start = 0

        for i, line in enumerate(lines):
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    body_start = i + 1
                    break
            elif in_frontmatter and ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                if key == 'sender':
                    metadata['sender'] = value
                elif key == 'message':
                    metadata['message'] = value

        # Get body if not in frontmatter
        if not metadata['message'] and body_start < len(lines):
            metadata['message'] = '\n'.join(lines[body_start:]).strip()

        # Fallback: try to extract from simple format
        if not metadata['sender']:
            for line in lines:
                if line.startswith('From:'):
                    metadata['sender'] = line.split(':', 1)[1].strip()
                elif line.startswith('Message:') and not metadata['message']:
                    metadata['message'] = line.split(':', 1)[1].strip()

        # Generate contextual response
        metadata['response'] = self._generate_response(
            metadata['sender'],
            metadata['message']
        )

        return metadata

    def _generate_response(self, sender: str, message: str) -> str:
        """Generate a contextual response based on message content."""
        message_lower = message.lower()

        # Check for common intents
        if any(word in message_lower for word in ['invoice', 'bill', 'payment']):
            return f"Hi {sender}, I've received your request for the invoice. I'm preparing it now and will send it to you shortly!"

        elif any(word in message_lower for word in ['price', 'pricing', 'cost', 'rate']):
            return f"Hi {sender}, thanks for your interest! Let me get the latest pricing information for you. I'll send it over shortly."

        elif any(word in message_lower for word in ['help', 'support', 'issue', 'problem']):
            return f"Hi {sender}, I'm sorry to hear you're facing an issue. I'm looking into this right away and will get back to you with a solution soon."

        elif any(word in message_lower for word in ['update', 'status', 'progress']):
            return f"Hi {sender}, absolutely! I'm getting the latest project update ready for you now. I'll send it over shortly!"

        elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return f"Hi {sender}! Hope you're doing well. How can I help you today?"

        elif any(word in message_lower for word in ['urgent', 'asap', 'emergency']):
            return f"Hi {sender}, I understand this is urgent. I'm prioritizing this right away and will respond shortly!"

        else:
            # Generic contextual response
            return f"Hi {sender}, thanks for your message! I've received it and will get back to you with a proper response shortly."

    def _create_plan(self, metadata: Dict[str, Any]) -> Path:
        """Create a plan file in Plans/ folder."""
        plan_id = f"PLAN_{metadata['task_id']}"
        plan_path = self.plans_dir / f"{plan_id}.md"

        plan_content = f"""---
id: {plan_id}
created: {datetime.now().isoformat()}
status: pending_execution
type: whatsapp_response
---

# Plan: Respond to WhatsApp Message

## Source
- **From**: {metadata['sender']}
- **Original Message**: {metadata['message'][:100]}{'...' if len(metadata['message']) > 100 else ''}

## Analysis
- **Intent**: {self._detect_intent(metadata['message'])}
- **Urgency**: {self._detect_urgency(metadata['message'])}
- **Tone**: Professional and helpful

## Action Plan
1. [x] Analyze incoming message
2. [x] Generate contextual response
3. [ ] Create draft in Pending_Approval
4. [ ] Wait for human approval
5. [ ] Send response via WhatsApp

## Draft Response
```
{metadata['response']}
```

## Execution Details
- **Recipient**: {metadata['sender']}
- **Platform**: WhatsApp
- **Requires Approval**: Yes (all outbound messages)
"""

        plan_path.write_text(plan_content, encoding='utf-8')
        logger.info(f"Created plan: {plan_path}")
        return plan_path

    def _create_draft(self, metadata: Dict[str, Any]) -> Path:
        """Create draft response in Pending_Approval/."""
        draft_id = f"DRAFT_{metadata['task_id']}"
        draft_path = self.pending_dir / f"{draft_id}.md"

        draft_content = f"""---
type: whatsapp_response
to: {metadata['sender']}
platform: whatsapp
original_sender: {metadata['sender']}
original_message: {metadata['message'][:50]}{'...' if len(metadata['message']) > 50 else ''}
created: {datetime.now().isoformat()}
status: pending_approval
---

## Response to {metadata['sender']}

{metadata['response']}

---

**To Approve**: Move this file to `/Approved/` folder
**To Reject**: Move this file to `/Rejected/` folder or delete
"""

        draft_path.write_text(draft_content, encoding='utf-8')
        logger.info(f"Created draft: {draft_path}")
        return draft_path

    def _detect_intent(self, message: str) -> str:
        """Detect the intent of the message."""
        message_lower = message.lower()
        intents = []

        if any(w in message_lower for w in ['invoice', 'bill']):
            intents.append('Invoice Request')
        if any(w in message_lower for w in ['price', 'cost', 'pricing']):
            intents.append('Pricing Inquiry')
        if any(w in message_lower for w in ['help', 'support', 'issue']):
            intents.append('Support Request')
        if any(w in message_lower for w in ['update', 'status']):
            intents.append('Status Update')

        return ', '.join(intents) if intents else 'General Inquiry'

    def _detect_urgency(self, message: str) -> str:
        """Detect urgency level."""
        message_lower = message.lower()

        if any(w in message_lower for w in ['urgent', 'asap', 'emergency', 'immediately']):
            return 'High'
        elif any(w in message_lower for w in ['soon', 'today', 'quick']):
            return 'Medium'
        else:
            return 'Normal'
