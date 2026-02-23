#!/usr/bin/env python3
"""
Setup All Credentials - Configure all service credentials
"""

import os
from pathlib import Path

def create_env_from_template():
    """Create .env from template"""
    template_file = Path(".env.template")
    env_file = Path(".env")

    if not template_file.exists():
        print("[ERROR] .env.template not found!")
        return False

    if env_file.exists():
        print("[INFO] .env already exists")
        if input("Overwrite? (y/N): ").lower() != 'y':
            return False

    # Copy template to .env
    with open(template_file, "r") as f:
        content = f.read()

    with open(env_file, "w") as f:
        f.write(content)

    print(f"[OK] Created {env_file} from template")
    return True

def show_configuration_guide():
    """Show configuration guide"""
    print("\n" + "="*60)
    print("CREDENTIAL CONFIGURATION GUIDE")
    print("="*60)

    print("""
To configure your AI Employee system:

1. EDIT THE .ENV FILE:
   Open .env in your editor and replace placeholder values:

   [CORE SYSTEM]
   - SECRET_KEY: Generate a random 12+ character string
   - JWT_SECRET_KEY: Generate another random 12+ character string

   [ODOO]
   - ODOO_URL: Your Odoo instance URL (e.g., http://localhost:8069)
   - ODOO_DB: Your Odoo database name
   - ODOO_USERNAME: Your Odoo username
   - ODOO_PASSWORD: Your Odoo password

   [GMAIL]
   - Get OAuth2 credentials from Google Cloud Console
   - Generate refresh token using OAuth2 flow

   [X/TWITTER]
   - Create app at https://developer.twitter.com/
   - Get API keys and access tokens

   [LINKEDIN]
   - Create app at https://www.linkedin.com/developers/
   - Get access token

   [WHATSAPP]
   - Create app at https://developers.facebook.com/
   - Get phone number ID and access token

   [FACEBOOK/INSTAGRAM]
   - Create app at https://developers.facebook.com/
   - Get page access token

2. SECURITY NOTES:
   - Never commit .env to version control
   - Keep .env file permissions restricted (600 on Unix)
   - Use app passwords, not main passwords
   - Rotate keys regularly

3. TESTING:
   - Keep DRY_RUN=true for initial testing
   - Set to false only when ready for real operations

4. QUICK START:
   For Odoo testing only, you need:
   - SECRET_KEY and JWT_SECRET_KEY (any random strings)
   - ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD
   - Keep DRY_RUN=true initially
""")

def validate_env():
    """Validate .env configuration"""
    print("\n" + "="*60)
    print("VALIDATING CONFIGURATION")
    print("="*60)

    # Load .env
    from dotenv import load_dotenv
    load_dotenv()

    # Required fields
    required = {
        "SECRET_KEY": "Core system secret",
        "JWT_SECRET_KEY": "JWT token secret",
    }

    missing = []
    for field, desc in required.items():
        if not os.getenv(field):
            missing.append(f"{field} - {desc}")

    if missing:
        print("[ERROR] Missing required fields:")
        for field in missing:
            print(f"  - {field}")
        return False

    print("[OK] Core configuration valid")

    # Check service configurations
    services = {
        "Odoo": ["ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"],
        "Gmail": ["GMAIL_TOKEN"],
        "X/Twitter": ["X_API_KEY", "X_API_SECRET"],
        "LinkedIn": ["LINKEDIN_ACCESS_TOKEN"],
        "WhatsApp": ["WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_ACCESS_TOKEN"],
        "Facebook": ["FACEBOOK_ACCESS_TOKEN"]
    }

    print("\nService Configuration:")
    for service, fields in services.items():
        configured = all(os.getenv(f) for f in fields)
        status = "[OK]" if configured else "[SKIP]"
        print(f"  {status} {service}")

    return True

def main():
    """Main setup"""
    print("AI Employee - Credential Setup")
    print("==============================")

    # Create .env from template
    if not create_env_from_template():
        return

    # Show guide
    show_configuration_guide()

    # Validate
    if input("\nValidate configuration now? (y/N): ").lower() == 'y':
        validate_env()

    print("\n" + "="*60)
    print("SETUP COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Edit .env with your credentials")
    print("2. Run: python setup_credentials.py --validate")
    print("3. Test individual services:")
    print("   - Odoo: python test_odoo_real.py")
    print("   - Gmail: python test_gmail_real.py")
    print("   - etc.")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        from dotenv import load_dotenv
        load_dotenv()
        validate_env()
    else:
        main()