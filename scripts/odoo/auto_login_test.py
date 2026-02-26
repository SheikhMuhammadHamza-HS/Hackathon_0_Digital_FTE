#!/usr/bin/env python3
"""
Auto Test Odoo Login with Common Credentials
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Common credentials to try
credentials = [
    {"username": "admin", "password": "admin"},
    {"username": "admin", "password": "Admin@123"},
    {"username": "admin", "password": "password"},
    {"username": "admin", "password": "123456"},
    {"username": "odoo", "password": "odoo"},
    {"username": "admin", "password": "odoo"},
    {"username": "demo", "password": "demo"},
    {"username": "admin", "password": ""},
]

async def test_credentials():
    print("="*60)
    print("AUTO TESTING ODOO LOGIN")
    print("="*60)
    print("\nTrying common credentials...\n")

    from ai_employee.integrations.odoo_client import get_odoo_client

    for cred in credentials:
        print(f"Trying: Username='{cred['username']}' Password='{cred['password'] or '(empty)'}'")

        # Set environment
        import os
        os.environ["ODOO_URL"] = "http://localhost:8069"
        os.environ["ODOO_DB"] = "test_db"  # Change if different
        os.environ["ODOO_USERNAME"] = cred["username"]
        os.environ["ODOO_PASSWORD"] = cred["password"]

        try:
            client = get_odoo_client()
            await client.initialize()

            # Get server info on success
            info = await client.get_server_info()
            if info:
                print(f"  ✅ SUCCESS! Connected with {cred['username']}")
                print(f"  Database: {info.get('database')}")
                print(f"  Version: {info.get('version')}")
                print("\n=== WORKING CREDENTIALS FOUND ===")
                print(f"Username: {cred['username']}")
                print(f"Password: {cred['password']}")
                print("\nUse these in Odoo login page!")
                await client.shutdown()
                return True

        except Exception as e:
            print(f"  ❌ Failed")
            # Don't show error for wrong password
            if "401" not in str(e) and "authentication" not in str(e).lower():
                print(f"  Error: {e}")

        await asyncio.sleep(0.5)  # Small delay between attempts

    print("\n❌ No working credentials found in common list")
    print("\nTry these in Odoo login:")
    print("1. Username: admin, Password: admin")
    print("2. Username: admin, Password: Admin@123")
    print("3. Check your database name in: http://localhost:8069/web/database/selector")
    return False

if __name__ == "__main__":
    success = asyncio.run(test_credentials())
    input("\nPress Enter to exit...")