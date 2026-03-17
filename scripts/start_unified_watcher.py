
import os
import sys
import time
import asyncio
import threading
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logger = logging.getLogger("UnifiedWatcher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

async def run_unified_watcher():
    load_dotenv()
    
    poll_interval = int(os.getenv("GMAIL_POLL_INTERVAL", 30))
    platinum_mode = os.getenv("PLATINUM_MODE", "local").lower()

    print("\n" + "="*70)
    print(f"🚀 UNIFIED AI EMPLOYEE WATCHER ACTIVE")
    print(f"1. GMAIL    : Polling every {poll_interval}s (Inbox -> Needs_Action)")
    print(f"2. APPROVAL : Cloud mode - local approvals skipped")
    print(f"3. ODOO     : Syncing triggers to ERP automatically")
    print(f"🌍 PLATINUM MODE: {platinum_mode.upper()}")
    print("="*70)
    print("Press Ctrl+C to stop the system.\n")

    # --- Gmail Watcher (optional, gracefully skip if no token) ---
    gmail_watcher = None
    gmail_token = os.getenv("GMAIL_TOKEN")
    token_file = Path("token.json")

    if not gmail_token and not token_file.exists():
        logger.warning("⚠️  Gmail credentials not found. Gmail polling is DISABLED.")
        logger.warning("    Set GMAIL_TOKEN env var on Render to enable Gmail automation.")
    else:
        try:
            from src.watchers.gmail_watcher import GmailWatcher
            gmail_watcher = GmailWatcher(poll_interval=poll_interval)
            logger.info("✅ Gmail Watcher initialized successfully.")
        except Exception as e:
            logger.warning(f"⚠️  Gmail Watcher init failed (safe to ignore): {e}")

    try:
        while True:
            # --- 1. GMAIL SCAN (only if credentials exist) ---
            if gmail_watcher:
                try:
                    ts_gmail = time.strftime("%H:%M:%S")
                    print(f"[{ts_gmail}] 📧 Scanning Gmail...")
                    gmail_found = gmail_watcher.poll_unread(max_results=5)
                    if gmail_found:
                        print(f"    ✨ Found {len(gmail_found)} new email(s). AI drafting started.")
                except Exception as e:
                    logger.error(f"Gmail scan error: {e}")
            else:
                logger.info("📧 Gmail polling skipped (no credentials). Waiting...")

            # --- 2. ODOO QUEUE (Sync Triggers to ERP) ---
            try:
                from scripts.process_odoo_queue import process_odoo_queue
                await process_odoo_queue()
            except Exception as e:
                logger.warning(f"Odoo queue processing skipped: {e}")

            # Wait for next cycle
            await asyncio.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n🛑 System stopped by user.")
    except Exception as e:
        print(f"\n❌ System Error: {e}")
        logger.error(f"Unified Watcher failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_unified_watcher())
