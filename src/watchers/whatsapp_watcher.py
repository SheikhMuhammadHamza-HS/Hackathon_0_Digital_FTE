"""
WhatsApp Watcher - Monitors WhatsApp Web for new messages.

Uses Playwright browser automation to monitor WhatsApp Web for unread messages.
Creates task files in /Needs_Action for each detected new message.

Safety Rules:
- Monitors only, does NOT send messages without human approval
- All outgoing messages require HITL via /Pending_Approval -> /Approved workflow
- Never writes API keys to logs or markdown files

Anti-Detection & Resilience Features:
- Multiple stealth layers to bypass automation detection
- Selector fallback system for UI changes
- Auto-reconnect on session loss
- Health monitoring and graceful degradation
- Message hashing for duplicate prevention (persistent across restarts)
"""
import asyncio
import logging
import random
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import hashlib
import json

from ..config.settings import settings
from ..utils.file_utils import ensure_directory_exists
from ..utils.security import is_safe_path
from ..models.trigger_file import TriggerFile, TriggerStatus

logger = logging.getLogger(__name__)


# WhatsApp Web selectors - organized by stability (most stable first)
# These are tried in order until one works
SELECTORS = {
    # Chat list container - most reliable indicators
    "chat_list": [
        '[data-testid="chat-list"]',
        'div[role="grid"]',
        '[aria-label="Chat list"]',
        '#pane-side',
        'div[data-testid="pane-side"]',
        'div._ak7l',
        'div._ak7m',
        'div[class*="pane-side"]',
    ],
    # QR code - login detection
    "qr_code": [
        'canvas[aria-label*="Scan this QR code"]',
        'canvas[aria-label="Scan this QR code to link a device!"]',
        '[data-testid="qrcode"]',
        'div[data-ref]',
        'div._akau',
        'div._akav',
        'canvas',
        'div[class*="qrcode"]',
        'div[class*="QRCode"]',
    ],
    # Unread indicator - badges with numbers (Strict version)
    "unread_badge": [
        'span[data-testid="icon-unread-count"]',
        'span[aria-label*="unread"]',
        'span[class*="unread"]',
        'div[class*="unread_"]'
    ],
    # Message container - individual messages
    "message_container": [
        'div[data-testid="msg-container"]',
        'div[class*="_ak8j"]',
        'div[class*="_ak8h"]',
        'div[role="row"]',
        'div[class*="message-in"]',
        'div[class*="message-out"]',
    ],
    # Chat list items
    "chat_item": [
        '[data-testid="chat-list-item"]',
        '[role="listitem"]',
        'div._ak72',
        'div._ak73',
    ],
    # Message text - selectable content
    "message_text": [
        'span.selectable-text',
        'span[dir="ltr"]',
        'div[dir="ltr"]',
        'span[class*="selectable"]',
        'div[class*="message-text"]',
        'div[class*="msg-text"]',
        'span[data-testid="message-text"]',
    ],
    # Sender name in chat header
    "chat_header": [
        'header [title]',
        'header span[dir="auto"]',
        '[data-testid="conversation-header"]',
    ],
    # Back button to return to chat list
    "back_button": [
        '[data-testid="back"]',
        '[data-testid="chevron-left"]',
        'button[aria-label="Back"]',
        'span[data-testid="back"]',
        'div[class*="back"]',
    ],
    # Timestamp in messages
    "message_time": [
        'span[data-testid="msg-meta"]',
        'span[class*="meta"]',
        'span[class*="timestamp"]',
        'span[aria-label*="time"]',
    ],
    # Verification: logged in state
    "logged_in": [
        'div[data-testid="chat-list"]',
        '[aria-label="Chat list"]',
        '#pane-side',
        'div[data-testid="pane-side"]',
        'span[data-testid="online"]',
        'span[aria-label*="online"]',
    ],
}


