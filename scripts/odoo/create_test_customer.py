#!/usr/bin/env python3
"""
Create Test Customer in Odoo
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
os.environ["ODOO_USERNAME"] = "admin"
os.environ["ODOO_PASSWORD"] = "admin123"

def create_customer():
    print("="*60)
    print("CREATE TEST CUSTOMER IN ODOO")
    print("="*60)

    try:
        from ai_employee.integrations.odoo_client import get_odoo_client
        import asyncio

        async def create():
            client = get_odoo_client()
            await client.initialize()

            print("\nCreating test customer...")

            # Create customer
            customer_data = {
                "name": "Test Client",
                "email": "test@testclient.com",
                "phone": "555-0123",
                "street": "123 Test Street",
                "city": "Test City",
                "state_id": 1,  # You may need to adjust this
                "zip": "12345",
                "country_id": 1,  # You may need to adjust this
                "is_company": True,
                "customer_rank": 1,
                "company_type": "company"
            }

            customer_id = await client._call_kw(
                "res.partner",
                "create",
                [customer_data]
            )

            print(f"\n✅ Customer created successfully!")
            print(f"   Customer ID: {customer_id}")
            print(f"   Name: Test Client")
            print(f"   Email: test@testclient.com")

            # Get the created customer details
            customer = await client.get_partner(customer_id)
            if customer:
                print(f"\n📋 Customer Details:")
                print(f"   Full Name: {customer.get('name')}")
                print(f"   Email: {customer.get('email')}")
                print(f"   Phone: {customer.get('phone')}")
                print(f"   Address: {customer.get('street')}, {customer.get('city')}")
                print(f"   Partner ID: {customer_id}")

            await client.shutdown()
            return customer_id

        customer_id = asyncio.run(create())

        # Save customer info to file
        client_file = project_root / "Vault" / "Clients" / "Test Client.md"
        client_file.parent.mkdir(parents=True, exist_ok=True)

        client_content = f"""---
name: Test Client
odoo_partner_id: {customer_id}
payment_terms: 30
tax_id: 12-3456789
default_journal: Sales
---

# Test Client

**Address:** 123 Test Street, Test City, TC 12345
**Contact:** Test Person
**Email:** test@testclient.com
**Phone:** 555-0123

## Billing Information
- **Payment Terms:** Net 30
- **Tax Rate:** 10%
- **Currency:** USD
"""

        with open(client_file, "w") as f:
            f.write(client_content)

        print(f"\n📁 Client file created: {client_file}")
        print("\n✅ Ready for invoice testing!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Odoo is running")
        print("2. Check URL: http://localhost:8069")
        print("3. Verify database name: hackathon_zero")
        print("4. Check credentials: admin / admin123")

if __name__ == "__main__":
    create_customer()
    input("\nPress Enter to exit...")