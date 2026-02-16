"""
Diagnostic to find correct selectors for open chat.
Run this after scanning QR code.
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
    print("WhatsApp Chat Diagnostic")
    print("="*60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("\nOpening WhatsApp Web...")
        await page.goto("https://web.whatsapp.com")

        print("Waiting for login (scan QR code)...")
        for i in range(90):
            await asyncio.sleep(1)
            if await page.query_selector('[data-testid="chat-list"]'):
                print(f"Logged in after {i+1} seconds!")
                break

        await asyncio.sleep(3)

        print("\nFinding chats...")
        chat_items = []
        for selector in ['div._ak8q', 'div[role="grid"] > div']:
            items = await page.query_selector_all(selector)
            if items:
                chat_items = items
                print(f"Found {len(chat_items)} chats")
                break

        if chat_items:
            print(f"\nClicking on first chat...")
            await chat_items[0].click()
            await asyncio.sleep(3)

            # Get page HTML to find selectors
            html = await page.evaluate('() => document.documentElement.outerHTML')
            chat_html = html[html.find('conversation-header'):html.find('conversation-header')+1000]
            print(f"\n[Chat Header HTML snippet]:\n{chat_html[:300]}...")

            print("\n[Testing message selectors...]")
            msg_selectors = [
                'div[data-testid="msg-container"]',
                'div[data-testid="message-container"]',
                'div[role="log"]',
                'div[class*="message-container"]',
                'div[data-testid="conversation-panel-messages"]',
                '[data-testid="message-in"]',
                '[data-testid="message-out"]',
            ]

            for selector in msg_selectors:
                count = len(await page.query_selector_all(selector))
                print(f"  {selector}: {count}")

            print("\n[Testing text selectors...]")
            text_selectors = [
                'span.selectable-text',
                'span[data-testid="message-text"]',
                'div[class*="message-text"]',
                '[class*="selectable"]',
            ]

            for selector in text_selectors:
                count = len(await page.query_selector_all(selector))
                print(f"  {selector}: {count}")

            print("\n[Taking screenshot...")
            await page.screenshot(path=str(Path("Logs/whatsapp_chat_open.png")))
            print("  Saved to: Logs/whatsapp_chat_open.png")

        print("\nWaiting 60 seconds for inspection...")
        await asyncio.sleep(60)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())