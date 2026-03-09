
import asyncio
import os
import sys
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_employee.integrations.odoo_client import get_odoo_client

async def process_odoo_queue():
    load_dotenv()
    
    print("\n" + "="*70)
    print("🚀 ODOO QUEUE PROCESSOR — SYNCING TRIGGERS TO ERP")
    print("="*70)
    
    trigger_dir = Path("./Vault/Odoo/Triggers")
    archive_dir = Path("./Vault/Odoo/Archive")
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    triggers = list(trigger_dir.glob("odoo-invoice-*.md"))
    
    if not triggers:
        print("💡 No pending Odoo triggers found in Vault/Needs_Action/.")
        return

    print(f"📦 Found {len(triggers)} pending triggers. Initializing Odoo connection...")
    
    client = get_odoo_client()
    try:
        await client.initialize()
        
        # Get a valid income account ID
        accounts = await client._call_kw(
            "account.account",
            "search_read",
            [[["account_type", "=", "income"]], ["id", "name"], 1]
        )
        if not accounts:
            accounts = await client._call_kw("account.account", "search_read", [[], ["id", "name"], 1])
        
        account_id = accounts[0]["id"] if accounts else 27 # Default to 27 if all else fails
        print(f"📊 Using Income Account: {account_id}")

        for trigger in triggers:
            print(f"\n[SYNCING] {trigger.name}...")
            content = trigger.read_text(encoding='utf-8')
            
            # Extract data from the trigger file using Regex
            client_match = re.search(r"\*\*Client:\*\* (.*)", content)
            total_match = re.search(r"\*\*Total Due:\*\* \$(.*)", content)
            
            client_name = client_match.group(1).strip() if client_match else "Unknown Client"
            total_str = total_match.group(1).strip().replace(",", "") if total_match else "0.00"
            total_amount = float(total_str)
            
            # If "Unknown Client" in details, try to get from the original content section
            if client_name == "Unknown Client":
                orig_client = re.search(r"Client: (.*)", content, re.IGNORECASE)
                if orig_client:
                    client_name = orig_client.group(1).strip()

            print(f"  👤 Client: {client_name}")
            print(f"  💰 Amount: ${total_amount:,.2f}")

            # 1. Ensure Partner Exists
            partners = await client._call_kw("res.partner", "search_read", [[["name", "=", client_name]], ["id"]])
            if partners:
                p_id = partners[0]["id"]
            else:
                p_id = await client._call_kw("res.partner", "create", [{"name": client_name}])
                print(f"  ✨ Created new partner in Odoo (ID: {p_id})")

            # 2. Create Invoice
            invoice_data = {
                "partner_id": p_id,
                "move_type": "out_invoice",
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "invoice_line_ids": [
                    (0, 0, {
                        "name": f"AI Services for {client_name}",
                        "quantity": 1,
                        "price_unit": total_amount,
                        "account_id": account_id
                    })
                ]
            }
            
            result = await client.create_invoice(invoice_data)
            print(f"  ✅ SUCCESS: Odoo Invoice Generated (ID: {result['id']})")
            
            # 3. Archive the trigger
            archive_path = archive_dir / trigger.name
            trigger.rename(archive_path)
            print(f"  📁 Trigger archived to {archive_path}")

        await client.shutdown()
        
    except Exception as e:
        print(f"❌ Error during Odoo Sync: {e}")

    print("\n" + "="*70)
    print("📊 SYNC COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(process_odoo_queue())
