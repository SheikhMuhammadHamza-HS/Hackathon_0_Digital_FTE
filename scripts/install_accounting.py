
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_employee.integrations.odoo_client import get_odoo_client

async def install_accounting():
    load_dotenv()
    
    print("🚀 Triggering Accounting Module Installation...")
    
    client = get_odoo_client()
    try:
        await client.initialize()
        
        # 1. Find the 'account' module ID
        modules = await client._call_kw(
            "ir.module.module",
            "search_read",
            [[["name", "=", "account"]]],
            {"fields": ["id", "state"]}
        )
        
        if not modules:
            print("❌ Module 'account' not found!")
            return
            
        module_id = modules[0]["id"]
        state = modules[0]["state"]
        print(f"📦 Module ID: {module_id}, Current State: {state}")
        
        if state == "installed":
            print("✅ Already installed.")
        else:
            print("⏳ Installing module. This will take a moment (Odoo will restart internal workers)...")
            # button_immediate_install is a special method that triggers the installation
            await client._call_kw("ir.module.module", "button_immediate_install", [module_id])
            print("✅ Installation triggered.")
            
        await client.shutdown()
        
    except Exception as e:
        print(f"❌ Error during installation: {e}")
        # Sometimes this causes a timeout because Odoo resets its worker during installation
        if "Timeout" in str(e) or "Connection" in str(e):
            print("💡 This is expected as Odoo restarts during installation. Wait 1 minute.")

if __name__ == "__main__":
    asyncio.run(install_accounting())
