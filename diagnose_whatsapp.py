import asyncio
import logging
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from src.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def diagnose():
    session_dir = Path(settings.LOGS_PATH) / "whatsapp_session"
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=False
        )
        page = context.pages[0] if context.pages else await context.new_page()
        logger.info("Opening WhatsApp...")
        await page.goto("https://web.whatsapp.com")
        await asyncio.sleep(10)
        
        logger.info("Analyzing chat list...")
        chats = await page.evaluate("""
            () => {
                const results = [];
                const chatElements = document.querySelectorAll('[data-testid="cell-frame-container"], [role="listitem"]');
                chatElements.forEach((chat, i) => {
                    if (i > 10) return; // Only first 10
                    results.push({
                        html: chat.outerHTML.substring(0, 1000),
                        text: chat.innerText
                    });
                });
                return results;
            }
        """)
        
        for i, chat in enumerate(chats):
            logger.info(f"--- Chat {i} ---")
            logger.info(f"Text: {chat['text'].replace('\\n', ' ')}")
            logger.info(f"HTML Preview: {chat['html']}")
            
        await page.screenshot(path="whatsapp_diagnostic.png")
        logger.info("Screenshot saved to whatsapp_diagnostic.png")
        await context.close()

if __name__ == "__main__":
    asyncio.run(diagnose())
