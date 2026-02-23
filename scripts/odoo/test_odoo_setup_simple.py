#!/usr/bin/env python3
"""
Odoo Test Setup - Configure and test Odoo connection (Windows compatible)
"""

import os
import sys
from pathlib import Path

def check_odoo_requirements():
    """Check if Odoo requirements are met"""
    print("="*60)
    print("ODOO TEST SETUP")
    print("="*60)

    # Check environment variables
    required_vars = {
        "ODOO_URL": "URL to Odoo instance (e.g., http://localhost:8069)",
        "ODOO_DB": "Database name",
        "ODOO_USERNAME": "Username",
        "ODOO_PASSWORD": "Password"
    }

    print("\nChecking environment variables...")
    missing = []
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask password in output
            if "PASSWORD" in var:
                display_value = "*" * len(value)
            else:
                display_value = value
            print(f"  [OK] {var}: {display_value}")
        else:
            print(f"  [FAIL] {var}: Missing - {desc}")
            missing.append(var)

    if missing:
        print(f"\n[INFO] Missing {len(missing)} required variables:")
        for var in missing:
            print(f"     - {var}")
        return False

    return True

def create_test_env():
    """Create a test .env file template"""
    print("\nCreating .env template...")

    env_content = """# AI Employee Configuration
SECRET_KEY=Test-Secret-Key-12-Chars!
JWT_SECRET_KEY=Test-JWT-Secret-12-Chars!

# Odoo Configuration
ODOO_URL=http://localhost:8069
ODOO_DB=test_db
ODOO_USERNAME=admin
ODOO_PASSWORD=admin

# Test Mode
DRY_RUN=true
ENVIRONMENT=test

# Paths
INBOX_PATH=./Inbox
NEEDS_ACTION_PATH=./Needs_Action
DONE_PATH=./Done
LOGS_PATH=./Logs
"""

    env_file = Path(".env.test")
    if not env_file.exists():
        with open(env_file, "w") as f:
            f.write(env_content)
        print(f"  [OK] Created {env_file}")
        print(f"  [INFO] Please edit {env_file} with your Odoo credentials")
    else:
        print(f"  [INFO] {env_file} already exists")

    return env_file

def test_odoo_connection():
    """Test Odoo connection using the client"""
    print("\nTesting Odoo connection...")

    # Add project root to path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    try:
        from ai_employee.integrations.odoo_client import get_odoo_client
        import asyncio

        async def run_test():
            client = get_odoo_client()

            # Test initialization
            await client.initialize()
            print("  [OK] Odoo client initialized")

            # Test server info
            server_info = await client.get_server_info()
            if server_info:
                print(f"  [OK] Connected to Odoo {server_info.get('version', 'unknown')}")
                print(f"       Database: {server_info.get('database')}")
                print(f"       URL: {server_info.get('server_url')}")
            else:
                print("  [WARN] Connected but couldn't retrieve server info")

            # Test connection
            if await client.test_connection():
                print("  [OK] Odoo connection test passed")
            else:
                print("  [FAIL] Odoo connection test failed")

            await client.shutdown()
            return True

        return asyncio.run(run_test())

    except Exception as e:
        print(f"  [FAIL] Odoo connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure Odoo is running on the specified URL")
        print("  2. Check database name is correct")
        print("  3. Verify username and password")
        print("  4. Check network connectivity")
        return False

def create_test_directories():
    """Create test directories"""
    print("\nCreating test directories...")

    directories = [
        "Inbox",
        "Needs_Action",
        "Done",
        "Logs",
        "Pending_Approval",
        "Approved",
        "Vault/Clients",
        "Vault/Accounting"
    ]

    for dir_path in directories:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {dir_path}")

def create_test_client():
    """Create a test client file"""
    print("\nCreating test client...")

    client_file = Path("Vault/Clients/Test Client.md")
    if not client_file.exists():
        client_content = """---
name: Test Client
odoo_partner_id: 1
payment_terms: 30
tax_id: 12-3456789
default_journal: Sales
---

# Test Client

**Address:** 123 Test Street, Test City, TC 12345
**Contact:** Test Person
**Email:** test@testclient.com
**Phone:** 555-0123

## Billing Information
- **Payment Terms:** Net 30
- **Tax Rate:** 10%
- **Currency:** USD
"""
        with open(client_file, "w") as f:
            f.write(client_content)
        print(f"  [OK] Created {client_file}")
    else:
        print(f"  [INFO] Test client already exists")

def main():
    """Main setup function"""
    print(f"Current working directory: {Path.cwd()}")

    # Check if we have credentials
    if not check_odoo_requirements():
        print("\n" + "="*60)
        print("SETUP REQUIRED")
        print("="*60)
        print("\nOption 1: Use local Odoo instance")
        print("  1. Install Odoo Community Edition")
        print("  2. Start Odoo on http://localhost:8069")
        print("  3. Create a database (e.g., 'test_db')")
        print("  4. Create admin user")

        print("\nOption 2: Use cloud/staging Odoo")
        print("  1. Get URL, database, username, password")
        print("  2. Set environment variables:")
        print("     - ODOO_URL=https://your-odoo-instance.com")
        print("     - ODOO_DB=your_database")
        print("     - ODOO_USERNAME=your_username")
        print("     - ODOO_PASSWORD=your_password")

        # Create template
        create_test_env()

        print("\nAfter configuring credentials:")
        print("  1. Set DRY_RUN=true in .env")
        print("  2. Run: python test_odoo_setup_simple.py")
        return False

    # Create test structure
    create_test_directories()
    create_test_client()

    # Test connection
    print("\n" + "="*60)
    print("TESTING ODOO CONNECTION")
    print("="*60)

    success = test_odoo_connection()

    if success:
        print("\n[SUCCESS] Odoo setup complete!")
        print("\nNext steps:")
        print("  1. Test invoice creation with DRY_RUN=true")
        print("  2. Review approval workflow")
        print("  3. Set DRY_RUN=false for real operations")
    else:
        print("\n[FAIL] Odoo setup failed. Please check configuration.")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)