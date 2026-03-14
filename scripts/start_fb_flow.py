
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
from ai_employee.utils.file_locker import FileLocker

logger = get_logger("FacebookFlow")

async def run_fb_flow():
    load_dotenv()
    poll_interval = 30 # Check for Facebook posts/mentions every 30 seconds
    
    print("\n" + "="*70)
    print("🚀 FACEBOOK FULL WORKFLOW ACTIVE")
    print("1. MONITORING : Watch for Meta Page Mentions/Tags")
    print("2. POSTING    : Scheduled/Approved drafts posted to Feed")
    print("="*70)
    
    platinum_mode = os.getenv("PLATINUM_MODE", "local").lower()
    print(f"🌍 Current PLATINUM_MODE: {platinum_mode.upper()}")
    if platinum_mode == "cloud":
        print("☁️ Cloud node will only monitor. Posting is restricted to local node.")
    print("Press Ctrl+C to stop Facebook Flow.\n")

    agent_id = os.getenv("AGENT_ID", "fb_worker_01")
    locker = FileLocker(Path("./Vault"), agent_id)
    approval_watcher = ApprovalWatcher(poll_interval=5)

    try:
        while True:
            ts = time.strftime("%H:%M:%S")
            # --- 1. Identify and process Facebook Actions from Approved folder ---
            if platinum_mode == "local":
                for path in approval_watcher.approved_dir.iterdir():
                    if path.is_file() and path not in approval_watcher.seen:
                        # Skip if already claimed by someone else
                        claimed_path = locker.claim_file(path)
                        if not claimed_path:
                            approval_watcher.seen.add(path) # Mark seen so we don't try again
                            continue
    
                        content = claimed_path.read_text(encoding='utf-8').lower()
                        if "platform: facebook" in content:
                            print(f"[{ts}] 🔵 Facebook Post Detected: {claimed_path.name}")
                            approval_watcher.seen.add(path) # Add original path to seen
                            approval_watcher._process_file(claimed_path)
                            
                            # Move to Done folder after processing
                            locker.release_to_done(claimed_path)
                        else:
                            # If not FB, release back to Approved for other agents
                            locker.release_to_folder(claimed_path, "Approved")

            # --- 2. Optional: Pull mentions or stats from API ---
            # (Mentions pulling logic would go here)
            
            await asyncio.sleep(poll_interval)
            
    except KeyboardInterrupt:
        print("\n🛑 Facebook Flow stopped.")
    except Exception as e:
        logger.error(f"Facebook Flow failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_fb_flow())
