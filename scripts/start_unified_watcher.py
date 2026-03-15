
import os
import sys
import time
import asyncio
import threading
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.watchers.gmail_watcher import GmailWatcher
from src.watchers.approval_watcher import ApprovalWatcher
from src.config.logging_config import get_logger
from scripts.process_odoo_queue import process_odoo_queue

logger = get_logger("UnifiedWatcher")

async def run_unified_watcher():
    load_dotenv()
    
    poll_interval = int(os.getenv("GMAIL_POLL_INTERVAL", 30))
    app_poll_interval = 5 # Check approved folder every 5 seconds
    
    print("\n" + "="*70)
    print(f"🚀 UNIFIED AI EMPLOYEE WATCHER ACTIVE")
    print(f"1. GMAIL    : Polling every {poll_interval}s (Inbox -> Needs_Action)")
    print(f"2. APPROVAL : Polling every {app_poll_interval}s (Approved -> Done/Sent)")
    print(f"3. ODOO     : Syncing triggers to ERP automatically")
    
    platinum_mode = os.getenv("PLATINUM_MODE", "local").lower()
    print(f"🌍 PLATINUM MODE: {platinum_mode.upper()}")
    print("="*70)
    
    print("Press Ctrl+C to stop the system.\n")

    try:
        # Initialize Watchers
        gmail_watcher = GmailWatcher(poll_interval=poll_interval)
        approval_watcher = ApprovalWatcher(poll_interval=app_poll_interval)

        # We run them in a loop
        while True:
            # --- 1. GMAIL SCAN ---
            ts_gmail = time.strftime("%H:%M:%S")
            print(f"[{ts_gmail}] 📧 Scanning Gmail...")
            gmail_found = gmail_watcher.poll_unread(max_results=5)
            if gmail_found:
                print(f"    ✨ Found {len(gmail_found)} new email(s). AI drafting started.")

            # --- 2. APPROVAL MONITOR (Action Execution) ---
            if platinum_mode == "local":
                ts_app = time.strftime("%H:%M:%S")
                for path in approval_watcher.approved_dir.iterdir():
                    if path.is_file() and path not in approval_watcher.seen:
                        print(f"[{ts_app}] ✅ APPROVED FILE DETECTED: {path.name}")
                        approval_watcher.seen.add(path)
                        # This executes the action (Email/Odoo Trigger)
                        approval_watcher._process_file(path)
            else:
                # Cloud node doesn't process approvals
                pass
                
            
            # --- 3. ODOO QUEUE (Sync Triggers to ERP) ---
            await process_odoo_queue()
            
            # Wait for next cycle (poll_interval is e.g. 30s)
            await asyncio.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n🛑 System stopped by user.")
    except Exception as e:
        print(f"\n❌ System Error: {e}")
        logger.error(f"Unified Watcher failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_unified_watcher())
