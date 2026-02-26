#!/usr/bin/env python3
"""
Fix Odoo Authentication Issue
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def troubleshoot_auth():
    print("="*60)
    print("ODOO AUTHENTICATION TROUBLESHOOTER")
    print("="*60)

    # Load current env
    env_file = project_root / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            lines = f.readlines()

        print("\nCurrent Odoo configuration:")
        for i, line in enumerate(lines[18:25], 19):
            if line.startswith("ODOO_"):
                print(f"  {line.strip()}")

    print("\nCommon issues and fixes:")
    print("1. Wrong database name")
    print("   - Your database is 'just-me1' (from URL)")
    print("   - Make sure ODOO_DB=just-me1")

    print("\n2. Wrong URL")
    print("   - Use full URL: https://just-me1.odoo.com")
    print("   - Not http://localhost:8069")

    print("\n3. Wrong email/password")
    print("   - Use your actual Odoo.com credentials")
    print("   - Not your local database credentials")

    print("\n4. Session issues")
    print("   - Try logging out and logging back in Odoo.com")
    print("   - Clear browser cache")

    print("\n5. Database not fully setup")
    print("   - Go to: https://just-me1.odoo.com/web/database/manager")
    print("   - Check if database is active")

    print("\nQuick fix steps:")
    print("1. Verify your database is accessible at: https://just-me1.odoo.com")
    print("2. Try logging out and back in")
    print("3. Check .env file has correct credentials")
    print("4. Run: python scripts/run.py odoo test")

if __name__ == "__main__":
    troubleshoot_auth()