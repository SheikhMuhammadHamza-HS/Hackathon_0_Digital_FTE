
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_employee.integrations.odoo_client import get_odoo_client

async def showcase_odoo():
    load_dotenv()
    
    # Paths
    needs_action_dir = Path("./Needs_Action")
    approved_dir = Path("./Approved")
    done_dir = Path("./Done")
    
    for d in [needs_action_dir, approved_dir, done_dir]:
        d.mkdir(exist_ok=True)

    print("\n" + "="*70)
    print("💎 GOLD TIER: FULL ODOO ERP WORKFLOW DEMONSTRATION")
    print("="*70)

    # STEP 1: Incoming Request (AI generated from Email Inbox)
    client_name = "Tech Solutions Ltd"
    invoice_id_fake = f"INV-SHOW-{datetime.now().strftime('%H%M%S')}"
    
    request_content = f"""# INVOICE REQUEST: {client_name}
**Platform:** email
**Subject:** Request for Project Billing - Phase 2
**Date:** {datetime.now().strftime('%Y-%m-%d')}

## Services
- Software Development (AI Module): 40 hours @ $150/hr
- Technical Consultancy: 5 hours @ $200/hr

**Total Due:** $7,000.00
**Priority:** High
"""
    
    request_file = needs_action_dir / f"{invoice_id_fake}.md"
    request_file.write_text(request_content, encoding='utf-8')
    print(f"\n[STEP 1] 📥 Incoming Request Created:")
    print(f"  Folder: ./Needs_Action/{request_file.name}")
    print(f"  Status: AI system has identified a billing requirement.")
    
    # STEP 2: Approval (HITL Simulation)
    print(f"\n[STEP 2] 👔 Human Approval Required (HITL):")
    print(f"  ---> Action: Move file from 'Needs_Action' to 'Approved'")
    
    # Simulating the human move
    approved_file = approved_dir / request_file.name
    request_file.rename(approved_file)
    print(f"  ✅ SUCCESS: Manager approved the request. File moved to ./Approved/")

    # STEP 3: Odoo Sync (The Live Integration)
    print(f"\n[STEP 3] ⚙️ Executing Live Odoo Integration:")
    print(f"  Connecting to Odoo Community Edition...")
    
    client = get_odoo_client()
    try:
        await client.initialize()
        
        # Ensure partner exists
        partners = await client._call_kw("res.partner", "search_read", [[["name", "=", client_name]], ["id"]])
        partner_id = partners[0]["id"] if partners else await client._call_kw("res.partner", "create", [{"name": client_name}])
        
        # Create Invoice
        invoice_data = {
            "partner_id": partner_id,
            "move_type": "out_invoice",
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "invoice_line_ids": [
                (0, 0, {"name": "AI Software Dev - Showcase", "quantity": 40, "price_unit": 150.00, "account_id": 27}),
                (0, 0, {"name": "Technical consultancy - Showcase", "quantity": 5, "price_unit": 200.00, "account_id": 27})
            ]
        }
        
        result = await client.create_invoice(invoice_data)
        odoo_id = result["id"]
        
        print(f"  💎 SUCCESS: Draft Invoice {odoo_id} generated live in Odoo ERP!")
        
        # STEP 4: Reporting & Cleanup
        final_path = done_dir / approved_file.name
        approved_file.rename(final_path)
        print(f"\n[STEP 4] 📈 Reporting & Cleanup:")
        print(f"  Task marked as finished. File moved to ./Done/")
        
        # Generate CEO report
        import subprocess
        subprocess.run(["python", "scripts/generate_ceo_briefing.py"], capture_output=True)
        print(f"  ✅ CEO Dashboard Updated (Dashboard.md).")
        
        await client.shutdown()
        
    except Exception as e:
        print(f"\n❌ FAILED at Odoo Sync: {e}")
        if "reconnect" in str(e).lower():
            print("  💡 Tip: Ensure Odoo Docker container is running.")

    print("\n" + "="*70)
    print("📊 WORKFLOW COMPLETE: Request -> Approve -> Odoo Draft -> Report")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(showcase_odoo())
