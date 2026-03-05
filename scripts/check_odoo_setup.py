
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ai_employee.integrations.odoo_client import get_odoo_client

async def check_odoo_setup():
    load_dotenv()
    
    print("🔄 Checking Odoo Modules...")
    
    client = get_odoo_client()
    try:
        await client.initialize()
        
        # Check if account module is installed
        modules = await client._call_kw(
            "ir.module.module",
            "search_read",
            [[["name", "=", "account"]]],
            {"fields": ["name", "state"]}
        )
        
        if modules:
            module = modules[0]
            print(f"📦 Module 'account': {module.get('state')}")
        else:
            print("❌ Module 'account' NOT FOUND in the system.")
            
        # Check for companies
        companies = await client._call_kw(
            "res.company",
            "search_read",
            [[], ["name", "currency_id"]]
        )
        print(f"🏢 Companies: {companies}")
        
        await client.shutdown()
        
    except Exception as e:
        print(f"❌ Error during check: {e}")

if __name__ == "__main__":
    asyncio.run(check_odoo_setup())
