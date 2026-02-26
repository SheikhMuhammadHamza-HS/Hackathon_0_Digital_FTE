#!/usr/bin/env python3
"""
List available Odoo databases
"""

import requests
import json

def list_odoo_databases():
    print("="*60)
    print("LISTING ODOO DATABASES")
    print("="*60)

    odoo_url = "http://localhost:8069"

    try:
        # Try to get database list
        response = requests.get(f"{odoo_url}/web/database/list")

        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("result"):
                    databases = data["result"]
                    print(f"\nFound {len(databases)} databases:")
                    for db in databases:
                        print(f"  - {db}")
                else:
                    print("\nNo databases found or response format unexpected")
                    print(f"Response: {data}")
            except json.JSONDecodeError:
                print("\nResponse is not valid JSON")
                print(f"Response text: {response.text[:500]}")
        else:
            print(f"\nFailed to get database list (HTTP {response.status_code})")
            print("\nThis could mean:")
            print("1. Odoo is not running")
            print("2. Database manager is disabled")
            print("3. Wrong port")

            # Try basic connectivity
            print("\nTrying basic connectivity test...")
            try:
                response = requests.get(odoo_url)
                if response.status_code == 200:
                    print("[OK] Odoo is responding at http://localhost:8069")
                    print("Database list might be disabled for security")
                else:
                    print(f"[ERROR] Odoo not responding (HTTP {response.status_code})")
            except requests.exceptions.ConnectionError:
                print("[ERROR] Cannot connect to http://localhost:8069")
                print("Make sure Odoo is running!")

    except Exception as e:
        print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    list_odoo_databases()