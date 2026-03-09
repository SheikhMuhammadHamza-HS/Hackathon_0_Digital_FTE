
import os
import sys
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.watchers.gmail_watcher import GmailWatcher
from src.config.logging_config import get_logger

logger = get_logger("GmailAutoWatcher")

async def run_continuous_gmail_watcher():
    load_dotenv()
    
    # Set the poll interval in .env or default to 30
    poll_interval = int(os.getenv("GMAIL_POLL_INTERVAL", 30))
    
    print("\n" + "="*70)
    print(f"🚀 GMAIL AUTO-WATCHER (POLL: {poll_interval}s)")
    print("Workflow: Inbox -> Needs_Action -> AI Plan & Draft -> Approval")
    print("="*70)
    print("Press Ctrl+C to stop the watcher.\n")

    try:
        # Initialize the watcher with the desired interval
        watcher = GmailWatcher(poll_interval=poll_interval)
        
        while True:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] 🔍 Checking for new emails...")
            
            # Poll unread: This function in gmail_watcher already:
            # 1. Detects unread email
            # 2. Creates .md in Needs_Action
            # 3. Marks as READ in Gmail
            # 4. Triggers EmailProcessor to create Plan and Draft in Pending_Approval
            created_files = watcher.poll_unread(max_results=5)
            
            if created_files:
                print(f"  ✨ Found {len(created_files)} new email(s)!")
                for f in created_files:
                    print(f"    ✅ Task Created: {f.name}")
                    print(f"    📝 AI Plan & Draft generated in Pending_Approval")
            else:
                print("  📭 No new emails.")

            await asyncio.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n🛑 Watcher stopped by user.")
    except Exception as e:
        print(f"\n❌ Watcher Error: {e}")
        logger.error(f"Gmail Auto-Watcher failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_continuous_gmail_watcher())
