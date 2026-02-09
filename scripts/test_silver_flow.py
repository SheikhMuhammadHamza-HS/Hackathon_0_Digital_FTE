
import sys
import time
import shutil
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.services.task_generator import TaskGenerator
from src.agents.email_processor import EmailProcessor
from src.watchers.approval_watcher import ApprovalWatcher

def run_silver_test():
    print("=== Silver Tier Workflow Test ===")
    
    # 1. Setup paths
    inbox = Path(settings.INBOX_PATH)
    pending = Path(settings.PENDING_APPROVAL_PATH)
    approved = Path(settings.APPROVED_PATH)
    done = Path(settings.DONE_PATH)
    
    # Clean previous run
    test_file = inbox / "silver_test.txt"
    if test_file.exists(): test_file.unlink()
    
    # 2. Create Trigger (simulating FileWatcher)
    print("\n[Step 1] Creating Task (Trigger File)...")
    content = "Subject: Test Request\nTo: client@example.com\n\nPlease draft a reply to this email."
    test_file.write_text(content)
    print(f"Created file: {test_file}")
    
    from src.services.trigger_generator import TriggerGenerator
    
    # Generate trigger exactly as FileWatcher does
    trigger_file = TriggerGenerator.create_trigger_file(
        source_path=str(test_file),
        needs_action_dir=str(settings.NEEDS_ACTION_PATH)
    )
    
    if trigger_file:
        print(f"Trigger generated: {trigger_file.filename}")
    else:
        print("Failed to generate trigger file.")
        return

    # 3. AI Drafting
    print("\n[Step 2] AI Drafting (EmailProcessor)...")
    # trigger_file is already a TriggerFile object, no need to load from disk again
    
    processor = EmailProcessor()
    print("Sending to Gemini for drafting...")
    success = processor.process_trigger_file(trigger_file)
    
    if success:
        print("Draft Generated Successfully!")
    else:
        print("Draft Generation Failed.")
        return

    # Check Pending Approval
    time.sleep(1)  # Wait for file system
    drafts = list(pending.glob("*.md"))
    if not drafts:
        print("Error: No draft found in Pending_Approval")
        return
    latest_draft = sorted(drafts, key=lambda p: p.stat().st_mtime)[-1]
    
    print(f"\n[Step 3] Human Approval Required")
    print(f"Draft waiting at: {latest_draft}")
    print("\n--- ACTION REQUIRED ---")
    print("Option A: Manually move the file to the 'Approved' folder.")
    print("Option B: Press [ENTER] here to let the script move it for you.")
    print("Script is watching for the file to appear in /Approved...")

    dest = approved / latest_draft.name
    
    # Reactive polling loop
    start_wait = time.time()
    while not dest.exists():
        # Check if user pressed Enter (non-blocking in a multi-threaded way would be complex, 
        # so we'll just use a timeout or a short-circuit check)
        # For simplicity in this script, we'll check for the file REACTIVELY.
        if not latest_draft.exists():
            # If it's gone from Pending but not in Approved yet (latency), just wait
            time.sleep(0.5)
            if dest.exists(): break
            
        # Give the user a chance to press Enter or move manually
        # We'll use a 0.1s sleep to keep CPU low
        time.sleep(0.5)
        
        # If the user is still in the terminal, they might press Enter. 
        # But wait, input() is blocking. Let's use a timeout-based approach or just inform them.
        # IMPROVED: Just tell them to press Enter if they haven't moved it.
        if (time.time() - start_wait) > 30: # 30s timeout for auto-check
             break
             
    if not dest.exists():
        print("\n(Note: You can also just press Enter to proceed if you already moved it or want to move it now)")
        input("Press Enter to continue...")
        
    if latest_draft.exists() and not dest.exists():
        shutil.move(str(latest_draft), str(dest))
        print(f"Moved draft to: {dest}")
    elif dest.exists():
        print(f"File detected in Approved: {dest}")
    else:
        print(f"Error: Draft file not found.")
        return
    
    # 5. Execution
    print("\n[Step 4] Executing Approved Action...")
    watcher = ApprovalWatcher()
    # Manually process the file
    watcher._process_file(dest)
    
    print("\n=== Test Complete ===")
    print(f"Check {done} folder for final record.")
    print("Check Dashboard.md for event logs.")

if __name__ == "__main__":
    run_silver_test()
