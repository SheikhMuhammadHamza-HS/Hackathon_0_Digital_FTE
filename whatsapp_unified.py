#!/usr/bin/env python3
"""
Unified WhatsApp HITL - Watcher + Sender in ONE terminal.

This combines:
1. WhatsApp Watcher - Monitors incoming messages
2. Persistence Loop - Generates AI responses and sends approved messages
3. Sequential processing - Watcher runs, then sender runs (no async conflicts)

Usage: python whatsapp_unified.py
"""
import asyncio
import logging
import time
import sys
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import settings

try:
    from playwright.async_api import async_playwright
except ImportError:
    logger.error("Playwright not installed. Run: pip install playwright")
    sys.exit(1)


class UnifiedWhatsAppHITL:
    """Combined WhatsApp Watcher and Sender."""

    def __init__(self):
        self.session_dir = Path(settings.LOGS_PATH) / "whatsapp_session"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.needs_action_dir = Path(settings.NEEDS_ACTION_PATH)
        self.pending_approval_dir = Path(settings.PENDING_APPROVAL_PATH)
        self.approved_dir = Path(settings.APPROVED_PATH)
        self.done_dir = Path(settings.DONE_PATH)

        self.running = False
        self.browser_context = None
        self.page = None
        self.playwright = None

        # Track already seen chats to avoid processing old messages
        self.initial_chats = set()
        self.system_start_time = datetime.now()
        self.processed_messages = set()  # Track processed message hashes

    async def initialize_browser(self) -> bool:
        """Initialize browser with saved session."""
        try:
            logger.info("=" * 60)
            logger.info("Initializing WhatsApp Browser Session")
            logger.info("=" * 60)

            self.playwright = await async_playwright().start()

            self.browser_context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=False,
                args=[
                    '--window-size=1400,900',
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )

            if self.browser_context.pages:
                self.page = self.browser_context.pages[0]
            else:
                self.page = await self.browser_context.new_page()

            logger.info("Opening WhatsApp Web...")
            await self.page.goto("https://web.whatsapp.com", wait_until="networkidle", timeout=120000)
            await asyncio.sleep(3)

            # Check login with multiple selectors
            logged_in = False
            selectors = ['[data-testid="chat-list"]', '#pane-side', 'div[role="grid"]']

            for selector in selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem and await elem.is_visible():
                        logged_in = True
                        logger.info(f"Already logged in! (found: {selector})")
                        break
                except:
                    continue

            if not logged_in:
                logger.info("=" * 60)
                logger.info("PLEASE SCAN QR CODE")
                logger.info("=" * 60)
                logger.info("1. Look at the browser window")
                logger.info("2. Scan QR code with your phone")
                logger.info("3. Waiting up to 3 minutes...")
                logger.info("=" * 60)

                start_time = time.time()
                while time.time() - start_time < 180:
                    await asyncio.sleep(3)

                    for selector in selectors:
                        try:
                            elem = await self.page.query_selector(selector)
                            if elem and await elem.is_visible():
                                logged_in = True
                                break
                        except:
                            continue

                    if logged_in:
                        break

                    elapsed = int(time.time() - start_time)
                    if elapsed % 15 == 0:
                        logger.info(f"Still waiting for login... ({elapsed}s)")

                if not logged_in:
                    logger.error("Login timeout!")
                    return False

                logger.info("Login successful!")

            # NOW capture initial state after successful login
            await self._capture_initial_state()

            return True

        except Exception as e:
            logger.error(f"Browser initialization failed: {e}")
            return False

    async def _capture_initial_state(self):
        """Capture initial state - record sender+timestamp to detect only NEW messages."""
        try:
            logger.info("[INIT] Recording current chat states...")
            await asyncio.sleep(5)  # Wait for WhatsApp to fully load chats

            # Use same selectors as scan_messages
            all_chats = []
            for selector in ['div[data-testid="cell-frame-container"]', 'div[role="listitem"]', '#pane-side div[role="grid"] > div', 'div._ak8l', 'div._ak8h']:
                try:
                    chats = await self.page.query_selector_all(selector)
                    if chats and len(chats) > 0:
                        all_chats = chats
                        logger.info(f"[INIT] Using selector: {selector}, found {len(chats)} chats")
                        break
                except:
                    continue

            recorded = 0
            for chat in all_chats:
                try:
                    # Get sender name
                    sender = "Unknown"
                    for title_selector in ['span[dir="auto"]', 'span[title]', 'div[title]']:
                        title_elem = await chat.query_selector(title_selector)
                        if title_elem:
                            sender = await title_elem.text_content() or "Unknown"
                            sender = sender.strip()
                            if sender and sender != "Unknown":
                                break

                    if not sender or sender == "Unknown":
                        continue

                    # Get timestamp - same selectors as scan_messages
                    last_msg_time = ""
                    for time_selector in ['span[data-testid="last-msg-status"]', 'div[class*="time"]', 'span[class*="time"]']:
                        time_elem = await chat.query_selector(time_selector)
                        if time_elem:
                            last_msg_time = await time_elem.text_content() or ""
                            last_msg_time = last_msg_time.strip()
                            break

                    # Record this state (even if timestamp is empty - use sender only as fallback)
                    if last_msg_time:
                        chat_key = f"{sender}_{last_msg_time}"
                    else:
                        chat_key = f"{sender}_no_time"
                    self.processed_messages.add(chat_key)
                    self.initial_chats.add(sender)
                    recorded += 1

                except:
                    continue

            logger.info(f"[INIT] Recorded {recorded} chats with timestamps")
            logger.info(f"[INIT] Total unique senders: {len(self.initial_chats)}")

        except Exception as e:
            logger.warning(f"[INIT] Could not capture initial state: {e}")

    async def scan_messages(self) -> int:
        """Scan for new WhatsApp messages using the shared browser.

        Uses timestamp-based detection instead of unread indicators.
        Compares current chat state with previous state to detect new messages.
        """
        try:
            logger.info("[WATCHER] Scanning for new messages...")

            # Navigate to WhatsApp (if not already there)
            if "web.whatsapp.com" not in self.page.url:
                await self.page.goto("https://web.whatsapp.com", wait_until="networkidle")
                await asyncio.sleep(3)

            # Don't reload - it disrupts the session. Just ensure we're on the page
            await asyncio.sleep(2)

            # Get all chat items - try multiple selectors
            chats = []
            selectors_to_try = [
                'div[data-testid="cell-frame-container"]',
                'div[role="listitem"]',
                '#pane-side div[role="grid"] > div',
                'div._ak8l',
                'div._ak8h',
            ]

            for selector in selectors_to_try:
                try:
                    chats = await self.page.query_selector_all(selector)
                    if chats and len(chats) > 0:
                        logger.info(f"[WATCHER] Found {len(chats)} chats")
                        break
                except Exception as e:
                    continue

            if not chats:
                logger.warning("[WATCHER] No chats found!")
                return 0

            new_count = 0

            for i, chat in enumerate(chats[:20]):  # Check first 20 chats
                try:
                    # Get sender name
                    sender = "Unknown"
                    for title_selector in ['span[dir="auto"]', 'span[title]', 'div[title]']:
                        title_elem = await chat.query_selector(title_selector)
                        if title_elem:
                            sender = await title_elem.text_content() or "Unknown"
                            sender = sender.strip()
                            if sender and sender != "Unknown":
                                break

                    if not sender or sender == "Unknown":
                        continue

                    # Get timestamp of last message in this chat
                    last_msg_time = ""
                    for time_selector in ['span[data-testid="last-msg-status"]', 'div[class*="time"]', 'span[class*="time"]']:
                        time_elem = await chat.query_selector(time_selector)
                        if time_elem:
                            last_msg_time = await time_elem.text_content() or ""
                            break

                    # Create unique key for this chat's last message
                    chat_key = f"{sender}_{last_msg_time}"

                    # Check if this sender was already seen at startup
                    sender_seen_at_startup = sender in self.initial_chats

                    # Skip if we've seen this exact state before
                    if chat_key in self.processed_messages:
                        continue

                    # If sender was seen at startup and this is first scan, skip it
                    # (it's an old message, not a new one)
                    if sender_seen_at_startup and len(self.processed_messages) <= len(self.initial_chats):
                        # Mark it as processed so we don't see it again
                        self.processed_messages.add(chat_key)
                        continue

                    # NEW MESSAGE DETECTED
                    logger.info(f"[WATCHER] NEW message from: {sender}")

                    # Click chat to open it
                    await chat.click()
                    await asyncio.sleep(2)

                    # Get the actual last message content
                    last_message = ""

                    # Try to get messages from the conversation
                    msg_selectors = ['div.message-in', 'div[class*="message-in"]', 'div._amk4', 'div._amk6']
                    for msg_sel in msg_selectors:
                        messages = await self.page.query_selector_all(msg_sel)
                        if messages:
                            # Get the last incoming message
                            for msg in reversed(messages[-3:]):
                                text_selectors = ['span.selectable-text', 'span[class*="selectable"]', 'div[class*="text"]']
                                for txt_sel in text_selectors:
                                    text_elem = await msg.query_selector(txt_sel)
                                    if text_elem:
                                        text = await text_elem.text_content() or ""
                                        if text and len(text.strip()) > 0:
                                            last_message = text.strip()
                                            break
                                if last_message:
                                    break
                        if last_message:
                            break

                    if last_message:
                        logger.info(f"[WATCHER] Message: {last_message[:60]}...")

                        # Mark as processed
                        self.processed_messages.add(chat_key)

                        # Create task file
                        await self._create_task_file(sender, last_message)
                        new_count += 1

                        # Add to initial chats so we don't process again
                        self.initial_chats.add(sender)

                    # Go back to chat list using Escape key
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.debug(f"[WATCHER] Error processing chat {i}: {e}")
                    continue

            logger.info(f"[WATCHER] Total new messages: {new_count}")
            return new_count

        except Exception as e:
            logger.error(f"[WATCHER] Scan error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return 0

    async def _create_task_file(self, sender: str, message: str):
        """Create task file in Needs_Action."""
        try:
            clean_sender = "".join(c for c in sender if c.isalnum() or c in (' ', '-', '_')).strip()
            clean_sender = clean_sender.replace(' ', '_')[:30]

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"WHATSAPP_{timestamp}_{clean_sender}.md"
            filepath = self.needs_action_dir / filename

            content = f"""---
type: whatsapp_message
sender: "{sender}"
message: "{message[:200]}"
received: "{timestamp}"
status: pending
---

## WhatsApp Message from {sender}

**Received:** {timestamp}

### Message Content
{message}

---

*This message needs a response. AI will generate a draft.*
"""
            filepath.write_text(content, encoding='utf-8')
            logger.info(f"[WATCHER] Created task: {filename}")

        except Exception as e:
            logger.error(f"[WATCHER] Failed to create task: {e}")

    async def process_needs_action(self) -> dict:
        """Process files in Needs_Action."""
        result = {'processed': 0, 'failed': 0}

        try:
            files = list(self.needs_action_dir.glob("*.md"))

            for filepath in files:
                try:
                    logger.info(f"[PROCESSOR] Processing: {filepath.name}")

                    # Read file
                    content = filepath.read_text(encoding='utf-8')

                    # Detect if WhatsApp
                    if 'whatsapp' not in content.lower():
                        continue

                    # Extract sender and message
                    sender = "Unknown"
                    message = ""

                    for line in content.split('\n'):
                        if line.startswith('sender:'):
                            sender = line.split(':', 1)[1].strip().strip('"')
                        if line.startswith('message:'):
                            message = line.split(':', 1)[1].strip().strip('"')

                    # Generate simple response
                    response = f"Salam {sender}! Thanks for your message: '{message}'. I'll get back to you soon."

                    # Create draft
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    draft_filename = f"DRAFT_{timestamp}_{sender.replace(' ', '_')[:20]}.md"
                    draft_path = self.pending_approval_dir / draft_filename

                    draft_content = f"""---
type: whatsapp_response
to: "{sender}"
platform: whatsapp
original_sender: "{sender}"
original_message: "{message}"
status: pending
---

{response}
"""
                    draft_path.write_text(draft_content, encoding='utf-8')
                    logger.info(f"[PROCESSOR] Created draft: {draft_filename}")

                    # Move original to done
                    done_path = self.done_dir / filepath.name
                    filepath.rename(done_path)

                    result['processed'] += 1

                except Exception as e:
                    logger.error(f"[PROCESSOR] Error: {e}")
                    result['failed'] += 1

        except Exception as e:
            logger.error(f"[PROCESSOR] Scan error: {e}")

        return result

    async def process_approved(self) -> dict:
        """Process approved messages and send them."""
        result = {'sent': 0, 'failed': 0}

        try:
            files = list(self.approved_dir.glob("*.md"))

            for filepath in files:
                try:
                    logger.info(f"[SENDER] Sending: {filepath.name}")

                    content = filepath.read_text(encoding='utf-8')

                    # Extract recipient and message from YAML frontmatter
                    import re
                    recipient = ""
                    message = ""

                    # Try to extract 'to:' from YAML frontmatter
                    to_match = re.search(r'^to:\s*["\']?([^"\'\n]+)["\']?$', content, re.MULTILINE)
                    if to_match:
                        recipient = to_match.group(1).strip()

                    # Extract body after second '---'
                    parts = content.split('---')
                    if len(parts) >= 3:
                        # Body is after the second ---
                        body = parts[2].strip()
                        # Get first non-empty line
                        for line in body.split('\n'):
                            stripped = line.strip()
                            if stripped:
                                message = stripped
                                break
                    else:
                        # No YAML frontmatter, just get first line
                        for line in content.split('\n'):
                            stripped = line.strip()
                            if stripped and not stripped.startswith('---'):
                                message = stripped
                                break

                    if not recipient or not message:
                        logger.error(f"[SENDER] Missing recipient or message in {filepath.name}")
                        result['failed'] += 1
                        continue

                    # Send via WhatsApp Web
                    success = await self._send_whatsapp_message(recipient, message)

                    if success:
                        # Move to done
                        done_path = self.done_dir / filepath.name
                        filepath.rename(done_path)
                        logger.info(f"[SENDER] Sent and moved to Done: {filepath.name}")
                        result['sent'] += 1
                    else:
                        result['failed'] += 1

                except Exception as e:
                    logger.error(f"[SENDER] Error: {e}")
                    result['failed'] += 1

        except Exception as e:
            logger.error(f"[SENDER] Scan error: {e}")

        return result

    async def _send_whatsapp_message(self, recipient: str, message: str) -> bool:
        """Send a WhatsApp message using the shared browser."""
        try:
            logger.info(f"[SENDER] Sending to {recipient}...")

            # Make sure we're on WhatsApp
            if "web.whatsapp.com" not in self.page.url:
                await self.page.goto("https://web.whatsapp.com", wait_until="networkidle")
                await asyncio.sleep(3)

            # Search for contact
            search_box = await self.page.query_selector('div[contenteditable="true"]')
            if not search_box:
                logger.error("[SENDER] Search box not found")
                return False

            await search_box.click()
            await asyncio.sleep(0.5)

            # Clear and type
            await self.page.keyboard.press("Control+a")
            await self.page.keyboard.press("Delete")
            await search_box.type(recipient, delay=100)
            await asyncio.sleep(2)

            # Press Enter to select
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(3)

            # Find message input
            inputs = await self.page.query_selector_all('div[contenteditable="true"]')
            msg_input = None

            for inp in inputs:
                data_tab = await inp.get_attribute('data-tab')
                if data_tab == '1':
                    msg_input = inp
                    break

            if not msg_input:
                msg_input = await self.page.query_selector('footer div[contenteditable="true"]')

            if not msg_input:
                logger.error("[SENDER] Message input not found")
                return False

            # Type and send
            await msg_input.click()
            await asyncio.sleep(0.5)
            await msg_input.type(message, delay=50)
            await asyncio.sleep(1)

            await self.page.keyboard.press("Enter")
            await asyncio.sleep(2)

            logger.info(f"[SENDER] Message sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"[SENDER] Send error: {e}")
            return False

    async def run(self):
        """Run the unified loop."""
        logger.info("=" * 60)
        logger.info("Unified WhatsApp HITL System")
        logger.info("=" * 60)
        logger.info("Workflow:")
        logger.info("1. Scan WhatsApp for new messages")
        logger.info("2. Create AI response drafts in Pending_Approval")
        logger.info("3. You move drafts to Approved folder")
        logger.info("4. System sends approved messages")
        logger.info("=" * 60)

        # Initialize browser
        if not await self.initialize_browser():
            return

        self.running = True
        cycle = 0

        try:
            while self.running:
                cycle += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"CYCLE #{cycle}")
                logger.info('='*60)

                # Step 1: Scan for messages
                new_msgs = await self.scan_messages()

                # Step 2: Process Needs_Action
                processed = await self.process_needs_action()
                if processed['processed'] > 0:
                    logger.info(f"[PROCESSOR] Created {processed['processed']} drafts in Pending_Approval")
                    logger.info("[ACTION REQUIRED] Review drafts in Pending_Approval, move to Approved to send")

                # Step 3: Process Approved
                approved = await self.process_approved()
                if approved['sent'] > 0:
                    logger.info(f"[SENDER] Sent {approved['sent']} messages")

                # Summary
                pending = len(list(self.pending_approval_dir.glob("*.md")))
                approved_count = len(list(self.approved_dir.glob("*.md")))

                logger.info(f"[STATUS] Pending approval: {pending} | Approved waiting: {approved_count}")
                logger.info(f"[WAIT] Next scan in 30 seconds... (Ctrl+C to stop)")

                await asyncio.sleep(30)

        except KeyboardInterrupt:
            logger.info("\nStopping...")
        finally:
            self.running = False
            if self.browser_context:
                await self.browser_context.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Stopped.")


def main():
    unified = UnifiedWhatsAppHITL()
    try:
        asyncio.run(unified.run())
    except KeyboardInterrupt:
        logger.info("\nExited by user")


if __name__ == "__main__":
    main()
