#!/usr/bin/env python3
"""
Run Odoo test from project root
"""

import os
import sys
from pathlib import Path

# Ensure we're at project root
project_root = Path(__file__).parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

# Import and run
import asyncio
from ai_employee.core.config import get_config
from ai_employee.integrations.odoo_client import OdooClient

async def main():
    print("="*60)
    print("TESTING LOCAL ODOO CONNECTION")
    print("="*60)

    # Check .env values
    print("\nChecking .env configuration:")
    print(f"  ODOO_URL: {os.getenv('ODOO_URL', 'NOT SET')}")
    print(f"  ODOO_DB: {os.getenv('ODOO_DB', 'NOT SET')}")
    print(f"  ODOO_USERNAME: {os.getenv('ODOO_USERNAME', 'NOT SET')}")

    # Load config
    config = get_config()

    if not hasattr(config, 'odoo') or not config.odoo:
        print("\n[ERROR] No Odoo configuration found!")
        print("Make sure ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD are set in .env")
        return

    print(f"\nLoaded configuration:")
    print(f"  URL: {config.odoo.url}")
    print(f"  Database: {config.odoo.database}")
    print(f"  Username: {config.odoo.username}")

    # Test connection
    client = OdooClient(config)

    try:
        print("\nInitializing connection...")
        await client.initialize()

        print("[OK] Connected successfully!")
        print(f"  User ID: {client.user_id}")
        print(f"  Company ID: {client.company_id}")

        # Test basic operation
        print("\nTesting basic API call...")
        users = await client.execute_kw('res.users', 'search', [[]])
        print(f"[OK] Found {len(users)} users")

        # Check accounting module
        print("\nChecking for accounting modules...")
        try:
            # Check for account module
            account_mods = await client.execute_kw(
                'ir.module.module',
                'search',
                [[['name', 'in', ['account', 'account_accountant']]]]
            )
            if account_mods:
                print(f"[OK] Found {len(account_mods)} accounting-related modules")
            else:
                print("[INFO] No accounting modules found - install from Odoo Apps")
        except Exception as e:
            print(f"[WARNING] Could not check modules: {e}")

        await client.shutdown()
        print("\n[OK] Test completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Odoo is running: http://localhost:8069")
        print(f"2. Create database '{config.odoo.database}' if needed")
        print("3. Check that admin credentials are correct")
        print("4. Ensure database exists and is accessible")

if __name__ == "__main__":
    asyncio.run(main())