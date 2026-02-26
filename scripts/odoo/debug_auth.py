#!/usr/bin/env python3
"""
Debug Odoo Authentication Issue
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
os.environ["ODOO_USERNAME"] = "admin@hackathon.com"
os.environ["ODOO_PASSWORD"] = "admin123"

def debug_auth():
    print("="*60)
    print("DEBUGGING ODOO AUTHENTICATION")
    print("="*60)
    print("\nTesting with:")
    print(f"  URL: {os.environ['ODOO_URL']}")
    print(f"  DB: {os.environ['ODOO_DB']}")
    print(f"  User: {os.environ['ODOO_USERNAME']}")
    print(f"  Password: {'*' * len(os.environ['ODOO_PASSWORD'])}")

    try:
        from ai_employee.integrations.odoo_client import get_odoo_client
        import asyncio

        async def test():
            print("\n1. Getting Odoo client...")
            client = get_odoo_client()

            print("2. Initializing...")
            await client.initialize()
            print("   [OK] Initialized successfully")

            print("3. Getting session info...")
            print(f"   Session ID: {client.session_id}")
            print(f"   User ID: {client.user_id}")
            print(f"   Company ID: {client.company_id}")

            print("\n4. Testing connection...")
            if await client.test_connection():
                print("   [OK] Connection test passed!")
            else:
                print("   [FAIL] Connection test failed")

            print("\n5. Getting server info...")
            info = await client.get_server_info()
            if info:
                print(f"   Version: {info.get('version')}")
                print(f"   Database: {info.get('database')}")

            await client.shutdown()
            return True

        success = asyncio.run(test())
        if success:
            print("\n[SUCCESS] Authentication working!")
            print("\nNow you can test invoice creation!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nPossible issues:")
        print("1. Database name mismatch (case sensitive)")
        print("2. User credentials wrong")
        print("3. Database not fully initialized")

if __name__ == "__main__":
    debug_auth()
    input("\nPress Enter to exit...")