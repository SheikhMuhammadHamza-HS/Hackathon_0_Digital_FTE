"""
Simple test script for WhatsApp Watcher.
Run this to test if the watcher can connect and extract messages.

Usage:
    python test_whatsapp_watcher.py

This will:
1. Launch browser (headless=False so you can see what's happening)
2. Connect to WhatsApp Web (scan QR if needed)
3. Extract unread messages
4. Print results to console
5. Save test output to Logs/test_whatsapp_watcher.log
"""
import asyncio
import sys
import logging
import io
from pathlib import Path
from datetime import datetime

# Fix Windows encoding issue
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup logging
LOGS_PATH = Path(__file__).parent / "Logs"
LOGS_PATH.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_PATH / "test_whatsapp_watcher.log", encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


async def test_whatsapp_connection():
    """Test if we can connect to WhatsApp Web."""
    print("\n" + "="*60)
    print("TEST 1: Connect to WhatsApp Web")
    print("="*60)

    try:
        from playwright.async_api import async_playwright

        # Use SAME session directory as manual test
        session_dir = LOGS_PATH / "whatsapp_session"
        session_dir.mkdir(exist_ok=True)

        print(f"\n[1/4] Launching browser (session: {session_dir})...")
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(session_dir),
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )

            page = context.pages[0] if context.pages else await context.new_page()

            print("[2/4] Navigating to WhatsApp Web...")
            await page.goto("https://web.whatsapp.com", timeout=60000)
            await asyncio.sleep(5)

            print("[3/4] Checking if logged in...")

            # Check for QR code
            qr_selectors = [
                'canvas[aria-label*="Scan this QR code"]',
                '[data-testid="qrcode"]',
                'div[data-ref]',
                'canvas'
            ]

            has_qr = False
            for selector in qr_selectors:
                try:
                    if await page.query_selector(selector):
                        has_qr = True
                        print(f"  → QR code detected! Please scan it.")
                        break
                except:
                    continue

            if has_qr:
                print("\n" + "!"*60)
                print("!!! SCAN THE QR CODE IN THE BROWSER WINDOW !!!")
                print("!"*60)
                print("\nWaiting for login (90 seconds)...")
                print("(Session will be saved - you only need to scan once!)")
                await asyncio.sleep(90)

            # Check if logged in now
            logged_in = False
            login_selectors = [
                '[data-testid="chat-list"]',
                'div[role="grid"]',
                '#pane-side'
            ]

            for selector in login_selectors:
                try:
                    if await page.query_selector(selector):
                        logged_in = True
                        print(f"  → Logged in! (found: {selector})")
                        break
                except:
                    continue

            if not logged_in:
                print("  → Not logged in yet. Taking screenshot...")
                await page.screenshot(path=str(LOGS_PATH / "test_login_state.png"))
                print("  → Saved screenshot to Logs/test_login_state.png")
            else:
                print("[4/4] Connection successful! ✓")
                print("    Session saved - next run will auto-login!")

            await asyncio.sleep(2)
            await context.close()

            return logged_in

    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_message_extraction():
    """Test if we can extract messages."""
    print("\n" + "="*60)
    print("TEST 2: Extract Messages")
    print("="*60)

    try:
        from playwright.async_api import async_playwright

        # Use SAME session directory as TEST 1
        session_dir = LOGS_PATH / "whatsapp_session"

        async with async_playwright() as p:
            print("\n[1/5] Launching browser (using saved session)...")
            print(f"    Session dir: {session_dir}")

            # Close any existing browser from TEST 1
            print("[2/5] Waiting for previous browser to close...")
            await asyncio.sleep(3)

            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(session_dir),
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )

            page = context.pages[0] if context.pages else await context.new_page()

            print("[3/5] Navigating to WhatsApp Web...")
            await page.goto("https://web.whatsapp.com", timeout=60000)
            await asyncio.sleep(10)  # Wait longer for page to load

            print("[4/5] Finding chat list...")
            # Try multiple selectors
            chat_list = None
            for selector in [
                '[data-testid="chat-list"]',
                'div[role="grid"]',
                '#pane-side',
                '[aria-label="Chat list"]',
                'div[class*="pane-side"]'
            ]:
                try:
                    if await page.query_selector(selector):
                        chat_list = await page.query_selector(selector)
                        print(f"  → Chat list found with: {selector}")
                        break
                except:
                    continue

            if not chat_list:
                print("  → Chat list not found. Taking screenshot...")
                await page.screenshot(path=str(LOGS_PATH / "test_no_chatlist.png"))
                print("  → Saved screenshot to Logs/test_no_chatlist.png")
                await context.close()
                return []

            print("[5/5] Finding unread chats...")
            # Try multiple chat selectors based on diagnostic results
            chat_items = []
            for chat_selector in [
                'div._ak8q',  # 68 elements found
                'div[role="grid"] > div',  # 67 elements found
                'div[tabindex]',  # 142 elements
            ]:
                try:
                    items = await page.query_selector_all(chat_selector)
                    if items:
                        chat_items = items
                        print(f"  → Found {len(chat_items)} chats with: {chat_selector}")
                        break
                except:
                    continue

            # Also check for unread badges
            unread_badges = await page.query_selector_all('span[aria-label*="unread"]')
            print(f"  → Found {len(unread_badges)} unread badges")

            messages = []

            for i, chat in enumerate(chat_items[:15]):  # Check first 15
                try:
                    # Check if this chat is clickable
                    is_clickable = await chat.is_visible() if hasattr(chat, 'is_visible') else True
                    if not is_clickable:
                        continue

                    # Check for unread indicator
                    classes = await chat.get_attribute('class') or ''
                    has_unread = 'unread' in classes.lower() or await chat.query_selector('span[aria-label*="unread"]')

                    # Also process first chat even if no unread (for testing)
                    if has_unread or i == 0:
                        print(f"\n  → Chat {i+1}: Processing {'(UNREAD)' if has_unread else '(for testing)'}")
                        print(f"     Clicking on chat...")

                        await chat.click()
                        await asyncio.sleep(2)

                        # Get sender
                        try:
                            sender_el = await page.query_selector('[data-testid="conversation-header"]')
                            sender = "Unknown"
                            if sender_el:
                                sender = await sender_el.text_content()
                                sender = sender.strip()[:50] if sender else "Unknown"
                        except:
                            sender = "Unknown"

                        print(f"     Sender: {sender}")

                        # Get messages
                        msg_containers = await page.query_selector_all('div[data-testid="msg-container"]')
                        print(f"     Found {len(msg_containers)} messages")

                        for msg in msg_containers[-5:]:  # Last 5 messages
                            try:
                                text_el = await msg.query_selector('span.selectable-text')
                                text = ""
                                if text_el:
                                    text = await text_el.text_content()
                                    text = text.strip() if text else ""

                                if text:
                                    messages.append({
                                        'sender': sender,
                                        'text': text[:100],
                                        'timestamp': 'now'
                                    })
                                    print(f"       - {text[:50]}...")
                            except:
                                continue

                        # Go back
                        back_btn = await page.query_selector('[data-testid="back"]')
                        if back_btn:
                            await back_btn.click()
                            await asyncio.sleep(1)

                except Exception as e:
                    print(f"     Error: {e}")
                    continue

            print(f"\n[6/6] Extracted {len(messages)} messages ✓")
            print(f"    Session saved to: {session_dir}")
            print(f"    Keep this session for future tests!")

            await context.close()

            return messages

    except Exception as e:
        print(f"✗ Extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return []


async def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# WhatsApp Watcher Test Script")
    print("#"*60)

    # Test 1: Connection
    connected = await test_whatsapp_connection()

    if not connected:
        print("\n⚠️  Connection failed. Please:")
        print("   1. Make sure you're connected to internet")
        print("   2. Run this test again and scan the QR code")
        print("   3. Wait for login to complete")
        return

    # Test 2: Message extraction
    messages = await test_message_extraction()

    # Print results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"\nTotal messages extracted: {len(messages)}\n")

    for i, msg in enumerate(messages, 1):
        print(f"{i}. From: {msg['sender']}")
        print(f"   Text: {msg['text']}")
        print()

    if messages:
        print("✅ Test PASSED - Messages extracted successfully!")
    else:
        print("⚠️  Test WARNING - No messages found (maybe no unread chats)")
        print("   Send yourself a message on WhatsApp and try again")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()