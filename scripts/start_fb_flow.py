
import os
import sys
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.logging_config import get_logger
from src.watchers.approval_watcher import ApprovalWatcher

logger = get_logger("FacebookFlow")

async def run_fb_flow():
    load_dotenv()
    poll_interval = 30 # Check for Facebook posts/mentions every 30 seconds
    
    print("\n" + "="*70)
    print("🚀 FACEBOOK FULL WORKFLOW ACTIVE")
    print("1. MONITORING : Watch for Meta Page Mentions/Tags")
    print("2. POSTING    : Scheduled/Approved drafts posted to Feed")
    print("="*70)
    print("Press Ctrl+C to stop Facebook Flow.\n")

    approval_watcher = ApprovalWatcher(poll_interval=5)

    try:
        while True:
            ts = time.strftime("%H:%M:%S")
            # --- 1. Identify and process Facebook Actions from Approved folder ---
            for path in approval_watcher.approved_dir.iterdir():
                if path.is_file() and path not in approval_watcher.seen:
                    content = path.read_text(encoding='utf-8').lower()
                    if "platform: facebook" in content:
                        print(f"[{ts}] 🔵 Facebook Post Detected: {path.name}")
                        approval_watcher.seen.add(path)
                        approval_watcher._process_file(path)

            # --- 2. Optional: Pull mentions or stats from API ---
            # (Mentions pulling logic would go here)
            
            await asyncio.sleep(poll_interval)
            
    except KeyboardInterrupt:
        print("\n🛑 Facebook Flow stopped.")
    except Exception as e:
        logger.error(f"Facebook Flow failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_fb_flow())
