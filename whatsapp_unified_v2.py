#!/usr/bin/env python3
"""
Unified WhatsApp HITL - Watcher + Sender in ONE terminal.
Uses JavaScript injection for reliable NEW message detection.
"""
import asyncio
import logging
import time
import sys
import hashlib
import google.generativeai as genai
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Set, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))
from src.config.settings import settings

try:
    from playwright.async_api import async_playwright
except ImportError:
    logger.error("Playwright not installed. Run: pip install playwright")
    sys.exit(1)


class UnifiedWhatsAppHITL:
    def __init__(self):
        self.session_dir = Path(settings.LOGS_PATH) / "whatsapp_session"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.needs_action_dir = Path(settings.NEEDS_ACTION_PATH)
        self.plans_dir = Path(settings.DONE_PATH).parent / "Plans"
        self.pending_approval_dir = Path(settings.PENDING_APPROVAL_PATH)
        self.approved_dir = Path(settings.APPROVED_PATH)
        self.done_dir = Path(settings.DONE_PATH)

        # Ensure directories exist
        for dir_path in [self.needs_action_dir, self.plans_dir, self.pending_approval_dir,
                         self.approved_dir, self.done_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        self.running = False
        self.browser_context = None
        self.page = None
        self.playwright = None

        # Track processed message hashes (sender + fingerprint)
        self.seen_hashes: Set[str] = set()
        self.first_scan_done = False
        self.last_extraction_hash = {} # sender -> last_msg_hash

        # Initialize Gemini AI
        self.ai_available = False
        self.model = None
        api_key = settings.GEMINI_API_KEY
        if api_key and not api_key.startswith("your_"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                self.ai_available = True
                logger.info("Gemini AI configured for contextual responses")
            except Exception as e:
                logger.warning(f"Failed to configure Gemini AI: {e}")

    async def initialize_browser(self) -> bool:
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

            # Check login
            selectors = ['[data-testid="chat-list"]', '#pane-side', 'div[role="grid"]']
            logged_in = False

            for selector in selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem and await elem.is_visible():
                        logged_in = True
                        logger.info(f"Already logged in!")
                        break
                except:
                    continue

            if not logged_in:
                logger.info("=" * 60)
                logger.info("PLEASE SCAN QR CODE")
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
                await asyncio.sleep(2)

            # First scan - record all existing messages
            logger.info("Starting first scan...")
            await self._first_scan()
            logger.info("First scan completed.")

            return True

        except Exception as e:
            logger.error(f"Browser initialization failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def _get_chat_list_js(self):
        """Extracts chat list data with stable keys based on unread counts."""
        return await self.page.evaluate("""
            () => {
                const results = [];
                const chatElements = document.querySelectorAll(
                    '[data-testid="cell-frame-container"], [role="listitem"], #pane-side div[role="row"]'
                );

                chatElements.forEach(chat => {
                    try {
                        const nameEl = chat.querySelector('[data-testid="cell-frame-title"], [title], span[dir="auto"], strong');
                        let sender = nameEl ? (nameEl.getAttribute('title') || nameEl.textContent || "Unknown").trim() : "Unknown";
                        
                        const unreadBadge = chat.querySelector('span[aria-label*="unread"], [class*="badge"], [class*="unread"]');
                        let unreadCount = 0;
                        if (unreadBadge) {
                            const countMatch = unreadBadge.innerText.match(/\\d+/);
                            unreadCount = countMatch ? parseInt(countMatch[0]) : 1;
                        }

                        if (sender !== "Unknown") {
                            results.push({
                                sender: sender,
                                hasUnread: !!unreadBadge,
                                unreadCount: unreadCount,
                                key: `${sender}:${unreadCount}`
                            });
                        }
                    } catch (e) {}
                });
                return results;
            }
        """)

    async def _first_scan(self):
        """Build a baseline of existing unread chats to ignore them."""
        logger.info("[INIT] Building chat baseline (tagging existing unreads as 'old')...")

        try:
            await self.page.wait_for_selector('[data-testid="chat-list"], #pane-side', timeout=30000)
            
            for i in range(3):
                chat_data = await self._get_chat_list_js()
                for chat in chat_data:
                    if chat['hasUnread']:
                        # Store stable key so we don't process it as "new"
                        self.seen_hashes.add(chat['key'])
                
                await self.page.mouse.wheel(0, 800)
                await asyncio.sleep(1)

            # Scroll back to top
            await self.page.mouse.wheel(0, -3000)
            await asyncio.sleep(1)

        except Exception as e:
            logger.warning(f"[INIT] Baseline building interrupted: {e}")

        logger.info(f"[INIT] Baseline built: Ignore {len(self.seen_hashes)} existing unread states.")
        self.first_scan_done = True

    async def scan_messages(self) -> int:
        """Scan ONLY for new unread messages that weren't in the baseline."""
        try:
            logger.info("[WATCHER] Scanning...")
            chat_data = await self._get_chat_list_js()
            
            new_count = 0
            for chat in chat_data:
                # 1. Skip read messages
                if not chat['hasUnread']:
                    continue

                sender = chat['sender']
                combined_key = chat['key']

                # 2. Skip old unreads (from baseline or previously processed)
                if combined_key in self.seen_hashes:
                    continue

                logger.info(f"[WATCHER] NEW UNREAD detected from: {sender} (Count: {chat['unreadCount']})")
                
                try:
                    # 1. Native Click with Locator
                    chat_selector = f'xpath=//span[@title="{sender}"]/ancestor::div[@role="row"] | //span[contains(text(), "{sender}")]/ancestor::div[@data-testid="cell-frame-container"]'
                    chat_locator = self.page.locator(chat_selector).first
                    
                    if await chat_locator.count() > 0:
                        await chat_locator.click(force=True, timeout=5000)
                    else:
                        # Fallback to search bar if locator doesn't find it instantly
                        logger.info(f"[WATCHER] Locator failed for {sender}, trying search bar...")
                        search_box = await self.page.query_selector('div[contenteditable="true"]')
                        if search_box:
                            await search_box.click()
                            await self.page.keyboard.press("Control+a")
                            await self.page.keyboard.press("Delete")
                            await search_box.type(sender, delay=30)
                            await asyncio.sleep(2)
                            await self.page.keyboard.press("Enter")

                    # 2. Wait for conversation pane to stabilize
                    await self.page.wait_for_selector('[role="main"], [data-testid="conversation-panel-wrapper"], #main', timeout=10000)
                    await asyncio.sleep(2)
                    
                    # 3. Message Extraction
                    msg_data = await self.page.evaluate("""
                        () => {
                            const pane = document.querySelector('[role="main"], [data-testid="conversation-panel-wrapper"], #main');
                            if (!pane) return null;

                            // Strategy 1: Last incoming message container
                            const containers = pane.querySelectorAll('[data-testid="msg-container"], .message-in');
                            if (containers.length > 0) {
                                return containers[containers.length - 1].innerText;
                            }
                            
                            // Strategy 2: Raw text fallback
                            return pane.innerText;
                        }
                    """)

                    if msg_data:
                        import re
                        lines = [l.strip() for l in msg_data.split('\n') if len(l.strip()) > 0]
                        junk = [sender.lower(), "read", "delivered", "sent", "edited", "today", "yesterday"]
                        clean_lines = []
                        for l in lines:
                            if any(k in l.lower() for k in junk) and len(l) < len(sender) + 5:
                                continue
                            if re.match(r'^\d{1,2}:\d{2}', l): continue
                            clean_lines.append(l)
                        
                        final_msg = " ".join(clean_lines[-3:]).strip()
                        
                        if len(final_msg) > 1:
                            logger.info(f"[WATCHER] Extracted: {final_msg[:50]}...")
                            await self._create_task_file(sender, final_msg)
                            self.seen_hashes.add(combined_key)
                            self.last_extraction_hash[sender] = hashlib.md5(final_msg.encode()).hexdigest()
                            new_count += 1
                        else:
                            logger.warning(f"[WATCHER] No valid text content for {sender}")
                            self.seen_hashes.add(combined_key)
                    else:
                        logger.warning(f"[WATCHER] Extraction failed for {sender}")
                        self.seen_hashes.add(combined_key)

                    # Reset UI
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error processing {sender}: {e}")
                    self.seen_hashes.add(combined_key)
                    
                    # Close chat
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error processing {sender}: {e}")
                    # Add to seen if it keeps failing to prevent infinite spam
                    if "click" not in str(e).lower():
                        self.seen_hashes.add(combined_key)

            return new_count

        except Exception as e:
            logger.error(f"[WATCHER] Scan error: {e}")
            return 0

    async def _create_task_file(self, sender: str, message: str):
        try:
            # Clean message from trailing timestamps (fallback for JS extraction)
            import re
            message = re.sub(r'\d{1,2}:\d{2}$', '', message.strip()).strip()
            
            clean_sender = "".join(c for c in sender if c.isalnum() or c in (' ', '-', '_')).strip()
            clean_sender = clean_sender.replace(' ', '_')[:30]

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"WHATSAPP_{timestamp}_{clean_sender}.md"
            filepath = self.needs_action_dir / filename

            content = f"""---
type: whatsapp_message
sender: "{sender}"
message: "{message.replace('"', '\\"')}"
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
        result = {'processed': 0, 'failed': 0}

        try:
            files = list(self.needs_action_dir.glob("*.md"))

            for filepath in files:
                try:
                    logger.info(f"[PROCESSOR] Processing: {filepath.name}")

                    content = filepath.read_text(encoding='utf-8')

                    if 'whatsapp' not in content.lower():
                        continue

                    sender = "Unknown"
                    message = ""

                    for line in content.split('\n'):
                        if line.startswith('sender:'):
                            sender = line.split(':', 1)[1].strip().strip('"')
                        if line.startswith('message:'):
                            message = line.split(':', 1)[1].strip().strip('"')

                    # Step 1: Generate Contextual Response via AI
                    ai_response = f"Salam {sender}! Umeed hai aap khairiyat se honge. Aapka message mil gaya hai, main jald hi aapko tafseel ke saath jawab deta hun."
                    strategy = "Acknowledge the message and maintain professional tone."
                    
                    if self.ai_available:
                        try:
                            prompt = f"""You are Hamza Digital FTE, a smart AI assistant.
Draft a professional and friendly WhatsApp response to this message:
Sender: {sender}
Message: {message}

Guidelines:
1. Be concise (2-4 sentences).
2. Use a friendly yet professional tone.
3. Directly address what the user said.
4. Sign off naturally.

Output ONLY the response text."""
                            response = self.model.generate_content(prompt)
                            if response and response.text:
                                ai_response = response.text.strip()
                                # Clean up any quotes or prefixes
                                ai_response = re.sub(r'^(Response|Reply|Draft|WhatsApp Response):', '', ai_response).strip().strip('"')
                                strategy = f"Contextual response generated based on: '{message[:50]}...'"
                        except Exception as e:
                            logger.error(f"AI Generation failed: {e}")

                    # Step 2: Create Plan
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    # Sanitize sender name for safe filename (remove path separators)
                    safe_sender = "".join(c for c in sender if c.isalnum() or c in (' ', '-', '_')).strip()
                    safe_sender = safe_sender.replace(' ', '_')[:20]
                    plan_filename = f"PLAN_{timestamp}_{safe_sender}.md"
                    plan_path = self.plans_dir / plan_filename

                    plan_content = f"""# Response Plan for {sender}

## Task Summary
- **Source**: WhatsApp Message
- **Sender**: {sender}
- **Received**: {timestamp}
- **Status**: Planning

## Original Message
> {message}

## Proposed Response Strategy
1. {strategy}
2. Ensure clear communication.

## Draft Response
{ai_response}

## Next Steps
- [ ] Review draft response
- [ ] Approve or modify as needed
- [ ] Send via WhatsApp

---
*Plan generated by AI Employee*
"""
                    plan_path.write_text(plan_content, encoding='utf-8')
                    logger.info(f"[PROCESSOR] Created plan: {plan_filename}")

                    # Step 3: Create Draft in Pending_Approval (safe_sender already defined above)
                    draft_filename = f"DRAFT_{timestamp}_{safe_sender}.md"
                    draft_path = self.pending_approval_dir / draft_filename

                    draft_content = f"""---
type: whatsapp_response
to: "{sender}"
platform: whatsapp
original_sender: "{sender}"
original_message: "{message.replace('"', '\\"')}"
plan_file: "{plan_filename}"
status: pending_approval
---

{ai_response}

---
**Instructions:**
1. Review this draft response above
2. Edit the message if needed
3. Move this file to the `Approved/` folder to send
4. System will automatically send once approved
"""
                    draft_path.write_text(draft_content, encoding='utf-8')
                    logger.info(f"[PROCESSOR] Created draft: {draft_filename}")

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
        result = {'sent': 0, 'failed': 0}

        try:
            files = list(self.approved_dir.glob("*.md"))

            # Filter files that are at least 10 seconds old (gives user time to review)
            import time
            eligible_files = []
            for filepath in files:
                file_age = time.time() - filepath.stat().st_mtime
                if file_age >= 10:  # 10 seconds delay before sending
                    eligible_files.append(filepath)
                else:
                    logger.info(f"[SENDER] Waiting: {filepath.name} (will send in {10-int(file_age)}s)")

            for filepath in eligible_files:
                try:
                    logger.info(f"[SENDER] Sending: {filepath.name}")

                    content = filepath.read_text(encoding='utf-8')

                    lines = content.split('\n')
                    frontmatter_end_idx = -1
                    
                    # 1. Find the end of frontmatter
                    if lines and lines[0].strip() == '---':
                        for i in range(1, len(lines)):
                            if lines[i].strip() == '---':
                                frontmatter_end_idx = i
                                break
                    
                    # 2. Extract recipient from anywhere and message from after frontmatter
                    body_lines = []
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped.lower().startswith('to:'):
                            recipient = stripped.split(':', 1)[1].strip().strip('"')
                        
                        if i > frontmatter_end_idx and stripped:
                            # Skip instructions/metadata at bottom
                            if stripped == '---' or stripped.startswith('**Instructions:'):
                                break
                            body_lines.append(stripped)

                    message = "\n".join(body_lines).strip()

                    if not recipient or not message:
                        logger.error(f"[SENDER] Missing recipient or message")
                        result['failed'] += 1
                        continue

                    success = await self._send_whatsapp_message(recipient, message)

                    if success:
                        done_path = self.done_dir / filepath.name
                        filepath.rename(done_path)
                        logger.info(f"[SENDER] Sent: {filepath.name}")
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
        try:
            logger.info(f"[SENDER] Sending to {recipient}...")

            if "web.whatsapp.com" not in self.page.url:
                await self.page.goto("https://web.whatsapp.com", wait_until="networkidle")
                await asyncio.sleep(3)

            search_box = await self.page.query_selector('div[contenteditable="true"]')
            if not search_box:
                logger.error("[SENDER] Search box not found")
                return False

            await search_box.click()
            await asyncio.sleep(0.5)
            await self.page.keyboard.press("Control+a")
            await self.page.keyboard.press("Delete")
            await search_box.type(recipient, delay=100)
            await asyncio.sleep(2)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(3)

            # Find the message input box - try multiple methods
            msg_input = await self.page.query_selector('footer div[contenteditable="true"]')
            
            if not msg_input:
                # Try finding based on data-tab or role
                inputs = await self.page.query_selector_all('div[contenteditable="true"]')
                for inp in inputs:
                    data_tab = await inp.get_attribute('data-tab')
                    if data_tab == '1' or await inp.get_attribute('role') == 'textbox':
                        msg_input = inp
                        break

            if not msg_input:
                # Last resort: click the bottom area where input usually is
                logger.warning("[SENDER] Could not find input box specifically, trying broad selector")
                msg_input = await self.page.query_selector('footer div.lexical-rich-text')

            if not msg_input:
                logger.error("[SENDER] Message input not found")
                return False

            await msg_input.click()
            await asyncio.sleep(1)
            # Use fill or type depending on what's more reliable
            await msg_input.type(message, delay=20)
            await asyncio.sleep(1)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(2)

            logger.info(f"[SENDER] Message sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"[SENDER] Send error: {e}")
            return False

    async def run(self):
        logger.info("=" * 60)
        logger.info("Unified WhatsApp HITL System")
        logger.info("=" * 60)

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

                new_msgs = await self.scan_messages()

                processed = await self.process_needs_action()
                if processed['processed'] > 0:
                    logger.info(f"[PROCESSOR] Created {processed['processed']} drafts")
                    logger.info("[ACTION REQUIRED] Move files from Pending_Approval to Approved")

                # Process approved files (with 60-second delay for safety)
                approved = await self.process_approved()
                if approved['sent'] > 0:
                    logger.info(f"[SENDER] Sent {approved['sent']} messages")

                # Show status
                approved_files = list(self.approved_dir.glob("*.md"))
                if approved_files:
                    logger.info(f"[APPROVED] {len(approved_files)} files waiting (10s delay before send)")

                pending = len(list(self.pending_approval_dir.glob("*.md")))
                approved_count = len(list(self.approved_dir.glob("*.md")))

                logger.info(f"[STATUS] Pending: {pending} | Approved waiting: {approved_count}")
                logger.info(f"[WAIT] Next scan in 30 seconds...")

                await asyncio.sleep(30)

        except KeyboardInterrupt:
            logger.info("\nStopping...")
        finally:
            self.running = False
            try:
                if self.browser_context:
                    await self.browser_context.close()
                if self.playwright:
                    await self.playwright.stop()
            except:
                pass
            logger.info("Stopped.")


def main():
    unified = UnifiedWhatsAppHITL()
    try:
        asyncio.run(unified.run())
    except KeyboardInterrupt:
        logger.info("\nExited by user")


if __name__ == "__main__":
    main()
