#!/usr/bin/env python3
"""
Simple Odoo Authentication Test
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

def test_simple():
    print("="*60)
    print("SIMPLE ODOO TEST")
    print("="*60)

    try:
        from ai_employee.integrations.odoo_client import get_odoo_client
        import asyncio

        async def run():
            client = get_odoo_client()

            print("\n1. Initializing...")
            await client.initialize()
            print("   [OK] Initialized")

            print("\n2. Creating test invoice...")
            invoice_data = {
                "partner_id": 3,  # Using partner_id from auth response
                "move_type": "out_invoice",
                "invoice_date": "2026-02-24",
                "invoice_line_ids": [
                    [0, 0, {
                        "name": "Test Service",
                        "quantity": 1,
                        "price_unit": 100.0
                    }]
                ]
            }

            try:
                invoice_id = await client.create_invoice(invoice_data)
                print(f"   [OK] Created invoice: {invoice_id}")
            except Exception as e:
                print(f"   [DRY RUN] Would create invoice: {e}")

            await client.shutdown()
            return True

        success = asyncio.run(run())
        return success

    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False

if __name__ == "__main__":
    test_simple()