#!/usr/bin/env python3
"""
Debug Approval Path - Check where ApprovalWatcher is looking
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
env_file = project_root / "scripts" / "config" / ".env"
if env_file.exists():
    load_dotenv(env_file)

from src.config import settings

print("="*60)
print("APPROVAL PATH DEBUG")
print("="*60)

print(f"\nProject Root: {project_root}")
print(f"Base Dir from Settings: {Path(settings.BASE_DIR)}")
print(f"APPROVED_PATH from Settings: {settings.APPROVED_PATH}")
print(f"Full Expected Path: {Path(settings.BASE_DIR) / settings.APPROVED_PATH}")

# Check if files exist
approved_dir = project_root / "Approved"
print(f"\nApproved Dir: {approved_dir}")
print(f"Exists: {approved_dir.exists()}")

if approved_dir.exists():
    files = list(approved_dir.glob("*.md"))
    print(f"Files found ({len(files)}):")
    for f in files:
        print(f"  - {f.name}")
else:
    print(" Approved directory not found!")

# Check where ApprovalWatcher would look
try:
    from src.watchers.approval_watcher import ApprovalWatcher
    watcher = ApprovalWatcher()
    print(f"\nApprovalWatcher is looking at: {watcher.approved_dir}")
    print(f"Watcher's approved dir exists: {watcher.approved_dir.exists()}")

    if watcher.approved_dir.exists():
        files = list(watcher.approved_dir.glob("*.md"))
        print(f"Files in watcher dir ({len(files)}):")
        for f in files:
            print(f"  - {f.name}")
except Exception as e:
    print(f"\nError creating ApprovalWatcher: {e}")