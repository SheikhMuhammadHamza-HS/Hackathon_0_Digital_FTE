#!/usr/bin/env python3
"""
Configure Real Odoo Credentials - Secure setup for production testing
"""

import os
from pathlib import Path
import getpass

def configure_odoo_credentials():
    """Configure Odoo credentials securely"""
    print("="*60)
    print("ODOO REAL CREDENTIALS CONFIGURATION")
    print("="*60)

    print("\nPlease provide your Odoo instance details:")
    print("(Press Enter to use current value if shown)")

    # Get current values
    current_url = os.getenv("ODOO_URL", "http://localhost:8069")
    current_db = os.getenv("ODOO_DB", "")
    current_user = os.getenv("ODOO_USERNAME", "")

    # Get new values
    print(f"\nOdoo URL [{current_url}]: ", end="")
    url = input().strip()
    if not url:
        url = current_url

    print(f"Database Name [{current_db}]: ", end="")
    db = input().strip()
    if not db:
        if not current_db:
            print("Database name is required!")
            return None
        db = current_db

    print(f"Username [{current_user}]: ", end="")
    username = input().strip()
    if not username:
        if not current_user:
            print("Username is required!")
            return None
        username = current_user

    # Get password securely
    password = getpass.getpass("Password: ")
    if not password:
        print("Password is required!")
        return None

    # Create .env.local file
    env_file = Path(".env.local")
    print(f"\nSaving credentials to {env_file}...")

    # Read existing .env if it exists
    env_content = []
    if Path(".env").exists():
        with open(".env", "r") as f:
            env_content = f.readlines()

    # Update or add Odoo configuration
    odoo_config = [
        f"# Odoo Configuration - Real Credentials\n",
        f"ODOO_URL={url}\n",
        f"ODOO_DB={db}\n",
        f"ODOO_USERNAME={username}\n",
        f"ODOO_PASSWORD={password}\n",
        f"\n# Test Mode - Set to 'false' for real operations\n",
        f"DRY_RUN=false\n",
        f"ENVIRONMENT=test\n"
    ]

    # Remove existing Odoo config
    env_content = [line for line in env_content if not line.startswith("ODOO_")]
    env_content = [line for line in env_content if not line.startswith("DRY_RUN=")]

    # Add new config
    with open(env_file, "w") as f:
        f.writelines(env_content)
        f.writelines(odoo_config)

    # Set permissions (Unix only)
    try:
        os.chmod(env_file, 0o600)
        print("  [OK] File permissions set to 600 (owner read/write only)")
    except:
        print("  [WARN] Could not set file permissions")

    print(f"\n[SUCCESS] Credentials saved to {env_file}")
    print("\nTo use these credentials:")
    print("  1. Copy .env.local to .env")
    print("  2. Or run: export $(cat .env.local | xargs)")
    print("  3. Then run: python test_odoo_real.py")

    return {
        'url': url,
        'db': db,
        'username': username,
        'env_file': env_file
    }

def test_connection_quick():
    """Quick connection test"""
    print("\n" + "="*60)
    print("QUICK CONNECTION TEST")
    print("="*60)

    # Load .env.local if it exists
    env_local = Path(".env.local")
    if env_local.exists():
        print(f"Loading credentials from {env_local}...")
        with open(env_local, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

    # Check credentials
    if not all([os.getenv("ODOO_URL"), os.getenv("ODOO_DB"),
                os.getenv("ODOO_USERNAME"), os.getenv("ODOO_PASSWORD")]):
        print("[ERROR] Missing Odoo credentials!")
        print("Please run: python configure_odoo_real.py")
        return False

    # Test basic HTTP connection
    import urllib.request
    import urllib.error

    url = os.getenv("ODOO_URL")
    try:
        print(f"\nTesting connection to {url}...")
        response = urllib.request.urlopen(f"{url}/web/database/selector", timeout=10)
        if response.getcode() == 200:
            print("[OK] Odoo server is responding")
            return True
    except urllib.error.HTTPError as e:
        print(f"[WARN] HTTP Error: {e.code}")
        if e.code == 404:
            print("  This is normal - the endpoint may not exist")
            return True
    except urllib.error.URLError as e:
        print(f"[ERROR] Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check if Odoo is running")
        print("  2. Verify the URL is correct")
        print("  3. Check network connectivity")
        print("  4. Verify firewall settings")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

    return False

def main():
    """Main configuration"""
    print("This script will help you configure real Odoo credentials.")
    print("Your credentials will be saved to .env.local with restricted permissions.\n")

    # First, try quick test
    if Path(".env.local").exists():
        print("Found existing .env.local file")
        if input("Test existing connection? (y/N): ").lower() == 'y':
            test_connection_quick()
            return

    # Configure new credentials
    config = configure_odoo_credentials()

    if config:
        print("\n" + "="*60)
        print("CONFIGURATION COMPLETE")
        print("="*60)
        print(f"Odoo URL: {config['url']}")
        print(f"Database: {config['db']}")
        print(f"Username: {config['username']}")
        print(f"Config file: {config['env_file']}")

if __name__ == "__main__":
    main()