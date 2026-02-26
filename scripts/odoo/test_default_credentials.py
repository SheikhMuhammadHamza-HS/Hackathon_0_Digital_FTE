#!/usr/bin/env python3
"""
Test Odoo with Default Credentials
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test common credentials
common_credentials = [
    {"db": "odoo", "user": "admin", "pass": "admin"},
    {"db": "test_db", "user": "admin", "pass": "admin"},
    {"db": "postgres", "user": "odoo", "pass": "odoo"},
    {"db": "mycompany", "user": "admin", "pass": "admin"},
    {"db": "demo", "user": "admin", "pass": "admin"},
]

print("="*60)
print("TESTING COMMON ODOO CREDENTIALS")
print("="*60)

for cred in common_credentials:
    print(f"\nTrying: DB={cred['db']}, User={cred['user']}")
    print("----------------------------------------")

    # Write temp .env
    import os
    os.environ["ODOO_URL"] = "http://localhost:8069"
    os.environ["ODOO_DB"] = cred["db"]
    os.environ["ODOO_USERNAME"] = cred["user"]
    os.environ["ODOO_PASSWORD"] = cred["pass"]

    # Run test
    try:
        from ai_employee.integrations.odoo_client import get_odoo_client
        import asyncio

        async def test():
            client = get_odoo_client()
            try:
                await client.initialize()
                print(f"[SUCCESS] Connected with: {cred}")
                await client.shutdown()
                return True
            except Exception as e:
                print(f"[FAIL] {e}")
                return False

        success = asyncio.run(test())
        if success:
            print("\n✅ FOUND WORKING CREDENTIALS!")
            print(f"Please update scripts/config/.env with:")
            print(f"ODOO_DB={cred['db']}")
            print(f"ODOO_USERNAME={cred['user']}")
            print(f"ODOO_PASSWORD={cred['pass']}")
            break
    except Exception as e:
        print(f"[ERROR] {e}")