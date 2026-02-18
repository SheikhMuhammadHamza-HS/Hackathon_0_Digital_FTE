#!/usr/bin/env python3
"""
Test Gmail automation with REAL emails from your inbox.
"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.watchers.gmail_watcher import GmailWatcher
from src.config.settings import settings

def test_real_gmail():
    print("\n" + "="*60)
    print("REAL GMAIL TEST")
    print("="*60)
    print(f"Testing with live Gmail account at: {datetime.now()}")
    print()

    # Initialize watcher
    print("[1/3] Initializing Gmail watcher...")
    watcher = GmailWatcher(poll_interval=60)
    print("[OK] Gmail watcher initialized\n")

    # Poll for unread messages
    print("[2/3] Checking for unread emails in your inbox...")
    print("      (This will check up to 5 unread messages)")
    print()

    created_files = watcher.poll_unread(max_results=5)

    if created_files:
        print(f"\n[OK] SUCCESS! Found and processed {len(created_files)} unread email(s):")
        print()

        for i, file_path in enumerate(created_files, 1):
            print(f"  Email #{i}:")
            print(f"    Task File: {file_path.name}")

            # Read and show details
            try:
                content = file_path.read_text(encoding='utf-8')
                for line in content.split('\n'):
                    if line.startswith('from:'):
                        print(f"    From: {line.split(':', 1)[1].strip()}")
                    elif line.startswith('subject:'):
                        print(f"    Subject: {line.split(':', 1)[1].strip()}")
                    elif line.startswith('received_at:'):
                        print(f"    Received: {line.split(':', 1)[1].strip()}")
                print()
            except Exception as e:
                print(f"    [Error reading file: {e}]")

        print("[3/3] AI Processing...")
        print("      The email processor should automatically create drafts")
        print("      in Pending_Approval folder.")
        print()

        # Wait a moment for processing
        time.sleep(2)

        # Check for new drafts
        from pathlib import Path
        pending = Path(settings.PENDING_APPROVAL_PATH)
        drafts = sorted(pending.glob('*.md'), key=lambda x: x.stat().st_mtime)

        if drafts:
            print(f"[OK] Found {len(drafts)} draft(s) in Pending_Approval:")
            for draft in drafts[-5:]:  # Show last 5
                print(f"    - {draft.name}")
        else:
            print("[INFO] No drafts found yet (may still be processing)")

        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("="*60)
        print("1. Check Needs_Action folder - task files were created")
        print("2. Check Pending_Approval folder - AI drafts should appear")
        print("3. Review drafts and move to Approved to send")
        print()
        print("To run continuously, use:")
        print("  python -m src.cli.main start")

        return True

    else:
        print("\n[INFO] No unread emails found in your inbox.")
        print()
        print("To test with real emails:")
        print("  1. Send an email to your Gmail account")
        print("  2. Mark it as UNREAD")
        print("  3. Run this test again")
        print()
        return False

if __name__ == "__main__":
    success = test_real_gmail()
    sys.exit(0 if success else 1)