class WhatsAppWatcher:
    """Watches WhatsApp Web for unread messages and creates task files.

    This watcher uses Playwright to connect to WhatsApp Web and poll for unread
    messages at a configurable interval. For each unread message, it creates a
    markdown file in the Needs_Action directory.

    Safety: This watcher only READS messages. All outbound actions require
    human approval via the HITL workflow.
    """

    def __init__(self, poll_interval: int = 60, headless: bool = False,
                 max_retries: int = 3, reconnect_delay: int = 10):
        """Initialize WhatsApp watcher.

        Args:
            poll_interval: Seconds between poll cycles (default: 60)
            headless: Run browser in headless mode (default: False for QR scan)
            max_retries: Maximum retry attempts for failed operations
            reconnect_delay: Seconds to wait before reconnection attempts
        """
        self.poll_interval = poll_interval
        self.headless = headless
        self.max_retries = max_retries
        self.reconnect_delay = reconnect_delay
        self.needs_action_path = Path(settings.NEEDS_ACTION_PATH)
        ensure_directory_exists(self.needs_action_path)

        # Load processed hashes from persistent storage
        self.processed_hashes: set = set()
        self._load_processed_hashes()

        self.running = False
        self._browser = None
        self._page = None
        self._context = None
        self._playwright = None
        self._consecutive_errors = 0
        self._max_consecutive_errors = 5
        self._last_successful_poll: Optional[datetime] = None
        self._session_valid = False

        logger.info(
            "WhatsAppWatcher initialized (poll=%ds, headless=%s, max_retries=%d)",
            poll_interval, headless, max_retries
        )

    def _get_processed_hashes_path(self) -> Path:
        """Get path to processed hashes storage file."""
        logs_path = Path(settings.LOGS_PATH)
        logs_path.mkdir(parents=True, exist_ok=True)
        return logs_path / "whatsapp_processed_hashes.json"

    def _load_processed_hashes(self) -> None:
        """Load processed message hashes from persistent storage."""
        try:
            hashes_path = self._get_processed_hashes_path()
            if hashes_path.exists():
                with open(hashes_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_hashes = set(data.get('hashes', []))
                logger.info(f"Loaded {len(self.processed_hashes)} processed message hashes")
        except Exception as e:
            logger.warning(f"Failed to load processed hashes: {e}")
            self.processed_hashes = set()

    def _save_processed_hashes(self) -> None:
        """Save processed message hashes to persistent storage."""
        try:
            hashes_path = self._get_processed_hashes_path()
            with open(hashes_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'hashes': list(self.processed_hashes),
                    'last_updated': datetime.now().isoformat()
                }, f)
        except Exception as e:
            logger.warning(f"Failed to save processed hashes: {e}")

    def _get_stealth_script(self) -> str:
        """Generate comprehensive stealth script to evade detection."""
        return """
            // ==========================================
            // ANTI-DETECTION STEALTH SCRIPT
            // ==========================================

            // 1. Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                set: undefined,
                configurable: false
            });

            // 2. Remove automation indicators
            window.cdc_abc = undefined;
            window.cdc_asd = undefined;
            window._selenium = undefined;
            window._phantom = undefined;
            window.callSelenium = undefined;
            window.domAutomation = undefined;
            window.domAutomationController = undefined;

            // 3. Mock plugins (make browser look like normal Chrome)
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5].map(i => ({
                    name: 'Chrome PDF Plugin',
                    filename: 'internal-pdf-viewer',
                    description: i === 0 ? 'Portable Document Format' : 'Internal PDF Viewer',
                    version: '1.0.0',
                    length: 1
                })),
                configurable: false
            });

            // 4. Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'en-GB'],
                configurable: false
            });
            Object.defineProperty(navigator, 'language', {
                get: () => 'en-US',
                configurable: false
            });
            Object.defineProperty(navigator, 'userLanguage', {
                get: () => 'en-US',
                configurable: false
            });

            // 5. Mock hardware concurrency (CPU cores)
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
                configurable: false
            });

            // 6. Mock device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
                configurable: false
            });

            // 7. Mock connection type (if available)
            if (navigator.connection) {
                Object.defineProperty(navigator.connection, 'effectiveType', {
                    get: () => '4g',
                    configurable: false
                });
                Object.defineProperty(navigator.connection, 'downlink', {
                    get: () => 10,
                    configurable: false
                });
            }

            // 8. Mock screen properties
            Object.defineProperty(screen, 'colorDepth', {
                get: () => 24,
                configurable: false
            });
            Object.defineProperty(screen, 'pixelDepth', {
                get: () => 24,
                configurable: false
            });

            // 9. Mock permissions
            const originalQuery = window.Notification?.requestPermission;
            window.Notification = {
                requestPermission: async () => 'default',
                permission: 'default'
            };

            // 10. Remove automation-specific event listeners
            if (window.EventTarget) {
                const originalAdd = EventTarget.prototype.addEventListener;
                EventTarget.prototype.addEventListener = function(type, listener, options) {
                    if (type === 'beforeunload' || type === 'unload') {
                        return; // Skip automation-related listeners
                    }
                    return originalAdd.apply(this, arguments);
                };
            }

            // 11. Mock iframe creation detection
            const originalCreate = document.createElement;
            document.createElement = function(tagName, options) {
                const el = originalCreate.apply(document, arguments);
                if (tagName.toLowerCase() === 'iframe') {
                    Object.defineProperty(el, 'contentWindow', {
                        get: () => ({
                            navigator: window.navigator,
                            location: window.location,
                            document: window.document
                        })
                    });
                }
                return el;
            };

            // 12. Add fake mouse/touch events capability
            Object.defineProperty(navigator, 'maxTouchPoints', {
                get: () => 0,
                configurable: false
            });

            // 13. Override clipboard API if present
            if (navigator.clipboard) {
                navigator.clipboard.read = async () => ({ data: '' });
                navigator.clipboard.write = async () => {};
            }

            // 14. Mock IndexedDB
            const originalIDB = window.indexedDB;
            window.indexedDB = originalIDB;

            // 15. Randomize canvas fingerprint slightly
            const originalGet = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type) {
                if (type === '2d') {
                    const ctx = originalGet.apply(this, arguments);
                                            // Slightly randomize rendering to avoid fingerprinting
                    const originalFill = ctx.fillText;
                    ctx.fillText = function(text, x, y) {
                        return originalFill.apply(this, [
                            text,
                            x + (Math.random() - 0.5) * 0.1,
                            y + (Math.random() - 0.5) * 0.1
                        ]);
                    };
                    return ctx;
                }
                return originalGet.apply(this, arguments);
            };

            // 16. Override Date to add slight randomness
            const originalNow = Date.now;
            Date.now = function() {
                const base = originalNow();
                return base + Math.floor((Math.random() - 0.5) * 100);
            };

            console.log('[Stealth] Anti-detection script applied successfully');
        """

    async def _try_selectors(self, selectors: List[str], action: str = "find",
                            timeout: int = 5000) -> Tuple[Optional[Any], Optional[str]]:
        """Try multiple selectors until one works.

        Args:
            selectors: List of selectors to try
            action: Action to perform - "find", "click", "text"
            timeout: Timeout per selector

        Returns:
            Tuple of (result, working_selector)
        """
        for selector in selectors:
            try:
                element = await self._page.query_selector(selector)
                if element:
                    logger.debug(f"Selector '{selector}' worked for {action}")
                    if action == "click":
                        await element.click()
                    return element, selector
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed: {e}")
                continue
        return None, None

    async def _is_logged_in(self) -> bool:
        """Check if currently logged into WhatsApp Web."""
        for selector in SELECTORS["logged_in"]:
            try:
                element = await self._page.query_selector(selector)
                if element and await element.is_visible():
                    logger.debug(f"Login confirmed via selector: {selector}")
                    return True
            except Exception:
                continue
        return False

    async def _wait_for_login(self, timeout: int = 180) -> bool:
        """Wait for login (QR scan) with timeout.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if logged in, False if timed out
        """
        logger.info(f"Waiting for WhatsApp login (timeout: {timeout}s)...")

        start_time = time.time()
        last_qr_time = 0

        while time.time() - start_time < timeout:
            # Check for QR code first
            has_qr, _ = await self._try_selectors(SELECTORS["qr_code"], "find")

            if has_qr:
                last_qr_time = time.time()
                logger.info("QR code detected - please scan it")
                qr_path = Path(settings.LOGS_PATH) / "whatsapp_qr.png"
                try:
                    await self._page.screenshot(path=str(qr_path))
                    logger.info(f"QR screenshot saved: {qr_path}")
                except Exception as e:
                    logger.warning(f"Failed to save QR screenshot: {e}")

                # Wait for QR scan
                await asyncio.sleep(10)

                # Check if still showing QR
                still_qr, _ = await self._try_selectors(SELECTORS["qr_code"], "find")
                if still_qr:
                    logger.info("QR still visible - waiting for scan...")
                    continue

            # Check if logged in
            if await self._is_logged_in():
                logger.info("Successfully logged in!")
                return True

            # Periodic status update
            elapsed = int(time.time() - start_time)
            if elapsed > 0 and elapsed % 30 == 0 and elapsed != last_qr_time:
                logger.info(f"Still waiting... ({elapsed}s elapsed)")

            await asyncio.sleep(3)

        logger.warning("Login timeout reached")
        return False

    async def _initialize_browser(self) -> bool:
        """Initialize Playwright browser with maximum stealth.

        Returns:
            True if successful, False otherwise
        """
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()

            user_data_dir = Path(settings.LOGS_PATH) / "whatsapp_session"
            user_data_dir.mkdir(parents=True, exist_ok=True)

            # Modern user agent with realistic properties
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            )

            logger.info(f"Launching browser (headless={self.headless})...")

            # Launch with persistent context
            try:
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=self.headless,
                    user_agent=user_agent,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-blink-features',
                        '--disable-infobars',
                        '--window-position=0,0',
                        '--window-size=1600,900',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--ignore-certificate-errors',
                        '--disable-extensions',
                        '--disable-component-extensions-with-background-pages',
                        '--disable-background-networking',
                        '--disable-sync',
                        '--disable-translate',
                        '--metrics-recording-only',
                        '--mute-audio',
                        '--no-service-autorun',
                        '--safebrowsing-disable-auto-update',
                        '--enable-ocr',
                        '--disable-software-rasterizer',
                        '--disable-gpu',
                    ],
                    viewport={'width': 1600, 'height': 900},
                    ignore_default_args=['--enable-automation', '--mute-audio'],
                    java_script_enabled=True,
                    locale='en-US',
                    timezone_id='UTC',
                    color_scheme='light',
                )
            except Exception as launch_error:
                logger.error(f"Persistent context failed: {launch_error}")
                # Fallback to regular browser
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--no-first-run',
                    ]
                )
                self._context = await self._browser.new_context(
                    user_agent=user_agent,
                    viewport={'width': 1600, 'height': 900},
                    locale='en-US',
                )

            # Get or create page
            if self._context.pages:
                self._page = self._context.pages[0]
            else:
                self._page = await self._context.new_page()

            # Apply stealth script
            await self._page.add_init_script(self._get_stealth_script())

            # Additional CDP commands for stealth
            try:
                await self._page.cdp_send_command('Network.setUserAgentOverride', {
                    'userAgent': user_agent
                })
            except Exception:
                pass  # CDP may not be available

            # Navigate to WhatsApp Web
            logger.info("Navigating to WhatsApp Web...")
            await self._page.goto(
                "https://web.whatsapp.com",
                wait_until="domcontentloaded",
                timeout=60000
            )

            # Wait for page to stabilize
            await asyncio.sleep(3)

            # Check login status
            if await self._is_logged_in():
                logger.info("Session restored - already logged in!")
                self._session_valid = True
                return True

            # Wait for login
            self._session_valid = await self._wait_for_login(timeout=180)

            return self._session_valid

        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return False
        except Exception as e:
            logger.error(f"Browser initialization failed: {e}")
            return False

    async def _refresh_session_if_needed(self) -> bool:
        """Check and refresh session if needed.

        Returns:
            True if session is valid, False if re-login needed
        """
        try:
            # Check if page is still accessible
            if not self._page or self._page.is_closed():
                logger.warning("Page closed - reconnecting...")
                return False

            # Check for connection issues
            try:
                await self._page.evaluate('1 + 1')
            except Exception:
                logger.warning("Page unresponsive - reconnecting...")
                return False

            # Check for login state
            if not await self._is_logged_in():
                logger.warning("Session expired - re-login needed")
                return False

            return True

        except Exception as e:
            logger.error(f"Session check failed: {e}")
            return False

    async def _reconnect(self) -> bool:
        """Attempt to reconnect to WhatsApp Web.

        Returns:
            True if reconnected successfully
        """
        logger.info("Attempting to reconnect...")

        # Clean up old session
        try:
            await self.cleanup()
        except Exception:
            pass

        # Wait before reconnecting
        await asyncio.sleep(self.reconnect_delay)

        # Try to reinitialize
        success = await self._initialize_browser()

        if success:
            self._consecutive_errors = 0
            logger.info("Reconnected successfully!")
        else:
            self._consecutive_errors += 1
            logger.error(f"Reconnect failed ({self._consecutive_errors}/{self._max_consecutive_errors})")

        return success

    def _create_message_hash(self, message: Dict[str, Any]) -> str:
        """Create a unique hash for a message to prevent duplicates."""
        hash_data = f"{message.get('id', '')}{message.get('timestamp', '')}{message.get('text', '')}"
        return hashlib.md5(hash_data.encode()).hexdigest()

    async def _get_unread_messages(self) -> List[Dict[str, Any]]:
        """Get list of unread messages from WhatsApp Web.
        
        Returns:
           List of message dictionaries
        """
        messages = []
        if not self._page:
            return messages

        try:
            logger.info("=" * 50)
            logger.info("Checking for NEW unread messages...")
            logger.info("=" * 50)

            # Step 1: Find all chat items in the sidebar
            # We look for containers that represent a single chat row
            chat_selectors = ['[role="listitem"]', '[data-testid="chat-list-item"]', 'div._ak72', 'div._ak73']
            chat_items = []
            for sel in chat_selectors:
                items = await self._page.query_selector_all(sel)
                if items:
                    chat_items = items
                    break
            
            if not chat_items:
                logger.info("No chat items found in sidebar.")
                return []

            # Step 2: Identify chats with explicit unread badges
            unread_targets = []
            seen_names = set()
            
            for i, chat in enumerate(chat_items[:20]): # Check top 20 chats
                try:
                    # Look for unread count badge (green circle)
                    badge = await chat.query_selector('[data-testid="icon-unread-count"], span[aria-label*="unread"]')
                    if not badge:
                        continue
                    
                    # Verify it has numeric or text content indicating a new message
                    badge_text = await badge.text_content()
                    if not badge_text and 'unread' not in (await badge.get_attribute('aria-label') or '').lower():
                        continue
                        
                    # Get chat name FROM SIDEBAR (Source of Truth)
                    name_el = await chat.query_selector('span[title], [class*="title"]')
                    chat_name = "Unknown"
                    if name_el:
                        chat_name = (await name_el.get_attribute('title') or await name_el.text_content() or "Unknown").strip()
                    
                    if chat_name in seen_names:
                        continue
                        
                    unread_targets.append((chat, chat_name))
                    seen_names.add(chat_name)
                    logger.info(f"Detected {badge_text or 'new'} messages in chat: '{chat_name}'")
                except: continue

            if not unread_targets:
                logger.info("No unread badges found.")
                return []

            # Step 3: Process identified chats
            for idx, (chat_el, chat_name) in enumerate(unread_targets):
                try:
                    logger.info(f"Processing chat {idx+1}/{len(unread_targets)}: {chat_name}")
                    
                    # Click chat to open
                    await chat_el.scroll_into_view_if_needed()
                    await chat_el.click()
                    await asyncio.sleep(2) # Wait for panel to load
                    
                    # Verify sender name from the opened header (if it matches or is better)
                    sender = chat_name
                    header_name_el = await self._page.query_selector('header [title], header span[dir="auto"]')
                    if header_name_el:
                        header_text = (await header_name_el.get_attribute('title') or await header_name_el.text_content() or "").strip()
                        if header_text and len(header_text) > 1 and 'refreshed' not in header_text.lower():
                            sender = header_text
                    
                    # Extract last message
                    msg_text = ""
                    msg_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Find message containers
                    msg_containers = await self._page.query_selector_all('[data-testid="msg-container"], .message-in, ._ak8j, ._ak8h')
                    if msg_containers:
                        # Process only the LATEST message
                        latest_msg = msg_containers[-1]
                        
                        # Target text span specifically
                        text_span = await latest_msg.query_selector('span.selectable-text, [data-testid="selectable-text"]')
                        if text_span:
                            msg_text = (await text_span.text_content() or "").strip()
                        
                        # If failed, try raw text but filter metadata
                        if not msg_text:
                            raw = (await latest_msg.text_content() or "").strip()
                            # Remove trailing time indicators (e.g. "10:30 PM")
                            import re
                            msg_text = re.sub(r'\d{1,2}:\d{2}\s?(?:AM|PM)?$', '', raw).strip()
                            
                        # Filter system/junk strings
                        junk = ['forwarded', 'unread message', 'status-dblcheck', 'encryption', 'typing...', 'audio-play']
                        if any(j in msg_text.lower() for j in junk) or len(msg_text) < 1:
                            logger.info(f"Skipped system/junk message: {msg_text[:30]}...")
                            continue

                        # Get message ID for hashing
                        msg_id = await latest_msg.get_attribute('data-id') or f"{sender}_{hash(msg_text)}"
                        msg_hash = hashlib.md5(f"{msg_id}{msg_text}".encode()).hexdigest()
                        
                        if msg_hash not in self.processed_hashes:
                            messages.append({
                                'id': msg_id,
                                'sender': sender,
                                'text': msg_text,
                                'timestamp': msg_timestamp,
                                'hash': msg_hash
                            })
                            logger.info(f"✓ New message from {sender}: {msg_text[:50]}...")
                        else:
                            logger.debug(f"Message already processed: {msg_text[:30]}")
                            
                    # Deselect chat by pressing Escape or clicking search
                    await self._page.keyboard.press('Escape')
                    await asyncio.sleep(0.5)
                    await self._page.keyboard.press('Escape')
                    
                except Exception as e:
                    logger.error(f"Error processing chat '{chat_name}': {e}")
                    continue

            return messages

        except Exception as e:
            logger.error(f"Extraction loop error: {e}")
            return []

    def _create_task_file(self, message: Dict[str, Any]) -> Optional[Path]:
        """Create a markdown task file for a WhatsApp message.
        
        Args:
            message: Message dictionary with sender, text, etc.
            
        Returns:
            Path to the created file, or None if skipped/failed
        """
        try:
            msg_id = message.get('id', 'unknown')
            sender = message.get('sender', 'Unknown')
            msg_text = message.get('text', '')
            msg_timestamp = message.get('timestamp', '')
            msg_hash = message.get('hash', '')

            # Check for existing hash
            if msg_hash in self.processed_hashes:
                return None

            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            # Clean sender name for filename
            safe_sender = "".join(c if c.isalnum() or c in '-_' else '_' for c in sender)[:30]
            task_id = f"WHATSAPP_{timestamp}_{safe_sender}"

            content = f"""---
type: whatsapp_message
id: "{msg_id}"
sender: "{sender}"
hash: "{msg_hash}"
received_at: "{msg_timestamp}"
detected_at: "{timestamp}"
status: pending
platform: whatsapp
---

## WhatsApp Message from {sender}

**Received:** {msg_timestamp}

### Message Content

{msg_text}

---

## Actions Required
- [ ] Read and understand message
- [ ] Generate contextual response using Gemini AI
- [ ] Save draft to Pending_Approval for human review
- [ ] Mark as processed
"""
            file_path = self.needs_action_path / f"{task_id}.md"
            file_path.write_text(content, encoding='utf-8')
            
            self.processed_hashes.add(msg_hash)
            self._save_processed_hashes()
            
            logger.info("✓ Created task file: %s", file_path.name)
            return file_path
        except Exception as e:
            logger.error(f"Failed to create task file: {e}")
            return None

    async def _process_new_messages(self) -> int:
        """Poll for unread messages and create task files."""
        if not self._page:
            logger.warning("Browser not initialized")
            return 0

        created_count = 0
        retry_count = 0
        max_extraction_retries = 3

        while retry_count < max_extraction_retries:
            try:
                messages = await self._get_unread_messages()

                for message in messages:
                    # Skip if already processed
                    msg_hash = self._create_message_hash(message)
                    if msg_hash in self.processed_hashes:
                        continue

                    task_path = await self._create_task_file(message)
                    if task_path:
                        created_count += 1

                if created_count > 0:
                    logger.info("Processed %d new messages", created_count)
                    self._last_successful_poll = datetime.now()

                # Success - break out of retry loop
                break

            except Exception as e:
                retry_count += 1
                logger.error(f"Poll attempt {retry_count} failed: {e}")

                if retry_count >= max_extraction_retries:
                    logger.error("Max extraction retries reached")
                    break

                # Wait before retry with exponential backoff
                await asyncio.sleep(2 ** retry_count)

        return created_count

    async def start(self) -> None:
        """Start the WhatsApp watcher loop."""
        self.running = True
        reconnect_count = 0

        logger.info("WhatsApp watcher starting...")

        # Initial browser setup
        if not await self._initialize_browser():
            logger.error("Failed to initialize browser")
            return

        logger.info("WhatsApp watcher running")

        while self.running:
            try:
                # Check if we need to reconnect
                if not await self._refresh_session_if_needed():
                    reconnect_count += 1
                    if reconnect_count > self.max_retries:
                        logger.error("Max reconnection attempts reached")
                        break

                    if not await self._reconnect():
                        await asyncio.sleep(self.reconnect_delay * 2)
                        continue

                    reconnect_count = 0

                # Poll for messages
                count = await self._process_new_messages()

                # Reset error count on success
                if count >= 0:
                    self._consecutive_errors = 0

            except Exception as e:
                logger.error("Watcher loop error: %s", e)
                self._consecutive_errors += 1

                if self._consecutive_errors >= self._max_consecutive_errors:
                    logger.error("Too many consecutive errors - attempting reconnect")
                    if not await self._reconnect():
                        logger.error("Reconnect failed - stopping watcher")
                        break

            await asyncio.sleep(self.poll_interval)

        logger.info("WhatsApp watcher stopped")

    def stop(self) -> None:
        """Stop the WhatsApp watcher."""
        self.running = False
        logger.info("Stop requested")

    async def cleanup(self) -> None:
        """Clean up browser resources."""
        try:
            if self._context:
                await self._context.close()
                self._context = None
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            self._page = None
            logger.info("Cleanup complete")
        except Exception as e:
            logger.error("Cleanup error: %s", e)


def _run_watcher_in_thread(poll_interval: int = 60, headless: bool = True):
    """Run the async watcher in a synchronous thread."""
    async def _run():
        watcher = WhatsAppWatcher(poll_interval=poll_interval, headless=headless)
        try:
            await watcher.start()
        except Exception as e:
            logger.error("Watcher thread error: %s", e)
        finally:
            await watcher.cleanup()

    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_run())


if __name__ == "__main__":
    async def main():
        watcher = WhatsAppWatcher(poll_interval=30, headless=False)
        try:
            await watcher.start()
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        finally:
            await watcher.cleanup()

    asyncio.run(main())
