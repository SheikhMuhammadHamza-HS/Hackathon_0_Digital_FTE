"""
Test WhatsApp extraction using SAVED SESSION (no re-login needed)
Run AFTER: python test_whatsapp_manual.py
"""
import asyncio
import sys
import io
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

async def test_with_saved_session():
    """Test using saved session - NO QR CODE NEEDED!"""
    print("="*70)
    print("Testing with SAVED SESSION")
    print("="*70)
    print("\nThis uses your existing WhatsApp session.")
    print("NO QR CODE SCANNING NEEDED!\n")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            session_dir = Path("Logs/whatsapp_session")

            if not session_dir.exists():
                print("❌ No saved session found!")
                print("Run this first: python test_whatsapp_manual.py")
                return

            print(f"[1/3] Using saved session: {session_dir}")

            # Use persistent context to reuse session
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(session_dir),
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )

            page = context.pages[0] if context.pages else await context.new_page()

            print("[2/3] Loading WhatsApp (should auto-login)...")
            await page.goto("https://web.whatsapp.com", timeout=60000)
            await asyncio.sleep(5)

            # Check if logged in
            logged_in = await page.evaluate("""
                () => !!(document.querySelector('[data-testid="chat-list"]') ||
                         document.querySelector('div[role="grid"]'))
            """)

            if not logged_in:
                print("❌ Not logged in. Run: python test_whatsapp_manual.py")
                await context.close()
                return

            print("✓ Logged in automatically using saved session!")

            print("\n[3/3] Testing new message selectors...")

            # Get chat items
            chat_items = await page.query_selector_all('div[role="grid"] > div')
            print(f"    Found {len(chat_items)} chat items")

            messages_extracted = 0

            if chat_items:
                # Test first 3 chats
                for i in range(min(len(chat_items), 3)):
                    try:
                        chat = chat_items[i]

                        # Check for unread or process anyway
                        has_unread = await chat.query_selector('span[aria-label*="unread"]')

                        if has_unread or i == 0:
                            print(f"\n    Chat {i+1}:")

                            # Get chat name
                            chat_name = "Unknown"
                            try:
                                name_el = await chat.query_selector('span[title]')
                                if name_el:
                                    chat_name = await name_el.get_attribute('title') or 'Unknown'
                                else:
                                    # Try alternate selector
                                    name_el = await chat.query_selector('div[title]')
                                    if name_el:
                                        chat_name = await name_el.get_attribute('title') or 'Unknown'
                            except:
                                pass

                            print(f"    Name: {chat_name}")

                            # Click chat
                            await chat.click()
                            await asyncio.sleep(2)

                            # Try NEW SELECTORS
                            print("      Testing selectors...")

                            # Updated selectors from our analysis
                            selectors_to_test = [
                                'div[class*="_ak9"]',
                                'div[class*="_ak7"]',
                                'div[class*="_ao"]',
                                'div[class*="_am"]',
                                'div[class*="message-in"]',
                                'div[class*="message-out"]'
                            ]

                            for selector in selectors_to_test:
                                try:
                                    elements = await page.query_selector_all(selector)
                                    if elements:
                                        # Count elements with actual text
                                        valid_elements = 0
                                        for el in elements:
                                            text = await el.text_content()
                                            if text and len(text.strip()) > 5:
                                                valid_elements += 1

                                        if valid_elements > 0:
                                            print(f"        ✓ {selector}: {valid_elements} messages")

                                            # Show first message
                                            first_msg = elements[0]
                                            msg_text = await first_msg.text_content()
                                            print(f"          First: {msg_text.strip()[:60]}...")

                                            messages_extracted += valid_elements
                                            break  # Stop after first working selector

                                except Exception as e:
                                    continue

                            # Go back to chat list
                            back_btn = await page.query_selector('[data-testid="back"]')
                            if back_btn:
                                await back_btn.click()
                                await asyncio.sleep(1)

                    except Exception as e:
                        print(f"      Error: {e}")
                        continue

            print(f"\n{'='*70}")
            if messages_extracted > 0:
                print(f"SUCCESS! {messages_extracted} messages found with new selectors")
                print("The selector update is working!")
            else:
                print("No messages found with new selectors")
                print("May need further refinement")
            print(f"{'='*70}")

            print("\nPress Enter to close...")
            input()
            await context.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_saved_session())
