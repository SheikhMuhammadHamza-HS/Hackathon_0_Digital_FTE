#!/usr/bin/env python3
"""
Test Direct Odoo.com API Connection
"""

import asyncio
import aiohttp
import json

async def test_direct_api():
    print("="*60)
    print("TESTING DIRECT ODOO.COM API")
    print("="*60)

    url = "https://just-me1.odoo.com/web/session/authenticate"
    headers = {"Content-Type": "application/json"}

    data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": "just-me1",
            "login": "sheikhmhamza37@gmail.com",
            "password": "oddoHackathonZero123"
        }
    }

    print(f"\nConnecting to: {url}")
    print(f"Database: just-me1")
    print(f"Login: sheikhmhamza37@gmail.com")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                print(f"\nStatus Code: {response.status}")

                if response.status == 200:
                    result = await response.json()

                    if "result" in result:
                        session_info = result["result"]
                        print(f"\n✅ Authentication Successful!")
                        print(f"User ID: {session_info.get('uid')}")
                        print(f"Company: {session_info.get('company_id')}")
                        print(f"Name: {session_info.get('name')}")
                        print(f"Username: {session_info.get('username')}")
                        print(f"Database: {session_info.get('db')}")

                        # Test a simple API call
                        print(f"\nTesting simple API call...")

                        test_url = "https://just-me1.odoo.com/web/dataset/call_kw"
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
                                    print(f"✅ API Test Successful! Found {len(users)} users")
                                else:
                                    print("⚠️ API Test: No 'result' in response")
                            else:
                                print(f"❌ API Test Failed: HTTP {test_response.status}")
                    else:
                        print(f"❌ Authentication Failed: {result}")
                else:
                    print(f"❌ HTTP Error: {response.status}")
                    print(f"Response: {await response.text()}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPossible issues:")
        print("1. Wrong database name")
        print("2. Wrong credentials")
        print("3. Network connectivity issues")
        print("4. CORS or firewall blocking")

if __name__ == "__main__":
    asyncio.run(test_direct_api())