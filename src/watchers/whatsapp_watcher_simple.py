"""
Simplified WhatsApp Watcher - Detects incoming messages via WhatsApp Web.

Monitors WhatsApp Web for new messages and creates tasks in Needs_Action.
Uses Playwright to watch the web interface.
"""
import logging
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

from ..config.settings import settings
from ..utils.file_utils import ensure_directory_exists

logger = logging.getLogger(__name__)


class WhatsAppWatcherSimple:
    """Simple WhatsApp watcher that monitors for new messages."""

    def __init__(self):
        self.needs_action_dir = Path(settings.NEEDS_ACTION_PATH)
        self.logs_dir = Path(settings.LOGS_PATH)
        self.session_dir = self.logs_dir / "whatsapp_session"
        self.processed_hashes_file = self.logs_dir / "whatsapp_processed_hashes.json"

        ensure_directory_exists(self.needs_action_dir)
        ensure_directory_exists(self.session_dir)
        ensure_directory_exists(self.logs_dir)

        self.processed_hashes = self._load_processed_hashes()
        self.running = False

        if sync_playwright is None:
            raise ImportError("Playwright not installed. Run: pip install playwright")

    def _load_processed_hashes(self) -> set:
        """Load processed message hashes to avoid duplicates."""
        if self.processed_hashes_file.exists():
            try:
                data = json.loads(self.processed_hashes_file.read_text())
                return set(data)
            except:
                return set()
        return set()

    def _save_processed_hashes(self):
        """Save processed hashes."""
        self.processed_hashes_file.write_text(
            json.dumps(list(self.processed_hashes))
        )

    def _generate_hash(self, sender: str, message: str, timestamp: str) -> str:
        """Generate unique hash for a message."""
        import hashlib
        content = f"{sender}:{message}:{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()

    def _create_task_file(self, sender: str, message: str, timestamp: str) -> Path:
        """Create task file in Needs_Action."""
        # Clean sender name for filename
        clean_sender = "".join(c for c in sender if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_sender = clean_sender.replace(' ', '_')[:30]

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"WHATSAPP_{timestamp_str}_{clean_sender}.md"
        filepath = self.needs_action_dir / filename

        # Generate hash
        msg_hash = self._generate_hash(sender, message, timestamp)

        content = f"""---
type: whatsapp
sender: {sender}
message: {message[:200]}{'...' if len(message) > 200 else ''}
received: {timestamp}
hash: {msg_hash}
status: pending
---

## WhatsApp Message

**From:** {sender}
**Time:** {timestamp}

### Message Content
{message}

---

*This message needs a response. AI will generate a draft.*
"""

        filepath.write_text(content, encoding='utf-8')
        logger.info(f"Created task file: {filename}")

        # Save hash
        self.processed_hashes.add(msg_hash)
        self._save_processed_hashes()

        return filepath

    def scan_for_messages(self) -> List[Dict[str, Any]]:
        """Scan WhatsApp Web for unread messages.

        Returns:
            List of new messages found
        """
        new_messages = []

        with sync_playwright() as p:
            # Launch with persistent context
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=False,  # Need visible browser for QR if not logged in
                args=[
                    '--window-size=1400,900',
                    '--disable-blink-features=AutomationControlled',
                ]
            )

            page = context.pages[0] if context.pages else context.new_page()

            try:
                # Navigate to WhatsApp Web
                logger.info("Opening WhatsApp Web...")
                page.goto("https://web.whatsapp.com", wait_until="networkidle", timeout=120000)

                # Wait for chat list (logged in) or QR code
                try:
                    # Try to find chat list (already logged in)
                    page.wait_for_selector('[data-testid="chat-list"]', timeout=15000)
                    logger.info("Already logged in to WhatsApp Web")
                except:
                    # Need to scan QR
                    logger.info("="*60)
                    logger.info("PLEASE SCAN QR CODE")
                    logger.info("="*60)
                    logger.info("1. Look at the browser window")
                    logger.info("2. Scan QR code with your phone")
                    logger.info("3. Waiting up to 60 seconds...")
                    logger.info("="*60)

                    # Wait for login
                    page.wait_for_selector('[data-testid="chat-list"]', timeout=60000)
                    logger.info("Login successful!")

                # Wait for chats to load
                page.wait_for_timeout(3000)

                # Find unread messages
                logger.info("Scanning for unread messages...")

                # Look for unread indicators
                unread_selectors = [
                    'span[aria-label*="unread"]',
                    'span[data-testid="icon-unread-count"]',
                    'div[data-testid="cell-frame-container"] span[dir="auto"]',
                ]

                # Get all chat items
                chats = page.query_selector_all('div[data-testid="cell-frame-container"]')
                logger.info(f"Found {len(chats)} chats")

                for chat in chats[:10]:  # Check first 10 chats
                    try:
                        # Get sender name
                        title_elem = chat.query_selector('span[dir="auto"]')
                        if not title_elem:
                            continue

                        sender = title_elem.text_content() or "Unknown"

                        # Check for unread indicator
                        unread_elem = chat.query_selector('span[aria-label*="unread"]')
                        if unread_elem:
                            unread_count = unread_elem.text_content() or "1"
                            logger.info(f"Unread from {sender}: {unread_count} messages")

                            # Click to open chat
                            chat.click()
                            page.wait_for_timeout(2000)

                            # Get last few messages
                            messages = page.query_selector_all('div.message-in, div.message-out')

                            for msg in messages[-3:]:  # Last 3 messages
                                text_elem = msg.query_selector('span.selectable-text')
                                if text_elem:
                                    text = text_elem.text_content() or ""
                                    time_elem = msg.query_selector('span[data-testid="msg-meta"]')
                                    msg_time = time_elem.text_content() if time_elem else datetime.now().strftime("%H:%M")

                                    # Only process incoming messages
                                    if 'message-in' in str(msg.get_attribute('class') or ''):
                                        msg_hash = self._generate_hash(sender, text, msg_time)

                                        if msg_hash not in self.processed_hashes:
                                            new_messages.append({
                                                'sender': sender,
                                                'message': text,
                                                'timestamp': msg_time
                                            })
                                            logger.info(f"New message from {sender}: {text[:50]}...")

                            # Go back to chat list
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(500)

                    except Exception as e:
                        logger.debug(f"Error processing chat: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error scanning WhatsApp: {e}")

            finally:
                context.close()

        return new_messages

    def run_once(self) -> int:
        """Run one scan cycle.

        Returns:
            Number of new messages found
        """
        logger.info("="*60)
        logger.info("WhatsApp Watcher - Scanning for new messages")
        logger.info("="*60)

        messages = self.scan_for_messages()

        for msg in messages:
            self._create_task_file(
                msg['sender'],
                msg['message'],
                msg['timestamp']
            )

        logger.info(f"Found {len(messages)} new messages")
        return len(messages)

    def run_continuous(self, interval: int = 60):
        """Run continuous monitoring.

        Args:
            interval: Seconds between scans
        """
        self.running = True
        logger.info(f"Starting continuous monitoring (interval: {interval}s)")

        while self.running:
            try:
                count = self.run_once()
                if count > 0:
                    logger.info(f"Processed {count} new messages")

                # Wait for next scan
                for _ in range(interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except KeyboardInterrupt:
                logger.info("Stopping watcher...")
                self.running = False
            except Exception as e:
                logger.error(f"Error in watcher loop: {e}")
                time.sleep(10)

        logger.info("Watcher stopped")

    def stop(self):
        """Stop the watcher."""
        self.running = False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WhatsApp Watcher")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=60, help="Scan interval in seconds")
    args = parser.parse_args()

    watcher = WhatsAppWatcherSimple()

    if args.once:
        watcher.run_once()
    else:
        watcher.run_continuous(args.interval)
