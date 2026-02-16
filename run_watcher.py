import logging
import sys
import asyncio
from pathlib import Path

# Setup logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("watcher_debug.log")
    ]
)

# Now import the watcher
from src.watchers.whatsapp_watcher import WhatsAppWatcher

async def main():
    print("Starting WhatsApp Watcher in background...")
    watcher = WhatsAppWatcher(headless=True)
    try:
        await watcher.start()
    except Exception as e:
        logging.error(f"Watcher crashed: {e}")
    finally:
        await watcher.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
