#!/usr/bin/env python3
"""
Check available Odoo databases
"""

import requests
import json

def check_databases():
    print("="*60)
    print("CHECKING AVAILABLE ODOO DATABASES")
    print("="*60)

    try:
        # Get database list
        response = requests.get("http://localhost:8069/web/database/selector")
        if response.status_code == 200:
            print("\n✅ Odoo is running successfully!")
            print("\nPlease check the database selector page:")
            print("http://localhost:8069/web/database/selector")
            print("\nLook for your database name in the list.")
            print("It might be different from 'hackathon_zero'.")

            # Try to parse HTML for database names
            import re
            matches = re.findall(r'<option[^>]*>([^<]+)</option>', response.text)
            if matches:
                print("\nFound these databases:")
                for match in matches[1:]:  # Skip first "Select Database" option
                    print(f"  - {match}")
        else:
            print("\n❌ Odoo not responding correctly")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease ensure:")
        print("1. Odoo is running on port 8069")
        print("2. Navigate to: http://localhost:8069/web/database/selector")

if __name__ == "__main__":
    check_databases()
    input("\nPress Enter to exit...")