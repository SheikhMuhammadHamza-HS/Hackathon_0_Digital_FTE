import xmlrpc.client

url = 'http://localhost:8069'
db = 'odoo_hackathon'
username = 'admin'
password = 'admin'

def setup_test_data():
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        if not uid:
            print("Auth failed")
            return
            
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # 1. Create a Customer
        partner_id = models.execute_kw(db, uid, password, 'res.partner', 'create', [{
            'name': 'Hackathon Client',
            'email': 'client@example.com',
            'is_company': True,
        }])
        print(f"Created Customer 'Hackathon Client' with ID: {partner_id}")
        
        # 2. Update Vault file
        vault_client_path = r"d:\hackathon_zero\Vault\Clients\Hackathon Client.md"
        content = f"""---
name: Hackathon Client
odoo_partner_id: {partner_id}
payment_terms: 30
default_journal: Sales
---

# Hackathon Client
Created for Gold Tier testing.
"""
        with open(vault_client_path, "w") as f:
            f.write(content)
        print(f"Updated Vault client file: {vault_client_path}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    setup_test_data()
