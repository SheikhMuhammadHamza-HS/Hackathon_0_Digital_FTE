import asyncio
from playwright.async_api import async_playwright
import os

async def take_snapshot():
    print("Capturing latest state...")
    async with async_playwright() as p:
        user_data_dir = os.path.join("Logs", "whatsapp_session")
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        )
        page = browser.pages[0]
        # Stealth Script
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        await page.goto("https://web.whatsapp.com")
        await asyncio.sleep(15) # Give it plenty of time
        path = os.path.join("Logs", "whatsapp_latest.png")
        await page.screenshot(path=path)
        print(f"Snapshot saved to {path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_snapshot())
