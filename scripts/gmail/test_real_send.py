#!/usr/bin/env python3
"""
Test Real Email Sending - Test the updated EmailSender
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

from src.agents.email_sender import EmailSender

def test_real_send():
    """Test sending a real email"""
    print("="*60)
    print("TESTING REAL EMAIL SENDING")
    print("="*60)

    # Create EmailSender
    sender = EmailSender()

    # Check if MCP is available
    print(f"MCP Available: {sender.use_mcp}")

    # Create test draft
    test_draft = project_root / "Approved" / "test_direct_send.md"
    test_content = """Subject: Direct Gmail API Test
Platform: email
To: hamza sheikh <sheikhmhamza37@gmail.com>

This is a direct test of the Gmail API integration.
Testing if real emails are sent instead of mock mode.

Time: $(date)
"""

    test_draft.write_text(test_content)
    print(f"\nCreated test draft: {test_draft.name}")

    # Send the email
    print("\nSending email...")
    success = sender.send_draft(test_draft)

    if success:
        print("\n[SUCCESS] Email sent successfully!")
    else:
        print("\n[FAIL] Email failed to send")

    # Check if file was moved
    if test_draft.exists():
        print("\nNote: File still in Approved - check Failed folder")
    else:
        print("\nFile moved from Approved folder")

if __name__ == "__main__":
    test_real_send()