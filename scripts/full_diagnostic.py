
import os
import asyncio
import json
import httpx
from dotenv import load_dotenv
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

async def test_odoo():
    print("\n--- [ODOO] Diagnostic ---")
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    user = os.getenv("ODOO_USERNAME")
    pwd = os.getenv("ODOO_PASSWORD")
    
    print(f"Connecting to: {url} ({db}) as {user}...")
    try:
        from ai_employee.integrations.odoo_client import get_odoo_client
        client = get_odoo_client()
        await client.initialize()
        info = await client.get_server_info()
        print(f"✅ Odoo Connection SUCCESS. Version: {info.get('version')}")
        await client.shutdown()
        return True
    except Exception as e:
        print(f"❌ Odoo Connection FAILED: {e}")
        return False

async def test_gmail():
    print("\n--- [GMAIL] Diagnostic ---")
    try:
        # Try both env and file
        token_str = os.getenv("GMAIL_TOKEN")
        if token_str:
            creds_data = json.loads(token_str)
            creds = Credentials.from_authorized_user_info(creds_data)
        elif Path("token.json").exists():
            creds = Credentials.from_authorized_user_file("token.json")
        else:
            print("❌ No Gmail credentials found.")
            return False

        service = build("gmail", "v1", credentials=creds)
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        print(f"✅ Gmail Connection SUCCESS. Found {len(labels)} labels.")
        return True
    except Exception as e:
        print(f"❌ Gmail Connection FAILED: {e}")
        return False

async def test_facebook():
    print("\n--- [FACEBOOK] Diagnostic ---")
    token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    
    if not token or not page_id:
        print("❌ Facebook credentials missing in .env")
        return False
        
    try:
        url = f"https://graph.facebook.com/v21.0/{page_id}?access_token={token}&fields=name,about"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            data = resp.json()
            if "error" in data:
                print(f"❌ Facebook API Error: {data['error'].get('message')}")
                return False
            print(f"✅ Facebook Connection SUCCESS. Page Name: {data.get('name')}")
            return True
    except Exception as e:
        print(f"❌ Facebook Connection FAILED: {e}")
        return False

async def test_whatsapp():
    print("\n--- [WHATSAPP] Diagnostic ---")
    token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    
    if not token or not phone_id:
        print("❌ WhatsApp credentials missing in .env")
        return False
        
    try:
        url = f"https://graph.facebook.com/v21.0/{phone_id}?access_token={token}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            data = resp.json()
            if "error" in data:
                print(f"❌ WhatsApp API Error: {data['error'].get('message')}")
                return False
            print(f"✅ WhatsApp Connection SUCCESS. Status: Available")
            return True
    except Exception as e:
        print(f"❌ WhatsApp Connection FAILED: {e}")
        return False

async def run_diagnostics():
    load_dotenv()
    print("🔍 Starting Full System Connectivity Diagnostic...")
    
    results = await asyncio.gather(
        test_odoo(),
        test_gmail(),
        test_facebook(),
        test_whatsapp()
    )
    
    print("\n" + "="*40)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*40)
    services = ["Odoo", "Gmail", "Facebook", "WhatsApp"]
    for i, res in enumerate(results):
        status = "✅ READY" if res else "❌ NEEDS FIXING"
        print(f"{services[i]:<10}: {status}")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
