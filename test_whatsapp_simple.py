"""
Simple WhatsApp test - no session persistence.
Just tests if we can connect and extract messages in one run.
"""
import asyncio
import sys
import io
from playwright.async_api import async_playwright
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

async def main():
    print("="*60)
    print("WhatsApp Simple Test (No Session Persistence)")
    print("="*60)
    print("\nSteps:")
    print("1. Browser will open")
    print("2. Scan the QR code")
    print("3. Wait for WhatsApp to load")
    print("4. Script will test message extraction")
    print("\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("[1/4] Opening WhatsApp Web...")
        await page.goto("https://web.whatsapp.com")

        print("[2/4] Waiting for login (scan QR code now)...")
        print("    Script will wait up to 90 seconds for login...")

        # Wait for login
        for i in range(90):
            await asyncio.sleep(1)
            # Check if logged in
            for selector in [
                '[data-testid="chat-list"]',
                '[aria-label="Chat list"]',
                'div[role="grid"]'
            ]:
                if await page.query_selector(selector):
                    print(f"\n    Logged in after {i+1} seconds!")
                    break
            else:
                continue
            break
        else:
            print("\n    Login timeout. Please try again.")
            await browser.close()
            return

        await asyncio.sleep(3)

        print("\n[3/4] Finding chats...")
        # Use the correct selector
        chat_items = []
        for selector in ['div._ak8q', 'div[role="grid"] > div']:
            try:
                items = await page.query_selector_all(selector)
                if items:
                    chat_items = items
                    print(f"    Found {len(chat_items)} chats with: {selector}")
                    break
            except:
                continue

        if not chat_items:
            print("    ERROR: No chats found!")
            await browser.close()
            return

        # Check for unread badges
        unread_badges = await page.query_selector_all('span[aria-label*="unread"]')
        print(f"    Found {len(unread_badges)} unread badges")

        print("\n[4/4] Testing message extraction...")

        messages = []
        for i in range(min(len(chat_items), 5)):
            chat = chat_items[i]
            try:
                has_unread = await chat.query_selector('span[aria-label*="unread"]')

                if has_unread or i == 0:  # Test first chat even if no unread
                    print(f"\n    Chat {i+1}: Clicking...")
                    await chat.click()
                    await asyncio.sleep(2)

                    # Get sender
                    sender = "Unknown"
                    try:
                        sender_el = await page.query_selector('[data-testid="conversation-header"]')
                        if sender_el:
                            sender = await sender_el.text_content()
                            sender = sender.strip()[:50] if sender else "Unknown"
                    except:
                        pass

                    print(f"        Sender: {sender}")

                    # Get messages - try multiple selectors
                    msg_containers = []
                    for msg_selector in [
                        'div[data-testid="msg-container"]',
                        'div[data-testid="message-container"]',
                        'div[role="log"]',
                        'div[class*="message-container"]'
                    ]:
                        try:
                            items = await page.query_selector_all(msg_selector)
                            if items:
                                msg_containers = items
                                print(f"        Found {len(msg_containers)} messages with: {msg_selector}")
                                break
                        except:
                            continue

                    for msg in msg_containers[-3:]:
                        try:
                            # Try multiple text selectors
                            text_el = None
                            for text_selector in [
                                'span.selectable-text',
                                'span[class*="selectable"]',
                                'div[class*="text"]'
                            ]:
                                try:
                                    text_el = await msg.query_selector(text_selector)
                                    if text_el:
                                        break
                                except:
                                    continue

                            text = ""
                            if text_el:
                                text = await text_el.text_content()
                                text = text.strip() if text else ""

                            # Fallback: get all text
                            if not text:
                                try:
                                    text = await msg.text_content()
                                    text = text.strip() if text else ""
                                except:
                                    pass

                            if text:
                                messages.append({'sender': sender, 'text': text[:50]})
                                print(f"        - {text[:50]}")
                        except:
                            continue

                    # Go back
                    back_btn = await page.query_selector('[data-testid="back"]')
                    if back_btn:
                        await back_btn.click()
                        await asyncio.sleep(1)

            except Exception as e:
                print(f"    Error processing chat {i}: {e}")
                continue

        print("\n" + "="*60)
        print(f"RESULTS: {len(messages)} messages extracted")
        print("="*60)

        print("\nPress Enter to close browser...")
        input()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())