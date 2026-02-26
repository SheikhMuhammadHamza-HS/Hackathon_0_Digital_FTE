import xmlrpc.client
import time

url = 'http://localhost:8069'
db = 'odoo_hackathon'
username = 'admin'
password = 'admin'

def install_invoicing():
    print(f"Connecting to Odoo at {url}...")
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        if not uid:
            print("Authentication failed!")
            return
        
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # Search for 'account' module (Invoicing)
        print("Searching for Invoicing module (account)...")
        module_ids = models.execute_kw(db, uid, password, 'ir.module.module', 'search', [[['name', '=', 'account']]])
        
        if not module_ids:
            print("Module 'account' not found!")
            return
            
        # Install the module
        print("Activating Invoicing module... Please wait, this might take a minute.")
        models.execute_kw(db, uid, password, 'ir.module.module', 'button_immediate_install', [module_ids])
        
        print("Success! Invoicing module is being installed. Odoo will restart internally.")
        print("Wait for 30 seconds, then refresh your browser.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    install_invoicing()
