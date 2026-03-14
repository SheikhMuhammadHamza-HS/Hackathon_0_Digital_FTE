import os
import sys
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.logging_config import get_logger

logger = get_logger("DashboardUpdater")

async def run_dashboard_updater():
    load_dotenv()
    poll_interval = int(os.getenv("DASHBOARD_POLL_INTERVAL", 15))
    
    print("\n" + "="*70)
    print("🚀 DASHBOARD SINGLE-WRITER DAEMON (PLATINUM TIER)")
    print("="*70)
    
    platinum_mode = os.getenv("PLATINUM_MODE", "local").lower()
    print(f"🌍 Current PLATINUM_MODE: {platinum_mode.upper()}")
    
    if platinum_mode == "cloud":
        print("☁️ Running in cloud mode. Skipping Dashboard merging.")
        print("   The Cloud node only writes signals to Vault/Updates/.")
        print("   The Local node is responsible for writing to Dashboard.md.")
        return
        
    print("💻 Running in local mode. Merging signals into Dashboard.md...")
    
    updates_dir = Path("./Vault/Updates")
    archive_dir = Path("./Vault/Archive/Updates")
    dashboard_path = Path("./Dashboard.md")
    vault_dashboard_path = Path("./Vault/Dashboard.md")
    
    updates_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Check which dashboard file exists
    if not dashboard_path.exists() and vault_dashboard_path.exists():
        dashboard_path = vault_dashboard_path
        
    if not dashboard_path.exists():
        print(f"⚠️ Dashboard file not found at {dashboard_path}. A new one will be created.")
        dashboard_path.write_text("# 🤖 AI Employee — Main Dashboard\n\n", encoding="utf-8")

    while True:
        try:
            signals = list(updates_dir.glob("*.md")) + list(updates_dir.glob("*.txt"))
            
            if signals:
                with open(dashboard_path, "a", encoding="utf-8") as f:
                    for signal in signals:
                        ts = time.strftime("%H:%M:%S")
                        print(f"[{ts}] 📝 Merging update signal: {signal.name}")
                        content = signal.read_text(encoding="utf-8").strip()
                        
                        # Add a separator if it's not a table row
                        if not content.startswith("|"):
                            content = f"\n### Update from Cloud Agent ({signal.name})\n" + content + "\n"
                        else:
                            content = "\n" + content
                            
                        f.write(content)
                        
                        # Move to archive to prevent duplicate processing
                        archived_path = archive_dir / signal.name
                        signal.rename(archived_path)
            
            await asyncio.sleep(poll_interval)
            
        except KeyboardInterrupt:
            print("\n🛑 Dashboard Updater stopped.")
            break
        except Exception as e:
            logger.error(f"Error merging dashboard updates: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_dashboard_updater())
