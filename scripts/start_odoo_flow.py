
import os
import sys
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.logging_config import get_logger
from scripts.process_odoo_queue import process_odoo_queue
from src.watchers.approval_watcher import ApprovalWatcher

logger = get_logger("OdooFlow")

async def run_odoo_flow():
    load_dotenv()
    poll_interval = 10 # Check for Odoo actions every 10 seconds
    
    print("\n" + "="*70)
    print("🚀 ODOO FULL WORKFLOW ACTIVE")
    print("1. WATCHING   : Approved folder for Invoice/File actions")
    print("2. SYNCING    : Automatic ERP entry creation")
    print("3. ARCHIVING  : Moves processed items to Done")
    print("="*70)
    print("Press Ctrl+C to stop Odoo Flow.\n")

    approval_watcher = ApprovalWatcher(poll_interval=5)

    try:
        while True:
            ts = time.strftime("%H:%M:%S")
            # --- 1. Identify and process Odoo actions from Approved folder ---
            found = False
            for path in approval_watcher.approved_dir.iterdir():
                if path.is_file() and path not in approval_watcher.seen:
                    # Generic filter: if it's Odoo/Invoice related
                    content = path.read_text(encoding='utf-8').lower()
                    if "platform: file_action" in content or "invoice" in content or "odoo" in content:
                        print(f"[{ts}] 📊 Odoo Action Detected: {path.name}")
                        approval_watcher.seen.add(path)
                        approval_watcher._process_file(path)
                        found = True

            # --- 2. Run the actual ERP Sync Queue ---
            if found:
                print(f"[{ts}] ⚙️ Executing ERP Sync...")
                await process_odoo_queue()
                
            await asyncio.sleep(poll_interval)
            
    except KeyboardInterrupt:
        print("\n🛑 Odoo Flow stopped.")
    except Exception as e:
        logger.error(f"Odoo Flow failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_odoo_flow())
