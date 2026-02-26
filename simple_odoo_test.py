import requests
import json

# Direct test without all the complexity
url = "http://localhost:8069/jsonrpc"
headers = {"Content-Type": "application/json"}

payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "service": "common",
        "method": "login",
        "args": ["hackathon_zero", "admin", "admin123"]
    },
    "id": 1
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    result = response.json()

    if "result" in result:
        print("✅ SUCCESS! Connected to Odoo")
        print(f"User ID: {result['result']}")
    else:
        print("❌ Failed to connect")
        print(f"Error: {result}")

except Exception as e:
    print(f"❌ Error: {e}")
    print("Make sure Odoo is running at http://localhost:8069")