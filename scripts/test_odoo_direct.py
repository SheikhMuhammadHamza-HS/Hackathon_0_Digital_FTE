
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_employee.integrations.odoo_client import OdooClient

async def test_odoo_direct():
    load_dotenv()
    
    print("🔄 Testing direct Odoo connection...")
    
    client = OdooClient()
    try:
        await client.initialize()
        is_connected = await client.test_connection()
        
        if is_connected:
            print("✅ Odoo Connection PASSED!")
            
            # Get server info
            info = await client.get_server_info()
            print(f"📊 Server Info: {info}")
            
            # Try to list companies to verify permissions
            companies = await client._call_kw(
                "res.company",
                "search_read",
                [[], ["name", "email", "phone"]]
            )
            print(f"🏢 Companies found: {len(companies)}")
            for company in companies:
                print(f"  - {company.get('name')}")
                
        else:
            print("❌ Odoo Connection FAILED!")
            
        await client.shutdown()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_odoo_direct())
