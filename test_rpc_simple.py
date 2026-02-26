import xmlrpc.client

url = 'http://localhost:8069'
db = 'odoo_hackathon'
username = 'admin'
password = 'admin'

print(f"Connecting to {url}...")
try:
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    version = common.version()
    print(f"Odoo Version: {version.get('server_version')}")
    
    # Try to list databases
    try:
        dbs = common.list_db()
        print(f"Available databases: {dbs}")
    except Exception as e:
        print(f"Could not list databases: {e}")

    # Try to authenticate
    uid = common.authenticate(db, username, password, {})
    if uid:
        print(f"AUTHENTICATION SUCCESSFUL! User ID: {uid}")
    else:
        print("AUTHENTICATION FAILED: Invalid credentials or database name.")

except Exception as e:
    print(f"ERROR: {e}")
