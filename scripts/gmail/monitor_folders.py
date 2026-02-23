#!/usr/bin/env python3
"""
Monitor Approved and Done folders in real-time
"""

import time
import os
from pathlib import Path

def monitor_folders():
    """Monitor folder changes"""
    print("="*60)
    print("FOLDER MONITOR")
    print("="*60)

    approved = Path("Approved")
    done = Path("Done")
    failed = Path("Failed")

    print("\nWatching folders...")
    print("Press Ctrl+C to stop\n")

    last_approved = set()
    last_done = set()
    last_failed = set()

    try:
        while True:
            # Get current files
            current_approved = set(f.name for f in approved.glob("*.md"))
            current_done = set(f.name for f in done.glob("*.md"))
            current_failed = set(f.name for f in failed.glob("*.md"))

            # Check for new files
            new_approved = current_approved - last_approved
            new_done = current_done - last_done
            new_failed = current_failed - last_failed

            if new_approved:
                for f in new_approved:
                    print(f"[{time.strftime('%H:%M:%S')}] 📥 APPROVED: {f}")
            if new_done:
                for f in new_done:
                    print(f"[{time.strftime('%H:%M:%S')}] ✅ DONE: {f}")
            if new_failed:
                for f in new_failed:
                    print(f"[{time.strftime('%H:%M:%S')}] ❌ FAILED: {f}")

            # Update last seen
            last_approved = current_approved
            last_done = current_done
            last_failed = current_failed

            # Show status every 5 seconds
            if int(time.time()) % 5 == 0:
                print(f"[{time.strftime('%H:%M:%S')}] Status: Approved={len(current_approved)}, Done={len(current_done)}, Failed={len(current_failed)}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

if __name__ == "__main__":
    monitor_folders()