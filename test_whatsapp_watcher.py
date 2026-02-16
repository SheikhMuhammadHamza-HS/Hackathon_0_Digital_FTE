import asyncio
import logging
from src.watchers.whatsapp_watcher import WhatsAppWatcher

logging.basicConfig(level=logging.INFO)

async def main():
    watcher = WhatsAppWatcher(poll_interval=30, headless=False)  # headless=False to see browser
    try:
        await watcher.start()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        await watcher.cleanup()

if __name__ == "__main__":
    asyncio.run(main())