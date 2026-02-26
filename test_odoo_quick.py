#!/usr/bin/env python3
"""Quick Odoo Connection Test - Fixed Version"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_odoo():
    print("="*60)
    print("ODOO CONNECTION TEST - FIXED VERSION")
    print("="*60)

    # Check environment
    print("\n[INFO] Current Directory:", os.getcwd())
    print("[INFO] Python Path:", sys.path[0])

    # Try to import
    try:
        print("\n[INFO] Importing ai_employee.integrations.odoo_client...")
        from ai_employee.integrations.odoo_client import get_odoo_client
        print("[OK] Import successful!")
    except ImportError as e:
        print(f"\n[ERROR] Import failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you're in the hackathon_zero directory")
        print("2. Check that ai_employee folder exists")
        print("3. Verify __init__.py files exist")
        return False

    # Set credentials from .env.local if exists
    env_file = project_root / ".env.local"
    if env_file.exists():
        print(f"\n[INFO] Loading credentials from {env_file}...")
        with open(env_file) as f:
            for line in f:
                if line.strip() and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        print("[OK] Credentials loaded!")

    # Show credentials (without password)
    print("\n[INFO] Connection Details:")
    print(f"  URL: {os.getenv('ODOO_URL')}")
    print(f"  Database: {os.getenv('ODOO_DB')}")
    print(f"  Username: {os.getenv('ODOO_USERNAME')}")
    print(f"  Password: {'*' * len(os.getenv('ODOO_PASSWORD', ''))}")

    # Check DRY_RUN
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    if dry_run:
        print("\n[INFO] Running in DRY RUN mode")
    else:
        print("\n[WARNING] RUNNING IN REAL MODE")

    # Test connection
    try:
        print("\n[INFO] Initializing Odoo client...")
        client = get_odoo_client()

        print("[INFO] Connecting to Odoo...")
        await client.initialize()
        print("[OK] Odoo client initialized!")

        # Test basic connection
        if await client.test_connection():
            print("[OK] Connection test passed!")

            # Get server info
            try:
                server_info = await client.get_server_info()
                if server_info:
                    print("\n[OK] Server Info:")
                    print(f"  Version: {server_info.get('version', 'Unknown')}")
                    print(f"  Database: {server_info.get('database', 'Unknown')}")
            except:
                print("[WARN] Could not get server info (but connection works)")

            # Try to get company info
            try:
                companies = await client._call_kw(
                    "res.company",
                    "search_read",
                    [[], ["name"], 1]
                )
                if companies:
                    print(f"\n[OK] Found company: {companies[0].get('name', 'Unknown')}")
            except:
                print("[WARN] Could not fetch company data (may need permissions)")

            print("\n🎉 SUCCESS! Odoo is ready for AI Employee!")
            return True

        else:
            print("[ERROR] Connection test failed")
            return False

    except Exception as e:
        print(f"\n[ERROR] Connection failed: {e}")
        print("\nPossible causes:")
        print("1. Odoo is not running (check: docker ps)")
        print("2. Wrong database name")
        print("3. Wrong username/password")
        print("4. Network/firewall issues")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_odoo())
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed - check the errors above")

    input("\nPress Enter to exit...")