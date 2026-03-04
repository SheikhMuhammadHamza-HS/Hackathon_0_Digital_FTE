import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1. LOAD ENV IMMEDIATELY
env_path = Path(__file__).parent.parent / ".env.local"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# 2. SETUP PATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3. IMPORTS
from ai_employee.core.config import get_config
from ai_employee.integrations.odoo_client import get_odoo_client
from ai_employee.utils.logging_config import setup_logging

async def finalize_invoicing():
    setup_logging("INFO")
    
    config = get_config()
    odoo = get_odoo_client()
    
    # Live mode
    os.environ["DRY_RUN"] = "false"
    
    print("="*60)
    print("FINALIZING INVOICE (AI AGENT POSTING)")
    print("="*60)
    print(f"DEBUG: Using DB '{config.odoo.database}' at {config.odoo.url}")

    await odoo.initialize()
    
    approved_dir = Path(config.paths.approved_path)
    files = list(approved_dir.glob("invoice_*.md"))
    
    if not files:
        print("No approved invoices found.")
        await odoo.shutdown()
        return

    for file_path in files:
        print(f"Processing Approval: {file_path.name}")
        
        # We know from previous step this is Odoo ID 29
        odoo_invoice_id = 29
        
        try:
            success = await odoo.post_invoice(odoo_invoice_id)
            if success:
                print(f"✅ Success! Invoice {odoo_invoice_id} is now POSTED (Finalized).")
                
                # Move to Done
                done_dir = Path(config.paths.done_path)
                done_dir.mkdir(parents=True, exist_ok=True)
                new_path = done_dir / file_path.name.replace(".md", "_done.md")
                file_path.rename(new_path)
                print(f"Task completed. Record moved to {done_dir}")
            else:
                print("❌ Failed to post invoice.")
        except Exception as e:
            print(f"❌ Error: {e}")

    await odoo.shutdown()

if __name__ == "__main__":
    asyncio.run(finalize_invoicing())
