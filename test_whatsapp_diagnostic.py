"""
Diagnostic script to find the correct WhatsApp chat selectors.
Run after logging in to WhatsApp Web.
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
    print("WhatsApp Selector Diagnostic")
    print("="*60)

    async with async_playwright() as p:
        session_dir = Path("Logs/whatsapp_test_session")

        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=False
        )

        if context.pages:
            page = context.pages[0]
        else:
            page = await context.new_page()

        await page.goto("https://web.whatsapp.com")
        await asyncio.sleep(5)

        print("\n[1] Finding chat list container...")
        chat_list = None
        for selector in [
            '[data-testid="chat-list"]',
            '[aria-label="Chat list"]',
            '#pane-side',
            'div[role="grid"]'
        ]:
            if await page.query_selector(selector):
                chat_list = selector
                print(f"  ✓ Found: {selector}")
                break

        if not chat_list:
            print("  ✗ Chat list not found!")
            return

        # Get all possible chat elements
        print("\n[2] Trying different chat selectors...")

        selectors_to_test = [
            '[role="listitem"]',
            '[data-testid="cell-frame-container"]',
            '[data-testid="conversation-item"]',
            'div._ak8q',
            'div[data-testid="chat-list"] > div',
            'div[role="grid"] > div',
            'div[class*="chat"]',
            'div[tabindex]',
        ]

        for selector in selectors_to_test:
            try:
                count = len(await page.query_selector_all(selector))
                print(f"  {selector}: {count} elements")
            except:
                print(f"  {selector}: ERROR")

        # Get HTML of first few divs in chat list
        print("\n[3] Examining chat list HTML structure...")
        try:
            chat_list_el = await page.query_selector('[data-testid="chat-list"]')
            if chat_list_el:
                divs = await chat_list_el.query_selector_all('div')
                print(f"  Found {len(divs)} divs in chat list")

                # Show classes of first 10 divs
                for i, div in enumerate(divs[:10]):
                    classes = await div.get_attribute('class') or ''
                    if classes:
                        print(f"  Div {i}: class='{classes}'")
        except Exception as e:
            print(f"  Error: {e}")

        # Check for unread badges
        print("\n[4] Checking unread badges...")
        unread_selectors = [
            '[data-testid="icon-unread-count"]',
            'span[aria-label*="unread"]',
            'span[class*="unread"]',
        ]
        for selector in unread_selectors:
            count = len(await page.query_selector_all(selector))
            print(f"  {selector}: {count} found")

        print("\n[5] Taking screenshot...")
        await page.screenshot(path=str(Path("Logs/whatsapp_diagnostic.png")))
        print("  Saved to: Logs/whatsapp_diagnostic.png")

        print("\nPress Ctrl+C to close...")
        try:
            await asyncio.sleep(60)
        except KeyboardInterrupt:
            pass

        await context.close()

if __name__ == "__main__":
    asyncio.run(main())