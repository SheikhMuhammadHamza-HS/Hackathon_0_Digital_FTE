import asyncio
from playwright.async_api import async_playwright

async def main():
    print("Initializing Playwright (Simple Launch)...")
    async with async_playwright() as p:
        try:
            print("Launching browser...")
            browser = await p.chromium.launch(headless=False)
            print("Successfully launched! Opening WhatsApp...")
            page = await browser.new_page()
            await page.goto("https://web.whatsapp.com")
            print("WhatsApp opened! Screen check...")
            await asyncio.sleep(10)
            await browser.close()
            print("Closed.")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
