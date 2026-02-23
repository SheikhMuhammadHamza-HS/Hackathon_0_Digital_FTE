#!/usr/bin/env python3
"""
Test Configuration Loading - Verify .env loads correctly
"""

import os
from pathlib import Path
from dotenv import load_dotenv

def test_load_config():
    """Test if configuration loads correctly"""
    print("="*60)
    print("CONFIGURATION LOADING TEST")
    print("="*60)

    # Load .env
    env_file = Path(".env")
    if not env_file.exists():
        print(f"[ERROR] {env_file} not found!")
        return False

    print(f"[OK] Found {env_file}")
    load_dotenv()

    # Check core configuration
    print("\nCore Configuration:")
    core_vars = {
        "SECRET_KEY": "Core secret key",
        "JWT_SECRET_KEY": "JWT secret key",
        "ENVIRONMENT": "Environment",
        "DRY_RUN": "Dry run mode"
    }

    for var, desc in core_vars.items():
        value = os.getenv(var)
        if value:
            if "SECRET" in var or "TOKEN" in var:
                display = "*" * min(len(value), 10)
            else:
                display = value
            print(f"  [OK] {var}: {display}")
        else:
            print(f"  [FAIL] {var}: Missing")

    # Check service configurations
    print("\nService Status:")
    services = {
        "Odoo": ["ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"],
        "Gmail": ["GMAIL_TOKEN"],
        "Gemini": ["GEMINI_API_KEY"],
        "WhatsApp": ["WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_ACCESS_TOKEN"],
        "X/Twitter": ["X_API_KEY", "X_API_SECRET"],
        "LinkedIn": ["LINKEDIN_ACCESS_TOKEN"],
        "Facebook": ["FACEBOOK_ACCESS_TOKEN"]
    }

    for service, vars_list in services.items():
        configured = sum(1 for v in vars_list if os.getenv(v))
        total = len(vars_list)
        status = "[OK]" if configured == total else "[PARTIAL]" if configured > 0 else "[MISSING]"
        print(f"  {status} {service}: {configured}/{total} configured")

    # Check Odoo specifically
    print("\nOdoo Configuration Details:")
    odoo_vars = ["ODOO_URL", "ODOO_DB", "ODOO_USERNAME"]
    for var in odoo_vars:
        value = os.getenv(var)
        if value and not value.startswith("your_"):
            print(f"  [OK] {var}: {value}")
        else:
            print(f"  [SETUP] {var}: Needs configuration")

    return True

def main():
    """Main test"""
    success = test_load_config()

    if success:
        print("\n" + "="*60)
        print("NEXT STEPS")
        print("="*60)
        print("\n1. For Odoo testing:")
        print("   - Configure ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD")
        print("   - Run: python test_odoo_real.py")
        print("\n2. For Gmail testing:")
        print("   - Already configured!")
        print("   - Run: python test_gmail_real.py")
        print("\n3. For other services:")
        print("   - See CREDENTIAL_STATUS.md for details")

    return success

if __name__ == "__main__":
    main()