
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.watchers.gmail_watcher import GmailWatcher
from src.config.logging_config import get_logger

logger = get_logger("GmailDemo")

async def demo_gmail():
    load_dotenv()
    print("\n" + "="*70)
    print("📧 GMAIL INTEGRATION DEMO — MONITORING UNREAD EMAILS")
    print("="*70)

    try:
        watcher = GmailWatcher(poll_interval=10)
        print("🔍 Scanning your Gmail Inbox for unread messages...")
        
        # Poll unread
        created_files = watcher.poll_unread(max_results=3)
        
        if created_files:
            print(f"\n✅ SUCCESS! Found {len(created_files)} unread messages.")
            for f in created_files:
                print(f"  📥 Task Created: {f.name}")
                print(f"  📂 Destination: {f.parent.resolve()}")
                
            print("\n💡 These emails have been converted into AI tasks.")
            print("They are now waiting in 'Vault/Workflow/Needs_Action' for your review.")
        else:
            print("\n📭 No unread messages found right now.")
            print("To see this in action, send an email to yourself and run this script again!")
            
            # For the sake of demo, let's simulate what happens when an email arrives
            print("\n[SIMULATING INCOMING EMAIL FOR DEMO]...")
            sim_path = Path("./Vault/Workflow/Needs_Action/GMAIL_SIM_123.md")
            sim_path.parent.mkdir(parents=True, exist_ok=True)
            content = """---
type: email
id: "sim_123"
from: "hamza.labs@example.com"
subject: "Request for AI Consultation"
status: pending
---
## Email Content
Hi Hamza, I am interested in your AI services. Can we schedule a meeting?

## Actions Required
- [ ] Draft a reply
"""
            sim_path.write_text(content, encoding='utf-8')
            print(f"  ✨ Simulated Email Task Created: {sim_path.name}")
            print(f"  📍 Path: {sim_path.resolve()}")

    except Exception as e:
        print(f"❌ Error during Gmail Demo: {e}")
        if "credentials" in str(e).lower():
            print("💡 Tip: Ensure your GMAIL_TOKEN is valid in .env")

    print("\n" + "="*70)
    print("📊 GMAIL DEMO COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(demo_gmail())
