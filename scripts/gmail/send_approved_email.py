#!/usr/bin/env python3
"""
Send Approved Email - Direct Gmail API sending
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

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
import email
from email.mime.text import MIMEText

def send_email():
    """Send approved email"""
    print("="*60)
    print("SENDING APPROVED EMAIL")
    print("="*60)

    # Get Gmail token from env
    gmail_token_str = os.getenv("GMAIL_TOKEN")
    if not gmail_token_str:
        print("[ERROR] GMAIL_TOKEN not found in environment")
        return False

    # Parse token
    import json
    token_info = json.loads(gmail_token_str)
    creds = Credentials.from_authorized_user_info(token_info)

    # Build Gmail service
    try:
        service = build('gmail', 'v1', credentials=creds)
        print("[OK] Gmail service connected")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Gmail: {e}")
        return False

    # Find approved email
    approved_dir = project_root / "Approved"
    approved_files = list(approved_dir.glob("*.md"))

    if not approved_files:
        print("[INFO] No approved emails found")
        return True

    # Send each approved email
    for draft_file in approved_files:
        print(f"\nProcessing: {draft_file.name}")

        # Parse draft
        content = draft_file.read_text()
        lines = content.split('\n')

        to_addr = None
        subject = None
        thread_id = None
        message_id = None
        body_start = 0

        for i, line in enumerate(lines):
            if line.startswith("To: "):
                to_addr = line[4:]
            elif line.startswith("Subject: "):
                subject = line[9:]
            elif line.startswith("Thread-ID: "):
                thread_id = line[11:]
            elif line.startswith("Message-ID: "):
                message_id = line[12:]
            elif line.strip() == "" and body_start == 0:
                body_start = i + 1

        if not to_addr or not subject:
            print(f"[ERROR] Missing To or Subject in {draft_file.name}")
            continue

        # Extract body
        body = '\n'.join(lines[body_start:]).strip()

        # Create message
        message = MIMEText(body)
        message['to'] = to_addr
        message['subject'] = subject

        if message_id:
            message['In-Reply-To'] = message_id
            message['References'] = message_id

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Send email
        try:
            if thread_id:
                # Send as reply
                result = service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message, 'threadId': thread_id}
                ).execute()
            else:
                # Send as new email
                result = service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()

            print(f"[OK] Email sent! Message ID: {result['id']}")

            # Move to Done
            done_dir = project_root / "Done"
            draft_file.rename(done_dir / draft_file.name)
            print(f"[OK] Moved to Done folder")

        except Exception as e:
            print(f"[ERROR] Failed to send email: {e}")

    return True

if __name__ == "__main__":
    success = send_email()
    sys.exit(0 if success else 1)