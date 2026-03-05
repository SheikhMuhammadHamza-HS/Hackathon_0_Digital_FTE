
import asyncio
import aiohttp
from urllib.parse import urljoin

async def debug_odoo_auth():
    base_url = "http://localhost:8069"
    auth_url = urljoin(base_url, "/web/session/authenticate")
    auth_data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": "odoo",
            "login": "admin",
            "password": "admin"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(auth_url, json=auth_data) as response:
            result = await response.json()
            print(f"Status: {response.status}")
            print(f"Result Result Keys: {result.get('result', {}).keys()}")
            print(f"Result Result UID: {result.get('result', {}).get('uid')}")
            print(f"Result Result SessionID: {result.get('result', {}).get('session_id')}")
            # Check cookies
            print(f"Cookies: {session.cookie_jar.filter_cookies(base_url)}")

if __name__ == "__main__":
    asyncio.run(debug_odoo_auth())
