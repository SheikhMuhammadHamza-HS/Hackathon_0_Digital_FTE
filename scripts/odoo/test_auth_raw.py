#!/usr/bin/env python3
"""
Test Raw Odoo Authentication Response
"""

import asyncio
import aiohttp
import json

async def test_raw_auth():
    print("="*60)
    print("RAW ODOO AUTHENTICATION TEST")
    print("="*60)

    url = "http://localhost:8069/web/session/authenticate"
    headers = {"Content-Type": "application/json"}

    # Try different data formats
    data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": "hackathon_zero",
            "login": "admin@hackathon.com",
            "password": "admin123"
        }
    }

    async with aiohttp.ClientSession() as session:
        print(f"\nSending request to: {url}")
        print(f"Data: {json.dumps(data, indent=2)}")

        try:
            async with session.post(url, json=data, headers=headers) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    result = await response.json()
                    print(f"Response: {json.dumps(result, indent=2)}")

                    if result.get("result"):
                        print(f"\nSession ID: {result['result'].get('session_id')}")
                        print(f"User ID: {result['result'].get('uid')}")
                        print(f"Company ID: {result['result'].get('company_id')}")
                    else:
                        print("No 'result' in response")
                else:
                    print(f"Error: {response.status}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_raw_auth())