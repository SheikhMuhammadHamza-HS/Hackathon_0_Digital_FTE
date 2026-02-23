#!/usr/bin/env python3
"""
Update Odoo Credentials - Simple update script
"""

import os
from pathlib import Path

def update_odoo_in_env():
    """Update Odoo credentials in .env file"""
    print("="*60)
    print("UPDATE ODOO CREDENTIALS")
    print("="*60)

    env_file = Path(".env")
    if not env_file.exists():
        print("[ERROR] .env file not found!")
        return False

    # Read current .env
    with open(env_file, "r") as f:
        lines = f.readlines()

    # Show current values
    print("\nCurrent Odoo Configuration:")
    for line in lines:
        if line.startswith("ODOO_"):
            key, value = line.strip().split("=", 1)
            if "PASSWORD" in key:
                value = "*" * len(value) if value != "your_password" else value
            print(f"  {key}: {value}")

    print("\nTo update Odoo credentials:")
    print("1. Edit .env file directly")
    print("2. Update these lines:")
    print("   ODOO_URL=http://your-odoo-instance:8069")
    print("   ODOO_DB=your_database_name")
    print("   ODOO_USERNAME=your_username")
    print("   ODOO_PASSWORD=your_password")
    print("\n3. After updating, run: python test_odoo_real.py")

    # Check if still using defaults
    needs_update = any(
        "your_database_name" in line or
        "your_username" in line or
        "your_password" in line
        for line in lines
        if line.startswith("ODOO_")
    )

    if needs_update:
        print("\n[INFO] You still have placeholder values that need updating")
    else:
        print("\n[OK] Odoo credentials appear to be configured")

    return True

def main():
    """Main update function"""
    update_odoo_in_env()

if __name__ == "__main__":
    main()