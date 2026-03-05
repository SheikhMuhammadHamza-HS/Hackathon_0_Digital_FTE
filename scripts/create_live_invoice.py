
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_employee.integrations.odoo_client import get_odoo_client

async def create_live_invoice():
    load_dotenv()
    
    print("🚀 Starting Gold Tier: Live Odoo Invoice Process")
    client = get_odoo_client()
    
    try:
        await client.initialize()
        
        # 1. Ensure a partner exists
        print("🔍 Checking/Creating Partner...")
        partner_name = "Hackathon AI Client"
        partners = await client._call_kw(
            "res.partner",
            "search_read",
            [[["name", "=", partner_name]], ["id"]]
        )
        
        if partners:
            partner_id = partners[0]["id"]
            print(f"✅ Found existing partner: {partner_name} (ID: {partner_id})")
        else:
            partner_id = await client._call_kw(
                "res.partner",
                "create",
                [{"name": partner_name, "email": "client@example.com"}]
            )
            print(f"✅ Created new partner: {partner_name} (ID: {partner_id})")
            
        # 2. Create a Draft Invoice
        print("📝 Creating Draft Invoice (account.move)...")
        
        # We need an account_id for the invoice line. 
        # Usually, Odoo has a default 'Income' account. Let's find one.
        accounts = await client._call_kw(
            "account.account",
            "search_read",
            [[["account_type", "=", "income"]], ["id", "name"], 1]
        )
        
        if not accounts:
            print("⚠️ No income account found, trying generic search...")
            accounts = await client._call_kw(
                "account.account",
                "search_read",
                [[], ["id", "name"], 1]
            )
            
        account_id = accounts[0]["id"] if accounts else 1
        print(f"📊 Using Account ID: {account_id} ({accounts[0]['name'] if accounts else 'Default'})")

        invoice_data = {
            "partner_id": partner_id,
            "move_type": "out_invoice", # Customer Invoice
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "invoice_line_ids": [
                (0, 0, {
                    "name": "AI Automation Service - Gold Tier Package",
                    "quantity": 1,
                    "price_unit": 2500.00,
                    "account_id": account_id
                })
            ]
        }
        
        invoice_result = await client.create_invoice(invoice_data)
        invoice_id = invoice_result["id"]
        
        print(f"🎉 SUCCESS! Draft Invoice created in Odoo.")
        print(f"🆔 Odoo Invoice ID: {invoice_id}")
        
        # 3. Read back details to verify
        details = await client._call_kw(
            "account.move",
            "read",
            [[invoice_id], ["name", "amount_total", "state"]]
        )
        
        if details:
            inv = details[0]
            print(f"📄 Invoice Reference: {inv.get('name')}")
            print(f"💰 Total Amount: ${inv.get('amount_total'):,.2f}")
            print(f"🚦 Status: {inv.get('state').upper()}")
            
        await client.shutdown()
        
    except Exception as e:
        print(f"❌ Failed to create live invoice: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_live_invoice())
