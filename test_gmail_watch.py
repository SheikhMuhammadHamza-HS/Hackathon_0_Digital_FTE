import os
import json
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

def watch_gmail():
    load_dotenv()
    token_str = os.getenv("GMAIL_TOKEN")
    if not token_str:
        print("❌ GMAIL_TOKEN not found in .env")
        return
        
    try:
        token_info = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_info)
        service = build('gmail', 'v1', credentials=creds)
        
        print("👀 GMAIL WATCHER ACTIVE - Waiting for UNREAD emails...")
        print("   (Har 10 sec mein check ho raha hai... Ctrl+C to stop)")
        
        last_found = set()
        
        while True:
            results = service.users().messages().list(userId='me', q='is:unread', maxResults=5).execute()
            messages = results.get('messages', [])
            
            found_ids = {m['id'] for m in messages}
            new_ids = found_ids - last_found
            
            if new_ids:
                print(f"\n✨ NEW EMAIL(S) DETECTED! ({len(new_ids)})")
                for msg_id in new_ids:
                    msg_obj = service.users().messages().get(userId='me', id=msg_id).execute()
                    subject = next((h['value'] for h in msg_obj['payload']['headers'] if h['name'].lower() == 'subject'), 'No Subject')
                    sender = next((h['value'] for h in msg_obj['payload']['headers'] if h['name'].lower() == 'from'), 'Unknown')
                    print(f"   📧 From: {sender} | Subject: {subject}")
                
            last_found = found_ids
            time.sleep(10)
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    watch_gmail()
