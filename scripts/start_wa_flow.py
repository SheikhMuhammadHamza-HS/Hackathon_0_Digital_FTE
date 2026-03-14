
import os
import sys
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.logging_config import get_logger
from src.watchers.whatsapp_watcher import WhatsAppWatcher
from src.watchers.approval_watcher import ApprovalWatcher
from ai_employee.utils.file_locker import FileLocker

logger = get_logger("WhatsAppFlow")

async def run_wa_flow():
    load_dotenv()
    poll_interval = int(os.getenv("WHATSAPP_POLL_INTERVAL", 60))
    app_poll_interval = 10 # Interval for checking approved drafts
    
    print("\n" + "="*70)
    print("🚀 WHATSAPP FULL WORKFLOW ACTIVE")
    print(f"1. MONITORING : Browsing WhatsApp Web (Poll: {poll_interval}s)")
    print("2. DRAFTING   : AI detects new messages -> Needs_Action")
    print("3. SENDING    : Approved drafts are sent automatically via Browser")
    print("="*70)
    print("Keep the browser window open and scan QR if needed.\n")

    platinum_mode = os.getenv("PLATINUM_MODE", "local").lower()
    print(f"🌍 Current PLATINUM_MODE: {platinum_mode.upper()}")
    if platinum_mode == "cloud":
        print("☁️ Cloud node will only monitor INBOX. Sending is restricted to local node.")
    
    # Initialize Watcher (Handling incoming)
    wa_watcher = WhatsAppWatcher(poll_interval=poll_interval, headless=False)
    # Initialize Approval Execution (Handling outgoing)
    approval_watcher = ApprovalWatcher(poll_interval=app_poll_interval)
    
    agent_id = os.getenv("AGENT_ID", "wa_worker_01")
    locker = FileLocker(Path("./Vault"), agent_id)

    # CRITICAL: Since we want to use the same browser, we must share the page instance
    # The WhatsAppSender in approval_watcher.executor needs to know about wa_watcher's page

    try:
        # Start browser session
        success = await wa_watcher._initialize_browser()
        if not success:
            print("❌ WhatsApp Initialization Failed. Check logs.")
            return

        # Inject the shared page into the executor's WhatsApp sender
        if hasattr(approval_watcher.executor, "set_whatsapp_page"):
            approval_watcher.executor.set_whatsapp_page(wa_watcher._page)
        
        # We also need to make sure the ApprovalWatcher doesn't call execute() in a way
        # that blocks the main loop or starts its own loop if we are doing it manually.
        
        while True:
            ts = time.strftime("%H:%M:%S")
            
            # --- 1. Watch for INCOMING messages ---
            print(f"[{ts}] 🔍 Checking for new WhatsApp messages...")
            # Use the internal extraction but wrapped in error handling
            try:
                # This also creates task files in Needs_Action
                await wa_watcher._process_new_messages()
            except Exception as e:
                logger.error(f"Error during message extraction: {e}")

            # --- 2. Watch for APPROVED drafts to SEND ---
            # Instead of calling approval_watcher.start(), we poll it here manually
            # to keep everything in one async context and share the browser page.
            if platinum_mode == "local":
                for path in approval_watcher.approved_dir.iterdir():
                    if path.is_file() and path not in approval_watcher.seen:
                        claimed_path = locker.claim_file(path)
                        if not claimed_path:
                            approval_watcher.seen.add(path)
                            continue
                            
                        content = claimed_path.read_text(encoding='utf-8').lower()
                        if "platform: whatsapp" in content:
                            print(f"[{ts}] 📱 Sending Approved WhatsApp Message: {claimed_path.name}")
                            approval_watcher.seen.add(path)
                            # This uses the executor which now has the shared wa_watcher._page
                            approval_watcher._process_file(claimed_path)
                            
                            # Mark as done
                            locker.release_to_done(claimed_path)
                            # Brief wait after sending to avoid browser freezing
                            await asyncio.sleep(2)
                        else:
                            locker.release_to_folder(claimed_path, "Approved")

            # Wait for next cycle (default 60s)
            await asyncio.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n🛑 WhatsApp Flow stopped.")
    except Exception as e:
        print(f"\n❌ Script Error: {e}")
        logger.error(f"WhatsApp Flow failed: {e}")
    finally:
        await wa_watcher.cleanup()

if __name__ == "__main__":
    asyncio.run(run_wa_flow())
