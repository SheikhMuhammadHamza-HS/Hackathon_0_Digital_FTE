import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

def test_gmail_all():
    load_dotenv()
    token_str = os.getenv("GMAIL_TOKEN")
    if not token_str:
        print("❌ GMAIL_TOKEN not found in .env")
        return
        
    try:
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info)
        service = build('gmail', 'v1', credentials=creds)
        
        # Get profile to see which account we are in
        profile = service.users().getProfile(userId='me').execute()
        print(f"👤 Connected to: {profile.get('emailAddress')}")
        
        print("\n🔍 Fetching LAST 10 EMAILS (regardless of status)...")
        results = service.users().messages().list(userId='me', maxResults=10).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("❌ No emails found in this account.")
        else:
            for msg in messages:
                msg_id = msg['id']
                msg_obj = service.users().messages().get(userId='me', id=msg_id).execute()
                subject = next((h['value'] for h in msg_obj['payload']['headers'] if h['name'].lower() == 'subject'), 'No Subject')
                labels = msg_obj.get('labelIds', [])
                is_unread = 'UNREAD' in labels
                print(f"   [{'UNREAD' if is_unread else ' READ '}] ID: {msg_id} | Subject: {subject}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_gmail_all()
