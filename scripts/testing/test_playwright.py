import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto("https://www.google.com")
            print("Successfully opened Google")
            await asyncio.sleep(5)
            await browser.close()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
