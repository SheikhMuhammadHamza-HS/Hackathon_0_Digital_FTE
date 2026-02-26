#!/usr/bin/env python3
"""
Simple test to verify Odoo connection using updated .env settings
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ai_employee.core.config import get_config
from ai_employee.integrations.odoo_client import OdooClient
import asyncio

async def test_odoo():
    print("="*60)
    print("TESTING ODOO CONNECTION WITH UPDATED CONFIG")
    print("="*60)

    # Load configuration
    config = get_config()

    if not hasattr(config, 'odoo'):
        print("[ERROR] No Odoo configuration found!")
        print("Please check .env file for ODOO_* variables")
        return

    print(f"\nOdoo Configuration:")
    print(f"  URL: {config.odoo.url}")
    print(f"  Database: {config.odoo.database}")
    print(f"  Username: {config.odoo.username}")
    print(f"  Timeout: {config.odoo.timeout}s")

    # Test connection
    client = OdooClient(config)

    try:
        print("\nAttempting to connect...")
        await client.authenticate()

        print("[OK] Successfully connected to Odoo!")
        print(f"  User ID: {client.user_id}")
        print(f"  Session ID: {client.session_id[:20]}..." if client.session_id else "  No session ID")

        # Test basic API call
        print("\nTesting API call to list users...")
        users = await client.execute_kw('res.users', 'search', [[]])
        print(f"[OK] Found {len(users)} users in the system")

        # Check if accounting module is installed
        print("\nChecking accounting module...")
        try:
            accounting_modules = await client.execute_kw(
                'ir.module.module',
                'search',
                [[['name', '=', 'account_accountant']]]
            )
            if accounting_modules:
                print("[OK] Accounting/Accounting module is installed")
            else:
                # Check basic accounting
                basic_accounting = await client.execute_kw(
                    'ir.module.module',
                    'search',
                    [[['name', '=', 'account']]]
                )
                if basic_accounting:
                    print("[OK] Basic Accounting module is installed")
                else:
                    print("[INFO] No accounting module found - you may need to install it from Apps")
        except Exception as e:
            print(f"[WARNING] Could not check accounting module: {e}")

    except Exception as e:
        print(f"\n[ERROR] Failed to connect: {e}")

        print("\nTroubleshooting:")
        print("1. Ensure Odoo is running at http://localhost:8069")
        print("2. Create database 'hackathon_zero' if it doesn't exist")
        print("3. Check that admin/admin credentials are correct")
        print("4. Verify database exists in Odoo")

if __name__ == "__main__":
    asyncio.run(test_odoo())