import os
import json
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from pathlib import Path

def test_send_gmail():
    # Load from .env manually
    token_str = None
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if line.startswith("GMAIL_TOKEN="):
                token_str = line.split("=", 1)[1].strip()
                break

    if not token_str:
        print("GMAIL_TOKEN not found in .env")
        return

    token_data = json.loads(token_str)
    # Map 'token' to 'access_token' if needed
    if 'token' in token_data and 'access_token' not in token_data:
        token_data['access_token'] = token_data['token']
    
    creds = Credentials.from_authorized_user_info(token_data)
    service = build('gmail', 'v1', credentials=creds)

    message = MIMEText('This is a test from the Python debug script.')
    message['to'] = 'sheikhasadullah22@gmail.com'
    message['subject'] = 'Debug Test'
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    # Use the thread ID from the user's failed test
    thread_id = "19c708f72f09095e"
    
    try:
        sent = service.users().messages().send(
            userId='me', 
            body={'raw': raw, 'threadId': thread_id}
        ).execute()
        print(f"Success! Message ID: {sent['id']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_send_gmail()
