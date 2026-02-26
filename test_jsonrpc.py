import requests
import json

url = "http://localhost:8069/web/session/authenticate"
db = "odoo_hackathon"
username = "admin"
password = "admin"

payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "db": db,
        "login": username,
        "password": password
    }
}

print(f"Testing JSON-RPC at {url}...")
try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    result = response.json()
    if "error" in result:
        print(f"ERROR: {result['error']}")
    else:
        print(f"SUCCESS! Result: {result.get('result', {}).get('uid')}")
        print(f"Session ID: {result.get('result', {}).get('session_id')}")
except Exception as e:
    print(f"FAILED: {e}")
