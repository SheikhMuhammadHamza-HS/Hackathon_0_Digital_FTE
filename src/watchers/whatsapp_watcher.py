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
from ..agents.email_processor import EmailProcessor
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
    # Unread indicator - badges with numbers
    "unread_badge": [
        'span[data-testid="icon-unread-count"]',
        'span[aria-label*="unread message count"]',
        'span[aria-label*="unread count"]',
        'span[class*="unread"]',
        'div[class*="unread"]',
        'span[aria-label*="unread"]',
    ],
    # Message container - individual messages
    "message_container": [
        # WhatsApp's obfuscated class patterns (most recent as of 2026)
        'div[class*="_ak9"]',
        'div[class*="_ak7"]',
        'div[class*="_ao"]',
        'div[class*="_am"]',
        'div[role="log"]',
        'div[data-testid="msg-container"]',
        'div[data-testid="message-container"]',
        'div[class*="message-container"]',
        'div[class*="msg-container"]',
        'div[data-testid="conversation-panel-messages"]',
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
        '[data-testid="conversation-panel-header"]',
        'header[data-testid="conversation-header"]',
        'div[class*="header"]',
        'div[class*="chat-header"]',
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
            headless: Run browser in headless mode (default: True)
            max_retries: Maximum retry attempts for failed operations
            reconnect_delay: Seconds to wait before reconnection attempts
        """
        self.poll_interval = poll_interval
        self.headless = headless
        self.max_retries = max_retries
        self.reconnect_delay = reconnect_delay
        self.needs_action_path = Path(settings.NEEDS_ACTION_PATH)
        ensure_directory_exists(self.needs_action_path)
        self.running = False
        self.processed_hashes: set = set()
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
            // These are often added by Selenium/Playwright/Puppeteer
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
            logger.warning("Page not initialized")
            return messages

        try:
            logger.info("=" * 50)
            logger.info("Starting message extraction...")
            logger.info("=" * 50)

            # Step 1: Find the chat list container
            chat_list_container = None
            for selector in SELECTORS["chat_list"]:
                try:
                    el = await self._page.query_selector(selector)
                    if el and await el.is_visible():
                        chat_list_container = el
                        logger.info(f"Found chat list with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not chat_list_container:
                logger.warning("Could not find chat list!")
                # Take diagnostic screenshot
                try:
                    await self._page.screenshot(path=str(Path(settings.LOGS_PATH) / "no_chat_list.png"))
                except:
                    pass
                return messages

            # Step 2: Find all chat items in the list
            chat_items = await self._page.query_selector_all('[role="listitem"]')
            logger.info(f"Found {len(chat_items)} chat items in sidebar")

            if not chat_items:
                # Try alternative - all clickable divs in chat list
                chat_items = await chat_list_container.query_selector_all('div')
                logger.info(f"Fallback: found {len(chat_items)} divs in chat list")

            # Step 3: Find chats with unread indicators
            unread_chats = []
            for i, chat in enumerate(chat_items[:15]):  # Check first 15
                try:
                    # Check for unread badge/number
                    html = await chat.evaluate('el => el.outerHTML')
                    classes = await chat.get_attribute('class') or ''

                    # Look for unread patterns
                    has_unread = (
                        'unread' in classes.lower() or
                        '_ak' in classes or  # WhatsApp internal classes
                        await chat.query_selector('[data-testid="icon-unread-count"]') is not None or
                        await chat.query_selector('span[aria-label*="unread"]') is not None
                    )

                    if has_unread:
                        unread_chats.append(chat)
                        logger.info(f"Chat {i}: Has unread indicator")
                except Exception as e:
                    logger.debug(f"Error checking chat {i}: {e}")

            logger.info(f"Found {len(unread_chats)} chats with unread indicators")

            # If no explicit unread found, take the first few chats as potential new messages
            if not unread_chats:
                logger.info("No unread badges found - checking recent chats for new messages")
                unread_chats = chat_items[:3]  # Check first 3 chats

            # Step 4: Process each unread chat
            for i, chat in enumerate(unread_chats):
                try:
                    logger.info("-" * 30)
                    logger.info(f"Processing chat {i + 1}/{len(unread_chats)}")

                    # Get chat name before clicking
                    chat_name = "Unknown"
                    try:
                        name_el = await chat.query_selector('span[class*="title"], div[class*="title"], span[title]')
                        if name_el:
                            chat_name = await name_el.get_attribute('title') or await name_el.text_content() or "Unknown"
                            chat_name = chat_name.strip()[:100]
                    except Exception:
                        pass

                    logger.info(f"Chat name: {chat_name}")

                    # Click on the chat
                    try:
                        await chat.click()
                        await asyncio.sleep(random.uniform(1.5, 2.5))
                        logger.info("Clicked on chat")
                    except Exception as click_err:
                        logger.warning(f"Click failed: {click_err}")
                        # Try using JavaScript click
                        try:
                            await self._page.evaluate('el => el.click()', chat)
                            await asyncio.sleep(2)
                        except:
                            continue

                    # Step 5: Wait for chat to load
                    chat_loaded = False
                    for wait_attempt in range(5):
                        try:
                            # Check if chat header is visible
                            header = await self._page.query_selector('[data-testid="conversation-header"], header')
                            if header and await header.is_visible():
                                chat_loaded = True
                                logger.info(f"Chat loaded (attempt {wait_attempt + 1})")
                                break
                        except:
                            pass
                        await asyncio.sleep(1)

                    if not chat_loaded:
                        logger.warning("Chat did not load properly")
                        continue

                    # Step 6: Extract sender name from header
                    sender = chat_name
                    try:
                        # Try multiple ways to get sender name
                        for header_selector in [
                            '[data-testid="conversation-header"]',
                            'header [class*="title"]',
                            'header span',
                            '[data-testid="conversation-panel-header"]'
                        ]:
                            header_el = await self._page.query_selector(header_selector)
                            if header_el:
                                text = await header_el.text_content()
                                if text and text.strip() and text.strip() != "Hamza Digital FTE":
                                    sender = text.strip()[:100]
                                    logger.info(f"Sender from header: {sender}")
                                    break
                    except Exception as e:
                        logger.debug(f"Failed to get sender: {e}")

                    # Step 7: Get messages from chat
                    logger.info("Extracting messages...")

                    # Try to find message container
                    msg_containers = []
                    for msg_selector in [
                        'div[role="log"]',
                        'div[data-testid="message-container"]',
                        'div[data-testid="msg-container"]',
                        'div[class*="message-container"]',
                        'div[class*="msg-container"]'
                    ]:
                        try:
                            containers = await self._page.query_selector_all(msg_selector)
                            if containers:
                                msg_containers = containers
                                logger.info(f"Found {len(msg_containers)} messages with: {msg_selector}")
                                break
                        except:
                            continue

                    # Fallback: get all message-like divs
                    if not msg_containers:
                        logger.info("Trying fallback message extraction...")
                        # Get the main chat area content
                        all_divs = await self._page.query_selector_all('div')
                        for div in all_divs[-30:]:  # Check last 30 divs
                            try:
                                text = await div.text_content()
                                if text and len(text.strip()) > 5:
                                    classes = await div.get_attribute('class') or ''
                                    # Check if it looks like a message
                                    if '_ao' in classes or 'message' in classes.lower():
                                        msg_containers.append(div)
                            except:
                                continue
                        logger.info(f"Fallback: found {len(msg_containers)} potential messages")

                    # Step 8: Process messages (get last few)
                    if msg_containers:
                        messages_to_check = msg_containers[-10:]  # Last 10 messages
                        logger.info(f"Processing {len(messages_to_check)} recent messages")

                        for msg_idx, msg_container in enumerate(messages_to_check):
                            try:
                                # Extract message text
                                message_text = ""
                                for text_selector in [
                                    'span.selectable-text',
                                    'span[class*="selectable"]',
                                    'div[class*="text"]',
                                    'span[data-testid="message-text"]'
                                ]:
                                    try:
                                        text_el = await msg_container.query_selector(text_selector)
                                        if text_el:
                                            content = await text_el.text_content()
                                            if content and content.strip():
                                                message_text = content.strip()
                                                break
                                    except:
                                        continue

                                # Fallback: get all text from container
                                if not message_text:
                                    try:
                                        message_text = await msg_container.text_content()
                                        message_text = message_text.strip() if message_text else ""
                                    except:
                                        pass

                                if not message_text:
                                    continue

                                # Get timestamp
                                timestamp = ""
                                for time_selector in [
                                    'span[aria-label]',
                                    'span[class*="meta"]',
                                    'span[data-testid="msg-meta"]'
                                ]:
                                    try:
                                        time_el = await msg_container.query_selector(time_selector)
                                        if time_el:
                                            ts = await time_el.get_attribute('aria-label') or await time_el.text_content()
                                            if ts:
                                                timestamp = ts.strip()
                                                break
                                    except:
                                        continue

                                # Get message ID if available
                                msg_id = await msg_container.get_attribute('data-id') or ""
                                if not msg_id:
                                    msg_id = f"{sender}_{message_text[:20]}_{timestamp}"

                                # Create message dict
                                msg_hash = hashlib.md5(
                                        f"{msg_id}{message_text}{timestamp}".encode()
                                    ).hexdigest()

                                message = {
                                    'id': msg_id,
                                    'sender': sender,
                                    'text': message_text[:5000],
                                    'timestamp': timestamp,
                                    'hash': msg_hash
                                }

                                # Avoid duplicates
                                if msg_hash not in [m.get('hash', '') for m in messages]:
                                    messages.append(message)
                                    logger.info(f"✓ Extracted message {msg_idx + 1}: {message_text[:50]}...")
                                else:
                                    logger.debug(f"Duplicate message skipped: {message_text[:30]}")

                            except Exception as e:
                                logger.debug(f"Error processing message {msg_idx}: {e}")
                                continue
                    else:
                        logger.warning("No message containers found!")

                    # Step 9: Go back to chat list
                    try:
                        back_btn = await self._page.query_selector('[data-testid="back"], [data-testid="chevron-left"]')
                        if back_btn and await back_btn.is_visible():
                            await back_btn.click()
                            await asyncio.sleep(1)
                            logger.info("Returned to chat list")
                    except:
                        # Navigate back to chat list via URL
                        await self._page.goto("https://web.whatsapp.com", timeout=30000)
                        await asyncio.sleep(3)

                except Exception as e:
                    logger.error(f"Error processing chat {i}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    continue

            logger.info("=" * 50)
            logger.info(f"Extraction complete: {len(messages)} messages found")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            import traceback
            logger.debug(traceback.format_exc())

        return messages

    async def _create_task_file(self, message: Dict[str, Any]) -> Optional[Path]:
        """Create a task file for a WhatsApp message."""
        try:
            msg_hash = self._create_message_hash(message)
            if msg_hash in self.processed_hashes:
                logger.debug("Message already processed: %s", msg_hash)
                return None

            # Extract message data with defaults
            msg_id = message.get('id', '') or f"msg_{int(time.time())}"
            sender = message.get('sender', 'Unknown')
            msg_text = message.get('text', '')
            msg_timestamp = message.get('timestamp', '')

            timestamp = datetime.now().isoformat()
            task_id = f"WHATSAPP_{timestamp.replace(':', '-').replace('.', '-')}"

            content = f"""---
type: whatsapp_message
id: "{msg_id}"
sender: "{sender}"
hash: "{msg_hash}"
received_at: "{msg_timestamp}"
detected_at: "{timestamp}"
status: pending
---

## Message from {sender}

{msg_text}

## Actions Required
- [ ] Read and understand message
- [ ] Draft response (if needed) - will require approval
- [ ] Mark as processed
"""

            file_path = self.needs_action_path / f"{task_id}.md"

            if not is_safe_path(str(file_path), str(self.needs_action_path)):
                logger.warning("Unsafe path blocked for message %s", msg_id)
                return None

            file_path.write_text(content, encoding='utf-8')
            self.processed_hashes.add(msg_hash)

            logger.info("✓ Created task file: %s", file_path.name)
            logger.info("  - Sender: %s", sender)
            logger.info("  - Message: %s", msg_text[:100] + "..." if len(msg_text) > 100 else msg_text)
            return file_path

        except Exception as e:
            logger.error("Failed to create task file: %s", e)
            import traceback
            logger.debug(traceback.format_exc())
            return None

    async def _process_new_messages(self) -> int:
        """Poll for unread messages and create task files."""
        if not self._page:
            logger.warning("Browser not initialized")
            return 0

        try:
            messages = await self._get_unread_messages()
            created_count = 0

            for message in messages:
                # Skip if already processed
                msg_hash = self._create_message_hash(message)
                if msg_hash in self.processed_hashes:
                    continue

                task_path = await self._create_task_file(message)
                if task_path:
                    created_count += 1

                    # Process the message
                    try:
                        trigger_file = TriggerFile(
                            id=message.get('id', ''),
                            filename=task_path.name,
                            type="whatsapp",
                            source_path=str(task_path),
                            status=TriggerStatus.PENDING,
                            timestamp=datetime.now(),
                            location=str(task_path)
                        )

                        processor = EmailProcessor()
                        processor.process_trigger_file(trigger_file)
                    except Exception as pe:
                        logger.error("Failed to process task %s: %s", task_path.name, pe)

            if created_count > 0:
                logger.info("Processed %d new messages", created_count)
                self._last_successful_poll = datetime.now()

            return created_count

        except Exception as e:
            logger.error("Poll failed: %s", e)
            return 0

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