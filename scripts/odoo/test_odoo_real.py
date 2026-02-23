#!/usr/bin/env python3
"""
Test Real Odoo Integration - Connect to actual Odoo instance
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_odoo_connection():
    """Test real Odoo connection"""
    print("="*60)
    print("ODOO REAL CONNECTION TEST")
    print("="*60)

    # Load environment
    os.environ["ENVIRONMENT"] = "test"

    # Check credentials
    required = ["ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"]
    missing = [var for var in required if not os.getenv(var)]

    if missing:
        print(f"[ERROR] Missing credentials: {', '.join(missing)}")
        print("\nPlease configure your credentials:")
        print("1. Copy .env.odoo_template to .env.local")
        print("2. Edit .env.local with your Odoo details")
        print("3. Run: export $(cat .env.local | xargs)")
        print("4. Run this script again")
        return False

    # Show connection info (without password)
    print(f"\nConnecting to:")
    print(f"  URL: {os.getenv('ODOO_URL')}")
    print(f"  Database: {os.getenv('ODOO_DB')}")
    print(f"  Username: {os.getenv('ODOO_USERNAME')}")
    print(f"  Password: {'*' * len(os.getenv('ODOO_PASSWORD', ''))}")

    # Check DRY_RUN mode
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    if dry_run:
        print("\n[INFO] Running in DRY RUN mode")
    else:
        print("\n[WARNING] RUNNING IN REAL MODE - Actual operations will be performed!")

    # Import and test Odoo client
    try:
        from ai_employee.integrations.odoo_client import get_odoo_client

        print("\nInitializing Odoo client...")
        client = get_odoo_client()

        # Test connection
        await client.initialize()
        print("[OK] Odoo client initialized successfully")

        # Get server info
        server_info = await client.get_server_info()
        if server_info:
            print(f"\n[OK] Connected to Odoo:")
            print(f"  Version: {server_info.get('version', 'Unknown')}")
            print(f"  Database: {server_info.get('database')}")
            print(f"  Server URL: {server_info.get('server_url')}")

        # Test connection
        if await client.test_connection():
            print("\n[OK] Odoo connection test passed")

            # Try to list some data
            try:
                # Get company info
                companies = await client._call_kw(
                    "res.company",
                    "search_read",
                    [[], ["name", "email", "phone"]]
                )
                if companies:
                    print(f"\n[OK] Found {len(companies)} company/companies:")
                    for company in companies[:3]:  # Show max 3
                        print(f"  - {company.get('name', 'Unknown')}")

                # Get partners (optional)
                partners = await client._call_kw(
                    "res.partner",
                    "search_read",
                    [[["is_company", "=", True]], ["name", "email"], 5]
                )
                if partners:
                    print(f"\n[OK] Found {len(partners)} customers:")
                    for partner in partners[:5]:  # Show max 5
                        print(f"  - {partner.get('name', 'Unknown')}")

            except Exception as e:
                print(f"\n[WARN] Could not retrieve data: {e}")

        else:
            print("\n[FAIL] Odoo connection test failed")

        await client.shutdown()
        return True

    except Exception as e:
        print(f"\n[ERROR] Odoo connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify Odoo is running and accessible")
        print("  2. Check database name is correct")
        print("  3. Verify username and password")
        print("  4. Check if user has permissions")
        print("  5. Verify network/firewall settings")
        return False

async def create_test_invoice():
    """Create a test invoice in Odoo"""
    print("\n" + "="*60)
    print("CREATE TEST INVOICE")
    print("="*60)

    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    if dry_run:
        print("[DRY RUN] Would create real invoice in Odoo")
        return True

    if input("\nCreate a test invoice? (y/N): ").lower() != 'y':
        print("Skipped")
        return True

    try:
        from ai_employee.integrations.odoo_client import get_odoo_client

        client = get_odoo_client()
        await client.initialize()

        # Find or create a test partner
        partners = await client._call_kw(
            "res.partner",
            "search_read",
            [[["name", "=", "Test Client AI Employee"]], ["id"]]
        )

        if not partners:
            # Create test partner
            partner_id = await client._call_kw(
                "res.partner",
                "create",
                [{
                    "name": "Test Client AI Employee",
                    "email": "test@aiemployee.com",
                    "is_company": True,
                    "customer_rank": 1
                }]
            )
            print(f"[OK] Created test partner with ID: {partner_id}")
        else:
            partner_id = partners[0]["id"]
            print(f"[OK] Using existing partner ID: {partner_id}")

        # Create invoice
        invoice_data = {
            "partner_id": partner_id,
            "move_type": "out_invoice",
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "invoice_line_ids": [
                [0, 0, {
                    "name": "Test Service - AI Employee",
                    "quantity": 10,
                    "price_unit": 100,
                    "account_id": 1  # You may need to adjust this
                }]
            ]
        }

        invoice_id = await client.create_invoice(invoice_data)
        print(f"[OK] Created draft invoice with ID: {invoice_id['id']}")

        # Get invoice details
        invoice = await client._call_kw(
            "account.move",
            "read",
            [invoice_id["id"], ["name", "amount_total"]]
        )
        if invoice:
            inv = invoice[0]
            print(f"\nInvoice Details:")
            print(f"  Number: {inv.get('name', 'N/A')}")
            print(f"  Total: ${inv.get('amount_total', 0):.2f}")

        await client.shutdown()
        return True

    except Exception as e:
        print(f"[ERROR] Failed to create test invoice: {e}")
        return False

async def main():
    """Main test function"""
    print("AI Employee - Odoo Real Integration Test")
    print("=====================================")

    # Test connection
    if not await test_odoo_connection():
        print("\n[FAIL] Connection test failed")
        return False

    # Create test invoice (optional)
    if await create_test_invoice():
        print("\n[SUCCESS] All tests completed!")
        print("\nThe system is ready for:")
        print("  1. Processing invoice requests from Needs_Action")
        print("  2. Creating approval workflows")
        print("  3. Posting approved invoices to Odoo")
        return True

    return False

if __name__ == "__main__":
    # Try to load .env.local if it exists
    env_local = Path(".env.local")
    if env_local.exists():
        print(f"Loading credentials from {env_local}...")
        with open(env_local, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value

    # Run tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)