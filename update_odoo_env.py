#!/usr/bin/env python3
"""
Update Odoo Configuration in .env
"""

import os
from pathlib import Path

def update_odoo_config():
    print("="*60)
    print("UPDATE ODOO CONFIGURATION")
    print("="*60)

    # Find .env file
    env_file = Path("scripts/config/.env")
    if not env_file.exists():
        print(f"[ERROR] {env_file} not found!")
        return

    # Read current .env
    with open(env_file, "r") as f:
        lines = f.readlines()

    # Update Odoo configuration
    updated_lines = []
    for line in lines:
        if line.startswith("ODOO_URL="):
            updated_lines.append("ODOO_URL=http://localhost:8069\n")
        elif line.startswith("ODOO_DB="):
            updated_lines.append("ODOO_DB=test_db\n")  # Change this to your DB name
        elif line.startswith("ODOO_USERNAME="):
            updated_lines.append("ODOO_USERNAME=admin\n")
        elif line.startswith("ODOO_PASSWORD="):
            updated_lines.append("ODOO_PASSWORD=admin\n")  # Change to your password
        else:
            updated_lines.append(line)

    # Write back
    with open(env_file, "w") as f:
        f.writelines(updated_lines)

    print("[OK] Updated Odoo configuration in scripts/config/.env")
    print("\nCurrent configuration:")
    print("  ODOO_URL=http://localhost:8069")
    print("  ODOO_DB=test_db")
    print("  ODOO_USERNAME=admin")
    print("  ODOO_PASSWORD=admin")
    print("\n⚠️  Please update these values if different:")
    print("  - Change ODOO_DB to your actual database name")
    print("  - Change ODOO_PASSWORD to your actual password")

if __name__ == "__main__":
    update_odoo_config()