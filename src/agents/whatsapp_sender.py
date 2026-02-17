"""
WhatsApp Sender - Handles sending WhatsApp messages via Playwright or MCP.

This module provides functionality to send WhatsApp messages using either:
1. Direct Playwright browser automation (preferred for session persistence)
2. MCP whatsapp-mcp server (if available)
3. Mock mode (for development/testing)

Safety: Only sends messages that have been explicitly approved by human review.
All messages must go through the Pending_Approval -> Approved workflow.
"""
import logging
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Optional,Tuple
from datetime import datetime

from ..config.settings import settings
from ..services.mcp_client import get_mcp_manager
from ..utils.security import is_safe_path

logger = logging.getLogger(__name__)


class WhatsAppSender:
    """Agent responsible for sending WhatsApp messages via Playwright or MCP.

    This sender supports multiple modes:
    - playwrite: Direct browser automation (maintains session with watcher)
    - mcp: Use MCP whatsapp-mcp server
    - mock: Simulation mode for testing
    """

    def __init__(self, mode: str = "auto"):
        """Initialize the WhatsApp sender.

        Args:
            mode: Sending mode - 'playwright', 'mcp', 'mock', or 'auto' (default: auto)
                  'auto' tries playwright first, then mcp, then mock
        """
        self.mode = mode
        self.mcp_manager = get_mcp_manager()
        self._playwright_page = None  # Shared page instance if available
        self._last_send_time = 0
        self._min_send_interval = 2  # Minimum seconds between sends (rate limiting)

        logger.info(f"WhatsAppSender initialized (mode={mode})")

    def set_playwright_page(self, page):
        """Set a shared Playwright page instance for sending.

        This allows the sender to use the same browser session as the watcher,
        avoiding repeated QR code scanning.

        Args:
            page: Playwright page object
        """
        self._playwright_page = page
        logger.debug("Playwright page set for WhatsAppSender")

    def send_draft(self, draft_path: Path) -> bool:
        """Send the WhatsApp draft file.

        Args:
            draft_path: Absolute path to a markdown draft in APPROVED_PATH

        Returns:
            True on success, False on failure
        """
        try:
            # Safety check
            base_dir = Path(settings.APPROVED_PATH)
            if not is_safe_path(draft_path, base_dir):
                logger.error("Unsafe draft path detected: %s", draft_path)
                return False

            # Parse the draft
            parsed = self._parse_draft(draft_path)

            if not parsed['to']:
                logger.error("No recipient found in WhatsApp draft: %s", draft_path)
                return False

            if not parsed['body']:
                logger.error("No message body found in WhatsApp draft: %s", draft_path)
                return False

            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self._last_send_time
            if time_since_last < self._min_send_interval:
                sleep_time = self._min_send_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)

            # Determine sending method
            if self.mode == "playwright":
                result = self._send_via_playwright(parsed)
            elif self.mode == "mcp":
                result = self._send_via_mcp(parsed)
            elif self.mode == "mock":
                result = self._send_mock(parsed)
            else:  # auto mode
                result = self._send_auto(parsed)

            self._last_send_time = time.time()

            if result:
                logger.info(f"✅ WhatsApp message sent successfully to {parsed['to']}")
            else:
                logger.error(f"❌ Failed to send WhatsApp message to {parsed['to']}")

            return result

        except Exception as e:
            logger.error("Failed to send WhatsApp draft %s: %s", draft_path, e)
            return False

    def _parse_draft(self, draft_path: Path) -> Dict[str, Any]:
        """Extract metadata and body from the markdown draft.

        Handles YAML frontmatter format with --- markers.
        """
        content = draft_path.read_text(encoding='utf-8')
        lines = content.splitlines()

        metadata = {
            'to': '',
            'body': '',
            'platform': 'whatsapp',
            'subject': '',
            'thread_id': None,
            'message_id': None
        }

        # Check if YAML frontmatter exists
        if lines and lines[0].strip() == '---':
            # YAML frontmatter format
            in_frontmatter = True
            frontmatter_end = -1

            for i in range(1, len(lines)):
                line = lines[i]
                stripped = line.strip()

                if stripped == '---':
                    frontmatter_end = i
                    break

                # Parse fields
                if ':' in stripped:
                    key, value = stripped.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()

                    if key == 'to':
                        metadata['to'] = value
                    elif key == 'subject':
                        metadata['subject'] = value
                    elif key == 'platform':
                        metadata['platform'] = value.lower()
                    elif key == 'original_sender':
                        if not metadata['to']:
                            metadata['to'] = value
                    elif key == 'thread-id':
                        metadata['thread_id'] = value
                    elif key == 'message-id':
                        metadata['message_id'] = value

            # Body is after frontmatter
            if frontmatter_end > 0:
                body_lines = []
                for line in lines[frontmatter_end + 1:]:
                    stripped = line.strip()
                    # Skip markdown headers and instructions
                    if stripped.startswith('#') or stripped.startswith('**'):
                        continue
                    if stripped:
                        body_lines.append(stripped)
                metadata['body'] = ' '.join(body_lines).strip()
        else:
            # Simple format without YAML frontmatter
            in_body = False
            body_lines = []

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                if stripped.lower().startswith('to:'):
                    metadata['to'] = stripped.split(':', 1)[1].strip()
                elif stripped.lower().startswith('platform:'):
                    metadata['platform'] = stripped.split(':', 1)[1].strip().lower()
                elif ':' not in stripped or in_body:
                    body_lines.append(stripped)
                    in_body = True

            metadata['body'] = ' '.join(body_lines).strip()

        # Log parsed info
        logger.info(f"Parsed draft - To: {metadata['to']}, Platform: {metadata['platform']}")
        logger.info(f"Body length: {len(metadata['body'])} chars")
        logger.info(f"Body preview: {metadata['body'][:200]}...")

        return metadata

    def _send_auto(self, parsed: dict) -> bool:
        """Automatically choose the best sending method.

        Priority:
        1. Playwright (if we have an active session)
        2. MCP (if server is available)
        3. Mock (fallback)

        Args:
            parsed: Parsed draft data

        Returns:
            True if sent successfully
        """
        # Try Playwright first if we have a page
        if self._playwright_page:
            try:
                return self._send_via_playwright(parsed)
            except Exception as e:
                logger.warning(f"Playwright send failed, trying MCP: {e}")

        # Try MCP next
        try:
            return self._send_via_mcp(parsed)
        except Exception as e:
            logger.warning(f"MCP send failed, falling back to mock: {e}")

        # Final fallback to mock
        return self._send_mock(parsed)

    def _send_via_playwright(self, parsed: dict) -> bool:
        """Send WhatsApp message using direct Playwright automation.

        This uses the same browser session as the watcher, maintaining login state.

        Args:
            parsed: Parsed draft data with 'to' and 'body'

        Returns:
            True if sent successfully
        """
        # Import here to avoid dependency issues if playwright isn't installed
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright")
            raise RuntimeError("Playwright not available")

        # If we don't have a shared page, create a new browser session
        if not self._playwright_page:
            logger.info("No shared Playwright page, creating new session...")
            return self._send_via_new_playwright_session(parsed)

        # Use existing page
        try:
            return self._send_with_page(self._playwright_page, parsed)
        except Exception as e:
            logger.error(f"Failed to send with shared page: {e}")
            return False

    def _send_via_new_playwright_session(self, parsed: dict) -> bool:
        """Create a new Playwright session and send the message.

        Args:
            parsed: Parsed draft data

        Returns:
            True if sent successfully
        """
        from playwright.sync_api import sync_playwright

        user_data_dir = Path(settings.LOGS_PATH) / "whatsapp_sender_session"

        with sync_playwright() as p:
            # Launch with persistent context to reuse session
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,  # Need visible browser for QR if not logged in
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--window-size=1600,900',
                ]
            )

            page = context.pages[0] if context.pages else context.new_page()

            try:
                # Navigate to WhatsApp Web
                logger.info("Navigating to WhatsApp Web...")
                page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)  # Wait for initial load

                # Check if logged in using multiple selectors
                logged_in_selectors = [
                    '[data-testid="chat-list"]',
                    '[aria-label="Chat list"]',
                    '#pane-side',
                    'div[data-testid="pane-side"]',
                    'span[data-testid="online"]',
                    '[data-testid="search-icon"]',
                ]

                is_logged_in = False
                for selector in logged_in_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element and element.is_visible():
                            logger.info(f"Login detected via selector: {selector}")
                            is_logged_in = True
                            break
                    except:
                        continue

                if not is_logged_in:
                    logger.info("=" * 60)
                    logger.info("NOT LOGGED IN - PLEASE SCAN QR CODE")
                    logger.info("=" * 60)
                    logger.info("1. Look at the browser window")
                    logger.info("2. Scan the QR code with your phone")
                    logger.info("3. Waiting up to 120 seconds...")
                    logger.info("=" * 60)

                    # Wait longer for manual QR scan with progress updates
                    max_wait = 120  # 2 minutes
                    check_interval = 3
                    waited = 0

                    while waited < max_wait:
                        page.wait_for_timeout(check_interval * 1000)
                        waited += check_interval

                        # Check if logged in now
                        for selector in logged_in_selectors:
                            try:
                                element = page.query_selector(selector)
                                if element and element.is_visible():
                                    logger.info(f"✅ Login successful after {waited} seconds!")
                                    is_logged_in = True
                                    break
                            except:
                                continue

                        if is_logged_in:
                            break

                        # Show progress every 15 seconds
                        if waited % 15 == 0:
                            logger.info(f"Still waiting... {waited}/{max_wait} seconds")

                    if not is_logged_in:
                        logger.error("❌ Timeout: QR code not scanned within 120 seconds")
                        context.close()
                        return False

                # Extra wait for WhatsApp to fully load
                logger.info("Waiting for WhatsApp to fully load...")
                page.wait_for_timeout(5000)

                # Send the message
                result = self._send_with_page_sync(page, parsed)

                # Wait before closing so user can see the sent message
                if result:
                    logger.info("Message sent successfully, waiting 3 seconds before closing...")
                    page.wait_for_timeout(3000)

                context.close()
                return result

            except Exception as e:
                logger.error(f"Error in new Playwright session: {e}")
                import traceback
                logger.error(traceback.format_exc())
                context.close()
                return False

    def _send_with_page(self, page, parsed: dict) -> bool:
        """Send message using an existing async Playwright page.

        Args:
            page: Playwright page object (async)
            parsed: Parsed draft data

        Returns:
            True if sent successfully
        """
        # This would be called with an async page - convert to sync operations
        # For now, delegate to the sync version
        return self._send_with_page_sync(page, parsed)

    def _send_with_page_sync(self, page, parsed: dict) -> bool:
        """Send message using a synchronous Playwright page.

        Args:
            page: Playwright page object
            parsed: Parsed draft data with 'to' (recipient) and 'body' (message)

        Returns:
            True if sent successfully
        """
        recipient = parsed['to']
        message = parsed['body']

        try:
            # Step 1: Search for the contact
            logger.info(f"Searching for contact: {recipient}")

            # Take screenshot for debugging
            debug_dir = Path(settings.LOGS_PATH) / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(debug_dir / "01_before_search.png"))

            # Click on search box
            search_selectors = [
                '[data-testid="chat-list-search"]',
                '[data-icon="search"]',
                'div[contenteditable="true"]',
                '[title="Search input textbox"]',
                'div[role="textbox"]'
            ]

            search_box = None
            for selector in search_selectors:
                try:
                    search_box = page.query_selector(selector)
                    if search_box and search_box.is_visible():
                        logger.debug(f"Found search box with selector: {selector}")
                        break
                except:
                    continue

            if not search_box:
                logger.error("Could not find search box")
                page.screenshot(path=str(debug_dir / "error_no_search.png"))
                return False

            # Click search and type recipient
            search_box.click()
            page.wait_for_timeout(500)
            page.keyboard.press("Control+a")
            page.keyboard.press("Delete")
            page.wait_for_timeout(200)

            # Type recipient
            search_box.type(recipient, delay=50)
            logger.info(f"Typed recipient: {recipient}")
            page.wait_for_timeout(2000)  # Wait for search results

            page.screenshot(path=str(debug_dir / "02_after_search.png"))

            # Step 2: Click on the contact
            # Try multiple strategies to find the contact
            contact_clicked = False

            # Strategy 1: Try exact title match
            try:
                contact = page.query_selector(f'span[title="{recipient}"]')
                if contact:
                    contact.click()
                    contact_clicked = True
                    logger.info(f"Clicked contact by exact title match")
                    page.wait_for_timeout(1500)
            except Exception as e:
                logger.debug(f"Exact title match failed: {e}")

            # Strategy 2: Try pressing Enter to select first search result
            if not contact_clicked:
                try:
                    logger.info("Trying to press Enter to select first result...")
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(2000)
                    # Verify if chat opened by checking for message input
                    msg_check = page.query_selector('div[contenteditable="true"]')
                    if msg_check and msg_check.is_visible():
                        contact_clicked = True
                        logger.info(f"Chat opened by pressing Enter")
                except Exception as e:
                    logger.debug(f"Enter key selection failed: {e}")

            # Strategy 3: Try first listitem in search results
            if not contact_clicked:
                try:
                    contacts = page.query_selector_all('[role="listitem"]')
                    if contacts and len(contacts) > 0:
                        contacts[0].click()
                        contact_clicked = True
                        logger.info(f"Clicked first contact in search results")
                        page.wait_for_timeout(1500)
                except Exception as e:
                    logger.debug(f"First listitem click failed: {e}")

            # Strategy 4: Try cell-frame-container
            if not contact_clicked:
                try:
                    contact = page.query_selector('div[data-testid="cell-frame-container"]')
                    if contact:
                        contact.click()
                        contact_clicked = True
                        logger.info(f"Clicked contact using cell-frame-container")
                        page.wait_for_timeout(1500)
                except Exception as e:
                    logger.debug(f"Cell frame click failed: {e}")

            if not contact_clicked:
                logger.error(f"Could not find or click contact: {recipient}")
                page.screenshot(path=str(debug_dir / "error_no_contact.png"))
                return False

            logger.info(f"Selected contact: {recipient}")
            page.screenshot(path=str(debug_dir / "03_chat_opened.png"))

            # Step 3: Find and fill message input
            logger.info("Looking for message input...")

            # Wait for chat to fully load
            page.wait_for_timeout(2000)

            input_selectors = [
                'div[contenteditable="true"][data-tab="1"]',
                'div[contenteditable="true"][data-tab="10"]',
                '[data-testid="conversation-compose-box-input"]',
                '[title="Type a message"]',
                'div[contenteditable="true"]'
            ]

            msg_input = None
            for selector in input_selectors:
                try:
                    msg_input = page.query_selector(selector)
                    if msg_input and msg_input.is_visible():
                        logger.debug(f"Found message input with selector: {selector}")
                        break
                except:
                    continue

            if not msg_input:
                logger.error("Could not find message input box")
                page.screenshot(path=str(debug_dir / "error_no_input.png"))
                return False

            # Click input and type message
            msg_input.click()
            page.wait_for_timeout(500)

            # Clear any existing text
            page.keyboard.press("Control+a")
            page.keyboard.press("Delete")
            page.wait_for_timeout(200)

            # Type message - use fill() for reliability with longer messages
            logger.info(f"Typing message ({len(message)} chars): {message[:50]}...")

            # Try fill() first (more reliable for longer text)
            try:
                msg_input.fill(message)
                logger.debug("Used fill() for message input")
            except Exception as fill_err:
                logger.warning(f"fill() failed, falling back to type(): {fill_err}")
                # Fallback to type() for shorter messages
                if len(message) <= 100:
                    msg_input.type(message, delay=30)
                else:
                    # For longer messages, type in chunks
                    chunk_size = 50
                    for i in range(0, len(message), chunk_size):
                        chunk = message[i:i+chunk_size]
                        msg_input.type(chunk, delay=10)
                        page.wait_for_timeout(50)

            page.wait_for_timeout(1000)

            page.screenshot(path=str(debug_dir / "04_message_typed.png"))

            # Verify message was typed correctly
            page.wait_for_timeout(500)  # Wait for text to settle
            typed_text = msg_input.text_content() or ""
            typed_clean = typed_text.strip()
            expected_clean = message.strip()

            if not typed_clean:
                logger.error("Message input is empty after typing!")
                return False

            # Check if message was entered correctly (allow for some whitespace differences)
            if len(typed_clean) < len(expected_clean) * 0.9:  # Allow 10% tolerance
                logger.warning(f"Message verification failed. Expected ~{len(expected_clean)} chars, Got: {len(typed_clean)} chars")
                logger.warning(f"Expected: {expected_clean[:50]}...")
                logger.warning(f"Got: {typed_clean[:50]}...")

                # Try to fix by filling again
                try:
                    logger.info("Retrying with fill() method...")
                    msg_input.fill(message)
                    page.wait_for_timeout(800)
                    # Re-verify
                    typed_text = msg_input.text_content() or ""
                    if len(typed_text.strip()) < len(expected_clean) * 0.5:
                        logger.error("Message still incomplete after retry")
                        return False
                except Exception as retry_err:
                    logger.error(f"Retry failed: {retry_err}")
                    return False
            else:
                logger.info(f"Message verified: {len(typed_clean)} characters entered")

            # Step 4: Send the message
            logger.info("Sending message...")

            # Ensure input has focus before sending
            msg_input.click()
            page.wait_for_timeout(300)

            # Method 1: Try clicking send button first (more reliable)
            send_clicked = False
            send_selectors = [
                '[data-testid="send"]',
                'button[data-testid="send"]',
                'button[aria-label="Send"]',
                'span[data-icon="send"]',
                'div[data-testid="send"]'
            ]

            # Wait a moment for send button to appear (enabled after typing)
            page.wait_for_timeout(1000)

            for selector in send_selectors:
                try:
                    send_btn = page.query_selector(selector)
                    if send_btn and send_btn.is_visible() and send_btn.is_enabled():
                        send_btn.click()
                        logger.info("Clicked send button")
                        send_clicked = True
                        break
                except Exception as e:
                    logger.debug(f"Send selector {selector} failed: {e}")
                    continue

            # Method 2: Press Enter if send button not clicked
            if not send_clicked:
                logger.info("Send button not found, using Enter key...")
                page.keyboard.press("Enter")
                page.wait_for_timeout(500)
                # Double-press Enter sometimes needed
                page.keyboard.press("Enter")

            page.wait_for_timeout(3000)  # Wait longer for message to send

            # Verify message was sent by checking input is cleared
            final_text = msg_input.text_content() or ""
            if final_text.strip():
                logger.warning(f"Input still has text after send attempt: '{final_text[:50]}...'")
                logger.warning("Message may not have been sent!")
                # Try sending again
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)

            page.screenshot(path=str(debug_dir / "05_after_send.png"))

            logger.info(f"✅ Message sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"❌ Error sending message via Playwright: {e}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                page.screenshot(path=str(debug_dir / "error_exception.png"))
            except:
                pass
            return False

    def _send_via_mcp(self, parsed: dict) -> bool:
        """Send WhatsApp message using MCP whatsapp-mcp server.

        Args:
            parsed: Parsed draft data

        Returns:
            True if sent successfully
        """
        try:
            client = self.mcp_manager.get_client('whatsapp-mcp')
            if not client:
                logger.warning("whatsapp-mcp client not available")
                raise RuntimeError("MCP client not available")

            tool_name = 'send_message'
            args = {
                'to': parsed['to'],
                'body': parsed['body']
            }

            logger.info(f"Calling MCP tool {tool_name} for recipient {args['to']}")
            result = client.call_tool(tool_name, args)

            if result and not result.get('isError'):
                if 'content' in result:
                    logger.info("WhatsApp message sent via MCP: %s", result['content'][0]['text'])
                    return True
                else:
                    logger.error(f"MCP {tool_name} returned success but no content")
                    return True
            else:
                error_msg = result.get('content', [{}])[0].get('text', 'Unknown MCP error') if result else 'No result from MCP'
                logger.error(f"MCP {tool_name} failed: {error_msg}")
                raise RuntimeError(f"MCP call failed: {error_msg}")

        except Exception as e:
            logger.error("Failed to send via WhatsApp MCP: %s", e)
            raise  # Re-raise to allow fallback

    def _send_mock(self, parsed: dict) -> bool:
        """Mock sending WhatsApp message (for development/testing).

        Args:
            parsed: Parsed draft data

        Returns:
            Always True (simulated success)
        """
        logger.info("[MOCK] Sending WhatsApp message to %s", parsed['to'])
        logger.info("[MOCK] Body: %s", parsed['body'][:100] + "..." if len(parsed['body']) > 100 else parsed['body'])
        print(f"📱 [MOCK] WhatsApp sent to {parsed['to']}")

        # Create a log entry
        log_dir = Path(settings.LOGS_PATH)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "whatsapp_mock_log.txt"

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().isoformat()}] To: {parsed['to']}\n")
            f.write(f"  Body: {parsed['body'][:200]}...\n")
            f.write("-" * 50 + "\n")

        return True

    def validate_recipient(self, recipient: str) -> Tuple[bool, str]:
        """Validate a WhatsApp recipient identifier.

        Args:
            recipient: Phone number or contact name

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not recipient or not recipient.strip():
            return False, "Recipient cannot be empty"

        recipient = recipient.strip()

        # Check if it looks like a phone number
        digits_only = ''.join(c for c in recipient if c.isdigit())
        if len(digits_only) >= 7:
            # Looks like a phone number
            if len(digits_only) < 10:
                return False, f"Phone number too short: {digits_only}"
            return True, ""

        # Assume it's a contact name
        if len(recipient) < 2:
            return False, "Contact name too short"

        return True, ""
