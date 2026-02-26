#!/usr/bin/env python3
"""
Update Odoo Credentials - Please provide your actual credentials
"""

from pathlib import Path

def update_odoo_creds():
    print("="*60)
    print("UPDATE ODOO CREDENTIALS")
    print("="*60)

    print("\nCurrent configuration:")
    print("  URL: https://just-me1.odoo.com")
    print("  Database: just-me1")

    print("\nPlease update these in .env file:")
    print("  Line 21: ODOO_USERNAME=your.email@gmail.com")
    print("  Line 22: ODOO_PASSWORD=yourpassword")

    print("\nInstructions:")
    print("1. Open .env file")
    print("2. Update line 21 with your actual email")
    print("3. Update line 22 with your actual password")
    print("4. Save the file")

    # Show current .env Odoo section
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, "r") as f:
            lines = f.readlines()

        print("\nCurrent Odoo configuration in .env:")
        for i, line in enumerate(lines[18:25], 19):
            if line.strip():
                print(f"  Line {i}: {line.strip()}")

if __name__ == "__main__":
    update_odoo_creds()