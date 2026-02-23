#!/usr/bin/env python3
"""
Clean Gmail Agent - Without warnings
"""

import warnings
import os
import asyncio
from pathlib import Path

# Suppress all warnings
warnings.filterwarnings("ignore")

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables to fix cache issues
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

# Load environment
from dotenv import load_dotenv
env_file = project_root / "scripts" / "config" / ".env"
if env_file.exists():
    load_dotenv(env_file)

async def check_and_send():
    """Check Approved folder and send emails"""
    print("="*60)
    print("GMAIL CLEAN SENDER")
    print("="*60)

    approved_dir = project_root / "Approved"
    files = list(approved_dir.glob("*.md"))

    if not files:
        print("[INFO] No files in Approved folder")
        return

    print(f"[INFO] Found {len(files)} file(s) in Approved")

    for file in files:
        print(f"\n[PROCESSING] {file.name}")

        # Check format
        content = file.read_text()
        if "Platform:" not in content:
            print(f"[ERROR] Missing 'Platform:' line in {file.name}")
            continue

        # Parse
        lines = content.split('\n')
        platform = None
        to_addr = None
        subject = None

        for line in lines:
            if line.startswith("Platform:"):
                platform = line.split(":", 1)[1].strip()
            elif line.startswith("To:"):
                to_addr = line.split(":", 1)[1].strip()
            elif line.startswith("Subject:"):
                subject = line.split(":", 1)[1].strip()

        print(f"  Platform: {platform}")
        print(f"  To: {to_addr}")
        print(f"  Subject: {subject}")

        if platform == "email":
            # Send using direct sender
            from send_approved_email import send_email
            send_email()
            break
        else:
            print(f"[WARN] Unsupported platform: {platform}")

    print("\n[DONE]")

if __name__ == "__main__":
    import sys
    asyncio.run(check_and_send())