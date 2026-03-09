
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

logger = get_logger("UnifiedWatcher")

async def run_unified_watcher():
    load_dotenv()
    
    poll_interval = int(os.getenv("GMAIL_POLL_INTERVAL", 30))
    app_poll_interval = 5 # Check approved folder every 5 seconds
    
    print("\n" + "="*70)
    print(f"🚀 UNIFIED AI EMPLOYEE WATCHER ACTIVE")
    print(f"1. GMAIL    : Polling every {poll_interval}s (Inbox -> Needs_Action)")
    print(f"2. APPROVAL : Polling every {app_poll_interval}s (Approved -> Done/Sent)")
    print("="*70)
    print("Press Ctrl+C to stop the system.\n")

    try:
        # Initialize Watchers
        gmail_watcher = GmailWatcher(poll_interval=poll_interval)
        approval_watcher = ApprovalWatcher(poll_interval=app_poll_interval)

        # We run them in a loop
        while True:
            # 1. Check Gmail
            ts_gmail = time.strftime("%H:%M:%S")
            print(f"[{ts_gmail}] 📧 Scanning Gmail...")
            gmail_found = gmail_watcher.poll_unread(max_results=5)
            if gmail_found:
                print(f"    ✨ Found {len(gmail_found)} new email(s). AI drafting started.")

            # 2. Check Approved Folder (The "Action" part)
            ts_app = time.strftime("%H:%M:%S")
            # We manually call a poll-like function for ApprovalWatcher
            # By default ApprovalWatcher.start is blocking, so we use a faster check.
            for path in approval_watcher.approved_dir.iterdir():
                if path.is_file() and path not in approval_watcher.seen:
                    print(f"[{ts_app}] ✅ APPROVED FILE DETECTED: {path.name}")
                    approval_watcher.seen.add(path)
                    approval_watcher._process_file(path)
            
            # Wait for next cycle
            await asyncio.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n🛑 System stopped by user.")
    except Exception as e:
        print(f"\n❌ System Error: {e}")
        logger.error(f"Unified Watcher failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_unified_watcher())
