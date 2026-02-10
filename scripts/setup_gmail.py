
import os
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def setup_gmail():
    print("=== Gmail OAuth Setup Assistant ===")
    
    creds_path = Path("credentials.json")
    if not creds_path.exists():
        print("Error: credentials.json not found in the root directory.")
        print("Please rename your downloaded JSON to 'credentials.json' and place it here.")
        return

    print("Step 1: Initiating OAuth Flow...")
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    
    # This will open a browser window for login
    creds = flow.run_local_server(port=0)
    
    # Save the credentials for the next run
    token_data = json.loads(creds.to_json())
    token_path = Path("token.json")
    token_path.write_text(json.dumps(token_data, indent=4))
    
    print("\nSuccess! ✅")
    print(f"Token saved to: {token_path}")
    print("You can now start the agent, and it will monitor your real Gmail inbox.")

if __name__ == "__main__":
    try:
        setup_gmail()
    except Exception as e:
        print(f"\nFailed to setup Gmail: {e}")
        print("\nNote: Make sure you have installed the required libraries:")
        print("pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
