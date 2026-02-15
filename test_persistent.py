import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def main():
    print("Initializing Playwright...")
    async with async_playwright() as p:
        user_data_dir = Path("./Logs/whatsapp_session_test")
        user_data_dir.mkdir(parents=True, exist_ok=True)
        print(f"Launching persistent context in {user_data_dir}...")
        try:
            # Short timeout for launch
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
                args=['--no-sandbox']
            )
            print("Successfully launched!")
            await asyncio.sleep(2)
            await context.close()
            print("Closed context.")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
