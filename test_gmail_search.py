import os
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

def test_gmail():
    load_dotenv()
    token_str = os.getenv("GMAIL_TOKEN")
    if not token_str:
        print("❌ GMAIL_TOKEN not found in .env")
        return
        
    try:
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info)
        service = build('gmail', 'v1', credentials=creds)
        
        print("🔍 Searching for UNREAD emails...")
        results = service.users().messages().list(userId='me', q='is:unread', maxResults=5).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("✅ No unread emails found.")
        else:
            print(f"✨ Found {len(messages)} unread email(s):")
            for msg in messages:
                msg_id = msg['id']
                msg_obj = service.users().messages().get(userId='me', id=msg_id).execute()
                subject = next((h['value'] for h in msg_obj['payload']['headers'] if h['name'].lower() == 'subject'), 'No Subject')
                print(f"   - ID: {msg_id} | Subject: {subject}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_gmail()
