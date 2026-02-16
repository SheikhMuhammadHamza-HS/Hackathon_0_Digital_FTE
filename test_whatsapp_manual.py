"""
Simple WhatsApp test - keeps browser open for manual login.
Run this, scan the QR code, and the browser will stay open.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def main():
    print("="*60)
    print("WhatsApp Manual Login Test")
    print("="*60)
    print("\n1. Browser will open")
    print("2. Scan the QR code with your phone")
    print("3. Wait for WhatsApp to load")
    print("4. Browser will stay open for testing")
    print("\nPress Ctrl+C to close...\n")

    async with async_playwright() as p:
        # Launch browser (will save session)
        session_dir = Path("Logs/whatsapp_session")
        session_dir.mkdir(exist_ok=True)

        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=False
        )

        if browser.pages:
            page = browser.pages[0]
        else:
            page = await browser.new_page()

        await page.goto("https://web.whatsapp.com")

        print("\n✓ Browser opened. Scan QR code now...")
        print("✓ Session will be saved to:", session_dir)

        # Keep browser open
        try:
            await asyncio.sleep(300)  # Wait 5 minutes
        except KeyboardInterrupt:
            print("\n\nClosing browser...")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())