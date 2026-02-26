#!/usr/bin/env python3
"""
Check Odoo database and setup
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_employee.core.config import get_config
import json

def check_odoo_setup():
    print("="*60)
    print("ODOO SETUP CHECK")
    print("="*60)

    # Load configuration
    config = get_config()

    if not hasattr(config, 'odoo'):
        print("[ERROR] No Odoo configuration found in .env")
        return

    print(f"\nConfiguration from .env:")
    print(f"  ODOO_URL: {config.odoo.url}")
    print(f"  ODOO_DB: {config.odoo.database}")
    print(f"  ODOO_USERNAME: {config.odoo.username}")

    # Check if URL is correct
    if "localhost:8069" not in config.odoo.url:
        print(f"\n[WARNING] URL doesn't contain localhost:8069")
        print(f"Current: {config.odoo.url}")
        print(f"Expected: http://localhost:8069")

    # Check database name
    if config.odoo.database != "hackathon_zero":
        print(f"\n[INFO] Database name is '{config.odoo.database}'")
        print("Make sure this database exists in Odoo")

    print("\nNext steps:")
    print("1. Open http://localhost:8069 in your browser")
    print(f"2. Select or create database '{config.odoo.database}'")
    print("3. Login with admin credentials")
    print("4. Install Accounting app from Apps if not already installed")
    print("5. Run the test again")

if __name__ == "__main__":
    check_odoo_setup()