#!/usr/bin/env python3
"""
Direct Odoo Connection Test - Bypass login page
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set environment
os.environ["SECRET_KEY"] = "Test-Secret-Key-12-Chars!"
os.environ["JWT_SECRET_KEY"] = "Test-JWT-Secret-12-Chars!"
os.environ["ODOO_URL"] = "http://localhost:8069"
os.environ["ODOO_DB"] = "hackathon_zero"

def test_connection():
    print("="*60)
    print("DIRECT ODOO CONNECTION TEST")
    print("="*60)
    print("\nTrying to connect to Odoo database: hackathon_zero")
    print("This bypasses the login page!\n")

    try:
        from ai_employee.integrations.odoo_client import get_odoo_client
        import asyncio

        async def connect():
            print("1. Getting Odoo client...")
            client = get_odoo_client()

            print("2. Initializing connection...")
            await client.initialize()
            print("   ✅ Connected successfully!")

            print("3. Getting server info...")
            info = await client.get_server_info()
            if info:
                print(f"   Database: {info.get('database')}")
                print(f"   Server URL: {info.get('server_url')}")

            print("4. Testing data access...")
            try:
                companies = await client._call_kw(
                    "res.company",
                    "search_read",
                    [[], ["name"], 5]
                )
                print(f"   Found {len(companies)} companies")
                if companies:
                    print(f"   First company: {companies[0].get('name')}")
            except:
                print("   Could not fetch companies (might need permissions)")

            print("\n✅ SUCCESS! Odoo is working!")
            print("\nNow create a test user in Odoo:")
            print("1. Go to Settings → Users & Companies → Users")
            print("2. Create a new API user")
            print("3. Give them Accounting permissions")

            await client.shutdown()
            return True

        asyncio.run(connect())

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPossible reasons:")
        print("1. Wrong database name (is it really 'hackathon_zero'?)")
        print("2. Odoo not running properly")
        print("3. Database not fully initialized")
        return False

if __name__ == "__main__":
    print("This test doesn't need login credentials!")
    print("It uses direct API access to test Odoo.\n")
    success = test_connection()
    input("\nPress Enter to exit...")