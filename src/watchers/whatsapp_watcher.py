"""
WhatsApp Watcher - Monitors WhatsApp Web for new messages.

Uses Playwright browser automation to monitor WhatsApp Web for unread messages.
Creates task files in /Needs_Action for each detected new message.

Safety Rules:
- Monitors only, does NOT send messages without human approval
- All outgoing messages require HITL via /Pending_Approval -> /Approved workflow
- Never writes API keys to logs or markdown files
"""
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
import hashlib

from ..config.settings import settings
from ..utils.file_utils import ensure_directory_exists
from ..utils.security import is_safe_path
from ..agents.email_processor import EmailProcessor
from ..models.trigger_file import TriggerFile, TriggerStatus

logger = logging.getLogger(__name__)


class WhatsAppWatcher:
    """Watches WhatsApp Web for unread messages and creates task files.

    This watcher uses Playwright to connect to WhatsApp Web and poll for unread
    messages at a configurable interval. For each unread message, it creates a
    markdown file in the Needs_Action directory.

    Safety: This watcher only READS messages. All outbound actions require
    human approval via the HITL workflow.
    """

    def __init__(self, poll_interval: int = 60, headless: bool = True):
        """Initialize WhatsApp watcher.

        Args:
            poll_interval: Seconds between poll cycles (default: 60)
            headless: Run browser in headless mode (default: True)
        """
        self.poll_interval = poll_interval
        self.headless = headless
        self.needs_action_path = Path(settings.NEEDS_ACTION_PATH)
        ensure_directory_exists(self.needs_action_path)
        self.running = False
        self.processed_hashes: set = set()
        self._browser = None
        self._page = None

        logger.info(
            "WhatsAppWatcher initialized (poll every %s sec, headless=%s)",
            poll_interval,
            headless
        )

    async def _initialize_browser(self) -> None:
        """Initialize Playwright browser and navigate to WhatsApp Web.

        Note: First run requires manual QR code scanning.
        Subsequent runs will use saved session if available.
        """
        try:
            from playwright.async_api import async_playwright

            playwright = await async_playwright().start()

            # Launch browser with persistent context for session persistence
            user_data_dir = Path(settings.LOGS_PATH) / "whatsapp_session"
            user_data_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Launching Chromium with user data dir: {user_data_dir}")
            try:
                self._browser = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=self.headless,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-extensions'
                    ],
                    # Add a timeout for context launch
                    timeout=60000 
                )
            except Exception as launch_error:
                logger.error(f"Chromium launch failed: {launch_error}")
                raise

            # Get or create page
            if len(self._browser.pages) > 0:
                self._page = self._browser.pages[0]
            else:
                self._page = await self._browser.new_page()

            # Navigate to WhatsApp Web
            logger.info("Navigating to https://web.whatsapp.com ...")
            await self._page.goto('https://web.whatsapp.com', wait_until='domcontentloaded')
            
            # Wait for either login (QR code) or main interface to load
            try:
                # Give it a few seconds for JS to start
                await asyncio.sleep(8)
                
                current_url = self._page.url
                logger.info(f"Current page URL: {current_url}")
                
                # Check for QR code
                logger.info("Scanning for QR code or active session...")
                
                # Try multiple selectors for the QR code or the login screen
                qr_selectors = [
                    'canvas[aria-label="Scan this QR code to link a device!"]',
                    'canvas',
                    '[data-testid="qrcode"]',
                    'div[data-ref]'
                ]
                
                found_qr = False
                for selector in qr_selectors:
                    try:
                        element = await self._page.wait_for_selector(selector, timeout=3000)
                        if element:
                            found_qr = True
                            logger.info(f"QR code element found with selector: {selector}")
                            break
                    except:
                        continue
                
                if found_qr:
                    logger.warning("!!! ACTION REQUIRED: PLEASE SCAN THE QR CODE IN THE OPENED BROWSER !!!")
                else:
                    logger.info("QR code not detected via primary selectors. Taking diagnostic screenshot...")
                    diag_path = Path(settings.LOGS_PATH) / "whatsapp_diag.png"
                    await self._page.screenshot(path=str(diag_path))
                    logger.info(f"Diagnostic screenshot saved to {diag_path}")
                
                # Wait for main interface after QR scan or if already logged in
                logger.info("Waiting for WhatsApp interface (chat list) to load...")
                await self._page.wait_for_selector(
                    '[data-testid="chat-list"]',
                    timeout=180000  # 3 minutes
                )
                logger.info("Success: WhatsApp interface loaded.")
            except Exception as e:
                # Capture screenshot on failure to help debug
                screenshot_path = Path(settings.LOGS_PATH) / "whatsapp_error.png"
                await self._page.screenshot(path=str(screenshot_path))
                logger.error(f"Failed to connect to WhatsApp Web. Diagnostic screenshot saved to {screenshot_path}")
                logger.error(f"Error detail: {str(e)}")

            logger.info("WhatsApp Web browser initialized")

        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            raise
        except Exception as e:
            logger.error("Failed to initialize browser: %s", e)
            raise

    def _create_message_hash(self, message: Dict[str, Any]) -> str:
        """Create a unique hash for a message to prevent duplicates."""
        hash_data = f"{message.get('id', '')}{message.get('timestamp', '')}{message.get('text', '')}"
        return hashlib.md5(hash_data.encode()).hexdigest()

    async def _get_unread_messages(self) -> List[Dict[str, Any]]:
        """Get list of unread messages from WhatsApp Web.

        Returns:
            List of message dictionaries with keys: id, sender, text, timestamp
        """
        messages = []

        try:
            # Find all unread chat indicators
            unread_chats = await self._page.query_selector_all('span[data-testid="icon-unread-count"]')

            for chat_indicator in unread_chats:
                try:
                    # Navigate to chat
                    chat = await chat_indicator.evaluate_handle('el => el.closest("[role=listitem]")')
                    if not chat:
                        continue

                    chat_element = chat.as_element()
                    await chat_element.click()

                    # Wait for messages to load
                    await self._page.wait_for_selector('div[data-testid="msg-container"]', timeout=5000)

                    # Get sender name
                    try:
                        sender = await self._page.text_content('[data-testid="conversation-panel-header"] span')
                        sender = sender.strip() if sender else "Unknown"
                    except:
                        sender = "Unknown"

                    # Get all unread messages (with blue dot or in this chat)
                    message_containers = await self._page.query_selector_all('div[data-testid="msg-container"]')

                    for msg_container in message_containers[-5:]:  # Get last 5 messages
                        try:
                            # Get message ID
                            msg_id = await msg_container.get_attribute('data-id') or ""

                            # Get message text
                            try:
                                text_element = await msg_container.query_selector('span.selectable-text')
                                text = await text_element.text_content() if text_element else ""
                                text = text.strip() if text else "[Media or System Message]"
                            except:
                                text = "[Could not extract text]"

                            # Get timestamp
                            try:
                                timestamp_element = await msg_container.query_selector('span[data-testid="msg-meta"]')
                                timestamp = await timestamp_element.text_content() if timestamp_element else ""
                            except:
                                timestamp = ""

                            messages.append({
                                'id': msg_id,
                                'sender': sender,
                                'text': text,
                                'timestamp': timestamp
                            })

                        except Exception as e:
                            logger.debug("Could not extract message: %s", e)
                            continue

                    # Go back to chat list
                    back_button = await self._page.query_selector('[data-testid="back"]')
                    if back_button:
                        await back_button.click()
                        await self._page.wait_for_selector('[data-testid="chat-list"]', timeout=5000)

                except Exception as e:
                    logger.debug("Could not process chat: %s", e)
                    continue

        except Exception as e:
            logger.error("Error getting unread messages: %s", e)

        return messages

    async def _create_task_file(self, message: Dict[str, Any]) -> Optional[Path]:
        """Create a task file for a WhatsApp message.

        Args:
            message: Message dictionary with id, sender, text, timestamp

        Returns:
            Path to created task file, or None if creation failed
        """
        try:
            msg_hash = self._create_message_hash(message)
            if msg_hash in self.processed_hashes:
                return None

            # Generate task ID
            timestamp = datetime.now().isoformat()
            task_id = f"WHATSAPP_{timestamp.replace(':', '-').replace('.', '-')}"

            # Create markdown content with YAML frontmatter
            content = f"""---
type: whatsapp_message
id: "{message['id']}"
sender: "{message['sender']}"
hash: "{msg_hash}"
received_at: "{message['timestamp']}"
detected_at: "{timestamp}"
status: pending
---

## Message from {message['sender']}

{message['text']}

## Actions Required
- [ ] Read and understand message
- [ ] Draft response (if needed) - will require approval
- [ ] Mark as processed
"""

            file_path = self.needs_action_path / f"{task_id}.md"

            # Safety: ensure file stays within needs_action_path
            if not is_safe_path(str(file_path), str(self.needs_action_path)):
                logger.warning("Unsafe path blocked for WhatsApp message %s", message['id'])
                return None

            file_path.write_text(content, encoding='utf-8')
            self.processed_hashes.add(msg_hash)

            logger.info("Created WhatsApp task: %s", file_path.name)
            return file_path

        except Exception as e:
            logger.error("Failed to create task file for message %s: %s", message['id'], e)
            return None

    async def _process_new_messages(self) -> int:
        """Poll for unread messages and create task files.

        Returns:
            Number of task files created
        """
        if not self._page:
            logger.warning("Browser not initialized, cannot poll")
            return 0

        try:
            messages = await self._get_unread_messages()
            created_count = 0

            for message in messages:
                task_path = await self._create_task_file(message)
                if task_path:
                    created_count += 1

                    # Trigger processing (similar to Gmail watcher)
                    try:
                        from ..models.trigger_file import TriggerStatus
                        trigger_file = TriggerFile(
                            id=message['id'],
                            filename=task_path.name,
                            type="whatsapp",
                            source_path=str(task_path),
                            status=TriggerStatus.PENDING,
                            timestamp=datetime.now(),
                            location=str(task_path)
                        )

                        # Use email processor for now (can create WhatsApp-specific processor later)
                        processor = EmailProcessor()
                        processor.process_trigger_file(trigger_file)
                    except Exception as pe:
                        logger.error("Failed to process WhatsApp task %s: %s", message['id'], pe)

            return created_count

        except Exception as e:
            logger.error("WhatsApp poll failed: %s", e)
            return 0

    async def start(self) -> None:
        """Start the WhatsApp watcher loop.

        This is an async method that runs until self.running is False.
        For CLI integration, run this in a background thread.
        """
        self.running = True

        try:
            await self._initialize_browser()
            logger.info("WhatsApp watcher started")
        except Exception as e:
            logger.error("Failed to initialize WhatsApp watcher: %s", e)
            return

        while self.running:
            try:
                count = await self._process_new_messages()
                if count > 0:
                    logger.info("WhatsApp watcher: %d new messages processed", count)
            except Exception as e:
                logger.error("WhatsApp watcher loop error: %s", e)

            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop the WhatsApp watcher."""
        self.running = False
        logger.info("WhatsApp watcher stop requested")

    async def cleanup(self) -> None:
        """Clean up browser resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None
            logger.info("WhatsApp watcher cleaned up")


def _run_watcher_in_thread(poll_interval: int = 60, headless: bool = True):
    """Run the async watcher in a synchronous thread."""
    async def _run():
        watcher = WhatsAppWatcher(poll_interval=poll_interval, headless=headless)
        try:
            await watcher.start()
        except Exception as e:
            logger.error("WhatsApp watcher thread error: %s", e)
        finally:
            await watcher.cleanup()

    # Create new event loop for this thread
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_run())


if __name__ == "__main__":
    # Run watcher synchronously for testing
    async def main():
        watcher = WhatsAppWatcher(poll_interval=30, headless=False)
        try:
            await watcher.start()
        except KeyboardInterrupt:
            logger.info("WhatsApp watcher stopped by user")
        finally:
            await watcher.cleanup()

    asyncio.run(main())