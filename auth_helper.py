import json
import os
from pathlib import Path

def setup_auth():
    print("=== Authentication Helper ===")
    
    # 1. Setup Gmail Token
    print("\n📧 Configuring Gmail Authentication...")
    token_path = Path("token.json")
    creds_path = Path("credentials.json")
    
    gmail_token = {}
    
    if token_path.exists():
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                token_data = json.load(f)
                gmail_token.update(token_data)
            print("  ✅ Read token.json")
        except Exception as e:
            print(f"  ❌ Failed to read token.json: {e}")
            
    if creds_path.exists():
        try:
            with open(creds_path, "r", encoding="utf-8") as f:
                creds_data = json.load(f)
                # Google credentials often have a top-level key like 'installed' or 'web'
                if "installed" in creds_data:
                    client_config = creds_data["installed"]
                elif "web" in creds_data:
                    client_config = creds_data["web"]
                else:
                    client_config = creds_data
                
                gmail_token["client_id"] = client_config.get("client_id")
                gmail_token["client_secret"] = client_config.get("client_secret")
                gmail_token["redirect_uri"] = client_config.get("redirect_uris", ["http://localhost"])[0]
            print("  ✅ Read credentials.json")
        except Exception as e:
            print(f"  ❌ Failed to read credentials.json: {e}")
    
    if gmail_token:
        # Create the single-line JSON string for the environment variable
        gmail_token_str = json.dumps(gmail_token)
        update_env("GMAIL_TOKEN", gmail_token_str)
        print("  ✅ Updated .env with GMAIL_TOKEN")
    else:
        print("  ⚠️ Could not construct GMAIL_TOKEN. Ensure token.json and credentials.json exist.")

    # 2. Setup LinkedIn Token
    print("\n🔗 Configuring LinkedIn Authentication...")
    linkedin_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    linkedin_user = os.getenv("LINKEDIN_USER_ID")
    
    if not linkedin_token:
        print("  ❌ LINKEDIN_ACCESS_TOKEN not found in environment. Please add it manually to .env")
    else:
        print("  ✅ LINKEDIN_ACCESS_TOKEN already set")
        
    if not linkedin_user:
        print("  ℹ️ LINKEDIN_USER_ID not found in environment (optional).")
    else:
        print("  ✅ LINKEDIN_USER_ID already set")

def update_env(key, value):
    env_path = Path(".env")
    lines = []
    
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    
    # Check if key exists and update it, otherwise append
    new_lines = []
    key_found = False
    
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            key_found = True
        else:
            new_lines.append(line)
            
    if not key_found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"{key}={value}\n")
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    setup_auth()
