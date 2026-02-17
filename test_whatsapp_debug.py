#!/usr/bin/env python3
"""
Quick debug script - test if message detection is working
"""
import asyncio
import logging
import sys
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('whatsapp_debug_output.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))
from src.config.settings import settings

try:
    from playwright.async_api import async_playwright
except ImportError:
    logger.error("Playwright not installed")
    sys.exit(1)


async def test_detection():
    session_dir = Path(settings.LOGS_PATH) / "whatsapp_session"
    
    logger.info("="*60)
    logger.info("WhatsApp Message Detection Test")
    logger.info("="*60)
    
    playwright = await async_playwright().start()
    
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(session_dir),
        headless=False,
        args=['--window-size=1400,900']
    )
    
    page = context.pages[0] if context.pages else await context.new_page()
    
    logger.info("Opening WhatsApp Web...")
    await page.goto("https://web.whatsapp.com", wait_until="networkidle", timeout=120000)
    await asyncio.sleep(5)
    
    # Check login
    chat_list = await page.query_selector('[data-testid="chat-list"]')
    if not chat_list:
        logger.error("Not logged in!")
        await context.close()
        await playwright.stop()
        return
    
    logger.info("Logged in successfully!")
    logger.info("Fetching chat data with JavaScript...")
    
    # Get chat data
    chat_data = await page.evaluate("""
        () => {
            const results = [];
            const chatElements = document.querySelectorAll(
                '[data-testid="cell-frame-container"]'
            );
            
            chatElements.forEach((chat, index) => {
                try {
                    // Get sender
                    let sender = "Unknown";
                    const nameEl = chat.querySelector('[data-testid="cell-frame-title"]');
                    if (nameEl) {
                        sender = nameEl.textContent || "Unknown";
                    }
                    
                    // Check for unread
                    let unread = false;
                    const spans = chat.querySelectorAll('span');
                    for (const span of spans) {
                        const text = span.textContent;
                        const ariaLabel = span.getAttribute('aria-label') || '';
                        if (/^\\d+$/.test(text) && ariaLabel.toLowerCase().includes('unread')) {
                            unread = true;
                            break;
                        }
                    }
                    
                    if (unread) {
                        results.push({
                            index: index,
                            sender: sender.trim()
                        });
                    }
                } catch (e) {}
            });
            
            return results;
        }
    """)
    
    logger.info(f"Found {len(chat_data)} chats with UNREAD messages:")
    for chat in chat_data:
        logger.info(f"  - {chat['sender']} (index: {chat['index']})")
    
    if len(chat_data) > 0:
        logger.info("\nTrying to click first unread chat...")
        first_chat = chat_data[0]
        
        try:
            await page.evaluate(f"""
                () => {{
                    const chats = document.querySelectorAll('[data-testid="cell-frame-container"]');
                    if (chats[{first_chat['index']}]) {{
                        chats[{first_chat['index']}].click();
                    }}
                }}
            """)
            await asyncio.sleep(3)
            
            logger.info("Extracting message text...")
            
            full_msg = await page.evaluate("""
                () => {
                    const msgs = document.querySelectorAll('div.message-in, div[data-testid="msg-container"]');
                    for (let i = msgs.length - 1; i >= 0; i--) {
                        const textEl = msgs[i].querySelector('span.selectable-text, .copyable-text');
                        if (textEl) {
                            const text = textEl.textContent.trim();
                            if (text) return text;
                        }
                    }
                    return '';
                }
            """)
            
            if full_msg:
                logger.info(f"\n✅ MESSAGE EXTRACTED:")
                logger.info(f"   Sender: {first_chat['sender']}")
                logger.info(f"   Message: {full_msg}")
            else:
                logger.warning("❌ Could not extract message text")
                
        except Exception as e:
            logger.error(f"Error clicking/extracting: {e}")
    else:
        logger.warning("No unread chats found!")
        logger.info("Please send a message to your WhatsApp and run this again")
    
    logger.info("\n" + "="*60)
    logger.info("Test Complete - Check whatsapp_debug_output.log for details")
    logger.info("="*60)
    
    await asyncio.sleep(2)
    await context.close()
    await playwright.stop()


if __name__ == "__main__":
    try:
        asyncio.run(test_detection())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
