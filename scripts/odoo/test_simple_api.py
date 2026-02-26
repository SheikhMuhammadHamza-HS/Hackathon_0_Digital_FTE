#!/usr/bin/env python3
"""
Simple Odoo.com API Test
"""

import asyncio
import aiohttp
import json

async def test_simple_api():
    print("="*60)
    print("SIMPLE ODOO API TEST")
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

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                print(f"Status: {response.status}")

                if response.status == 200:
                    result = await response.json()

                    if "result" in result:
                        session_info = result["result"]
                        print(f"SUCCESS!")
                        print(f"User ID: {session_info.get('uid')}")
                        print(f"Company ID: {session_info.get('company_id')}")
                        return True
                    else:
                        print(f"FAILED: {result}")
                else:
                    print(f"FAILED: HTTP {response.status}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_api())