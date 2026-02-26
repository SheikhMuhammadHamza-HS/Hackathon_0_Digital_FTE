#!/usr/bin/env python3
"""
Test Direct Local Odoo API Connection
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_local_odoo_api():
    print("="*60)
    print("TESTING LOCAL ODOO API")
    print("="*60)

    # Get configuration from environment
    odoo_url = os.getenv("ODOO_URL", "http://localhost:8069")
    odoo_db = os.getenv("ODOO_DB", "hackathon_zero")
    odoo_user = os.getenv("ODOO_USERNAME", "admin")
    odoo_password = os.getenv("ODOO_PASSWORD", "admin")

    auth_url = f"{odoo_url}/web/session/authenticate"
    headers = {"Content-Type": "application/json"}

    data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": odoo_db,
            "login": odoo_user,
            "password": odoo_password
        }
    }

    print(f"\nConnecting to: {auth_url}")
    print(f"Database: {odoo_db}")
    print(f"Login: {odoo_user}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, json=data, headers=headers) as response:
                print(f"\nStatus Code: {response.status}")

                if response.status == 200:
                    result = await response.json()

                    if "result" in result:
                        session_info = result["result"]
                        print(f"\n[OK] Authentication Successful!")
                        print(f"User ID: {session_info.get('uid')}")
                        print(f"Company: {session_info.get('company_id')}")
                        print(f"Name: {session_info.get('name')}")
                        print(f"Username: {session_info.get('username')}")
                        print(f"Database: {session_info.get('db')}")

                        # Test a simple API call
                        print(f"\nTesting simple API call...")

                        test_url = f"{odoo_url}/web/dataset/call_kw"
                        test_data = {
                            "jsonrpc": "2.0",
                            "method": "call",
                            "params": {
                                "model": "res.users",
                                "method": "search",
                                "args": [[]],
                                "kwargs": {}
                            }
                        }

                        # Add session to context
                        if session_info.get("session_id"):
                            test_data["params"]["kwargs"] = {"session_id": session_info["session_id"]}

                        async with session.post(test_url, json=test_data, headers=headers) as test_response:
                            if test_response.status == 200:
                                test_result = await test_response.json()
                                if "result" in test_result:
                                    users = test_result["result"]
                                    print(f"[OK] API Test Successful! Found {len(users)} users")
                                else:
                                    print("[WARNING] API Test: No 'result' in response")
                            else:
                                print(f"[ERROR] API Test Failed: HTTP {test_response.status}")

                        # Check if Accounting app is installed
                        print(f"\nChecking Accounting module...")
                        module_check = {
                            "jsonrpc": "2.0",
                            "method": "call",
                            "params": {
                                "model": "ir.module.module",
                                "method": "search",
                                "args": [[["name", "=", "account"]]],
                                "kwargs": {}
                            }
                        }

                        async with session.post(test_url, json=module_check, headers=headers) as mod_response:
                            if mod_response.status == 200:
                                mod_result = await mod_response.json()
                                if "result" in mod_result and mod_result["result"]:
                                    print(f"[OK] Accounting module found!")
                                else:
                                    print("[INFO] Accounting module not installed - you may need to install it")
                    else:
                        error_msg = result.get("error", {}).get("data", {}).get("message", "Unknown error")
                        print(f"[ERROR] Authentication Failed: {error_msg}")
                else:
                    print(f"[ERROR] HTTP Error: {response.status}")
                    error_text = await response.text()
                    print(f"Response: {error_text}")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        print("\nPossible issues:")
        print("1. Odoo is not running on localhost:8069")
        print("2. Database 'hackathon_zero' doesn't exist")
        print("3. Wrong admin credentials")
        print("4. Network connectivity issues")

        print("\nSuggestions:")
        print("1. Make sure Odoo is running: http://localhost:8069")
        print("2. Create database 'hackathon_zero' if it doesn't exist")
        print("3. Use admin/admin for default local Odoo")

if __name__ == "__main__":
    asyncio.run(test_local_odoo_api())